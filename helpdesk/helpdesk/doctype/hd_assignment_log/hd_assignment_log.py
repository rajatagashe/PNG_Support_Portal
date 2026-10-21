import frappe
from frappe.model.document import Document


class HDAssignmentLog(Document):
    pass


def has_permission(doc, ptype="read", user=None):
    if not user:
        user = frappe.session.user
    if user == "Administrator":
        return True
    roles = frappe.get_roles(user)
    if "System Manager" in roles or "Agent" in roles or "Agent Manager" in roles or "HD Team Lead" in roles:
        return True

    # Customer users can read assignment logs only for tickets of their CGD entity
    if doc and doc.ticket:
        return frappe.has_permission("HD Ticket", ptype, doc.ticket, user=user)
    return False


def permission_query(user=None):
    if not user:
        user = frappe.session.user
    if user == "Administrator":
        return ""
    roles = frappe.get_roles(user)
    if "System Manager" in roles or "Agent" in roles or "Agent Manager" in roles or "HD Team Lead" in roles:
        return ""

    # Customer users: restrict to accessible tickets
    from helpdesk.helpdesk.doctype.hd_ticket.hd_ticket import permission_query as ticket_pq

    ticket_conditions = ticket_pq(user)
    if ticket_conditions:
        return f"`tabHD Assignment Log`.ticket IN (SELECT name FROM `tabHD Ticket` WHERE {ticket_conditions})"
    return "1=0"
