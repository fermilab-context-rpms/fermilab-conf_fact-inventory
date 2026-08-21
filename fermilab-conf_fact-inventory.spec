%global fact_inventory_api_server %{?fact_inventory_api_server}%{!?fact_inventory_api_server:https://fact-inventory.fnal.gov}

Name:    fermilab-conf_fact-inventory
Version: 0.0.1
Release: 1%{?dist}

Group:   Fermilab
License: AGPL-3.0-or-later

URL:     https://github.com/fermilab-context-rpms/fermilab-conf_fact-inventory
Source0: %{name}.tar.gz

BuildArch: noarch

#Obsoletes:  fermilab-conf_ocsinventory < 1:0
#Obsoletes:  fermilab-util_ocsinventory < 1:0

#######################################################
# Required for %%post script macros
BuildRequires: systemd

# Required for %%check file validation
BuildRequires: python3
BuildRequires: python3-pyyaml
BuildRequires: logrotate

#######################################################
# The service and its component parts
Requires: systemd
Requires(post): systemd
Requires(preun): systemd
Requires(postun): systemd

Requires:  ansible-core
Requires:  /usr/bin/ansible-playbook
Requires:  python3

Requires:  ansible-collection(fermilab.fact_inventory)

# Suggests is a very weak dep.
# The service will overwrite the log automatically ensuring
# you always have the latest copy.
# Rotation is only required for folks who want a long audit trail.
Suggests:  logrotate

#######################################################
# local_fact: lsmod -> bash, sort, LANG=C.UTF-8
Requires:  bash
Requires:  coreutils
Requires:  glibc-common


#######################################################
Summary: Configure fact-inventory for Fermilab
%description
This RPM will setup and enable fact-inventory collection for use at Fermilab.


%prep
%autosetup -n %{name}


%build

#######################################################
cat >conf/%{name}_api_server.yml <<EOF
---
fact_inventory_gather_api_server: "%{fact_inventory_api_server}"
EOF

cat >conf/%{name}_local_facts_dir.yml <<EOF
---
fact_inventory_gather_local_facts_dir: "%{_libexecdir}/%{name}/local_facts/"
EOF

cat >conf/%{name}_audit_log.yml <<EOF
---
fact_inventory_gather_audit_enabled: true
fact_inventory_gather_audit_path: %{_var}/log/%{name}/inventory.json
EOF

cat >conf/%{name}_suppress_stdout.yml <<EOF
---
fact_inventory_gather_suppress_audit_output: true
fact_inventory_gather_suppress_collection_output: true
fact_inventory_gather_suppress_submit_output: true
EOF

#######################################################
cat >conf/%{name}.logrotate <<EOF
%{_var}/log/%{name}/inventory.json {
    missingok
    notifempty
    daily
    compress
    minsize 128
}
EOF

#######################################################
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
%{__mkdir_p} -m 0755 %{buildroot}/%{_datarootdir}/%{name}/group_vars/all

%{__ln_s} %{_sysconfdir}/%{name} %{buildroot}/%{_datarootdir}/%{name}/host_vars/localhost

# Files packaged up in the source repo
%{__cp} -a local_facts/*.fact %{buildroot}/%{_libexecdir}/%{name}/local_facts/

%{__install} -m 0644 -D conf/README.txt %{buildroot}/%{_sysconfdir}/%{name}/README.txt

%{__install} -m 0644 -D gather.yml %{buildroot}/%{_datarootdir}/%{name}/gather.yml
%{__install} -m 0644 -D hosts.yml %{buildroot}/%{_datarootdir}/%{name}/hosts.yml

%{__install} -m 0644 -D systemd/30-%{name}.preset %{buildroot}/%{_presetdir}/30-%{name}.preset
%{__install} -m 0644 -D systemd/%{name}.service %{buildroot}/%{_unitdir}/%{name}.service
%{__install} -m 0644 -D systemd/%{name}.timer %{buildroot}/%{_unitdir}/%{name}.timer

# Files generated in this spec
%{__install} -m 0644 -D conf/%{name}.logrotate %{buildroot}/%{_sysconfdir}/logrotate.d/%{name}

%{__cp} conf/*.yml %{buildroot}/%{_datarootdir}/%{name}/group_vars/all/

%{__install} -m 0644 -D systemd/%{name}-paths.conf %{buildroot}/%{_unitdir}/%{name}.service.d/%{name}-paths.conf


%check

%if 0%{?rhel} > 8
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
        result = subprocess.run([path], capture_output=True, text=True, check=True)
        try:
            json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise SystemExit(f'ERROR: {path} output is not valid JSON: {exc}')
    else:
        with open(path) as stream:
            json.load(stream)

# conf: every .yml file must be valid YAML
for name in sorted(os.listdir('conf')):
    if name.endswith('.yml'):
        with open(os.path.join('conf', name)) as stream:
            yaml.safe_load(stream)

# ansible: Check our control files
for name in ['gather.yml', 'hosts.yml']:
    with open(name) as stream:
        yaml.safe_load(stream)

# systemd: every unit (not preset) must have valid syntax
# Use strict=False to allow duplicate keys (e.g., multiple Environment= lines)
# systemd-analyze can't run from mock chroot
for name in sorted(os.listdir('systemd')):
    if name.endswith('.preset'):
        continue
    path = os.path.join('systemd', name)
    config = configparser.ConfigParser(strict=False)
    config.read(path)
    if not config.sections():
        raise SystemExit(f'ERROR: {name} has no sections')
PYEOF
%endif

# Native syntax check of the logrotate config
logrotate -d conf/%{name}.logrotate || exit 1


%preun
%systemd_preun %{name}.timer


%post
# default timespec may have changed, always run this
if [ -x "/usr/lib/systemd/systemd-update-helper" ]; then
    /usr/lib/systemd/systemd-update-helper system-reload || :
fi

%systemd_post %{name}.timer

# ensure timer is running if unmasked
if systemctl is-enabled --quiet %{name}.timer; then
    systemctl start %{name}.timer
fi


%postun
%systemd_postun_with_restart %{name}.timer

# missing or different unit files present logging errors, always run this
if [ -x "/usr/lib/systemd/systemd-update-helper" ]; then
    /usr/lib/systemd/systemd-update-helper system-reload || :
fi


%files
%doc README.md
%license LICENSE

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
* Thu Aug 20 2026 Pat Riehecky <riehecky@fnal.gov> - 0.0.1-1
- Initial test package
