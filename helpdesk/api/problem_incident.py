# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from helpdesk.utils import agent_only


@frappe.whitelist()
@agent_only
def get_linked_incidents(problem_ticket: str) -> list[dict]:
    """Retrieve all incident tickets linked to a master problem ticket."""
    if not problem_ticket or not frappe.db.exists("HD Ticket", problem_ticket):
        frappe.throw(_("Problem ticket not found"), frappe.DoesNotExistError)

    return frappe.get_list(
        "HD Ticket",
        filters={"problem_ticket": problem_ticket},
        fields=["name", "subject", "status", "priority", "customer", "raised_by", "creation", "modified"],
        order_by="creation desc",
    )


@frappe.whitelist()
@agent_only
def link_incident_to_problem(incident_ticket: str, problem_ticket: str) -> dict:
    """Link a child incident ticket to a master problem ticket."""
    if not incident_ticket or not frappe.db.exists("HD Ticket", incident_ticket):
        frappe.throw(_("Incident ticket not found"), frappe.DoesNotExistError)

    if not problem_ticket or not frappe.db.exists("HD Ticket", problem_ticket):
        frappe.throw(_("Problem ticket not found"), frappe.DoesNotExistError)

    if incident_ticket == problem_ticket:
        frappe.throw(_("A ticket cannot be linked to itself as a problem ticket."))

    prob_doc = frappe.get_doc("HD Ticket", problem_ticket)
    if prob_doc.ticket_type != "Problem":
        frappe.throw(_("Target ticket #{0} is not classified as a Problem ticket.").format(problem_ticket))

    inc_doc = frappe.get_doc("HD Ticket", incident_ticket)
    inc_doc.problem_ticket = problem_ticket
    inc_doc.ticket_type = "Incident"
    inc_doc.flags.ignore_permissions = True
    inc_doc.save(ignore_permissions=True)

    inc_doc.add_comment("Info", f"Linked as child incident to Problem Ticket #{problem_ticket}.")

    return {"incident": incident_ticket, "problem": problem_ticket, "status": "Linked"}


@frappe.whitelist()
@agent_only
def unlink_incident_from_problem(incident_ticket: str) -> dict:
    """Unlink an incident ticket from its master problem ticket."""
    if not incident_ticket or not frappe.db.exists("HD Ticket", incident_ticket):
        frappe.throw(_("Incident ticket not found"), frappe.DoesNotExistError)

    inc_doc = frappe.get_doc("HD Ticket", incident_ticket)
    old_problem = inc_doc.problem_ticket
    inc_doc.problem_ticket = None
    inc_doc.flags.ignore_permissions = True
    inc_doc.save(ignore_permissions=True)

    if old_problem:
        inc_doc.add_comment("Info", f"Unlinked from Problem Ticket #{old_problem}.")

    return {"incident": incident_ticket, "unlinked": True}


@frappe.whitelist()
@agent_only
def propagate_problem_resolution(problem_ticket: str, resolution_details: str = None) -> dict:
    """Manually trigger resolution propagation from a problem ticket to all linked incidents."""
    if not problem_ticket or not frappe.db.exists("HD Ticket", problem_ticket):
        frappe.throw(_("Problem ticket not found"), frappe.DoesNotExistError)

    prob_doc = frappe.get_doc("HD Ticket", problem_ticket)
    if resolution_details:
        prob_doc.resolution_details = resolution_details

    prob_doc.propagate_resolution_to_incidents()
    return {
        "problem_ticket": problem_ticket,
        "propagated": True,
        "incident_count": prob_doc.incident_count or 0,
    }
