# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.api.portal import get_portal_branding, get_portal_cgd_entities
from helpdesk.test_utils import make_hd_customer, make_vip_customer


class TestPortalBranding(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")

    def test_guest_portal_branding(self):
        """Guest user receives default MyPNG system branding."""
        frappe.set_user("Guest")
        branding = get_portal_branding()
        self.assertFalse(branding["is_customer"])
        self.assertIn("Support", branding["brand_name"])
        self.assertIn("City Gas Distribution", branding["banner_title"])
        self.assertFalse(branding["is_vip"])

    def test_customer_portal_branding(self):
        """Logged-in customer contact receives personalized entity branding."""
        frappe.set_user("Administrator")
        customer = make_hd_customer("BPCL Natural Gas", domain="bpcl.test")

        # Create contact and user
        user_email = "consumer@bpcl.test"
        if not frappe.db.exists("User", user_email):
            user = frappe.get_doc({
                "doctype": "User",
                "email": user_email,
                "first_name": "BPCL",
                "last_name": "Consumer",
                "roles": [{"role": "HD Customer"}],
            }).insert(ignore_permissions=True)

        if not frappe.db.exists("Contact", {"email_id": user_email}):
            contact = frappe.get_doc({
                "doctype": "Contact",
                "first_name": "BPCL Consumer",
                "email_id": user_email,
                "user": user_email,
            })
            contact.append("email_ids", {"email_id": user_email, "is_primary": 1})
            contact.insert(ignore_permissions=True)

        # Link contact to customer
        customer_doc = frappe.get_doc("HD Customer", customer.name)
        if not any(row.contact_name == "BPCL Consumer" for row in customer_doc.contacts):
            customer_doc.append("contacts", {"contact_name": "BPCL Consumer"})
            customer_doc.save(ignore_permissions=True)

        frappe.set_user(user_email)
        branding = get_portal_branding()

        self.assertTrue(branding["is_customer"])
        self.assertEqual(branding["customer_name"], "BPCL Natural Gas")
        self.assertIn("BPCL Natural Gas", branding["brand_name"])
        self.assertIn("BPCL Natural Gas", branding["banner_title"])

    def test_vip_customer_portal_branding(self):
        """VIP customer user receives VIP indicator in portal branding."""
        frappe.set_user("Administrator")
        vip_cust = make_vip_customer("GAIL Industrial Elite", is_vip=1, vip_priority="Urgent")

        vip_user = "ops_lead@gail.test"
        if not frappe.db.exists("User", vip_user):
            frappe.get_doc({
                "doctype": "User",
                "email": vip_user,
                "first_name": "GAIL",
                "last_name": "Lead",
                "roles": [{"role": "HD Customer Manager"}],
            }).insert(ignore_permissions=True)

        if not frappe.db.exists("Contact", {"email_id": vip_user}):
            contact = frappe.get_doc({
                "doctype": "Contact",
                "first_name": "GAIL Lead",
                "email_id": vip_user,
                "user": vip_user,
            })
            contact.append("email_ids", {"email_id": vip_user, "is_primary": 1})
            contact.insert(ignore_permissions=True)

        cust_doc = frappe.get_doc("HD Customer", vip_cust.name)
        if not any(row.contact_name == "GAIL Lead" for row in cust_doc.contacts):
            cust_doc.append("contacts", {"contact_name": "GAIL Lead"})
            cust_doc.save(ignore_permissions=True)

        frappe.set_user(vip_user)
        branding = get_portal_branding()

        self.assertTrue(branding["is_customer"])
        self.assertTrue(branding["is_vip"])
        self.assertEqual(branding["vip_priority"], "Urgent")

    def test_get_portal_cgd_entities(self):
        """CGD entities directory returns active customers."""
        frappe.set_user("Guest")
        make_hd_customer("IGL Gas Network")
        entities = get_portal_cgd_entities()
        self.assertIsInstance(entities, list)
        self.assertTrue(any(e["customer_name"] == "IGL Gas Network" for e in entities))
