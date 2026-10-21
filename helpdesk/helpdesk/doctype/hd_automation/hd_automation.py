# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import json
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime, time_diff_in_hours


class HDAutomation(Document):
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

    def evaluate(self, ticket) -> bool:
        """Evaluate whether a ticket satisfies time-based and field conditions."""
        if not self.is_enabled:
            return False

        if not self.conditions_json:
            return True

        conditions = json.loads(self.conditions_json)
        now = now_datetime()

        for cond in conditions:
            field = cond.get("field")
            operator = cond.get("operator", "==")
            expected = cond.get("value")

            # Handle computed time elapsed fields
            if field == "hours_since_last_customer_response":
                val = ticket.get("last_customer_response")
                actual = time_diff_in_hours(now, val) if val else 999999
            elif field == "hours_since_last_agent_response":
                val = ticket.get("last_agent_response")
                actual = time_diff_in_hours(now, val) if val else 999999
            elif field == "hours_since_created":
                val = ticket.get("creation")
                actual = time_diff_in_hours(now, val) if val else 999999
            else:
                actual = ticket.get(field)

            if not self.compare_values(actual, operator, expected):
                return False

        return True

    def compare_values(self, actual, operator: str, expected) -> bool:
        try:
            if operator in (">=", ">", "<=", "<"):
                actual_num = float(actual if actual is not None else 0)
                expected_num = float(expected)
                if operator == ">=":
                    return actual_num >= expected_num
                elif operator == ">":
                    return actual_num > expected_num
                elif operator == "<=":
                    return actual_num <= expected_num
                elif operator == "<":
                    return actual_num < expected_num

            if operator in ("==", "equals"):
                return str(actual or "").strip().lower() == str(expected or "").strip().lower()
            elif operator in ("!=", "not_equals"):
                return str(actual or "").strip().lower() != str(expected or "").strip().lower()
            elif operator == "contains":
                return str(expected or "").lower() in str(actual or "").lower()
            elif operator == "not_contains":
                return str(expected or "").lower() not in str(actual or "").lower()
            elif operator == "is_set":
                return bool(actual)
            elif operator == "is_not_set":
                return not bool(actual)
        except Exception:
            return False

        return False

    def apply_actions(self, ticket):
        """Execute automation actions on the ticket."""
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
            elif action_type == "Add Tag" and value:
                ticket.add_tag(str(value).strip())
            elif action_type == "Remove Tag" and value:
                ticket.remove_tag(str(value).strip())

        if needs_save:
            ticket.flags.ignore_status_guards = True
            ticket.save(ignore_permissions=True)
