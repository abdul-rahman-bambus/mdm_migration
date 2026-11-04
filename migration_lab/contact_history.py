"""Explicit 1–5 contact lab trial: preview first, then import historical chatter."""

import argparse
import base64
import importlib.util
import json
import os
import re
import xmlrpc.client
from pathlib import Path

from .journal import Journal, PilotError
from .pilot import identity
from .preflight import ProbeFailure, ReadOnlyRPC, Settings, classify

_spec = importlib.util.spec_from_file_location("bambus_contact_contract", Path(__file__).resolve().parents[1] / "addons/bambus_migration_control/contact_contract.py")
contract = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(contract)


class Source:
    """Odoo 12 reads only; bounded and no body, filenames or email in reports."""

    def __init__(self, settings):
        self.settings, self.rpc = settings, ReadOnlyRPC(settings, timeout=60)
        version = self.rpc.call("common", "version")
        if version.get("server_version_info", [None])[0] != 12:
            raise PilotError("contact_trial_requires_odoo12")
        self.uid = self.rpc.call("common", "authenticate", settings.database, settings.username, settings.password, {})
        if type(self.uid) is not int or self.uid <= 0:
            raise PilotError("source_authentication_failed")

    def read(self, model, domain, fields, cap):
        rows = self.rpc.call("object", "execute_kw", self.settings.database, self.uid, self.settings.password,
                             model, "search_read", [domain], {"fields": fields, "limit": cap + 1, "order": "id",
                                                             "context": {"active_test": False, "bin_size": False}})
        if not isinstance(rows, list) or len(rows) > cap or any(not isinstance(row, dict) for row in rows):
            raise PilotError("source_trial_limit_or_response_invalid")
        return rows

    def extract(self, contact_id):
        rows = self.read("res.partner", [["id", "=", contact_id]], [*(f for f in contract.FIELDS if f != "country_code"), "country_id", "parent_id"], 1)
        if not rows or rows[0].get("parent_id"):
            raise PilotError("trial_requires_existing_top_level_contact")
        if self.read("res.users", [["partner_id", "=", contact_id]], ["id"], 1):
            raise PilotError("trial_excludes_user_contacts")
        contact = rows[0]
        if contact.get("country_id"):
            countries = self.read("res.country", [["id", "=", contact["country_id"][0]]], ["code"], 1)
            if not countries:
                raise PilotError("source_country_inaccessible")
            contact["country_code"] = countries[0]["code"]
        else:
            contact["country_code"] = ""
        values = {key: contact[key] if key in {"is_company", "active"} else contact[key] or "" for key in contract.FIELDS}
        messages = self.read("mail.message", [["model", "=", "res.partner"], ["res_id", "=", contact_id]],
                             ["date", "author_id", "email_from", "subject", "body", "message_type", "subtype_id", "tracking_value_ids", "attachment_ids"], contract.MAX_MESSAGES)
        tracking_ids = sorted({n for row in messages for n in row["tracking_value_ids"]})
        tracking_fields = ["field_desc", "field_type", "old_value_char", "new_value_char", "old_value_text", "new_value_text",
                           "old_value_integer", "new_value_integer", "old_value_float", "new_value_float", "old_value_monetary", "new_value_monetary", "old_value_datetime", "new_value_datetime"]
        tracking = {r["id"]: r for r in self.read("mail.tracking.value", [["id", "in", tracking_ids]], tracking_fields, 500)} if tracking_ids else {}
        if set(tracking) != set(tracking_ids):
            raise PilotError("source_tracking_values_inaccessible")
        direct = self.read("ir.attachment", [["res_model", "=", "res.partner"], ["res_id", "=", contact_id]], ["id"], contract.MAX_ATTACHMENTS)
        attachment_ids = sorted({r["id"] for r in direct} | {n for row in messages for n in row["attachment_ids"]})
        if len(attachment_ids) > contract.MAX_ATTACHMENTS:
            raise PilotError("trial_attachment_count_exceeded")
        metadata = self.read("ir.attachment", [["id", "in", attachment_ids]], ["name", "type", "file_size"], contract.MAX_ATTACHMENTS) if attachment_ids else []
        if {r["id"] for r in metadata} != set(attachment_ids):
            raise PilotError("source_attachments_inaccessible")
        if any(r["type"] != "binary" or type(r["file_size"]) is not int or not 0 <= r["file_size"] <= contract.MAX_FILE for r in metadata):
            raise PilotError("trial_requires_bounded_binary_attachments")
        if sum(r["file_size"] for r in metadata) > contract.MAX_TOTAL:
            raise PilotError("trial_attachment_total_exceeded")
        attachments = []
        for meta in metadata:
            row = self.read("ir.attachment", [["id", "=", meta["id"]]], ["name", "datas", "file_size", "type"], 1)
            if not row or row[0]["type"] != "binary" or row[0]["file_size"] != meta["file_size"] or row[0]["name"] != meta["name"]:
                raise PilotError("source_attachment_changed_during_read")
            try:
                encoded = row[0]["datas"] or ""
                raw = base64.b64decode("".join(encoded.split()), validate=True)
            except (ValueError, TypeError):
                raise PilotError("invalid_source_attachment") from None
            if len(raw) != meta["file_size"]:
                raise PilotError("source_attachment_bytes_unavailable")
            attachments.append({"id": meta["id"], "name": meta["name"], "data": base64.b64encode(raw).decode()})

        def change(row):
            kind = row["field_type"]
            if kind not in {"char", "text", "selection", "many2one", "integer", "boolean", "float", "monetary", "date", "datetime"}:
                raise PilotError("unsupported_source_tracking_type")
            suffix = {"text": "text", "integer": "integer", "boolean": "integer",
                      "float": "float", "monetary": "monetary", "date": "datetime", "datetime": "datetime"}.get(kind, "char")
            def value(prefix):
                value = row[prefix + "_value_" + suffix]
                if kind == "boolean":
                    return str(bool(value))
                return "" if value is False or value is None else str(value)
            return {"field": row["field_desc"] or "Unknown field", "old": value("old"), "new": value("new")}

        data = {"version": contract.VERSION, "source_id": contact_id, "values": values, "attachments": attachments,
                "messages": [{"id": m["id"], "date": m["date"], "author": m["author_id"][1] if m["author_id"] else m["email_from"] or "",
                              "subject": m["subject"] or "", "body": m["body"] or "", "kind": m["message_type"],
                              "subtype": m["subtype_id"][1] if m["subtype_id"] else "",
                              "changes": [change(tracking[n]) for n in m["tracking_value_ids"]],
                              "attachments": sorted(m["attachment_ids"])} for m in messages]}
        try:
            return contract.validate(data)
        except (ValueError, TypeError):
            raise PilotError("unsupported_or_invalid_source_history") from None


