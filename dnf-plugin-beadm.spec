Name:		python3-dnf-plugin-beadm
Version:	0.1.0
Release:	1%{?dist}
Summary:	BE Plugin for DNF

License:	GPLv3
URL:		https://github.com/t0fik/dnf-plugin-beadm
Source0:	https://github.com/t0fik/dnf-plugin-beadm/archive/v%{version}/dnf-plugin-beadm-%{version}.tar.gz

Requires:	zfs-beadm >= 1.1.10

Provides: dnf-command(beadm)

%description
Beadm plugin allows dnf utilize ZFS boot environments

%install
install -D -pm 644 beadm.py %{python3_sitelib}/dnf-plugins/beadm.py

%files
%{python3_sitelib}/dnf-plugins/beadm.py
%license

%changelog
* Fri 19 2019 Jerzy Drozdz <rpmbuilder@jdsieci.pl> - 0.1.0-1
- Initial build
