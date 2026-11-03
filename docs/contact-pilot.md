# Run the synthetic contact migration pilot locally

This pilot creates one clearly marked synthetic contact on Odoo 12, then copies
name, email and phone into Odoo 20 when explicitly applied. It does not migrate
existing business contacts, roles, companies, addresses, images or attachments.
`ref` is a technical migration marker. The mapping manifest is
`mappings/synthetic-contact-v1.json`; scope changes require code review.

The worker is restricted to loopback Odoo ports 8012/8020 and databases
odoo12_demo/odoo20_migration. It authenticates and inspects the actual four
required char fields before writing. Extra mandatory writable fields block the
pilot rather than being filled with invented defaults. Every pilot command
requires `--lab-only`.

## 1. Pull and install

From the local repository root:

```bash
git switch development
git pull --ff-only origin development
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-pilot.txt
```

Use the same exported ODOO12_URL/DB/USERNAME/PASSWORD and ODOO20 equivalents as
the successful local connectivity check. Neither `.env` nor `.env.example` is
automatically loaded. Activating the virtual environment preserves exports.

## 2. Start the separate journal

Keep both existing Odoo applications running. Choose a journal-only password
and retain it securely; do not put it in Git or chat:

```bash
read -r -s -p "Journal-only password: " JOURNAL_DB_PASSWORD
echo
export JOURNAL_DB_PASSWORD
docker compose -f lab/journal.compose.yaml up -d --wait
python -m migration_lab.pilot journal-check --lab-only
python -m migration_lab.pilot init-journal --lab-only
```

The journal uses its own Compose project and named volume. PostgreSQL is bound
to 127.0.0.1:55432, with database bambus_migration_journal and role bambus_journal.
It does not initialize or modify either Odoo database. Init is repeatable and
preserves history. Existing journal volumes require their original password;
changing an environment variable does not rotate the stored database password.
If port 55432 is occupied, export a different JOURNAL_DB_PORT before both Compose
startup and worker commands. Keep the same journal for all retries/reruns.

## 3. Seed the source and review the dry run

```bash
python -m migration_lab.pilot seed --lab-only --label smoke-001
python -m migration_lab.pilot sync --lab-only --label smoke-001
```

Seed creates `Bambus migration pilot smoke-001` on the source, with an
example.invalid email and a reserved fictional phone number. Repeating seed
reuses that contact. The second command is a dry run: expected state dry_run,
proposed_operation create and fields name/email/phone. It writes audit entries
to the independent journal but does not write to the target.

Stop if either command reports blocked/failed or the proposal is unexpected.
No migration should proceed through a failed prerequisite.

## 4. Apply and verify duplicate prevention

```bash
python -m migration_lab.pilot sync --lab-only --label smoke-001 --apply
python -m migration_lab.pilot sync --lab-only --label smoke-001 --apply
python -m migration_lab.pilot status --lab-only --label smoke-001
```

Expected first result: state reconciled, operation create, and source/target IDs.
Expected repeat: state reconciled, operation no_change, same target ID. The IDs
need not match between databases. In Odoo 20 Contacts, search the synthetic name
and inspect its email/phone. The worker also re-reads and compares all three
fields before committing successful mapping/history; an API create response
alone is insufficient. GUI record visibility depends on the logged-in user's
permissions and filters; backend reconciliation uses the migration account.

## 5. Verify a controlled update

```bash
python -m migration_lab.pilot change-source --lab-only --label smoke-001 --phone +12025550123
python -m migration_lab.pilot sync --lab-only --label smoke-001
python -m migration_lab.pilot sync --lab-only --label smoke-001 --apply
```

Expected dry-run proposal: update, fields phone. Apply should reconcile against
the same target ID. Only reserved +12025550100 through +12025550199 phone values
are accepted. Source name/email and both marker identities are deliberately
fixed to the synthetic fixture; arbitrary records are refused.

## Failure and interruption handling

