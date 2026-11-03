import unittest
from unittest.mock import patch

from migration_lab.inventory import DEPENDENCIES, collect
from migration_lab.preflight import ProbeFailure, Settings


class InventoryTests(unittest.TestCase):
    settings = Settings("https://example.com", "lab", "user", "secret")

    def rpc(self, rows, failed_model=None):
        def call(endpoint, operation, *args):
            if operation == "version":
                return {"server_version_info": [12, 0]}
            if operation == "authenticate":
                return 1
            self.assertEqual(operation, "execute_kw")
            model, method, positional, kwargs = args[3:]
            if method == "search_read":
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
        self.assertEqual(set(result["models"]), set(DEPENDENCIES))
        self.assertNotIn("secret", str(result))

    def test_missing_model_remains_partial_while_others_continue(self):
        with patch("migration_lab.inventory.ReadOnlyRPC") as rpc:
            rpc.return_value.call.side_effect = self.rpc(lambda offset: [], "mail.activity")
            result = collect(self.settings, 12)
        self.assertEqual(result["state"], "partial")
        self.assertEqual(result["models"]["mail.activity"]["error_category"], "rpc_fault")
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
