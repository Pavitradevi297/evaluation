import frappe
from frappe.tests.utils import FrappeTestCase


class TestDeliveryZone(FrappeTestCase):
    def test_required_seed_zones_exist_after_install(self):
        for name in ("North Zone", "Central Zone", "South Zone"):
            self.assertTrue(frappe.db.exists("Delivery Zone", name))
