import frappe
from frappe.model.document import Document


class DeliveryOrder(Document):

    def validate(self):
        self.validate_phone()
        self.validate_rider()
        self.validate_failure_reason()
        self.calculate_packaging_total()
        self.calculate_delivery_fee()
        self.calculate_final_amount()

    def validate_phone(self):
        phone = (self.customer_phone or "").strip()
        if not phone.isdigit() or len(phone) != 10:
            frappe.throw("Customer phone must contain exactly 10 digits.")

    def validate_rider(self):
        rider_required_statuses = {
            "In Transit", "Delivery Failed", "Re-attempt Scheduled",
            "Delivered", "Escalated", "Cancelled",
        }
        if self.status in rider_required_statuses and not self.assigned_rider:
            frappe.throw("An Assigned Rider is required for this delivery status.")

        if not self.assigned_rider:
            return

        rider = frappe.get_doc("Rider", self.assigned_rider)
        if rider.status != "Active":
            frappe.throw(f"Rider {rider.rider_name} is not Active.")

        if rider.assigned_zone != self.delivery_zone:
            frappe.throw("Assigned Rider does not belong to the selected Delivery Zone.")

    def validate_failure_reason(self):
        if self.status == "Delivery Failed" and not self.failure_reason:
            frappe.throw("Failure Reason is mandatory when delivery status is Delivery Failed.")

    def calculate_packaging_total(self):
        total = 0
        for row in self.packaging_used or []:
            row.total_price = (row.quantity or 0) * (row.unit_price or 0)
            total += row.total_price
        self.packaging_total = total

    def calculate_delivery_fee(self):
        if self.delivery_fee is None or self.delivery_fee == 0:
            self.delivery_fee = frappe.db.get_single_value(
                "Dispatch Settings", "default_delivery_fee"
            ) or 0

    def calculate_final_amount(self):
        self.final_amount = (self.packaging_total or 0) + (self.delivery_fee or 0)

    def before_submit(self):
        if self.status != "Delivered":
            frappe.throw("Only Delivery Orders with status Delivered can be submitted.")
        self.check_packaging_stock()

    def check_packaging_stock(self):
        for row in self.packaging_used or []:
            if not row.material:
                continue
            available_stock = frappe.db.get_value(
                "Packaging Material", row.material, "stock_qty"
            ) or 0
            required_qty = row.quantity or 0
            if available_stock < required_qty:
                frappe.throw(
                    f"Insufficient stock for packaging material {row.material}. "
                    f"Available: {available_stock}, Required: {required_qty}."
                )

    def on_submit(self):
        self.deduct_packaging_stock()
        self.create_delivery_receipt()

        frappe.enqueue(
            "dashpoint.dashpoint.api.send_delivery_confirmation",
            queue="short",
            delivery_order_name=self.name,
        )

        frappe.enqueue(
            "dashpoint.dashpoint.api.send_webhook",
            queue="short",
            delivery_order_name=self.name,
        )

    def deduct_packaging_stock(self):
        for row in self.packaging_used or []:
            if not row.material:
                continue
            current_stock = frappe.db.get_value(
                "Packaging Material", row.material, "stock_qty"
            ) or 0
       
            frappe.db.set_value(
                "Packaging Material",
                row.material,
                "stock_qty",
                current_stock - (row.quantity or 0),
                update_modified=False,
            )

    def create_delivery_receipt(self):
        if frappe.db.exists("Delivery Receipt", {"delivery_order": self.name}):
            return frappe.get_doc("Delivery Receipt", {"delivery_order": self.name})

        receipt = frappe.new_doc("Delivery Receipt")
        receipt.delivery_order = self.name
        receipt.receipt_date = frappe.utils.nowdate()
        receipt.delivery_fee = self.delivery_fee or 0
        receipt.packaging_total = self.packaging_total or 0
        receipt.total_amount = self.final_amount or 0
        receipt.final_amount = self.final_amount or 0
        receipt.payment_status = self.payment_status or "Unpaid"

        for row in self.packaging_used or []:
            receipt.append("packaging_usage", {
                "material": row.material,
                "material_name": row.material_name,
                "unit_price": row.unit_price,
                "quantity": row.quantity,
                "total_price": row.total_price,
            })

        receipt.insert(ignore_permissions=True)
        receipt.flags.ignore_permissions = True
        receipt.submit()
        return receipt

    def record_delivery_attempt(self, outcome, failure_reason=None):
        if outcome == "Failed":
            if not failure_reason:
                frappe.throw("Failure Reason is mandatory when Outcome is Failed.")
            self.status = "Delivery Failed"
            self.failure_reason = failure_reason
            self.delivery_attempts_count = (self.delivery_attempts_count or 0) + 1

            max_attempts = frappe.db.get_single_value(
                "Dispatch Settings", "max_delivery_attempts"
            ) or 3
            self.status = (
                "Escalated"
                if self.delivery_attempts_count >= max_attempts
                else "Re-attempt Scheduled"
            )

        elif outcome == "Delivered":
            self.status = "Delivered"
            self.delivered_on = frappe.utils.now_datetime()

        else:
            frappe.throw("Invalid delivery attempt outcome.")

        self.save(ignore_permissions=True)
        frappe.publish_realtime(
            "delivery_status_changed",
            {"delivery_order": self.name, "status": self.status},
            user=self.owner,
        )
        return self.status

    def before_cancel(self):
        self.status = "Cancelled"

    def on_cancel(self):
        self.restore_packaging_stock()
        receipt_name = frappe.db.get_value(
            "Delivery Receipt", {"delivery_order": self.name}, "name"
        )
        if receipt_name:
            receipt = frappe.get_doc("Delivery Receipt", receipt_name)
            if receipt.docstatus == 1:
                receipt.flags.ignore_permissions = True
                receipt.cancel()

    def restore_packaging_stock(self):
        for row in self.packaging_used or []:
            if not row.material:
                continue
            current_stock = frappe.db.get_value(
                "Packaging Material", row.material, "stock_qty"
            ) or 0
            frappe.db.set_value(
                "Packaging Material",
                row.material,
                "stock_qty",
                current_stock + (row.quantity or 0),
                update_modified=False,
            )

    def on_trash(self):
        if self.status not in {"Draft", "Cancelled"}:
            frappe.throw(
                "Delivery Orders may be deleted only when status is Draft or Cancelled."
            )

    def on_update(self):
        return


@frappe.whitelist()
def record_delivery_attempt(delivery_order_name, outcome, failure_reason=None):
    delivery_order = frappe.get_doc("Delivery Order", delivery_order_name)
    delivery_order.record_delivery_attempt(outcome, failure_reason)

    return {
        "name": delivery_order.name,
        "status": delivery_order.status,
        "attempts": delivery_order.delivery_attempts_count,
    }
