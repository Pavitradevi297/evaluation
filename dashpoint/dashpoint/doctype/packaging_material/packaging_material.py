import frappe
from frappe.model.document import Document


class PackagingMaterial(Document):

    def autoname(self):
        self.material_code = (self.material_code or "").upper()
        self.name = frappe.model.naming.make_autoname("PKG-.YYYY.-.####")

    def validate(self):
        if (self.charge_to_customer or 0) < (self.unit_cost or 0):
            frappe.throw("Charge to Customer cannot be less than Unit Cost.")
