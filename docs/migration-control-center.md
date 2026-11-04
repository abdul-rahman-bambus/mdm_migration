# Bambus Migration Control — local installation and operation

For an existing installation upgrading to 20.0.3.0.0, first follow the schema
upgrade steps in [the contact-history runbook](contact-history-trial.md). Upgrade
the stored partner field before restarting the application; retain all volumes
and the working container's database credentials.

This Odoo 20 Community addon displays journal-backed tracking. Its overview,
records, execution attempts, timelines, issues and last reconciled mappings are
read-only. PostgreSQL remains authoritative outside Odoo. The app does not store
journal passwords or either Odoo application's login credentials.

## Where synchronization starts

There are two distinct operations, both initiated from the local repository's
terminal in this release:

1. **Contact migration:** the existing pilot worker reads Odoo 12 and explicitly
   applies/reconciles the synthetic contact in Odoo 20.
2. **Tracking import:** the new monitor reads the independent journal and writes
   only the addon's tracking models in Odoo 20. It never migrates contacts.

The UI's **Reload view** fetches the latest imported tracking data. It neither
starts contact migration nor executes a shell command. UI-triggered migration
requests, approvals and background execution are not implemented in this release.

## 1. Pull the addon

From the local checkout, with the pilot virtual environment active:

```bash
git switch development
git pull --ff-only origin development
```

No new runtime package is needed beyond requirements-pilot.txt. The addon uses
Odoo's installed base/web dependencies; journal access stays in the host worker.

## 2. Make the addon visible to the existing Odoo 20 service

The tracked Compose file now mounts ../../addons read-only at /mnt/bambus-addons
and adds that directory alongside both existing source addon paths. Existing
source/filestore mounts, databases and ports are preserved. No image rebuild is
needed for this Python/XML addon.

Compose requires both existing laboratory PostgreSQL passwords while resolving
the file. If not already exported, enter the original values securely:

```bash
if [ -z "${LAB_PG12_PASSWORD:-}" ]; then
    read -r -s -p "Existing pg12 database password: " LAB_PG12_PASSWORD
    echo
    export LAB_PG12_PASSWORD
fi
if [ -z "${LAB_PG20_PASSWORD:-}" ]; then
    read -r -s -p "Existing pg20 database password: " LAB_PG20_PASSWORD
    echo
    export LAB_PG20_PASSWORD
fi
docker compose -f lab/odoo_migration_lab/compose.yaml up -d --no-deps --no-build odoo20
```

This recreates only the Odoo 20 application container to apply the new mount and
startup path. It does not restart PostgreSQL/Odoo 12, initialize databases, or
remove volumes. Use the existing database passwords; changing an export does
not change PostgreSQL's stored password.

## 3. Install through Odoo 20

In your local Odoo 20 UI, enable developer mode, open Apps and update the Apps
List. Search **Bambus Migration Control** and install it.

In Settings → Users, give the ODOO20_USERNAME account the **Migration Control /
Journal Importer** privilege under Migration Operations. For the lab this can
be your existing administrator account. Reload the UI afterward. Users who only
need to inspect tracking should receive **Viewer** instead. The app menu appears
only for these roles. In developer mode, the same groups can also be managed
through Settings → Users & Companies → Groups.

Importer is a trusted machine role: it can submit validated tracking data through
the dedicated importer methods. It grants no edit/delete interface for mirrors;
ordinary ORM writes are blocked even for importer accounts. Contact access is
still governed by the user's existing Odoo permissions. Do not grant Importer to
ordinary viewers. Import authentication is not a cryptographic proof of journal
provenance; the trusted worker and independent journal remain the authority.

## 4. Initialize the additive journal monitoring identity

Keep the original JOURNAL_DB_PASSWORD exported, and the existing ODOO20 variables.
The following adds the stable monitoring identity table if missing and preserves
all runs/events/mappings:

```bash
python -m migration_lab.pilot init-journal --lab-only
python -m migration_lab.monitor
```

Expected monitor result: imported with counts, or unchanged if the same revision
was already imported. The addon then appears under **Bambus Migration Control**.
All figures come from the journal; there are no seeded dashboard totals.

