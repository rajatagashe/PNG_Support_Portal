import json
from unittest.mock import MagicMock, patch
import frappe
from frappe.tests.utils import FrappeTestCase
from helpdesk.automation.webhook_engine import (
    dispatch_ticket_webhooks,
    verify_webhook_signature,
)
from helpdesk.test_utils import make_hd_customer, make_ticket, make_webhook


class TestWebhookEngine(FrappeTestCase):
    def setUp(self):
        frappe.set_user("Administrator")
        self.customer = make_hd_customer("Webhook CGD Customer", "webhookcgd.test")
        self.other_customer = make_hd_customer("Other CGD Customer", "othercgd.test")

    def tearDown(self):
        frappe.set_user("Administrator")

    @patch("urllib.request.urlopen")
    def test_webhook_dispatch_and_hmac_signature(self, mock_urlopen):
        # Configure mock HTTP response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"received": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        secret = "super-secret-hmac-key"
        webhook = make_webhook(
            webhook_name="Test Outgoing Webhook",
            target_url="https://api.mockcgd.test/v1/tickets",
            events="All",
            secret_key=secret,
            is_active=1,
        )

        ticket = make_ticket(
            subject="Test Webhook Dispatch",
            customer=self.customer.name,
        )

        # Verify urllib.request.urlopen was called
        self.assertTrue(mock_urlopen.called)
        call_args = mock_urlopen.call_args[0]
        req = call_args[0]
        self.assertEqual(req.get_method(), "POST")
        self.assertEqual(req.full_url, "https://api.mockcgd.test/v1/tickets")

        # Verify HMAC signature header presence and mathematical validity
        sig_header = req.headers.get("X-helpdesk-signature") or req.headers.get("X-Helpdesk-Signature")
        self.assertIsNotNone(sig_header)
        payload_bytes = req.data
        self.assertTrue(verify_webhook_signature(payload_bytes, secret, sig_header))

        # Verify HD Webhook Log record
        log = frappe.db.get_value(
            "HD Webhook Log",
            {"ticket": ticket.name, "webhook": webhook.name},
            ["name", "success", "event", "response_status"],
            as_dict=True,
        )
        self.assertIsNotNone(log)
        self.assertEqual(log.success, 1)
        self.assertEqual(log.response_status, 200)

    @patch("urllib.request.urlopen")
    def test_webhook_cgd_customer_filter(self, mock_urlopen):
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"ok": true}'
        mock_urlopen.return_value.__enter__.return_value = mock_response

        # Webhook strictly restricted to self.customer
        make_webhook(
            webhook_name="Customer A Webhook",
            target_url="https://api.customera.test/events",
            events="On Ticket Creation",
            cgd_filter=self.customer.name,
            is_active=1,
        )

        # Ticket created for a different customer
        ticket_b = make_ticket(
            subject="Customer B Ticket",
            customer=self.other_customer.name,
        )

        # Webhook should NOT have logged or dispatched for ticket_b
        log_exists = frappe.db.exists(
            "HD Webhook Log",
            {"ticket": ticket_b.name, "webhook": "Customer A Webhook"},
        )
        self.assertFalse(bool(log_exists))
