import frappe
from frappe import _


@frappe.whitelist()
def get_stuck_deliveries():
    """Return open deliveries older than two days using Frappe Query Builder."""
    from frappe.query_builder import DocType
    from pypika import Order

    delivery_order = DocType("Delivery Order")
    cutoff = frappe.utils.add_days(frappe.utils.now_datetime(), -2)

    return (
        frappe.qb.from_(delivery_order)
        .select(
            delivery_order.name,
            delivery_order.customer_name,
            delivery_order.assigned_rider,
            delivery_order.creation,
        )
        .where(
            delivery_order.status.isin(["In Transit", "Re-attempt Scheduled"])
            & (delivery_order.creation < cutoff)
        )
        .orderby(delivery_order.creation, order=Order.asc)
        .run(as_dict=True)
    )


@frappe.whitelist()
def reassign_zone(from_rider, to_rider):
    """Transfer all open Delivery Orders from one rider to another."""
    open_statuses = (
        "Draft",
        "Pickup Scheduled",
        "In Transit",
        "Delivery Failed",
        "Re-attempt Scheduled",
    )
    placeholders = ", ".join(["%s"] * len(open_statuses))

    try:
        frappe.db.sql(
            f"""
            UPDATE `tabDelivery Order`
            SET assigned_rider = %s
            WHERE assigned_rider = %s
              AND status IN ({placeholders})
            """,
            [to_rider, from_rider, *open_statuses],
        )
        frappe.db.commit()
        return {"success": True, "from_rider": from_rider, "to_rider": to_rider}
    except Exception:
        frappe.db.rollback()
        frappe.log_error(frappe.get_traceback(), "DashPoint - Rider Reassignment Failed")
        raise


@frappe.whitelist()
def rename_rider(old_name, new_name):
    """Rename a Rider through Frappe so linked Delivery Orders are updated safely."""
    if not frappe.db.exists("Rider", old_name):
        frappe.throw(_("Rider {0} does not exist.").format(old_name))
    if frappe.db.exists("Rider", new_name):
        frappe.throw(_("Rider {0} already exists.").format(new_name))
    return frappe.rename_doc("Rider", old_name, new_name, merge=False)


@frappe.whitelist()
def share_delivery_order(delivery_order_name, user_email):
    """Grant a specific user read access to one Delivery Order."""
    if not frappe.db.exists("Delivery Order", delivery_order_name):
        frappe.throw(_("Delivery Order {0} does not exist.").format(delivery_order_name))
    frappe.share.add("Delivery Order", delivery_order_name, user_email, read=1)
    return {"shared": True, "delivery_order": delivery_order_name, "user": user_email}


@frappe.whitelist()
def unsafe_get_delivery_order_data():
    """Intentionally unsafe example for README/security training; never use in production."""
    return frappe.get_all("Delivery Order", fields="*")


@frappe.whitelist()
def safe_get_delivery_order_data():
    """Return permission-aware Delivery Orders and hide customer contact data from non-managers."""
    fields = [
        "name", "customer_name", "customer_phone", "customer_email", "pickup_address",
        "delivery_address", "delivery_zone", "assigned_rider", "status",
        "delivery_attempts_count", "final_amount", "creation",
    ]
    rows = frappe.get_list("Delivery Order", fields=fields, order_by="creation desc")
    if "DP Ops Manager" not in frappe.get_roles(frappe.session.user):
        for row in rows:
            row.pop("customer_phone", None)
            row.pop("customer_email", None)
    return rows

@frappe.whitelist()
def get_delivery_status():
    """Return safe delivery status information for a Delivery Order."""
    delivery_order_name = frappe.form_dict.get("delivery_order_name")

    if not delivery_order_name or not frappe.db.exists(
        "Delivery Order", delivery_order_name
    ):
        frappe.local.response["http_status_code"] = 404
        return {"error": "Not found"}

    order = frappe.db.get_value(
        "Delivery Order",
        delivery_order_name,
        ["status", "delivery_zone", "delivery_attempts_count"],
        as_dict=True,
    )

    return {
        "status": order.status,
        "zone": order.delivery_zone,
        "attempts": order.delivery_attempts_count,
    }

@frappe.whitelist()
def send_delivery_confirmation(delivery_order_name):
    """Background job for customer delivery confirmation email."""
    order = frappe.get_doc("Delivery Order", delivery_order_name)

    if not order.customer_email:
        frappe.logger("dashpoint").info(
            "Delivery confirmation skipped for %s: no customer email",
            order.name,
        )
        return

    frappe.sendmail(
        recipients=[order.customer_email],
        subject=_("Delivery completed: {0}").format(order.name),
        message=_("Your delivery {0} has been completed.").format(order.name),
    )


def send_webhook(delivery_order_name):
    """Send delivery-completed webhook from a background job."""
    import requests

    settings = frappe.get_single("Dispatch Settings")

    if not settings.webhook_url:
        return

    doc = frappe.get_doc("Delivery Order", delivery_order_name)

    payload = {
        "event": "delivery_completed",
        "delivery_order": doc.name,
        "amount": doc.final_amount,
    }

    try:
        response = requests.post(
            settings.webhook_url,
            json=payload,
            timeout=5,
        )
        response.raise_for_status()

        frappe.logger("dashpoint").info(
            "Delivery webhook sent successfully for %s",
            doc.name,
        )

    except Exception as e:
        frappe.log_error(
            f"Webhook failed: {e}",
            "Webhook Error",
        )

@frappe.whitelist()
def get_dispatch_center_name():
    return frappe.db.get_single_value("Dispatch Settings", "dispatch_center_name") or "DashPoint Dispatch Center"
