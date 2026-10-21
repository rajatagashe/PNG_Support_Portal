# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.api.side_conversation import (
    close_side_conversation,
    create_side_conversation,
    get_side_conversations,
    reopen_side_conversation,
    reply_to_side_conversation,
)
from helpdesk.test_utils import (
    make_agent,
    make_customer_user,
    make_ticket,
)


class TestSideConversation(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.agent_user = make_agent("agent.sideconvo@png.test")
        self.customer_user = make_customer_user("customer.isolated@png.test", roles=["HD Customer"])
        self.ticket = make_ticket(subject="Compressor Vibration Issue")

    def tearDown(self):
        frappe.set_user("Administrator")
        if hasattr(self, "ticket") and frappe.db.exists("HD Ticket", self.ticket.name):
            frappe.db.delete("HD Side Conversation Message", {"side_conversation": ["like", f"SC-{self.ticket.name}-%"]})
            frappe.db.delete("HD Side Conversation", {"ticket": self.ticket.name})
            frappe.db.delete("HD Ticket", {"name": self.ticket.name})

    def test_create_and_reply_side_conversation(self):
        """Test creating, fetching, replying to, and closing side conversations."""
        frappe.set_user(self.agent_user)

        # 1. Create side conversation
        res = create_side_conversation(
            ticket=self.ticket.name,
            subject="OEM Siemens Inquiry regarding vibration tolerances",
            recipients="support@siemens-turbines.test",
            message="Hello, can you verify normal operating vibration at 3000 RPM?",
        )
        conv = res["conversation"]
        self.assertEqual(conv["ticket"], self.ticket.name)
        self.assertEqual(conv["status"], "Open")

        conv_id = conv["name"]

        # 2. Fetch conversations
        all_convs = get_side_conversations(self.ticket.name)
        self.assertEqual(len(all_convs), 1)
        self.assertEqual(all_convs[0]["name"], conv_id)
        self.assertEqual(len(all_convs[0]["messages"]), 1)

        # 3. Post reply
        reply_res = reply_to_side_conversation(
            conversation_id=conv_id,
            message="Vendor responded via external phone: within acceptable limits.",
        )
        self.assertIn("within acceptable limits", reply_res["message"])

        # Verify messages list has 2 entries
        reloaded_convs = get_side_conversations(self.ticket.name)
        self.assertEqual(len(reloaded_convs[0]["messages"]), 2)

        # 4. Close conversation
        close_res = close_side_conversation(conv_id)
        self.assertEqual(close_res["status"], "Closed")

        # 5. Reopen conversation
        reopen_res = reopen_side_conversation(conv_id)
        self.assertEqual(reopen_res["status"], "Open")

    def test_side_conversation_customer_isolation(self):
        """Test that customer portal users cannot view or create side conversations."""
        frappe.set_user(self.agent_user)
        create_side_conversation(
            ticket=self.ticket.name,
            subject="Internal Engineering Audit",
            recipients="audit@internal.test",
            message="Internal sensitive review notes.",
        )

        # Switch to customer user
        frappe.set_user(self.customer_user)

        with self.assertRaises(frappe.PermissionError):
            create_side_conversation(
                ticket=self.ticket.name,
                subject="Customer attempt",
                recipients="test@test.com",
                message="Should fail",
            )

        with self.assertRaises(frappe.PermissionError):
            get_side_conversations(self.ticket.name)
