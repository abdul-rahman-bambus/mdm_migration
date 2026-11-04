# Local contact and historical chatter trial

This extends the migration experiment to 1–5 explicitly selected, top-level
Odoo 12 contacts in the documented local lab. It is separate from the old
synthetic-only pilot. Source access is read-only; no source addon is required.
This is not the client's custom MDM migration or a full customer/vendor mapping.

## What is copied

- Contact fields: name, email, phone, active and VAT/Tax ID. Country maps by ISO
  code, never by copying its source database ID. The original is_company flag
  must agree with Odoo 20's computed classification; it is verified rather than
  forced into a readonly field. Other fields, including addresses, original ref,
  ranks, tags, images and parent links, are not mapped. A dedicated ref marks the
  imported contact.
- Contact chatter from mail.message: original subject/date, original author
  label (or sender when no author exists), message type/subtype labels and
  readable body text. Historical messages appear as internal notes. Their real
  Odoo creation date is the import date; the message date is the original UTC
  date. Source users are not impersonated or automatically created.
- Tracked field changes become labelled old/new text in the historical entry.
  Native mail.tracking.value rows and their old field IDs are not copied.
- Binary attachments directly attached to the contact or linked to selected
  messages. Original filenames, bytes and message-to-file links are checked.
  Target files are private and linked to the new contact. Source attachment IDs
  and message IDs map independently in PostgreSQL.

Rich HTML is rendered as escaped, readable text. Inline image embedding, source
attachment URLs, tracking pixels and interactive content are not replayed.
Images can still migrate as separate binary attachments when linked in source.
Native image transformations that change bytes block the import for review.
Original rich rendering, threading/reply relationships, recipients, followers,
outgoing emails, activities, attachment creation metadata and custom log tables
are not preserved. Do not interpret readable history as full native mail fidelity.

Limits per contact: 100 messages, 20 attachments, 2 MiB per file, 8 MiB total
binary data, 500 tracking rows in source collection and 50 changes per message.
The read client also enforces bounded XML-RPC responses. Exceeding a limit,
inaccessible linked data or an unsupported message/attachment/tracking type
blocks the contact; it is never silently truncated. URL attachments are blocked.
User-account contacts and child contacts are excluded. Companies are supported
when native target classification agrees. In the tested Odoo 20 build, a
top-level contact is classified from its tax data. A legacy company without a
usable Tax ID, or an individual classified differently by target rules, blocks
preview with trial_company_classification_requires_mapping. Do not invent a VAT,
disable target computation or relabel the source just to make the import pass.
Country codes must resolve uniquely; native VAT validation/normalization can
also block apply/read-back. Parent/child relationships need a future mapping.

If an older worker reports only rpc_fault, pull development: native Odoo 20
can return the classification blocker as a bare XML-RPC UserError label. The
updated worker recognizes only its static allowlist and still suppresses raw
faults. This diagnostic fix does not resolve or bypass the classification
disagreement. Check whether the source is a company/person and whether its Tax
ID is empty or a placeholder; do not alter genuine source data to pass a trial.

## Upgrade and roles

Use development and the existing activated virtual environment. Restore the
connection variables as described in docs/contact-pilot.md after a reboot.

```bash
git switch development
git pull --ff-only origin development
source .venv/bin/activate
```

The addon now depends on native mail. Restart only the existing Odoo 20
application so its Python code is reloaded:

```bash
docker restart odoo_migration_lab-odoo20-1
```

After Odoo has started, enable developer mode, update the Apps list, then
**upgrade Bambus Migration Control** (install it if not already installed).
Assign the ODOO20_USERNAME worker account **Contact Trial Migrator**, under
Migration Operations / Migration Control. This role includes Journal Importer
and Viewer. The Journal Importer role alone cannot migrate contacts. Business
record writes respect the worker's native ACLs; sudo is used only for protected
identity receipts. This trusted execution role is restricted to the target
database named odoo20_migration; the CLI also restricts both loopback endpoints.

Keep the existing JOURNAL_DB_PASSWORD and eight ODOO connection settings
exported in the same terminal. Add the independent history mapping table:

```bash
python -m migration_lab.pilot init-journal --lab-only
```

