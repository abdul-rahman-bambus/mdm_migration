# Project status

Latest update: 2026-11-03 (Asia/Kolkata).
Branch: `work`. Assessed base/current pre-implementation commit:
`2ad4ef885a241dc66e6cfe4945f937f76cc74ad0`.
The implementation is committed after this status file is written; obtain its
exact revision with `git log -1 --format=%H` rather than treating the baseline
above as the implementation commit.

## Completed and verified

- Inspected available repository, tools, Docker daemon and expected local ports.
- Read-only assessment CLI, validated with synthetic XML-RPC fixtures.
- Configuration validation, bounded requests, authentication checks, metadata
  and ID-only sample reads, sanitized errors and explicit blocked outcomes.
- Initial AGENTS, README, architecture, assessment, connectivity, limitations,
  test evidence and future MDM documentation.
- User-local screenshot evidence: both servers authenticated via XML-RPC and
  supplied metadata for templates, variants and partners. See
  local-connectivity-evidence.md for field counts and sample limitations.
- Standalone core-model schema exporter, verified with mocked RPC responses;
  real schema export and comparison remain outstanding.

## Partial

- Phase 1: cloud assessment complete; the actual user-local lab is inaccessible.
- Phase 2: read-only XML-RPC probe exists. General version-specific connection
  adapters and live integration verification are not complete.

## Not started

Schema comparison, reviewed field maps, independent PostgreSQL journal,
persistent ID mappings, business record migrations, binary migration, chatter
feasibility, reconciliation, approved corrections/retries, Odoo control addon,
failure recovery simulations and performance measurement.

## Test evidence

Latest unittest run: 18 executed, 18 passed, 0 failed, 0 skipped (2.675s).
CLI help passed. Configuration-only assessment exits 1 as expected because all
eight connection variables are missing in the cloud. Both cloud-local HTTP probes
failed with connection refused. The user subsequently ran a separate inline
probe locally: authentication and metadata/sample reads succeeded on both real
servers. These are screenshot-reported results, not direct cloud tests.
No real migration was attempted; latest successful migration and reconciliation:
**none**. No measured migration performance exists.

## Environment and blockers

Python 3.12.14 and Docker 28.4.0 are available. No Docker containers or lab
configuration exist in this checkout; the documented home-relative path is
absent. The user confirmed the Odoo lab is local to their machine. No private
access route or Odoo credential bindings are configured. Local servers report
versions 12.0 and 20.0 with functioning XML-RPC. Source provenance, full schemas,
modules and database/filestore configuration remain unknown.

Known implementation defects: none identified by the current tests; this does
not establish real Odoo compatibility. Missing functionality is listed above.

## Next task

Export actual field definitions and installed module names from the local lab
using the same authenticated read-only route. Obtain existing lab configuration
without secrets. Compare schemas before migration writes. A supported direct
cloud connection remains optional if local execution supplies the evidence.
