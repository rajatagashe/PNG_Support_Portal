import frappe
from frappe.tests.utils import FrappeTestCase

from helpdesk.api.auth import get_user
from helpdesk.api.custom_reports import generate_ticket_report, get_hourly_ticket_heatmap
from helpdesk.api.doc import get_list_data
from helpdesk.api.email_management import (
    assign_email_ticket,
    get_email_dashboard_analytics,
    get_support_emails,
)
from helpdesk.api.session import get_users
from helpdesk.patches.add_support_email_role import execute as repair_support_email_perms
from helpdesk.test_utils import (
    create_agent,
    make_granular_agent,
    make_hd_customer,
    make_support_email_user,
    make_ticket,
)
from helpdesk.utils import SUPPORT_EMAIL_ROLE, is_admin, is_agent, is_support_email_only


class TestRoleBasedAccessControl(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.email_user = make_support_email_user("support.email.user@png.test")
        self.agent = create_agent("rbac.agent@png.test").name
        self.customer = make_hd_customer("RBAC Test CGD", "rbac-cgd.test").name

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_admin_has_full_access(self):
        self.assertTrue(is_admin("Administrator"))
        self.assertFalse(is_support_email_only("Administrator"))

        user_info = get_user()
        self.assertTrue(user_info["is_admin"])
        self.assertFalse(user_info["is_email_user_only"])
        self.assertEqual(user_info["role_type"], "admin")

        self.assertIn("emails", get_support_emails(page=1, page_length=5))
        self.assertIsNotNone(get_list_data("HD Agent"))
        self.assertIn("rows", generate_ticket_report(group_by="customer"))

    def test_email_user_is_not_an_agent(self):
        self.assertFalse(is_agent(self.email_user))
        self.assertTrue(is_support_email_only(self.email_user))

        frappe.set_user(self.email_user)
        user_info = get_user()
        self.assertFalse(user_info["is_admin"])
        self.assertFalse(user_info["is_agent"])
        self.assertTrue(user_info["is_email_user_only"])
        self.assertEqual(user_info["role_type"], "user")
        self.assertTrue(user_info["has_desk_access"])

    def test_email_user_can_use_support_email_page(self):
        frappe.set_user(self.email_user)
        self.assertIn("emails", get_support_emails(page=1, page_length=5))
        self.assertIn("summary", get_email_dashboard_analytics(view_mode="daily"))

        # the CGD filter on the page reads customers, but never writes them
        self.assertTrue(frappe.has_permission("HD Customer", "read", doc=self.customer))
        self.assertFalse(frappe.has_permission("HD Customer", "write", doc=self.customer))
        customers = frappe.get_list("HD Customer", pluck="name")
        self.assertIn(self.customer, customers)

    def test_email_user_is_blocked_from_agent_apis(self):
        frappe.set_user("Administrator")
        ticket = make_ticket(subject="RBAC isolation check")

        frappe.set_user(self.email_user)
        for call in (
            get_users,
            lambda: assign_email_ticket(ticket.name, agent=self.agent),
            lambda: get_list_data("HD Ticket"),
            lambda: get_list_data("HD Agent"),
            lambda: generate_ticket_report(group_by="customer"),
            get_hourly_ticket_heatmap,
        ):
            with self.assertRaises(frappe.PermissionError):
                call()
        self.assertFalse(frappe.has_permission("HD Ticket", "read", doc=ticket.name))

    def test_agents_with_email_role_are_not_restricted(self):
        frappe.get_doc("User", self.agent).add_roles(SUPPORT_EMAIL_ROLE)
        self.assertFalse(is_support_email_only(self.agent))

        tier1 = make_granular_agent("rbac.tier1@png.test", "HD Tier 1 Agent")
        frappe.get_doc("User", tier1).add_roles(SUPPORT_EMAIL_ROLE)
        self.assertFalse(is_support_email_only(tier1))

    def test_role_setup_keeps_standard_perms(self):
        # the old script inserted a lone Custom DocPerm, hiding HD Team's JSON perms
        frappe.db.delete("Custom DocPerm", {"parent": "HD Team"})
        frappe.get_doc(
            {
                "doctype": "Custom DocPerm",
                "parent": "HD Team",
                "parenttype": "DocType",
                "parentfield": "permissions",
                "role": SUPPORT_EMAIL_ROLE,
                "read": 1,
            }
        ).insert(ignore_permissions=True)
        frappe.clear_cache(doctype="HD Team")

        repair_support_email_perms()

        self.assertTrue(frappe.has_permission("HD Team", "write", user=self.agent))
        self.assertTrue(frappe.has_permission("HD Team", "read", user=self.email_user))
        self.assertFalse(frappe.has_permission("HD Team", "write", user=self.email_user))
