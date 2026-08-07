Host-specific configuration overrides
=============================================================================

This directory is linked as host_vars/localhost during Ansible execution,
allowing per-host customization of the fact-inventory client.

Configuration files
-------------------
Add YAML, JSON, or extensionless files to this directory. Only the
following file types are recognized:
  * .yaml
  * .yml
  * .json

Files without an extension may be treated as YAML. This should be avoided.

Files in this directory override or extend the default configuration
defined in group_vars/all, enabling site-specific customization.

Example
-------
Create "api_server.yml" to override the inventory server:

  echo "api_server: https://custom-inventory.example.com" > api_server.yml

Multiple files are merged; use descriptive names to organize settings
by purpose - such as "logging.yml"

Consult the role documentation for fermilab.fact_inventory.gather and its
utilized ansible variables.

See the packaged doc README.md for installation layout and configuration.
