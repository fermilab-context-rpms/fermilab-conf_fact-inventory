%define apiserver https://fact-inventory.fnal.gov

Name:		fermilab-conf_fact-inventory
Version:	0.0.0
Release:	1%{?dist}

Group:		Fermilab
License:	AGPL-3.0-or-later

URL:		https://github.com/fermilab-context-rpms/fermilab-conf_fact-inventory
Source0:	%{name}.tar.gz

BuildArch:	noarch
BuildRequires:	systemd

Requires:	ansible-core
Requires:	fact-inventory-gather
Requires:	/usr/libexec/fact-inventory-gather/gather.yml

Requires:	systemd
Requires:	kmod

#Obsoletes:	fermilab-conf_ocsinventory

Summary:	Configure fact-inventory for Fermilab
%description
This RPM will setup and enable fact-inventory for use at Fermilab.


%prep
%autosetup -n %{name}

%build

cat >%{name}.env <<EOF
CONNECTION=-i "localhost," -c local
VAR_ARGS=-e api_server="%{apiserver}" -e custom_fact_path="%{_libexecdir}/%{name}/local_facts/" -e "@%{_sysconfdir}/default/%{name}.yml"
EOF

%install

%{__install} -m 0644 -D %{name}.env %{buildroot}/%{_datarootdir}/%{name}/%{name}.env

%{__install} -m 0644 -D default/fermilab-conf_fact-inventory.yml %{buildroot}/%{_sysconfdir}/default/%{name}.yml

%{__install} -m 0644 -D systemd/30-%{name}.preset %{buildroot}/%{_presetdir}/30-%{name}.preset
%{__install} -m 0644 -D systemd/%{name}.service %{buildroot}/%{_unitdir}/%{name}.service
%{__install} -m 0644 -D systemd/%{name}.timer %{buildroot}/%{_unitdir}/%{name}.timer

%{__mkdir_p} -m 0755 %{buildroot}/%{_libexecdir}/%{name}/local_facts
%{__cp} -a local_facts/*.fact %{buildroot}/%{_libexecdir}/%{name}/local_facts/


%preun
%systemd_preun %{name}.timer

%post
%systemd_post %{name}.timer

%postun
%systemd_postun_with_restart %{name}.timer

%files
%config(noreplace) %{_sysconfdir}/default/%{name}.yml
%{name}/%{name}.env
%{_presetdir}/30-%{name}.preset
%{_unitdir}/%{name}.service
%{_unitdir}/%{name}.timer
%{_libexecdir}/%{name}/local_facts

%changelog
*
- Initial test package
