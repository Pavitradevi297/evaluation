import frappe
from frappe.utils import add_days, today


def check_stuck_reattempts():
    """Find deliveries stuck in retry and flag them for Ops Manager.

    The Audit Log entry acts as a daily idempotency sentinel.
    """

    # Idempotency guard: run only once per day.
    last_run = frappe.db.get_value(
        "Audit Log",
        {
            "action": "stuck_reattempt_check",
            "timestamp": [">=", f"{today()} 00:00:00"],
        },
        "name",
    )

    if last_run:
        return

    # Consider retry orders older than 24 hours as stuck.
    cutoff = add_days(today(), -1)

    orders = frappe.get_list(
        "Delivery Order",
        filters={
            "status": "Re-attempt Scheduled",
            "modified": ["<", cutoff],
        },
        fields=["name", "assigned_rider", "delivery_zone"],
    )

    for order in orders:
        frappe.logger("dashpoint").warning(
            "Stuck retry flagged for Ops Manager: "
            "Delivery Order %s (rider=%s, zone=%s)",
            order.name,
            order.assigned_rider,
            order.delivery_zone,
        )

    # Create the daily sentinel after processing.
    audit_log = frappe.new_doc("Audit Log")
    audit_log.doctype_name = "DashPoint Scheduler"
    audit_log.document_name = "Stuck Re-attempt Sweep"
    audit_log.action = "stuck_reattempt_check"
    audit_log.user = frappe.session.user
    audit_log.timestamp = frappe.utils.now_datetime()
    audit_log.insert(ignore_permissions=True)

    frappe.db.commit()


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
            order.name,
            order.assigned_rider,
            order.delivery_zone,
        )
