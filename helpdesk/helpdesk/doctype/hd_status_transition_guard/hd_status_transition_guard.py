# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class HDStatusTransitionGuard(Document):
    def validate(self):
        self.clean_fields()
        self.validate_distinct_statuses()

    def clean_fields(self):
        if self.allowed_roles:
            self.allowed_roles = ", ".join(
                role.strip() for role in self.allowed_roles.split(",") if role.strip()
            )
        if self.required_fields:
            self.required_fields = ", ".join(
                f.strip() for f in self.required_fields.split(",") if f.strip()
            )

    def validate_distinct_statuses(self):
        if self.from_status and self.from_status == self.to_status:
            frappe.throw(
                _("From Status and To Status cannot be identical."),
                frappe.ValidationError,
            )
