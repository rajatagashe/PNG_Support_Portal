"""Support Email Management: mailbox health, email detail, read state, replies and attachments."""

import html
from urllib.parse import quote, urlencode

import frappe
from frappe import _
from frappe.utils import cint, validate_email_address
from frappe.utils.html_utils import sanitize_html

from helpdesk.api.email_management import (
    get_support_email_accounts,
    get_sync_error_message,
    pull_support_mailbox,
)
from helpdesk.utils import admin_only, agent_or_email_user_only, is_admin, is_support_email_only

MESSAGE_FIELDS = [
    "name",
    "subject",
    "sender",
    "sender_full_name",
    "recipients",
    "cc",
    "content",
    "communication_date",
    "sent_or_received",
    "seen",
    "message_id",
]
ATTACHMENT_FIELDS = ["name", "file_name", "file_size", "file_url", "attached_to_doctype", "attached_to_name"]
ATTACHMENT_URL = "/api/method/helpdesk.api.support_mailbox.download_support_email_attachment?file="


@frappe.whitelist()
@agent_or_email_user_only
def get_mailbox_status() -> dict:
    """Connection health of each support mailbox; errors are described, never shown raw."""
    accounts = []
    for acc in get_support_email_accounts(include_disabled=True):
        email_account = frappe.get_doc("Email Account", acc.name)
        status = email_account.get_sync_status()
        state = status.get("state") or "not_synced"
        error_type = status.get("error_type")
        if email_account.auth_method == "OAuth" and not email_account.has_oauth_token():
            state, error_type = "error", "authorization_required"
        elif not acc.enable_incoming:
            state, error_type = "disabled", None

        accounts.append(
            {
                "account": acc.name,
                "email_id": acc.email_id,
                "auth_method": acc.auth_method,
                # app-only OAuth connects without a sign-in, so the page offers Activate
                "uses_app_access": bool(acc.backend_app_flow),
                "state": state,
                "error_type": error_type if state == "error" else None,
                "message": get_sync_error_message(error_type) if state == "error" else None,
                "last_success_at": status.get("last_success_at"),
                "last_failure_at": status.get("last_failure_at"),
                "last_email_at": get_last_email_at(acc.name),
            }
        )
    return {"accounts": accounts, "can_reconnect": is_admin()}


def get_last_email_at(email_account: str):
    return frappe.db.get_value(
        "Communication",
        {"email_account": email_account, "sent_or_received": "Received"},
        "max(communication_date)",
    )


@frappe.whitelist(methods=["POST"])
@admin_only
def get_mailbox_authorization_url(account: str) -> str:
    """Start the one-time Microsoft sign-in; the token is then kept and refreshed by Frappe."""
    email_account = frappe.get_doc("Email Account", account)
    if email_account.auth_method != "OAuth" or not email_account.connected_app:
        frappe.throw(_("Mailbox {0} is not set up for OAuth.").format(account))
    if email_account.backend_app_flow:
        frappe.throw(_("Mailbox {0} uses app-only access and needs no sign-in.").format(account))

    # the token is stored for whoever signs in, so the mailbox must read it from them
    if email_account.connected_user != frappe.session.user:
        frappe.db.set_value("Email Account", account, "connected_user", frappe.session.user)

    connected_app = frappe.get_doc("Connected App", email_account.connected_app)
    success_uri = "/helpdesk/support-emails?" + urlencode({"mailbox_authorized": account})
    return connected_app.initiate_web_application_flow(success_uri=success_uri)


@frappe.whitelist(methods=["POST"])
@admin_only
def activate_support_mailbox(account: str) -> dict:
    """Switch the mailbox on once it can log in; the save logs in once to prove it works.

    Delegated mailboxes come here after the sign-in, app-only ones once Exchange grants access.
    """
    email_account = frappe.get_doc("Email Account", account)
    if email_account.auth_method == "OAuth" and not email_account.has_oauth_token():
        frappe.throw(get_sync_error_message("authorization_required"))

    email_account.update(
        {"enable_incoming": 1, "enable_outgoing": 1, "default_incoming": 1, "default_outgoing": 1}
    )
    try:
        email_account.save()
    except Exception as e:
        frappe.log_error(title=f"Support mailbox activation failed: {account}")
        # the failed login already queued the server's own text; show only ours
        frappe.clear_messages()
        frappe.throw(get_sync_error_message(email_account.classify_sync_error(e)))
    return pull_support_mailbox(email_account)


