# User-local connectivity evidence — 2026-11-03

Evidence source: screenshots supplied by the user after running a read-only
inline Python XML-RPC probe on their own computer. These results were not
obtained by a direct connection from the cloud task.

Both instances reported successful authentication and field metadata retrieval.
The source reports server series 12.0 and the target reports version 20.0.
These are server-reported versions, not independently verified source revisions.

| Model | Source fields | Source sample size | Target fields | Target sample size |
|---|---:|---:|---:|---:|
| product.template | 75 | 1 | 92 | 0 |
| product.product | 83 | 1 | 111 | 0 |
| res.partner | 87 | 1 | 116 | 1 |

The read used limit=1, so sample sizes are not total record counts. Zero target
product samples means the query returned no accessible active products under
the current user/context; it does not prove the database contains none.

A preceding screenshot showed all four local containers running, with PostgreSQL
12 and 16 images reporting healthy. Odoo HTTP bindings were loopback ports 8012
and 8020. These are user-local observations, not cloud container state.

## What this establishes

- Local access to the common and object XML-RPC endpoints.
- Successful authentication for the configured laboratory databases/accounts.
- Field metadata access on three core models for both servers.
- ID-only sample reads, with explicit empty target product results.

## What remains unverified

Full field definitions, installed modules, source provenance, write access,
inactive-record handling, relational dependencies, invalid-credential behavior
on live servers, binary fields, notifications, migration and reconciliation.
The cloud workspace still cannot access the local services directly.
