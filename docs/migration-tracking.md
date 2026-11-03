# Pilot journal architecture

The pilot uses PostgreSQL 16 separately from both Odoo databases, with its own
Compose project/volume and fixed independent database name. Target Odoo restore
does not erase this journal. Keep its credentials and persistent volume; the
pilot does not implement production backup/restore operations.

Schema: bambus_pilot, version 1. Initialization only creates missing structures;
it never drops tables or clears records. Four tables retain schema version,
runs, append-only events and the last reconciled source/target mapping.

Each run stores source/target endpoint/database/model identities, mapping
version, operation, timestamps, IDs, payload digest and final status/error code.
Mappings identify source/target model and record IDs, stable marker, mapping
version, last successful run, digest and reconciliation state. Namespace binds
the environment identities, label and mapping version. Actual payloads and
passwords are not stored in the journal.

Run intent/extraction/validation/load/failure events are durable before advancing
to external API writes. A PostgreSQL session advisory lock covers each pilot
namespace. Reconciliation event, final success and mapping are committed in one
journal transaction after target readback. Odoo and journal do not share a
distributed transaction; the durable target marker closes the interrupted-create
retry window for workers sharing this journal. This is not a general exactly-once
guarantee against arbitrary external writers or independently configured journals.

Failed/incomplete runs remain in history. The mapping represents the last
reconciled payload, while status separately exposes the latest run result.
Target restore/mapping conflicts fail closed rather than overwriting a reused
ID or silently recreating a mapped record. Full restore reconciliation, approval
records, field-level correction workflow, multi-record batches and dashboard
synchronization remain future extensions. See contact-pilot.md for actual commands.
