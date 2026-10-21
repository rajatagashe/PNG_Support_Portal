# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.api.guest_ticket import (
    get_guest_ticket_details,
    guest_reply_to_ticket,
    submit_guest_ticket,
)


class TestGuestTicketMagicLink(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Guest")

    def tearDown(self):
        frappe.set_user("Administrator")
        if hasattr(self, "ticket_id") and frappe.db.exists("HD Ticket", self.ticket_id):
            frappe.db.delete("Communication", {"reference_doctype": "HD Ticket", "reference_name": self.ticket_id})
            frappe.db.delete("HD Ticket", {"name": self.ticket_id})

    def test_submit_guest_ticket_and_tracking(self):
        """Test guest public intake, token generation, and secure details retrieval."""
        res = submit_guest_ticket(
            subject="Domestic PNG Burner Ignition Failure",
            email="domestic.resident@citygas.test",
            description="Yellow flame and no ignition on burner 2.",
            full_name="Rajesh Sharma",
        )

        self.ticket_id = res["ticket"]
        self.guest_token = res["guest_token"]
        self.assertIn("/helpdesk/guest-tickets/", res["tracking_url"])
        self.assertTrue(len(self.guest_token) >= 32)

        # Retrieve ticket details using token
        details = get_guest_ticket_details(self.ticket_id, self.guest_token)
        self.assertEqual(details["ticket"]["name"], self.ticket_id)
        self.assertEqual(details["ticket"]["raised_by"], "domestic.resident@citygas.test")

    def test_guest_reply_to_ticket(self):
        """Test that guest can post replies using their magic-link token."""
        res = submit_guest_ticket(
            subject="Gas Odor Reported",
            email="resident2@citygas.test",
            description="Slight gas odor near the kitchen meter.",
        )
        self.ticket_id = res["ticket"]
        self.guest_token = res["guest_token"]

        # Guest posts reply
        reply_res = guest_reply_to_ticket(
            ticket_id=self.ticket_id,
            guest_token=self.guest_token,
            message="Technician arrived and turned off the valve.",
        )
        self.assertTrue(reply_res["success"])

        # Verify reply appears in ticket communications
        details = get_guest_ticket_details(self.ticket_id, self.guest_token)
        comm_contents = [c["content"] for c in details["communications"]]
        self.assertTrue(any("Technician arrived" in c for c in comm_contents))

    def test_invalid_guest_token_denied(self):
        """Test that unauthorized access with invalid or forged tokens is blocked."""
        res = submit_guest_ticket(
            subject="Bill Dispute Inquiry",
            email="dispute@citygas.test",
            description="Disputing meter units billed.",
        )
        self.ticket_id = res["ticket"]

        with self.assertRaises(frappe.PermissionError):
            get_guest_ticket_details(self.ticket_id, "invalid_or_forged_token")

        with self.assertRaises(frappe.PermissionError):
            guest_reply_to_ticket(self.ticket_id, "invalid_or_forged_token", "Hacker attempt")
