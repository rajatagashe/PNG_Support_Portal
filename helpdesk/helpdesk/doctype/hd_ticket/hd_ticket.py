import json
import uuid
from email.utils import parseaddr

import frappe
from bs4 import BeautifulSoup, Comment
from frappe import _
from frappe.core.page.permission_manager.permission_manager import remove
from frappe.desk.form.assign_to import add as assign
from frappe.desk.form.assign_to import clear as clear_all_assignments
from frappe.desk.form.assign_to import get as get_assignees
from frappe.email.email_body import get_message_id
from frappe.model.document import Document
from frappe.permissions import add_permission, update_permission_property
from frappe.utils import add_to_date, cint, get_string_between, getdate, now_datetime
from frappe.utils.html_utils import sanitize_html
from pypika.functions import Count
from pypika.queries import Query
from pypika.terms import Criterion

from helpdesk.consts import SERVER_COMPUTED_FIELDS
from helpdesk.helpdesk.doctype.hd_settings.helpers import (
    get_default_email_content,
    is_email_content_empty,
)
from helpdesk.helpdesk.utils.email import (
    default_outgoing_email_account,
    default_ticket_outgoing_email_account,
)
from helpdesk.notifications import clear as clear_notifications
from helpdesk.notifications import notify_ticket_reopened
from helpdesk.utils import (
    agent_only,
    capture_event,
    get_agents_team,
    get_customers,
    get_doc_room,
    is_admin,
    is_agent,
    publish_event,
)

from ..hd_service_level_agreement.utils import get_sla
from .customer_edit_controller import CustomerEditController

customer_not_allowed_fields = ["customer"]


