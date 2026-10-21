import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.api.customer_signup import (
    approve_signup_request,
    get_pending_signup_requests,
    reject_signup_request,
    submit_signup_request,
)
from helpdesk.test_utils import (
    make_agent,
    make_agent_manager,
    make_customer_signup_request,
    make_hd_customer,
)


class TestCustomerSignup(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.customer = make_hd_customer("IGL Gas")
        self.manager = make_agent_manager(prefix="signup-mgr")

    def test_submit_signup_request(self):
        """Test public submission of signup request."""
        frappe.set_user("Guest")
        res = submit_signup_request(
            full_name="Rajesh Kumar",
            email="rajesh@igl.co.in",
            requested_cgd=self.customer.name,
            designation="Operations Lead",
        )
        self.assertTrue(res.get("success"))
        self.assertTrue(res.get("request_id"))

        doc = frappe.get_doc("HD Customer Signup Request", res["request_id"])
        self.assertEqual(doc.status, "Pending")
        self.assertEqual(doc.email, "rajesh@igl.co.in")

    def test_duplicate_submission_blocked(self):
        """Test that submitting duplicate requests with same email is prevented."""
        make_customer_signup_request("dup@igl.co.in", "Dup User", self.customer.name)
        frappe.set_user("Guest")

        self.assertRaises(
            frappe.DuplicateEntryError,
            submit_signup_request,
            full_name="Dup User 2",
            email="dup@igl.co.in",
            requested_cgd=self.customer.name,
        )

    def test_approve_signup_request(self):
        """Test that manager approval activates user, links contact to customer, and assigns role."""
        req = make_customer_signup_request("approved.user@igl.co.in", "Approved User", self.customer.name)

        frappe.set_user(self.manager)
        res = approve_signup_request(req.name, customer=self.customer.name, role="HD Customer")
        self.assertEqual(res.get("status"), "Approved")

        req.reload()
        self.assertEqual(req.status, "Approved")
        self.assertEqual(req.reviewed_by, self.manager)

        # Verify User was created and enabled
        user = frappe.get_doc("User", "approved.user@igl.co.in")
        self.assertEqual(user.enabled, 1)
        self.assertIn("HD Customer", [r.role for r in user.roles])

        # Verify Contact was created and linked to customer
        contact = frappe.db.get_value("Contact", {"email_id": "approved.user@igl.co.in"})
        self.assertTrue(contact)

        customer_doc = frappe.get_doc("HD Customer", self.customer.name)
        is_member = any(row.contact_name == contact for row in customer_doc.contacts)
        self.assertTrue(is_member)

    def test_reject_signup_request(self):
        """Test rejecting a signup request records the reason and reviewer."""
        req = make_customer_signup_request("rejected.user@unknown.com", "Rejected User", self.customer.name)

        frappe.set_user(self.manager)
        res = reject_signup_request(req.name, reason="Not an authorized CGD representative")
        self.assertEqual(res.get("status"), "Rejected")

        req.reload()
        self.assertEqual(req.status, "Rejected")
        self.assertEqual(req.rejection_reason, "Not an authorized CGD representative")
        self.assertEqual(req.reviewed_by, self.manager)

        # User account should NOT exist
        self.assertFalse(frappe.db.exists("User", "rejected.user@unknown.com"))

    def test_unauthorized_user_cannot_approve(self):
        """Test that regular agents cannot approve signup requests."""
        agent = make_agent("regular.agent@helpdesk.com")
        req = make_customer_signup_request("agent.try@igl.co.in", "Agent Try", self.customer.name)

        frappe.set_user("regular.agent@helpdesk.com")
        self.assertRaises(
            frappe.PermissionError,
            approve_signup_request,
            req.name,
        )
