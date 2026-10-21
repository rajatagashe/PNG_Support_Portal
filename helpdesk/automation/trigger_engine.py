# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe


def run_triggers(ticket, event_type: str, previous_ticket=None, in_lifecycle: bool = True):
    """Fetch active triggers for event_type and execute matching ones in order."""
    if getattr(frappe.flags, "in_trigger_execution", False):
        # Prevent recursive trigger loops
        return

    triggers = frappe.get_all(
        "HD Trigger",
        filters={"is_enabled": 1, "event_type": event_type},
        fields=["name"],
        order_by="execution_order asc, creation asc",
    )

    if not triggers:
        return

    frappe.flags.in_trigger_execution = True
    try:
        for t_row in triggers:
            trigger_doc = frappe.get_doc("HD Trigger", t_row.name)
            if trigger_doc.evaluate(ticket, previous_ticket):
                trigger_doc.apply_actions(ticket, in_lifecycle=in_lifecycle)
    finally:
        frappe.flags.in_trigger_execution = False
