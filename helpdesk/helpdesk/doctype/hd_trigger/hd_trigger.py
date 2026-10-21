# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.model.document import Document


class HDTrigger(Document):
    def validate(self):
        self.validate_conditions_json()
        self.validate_actions_json()

    def validate_conditions_json(self):
        if not self.conditions_json:
            return
        try:
            parsed = json.loads(self.conditions_json)
            if not isinstance(parsed, list):
                frappe.throw(_("Conditions JSON must be a list of condition objects."))
        except json.JSONDecodeError as e:
            frappe.throw(_("Invalid Conditions JSON: {0}").format(str(e)))

    def validate_actions_json(self):
        if not self.actions_json:
            return
        try:
            parsed = json.loads(self.actions_json)
            if not isinstance(parsed, list):
                frappe.throw(_("Actions JSON must be a list of action objects."))
        except json.JSONDecodeError as e:
            frappe.throw(_("Invalid Actions JSON: {0}").format(str(e)))

    def evaluate(self, ticket, previous_ticket=None) -> bool:
        """Evaluate if the ticket matches all conditions in this trigger."""
        if not self.is_enabled:
            return False

        if not self.conditions_json:
            return True

        conditions = json.loads(self.conditions_json)
        for cond in conditions:
            if not self.check_condition(cond, ticket, previous_ticket):
                return False
        return True

    def check_condition(self, cond: dict, ticket, previous_ticket=None) -> bool:
        field = cond.get("field")
        operator = cond.get("operator", "==")
        expected = cond.get("value")

        actual = ticket.get(field)

        if operator in ("==", "equals"):
            return str(actual or "").strip().lower() == str(expected or "").strip().lower()
        elif operator in ("!=", "not_equals"):
            return str(actual or "").strip().lower() != str(expected or "").strip().lower()
        elif operator == "contains":
            if field == "tags":
                tags = ticket.get_tags() if hasattr(ticket, "get_tags") else []
                return str(expected or "").lower() in [t.lower() for t in tags]
            return str(expected or "").lower() in str(actual or "").lower()
        elif operator == "not_contains":
            if field == "tags":
                tags = ticket.get_tags() if hasattr(ticket, "get_tags") else []
                return str(expected or "").lower() not in [t.lower() for t in tags]
            return str(expected or "").lower() not in str(actual or "").lower()
        elif operator == "in":
            expected_list = expected if isinstance(expected, list) else [x.strip() for x in str(expected).split(",")]
            return str(actual or "").strip() in expected_list
        elif operator == "is_set":
            return bool(actual)
        elif operator == "is_not_set":
            return not bool(actual)
        elif operator == "changed_to":
            if not previous_ticket:
                return False
            prev_val = previous_ticket.get(field)
            return prev_val != actual and str(actual or "").strip().lower() == str(expected or "").strip().lower()

        return False

    def apply_actions(self, ticket, in_lifecycle: bool = True):
        """Execute all configured actions on the ticket."""
        if not self.actions_json:
            return

        actions = json.loads(self.actions_json)
        needs_save = False

        for action in actions:
            action_type = action.get("action_type")
            value = action.get("value")

            if action_type == "Set Status" and value:
                ticket.status = value
                needs_save = True
            elif action_type == "Set Priority" and value:
                ticket.priority = value
                needs_save = True
            elif action_type == "Set Team" and value:
                ticket.agent_group = value
                needs_save = True
            elif action_type == "Set Ticket Type" and value:
                ticket.ticket_type = value
                needs_save = True
            elif action_type == "Add Tag" and value:
                tag_str = str(value).strip()
                if not ticket.name:
                    if not hasattr(ticket.flags, "pending_trigger_tags") or ticket.flags.pending_trigger_tags is None:
                        ticket.flags.pending_trigger_tags = []
                    ticket.flags.pending_trigger_tags.append(tag_str)
                else:
                    ticket.add_tag(tag_str)
            elif action_type == "Remove Tag" and value:
                tag_str = str(value).strip()
                if ticket.name:
                    ticket.remove_tag(tag_str)

        if needs_save and not in_lifecycle:
            ticket.flags.ignore_status_guards = True
            ticket.save(ignore_permissions=True)