class HDTicket(Document, CustomerEditController):
    @property
    def default_open_status(self):
        return frappe.db.get_value(
            "HD Service Level Agreement",
            self.sla,
            "default_ticket_status",
        ) or frappe.db.get_single_value("HD Settings", "default_ticket_status")

    @property
    def ticket_reopen_status(self):
        return frappe.db.get_value(
            "HD Service Level Agreement",
            self.sla,
            "ticket_reopen_status",
        ) or frappe.db.get_single_value("HD Settings", "ticket_reopen_status")

    def publish_update(self):
        room = get_doc_room("HD Ticket", self.name)
        publish_event(
            "helpdesk:ticket-update", room=room, data={"ticket_id": self.name}
        )

    def autoname(self):
        return self.name

    def before_insert(self):
        self.generate_key()
        self.apply_ticket_insert_rules()
        self.run_insert_triggers()

    def validate_higher_perm_levels(self):
        # ahead of the framework's silent reset of fields the user cannot write,
        # so a customer's change is refused out loud instead of vanishing
        self.prevent_customer_edits()
        super().validate_higher_perm_levels()

    def before_validate(self):
        self.validate_granular_role_permissions()
        self.check_update_perms()
        self.set_ticket_type()
        self.set_raised_by()
        self.set_priority()
        self.set_first_responded_on()
        self.set_feedback_values()
        self.set_default_status()
        self.set_status_category()
        self.set_sla()

        self.validate_portal_contact()
        self.set_contact()
        self.set_customer()
        self.apply_vip_routing()

    def validate(self):
        self.validate_feedback()
        self.validate_status_transition()


    def before_save(self):
        self.set_resolution_date()
        self.apply_sla()
        self.handle_email_feedback()
        self.run_update_triggers()

        if self.is_new():
            self.raised_outside_working_hours = (
                self.is_currently_outside_working_hours()
            )

    def _get_rendered_template(
        self, content: str, default_content: str, args: dict[str, str] | None = None
    ):
        if args is None:
            args = dict()
        template_args = {
            "doc": self.as_dict(),
        }
        for key, value in args.items():
            template_args[key] = value
        return frappe.render_template(
            default_content if is_email_content_empty(content) else content,
            template_args,
        )

    def handle_email_feedback(self):
        if (
            self.is_new()
            or self.via_customer_portal
            or self.feedback_rating
            or not self.has_value_changed("status")
            or not self.key
        ):
            return

        [is_email_feedback_enabled, email_feedback_status] = frappe.get_cached_value(
            "HD Settings",
            "HD Settings",
            ["enable_email_ticket_feedback", "send_email_feedback_on_status"],
        )

        send_feedback_email = int(is_email_feedback_enabled) and (
            email_feedback_status == self.status
            or email_feedback_status == ""
            and self.status == "Closed"
        )

        if not send_feedback_email:
            return

        last_communication = self.get_last_communication()

        url = f"{frappe.utils.get_url()}/ticket-feedback/new?key={self.key}"
        feedback_email_content = frappe.db.get_single_value(
            "HD Settings", "feedback_email_content"
        )
        default_feedback_email_content = get_default_email_content("share_feedback")
        try:
            frappe.sendmail(
                recipients=[self.raised_by],
                subject=f"Re: {self.subject}",
                message=self._get_rendered_template(
                    feedback_email_content,
                    default_feedback_email_content,
                    {"url": url},
                ),
                reference_doctype="HD Ticket",
                reference_name=self.name,
                now=True,
                in_reply_to=last_communication.name if last_communication else None,
                email_headers={"X-Auto-Generated": "hd-email-feedback"},
            )
            frappe.msgprint(_("Feedback email has been sent to the customer"))
        except Exception as e:
            frappe.throw(_("Could not send feedback email,due to: {0}").format(e))

    def after_insert(self):
        # Telemetry Event
        self.capture_ticket_created_telemetry_events()
        publish_event("helpdesk:new-ticket")
        self.tag_first_ticket()
        self.apply_unclassified_tag()
        self.apply_vip_tag()
        self.apply_pending_trigger_tags()
        self.sync_problem_incident_count()
        self.dispatch_creation_webhooks()

        if self.get("description"):
            self.create_communication_via_contact(self.description, new_ticket=True)
            self.handle_inline_media_new_ticket()

        send_ack_email = frappe.db.get_single_value(
            "HD Settings", "send_acknowledgement_email"
        )
        if (
            not self.via_customer_portal
            and not frappe.flags.initial_sync
            and send_ack_email
        ):
            self.send_acknowledgement_email()

    def capture_ticket_created_telemetry_events(self):
        if self.subject == "Welcome to Helpdesk":
            return

        capture_event("ticket_created")
        if not self.via_customer_portal:
            capture_event("ticket_created_via_email")
        if self.via_customer_portal and not is_agent():
            capture_event("ticket_created_via_customer")

        if self.ticket_split_from:
            self.add_comment(
                "Info", "split the ticket from #{0}".format(self.ticket_split_from)
            )
            capture_event("ticket_split")

    def tag_first_ticket(self):
        """Tag the first ticket a requester ever raises.

        This is a one-time tag, so it only applies to the first ticket a requester raises.
        """
        from helpdesk.api.tags import FIRST_TICKET_TAG, FIRST_TICKET_TAG_COLOR

        if not self.raised_by:
            return
        earlier_ticket = frappe.db.exists(
            "HD Ticket", {"raised_by": self.raised_by, "name": ["!=", self.name]}
        )
        if earlier_ticket:
            return

        self.add_tag(FIRST_TICKET_TAG, FIRST_TICKET_TAG_COLOR)

    def on_update(self):
        # flake8: noqa
        if self.status_category == "Open":
            if (
                self.get_doc_before_save()
                and self.get_doc_before_save().status_category != "Open"
            ):
                agents = self.get_assigned_agents()
                if agents:
                    notify_ticket_reopened(
                        self.name,
                        [agent.name for agent in agents],
                        reopened_by=self.flags.reopened_by,
                    )

        self.remove_assignment_if_not_in_team()
        self.publish_update()
        self.capture_update_telemetry_events()
        self.sync_problem_incident_count()
        self.handle_problem_status_change()
        self.dispatch_update_webhooks()
        self.handle_csat_trigger_on_resolution()

    def dispatch_creation_webhooks(self):
        try:
            from helpdesk.automation.webhook_engine import dispatch_ticket_webhooks
            dispatch_ticket_webhooks(self, "On Ticket Creation")
        except Exception as e:
            frappe.log_error(f"Error dispatching creation webhook for {self.name}: {str(e)}", "Webhook Error")

    def dispatch_update_webhooks(self):
        try:
            from helpdesk.automation.webhook_engine import dispatch_ticket_webhooks
            old_doc = self.get_doc_before_save()
            if old_doc and old_doc.status != self.status:
                dispatch_ticket_webhooks(self, "On Status Change", old_doc=old_doc)
                if self.status in ["Resolved", "Closed"]:
                    dispatch_ticket_webhooks(self, "On Ticket Resolution", old_doc=old_doc)
            dispatch_ticket_webhooks(self, "On Ticket Update", old_doc=old_doc)
        except Exception as e:
            frappe.log_error(f"Error dispatching update webhook for {self.name}: {str(e)}", "Webhook Error")

    def handle_csat_trigger_on_resolution(self):
        old_doc = self.get_doc_before_save()
        if self.status in ["Resolved", "Closed"] and (not old_doc or old_doc.status not in ["Resolved", "Closed"]):
            try:
                from helpdesk.api.csat import trigger_resolution_csat
                trigger_resolution_csat(self)
            except Exception as e:
                frappe.log_error(f"Error triggering CSAT for {self.name}: {str(e)}", "CSAT Trigger Error")

    def capture_update_telemetry_events(self):
        capture_event("ticket_updated")

        if self.has_value_changed("status"):
            capture_event("ticket_status_updated")
        if (
            self.has_value_changed("status_category")
            and self.status_category == "Resolved"
        ):
            capture_event("ticket_resolved")

    def on_trash(self):
        self.validate_trash_permissions()
        self.sync_problem_incident_count(on_trash=True)

    def validate_trash_permissions(self):
        user = frappe.session.user
        if not user or user == "Administrator":
            return
        roles = set(frappe.get_roles(user))
        if ("HD Tier 1 Agent" in roles or "HD Auditor" in roles) and not (roles & {"System Manager", "Agent Manager", "HD Team Lead"}):
            frappe.throw(
                frappe._("HD Tier 1 Agents and Auditors are not permitted to delete tickets."),
                frappe.PermissionError,
            )

    def validate_granular_role_permissions(self):
        """Enforce granular agent role boundaries: Tier 1, Tier 2, Team Lead, and Auditor."""
        user = frappe.session.user
        if not user or user == "Administrator":
            return

        roles = set(frappe.get_roles(user))
        if roles & {"System Manager", "Agent Manager", "HD Team Lead"}:
            return

        # 1. Auditor check: strictly read-only
        if "HD Auditor" in roles and not (roles & {"Agent", "HD Tier 1 Agent", "HD Tier 2 Agent"}):
            frappe.throw(
                frappe._("Auditor role is read-only. You cannot modify tickets."),
                frappe.PermissionError,
            )

        # 2. Tier 1 Agent restrictions: cannot merge tickets or change SLA
        if "HD Tier 1 Agent" in roles and not (roles & {"HD Tier 2 Agent"}):
            if not self.is_new() and self.has_value_changed("is_merged") and self.is_merged:
                frappe.throw(
                    frappe._("HD Tier 1 Agents are not permitted to merge tickets."),
                    frappe.PermissionError,
                )
            if not self.is_new() and self.has_value_changed("sla"):
                frappe.throw(
                    frappe._("HD Tier 1 Agents are not permitted to modify ticket SLA."),
                    frappe.PermissionError,
                )

    def sync_problem_incident_count(self, on_trash=False):
        """Update incident_count on parent problem ticket(s)."""
        current_problem = None if on_trash else self.get("problem_ticket")
        before_save = self.get_doc_before_save()
        old_problem = before_save.get("problem_ticket") if before_save else None

        problems_to_update = set()
        if current_problem:
            problems_to_update.add(current_problem)
        if old_problem and old_problem != current_problem:
            problems_to_update.add(old_problem)

        for prob_id in problems_to_update:
            if prob_id and frappe.db.exists("HD Ticket", prob_id):
                filters = {"problem_ticket": prob_id}
                if on_trash:
                    filters["name"] = ["!=", self.name]
                count = frappe.db.count("HD Ticket", filters)
                frappe.db.set_value("HD Ticket", prob_id, "incident_count", count, update_modified=False)

    def handle_problem_status_change(self):
        """When a Problem ticket is resolved, propagate to linked incidents."""
        if self.ticket_type != "Problem":
            return
        before_save = self.get_doc_before_save()
        if not before_save or before_save.status == self.status:
            return

        if self.status_category == "Resolved" or self.status in ("Resolved", "Closed"):
            self.propagate_resolution_to_incidents()

    def propagate_resolution_to_incidents(self):
        """Resolve all linked incident tickets and add automated audit comment."""
        linked_incidents = frappe.get_all(
            "HD Ticket",
            filters={
                "problem_ticket": self.name,
                "status_category": ["!=", "Resolved"],
            },
            pluck="name",
        )
        for inc_name in linked_incidents:
            inc_doc = frappe.get_doc("HD Ticket", inc_name)
            inc_doc.status = self.status
            if self.resolution_details and not inc_doc.resolution_details:
                inc_doc.resolution_details = self.resolution_details
            inc_doc.flags.ignore_status_guards = True
            inc_doc.flags.ignore_permissions = True
            inc_doc.save(ignore_permissions=True)

            inc_doc.add_comment(
                "Comment",
                f"Resolved automatically via Master Problem Ticket #{self.name}."
            )

    def set_ticket_type(self):
        if self.ticket_type:
            return
        self.ticket_type = (
            frappe.db.get_single_value("HD Settings", "default_ticket_type") or ""
        )

    def set_raised_by(self):
        if self.raised_by:
            return
        self.raised_by = frappe.session.user

    def validate_portal_contact(self) -> None:
        """Block non-agent users from attributing a ticket to another contact.

        Agents are unrestricted, and so are system channels like email intake,
        which run as Administrator.
        """
        if is_agent() or is_admin():
            return
        if self.get("is_guest_ticket") or getattr(self.flags, "is_guest_ticket", False) or getattr(self.flags, "ignore_permissions", False):
            return
        if not self.contact:
            return

        if not self.is_new() and not self.has_value_changed("contact"):
            return

        if self.contact != self.get_session_contact():
            frappe.throw(
                _("You can only raise tickets for your own contact."),
                frappe.PermissionError,
            )

    def get_session_contact(self) -> str | None:
        """Resolve the Contact owned by the current session user.

        Match strictly on the ``user`` link. Fall back to the email only when
        it is the session user's own verified email and the Contact is not
        already linked to a different user, so an unrelated record that merely
        shares the email can never satisfy the ownership check.
        """
        contact = frappe.db.get_value("Contact", {"user": frappe.session.user})
        if contact:
            return contact

        user_email = frappe.db.get_value("User", frappe.session.user, "email")
        if not user_email:
            return None
        return frappe.db.get_value(
            "Contact", {"email_id": user_email, "user": ("in", ("", None))}
        )

    def set_contact(self):
        email_id = parseaddr(self.raised_by)[1]
        # flake8: noqa
        if email_id:
            if not self.contact:
                contact = frappe.db.get_value("Contact", {"email_id": email_id})
                if contact:
                    self.contact = contact

    def set_customer(self):
        # For existing tickets, only validate if customer value has changed
        if not self.is_new() and not self.has_value_changed("customer"):
            return

        contact_customers = get_customers(contact=self.contact) if self.contact else []

        if self.customer:
            if self.customer not in contact_customers and not is_agent():
                frappe.throw(
                    _(
                        "The selected customer {0} is not linked to the contact {1}."
                        "Please select a valid customer or update the contact's linked customers."
                    ).format(self.customer, self.contact),
                    frappe.ValidationError,
                )
            return

        if not frappe.db.get_single_value(
            "HD Settings", "auto_set_customer_from_contact"
        ):
            return

        # Auto-set customer only for new tickets
        if self.is_new() and self.contact:
            if len(contact_customers) == 1:
                self.customer = contact_customers[0]
            elif (
                len(contact_customers) > 1
                and not is_agent()
                and self.via_customer_portal
            ):
                frappe.throw(
                    _(
                        "The contact {0} is linked to multiple customers. Please select the customer manually."
                    ).format(self.contact),
                    frappe.ValidationError,
                )

        if self.is_new() and not self.customer:
            self.map_customer_from_domain()

        if self.is_new() and not self.customer:
            self.handle_unclassified_ticket()

    def map_customer_from_domain(self):
        """Map customer and default team from sender domain via HD Domain Mapping or HD Customer."""
        if not self.raised_by or self.customer:
            return

        email_id = parseaddr(self.raised_by)[1]
        if not email_id or "@" not in email_id:
            return

        domain = email_id.split("@")[-1].strip().lower()

        # 1. Check HD Domain Mapping
        mapping = frappe.db.get_value(
            "HD Domain Mapping",
            {"domain": domain, "is_active": 1},
            ["customer", "default_team"],
            as_dict=True,
        )
        if mapping and mapping.customer:
            self.customer = mapping.customer
            if not self.agent_group and mapping.default_team:
                self.agent_group = mapping.default_team
            self.ensure_contact_linked_to_customer(email_id, mapping.customer)
            return

        # 2. Fallback to HD Customer.domain if matching
        customer = frappe.db.get_value("HD Customer", {"domain": domain}, "name")
        if customer:
            self.customer = customer
            self.ensure_contact_linked_to_customer(email_id, customer)

    def ensure_contact_linked_to_customer(self, email_id: str, customer: str):
        """Ensure a Contact exists for email_id and is associated with the customer."""
        if not self.contact:
            contact = frappe.db.get_value("Contact", {"email_id": email_id})
            if not contact:
                first_name = parseaddr(self.raised_by)[0] or email_id.split("@")[0]
                contact_doc = frappe.get_doc(
                    {
                        "doctype": "Contact",
                        "first_name": first_name,
                        "email_id": email_id,
                    }
                )
                contact_doc.append("email_ids", {"email_id": email_id, "is_primary": 1})
                contact_doc.insert(ignore_permissions=True)
                contact = contact_doc.name
            self.contact = contact

        # Link contact to HD Customer if not already linked
        if customer and self.contact and frappe.db.exists("HD Customer", customer):
            customer_doc = frappe.get_doc("HD Customer", customer)
            already_linked = any(
                row.contact_name == self.contact for row in customer_doc.contacts
            )
            if not already_linked:
                customer_doc.append("contacts", {"contact_name": self.contact})
                customer_doc.save(ignore_permissions=True)

    def handle_unclassified_ticket(self):
        """Route unmapped tickets to the unclassified triage team and schedule unclassified tag."""
        if self.customer:
            return

        unclassified_team = frappe.db.get_single_value(
            "HD Settings", "unclassified_team"
        )
        if unclassified_team and not self.agent_group:
            self.agent_group = unclassified_team

        tag_unmapped = frappe.db.get_single_value(
            "HD Settings", "tag_unmapped_tickets"
        )
        if tag_unmapped:
            self.flags.tag_as_unclassified = True

    def apply_unclassified_tag(self):
        """Apply 'unclassified-cgd' tag if the ticket had no mapped customer."""
        if getattr(self.flags, "tag_as_unclassified", False):
            self.add_tag("unclassified-cgd")

    def apply_vip_routing(self):
        """Apply VIP / Priority CGD escalation rules for high-priority CGD entities."""
        if not self.is_new() and not self.has_value_changed("customer"):
            return

        vip_rule = None
        # 1. Match active HD VIP Routing Rule by customer
        if self.customer and frappe.db.table_exists("HD VIP Routing Rule"):
            vip_rule = frappe.db.get_value(
                "HD VIP Routing Rule",
                {"customer": self.customer, "is_active": 1},
                [
                    "name",
                    "escalate_priority",
                    "escalate_team",
                    "escalate_sla",
                    "vip_tag",
                    "require_senior_agent",
                ],
                as_dict=True,
            )

        # 2. Match active HD VIP Routing Rule by domain
        if not vip_rule and self.raised_by and frappe.db.table_exists("HD VIP Routing Rule"):
            email_id = parseaddr(self.raised_by)[1]
            if email_id and "@" in email_id:
                domain = email_id.split("@")[-1].strip().lower()
                vip_rule = frappe.db.get_value(
                    "HD VIP Routing Rule",
                    {"domain": domain, "is_active": 1},
                    [
                        "name",
                        "escalate_priority",
                        "escalate_team",
                        "escalate_sla",
                        "vip_tag",
                        "require_senior_agent",
                    ],
                    as_dict=True,
                )

        # 3. Check HD Customer is_vip flag
        customer_vip_data = None
        if self.customer and frappe.db.exists("HD Customer", self.customer):
            customer_vip_data = frappe.db.get_value(
                "HD Customer",
                self.customer,
                ["is_vip", "vip_priority", "vip_team", "vip_sla"],
                as_dict=True,
            )

        is_vip = bool(vip_rule) or bool(customer_vip_data and customer_vip_data.get("is_vip"))
        if not is_vip:
            return

        # Determine escalation parameters
        escalate_priority = (
            (vip_rule and vip_rule.get("escalate_priority"))
            or (customer_vip_data and customer_vip_data.get("vip_priority"))
            or "Urgent"
        )
        escalate_team = (
            (vip_rule and vip_rule.get("escalate_team"))
            or (customer_vip_data and customer_vip_data.get("vip_team"))
        )
        escalate_sla = (
            (vip_rule and vip_rule.get("escalate_sla"))
            or (customer_vip_data and customer_vip_data.get("vip_sla"))
        )
        vip_tag = (vip_rule and vip_rule.get("vip_tag")) or "vip-cgd"

        # Escalate priority
        priority_rank = {"Low": 1, "Medium": 2, "High": 3, "Urgent": 4}
        curr_rank = priority_rank.get(self.priority or "", 0)
        target_rank = priority_rank.get(escalate_priority, 4)
        if target_rank > curr_rank:
            self.priority = escalate_priority

        # Escalate team if not already custom set or if set to unclassified
        unclassified_team = frappe.db.get_single_value("HD Settings", "unclassified_team")
        if escalate_team and (not self.agent_group or self.agent_group == unclassified_team):
            self.agent_group = escalate_team

        # Escalate SLA policy
        if escalate_sla:
            self.sla = escalate_sla

        # Tagging flag
        self.flags.tag_as_vip = vip_tag
        self.flags.is_vip_ticket = True
        if vip_rule and vip_rule.get("require_senior_agent"):
            self.flags.require_senior_agent = True

    def apply_vip_tag(self):
        """Apply configured VIP tag if ticket was identified as VIP."""
        tag = getattr(self.flags, "tag_as_vip", None)
        if tag:
            self.add_tag(tag)

    def set_priority(self):
        if self.priority:
            return
        self.priority = frappe.get_cached_value(
            "HD Ticket Type", self.ticket_type, "priority"
        ) or frappe.get_cached_value("HD Settings", "HD Settings", "default_priority")

    def set_first_responded_on(self):
        if self.is_new():
            return
        if self.first_responded_on:
            return

        old_status_category = (
            self.get_doc_before_save().status_category
            if self.get_doc_before_save()
            else None
        )
        is_closed_or_resolved = (
            old_status_category == "Open" and self.status_category == "Resolved"
        )

        if self.status_category == "Paused" or is_closed_or_resolved:
            self.first_responded_on = frappe.utils.now_datetime()

    def set_feedback_values(self):
        if not self.feedback:
            return
        feedback_option = frappe.get_doc("HD Ticket Feedback Option", self.feedback)
        self.feedback_rating = feedback_option.rating

    @property
    def has_agent_replied(self):
        return frappe.db.exists(
            "Communication",
            {
                "reference_doctype": "HD Ticket",
                "reference_name": self.name,
                "sent_or_received": "Sent",
            },
        )

    def validate_feedback(self):
        is_feedback_mandatory = frappe.get_cached_value(
            "HD Settings", "HD Settings", "is_feedback_mandatory"
        )
        if (
            self.feedback_rating
            or self.status_category != "Resolved"
            or is_agent()
            or not self.has_agent_replied
            or not is_feedback_mandatory
        ):
            return

        frappe.throw(
            _("Ticket must be resolved with a feedback"), frappe.ValidationError
        )

    def generate_key(self):
        self.key = uuid.uuid4()

    def remove_assignment_if_not_in_team(self):
        """
        Removes the assignment if the agent is not in the team.
        Should be called inside on_update
        """
        if self.is_new():
            return
        if not self.agent_group or (hasattr(self, "_assign") and not self._assign):
            return
        if self.has_value_changed("agent_group") and self.status_category == "Open":
            current_assigned_agent = self.get_assigned_agent()
            if not current_assigned_agent:
                return
            is_agent_in_assigned_team = self.agent_in_assigned_team(
                current_assigned_agent, self.agent_group
            )

            if (
                not is_agent_in_assigned_team
            ) and self.users_present_in_team_assignment_rule():
                clear_all_assignments("HD Ticket", self.name)

    def agent_in_assigned_team(self, agent, team):
        return frappe.db.exists(
            "HD Team Member",
            {
                "parent": team,
                "user": agent,
            },
        )

    def users_present_in_team_assignment_rule(self):
        if not self.agent_group:
            return False

        assignment_rule = frappe.db.get_value(
            "HD Team", self.agent_group, "assignment_rule"
        )
        if not assignment_rule:
            return False

        is_disabled = frappe.db.get_value(
            "Assignment Rule", assignment_rule, "disabled"
        )
        if is_disabled:
            return False

        users = frappe.get_all(
            "Assignment Rule User", filters={"parent": assignment_rule}
        )
        if not users:
            return False

        return True

    @frappe.whitelist()
    @agent_only
    def assign_agent(self, agent: str):
        # core assign_to notifies and emails the agent (self-assign suppressed);
        # its Notification Log row derives app="helpdesk" from the ticket
        assign({"assign_to": [agent], "doctype": "HD Ticket", "name": self.name})

    def add_tag(self, tag: str, color: str = "Gray"):
        """Tag this ticket, claiming the Tag master for helpdesk.

        Overrides ``Document.add_tag``, which links the tag but leaves the
        master without app/color, so it never lists in the tag picker.
        ``remove_tag`` needs no override: core's already ignores a tag that
        is not applied.
        """
        from helpdesk.api.tags import apply_tag

        apply_tag(self.doctype, self.name, tag, color)

    def get_assigned_agents(self):
        assignees = get_assignees({"doctype": "HD Ticket", "name": self.name})
        if len(assignees) > 0:
            names = [assignee.owner for assignee in assignees]
            return frappe.get_all("HD Agent", filters={"name": ["in", names]})

    def get_assigned_agent(self):
        # TODO: deprecate this
        # for some reason _assign is not set, maybe a framework bug?
        if hasattr(self, "_assign") and self._assign:
            assignees = json.loads(self._assign)
            if len(assignees) > 0:
                # TODO: temporary fix, remove this when only agents can be assigned to ticket
                exists = frappe.db.exists("HD Agent", assignees[0])
                if exists:
                    return assignees[0]

        assignees = get_assignees({"doctype": "HD Ticket", "name": self.name})
        if len(assignees) > 0:
            # TODO: temporary fix, remove this when only agents can be assigned to ticket
            return frappe.db.exists("HD Agent", assignees[0].owner)

        return None

    def skip_email_workflow(self):
        skip: str = frappe.get_value("HD Settings", None, "skip_email_workflow") or "0"

        return bool(int(skip))

    def _resolve_sender_email(self, email_account_name, from_email_id):
        if not email_account_name:
            sender_email = self.sender_email()
            return sender_email, (sender_email.name if sender_email else None)

        if not frappe.db.exists("Email Account", email_account_name):
            frappe.throw(_("No Email Account found for {0}").format(from_email_id))

        sender_email = frappe._dict(name=email_account_name, email_id=from_email_id)
        return sender_email, email_account_name

    def instantly_send_email(self):
        check: str = (
            frappe.get_value("HD Settings", None, "instantly_send_email") or "0"
        )

        return bool(int(check))

    @frappe.whitelist()
    def get_last_communication(self):
        filters = {
            "reference_doctype": "HD Ticket",
            "reference_name": ["=", str(self.name)],
        }

        try:
            communication = frappe.get_last_doc(
                "Communication",
                filters=filters,
            )

            return communication
        except Exception:
            return None

    def _last_threadable_communication(self) -> str | None:
        """Name of the newest communication that has a message_id.

        Frappe builds In-Reply-To from that field, so a communication without one
        cannot be replied to. Portal replies sent no email and have none.
        """
        return frappe.db.get_value(
            "Communication",
            {
                "reference_doctype": "HD Ticket",
                "reference_name": str(self.name),
                "message_id": ["is", "set"],
            },
            "name",
            order_by="creation desc",
        )

    def last_communication_email(self):
        if not (communication := self.get_last_communication()):
            return

        if not communication.email_account:
            return

        email_account = frappe.get_doc("Email Account", communication.email_account)

        if not email_account.enable_outgoing:
            return

        return email_account

    def sender_email(self):
        """
        Find an email to use as sender. Fall back through multiple choices

        :return: `Email Account`
        """
        if email_account := self.last_communication_email():
            return email_account

        if email_account := default_ticket_outgoing_email_account():
            return email_account

        if email_account := default_outgoing_email_account():
            return email_account

    @property
    def portal_uri(self):
        root_uri = frappe.utils.get_url()
        return f"{root_uri}/helpdesk/my-tickets/{self.name}"

    @frappe.whitelist()
    def new_comment(self, content: str, attachments: list[str] = []):
        if not is_agent():
            frappe.throw(
                _("You are not permitted to add a comment"), frappe.PermissionError
            )
        comment = self.add_comment("Comment", content)
        urls = [a.get("file_url") for a in attachments if a.get("file_url")]
        soup = BeautifulSoup(content or "", "html.parser")
        urls += [
            tag["src"] for tag in soup.find_all(["img", "video"]) if tag.has_attr("src")
        ]
        self.claim_comment_files(comment.name, urls)
        return comment.name

    def claim_comment_files(self, comment: str, urls: list[str]):
        """Move a comment's files off the ticket and onto the comment.

        The editor uploads against the ticket, which every customer on it can
        read. Only the comment is agent-only, so the file has to hang off the
        comment to inherit that, and no row may be left on the ticket: any one
        readable row serves the url (see frappe's `find_file_by_url`).
        """
        if not urls:
            return
        # Someone else's file was embedded, not uploaded here; leave it be
        claimed = frappe.get_all(
            "File",
            filters={
                "file_url": ["in", urls],
                "attached_to_doctype": "HD Ticket",
                "attached_to_name": self.name,
                "owner": frappe.session.user,
            },
            pluck="name",
        )
        for name in claimed:
            frappe.db.set_value(
                "File",
                name,
                {"attached_to_doctype": "Comment", "attached_to_name": comment},
            )
        # own uploads only: a row on the comment makes its url servable to readers
        owned = frappe.get_all(
            "File",
            filters={"file_url": ["in", urls], "owner": frappe.session.user},
            pluck="file_url",
        )
        for url in set(owned):
            self.attach_file_with_doc("Comment", comment, url)

    @frappe.whitelist()
    @agent_only
    def reply_via_agent(
        self,
        message: str,
        from_email: dict | None = None,
        to: str | None = None,
        cc: str | None = None,
        bcc: str | None = None,
        attachments: list[str] = [],
        propagate_to_incidents: bool = False,
    ):
        if not is_agent():
            frappe.throw(
                _("You are not permitted to reply as an agent"), frappe.PermissionError
            )

        agent_signature = frappe.db.get_value("HD Agent", {"user": frappe.session.user}, "signature")
        if agent_signature and agent_signature.strip() and agent_signature not in message:
            message = f"{message}<br><br>{agent_signature}"

        skip_email_workflow = self.skip_email_workflow()
        medium = "" if skip_email_workflow else "Email"
        subject = f"Re: {self.subject}"
        from_email_id = from_email.get("email_id") if from_email else None
        email_account_name = from_email.get("email_account") if from_email else None
        sender = from_email_id or frappe.session.user
        recipients = to

        sender_email = None
        if not skip_email_workflow:
            sender_email, email_account_name = self._resolve_sender_email(
                email_account_name, from_email_id
            )

        if recipients == "Administrator":
            recipients = frappe.get_value("User", "Administrator", "email")

        communication = frappe.get_doc(
            {
                "bcc": bcc,
                "cc": cc,
                "communication_medium": medium,
                "communication_type": "Communication",
                "content": message,
                "doctype": "Communication",
                "email_account": email_account_name,
                "email_status": "Open",
                "recipients": recipients,
                "reference_doctype": "HD Ticket",
                "reference_name": self.name,
                "sender": sender,
                "sender_full_name": frappe.utils.get_fullname(),
                "sent_or_received": "Sent",
                "status": "Linked",
                "subject": subject,
            }
        )

        communication.in_reply_to = self._last_threadable_communication()

        # Each reply needs its own id so the next reply can point at it. Saved after
        # the send below, not here.
        should_send_email = not skip_email_workflow and frappe.db.get_single_value(
            "HD Settings", "enable_reply_email_via_agent"
        )
        message_id = None
        if should_send_email:
            # fail before writing anything we would have to undo
            if not sender_email:
                frappe.throw(
                    _(
                        "Unable to send email. Please setup default outgoing email account."
                    )
                )
            message_id = get_string_between("<", get_message_id(), ">")

        communication.insert(ignore_permissions=True)
        capture_event("agent_replied")

        _attachments = []

        for attachment in attachments:
            file_url = frappe.db.get_value("File", attachment, "file_url")
            self.attach_file_with_doc("Communication", communication.name, file_url)
            self.attach_file_with_doc("HD Ticket", self.name, file_url)
            _attachments.append({"file_url": file_url})

        if not should_send_email:
            return communication.name

        message = self.parse_content(message)

        reply_to_email = sender_email.email_id
        rendered_template: str | None = None
        if self.via_customer_portal:
            email_content = frappe.db.get_single_value(
                "HD Settings", "reply_via_agent_email_content"
            )
            default_email_content = get_default_email_content("reply_via_agent")
            try:
                rendered_template = self._get_rendered_template(
                    email_content,
                    default_email_content,
                    {"message": message, "ticket_url": self.portal_uri},
                )
            except Exception as e:
                frappe.throw(_("Could not an email due to: {0}").format(e))

        send_delayed = True
        send_now = False

        if self.instantly_send_email():
            send_delayed = False
            send_now = True

        try:
            queued_email = frappe.sendmail(
                attachments=_attachments,
                bcc=bcc,
                cc=cc,
                communication=communication.name,
                delayed=send_delayed,
                expose_recipients="header",
                message=rendered_template if rendered_template is not None else message,
                as_markdown=True,
                now=send_now,
                recipients=recipients,
                reference_doctype="HD Ticket",
                reference_name=self.name,
                reply_to=reply_to_email,
                sender=reply_to_email,
                subject=subject,
                with_container=False,
                in_reply_to=communication.in_reply_to,
                message_id=message_id,
            )
        except Exception as e:
            frappe.throw(str(e))

        # Save the id now that a mail is queued carrying it. A reply we could not hand
        # off keeps no id, so it can never become the next reply's parent.
        if queued_email:
            communication.db_set("message_id", message_id)

        if propagate_to_incidents and self.ticket_type == "Problem":
            linked_incidents = frappe.get_all(
                "HD Ticket",
                filters={"problem_ticket": self.name},
                pluck="name",
            )
            for inc_id in linked_incidents:
                frappe.get_doc("HD Ticket", inc_id).add_comment(
                    "Comment",
                    f"Public update from Master Problem #{self.name}:<br>{message}",
                )

        return communication.name

    @frappe.whitelist()
    # flake8: noqa
    def create_communication_via_contact(
        self, message: str, attachments: list[dict] = [], new_ticket: bool = False
    ):
        if not new_ticket and frappe.db.get_single_value(
            "HD Settings", "enable_reply_email_to_agent"
        ):
            # send email to assigned agents
            self.send_reply_email_to_agent(message)

        # if self.status_category == "Paused" and not new_ticket:
        if not new_ticket:
            self.status = self.ticket_reopen_status
            # flag for allowing status change when reply came in outside support portal
            self.flags.customer_reply_reopen = True
            self.save(ignore_permissions=True)

        c = frappe.new_doc("Communication")
        c.communication_type = "Communication"
        c.communication_medium = "Email"
        c.sent_or_received = "Received"
        c.email_status = "Open"
        c.subject = f"Re: {self.subject}"
        c.sender = frappe.session.user
        c.content = message
        c.status = "Linked"
        c.reference_doctype = "HD Ticket"
        c.reference_name = self.name
        c.ignore_permissions = True
        c.ignore_mandatory = True
        c.save(ignore_permissions=True)

        _attachments = self.get("attachments") or attachments or []
        if not len(_attachments):
            return
        QBFile = frappe.qb.DocType("File")
        condition_name = [QBFile.name == i["name"] for i in _attachments]
        frappe.qb.update(QBFile).set(QBFile.attached_to_name, c.name).set(
            QBFile.attached_to_doctype, "Communication"
        ).where(Criterion.any(condition_name)).run()

        # attach files to ticket
        file_urls = frappe.get_all(
            "File", filters={"attached_to_name": c.name}, pluck="file_url"
        )
        for url in file_urls:
            self.attach_file_with_doc("HD Ticket", self.name, url)

    def handle_inline_media_new_ticket(self):
        soup = BeautifulSoup(self.description, "html.parser")
        files = []  # List of file URLs
        for tag in soup.find_all(["img", "video"]):
            if tag.has_attr("src"):
                src = tag["src"]
                files.append(src)
        for f in files:
            file = frappe.db.exists(
                "File",
                {
                    "file_url": f,
                    "attached_to_doctype": ["is", "Not Set"],
                    "owner": frappe.session.user,
                },
            )
            if file:
                doc = frappe.get_doc("File", file)
                doc.attached_to_doctype = "HD Ticket"
                doc.attached_to_name = self.name
                doc.save()

    def send_reply_email_to_agent(
        self, message: str = "Please check the latest update on the portal."
    ):
        assigned_agents = self.get_assigned_agents()
        if not assigned_agents:
            return

        recipients = [a.get("name") for a in self.get_assigned_agents()]

        email_content = frappe.db.get_single_value(
            "HD Settings", "reply_email_to_agent_content"
        )
        default_email_content = get_default_email_content("reply_to_agents")
        try:
            frappe.sendmail(
                recipients=recipients,
                subject=f"Re: {self.subject} - #{self.name}",
                message=self._get_rendered_template(
                    email_content,
                    default_email_content,
                    {
                        "ticket_url": frappe.utils.get_url(
                            "/helpdesk/tickets/" + str(self.name)
                        ),
                        "message": message,
                    },
                ),
                reference_doctype="HD Ticket",
                reference_name=self.name,
                now=True,
            )
        except Exception as e:
            frappe.throw(_(e))

    def send_acknowledgement_email(self):
        acknowledgement_email_content = frappe.db.get_single_value(
            "HD Settings", "acknowledgement_email_content"
        )
        default_acknowledgement_email_content = get_default_email_content(
            "acknowledgement"
        )

        try:
            frappe.sendmail(
                recipients=[self.raised_by],
                subject=_("Ticket #{0}: We've received your request").format(self.name),
                message=self._get_rendered_template(
                    acknowledgement_email_content,
                    default_acknowledgement_email_content,
                ),
                reference_doctype="HD Ticket",
                reference_name=self.name,
                now=True,
                expose_recipients="header",
                email_headers={"X-Auto-Generated": "hd-acknowledgement"},
            )
        except Exception as e:
            frappe.throw(
                _("Could not send an acknowledgement email due to: {0}").format(e)
            )

    @frappe.whitelist()
    def mark_seen(self) -> int:
        self.add_viewed(
            unique_views=True, force=True
        )  # Document class method, no way to add unique_views via document settings, hence used force and unique_views=True
        self.add_seen()
        return clear_notifications(ticket=self.name)

    def is_valid_status_transition(self) -> bool:
        """Closing an already-resolved ticket wraps up an outcome, it is not a new one."""
        if self.is_new() or not self.has_value_changed("status"):
            return False
        if self.status != "Closed":
            return True
        previous = self.get_doc_before_save()
        return not previous or previous.status_category != "Resolved"

    def set_resolution_date(self):
        """Stamp when the ticket was resolved. Runs for every ticket, with or
        without an SLA, since it is what resolution analytics bucket by."""
        if not self.is_valid_status_transition():
            return

        if self.status_category != "Resolved":
            self.resolution_date = None
            self.resolution_time = None  # apply_sla() won't run to clear it if no SLA is attached, so clear it here
            return
        if self.resolution_date and not self.has_value_changed("status_category"):
            return
        self.resolution_date = now_datetime()

    def set_sla(self):
        """
        Find an SLA to apply to this ticket.

        If no SLA is found, clear the SLA fields. If an SLA is found, set the SLA field
        """
        if sla := get_sla(self):
            self.sla = sla.name
        else:
            self.clear_sla_fields()

    def clear_sla_fields(self):
        """If no sla is found, clear the sla fields. The clock start is kept, so
        flapping a condition off and on buys no time."""
        self.sla = None
        self.response_by = None
        self.resolution_by = None
        if self.status_category != "Paused":
            self.on_hold_since = (
                None  # else the detached window is added into the hold time.
            )
        if self.agreement_status != "Failed":
            self.agreement_status = None

    def apply_sla(self):
        """
        Apply SLA if set.
        """
        if sla := self.get_sla():
            sla.apply(self)

    def get_sla(self):
        if not self.sla:
            return None
        return frappe.get_doc("HD Service Level Agreement", self.sla)

    def is_currently_outside_working_hours(self):
        """Return True if today is a holiday or now is outside this SLA's working hours."""
        sla = self.get_sla()
        if not sla:
            return False
        if getdate() in sla.get_holidays():
            return True
        return not sla.is_working_time(now_datetime(), sla.get_working_hours())

    def set_default_status(self):
        if self.is_new():
            self.status = self.default_open_status

    def set_status_category(self):
        self.status_category = self.status_category or frappe.get_value(
            "HD Ticket Status",
            self.status,
            "category",
        )

    def get_merge_target(self):
        # Follow the chain of merged tickets to the final, non-merged ticket. Return None
        # if the chain dead-ends on a missing ticket or loops back on itself (a corrupt
        # cycle), so a reply is never redirected onto another merged ticket.
        current_ticket_name = self.merged_with
        visited_ticket_names = {self.name}
        while current_ticket_name and current_ticket_name not in visited_ticket_names:
            ticket = frappe.db.get_value(
                "HD Ticket",
                current_ticket_name,
                ["is_merged", "merged_with"],
                as_dict=True,
            )
            if not ticket:
                return None
            visited_ticket_names.add(current_ticket_name)
            if not ticket.is_merged:
                return current_ticket_name
            if not ticket.merged_with:
                return None
            current_ticket_name = ticket.merged_with
        return None

    def redirect_communication_to_merge_target(self, communication):
        merge_target_name = self.get_merge_target()
        if not merge_target_name:
            return False
        communication.db_set("reference_name", merge_target_name)
        merge_target = frappe.get_doc("HD Ticket", merge_target_name)
        merge_target.on_communication_update(communication)
        return True

    # `on_communication_update` is a special method exposed from `Communication` doctype.
    # It is called when a communication is updated. Beware of changes as this effectively
    # is an external dependency. Refer `communication.py` of Frappe framework for more.
    # Since this is called from communication itself, `c` is the communication doc.
    def on_communication_update(self, c):
        # A reply to a merged ticket belongs to its merge target; redirect it there. If no
        # safe target resolves (cycle/dead-end), fall through and handle it here so the
        # reply isn't dropped.
        if c.sent_or_received == "Received" and self.is_merged and self.merged_with:
            if self.redirect_communication_to_merge_target(c):
                return

        # If communication is incoming, then it is a reply from customer, and ticket must
        # be reopened.
        # handle re opening tickets for email
        if c.sent_or_received == "Received":
            # check if agent has replied

            if self.has_agent_replied:
                self.status = self.ticket_reopen_status
                self.flags.reopened_by = c.sender
            else:
                self.status = self.default_open_status
            # if received that means customer has replied
            self.last_customer_response = frappe.utils.now_datetime()
        # If communication is outgoing, it must be a reply from agent
        if c.sent_or_received == "Sent":
            # Ignore system notifications
            if c.communication_type and c.communication_type == "Automated Message":
                return
            # Set first response date if not set already
            self.first_responded_on = (
                self.first_responded_on or frappe.utils.now_datetime()
            )
            self.last_agent_response = frappe.utils.now_datetime()

            # TODO: remove this feature once we add automation feature
            if frappe.db.get_single_value("HD Settings", "auto_update_status"):
                self.status = frappe.db.get_single_value(
                    "HD Settings", "update_status_to"
                )

        # email tickets are inserted blank; set_only_once refuses the save that
        # would fill it, so write it already sanitized the way that save would
        if not self.description:
            self.db_set(
                "description",
                sanitize_html(c.content, linkify=True),
                update_modified=False,
            )
        # portal replies save as the customer; the reset must keep server-set fields
        self.flags.ignore_permlevel_for_fields = list(SERVER_COMPUTED_FIELDS)
        self.flags.ignore_customer_edit_guard = True
        # Save the ticket, allowing for hooks to run.
        self.save()

    def attach_file_with_doc(self, doctype, docname, file_url):
        if frappe.db.exists(
            "File",
            {
                "file_url": file_url,
                "attached_to_doctype": doctype,
                "attached_to_name": docname,
            },
        ):
            return
        file_doc = frappe.new_doc("File")
        file_doc.attached_to_doctype = doctype
        file_doc.attached_to_name = docname
        file_doc.file_url = file_url
        file_doc.save(ignore_permissions=True)

    @staticmethod
    def default_list_data(show_customer_portal_fields=False):
        columns = [
            {
                "label": "ID",
                "type": "Int",
                "key": "name",
                "width": "auto",
            },
            {
                "label": "Subject",
                "type": "Data",
                "key": "subject",
                "width": "25rem",
            },
            {
                "label": "Status",
                "type": "Select",
                "key": "status",
                "width": "8rem",
            },
            {
                "label": "First Response",
                "type": "Datetime",
                "key": "response_by",
                "width": "8rem",
            },
            {
                "label": "Resolution",
                "type": "Datetime",
                "key": "resolution_by",
                "width": "8rem",
            },
            {
                "label": "Assigned To",
                "type": "MultipleAvatar",
                "key": "_assign",
                "width": "8rem",
            },
            {
                "label": "Customer",
                "type": "Link",
                "key": "customer",
                "options": "HD Customer",
                "width": "8rem",
            },
            {
                "label": "Priority",
                "type": "Link",
                "options": "HD Ticket Priority",
                "key": "priority",
                "width": "10rem",
            },
            {
                "label": "Type",
                "type": "Link",
                "options": "HD Ticket Type",
                "key": "ticket_type",
                "width": "11rem",
            },
            {
                "label": "Team",
                "type": "Link",
                "options": "HD Team",
                "key": "agent_group",
                "width": "10rem",
            },
            {
                "label": "Contact",
                "type": "Link",
                "key": "contact",
                "options": "Contact",
                "width": "8rem",
            },
            {
                "label": "Rating",
                "type": "Rating",
                "key": "feedback_rating",
                "width": "10rem",
            },
            {
                "label": "Created",
                "type": "Datetime",
                "key": "creation",
                "options": "Contact",
                "width": "8rem",
            },
        ]
        customer_portal_columns = [
            {
                "label": "ID",
                "type": "Int",
                "key": "name",
                "width": "5rem",
            },
            {
                "label": "Subject",
                "type": "Data",
                "key": "subject",
                "width": "22rem",
            },
            {
                "label": "Status",
                "type": "Select",
                "key": "status",
                "width": "11rem",
            },
            {
                "label": "Priority",
                "type": "Link",
                "options": "HD Ticket Priority",
                "key": "priority",
                "width": "10rem",
            },
            {
                "label": "First response",
                "type": "Datetime",
                "key": "response_by",
                "width": "8rem",
            },
            {
                "label": "Resolution",
                "type": "Datetime",
                "key": "resolution_by",
                "width": "8rem",
            },
            {
                "label": "Team",
                "type": "Link",
                "options": "HD Team",
                "key": "agent_group",
                "width": "10rem",
            },
            {
                "label": "Created",
                "type": "Datetime",
                "key": "creation",
                "options": "Contact",
                "width": "8rem",
            },
        ]
        rows = [
            "name",
            "subject",
            "status",
            "priority",
            "ticket_type",
            "agent_group",
            "contact",
            "agreement_status",
            "response_by",
            "resolution_by",
            "customer",
            "first_responded_on",
            "modified",
            "creation",
            "_assign",
            "resolution_date",
        ]
        return {
            "columns": (
                customer_portal_columns if show_customer_portal_fields else columns
            ),
            "rows": rows,
        }

    def parse_content(self, content):
        """
        Finds 'src' attribute of img/video and replaces it  with 'embed' attribute
        embed tag is important because framework replaces it with <img src="cid:content_id">
        this in turn is displayed as an image in the mail sent to the customer
        """
        if not content:
            return ""

        soup = BeautifulSoup(content, "html.parser")

        # comments (e.g. Outlook MSO conditionals in quoted replies) get mangled
        # by the markdown conversion in sendmail and show up as visible text
        for comment in soup.find_all(string=lambda s: isinstance(s, Comment)):
            comment.extract()

        for tag in soup.find_all(["img", "video"]):
            src = tag.get("src")
            # only site files can be embedded; external URLs must keep their src
            if not src or not src.startswith(("/private/files/", "/files/")):
                continue
            tag["embed"] = src
            del tag["src"]

        return str(soup)

    @staticmethod
    def filter_standard_fields(fields):
        for f in fields:
            if f["name"] in customer_not_allowed_fields:
                fields.remove(f)
        return fields

    def validate_status_transition(self):
        if self.is_new() or not self.has_value_changed("status"):
            return

        if getattr(self.flags, "ignore_status_guards", False):
            return

        old_status = (
            self.get_doc_before_save().status
            if self.get_doc_before_save()
            else None
        )
        new_status = self.status

        guards = frappe.get_all(
            "HD Status Transition Guard",
            filters={"is_enabled": 1, "to_status": new_status},
            fields=[
                "name",
                "from_status",
                "to_status",
                "allowed_roles",
                "required_fields",
                "error_message",
            ],
        )

        user_roles = frappe.get_roles()

        for guard in guards:
            if guard.from_status and guard.from_status != old_status:
                continue

            if guard.allowed_roles:
                allowed = [
                    r.strip() for r in guard.allowed_roles.split(",") if r.strip()
                ]
                if not any(role in user_roles for role in allowed):
                    msg = guard.error_message or _(
                        "You do not have permission to transition ticket status from '{0}' to '{1}'."
                    ).format(old_status, new_status)
                    frappe.throw(msg, frappe.PermissionError)

            if guard.required_fields:
                required = [
                    f.strip()
                    for f in guard.required_fields.split(",")
                    if f.strip()
                ]
                missing = [f for f in required if not self.get(f)]
                if missing:
                    msg = guard.error_message or _(
                        "The following fields are required to set status to '{0}': {1}."
                    ).format(new_status, ", ".join(missing))
                    frappe.throw(msg, frappe.ValidationError)

    def run_insert_triggers(self):
        from helpdesk.automation.trigger_engine import run_triggers

        run_triggers(self, "On Ticket Creation")

    def apply_pending_trigger_tags(self):
        pending = getattr(self.flags, "pending_trigger_tags", None)
        if pending:
            for tag in pending:
                self.add_tag(tag)

    def run_update_triggers(self):
        from helpdesk.automation.trigger_engine import run_triggers

        prev = self.get_doc_before_save()
        if self.has_value_changed("status"):
            run_triggers(self, "On Status Change", previous_ticket=prev)
        run_triggers(self, "On Ticket Update", previous_ticket=prev)


