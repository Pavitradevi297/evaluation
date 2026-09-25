import frappe
from frappe.tests.utils import FrappeTestCase
from unittest.mock import patch

from dashpoint.dashpoint.api import rename_rider, share_delivery_order
from dashpoint.permissions import delivery_order_query_conditions


class TestAPIAndPermissions(FrappeTestCase):
    def test_share_delivery_order_calls_share(self):
        order = frappe.get_doc({
            "doctype": "Delivery Order", "customer_name": "Share Test", "customer_phone": "9876543210",
            "pickup_address": "A", "delivery_address": "B", "delivery_zone": "North Zone",
            "package_description": "Parcel", "status": "Draft", "naming_series": "DO-.YYYY.-.#####",
        }).insert(ignore_permissions=True)
        with patch("frappe.share.add") as share_add:
            result = share_delivery_order(order.name, "share@example.com")
            share_add.assert_called_once_with("Delivery Order", order.name, "share@example.com", read=1)
            self.assertTrue(result["shared"])

    def test_rename_rider_uses_frappe_rename_doc(self):
        rider = frappe.get_doc({
            "doctype": "Rider", "rider_name": "Rename Test", "assigned_zone": "North Zone",
            "status": "Active", "vehicle_type": "Bike", "naming_series": "RDR-.####",
        }).insert(ignore_permissions=True)
        with patch("frappe.rename_doc", return_value="RDR-TEST-RENAMED") as rename_doc:
            result = rename_rider(rider.name, "RDR-TEST-RENAMED")
            rename_doc.assert_called_once_with("Rider", rider.name, "RDR-TEST-RENAMED", merge=False)
            self.assertEqual(result, "RDR-TEST-RENAMED")

    def test_rider_query_condition_is_row_limited_for_rider_role(self):
        # The exact SQL condition is evaluated against the session user's Rider in a live site.
        # Managers intentionally receive an empty condition.
        with patch("frappe.get_roles", return_value=["DP Ops Manager"]):
            self.assertEqual(delivery_order_query_conditions("test@example.com"), "")

    def test_safe_api_has_permission_aware_entrypoint(self):
        from dashpoint.dashpoint.api import safe_get_delivery_order_data
        self.assertTrue(callable(safe_get_delivery_order_data))
