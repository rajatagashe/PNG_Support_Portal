import secrets
import frappe
from frappe import _
from frappe.utils import now_datetime, get_url
from helpdesk.utils import agent_only


def create_or_get_csat_survey(ticket_name, agent=None):
    """Create or return an existing HD CSAT Survey for a ticket."""
    existing = frappe.db.get_value(
        "HD CSAT Survey",
        {"ticket": ticket_name},
        ["name", "survey_token", "status", "rating"],
        as_dict=True,
    )
    if existing:
        return frappe.get_doc("HD CSAT Survey", existing.name)

    ticket = frappe.get_doc("HD Ticket", ticket_name)
    survey = frappe.new_doc("HD CSAT Survey")
    survey.ticket = ticket.name
    survey.customer = ticket.get("customer")
    survey.contact = ticket.get("contact")

    agent_id = agent or ticket.get("agent")
    if not agent_id and hasattr(ticket, "get_assigned_agent"):
        agent_id = ticket.get_assigned_agent()
    survey.agent = agent_id

    survey.status = "Pending"
    survey.survey_token = secrets.token_urlsafe(32)
    survey.insert(ignore_permissions=True)
    return survey


def trigger_resolution_csat(ticket):
    """Trigger CSAT survey creation and dispatch email when a ticket is resolved."""
    if ticket.flags.in_csat_trigger:
        return
    ticket.flags.in_csat_trigger = True

    try:
        survey = create_or_get_csat_survey(ticket.name)
        if survey.status == "Submitted":
            return

        # Build notification recipient
        recipient_email = None
        if ticket.contact:
            recipient_email = frappe.db.get_value("Contact", ticket.contact, "email_id")
        if not recipient_email and ticket.raised_by:
            recipient_email = ticket.raised_by

        if recipient_email:
            send_csat_email(survey, ticket, recipient_email)
    except Exception as e:
        frappe.log_error(f"Error triggering CSAT for {ticket.name}: {str(e)}", "CSAT Trigger Error")


def send_csat_email(survey, ticket, recipient_email):
    """Send satisfaction survey email with one-click rating links."""
    base_url = get_url()
    rating_links = "".join([
        f'<a href="{base_url}/api/method/helpdesk.api.csat.record_rating_link?token={survey.survey_token}&rating={r}" '
        f'style="display:inline-block;padding:8px 16px;margin:4px;background:#ea580c;color:#ffffff;text-decoration:none;border-radius:4px;font-weight:bold;">'
        f'{r} {"★" * r}</a> '
        for r in range(1, 6)
    ])

    subject = f"How would you rate our support for Ticket #{ticket.name}?"
    message = f"""
    <div style="font-family: sans-serif; max-width: 600px; margin: auto; padding: 20px; border: 1px solid #fed7aa; border-radius: 8px;">
        <h2 style="color: #ea580c;">We'd love your feedback!</h2>
        <p>Your ticket <strong>#{ticket.name}: {ticket.subject}</strong> was recently marked as resolved.</p>
        <p>Please take a moment to rate your experience with our support team:</p>
        <div style="text-align: center; margin: 24px 0;">
            {rating_links}
        </div>
        <p style="color: #666; font-size: 13px;">1 = Poor, 5 = Excellent</p>
    </div>
    """

    frappe.sendmail(
        recipients=[recipient_email],
        subject=subject,
        message=message,
        reference_doctype="HD Ticket",
        reference_name=ticket.name,
        now=True,
    )


@frappe.whitelist(allow_guest=True)
def get_csat_survey(survey_token):
    """Retrieve public survey context for web submission."""
    survey = frappe.db.get_value(
        "HD CSAT Survey",
        {"survey_token": survey_token},
        ["name", "ticket", "customer", "agent", "status", "rating", "feedback"],
        as_dict=True,
    )
    if not survey:
        frappe.throw(_("Invalid or expired survey token."), frappe.DoesNotExistError)

    ticket_subject = frappe.db.get_value("HD Ticket", survey.ticket, "subject")
    agent_name = frappe.db.get_value("HD Agent", survey.agent, "agent_name") if survey.agent else None
    customer_name = frappe.db.get_value("HD Customer", survey.customer, "customer_name") if survey.customer else None

    return {
        "name": survey.name,
        "ticket": survey.ticket,
        "ticket_subject": ticket_subject,
        "agent": survey.agent,
        "agent_name": agent_name,
        "customer": survey.customer,
        "customer_name": customer_name,
        "status": survey.status,
        "rating": survey.rating,
        "feedback": survey.feedback,
    }