# Check if `user` has access to this specific ticket (`doc`). This implements extra
# permission checks which is not possible with standard permission system. This function
# is being called from hooks. `doc` is the ticket to check against
def has_permission(doc, user=None):
    user = user or frappe.session.user
    if is_admin(user):
        return True
    if "HD Auditor" in frappe.get_roles(user):
        return True
    if user in (doc.contact, doc.raised_by, doc.owner):
        return True
    if _is_customer_manager(doc.customer, user):
        return True
    if not is_agent(user):
        return False
    return _agent_has_permission(doc, user)


def _is_customer_manager(customer: str, user: str) -> bool:
    return any(
        c.get("name") == customer and c.get("is_manager")
        for c in get_customers(user, get_roles=True)
    )


def _agent_has_permission(doc, user: str) -> bool:
    if not frappe.db.get_single_value("HD Settings", "restrict_tickets_by_agent_group"):
        return True
    show_tickets_without_team = frappe.db.get_single_value(
        "HD Settings", "do_not_restrict_tickets_without_an_agent_group"
    )
    if show_tickets_without_team and not doc.get("agent_group"):
        return True

    if doc.get("_assign"):
        try:
            if user in json.loads(doc._assign):
                return True
        except ValueError, TypeError:
            return False

    teams = get_agents_team(user)
    if any(team.get("ignore_restrictions") for team in teams):
        return True

    team_names = [t.team_name for t in teams]
    is_team_member = frappe.db.exists(
        "HD Team Member", {"parent": ["in", team_names], "user": user}
    )
    return bool(is_team_member) and doc.get("agent_group") in team_names


