import importlib.util
import os
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch


spec = importlib.util.spec_from_file_location(
    "export_local_schema", Path(__file__).resolve().parents[1] / "scripts/export_local_schema.py")
exporter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(exporter)


class SchemaExportTests(unittest.TestCase):
    def environment(self):
        return {f"{prefix}_{key}": value for prefix, port in (("ODOO12", 8012), ("ODOO20", 8020))
                for key, value in (("URL", f"http://localhost:{port}"), ("DB", "lab"),
                                   ("USERNAME", "user"), ("PASSWORD", "private"))}

    def test_reads_only_metadata_for_both_instances(self):
        rpc = MagicMock()
        rpc.__enter__.return_value = rpc
        rpc.authenticate.return_value = 1
        rpc.execute_kw.return_value = {"name": {"type": "char"}}
        with patch.dict(os.environ, self.environment(), clear=True), patch.object(
                exporter.xmlrpc.client, "ServerProxy", return_value=rpc):
            report = exporter.collect()
        self.assertEqual(rpc.execute_kw.call_count, 6)
        for call in rpc.execute_kw.call_args_list:
            self.assertEqual(call.args[4], "fields_get")
        self.assertEqual(len(report["ODOO20"]["models"]), 3)
        self.assertNotIn("private", str(report))

    def test_authentication_failure_stops_metadata_reads(self):
        rpc = MagicMock()
        rpc.__enter__.return_value = rpc
        rpc.authenticate.return_value = False
        with patch.dict(os.environ, self.environment(), clear=True), patch.object(
                exporter.xmlrpc.client, "ServerProxy", return_value=rpc):
            report = exporter.collect()
        rpc.execute_kw.assert_not_called()
        self.assertEqual(report["ODOO12"]["error_type"], "AuthenticationFailed")

    def test_metadata_errors_are_redacted_and_models_continue(self):
        rpc = MagicMock()
        rpc.__enter__.return_value = rpc
        rpc.authenticate.return_value = 1
        rpc.execute_kw.side_effect = RuntimeError("private")
        with patch.dict(os.environ, self.environment(), clear=True), patch.object(
                exporter.xmlrpc.client, "ServerProxy", return_value=rpc):
            report = exporter.collect()
        self.assertEqual(rpc.execute_kw.call_count, 6)
        self.assertNotIn("private", str(report))
        self.assertEqual(report["ODOO12"]["models"]["res.partner"]["error_type"], "RuntimeError")
