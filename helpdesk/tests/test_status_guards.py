# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.test_utils import (
    make_agent,
    make_agent_manager,
    make_status_guard,
    make_ticket,
)


class TestStatusGuards(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        for s in ("Open", "In Progress", "Resolved", "Closed"):
            if not frappe.db.exists("HD Ticket Status", s):
                frappe.get_doc(
                    {
                        "doctype": "HD Ticket Status",
                        "label_agent": s,
                        "category": "Resolved" if s == "Resolved" else ("Closed" if s == "Closed" else "Open"),
                        "enabled": 1,
                    }
                ).insert(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.delete("HD Status Transition Guard")

    def test_required_resolution_details_guard(self):
        """Test that transitioning to Resolved without resolution_details is blocked."""
        make_status_guard(
            to_status="Resolved",
            required_fields="resolution_details",
            error_message="Resolution details must be entered before resolving a ticket.",
        )

        ticket = make_ticket(subject="Network Glitch at Depot", status="Open")
        ticket.reload()

        # Attempt to resolve without resolution_details
        ticket.status = "Resolved"
        self.assertRaises(frappe.ValidationError, ticket.save)

        # Reload after failed attempt, provide resolution details and save successfully
        ticket.reload()
        ticket.status = "Resolved"
        ticket.resolution_details = "Rebooted depot switch and validated connectivity."
        ticket.save()
        ticket.reload()
        self.assertEqual(ticket.status, "Resolved")

    def test_role_restricted_transition_guard(self):
        """Test that transitions restricted to Agent Manager cannot be performed by regular agents."""
        make_status_guard(
            from_status="Open",
            to_status="Closed",
            allowed_roles="Agent Manager, System Manager",
            error_message="Only managers can directly close an open ticket.",
        )

        agent_email = make_agent("ops.agent1@cgd.test")
        manager_email = make_agent_manager(prefix="ops-mgr1")

        ticket = make_ticket(subject="Billing Query", status="Open")
        ticket.reload()

        # Agent attempt to directly close
        frappe.set_user(agent_email)
        ticket.status = "Closed"
        self.assertRaises(frappe.PermissionError, ticket.save)

        # Manager attempt to directly close
        frappe.set_user(manager_email)
        ticket.reload()
        ticket.status = "Closed"
        ticket.save()
        ticket.reload()
        self.assertEqual(ticket.status, "Closed")
