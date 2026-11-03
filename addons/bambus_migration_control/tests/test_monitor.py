from copy import deepcopy
import uuid

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user


@tagged("post_install", "-at_install")
class TestMigrationMonitor(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.importer = new_test_user(cls.env, login="monitor-importer-test", groups="base.group_user,bambus_migration_control.group_migration_importer")
        cls.viewer = new_test_user(cls.env, login="monitor-viewer-test", groups="base.group_user,bambus_migration_control.group_migration_viewer")
        cls.other = new_test_user(cls.env, login="monitor-other-test", groups="base.group_user")

    def setUp(self):
        super().setUp()
        self.api = self.env["bambus.migration.source"].with_user(self.importer)
        journal = str(uuid.uuid4())
        revision = "a" * 64
        self.manifest = {"journal_key": journal, "revision": revision,
                         "snapshot_key": str(uuid.uuid5(uuid.UUID(journal), revision)),
                         "captured_at": "2026-01-01T00:10:00+00:00", "counts": {"runs": 2, "events": 2, "mappings": 1}}
        self.runs = []
        for n in (1, 2):
            self.runs.append({"id": str(uuid.uuid4()), "namespace": "b" * 64, "operation": "apply", "state": "reconciled",
                "source_identity": "loopback:8012/odoo12_demo/res.partner", "target_identity": "loopback:8020/odoo20_migration/res.partner",
                "mapping_version": "synthetic-contact-v1", "source_id": 101, "target_id": 901,
                "payload_digest": "c" * 64, "error_code": None,
                "started_at": f"2026-01-01T00:0{n}:00.123456+00:00", "finished_at": f"2026-01-01T00:0{n}:01.123456+00:00"})
        self.events = [{"id": n, "run_id": run["id"], "state": "reconciled", "details": {},
                        "created_at": run["finished_at"]} for n, run in enumerate(self.runs, 1)]
        self.mappings = [{"namespace": "b" * 64, "source_model": "res.partner", "source_id": 101,
            "target_model": "res.partner", "target_id": 901, "marker": "bambus-pilot-target:" + "b" * 64,
            "mapping_version": "synthetic-contact-v1", "payload_digest": "c" * 64,
            "last_run": self.runs[-1]["id"], "state": "reconciled", "updated_at": self.runs[-1]["finished_at"]}]

    def import_all(self, manifest=None):
        manifest = manifest or self.manifest
        self.api.begin_import(manifest)
        for kind, rows in (("runs", self.runs), ("events", self.events), ("mappings", self.mappings)):
            if rows:
                self.api.import_page(manifest["snapshot_key"], kind, rows)
        return self.api.finish_import(manifest["snapshot_key"])

    def source(self):
        return self.env["bambus.migration.source"].search([("journal_key", "=", self.manifest["journal_key"])])

    def test_reruns_group_into_one_record_and_keep_all_attempts(self):
        self.import_all()
        source = self.source()
        self.assertEqual((source.record_count, source.run_count, source.reconciled_count, source.mapping_count), (1, 2, 1, 1))
        record = self.env["bambus.migration.record"].search([("snapshot_id", "=", source.snapshot_id.id)])
        self.assertEqual(record.latest_run_id.journal_run_id, self.runs[-1]["id"])
        self.assertEqual(record.target_record_id, 901)
        self.assertEqual(len(record.run_ids), 2)
        self.assertEqual(source.action_reload()["tag"], "reload")

    def test_import_is_idempotent_and_completed_pages_are_immutable(self):
        self.import_all()
        self.assertEqual(self.api.begin_import(self.manifest)["state"], "unchanged")
        self.assertEqual(self.api.finish_import(self.manifest["snapshot_key"])["state"], "complete")
        with self.assertRaises(UserError):
            self.api.import_page(self.manifest["snapshot_key"], "runs", self.runs)
        self.assertEqual(self.source().run_count, 2)

    def test_interrupted_pages_resume_without_duplicates(self):
        self.api.begin_import(self.manifest)
        for _ in range(2):
            self.api.import_page(self.manifest["snapshot_key"], "runs", self.runs)
        self.assertFalse(self.source().snapshot_id)
        self.assertEqual(self.api.begin_import(self.manifest)["state"], "importing")
        self.import_all()
        self.assertEqual(self.source().run_count, 2)

    def test_viewer_cannot_import_or_forge_write_context(self):
        with self.assertRaises(AccessError):
            self.env["bambus.migration.source"].with_user(self.viewer).begin_import(self.manifest)
        with self.assertRaises(AccessError):
            self.env["bambus.migration.source"].with_user(self.importer).with_context(_bambus_import_token=True).create({"journal_key": str(uuid.uuid4())})

    def test_importer_cannot_directly_edit_or_delete_mirrors(self):
        self.import_all()
        source = self.source().with_user(self.importer)
        with self.assertRaises(AccessError):
            source.write({"record_count": 999})
        with self.assertRaises(AccessError):
            source.sudo().unlink()
        self.assertEqual(source.with_user(self.viewer).record_count, 1)

    def test_unassigned_internal_user_cannot_read_tracking(self):
        self.import_all()
        with self.assertRaises(AccessError):
            self.env["bambus.migration.source"].with_user(self.other).search([])

    def test_incomplete_snapshot_cannot_replace_previous_complete_view(self):
        self.import_all()
        previous = self.source().snapshot_id
        next_manifest = deepcopy(self.manifest)
        next_manifest.update(revision="d" * 64, snapshot_key=str(uuid.uuid5(uuid.UUID(self.manifest["journal_key"]), "d" * 64)), captured_at="2026-01-01T00:20:00+00:00")
        self.api.begin_import(next_manifest)
        self.api.import_page(next_manifest["snapshot_key"], "runs", self.runs)
        with self.assertRaises(UserError):
            self.api.finish_import(next_manifest["snapshot_key"])
        self.assertEqual(self.source().snapshot_id, previous)
        self.assertTrue(previous.is_current)

    def test_unreconciled_run_cannot_claim_success(self):
        self.events[-1]["state"] = "loaded"
        self.api.begin_import(self.manifest)
        self.api.import_page(self.manifest["snapshot_key"], "runs", self.runs)
        self.api.import_page(self.manifest["snapshot_key"], "events", self.events)
        self.api.import_page(self.manifest["snapshot_key"], "mappings", self.mappings)
        with self.assertRaises(UserError):
            self.api.finish_import(self.manifest["snapshot_key"])
        self.assertFalse(self.source().snapshot_id)

    def test_latest_failure_does_not_hide_historical_success_mapping(self):
        self.runs[-1].update(state="failed", error_code="rpc_fault")
        self.events[-1].update(state="failed", details={"error_code": "rpc_fault"})
        self.mappings[0]["last_run"] = self.runs[0]["id"]
        self.import_all()
        source = self.source()
        self.assertEqual((source.record_count, source.attention_count, source.reconciled_count, source.mapping_count), (1, 1, 0, 1))
        record = self.env["bambus.migration.record"].search([("snapshot_id", "=", source.snapshot_id.id)])
        self.assertEqual(record.latest_state, "failed")
        self.assertEqual(record.mapping_id.last_run_id.state, "reconciled")

    def test_incomplete_run_is_attention_not_a_live_process_claim(self):
        self.runs[-1].update(state="running", finished_at=None, payload_digest=None)
        self.events[-1].update(state="load_intent", details={"operation": "create"})
        self.mappings[0]["last_run"] = self.runs[0]["id"]
        self.import_all()
        self.assertEqual(self.source().attention_count, 1)
        self.assertEqual(self.source().reconciled_count, 0)

    def test_business_values_are_not_accepted_as_event_details(self):
        self.events[0]["details"] = {"password": "fabricated-canary"}
        self.api.begin_import(self.manifest)
        self.api.import_page(self.manifest["snapshot_key"], "runs", self.runs)
        with self.assertRaises(UserError) as caught:
            self.api.import_page(self.manifest["snapshot_key"], "events", self.events)
        self.assertNotIn("fabricated-canary", str(caught.exception))

    def test_mapping_conflicting_with_run_is_rejected(self):
        self.mappings[0]["target_id"] = 999
        self.api.begin_import(self.manifest)
        self.api.import_page(self.manifest["snapshot_key"], "runs", self.runs)
        with self.assertRaises(UserError):
            self.api.import_page(self.manifest["snapshot_key"], "mappings", self.mappings)

    def test_counts_cannot_be_overfilled(self):
        self.manifest["counts"]["runs"] = 1
        self.api.begin_import(self.manifest)
        with self.assertRaises(UserError):
            self.api.import_page(self.manifest["snapshot_key"], "runs", self.runs)

    def test_microsecond_order_and_readable_record_search(self):
        self.runs[0].update(started_at="2026-01-01T00:02:00.000001+00:00", finished_at="2026-01-01T00:02:00.000002+00:00")
        self.runs[1].update(started_at="2026-01-01T00:02:00.000003+00:00", finished_at="2026-01-01T00:02:00.000004+00:00")
        self.events[0]["created_at"] = self.runs[0]["finished_at"]
        self.events[1]["created_at"] = self.runs[1]["finished_at"]
        self.import_all()
        record = self.env["bambus.migration.record"].with_user(self.viewer).search([("name", "ilike", "Contact 101")])
        self.assertEqual(len(record), 1)
        self.assertEqual(record.latest_run_id.journal_run_id, self.runs[1]["id"])

    def test_role_capability_is_clear_without_granting_read_or_write(self):
        self.assertTrue(self.api.monitor_info()["can_import"])
        info = self.env["bambus.migration.source"].with_user(self.other).monitor_info()
        self.assertFalse(info["can_import"])
        self.assertTrue(info["monitoring_only"])

    def test_older_completed_import_cannot_replace_newer_snapshot(self):
        self.api.begin_import(self.manifest)
        for kind, rows in (("runs", self.runs), ("events", self.events), ("mappings", self.mappings)):
            self.api.import_page(self.manifest["snapshot_key"], kind, rows)
        newer = deepcopy(self.manifest)
        newer.update(revision="d" * 64, snapshot_key=str(uuid.uuid5(uuid.UUID(self.manifest["journal_key"]), "d" * 64)), captured_at="2026-01-01T00:20:00+00:00")
        self.import_all(newer)
        active = self.source().snapshot_id
        result = self.api.finish_import(self.manifest["snapshot_key"])
        self.assertFalse(result["promoted"])
        self.assertEqual(self.source().snapshot_id, active)
        self.assertTrue(active.is_current)

    def test_existing_snapshot_manifest_counts_cannot_change(self):
        self.import_all()
        changed = deepcopy(self.manifest)
        changed["counts"]["events"] += 1
        with self.assertRaises(UserError):
            self.api.begin_import(changed)

    def test_empty_journal_is_imported_without_manufactured_records(self):
        self.manifest["counts"] = {"runs": 0, "events": 0, "mappings": 0}
        self.runs, self.events, self.mappings = [], [], []
        self.import_all()
        source = self.source()
        self.assertEqual((source.record_count, source.run_count, source.mapping_count), (0, 0, 0))
        self.assertEqual(source.snapshot_id.state, "complete")

    def test_target_navigation_requires_live_marker_and_respects_viewer_access(self):
        partner = self.env["res.partner"].create({"name": "Synthetic control target", "ref": self.mappings[0]["marker"]})
        for run in self.runs:
            run["target_id"] = partner.id
        self.mappings[0]["target_id"] = partner.id
        self.import_all()
        record = self.env["bambus.migration.record"].with_user(self.viewer).search([("snapshot_id", "=", self.source().snapshot_id.id)])
        self.assertEqual(record.action_open_target()["res_id"], partner.id)
        partner.write({"ref": "unrelated-record"})
        with self.assertRaises(UserError):
            record.action_open_target()

    def test_changed_import_replaces_current_rows_without_counting_archives(self):
        self.import_all()
        old = self.source().snapshot_id
        newer = deepcopy(self.manifest)
        newer.update(revision="e" * 64, snapshot_key=str(uuid.uuid5(uuid.UUID(self.manifest["journal_key"]), "e" * 64)), captured_at="2026-01-01T00:30:00+00:00")
        self.import_all(newer)
        self.assertFalse(old.is_current)
        self.assertNotEqual(self.source().snapshot_id, old)
        domain = [("current", "=", True), ("snapshot_id.source_id", "=", self.source().id)]
        self.assertEqual(self.env["bambus.migration.record"].search_count(domain), 1)
        self.assertEqual(self.env["bambus.migration.run"].search_count(domain), 2)
        self.assertEqual(len(self.source().snapshot_ids), 2)
