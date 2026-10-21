# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class HDVIPRoutingRule(Document):
    def validate(self):
        self.clean_domain()
        self.validate_target()

    def clean_domain(self):
        if self.domain:
            self.domain = self.domain.strip().lower()
            if "@" in self.domain:
                self.domain = self.domain.split("@")[-1].strip()

    def validate_target(self):
        if not self.customer and not self.domain:
            frappe.throw(
                _("A VIP Routing Rule must specify at least a Customer or a Domain."),
                frappe.ValidationError,
            )
