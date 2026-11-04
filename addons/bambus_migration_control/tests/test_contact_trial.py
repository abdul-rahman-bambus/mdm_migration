import base64
from copy import deepcopy

from odoo.exceptions import AccessError, UserError
from odoo.tests import TransactionCase, tagged
from odoo.tests.common import new_test_user

from .. import contact_contract as contract


@tagged("post_install", "-at_install")
class TestContactHistoryTrial(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.worker = new_test_user(cls.env, login="history-worker-test", groups="base.group_user,base.group_partner_manager,bambus_migration_control.group_contact_trial")
        cls.viewer = new_test_user(cls.env, login="history-viewer-test", groups="base.group_user,bambus_migration_control.group_migration_importer")
        cls.restricted = new_test_user(cls.env, login="history-restricted-test", groups="base.group_user,bambus_migration_control.group_contact_trial")

    def setUp(self):
        super().setUp()
        self.api = self.env["res.partner"].with_user(self.worker)
        self.data = {"version": contract.VERSION, "source_id": 2001,
                     "values": {"name": "Synthetic history trial", "email": "history@example.invalid", "phone": "+12025550100", "is_company": False, "active": True, "vat": "", "country_code": ""},
                     "messages": [{"id": 101, "date": "2019-10-01 09:30:00", "author": "Historical test author",
                                   "subject": "Historic note", "body": "<p>Original <b>note</b></p>", "kind": "comment", "subtype": "Note",
                                   "changes": [{"field": "Phone", "old": "100", "new": "200"}], "attachments": [301]}],
                     "attachments": [{"id": 301, "name": "synthetic.txt", "data": base64.b64encode(b"historical trial\n").decode()}]}

    def counts(self):
        return tuple(self.env[name].sudo().search_count([]) for name in ("res.partner", "mail.message", "ir.attachment", "bambus.contact.receipt", "mail.mail", "mail.notification", "mail.followers", "mail.activity"))

    def test_preview_writes_nothing(self):
        before = self.counts()
        result = self.api.bambus_trial_preview(self.data)
        self.assertEqual(result["operation"], "create")
        self.assertEqual((result["messages"], result["attachments"], result["tracking_changes"]), (1, 1, 1))
        self.assertEqual(self.counts(), before)

    def test_apply_preserves_readable_history_bytes_and_date_without_notifications(self):
        before = self.counts()
        result = self.api.bambus_trial_apply(self.data)
        after = self.counts()
        self.assertEqual(tuple(a-b for a,b in zip(after, before)), (1, 1, 1, 3, 0, 0, 0, 0))
        self.assertEqual(result["state"], "reconciled")
        item = next(i for i in result["items"] if i["kind"] == "message")
        message = self.env["mail.message"].browse(item["target_id"])
        self.assertEqual(str(message.date), "2019-10-01 09:30:00")
        self.assertIn("Historical test author", message.body)
        self.assertIn("Phone: 100 → 200", message.body)
        self.assertEqual(bytes(message.attachment_ids.raw), b"historical trial\n")
        self.assertFalse(message.author_id)
        self.assertEqual(message.subtype_id, self.env.ref("mail.mt_note"))

    def test_repeat_after_lost_response_does_not_duplicate(self):
        result = self.api.bambus_trial_apply(self.data)
        before = self.counts()
        repeated = self.api.bambus_trial_apply(self.data)
        self.assertEqual(repeated["target_id"], result["target_id"])
        self.assertEqual(repeated["operation"], "no_change")
        self.assertEqual(self.counts(), before)

    def test_contact_update_and_appended_note_only(self):
        first = self.api.bambus_trial_apply(self.data)
        self.data["values"]["phone"] = "+12025550101"
        self.data["messages"].append({**self.data["messages"][0], "id": 102, "date": "2019-10-02 09:30:00", "attachments": [], "changes": []})
        before = self.counts()
        result = self.api.bambus_trial_apply(self.data, first["target_id"], first["items"])
        self.assertEqual(result["operation"], "update")
        self.assertEqual(result["target_id"], first["target_id"])
        self.assertEqual(self.counts()[1], before[1] + 1)
        self.assertEqual(self.env["res.partner"].browse(first["target_id"]).phone, "+12025550101")

    def test_monitor_role_cannot_import_contacts_or_forge_receipts(self):
        with self.assertRaises(AccessError):
            self.api.with_user(self.viewer).bambus_trial_apply(self.data)
        with self.assertRaises(AccessError):
            self.env["bambus.contact.receipt"].with_user(self.worker).with_context(_bambus_import_token=True).create({})

    def test_original_message_change_and_removal_are_blocked(self):
        self.api.bambus_trial_apply(self.data)
        changed = deepcopy(self.data)
        changed["messages"][0]["body"] = "Edited old history"
        with self.assertRaisesRegex(UserError, "source_history_changed"):
            self.api.bambus_trial_apply(changed)
        changed["messages"] = []
        with self.assertRaisesRegex(UserError, "source_history_removed"):
            self.api.bambus_trial_apply(changed)

    def test_target_message_or_attachment_change_blocks_reuse(self):
        result = self.api.bambus_trial_apply(self.data)
        message_id = next(i["target_id"] for i in result["items"] if i["kind"] == "message")
        self.env["mail.message"].browse(message_id).write({"body": "Changed target note"})
        with self.assertRaisesRegex(UserError, "target_missing_or_modified"):
            self.api.bambus_trial_apply(self.data)

    def test_restore_missing_receipt_blocked_by_independent_expected_items(self):
        result = self.api.bambus_trial_apply(self.data)
        expected = deepcopy(result["items"])
        expected[0]["source_id"] = 9999
        before = self.counts()
        with self.assertRaisesRegex(UserError, "history_restore"):
            self.api.bambus_trial_apply(self.data, result["target_id"], expected)
        self.assertEqual(self.counts(), before)

    def test_target_contact_marker_and_reused_ids_blocked(self):
        result = self.api.bambus_trial_apply(self.data)
        self.env["res.partner"].browse(result["target_id"]).write({"ref": "changed-marker"})
        with self.assertRaises(UserError):
            self.api.bambus_trial_apply(self.data, result["target_id"])

    def test_failed_import_rolls_back_all_contact_resources(self):
        before = self.counts()
        from unittest.mock import patch
        model = type(self.env["mail.message"])
        with self.assertRaises(UserError), self.env.cr.savepoint():
            with patch.object(model, "create", side_effect=UserError("synthetic_failure")):
                self.api.bambus_trial_apply(self.data)
        self.assertEqual(self.counts(), before)

    def test_history_external_images_are_not_replayed(self):
        self.data["messages"][0]["body"] = '<p>Original</p><img src="https://example.invalid/tracker"><script>alert(1)</script>'
        result = self.api.bambus_trial_apply(self.data)
        message_id = next(i["target_id"] for i in result["items"] if i["kind"] == "message")
        body = str(self.env["mail.message"].browse(message_id).body)
        self.assertNotIn('<img', body)
        self.assertNotIn('<script', body)

    def test_payload_cannot_set_recipients_or_business_fields(self):
        self.data["values"]["supplier_rank"] = 1
        with self.assertRaisesRegex(UserError, "invalid_contact_trial_payload"):
            self.api.bambus_trial_apply(self.data)

    def test_existing_contact_candidate_is_not_merged_or_duplicated(self):
        self.env["res.partner"].with_context(tracking_disable=True).create({"name": self.data["values"]["name"]})
        before = self.counts()
        with self.assertRaisesRegex(UserError, "existing_contact_candidate"):
            self.api.bambus_trial_apply(self.data)
        self.assertEqual(self.counts(), before)

    def test_trial_role_does_not_bypass_native_contact_create_permissions(self):
        with self.assertRaises(AccessError):
            self.api.with_user(self.restricted).bambus_trial_apply(self.data)

    def test_archived_company_flags_are_preserved(self):
        self.data["values"].update(is_company=True, active=False, vat="SYNTHETIC-TAX-001")
        result = self.api.bambus_trial_apply(self.data)
        record = self.env["res.partner"].browse(result["target_id"])
        self.assertTrue(record.is_company)
        self.assertFalse(record.active)
        self.assertEqual(self.api.bambus_trial_apply(self.data)["operation"], "no_change")

    def test_changed_attachment_bytes_block_rerun(self):
        result = self.api.bambus_trial_apply(self.data)
        target_id = next(i["target_id"] for i in result["items"] if i["kind"] == "attachment")
        self.env["ir.attachment"].browse(target_id).write({"raw": b"changed bytes"})
        with self.assertRaisesRegex(UserError, "target_missing_or_modified"):
            self.api.bambus_trial_apply(self.data)

    def test_unrepresentable_legacy_company_classification_blocks_preview(self):
        self.data["values"]["is_company"] = True
        before = self.counts()
        with self.assertRaisesRegex(UserError, "company_classification"):
            self.api.bambus_trial_preview(self.data)
        self.assertEqual(self.counts(), before)

    def test_country_maps_by_code_without_copying_database_id(self):
        self.data["values"]["country_code"] = "OM"
        result = self.api.bambus_trial_apply(self.data)
        self.assertEqual(self.env["res.partner"].browse(result["target_id"]).country_id, self.env.ref("base.om"))
