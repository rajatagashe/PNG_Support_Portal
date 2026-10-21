# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

from datetime import datetime, timedelta
import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.automation.automation_engine import execute_automations
from helpdesk.test_utils import (
    make_automation,
    make_ticket,
)


class TestAutomations(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def tearDown(self):
        frappe.set_user("Administrator")
        frappe.db.delete("HD Automation")

    def test_time_based_auto_close_automation(self):
        """Test automation engine closes stale ticket with no customer response for 72 hours."""
        make_automation(
            automation_name="Auto Close Stale Ticket",
            conditions=[
                {"field": "status", "operator": "==", "value": "Open"},
                {"field": "hours_since_last_customer_response", "operator": ">=", "value": 72},
            ],
            actions=[
                {"action_type": "Set Status", "value": "Resolved"},
                {"action_type": "Add Tag", "value": "auto-escalated"},
            ],
        )

        ticket = make_ticket(subject="Old Query Pending Reply", status="Open")
        # Set last_customer_response to 4 days ago (96 hours)
        stale_time = datetime.now() - timedelta(hours=96)
        frappe.db.set_value("HD Ticket", ticket.name, "last_customer_response", stale_time)

        # Run automations
        execute_automations()

        ticket.reload()
        self.assertEqual(ticket.status, "Resolved")
        tags = ticket.get_tags() if hasattr(ticket, "get_tags") else []
        self.assertIn("auto-escalated", tags)
