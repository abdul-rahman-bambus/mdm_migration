# Connectivity assessment

Run from the repository root with Python 3.12. The CLI reads exported ODOO12_URL,
ODOO12_DB, ODOO12_USERNAME, ODOO12_PASSWORD and corresponding ODOO20 variables.
`.env.example` documents names only; it is not automatically sourced. Securely
configure dedicated laboratory credentials, never production ones.

`python3 -m migration_lab` checks configuration without network access and exits
1 because connectivity is untested. `python3 -m migration_lab --live --timeout 10`
performs read-only requests. Timeout applies to each request; there are no
automatic retries. Responses are bounded at 4 MiB. TLS verification stays enabled.
System proxy configuration is respected; redirects are rejected.

The probe checks `/xmlrpc/2/common` version and authentication, then
`/xmlrpc/2/object` fields_get and ID-only search_read for product.template,
product.product and res.partner. Expected reported majors are 12 and 20.
Unexpected versions block further requests to that instance. Authentication
failure blocks model reads. Empty samples are explicit and provide no evidence
of real record conversion. These requests do not create, update or delete data.

Exit 0 means implemented live connectivity checks passed for both configured
instances. `migration_ready` remains false: module inventory, schema comparison,
write permissions, mappings and reconciliation have not been established.
The current tests use synthetic servers, not actual Odoo installations.

## Cloud-to-local boundary

`localhost:8012` and `localhost:8020` on the user's computer are different from
the same addresses in this cloud task. Options requiring user configuration are
a supported private network route with secure HTTP access, or running the checker
locally and sharing its sanitized report. Do not expose PostgreSQL or publish
Odoo unsecured to make a check pass. No private route is currently configured.

If real Odoo rejects XML-RPC or lacks these models, retain the failure and inspect
the supported API and installed modules before selecting a version-specific
adapter. Do not invent API compatibility or suppress errors.
