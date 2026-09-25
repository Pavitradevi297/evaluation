import frappe
from frappe.tests.utils import FrappeTestCase


class TestPackagingMaterial(FrappeTestCase):
    def test_material_code_is_uppercase_and_named_by_series(self):
        doc = frappe.get_doc({
            "doctype": "Packaging Material", "material_name": "Bubble Wrap",
            "material_code": "bubble1", "unit_cost": 2, "charge_to_customer": 3,
        }).insert(ignore_permissions=True)
        self.assertEqual(doc.material_code, "BUBBLE1")
        self.assertTrue(doc.name.startswith("PKG-"))

    def test_customer_charge_cannot_be_less_than_cost(self):
        doc = frappe.get_doc({
            "doctype": "Packaging Material", "material_name": "Bad Material",
            "material_code": "BAD1", "unit_cost": 5, "charge_to_customer": 4,
        })
        with self.assertRaises(frappe.ValidationError):
            doc.insert(ignore_permissions=True)
