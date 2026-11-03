# Bambus Odoo migration framework

Generic migration preparation for a future MDM project. The specified lab is
Odoo 12 Community → Odoo 20 Community; the final production target is unconfirmed.
This repository currently provides **read-only connectivity assessment**, not a
working data migration engine. The existing Odoo lab is on the user's local
machine and is not connected to this cloud environment.

## Run the current tooling

Requirements: Python 3.12 (tested with 3.12.14). No third-party packages or
installation are required for the current module. From the repository root:

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

## Current lab and planned architecture

The supplied local path is `~/odoo/workspace/mdm_migration/lab/odoo_migration_lab`.
Its Compose configuration is absent here; there are no verified startup or
database initialization commands to publish yet. Do not reset its databases or
remove its volumes. Localhost in this cloud workspace refers to the cloud
machine, not the user's computer.

The planned engine will use observed version-specific APIs and explicit mappings,
with a separate PostgreSQL migration journal that survives target restores.
An Odoo control addon will synchronize journal data for review and authorized
background retry requests. See [architecture](docs/architecture.md).

## Development status

Product/partner/image/attachment migration, chatter preservation, schema mapping,
ID tracking, journal, reconciliation, fixes/retries, exports and the dashboard
are planned. There are no migration, database initialization, addon installation
or retry commands yet. No real migration or performance results exist.

Connection failures are categorized as configuration, network, timeout, HTTP,
RPC, response or version problems. Raw fault details are deliberately omitted.
Do not retry failed permanent mappings automatically when that feature is built.

Read [environment assessment](docs/environment-assessment.md),
[connectivity](docs/connectivity.md), [test results](docs/test-results.md),
[future MDM readiness](docs/future-mdm-readiness.md), and
[current status](docs/PROJECT_STATUS.md) before continuing. Documentation for each
migration area will be added with its implementation and verified procedures.
