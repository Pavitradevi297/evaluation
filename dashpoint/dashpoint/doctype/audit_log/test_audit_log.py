import frappe
from frappe.tests.utils import FrappeTestCase


class TestAuditLog(FrappeTestCase):
    def test_audit_log_schema(self):
        meta = frappe.get_meta("Audit Log")
        for fieldname in ("doctype_name", "document_name", "action", "user", "timestamp"):
            self.assertTrue(meta.has_field(fieldname))

    def test_update_creates_audit_record(self):
        zone = frappe.get_doc({"doctype": "Delivery Zone", "zone_name": "Audit Test Zone"}).insert(ignore_permissions=True)
        zone.description = "updated"
        zone.save(ignore_permissions=True)
        self.assertTrue(
            frappe.db.exists(
                "Audit Log",
                {"doctype_name": "Delivery Zone", "document_name": zone.name, "action": "on_update"},
            )
        )
