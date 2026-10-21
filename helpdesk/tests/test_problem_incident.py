# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.api.problem_incident import (
    get_linked_incidents,
    link_incident_to_problem,
    unlink_incident_from_problem,
)
from helpdesk.test_utils import (
    make_agent,
    make_incident_ticket,
    make_problem_ticket,
)


class TestProblemIncidentHierarchy(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.agent_user = make_agent("problem.solver@png.test")

        # Create master problem ticket
        self.problem = make_problem_ticket(
            subject="Major Pipeline Outage Sector 4",
            description="SCADA communication severed.",
        )

        # Create incident tickets
        self.incident_1 = make_incident_ticket(subject="No gas delivery Unit 101")
        self.incident_2 = make_incident_ticket(subject="Low pressure alarm Unit 102")

    def tearDown(self):
        frappe.set_user("Administrator")
        for doc in (getattr(self, "incident_1", None), getattr(self, "incident_2", None), getattr(self, "problem", None)):
            if doc and frappe.db.exists("HD Ticket", doc.name):
                frappe.db.delete("HD Ticket", {"name": doc.name})

    def test_problem_incident_linking_and_counter(self):
        """Test that linking incidents increments problem incident_count and unlinking decrements it."""
        frappe.set_user(self.agent_user)

        # Link first incident
        res1 = link_incident_to_problem(self.incident_1.name, self.problem.name)
        self.assertEqual(res1["status"], "Linked")

        # Link second incident
        res2 = link_incident_to_problem(self.incident_2.name, self.problem.name)
        self.assertEqual(res2["status"], "Linked")

        # Verify linked list
        linked = get_linked_incidents(self.problem.name)
        linked_names = [item["name"] for item in linked]
        self.assertIn(self.incident_1.name, linked_names)
        self.assertIn(self.incident_2.name, linked_names)

        # Verify counter
        count = frappe.db.get_value("HD Ticket", self.problem.name, "incident_count")
        self.assertEqual(count, 2)

        # Unlink first incident
        unlink_incident_from_problem(self.incident_1.name)
        count_after = frappe.db.get_value("HD Ticket", self.problem.name, "incident_count")
        self.assertEqual(count_after, 1)

    def test_mass_resolution_propagation(self):
        """Test that resolving a master problem ticket automatically resolves linked incidents."""
        frappe.set_user(self.agent_user)

        # Link incidents
        link_incident_to_problem(self.incident_1.name, self.problem.name)
        link_incident_to_problem(self.incident_2.name, self.problem.name)

        # Resolve problem ticket
        prob_doc = frappe.get_doc("HD Ticket", self.problem.name)
        prob_doc.status = "Resolved"
        prob_doc.resolution_details = "SCADA Fiber Line Re-spliced and pressurized."
        prob_doc.flags.ignore_status_guards = True
        prob_doc.save(ignore_permissions=True)

        # Check that incidents are resolved with matching resolution details
        inc1_reloaded = frappe.get_doc("HD Ticket", self.incident_1.name)
        inc2_reloaded = frappe.get_doc("HD Ticket", self.incident_2.name)

        self.assertEqual(inc1_reloaded.status, "Resolved")
        self.assertEqual(inc2_reloaded.status, "Resolved")
        self.assertEqual(inc1_reloaded.resolution_details, "SCADA Fiber Line Re-spliced and pressurized.")
        self.assertEqual(inc2_reloaded.resolution_details, "SCADA Fiber Line Re-spliced and pressurized.")

        # Check comment audit
        comments = frappe.get_all(
            "Comment",
            filters={"reference_doctype": "HD Ticket", "reference_name": self.incident_1.name},
            pluck="content",
        )
        self.assertTrue(any(f"Master Problem Ticket #{self.problem.name}" in c for c in comments))
