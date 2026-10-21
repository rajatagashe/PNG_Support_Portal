# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from helpdesk.utils import agent_only, is_agent


@frappe.whitelist()
@agent_only
def create_side_conversation(ticket: str, subject: str, recipients: str, message: str) -> dict:
    """Create a new side conversation and its initial message, hidden from the customer portal."""
    if not ticket or not frappe.db.exists("HD Ticket", ticket):
        frappe.throw(_("Valid ticket is required"), frappe.DoesNotExistError)

    if not subject or not subject.strip():
        frappe.throw(_("Subject is required"))

    if not recipients or not recipients.strip():
        frappe.throw(_("Recipients are required"))

    if not message or not message.strip():
        frappe.throw(_("Message content is required"))

    conversation = frappe.get_doc(
        {
            "doctype": "HD Side Conversation",
            "ticket": ticket,
            "subject": subject.strip(),
            "recipients": recipients.strip(),
            "status": "Open",
            "created_by": frappe.session.user,
        }
    ).insert(ignore_permissions=True)

    user_fullname = frappe.utils.get_fullname(frappe.session.user) or frappe.session.user
    msg_doc = frappe.get_doc(
        {
            "doctype": "HD Side Conversation Message",
            "side_conversation": conversation.name,
            "sender": user_fullname,
            "sender_email": frappe.session.user,
            "sender_type": "Agent",
            "message": message,
        }
    ).insert(ignore_permissions=True)

    return {
        "conversation": conversation.as_dict(),
        "initial_message": msg_doc.as_dict(),
    }


@frappe.whitelist()
@agent_only
def get_side_conversations(ticket: str) -> list[dict]:
    """Retrieve all side conversations for a ticket along with their message threads."""
    if not ticket:
        return []

    conversations = frappe.get_list(
        "HD Side Conversation",
        filters={"ticket": ticket},
        fields=["name", "ticket", "subject", "recipients", "status", "created_by", "creation", "modified"],
        order_by="creation desc",
    )

    for conv in conversations:
        messages = frappe.get_list(
            "HD Side Conversation Message",
            filters={"side_conversation": conv["name"]},
            fields=["name", "sender", "sender_email", "sender_type", "message", "creation"],
            order_by="creation asc",
        )
        conv["messages"] = messages

    return conversations


@frappe.whitelist()
@agent_only
def reply_to_side_conversation(conversation_id: str, message: str) -> dict:
    """Post an agent reply to an existing side conversation."""
    if not conversation_id or not frappe.db.exists("HD Side Conversation", conversation_id):
        frappe.throw(_("Side conversation not found"), frappe.DoesNotExistError)

    if not message or not message.strip():
        frappe.throw(_("Message is required"))

    user_fullname = frappe.utils.get_fullname(frappe.session.user) or frappe.session.user
    msg_doc = frappe.get_doc(
        {
            "doctype": "HD Side Conversation Message",
            "side_conversation": conversation_id,
            "sender": user_fullname,
            "sender_email": frappe.session.user,
            "sender_type": "Agent",
            "message": message,
        }
    ).insert(ignore_permissions=True)

    # Touch parent modified timestamp
    frappe.db.set_value("HD Side Conversation", conversation_id, "modified", frappe.utils.now())

    return msg_doc.as_dict()


@frappe.whitelist()
@agent_only
def close_side_conversation(conversation_id: str) -> dict:
    """Close a side conversation."""
    if not conversation_id or not frappe.db.exists("HD Side Conversation", conversation_id):
        frappe.throw(_("Side conversation not found"), frappe.DoesNotExistError)

    frappe.db.set_value("HD Side Conversation", conversation_id, "status", "Closed")
    return {"status": "Closed"}


@frappe.whitelist()
@agent_only
def reopen_side_conversation(conversation_id: str) -> dict:
    """Reopen a closed side conversation."""
    if not conversation_id or not frappe.db.exists("HD Side Conversation", conversation_id):
        frappe.throw(_("Side conversation not found"), frappe.DoesNotExistError)

    frappe.db.set_value("HD Side Conversation", conversation_id, "status", "Open")
    return {"status": "Open"}
