import json

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from .. import protocol

_IMPORT_TOKEN = object()
STATE_SELECTION = [("running", "Incomplete"), ("seeded", "Seeded"), ("source_updated", "Awaiting sync"),
                   ("dry_run", "Preview"), ("reconciled", "Reconciled"), ("failed", "Failed")]


class ImportProtected(models.AbstractModel):
    _name = "bambus.migration.protected"
    _description = "Protected journal mirror"

    def _assert_import(self):
        if self.env.context.get("_bambus_import_token") is not _IMPORT_TOKEN:
            raise AccessError(self.env._("Journal mirrors can only be changed by the authorized importer."))

    @api.model_create_multi
    def create(self, vals_list):
        self._assert_import()
        return super().create(vals_list)

    def write(self, values):
        self._assert_import()
        return super().write(values)

    def unlink(self):
        raise AccessError(self.env._("Journal history cannot be deleted from this app."))


class Mirror(models.AbstractModel):
    _name = "bambus.migration.mirror"
    _inherit = "bambus.migration.protected"
    _description = "Snapshot-linked journal mirror"

    snapshot_id = fields.Many2one("bambus.migration.snapshot", required=True, ondelete="restrict", index=True)
    current = fields.Boolean(related="snapshot_id.is_current", store=True, index=True)


