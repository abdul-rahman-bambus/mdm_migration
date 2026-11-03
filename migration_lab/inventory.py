"""Read-only installed-module and dependent-model inventory for the existing lab."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from .preflight import ProbeFailure, ReadOnlyRPC, Settings

DEPENDENCIES = (
    "product.category", "uom.uom", "uom.category", "product.attribute",
    "product.attribute.value", "product.template.attribute.line",
    "product.template.attribute.value", "res.country", "res.country.state",
    "res.partner.category", "res.company", "ir.attachment", "mail.message",
    "mail.followers", "mail.activity",
)
CORE_MODELS = ("product.template", "product.product", "res.partner")
ATTRIBUTES = ["string", "type", "required", "readonly", "relation", "selection",
              "store", "compute", "related", "company_dependent", "model_field"]


def collect(settings, expected_major, timeout=10, max_pages=100):
    rpc = ReadOnlyRPC(settings, timeout)
    result = {"state": "blocked", "models": {}}
    try:
        version = rpc.call("common", "version")
        info = version.get("server_version_info") if isinstance(version, dict) else None
        if not isinstance(info, (list, tuple)) or not info or info[0] != expected_major:
            raise ProbeFailure("unexpected_server_version")
        result["reported_major"] = info[0]
        uid = rpc.call("common", "authenticate", settings.database, settings.username, settings.password, {})
        if type(uid) is not int or uid <= 0:
            raise ProbeFailure("authentication_failed")
    except ProbeFailure as exc:
        result["error_category"] = str(exc)
        return result

    def execute(model, operation, args, kwargs):
        return rpc.call("object", "execute_kw", settings.database, uid, settings.password,
                        model, operation, args, kwargs)

    modules, seen = [], set()
    try:
        for page in range(max_pages):
            rows = execute("ir.module.module", "search_read", [[("state", "=", "installed")]],
                           {"fields": ["id", "name"], "limit": 100, "offset": page * 100, "order": "id"})
            if not isinstance(rows, list) or len(rows) > 100:
                raise ProbeFailure("invalid_module_response")
            for row in rows:
                if (not isinstance(row, dict) or type(row.get("id")) is not int
                        or not isinstance(row.get("name"), str) or row["id"] in seen):
                    raise ProbeFailure("invalid_or_repeated_module_page")
                seen.add(row["id"])
                modules.append(row["name"])
            if len(rows) < 100:
                result["installed_modules"] = {"state": "passed", "names": sorted(modules)}
                break
        else:
            raise ProbeFailure("module_page_limit_exceeded")
    except ProbeFailure as exc:
        result["installed_modules"] = {"state": "failed", "error_category": str(exc),
                                       "names_observed_incomplete": sorted(modules)}

    for model in CORE_MODELS + DEPENDENCIES:
        try:
            fields = execute(model, "fields_get", [], {"attributes": ATTRIBUTES})
            if not isinstance(fields, dict) or not fields or any(
                not isinstance(meta, dict) or not isinstance(meta.get("type"), str) for meta in fields.values()
            ):
                raise ProbeFailure("invalid_field_metadata")
            result["models"][model] = {"state": "passed", "fields": fields}
        except ProbeFailure as exc:
            result["models"][model] = {"state": "failed", "error_category": str(exc)}
            # Registry visibility narrows the diagnosis; it does not prove absence
            # for users whose metadata permissions may be restricted.
            try:
                rows = execute("ir.model", "search_read", [[("model", "=", model)]],
                               {"fields": ["model"], "limit": 1})
                if rows == []:
                    visibility = "not_visible_in_registry"
                elif (isinstance(rows, list) and len(rows) == 1 and isinstance(rows[0], dict)
                      and rows[0].get("model") == model):
                    visibility = "visible_in_registry"
                else:
                    visibility = "invalid_registry_response"
                result["models"][model]["registry_visibility"] = visibility
            except ProbeFailure:
                result["models"][model]["registry_visibility"] = "registry_query_failed"
    complete = (result["installed_modules"]["state"] == "passed"
                and all(item["state"] == "passed" for item in result["models"].values()))
    result["state"] = "passed" if complete else "partial"
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory; existing results are preserved")
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 120:
        parser.error("--timeout must be greater than zero and at most 120 seconds")
    # Fail before requests when the output location already exists.
    try:
        args.output_dir.mkdir(parents=True, exist_ok=False)
    except OSError:
        parser.exit(1, "Choose a new writable output directory.\n")
    report = {"format_version": 2, "migration_ready": False,
              "captured_at": datetime.now(timezone.utc).isoformat(), "instances": {}}
    for prefix, major in (("ODOO12", 12), ("ODOO20", 20)):
        try:
            settings = Settings.from_environment(prefix)
        except ValueError as exc:
            report["instances"][prefix] = {"state": "blocked", "configuration_error": str(exc)}
        else:
            report["instances"][prefix] = collect(settings, major, args.timeout)
    output = args.output_dir / "inventory.json"
    output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # Export core metadata from the same collection run, avoiding mixed snapshots.
    if all(all(instance.get("models", {}).get(model, {}).get("state") == "passed"
               for model in CORE_MODELS) for instance in report["instances"].values()):
        snapshot = {prefix: {model: instance["models"][model]["fields"] for model in CORE_MODELS}
                    for prefix, instance in report["instances"].items()}
        (args.output_dir / "schema.json").write_text(
            json.dumps(snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {output}. Missing models and access failures remain explicit in this report.")
    return 0 if all(item["state"] == "passed" for item in report["instances"].values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
