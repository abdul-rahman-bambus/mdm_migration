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

- `migration_lab/`: standard-library assessment tools plus the scoped contact pilot.
- `migration_lab/pilot.py`: explicit synthetic-only seed/dry-run/apply/update worker.
- `migration_lab/journal.py`: PostgreSQL journal; pilot dependency is optional.
- `migration_lab/monitor.py`: host-side read-only journal export to tracking models.
- `addons/bambus_migration_control/`: Odoo 20 monitoring UI and validated import API.
- `mappings/`: versioned, scope-checked synthetic pilot mapping manifest.
- `lab/journal.compose.yaml`: independent PostgreSQL project/volume for the journal.
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
Cloud validation uses owned disposable Odoo/PostgreSQL containers only. Do not
replace the user's existing lab or treat these tests as its installation.
Odoo Compose/installer require LAB_PG12_PASSWORD and LAB_PG20_PASSWORD with no defaults.
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
tooling. The synthetic-contact pilot now implements explicit writes, persistent
ID mapping, journal events and read-back reconciliation. General business-data
migration, broader approved mappings, UI-triggered job execution and target-restore
recovery remain unimplemented. The read-only Odoo tracking dashboard is now built.
User-local screenshot evidence confirms XML-RPC authentication, server-reported
versions 12.0/20.0, and metadata/sample reads on three models. See
docs/local-connectivity-evidence.md; this is not a cloud integration test.
Cloud-to-local access and credential bindings remain unavailable here.
The core schema export is committed and compared under docs/schema-reports/.
Next: install the tracking addon locally and import existing journal history per
docs/migration-control-center.md. Inventory tools remain available for schema
diagnostics; the collector refreshes core schemas and checks registry visibility
after metadata failures. A hidden/missing registry row is not proof of global
model absence. Preserve explicit partial results and review mappings.

Update README when setup/usage changes, this file when operational rules change,
and docs/PROJECT_STATUS.md after every meaningful implementation step. Record
unresolved decisions rather than inventing answers. Keep verified, failed,
partial, unsupported, planned and untested outcomes separate. Commit logical
changes when permitted; never claim unexecuted checks passed.

Do not push codex/inventory-review-local: it retains uploaded inventory and
detailed environment evidence that has not been authorized for publication.

## Synthetic contact pilot rules

See docs/contact-pilot.md and docs/migration-tracking.md. Commands require
--lab-only; target writes additionally require sync --apply. Source seed and
change-source explicitly write only the marked synthetic fixture. The pilot is
restricted to loopback ports 8012/8020 and documented laboratory database names.
Fields: name/email/phone; ref is the stable marker. Do not expand this scope by
editing only the manifest; code verifies the manifest matches its allowlist.

Use a separate PostgreSQL journal, never an Odoo database. Journal credentials
must be supplied through JOURNAL_DB_PASSWORD; do not add defaults. Start only
lab/journal.compose.yaml for the journal, preserving existing Odoo services.
Never remove its volume or erase failed/incomplete runs. All workers must share
one authoritative journal for locking/idempotence. Mark success only after
read-back reconciliation. Block source/target identity conflicts and target
restore/missing-mapping situations for review; do not auto-delete/recreate them.

Standard tests: python -m unittest discover -s tests -v (98 tests at this update).
Optional integration: python scripts/run_pilot_integration.py (16 tests), after
installing requirements-pilot.txt. It owns an isolated disposable PostgreSQL
container with tmpfs/no named volume and synthetic HTTP servers; cleanup only
removes that exact test container. User-local pilot create/rerun/update evidence
has been supplied; local tracking UI installation remains pending.

Journal readiness must use TCP (-h 127.0.0.1), not just the initialization
Unix socket. journal-check is read-only and does not require Odoo variables.
Keep connection diagnostics allowlisted and secret-free. Retry only transient
initial journal connections, at most three times, never authentication failures
or Odoo writes. Preserve existing volumes/passwords when diagnosing failures.

Before pilot creates, validate required extra fields through the same server's
default_get, using the same user/context. Never copy or invent extra values.
Keep create payload restricted to the manifest fields plus ref. False/zero are
valid defaults for their respective types; unknown/missing defaults stay blocked
with field names only. Perform this check before create intent. Read/update paths
must not require unrelated create defaults. Actual read-back reconciliation is
still mandatory; metadata/default availability alone never proves success.

## Tracking UI rules

