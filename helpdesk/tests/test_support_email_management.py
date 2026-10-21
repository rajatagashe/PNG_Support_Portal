import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.api.email_management import (
    assign_email_ticket,
    export_email_report_csv,
    export_email_report_xlsx,
    get_email_dashboard_analytics,
    get_support_emails,
    get_ticket_assignment_history,
    sync_support_emails,
)
from helpdesk.test_utils import (
    create_agent,
    make_hd_customer,
    make_team,
    make_ticket,
)


class TestSupportEmailManagement(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.cgd = make_hd_customer("BPCL Mumbai City Gas", "bpcl.in")
        agent1_doc = create_agent(email="email_agent_one@example.com", first_name="Agent One")
        agent2_doc = create_agent(email="email_agent_two@example.com", first_name="Agent Two")
        self.agent1 = agent1_doc.name
        self.agent2 = agent2_doc.name
        self.team1 = make_team("CGD Operations Tier 1", [self.agent1])
        self.team2 = make_team("CGD Escalations Tier 2", [self.agent2])

        self.ticket = make_ticket(
            subject="Gas Pressure Drop Alert",
            customer=self.cgd.name,
            raised_by="customer_contact@bpcl.in",
            priority="Urgent",
        )

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_sync_support_emails_safe_execution(self):
        # Should execute safely without uncaught exceptions even if mail server is not configured
        res = sync_support_emails()
        self.assertIn("success", res)
        self.assertIn("synced_accounts", res)
        self.assertIn("total_new_emails", res)
        self.assertIn("synced_at", res)

    def test_get_support_emails(self):
        res = get_support_emails(cgd=self.cgd.name)
        self.assertIn("emails", res)
        self.assertGreaterEqual(res["total_count"], 1)

        email = next((e for e in res["emails"] if e["ticket_id"] == self.ticket.name), None)
        self.assertIsNotNone(email)
        self.assertEqual(email["subject"], "Gas Pressure Drop Alert")
        self.assertEqual(email["sender_email"], "customer_contact@bpcl.in")
        self.assertEqual(email["cgd_id"], self.cgd.name)
        self.assertIn("received_date", email)
        self.assertIn("received_time", email)
        self.assertIn("original_message_id", email)

    def test_daily_weekly_monthly_analytics(self):
        # Daily
        daily = get_email_dashboard_analytics(view_mode="daily")
        self.assertEqual(daily["view_mode"], "daily")
        self.assertIn("summary", daily)
        self.assertIn("total_received", daily["summary"])
        self.assertIn("cgd_distribution", daily)
        self.assertIn("team_distribution", daily)
        self.assertIn("time_series", daily)

        # Weekly
        weekly = get_email_dashboard_analytics(view_mode="weekly")
        self.assertEqual(weekly["view_mode"], "weekly")
        self.assertIn("summary", weekly)
        self.assertIn("Trailing 7 Days", weekly["period_label"])

        # Monthly
        monthly = get_email_dashboard_analytics(view_mode="monthly")
        self.assertEqual(monthly["view_mode"], "monthly")
        self.assertIn("summary", monthly)
        self.assertIn("Trailing 30 Days", monthly["period_label"])

    def test_assign_email_ticket_and_auditable_history(self):
        # Assign to Team 1 and Agent 1
        res1 = assign_email_ticket(
            ticket_id=self.ticket.name,
            team=self.team1.name,
            agent=self.agent1,
            notes="Initial triage assignment to Tier 1",
            new_status="Open",
        )
        self.assertTrue(res1["success"])
        self.assertEqual(res1["team"], self.team1.name)
        self.assertEqual(res1["agent"], self.agent1)

        # Reassign to Team 2 and Agent 2
        res2 = assign_email_ticket(
            ticket_id=self.ticket.name,
            team=self.team2.name,
            agent=self.agent2,
            notes="Escalated to Tier 2 specialist team",
            new_status="Pending",
        )
        self.assertTrue(res2["success"])
        self.assertEqual(res2["team"], self.team2.name)
        self.assertEqual(res2["agent"], self.agent2)

        # Verify audit history
        history = get_ticket_assignment_history(self.ticket.name)
        self.assertGreaterEqual(len(history), 2)

        # Latest event must be escalation to Team 2
        latest = history[0]
        self.assertEqual(latest["to_team"], self.team2.name)
        self.assertEqual(latest["to_agent"], self.agent2)
        self.assertEqual(latest["from_team"], self.team1.name)
        self.assertEqual(latest["from_agent"], self.agent1)
        self.assertEqual(latest["reassignment_notes"], "Escalated to Tier 2 specialist team")
        self.assertEqual(latest["assigned_by"], "Administrator")

        # Previous event must be initial assignment to Team 1
        prev = history[1]
        self.assertEqual(prev["to_team"], self.team1.name)
        self.assertEqual(prev["to_agent"], self.agent1)
        self.assertEqual(prev["reassignment_notes"], "Initial triage assignment to Tier 1")

    def test_export_email_report_xlsx_multi_sheet(self):
        # Perform assignment so history exists
        assign_email_ticket(
            ticket_id=self.ticket.name,
            team=self.team1.name,
            agent=self.agent1,
            notes="Audit log for Excel export",
        )

        xlsx_res = export_email_report_xlsx(cgd=self.cgd.name)
        self.assertIn("filename", xlsx_res)
        self.assertTrue(xlsx_res["filename"].endswith(".xlsx"))
        self.assertIn("base64_content", xlsx_res)
        self.assertGreaterEqual(xlsx_res["total_emails"], 1)
        self.assertGreaterEqual(xlsx_res["total_audit_records"], 1)

    def test_export_email_report_csv(self):
        csv_res = export_email_report_csv(cgd=self.cgd.name)
        self.assertIn("csv_content", csv_res)
        self.assertIn("filename", csv_res)
        self.assertIn("Gas Pressure Drop Alert", csv_res["csv_content"])
        self.assertIn("customer_contact@bpcl.in", csv_res["csv_content"])
