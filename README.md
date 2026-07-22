# fermilab-conf_fact-inventory

RPM configuration package that sets up and enables the Fermilab
fact-inventory client on a host.  Once installed and running, the host
gathers local facts and reports them to the Fermilab inventory service.

The client itself is implemented by the upstream project
<https://github.com/fermitools/python-fact_inventory> and its Ansible
collection `fermilab.fact_inventory`; this package provides the
site-specific configuration, local facts, and scheduling glue.

## What it does

After installation, a systemd timer runs once per day (with a random
delay to spread load) and triggers a oneshot service that executes:

```
/usr/bin/ansible-playbook -i localhost.yml gather.yml
```

inside `%{_datarootdir}/fermilab-conf_fact-inventory`.  The playbook
runs the `fermilab.fact_inventory.gather` role against localhost, which
collects facts from this host and ships them to the inventory API
server.

The timer is enabled through a systemd preset, so it becomes active
immediately on install:

```
%{_presetdir}/30-fermilab-conf_fact-inventory.preset
```

## Installed layout

| Path | Purpose |
|------|---------|
| `%{_datarootdir}/fermilab-conf_fact-inventory/` | Ansible playbook, inventory, and role configuration (`group_vars/all`) |
| `%{_sysconfdir}/fermilab-conf_fact-inventory/` | Site configuration overrides, symlinked as `host_vars/localhost` |
| `%{_sysconfdir}/logrotate.d/fermilab-conf_fact-inventory` | Logrotate rules for the audit log |
| `%{_var}/log/fermilab-conf_fact-inventory/inventory.json` | Audit log written by the collection |
| `%{_libexecdir}/fermilab-conf_fact-inventory/local_facts/` | Local fact scripts executed by the collection |
| `%{_unitdir}/fermilab-conf_fact-inventory.{service,timer}` | systemd units driving the daily run |

### Site configuration

The API endpoint and paths are set in `group_vars/all` files generated
by the spec at build time:

* `fact_inventory_api_server` - the inventory service URL (defaults to
  <https://fact-inventory.fnal.gov>)
* `fact_inventory_local_facts_dir` - where the shipped `.fact` files live
* `fact_inventory_audit_path` - where the audit log is written

Per-host overrides go into `%{_sysconfdir}/fermilab-conf_fact-inventory/`
(dropping YAML files there mirrors them into `host_vars/localhost`).

## Local facts

Any file ending in `.fact` placed in the local facts directory is
executed by the collection on each run.  Files are packaged with the
RPM and shipped to `%{_libexecdir}/fermilab-conf_fact-inventory/local_facts/`:

* `lsmod.fact` - executable script reporting loaded kernel modules as
  the `lsmod` fact (from `/proc/modules`, sorted)

Two formats are supported:

* Executable scripts - output JSON on stdout
* Static files - must contain valid JSON (no shebang, no `+x` bit)

Every shipped fact file must end in `.fact`; the spec `%check` phase
verifies this, runs executable facts, and validates that non-executable
ones parse as JSON.

## Runtime behavior

* The service is `Type=oneshot` with `Restart=on-failure` (backoff of
  300s, at most 3 starts per hour), so a transient failure is retried
  automatically.
* The service runs with strict systemd sandboxing (`ProtectSystem`,
  `ProtectHome`, `PrivateTmp`, read-only root, and hardened kernel
  protections) at reduced scheduling priority (`Nice=6`).
* The audit log is rotated automatically by logrotate.
* View run job results with:

```
systemctl status fermilab-conf_fact-inventory.service
journalctl -u fermilab-conf_fact-inventory.service
```
or:
```
cat %{_var}/log/fermilab-conf_fact-inventory/inventory.json
```

## Building the RPM

Requires `rpm-build` and the `fermilab.fact_inventory` Ansible
collection at install time (see the spec `Requires`).

```
make sources   # create the source tarball for koji
make srpm      # build a source RPM
make rpm       # build a binary RPM locally
```

## Development

Add or edit `.fact` files under `local_facts/`, then build.  Facts must
be executable scripts emitting JSON or static JSON files, and must end
in `.fact` for the `%check` phase to accept them.

## License

AGPL-3.0-or-later
