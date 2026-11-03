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
- 57 standard tests passed (3.172s), 0 failures/errors/skips.
- 10 integration tests passed (9.263s), 0 failures/errors/skips, using real
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
