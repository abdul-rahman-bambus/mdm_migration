"""Explicit lab-only atomic history import. Never message_post or _notify_thread."""

import base64
from html import escape

from markupsafe import Markup
from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

from .. import contact_contract as contract
from .monitor import _IMPORT_TOKEN

QUIET = {"tracking_disable": True, "mail_create_nosubscribe": True, "mail_create_nolog": True,
         "mail_notify_force_send": False, "mail_notrack": True}


class ContactReceipt(models.Model):
    _name = "bambus.contact.receipt"
    _inherit = "bambus.migration.protected"
    _description = "Protected lab contact history identity receipt"

    namespace = fields.Char(required=True, index=True)
    kind = fields.Selection([("contact", "Contact"), ("message", "Message"), ("attachment", "Attachment")], required=True)
    source_id = fields.Integer(required=True)
    target_id = fields.Integer(required=True)
    source_digest = fields.Char(required=True)
    target_digest = fields.Char(required=True)
    _identity_unique = models.Constraint("UNIQUE(namespace,kind,source_id)", "Source history identity must be unique.")


class ContactTrial(models.Model):
    _inherit = "res.partner"

    @api.model
    def bambus_trial_info(self):
        return {"version": contract.VERSION,
                "can_apply": self.env.user.has_group("bambus_migration_control.group_contact_trial"),
                "lab_database": self.env.cr.dbname == "odoo20_migration"}

    def _bambus_gate(self, data):
        if (self.env.cr.dbname != "odoo20_migration" or not
                self.env.user.has_group("bambus_migration_control.group_contact_trial")):
            raise AccessError("Contact trial requires its dedicated role and laboratory database.")
        try:
            contract.validate(data)
        except (ValueError, TypeError, OverflowError):
            raise UserError("invalid_contact_trial_payload") from None
        namespace = contract.namespace(data["source_id"])
        self.env.cr.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", [namespace])
        # Only identity receipts use sudo. Business records always use caller ACLs.
        receipts = self.env["bambus.contact.receipt"].sudo().with_context(_bambus_import_token=_IMPORT_TOKEN)
        return namespace, receipts

    def _bambus_fingerprint(self, kind, record):
        if kind == "contact":
            return contract.digest({key: record[key] if key in {"is_company", "active"} else record[key] or ""
                                    for key in contract.FIELDS} | {"ref": record.ref})
        if kind == "attachment":
            return contract.digest({"name": record.name, "data": base64.b64encode(bytes(record.raw)).decode(),
                                    "model": record.res_model, "res_id": record.res_id, "public": record.public,
                                    "type": record.type})
        return contract.digest({"body": str(record.body or ""), "date": fields.Datetime.to_string(record.date),
                                "subject": record.subject or "", "model": record.model, "res_id": record.res_id,
                                "author": record.author_id.id, "type": record.message_type,
                                "subtype": record.subtype_id.id, "recipients": record.partner_ids.ids,
                                "attachments": sorted(record.attachment_ids.ids)})

    def _bambus_existing(self, receipts, namespace, kind, source_id):
        receipt = receipts.search([("namespace", "=", namespace), ("kind", "=", kind), ("source_id", "=", source_id)], limit=1)
        if not receipt:
            return receipt, None
        model = {"contact": "res.partner", "message": "mail.message", "attachment": "ir.attachment"}[kind]
        record = self.env[model].with_context(active_test=False).browse(receipt.target_id).exists()
        if not record or self._bambus_fingerprint(kind, record) != receipt.target_digest:
            raise UserError("trial_target_missing_or_modified_requires_review")
        return receipt, record

    def _bambus_values(self, data):
        values = {k: v for k, v in data["values"].items() if k not in {"is_company", "country_code"}}
        country_code = data["values"]["country_code"]
        countries = self.env["res.country"].search([("code", "=", country_code)], limit=2) if country_code else self.env["res.country"]
        if country_code and len(countries) != 1:
            raise UserError("trial_country_requires_unique_mapping")
        values["country_id"] = countries.id if countries else False
        # The tested Odoo 20 computes is_company from its commercial entity and
        # VAT. Do not force a readonly field or fabricate a VAT to match v12.
        prospective = self.new(values)
        prospective._compute_is_company()
        if bool(prospective.is_company) != data["values"]["is_company"]:
            raise UserError("trial_company_classification_requires_mapping")
        return values

    def _bambus_preview(self, data, expected_target, expected_items=None):
        namespace, receipts = self._bambus_gate(data)
        self._bambus_values(data)
        receipt, contact = self._bambus_existing(receipts, namespace, "contact", data["source_id"])
        marker = "bambus-pilot-target:" + namespace
        marked = self.with_context(active_test=False).search([("ref", "=", marker)])
        if (contact and marked != contact) or (not contact and marked):
            raise UserError("trial_contact_marker_conflict")
        if not contact:
            candidates = [("name", "=ilike", data["values"]["name"])]
            if data["values"]["email"]:
                candidates = ["|", ("email", "=ilike", data["values"]["email"]), *candidates]
            if self.with_context(active_test=False).search_count(candidates, limit=1):
                raise UserError("trial_existing_contact_candidate_requires_review")
        if expected_target is not None and (type(expected_target) is not int or not contact or contact.id != expected_target):
            raise UserError("trial_target_restore_requires_review")
        if not isinstance(expected_items or [], list) or len(expected_items or []) > 120:
            raise UserError("invalid_trial_expected_items")
        for item in expected_items or []:
            if (not isinstance(item, dict) or set(item) != {"kind", "source_id", "target_id", "digest"}
                    or item["kind"] not in {"message", "attachment"}):
                raise UserError("invalid_trial_expected_items")
            old, actual = self._bambus_existing(receipts, namespace, item["kind"], item["source_id"])
            if not actual or actual.id != item["target_id"] or old.source_digest != item["digest"]:
                raise UserError("trial_history_restore_requires_review")
        items, changed = [], False
        present = {("contact", data["source_id"])}
        for kind, rows in (("attachment", data["attachments"]), ("message", data["messages"])):
            for item in rows:
                old, actual = self._bambus_existing(receipts, namespace, kind, item["id"])
                item_digest = contract.digest(item)
                if old and old.source_digest != item_digest:
                    raise UserError("trial_source_history_changed_requires_review")
                present.add((kind, item["id"]))
                items.append({"kind": kind, "source_id": item["id"], "target_id": actual.id if actual else False,
                              "digest": item_digest})
                changed |= not bool(old)
        if any((row.kind, row.source_id) not in present for row in receipts.search([("namespace", "=", namespace)])):
            raise UserError("trial_source_history_removed_requires_review")
        if contact:
            changed |= receipt.source_digest != contract.digest(data["values"])
        return {"operation": "create" if not contact else "update" if changed else "no_change",
                "target_id": contact.id if contact else False, "items": items,
                "messages": len(data["messages"]), "attachments": len(data["attachments"]),
                "tracking_changes": sum(len(m["changes"]) for m in data["messages"])}

    @api.model
    def bambus_trial_preview(self, data, expected_target=None, expected_items=None):
        return self._bambus_preview(data, expected_target, expected_items)

    def _bambus_body(self, message):
        # Preserve readable content safely; do not carry active source image URLs,
        # tracking pixels, scripts or source-database attachment links into target.
        from odoo.tools import html2plaintext
        original = html2plaintext(message["body"])
        header = (f"Imported Odoo 12 history · {message['kind']} / {message['subtype']} · source message {message['id']} · "
                  f"original author: {message['author'] or 'Unknown'} · UTC {message['date']}")
        body = "<p><strong>" + escape(header) + "</strong></p><pre>" + escape(original) + "</pre>"
        for change in message["changes"]:
            body += "<p>" + escape(change["field"]) + ": " + escape(change["old"]) + " → " + escape(change["new"]) + "</p>"
        return Markup(body)

    @api.model
    def bambus_trial_apply(self, data, expected_target=None, expected_items=None):
        # One RPC transaction per contact: a failure rolls back contact, all
        # historical messages/attachments and receipts together.
        result = self._bambus_preview(data, expected_target, expected_items)
        namespace, receipts = self._bambus_gate(data)
        quiet = self.with_context(**QUIET)
        if result["target_id"]:
            contact = quiet.browse(result["target_id"])
            if result["operation"] != "no_change":
                contact.write(self._bambus_values(data))
        else:
            contact = quiet.create({**self._bambus_values(data), "ref": "bambus-pilot-target:" + namespace})

        def remember(kind, source_id, record, source_digest):
            values = {"namespace": namespace, "kind": kind, "source_id": source_id, "target_id": record.id,
                      "source_digest": source_digest, "target_digest": self._bambus_fingerprint(kind, record)}
            old = receipts.search([("namespace", "=", namespace), ("kind", "=", kind), ("source_id", "=", source_id)], limit=1)
            if old:
                old.write(values)
            else:
                receipts.create(values)

        attachment_map = {}
        by_key = {(i["kind"], i["source_id"]): i for i in result["items"]}
        for item in data["attachments"]:
            receipt = by_key["attachment", item["id"]]
            attachment = self.env["ir.attachment"].browse(receipt["target_id"]) if receipt["target_id"] else self.env["ir.attachment"].with_context(**QUIET).create({
                "name": item["name"], "raw": base64.b64decode(item["data"], validate=True), "res_model": "res.partner", "res_id": contact.id,
                "type": "binary", "public": False,
            })
            # Odoo may transform images; verify actual bytes, never trust create.
            actual = base64.b64encode(bytes(attachment.raw)).decode()
            if actual != item["data"]:
                raise UserError("trial_attachment_bytes_changed")
            attachment_map[item["id"]] = attachment.id
            remember("attachment", item["id"], attachment, receipt["digest"])
        for item in data["messages"]:
            receipt = by_key["message", item["id"]]
            if receipt["target_id"]:
                continue
            # Direct message create has no notification dispatch in native Odoo;
            # no message_post, recipients, followers, outgoing mail or activities.
            message = self.env["mail.message"].with_context(**QUIET).create({
                "model": "res.partner", "res_id": contact.id, "body": self._bambus_body(item),
                "subject": item["subject"], "date": item["date"], "message_type": "comment",
                "subtype_id": self.env.ref("mail.mt_note").id, "author_id": False,
                "email_from": False, "reply_to": False, "partner_ids": [],
                "attachment_ids": [(6, 0, [attachment_map[n] for n in item["attachments"]])],
            })
            if (fields.Datetime.to_string(message.date) != item["date"] or message.res_id != contact.id
                    or set(message.attachment_ids.ids) != {attachment_map[n] for n in item["attachments"]}
                    or message.partner_ids or str(message.body) != str(self._bambus_body(item))):
                raise UserError("trial_message_readback_failed")
            remember("message", item["id"], message, receipt["digest"])
        contact.invalidate_recordset()
        actual = {key: contact[key] if key in {"is_company", "active"} else contact[key] or "" for key in contract.FIELDS}
        if actual != data["values"]:
            raise UserError("trial_contact_readback_failed")
        remember("contact", data["source_id"], contact, contract.digest(data["values"]))
        verified = self._bambus_preview(data, contact.id)
        return {**verified, "state": "reconciled", "operation": result["operation"]}
