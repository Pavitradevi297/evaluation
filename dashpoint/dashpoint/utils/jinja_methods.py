import frappe


def get_dispatch_center_name():
    return frappe.db.get_single_value(
        "Dispatch Settings", "dispatch_center_name"
    ) or "DashPoint Dispatch Center"


def format_value(value, df=None, doc=None):
    return frappe.format_value(value, df, doc)
