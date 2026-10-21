import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.api.custom_reports import (
    export_report_csv,
    export_report_html,
    export_report_json,
    generate_ticket_report,
    get_cgd_entity_breakdown,
    get_hourly_ticket_heatmap,
    send_scheduled_analytics_digest,
)
from helpdesk.test_utils import make_hd_customer, make_ticket


class TestCustomReports(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.customer = make_hd_customer("Reporting CGD Entity", "reportcgd.test")
        self.ticket1 = make_ticket(
            subject="Reporting Test Ticket 1",
            customer=self.customer.name,
            priority="High",
        )
        self.ticket2 = make_ticket(
            subject="Reporting Test Ticket 2",
            customer=self.customer.name,
            priority="Low",
        )

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_generate_ticket_report_by_customer(self):
        report = generate_ticket_report(group_by="customer", customer=self.customer.name)
        self.assertEqual(report["group_by"], "customer")
        self.assertIn("rows", report)
        self.assertIn("breakdown", report)
        self.assertIn("summary", report)

        matched_row = next((r for r in report["rows"] if r["group_key"] == self.customer.name), None)
        self.assertIsNotNone(matched_row)
        self.assertGreaterEqual(matched_row["total_tickets"], 2)
        self.assertIn("sla_adherence_percent", matched_row)

    def test_generate_ticket_report_by_priority(self):
        report = generate_ticket_report(group_by="priority")
        self.assertEqual(report["group_by"], "priority")
        self.assertTrue(len(report["rows"]) > 0)
        self.assertIn("breakdown", report)

    def test_export_report_csv(self):
        csv_data = export_report_csv(group_by="customer", customer=self.customer.name)
        self.assertIn("Customer,Total Tickets,Open Tickets", csv_data)
        self.assertIn(self.customer.name, csv_data)
        self.assertIn("filename", csv_data)

    def test_export_report_json(self):
        json_res = export_report_json(group_by="customer", customer=self.customer.name)
        self.assertIn("json_content", json_res)
        self.assertIn("filename", json_res)
        self.assertIn("Reporting CGD Entity", json_res["json_content"])

    def test_export_report_html(self):
        html_res = export_report_html(group_by="customer", customer=self.customer.name)
        self.assertIn("html_content", html_res)
        self.assertIn("filename", html_res)
        self.assertIn("Helpdesk Operations Executive Summary", html_res["html_content"])
        self.assertIn("Print / Save PDF", html_res["html_content"])

    def test_get_cgd_entity_breakdown(self):
        res = get_cgd_entity_breakdown()
        self.assertIn("entities", res)
        self.assertGreaterEqual(res["total_entities"], 1)
        cgd_entry = next((e for e in res["entities"] if e["customer"] == self.customer.name), None)
        self.assertIsNotNone(cgd_entry)
        self.assertGreaterEqual(cgd_entry["total_tickets"], 2)
        self.assertIn("sla_compliance_rate", cgd_entry)

    def test_get_hourly_ticket_heatmap(self):
        heatmap = get_hourly_ticket_heatmap(days=7)
        self.assertIn("distribution", heatmap)
        self.assertEqual(len(heatmap["distribution"]), 24)
        self.assertIn("peak_hour", heatmap)

    def test_send_scheduled_analytics_digest(self):
        res = send_scheduled_analytics_digest(recipients=["support_lead@example.com"])
        self.assertTrue(res["success"])
        self.assertIn("support_lead@example.com", res["recipients"])
        self.assertIn("summary", res)
