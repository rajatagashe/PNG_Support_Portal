import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import validate_email_address


class HDCustomerSignupRequest(Document):
    def validate(self):
        self.clean_email()
        self.validate_email_format()
        self.validate_cgd_exists()

    def clean_email(self):
        if self.email:
            self.email = self.email.strip().lower()

    def validate_email_format(self):
        if self.email:
            validate_email_address(self.email, throw=True)

    def validate_cgd_exists(self):
        if self.requested_cgd and not frappe.db.exists("HD Customer", self.requested_cgd):
            frappe.throw(
                _("The selected CGD Customer '{0}' does not exist.").format(self.requested_cgd),
                frappe.DoesNotExistError,
            )

    @frappe.whitelist()
    def approve(self, customer: str | None = None, role: str | None = None):
        """Approve registration, provision user and contact, link to HD Customer."""
        self.check_review_permission()
        self.ensure_pending_status()

        target_customer = customer or self.requested_cgd
        target_role = role or self.assigned_role or "HD Customer"

        user = self.get_or_create_user(target_role)
        self.assign_user_roles(user, target_role)
        contact = self.get_or_create_contact(user)
        self.link_contact_to_customer(target_customer, contact, target_role)

        self.status = "Approved"
        self.assigned_role = target_role
        self.requested_cgd = target_customer
        self.reviewed_by = frappe.session.user
        self.reviewed_on = frappe.utils.now_datetime()
        self.save(ignore_permissions=True)

        return {"status": "Approved", "user": user.name}

    @frappe.whitelist()
    def reject(self, reason: str | None = None):
        """Reject the signup request."""
        self.check_review_permission()
        self.ensure_pending_status()

        self.status = "Rejected"
        self.rejection_reason = reason or _("Signup request declined by administrator.")
        self.reviewed_by = frappe.session.user
        self.reviewed_on = frappe.utils.now_datetime()
        self.save(ignore_permissions=True)

        return {"status": "Rejected"}

    def check_review_permission(self):
        user_roles = frappe.get_roles()
        if not ("System Manager" in user_roles or "Agent Manager" in user_roles):
            frappe.throw(
                _("Only an Agent Manager or System Manager can approve or reject signup requests."),
                frappe.PermissionError,
            )

    def ensure_pending_status(self):
        if self.status != "Pending":
            frappe.throw(
                _("This signup request has already been reviewed ({0}).").format(self.status),
                frappe.ValidationError,
            )

    def get_or_create_user(self, target_role: str | None = None):
        user = frappe.db.get_value("User", {"email": self.email})
        if user:
            user_doc = frappe.get_doc("User", user)
            if not user_doc.enabled:
                user_doc.enabled = 1
                user_doc.save(ignore_permissions=True)
            return user_doc

        roles = []
        if target_role and frappe.db.exists("Role", target_role):
            roles.append({"role": target_role})

        user_doc = frappe.get_doc(
            {
                "doctype": "User",
                "email": self.email,
                "first_name": self.full_name,
                "enabled": 1,
                "send_welcome_email": 1,
                "user_type": "Website User",
                "roles": roles,
            }
        )
        user_doc.insert(ignore_permissions=True)
        return user_doc

    def get_or_create_contact(self, user):
        contact = frappe.db.get_value("Contact", {"email_id": self.email}) or frappe.db.get_value(
            "Contact", {"user": user.name}
        )
        if contact:
            return contact

        contact_doc = frappe.get_doc(
            {
                "doctype": "Contact",
                "first_name": self.full_name,
                "email_id": self.email,
                "user": user.name,
                "phone": self.phone or "",
            }
        )
        contact_doc.append("email_ids", {"email_id": self.email, "is_primary": 1})
        if self.phone:
            contact_doc.append("phone_nos", {"phone": self.phone, "is_primary_phone": 1})
        contact_doc.insert(ignore_permissions=True)
        return contact_doc.name

    def link_contact_to_customer(self, customer: str, contact: str, role: str):
        if not customer or not frappe.db.exists("HD Customer", customer):
            return

        is_manager = role == "HD Customer Manager"
        customer_doc = frappe.get_doc("HD Customer", customer)
        for row in customer_doc.contacts:
            if row.contact_name == contact:
                if is_manager and not row.is_manager:
                    row.is_manager = True
                    customer_doc.save(ignore_permissions=True)
                return

        customer_doc.append("contacts", {"contact_name": contact, "is_manager": is_manager})
        customer_doc.save(ignore_permissions=True)

    def assign_user_roles(self, user, role: str):
        user.reload()
        current_roles = [r.role for r in user.roles]
        updated = False
        if role and role not in current_roles and frappe.db.exists("Role", role):
            user.append("roles", {"role": role})
            updated = True
        if updated:
            user.save(ignore_permissions=True)
