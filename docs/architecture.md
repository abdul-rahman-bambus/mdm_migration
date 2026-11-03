# Architecture and incremental implementation plan

## Implemented

`migration_lab.preflight` reads environment configuration and issues bounded,
read-only XML-RPC requests through urllib, preserving system TLS trust and
inherited proxy behavior. Redirects are refused to prevent credential forwarding.
Configuration-only operation never claims connectivity. Both instances are
assessed independently. No new dependency installation is required.

## Planned

1. Verify the existing local lab and inventory versions, modules and models.
2. Build version-specific adapters from observed external API behavior. The
   current XML-RPC probe is not an assertion of Odoo 20 compatibility.
3. Discover field metadata and compare schemas; review explicit versioned maps.
4. Establish an independent PostgreSQL journal with run/record/field/issue/fix/
   retry/reconciliation history and environment-aware ID mappings.
5. Build dependency-ordered product and partner migration, then binary handling.
6. Assess chatter feasibility, metadata preservation and notification suppression.
7. Reconcile expected values and relationships; only then mark final success.
8. Implement approved corrections, bounded retries and checkpoint recovery.
9. Add `bambus_migration_control` as a synchronized Odoo monitoring addon.
10. Test synthetic failure scenarios, interruption, reruns and target restoration;
    measure performance with explicitly bounded conclusions.

These are separate reviewable increments. Failed live prerequisites block live
migration; fixture results alone do not justify moving to business record writes.

The journal must survive a target rebuild, but stale mappings cannot be reused
blindly after restoration. Recovery must establish target identity and verify
mapped records before resuming. The concrete recovery protocol is not designed
or implemented yet.

## Safety boundaries

Source-to-target identities are explicit; source database IDs are never copied
as target relationships. Migration workers own writes and authorized retries.
The web addon must not execute arbitrary shell commands. Logs retain protected
diagnostic references, not passwords or unnecessary personal data. Historical
chatter support and production target version are unresolved decisions.

## Synthetic contact pilot increment

The separately guarded pilot adds explicit res.partner writes for a known
synthetic record, backed by an independent PostgreSQL journal. Standard
assessment clients remain read-only. Name/email/phone are the only payload
fields and ref is a deterministic technical marker. Versioned manifest and
runtime scope must agree. A journal session lock, durable intents and target
marker handle interrupted create retries; reconciliation is committed atomically
with the last-successful mapping in PostgreSQL. There is no cross-system
transaction. Restore conflicts fail closed. See migration-tracking.md and
contact-pilot.md; the wider planned architecture above is still incomplete.

## Read-only tracking UI increment

The implemented Odoo 20 addon mirrors journal metadata through an authenticated,
role-restricted import API; it has no PostgreSQL secret and never executes the
migration worker. The host monitor reads an independent repeatable-read READ
ONLY snapshot, validates the shared schema contract and sends bounded pages.
The UI activates only complete, checked snapshots and groups run attempts into
tracked namespaces. History stays authoritative outside Odoo; current journal
outcomes and historical successful mappings remain distinct. See
migration-control-center.md for setup, consistency, role and scale limits.