# Custom perms for list query. Only the `WHERE` part
# https://frappeframework.com/docs/user/en/python-api/hooks#modify-list-query
def permission_query(user: str | None = None):
    user = user or frappe.session.user
    if is_admin(user):
        return
    if not is_agent(user):
        return _customer_query(user)
    return _agent_query(user)


def _customer_query(user: str) -> str:
    """Non-agents see their own tickets, plus all tickets of customers they manage."""
    query = _get_base_visibility(user)
    managed_customers = _get_managed_customers(user)
    if managed_customers:
        query += " OR " + _build_in_clause("customer", managed_customers)
    return query


def _agent_query(user: str) -> str | None:
    query = _get_base_visibility(user)

    if not frappe.db.get_single_value("HD Settings", "restrict_tickets_by_agent_group"):
        return  # Restrictions disabled, return all tickets

    show_tickets_without_team = frappe.db.get_single_value(
        "HD Settings", "do_not_restrict_tickets_without_an_agent_group"
    )
    if show_tickets_without_team:
        query += " OR (`tabHD Ticket`.agent_group is null OR `tabHD Ticket`.agent_group = '')"

    # An agent on a team with `ignore_restrictions` set can see every team's tickets.
    teams = get_agents_team(user)
    if any(team.get("ignore_restrictions") for team in teams):
        all_teams = frappe.get_all("HD Team", pluck="name")
        if not all_teams:
            return query
        query += " OR (" + _build_in_clause("agent_group", all_teams) + ")"
        if not show_tickets_without_team:
            query += " OR (`tabHD Ticket`.agent_group is null)"
        return query

    query += " OR (JSON_SEARCH(`tabHD Ticket`._assign, 'all', {u}) IS NOT NULL)".format(
        u=frappe.db.escape(user)
    )
    team_names = [t.get("team_name") for t in teams]
    if team_names:
        query += " OR (" + _build_in_clause("agent_group", team_names) + ")"
    return query


