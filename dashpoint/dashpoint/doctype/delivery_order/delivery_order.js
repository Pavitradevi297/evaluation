frappe.ui.form.on("Delivery Order", {
    setup(frm) {
        frm.set_query("assigned_rider", () => ({ filters: { status: "Active", assigned_zone: frm.doc.delivery_zone } }));
    },

    refresh(frm) {
        frm.clear_custom_buttons();
        const status_colors = { Draft: "gray", "Pickup Scheduled": "blue", "In Transit": "blue", "Delivery Failed": "red", "Re-attempt Scheduled": "orange", Delivered: "green", Escalated: "red", Cancelled: "gray" };
        const status = frm.doc.status || "Draft";
        frm.dashboard.add_indicator(status, status_colors[status] || "gray");
        if (["In Transit", "Re-attempt Scheduled"].includes(frm.doc.status)) {
            frm.add_custom_button(__("Log Delivery Attempt"), () => show_delivery_attempt_dialog(frm), __("Delivery"));
            frm.add_custom_button(__("Reassign Rider"), () => reassign_delivery_rider(frm), __("Delivery"));
        }
    },

    assigned_rider(frm) {
        if (!frm.doc.assigned_rider) return;
        if (!frm.doc.delivery_zone) {
            frappe.msgprint(__("Please select a Delivery Zone before assigning a Rider."));
            return;
        }
        frappe.db.get_value("Rider", frm.doc.assigned_rider, "assigned_zone").then((r) => {
            const rider_zone = r.message?.assigned_zone;
            if (rider_zone && rider_zone !== frm.doc.delivery_zone) {
                frappe.msgprint({ title: __("Zone Mismatch"), message: __("The selected Rider belongs to {0}, but this Delivery Order is assigned to {1}.", [rider_zone, frm.doc.delivery_zone]), indicator: "orange" });
            }
        });
    }
});

function show_delivery_attempt_dialog(frm) {
    const dialog = new frappe.ui.Dialog({
        title: __("Log Delivery Attempt"),
        fields: [
            { fieldname: "outcome", label: __("Outcome"), fieldtype: "Select", options: ["Delivered", "Failed"], reqd: 1 },
            { fieldname: "failure_reason", label: __("Failure Reason"), fieldtype: "Select", options: ["", "Customer Unavailable", "Wrong Address", "Refused", "Other"], depends_on: "eval:doc.outcome=='Failed'" }
        ],
        primary_action_label: __("Submit"),
        primary_action(values) {
            if (values.outcome === "Failed" && !values.failure_reason) {
                frappe.msgprint({ title: __("Validation Error"), message: __("Failure Reason is required when Outcome is Failed."), indicator: "red" });
                return;
            }
            frappe.call({
                method: "dashpoint.dashpoint.doctype.delivery_order.delivery_order.record_delivery_attempt",
                args: { delivery_order_name: frm.doc.name, outcome: values.outcome, failure_reason: values.failure_reason || null },
                freeze: true, freeze_message: __("Recording delivery attempt...")
            }).then((r) => {
                if (!r.exc) {
                    dialog.hide();
                    frm.reload_doc();
                    frappe.show_alert({ message: __("Delivery attempt recorded successfully."), indicator: "green" });
                }
            });
        }
    });
    dialog.show();
}

function reassign_delivery_rider(frm) {
    frappe.prompt([{ fieldname: "new_rider", label: __("New Rider"), fieldtype: "Link", options: "Rider", reqd: 1, get_query() { return { filters: { status: "Active", assigned_zone: frm.doc.delivery_zone } }; } }], (values) => {
        frappe.confirm(__("Are you sure you want to reassign this Delivery Order to {0}?", [values.new_rider]), () => {
            frappe.call({ method: "dashpoint.dashpoint.api.reassign_zone", args: { from_rider: frm.doc.assigned_rider, to_rider: values.new_rider }, freeze: true, freeze_message: __("Reassigning Rider...") }).then((r) => {
                if (!r.exc) {
                    frm.set_value("assigned_rider", values.new_rider);
                    frm.trigger("assigned_rider");
                    frm.save().then(() => {
                        frappe.show_alert({ message: __("Rider reassigned successfully."), indicator: "green" });
                        frm.reload_doc();
                    });
                }
            });
        });
    }, __("Reassign Rider"), __("Reassign"));
}

frappe.ui.form.on("Packaging Usage Entry", {
    quantity(frm, cdt, cdn) { update_packaging_total(cdt, cdn); },
    unit_price(frm, cdt, cdn) { update_packaging_total(cdt, cdn); }
});

function update_packaging_total(cdt, cdn) {
    const row = frappe.get_doc(cdt, cdn);
    frappe.model.set_value(cdt, cdn, "total_price", flt(row.quantity) * flt(row.unit_price));
}
