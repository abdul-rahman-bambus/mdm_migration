"""Synthetic contact pilot; an explicitly applied write is always reconciled."""

import argparse
import hashlib
import json
import re
import urllib.parse
from pathlib import Path

from .journal import Journal, PilotError
from .preflight import ProbeFailure, ReadOnlyRPC, Settings

VERSION = "synthetic-contact-v1"
FIELDS = ("name", "email", "phone")
CONTEXT = {"active_test": False, "tracking_disable": True, "mail_create_nosubscribe": True,
           "mail_create_nolog": True, "mail_notify_force_send": False}


class PilotRPC(ReadOnlyRPC):
    # The assessment client itself remains read-only.
    OPERATIONS = ReadOnlyRPC.OPERATIONS | {"create", "write"}


class PartnerAPI:
    def __init__(self, settings, major, writable=False):
        self.settings, self.major, self.writable = settings, major, writable
        self.rpc = PilotRPC(settings) if writable else ReadOnlyRPC(settings)
        version = self.rpc.call("common", "version")
        info = version.get("server_version_info") if isinstance(version, dict) else None
        if not isinstance(info, (list, tuple)) or not info or info[0] != major:
            raise PilotError("unexpected_server_version")
        self.uid = self.rpc.call("common", "authenticate", settings.database, settings.username, settings.password, {})
        if type(self.uid) is not int or self.uid <= 0:
            raise PilotError("authentication_failed")
        metadata = self.execute("fields_get", [], {"attributes": ["type", "readonly", "required"]})
        if not isinstance(metadata, dict):
            raise PilotError("invalid_partner_metadata")
        for name in FIELDS + ("ref",):
            meta = metadata.get(name, {})
            if meta.get("type") != "char" or meta.get("readonly") not in (False, 0):
                raise PilotError("unsupported_pilot_field_metadata")
        if any(meta.get("required") and not meta.get("readonly")
                            for name, meta in metadata.items() if name not in FIELDS + ("ref",)):
            raise PilotError("extra_required_partner_field_requires_mapping")

    def execute(self, method, args, kwargs=None):
        return self.rpc.call("object", "execute_kw", self.settings.database, self.uid,
                             self.settings.password, "res.partner", method, args,
                             {"context": CONTEXT, **(kwargs or {})})

    def find(self, marker):
        rows = self.execute("search_read", [[["ref", "=", marker]]],
                            {"fields": ["id", "ref", *FIELDS], "limit": 2, "order": "id"})
        if not isinstance(rows, list) or len(rows) > 1:
            raise PilotError("duplicate_or_invalid_pilot_marker")
        if rows and (not isinstance(rows[0], dict) or type(rows[0].get("id")) is not int):
            raise PilotError("invalid_partner_response")
        return rows[0] if rows else None

    def create(self, values):
        if not self.writable or set(values) != set(FIELDS + ("ref",)):
            raise PilotError("pilot_write_scope_violation")
        result = self.execute("create", [values])
        if type(result) is not int or result <= 0:
            raise PilotError("invalid_create_response")
        return result

    def write(self, record_id, values):
        if not self.writable or not values or not set(values) <= set(FIELDS):
            raise PilotError("pilot_write_scope_violation")
        if self.execute("write", [[record_id], values]) is not True:
            raise PilotError("write_not_confirmed")


def identity(settings, expected_port, expected_database):
    parts = urllib.parse.urlsplit(settings.url)
    if (parts.scheme != "http" or parts.hostname not in {"localhost", "127.0.0.1", "::1"}
            or parts.port != expected_port or parts.path not in ("", "/")
            or settings.database != expected_database):
        raise PilotError("pilot_requires_documented_loopback_lab")
    return f"loopback:{expected_port}/{expected_database}/res.partner"


