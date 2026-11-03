import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest

from migration_lab.schema import compare, main, mapping_draft


def snapshot(source, target):
    return {"ODOO12": {"demo.model": source}, "ODOO20": {"demo.model": target}}


def field(kind="char", **kwargs):
    return {"type": kind, "readonly": False, "required": False, "store": True, **kwargs}


class SchemaComparisonTests(unittest.TestCase):
    def test_every_source_and_target_field_is_accounted_for(self):
        data = snapshot({"name": field(), "old": field()}, {"name": field(), "new": field(required=True)})
        result = compare(data)["models"]["demo.model"]
        rows = {row["field"]: row for row in result["fields"]}
        self.assertEqual(set(rows), {"name", "old", "new"})
        self.assertIn("source_only", rows["old"]["flags"])
        self.assertIn("new_required_field", rows["new"]["flags"])
        self.assertEqual(result["source_field_count"], 2)
        self.assertTrue(all(row["decision"] == "review_required" for row in rows.values()))

    def test_selection_order_is_not_a_change_and_labels_are_separate(self):
        old = field("selection", selection=[["a", "A"], ["b", "B"]])
        new = field("selection", selection=[["b", "New B"], ["a", "A"]])
        row = compare(snapshot({"type": old}, {"type": new}))["models"]["demo.model"]["fields"][0]
        self.assertIn("selection_labels_changed", row["flags"])
        self.assertNotIn("selection_keys_removed", row["flags"])
        self.assertNotIn("selection_keys_added", row["flags"])
        self.assertEqual(row["differences"]["selection_labels_changed"], ["b"])

    def test_removed_selection_keys_require_review(self):
        old = field("selection", selection=[["private", "Private"], ["contact", "Contact"]])
        new = field("selection", selection=[["contact", "Contact"]])
        row = compare(snapshot({"type": old}, {"type": new}))["models"]["demo.model"]["fields"][0]
        self.assertEqual(row["differences"]["selection_keys_removed"], ["private"])
        self.assertNotIn("same_name_scalar_candidate", row["flags"])

    def test_missing_metadata_never_implies_writeability(self):
        row = compare(snapshot({"name": field()}, {"name": {"type": "char"}}))["models"]["demo.model"]["fields"][0]
        self.assertIn("computed_status_unknown", row["flags"])
        self.assertIn("target_readonly_unknown", row["flags"])
        self.assertEqual(row["api_writeability"], "not_verified")
        self.assertNotIn("same_name_scalar_candidate", row["flags"])

    def test_dangerous_direct_copies_are_flagged(self):
        values = {"id": field("integer"), "relation": field("many2one", relation="res.partner"),
                  "image": field("binary"), "computed": field(compute="_compute_x"),
                  "company": field(company_dependent=True), "read_only": field(readonly=True)}
        rows = compare(snapshot(values, values))["models"]["demo.model"]["fields"]
        self.assertTrue(all("same_name_scalar_candidate" not in row["flags"] for row in rows))

    def test_type_and_relation_changes_are_explicit(self):
        source = {"description": field("text"), "channel": field("many2one", relation="mail.channel")}
        target = {"description": field("html"), "channel": field("many2one", relation="discuss.channel")}
        rows = {row["field"]: row for row in compare(snapshot(source, target))["models"]["demo.model"]["fields"]}
        self.assertIn("type_changed", rows["description"]["flags"])
        self.assertIn("relation_changed", rows["channel"]["flags"])

    def test_errors_and_invalid_metadata_are_rejected(self):
        valid = snapshot({"name": field()}, {"name": field()})
        bad_snapshots = [None, {}, {"ODOO12": {"x": {"error_type": "Fault"}}, "ODOO20": valid["ODOO20"]},
                         snapshot({"name": field()}, {"name": field(readonly="false")}),
                         snapshot({"name": field()}, {"name": field("selection", selection="callable")})]
        for data in bad_snapshots:
            with self.subTest(data=data), self.assertRaises(ValueError):
                compare(data)

    def test_comparison_does_not_mutate_input(self):
        data = snapshot({"name": field()}, {"name": field()})
        original = copy.deepcopy(data)
        self.assertFalse(compare(data)["migration_ready"])
        self.assertEqual(data, original)

    def test_cli_writes_reports_and_preserves_previous_outputs(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source, output = root / "snapshot.json", root / "comparison"
            source.write_text(json.dumps(snapshot({"name": field()}, {"name": field()})))
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(source), "--output-dir", str(output)]), 0)
            self.assertEqual({p.name for p in output.iterdir()}, {"comparison.json", "comparison.md", "fields.csv", "mapping-draft.json"})
            before = {p.name: p.read_bytes() for p in output.iterdir()}
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                main([str(source), "--output-dir", str(output)])
            self.assertEqual(error.exception.code, 1)
            self.assertEqual({p.name: p.read_bytes() for p in output.iterdir()}, before)

    def test_observed_lab_snapshot_regressions(self):
        root = Path(__file__).resolve().parents[1]
        data = json.loads((root / "odoo-schema-20261103-122514-132435.json").read_text())
        report = compare(data)
        self.assertEqual(sum(m["source_field_count"] for m in report["models"].values()), 245)
        self.assertEqual(sum(m["target_field_count"] for m in report["models"].values()), 319)
        products = {r["field"]: r for r in report["models"]["product.template"]["fields"]}
        partners = {r["field"]: r for r in report["models"]["res.partner"]["fields"]}
        self.assertIn("type_changed", products["description"]["flags"])
        self.assertIn("source_only", products["uom_po_id"]["flags"])
        self.assertIn("target_readonly", partners["is_company"]["flags"])
        self.assertEqual(partners["type"]["differences"]["selection_keys_removed"], ["private"])

    def test_mapping_draft_is_complete_but_never_approved(self):
        report = compare(snapshot({"name": field(), "old": field()}, {"name": field(), "new": field(required=True)}))
        report["input_sha256"] = "test-digest"
        draft = mapping_draft(report)
        self.assertEqual(draft["state"], "unapproved")
        rows = draft["models"]["demo.model"]["source_fields"]
        self.assertEqual({row["source_field"] for row in rows}, {"name", "old"})
        self.assertTrue(all(row["approved_target"] is None for row in rows))
        self.assertEqual(draft["models"]["demo.model"]["target_only_fields"][0]["required"], True)
