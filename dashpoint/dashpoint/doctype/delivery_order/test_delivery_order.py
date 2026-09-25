from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase


def make_delivery_zone(name="North Zone"):
    if frappe.db.exists("Delivery Zone", name):
        return frappe.get_doc("Delivery Zone", name)
    return frappe.get_doc({"doctype": "Delivery Zone", "zone_name": name}).insert(ignore_permissions=True)


def make_rider(zone="North Zone", **overrides):
    values = {
        "doctype": "Rider",
        "name": f"TEST-RIDER-{frappe.generate_hash(length=8).upper()}",
        "rider_name": f"Test Rider {frappe.generate_hash(length=6)}",
        "assigned_zone": zone,
        "status": "Active",
        "vehicle_type": "Bike",
        "naming_series": "TEST-RDR-.########",
    }
    values.update(overrides)
    return frappe.get_doc(values).insert(ignore_permissions=True)


def make_packaging_material(stock_qty=10, **overrides):
    values = {
        "doctype": "Packaging Material",
        "material_name": "Test Box",
        "material_code": f"TESTBOX{frappe.generate_hash(length=6).upper()}",
        "unit_cost": 2,
        "charge_to_customer": 3,
        "stock_qty": stock_qty,
        "reorder_level": 20,
        "is_active": 1,
    }
    values.update(overrides)
    return frappe.get_doc(values).insert(ignore_permissions=True)


def make_delivery_order(zone="North Zone", rider=None, submittable=False, **overrides):
    rider = rider or make_rider(zone=zone)
    material = overrides.pop("_material", None)
    values = {
        "doctype": "Delivery Order", "customer_name": "Test Customer", "customer_phone": "9876543210",
        "customer_email": "customer@example.com", "pickup_address": "Pickup Address",
        "delivery_address": "Delivery Address", "delivery_zone": zone,
        "package_description": "Test package", "assigned_rider": rider.name,
        "priority": "Standard", "status": "Delivered" if submittable else "Draft",
        "payment_status": "Unpaid", "naming_series": "DO-.YYYY.-.#####",
    }
    if material:
        values["packaging_used"] = [{"material": material.name, "quantity": 1}]
    values.update(overrides)
    doc = frappe.get_doc(values).insert(ignore_permissions=True)
    if submittable:
        doc.submit()
        doc.reload()
    return doc


