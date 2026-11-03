"""Read-only Odoo readiness checks. No business record writes or raw fault logging."""

import argparse
import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
import xmlrpc.client
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Settings:
    url: str
    database: str
    username: str
    password: str = field(repr=False)

    @classmethod
    def from_environment(cls, prefix, environ=None):
        env = os.environ if environ is None else environ
        names = [f"{prefix}_{suffix}" for suffix in ("URL", "DB", "USERNAME", "PASSWORD")]
        missing = [name for name in names if not env.get(name)]
        if missing:
            raise ValueError("Missing variables: " + ", ".join(missing))
        settings = cls(*(env[name] for name in names))
        try:
            parts = urllib.parse.urlsplit(settings.url)
            parts.port
        except ValueError:
            raise ValueError(f"Invalid {prefix}_URL") from None
        if (parts.scheme not in ("http", "https") or not parts.hostname
                or parts.username is not None or parts.password is not None
                or parts.query or parts.fragment):
            raise ValueError(f"Invalid {prefix}_URL: use an HTTP(S) base URL without credentials, query, or fragment")
        if parts.scheme == "http" and parts.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError(f"{prefix}_URL requires HTTPS outside loopback")
        return settings


class ProbeFailure(Exception):
    """Contains only an allowlisted category; never remote response text."""


def classify(exc):
    if isinstance(exc, xmlrpc.client.Fault):
        return "rpc_fault"
    if isinstance(exc, urllib.error.HTTPError):
        return "http_error"
    if isinstance(exc, (TimeoutError, socket.timeout)):
        return "timeout"
    if isinstance(exc, urllib.error.URLError):
        return "timeout" if isinstance(exc.reason, TimeoutError) else "network_error"
    if isinstance(exc, OSError):
        return "network_error"
    return "invalid_response"


class ReadOnlyRPC:
    """Explicit read allowlist, bounded responses, verified TLS and inherited proxy routing.

    urllib supplies proxy support including HTTPS CONNECT, unlike the default
    xmlrpc transport. There are deliberately no automatic retries or write methods.
    """

    METHODS = {"version", "authenticate", "execute_kw"}
    OPERATIONS = {"fields_get", "search_read", "search_count"}

    def __init__(self, settings, timeout=10, max_bytes=4 * 1024 * 1024):
        self.settings = settings
        self.timeout = timeout
        self.max_bytes = max_bytes
        # Do not forward XML-RPC credentials to a redirected endpoint.
        class NoRedirect(urllib.request.HTTPRedirectHandler):
            def redirect_request(self, req, fp, code, msg, headers, newurl):
                return None
        self.opener = urllib.request.build_opener(NoRedirect())

    def call(self, endpoint, method, *args):
        if endpoint not in ("common", "object") or method not in self.METHODS:
            raise ValueError("Unsupported read-only RPC call")
        if method == "execute_kw" and (len(args) < 5 or args[4] not in self.OPERATIONS):
            raise ValueError("Only assessment operations are allowed")
        try:
            body = xmlrpc.client.dumps(args, methodname=method, allow_none=True).encode("utf-8")
            request = urllib.request.Request(
                self.settings.url.rstrip("/") + "/xmlrpc/2/" + endpoint,
                data=body, headers={"Content-Type": "text/xml"}, method="POST",
            )
            with self.opener.open(request, timeout=self.timeout) as response:
                payload = response.read(self.max_bytes + 1)
            if len(payload) > self.max_bytes:
                raise ProbeFailure("response_too_large")
            values, _ = xmlrpc.client.loads(payload)
            return values[0]
        except ProbeFailure:
            raise
        except Exception as exc:
            raise ProbeFailure(classify(exc)) from None


def assess(settings, expected_major, timeout=10):
    rpc = ReadOnlyRPC(settings, timeout)
    checks = []

    def check(name, operation):
        try:
            detail = operation()
            checks.append({"check": name, "state": "passed", **detail})
            return True
        except ProbeFailure as exc:
            checks.append({"check": name, "state": "failed", "category": str(exc)})
            return False

    def version():
        result = rpc.call("common", "version")
        info = result.get("server_version_info") if isinstance(result, dict) else None
        if not isinstance(info, (list, tuple)) or not info or type(info[0]) is not int:
            raise ProbeFailure("invalid_version_response")
        if info[0] != expected_major:
            raise ProbeFailure("unexpected_server_version")
        return {"major": info[0]}

    if not check("xmlrpc_version", version):
        return {"state": "blocked", "checks": checks}

    uid = None

    def authenticate():
        nonlocal uid
        uid = rpc.call("common", "authenticate", settings.database,
                       settings.username, settings.password, {})
        if type(uid) is not int or uid <= 0:
            raise ProbeFailure("authentication_failed")
        return {}

    if not check("authentication", authenticate):
        return {"state": "blocked", "checks": checks}

    def execute(model, operation, args, kwargs):
        return rpc.call("object", "execute_kw", settings.database, uid,
                        settings.password, model, operation, args, kwargs)

    for model in ("product.template", "product.product", "res.partner"):
        def metadata(model=model):
            result = execute(model, "fields_get", [], {"attributes": ["type", "required", "readonly", "relation"]})
            if not isinstance(result, dict) or not result or "name" not in result:
                raise ProbeFailure("invalid_metadata")
            return {"field_count": len(result)}

        def sample(model=model):
            result = execute(model, "search_read", [[]], {"fields": ["id"], "limit": 1})
            if not isinstance(result, list) or len(result) > 1 or any(
                not isinstance(row, dict) or type(row.get("id")) is not int for row in result
            ):
                raise ProbeFailure("invalid_sample_response")
            # No record contents or identifiers are included in reports.
            return {"records_read": len(result), "sample_available": bool(result)}

        check(f"{model}.fields_get", metadata)
        check(f"{model}.sample_read", sample)
    return {"state": "passed" if all(c["state"] == "passed" for c in checks) else "blocked",
            "checks": checks}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Perform read-only requests using exported laboratory credentials")
    parser.add_argument("--timeout", type=float, default=10)
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 120:
        parser.error("--timeout must be greater than zero and at most 120 seconds")
    report = {"scope": "connectivity_only", "migration_ready": False, "instances": {}}
    for prefix, major in (("ODOO12", 12), ("ODOO20", 20)):
        try:
            settings = Settings.from_environment(prefix)
        except ValueError as exc:
            result = {"state": "blocked", "configuration_error": str(exc)}
        else:
            result = assess(settings, major, args.timeout) if args.live else {"state": "configured_not_tested"}
        report["instances"][prefix] = result
    print(json.dumps(report, indent=2))
    # A configuration-only run never establishes connectivity readiness.
    return 0 if args.live and all(r["state"] == "passed" for r in report["instances"].values()) else 1
