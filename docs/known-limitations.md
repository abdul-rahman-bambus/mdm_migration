# Known limitations

- The Odoo lab exists on the user's local machine, not in this cloud workspace.
- Real server versions, endpoints, schemas, modules and credentials are unverified.
- No live database/API authentication or migration test has succeeded here.
- Current tooling is a read-only XML-RPC assessment, not full connection adapters.
- General search/create/write, pagination, retries, schema export/comparison,
  module inventory, migrations, journal, mappings, recovery and UI are not built.
- Synthetic fixture tests establish protocol and error-handling behavior only.
- Raw remote fault bodies are suppressed; safe detailed diagnostic storage is
  future work. No exception text containing server data is written to reports.
- HTTPS proxy behavior uses Python's standard urllib configuration; it has not
  been integration-tested against a remote Odoo endpoint in this environment.
- No performance or enterprise-scale readiness claim can be made.
