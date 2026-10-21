# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.test_utils import (
    make_agent,
    make_hd_customer,
    make_sla,
    make_team,
    make_ticket,
    make_vip_customer,
    make_vip_routing_rule,
)


class TestVIPRouting(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        # Ensure standard roles exist
        from helpdesk.setup.install import setup_granular_agent_roles
        setup_granular_agent_roles()

    def test_vip_customer_auto_escalation(self):
        """VIP customer automatically escalates ticket priority, routes to VIP team, and tags ticket."""
        vip_team = make_team("VIP Escalation Team")
        vip_customer = make_vip_customer(
            customer_name="GAIL Priority Corp",
            is_vip=1,
            vip_priority="Urgent",
            vip_team=vip_team.name,
        )

        ticket = make_ticket(
            subject="Gas pipeline pressure drop at GAIL terminal",
            customer=vip_customer.name,
            priority="Low",
        )

        self.assertEqual(ticket.priority, "Urgent")
        self.assertEqual(ticket.agent_group, vip_team.name)

        # Check tag
        tags = frappe.get_all(
            "Tag Link",
            filters={"document_type": "HD Ticket", "document_name": ticket.name},
            pluck="tag",
        )
        self.assertIn("vip-cgd", tags)

    def test_vip_domain_routing_rule(self):
        """Inbound ticket matching a VIP Routing Rule domain escalates priority and applies VIP tag."""
        rule = make_vip_routing_rule(
            rule_name="GAIL Domain Rule",
            domain="gail.gov.in",
            escalate_priority="Urgent",
            vip_tag="gail-priority",
        )

        ticket = make_ticket(
            subject="Telemetry sync failure",
            raised_by="ops@gail.gov.in",
            priority="Low",
        )

        self.assertEqual(ticket.priority, "Urgent")
        tags = frappe.get_all(
            "Tag Link",
            filters={"document_type": "HD Ticket", "document_name": ticket.name},
            pluck="tag",
        )
        self.assertIn("gail-priority", tags)

    def test_vip_custom_sla_escalation(self):
        """VIP Routing Rule can assign an accelerated VIP SLA policy."""
        vip_sla = make_sla(
            sla_name="VIP Rapid Response SLA",
        )
        customer = make_hd_customer("BPCL Refinery South")
        rule = make_vip_routing_rule(
            rule_name="BPCL VIP SLA Rule",
            customer=customer.name,
            escalate_priority="High",
            escalate_sla=vip_sla.name,
            vip_tag="bpcl-vip",
        )

        ticket = make_ticket(
            subject="Refinery connection latency",
            customer=customer.name,
            priority="Low",
        )

        self.assertEqual(ticket.priority, "High")
        self.assertEqual(ticket.sla, vip_sla.name)

    def test_non_vip_customer_standard_routing(self):
        """Regular non-VIP customer tickets do not receive VIP priority escalation or tags."""
        regular_customer = make_hd_customer("Standard CGD Vendor")
        # Ensure is_vip is 0
        frappe.db.set_value("HD Customer", regular_customer.name, "is_vip", 0)

        ticket = make_ticket(
            subject="General portal question",
            customer=regular_customer.name,
            priority="Medium",
        )

        self.assertEqual(ticket.priority, "Medium")
        tags = frappe.get_all(
            "Tag Link",
            filters={"document_type": "HD Ticket", "document_name": ticket.name},
            pluck="tag",
        )
        self.assertNotIn("vip-cgd", tags)

    def test_vip_senior_agent_assignment(self):
        """VIP ticket preferentially routes to senior agents (HD Tier 2 Agent) in assignment pool."""
        from helpdesk.overrides.assignment_rule import HelpdeskAssignmentRule

        # Create a Tier 1 agent and a Tier 2 agent
        junior_user = "junior_agent@mypng.test"
        senior_user = "senior_lead@mypng.test"

        for u in [junior_user, senior_user]:
            if not frappe.db.exists("User", u):
                frappe.get_doc({
                    "doctype": "User",
                    "email": u,
                    "first_name": u.split("@")[0],
                    "roles": [{"role": "Agent"}],
                }).insert(ignore_permissions=True)

        # Assign granular roles
        if not frappe.db.exists("Has Role", {"parent": junior_user, "role": "HD Tier 1 Agent"}):
            frappe.get_doc({"doctype": "Has Role", "parent": junior_user, "parenttype": "User", "parentfield": "roles", "role": "HD Tier 1 Agent"}).insert(ignore_permissions=True)
        if not frappe.db.exists("Has Role", {"parent": senior_user, "role": "HD Tier 2 Agent"}):
            frappe.get_doc({"doctype": "Has Role", "parent": senior_user, "parenttype": "User", "parentfield": "roles", "role": "HD Tier 2 Agent"}).insert(ignore_permissions=True)

        make_agent(junior_user)
        make_agent(senior_user)

        vip_customer = make_vip_customer("GAIL Elite", is_vip=1)
        ticket = make_ticket(
            subject="GAIL Elite Urgent Escalation",
            customer=vip_customer.name,
        )

        # Mock an assignment rule
        rule_doc = frappe.new_doc("Assignment Rule")
        rule_doc.document_type = "HD Ticket"
        rule_doc.rule = "Round Robin"
        rule_doc.set("users", [{"user": junior_user}, {"user": senior_user}])

        custom_rule = HelpdeskAssignmentRule(rule_doc.as_dict())
        assigned_user = custom_rule.get_user(ticket)

        # Senior user should be preferred for VIP ticket
        self.assertEqual(assigned_user, senior_user)
