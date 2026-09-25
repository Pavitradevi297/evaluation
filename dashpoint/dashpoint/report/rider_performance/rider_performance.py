import frappe
from frappe import _


def execute(filters=None):
    filters = frappe._dict(filters or {})
    data = get_data(filters)
    return get_columns(), data, None, get_chart(data), get_report_summary(data)


def get_columns():
    return [
        {"label": _("Rider"), "fieldname": "rider", "fieldtype": "Link", "options": "Rider", "width": 180},
        {"label": _("Total Deliveries"), "fieldname": "total_deliveries", "fieldtype": "Int", "width": 130},
        {"label": _("Delivered"), "fieldname": "delivered", "fieldtype": "Int", "width": 100},
        {"label": _("Avg Attempts per Delivery"), "fieldname": "avg_attempts", "fieldtype": "Float", "precision": 2, "width": 170},
        {"label": _("Revenue"), "fieldname": "revenue", "fieldtype": "Currency", "width": 120},
        {"label": _("Success Rate %"), "fieldname": "success_rate", "fieldtype": "Percent", "width": 120},
    ]


def get_data(filters):
    conditions = []
    if filters.get("from_date"):
        conditions.append(["creation", ">=", f"{filters.from_date} 00:00:00"])
    if filters.get("to_date"):
        conditions.append(["creation", "<=", f"{filters.to_date} 23:59:59"])
    if filters.get("rider"):
        conditions.append(["assigned_rider", "=", filters.rider])

    orders = frappe.get_list(
        "Delivery Order",
        filters=conditions,
        fields=["assigned_rider", "status", "delivery_attempts_count", "final_amount"],
        order_by="assigned_rider asc",
    )

    rider_names = {row.assigned_rider for row in orders if row.assigned_rider}
    rider_records = frappe.get_list(
        "Rider",
        filters={"name": ["in", list(rider_names)]},
        fields=["name", "rider_name"],
    ) if rider_names else []
    riders = {row.name: row.rider_name for row in rider_records}

    result = {}
    for order in orders:
        rider = order.assigned_rider
        if not rider:
            continue
        result.setdefault(rider, {"rider": rider, "rider_name": riders.get(rider) or rider, "total_deliveries": 0, "delivered": 0, "attempts": 0, "revenue": 0})
        result[rider]["total_deliveries"] += 1
        result[rider]["attempts"] += order.delivery_attempts_count or 0
        result[rider]["revenue"] += order.final_amount or 0
        if order.status == "Delivered":
            result[rider]["delivered"] += 1

    data = []
    for row in result.values():
        total = row["total_deliveries"]
        data.append({
            "rider": row["rider"],
            "rider_name": row["rider_name"],
            "total_deliveries": total,
            "delivered": row["delivered"],
            "avg_attempts": row["attempts"] / total if total else 0,
            "revenue": row["revenue"],
            "success_rate": (row["delivered"] / total) * 100 if total else 0,
        })
    return data


def get_chart(data):
    return {
        "data": {
            "labels": [row["rider_name"] for row in data],
            "datasets": [
                {"name": _("Total"), "values": [row["total_deliveries"] for row in data]},
                {"name": _("Delivered"), "values": [row["delivered"] for row in data]},
            ],
        },
        "type": "bar",
        "height": 300,
    }


def get_report_summary(data):
    total_deliveries = sum(row["total_deliveries"] for row in data)
    total_revenue = sum(row["revenue"] for row in data)
    top_rider = max(data, key=lambda row: row["delivered"])["rider_name"] if data else "-"
    return [
        {"value": total_deliveries, "indicator": "Blue", "label": _("Total Deliveries"), "datatype": "Int"},
        {"value": total_revenue, "indicator": "Green", "label": _("Total Revenue"), "datatype": "Currency"},
        {"value": top_rider, "indicator": "Orange", "label": _("Top Rider")},
    ]