def specification(label, source_identity, target_identity):
    if re.fullmatch(r"[a-z0-9][a-z0-9-]{0,31}", label) is None:
        raise PilotError("invalid_pilot_label")
    namespace = hashlib.sha256(json.dumps([source_identity, target_identity, label, VERSION]).encode()).hexdigest()
    return {"namespace": namespace, "source_marker": "bambus-pilot-source:" + label,
            "target_marker": "bambus-pilot-target:" + namespace,
            "name": "Bambus migration pilot " + label,
            "email": "bambus-pilot-" + label + "@example.invalid"}


def synthetic(row, spec, marker):
    if (not row or row.get("ref") != marker or row.get("name") != spec["name"]
            or row.get("email") != spec["email"]
            or re.fullmatch(r"\+120255501[0-9]{2}", row.get("phone") or "") is None):
        raise PilotError("record_is_not_the_expected_synthetic_contact")


def payload(row):
    return {name: row.get(name) or "" for name in FIELDS}


def migrate(source, target, journal, spec, source_identity, target_identity, action="sync", apply=False, phone=None):
    try:
        config = json.loads((Path(__file__).resolve().parents[1] / "mappings/synthetic-contact-v1.json").read_text())
    except (OSError, ValueError):
        raise PilotError("pilot_mapping_manifest_unavailable") from None
    if config != {"mapping_version": VERSION, "scope": "synthetic-lab-only", "source_model": "res.partner",
                  "target_model": "res.partner", "fields": [
                      {"source": name, "target": name, "transform": "identity"} for name in FIELDS]}:
        raise PilotError("pilot_mapping_manifest_requires_review")
    namespace = spec["namespace"]
    with journal.lock(namespace):
        run_id = journal.start(namespace, action if action != "sync" else ("apply" if apply else "dry_run"),
                               source_identity, target_identity, VERSION)
        source_id = target_id = None
        digest = None
        try:
            row = source.find(spec["source_marker"])
            if action == "seed" and row is None:
                if journal.has_intent(namespace, "source_create_intent"):
                    raise PilotError("unresolved_source_create_requires_review")
                journal.event(run_id, "source_create_intent")
                source.create({"ref": spec["source_marker"], "name": spec["name"],
                               "email": spec["email"], "phone": "+12025550100"})
                row = source.find(spec["source_marker"])
            synthetic(row, spec, spec["source_marker"])
            source_id = row["id"]
            journal.event(run_id, "extracted", source_id=source_id)
            if action in {"seed", "change-source"}:
                if action == "change-source":
                    if re.fullmatch(r"\+120255501[0-9]{2}", phone or "") is None:
                        raise PilotError("phone_must_be_reserved_synthetic_number")
                    journal.event(run_id, "source_update_intent", fields=["phone"])
                    source.write(source_id, {"phone": phone})
                    row = source.find(spec["source_marker"])
                    synthetic(row, spec, spec["source_marker"])
                    if row["phone"] != phone:
                        raise PilotError("source_update_reconciliation_failed")
                state = "seeded" if action == "seed" else "source_updated"
                journal.event(run_id, state, source_id=source_id)
                journal.finish(run_id, state, source_id)
                return {"run_id": run_id, "state": state, "source_id": source_id}

            mapping = journal.mapping(namespace)
            if mapping and (mapping["source_id"] != source_id or mapping["mapping_version"] != VERSION
                            or mapping["marker"] != spec["target_marker"]):
                raise PilotError("source_identity_or_mapping_version_changed")
            destination = target.find(spec["target_marker"])
            if destination:
                synthetic(destination, spec, spec["target_marker"])
                target_id = destination["id"]
            if mapping and (not destination or target_id != mapping["target_id"]):
                raise PilotError("target_restore_or_mapping_conflict_requires_review")
            if destination is None and journal.has_intent(namespace, "load_intent", "create"):
                # A missing marker may mean a rejected write, a restore or hidden
                # records. Never interpret an ambiguous absence as permission to
                # create again. Visible committed markers can still be recovered.
                raise PilotError("unresolved_target_create_requires_review")
            values = payload(row)
            digest = hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()
            changed = list(FIELDS) if not destination else [key for key in FIELDS if values[key] != payload(destination)[key]]
            operation = "create" if destination is None else ("update" if changed else "no_change")
            journal.event(run_id, "validated", operation=operation, fields=changed)
            if not apply:
                journal.event(run_id, "dry_run", operation=operation, fields=changed)
                journal.finish(run_id, "dry_run", source_id, target_id, digest)
                return {"run_id": run_id, "state": "dry_run", "proposed_operation": operation,
                        "fields": changed, "source_id": source_id, "target_id": target_id}
            journal.event(run_id, "load_intent", operation=operation, target_id=target_id)
            if operation == "create":
                target_id = target.create({"ref": spec["target_marker"], **values})
            elif operation == "update":
                target.write(target_id, {key: values[key] for key in changed})
            journal.event(run_id, "loaded", target_id=target_id)
            # Re-query the stable marker rather than trusting the write response.
            actual = target.find(spec["target_marker"])
            synthetic(actual, spec, spec["target_marker"])
            mismatches = [name for name in FIELDS if payload(actual)[name] != values[name]]
            if actual["id"] != target_id or mismatches:
                journal.event(run_id, "reconciliation_failed", fields=mismatches)
                raise PilotError("target_reconciliation_failed")
            journal.reconciled(namespace, run_id, source_id, target_id, spec["target_marker"], VERSION, digest)
            return {"run_id": run_id, "state": "reconciled", "operation": operation,
                    "source_id": source_id, "target_id": target_id, "fields_verified": list(FIELDS)}
        except (PilotError, ProbeFailure) as exc:
            journal.event(run_id, "failed", error_code=str(exc))
            journal.finish(run_id, "failed", source_id, target_id, digest, str(exc))
            raise
        except Exception:
            journal.event(run_id, "failed", error_code="unexpected_pilot_error")
            journal.finish(run_id, "failed", source_id, target_id, digest, "unexpected_pilot_error")
            raise PilotError("unexpected_pilot_error") from None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["init-journal", "seed", "sync", "change-source", "status"])
    parser.add_argument("--lab-only", action="store_true", required=True)
    parser.add_argument("--label", default="smoke-001")
    parser.add_argument("--apply", action="store_true", help="Authorize the reviewed synthetic contact write to the target")
    parser.add_argument("--phone", help="change-source only; reserved +12025550100 through +12025550199")
    args = parser.parse_args(argv)
    if args.apply and args.action != "sync":
        parser.error("--apply is only valid for sync")
    if (args.phone is not None) != (args.action == "change-source"):
        parser.error("--phone is required only for change-source")
    journal = None
    try:
        journal = Journal.from_environment()
        if args.action == "init-journal":
            journal.initialize()
            result = {"state": "journal_initialized"}
        else:
            source_settings = Settings.from_environment("ODOO12")
            target_settings = Settings.from_environment("ODOO20")
            source_identity = identity(source_settings, 8012, "odoo12_demo")
            target_identity = identity(target_settings, 8020, "odoo20_migration")
            spec = specification(args.label, source_identity, target_identity)
            if args.action == "status":
                result = journal.status(spec["namespace"])
            else:
                # Authenticate and validate BOTH endpoints before any source/target write.
                source = PartnerAPI(source_settings, 12, writable=args.action in {"seed", "change-source"})
                target = PartnerAPI(target_settings, 20, writable=args.action == "sync" and args.apply)
                result = migrate(source, target, journal, spec, source_identity, target_identity,
                                 args.action, args.apply, args.phone)
        print(json.dumps(result, indent=2, default=str))
        return 0
    except ValueError:
        print(json.dumps({"state": "blocked", "error": "invalid_or_missing_connection_configuration"}))
    except (PilotError, ProbeFailure) as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}))
    except KeyboardInterrupt:
        print(json.dumps({"state": "interrupted", "next": "retry_same_label_after_reviewing_status"}))
    except Exception:
        print(json.dumps({"state": "failed", "error": "journal_or_unexpected_error"}))
    finally:
        if journal:
            journal.close()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
