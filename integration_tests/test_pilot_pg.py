"""Invoked by scripts/run_pilot_integration.py, never against an existing lab DB."""

import contextlib
import io
import json
import os
import threading
import unittest
import uuid
import xmlrpc.client
from unittest.mock import patch
from http.server import BaseHTTPRequestHandler, HTTPServer

from migration_lab.journal import Journal, PilotError
from migration_lab.pilot import PartnerAPI, main, migrate, specification
from migration_lab.preflight import ProbeFailure, Settings


class RPCPartnerFixture:
    def __init__(self, major):
        self.major, self.rows, self.calls = major, {}, []
        self.lose_response = self.corrupt = self.reject_create = False

    def __enter__(self):
        fixture = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def do_POST(self):
                args, operation = xmlrpc.client.loads(self.rfile.read(int(self.headers["Content-Length"])))
                fixture.calls.append((operation, args))
                if operation == "version":
                    result = {"server_version_info": [fixture.major, 0]}
                elif operation == "authenticate":
                    result = 1
                else:
                    _, _, _, model, method, positional, kwargs = args
                    assert model == "res.partner"
                    assert kwargs["context"]["tracking_disable"] is True
                    assert kwargs["context"]["mail_create_nosubscribe"] is True
                    if method == "fields_get":
                        result = {name: {"type": "char", "readonly": False, "required": False}
                                  for name in ("name", "email", "phone", "ref")}
                    elif method == "search_read":
                        marker = positional[0][0][2]
                        result = [dict(row) for row in fixture.rows.values() if row["ref"] == marker][:2]
                    elif method == "create":
                        if fixture.reject_create:
                            self.respond(xmlrpc.client.Fault(1, "simulated rejected create"))
                            return
                        key = max(fixture.rows, default=fixture.major * 100) + 1
                        fixture.rows[key] = {"id": key, **positional[0]}
                        if fixture.corrupt:
                            fixture.rows[key]["phone"] = "+12025550199"
                        if fixture.lose_response:
                            fixture.lose_response = False
                            self.respond(xmlrpc.client.Fault(1, "simulated lost acknowledgement"))
                            return
                        result = key
                    elif method == "write":
                        fixture.rows[positional[0][0]].update(positional[1])
                        result = True
                    else:
                        raise AssertionError(method)
                self.respond((result,))

            def respond(self, result):
                body = xmlrpc.client.dumps(result, methodresponse=True).encode()
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server = HTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.api = PartnerAPI(Settings(f"http://127.0.0.1:{self.server.server_port}", "fixture", "fixture", "fixture-only"), self.major, writable=True)
        return self

    def __exit__(self, *args):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()


