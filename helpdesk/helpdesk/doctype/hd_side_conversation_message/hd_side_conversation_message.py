# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from helpdesk.utils import is_agent


class HDSideConversationMessage(Document):
    def before_insert(self):
        self.populate_sender_details()

    def populate_sender_details(self):
        if not self.sender_email:
            self.sender_email = frappe.session.user
        if not self.sender:
            self.sender = frappe.utils.get_fullname(frappe.session.user) or frappe.session.user


def has_permission(doc, ptype="read", user=None):
    """Side conversation messages are strictly agent-only."""
    if not user:
        user = frappe.session.user
    if user == "Administrator" or "System Manager" in frappe.get_roles(user):
        return True
    return is_agent(user)
