from copy import deepcopy
import unittest
import uuid
from unittest.mock import patch

from migration_lab.journal import PilotError
from migration_lab.monitor import MirrorClient, MirrorRPC, protocol
from migration_lab.preflight import Settings


class MonitorProtocolTests(unittest.TestCase):
    def run_row(self):
        return {"id": str(uuid.uuid4()), "namespace": "a" * 64, "operation": "apply", "state": "reconciled",
                "source_identity": "fixture-source", "target_identity": "fixture-target", "mapping_version": "synthetic-contact-v1",
                "source_id": 101, "target_id": 901, "payload_digest": "b" * 64, "error_code": None,
                "started_at": "2026-01-01T01:00:00.123456+05:30", "finished_at": "2026-01-01T01:00:01.123456+05:30"}

    def test_datetime_conversion_preserves_order_and_utc(self):
        row = self.run_row()
        self.assertEqual(protocol.row("runs", row), row)
        timestamp = protocol.timestamp(row["started_at"])
        self.assertIsNone(timestamp.tzinfo)
        self.assertEqual((timestamp.hour, timestamp.minute, timestamp.microsecond), (19, 30, 123456))

    def test_unknown_states_business_values_and_wrong_types_are_rejected(self):
        row = self.run_row()
        for key, value in (("state", []), ("state", "invented_success"), ("source_id", True), ("payload_digest", "raw-value")):
            bad = deepcopy(row)
            bad[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                protocol.row("runs", bad)
        bad = deepcopy(row)
        bad["password"] = "fabricated-canary"
        with self.assertRaises(ValueError) as caught:
            protocol.row("runs", bad)
        self.assertNotIn("fabricated-canary", str(caught.exception))

    def test_event_details_allow_field_names_not_payloads(self):
        event = {"id": 1, "run_id": str(uuid.uuid4()), "state": "validated", "created_at": "2026-01-01T00:00:00Z",
                 "details": {"fields": ["name", "email"], "operation": "create"}}
        self.assertEqual(protocol.row("events", event), event)
        event["details"] = {"source_value": "person@example.invalid"}
        with self.assertRaises(ValueError):
            protocol.row("events", event)
        event["details"] = {"operation": []}
        with self.assertRaises(ValueError):
            protocol.row("events", event)

    def test_batch_and_manifest_limits_are_bounded(self):
        with self.assertRaises(ValueError):
            protocol.page("runs", [self.run_row()] * 101)
        with self.assertRaises(ValueError):
            protocol.page({}, [])
        key = str(uuid.uuid4())
        revision = "a" * 64
        manifest = {"journal_key": key, "revision": revision, "snapshot_key": str(uuid.uuid5(uuid.UUID(key), revision)),
                    "captured_at": "2026-01-01T00:00:00Z", "counts": {"runs": 1, "events": 1, "mappings": 0}}
        self.assertEqual(protocol.manifest(manifest), manifest)
        manifest["counts"]["runs"] = 10001
        with self.assertRaises(ValueError):
            protocol.manifest(manifest)

    def test_client_never_exposes_business_write_methods(self):
        self.assertNotIn("create", MirrorRPC.OPERATIONS)
        self.assertNotIn("write", MirrorRPC.OPERATIONS)
        settings = Settings("http://localhost:8020", "fixture", "fixture", "fixture-only")
        with patch("migration_lab.monitor.MirrorRPC") as rpc:
            rpc.OPERATIONS = {"monitor_info", "begin_import", "import_page", "finish_import"}
            rpc.return_value.call.side_effect = [{"server_version_info": [20, 0]}, 1,
                {"version": 1, "can_import": True, "monitoring_only": True}, {"state": "complete"}]
            client = MirrorClient(settings)
            client.call("finish_import", str(uuid.uuid4()))
            args = rpc.return_value.call.call_args.args
            self.assertEqual(args[5], "bambus.migration.source")
            with self.assertRaises(PilotError):
                client.call("write", {})

    def test_missing_importer_role_has_actionable_error(self):
        with patch("migration_lab.monitor.MirrorRPC") as rpc:
            rpc.OPERATIONS = {"monitor_info", "begin_import", "import_page", "finish_import"}
            rpc.return_value.call.side_effect = [{"server_version_info": [20, 0]}, 1,
                {"version": 1, "can_import": False, "monitoring_only": True}]
            with self.assertRaisesRegex(PilotError, "assign_migration_journal_importer_role"):
                MirrorClient(Settings("http://localhost:8020", "fixture", "fixture", "fixture-only"))
