# Copyright (c) 2026, Pavitradevi and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class AuditLog(Document):
    pass


def log_document_event(doc, method=None):
    """Create an Audit Log entry for document events."""

    # Do not audit Audit Log documents themselves
    if doc.doctype == "Audit Log":
        return

    audit_log = frappe.new_doc("Audit Log")

    audit_log.doctype_name = doc.doctype
    audit_log.document_name = doc.name
    audit_log.action = method or "Unknown"
    audit_log.user = frappe.session.user
    audit_log.timestamp = frappe.utils.now_datetime()

    audit_log.insert(ignore_permissions=True)
