import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.api.csat import (
    create_or_get_csat_survey,
    get_csat_leaderboard,
    get_csat_survey,
    submit_csat_survey,
)
from helpdesk.test_utils import make_agent, make_hd_customer, make_ticket


class TestCSATSurvey(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.customer = make_hd_customer("CSAT Test Customer", "csattest.com")
        self.agent_email = make_agent("csat_agent@example.com", "CSAT Agent")
        self.agent_doc = frappe.get_doc("HD Agent", {"user": self.agent_email})

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_csat_lifecycle_and_submission(self):
        ticket = make_ticket(
            subject="CSAT Support Ticket",
            customer=self.customer.name,
        )

        # 1. Create survey
        survey = create_or_get_csat_survey(ticket.name, agent=self.agent_doc.name)
        self.assertEqual(survey.status, "Pending")
        self.assertTrue(bool(survey.survey_token))
        self.assertEqual(survey.ticket, ticket.name)

        # 2. Public get_csat_survey endpoint check
        public_data = get_csat_survey(survey.survey_token)
        self.assertEqual(public_data["ticket"], ticket.name)
        self.assertEqual(public_data["ticket_subject"], "CSAT Support Ticket")
        self.assertEqual(public_data["status"], "Pending")

        # 3. Submit survey
        res = submit_csat_survey(
            survey_token=survey.survey_token,
            rating=5,
            feedback="Prompt and polite resolution!",
        )
        self.assertTrue(res["success"])
        self.assertEqual(res["rating"], 5)

        # 4. Verify survey persisted state
        survey.reload()
        self.assertEqual(survey.status, "Submitted")
        self.assertEqual(survey.rating, 5)
        self.assertEqual(survey.feedback, "Prompt and polite resolution!")
        self.assertIsNotNone(survey.submitted_at)

        # 5. Verify feedback sync to ticket
        ticket.reload()
        self.assertEqual(ticket.feedback_rating, 1.0)
        self.assertEqual(ticket.feedback_extra, "Prompt and polite resolution!")

    def test_csat_leaderboard_computation(self):
        ticket1 = make_ticket(subject="T1", customer=self.customer.name)
        ticket2 = make_ticket(subject="T2", customer=self.customer.name)

        s1 = create_or_get_csat_survey(ticket1.name, agent=self.agent_doc.name)
        s2 = create_or_get_csat_survey(ticket2.name, agent=self.agent_doc.name)

        submit_csat_survey(s1.survey_token, rating=5, feedback="Flawless")
        submit_csat_survey(s2.survey_token, rating=4, feedback="Good")

        leaderboard_data = get_csat_leaderboard()
        self.assertIn("leaderboard", leaderboard_data)
        self.assertIn("summary", leaderboard_data)

        agent_entry = next((item for item in leaderboard_data["leaderboard"] if item["agent"] == self.agent_doc.name), None)
        self.assertIsNotNone(agent_entry)
        self.assertGreaterEqual(agent_entry["total_surveys"], 2)
        self.assertEqual(agent_entry["csat_percentage"], 100.0)
        self.assertGreaterEqual(agent_entry["avg_rating"], 4.5)
