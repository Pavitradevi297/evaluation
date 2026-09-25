frappe.query_reports["Active Deliveries"] = {
    filters: [
        {
            fieldname: "delivery_zone",
            label: __("Delivery Zone"),
            fieldtype: "Select",
            options: ["All Zones", "North Zone", "Central Zone", "South Zone"],
            default: "All Zones",
            reqd: 0
        }
    ],
    onload(report) {
        report.set_filter_value("delivery_zone", "All Zones");
    }
};
