# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

from datetime import timedelta
import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.api.sla_metrics import get_ticket_sla_metrics
from helpdesk.test_utils import make_ticket


class TestSLACountdownMetrics(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.ticket = make_ticket(subject="Gas Pipeline Pressure Loss")

    def tearDown(self):
        frappe.set_user("Administrator")
        if hasattr(self, "ticket") and frappe.db.exists("HD Ticket", self.ticket.name):
            frappe.db.delete("HD Ticket", {"name": self.ticket.name})

    def test_sla_countdown_metrics(self):
        """Test healthy, urgent, breached, and fulfilled SLA countdown metric calculations."""
        now = frappe.utils.now_datetime()

        # 1. Healthy: Response due in 2 hours (> 30 mins)
        frappe.db.set_value(
            "HD Ticket",
            self.ticket.name,
            {
                "sla": "Standard",
                "first_responded_on": None,
                "response_by": now + timedelta(hours=2),
                "resolution_by": now + timedelta(days=1),
            },
            update_modified=False,
        )

        m_healthy = get_ticket_sla_metrics(self.ticket.name)
        self.assertEqual(m_healthy["response"]["badge"], "healthy")
        self.assertIn("left", m_healthy["response"]["human"])

        # 2. Urgent: Response due in 15 minutes (< 30 mins)
        frappe.db.set_value(
            "HD Ticket",
            self.ticket.name,
            {"response_by": now + timedelta(minutes=15)},
            update_modified=False,
        )

        m_urgent = get_ticket_sla_metrics(self.ticket.name)
        self.assertEqual(m_urgent["response"]["badge"], "urgent")
        self.assertIn("left", m_urgent["response"]["human"])

        # 3. Breached: Response overdue by 45 minutes
        frappe.db.set_value(
            "HD Ticket",
            self.ticket.name,
            {"response_by": now - timedelta(minutes=45)},
            update_modified=False,
        )

        m_breached = get_ticket_sla_metrics(self.ticket.name)
        self.assertEqual(m_breached["response"]["badge"], "breached")
        self.assertIn("Breached by", m_breached["response"]["human"])

        # 4. Fulfilled: Agent already responded
        frappe.db.set_value(
            "HD Ticket",
            self.ticket.name,
            {"first_responded_on": now},
            update_modified=False,
        )

        m_fulfilled = get_ticket_sla_metrics(self.ticket.name)
        self.assertEqual(m_fulfilled["response"]["badge"], "fulfilled")
        self.assertEqual(m_fulfilled["response"]["human"], "Responded")

