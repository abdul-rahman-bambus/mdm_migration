# Bambus Odoo migration framework

Generic migration preparation for a future MDM project. The specified lab is
Odoo 12 Community → Odoo 20 Community; the final production target is unconfirmed.
This repository provides connectivity/inventory/schema tooling and a **limited
synthetic-contact migration pilot** with an independent PostgreSQL journal.
The broader migration engine remains in development. Use `development`.
The existing Odoo lab is on the user's local
machine and is not connected to this cloud environment.

## Run the current tooling

Requirements: Python 3.12 (tested with 3.12.14). Assessment/schema tools and unit
tests use the standard library. The optional contact pilot needs the pinned
packages in requirements-pilot.txt and a separate PostgreSQL journal. From the repository root:

```sh
python3 -m unittest discover -s tests -v
python3 -m migration_lab --help
python3 -m migration_lab
```

The final command validates exported configuration only. It returns exit status
1 when live connectivity has not been established, even if variables are set.
The test suite starts loopback-only HTTP servers and does not contact Odoo.

Configure the eight variables listed in `.env.example` through secure environment
settings or your local process environment. The CLI does not load `.env` files.
Do not commit passwords or use production accounts. Remote URLs require HTTPS;
HTTP is allowed only for loopback lab addresses. Do not embed credentials in URLs.

After connectivity is provided, the available live command is:

```sh
python3 -m migration_lab --live --timeout 10
```

It checks each server's reported major version, authentication, field metadata,
and one ID-only sample from product templates, variants and partners. It does
not write data. Reports go to stdout; no record contents, passwords or raw remote
faults are emitted. Exit 0 means the implemented connectivity checks passed;
it does not establish migration readiness. Empty sample sets are reported.
This command has passed against synthetic fixtures, **not real Odoo servers**.
A separate inline probe run by the user succeeded against the local Odoo
servers. See [local connectivity evidence](docs/local-connectivity-evidence.md).
The cloud workspace still has no direct connection to those services.

The standalone `scripts/export_local_schema.py` exports metadata from the three
core models using those same variables and loopback endpoints. Run it locally
with `python3 scripts/export_local_schema.py` once that file is available there.
It writes a new timestamped `odoo-schema-*.json` file without overwriting existing
files. Inspect any `error_type` entries before treating an export as complete.
A core schema export from the local lab is now committed. The installed-module and dependent-model inventory is still pending.

## Current lab and planned architecture

The supplied local path is `~/odoo/workspace/mdm_migration/lab/odoo_migration_lab`.
Its Compose files, Dockerfiles and installer are now tracked here. Compose
validation and installer shell syntax checks passed; full cloud builds and
startup have not been run. Do not reset its databases or
remove its volumes. Localhost in this cloud workspace refers to the cloud
machine, not the user's computer.

The planned engine will use observed version-specific APIs and explicit mappings,
with a separate PostgreSQL migration journal that survives target restores.
An Odoo control addon will synchronize journal data for review and authorized
background retry requests. See [architecture](docs/architecture.md).

## Development status

Product/partner/image/attachment migration, chatter preservation, approved schema mapping,
general ID tracking, multi-model reconciliation, approval workflows, exports
and the dashboard remain planned. The pilot implements single synthetic-contact
ID mapping, history and reconciliation; real Odoo acceptance is still pending.
No real migration or migration performance results exist.

Connection failures are categorized as configuration, network, timeout, HTTP,
RPC, response or version problems. Raw fault details are deliberately omitted.
Do not retry failed permanent mappings automatically when that feature is built.

Read [environment assessment](docs/environment-assessment.md),
[connectivity](docs/connectivity.md), [test results](docs/test-results.md),
[future MDM readiness](docs/future-mdm-readiness.md), and
[current status](docs/PROJECT_STATUS.md) before continuing. Documentation for each
migration area will be added with its implementation and verified procedures.

## Compare schemas and collect local inventory

The supplied snapshot covers 245 source fields and 319 target fields. Tested
comparison command (use a new output directory for each run):

```sh
python3 -m migration_lab.schema odoo-schema-20261103-122514-132435.json --output-dir reports/schema-review-1
```

Outputs: comparison.json, comparison.md, fields.csv and mapping-draft.json.
The [initial report](docs/schema-reports/odoo12-20-initial/comparison.md) is checked
in. Matching field names/types are candidates only; all mappings are unapproved.

Next, run locally with both applications running and the same eight exported
connection variables:

```sh
python3 -m migration_lab.inventory --output-dir reports/local-inventory-2
```

Share `reports/local-inventory-2/inventory.json`. This only reads installed module
names and metadata for three core models plus 15 dependent models. It checks
registry visibility after metadata failures and includes a UTC capture timestamp. Exit 1 can mean partial evidence;
errors remain explicit and the report is still useful. Pagination is bounded.
Updated core-refresh and registry-diagnostic behavior has automated mock coverage;
live behavior still needs validation. When core reads succeed, schema.json is
exported from the same collection run, even if a dependency check is partial.

Original Odoo Compose/installer startup now requires exported LAB_PG12_PASSWORD and
LAB_PG20_PASSWORD matching the existing lab databases; see the lab README.
The inventory command only needs the eight ODOO variables and does not require
restarting existing containers.

## Run the first synthetic contact migration

Follow [the local pilot runbook](docs/contact-pilot.md). It includes exact
installation, journal startup, seed, dry-run, apply, rerun and update commands.
Only name/email/phone are mapped, with ref reserved for a technical marker.
`sync` defaults to dry-run; `--apply` explicitly enables the target write.
It refuses arbitrary business contacts and remote/production endpoints.

The journal uses its own Compose project and persistent volume, preserving
history independently of the target database. Restore conflicts fail closed.
The full CLI lifecycle passed against real PostgreSQL and synthetic XML-RPC
servers; it has not yet been validated against the user's real Odoo instances.

For journal startup failures, run `python -m migration_lab.pilot journal-check
--lab-only` on one line. It checks connectivity without initialization or Odoo
calls and returns secret-free error categories. See the troubleshooting section
of docs/contact-pilot.md; retain the original journal password and volume.

The pilot honors usable Odoo-owned defaults for extra required partner fields
without adding them to the migration payload. Dry-run lists their names only;
unresolved fields still block with safe diagnostics. Reads/updates do not run
unrelated create checks. See the required-fields section in docs/contact-pilot.md.
