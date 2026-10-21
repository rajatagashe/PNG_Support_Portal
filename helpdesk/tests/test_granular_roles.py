# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.test_utils import (
    make_granular_agent,
    make_sla,
    make_ticket,
    make_user,
)


class TestGranularRolesRBAC(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.tier1_user = make_granular_agent("tier1.agent@png.test", "HD Tier 1 Agent")
        self.auditor_user = make_user("auditor.compliance@png.test", ["HD Auditor"])
        self.ticket = make_ticket(subject="Compressor Routine Inspection")
        self.alt_sla = make_sla("Alt Test SLA")

    def tearDown(self):
        frappe.set_user("Administrator")
        if hasattr(self, "ticket") and frappe.db.exists("HD Ticket", self.ticket.name):
            frappe.db.delete("HD Ticket", {"name": self.ticket.name})
        if hasattr(self, "alt_sla") and frappe.db.exists("HD Service Level Agreement", self.alt_sla.name):
            frappe.db.delete("HD Service Level Agreement", {"name": self.alt_sla.name})

    def test_tier1_agent_restrictions(self):
        """Test that HD Tier 1 Agent cannot merge tickets, modify SLA, or delete tickets."""
        frappe.set_user(self.tier1_user)

        ticket_doc = frappe.get_doc("HD Ticket", self.ticket.name)

        # Attempt to merge ticket -> should fail
        ticket_doc.is_merged = 1
        ticket_doc.merged_with = self.ticket.name
        with self.assertRaises(frappe.PermissionError):
            ticket_doc.save()

        # Reload clean ticket
        ticket_doc.reload()

        # Attempt to modify SLA -> should fail
        ticket_doc.sla = self.alt_sla.name
        with self.assertRaises(frappe.PermissionError):
            ticket_doc.save()

        # Attempt to delete ticket -> should fail
        with self.assertRaises(frappe.PermissionError):
            ticket_doc.delete()

    def test_auditor_read_only(self):
        """Test that HD Auditor can read tickets but cannot modify or delete them."""
        frappe.set_user(self.auditor_user)

        # Reading ticket -> permitted
        has_read = frappe.has_permission("HD Ticket", "read", self.ticket.name, user=self.auditor_user)
        self.assertTrue(has_read)

        # Modifying ticket -> forbidden
        ticket_doc = frappe.get_doc("HD Ticket", self.ticket.name)
        ticket_doc.subject = "Auditor Unauthorized Tamper"
        with self.assertRaises(frappe.PermissionError):
            ticket_doc.save()

        # Deleting ticket -> forbidden
        with self.assertRaises(frappe.PermissionError):
            ticket_doc.delete()

