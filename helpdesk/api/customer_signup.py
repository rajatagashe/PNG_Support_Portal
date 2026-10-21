import frappe
from frappe import _

from helpdesk.utils import agent_manager_only


@frappe.whitelist(allow_guest=True)
def submit_signup_request(
    full_name: str,
    email: str,
    requested_cgd: str,
    designation: str | None = None,
    phone: str | None = None,
) -> dict:
    """Public endpoint for CGD customers to request portal access."""
    if not email or not full_name or not requested_cgd:
        frappe.throw(
            _("Full Name, Email Address, and Requested CGD are required."),
            frappe.MandatoryError,
        )

    # Check if a pending or approved request already exists for this email
    existing = frappe.db.get_value(
        "HD Customer Signup Request",
        {"email": email.strip().lower()},
        ["name", "status"],
        as_dict=True,
    )
    if existing:
        if existing.status == "Pending":
            frappe.throw(
                _("A signup request for '{0}' is already pending review.").format(email),
                frappe.DuplicateEntryError,
            )
        elif existing.status == "Approved":
            frappe.throw(
                _("An account for '{0}' has already been approved. Please log in or reset your password.").format(email),
                frappe.DuplicateEntryError,
            )

    doc = frappe.get_doc(
        {
            "doctype": "HD Customer Signup Request",
            "full_name": full_name.strip(),
            "email": email.strip().lower(),
            "requested_cgd": requested_cgd,
            "designation": designation,
            "phone": phone,
            "status": "Pending",
        }
    )
    doc.insert(ignore_permissions=True)

    return {
        "success": True,
        "message": _("Your signup request has been submitted and is pending administrator approval."),
        "request_id": doc.name,
    }


@frappe.whitelist()
@agent_manager_only
def get_pending_signup_requests() -> list[dict]:
    """Retrieve all pending customer registration requests for manager review."""
    return frappe.get_list(
        "HD Customer Signup Request",
        filters={"status": "Pending"},
        fields=[
            "name",
            "full_name",
            "email",
            "requested_cgd",
            "designation",
            "phone",
            "status",
            "assigned_role",
            "creation",
        ],
        order_by="creation desc",
    )


@frappe.whitelist()
@agent_manager_only
def approve_signup_request(
    request_name: str,
    customer: str | None = None,
    role: str | None = None,
) -> dict:
    """Approve a signup request and activate the customer account."""
    doc = frappe.get_doc("HD Customer Signup Request", request_name)
    return doc.approve(customer=customer, role=role)


@frappe.whitelist()
@agent_manager_only
def reject_signup_request(
    request_name: str,
    reason: str | None = None,
) -> dict:
    """Reject a customer signup request with a stated reason."""
    doc = frappe.get_doc("HD Customer Signup Request", request_name)
    return doc.reject(reason=reason)
