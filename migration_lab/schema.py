"""Conservative offline schema comparison; never approves migration mappings."""

import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

RELATIONS = {"many2one", "one2many", "many2many", "reference", "many2one_reference"}
SYSTEM_FIELDS = {"id", "display_name", "__last_update", "create_uid", "create_date", "write_uid", "write_date"}
BOOLEAN_ATTRIBUTES = ("readonly", "required", "store", "company_dependent")


def validate_snapshot(data):
    if not isinstance(data, dict):
        raise ValueError("Snapshot must be an object")
    for side in ("ODOO12", "ODOO20"):
        models = data.get(side)
        if not isinstance(models, dict) or not models:
            raise ValueError(f"Missing or empty {side} models")
        for model, fields in models.items():
            if not isinstance(fields, dict) or not fields or "error_type" in fields:
                raise ValueError(f"Incomplete model metadata: {side}.{model}")
            for name, meta in fields.items():
                if not isinstance(meta, dict) or not isinstance(meta.get("type"), str):
                    raise ValueError(f"Incomplete field metadata: {side}.{model}.{name}")
                for key in BOOLEAN_ATTRIBUTES:
                    if key in meta and not (type(meta[key]) is bool or
                                            (type(meta[key]) is int and meta[key] in (0, 1))):
                        raise ValueError(f"Invalid {key} metadata: {side}.{model}.{name}")
                if "selection" in meta and meta["selection"] is not None:
                    items = meta["selection"]
                    if not isinstance(items, list) or any(
                        not isinstance(item, (list, tuple)) or len(item) != 2
                        or type(item[0]) not in (str, int) for item in items
                    ):
                        raise ValueError(f"Invalid selection metadata: {side}.{model}.{name}")
                    if len({item[0] for item in items}) != len(items):
                        raise ValueError(f"Duplicate selection keys: {side}.{model}.{name}")


def selection_changes(source, target):
    if source.get("type") != "selection" or target.get("type") != "selection":
        return {}
    if source.get("selection") is None or target.get("selection") is None:
        return {"selection_metadata_unknown": True}
    old, new = dict(source["selection"]), dict(target["selection"])
    order = lambda values: sorted(values, key=lambda value: (type(value).__name__, str(value)))
    return {"selection_keys_removed": order(old.keys() - new.keys()),
            "selection_keys_added": order(new.keys() - old.keys()),
            "selection_labels_changed": order(key for key in old.keys() & new.keys() if old[key] != new[key])}


def compare(data):
    validate_snapshot(data)
    result = {"format_version": 1, "migration_ready": False, "mapping_status": "review_required", "models": {}}
    for model in sorted(data["ODOO12"].keys() | data["ODOO20"].keys()):
        source = data["ODOO12"].get(model, {})
        target = data["ODOO20"].get(model, {})
        rows = []
        for name in sorted(source.keys() | target.keys()):
            def normalized(meta):
                if meta is None:
                    return None
                return {key: bool(value) if key in BOOLEAN_ATTRIBUTES else value
                        for key, value in meta.items()}

            old, new = normalized(source.get(name)), normalized(target.get(name))
            flags = []
            details = {}
            for side, raw in (("source", source.get(name)), ("target", target.get(name))):
                if raw is not None and any(type(raw.get(key)) is int for key in BOOLEAN_ATTRIBUTES):
                    flags.append(f"{side}_boolean_metadata_normalized")
            if old is None:
                flags.append("target_only")
            elif new is None:
                flags.append("source_only")
            else:
                for key in ("type", "relation", "required", "readonly", "store", "company_dependent", "related", "model_field"):
                    if old.get(key) != new.get(key):
                        flags.append(f"{key}_changed")
                        details[key] = {"source": old.get(key), "target": new.get(key)}
                details.update(selection_changes(old, new))
                for key, values in details.items():
                    if key.startswith("selection_") and values:
                        flags.append(key)
            if new is not None:
                if new.get("readonly") is True:
                    flags.append("target_readonly")
                elif "readonly" not in new:
                    flags.append("target_readonly_unknown")
                if new.get("required") is True and (old is None or old.get("required") is not True):
                    flags.append("new_required_field")
                if new.get("type") in RELATIONS:
                    flags.append("relational_mapping_required")
                if new.get("type") in {"reference", "many2one_reference"}:
                    flags.append("polymorphic_reference_review")
                if new.get("related"):
                    flags.append("related_field_review")
                if new.get("store") is False:
                    flags.append("nonstored_field_review")
                if new.get("company_dependent") is True:
                    flags.append("company_context_required")
                if new.get("type") == "binary":
                    flags.append("binary_validation_required")
                if "compute" not in new:
                    flags.append("computed_status_unknown")
                elif new["compute"]:
                    flags.append("computed_field_review")
            if name in SYSTEM_FIELDS:
                flags.append("system_field_do_not_copy")
            # 'Candidate' describes only matching structural metadata.
            blockers = {"type_changed", "relation_changed", "target_readonly", "target_readonly_unknown",
                        "source_only", "target_only", "system_field_do_not_copy", "selection_keys_removed",
                        "selection_keys_added", "selection_metadata_unknown", "relational_mapping_required",
                        "related_field_review", "nonstored_field_review", "company_context_required",
                        "binary_validation_required", "computed_field_review"}
            if old is not None and new is not None and not blockers.intersection(flags):
                flags.append("same_name_scalar_candidate")
            rows.append({"field": name, "source": old, "target": new,
                         "flags": flags, "differences": details, "decision": "review_required",
                         "api_writeability": "not_verified"})
        counts = Counter(flag for row in rows for flag in row["flags"])
        result["models"][model] = {"source_field_count": len(source), "target_field_count": len(target),
                                   "union_field_count": len(rows), "flag_counts": dict(sorted(counts.items())),
                                   "fields": rows}
    return result


