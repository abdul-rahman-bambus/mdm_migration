# Schema discovery status

The local connectivity probe found different field counts on all three core
models. Counts alone identify no specific renamed, removed or compatible fields.

`scripts/export_local_schema.py` requests explicit field metadata for
product.template, product.product and res.partner. It does not collect business
records, defaults, attachments or passwords. Only local lab loopback endpoints
are accepted. Per-model failures remain visible as `error_type` entries.

Run from a local working directory with the existing exported connection
variables. It creates `odoo-schema-<UTC timestamp>.json` using exclusive file
creation. Inspect the JSON and share it for comparison. This script has mocked
unit coverage; actual local schema exports have not yet been supplied.

Computed status, defaults and API writeability may not be discoverable through
fields_get. Omitted attributes mean unknown, not false. In particular readonly
false does not prove create/write permission or safe migration behavior.

Next: compare actual snapshots conservatively; separately review suspected
renames, changed selection keys, relational dependencies and required fields.
The module inventory and dependent-model schemas still need collection.
No mapping configuration is approved and no comparison report exists yet.
