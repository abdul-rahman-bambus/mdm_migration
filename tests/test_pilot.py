from contextlib import contextmanager
import unittest
from unittest.mock import patch

from migration_lab.journal import PilotError
from migration_lab.pilot import identity, migrate, specification
from migration_lab.preflight import ProbeFailure, Settings


class MemoryAPI:
    def __init__(self):
        self.rows = {}
        self.creates = self.updates = 0
        self.lose_response = False
        self.interrupt = False
        self.corrupt = False

    def find(self, marker):
        rows = [dict(row) for row in self.rows.values() if row["ref"] == marker]
        if len(rows) > 1:
            raise PilotError("duplicate_or_invalid_pilot_marker")
        return rows[0] if rows else None

    def validate_create(self):
        return []

    def create(self, values):
        self.creates += 1
        key = max(self.rows, default=0) + 1
        self.rows[key] = {"id": key, **values}
        if self.corrupt:
            self.rows[key]["phone"] = "+12025550199"
        if self.lose_response:
            self.lose_response = False
            raise ProbeFailure("timeout")
        if self.interrupt:
            self.interrupt = False
            raise KeyboardInterrupt()
        return key

    def write(self, record_id, values):
        self.updates += 1
        self.rows[record_id].update(values)


class MemoryJournal:
    def __init__(self):
        self.runs, self.events, self.mappings, self.namespaces = {}, [], {}, {}

    @contextmanager
    def lock(self, namespace):
        yield

    def start(self, *args):
        key = str(len(self.runs) + 1)
        self.runs[key] = "running"
        self.namespaces[key] = args[0]
        return key

    def event(self, run_id, state, **details):
        self.events.append((run_id, state, details))

    def mapping(self, namespace):
        return self.mappings.get(namespace)

    def has_intent(self, namespace, state, operation=None):
        return any(self.namespaces[run_id] == namespace and event == state
                   and (operation is None or details.get("operation") == operation)
                   for run_id, event, details in self.events)

    def finish(self, run_id, state, *args):
        self.runs[run_id] = state

    def reconciled(self, namespace, run_id, source_id, target_id, marker, version, digest):
        self.mappings[namespace] = {"source_id": source_id, "target_id": target_id, "marker": marker, "mapping_version": version}
        self.runs[run_id] = "reconciled"