class Source(models.Model):
    _name = "bambus.migration.source"
    _inherit = "bambus.migration.protected"
    _description = "Migration journal overview"
    _rec_name = "name"

    name = fields.Char(default="Contact migration journal", required=True)
    journal_key = fields.Char(required=True, index=True)
    snapshot_id = fields.Many2one("bambus.migration.snapshot", string="Active snapshot", ondelete="restrict")
    captured_at = fields.Datetime(related="snapshot_id.captured_at")
    imported_at = fields.Datetime(related="snapshot_id.completed_at")
    record_count = fields.Integer(string="Tracked records")
    reconciled_count = fields.Integer(string="Latest reconciled")
    attention_count = fields.Integer(string="Need attention")
    pending_count = fields.Integer(string="Awaiting sync / preview")
    run_count = fields.Integer(string="Execution attempts")
    failure_count = fields.Integer(string="Historical failed attempts")
    mapping_count = fields.Integer(string="Last reconciled mappings")
    event_count = fields.Integer(string="Journal events")
    last_checked_at = fields.Datetime(string="Last monitor check")
    monitor_state = fields.Selection([("empty", "Waiting for import"), ("importing", "Import incomplete"), ("ready", "Imported")], default="empty")
    snapshot_ids = fields.One2many("bambus.migration.snapshot", "source_id", string="Import history")
    _journal_unique = models.Constraint("UNIQUE(journal_key)", "Journal identity must be unique.")

    def _import_env(self):
        if not self.env.user.has_group("bambus_migration_control.group_migration_importer"):
            raise AccessError(self.env._("The Migration Journal Importer role is required."))
        return self.sudo().with_context(_bambus_import_token=_IMPORT_TOKEN).env

    @api.model
    def monitor_info(self):
        return {"version": 1, "can_import": self.env.user.has_group("bambus_migration_control.group_migration_importer"),
                "monitoring_only": True}

    @api.model
    def begin_import(self, manifest):
        env = self._import_env()
        try:
            protocol.manifest(manifest)
        except ValueError:
            raise UserError(self.env._("Invalid monitoring manifest.")) from None
        # Serialize imports for this journal for this RPC transaction.
        env.cr.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [manifest["journal_key"]])
        source = env[self._name].search([("journal_key", "=", manifest["journal_key"])], limit=1)
        if not source:
            source = env[self._name].create({"journal_key": manifest["journal_key"]})
        source.write({"last_checked_at": fields.Datetime.now()})
        snapshot = env["bambus.migration.snapshot"].search([("key", "=", manifest["snapshot_key"])], limit=1)
        if snapshot:
            if snapshot.source_id != source or snapshot.revision != manifest["revision"]:
                raise UserError(self.env._("Snapshot identity conflict."))
            if {"runs": snapshot.expected_runs, "events": snapshot.expected_events, "mappings": snapshot.expected_mappings} != manifest["counts"]:
                raise UserError(self.env._("Snapshot manifest changed without a new revision."))
            if snapshot.state == "complete" and source.snapshot_id != snapshot:
                raise UserError(self.env._("Journal revision reverted; review journal restore before importing."))
            source.write({"monitor_state": "ready" if snapshot.state == "complete" else "importing"})
            return {"state": "unchanged" if snapshot.state == "complete" else "importing"}
        source.write({"monitor_state": "importing"})
        env["bambus.migration.snapshot"].create({
            "key": manifest["snapshot_key"], "source_id": source.id, "revision": manifest["revision"],
            "captured_at": protocol.timestamp(manifest["captured_at"]),
            "expected_runs": manifest["counts"]["runs"], "expected_events": manifest["counts"]["events"],
            "expected_mappings": manifest["counts"]["mappings"],
        })
        return {"state": "importing"}

    @api.model
    def import_page(self, snapshot_key, kind, rows):
        env = self._import_env()
        try:
            protocol.uid(snapshot_key)
            protocol.page(kind, rows)
        except ValueError:
            raise UserError(self.env._("Invalid monitoring page.")) from None
        snapshot = env["bambus.migration.snapshot"].search([("key", "=", snapshot_key)], limit=1)
        if not snapshot:
            raise UserError(self.env._("No importable snapshot was found."))
        env.cr.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [snapshot.source_id.journal_key])
        env.cr.execute("SELECT id FROM bambus_migration_snapshot WHERE id=%s FOR UPDATE", [snapshot.id])
        snapshot.invalidate_recordset(["state"])
        if snapshot.state != "importing":
            raise UserError(self.env._("Completed snapshots are immutable."))
        model = env[{"runs": "bambus.migration.run", "events": "bambus.migration.event", "mappings": "bambus.migration.mapping"}[kind]]
        for item in rows:
            values = {"snapshot_id": snapshot.id}
            if kind == "runs":
                key_field, key = "journal_run_id", item["id"]
                values.update({name: item[name] or False for name in (
                    "namespace", "operation", "source_identity", "target_identity", "mapping_version", "state", "payload_digest", "error_code")})
                values.update(source_record_id=item["source_id"] or 0, target_record_id=item["target_id"] or 0,
                              started_at=protocol.timestamp(item["started_at"]), finished_at=protocol.timestamp(item["finished_at"], nullable=True))
            else:
                run_key = item["run_id"] if kind == "events" else item["last_run"]
                run = env["bambus.migration.run"].search([("snapshot_id", "=", snapshot.id), ("journal_run_id", "=", run_key)], limit=1)
                if not run:
                    raise UserError(self.env._("Import runs before dependent journal entries."))
                if kind == "events":
                    key_field, key = "journal_event_id", item["id"]
                    values.update(run_id=run.id, state=item["state"], details=json.dumps(item["details"], sort_keys=True),
                                  occurred_at=protocol.timestamp(item["created_at"]))
                else:
                    key_field, key = "namespace", item["namespace"]
                    if (run.namespace != key or run.state != "reconciled" or run.source_record_id != item["source_id"]
                            or run.target_record_id != item["target_id"] or run.payload_digest != item["payload_digest"]
                            or run.mapping_version != item["mapping_version"]):
                        raise UserError(self.env._("Mapping evidence conflicts with its reconciled run."))
                    values.update({name: item[name] for name in ("source_model", "target_model", "marker", "mapping_version", "payload_digest", "state")})
                    values.update(source_record_id=item["source_id"], target_record_id=item["target_id"],
                                  last_run_id=run.id, updated_at=protocol.timestamp(item["updated_at"]))
            values[key_field] = key
            existing = model.search([("snapshot_id", "=", snapshot.id), (key_field, "=", key)], limit=1)
            if existing:
                existing.write(values)
            else:
                model.create(values)
        expected = {"runs": snapshot.expected_runs, "events": snapshot.expected_events, "mappings": snapshot.expected_mappings}[kind]
        if model.search_count([("snapshot_id", "=", snapshot.id)]) > expected:
            raise UserError(self.env._("Page exceeds the journal manifest count."))
        return {"state": "importing", "rows": len(rows)}

    @api.model
    def finish_import(self, snapshot_key):
        env = self._import_env()
        snapshot = env["bambus.migration.snapshot"].search([("key", "=", snapshot_key)], limit=1)
        if not snapshot:
            raise UserError(self.env._("Snapshot was not found."))
        env.cr.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", [snapshot.source_id.journal_key])
        env.cr.execute("SELECT id FROM bambus_migration_snapshot WHERE id=%s FOR UPDATE", [snapshot.id])
        snapshot.invalidate_recordset(["state"])
        if snapshot.state == "complete":
            return {"state": "complete"}
        for model, expected in (("run", snapshot.expected_runs), ("event", snapshot.expected_events), ("mapping", snapshot.expected_mappings)):
            if env["bambus.migration." + model].search_count([("snapshot_id", "=", snapshot.id)]) != expected:
                raise UserError(self.env._("Snapshot counts do not match the journal manifest."))
        runs = env["bambus.migration.run"].search([("snapshot_id", "=", snapshot.id)], order="started_at, journal_run_id")
        mappings = env["bambus.migration.mapping"].search([("snapshot_id", "=", snapshot.id)])
        grouped = {}
        for run in runs:
            grouped.setdefault(run.namespace, []).append(run)
            if run.state == "reconciled" and not any(event.state == "reconciled" for event in run.event_ids):
                raise UserError(self.env._("A reconciled run has no reconciliation event."))
        for namespace, history in grouped.items():
            latest = history[-1]
            mapping = mappings.filtered(lambda rec: rec.namespace == namespace)
            record = env["bambus.migration.record"].create({
                "snapshot_id": snapshot.id, "namespace": namespace, "latest_run_id": latest.id,
                "latest_state": latest.state, "source_record_id": latest.source_record_id or (mapping.source_record_id if mapping else 0),
                "target_record_id": latest.target_record_id or (mapping.target_record_id if mapping else 0),
                "mapping_id": mapping.id if mapping else False,
            })
            for run in history:
                run.write({"record_id": record.id})
                if run.state in {"failed", "running"}:
                    env["bambus.migration.issue"].create({"snapshot_id": snapshot.id, "run_id": run.id,
                        "error_code": run.error_code or "incomplete_run_requires_review",
                        "severity": "error" if run.state == "failed" else "warning"})
        # A complete source snapshot becomes visible in one Odoo transaction.
        source = snapshot.source_id
        env.cr.execute("SELECT id FROM bambus_migration_source WHERE id=%s FOR UPDATE", [source.id])
        source.invalidate_recordset(["snapshot_id"])
        if source.snapshot_id and source.snapshot_id.captured_at > snapshot.captured_at:
            snapshot.write({"state": "complete", "completed_at": fields.Datetime.now()})
            return {"state": "complete", "promoted": False}
        if source.snapshot_id:
            source.snapshot_id.write({"is_current": False})
        snapshot.write({"state": "complete", "is_current": True, "completed_at": fields.Datetime.now()})
        records = env["bambus.migration.record"].search([("snapshot_id", "=", snapshot.id)])
        source.write({"snapshot_id": snapshot.id, "monitor_state": "ready", "record_count": len(records),
            "reconciled_count": len(records.filtered(lambda r: r.latest_state == "reconciled")),
            "attention_count": len(records.filtered(lambda r: r.latest_state in {"failed", "running"})),
            "pending_count": len(records.filtered(lambda r: r.latest_state in {"seeded", "source_updated", "dry_run"})),
            "run_count": len(runs), "failure_count": len(runs.filtered(lambda r: r.state == "failed")),
            "mapping_count": len(mappings), "event_count": snapshot.expected_events})
        return {"state": "complete", "records": len(records)}

    def action_reload(self):
        return {"type": "ir.actions.client", "tag": "reload"}

    def _open(self, model):
        self.ensure_one()
        return {"type": "ir.actions.act_window", "name": self.env._("Migration history"),
                "res_model": "bambus.migration." + model, "view_mode": "list,form",
                "domain": [("snapshot_id", "=", self.snapshot_id.id)]}

    def action_records(self):
        return self._open("record")

    def action_runs(self):
        return self._open("run")

    def action_issues(self):
        return self._open("issue")

    def action_mappings(self):
        return self._open("mapping")


