import hashlib
import hmac
import json
import uuid
import frappe
from frappe.utils import now_datetime
import urllib.request
import urllib.error


def dispatch_ticket_webhooks(ticket, event, old_doc=None):
    """Evaluate and dispatch outgoing webhooks for ticket lifecycle events."""
    if ticket.flags.in_webhook_dispatch:
        return
    ticket.flags.in_webhook_dispatch = True

    try:
        webhooks = get_matching_webhooks(ticket, event, old_doc)
        if not webhooks:
            return

        payload = build_webhook_payload(ticket, event, old_doc)

        for wh in webhooks:
            send_single_webhook(wh, payload, ticket.name, event)
    except Exception as e:
        frappe.log_error(f"Error dispatching webhooks for ticket {ticket.name}: {str(e)}", "Webhook Dispatch Error")


def get_matching_webhooks(ticket, event, old_doc=None):
    """Find active HD Webhook records matching event and customer filters."""
    filters = {"is_active": 1}
    active_webhooks = frappe.get_all(
        "HD Webhook",
        filters=filters,
        fields=["name", "webhook_name", "target_url", "secret_key", "events", "cgd_filter", "custom_headers"],
    )

    matching = []
    for wh in active_webhooks:
        # Check event match
        if wh.events != "All" and wh.events != event:
            continue

        # Check CGD customer filter
        if wh.cgd_filter and ticket.customer and wh.cgd_filter != ticket.customer:
            continue

        # For 'On Status Change', verify status actually changed
        if event == "On Status Change" and old_doc:
            if ticket.status == old_doc.status:
                continue

        matching.append(wh)

    return matching


def build_webhook_payload(ticket, event, old_doc=None):
    """Assemble structured JSON payload for outgoing webhooks."""
    data = {
        "event": event,
        "delivery_id": str(uuid.uuid4()),
        "timestamp": now_datetime().isoformat(),
        "ticket": {
            "name": ticket.name,
            "subject": ticket.get("subject"),
            "status": ticket.get("status"),
            "priority": ticket.get("priority"),
            "customer": ticket.get("customer"),
            "contact": ticket.get("contact"),
            "agent": ticket.get("agent") or (ticket.get_assigned_agent() if hasattr(ticket, "get_assigned_agent") else None),
            "team": ticket.get("team"),
            "raised_by": ticket.get("raised_by"),
            "creation": str(ticket.creation),
            "modified": str(ticket.modified),
        },
    }

    if old_doc and hasattr(old_doc, "status") and old_doc.status != ticket.status:
        data["previous_status"] = old_doc.status

    return data


def send_single_webhook(webhook, payload, ticket_name, event):
    """Execute HTTP POST with HMAC SHA-256 signature and record HD Webhook Log."""
    payload_str = json.dumps(payload, default=str)
    payload_bytes = payload_str.encode("utf-8")

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Frappe-Helpdesk-Webhook/2.0",
        "X-Helpdesk-Event": event,
        "X-Helpdesk-Delivery": payload.get("delivery_id", ""),
    }

    # Read decrypted password field via get_password if exists
    secret_key = None
    if frappe.db.exists("HD Webhook", webhook["name"]):
        try:
            secret_key = frappe.get_doc("HD Webhook", webhook["name"]).get_password("secret_key")
        except Exception:
            secret_key = None
    if not secret_key and webhook.get("secret_key") and webhook.get("secret_key") != "*****":
        secret_key = webhook.get("secret_key")

    if secret_key:
        signature = hmac.new(secret_key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
        headers["X-Helpdesk-Signature"] = f"sha256={signature}"

    # Merge custom headers
    if webhook.get("custom_headers"):
        try:
            custom = json.loads(webhook["custom_headers"])
            if isinstance(custom, dict):
                headers.update(custom)
        except Exception:
            pass

    target_url = webhook.get("target_url")
    response_status = None
    response_body = ""
    error_message = ""
    success = False

    try:
        req = urllib.request.Request(target_url, data=payload_bytes, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=5) as response:
            response_status = response.status
            response_body = response.read().decode("utf-8", errors="replace")[:2000]
            success = 200 <= response_status < 300
    except urllib.error.HTTPError as e:
        response_status = e.code
        response_body = e.read().decode("utf-8", errors="replace")[:2000]
        error_message = f"HTTP Error {e.code}: {e.reason}"
    except Exception as e:
        error_message = str(e)

    # Record log
    try:
        log = frappe.new_doc("HD Webhook Log")
        log.webhook = webhook["name"]
        log.ticket = ticket_name
        log.event = event
        log.target_url = target_url
        log.payload = payload_str
        log.response_status = response_status or 0
        log.response_body = response_body
        log.error_message = error_message
        log.success = 1 if success else 0
        log.insert(ignore_permissions=True)
    except Exception as log_err:
        frappe.log_error(f"Failed to write HD Webhook Log: {str(log_err)}", "Webhook Log Error")

    return success


def verify_webhook_signature(payload_bytes, secret_key, signature_header):
    """Verify an incoming or test webhook payload against expected HMAC signature."""
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    received_sig = signature_header.split("sha256=")[1]
    expected_sig = hmac.new(secret_key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(received_sig, expected_sig)
