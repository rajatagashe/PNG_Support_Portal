"""Communication lifecycle hooks for the Support Email Management page."""

from helpdesk.utils import publish_event

SUPPORT_EMAIL_RECEIVED_EVENT = "helpdesk:support-email-received"


def after_insert(doc, method: str | None = None):
    """Tell open support email pages to refresh; the event carries no email data."""
    if doc.reference_doctype != "HD Ticket" or doc.communication_medium != "Email":
        return
    if doc.sent_or_received != "Received":
        return
    publish_event(SUPPORT_EMAIL_RECEIVED_EVENT)
