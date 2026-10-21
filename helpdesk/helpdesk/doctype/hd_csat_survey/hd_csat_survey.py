import secrets
import frappe
from frappe.model.document import Document


class HDCSATSurvey(Document):
    def before_insert(self):
        self.generate_token_if_missing()

    def generate_token_if_missing(self):
        if not self.survey_token:
            self.survey_token = secrets.token_urlsafe(32)
