import frappe
from frappe.tests.utils import FrappeTestCase

from dashpoint.dashpoint.doctype.delivery_order.test_delivery_order import (
    make_delivery_order,
    make_packaging_material,
)


class TestDeliveryReceipt(FrappeTestCase):
    def test_receipt_autoname_and_before_print_summary(self):
        material = make_packaging_material()
        order = make_delivery_order(_material=material, status="Delivered")
        receipt = frappe.new_doc("Delivery Receipt")
        receipt.delivery_order = order.name
        receipt.insert(ignore_permissions=True)
        receipt.reload()
        self.assertTrue(receipt.receipt_number.startswith("DR-"))
        receipt.before_print()
        self.assertEqual(
            receipt.print_summary,
            f"{receipt.customer_name} - {receipt.delivery_zone}",
        )