class TrialRPC(ReadOnlyRPC):
    OPERATIONS = {"bambus_trial_info", "bambus_trial_preview", "bambus_trial_apply"}
    ERROR_CODES = {
        "invalid_contact_trial_payload", "invalid_trial_expected_items", "trial_target_missing_or_modified_requires_review",
        "trial_contact_marker_conflict", "trial_existing_contact_candidate_requires_review", "trial_target_restore_requires_review",
        "trial_history_restore_requires_review", "trial_source_history_changed_requires_review", "trial_source_history_removed_requires_review",
        "trial_attachment_bytes_changed", "trial_message_readback_failed", "trial_contact_readback_failed",
        "trial_country_requires_unique_mapping", "trial_company_classification_requires_mapping",
    }

    def failure_code(self, exc):
        if isinstance(exc, xmlrpc.client.Fault):
            # Inspect faults only to recognize code-owned labels; never emit a
            # remote traceback, custom-module error, record name or field value.
            # /xmlrpc/2 returns native UserError text as a bare faultString.
            candidates = [exc.faultString.strip()]
            if isinstance(exc.faultCode, str) and exc.faultCode.startswith("warning -- UserError\n\n"):
                candidates.append(exc.faultCode.removeprefix("warning -- UserError\n\n").strip())
            match = re.search(r"(?:odoo\.exceptions\.)?UserError: ([a-z0-9_]+)\s*$", exc.faultString)
            if match:
                candidates.append(match[1])
            for candidate in candidates:
                if candidate in self.ERROR_CODES:
                    return candidate
        return classify(exc)