class Snapshot(models.Model):
    _name = "bambus.migration.snapshot"
    _inherit = "bambus.migration.protected"
    _description = "Monitoring snapshot"
    _rec_name = "key"
    _order = "captured_at desc"
    key = fields.Char(required=True, index=True)
    source_id = fields.Many2one("bambus.migration.source", required=True, ondelete="restrict")
    revision = fields.Char(required=True)
    state = fields.Selection([("importing", "Import incomplete"), ("complete", "Imported")], default="importing", required=True)
    captured_at = fields.Datetime(required=True)
    completed_at = fields.Datetime()
    is_current = fields.Boolean(default=False, index=True)
    expected_runs = fields.Integer()
    expected_events = fields.Integer()
    expected_mappings = fields.Integer()
    _key_unique = models.Constraint("UNIQUE(key)", "Snapshot identity must be unique.")


class Run(models.Model):
    _name = "bambus.migration.run"
    _inherit = "bambus.migration.mirror"
    _description = "Migration execution attempt"
    _rec_name = "journal_run_id"
    _order = "started_at desc, journal_run_id"
    journal_run_id = fields.Char(required=True, index=True)
    namespace = fields.Char(required=True, index=True)
    operation = fields.Selection([(v, v.replace("-", " ").replace("_", " ").title()) for v in sorted(protocol.OPERATIONS)], required=True)
    state = fields.Selection(STATE_SELECTION, required=True, index=True)
    source_identity = fields.Char()
    target_identity = fields.Char()
    source_record_id = fields.Integer(string="Source ID")
    target_record_id = fields.Integer(string="Target ID")
    mapping_version = fields.Char()
    payload_digest = fields.Char()
    error_code = fields.Char(index=True)
    started_at = fields.Datetime()
    finished_at = fields.Datetime()
    duration = fields.Float(compute="_compute_duration", string="Seconds")
    event_ids = fields.One2many("bambus.migration.event", "run_id")
    record_id = fields.Many2one("bambus.migration.record", ondelete="restrict")
    _run_unique = models.Constraint("UNIQUE(snapshot_id,journal_run_id)", "Run already imported.")

    @api.depends("started_at", "finished_at")
    def _compute_duration(self):
        for run in self:
            run.duration = (run.finished_at - run.started_at).total_seconds() if run.finished_at and run.started_at else 0


