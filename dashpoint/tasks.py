import frappe


def process_delivery_orders():
    """Log scheduled attention for deliveries waiting for a retry."""
    orders = frappe.get_list(
        "Delivery Order",
        filters={"status": "Re-attempt Scheduled"},
        fields=["name", "assigned_rider", "delivery_zone"],
    )
    for order in orders:
        frappe.logger("dashpoint").info(
            "Scheduled processing for Delivery Order %s (rider=%s, zone=%s)",
            order.name, order.assigned_rider, order.delivery_zone,
        )
