app_name = "dashpoint"
app_title = "DashPoint"
app_publisher = "Pavitradevi"
app_description = "Same-day courier dispatch management built on pure Frappe."
app_email = "pavitradevi297@gmail.com"
app_license = "mit"
 
jinja = {
    "methods": "dashpoint.dashpoint.utils.jinja_methods"
}

after_install = "dashpoint.install.after_install"

permission_query_conditions = {
    "Delivery Order": "dashpoint.permissions.delivery_order_query_conditions"
}

doc_events = {
    "*": {
        "on_update": "dashpoint.dashpoint.doctype.audit_log.audit_log.log_document_event",
        "on_submit": "dashpoint.dashpoint.doctype.audit_log.audit_log.log_document_event",
        "on_cancel": "dashpoint.dashpoint.doctype.audit_log.audit_log.log_document_event",
    }
}

scheduler_events = {
    "daily": [
        "dashpoint.tasks.check_stuck_reattempts"
    ]
}

fixtures = [
    {"dt": "Role", "filters": [["name", "in", ["DP Dispatch Staff", "DP Rider", "DP Ops Manager"]]]},
    {"dt": "DocPerm", "filters": [["role", "in", ["DP Dispatch Staff", "DP Rider", "DP Ops Manager"]]]},
    {"dt": "Delivery Zone", "filters": [["name", "in", ["North Zone", "Central Zone", "South Zone"]]]},
    {"dt": "Dispatch Settings", "filters": []},
    {"dt": "Letter Head", "filters": [["name", "=", "DashPoint Letter Head"]]},
]
