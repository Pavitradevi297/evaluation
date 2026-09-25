import frappe


def delivery_order_query_conditions(user=None):
    user = user or frappe.session.user
    roles = frappe.get_roles(user)

    if "DP Ops Manager" in roles or "System Manager" in roles:
        return ""

    if "DP Rider" in roles:
        rider = frappe.db.get_value("Rider", {"user": user}, "name")
        if rider:
            return "`tabDelivery Order`.`assigned_rider` = {0}".format(frappe.db.escape(rider))
        return "1=0"

    return ""
