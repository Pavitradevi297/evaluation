import frappe
from frappe.tests.utils import FrappeTestCase


class TestRider(FrappeTestCase):
    def test_rider_schema_supports_owner_permission(self):
        meta = frappe.get_meta("Rider")
        self.assertTrue(meta.has_field("user"))
        self.assertTrue(meta.has_field("assigned_zone"))
