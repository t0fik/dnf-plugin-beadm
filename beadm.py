from __future__ import unicode_literals
import dnf.cli
from dnf.cli import CliError
import subprocess
import os
import os.path
import json
import tempfile

from pprint import pprint


RELEASEVER_MSG = "Need a --releasever greater than the current system version."
CANT_RESET_RELEASEVER = "Sorry, you need to use 'download --releasever' instead of '--network'"

# --- Helper functions ----------------------------------------------------------


def mount(bename, mountpoint=''):
    proc = subprocess.Popen(['/usr/sbin/beadm', 'mount', '-m', bename, mountpoint],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)
    root = proc.stdout.readline().decode('utf-8').rstrip(os.linesep)
    proc.wait()
    for mp in ['/dev', '/sys', '/proc', '/run']:
        subprocess.Popen(['/usr/bin/mount', '-o', 'bind', mp, os.path.join(root, mp.lstrip('/'))],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    subprocess.Popen(['/usr/bin/mount', '-t', 'efivars', 'efivars', os.path.join(root, 'sys/firmware/efi/efivars')],
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    source, target = get_efi()
    subprocess.Popen(['/usr/bin/mount', source, os.path.join(root, target.lstrip('/'))],
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)
    source, target = get_selinux_fs()
    if source is not None:
        subprocess.Popen(['/usr/bin/mount', '-t', 'selinuxfs', source, os.path.join(root, target.lstrip('/'))],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    return root


def unmount(be):
    proc = subprocess.Popen(['/usr/sbin/beadm', 'umount', be],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    proc.wait()
    if proc.returncode != 0:
        return False
    return True


def activate_be(bename):
    subprocess.Popen(['/usr/sbin/beadm', 'activate', bename],
                     stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL)


def create_be(bename):
    proc = subprocess.Popen(['/usr/sbin/beadm', 'create', bename],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    proc.wait()
    if proc.returncode != 0:
        return False
    return True


def distro_id():
    proc = subprocess.Popen(['/usr/bin/lsb_release', '-si'],
                     stdout=subprocess.PIPE,
                     stderr=subprocess.DEVNULL)
    return proc.stdout.readline().decode('utf-8').rstrip(os.linesep)


def get_efi():
    for fs in findmnt():
        if fs.get('target') == '/boot/efi':
            return fs.get('source'), fs.get('target')


def get_selinux_fs():
    for fs in findmnt():
        if fs.get('source') == 'selinuxfs':
            return fs.get('source'), fs.get('target')
    return None, None


def findmnt():
    proc = subprocess.Popen(['/usr/bin/findmnt', '-lJ'],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL)
    return json.load(proc.stdout).get('filesystems')


def checkReleaseVer(conf, target=None):
    if dnf.rpm.detect_releasever(conf.installroot) == conf.releasever:
        raise CliError(RELEASEVER_MSG)
    if target and target != conf.releasever:
        # it's too late to set releasever here, so this can't work.
        # (see https://bugzilla.redhat.com/show_bug.cgi?id=1212341)
        raise CliError(CANT_RESET_RELEASEVER)


CMDS = ['sysupg', 'update']


# --- The actual Plugin and Command


class Beadm(dnf.Plugin):
    name = 'beadm-system-upgrade'

    def __init__(self, base, cli):
        super(Beadm, self).__init__(base, cli)
        if cli:
            cli.register_command(BeadmCommand)


class BeadmCommand(dnf.cli.Command):
    aliases = ('beadm', 'be')
    summary = 'Upgrades system on ZFS boot environment'

    def __init__(self, cli):
        super(BeadmCommand, self).__init__(cli)

    @staticmethod
    def set_argparser(parser):
        parser.add_argument("--no-downgrade", dest='distro_sync',
                            action='store_false',
                            help="keep installed packages if the new release's version is older")
        parser.add_argument("--be", type=str,
                            help="Optional boot environment name")
        parser.add_argument('tid', nargs=1, choices=CMDS,
                            metavar="[%s]" % "|".join(CMDS))

    def pre_configure(self):
        self.opts.installroot = tempfile.mkdtemp()
        self.base.conf.cachedir = os.path.join(self.opts.installroot, self.base.conf.cachedir.lstrip('/'))
        self.base.conf.logdir = os.path.join(self.opts.installroot, self.base.conf.logdir.lstrip('/'))
        self.base.conf.persistdir = os.path.join(self.opts.installroot, self.base.conf.persistdir.lstrip('/'))
        if self.opts.be is None:
            self.opts.be = '{}{}'.format(distro_id().lower(), self.opts.releasever)

    def configure(self):
        self._call_sub("configure")

    def run(self):
        self._call_sub('run')

    def run_transaction(self):
        self._call_sub("transaction")

    def _call_sub(self, name):
        subfunc = getattr(self, name + '_' + self.opts.tid[0], None)
        if callable(subfunc):
            subfunc()

    # System upgrade sub-command
    def run_sysupg(self):
        if self.opts.distro_sync:
            self.base.distro_sync()
        else:
            self.base.upgrade_all()


    def transaction_sysupg(self):
        if not unmount(self.opts.be):
            print(f"Could not unmount. To unmount run 'beadm unmount {self.opts.be}'")
        print(f"Run 'beadm activate {self.opts.be}' to activate new system on next reboot")

    def configure_sysupg(self):
        checkReleaseVer(self.base.conf, target=self.opts.releasever)
        print("Creating BE")
        if not create_be(self.opts.be):
            raise CliError(f"BE '{self.opts.be}' already exists.")
        self.cli.demands.root_user = True
        self.cli.demands.resolving = True
        self.cli.demands.available_repos = True
        self.cli.demands.sack_activation = True
        mount(self.opts.be, self.opts.installroot)

    # Update system packages
    def run_update(self):
        self.base.upgrade()

    def configure_update(self):
        self.cli.demands.root_user = True
        self.cli.demands.resolving = True
        self.cli.demands.available_repos = True
        self.cli.demands.sack_activation = True
        mount(self.opts.be, self.opts.installroot)