If the monitor returns initialize_journal_for_monitoring, rerun initialization
with the original journal credentials. install_or_upgrade_tracking_addon means
the target addon endpoint is unavailable; confirm installation/upgrade in Apps.
assign_migration_journal_importer_role identifies the required target account
privilege. Raw RPC messages and passwords are never printed by the monitor.

## 5. Keep tracking updated

In a dedicated terminal using the same virtual environment and exported journal/
Odoo 20 variables:

```bash
python -m migration_lab.monitor --watch --interval 10
```

This checks for changes every ten seconds and stops on an error instead of
looping on invalid credentials. It updates a monitor-check timestamp even when
history has not changed. The dashboard reports capture/import/check timestamps.
Use **Reload view** or browser reload to display newly imported history; the
page does not automatically poll. Ctrl+C stops only the monitor process.

In another terminal with the pilot connection variables, initiate a migration:

```bash
python -m migration_lab.pilot sync --lab-only --label smoke-001
```

Review the dry run. Then explicitly apply:

```bash
python -m migration_lab.pilot sync --lab-only --label smoke-001 --apply
```

The monitor imports that run afterward. It cannot initiate migration, automatic
retry or record deletion. The source Odoo 12 login is unnecessary for monitoring.

## How to interpret the UI

- **Tracked records:** one group per pilot namespace. Reruns of the same key do
  not increase the record count. Mapping-version changes create distinct keys;
  cross-version/global entity deduplication is not claimed.
- **Latest reconciled / need attention / awaiting sync:** derived from each key's
  latest run, including source updates and previews. These differ from the number
  of historical successful mappings or failed attempts.
- **Incomplete:** a run has no final result. This is not proof a process is alive.
- **Mappings:** evidence from the last successful reconciliation. A newer failed
  attempt does not erase that evidence or become successful because it exists.
- **Issues:** failed or incomplete attempts from the journal. They are not
  diagnosed root causes, approved fixes or completed resolution workflows.
- **Open target contact:** verifies the stored marker before opening the local
  contact and respects native user permissions. Missing/reused/conflicting IDs
  are blocked for review, preserving restore safety.

Timestamps are stored as UTC and displayed by Odoo using user/browser timezone
settings. Source/target IDs and payload digests are evidence, not newly compared
business values. Monitoring does not revalidate current contacts or prove target
restoration preserved them. The actual migration worker performs reconciliation.

## Consistency, retention and recovery

The worker reads a repeatable-read, read-only PostgreSQL transaction and sends
bounded pages through the dedicated Odoo import API. The app stages a complete
snapshot, checks counts/reconciliation/mapping evidence, and activates it in one
Odoo transaction. Interrupted imports leave the previous complete view available
and can resume idempotently. An older concurrent import cannot replace a newer
one. Completed snapshots are immutable; direct create/write/delete is blocked.

The change signature covers supported journal append/update paths, not arbitrary
manual SQL tampering. A known older journal revision is blocked for review if
the independent journal is restored backward. Odoo-only restore/rebuild can be
followed by addon installation and a fresh full import from the intact journal;
this restores tracking, not business records or their validity.

Initial limits: 100 rows per page and 10,000 rows per journal table. Changed
revisions retain full snapshot copies, including previous/import-incomplete
copies; retention/compaction is not implemented. These pilot limits are not an
enterprise performance claim. Viewer access spans all imported journals in the
database; company/OPCO-specific segregation is future scope.

## Validation

The addon was installed on the official Odoo 20 image and tested with real
PostgreSQL and Chromium. Native tests exercise roles, direct-write/context spoof
protection, idempotence, incomplete/stale/empty imports, evidence validation,
unique-record counts and safe target navigation. The end-to-end run used a
synthetic Odoo 12 source, real Odoo 20 contact migration, the real journal, and
the actual monitor/import/browser path. Contact count stayed unchanged during
monitoring. This is separate from installation on your existing local lab.

Optional reproducible developer test (Docker, Chromium required):

```bash
python -m pip install -r requirements-control-test.txt
python scripts/run_control_integration.py
```

It owns disposable test containers/network/tmpfs, removes only those resources,
and writes redacted logs/screenshots under ignored reports/control-integration/.
No existing lab database or named volume is used.
