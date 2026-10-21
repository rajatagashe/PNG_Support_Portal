import json
import frappe
from frappe.model.document import Document
from frappe import _


class HDWebhook(Document):
    def validate(self):
        self.validate_custom_headers()

    def validate_custom_headers(self):
        if self.custom_headers and self.custom_headers.strip():
            try:
                parsed = json.loads(self.custom_headers)
                if not isinstance(parsed, dict):
                    frappe.throw(_("Custom Headers must be a valid JSON object/dictionary."))
            except Exception as e:
                frappe.throw(_("Invalid JSON in Custom Headers: {0}").format(str(e)))
