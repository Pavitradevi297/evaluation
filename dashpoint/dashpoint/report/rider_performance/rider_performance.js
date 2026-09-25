frappe.query_reports["Rider Performance"] = {
    filters: [
        { fieldname: "from_date", label: __("From Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.add_months(frappe.datetime.get_today(), -1) },
        { fieldname: "to_date", label: __("To Date"), fieldtype: "Date", reqd: 1, default: frappe.datetime.get_today() },
        { fieldname: "rider", label: __("Rider"), fieldtype: "Link", options: "Rider" }
    ],
    formatter(value, row, column, data) {
        if (column.fieldname === "rider" && data?.rider) {
            return `<a href="/app/rider/${encodeURIComponent(data.rider)}">${frappe.utils.escape_html(data.rider)}</a>`;
        }
        if (column.fieldname === "success_rate" && data) {
            if (data.success_rate < 70) return `<span style="color:red;font-weight:600">${value}</span>`;
            if (data.success_rate >= 90) return `<span style="color:green;font-weight:600">${value}</span>`;
        }
        return value;
    }
};