@frappe.whitelist(allow_guest=True)
def submit_csat_survey(survey_token, rating, feedback=None):
    """Submit customer satisfaction rating and optional feedback."""
    survey_name = frappe.db.get_value("HD CSAT Survey", {"survey_token": survey_token}, "name")
    if not survey_name:
        frappe.throw(_("Invalid or expired survey token."), frappe.DoesNotExistError)

    try:
        rating_int = int(rating)
        if rating_int < 1 or rating_int > 5:
            frappe.throw(_("Rating must be an integer between 1 and 5."))
    except (ValueError, TypeError):
        frappe.throw(_("Invalid rating value."))

    survey = frappe.get_doc("HD CSAT Survey", survey_name)
    survey.rating = rating_int
    survey.feedback = feedback or ""
    survey.status = "Submitted"
    survey.submitted_at = now_datetime()
    survey.ip_address = frappe.local.request_ip if hasattr(frappe.local, "request_ip") else ""
    survey.save(ignore_permissions=True)

    # Sync back to HD Ticket feedback fields for dashboard/analytics compatibility
    if survey.ticket and frappe.db.exists("HD Ticket", survey.ticket):
        ticket = frappe.get_doc("HD Ticket", survey.ticket)
        # Frappe UI Rating field is normalized 0.0 to 1.0 (rating / 5)
        ticket.feedback_rating = float(rating_int) / 5.0
        if feedback:
            ticket.feedback_extra = feedback
        ticket.flags.in_csat_trigger = True
        ticket.save(ignore_permissions=True)

    return {
        "success": True,
        "message": _("Thank you for your feedback!"),
        "rating": rating_int,
    }


@frappe.whitelist(allow_guest=True)
def record_rating_link(token, rating):
    """One-click rating recording directly from email links."""
    result = submit_csat_survey(survey_token=token, rating=rating)
    rating_val = result.get("rating", rating)
    html_response = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Thank You - Feedback Received</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #fffaf5; display: flex; justify-content: center; align-items: center; min-height: 100vh; margin: 0; }}
            .card {{ background: #ffffff; border: 1px solid #fed7aa; border-radius: 12px; padding: 32px; max-width: 440px; text-align: center; box-shadow: 0 4px 12px rgba(234, 88, 12, 0.1); }}
            h1 {{ color: #ea580c; margin-top: 0; font-size: 24px; }}
            .stars {{ font-size: 32px; color: #ea580c; margin: 16px 0; }}
            p {{ color: #431407; line-height: 1.5; }}
        </style>
    </head>
    <body>
        <div class="card">
            <h1>Thank You!</h1>
            <div class="stars">{"★" * int(rating_val)}</div>
            <p>Your feedback ({rating_val} / 5) has been recorded successfully.</p>
            <p>We appreciate your response and are committed to serving you better.</p>
        </div>
    </body>
    </html>
    """
    frappe.response["type"] = "page"
    frappe.response["page_name"] = "feedback_thanks"
    frappe.respond_as_web_page(_("Feedback Received"), html_response)


@frappe.whitelist()
@agent_only
def get_csat_leaderboard(from_date=None, to_date=None, customer=None):
    """Compute agent & team satisfaction scorecard and ratings breakdown."""
    conditions = ["status = 'Submitted'"]
    values = {}

    if from_date:
        conditions.append("submitted_at >= %(from_date)s")
        values["from_date"] = from_date
    if to_date:
        conditions.append("submitted_at <= %(to_date)s")
        values["to_date"] = to_date
    if customer:
        conditions.append("customer = %(customer)s")
        values["customer"] = customer

    where_clause = " AND ".join(conditions)

    # Agent breakdown
    agent_rows = frappe.db.sql(
        f"""
        SELECT 
            agent,
            COUNT(name) as total_surveys,
            AVG(rating) as avg_rating,
            SUM(CASE WHEN rating >= 4 THEN 1 ELSE 0 END) as positive_surveys,
            SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) as stars_5,
            SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) as stars_4,
            SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) as stars_3,
            SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) as stars_2,
            SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) as stars_1
        FROM `tabHD CSAT Survey`
        WHERE {where_clause} AND agent IS NOT NULL AND agent != ''
        GROUP BY agent
        ORDER BY avg_rating DESC, total_surveys DESC
        """,
        values,
        as_dict=True,
    )

    leaderboard = []
    for r in agent_rows:
        agent_name = frappe.db.get_value("HD Agent", r.agent, "agent_name") or r.agent
        total = int(r.total_surveys)
        positive = int(r.positive_surveys)
        csat_pct = round((positive / total * 100.0), 1) if total > 0 else 0.0

        leaderboard.append({
            "agent": r.agent,
            "agent_name": agent_name,
            "total_surveys": total,
            "avg_rating": round(float(r.avg_rating), 2) if r.avg_rating else 0.0,
            "csat_percentage": csat_pct,
            "stars_5": int(r.stars_5),
            "stars_4": int(r.stars_4),
            "stars_3": int(r.stars_3),
            "stars_2": int(r.stars_2),
            "stars_1": int(r.stars_1),
        })

    # Overall Summary
    total_surveys = sum(item["total_surveys"] for item in leaderboard)
    overall_avg = round(sum(item["avg_rating"] * item["total_surveys"] for item in leaderboard) / total_surveys, 2) if total_surveys > 0 else 0.0
    overall_positive = sum(item["stars_5"] + item["stars_4"] for item in leaderboard)
    overall_csat_pct = round((overall_positive / total_surveys * 100.0), 1) if total_surveys > 0 else 0.0

    return {
        "leaderboard": leaderboard,
        "summary": {
            "total_surveys": total_surveys,
            "avg_rating": overall_avg,
            "csat_percentage": overall_csat_pct,
            "total_agents": len(leaderboard),
        },
    }