class Event(models.Model):
    _name = "bambus.migration.event"
    _inherit = "bambus.migration.mirror"
    _description = "Migration journal event"
    _order = "journal_event_id"
    journal_event_id = fields.Integer(required=True)
    run_id = fields.Many2one("bambus.migration.run", required=True, ondelete="restrict")
    state = fields.Char(required=True)
    details = fields.Text()
    occurred_at = fields.Datetime()
    _event_unique = models.Constraint("UNIQUE(snapshot_id,journal_event_id)", "Event already imported.")


class Mapping(models.Model):
    _name = "bambus.migration.mapping"
    _inherit = "bambus.migration.mirror"
    _description = "Last reconciled record mapping"
    _rec_name = "namespace"
    namespace = fields.Char(required=True, index=True)
    source_model = fields.Char()
    source_record_id = fields.Integer(string="Source ID")
    target_model = fields.Char()
    target_record_id = fields.Integer(string="Target ID")
    marker = fields.Char()
    mapping_version = fields.Char()
    payload_digest = fields.Char()
    last_run_id = fields.Many2one("bambus.migration.run", ondelete="restrict")
    state = fields.Selection([("reconciled", "Last reconciled")])
    updated_at = fields.Datetime()
    _mapping_unique = models.Constraint("UNIQUE(snapshot_id,namespace)", "Mapping already imported.")


class Record(models.Model):
    _name = "bambus.migration.record"
    _inherit = "bambus.migration.mirror"
    _description = "Tracked migration record"
    _rec_name = "name"
    name = fields.Char(compute="_compute_name", store=True)
    namespace = fields.Char(required=True)
    source_record_id = fields.Integer(string="Source ID")
    target_record_id = fields.Integer(string="Target ID")
    latest_run_id = fields.Many2one("bambus.migration.run", ondelete="restrict")
    latest_state = fields.Selection(STATE_SELECTION, index=True)
    mapping_id = fields.Many2one("bambus.migration.mapping", ondelete="restrict")
    run_ids = fields.One2many("bambus.migration.run", "record_id")
    _record_unique = models.Constraint("UNIQUE(snapshot_id,namespace)", "Record already grouped.")

    @api.depends("source_record_id", "target_record_id")
    def _compute_name(self):
        for record in self:
            record.name = "Contact %s → %s" % (record.source_record_id or "—", record.target_record_id or "—")

    def action_open_target(self):
        self.ensure_one()
        if not self.target_record_id:
            raise UserError(self.env._("This record has no target ID."))
        if self.mapping_id and self.mapping_id.target_record_id != self.target_record_id:
            raise UserError(self.env._("Latest target ID conflicts with the last reconciled mapping; review the run."))
        partner = self.env["res.partner"].browse(self.target_record_id).exists()
        expected_marker = self.mapping_id.marker or "bambus-pilot-target:" + self.namespace
        if not partner or partner.ref != expected_marker:
            raise UserError(self.env._("The historical target is missing or its ID was reused. Review restore/mapping history."))
        return {"type": "ir.actions.act_window", "res_model": "res.partner", "res_id": self.target_record_id, "view_mode": "form"}


class Issue(models.Model):
    _name = "bambus.migration.issue"
    _inherit = "bambus.migration.mirror"
    _description = "Journal failure or incomplete attempt"
    _rec_name = "error_code"
    run_id = fields.Many2one("bambus.migration.run", ondelete="restrict", required=True)
    error_code = fields.Char(required=True)
    severity = fields.Selection([("warning", "Warning"), ("error", "Error")], required=True)
