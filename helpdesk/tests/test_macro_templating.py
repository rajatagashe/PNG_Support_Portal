# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.api.saved_replies import get_rendered_saved_reply
from helpdesk.test_utils import (
    make_agent,
    make_contact,
    make_hd_customer,
    make_ticket,
)


class TestMacroTemplating(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.agent_email = make_agent("support.agent1@png.test")
        self.customer = make_hd_customer("Adani Total Gas", domain="adanigas.com")
        self.contact = make_contact("Suresh Patel", "suresh@adanigas.com")

        # Create test saved reply with rich Jinja macro variables
        self.saved_reply = frappe.get_doc(
            {
                "doctype": "HD Saved Reply",
                "title": "Macro Greeting Template",
                "scope": "Global",
                "message": (
                    "Dear {{ customer.customer_name }} Team,\n"
                    "Regarding ticket #{{ ticket.name }} ({{ ticket.subject }}):\n"
                    "Assigned Agent: {{ agent.agent_name }}.\n"
                    "Thank you!"
                ),
            }
        ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user("Administrator")
        if hasattr(self, "saved_reply"):
            frappe.db.delete("HD Saved Reply", {"name": self.saved_reply.name})

    def test_saved_reply_macro_rendering(self):
        """Test that Jinja macros interpolate ticket, customer, and agent details."""
        ticket = make_ticket(
            subject="Pressure Regulator Leakage",
            customer=self.customer.name,
            contact=self.contact,
        )

        frappe.set_user(self.agent_email)
        rendered = get_rendered_saved_reply(ticket.name, self.saved_reply.name)

        msg = rendered.get("message", "")
        self.assertIn("Dear Adani Total Gas Team,", msg)
        self.assertIn(f"Regarding ticket #{ticket.name} (Pressure Regulator Leakage):", msg)
        self.assertIn("Assigned Agent:", msg)
