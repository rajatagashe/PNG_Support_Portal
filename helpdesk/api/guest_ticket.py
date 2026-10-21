from contextlib import contextmanager
import secrets
import frappe
from frappe import _


@contextmanager
def as_admin_if_guest():
    current_user = frappe.session.user
    if current_user == "Guest":
        frappe.set_user("Administrator")
        try:
            yield
        finally:
            frappe.set_user(current_user)
    else:
        yield


@frappe.whitelist(allow_guest=True)
def submit_guest_ticket(
    subject: str,
    email: str,
    description: str,
    full_name: str | None = None,
) -> dict:
    """Submit a ticket without mandatory user account creation and generate magic-link tracking."""
    if not email or "@" not in email:
        frappe.throw(_("A valid email address is required."))
    if not subject or not subject.strip():
        frappe.throw(_("Subject is required."))
    if not description or not description.strip():
        frappe.throw(_("Description is required."))

    clean_email = email.strip().lower()
    clean_name = (full_name or clean_email.split("@")[0]).strip()

    with as_admin_if_guest():
        # Get or create Contact
        contact_name = frappe.db.get_value("Contact", {"email_id": clean_email}, "name")
        if not contact_name:
            contact_doc = frappe.get_doc(
                {
                    "doctype": "Contact",
                    "first_name": clean_name,
                    "email_id": clean_email,
                }
            )
            contact_doc.append("email_ids", {"email_id": clean_email, "is_primary": 1})
            contact_doc.insert(ignore_permissions=True)
            contact_name = contact_doc.name

        guest_token = secrets.token_urlsafe(32)

        ticket = frappe.get_doc(
            {
                "doctype": "HD Ticket",
                "subject": subject.strip(),
                "description": description.strip(),
                "raised_by": clean_email,
                "contact": contact_name,
                "guest_token": guest_token,
                "is_guest_ticket": 1,
                "via_customer_portal": 0,
            }
        )
        ticket.flags.ignore_permissions = True
        ticket.insert(ignore_permissions=True)

    return {
        "ticket": ticket.name,
        "guest_token": guest_token,

        "tracking_url": f"/helpdesk/guest-tickets/{ticket.name}?token={guest_token}",
        "message": _("Ticket #{0} submitted successfully.").format(ticket.name),
    }


@frappe.whitelist(allow_guest=True)
def get_guest_ticket_details(ticket_id: str, guest_token: str) -> dict:
    """Retrieve ticket details and public timeline using cryptographic magic-link token."""
    if not ticket_id or not guest_token:
        frappe.throw(_("Ticket ID and guest token are required."), frappe.ValidationError)

    ticket_row = frappe.db.get_value(
        "HD Ticket",
        {"name": ticket_id, "guest_token": guest_token},
        ["name", "subject", "status", "priority", "raised_by", "creation", "modified", "guest_token"],
        as_dict=True,
    )
    if not ticket_row:
        frappe.throw(_("Invalid ticket or guest access token."), frappe.PermissionError)

    # Fetch public communications only (never internal notes or side conversations)
    comms = frappe.get_all(
        "Communication",
        filters={
            "reference_doctype": "HD Ticket",
            "reference_name": ticket_id,
            "communication_type": "Communication",
        },
        fields=["name", "sender", "sender_full_name", "content", "creation", "sent_or_received"],
        order_by="creation asc",
    )

    return {
        "ticket": ticket_row,
        "communications": comms,
    }


@frappe.whitelist(allow_guest=True)
def guest_reply_to_ticket(ticket_id: str, guest_token: str, message: str) -> dict:
    """Allow guest requester to reply to their ticket thread via validated token."""
    if not ticket_id or not guest_token or not message or not message.strip():
        frappe.throw(_("Ticket ID, token, and message are required."))

    with as_admin_if_guest():
        ticket_doc = frappe.get_doc("HD Ticket", ticket_id)
        if not ticket_doc.guest_token or ticket_doc.guest_token != guest_token:
            frappe.throw(_("Invalid or expired guest token."), frappe.PermissionError)

        # Create Communication
        comm = frappe.get_doc(
            {
                "doctype": "Communication",
                "communication_type": "Communication",
                "communication_medium": "Email",
                "reference_doctype": "HD Ticket",
                "reference_name": ticket_id,
                "sender": ticket_doc.raised_by,
                "sender_full_name": ticket_doc.raised_by.split("@")[0],
                "sent_or_received": "Received",
                "content": message.strip(),
                "subject": f"Re: {ticket_doc.subject}",
            }
        ).insert(ignore_permissions=True)

        # Touch ticket and update response timestamp
        ticket_doc.reload()
        ticket_doc.last_customer_response = frappe.utils.now()
        if ticket_doc.status in ("Resolved", "Closed"):
            ticket_doc.status = "Open"
        ticket_doc.flags.ignore_permissions = True
        ticket_doc.flags.ignore_status_guards = True
        ticket_doc.save(ignore_permissions=True)



    return {
        "ticket": ticket_id,
        "status": ticket_doc.status,
        "communication": comm.name,
        "success": True,
    }
