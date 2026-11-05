"""Pull development and upgrade installed modules in the existing local Docker lab."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import time
import urllib.request

DOCKER = ["docker", "--host=unix:///var/run/docker.sock"]
LABS = {
    12: {"container": "odoo_migration_lab-odoo12-1", "pg": "odoo_migration_lab-pg12-1",
         "host": "pg12", "database": "odoo12_demo", "port": 8012,
         "paths": ["/opt/odoo/odoo/addons", "/opt/odoo/addons"]},
    20: {"container": "odoo_migration_lab-odoo20-1", "pg": "odoo_migration_lab-pg20-1",
         "host": "pg20", "database": "odoo20_migration", "port": 8020,
         "paths": ["/opt/odoo/odoo/addons", "/opt/odoo/addons", "/mnt/bambus-addons"]},
}

# Runs inside the selected container with its existing PGPASSWORD. It never
# prints/reads credentials, initializes a database, or changes module state.
PREFLIGHT = """import ast, json, sys
from pathlib import Path
import psycopg2
from odoo import release
major, database, host, paths, modules = json.loads(sys.argv[1])
if release.version_info[0] != major:
    sys.exit('Wrong Odoo major version in the selected container.')
for module in modules:
    files = [Path(path) / module / name for path in paths for name in ('__manifest__.py', '__openerp__.py')]
    manifest = next((path for path in files if path.is_file()), None)
    if manifest is None:
        sys.exit('Module is not visible in the configured addon paths: ' + module)
    data = ast.literal_eval(manifest.read_text())
    version = str(data.get('version', ''))
    if (version.startswith('12.0.') or version.startswith('20.0.')) and not version.startswith(str(major) + '.0.'):
        sys.exit('Module manifest targets a different Odoo major: ' + module)
with psycopg2.connect(host=host, user='odoo', dbname=database, connect_timeout=5) as db:
    db.set_session(readonly=True)
    with db.cursor() as cursor:
        cursor.execute('SELECT name,state FROM ir_module_module WHERE name = ANY(%s)', (modules,))
        states = dict(cursor.fetchall())
        if any(states.get(module) != 'installed' for module in modules):
            sys.exit('Every selected module must already be installed. Install through Apps first, or resolve pending module operations.')
print('Selected module files, Odoo version and installed state checked.')
"""


class UpdateError(Exception):
    pass


def execute(command, *, cwd, env, stream=False):
    try:
        result = subprocess.run(command, cwd=cwd, env=env, text=True,
                                **({} if stream else {"capture_output": True}))
    except OSError:
        raise UpdateError("Required Git/Docker executable is unavailable.") from None
    if result.returncode:
        raise UpdateError("Operation failed; no subsequent upgrade/restart step was run. Check Git manually or the upgrade output above.")
    return "" if stream else result.stdout.strip()


def modules_from(values):
    modules = [name for value in values for name in value.split(",")]
    if (not modules or len(set(modules)) != len(modules)
            or any(re.fullmatch(r"[a-zA-Z_][a-zA-Z0-9_]*", name) is None or name == "all" for name in modules)):
        raise UpdateError("Use explicit, unique technical module names; 'all' is not allowed.")
    return modules


def upgrade_command(version, modules):
    lab = LABS[version]
    return [*DOCKER, "exec", lab["container"], "/opt/venv/bin/python", "/opt/odoo/odoo-bin",
            "--config=/dev/null", "--db_host=" + lab["host"], "--db_user=odoo",
            "--database=" + lab["database"], "--addons-path=" + ",".join(lab["paths"]),
            "--data-dir=/var/lib/odoo", "--update=" + ",".join(modules), "--stop-after-init", "--no-http"]


def update(root, version, modules, pull=True, runner=execute):
    env = {k: v for k, v in os.environ.items() if k not in {
        "DOCKER_HOST", "DOCKER_CONTEXT", "DOCKER_TLS", "DOCKER_TLS_VERIFY", "DOCKER_CERT_PATH"}}
    def run(command, stream=False):
        return runner(command, cwd=root, env=env, stream=stream)

    if run(["git", "branch", "--show-current"]) != "development":
        raise UpdateError("Switch this checkout to development first; the script never switches branches.")
    if pull and run(["git", "status", "--porcelain"]):
        raise UpdateError("Working tree has local changes. Preserve them before pulling, or explicitly use --skip-pull to upgrade your local code.")
    lab = LABS[version]
    if run([*DOCKER, "inspect", "--format", "{{.State.Running}}", lab["container"]]) != "true":
        raise UpdateError("Start the selected Odoo container first. This exec-based helper needs it running.")
    if run([*DOCKER, "inspect", "--format", "{{.State.Health.Status}}", lab["pg"]]) != "healthy":
        raise UpdateError("The selected PostgreSQL container must be healthy before upgrade.")
    if pull:
        print("Pulling origin/development with fast-forward only...", flush=True)
        run(["git", "pull", "--ff-only", "origin", "development"])
    check = [version, lab["database"], lab["host"], lab["paths"], modules]
    print("Checking installed modules and mounted source...", flush=True)
    run([*DOCKER, "exec", lab["container"], "/opt/venv/bin/python", "-c", PREFLIGHT, json.dumps(check)], stream=True)
    print("Upgrading selected modules. Pause use of this Odoo UI and migration workers until finished.", flush=True)
    run(upgrade_command(version, modules), stream=True)
    print("Upgrade completed; restarting only " + lab["container"] + "...", flush=True)
    run([*DOCKER, "restart", lab["container"]])


def wait_ready(version, timeout=90):
    lab = LABS[version]
    url = "http://127.0.0.1:" + str(lab["port"]) + "/web/login?db=" + lab["database"]
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3) as response:
                if response.status == 200:
                    print("Odoo login page is responding: http://localhost:" + str(lab["port"]))
                    return
        except Exception:
            pass
        time.sleep(1)
    raise UpdateError("Upgrade completed, but the login page did not become ready. Check docker logs for " + lab["container"] + ". No automatic rollback was attempted.")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--odoo", type=int, choices=sorted(LABS), default=20)
    parser.add_argument("--modules", nargs="+", required=True, help="Technical names, separated by spaces or commas")
    parser.add_argument("--skip-pull", action="store_true", help="Upgrade local edits without pulling; still requires development")
    parser.add_argument("--dry-run", action="store_true", help="Print intended commands only; no readiness checks or changes")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    try:
        modules = modules_from(args.modules)
        if args.dry_run:
            print("Preview only; container readiness and installed modules have not been checked.")
            if not args.skip_pull:
                print(shlex.join(["git", "pull", "--ff-only", "origin", "development"]))
            print(shlex.join(upgrade_command(args.odoo, modules)))
            print(shlex.join([*DOCKER, "restart", LABS[args.odoo]["container"]]))
            return 0
        directory = root / "reports"
        directory.mkdir(exist_ok=True)
        with open(directory / "module-upgrade.lock", "a") as lock:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise UpdateError("Another lab module update is already running.") from None
            update(root, args.odoo, modules, not args.skip_pull)
            wait_ready(args.odoo)
        return 0
    except UpdateError as exc:
        print("Stopped: " + str(exc))
    except KeyboardInterrupt:
        print("Interrupted. An upgrade may still be running inside Docker; inspect it before retrying or restarting.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
