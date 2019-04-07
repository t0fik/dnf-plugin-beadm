Name:		python3-dnf-plugin-beadm
Version:	0.1.1
Release:	1%{?dist}
Summary:	BE Plugin for DNF

License:	GPLv3
URL:		https://github.com/t0fik/dnf-plugin-beadm
Source0:	https://github.com/t0fik/dnf-plugin-beadm/archive/v%{version}/dnf-plugin-beadm-%{version}.tar.gz
BuildArch:	noarch

Requires:	zfs-beadm >= 1.1.10
Requires:   python3-dnf

BuildRequires: python3
BuildRequires: python3-rpm-macros

Provides: dnf-command(beadm)

%description
Beadm plugin allows dnf utilize ZFS boot environments

%prep
%setup -q

%install
install -D -pm 644 beadm.py %{buildroot}%{python3_sitelib}/dnf-plugins/beadm.py

%files
%{python3_sitelib}/dnf-plugins/beadm.py
%{python3_sitelib}/dnf-plugins/__pycache__/beadm.*
%license

%changelog
* Sun Apr 07 2019 Jerzy Drozdz <rpmbuilder@jdsieci.pl> - 0.1.1-1
- dist-sync is default method now

* Sat Apr 06 2019 Jerzy Drozdz <rpmbuilder@jdsieci.pl> - 0.1.0-2
- Added python3-dnf requisite

* Sat Apr 06 2019 Jerzy Drozdz <rpmbuilder@jdsieci.pl> - 0.1.0-1
- Initial build
