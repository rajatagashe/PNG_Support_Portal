import frappe

from helpdesk.setup.install import setup_support_email_role
from helpdesk.utils import SUPPORT_EMAIL_ROLE

# The old provisioning script inserted these rows directly, which made Frappe drop
# the doctype's standard perms wherever they were its only Custom DocPerm rows
OLD_PERM_DOCTYPES = (
    "HD Ticket",
    "Communication",
    "HD Assignment Log",
    "Email Account",
    "HD Customer",
    "HD Team",
)


def execute():
    """Drop the role's directly inserted perms, then grant them again the safe way."""
    for dt in OLD_PERM_DOCTYPES:
        frappe.db.delete("Custom DocPerm", {"parent": dt, "role": SUPPORT_EMAIL_ROLE})
        frappe.clear_cache(doctype=dt)
    setup_support_email_role()
