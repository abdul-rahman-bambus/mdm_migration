"""Standalone, read-only metadata export for execution beside the local lab."""

import json
import os
import socket
import xmlrpc.client
from datetime import datetime, timezone
from pathlib import Path


def collect():
    report = {}
    for prefix in ("ODOO12", "ODOO20"):
        result = {"models": {}}
        report[prefix] = result
        try:
            url, db, user, password = [os.environ[f"{prefix}_{n}"]
                                      for n in ("URL", "DB", "USERNAME", "PASSWORD")]
            # This portable helper is for the existing local lab only.
            if url.rstrip("/") not in ("http://localhost:8012", "http://localhost:8020",
                                        "http://127.0.0.1:8012", "http://127.0.0.1:8020"):
                raise ValueError("Expected a local laboratory endpoint")
            with xmlrpc.client.ServerProxy(url.rstrip("/") + "/xmlrpc/2/common") as common:
                uid = common.authenticate(db, user, password, {})
            if not uid:
                result["error_type"] = "AuthenticationFailed"
                continue
            with xmlrpc.client.ServerProxy(url.rstrip("/") + "/xmlrpc/2/object") as rpc:
                for model in ("product.template", "product.product", "res.partner"):
                    try:
                        result["models"][model] = rpc.execute_kw(
                            db, uid, password, model, "fields_get", [],
                            {"attributes": ["string", "type", "required", "readonly",
                                            "relation", "selection", "store", "compute",
                                            "related", "company_dependent"]})
                    except Exception as exc:
                        result["models"][model] = {"error_type": type(exc).__name__}
        except Exception as exc:
            result["error_type"] = type(exc).__name__
    return report


def main():
    socket.setdefaulttimeout(15)
    report = collect()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    output = Path(f"odoo-schema-{timestamp}.json")
    with output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, indent=2, ensure_ascii=False)
    print(f"Saved {output.resolve()}")
    print("Export may contain per-model errors; inspect it before treating it as complete.")


if __name__ == "__main__":
    main()
