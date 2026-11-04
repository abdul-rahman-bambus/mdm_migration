"""Shared, dependency-free monitor import contract. No business values accepted."""

from datetime import datetime, timezone
import re
import uuid

MAX_ROWS = 10000
PAGE_SIZE = 100
RUN_STATES = {"running", "seeded", "source_updated", "dry_run", "reconciled", "failed"}
OPERATIONS = {"seed", "change-source", "dry_run", "apply"}
EVENT_STATES = {"pending", "source_defaults_validated", "source_create_intent", "source_update_intent",
                "source_updated", "seeded", "extracted", "validated", "dry_run", "load_intent", "loaded",
                "reconciliation_failed", "reconciled", "failed"}
SCHEMAS = {
    "runs": {"id", "namespace", "operation", "source_identity", "target_identity", "mapping_version", "state",
             "source_id", "target_id", "payload_digest", "error_code", "started_at", "finished_at"},
    "events": {"id", "run_id", "state", "details", "created_at"},
    "mappings": {"namespace", "source_model", "source_id", "target_model", "target_id", "marker",
                 "mapping_version", "payload_digest", "last_run", "state", "updated_at"},
}


class InvalidPayload(ValueError):
    pass


def require(condition):
    if not condition:
        raise InvalidPayload("invalid_monitor_payload")


def uid(value):
    require(isinstance(value, str))
    try:
        require(str(uuid.UUID(value)) == value)
    except (ValueError, AttributeError):
        raise InvalidPayload("invalid_monitor_uuid") from None
    return value


def text(value, pattern=r"[A-Za-z0-9_:/.-]{1,256}"):
    require(isinstance(value, str) and re.fullmatch(pattern, value) is not None)
    return value


def digest(value):
    return text(value, r"[0-9a-f]{64}")


def number(value, nullable=False):
    if nullable and value is None:
        return value
    require(type(value) is int and 0 < value <= 2147483647)
    return value


def timestamp(value, nullable=False):
    if nullable and value is None:
        return None
    require(isinstance(value, str))
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(parsed.tzinfo is not None)
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)
    except (ValueError, OverflowError):
        raise InvalidPayload("invalid_monitor_timestamp") from None


def manifest(data):
    require(isinstance(data, dict) and set(data) == {"journal_key", "revision", "snapshot_key", "captured_at", "counts"})
    uid(data["journal_key"])
    digest(data["revision"])
    uid(data["snapshot_key"])
    require(data["snapshot_key"] == str(uuid.uuid5(uuid.UUID(data["journal_key"]), data["revision"])))
    timestamp(data["captured_at"])
    require(isinstance(data["counts"], dict) and set(data["counts"]) == set(SCHEMAS))
    require(all(type(n) is int and 0 <= n <= MAX_ROWS for n in data["counts"].values()))
    return data


def row(kind, data):
    require(isinstance(kind, str) and kind in SCHEMAS and isinstance(data, dict) and set(data) == SCHEMAS[kind])
    if kind == "runs":
        uid(data["id"])
        digest(data["namespace"])
        require(isinstance(data["operation"], str) and data["operation"] in OPERATIONS
                and isinstance(data["state"], str) and data["state"] in RUN_STATES)
        for key in ("source_identity", "target_identity", "mapping_version"):
            text(data[key])
        for key in ("source_id", "target_id"):
            number(data[key], nullable=True)
        if data["payload_digest"] is not None:
            digest(data["payload_digest"])
        if data["error_code"] is not None:
            text(data["error_code"], r"[A-Za-z_][A-Za-z0-9_]{0,127}")
        start = timestamp(data["started_at"])
        end = timestamp(data["finished_at"], nullable=True)
        require(end is None or end >= start)
    elif kind == "events":
        number(data["id"])
        uid(data["run_id"])
        require(isinstance(data["state"], str) and data["state"] in EVENT_STATES)
        timestamp(data["created_at"])
        details = data["details"]
        require(isinstance(details, dict) and set(details) <= {"fields", "server_default_fields", "operation", "source_id", "target_id", "error_code", "messages", "attachments", "tracking_changes"})
        for key, value in details.items():
            if key in {"messages", "attachments", "tracking_changes"}:
                require(type(value) is int and 0 <= value <= MAX_ROWS)
            elif key in {"fields", "server_default_fields"}:
                require(isinstance(value, list) and len(value) <= 100)
                for name in value:
                    text(name, r"[A-Za-z_][A-Za-z0-9_]{0,127}")
            elif key in {"source_id", "target_id"}:
                number(value, nullable=True)
            elif key == "operation":
                require(isinstance(value, str) and value in {"create", "update", "no_change"})
            else:
                text(value, r"[A-Za-z_][A-Za-z0-9_]{0,127}")
    else:
        digest(data["namespace"])
        for key in ("source_model", "target_model"):
            require(data[key] == "res.partner")
        for key in ("source_id", "target_id"):
            number(data[key])
        text(data["marker"], r"bambus-pilot-target:[0-9a-f]{64}")
        text(data["mapping_version"])
        digest(data["payload_digest"])
        uid(data["last_run"])
        require(data["state"] == "reconciled")
        timestamp(data["updated_at"])
    return data


def page(kind, rows):
    require(isinstance(kind, str) and kind in SCHEMAS and isinstance(rows, list) and 0 < len(rows) <= PAGE_SIZE)
    for item in rows:
        row(kind, item)
    return rows
