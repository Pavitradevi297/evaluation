# Copyright (c) 2026, Pavitradevi and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class PackagingUsageEntry(Document):

    def validate(self):
        self.total_price = (
            (self.quantity or 0) * (self.unit_price or 0)
        )
