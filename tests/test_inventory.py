import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from migration_lab.inventory import CORE_MODELS, DEPENDENCIES, collect, main
from migration_lab.preflight import ProbeFailure, Settings


class InventoryTests(unittest.TestCase):
    settings = Settings("https://example.com", "lab", "user", "secret")

    def rpc(self, rows, failed_model=None, registry_rows=None):
        def call(endpoint, operation, *args):
            if operation == "version":
                return {"server_version_info": [12, 0]}
            if operation == "authenticate":
                return 1
            self.assertEqual(operation, "execute_kw")
            model, method, positional, kwargs = args[3:]
            if method == "search_read":
                if model == "ir.model":
                    return [] if registry_rows is None else registry_rows
                self.assertEqual(model, "ir.module.module")
                self.assertEqual(positional, [[("state", "=", "installed")]])
                return rows(kwargs["offset"])
            self.assertEqual(method, "fields_get")
            if model == failed_model:
                raise ProbeFailure("rpc_fault")
            return {"name": {"type": "char"}}
        return call

    def test_module_pagination_and_dependency_inventory(self):
        pages = lambda offset: [{"id": i, "name": f"module_{i}"} for i in range(offset + 1, min(offset + 101, 106))]
        with patch("migration_lab.inventory.ReadOnlyRPC") as rpc:
            rpc.return_value.call.side_effect = self.rpc(pages)
            result = collect(self.settings, 12)
        self.assertEqual(result["state"], "passed")
        self.assertEqual(len(result["installed_modules"]["names"]), 105)
        self.assertEqual(set(result["models"]), set(CORE_MODELS + DEPENDENCIES))
        self.assertNotIn("secret", str(result))

    def test_missing_model_remains_partial_while_others_continue(self):
        with patch("migration_lab.inventory.ReadOnlyRPC") as rpc:
            rpc.return_value.call.side_effect = self.rpc(lambda offset: [], "mail.activity")
            result = collect(self.settings, 12)
        self.assertEqual(result["state"], "partial")
        self.assertEqual(result["models"]["mail.activity"]["error_category"], "rpc_fault")
        self.assertEqual(result["models"]["mail.activity"]["registry_visibility"], "not_visible_in_registry")
        self.assertEqual(result["models"]["ir.attachment"]["state"], "passed")

    def test_repeated_page_is_detected(self):
        page = [{"id": i, "name": f"module_{i}"} for i in range(100)]
        with patch("migration_lab.inventory.ReadOnlyRPC") as rpc:
            rpc.return_value.call.side_effect = self.rpc(lambda offset: page)
            result = collect(self.settings, 12)
        self.assertEqual(result["installed_modules"]["error_category"], "invalid_or_repeated_module_page")
        self.assertEqual(result["state"], "partial")

    def test_page_limit_never_claims_complete_inventory(self):
        page = [{"id": i, "name": f"module_{i}"} for i in range(100)]
        with patch("migration_lab.inventory.ReadOnlyRPC") as rpc:
            rpc.return_value.call.side_effect = self.rpc(lambda offset: page)
            result = collect(self.settings, 12, max_pages=1)
        self.assertEqual(result["installed_modules"]["error_category"], "module_page_limit_exceeded")

    def test_authentication_failure_prevents_inventory_requests(self):
        with patch("migration_lab.inventory.ReadOnlyRPC") as rpc:
            rpc.return_value.call.side_effect = [{"server_version_info": [12, 0]}, False]
            result = collect(self.settings, 12)
            self.assertEqual(rpc.return_value.call.call_count, 2)
        self.assertEqual(result["error_category"], "authentication_failed")

    def test_visible_model_fault_is_not_reported_as_missing(self):
        with patch("migration_lab.inventory.ReadOnlyRPC") as rpc:
            rpc.return_value.call.side_effect = self.rpc(lambda offset: [], "uom.category", [{"model": "uom.category"}])
            result = collect(self.settings, 12)
        self.assertEqual(result["models"]["uom.category"]["registry_visibility"], "visible_in_registry")
        self.assertEqual(result["state"], "partial")

    def test_registry_access_failure_preserves_original_model_error(self):
        ordinary = self.rpc(lambda offset: [], "uom.category")

        def call(endpoint, operation, *args):
            if operation == "execute_kw" and args[3] == "ir.model":
                raise ProbeFailure("rpc_fault")
            return ordinary(endpoint, operation, *args)

        with patch("migration_lab.inventory.ReadOnlyRPC") as rpc:
            rpc.return_value.call.side_effect = call
            result = collect(self.settings, 12)
        row = result["models"]["uom.category"]
        self.assertEqual(row["error_category"], "rpc_fault")
        self.assertEqual(row["registry_visibility"], "registry_query_failed")

    def test_cli_exports_core_schema_even_when_dependency_check_is_partial(self):
        instances = [{"state": "partial", "models": {
            **{model: {"state": "passed", "fields": {"name": {"type": "char"}}} for model in CORE_MODELS},
            "uom.category": {"state": "failed", "error_category": "rpc_fault"}
        }} for _ in range(2)]
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "inventory"
            with patch("migration_lab.inventory.Settings.from_environment", return_value=self.settings), patch(
                "migration_lab.inventory.collect", side_effect=instances
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--output-dir", str(output)]), 1)
            snapshot = json.loads((output / "schema.json").read_text())
            self.assertEqual(set(snapshot["ODOO12"]), set(CORE_MODELS))
            report = json.loads((output / "inventory.json").read_text())
            self.assertIn("captured_at", report)
            self.assertFalse(report["migration_ready"])

    def test_cli_does_not_export_incomplete_core_schema(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "inventory"
            with patch("migration_lab.inventory.Settings.from_environment", return_value=self.settings), patch(
                "migration_lab.inventory.collect", return_value={"state": "blocked", "models": {}}
            ), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main(["--output-dir", str(output)]), 1)
            self.assertTrue((output / "inventory.json").exists())
            self.assertFalse((output / "schema.json").exists())
