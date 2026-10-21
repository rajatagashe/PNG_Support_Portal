# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.test_utils import (
    make_team,
    make_ticket,
    make_trigger,
)


class TestTriggers(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.delete("HD Trigger")

    def test_on_ticket_creation_trigger(self):
        """Test trigger executes on ticket insert when subject contains emergency keywords."""
        hazmat_team = make_team("Pipeline Incident Team")

        make_trigger(
            trigger_name="Auto Triage Gas Leakage",
            event_type="On Ticket Creation",
            conditions=[
                {"field": "subject", "operator": "contains", "value": "Leakage"},
            ],
            actions=[
                {"action_type": "Set Priority", "value": "Urgent"},
                {"action_type": "Set Team", "value": hazmat_team.name},
                {"action_type": "Add Tag", "value": "emergency-cgd"},
            ],
        )

        ticket = make_ticket(subject="Urgent: Gas Leakage Detected at Block 4")
        ticket.reload()

        self.assertEqual(ticket.priority, "Urgent")
        self.assertEqual(ticket.agent_group, hazmat_team.name)
        tags = ticket.get_tags() if hasattr(ticket, "get_tags") else []
        self.assertIn("emergency-cgd", tags)

    def test_on_status_change_trigger(self):
        """Test trigger executes when status changes to a specific value."""
        make_trigger(
            trigger_name="Tag On Resolved",
            event_type="On Status Change",
            conditions=[
                {"field": "status", "operator": "==", "value": "Resolved"},
            ],
            actions=[
                {"action_type": "Add Tag", "value": "ready-for-review"},
            ],
        )

        ticket = make_ticket(subject="General Meter Reading Issue", status="Open")
        ticket.reload()
        ticket.status = "Resolved"
        ticket.save()
        ticket.reload()

        tags = ticket.get_tags() if hasattr(ticket, "get_tags") else []
        self.assertIn("ready-for-review", tags)
