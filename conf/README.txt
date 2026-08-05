Host-specific configuration overrides for fermilab-conf_fact-inventory
======================================================================

This directory is linked as host_vars/localhost during Ansible execution,
allowing per-host customization of the fact-inventory client.

Configuration files
-------------------
Add YAML, JSON, or extensionless files to this directory. Only the
following file types are recognized:
  - .yaml
  - .yml
  - .json

Files without an extension may be treated as YAML. This should be avoided.

Files in this directory override or extend the default configuration
defined in group_vars/all, enabling site-specific customization such as:
  - Custom fact_inventory_api_server endpoint
  - fact_inventory_audit_path location
  - Additional local facts or variables

Example
-------
Create "inventory.yml" to override the inventory server:
  fact_inventory_api_server: https://custom-inventory.example.com

Multiple files are merged; use descriptive names to organize settings
by purpose (e.g., "database.yml", "api.yml", "monitoring.yml").

See the packaged doc README.md for installation layout and configuration details.
