import contextlib
import io
import json
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from migration_lab.journal import Journal, PilotError, connection_failure
from migration_lab.pilot import main


class JournalConnectionTests(unittest.TestCase):
    def fake_driver(self):
        driver = types.ModuleType("psycopg")
        driver.__path__ = []
        driver.connect = MagicMock()
        rows = types.ModuleType("psycopg.rows")
        rows.dict_row = object()
        return driver, {"psycopg": driver, "psycopg.rows": rows}

    def test_safe_categories_never_include_raw_error_or_password(self):
        cases = [("password authentication failed canary-secret", "journal_authentication_failed"),
                 ("connection refused canary-secret", "journal_not_ready"),
                 ("timeout expired canary-secret", "journal_connection_timeout"),
                 ("database x does not exist canary-secret", "journal_database_missing"),
                 ("SSL certificate verify failed canary-secret", "journal_tls_error"),
                 ("arbitrary error canary-secret", "journal_connection_failed")]
        for text, expected in cases:
            with self.subTest(expected=expected):
                code, diagnostics = connection_failure(OSError(text))
                self.assertEqual(code, expected)
                self.assertNotIn("canary-secret", json.dumps([code, diagnostics]))

    def test_authentication_sqlstate_overrides_transient_text(self):
        exc = OSError("connection refused")
        exc.sqlstate = "28P01"
        self.assertEqual(connection_failure(exc)[0], "journal_authentication_failed")

    def test_transient_startup_failure_is_retried(self):
        driver, modules = self.fake_driver()
        connection = MagicMock()
        connection.execute.return_value.fetchone.return_value = {"name": "bambus_migration_journal"}
        driver.connect.side_effect = [OSError("Connection refused"), connection]
        with patch.dict(sys.modules, modules), patch.dict("os.environ", {"JOURNAL_DB_PASSWORD": "canary-secret"}, clear=True), patch("migration_lab.journal.time.sleep") as sleep:
            self.assertIs(Journal.from_environment().connection, connection)
        self.assertEqual(driver.connect.call_count, 2)
        sleep.assert_called_once_with(1)

    def test_authentication_failure_is_not_retried(self):
        driver, modules = self.fake_driver()
        driver.connect.side_effect = OSError("password authentication failed: canary-secret")
        with patch.dict(sys.modules, modules), patch.dict("os.environ", {"JOURNAL_DB_PASSWORD": "canary-secret"}, clear=True), self.assertRaisesRegex(PilotError, "journal_authentication_failed") as caught:
            Journal.from_environment()
        self.assertEqual(driver.connect.call_count, 1)
        self.assertEqual(caught.exception.diagnostics["attempts"], 1)
        self.assertNotIn("canary-secret", json.dumps(caught.exception.diagnostics))

    def test_startup_retries_are_bounded(self):
        driver, modules = self.fake_driver()
        driver.connect.side_effect = OSError("Connection refused")
        with patch.dict(sys.modules, modules), patch.dict("os.environ", {"JOURNAL_DB_PASSWORD": "canary-secret"}, clear=True), patch("migration_lab.journal.time.sleep") as sleep, self.assertRaises(PilotError) as caught:
            Journal.from_environment()
        self.assertEqual(driver.connect.call_count, 3)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(caught.exception.diagnostics["attempts"], 3)

    def test_invalid_port_does_not_attempt_connection(self):
        driver, modules = self.fake_driver()
        with patch.dict(sys.modules, modules), patch.dict("os.environ", {"JOURNAL_DB_PASSWORD": "canary-secret", "JOURNAL_DB_PORT": "bad"}, clear=True), self.assertRaisesRegex(PilotError, "invalid_JOURNAL_DB_PORT"):
            Journal.from_environment()
        driver.connect.assert_not_called()

    def test_failed_verification_closes_connection_and_redacts_error(self):
        driver, modules = self.fake_driver()
        connection = driver.connect.return_value
        connection.execute.side_effect = TypeError("canary-secret")
        with patch.dict(sys.modules, modules), patch.dict("os.environ", {"JOURNAL_DB_PASSWORD": "canary-secret"}, clear=True), self.assertRaises(PilotError) as caught:
            Journal.from_environment()
        connection.close.assert_called_once()
        self.assertEqual(caught.exception.diagnostics["exception_type"], "TypeError")
        self.assertNotIn("canary-secret", str(caught.exception))

    def test_journal_check_does_not_initialize_or_contact_odoo(self):
        journal = MagicMock()
        output = io.StringIO()
        with patch("migration_lab.pilot.Journal.from_environment", return_value=journal), patch("migration_lab.pilot.PartnerAPI") as api, contextlib.redirect_stdout(output):
            self.assertEqual(main(["journal-check", "--lab-only"]), 0)
        journal.initialize.assert_not_called()
        api.assert_not_called()
        self.assertEqual(json.loads(output.getvalue())["state"], "journal_connected")

    def test_cli_connection_failure_prints_only_safe_diagnostics(self):
        error = PilotError("journal_authentication_failed", {"host": "127.0.0.1", "port": 55432, "attempts": 1})
        output = io.StringIO()
        with patch("migration_lab.pilot.Journal.from_environment", side_effect=error), contextlib.redirect_stdout(output):
            self.assertEqual(main(["journal-check", "--lab-only"]), 1)
        self.assertEqual(json.loads(output.getvalue())["diagnostics"]["port"], 55432)
