# Test results — 2026-11-03

Command from `/workspace/mdm_migration`:

```sh
python3 -m unittest discover -s tests -v
```

Latest run: **57 tests, 57 passed, 0 failures/errors, 0 skipped**, 3.172 seconds.
Additional pilot integration suite: **10 tests, 10 passed**, 0 failures/errors/skips,
9.263 seconds, using real PostgreSQL and synthetic Odoo HTTP servers.
The command ran with loopback socket access outside the command sandbox.

Coverage exercised: environment validation and secret redaction; complete
read-only XML-RPC request sequence; unexpected version blocking; invalid
authentication blocking; sanitized RPC faults; explicit empty samples; refusal
of redirects; malformed responses; response-size bounds; timeout without retry;
write refusal; configuration-only CLI status; end-to-end CLI requests to separate
synthetic version-12 and version-20 servers; unavailable service detection.
Three additional mocked-RPC tests cover core schema export, refusal to read
metadata after failed authentication, and sanitized errors while continuing
independent model requests. They do not validate real metadata compatibility.

These are synthetic protocol fixtures. No real Odoo version, schema, database,
write permission, image, attachment, chatter or migrated record was tested.

`python3 -m migration_lab --help` passed. `python3 -m migration_lab` returned
the expected exit 1 and named the missing variables for both instances without
printing credentials. This is an expected blocked check, not a live success.

Actual environment requests to both expected local Odoo ports were refused.
Docker reported zero local containers. See environment-assessment.md.

Subsequent user-local inline probe: both real servers authenticated and returned
metadata/sample reads. See local-connectivity-evidence.md. This does not change
the automated test count and does not validate the downloadable checker on real
servers. The screenshots establish local, not cloud, connectivity.

## Latest schema and inventory validation

The added comparator tests exercise full field accounting, structural changes,
selection order/labels/removed keys, unknown writeability, protected fields,
invalid snapshots, input immutability, output preservation, unapproved drafts,
and regressions against the supplied real 245/319-field snapshot. Inventory
mock tests exercise pagination, dependent-model failures, repeated pages,
page limits and authentication gating. No real local inventory has run yet.

`LAB_PG12_PASSWORD=validation-placeholder LAB_PG20_PASSWORD=validation-placeholder docker compose -f lab/odoo_migration_lab/compose.yaml config --quiet` passed.
The placeholders were only for syntax validation, not authentication.
`bash -n lab/odoo_migration_lab/install.sh` passed. These establish configuration
and shell syntax only; they do not validate source cloning, legacy builds,
startup, initialization or migration behavior.

## Updated metadata and inventory behavior

New tests cover strict integer-0/1 boolean normalization without input mutation,
rejection of other integer values, polymorphic-reference mapping requirements,
registry visibility/access failure diagnostics, export of complete core metadata
alongside partial dependency results, and refusal to export incomplete core
schemas. Updated live probes have not been run against actual servers here.
User-uploaded detailed environment reports are retained locally, not published.

## Synthetic contact pilot

Added unit coverage: dry-run zero target writes, explicit apply and idempotent
reruns, controlled update, lost response recovery, interrupted-run continuation,
failed read-back preventing reconciliation, synthetic guard, missing/reused
mapped target IDs, journal-intent failure before target write, repeatable seed,
lab endpoint/database restrictions, mapping manifest tampering and phone guards.

Integration command: `.venv/bin/python scripts/run_pilot_integration.py`.
Ten tests used a real independent PostgreSQL container and two synthetic Odoo
XML-RPC HTTP servers. They exercised CLI lifecycle, actual locking and durable
history, lost source/target create acknowledgements, process interruption/new
connection retry, read-back mismatch rollback of success/mapping, target loss
while retaining the journal, and repeatable initialization. HTTP fixtures used
ephemeral loopback ports; CLI endpoint identity was patched only in that test,
while normal runtime endpoint restrictions are separately unit tested.

The owned PostgreSQL test container used tmpfs and no named volume and was
removed after each test suite. No actual Odoo database, container or persistent
journal was used. Actual Odoo create/write/notification compatibility remains
unverified. No local client data or detailed environment inventory was published.

Pinned requirements installation and `.venv/bin/python -m pip check` passed.
Journal Compose config validation with a non-secret placeholder passed; actual
Compose persistent-service startup on the user's computer remains untested.

Final safety coverage also verifies durable create intent without a visible
marker blocks a duplicate attempt, including hidden-source/target simulations
and a real PostgreSQL test of a rejected remote create.
