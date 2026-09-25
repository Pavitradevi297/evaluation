import frappe


def after_install():
    
    for zone_name in ["North Zone", "Central Zone", "South Zone"]:
        if not frappe.db.exists("Delivery Zone", {"zone_name": zone_name}):
            zone = frappe.new_doc("Delivery Zone")
            zone.zone_name = zone_name
            zone.insert(ignore_permissions=True)

  
    if not frappe.db.exists("Dispatch Settings"):
        settings = frappe.new_doc("Dispatch Settings")
        settings.dispatch_center_name = "DashPoint Dispatch Center"
        settings.ops_manager_email = "opsmanager@example.com"
        settings.max_delivery_attempts = 3
        settings.default_delivery_fee = 60
        settings.low_stock_alert_enabled = 1
        settings.insert(ignore_permissions=True)

    if not frappe.db.exists("Letter Head", "DashPoint Letter Head"):
        letter_head = frappe.new_doc("Letter Head")
        letter_head.name = "DashPoint Letter Head"
        letter_head.content = (
            "<div style=\"text-align:center;\">"
            "<strong>DashPoint Dispatch Center</strong><br>"
            "Delivery &amp; Logistics Management"
            "</div>"
        )
        letter_head.is_default = 1
        letter_head.disabled = 0
        letter_head.insert(ignore_permissions=True)

    frappe.db.commit()
    frappe.msgprint(
        "DashPoint installed successfully. Default Delivery Zones, "
        "Dispatch Settings, and Letter Head created."
    )
