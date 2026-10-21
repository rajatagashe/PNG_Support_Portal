# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.test_utils import (
    make_agent,
    make_incident_ticket,
    make_problem_ticket,
    make_ticket,
)


class TestAgentSignatureAndPropagation(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.agent_user = make_agent("support.senior@png.test")

        # Set signature on HD Agent
        agent_name = frappe.db.get_value("HD Agent", {"user": self.agent_user}, "name")
        self.signature_text = "--\nSenior Support Engineer\nMyPNG Helpdesk Operations"
        frappe.db.set_value("HD Agent", agent_name, "signature", self.signature_text)

        self.ticket = make_ticket(subject="Meter Calibration Request")

    def tearDown(self):
        frappe.set_user("Administrator")
        if hasattr(self, "ticket") and frappe.db.exists("HD Ticket", self.ticket.name):
            frappe.db.delete("Communication", {"reference_doctype": "HD Ticket", "reference_name": self.ticket.name})
            frappe.db.delete("HD Ticket", {"name": self.ticket.name})

    def test_reply_appends_agent_signature(self):
        """Test that reply_via_agent automatically appends agent's signature."""
        frappe.set_user(self.agent_user)
        ticket_doc = frappe.get_doc("HD Ticket", self.ticket.name)

        comm_name = ticket_doc.reply_via_agent(
            message="Your calibration is scheduled for Monday 10:00 AM.",
        )

        comm = frappe.get_doc("Communication", comm_name)
        self.assertIn("Your calibration is scheduled", comm.content)
        self.assertIn(self.signature_text, comm.content)

    def test_reply_propagates_to_child_incidents(self):
        """Test that replying to a problem ticket with propagate_to_incidents copies comment to linked incidents."""
        frappe.set_user(self.agent_user)

        prob_ticket = make_problem_ticket(subject="City Gas Station Power Grid Trip")
        inc_ticket = make_incident_ticket(subject="Station 12 Offline", problem_ticket=prob_ticket.name)

        prob_ticket.reply_via_agent(
            message="Diesel generator backup online. Normal pressure expected in 20 mins.",
            propagate_to_incidents=True,
        )

        comments = frappe.get_all(
            "Comment",
            filters={"reference_doctype": "HD Ticket", "reference_name": inc_ticket.name},
            pluck="content",
        )
        self.assertTrue(any("Diesel generator backup online" in c for c in comments))

        # Cleanup
        frappe.set_user("Administrator")
        frappe.db.delete("HD Ticket", {"name": ["in", [prob_ticket.name, inc_ticket.name]]})
