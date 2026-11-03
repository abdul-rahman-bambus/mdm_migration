"""Copy a bounded, consistent journal snapshot into the Odoo tracking addon.

This command never calls res.partner create/write and never executes migration.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import uuid

from .journal import Journal, PilotError
from .pilot import identity
from .preflight import ProbeFailure, ReadOnlyRPC, Settings

_spec = importlib.util.spec_from_file_location("bambus_monitor_protocol", Path(__file__).resolve().parents[1] / "addons/bambus_migration_control/protocol.py")
protocol = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(protocol)

COLUMNS = {
    "runs": "id,namespace,operation,source_identity,target_identity,mapping_version,state,source_id,target_id,payload_digest,error_code,started_at,finished_at",
    "events": "id,run_id,state,details,created_at",
    "mappings": "namespace,source_model,source_id,target_model,target_id,marker,mapping_version,payload_digest,last_run,state,updated_at",
}


class MirrorRPC(ReadOnlyRPC):
    OPERATIONS = {"monitor_info", "begin_import", "import_page", "finish_import"}


class MirrorClient:
    def __init__(self, settings):
        self.settings, self.rpc = settings, MirrorRPC(settings)
        version = self.rpc.call("common", "version")
        info = version.get("server_version_info") if isinstance(version, dict) else None
        if not isinstance(info, (list, tuple)) or not info or info[0] != 20:
            raise PilotError("monitor_requires_odoo20")
        self.uid = self.rpc.call("common", "authenticate", settings.database, settings.username, settings.password, {})
        if type(self.uid) is not int or self.uid <= 0:
            raise PilotError("monitor_authentication_failed")
        try:
            info = self.call("monitor_info")
        except ProbeFailure:
            raise PilotError("install_or_upgrade_tracking_addon") from None
        if info.get("version") != 1 or info.get("monitoring_only") is not True:
            raise PilotError("unsupported_tracking_addon_protocol")
        if info.get("can_import") is not True:
            raise PilotError("assign_migration_journal_importer_role")

    def call(self, method, *args):
        if method not in MirrorRPC.OPERATIONS:
            raise PilotError("monitor_method_not_allowed")
        result = self.rpc.call("object", "execute_kw", self.settings.database, self.uid, self.settings.password,
                               "bambus.migration.source", method, list(args), {})
        if not isinstance(result, dict):
            raise PilotError("invalid_monitor_response")
        return result


def serialize(row):
    return {key: value.isoformat() if hasattr(value, "isoformat") else str(value) if isinstance(value, uuid.UUID) else value
            for key, value in row.items()}


def transfer(journal, client):
    connection = journal.connection
    with connection.transaction():
        connection.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY")
        try:
            versions = connection.execute("SELECT version FROM bambus_pilot.version").fetchall()
            journal_key = str(connection.execute("SELECT journal_key FROM bambus_pilot.monitor_identity WHERE singleton").fetchone()["journal_key"])
        except Exception:
            raise PilotError("initialize_journal_for_monitoring") from None
        if versions != [{"version": 1}]:
            raise PilotError("unsupported_journal_version_for_monitor")
        counts, signature = {}, {}
        for kind in COLUMNS:
            # SQL identifiers are a closed code-owned set, never payload values.
            counts[kind] = connection.execute(f"SELECT count(*) AS n FROM bambus_pilot.{kind}").fetchone()["n"]
        signature["runs"] = serialize(connection.execute("SELECT max(started_at) AS started,max(finished_at) AS finished FROM bambus_pilot.runs").fetchone())
        signature["events"] = connection.execute("SELECT max(id) AS last_id FROM bambus_pilot.events").fetchone()
        signature["mappings"] = serialize(connection.execute("SELECT max(updated_at) AS updated FROM bambus_pilot.mappings").fetchone())
        revision = hashlib.sha256(json.dumps([counts, signature], sort_keys=True).encode()).hexdigest()
        manifest = {"journal_key": journal_key, "revision": revision,
                    "snapshot_key": str(uuid.uuid5(uuid.UUID(journal_key), revision)), "counts": counts,
                    "captured_at": connection.execute("SELECT transaction_timestamp() AS stamp").fetchone()["stamp"].isoformat()}
        try:
            protocol.manifest(manifest)
        except ValueError:
            raise PilotError("monitor_snapshot_exceeds_supported_limits") from None
        response = client.call("begin_import", manifest)
        if response.get("state") == "unchanged":
            return {"state": "unchanged", "counts": counts}
        if response.get("state") != "importing":
            raise PilotError("invalid_monitor_begin_response")
        for kind, columns in COLUMNS.items():
            with connection.cursor(name="monitor_" + kind) as cursor:
                cursor.execute(f"SELECT {columns} FROM bambus_pilot.{kind} ORDER BY " + ("namespace" if kind == "mappings" else "id"))
                while batch := cursor.fetchmany(protocol.PAGE_SIZE):
                    rows = [serialize(item) for item in batch]
                    try:
                        protocol.page(kind, rows)
                    except ValueError:
                        raise PilotError("unsupported_journal_metadata_for_monitor") from None
                    response = client.call("import_page", manifest["snapshot_key"], kind, rows)
                    if response.get("rows") != len(rows):
                        raise PilotError("monitor_page_not_confirmed")
        response = client.call("finish_import", manifest["snapshot_key"])
        if response.get("state") != "complete":
            raise PilotError("monitor_snapshot_not_completed")
        return {"state": "imported", "counts": counts, "snapshot_key": manifest["snapshot_key"]}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--watch", action="store_true", help="Repeat successful imports; stop on errors")
    parser.add_argument("--interval", type=int, default=10, help="Watch interval, 5–3600 seconds")
    args = parser.parse_args(argv)
    if not 5 <= args.interval <= 3600:
        parser.error("--interval must be between 5 and 3600 seconds")
    try:
        while True:
            settings = Settings.from_environment("ODOO20")
            identity(settings, 8020, "odoo20_migration")
            journal = Journal.from_environment()
            try:
                result = transfer(journal, MirrorClient(settings))
            finally:
                journal.close()
            print(json.dumps(result), flush=True)
            if not args.watch:
                return 0
            time.sleep(args.interval)
    except KeyboardInterrupt:
        print(json.dumps({"state": "stopped"}))
        return 0
    except (PilotError, ProbeFailure) as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}))
    except ValueError:
        print(json.dumps({"state": "blocked", "error": "invalid_or_missing_monitor_configuration"}))
    except Exception:
        print(json.dumps({"state": "blocked", "error": "journal_or_monitor_error"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
