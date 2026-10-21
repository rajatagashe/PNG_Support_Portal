# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from helpdesk.utils import is_agent


class HDSideConversation(Document):
    def before_insert(self):
        self.set_creator()
        self.validate_recipients()

    def set_creator(self):
        if not self.created_by:
            self.created_by = frappe.session.user

    def validate_recipients(self):
        if not self.recipients or not self.recipients.strip():
            frappe.throw(frappe._("At least one recipient email is required for a side conversation."))


def has_permission(doc, ptype="read", user=None):
    """Side conversations are strictly agent-only and hidden from customer portal users."""
    if not user:
        user = frappe.session.user
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True
    return is_agent(user)
