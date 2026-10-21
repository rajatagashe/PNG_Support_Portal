import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.api.widget import (
    get_widget_config,
    search_widget_articles,
    submit_widget_ticket,
)
from helpdesk.test_utils import make_hd_customer


class TestWidgetAPI(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.customer = make_hd_customer("Widget CGD", "widgetcgd.test")

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_widget_config(self):
        cfg = get_widget_config()
        self.assertIn("title", cfg)
        self.assertEqual(cfg["primary_color"], "#ea580c")
        self.assertEqual(cfg["secondary_color"], "#fed7aa")
        self.assertIn("ticket_types", cfg)

    def test_widget_article_search(self):
        # Create published article
        article_title = "Billing & Gas Invoicing Guide"
        if not frappe.db.exists("HD Article", {"title": article_title}):
            article = frappe.get_doc({
                "doctype": "HD Article",
                "title": article_title,
                "content": "<p>PNG invoices are generated monthly based on meter readings.</p>",
                "status": "Published",
            })
            article.insert(ignore_permissions=True)

        results = search_widget_articles("Invoicing")
        self.assertTrue(len(results) > 0)
        matched = next((a for a in results if "Invoicing" in a["title"]), None)
        self.assertIsNotNone(matched)

    def test_submit_widget_ticket(self):
        res = submit_widget_ticket(
            subject="Widget Pipeline Inspection Request",
            description="Requesting safety check for commercial gas connection.",
            email="manager@widgetcgd.test",
            name="Plant Manager",
        )
        self.assertTrue(res["success"])
        ticket_name = res["ticket_name"]
        self.assertTrue(bool(ticket_name))

        ticket = frappe.get_doc("HD Ticket", ticket_name)
        self.assertEqual(ticket.subject, "Widget Pipeline Inspection Request")
        self.assertEqual(ticket.customer, self.customer.name)
        self.assertTrue(bool(ticket.guest_token))
