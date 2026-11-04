import base64
from copy import deepcopy
import unittest

from migration_lab.contact_history import Source, TrialRPC, contract, validate_plan
from migration_lab.journal import PilotError


def sample():
    return {"version": contract.VERSION, "source_id": 41,
            "values": {"name": "Synthetic contact", "email": "trial@example.invalid", "phone": "+12025550100", "is_company": False, "active": True, "vat": "", "country_code": ""},
            "messages": [{"id": 101, "date": "2019-10-01 09:30:00", "author": "Synthetic author", "subject": "Note",
                          "body": "<p>Historic note</p>", "kind": "comment", "subtype": "Note", "changes": [{"field": "Phone", "old": "100", "new": "200"}], "attachments": [301]}],
            "attachments": [{"id": 301, "name": "history.txt", "data": base64.b64encode(b"synthetic history\n").decode()}]}


class TestContactHistory(unittest.TestCase):
    def test_valid_contract_and_stable_scoped_namespace(self):
        self.assertEqual(contract.validate(sample()), sample())
        self.assertEqual(contract.namespace(41), contract.namespace(41))
        self.assertNotEqual(contract.namespace(41), contract.namespace(42))

    def test_contract_rejects_business_scope_expansion_and_recipients(self):
        for key in ("supplier_rank", "parent_id", "password"):
            data = sample()
            data["values"][key] = 1
            with self.assertRaises(ValueError):
                contract.validate(data)
        data = sample()
        data["messages"][0]["recipients"] = [1]
        with self.assertRaises(ValueError):
            contract.validate(data)

    def test_dates_duplicates_attachment_links_and_base64_fail_closed(self):
        changes = [lambda d: d["messages"][0].update(date="2019-02-31 00:00:00"),
                   lambda d: d["attachments"][0].update(data="not base64"),
                   lambda d: d["messages"][0].update(attachments=[999]),
                   lambda d: d["messages"].append(deepcopy(d["messages"][0]))]
        for change in changes:
            data = sample()
            change(data)
            with self.assertRaises(ValueError):
                contract.validate(data)

    def test_strict_trial_limits(self):
        data = sample()
        data["attachments"][0]["data"] = base64.b64encode(b"x" * (contract.MAX_FILE + 1)).decode()
        with self.assertRaises(ValueError):
            contract.validate(data)
        data = sample()
        data["messages"][0]["body"] = "x" * 65537
        with self.assertRaises(ValueError):
            contract.validate(data)

    def test_plan_requires_bounded_unique_selected_contacts(self):
        row = {"source_id": 41, "digest": contract.digest(sample()), "expected_target": None,
               "operation": "create", "messages": 1, "attachments": 1, "tracking_changes": 1}
        self.assertEqual(validate_plan({"version": contract.VERSION, "contacts": [row]}), [row])
        for rows in ([], [row, row], [row] * 6):
            with self.assertRaises(PilotError):
                validate_plan({"version": contract.VERSION, "contacts": rows})

    def test_rpc_write_allowlist_is_separate_from_source(self):
        from migration_lab.preflight import ReadOnlyRPC
        self.assertNotIn("create", ReadOnlyRPC.OPERATIONS)
        self.assertNotIn("write", TrialRPC.OPERATIONS)
        self.assertNotIn("message_post", TrialRPC.OPERATIONS)
        self.assertEqual(len(TrialRPC.OPERATIONS), 3)

    def test_only_static_trial_fault_codes_are_reported(self):
        import xmlrpc.client
        rpc = object.__new__(TrialRPC)
        safe = xmlrpc.client.Fault(1, "Traceback\nodoo.exceptions.UserError: trial_history_restore_requires_review\n")
        self.assertEqual(rpc.failure_code(safe), "trial_history_restore_requires_review")
        private = xmlrpc.client.Fault(1, "UserError: customer password private@example.invalid")
        self.assertEqual(rpc.failure_code(private), "rpc_fault")

    def test_native_odoo_fault_formats_propagate_only_allowlisted_labels(self):
        import xmlrpc.client
        from unittest.mock import patch
        from migration_lab.preflight import ProbeFailure, Settings
        code = "trial_company_classification_requires_mapping"
        faults = [xmlrpc.client.Fault(2, code),
                  xmlrpc.client.Fault("warning -- UserError\n\n" + code, ""),
                  xmlrpc.client.Fault(2, "private@example.invalid"),
                  xmlrpc.client.Fault(2, code + " private@example.invalid")]
        for fault, expected in zip(faults, [code, code, "rpc_fault", "rpc_fault"]):
            rpc = TrialRPC(Settings("http://127.0.0.1:8020", "odoo20_migration", "synthetic", "synthetic"))
            payload = xmlrpc.client.dumps(fault).encode()
            with patch.object(rpc.opener, "open") as open_request:
                open_request.return_value.__enter__.return_value.read.return_value = payload
                with self.assertRaises(ProbeFailure) as caught:
                    rpc.call("object", "execute_kw", "odoo20_migration", 2, "synthetic", "res.partner", "bambus_trial_preview", [], {})
            self.assertEqual(str(caught.exception), expected)

    def test_source_extracts_tracking_attachment_and_original_date(self):
        source = object.__new__(Source)
        data = sample()
        tracking_row = {"id": 201, "field_desc": "Phone", "field_type": "char", "old_value_char": "100", "new_value_char": "200"}
        def read(model, domain, fields, cap):
            if model == "res.partner":
                return [{"id": 41, "parent_id": False, **data["values"]}]
            if model == "res.users":
                return []
            if model == "mail.message":
                return [{"id": 101, "date": "2019-10-01 09:30:00", "author_id": [7, "Synthetic author"], "subject": "Note",
                         "body": "<p>Historic note</p>", "message_type": "comment", "subtype_id": [2, "Note"], "tracking_value_ids": [201], "attachment_ids": [301]}]
            if model == "mail.tracking.value":
                return [tracking_row]
            return [{"id": 301, "name": "history.txt", "type": "binary", "file_size": len(b"synthetic history\n"), "datas": data["attachments"][0]["data"]}]
        source.read = read
        self.assertEqual(source.extract(41), data)
        tracking_row.update(field_type="monetary", old_value_monetary=12.5, new_value_monetary=15.0,
                            old_value_float=99.0, new_value_float=100.0)
        self.assertEqual(source.extract(41)["messages"][0]["changes"], [{"field": "Phone", "old": "12.5", "new": "15.0"}])
        tracking_row.update(field_type="boolean", old_value_integer=0, new_value_integer=1)
        self.assertEqual(source.extract(41)["messages"][0]["changes"], [{"field": "Phone", "old": "False", "new": "True"}])

    def test_source_blocks_child_contact_and_user_contact(self):
        source = object.__new__(Source)
        source.read = lambda *a: [{"parent_id": [1, "Parent"]}]
        with self.assertRaisesRegex(PilotError, "top_level"):
            source.extract(41)
        source.read = lambda model, *a: [{"parent_id": False}] if model == "res.partner" else [{"id": 1}]
        with self.assertRaisesRegex(PilotError, "user_contacts"):
            source.extract(41)
