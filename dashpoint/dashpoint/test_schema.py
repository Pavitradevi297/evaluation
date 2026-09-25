import frappe
from frappe.tests.utils import FrappeTestCase


class TestDashPointSchema(FrappeTestCase):
    def test_core_doctypes_exist(self):
        for doctype in (
            "Delivery Zone", "Rider", "Packaging Material", "Dispatch Settings",
            "Delivery Order", "Packaging Usage Entry", "Delivery Receipt", "Audit Log",
        ):
            self.assertTrue(frappe.db.exists("DocType", doctype), doctype)

    def test_delivery_order_required_fields(self):
        meta = frappe.get_meta("Delivery Order")
        required = {
            "customer_name": "Data",
            "customer_phone": "Data",
            "pickup_address": "Small Text",
            "delivery_address": "Small Text",
            "delivery_zone": "Link",
            "package_description": "Text Editor",
            "delivery_attempts_count": "Int",
            "delivered_on": "Datetime",
        }
        for fieldname, fieldtype in required.items():
            df = meta.get_field(fieldname)
            self.assertIsNotNone(df)
            self.assertEqual(df.fieldtype, fieldtype)

    def test_dispatch_settings_exact_fields(self):
        meta = frappe.get_meta("Dispatch Settings")
        for fieldname in (
            "dispatch_center_name", "ops_manager_email", "max_delivery_attempts",
            "default_delivery_fee", "low_stock_alert_enabled",
        ):
            self.assertTrue(meta.has_field(fieldname), fieldname)

    def test_permission_matrix_matches_core_roles(self):
        expected = {
            "Delivery Zone": {"DP Dispatch Staff": (1,0,0,0), "DP Rider": (1,0,0,0), "DP Ops Manager": (1,1,1,0)},
            "Rider": {"DP Dispatch Staff": (1,0,0,0), "DP Rider": (1,1,0,0), "DP Ops Manager": (1,1,1,0)},
            "Packaging Material": {"DP Dispatch Staff": (1,0,0,0), "DP Rider": (1,0,0,0), "DP Ops Manager": (1,1,1,0)},
            "Delivery Order": {"DP Dispatch Staff": (1,1,1,0), "DP Rider": (1,1,0,1), "DP Ops Manager": (1,1,1,1)},
            "Delivery Receipt": {"DP Dispatch Staff": (1,0,0,0), "DP Ops Manager": (1,1,1,1)},
        }
        for doctype, role_matrix in expected.items():
            meta = frappe.get_meta(doctype)
            actual = {
                p.role: (p.read, p.write, p.create, p.submit)
                for p in meta.permissions
                if p.role in role_matrix
            }
            for role, values in role_matrix.items():
                self.assertEqual(actual.get(role), values, f"{doctype} / {role}")