class Target:
    def __init__(self, settings):
        self.settings, self.rpc = settings, TrialRPC(settings, timeout=120)
        version = self.rpc.call("common", "version")
        if version.get("server_version_info", [None])[0] != 20:
            raise PilotError("contact_trial_requires_odoo20")
        self.uid = self.rpc.call("common", "authenticate", settings.database, settings.username, settings.password, {})
        if type(self.uid) is not int or self.uid <= 0:
            raise PilotError("target_authentication_failed")
        try:
            info = self.call("bambus_trial_info")
        except ProbeFailure:
            raise PilotError("upgrade_tracking_addon_for_contact_trial") from None
        if info.get("version") != contract.VERSION or not info.get("lab_database"):
            raise PilotError("unsupported_target_trial_protocol_or_database")
        if info.get("can_apply") is not True:
            raise PilotError("assign_contact_trial_migrator_role")

    def call(self, method, *args):
        if method not in TrialRPC.OPERATIONS:
            raise PilotError("trial_method_not_allowed")
        result = self.rpc.call("object", "execute_kw", self.settings.database, self.uid, self.settings.password,
                               "res.partner", method, list(args), {})
        if not isinstance(result, dict):
            raise PilotError("invalid_trial_response")
        return result


def execute_contact(source, target, journal, contact_id, apply=False, approved_digest=None):
    namespace = contract.namespace(contact_id)
    with journal.lock(namespace):
        run = journal.start(namespace, "apply" if apply else "dry_run", contract.SOURCE, contract.TARGET, contract.VERSION)
        target_id = None
        payload_digest = None
        try:
            data = source.extract(contact_id)
            payload_digest = contract.digest(data)
            if apply and approved_digest != payload_digest:
                raise PilotError("source_changed_regenerate_trial_plan")
            mapping = journal.mapping(namespace)
            if mapping and (mapping["source_id"] != contact_id or mapping["mapping_version"] != contract.VERSION):
                raise PilotError("trial_journal_identity_conflict")
            expected = mapping["target_id"] if mapping else None
            expected_items = journal.connection.execute(
                "SELECT kind,source_id,target_id,payload_digest AS digest FROM bambus_pilot.history_items WHERE namespace=%s ORDER BY kind,source_id",
                (namespace,)).fetchall()
            preview = target.call("bambus_trial_preview", data, expected, expected_items)
            target_id = preview["target_id"] or None
            if not target_id and journal.has_intent(namespace, "load_intent", "create"):
                raise PilotError("unresolved_target_create_requires_review")
            counts = {k: preview[k] for k in ("messages", "attachments", "tracking_changes")}
            journal.event(run, "validated", source_id=contact_id, target_id=target_id,
                          fields=list(contract.FIELDS), operation=preview["operation"], **counts)
            if not apply:
                journal.finish(run, "dry_run", contact_id, target_id, payload_digest)
                return {"source_id": contact_id, "digest": payload_digest, "expected_target": target_id,
                        "operation": preview["operation"], **counts}
            journal.event(run, "load_intent", operation=preview["operation"], target_id=target_id)
            result = target.call("bambus_trial_apply", data, expected, expected_items)
            if result.get("state") != "reconciled" or type(result.get("target_id")) is not int:
                raise PilotError("trial_apply_not_reconciled")
            target_id = result["target_id"]
            # A second RPC verifies committed receipts and current target state.
            verified = target.call("bambus_trial_preview", data, target_id, expected_items)
            if verified.get("operation") != "no_change" or any(verified[k] != counts[k] for k in counts):
                raise PilotError("trial_committed_readback_failed")
            with journal.connection.transaction():
                for item in verified["items"]:
                    if type(item.get("target_id")) is not int:
                        raise PilotError("trial_history_mapping_missing")
                    old = journal.connection.execute("SELECT target_id,payload_digest FROM bambus_pilot.history_items WHERE namespace=%s AND kind=%s AND source_id=%s",
                                                     (namespace, item["kind"], item["source_id"])).fetchone()
                    if old and (old["target_id"] != item["target_id"] or old["payload_digest"] != item["digest"]):
                        raise PilotError("trial_history_mapping_conflict")
                    journal.connection.execute("INSERT INTO bambus_pilot.history_items (namespace,kind,source_id,target_id,payload_digest,last_run) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT (namespace,kind,source_id) DO UPDATE SET last_run=EXCLUDED.last_run",
                                               (namespace, item["kind"], item["source_id"], item["target_id"], item["digest"], run))
                journal.event(run, "loaded", target_id=target_id, **counts)
                journal.reconciled(namespace, run, contact_id, target_id, "bambus-pilot-target:" + namespace, contract.VERSION, payload_digest)
            return {"source_id": contact_id, "target_id": target_id, "state": "reconciled", "operation": result["operation"], **counts}
        except Exception as exc:
            code = str(exc) if isinstance(exc, (PilotError, ProbeFailure)) else "unexpected_contact_trial_error"
            journal.event(run, "failed", error_code=code)
            journal.finish(run, "failed", contact_id, target_id, payload_digest, code)
            raise PilotError(code) from None


