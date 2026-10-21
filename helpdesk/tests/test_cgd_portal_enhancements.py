import base64
import io
import openpyxl
import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.api.cgd_portal import (
    assign_or_escalate_ticket,
    export_cgd_report_xlsx,
    get_cgd_dashboard_analytics,
    get_l1_l2_teams,
    get_ticket_attachments,
    get_ticket_tracking_info,
    provision_l1_l2_teams,
)
from helpdesk.test_utils import (
    add_customer_member,
    create_agent,
    make_customer_user,
    make_hd_customer,
    make_team,
    make_ticket,
    make_ticket_attachment,
)


class TestCgdPortalEnhancements(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.cgd = make_hd_customer("GAIL Gas Mumbai CGD", "gailgas.com")
        self.customer_user = make_customer_user("gail_operator@gailgas.com", "GAIL Operator")
        add_customer_member(self.cgd.name, self.customer_user)

        agent1 = create_agent(email="l1_agent_cgd@example.com", first_name="L1 Agent")
        agent2 = create_agent(email="l2_agent_cgd@example.com", first_name="L2 Specialist")
        self.agent1 = agent1.name
        self.agent2 = agent2.name

        self.l1_team = make_team("L1 Support", [self.agent1])
        self.l2_team = make_team("L2 Support", [self.agent2])

        self.ticket = make_ticket(
            subject="Pressure regulator valve pressure loss",
            customer=self.cgd.name,
            raised_by=self.customer_user,
            priority="High",
        )

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_l1_l2_team_provisioning(self):
        res = provision_l1_l2_teams()
        self.assertTrue(res["success"])
        teams = get_l1_l2_teams()
        self.assertGreaterEqual(len(teams), 2)
        team_names = [t["name"] for t in teams]
        self.assertIn("L1 Support", team_names)
        self.assertIn("L2 Support", team_names)

        l2_entry = next(t for t in teams if t["name"] == "L2 Support")
        self.assertEqual(l2_entry["tier"], "L2")

    def test_assign_and_escalate_workflow(self):
        # 1. Initial assignment to L1 Support
        res1 = assign_or_escalate_ticket(
            ticket_id=self.ticket.name,
            team=self.l1_team.name,
            agent=self.agent1,
            action_type="Assignment",
            new_status="Open",
            reason="Initial assignment to L1 triage desk",
        )
        self.assertTrue(res1["success"])
        self.ticket.reload()
        self.assertEqual(self.ticket.agent_group, self.l1_team.name)
        self.assertEqual(self.ticket.status, "Open")
        self.assertFalse(bool(self.ticket.is_escalated))

        # 2. Escalate to L2 Support
        res2 = assign_or_escalate_ticket(
            ticket_id=self.ticket.name,
            team=self.l2_team.name,
            agent=self.agent2,
            action_type="Escalation",
            escalation_level="L2",
            new_status="Pending",
            reason="Unresolved SCADA telemetry error requiring Tier 2 engineering investigation",
        )
        self.assertTrue(res2["success"])
        self.ticket.reload()
        self.assertEqual(self.ticket.agent_group, self.l2_team.name)
        self.assertEqual(self.ticket.status, "Pending")
        self.assertEqual(self.ticket.is_escalated, 1)
        self.assertEqual(self.ticket.escalation_level, "L2")

        # 3. Verify audit log entry
        logs = frappe.get_all(
            "HD Assignment Log",
            filters={"ticket": self.ticket.name},
            fields=["action_type", "from_team", "to_team", "from_agent", "to_agent", "assigned_by", "reassignment_notes"],
            order_by="assignment_datetime desc",
        )
        self.assertGreaterEqual(len(logs), 2)
        latest = logs[0]
        self.assertEqual(latest.action_type, "Escalation")
        self.assertEqual(latest.from_team, self.l1_team.name)
        self.assertEqual(latest.to_team, self.l2_team.name)
        self.assertEqual(latest.from_agent, self.agent1)
        self.assertEqual(latest.to_agent, self.agent2)
        self.assertEqual(latest.assigned_by, "Administrator")
        self.assertIn("SCADA telemetry", latest.reassignment_notes)

    def test_customer_resolution_details_and_notes_masking(self):
        # Resolve ticket with resolution summary and internal audit notes
        assign_or_escalate_ticket(
            ticket_id=self.ticket.name,
            team=self.l2_team.name,
            agent=self.agent2,
            action_type="Escalation",
            escalation_level="L2",
            reason="INTERNAL_CONFIDENTIAL: Firmware flash needed on RTU unit #412",
        )

        self.ticket.reload()
        self.ticket.status = "Resolved"
        self.ticket.resolution_details = "<p>Calibrated pressure regulator valve and verified gas flow rate at 1.4 bar.</p>"
        self.ticket.save(ignore_permissions=True)

        # Customer reads tracking info
        frappe.set_user(self.customer_user)
        info = get_ticket_tracking_info(self.ticket.name)

        self.assertEqual(info["ticket_id"], self.ticket.name)
        self.assertEqual(info["status"], "Resolved")
        self.assertEqual(info["escalation_level"], "L2")
        self.assertIn("Calibrated pressure regulator valve", info["resolution_details"])

        # Check that internal confidential notes were masked for customer
        self.assertTrue(len(info["history"]) > 0)
        customer_history_note = info["history"][0]["reassignment_notes"]
        self.assertNotIn("INTERNAL_CONFIDENTIAL", customer_history_note)
        self.assertIn("Escalated to technical support", customer_history_note)

    def test_ticket_attachments_secure_fetch(self):
        # Create attachments
        log_file = make_ticket_attachment(self.ticket.name, "pressure_telemetry.log", "Timestamp 10:00:00 Pressure=1.2bar")
        img_file = make_ticket_attachment(self.ticket.name, "valve_damage.png", "PNGDATA")

        frappe.set_user(self.customer_user)
        attachments = get_ticket_attachments(self.ticket.name)

        file_names = [a["file_name"] for a in attachments]
        self.assertIn("pressure_telemetry.log", file_names)
        self.assertIn("valve_damage.png", file_names)

        log_item = next(a for a in attachments if a["file_name"] == "pressure_telemetry.log")
        self.assertTrue(log_item["is_log"])
        self.assertFalse(log_item["is_image"])

        img_item = next(a for a in attachments if a["file_name"] == "valve_damage.png")
        self.assertTrue(img_item["is_image"])
        self.assertFalse(img_item["is_log"])

    def test_cgd_dashboard_analytics(self):
        # Customer view
        frappe.set_user(self.customer_user)
        data = get_cgd_dashboard_analytics(view_mode="daily")

        self.assertEqual(data["cgd"], self.cgd.name)
        self.assertIn("summary", data)
        self.assertIn("total_tickets", data["summary"])
        self.assertGreaterEqual(data["summary"]["total_tickets"], 1)
        self.assertIn("priority_breakdown", data)
        self.assertIn("team_breakdown", data)
        self.assertIn("recent_tickets", data)

        recent = data["recent_tickets"]
        ticket_item = next((t for t in recent if t["name"] == self.ticket.name), None)
        self.assertIsNotNone(ticket_item)
        self.assertEqual(ticket_item["subject"], "Pressure regulator valve pressure loss")

    def test_cgd_report_xlsx_export(self):
        frappe.set_user(self.customer_user)
        res = export_cgd_report_xlsx()

        self.assertIn("filename", res)
        self.assertTrue(res["filename"].endswith(".xlsx"))
        self.assertIn("base64_content", res)
        self.assertGreaterEqual(res["total_tickets"], 1)

        # Validate excel workbook structure
        raw_bytes = base64.b64decode(res["base64_content"])
        wb = openpyxl.load_workbook(io.BytesIO(raw_bytes))
        sheet_names = wb.sheetnames

        self.assertIn("CGD Tickets & Resolutions", sheet_names)
        self.assertIn("Assignment & Escalations", sheet_names)

        ws_tickets = wb["CGD Tickets & Resolutions"]
        header_vals = [cell.value for cell in ws_tickets[1]]
        self.assertIn("Ticket ID", header_vals)
        self.assertIn("CGD Entity", header_vals)
        self.assertIn("Resolution Summary", header_vals)
        self.assertIn("Tier Level", header_vals)
