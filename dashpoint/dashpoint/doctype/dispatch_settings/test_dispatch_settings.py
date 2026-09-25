import frappe
from frappe.tests.utils import FrappeTestCase


class TestDispatchSettings(FrappeTestCase):
    def test_defaults(self):
        self.assertEqual(frappe.db.get_single_value("Dispatch Settings", "max_delivery_attempts"), 3)
        self.assertEqual(frappe.db.get_single_value("Dispatch Settings", "default_delivery_fee"), 60)
        self.assertEqual(frappe.db.get_single_value("Dispatch Settings", "low_stock_alert_enabled"), 1)