class PostgresPilotTests(unittest.TestCase):
    def setUp(self):
        self.journal = Journal.from_environment()
        self.addCleanup(self.journal.close)
        self.journal.initialize()
        self.source = self.enterContext(RPCPartnerFixture(12))
        self.target = self.enterContext(RPCPartnerFixture(20))
        self.label = "test-" + uuid.uuid4().hex[:20]
        self.spec = specification(self.label, "fixture-source", "fixture-target")
        self.action("seed")

    def action(self, action="sync", apply=False, phone=None):
        return migrate(self.source.api, self.target.api, self.journal, self.spec,
                       "fixture-source", "fixture-target", action, apply, phone)

    def test_dry_run_then_create_rerun_update_and_persistent_history(self):
        self.assertEqual(self.action()["proposed_operation"], "create")
        self.assertEqual(len(self.target.rows), 0)
        first = self.action(apply=True)
        self.assertNotEqual(first["source_id"], first["target_id"])
        self.assertEqual(self.action(apply=True)["operation"], "no_change")
        self.action("change-source", phone="+12025550123")
        self.assertEqual(self.action(apply=True)["operation"], "update")
        self.assertEqual(len(self.target.rows), 1)
        other = Journal.from_environment()
        try:
            saved = other.status(self.spec["namespace"])
            self.assertEqual(saved["mapping"]["target_id"], first["target_id"])
            self.assertEqual(len(saved["runs"]), 6)
            self.assertEqual(saved["mapping"]["state"], "reconciled")
        finally:
            other.close()

    def test_lost_create_acknowledgement_retries_without_duplicate(self):
        self.target.lose_response = True
        with self.assertRaises(ProbeFailure):
            self.action(apply=True)
        self.assertEqual(self.journal.status(self.spec["namespace"])["runs"][0]["state"], "failed")
        self.assertIsNone(self.journal.mapping(self.spec["namespace"]))
        self.assertEqual(self.action(apply=True)["state"], "reconciled")
        self.assertEqual(len(self.target.rows), 1)

    def test_real_journal_lock_blocks_concurrent_worker(self):
        other = Journal.from_environment()
        try:
            with self.journal.lock(self.spec["namespace"]), self.assertRaisesRegex(PilotError, "pilot_busy"):
                with other.lock(self.spec["namespace"]):
                    self.fail("A second worker must not acquire the same lock")
        finally:
            other.close()

    def test_failed_reconciliation_never_commits_successful_mapping(self):
        self.target.corrupt = True
        with self.assertRaisesRegex(PilotError, "target_reconciliation_failed"):
            self.action(apply=True)
        self.assertIsNone(self.journal.mapping(self.spec["namespace"]))
        status = self.journal.status(self.spec["namespace"])
        self.assertEqual(status["runs"][0]["state"], "failed")
        events = self.journal.connection.execute(
            "SELECT state FROM bambus_pilot.events WHERE run_id=%s ORDER BY id", (status["runs"][0]["id"],)
        ).fetchall()
        self.assertIn("reconciliation_failed", [event["state"] for event in events])

    def test_mapping_survives_target_loss_and_blocks_unsafe_recreation(self):
        self.action(apply=True)
        self.target.rows.clear()  # Only synthetic HTTP fixture data, never a real Odoo DB.
        with self.assertRaisesRegex(PilotError, "target_restore_or_mapping_conflict"):
            self.action(apply=True)
        self.assertIsNotNone(self.journal.mapping(self.spec["namespace"]))
        self.assertEqual(self.journal.status(self.spec["namespace"])["latest_run_state"], "failed")

    def test_repeated_initialization_preserves_existing_runs(self):
        before = self.journal.status(self.spec["namespace"])
        self.journal.initialize()
        after = self.journal.status(self.spec["namespace"])
        self.assertEqual(before, after)

    def test_interrupt_then_new_worker_recovers_committed_target(self):
        original = self.target.api.create

        def interrupted_create(values):
            original(values)
            raise KeyboardInterrupt()

        with patch.object(self.target.api, "create", side_effect=interrupted_create), self.assertRaises(KeyboardInterrupt):
            self.action(apply=True)
        self.assertEqual(self.journal.status(self.spec["namespace"])["runs"][0]["state"], "running")
        self.journal.close()
        self.journal = Journal.from_environment()
        self.addCleanup(self.journal.close)
        self.assertEqual(self.action(apply=True)["state"], "reconciled")
        self.assertEqual(len(self.target.rows), 1)

    def test_source_seed_lost_acknowledgement_does_not_duplicate(self):
        self.spec = specification("seed-" + uuid.uuid4().hex[:20], "fixture-source", "fixture-target")
        self.source.lose_response = True
        with self.assertRaises(ProbeFailure):
            self.action("seed")
        size = len(self.source.rows)
        self.assertEqual(self.action("seed")["state"], "seeded")
        self.assertEqual(len(self.source.rows), size)

    def test_cli_lifecycle_against_real_journal_and_http_fixtures(self):
        env = {}
        for prefix, fixture in (("ODOO12", self.source), ("ODOO20", self.target)):
            for suffix, value in (("URL", fixture.api.settings.url), ("DB", "fixture"),
                                  ("USERNAME", "fixture"), ("PASSWORD", "fixture-only")):
                env[f"{prefix}_{suffix}"] = value
        commands = [["seed"], ["sync"], ["sync", "--apply"], ["sync", "--apply"],
                    ["change-source", "--phone", "+12025550123"], ["sync", "--apply"], ["status"]]
        reports = []
        for command in commands:
            output = io.StringIO()
            # Use ephemeral fixture ports; production endpoint restrictions are
            # separately exercised by unit tests and are not configurable in CLI.
            with patch.dict(os.environ, env), patch("migration_lab.pilot.identity", side_effect=["fixture-source", "fixture-target"]), contextlib.redirect_stdout(output):
                self.assertEqual(main(command + ["--lab-only", "--label", self.label]), 0)
            self.assertNotIn(os.environ["JOURNAL_DB_PASSWORD"], output.getvalue())
            reports.append(json.loads(output.getvalue()))
        self.assertEqual(reports[1]["state"], "dry_run")
        self.assertEqual(reports[2]["operation"], "create")
        self.assertEqual(reports[3]["operation"], "no_change")
        self.assertEqual(reports[5]["operation"], "update")
        self.assertEqual(reports[6]["mapping"]["state"], "reconciled")
        self.assertEqual(len(self.target.rows), 1)

    def test_unknown_create_without_visible_marker_requires_review(self):
        self.target.reject_create = True
        with self.assertRaises(ProbeFailure):
            self.action(apply=True)
        self.target.reject_create = False
        with self.assertRaisesRegex(PilotError, "unresolved_target_create_requires_review"):
            self.action(apply=True)
        self.assertEqual(len(self.target.rows), 0)
        self.assertTrue(self.journal.has_intent(self.spec["namespace"], "load_intent", "create"))
