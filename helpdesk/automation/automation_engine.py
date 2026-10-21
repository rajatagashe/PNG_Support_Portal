# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe


def execute_automations():
    """Evaluate and run all active time-based automations on non-closed tickets."""
    automations = frappe.get_all(
        "HD Automation",
        filters={"is_enabled": 1},
        fields=["name"],
    )

    if not automations:
        return

    # Process all tickets that are not closed
    closed_statuses = frappe.get_all(
        "HD Ticket Status",
        filters={"category": "Closed"},
        pluck="name",
    ) or ["Closed", "Resolved"]

    tickets = frappe.get_all(
        "HD Ticket",
        filters={"status": ["not in", closed_statuses]},
        fields=["name"],
        limit=500,
    )

    for t_row in tickets:
        ticket = frappe.get_doc("HD Ticket", t_row.name)
        for auto_row in automations:
            auto_doc = frappe.get_doc("HD Automation", auto_row.name)
            if auto_doc.evaluate(ticket):
                auto_doc.apply_actions(ticket)
