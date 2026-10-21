import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.test_utils import (
    make_domain_mapping,
    make_hd_customer,
    make_team,
    make_ticket,
)


class TestDomainMapping(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        frappe.db.set_single_value("HD Settings", "auto_set_customer_from_contact", 1)
        frappe.db.set_single_value("HD Settings", "tag_unmapped_tickets", 1)

    def test_domain_mapping_validation(self):
        """Test domain cleaning and format validation."""
        mapping = frappe.get_doc(
            {
                "doctype": "HD Domain Mapping",
                "domain": "  @VAL-TEST.IN  ",
                "customer": make_hd_customer("BPCL Test 1").name,
            }
        )
        mapping.insert(ignore_permissions=True)
        self.assertEqual(mapping.domain, "val-test.in")

        # Invalid domain without a dot should fail
        invalid_mapping = frappe.get_doc(
            {
                "doctype": "HD Domain Mapping",
                "domain": "invalid",
                "customer": make_hd_customer("BPCL Test 1").name,
            }
        )
        self.assertRaises(frappe.ValidationError, invalid_mapping.insert)

    def test_ticket_domain_customer_mapping(self):
        """Test that a new ticket automatically maps customer and default team based on sender domain."""
        customer = make_hd_customer("BPCL Corporation", domain="bpcl.co.in")
        team = make_team("BPCL Support Team")
        make_domain_mapping("bpcl.in", customer.name, default_team=team.name)

        ticket = make_ticket(
            subject="Gas Pressure Issue at Depot",
            raised_by="User Name <ops@bpcl.in>",
        )

        self.assertEqual(ticket.customer, customer.name)
        self.assertEqual(ticket.agent_group, team.name)

        # Contact should be created and linked to customer
        contact = frappe.db.get_value("Contact", {"email_id": "ops@bpcl.in"})
        self.assertTrue(contact)
        self.assertEqual(ticket.contact, contact)

        customer_doc = frappe.get_doc("HD Customer", customer.name)
        is_linked = any(row.contact_name == contact for row in customer_doc.contacts)
        self.assertTrue(is_linked)

    def test_ticket_fallback_to_customer_domain(self):
        """Test that if no HD Domain Mapping exists, it falls back to HD Customer.domain."""
        customer = make_hd_customer("GAIL India", domain="gail.co.in")

        ticket = make_ticket(
            subject="Pipeline Query",
            raised_by="Operations <nodal@gail.co.in>",
        )

        self.assertEqual(ticket.customer, customer.name)

    def test_unclassified_ticket_triage_routing(self):
        """Test MAIL-04: unrecognized domain routes to unclassified team and gets tagged."""
        triage_team = make_team("Triage Unclassified Team")
        frappe.db.set_single_value("HD Settings", "unclassified_team", triage_team.name)

        ticket = make_ticket(
            subject="General Public Query",
            raised_by="Consumer <citizen@gmail.com>",
        )

        self.assertIsNone(ticket.customer)
        self.assertEqual(ticket.agent_group, triage_team.name)

        # Check tag
        tags = ticket.get_tags() if hasattr(ticket, "get_tags") else []
        self.assertIn("unclassified-cgd", tags)
