# Environment assessment — 2026-11-03

## Observed cloud checkout

Root: `/workspace/mdm_migration`. Initial branch: `work`.
Baseline commit: `2ad4ef885a241dc66e6cfe4945f937f76cc74ad0` (`Create test`).
Initial tracked content: one five-byte file, `test`. Initial working tree clean.
No README, AGENTS, Compose, Dockerfiles, dependency declarations, Odoo addons,
migration scripts or tracking mechanisms existed. No existing project
configuration was overwritten.

The documented home-relative lab path does not exist here. A search of workspace
and accessible temporary directories found no Compose or AGENTS files before
development. One unrelated daemon directory in /tmp was inaccessible; this is
not a claim of complete machine-wide discovery.

## Actual checks

| Check | Observation |
|---|---|
| Python | 3.12.14 available |
| Docker daemon | 28.4.0, reachable on managed Unix socket outside command sandbox |
| All local Docker containers | Empty listing, including stopped containers |
| HTTP `/web/login` on 127.0.0.1:8012 | Connection refused |
| HTTP `/web/login` on 127.0.0.1:8020 | Connection refused |
| PostgreSQL CLI | Not installed |
| Eight ODOO12/ODOO20 connection variables | All absent |
| Managed credential bindings | None configured |
| Private network/VPN | Not configured; TCP grant lists empty |

The user confirmed that the existing lab is in their local environment. This
cloud task cannot inspect that machine's services, filesystem, databases or
Docker volumes through its own localhost. The claimed Odoo and PostgreSQL
versions, installed modules, source mounts, database settings, XML-RPC endpoints,
credentials and filestore remain unverified.

## Required follow-up

Provide the existing lab configuration and a supported connection path, or run
this repository's assessment on the local machine. Remote access must preserve
authentication and TLS. Avoid publicly exposing either database. Do not assume
that an Odoo 20 image or XML-RPC implementation is available; inspect the actual
server version and supported API when reachable. No replacement Docker lab was
created, and no service, database or volume was modified.

Current readiness: Python development and fixture testing work. Live Odoo
assessment, schema discovery and migration testing are blocked by missing access.

## Subsequent development-branch assessment

The user's upload landed on remote main at 8aa2ec5. Its files were imported into
development after sanitization; the original main history was not rewritten.
Compose, both Dockerfiles, the installer and lab README are now present. The
source clones are not tracked/present here; install.sh clones Odoo branches 12.0
and 20.0 without commit pins. No heavy rebuild was run because the user's lab
already runs locally and live cloud access remains unavailable.

Compose configuration validation and installer shell syntax checks passed.
These are not build/startup tests. Existing tracked build logs were preserved;
new logs and nested source clones are ignored. The supplied configuration originally contained lab password literals; values
were not copied into reports. Those literals have now been replaced with required
LAB_PG12_PASSWORD/LAB_PG20_PASSWORD variables, without changing existing databases.
Source pinning and verified cloud builds remain operational hardening work. No database, source code mount, container or volume was reset.

The committed core-model export has been compared; see schema-comparison.md.
User-local connectivity evidence remains separate from cloud connectivity.
