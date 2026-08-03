%define apiserver https://fact-inventory.fnal.gov

Name:    fermilab-conf_fact-inventory
Version: 0.0.0
Release: 3%{?dist}

Group:   Fermilab
License: AGPL-3.0-or-later

URL:     https://github.com/fermilab-context-rpms/fermilab-conf_fact-inventory
Source0: %{name}.tar.gz

BuildArch: noarch

# Required for %%post scripts
BuildRequires: systemd

# Required for %%check phase validation
BuildRequires: python3
BuildRequires: python3-pyyaml
BuildRequires: logrotate

Requires: systemd
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

OrderWithRequires(post): systemd
OrderWithRequires(preun): systemd
OrderWithRequires(postun): systemd

Requires:  ansible-core
Requires:  /usr/bin/ansible-playbook

Requires:  ansible-collection(fermilab.fact_inventory)

Suggests:  logrotate

#Obsoletes:  fermilab-conf_ocsinventory < 1:0

Summary: Configure fact-inventory for Fermilab
%description
This RPM will setup and enable fact-inventory collection for use at Fermilab.


%prep
%autosetup -n %{name}


%build

cat >conf/%{name}_api_server.yml <<EOF
---
fact_inventory_gather_api_server: "%{apiserver}"
EOF

cat >conf/%{name}_local_facts_dir.yml <<EOF
---
fact_inventory_gather_local_facts_dir: "%{_libexecdir}/%{name}/local_facts/"
EOF

cat >conf/%{name}_log.yml <<EOF
---
fact_inventory_gather_audit_enabled: true
fact_inventory_gather_audit_path: %{_var}/log/%{name}/inventory.json
EOF


cat >conf/%{name}.logrotate <<EOF
%{_var}/log/%{name}/inventory.json {
    missingok
    notifempty
    create 0600 root root
    daily
    compress
}
EOF

cat > conf/README.yml <<EOF
---
# This directory is parsed as an ansible host_vars location for
# the "localhost" hostname. Parsed files should end in ".yaml",
# ".yml", or ".json".
EOF


cat >systemd/%{name}-paths.conf <<EOF
[Service]
WorkingDirectory=%{_datarootdir}/%{name}

ReadWritePaths=%{_var}/log/%{name}
EOF


%install

%{__mkdir_p} -m 0755 %{buildroot}/%{_sysconfdir}/%{name}
%{__mkdir_p} -m 0755 %{buildroot}/%{_var}/log/%{name}
%{__mkdir_p} -m 0755 %{buildroot}/%{_libexecdir}/%{name}/local_facts
%{__mkdir_p} -m 0755 %{buildroot}/%{_datarootdir}/%{name}/host_vars

%{__ln_s} %{_sysconfdir}/%{name} %{buildroot}/%{_datarootdir}/%{name}/host_vars/localhost

# Files packaged up in the source repo
%{__cp} -a local_facts/*.fact %{buildroot}/%{_libexecdir}/%{name}/local_facts/

%{__install} -m 0644 -D gather.yml %{buildroot}/%{_datarootdir}/%{name}/gather.yml
%{__install} -m 0644 -D hosts.yml %{buildroot}/%{_datarootdir}/%{name}/hosts.yml

%{__install} -m 0644 -D systemd/30-%{name}.preset %{buildroot}/%{_presetdir}/30-%{name}.preset
%{__install} -m 0644 -D systemd/%{name}.service %{buildroot}/%{_unitdir}/%{name}.service
%{__install} -m 0644 -D systemd/%{name}.timer %{buildroot}/%{_unitdir}/%{name}.timer

# Files generated in this spec
%{__install} -m 0644 -D conf/%{name}.logrotate %{buildroot}/%{_sysconfdir}/logrotate.d/%{name}

%{__install} -m 0644 -D conf/README.yml %{buildroot}/%{_sysconfdir}/%{name}/README.yml

%{__install} -m 0644 -D conf/%{name}_api_server.yml %{buildroot}/%{_datarootdir}/%{name}/group_vars/all/%{name}_api_server.yml
%{__install} -m 0644 -D conf/%{name}_local_facts_dir.yml %{buildroot}/%{_datarootdir}/%{name}/group_vars/all/%{name}_local_facts_dir.yml
%{__install} -m 0644 -D conf/%{name}_log.yml %{buildroot}/%{_datarootdir}/%{name}/group_vars/all/%{name}_log.yml

%{__install} -m 0644 -D systemd/%{name}-paths.conf %{buildroot}/%{_unitdir}/%{name}.service.d/%{name}-paths.conf


%check

python3 - <<'PYEOF' || exit 1
import configparser
import json
import os
import subprocess
import sys

import yaml

# local_facts: executables must run, other files must be valid JSON,
# and every file must end in .fact
for name in sorted(os.listdir('local_facts')):
    path = os.path.join('local_facts', name)
    if not os.path.isfile(path):
        continue
    if not name.endswith('.fact'):
        raise SystemExit(f'ERROR: {path} does not end in .fact')
    if os.access(path, os.X_OK):
        subprocess.run([path], stdout=subprocess.DEVNULL, check=True)
    else:
        with open(path) as stream:
            json.load(stream)

# conf: every .yml file must be valid YAML
for name in sorted(os.listdir('conf')):
    if name.endswith('.yml'):
        with open(os.path.join('conf', name)) as stream:
            yaml.safe_load(stream)

# systemd: every unit (not preset) must have at least one section
for name in sorted(os.listdir('systemd')):
    if name.endswith('.preset'):
        continue
    config = configparser.ConfigParser()
    config.read(os.path.join('systemd', name))
    if not config.sections():
        raise SystemExit(f'ERROR: {name} has no sections')
PYEOF

# Native syntax check of the logrotate config
logrotate -d conf/%{name}.logrotate || exit 1


%preun
%systemd_preun %{name}.timer


%post
%systemd_post %{name}.timer

# default timespec may have changed
if [ -x "/usr/lib/systemd/systemd-update-helper" ]; then
    /usr/lib/systemd/systemd-update-helper mark-restart-system-units %{name}.timer || :
fi

# ensure timer is running
systemctl start %{name}.timer


%postun
%systemd_postun_with_restart %{name}.timer

# missing or different unit files present logging errors
if [ -x "/usr/lib/systemd/systemd-update-helper" ]; then
    /usr/lib/systemd/systemd-update-helper system-reload || :
fi


%files
%doc README.md

%config(noreplace) %{_sysconfdir}/logrotate.d/%{name}

# we don't actually ship a config
# but we do ship a README so the dir isn't "empty"
%{_sysconfdir}/%{name}

%{_datarootdir}/%{name}
%{_libexecdir}/%{name}/local_facts

%{_presetdir}/30-%{name}.preset
%{_unitdir}/%{name}.service
%{_unitdir}/%{name}.timer
%{_unitdir}/%{name}.service.d/%{name}-paths.conf

%dir %attr(0755, root, root) %{_var}/log/%{name}


%changelog
* Mon Aug 3 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.0-3
- Fix failure to start unit

* Mon Aug 3 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.0-2
- Fix failure to start timer unit

* Fri Jul 31 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.0-1
- Initial test package
