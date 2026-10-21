# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.overrides.assignment_rule import HelpdeskAssignmentRule
from helpdesk.test_utils import (
    make_agent,
    make_assignment_rule,
    make_skill,
    make_ticket,
)


class TestSkillBasedRoutingAndCapacity(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.agent1_user = make_agent("scada.specialist@png.test")
        self.agent2_user = make_agent("billing.generalist@png.test")

        # Create skills
        self.skill_scada = make_skill("SCADA Integration")
        self.skill_billing = make_skill("Billing & Invoicing")

        # Assign skills to agents
        agent1_doc = frappe.get_doc("HD Agent", {"user": self.agent1_user})
        agent1_doc.skills = []
        agent1_doc.append("skills", {"skill": self.skill_scada.name})
        agent1_doc.max_concurrent_tickets = 5
        agent1_doc.save(ignore_permissions=True)

        agent2_doc = frappe.get_doc("HD Agent", {"user": self.agent2_user})
        agent2_doc.skills = []
        agent2_doc.append("skills", {"skill": self.skill_billing.name})
        agent2_doc.max_concurrent_tickets = 5
        agent2_doc.save(ignore_permissions=True)

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_skill_matching_routing(self):
        """Test that tickets requiring specialized skills are routed to qualified agents."""
        rule = make_assignment_rule(
            name="Test Skill Rule " + frappe.generate_hash(length=6),
            users=[self.agent1_user, self.agent2_user],
        )

        # Ticket requiring SCADA
        ticket = make_ticket(subject="SCADA Communication Timeout")
        ticket.append("skills", {"skill": self.skill_scada.name})

        assigned_user = rule.get_user(ticket)
        self.assertEqual(assigned_user, self.agent1_user)

        # Cleanup ticket and rule
        frappe.db.delete("HD Ticket", {"name": ticket.name})
        frappe.db.delete("Assignment Rule", {"name": rule.name})

    def test_agent_capacity_cap(self):
        """Test that agents who have reached their max concurrent ticket cap are skipped."""
        # Cap agent1 at 1 ticket, agent2 at 5 tickets
        agent1_doc = frappe.get_doc("HD Agent", {"user": self.agent1_user})
        agent1_doc.max_concurrent_tickets = 1
        agent1_doc.skills = []
        agent1_doc.save(ignore_permissions=True)

        agent2_doc = frappe.get_doc("HD Agent", {"user": self.agent2_user})
        agent2_doc.max_concurrent_tickets = 5
        agent2_doc.skills = []
        agent2_doc.save(ignore_permissions=True)

        # Create 1 open ticket assigned to agent 1
        existing_ticket = make_ticket(subject="Existing Active Job")
        import json
        frappe.db.set_value(
            "HD Ticket",
            existing_ticket.name,
            {"_assign": json.dumps([self.agent1_user]), "status_category": "Open"},
            update_modified=False,
        )

        rule = make_assignment_rule(
            name="Test Capacity Rule " + frappe.generate_hash(length=6),
            users=[self.agent1_user, self.agent2_user],
        )

        # New ticket should bypass saturated agent1 and route to agent2
        new_ticket = make_ticket(subject="Pipeline Valve Maintenance")
        assigned_user = rule.get_user(new_ticket)
        self.assertEqual(assigned_user, self.agent2_user)

        # Cleanup tickets and rule
        frappe.db.delete("HD Ticket", {"name": ["in", [existing_ticket.name, new_ticket.name]]})
        frappe.db.delete("Assignment Rule", {"name": rule.name})


