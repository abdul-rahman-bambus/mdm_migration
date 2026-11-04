# Project status

Latest update: 2026-11-04 (Asia/Kolkata). Branch: development.
Base for contact-history increment: 41a8855. Use git log -1 --format=%H for the latest commit.
Main and private local review branches are unchanged; never push those archives.

## Implemented

- Explicit 1–5 selected contact/history trial with reviewed-source-digest plans,
  read-only Odoo 12 extraction, atomic Odoo 20 contact/chatter/file imports and
  independent per-history ID/digest mappings. Original author labels and dates
  are preserved as readable internal history, not impersonated users/native
  tracking rows. Separate Contact Trial Migrator role; normal business ACLs.
- Scoped contact/Tax ID mapping and country lookup by ISO code. Native company
  classification must agree with source; unsupported classifications block
  preview instead of forcing readonly fields or inventing tax data.
- Synthetic contact pilot with explicit create/update, native-default validation,
  marker-based idempotence, journal intents/history, locking and reconciliation.
  User-local create/rerun/update results have been supplied successfully; actual
  run IDs, private inventory and screenshots are not published in this increment.
- Read-only Odoo 20 Bambus Migration Control addon: overview, grouped records,
  execution histories/timelines, issues, reconciliation evidence and mappings.
- Viewer and trusted Journal Importer roles; Odoo 20 ir.access permissions and
  protected mirror writes. No arbitrary shell execution or business sync in UI.
- Host-side monitor with consistent READ ONLY journal snapshot, bounded pages,
  change detection, stable journal identity, resumable staging and atomic
  activation. Immutable completed snapshots and stale-import protection.
- Current outcomes separated from historical successes/failures; reruns grouped
  as one tracked namespace. Incomplete attempts are not labelled live processes.
- Target-contact navigation validates its marker and honors native permissions.
- Additive journal monitoring identity and Odoo 20 addon mount/path configuration.
  No Odoo 12, PostgreSQL service, password, existing volume or database was reset.

## Executed validation

- 87 standard unit/protocol tests passed, 0 failures/errors/skips (3.742s).
- 16 PostgreSQL/HTTP pilot integration tests passed (14.525s), including READ ONLY
  monitor export and preservation of stable identity on repeat initialization.
- 40 native Odoo addon tests passed on official Odoo 20 (20.0-20261102), 0 failed
  or errors. Roles, context forgery/direct writes, idempotence, stale/partial/empty
  snapshots, evidence validation and marker-checked navigation were exercised.
- Contact-history tests additionally verify original dates/labels/content/file
  bytes, append-only history, rollback, permissions, archived companies, country
  mappings and classification conflicts. No outgoing mail/notifications,
  followers or activities were created by the historical import path.
- Real Chromium overview/lists/read-only controls, record timeline/drill-down,
  target navigation and stylesheet/layout assertions passed without page errors.
- End-to-end contact pipeline into actual Odoo 20 from a synthetic Odoo 12 server:
  seed, preview, lost acknowledgement, safe retry, rerun, source edit and update.
  Its real journal produced one tracked record across seven execution attempts.
  Monitor import did not change the target contact count. These are isolated
  synthetic integration results, not fabricated user dashboard totals.
- The full history worker ran against native Odoo 20, real PostgreSQL and a
  synthetic Odoo 12-shaped RPC source: preview, lost acknowledgement, safe
  recovery/rerun, source digest rejection, reviewed update, independent message/
  file mappings and journal UI transfer passed. Chromium opened that contact
  from tracking and verified its historical note, author label and attachment.
- Both Compose configurations validated with non-secret placeholders; pip check
  passed. Test containers/network/tmpfs were cleaned by their owner; no existing
  lab resource or named test volume was used.

Verified source reference for API inspection: official Odoo 20 branch commit
006f5cc915ebb0f30c6f8602c1b42e6d7ff1e754 (ignored dependency clone).
Odoo test image digest: a97a7665e2b9fd890e12785491a2c91d779f800bcbc30873dada1c8748b28f1c.
Runtime screenshots/logs/results are in ignored reports/control-integration/.
Detailed uploaded environment metadata remains private, outside the checkout.

## Local acceptance still needed

The addon is not installed on the user's running lab by these cloud tests.
Follow docs/migration-control-center.md: pull development, preserve/export the
existing PostgreSQL lab passwords, recreate only the Odoo 20 application to mount
addons, install through Apps, assign the worker account Journal Importer, repeat
non-destructive journal init, then run monitor. Verify actual history/counts and
Viewer permissions locally. No image rebuild or database reset is required.
For the new trial, follow docs/contact-history-trial.md: pull, restart only
Odoo 20, install/upgrade the addon, assign Contact Trial Migrator to a worker with
native contact permissions, initialize the additive journal table, select a
previously unmigrated contact, review its plan and apply. Actual Odoo 12 source
compatibility/chatter preservation still need acceptance on the user's lab.

Contact migration continues to start from pilot CLI with explicit --apply.
Tracking import starts from monitor CLI; --watch only repeats tracking imports.
Reload view does not initiate either worker or perform new reconciliation.

## Limits / future work

This is contact-pilot monitoring, not the complete enterprise migration engine.
UI-triggered job requests/approvals/retries, multi-model business migration,
general product/UoM/variant/binary/chatter migration, full fix workflow, record-company/OPCO
segregation, snapshot retention/compaction and scale benchmarks remain unbuilt.
Viewer sees imported journals in this database; importer is a trusted data role.
Snapshots cap each journal table at 10,000 rows and pages at 100. No actual
enterprise performance/cutover claim is made. Journal signatures cover supported
append/update paths, not arbitrary SQL tampering. Historical reconciliation is
not a new live target check. Actual local restoration procedures remain untested;
missing/conflicting business IDs still fail closed in the worker/navigation.

The selected-contact trial preserves bounded binary files/readable chatter only;
general binary migration, rich HTML, native tracking/thread relationships,
activities/followers, custom logs, ranks/accounting and full contact mappings are
not implemented. Native Odoo 20 computes is_company from tax/commercial data;
legacy classifications that cannot be represented remain blocked for mapping
review. Source collection spans RPC reads, so pause selected-record edits during
the trial. Target restores require review rather than automatic recreation.