Initialization is additive and preserves existing journal history/identity.
Never reset a database, change an existing PostgreSQL password, or remove a
volume to install/upgrade. Restart retains existing container configuration;
there is no need to re-enter LAB_PG passwords unless recreating via Compose.
The source account must read contacts, messages, tracking values and files.
Standard Odoo 12 restricts the tracking_value_ids relation to base.group_system;
use the existing authorized laboratory administrator for this experiment. The
worker does not bypass source record/field permissions or silently omit them.

## Select and preview

Select 1–5 top-level laboratory contacts with useful history. Use the developer
record ID from Odoo 12. Start with one contact that has not already been copied
by the old synthetic pilot. No contact or source content is seeded by this command.
Pause edits to the selected contacts/history while collecting and applying the
trial. Separate source RPC reads are not a transactionally consistent database
snapshot; live concurrent migration/delta capture is not implemented.

```bash
read -r -p "Odoo 12 contact ID for this trial: " CONTACT_TRIAL_ID
python -m migration_lab.contact_history plan --lab-only \
  --contact-ids "$CONTACT_TRIAL_ID" --output reports/contact-history-plan-1.json
```

For a later small batch, supply up to five explicit IDs after --contact-ids.
Do not run the old synthetic worker and this trial against the same contact:
cross-version/global entity deduplication is not implemented.

The target preview checks protected identity receipts and current imported
records but writes no target data. The independent journal records each preview.
Review the displayed field scope, per-contact proposed operation, message,
attachment and tracking-change counts. A candidate with matching target email
or name blocks creation for review; there is no automatic merge. This is a
conservative candidate check, not a complete duplicate-resolution system.

The plan contains only IDs, digests, operations and counts, not contact bodies,
email addresses, filenames, attachment bytes or credentials. It is created with
owner-only permissions and never overwrites another file. Keep it under ignored
reports/. A source change after preview requires a new plan/output filename.

## Apply the reviewed selection

```bash
python -m migration_lab.contact_history apply --lab-only \
  --plan reports/contact-history-plan-1.json --apply
```

This re-reads the source and requires its digest to match the reviewed snapshot.
It does not select any additional contacts. Each contact and all its historical
messages/files/target receipts are written in one Odoo transaction. A failure
rolls back that contact's transaction, not earlier successful contacts in the
batch. Processing stops on the first error; review the journal before retrying.
No message_post or notification-dispatch API is used. No historical emails,
notifications, activities or subscriptions should be produced by the native
addon path. Source customizations are read only; target custom mail hooks would
need separate validation before use outside this clean laboratory trial.

After commit, a separate read-back RPC checks contact fields, every receipt,
message content/date/links and attachment bytes. Only then does the independent
journal mark the contact reconciled and persist per-history ID/digest mappings.
Counts alone never establish reconciliation. Imported contact/history tampering
or missing/reused targets blocks review; it is not automatically overwritten.

## Rerun, updates and monitoring

Repeat the same apply command to verify no duplicates. A lost response can leave
Odoo committed while the journal attempt is failed: repeat the same plan after
review, and protected target receipts recover those identities without a second
copy. An ambiguous missing target with a prior create intent remains blocked.
Independent journal item mappings prevent silently recreating history lost from
a target restore. Do not delete those receipts or create a second journal.

For changed contact fields or new chatter, generate a new plan, review and apply.
Old source history is append-only in this trial: editing/removing a previously
imported message or attachment blocks for review. Contact edits made in Odoo 20
also block automatic overwrite. There is no approved conflict-resolution or
full restore-recovery workflow yet.

```bash
python -m migration_lab.monitor
# Or keep a separate terminal monitoring:
python -m migration_lab.monitor --watch --interval 10
```

Use Reload view in Bambus Migration Control. Each selected contact has a record
group, attempts, result and mapping. Event details show safe message/attachment/
tracking-change counts, not business content. Open target contact to read actual
imported historical notes and files. Per-message/file mappings are retained in
the independent journal; the dashboard does not yet provide separate item lists.
Customer/vendor ranks and accounting configuration are not part of this trial.

## Verification and boundaries

Run the standard suite and scripts/run_control_integration.py with its optional
test requirements. The isolated test uses native Odoo 20 and real PostgreSQL,
plus a synthetic Odoo 12-shaped RPC source. It tests notification suppression,
rollback, content/bytes/dates, lost acknowledgements, reruns, guarded updates,
source changes, target conflicts and monitoring. These tests do not establish
compatibility with the user's actual Odoo 12 database or custom addons; local
trial acceptance remains required. All test records and files are synthetic.
