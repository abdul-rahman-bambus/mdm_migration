import contextlib
import io
import json
import threading
import unittest
import xmlrpc.client
from http.server import BaseHTTPRequestHandler, HTTPServer
from unittest.mock import patch

from migration_lab.preflight import ProbeFailure, ReadOnlyRPC, Settings, assess, main


class RPCFixture:
    def __init__(self, mode="normal", major=12):
        self.mode = mode
        self.major = major
        self.calls = []

    def __enter__(self):
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                args, method = xmlrpc.client.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fixture.calls.append((self.path, method, args))
                if fixture.mode == "redirect":
                    self.send_response(307)
                    self.send_header("Location", "/redirected")
                    self.end_headers()
                    return
                if fixture.mode == "malformed":
                    payload = b"not XML"
                elif method == "version":
                    payload = xmlrpc.client.dumps(({"server_version_info": [fixture.major, 0]},), methodresponse=True).encode()
                elif method == "authenticate":
                    payload = xmlrpc.client.dumps((False if fixture.mode == "bad_auth" else 7,), methodresponse=True).encode()
                elif fixture.mode == "fault":
                    payload = xmlrpc.client.dumps(xmlrpc.client.Fault(1, "secret-password personal data")).encode()
                else:
                    result = {"name": {"type": "char"}} if args[4] == "fields_get" else ([] if fixture.mode == "empty" else [{"id": 42}])
                    payload = xmlrpc.client.dumps((result,), methodresponse=True).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.settings = Settings(f"http://127.0.0.1:{self.server.server_port}", "lab", "user", "secret-password")
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class PreflightTests(unittest.TestCase):
    def test_missing_configuration_lists_names_only(self):
        with self.assertRaisesRegex(ValueError, "ODOO12_PASSWORD"):
            Settings.from_environment("ODOO12", {"ODOO12_URL": "secret-value"})

    def test_url_validation_and_password_redaction(self):
        for url in ("http://remote.example", "https://user:secret@example.com", "https://example.com?token=secret", "https://example.com:bad", "https://[secret"):
            env = dict(zip(("X_URL", "X_DB", "X_USERNAME", "X_PASSWORD"), (url, "db", "user", "secret-password")))
            with self.subTest(url=url), self.assertRaises(ValueError) as error:
                Settings.from_environment("X", env)
            self.assertNotIn("secret", str(error.exception))
        self.assertNotIn("secret-password", repr(Settings("https://example.com", "db", "user", "secret-password")))

    def test_complete_read_only_protocol(self):
        with RPCFixture() as fixture:
            result = assess(fixture.settings, 12)
        self.assertEqual(result["state"], "passed")
        self.assertEqual(len(result["checks"]), 8)
        self.assertEqual(len(fixture.calls), 8)
        self.assertEqual(fixture.calls[1][2], ("lab", "user", "secret-password", {}))
        for path, method, args in fixture.calls[2:]:
            self.assertEqual(path, "/xmlrpc/2/object")
            self.assertEqual(method, "execute_kw")
            self.assertIn(args[4], {"fields_get", "search_read"})
            self.assertEqual(args[:3], ("lab", 7, "secret-password"))

    def test_wrong_version_blocks_authentication(self):
        with RPCFixture(major=19) as fixture:
            result = assess(fixture.settings, 20)
        self.assertEqual(result["checks"][0]["category"], "unexpected_server_version")
        self.assertEqual(len(fixture.calls), 1)

    def test_invalid_credentials_block_reads(self):
        with RPCFixture("bad_auth") as fixture:
            result = assess(fixture.settings, 12)
        self.assertEqual(result["checks"][-1]["category"], "authentication_failed")
        self.assertEqual(len(fixture.calls), 2)

    def test_remote_faults_are_redacted_and_independent_checks_continue(self):
        with RPCFixture("fault") as fixture:
            result = assess(fixture.settings, 12)
        self.assertEqual(result["state"], "blocked")
        self.assertEqual(len(result["checks"]), 8)
        self.assertNotIn("secret-password", json.dumps(result))
        self.assertNotIn("personal data", json.dumps(result))

    def test_empty_samples_are_explicit(self):
        with RPCFixture("empty") as fixture:
            result = assess(fixture.settings, 12)
        self.assertTrue(all(c["sample_available"] is False for c in result["checks"] if "sample_available" in c))

    def test_redirect_is_not_followed(self):
        with RPCFixture("redirect") as fixture:
            result = assess(fixture.settings, 12)
        self.assertEqual(len(fixture.calls), 1)
        self.assertEqual(result["checks"][0]["category"], "http_error")

    def test_malformed_response(self):
        with RPCFixture("malformed") as fixture:
            result = assess(fixture.settings, 12)
        self.assertEqual(result["checks"][0]["category"], "invalid_response")

    def test_bounded_response(self):
        with RPCFixture() as fixture:
            rpc = ReadOnlyRPC(fixture.settings, max_bytes=1)
            with self.assertRaisesRegex(ProbeFailure, "response_too_large"):
                rpc.call("common", "version")

    def test_timeout_is_sanitized_without_retry(self):
        rpc = ReadOnlyRPC(Settings("https://example.com", "db", "user", "secret-password"))
        with patch.object(rpc.opener, "open", side_effect=TimeoutError("secret-password")) as request:
            with self.assertRaisesRegex(ProbeFailure, "timeout"):
                rpc.call("common", "version")
        self.assertEqual(request.call_count, 1)

    def test_writes_are_refused_before_network(self):
        rpc = ReadOnlyRPC(Settings("https://example.com", "db", "user", "secret-password"))
        with self.assertRaises(ValueError):
            rpc.call("object", "execute_kw", "db", 1, "secret-password", "res.partner", "create", [{}])

    def test_cli_configuration_only_never_claims_ready(self):
        env = {f"{prefix}_{suffix}": value for prefix in ("ODOO12", "ODOO20")
               for suffix, value in (("URL", "https://example.com"), ("DB", "db"), ("USERNAME", "user"), ("PASSWORD", "secret-password"))}
        output = io.StringIO()
        with patch.dict("os.environ", env, clear=True), contextlib.redirect_stdout(output):
            self.assertEqual(main([]), 1)
        report = json.loads(output.getvalue())
        self.assertFalse(report["migration_ready"])
        self.assertEqual(report["instances"]["ODOO12"]["state"], "configured_not_tested")

    def test_cli_live_checks_both_versions_without_claiming_migration_ready(self):
        with RPCFixture(major=12) as source, RPCFixture(major=20) as target:
            env = {f"{prefix}_{suffix}": value for prefix, fixture in (("ODOO12", source), ("ODOO20", target))
                   for suffix, value in (("URL", fixture.settings.url), ("DB", "lab"), ("USERNAME", "user"), ("PASSWORD", "secret-password"))}
            output = io.StringIO()
            with patch.dict("os.environ", env, clear=True), contextlib.redirect_stdout(output):
                self.assertEqual(main(["--live"]), 0)
            report = json.loads(output.getvalue())
            self.assertFalse(report["migration_ready"])
            self.assertEqual(report["instances"]["ODOO20"]["state"], "passed")

    def test_unavailable_service(self):
        with RPCFixture() as fixture:
            settings = fixture.settings
        result = assess(settings, 12, timeout=1)
        self.assertEqual(result["checks"][0]["category"], "network_error")


if __name__ == "__main__":
    unittest.main()