def validate_plan(plan):
    if not isinstance(plan, dict) or set(plan) != {"version", "contacts"} or plan["version"] != contract.VERSION:
        raise PilotError("invalid_contact_trial_plan")
    rows = plan["contacts"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 5:
        raise PilotError("trial_requires_one_to_five_contact_ids")
    seen = set()
    for row in rows:
        if (not isinstance(row, dict) or set(row) != {"source_id", "digest", "expected_target", "operation", "messages", "attachments", "tracking_changes"}
                or type(row["source_id"]) is not int or not 0 < row["source_id"] < 2**31 or row["source_id"] in seen
                or not isinstance(row["digest"], str) or len(row["digest"]) != 64
                or any(c not in "0123456789abcdef" for c in row["digest"])
                or row["operation"] not in {"create", "update", "no_change"}
                or (row["expected_target"] is not None and (type(row["expected_target"]) is not int or not 0 < row["expected_target"] < 2**31))
                or any(type(row[k]) is not int or not 0 <= row[k] <= cap for k, cap in
                       (("messages", contract.MAX_MESSAGES), ("attachments", contract.MAX_ATTACHMENTS), ("tracking_changes", 500)))):
            raise PilotError("invalid_contact_trial_plan")
        seen.add(row["source_id"])
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["plan", "apply"])
    parser.add_argument("--lab-only", action="store_true", required=True)
    parser.add_argument("--contact-ids", nargs="+", type=int)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    if args.action == "plan" and (not args.contact_ids or not args.output or args.plan or args.apply):
        parser.error("plan requires --contact-ids and --output only")
    if args.action == "apply" and (not args.plan or not args.apply or args.contact_ids or args.output):
        parser.error("apply requires --plan and explicit --apply only")
    journal = None
    try:
        if args.action == "plan":
            if not 1 <= len(args.contact_ids) <= 5 or len(set(args.contact_ids)) != len(args.contact_ids) or any(not 0 < n < 2**31 for n in args.contact_ids):
                raise PilotError("trial_requires_one_to_five_unique_contact_ids")
            if args.output.exists():
                raise PilotError("use_new_plan_output_path")
            rows = [{"source_id": n} for n in args.contact_ids]
        else:
            if args.plan.stat().st_size > 16384:
                raise PilotError("trial_plan_too_large")
            rows = validate_plan(json.loads(args.plan.read_text()))
        src, dst = Settings.from_environment("ODOO12"), Settings.from_environment("ODOO20")
        identity(src, 8012, "odoo12_demo")
        identity(dst, 8020, "odoo20_migration")
        source, target = Source(src), Target(dst)
        journal = Journal.from_environment()
        if not journal.connection.execute("SELECT to_regclass('bambus_pilot.history_items') AS name").fetchone()["name"]:
            raise PilotError("initialize_journal_for_contact_history")
        results = []
        for row in rows:
            # Bind reviewed target ID too; a changed destination requires a fresh plan.
            mapping = journal.mapping(contract.namespace(row["source_id"]))
            if args.apply and row["expected_target"] is not None and (not mapping or mapping["target_id"] != row["expected_target"]):
                raise PilotError("trial_plan_target_mapping_changed")
            results.append(execute_contact(source, target, journal, row["source_id"], args.apply, row.get("digest")))
        if args.action == "plan":
            plan = {"version": contract.VERSION, "contacts": results}
            validate_plan(plan)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            with open(args.output, "x", opener=lambda path, flags: os.open(path, flags, 0o600)) as output:
                json.dump(plan, output, indent=2)
        print(json.dumps({"state": "reconciled" if args.apply else "preview", "contact_fields": list(contract.FIELDS),
                          "contacts": results}, indent=2))
        return 0
    except (PilotError, ProbeFailure) as exc:
        print(json.dumps({"state": "blocked", "error": str(exc)}))
    except (ValueError, OSError):
        print(json.dumps({"state": "blocked", "error": "invalid_trial_plan_or_configuration"}))
    except KeyboardInterrupt:
        print(json.dumps({"state": "interrupted", "next": "review_journal_and_retry_same_plan"}))
    except Exception:
        print(json.dumps({"state": "blocked", "error": "journal_or_contact_trial_error"}))
    finally:
        if journal:
            journal.close()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
