# Project status

Latest update: 2026-11-03 (Asia/Kolkata). Branch: development.
Base before this pilot increment: c02bac2. Use git log -1 --format=%H for HEAD.
Main is unchanged. Private inventory/review branches must not be pushed.

## Implemented and verified

- Existing read-only connectivity, module/schema inventory and offline schema
  comparison remain available. Detailed user-uploaded inventory remains private.
- Synthetic-only contact pilot: seed on Odoo 12, dry-run, explicitly applied
  target create/update, name/email/phone read-back reconciliation, status.
- Explicit versioned mapping manifest, endpoint/database guards, synthetic record
  guards, marker-based duplicate prevention and safe create acknowledgement retry.
- Independent PostgreSQL 16 journal: persistent run/event/mapping history,
  environment/model/record identities, payload fingerprints, mapping version,
  transactionally committed reconciliation and PostgreSQL worker locking.
- Target restore/ID conflicts fail closed; automatic restore recovery is not built.
- 72 standard tests passed (4.695s), 0 failures/errors/skips.
- 15 integration tests passed (13.558s), 0 failures/errors/skips, using real
  PostgreSQL and synthetic version-12/version-20 XML-RPC HTTP servers.
- CLI seed/dry-run/apply/rerun/update/status lifecycle passed against those fixtures.
- Actual PostgreSQL tests exercised locking, lost source/target acknowledgements,
  interruption/new-worker continuation, failed reconciliation, independent mapping
  retention after simulated target loss, and repeatable non-destructive init.
- Pinned pilot dependencies installed successfully; pip check passed.
- Independent journal Compose configuration validation passed with a non-secret
  validation placeholder. No user journal or Odoo volume/container was changed.

## Not verified on real Odoo

No cloud-to-local access exists. The user previously supplied successful live
read-only results, but no actual Odoo write/reconciliation pilot has yet run.
Synthetic HTTP fixture compatibility does not establish real Odoo behavior.
Mail suppression flags were verified in fixture requests, not custom Odoo hooks.
Journal Compose syntax is verified; actual PostgreSQL integration used a separate
owned test container, not the user's persistent journal service.

## Scope limits / not started

Arbitrary contacts, partner roles/classification/address relationships, products,
UoM transformations, variants, binary data, chatter, generic mapping execution,
full approval/fix/retry workflow, dashboard, bulk batches, performance measurement,
cutover and automatic restore recovery remain outside the implemented pilot.
The journal is a single-record foundation, not the completed tracking system.

## Current environment and evidence

Python 3.12.14; psycopg/psycopg-binary 3.2.3 and typing-extensions 4.16.0 in ignored
.venv. PostgreSQL 16 image pinned by tested digest. Integration test containers
were removed by their owner; no named test volume was created. Test data was
synthetic. No private uploaded metadata is included in this increment.

Latest successful real Odoo migration: none. Latest real Odoo reconciliation:
none. Tested fixture runs reconciled successfully; they are not production or
client readiness evidence. No measured migration throughput exists.

## Next local acceptance task

Follow docs/contact-pilot.md: pull development, install optional requirements,
export a journal-only password, start the independent journal and initialize it.
Keep existing Odoo services running with the same eight ODOO variables exported.
Seed label smoke-001, review dry-run, explicitly apply, repeat to verify same target
ID, then change the source's reserved synthetic phone and apply the update.
Share safe command output/status. Stop on blocked prerequisites; do not reset
volumes, delete mappings or bypass reconciliation to make a check pass.

## Journal startup diagnostic correction

Earlier local acceptance was blocked at journal connection, before any Odoo
pilot write. Journal initialization has since succeeded locally. The specific cause is still unconfirmed; the earlier generic code
hid it. Replaced Unix-socket readiness with TCP readiness and added journal-check
with allowlisted categories/diagnostics. Startup-only connection retries are
bounded at three and exclude authentication/configuration failures. Failed
connections close cleanly. No existing journal password/volume was changed.

Latest validation: 72 standard tests passed (4.695s) and 15 integration tests
passed (13.558s). Actual wrong-password classification and a history-preserving,
Odoo-independent journal-check were exercised against owned PostgreSQL. A
socket-only PostgreSQL probe separately reproduced the old readiness false
positive. New diagnostics still need execution on the user's computer.

## Required native-default correction

Local pilot seed/sync was blocked by the extra-required-field guard before
creating a contact. The guard incorrectly rejected native defaults during
connection setup. Create validation now queries default_get only when needed,
checks supported default types (including false/zero), leaves defaults to the
same server's ORM, and reports unresolved field names without values. It does
not copy extra fields or expand the mapping. Dry-run reports default field names.

Validated 72 unit/protocol tests (4.695s) and 15 real-PostgreSQL/synthetic-Odoo
integration tests (13.558s). New integration cases cover distinct source/target
defaults, unchanged payload scope, missing-default rejection before create intent,
correction without clearing history, and existing reads/updates without create
preconditions. Actual local Odoo create/reconciliation still awaits rerun.
No schema change, volume reset, password change or new package is required.
