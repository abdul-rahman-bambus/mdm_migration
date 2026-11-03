# Test results — 2026-11-03

Command from `/workspace/mdm_migration`:

```sh
python3 -m unittest discover -s tests -v
```

Latest run: **15 tests, 15 passed, 0 failures/errors, 0 skipped**, 4.688 seconds.
The command ran with loopback socket access outside the command sandbox.

Coverage exercised: environment validation and secret redaction; complete
read-only XML-RPC request sequence; unexpected version blocking; invalid
authentication blocking; sanitized RPC faults; explicit empty samples; refusal
of redirects; malformed responses; response-size bounds; timeout without retry;
write refusal; configuration-only CLI status; end-to-end CLI requests to separate
synthetic version-12 and version-20 servers; unavailable service detection.

These are synthetic protocol fixtures. No real Odoo version, schema, database,
write permission, image, attachment, chatter or migrated record was tested.

`python3 -m migration_lab --help` passed. `python3 -m migration_lab` returned
the expected exit 1 and named the missing variables for both instances without
printing credentials. This is an expected blocked check, not a live success.

Actual environment requests to both expected local Odoo ports were refused.
Docker reported zero local containers. See environment-assessment.md.