@frappe.whitelist()
@agent_or_email_user_only
def get_support_email(ticket_id: str) -> dict:
    """The full email thread of a support ticket, with sanitized bodies and attachments."""
    check_support_email_access(ticket_id)
    ticket = frappe.db.get_value(
        "HD Ticket",
        ticket_id,
        ["name", "subject", "raised_by", "status", "priority", "customer", "agent_group", "creation"],
        as_dict=True,
    )
    messages = frappe.get_all(
        "Communication",
        filters={
            "reference_doctype": "HD Ticket",
            "reference_name": ticket_id,
            "communication_type": "Communication",
            "communication_medium": "Email",
        },
        fields=MESSAGE_FIELDS,
        order_by="communication_date asc, creation asc",
    )

    attachments = get_email_attachments(ticket_id, [m.name for m in messages])
    message_file_urls = set()
    for message in messages:
        message.content = sanitize_html(message.content or "")
        message.attachments = [a for a in attachments if a.communication == message.name]
        message_file_urls.update(a.file_url for a in message.attachments)

    return {
        "ticket": ticket,
        "messages": messages,
        # a reply's files are attached to the ticket too, so list only the ones not shown above
        "attachments": [
            a for a in attachments if not a.communication and a.file_url not in message_file_urls
        ],
        "can_open_ticket": not is_support_email_only(),
    }


def get_email_attachments(ticket_id: str, communication_names: list[str]) -> list[frappe._dict]:
    """Files on the ticket and on its emails, each with a scoped download URL."""
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": "HD Ticket", "attached_to_name": ticket_id},
        fields=ATTACHMENT_FIELDS,
    )
    if communication_names:
        files += frappe.get_all(
            "File",
            filters={"attached_to_doctype": "Communication", "attached_to_name": ["in", communication_names]},
            fields=ATTACHMENT_FIELDS,
        )

    attachments = []
    for f in files:
        attachments.append(
            frappe._dict(
                name=f.name,
                file_name=f.file_name,
                file_size=f.file_size,
                file_url=f.file_url,
                communication=f.attached_to_name if f.attached_to_doctype == "Communication" else None,
                download_url=ATTACHMENT_URL + quote(f.name),
            )
        )
    return attachments


@frappe.whitelist(methods=["POST"])
@agent_or_email_user_only
def set_support_email_seen(ticket_id: str, seen: int = 1):
    """Mark every received email of a ticket read (seen=1) or unread (seen=0)."""
    check_support_email_access(ticket_id)
    frappe.db.set_value(
        "Communication",
        {"reference_doctype": "HD Ticket", "reference_name": ticket_id, "sent_or_received": "Received"},
        "seen",
        1 if cint(seen) else 0,
        update_modified=False,
    )


@frappe.whitelist(methods=["POST"])
@agent_or_email_user_only
def reply_to_support_email(ticket_id: str, message: str, cc: str | None = None):
    """Reply to the sender from the support mailbox; the reply is logged on the ticket."""
    check_support_email_access(ticket_id, "write")
    if not (message or "").strip():
        frappe.throw(_("Reply message cannot be empty."))
    if cc:
        validate_email_address(cc, throw=True)

    ticket = frappe.get_doc("HD Ticket", ticket_id)
    ticket.reply_via_agent(plain_text_to_html(message), to=ticket.raised_by, cc=cc or None)
    set_support_email_seen(ticket_id, 1)


def plain_text_to_html(text: str) -> str:
    """The reply box is plain text, so escape it before it goes into an HTML email."""
    return "<p>" + html.escape(text.strip()).replace("\n", "<br>") + "</p>"


@frappe.whitelist(methods=["GET"])
@agent_or_email_user_only
def download_support_email_attachment(file: str):
    """Serve a file only when it belongs to a support email or its ticket."""
    doc = frappe.get_doc("File", file)
    ticket_id = get_attachment_ticket(doc)
    if not ticket_id or doc.file_url.startswith(("http://", "https://")):
        frappe.throw(_("This file is not a support email attachment."), frappe.PermissionError)
    check_support_email_access(ticket_id)

    frappe.local.response.filename = doc.file_name
    frappe.local.response.filecontent = doc.get_content()
    frappe.local.response.type = "download"


def get_attachment_ticket(file_doc) -> str | None:
    if file_doc.attached_to_doctype == "HD Ticket":
        return file_doc.attached_to_name
    if file_doc.attached_to_doctype != "Communication":
        return None
    reference = frappe.db.get_value(
        "Communication", file_doc.attached_to_name, ["reference_doctype", "reference_name"], as_dict=True
    )
    if reference and reference.reference_doctype == "HD Ticket":
        return reference.reference_name
    return None


def check_support_email_access(ticket_id: str, ptype: str = "read"):
    """Support email users may handle every support email; agents keep their ticket permissions."""
    if not frappe.db.exists("HD Ticket", ticket_id):
        frappe.throw(_("Support email {0} not found.").format(ticket_id), frappe.DoesNotExistError)
    if is_support_email_only():
        return
    frappe.has_permission("HD Ticket", ptype, doc=ticket_id, throw=True)
