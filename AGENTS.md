# Bambus Odoo migration framework

Read this file and README.md first. Inspect the checkout before modifying code.
Use this existing isolated checkout; do not create worktrees unless requested.

## Objective and scope

Build a generic, auditable migration framework for the future MDM project.
The lab specification uses Odoo 12 Community → Odoo 20 Community. The client's
production target remains unconfirmed; its stated go-live is 2027-01-01.
Client modules, source database, filestore, workflows and acceptance criteria
have not been supplied. Never invent client-specific MDM behavior.

Products/templates/variants, partners, images, attachments and feasible chatter
are planned. Stock, valuation, financial balances and transactional migration
are out of scope without separate approval. No production access is authorized.

## Structure and environment

- `migration_lab/`: dependency-free Python assessment CLI, currently read-only.
- `migration_lab/schema.py`: offline comparison and unapproved mapping drafts.
- `migration_lab/inventory.py`: read-only local module/dependency inventory.
- `tests/`: unittest tests using synthetic loopback XML-RPC fixtures.
- `scripts/export_local_schema.py`: portable loopback-only metadata exporter.
- `.env.example`: variable names and non-secret lab defaults only.
- `docs/`: assessment, architecture, connectivity, test evidence and status.
- `test`: original repository placeholder; preserve it.

Expected external lab services: odoo12 (Odoo 12 Community, port 8012), pg12
(PostgreSQL 12), odoo20 (claimed Odoo 20 Community, port 8020), pg20
(PostgreSQL 16). Databases: odoo12_demo and odoo20_migration; documented DB
user: odoo. These are supplied specifications, not verified running versions.
The lab is local. Compose files and Dockerfiles are now tracked under
`lab/odoo_migration_lab/`; source clones and existing volumes remain local.
No Odoo containers have been started in this cloud task. Do not replace that lab.
Compose/installer require LAB_PG12_PASSWORD and LAB_PG20_PASSWORD with no defaults.
For existing volumes use their current passwords; changing environment variables
does not rotate database credentials. Inventory requires no container restart.
Develop and push on `development`; leave `main` unchanged. The user's lab upload
originally landed on main; its sanitized files were imported into development.
Do not push codex/development-before-cleanup; it preserves the earlier local
ancestry containing uploaded password literals. Remote main was not rewritten.

## Architecture and conventions

Planned: version-specific API adapters → schema discovery → explicit versioned
field mappings → dependency-ordered migration workers → reconciliation.
Use supported APIs; discover actual fields and external API availability before
implementation. Never silently ignore unsupported fields or copy all fields.
Never assume source IDs equal target IDs. Persistent mappings must include both
environment/database/model/record identities, run, mapping version and state.
Reruns and controlled updates must be idempotent, including target restore recovery.

An independent PostgreSQL journal will be authoritative and must survive target
restores. The planned `bambus_migration_control` Odoo addon is a synchronized UI,
not the sole journal. It must submit retry requests to an authorized worker;
never run arbitrary shell commands from web requests.

Record errors at field and record level with sanitized diagnostics, root cause,
severity and retry eligibility. Preserve history. A create/write response is not
final success: reconcile expected fields, relationships and binary content.
Normalize legitimate representation differences; document image resizing and
partial chatter limitations. Do not trigger historical email/notifications.

Retry flow: detect → diagnose → propose fix → approve → retry → reconcile → close.
Bound temporary retries; require approved corrections for permanent failures.
Never bypass reconciliation or erase failures. Never remove volumes, reset
databases, delete or deactivate business records without explicit authorization.

## Security and validation

Use laboratory accounts and environment-based credentials. Never print secrets,
raw RPC faults, unnecessary PII, credential files or the full process environment.
Keep TLS verification enabled. Remote credentials require HTTPS; loopback HTTP
is allowed for the lab. Read-only assessment never writes business records.

Run `python3 -m unittest discover -s tests -v` from the root. Tests require
loopback sockets. Fixtures do not validate live Odoo compatibility. Live checks:
`python3 -m migration_lab --live`; configure all variables first. No configuration
or authentication means blocked, never ready. Empty samples are explicit and
do not prove record-level behavior. Do not continue migration past failed live
prerequisites. Real migration tests must use synthetic data only.

## Status and handover

Implemented: assessment CLI, bounded read-only XML-RPC probes, offline schema
comparison, complete unapproved mapping draft and module/dependency inventory
tooling. Not implemented: migration writes, approved mappings, journal,
reconciliation, dashboard and recovery.
User-local screenshot evidence confirms XML-RPC authentication, server-reported
versions 12.0/20.0, and metadata/sample reads on three models. See
docs/local-connectivity-evidence.md; this is not a cloud integration test.
Cloud-to-local access and credential bindings remain unavailable here.
The core schema export is committed and compared under docs/schema-reports/.
Next: run `python3 -m migration_lab.inventory --output-dir reports/local-inventory-1`
locally with the existing exported variables. Missing dependency models remain
explicit partial results. Review module differences before deciding field maps.

Update README when setup/usage changes, this file when operational rules change,
and docs/PROJECT_STATUS.md after every meaningful implementation step. Record
unresolved decisions rather than inventing answers. Keep verified, failed,
partial, unsupported, planned and untested outcomes separate. Commit logical
changes when permitted; never claim unexecuted checks passed.
