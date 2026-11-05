# Pull and upgrade a custom module in the local Docker lab

Run this from the laptop's existing mdm_migration checkout. Both PostgreSQL and
the selected Odoo container must already be running, with PostgreSQL healthy.
Pause migration/monitor processes and avoid the selected Odoo UI during upgrade.
This helper is limited to the documented local databases and container names.

First retrieve the helper (one time), using the development branch:

```bash
cd ~/odoo/workspace/mdm_migration
git switch development
git pull --ff-only origin development
```

Upgrade the installed Odoo 20 custom tracking module:

```bash
python3 scripts/update_odoo_module.py --odoo 20 --modules bambus_migration_control
```

The helper pulls origin/development again with fast-forward only, verifies the
selected modules are mounted, checks the Odoo major and existing installed state,
performs --update with --stop-after-init --no-http in a separate Python process,
then restarts only Odoo 20 after success. It waits for its login page to respond.
This is a startup check, not functional module acceptance.

It uses the existing container's PGPASSWORD; no database passwords or ODOO login
variables need re-entering. It never reads/prints container environment values,
recreates containers, resets databases, removes volumes or starts contact sync.
The schema upgrade finishes before the application restart, including when a
module adds stored fields. Database credentials/filestore mounts are retained.
Module upgrade logs print locally; do not commit logs containing private data.

Preview intended commands without executing checks or changes:

```bash
python3 scripts/update_odoo_module.py --odoo 20 --modules bambus_migration_control --dry-run
```

To upgrade local edits without pulling (still on development):

```bash
python3 scripts/update_odoo_module.py --odoo 20 --modules bambus_migration_control --skip-pull
```

Multiple technical module names can be separated by spaces or commas. Only
already-installed modules can be upgraded; use Apps for a first installation.
The helper refuses 'all', duplicate/invalid names, a non-development branch,
dirty working tree before pull, stopped Odoo, unhealthy PostgreSQL, missing
module files, an explicit major-version mismatch or pending/uninstalled modules.
It never discards/stashes changes or force-pulls. A host lock prevents concurrent
helper calls from this checkout. Python 3.10+ is sufficient; no venv packages
are needed for this host script. Docker runs the matching Python inside Odoo.

## Odoo 12 and other source repositories

The same helper can select Odoo 12:

```bash
python3 scripts/update_odoo_module.py --odoo 12 --modules your_installed_custom_module
```

Replace the example with a module actually installed and visible in the Odoo 12
source addon paths. The current lab mounts this repository's addons/ directory
only into Odoo 20. It does not yet mount a separate version-12 custom addon
checkout. The helper does not add mounts or install the version-20 tracking addon
on Odoo 12; missing paths fail preflight. Configure a version-appropriate custom
mount/startup path separately before using modules outside those source paths.

Git pull here updates mdm_migration, including its tracked addons. It does not
pull ignored nested Odoo core clones under lab/odoo_migration_lab/source/ or
separate custom-module repositories. Updating Odoo core or Python dependencies
may require image rebuilds and a separate compatibility review. If the addon is
maintained in another Git checkout, update that checkout explicitly and use
--skip-pull for the upgrade; the configured mounted source must match.

## Failure handling

If pull, preflight or upgrade fails, no subsequent upgrade/restart step runs.
Code already pulled remains in place; there is no automatic code/database
rollback. Review the displayed error and fix the module before retrying.
If interrupted, a Docker exec process may still be running: inspect the selected
container before retrying or restarting. A database/module update can execute
the selected addon's migration hooks; this is not a backup/rollback system.
Do not use this lab helper against production.

If upgrade succeeds but the login page does not respond, inspect the selected
application's logs, for example:

```bash
docker logs --tail 60 odoo_migration_lab-odoo20-1
```
