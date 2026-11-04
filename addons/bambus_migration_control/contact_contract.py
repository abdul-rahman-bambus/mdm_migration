"""Bounded, versioned contact-history trial contract shared by host and addon."""

import base64
import hashlib
import json
import re
from datetime import datetime

VERSION = "contact-history-v1"
SOURCE = "loopback:8012/odoo12_demo/res.partner"
TARGET = "loopback:8020/odoo20_migration/res.partner"
FIELDS = ("name", "email", "phone", "is_company", "active", "vat", "country_code")
MAX_MESSAGES = 100
MAX_ATTACHMENTS = 20
MAX_FILE = 2 * 1024 * 1024
MAX_TOTAL = 8 * 1024 * 1024


def require(condition):
    if not condition:
        raise ValueError("invalid_contact_trial_payload")


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=True, separators=(",", ":")).encode()).hexdigest()


def namespace(source_id):
    return digest([SOURCE, TARGET, VERSION, source_id])


def number(value):
    require(type(value) is int and 0 < value < 2**31)
    return value


def text(value, limit=4096):
    require(isinstance(value, str) and len(value) <= limit and "\x00" not in value)
    return value


def validate(data):
    require(isinstance(data, dict) and set(data) == {"version", "source_id", "values", "messages", "attachments"})
    require(data["version"] == VERSION)
    number(data["source_id"])
    require(isinstance(data["values"], dict) and set(data["values"]) == set(FIELDS))
    for key, value in data["values"].items():
        if key in {"is_company", "active"}:
            require(type(value) is bool)
        else:
            text(value)
    require(bool(data["values"]["name"].strip()))
    require(data["values"]["country_code"] == "" or re.fullmatch(r"[A-Z]{2}", data["values"]["country_code"]) is not None)
    require(isinstance(data["attachments"], list) and len(data["attachments"]) <= MAX_ATTACHMENTS)
    require(isinstance(data["messages"], list) and len(data["messages"]) <= MAX_MESSAGES)
    attachment_ids, message_ids, total = set(), set(), 0
    for attachment in data["attachments"]:
        require(isinstance(attachment, dict) and set(attachment) == {"id", "name", "data"})
        number(attachment["id"])
        require(attachment["id"] not in attachment_ids)
        attachment_ids.add(attachment["id"])
        text(attachment["name"], 255)
        require(bool(attachment["name"]))
        text(attachment["data"], ((MAX_FILE + 2) // 3) * 4)
        try:
            content = base64.b64decode(attachment["data"], validate=True)
        except (ValueError, TypeError):
            raise ValueError("invalid_attachment_base64") from None
        require(len(content) <= MAX_FILE)
        total += len(content)
    require(total <= MAX_TOTAL)
    for message in data["messages"]:
        require(isinstance(message, dict) and set(message) == {"id", "date", "author", "subject", "body", "kind", "subtype", "changes", "attachments"})
        number(message["id"])
        require(message["id"] not in message_ids)
        message_ids.add(message["id"])
        text(message["date"], 19)
        require(re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", message["date"]) is not None)
        datetime.strptime(message["date"], "%Y-%m-%d %H:%M:%S")
        for key in ("author", "subject", "kind", "subtype"):
            text(message[key])
        require(message["kind"] in {"comment", "email", "notification"})
        text(message["body"], 65536)
        require(isinstance(message["attachments"], list) and len(message["attachments"]) == len(set(message["attachments"])))
        for item in message["attachments"]:
            number(item)
            require(item in attachment_ids)
        require(isinstance(message["changes"], list) and len(message["changes"]) <= 50)
        for change in message["changes"]:
            require(isinstance(change, dict) and set(change) == {"field", "old", "new"})
            for value in change.values():
                text(value)
    return data
