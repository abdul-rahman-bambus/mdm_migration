import json
import unittest
from unittest.mock import MagicMock, patch

from migration_lab.journal import PilotError
from migration_lab.pilot import PartnerAPI, PilotReadRPC, usable_default
from migration_lab.preflight import ProbeFailure, ReadOnlyRPC, Settings


class PartnerDefaultsTests(unittest.TestCase):
    def test_zero_and_false_defaults_are_not_treated_as_missing(self):
        for kind, value in (("boolean", False), ("integer", 0), ("float", 0.0),
                            ("selection", 0), ("many2one", 55), ("char", "provided")):
            with self.subTest(kind=kind):
                self.assertTrue(usable_default({"type": kind}, value))

    def test_invalid_empty_and_unknown_defaults_remain_blocked(self):
        for kind, value in (("char", ""), ("char", " "), ("integer", False), ("float", float("nan")),
                            ("many2one", 0), ("many2one", False), ("selection", False), ("binary", "unknown")):
            with self.subTest(kind=kind, value=value):
                self.assertFalse(usable_default({"type": kind}, value))
        self.assertFalse(usable_default({"type": "selection", "selection": [["person", "Person"]]}, "invalid"))

    def api(self):
        api = PartnerAPI.__new__(PartnerAPI)
        api.major = 12
        api._default_fields = None
        api.metadata = {"company_type": {"type": "selection", "required": True, "readonly": False,
                                          "selection": [["person", "Person"]]}}
        api.execute = MagicMock(return_value={"company_type": "person"})
        return api

    def test_native_defaults_are_validated_and_cached_without_becoming_payload(self):
        api = self.api()
        self.assertEqual(api.validate_create(), ["company_type"])
        self.assertEqual(api.validate_create(), ["company_type"])
        api.execute.assert_called_once_with("default_get", [["company_type"]])

    def test_missing_defaults_report_field_names_without_values(self):
        api = self.api()
        api.execute.return_value = {"company_type": "private-canary"}
        with self.assertRaises(PilotError) as caught:
            api.validate_create()
        self.assertEqual(caught.exception.diagnostics["fields"], ["company_type"])
        self.assertNotIn("private-canary", json.dumps(caught.exception.diagnostics))

    def test_failed_default_discovery_keeps_fields_and_safe_category(self):
        api = self.api()
        api.execute.side_effect = ProbeFailure("rpc_fault")
        with self.assertRaises(PilotError) as caught:
            api.validate_create()
        self.assertEqual(caught.exception.diagnostics["error_category"], "rpc_fault")
        self.assertEqual(caught.exception.diagnostics["fields"], ["company_type"])

    def test_pilot_read_adapter_allows_default_get_but_no_writes(self):
        self.assertIn("default_get", PilotReadRPC.OPERATIONS)
        self.assertNotIn("default_get", ReadOnlyRPC.OPERATIONS)
        rpc = PilotReadRPC(Settings("https://example.com", "fixture", "fixture", "fixture-only"))
        with self.assertRaises(ValueError):
            rpc.call("object", "execute_kw", "fixture", 1, "fixture-only", "res.partner", "create", [{}])