class TestDeliveryOrder(FrappeTestCase):
    # FrappeTestCase automatically rolls back test database changes, so most
    # tests do not need a custom tearDown that manually deletes test records.

    def test_invalid_phone_is_rejected(self):
        order = frappe.get_doc({
            "doctype": "Delivery Order", "customer_name": "Bad Phone", "customer_phone": "12345",
            "pickup_address": "A", "delivery_address": "B", "delivery_zone": "North Zone",
            "package_description": "Parcel", "status": "Draft", "naming_series": "DO-.YYYY.-.#####",
        })
        with self.assertRaises(frappe.ValidationError):
            order.insert(ignore_permissions=True)

    def test_packaging_total_and_final_amount(self):
        material = make_packaging_material()
        order = make_delivery_order(_material=material, delivery_fee=60)
        order.reload()
        self.assertEqual(order.packaging_total, 3)
        self.assertEqual(order.final_amount, 63)

    def test_before_submit_requires_delivered(self):
        order = make_delivery_order(status="In Transit")
        with self.assertRaises(frappe.ValidationError):
            order.submit()

    def test_before_submit_rejects_insufficient_stock(self):
        material = make_packaging_material(stock_qty=0)
        order = make_delivery_order(_material=material, status="Delivered")
        with self.assertRaises(frappe.ValidationError):
            order.submit()

    @patch("frappe.enqueue")
    def test_submit_deducts_stock_creates_receipt_and_enqueues_confirmation(self, enqueue):
        material = make_packaging_material(stock_qty=5)
        order = make_delivery_order(_material=material, status="Delivered")
        order.submit()
        self.assertEqual(frappe.db.get_value("Packaging Material", material.name, "stock_qty"), 4)
        receipt = frappe.db.get_value("Delivery Receipt", {"delivery_order": order.name}, "name")
        self.assertTrue(receipt)
        self.assertEqual(enqueue.call_count, 2)
        enqueue.assert_any_call(
            "dashpoint.dashpoint.api.send_delivery_confirmation",
            queue="short",
            delivery_order_name=order.name,
        )
        enqueue.assert_any_call(
            "dashpoint.dashpoint.api.send_webhook",
            queue="short",
            delivery_order_name=order.name,
        )

    @patch("requests.post")
    def test_webhook_sends_delivery_completed_payload(self, post):
        settings = frappe.get_single("Dispatch Settings")
        settings.webhook_url = "https://example.com/webhook"
        settings.save()

        material = make_packaging_material(stock_qty=5)
        order = make_delivery_order(_material=material, status="Delivered")

        post.return_value.raise_for_status.return_value = None

        from dashpoint.dashpoint.api import send_webhook

        send_webhook(order.name)

        post.assert_called_once_with(
            "https://example.com/webhook",
            json={
                "event": "delivery_completed",
                "delivery_order": order.name,
                "amount": order.final_amount,
            },
            timeout=5,
        )

    @patch("frappe.publish_realtime")
    def test_failed_attempt_retries_then_escalates(self, publish):
        order = make_delivery_order(status="In Transit")
        frappe.db.set_single_value("Dispatch Settings", "max_delivery_attempts", 2)
        first = frappe.get_doc("Delivery Order", order.name)
        first.record_delivery_attempt("Failed", "Customer Unavailable")
        self.assertEqual(first.status, "Re-attempt Scheduled")
        second = frappe.get_doc("Delivery Order", order.name)
        second.record_delivery_attempt("Failed", "Customer Unavailable")
        self.assertEqual(second.status, "Escalated")
        delivery_events = [
            call for call in publish.call_args_list
            if call.args and call.args[0] == "delivery_status_changed"
        ]
        self.assertEqual(len(delivery_events), 2)

    @patch("frappe.publish_realtime")
    def test_whitelisted_attempt_publishes_realtime(self, publish):
        from dashpoint.dashpoint.doctype.delivery_order.delivery_order import record_delivery_attempt
        order = make_delivery_order(status="In Transit")
        result = record_delivery_attempt(order.name, "Delivered")
        self.assertEqual(result["status"], "Delivered")
        delivery_events = [
            call for call in publish.call_args_list
            if call.args and call.args[0] == "delivery_status_changed"
        ]
        self.assertEqual(len(delivery_events), 1)
        self.assertEqual(
            delivery_events[0].args,
            (
                "delivery_status_changed",
                {"delivery_order": order.name, "status": "Delivered"},
            ),
        )
        self.assertEqual(delivery_events[0].kwargs, {"user": order.owner})

    def test_cancel_restores_stock_and_cancels_receipt(self):
        material = make_packaging_material(stock_qty=5)
        order = make_delivery_order(_material=material, status="Delivered")
        order.submit()
        self.assertEqual(frappe.db.get_value("Packaging Material", material.name, "stock_qty"), 4)
        order.cancel()
        self.assertEqual(frappe.db.get_value("Packaging Material", material.name, "stock_qty"), 5)
        receipt_name = frappe.db.get_value("Delivery Receipt", {"delivery_order": order.name}, "name")
        self.assertEqual(frappe.db.get_value("Delivery Receipt", receipt_name, "docstatus"), 2)
        self.assertEqual(frappe.db.get_value("Delivery Order", order.name, "status"), "Cancelled")

    def test_trash_allows_draft_and_rejects_other_statuses(self):
        draft = make_delivery_order(status="Draft")
        draft.delete(ignore_permissions=True)
        order = make_delivery_order(status="In Transit")
        with self.assertRaises(frappe.ValidationError):
            order.delete(ignore_permissions=True)

    def test_on_update_does_not_save_recursively(self):
        order = make_delivery_order()
        order.remarks = "Updated"
        order.save(ignore_permissions=True)
        self.assertEqual(frappe.db.get_value("Delivery Order", order.name, "remarks"), "Updated")
