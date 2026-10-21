import frappe
from frappe import _
from frappe.model.document import Document


class HDDomainMapping(Document):
    def autoname(self):
        self.set_name_from_domain()

    def validate(self):
        self.clean_domain()
        self.validate_domain_format()

    def set_name_from_domain(self):
        self.clean_domain()
        self.name = self.domain

    def clean_domain(self):
        if self.domain:
            self.domain = self.domain.strip().lower().lstrip("@")

    def validate_domain_format(self):
        if not self.domain or "." not in self.domain:
            frappe.throw(
                _("Please enter a valid domain name (e.g. 'bpcl.in')."),
                frappe.ValidationError,
            )
