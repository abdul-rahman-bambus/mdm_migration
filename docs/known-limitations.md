# Known limitations

- The Odoo lab exists on the user's local machine, not in this cloud workspace.
- Local screenshots show successful XML-RPC authentication and server-reported
  versions 12.0/20.0. Full schemas, source provenance and modules are unverified.
- No direct cloud-to-Odoo authentication or migration test has succeeded here.
- Assessment tooling remains read-only. A separately guarded synthetic contact
  pilot has been added; general business-data adapters are not complete.
- General migration adapters, bulk processing, approved business mappings,
  restore recovery and UI-triggered execution are not built. Read-only tracking
  UI is implemented and tested on real Odoo 20; local installation is pending. A single-record synthetic pilot journal,
  explicit apply/update and marker-based retry are implemented and fixture-tested. Offline schema comparison is tested;
  paginated module inventory is implemented but awaits real local execution.
- Synthetic fixture tests establish protocol and error-handling behavior only.
- Raw remote fault bodies are suppressed; safe detailed diagnostic storage is
  future work. No exception text containing server data is written to reports.
- HTTPS proxy behavior uses Python's standard urllib configuration; it has not
  been integration-tested against a remote Odoo endpoint in this environment.
- No performance or enterprise-scale readiness claim can be made.

- Local lab configuration and core schemas are now tracked; defaults, computed
  status, writeability and dependent-model/module inventory remain unresolved.

- The contact pilot requires real local Odoo acceptance. Its journal/history
  and retry behavior passed real PostgreSQL tests, but Odoo endpoints were
  synthetic HTTP fixtures. Scope and operational limits are in contact-pilot.md.

- The tracking UI has bounded full snapshots and broad per-database Viewer
  scope. Retention, per-company/OPCO rules and UI Start/Retry workflows remain
  unimplemented; see migration-control-center.md. Monitoring reports historical
  evidence and does not perform fresh reconciliation or repair restored targets.
