# Known limitations

- The Odoo lab exists on the user's local machine, not in this cloud workspace.
- Local screenshots show successful XML-RPC authentication and server-reported
  versions 12.0/20.0. Full schemas, source provenance and modules are unverified.
- No direct cloud-to-Odoo authentication or migration test has succeeded here.
- Current tooling is a read-only XML-RPC assessment, not full connection adapters.
- General migration create/write adapters, retries, migrations, journal, approved
  mappings, recovery and UI are not built. Offline schema comparison is tested;
  paginated module inventory is implemented but awaits real local execution.
- Synthetic fixture tests establish protocol and error-handling behavior only.
- Raw remote fault bodies are suppressed; safe detailed diagnostic storage is
  future work. No exception text containing server data is written to reports.
- HTTPS proxy behavior uses Python's standard urllib configuration; it has not
  been integration-tested against a remote Odoo endpoint in this environment.
- No performance or enterprise-scale readiness claim can be made.

- Local lab configuration and core schemas are now tracked; defaults, computed
  status, writeability and dependent-model/module inventory remain unresolved.
