import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname


class DeliveryReceipt(Document):

    def autoname(self):
        self.name = make_autoname("DR-.YYYY.-.#####")
        self.receipt_number = self.name

    def validate(self):
        if self.delivery_order and not self.packaging_usage:
            self.populate_from_delivery_order()
        self.calculate_packaging_totals()

    def populate_from_delivery_order(self):
        delivery_order = frappe.get_doc("Delivery Order", self.delivery_order)
        self.customer_name = delivery_order.customer_name
        self.delivery_zone = delivery_order.delivery_zone
        self.delivery_fee = delivery_order.delivery_fee
        self.payment_status = delivery_order.payment_status or "Unpaid"
        self.packaging_usage = []
        for row in delivery_order.packaging_used or []:
            self.append("packaging_usage", {
                "material": row.material,
                "material_name": row.material_name,
                "unit_price": row.unit_price,
                "quantity": row.quantity,
                "total_price": row.total_price,
            })

    def calculate_packaging_totals(self):
        packaging_total = 0
        for row in self.packaging_usage or []:
            row.total_price = (row.quantity or 0) * (row.unit_price or 0)
            packaging_total += row.total_price
        self.packaging_total = packaging_total
        self.final_amount = (self.delivery_fee or 0) + packaging_total
        self.total_amount = self.final_amount

    def before_print(self, print_settings=None):
        self.print_summary = f"{self.customer_name} - {self.delivery_zone}"
