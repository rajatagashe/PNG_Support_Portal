# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.api.agent_lock import (
    acquire_ticket_lock,
    get_ticket_lock,
    release_ticket_lock,
)
from helpdesk.test_utils import (
    make_agent,
    make_ticket,
)


class TestAgentCollisionLock(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.agent1_user = make_agent("agent.alpha@png.test")
        self.agent2_user = make_agent("agent.beta@png.test")
        self.ticket = make_ticket(subject="Critical Pipeline Valve Replacement")

    def tearDown(self):
        frappe.set_user("Administrator")
        release_ticket_lock(self.ticket.name)
        if hasattr(self, "ticket") and frappe.db.exists("HD Ticket", self.ticket.name):
            frappe.db.delete("HD Ticket", {"name": self.ticket.name})

    def test_acquire_and_release_lock(self):
        """Test standard lock acquisition, inspection, and release by the holding agent."""
        frappe.set_user(self.agent1_user)

        # 1. Acquire lock
        res = acquire_ticket_lock(self.ticket.name)
        self.assertTrue(res["acquired"])
        self.assertFalse(res["is_locked"])

        # 2. Check lock from agent1's perspective
        status = get_ticket_lock(self.ticket.name)
        self.assertTrue(status["is_locked"])
        self.assertTrue(status["is_self"])

        # 3. Release lock
        rel = release_ticket_lock(self.ticket.name)
        self.assertTrue(rel["released"])

        # 4. Check lock is cleared
        status_cleared = get_ticket_lock(self.ticket.name)
        self.assertFalse(status_cleared["is_locked"])

    def test_collision_warning_and_force_takeover(self):
        """Test that collision is flagged when another agent edits, and force takeover works."""
        # Agent 1 locks ticket
        frappe.set_user(self.agent1_user)
        acquire_ticket_lock(self.ticket.name)

        # Agent 2 checks lock
        frappe.set_user(self.agent2_user)
        status2 = get_ticket_lock(self.ticket.name)
        self.assertTrue(status2["is_locked"])
        self.assertFalse(status2["is_self"])
        self.assertEqual(status2["locked_by_user"], self.agent1_user)

        # Agent 2 attempts acquisition without force -> collision detected
        col_res = acquire_ticket_lock(self.ticket.name, force=False)
        self.assertTrue(col_res["is_locked"])
        self.assertFalse(col_res["acquired"])
        self.assertEqual(col_res["locked_by_user"], self.agent1_user)

        # Agent 2 forces takeover
        takeover_res = acquire_ticket_lock(self.ticket.name, force=True)
        self.assertTrue(takeover_res["acquired"])
        self.assertTrue(takeover_res["taken_over"])

        # Verify Agent 2 is now the lock owner
        status_now = get_ticket_lock(self.ticket.name)
        self.assertTrue(status_now["is_self"])
        self.assertEqual(status_now["locked_by_user"], self.agent2_user)
