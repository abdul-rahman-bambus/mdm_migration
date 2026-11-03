# Project status

Latest update: 2026-11-03 (Asia/Kolkata).
Active branch: `development`. Clean framework base for this increment:
`6db69b3`. Uploaded lab/schema source: remote main commit `8aa2ec5`.
Use `git log -1 --format=%H` for the latest implementation commit.

## Completed and verified

- Fetched the user's lab upload and core schema snapshot. The upload was on
  main (`8aa2ec5`), so its files were imported into development alongside the
  framework after sanitization; main itself was not modified. Earlier unpublished
  branch history is retained locally under codex/development-before-cleanup.
- Inspected Compose, Dockerfiles, installer, lab README and exported metadata.
- Offline comparison accounts for 245 source fields and 319 target fields
  across three models (390 union entries). Reports are checked in under
  docs/schema-reports/odoo12-20-initial, including input checksum provenance.
- Versioned, unapproved mapping draft accounts for every source field and
  target-only field. No mapping is approved and no business record was written.
- Read-only installed-module/dependency inventory command implemented and
  tested with mocks, including pagination, repeated pages and partial failures.
- 41 automated tests passed, 0 failures/errors/skips (4.675s).
- Compose configuration validation (with non-secret validation placeholders)
  and installer bash syntax validation passed.
- Replaced uploaded Compose/installer password literals with required exported
  LAB_PG12_PASSWORD and LAB_PG20_PASSWORD. Existing containers/databases were not
  changed; existing volumes require their current passwords. Automatic approval
  review rejected earlier push attempts because literals remained in ancestry.
  This development history was rebuilt from the clean framework base, importing
  the sanitized final files. Original uploaded history on remote main is unchanged.

## Partial / awaiting local evidence

The user-local screenshots establish authentication, server-reported versions
12.0/20.0, field metadata access and sample reads on core models. The supplied
schema snapshot establishes actual field definitions but not defaults, computed
status or API writeability. The cloud task still cannot reach the local lab.

User-supplied local inventory was received and reviewed. Detailed evidence is
retained outside the checkout and is not published. Updated core-refresh and
registry-diagnostic behavior still needs live validation. Failed metadata reads
remain partial; registry visibility is a diagnostic, not proof of global absence.
No cloud Odoo build, startup, database initialization or migration was attempted.
The expected source clones are absent here; installer clone steps and legacy
build dependencies have not been verified in this cloud environment.

## Mapping blockers found

Text-to-HTML changes, image-family changes, source-only purchase UoM, partner
mobile/customer/supplier fields, readonly partner is_company, absent company_type,
removed private address selection, new required product fields, and variant
relationships require decisions. Do not assume missing customer/supplier fields
map to ranks: those rank fields are absent in this target snapshot too.
See docs/field-mapping.md for migration impacts.

## Not started

Approved transformations, independent PostgreSQL journal, persistent ID mappings,
business record migration, binary migration/validation, chatter feasibility,
reconciliation, correction/retry workflow, control addon, recovery simulations
and migration performance measurement.

Latest successful migration run: none. Latest reconciliation: none.
Environment limitations are distinct from the tested offline capabilities above.

## Next task

On the local machine, pull development and run:

```sh
python3 -m migration_lab.inventory --output-dir reports/local-inventory-2
```

Use the existing securely exported ODOO12/ODOO20 variables. Share inventory.json
from that directory even if exit status is 1; partial errors need diagnosis.
Do not restart services, rerun the installer or reset any database for this check.
Use a new output directory for each subsequent inventory run.

## Remote synchronization

The user subsequently merged the original lab history into remote development
at 6d59aab. That update was merged locally at 4f9eab8, retaining the sanitized
Compose/installer files. Verified that every newly introduced Compose-bearing
commit uses environment references, then successfully pushed development.
The earlier password-literal upload already exists on the user's remote branches;
no new password-literal commits were added by this push. Main was unchanged.
The tested implementation files were preserved during branch synchronization.

## Latest tooling increment

The collector now includes core schemas alongside dependency metadata, a UTC
capture time, and registry-visibility diagnostics after failed reads. It exports
schema.json only when all core metadata succeeds. The comparator accepts only
integer 0/1 as boolean metadata, records that normalization, and explicitly flags
polymorphic references for ID mapping. No mapping is automatically approved.

All 41 automated tests pass. The newly updated live diagnostics have not yet
run against real servers. Automatic approval review rejected publication of the
uploaded inventory and detailed environment reports. Those files were retained
outside the checkout and omitted from development history; this increment
publishes code/tests and general usage documentation only. The private local
review commit is preserved under codex/inventory-review-local and must not be
pushed without authorization. No migration writes or reconciliation occurred.