class PilotEngineTests(unittest.TestCase):
    def setUp(self):
        self.source, self.target, self.journal = MemoryAPI(), MemoryAPI(), MemoryJournal()
        self.spec = specification("smoke-001", "source", "target")
        self.run_action("seed")

    def run_action(self, action="sync", apply=False, phone=None):
        return migrate(self.source, self.target, self.journal, self.spec, "source", "target", action, apply, phone)

    def test_dry_run_has_no_target_writes_or_mapping(self):
        result = self.run_action()
        self.assertEqual(result["proposed_operation"], "create")
        self.assertEqual(self.target.creates, 0)
        self.assertEqual(self.journal.mappings, {})

    def test_apply_reconciles_and_second_apply_creates_no_duplicate(self):
        first = self.run_action(apply=True)
        second = self.run_action(apply=True)
        self.assertEqual(first["state"], "reconciled")
        self.assertEqual(second["operation"], "no_change")
        self.assertEqual(first["target_id"], second["target_id"])
        self.assertEqual(self.target.creates, 1)

    def test_source_change_updates_same_target(self):
        self.run_action(apply=True)
        self.run_action("change-source", phone="+12025550123")
        result = self.run_action(apply=True)
        self.assertEqual(result["operation"], "update")
        self.assertEqual(self.target.rows[result["target_id"]]["phone"], "+12025550123")
        self.assertEqual(self.target.creates, 1)

    def test_lost_create_response_recovers_by_marker(self):
        self.target.lose_response = True
        with self.assertRaises(ProbeFailure):
            self.run_action(apply=True)
        self.assertIn("failed", self.journal.runs.values())
        result = self.run_action(apply=True)
        self.assertEqual(result["state"], "reconciled")
        self.assertEqual(self.target.creates, 1)

    def test_interruption_preserves_pending_run_and_retry_does_not_duplicate(self):
        self.target.interrupt = True
        with self.assertRaises(KeyboardInterrupt):
            self.run_action(apply=True)
        self.assertIn("running", self.journal.runs.values())
        self.assertEqual(self.run_action(apply=True)["state"], "reconciled")
        self.assertEqual(self.target.creates, 1)

    def test_create_success_with_corrupt_readback_is_not_reconciled(self):
        self.target.corrupt = True
        with self.assertRaisesRegex(PilotError, "target_reconciliation_failed"):
            self.run_action(apply=True)
        self.assertEqual(self.journal.mappings, {})
        self.assertIn("failed", self.journal.runs.values())

    def test_non_synthetic_source_is_refused(self):
        self.source.rows[1]["name"] = "Real contact"
        with self.assertRaisesRegex(PilotError, "record_is_not"):
            self.run_action(apply=True)
        self.assertEqual(self.target.creates, 0)

    def test_missing_target_after_mapping_is_blocked(self):
        self.run_action(apply=True)
        self.target.rows.clear()  # Simulated restore; no real Odoo data is deleted.
        with self.assertRaisesRegex(PilotError, "target_restore_or_mapping_conflict"):
            self.run_action(apply=True)
        self.assertEqual(self.target.creates, 1)

    def test_reused_target_id_with_foreign_marker_is_blocked(self):
        self.run_action(apply=True)
        self.target.rows[1]["ref"] = "foreign"
        with self.assertRaisesRegex(PilotError, "target_restore_or_mapping_conflict"):
            self.run_action(apply=True)
        self.assertEqual(self.target.updates, 0)

    def test_journal_intent_failure_prevents_target_write(self):
        original = self.journal.event

        def event(run_id, state, **details):
            if state == "load_intent":
                raise RuntimeError("simulated journal failure")
            return original(run_id, state, **details)

        with patch.object(self.journal, "event", side_effect=event), self.assertRaises(PilotError):
            self.run_action(apply=True)
        self.assertEqual(self.target.creates, 0)

    def test_repeated_seed_does_not_duplicate_source(self):
        self.run_action("seed")
        self.assertEqual(self.source.creates, 1)

    def test_pilot_cannot_use_arbitrary_databases_or_remote_urls(self):
        for url, database in [("https://example.com", "odoo12_demo"), ("http://localhost:8012", "production")]:
            with self.subTest(url=url), self.assertRaises(PilotError):
                identity(Settings(url, database, "user", "unused"), 8012, "odoo12_demo")

    def test_changed_mapping_manifest_blocks_before_any_target_write(self):
        with patch("migration_lab.pilot.Path.read_text", return_value="{}"), self.assertRaisesRegex(
                PilotError, "pilot_mapping_manifest_requires_review"):
            self.run_action(apply=True)
        self.assertEqual(self.target.creates, 0)

    def test_non_synthetic_phone_cannot_be_written_to_source(self):
        with self.assertRaisesRegex(PilotError, "phone_must_be_reserved_synthetic_number"):
            self.run_action("change-source", phone="+441234567890")
        self.assertEqual(self.source.updates, 0)

    def test_hidden_target_after_create_is_not_duplicated_on_retry(self):
        with patch.object(self.target, "find", return_value=None):
            with self.assertRaises(PilotError):
                self.run_action(apply=True)
            with self.assertRaisesRegex(PilotError, "unresolved_target_create_requires_review"):
                self.run_action(apply=True)
        self.assertEqual(self.target.creates, 1)

    def test_source_seed_with_hidden_marker_and_prior_intent_is_blocked(self):
        with patch.object(self.source, "find", return_value=None), self.assertRaisesRegex(
                PilotError, "unresolved_source_create_requires_review"):
            self.run_action("seed")
        self.assertEqual(self.source.creates, 1)