Read status before retrying the same apply command with the same label. There
are no automatic Odoo network/write retries. Initial journal connections retry
only transient startup/timeouts, at most three times; authentication failures
are not retried. Durable intent events precede writes. A
successful create whose response is lost is recovered by its stable marker,
then reconciled, rather than recreated blindly. Duplicate markers are blocked.
If a previous create intent exists but no marker is visible, the worker stops
for review instead of recreating blindly. Possible causes include a rejected
write, hidden records or restore; there is no CLI bypass. Use the same migration
accounts and journal for all attempts.

The shared journal's PostgreSQL advisory lock prevents two pilot workers from
processing the same mapping concurrently. All workers must use that journal.

A crashed/interrupted run may remain running in history because it has no final
event; that state is not proof a process is alive. A later successful retry adds
a new reconciled run and preserves the incomplete/failed attempt. Status reports
the latest run separately from the last reconciled mapping. A prior mapping is
historical evidence, not proof that the latest attempt succeeded.

After target restore/deletion or ID reuse, a missing/conflicting mapped target
is blocked for review. Automatic restore recovery is not implemented; do not
delete mappings or business records to force the test through. Source identity
changes also block. No cleanup/delete/deactivation commands are supplied.

Write context requests disabled chatter tracking, automatic subscription/logging
and immediate mail sending. Those flags were checked against synthetic servers;
actual Odoo/custom-module notification behavior is not yet verified. This pilot
does not migrate historical chatter or send intentional email.

## Verified capabilities and limits

Unit tests use in-memory APIs/journal. Integration tests use a real independent
PostgreSQL 16 instance and synthetic Odoo XML-RPC HTTP servers, including the CLI
lifecycle, interruption/restart, lost acknowledgements, actual journal locking,
reconciliation failure and persistence across connections. No real Odoo data
migration has run in this cloud workspace; the commands above are the first
local acceptance procedure and may expose version-specific behavior to diagnose.

Run standard tests with `python -m unittest discover -s tests -v`. To run the
separate integration suite: `python scripts/run_pilot_integration.py`. It needs
Docker and the pilot requirements; it creates/removes only its own disposable
container using tmpfs and no named volume. It never uses the user's journal or
Odoo databases. No journal passwords or synthetic field values are printed by
the worker; status exposes IDs, states, timestamps, markers and payload hashes.

The journal is a single-record pilot foundation, not the full multi-model audit,
approval/retry workflow or dashboard. Connection/preflight failures can occur
before a migration run starts and return safe CLI codes. Protected traceback
storage, production-scale performance, automated cutover/restore recovery and
backup procedures still require separate implementation and verification.

## Diagnose journal connection problems

A healthy PostgreSQL container is a readiness signal, not proof that the Python
client has the right password/port. The healthcheck now checks TCP, avoiding
success from the temporary Unix-socket-only server used during initialization.
It does not validate credentials. The read-only worker check uses the same
connection configuration as initialization and performs no schema/data writes:

```bash
python -m migration_lab.pilot journal-check --lab-only
```

Expected result: journal_connected. On failure the command reports a static
category and safe host/port/attempt/exception-type/SQLSTATE metadata, never raw
libpq messages, passwords or connection strings. Share that output for diagnosis.
The connection code closes failed connections and bounds transient retries.

- journal_authentication_failed: use the original password stored when this
  journal volume was initialized. Re-exporting a newly chosen password does not
  change that stored password. Do not remove/reinitialize the volume to fix it.
- journal_not_ready or journal_connection_timeout: check journal service status
  and the actual published TCP port. Compose's updated healthcheck applies on
  the next normal up/recreation; the existing persistent volume is preserved.
- invalid_JOURNAL_DB_PORT: export the numeric published port for both worker
  and Compose. Compose can read its .env while Python only reads exported vars.
- journal_database_missing/access_denied/TLS errors: diagnose the selected
  service/permissions/trust configuration; do not bypass verification or recreate
  databases merely to make the check pass.

Read-only service/port checks (they print no passwords):

```bash
docker compose -f lab/journal.compose.yaml ps
docker compose -f lab/journal.compose.yaml port journal 5432
```

Keep the existing exported journal password while checking. No Odoo connection
settings are required for journal-check or init-journal. Proceed to seed/sync
only after journal initialization succeeds.