def markdown(report, input_name, digest):
    lines = ["# Observed schema comparison", "", f"Input: `{input_name}`; SHA-256: `{digest}`.", "",
             "Generated offline from user-local metadata. No API writes, mapping approvals or migration occurred.",
             "Computed status and API writeability remain unknown where not supplied. Source-only fields may",
             "reflect installed-module differences; absence does not prove a version-wide removal.", "",
             "Selection keys are compared independently of labels and ordering. Every field appears below.", ""]
    escape = lambda value: str(value).replace("|", "\\|").replace("\n", " ")
    for model, entry in report["models"].items():
        lines += [f"## {model}", "", f"Source fields: {entry['source_field_count']}; target fields: {entry['target_field_count']}.", "",
                  "| Field | Source type | Target type | Review flags |", "|---|---|---|---|"]
        for row in entry["fields"]:
            lines.append("| " + " | ".join(escape(item) for item in (
                row["field"], (row["source"] or {}).get("type", "absent"),
                (row["target"] or {}).get("type", "absent"), ", ".join(row["flags"]))) + " |")
        lines.append("")
    return "\n".join(lines)


def mapping_draft(report):
    return {"format_version": 1, "mapping_version": "odoo12-20.lab.v1-draft",
            "state": "unapproved", "input_sha256": report["input_sha256"],
            "models": {model: {
                "source_fields": [{"source_field": row["field"],
                                   "same_name_target_candidate": row["field"] if row["target"] is not None else None,
                                   "approved_target": None, "transformation": None,
                                   "decision": "unresolved", "review_flags": row["flags"]}
                                  for row in item["fields"] if row["source"] is not None],
                "target_only_fields": [{"field": row["field"], "required": row["target"].get("required"),
                                        "decision": "unresolved"}
                                       for row in item["fields"] if row["source"] is None],
            } for model, item in report["models"].items()}}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True, help="New directory; existing output is never overwritten")
    args = parser.parse_args(argv)
    try:
        payload = args.snapshot.read_bytes()
        report = compare(json.loads(payload))
        digest = hashlib.sha256(payload).hexdigest()
        report["input_sha256"] = digest
        args.output_dir.mkdir(parents=True, exist_ok=False)
    except (OSError, ValueError) as exc:
        parser.exit(1, f"Comparison failed: {exc}\n")
    (args.output_dir / "comparison.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")
    (args.output_dir / "comparison.md").write_text(markdown(report, args.snapshot.name, digest), encoding="utf-8")
    (args.output_dir / "mapping-draft.json").write_text(json.dumps(mapping_draft(report), indent=2) + "\n")
    with (args.output_dir / "fields.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["model", "field", "source_type", "target_type", "flags", "decision", "api_writeability"])
        for model, entry in report["models"].items():
            for row in entry["fields"]:
                writer.writerow([model, row["field"], (row["source"] or {}).get("type", ""),
                                 (row["target"] or {}).get("type", ""), ";".join(row["flags"]),
                                 row["decision"], row["api_writeability"]])
    print(f"Compared {len(report['models'])} models. Reports: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