def _get_base_visibility(user: str) -> str:
    """WHERE fragment for tickets a user is directly tied to: owner, contact, or raiser."""

    return "(`tabHD Ticket`.owner = {u} OR `tabHD Ticket`.contact = {u} OR `tabHD Ticket`.raised_by = {u})".format(
        u=frappe.db.escape(user)
    )


def _get_managed_customers(user: str) -> list[str]:
    return [
        str(c.get("name"))
        for c in get_customers(user, get_roles=True)
        if c.get("is_manager")
    ]


def _build_in_clause(field: str, values: list[str]) -> str:
    _values = ", ".join(frappe.db.escape(v) for v in values)
    return f"`tabHD Ticket`.{field} in ({_values})"


def set_guest_ticket_creation_permission():
    doctype = "HD Ticket"
    add_permission(doctype, "Guest", 0)

    role = "Guest"
    permlevel = 0
    ptype = ["read", "write", "create", "if_owner"]

    for p in ptype:
        # update permissions
        update_permission_property(doctype, role, permlevel, p, 1)


def remove_guest_ticket_creation_permission():
    doctype = "HD Ticket"
    role = "Guest"
    permlevel = 0
    remove(doctype, role, permlevel, 1)


def close_tickets_after_n_days():
    if frappe.db.get_single_value("HD Settings", "auto_close_tickets") == 0:
        return

    status, days_threshold = frappe.db.get_value(
        "HD Settings", "HD Settings", ["auto_close_status", "auto_close_after_days"]
    )
    days_threshold = cint(days_threshold)

    # Compute the cutoff in the system timezone to match how communication_date is
    # stored. Using the database's NOW() instead would select the wrong tickets when
    # the DB server runs in a different timezone (e.g. UTC) than the Frappe system.
    inactivity_cutoff = add_to_date(now_datetime(), days=-days_threshold)

    tickets_to_close = (
        frappe.db.sql(
            """
                SELECT t.name
                FROM `tabHD Ticket` t
                INNER JOIN (
                    SELECT reference_name, MAX(communication_date) as last_communication_date
                    FROM `tabCommunication`
                    WHERE reference_doctype = 'HD Ticket'
                    GROUP BY reference_name
                ) latest_comm ON t.name = latest_comm.reference_name
                WHERE t.status = %(status)s
                AND latest_comm.last_communication_date < %(inactivity_cutoff)s
            """,
            {"inactivity_cutoff": inactivity_cutoff, "status": status},
            pluck="name",
        )
        or []
    )
    tickets_to_close = list(set(tickets_to_close))

    # cant do set_value because SLA will not be applied as setting directly to db and doc is not running.
    for ticket in tickets_to_close:
        doc = frappe.get_doc("HD Ticket", ticket)
        doc.status = "Closed"
        doc.flags.ignore_validate = True
        try:
            doc.save(ignore_permissions=True)
            # the status flip has a Version row; the reason is only recorded here
            doc.add_comment(
                "Info",
                f"automatically closed the ticket after {days_threshold} day{'s' if days_threshold > 1 else ''} of inactivity",
            )
        except Exception as e:
            frappe.log_error(
                message=f"Failed to auto close ticket {doc.name} after {days_threshold} days. Error: {e}",
                title="Auto Close Ticket Failed",
            )
            continue

        frappe.db.commit()  # nosemgrep


def update_sla_status_in_ticket():
    stale_tickets = frappe.get_all(
        "HD Ticket",
        filters={
            "status_category": ["=", "Open"],
            "sla": ["is", "set"],
        },
        pluck="name",
    )
    for ticket in stale_tickets:
        doc = frappe.get_doc("HD Ticket", ticket)
        sla = frappe.get_doc("HD Service Level Agreement", doc.sla)
        sla.handle_agreement_status(doc)
        try:
            frappe.db.set_value(
                "HD Ticket",
                doc.name,
                "agreement_status",
                doc.agreement_status,
                update_modified=False,
            )

        except Exception as e:
            frappe.log_error(
                message=f"Failed to update agreement status for ticket {doc.name}. Error: {e}",
                title="Update SLA Status Failed",
            )
            continue
        frappe.db.commit()  # nosemgrep
