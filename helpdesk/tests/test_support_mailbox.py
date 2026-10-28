import imaplib
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase, change_settings
from frappe.utils import add_to_date, now_datetime
from frappe.utils.file_lock import LockTimeoutError

from helpdesk.api.email_management import (
    get_support_emails,
    is_backing_off,
    sync_support_emails,
)
from helpdesk.api.support_mailbox import (
    activate_support_mailbox,
    download_support_email_attachment,
    get_mailbox_authorization_url,
    get_mailbox_status,
    get_support_email,
    reply_to_support_email,
    set_support_email_seen,
)
from helpdesk.overrides.email_account import CustomInboundMail
from helpdesk.test_utils import (
    clear_mailbox_sync_status,
    create_agent,
    make_connected_app,
    make_customer_user,
    make_email_attachment,
    make_raw_support_email,
    make_support_email,
    make_support_email_user,
    make_support_mailbox,
    make_ticket,
)


class TestMailboxSyncStatus(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.account = make_support_mailbox("Sync Status Mailbox")
        clear_mailbox_sync_status(self.account.name)

    def tearDown(self):
        clear_mailbox_sync_status(self.account.name)
        frappe.set_user("Administrator")

    def test_errors_are_classified(self):
        cases = {
            "connection_failed": OSError("Connection refused"),
            "authentication_failed": imaplib.IMAP4.error("AUTHENTICATE failed."),
            "sync_failed": ValueError("unexpected"),
        }
        for kind, exc in cases.items():
            self.assertEqual(self.account.classify_sync_error(exc), kind)

    def test_oauth_mailbox_without_token_needs_authorization(self):
        app = make_connected_app(f"Mailbox App {frappe.generate_hash(length=6)}")
        account = make_support_mailbox(
            f"OAuth Mailbox {frappe.generate_hash(length=6)}",
            auth_method="OAuth",
            connected_app=app.name,
            connected_user="Administrator",
        )
        self.assertEqual(account.classify_sync_error(OSError("timed out")), "authorization_required")

        status = self.status_of(account.name)
        self.assertEqual(status["error_type"], "authorization_required")
        result = sync_support_emails(account.name)
        self.assertEqual(result["errors"][0]["error_type"], "authorization_required")

    def test_app_only_mailbox_reports_missing_exchange_grants(self):
        app = make_connected_app(f"App Only {frappe.generate_hash(length=6)}")
        account = make_support_mailbox(
            f"App Only Mailbox {frappe.generate_hash(length=6)}",
            auth_method="OAuth",
            connected_app=app.name,
            backend_app_flow=1,
        )
        rejected = imaplib.IMAP4.error("AUTHENTICATE failed.")
        self.assertEqual(account.classify_sync_error(rejected), "app_access_denied")
        self.assertEqual(account.classify_sync_error(OSError("timed out")), "connection_failed")

        status = self.status_of(account.name)
        self.assertTrue(status["uses_app_access"])
        self.assertIsNone(status["error_type"])
        # there is no sign-in to start for an app-only mailbox
        with self.assertRaises(frappe.ValidationError):
            get_mailbox_authorization_url(account.name)

    def test_connection_failure_is_reported_without_the_raw_error(self):
        with patch.object(
            type(self.account),
            "get_incoming_server",
            side_effect=OSError("Connection refused by imap.secret-host.internal"),
        ):
            result = sync_support_emails(self.account.name)

        self.assertFalse(result["success"])
        error = result["errors"][0]
        self.assertEqual(error["error_type"], "connection_failed")
        self.assertNotIn("secret-host", error["message"])
        status = self.status_of(self.account.name)
        self.assertEqual(status["state"], "error")
        self.assertNotIn("secret-host", status["message"])

    def test_successful_pull_marks_mailbox_connected(self):
        self.account.record_sync_failure()
        with patch.object(type(self.account), "get_incoming_server") as server:
            server.return_value.select_imap_folder.return_value = False
            result = sync_support_emails(self.account.name)

        self.assertTrue(result["success"])
        self.assertEqual(self.status_of(self.account.name)["state"], "connected")

    def test_busy_mailbox_reports_in_progress(self):
        with patch("helpdesk.overrides.email_account.filelock", side_effect=LockTimeoutError("busy")):
            result = sync_support_emails(self.account.name)
        self.assertEqual(result["synced_accounts"][0]["status"], "in_progress")

    def test_scheduler_backs_off_after_a_failure(self):
        recent = {"state": "error", "last_failure_at": now_datetime()}
        old = {"state": "error", "last_failure_at": add_to_date(now_datetime(), minutes=-6)}
        self.assertTrue(is_backing_off(recent))
        self.assertFalse(is_backing_off(old))
        self.assertFalse(is_backing_off({"state": "connected"}))

    def test_scheduler_runs_mail_sync_every_minute(self):
        """Both scheduler_events blocks must survive; a second dict used to replace the first."""
        events = frappe.get_hooks("scheduler_events", app_name="helpdesk")
        self.assertIn(
            "helpdesk.api.email_management.scheduled_sync_support_emails", events["cron"]["* * * * *"]
        )
        self.assertIn("helpdesk.automation.automation_engine.execute_automations", events["hourly"])
        self.assertIn(
            "helpdesk.helpdesk.doctype.hd_ticket.hd_ticket.close_tickets_after_n_days", events["daily"]
        )

    def status_of(self, account: str) -> dict:
        return next(a for a in get_mailbox_status()["accounts"] if a["account"] == account)


class TestMailboxAdminActions(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.email_user = make_support_email_user("mailbox.admin.check@png.test")
        self.account = make_support_mailbox("Admin Actions Mailbox")

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_email_user_cannot_reconnect_or_activate(self):
        frappe.set_user(self.email_user)
        self.assertFalse(get_mailbox_status()["can_reconnect"])
        with self.assertRaises(frappe.PermissionError):
            get_mailbox_authorization_url(self.account.name)
        with self.assertRaises(frappe.PermissionError):
            activate_support_mailbox(self.account.name)

    def test_customer_cannot_read_mailbox_status(self):
        customer = make_customer_user("mailbox.customer@cgd.test")
        frappe.set_user(customer)
        with self.assertRaises(frappe.PermissionError):
            get_mailbox_status()

    def test_failed_activation_shows_only_the_friendly_message(self):
        def rejected_login(*args, **kwargs):
            frappe.msgprint("AUTHENTICATE failed.")
            raise imaplib.IMAP4.error("AUTHENTICATE failed.")

        with patch.object(type(self.account), "save", side_effect=rejected_login):
            with self.assertRaises(frappe.ValidationError):
                activate_support_mailbox(self.account.name)

        messages = [m.get("message") for m in frappe.get_message_log()]
        self.assertEqual(messages, ["The mail server rejected the support mailbox login."])
        frappe.clear_messages()

    def test_basic_mailbox_cannot_start_oauth_sign_in(self):
        with self.assertRaises(frappe.ValidationError):
            get_mailbox_authorization_url(self.account.name)


class TestSupportEmailDetail(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.email_user = make_support_email_user("detail.email.user@png.test")
        self.customer = make_customer_user("detail.customer@cgd.test")
        self.ticket = make_ticket(subject="Meter reading dispute", raised_by="asha@cgd.test")
        self.received = make_support_email(
            self.ticket.name,
            sender="asha@cgd.test",
            content="<p>Reading is 0042</p><script>alert(1)</script>",
        )
        self.attachment = make_email_attachment("Communication", self.received.name)

    def tearDown(self):
        frappe.set_user("Administrator")

    def test_email_user_sees_full_thread_and_attachments(self):
        frappe.set_user(self.email_user)
        email = get_support_email(self.ticket.name)

        message = next(m for m in email["messages"] if m.name == self.received.name)
        self.assertEqual(message.sender, "asha@cgd.test")
        self.assertEqual(message.sender_full_name, "Asha Customer")
        self.assertIn("Reading is 0042", message.content)
        self.assertNotIn("<script>", message.content)
        self.assertEqual([a.file_name for a in message.attachments], ["meter-photo.txt"])
        self.assertFalse(email["can_open_ticket"])

    def test_customer_cannot_read_support_email(self):
        frappe.set_user(self.customer)
        with self.assertRaises(frappe.PermissionError):
            get_support_email(self.ticket.name)

    def test_read_state_filters_and_toggles(self):
        frappe.set_user(self.email_user)
        self.assertIn(self.ticket.name, self.listed_tickets(read_state="unread"))

        set_support_email_seen(self.ticket.name, 1)
        self.assertEqual(frappe.db.get_value("Communication", self.received.name, "seen"), 1)
        self.assertNotIn(self.ticket.name, self.listed_tickets(read_state="unread"))
        self.assertIn(self.ticket.name, self.listed_tickets(read_state="read"))

        set_support_email_seen(self.ticket.name, 0)
        self.assertIn(self.ticket.name, self.listed_tickets(read_state="unread"))

    def test_search_matches_message_text_and_list_shows_details(self):
        frappe.set_user(self.email_user)
        rows = get_support_emails(search_text="Reading is 0042", page_length=100)["emails"]
        row = next(r for r in rows if r["ticket_id"] == self.ticket.name)
        self.assertEqual(row["sender_name"], "Asha Customer")
        self.assertTrue(row["is_unread"])
        self.assertTrue(row["has_attachments"])

    def test_attachment_download_is_limited_to_support_emails(self):
        frappe.set_user(self.email_user)
        download_support_email_attachment(self.attachment.name)
        self.assertEqual(frappe.local.response.filename, "meter-photo.txt")
        self.assertEqual(frappe.local.response.type, "download")

        frappe.set_user("Administrator")
        other = make_email_attachment("User", "Administrator", file_name="private-note.txt")
        frappe.set_user(self.email_user)
        with self.assertRaises(frappe.PermissionError):
            download_support_email_attachment(other.name)

    def listed_tickets(self, **filters) -> list[str]:
        return [r["ticket_id"] for r in get_support_emails(page_length=100, **filters)["emails"]]


class TestSupportEmailReply(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.email_user = make_support_email_user("reply.email.user@png.test")
        self.agent = create_agent("reply.agent@png.test").name
        self.customer = make_customer_user("reply.customer@cgd.test")
        self.ticket = make_ticket(subject="Billing question", raised_by="ravi@cgd.test")
        make_support_email(self.ticket.name, sender="ravi@cgd.test")

    def tearDown(self):
        frappe.set_user("Administrator")

    @change_settings("HD Settings", {"skip_email_workflow": 1})
    def test_email_user_reply_is_logged_and_escaped(self):
        frappe.set_user(self.email_user)
        reply_to_support_email(self.ticket.name, "Thanks <b>Ravi</b>\nWe will check.")

        frappe.set_user("Administrator")
        sent = frappe.get_all(
            "Communication",
            {"reference_name": self.ticket.name, "sent_or_received": "Sent"},
            ["content", "sender"],
        )
        self.assertEqual(len(sent), 1)
        self.assertEqual(sent[0].sender, self.email_user)
        self.assertIn("&lt;b&gt;Ravi&lt;/b&gt;<br>We will check.", sent[0].content)
        # the reply records the agent response time on the ticket
        self.assertIsNotNone(frappe.db.get_value("HD Ticket", self.ticket.name, "first_responded_on"))
        unread = frappe.db.count(
            "Communication", {"reference_name": self.ticket.name, "sent_or_received": "Received", "seen": 0}
        )
        self.assertEqual(unread, 0)

    @change_settings("HD Settings", {"skip_email_workflow": 1})
    def test_agent_can_reply(self):
        frappe.set_user(self.agent)
        reply_to_support_email(self.ticket.name, "Looking into it.")
        frappe.set_user("Administrator")
        self.assertTrue(
            frappe.db.exists("Communication", {"reference_name": self.ticket.name, "sent_or_received": "Sent"})
        )

    def test_empty_reply_is_rejected(self):
        frappe.set_user(self.email_user)
        with self.assertRaises(frappe.ValidationError):
            reply_to_support_email(self.ticket.name, "   ")

    def test_customer_cannot_reply_from_support_page(self):
        frappe.set_user(self.customer)
        with self.assertRaises(frappe.PermissionError):
            reply_to_support_email(self.ticket.name, "I am not support staff")


class TestInboundSupportEmail(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.account = make_support_mailbox("Inbound Mailbox")

    def test_same_email_fetched_twice_creates_one_ticket(self):
        message_id = f"dup-{frappe.generate_hash(length=8)}@cgd.test"
        raw = make_raw_support_email(message_id, "dup.sender@cgd.test", "Duplicate check")

        for _ in range(2):
            CustomInboundMail(raw, self.account, append_to="HD Ticket").process()

        communications = frappe.get_all("Communication", {"message_id": message_id}, pluck="reference_name")
        self.assertEqual(len(communications), 1)
        self.assertEqual(frappe.db.get_value("HD Ticket", communications[0], "raised_by"), "dup.sender@cgd.test")

    def test_received_email_notifies_open_pages(self):
        ticket = make_ticket(subject="Realtime check")
        with patch("helpdesk.extends.communication.publish_event") as publish:
            make_support_email(ticket.name)
            make_support_email(ticket.name, sent_or_received="Sent")
        publish.assert_called_once_with("helpdesk:support-email-received")
