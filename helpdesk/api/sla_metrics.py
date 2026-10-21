# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _


def format_duration_human(seconds: int) -> str:
    """Format duration in seconds into human-readable shorthand (e.g. 2h 15m, 45m, 1d 4h)."""
    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    if days > 0:
        rem_hours = hours % 24
        return f"{days}d {rem_hours}h" if rem_hours else f"{days}d"
    if hours > 0:
        rem_mins = minutes % 60
        return f"{hours}h {rem_mins}m" if rem_mins else f"{hours}h"
    return f"{minutes}m"


@frappe.whitelist()
def get_ticket_sla_metrics(ticket_id: str) -> dict:
    """Compute real-time countdown badges and SLA breach status for a ticket."""
    if not ticket_id or not frappe.db.exists("HD Ticket", ticket_id):
        frappe.throw(_("Ticket not found"), frappe.DoesNotExistError)

    doc = frappe.get_doc("HD Ticket", ticket_id)
    now = frappe.utils.now_datetime()

    metrics = {
        "ticket": doc.name,
        "sla": doc.sla,
        "agreement_status": doc.agreement_status,
        "response": {"status": "none", "badge": "none", "human": "No SLA", "seconds": None},
        "resolution": {"status": "none", "badge": "none", "human": "No SLA", "seconds": None},
    }

    if not doc.sla:
        return metrics

    # 1. Response SLA Metrics
    if doc.first_responded_on:
        metrics["response"] = {
            "status": "fulfilled",
            "badge": "fulfilled",
            "human": "Responded",
            "seconds": 0,
        }
    elif doc.response_by:
        due = frappe.utils.get_datetime(doc.response_by)
        diff_sec = int((due - now).total_seconds())
        metrics["response"]["seconds"] = diff_sec
        if diff_sec < 0:
            metrics["response"]["status"] = "breached"
            metrics["response"]["badge"] = "breached"
            metrics["response"]["human"] = f"Breached by {format_duration_human(abs(diff_sec))}"
        elif diff_sec < 1800:
            metrics["response"]["status"] = "approaching"
            metrics["response"]["badge"] = "urgent"
            metrics["response"]["human"] = f"{format_duration_human(diff_sec)} left"
        else:
            metrics["response"]["status"] = "healthy"
            metrics["response"]["badge"] = "healthy"
            metrics["response"]["human"] = f"{format_duration_human(diff_sec)} left"

    # 2. Resolution SLA Metrics
    is_resolved = doc.status in ("Resolved", "Closed") or doc.status_category == "Resolved"
    if is_resolved:
        metrics["resolution"] = {
            "status": "fulfilled",
            "badge": "fulfilled",
            "human": "Resolved",
            "seconds": 0,
        }
    elif doc.resolution_by:
        due = frappe.utils.get_datetime(doc.resolution_by)
        diff_sec = int((due - now).total_seconds())
        metrics["resolution"]["seconds"] = diff_sec
        if diff_sec < 0:
            metrics["resolution"]["status"] = "breached"
            metrics["resolution"]["badge"] = "breached"
            metrics["resolution"]["human"] = f"Breached by {format_duration_human(abs(diff_sec))}"
        elif diff_sec < 1800:
            metrics["resolution"]["status"] = "approaching"
            metrics["resolution"]["badge"] = "urgent"
            metrics["resolution"]["human"] = f"{format_duration_human(diff_sec)} left"
        else:
            metrics["resolution"]["status"] = "healthy"
            metrics["resolution"]["badge"] = "healthy"
            metrics["resolution"]["human"] = f"{format_duration_human(diff_sec)} left"

    return metrics