The Odoo 20 addon is a journal mirror, never the authority. Odoo 20 uses ir.access
with operation r for viewer permissions; do not substitute legacy ACL CSV files.
Viewer can read tracking; only the trusted Journal Importer role can call the
validated importer. Even importer users cannot directly create/write/delete
mirror records or forge the internal import capability through RPC context.
No raw business values/credentials are accepted in monitoring event details.

The host monitor reads a repeatable-read READ ONLY PostgreSQL transaction. It
stages bounded pages, preserves old complete views during partial imports,
checks counts/mapping/reconciliation evidence and atomically promotes completion.
All UI counts derive from journal data. Track records by namespace independently
of run attempts; newest failed/incomplete outcomes must not be hidden by an older
successful mapping. Incomplete is not evidence a worker is currently running.
Source/mapping checks prevent opening a missing/reused target ID. Respect normal
contact permissions; no sudo is used for target navigation.

Contact sync starts from pilot CLI; tracking import starts from monitor CLI.
Reload view only reloads imported metadata. UI-triggered migration/approval/retry
requires a separate authorized background-worker request design; never invoke
arbitrary commands from web requests. Do not put journal passwords in Odoo.

Native addon/browser validation: python scripts/run_control_integration.py,
after requirements-control-test.txt, Docker and Chromium. It owns disposable
Odoo/PostgreSQL containers/network/tmpfs only and never touches existing lab
services/volumes. Current results: 46 native Odoo upgrade tests plus browser smoke passed.
Keep redacted test logs/screenshots under ignored reports/, not in Git.

## Contact-history trial rules

User authorized a small contact/chatter/attachment trial; this does not authorize
the full custom MDM application. Separate migration_lab/contact_history.py from
the original synthetic-only worker. Accept 1–5 explicit top-level contact IDs,
preview and reviewed source digest before --apply. Keep source read-only. Fields
are name/email/phone/active/Tax ID, country by ISO code and checked is_company;
document omitted mappings. Never force readonly company classification or invent
VAT values; default native mode blocks classification disagreement. An explicit
--preserve-legacy-classification plan can retain source type through guarded
provenance and a compute extension on imported contacts only. Bind that policy
to the reviewed digest; never opt in automatically. Exclude
user-account contacts/children; block unsupported or inaccessible history.

The addon execution API requires Contact Trial Migrator and odoo20_migration,
separate from monitor permissions. No arbitrary web commands. Keep actual contact,
mail.message and ir.attachment access under caller ACLs. Only protected identity
receipts use sudo. Never message_post, notify, subscribe or send historical mail.
Preserve original dates/author labels; transform field changes to readable text,
not foreign native field IDs. Do not claim rich HTML/native tracking fidelity.

One atomic Odoo transaction per contact with target receipts; separate committed
read-back before independent journal success. Keep durable per-message/file
IDs/digests, lost-ack idempotence and restore/conflict guards. No automatic merge,
history edits/deletes, target overwrite after drift, or volume resets. Journal
mirror receives safe counts only; raw business histories never enter Git or
monitor metadata. See docs/contact-history-trial.md for limits and acceptance.
Recognize only allowlisted UserError codes across bare/native and traceback RPC
formats. Unknown fault text stays private. Diagnostic improvements must not
silently bypass classification or other migration guards.
Preserve native-mode receipt fingerprints and namespace identities when adding
optional classification policies. Do not reset imported provenance through
normal ORM/RPC writes; allow the ordinary native default during delegated user
creation. Upgrade the added partner column before restarting a source-based
application; preserve the working container's credentials and all volumes.
Ignore context/ir.default attempts to inject imported provenance on ordinary
creates; default-mode previews must likewise use the explicit native policy.
Top-level targets moved under another parent require review, not automatic
unlinking or shared-parent updates. The integration runner also needs public
commit 935c53e in local Git history for its previous-addon upgrade fixture.

## Local module deployment helper

scripts/update_odoo_module.py pulls development fast-forward only and upgrades
explicit installed module names in the existing selected Docker lab container.
Use its existing PGPASSWORD without inspecting/printing environment values. Never
upgrade all, discard local changes, recreate containers/volumes, or restart after
an unsuccessful upgrade. It requires the selected app running and PostgreSQL
healthy. --skip-pull supports local edits; --dry-run performs no readiness checks
or changes. This helper does not pull nested core Git clones or perform migration.
Odoo 12 has no custom repository-addon mount in the current Compose setup; do not
claim that the Odoo 20 tracking addon can be installed there. See
docs/docker-module-update.md. Helper control-flow/preflight tests are isolated;
actual execution on the user's laptop remains separate acceptance.
