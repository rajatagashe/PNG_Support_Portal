import frappe
from frappe import _
from frappe.utils import validate_email_address
from frappe.utils.html_utils import clean_html
from helpdesk.api.guest_ticket import submit_guest_ticket


@frappe.whitelist(allow_guest=True)
def get_widget_config():
    """Return theme branding, titles, and public configuration for the embeddable widget."""
    app_title = "PNG Helpdesk Support"
    if frappe.db.exists("DocType", "HD Settings"):
        app_title = frappe.db.get_single_value("HD Settings", "brand_name") or app_title

    ticket_types = frappe.get_all("HD Ticket Type", fields=["name"])

    return {
        "title": app_title,
        "primary_color": "#ea580c",
        "secondary_color": "#fed7aa",
        "ticket_types": [t["name"] for t in ticket_types],
        "powered_by": "PNG Helpdesk",
    }


@frappe.whitelist(allow_guest=True)
def search_widget_articles(query):
    """Fast public search across published knowledge base articles for the embeddable widget."""
    if not query or len(query.strip()) < 2:
        return []

    q = f"%{query.strip()}%"
    articles = frappe.db.sql(
        """
        SELECT name, title, category, content, modified
        FROM `tabHD Article`
        WHERE status = 'Published' AND (title LIKE %(q)s OR content LIKE %(q)s)
        ORDER BY modified DESC
        LIMIT 6
        """,
        {"q": q},
        as_dict=True,
    )

    results = []
    for art in articles:
        category_name = None
        if art.category:
            category_name = frappe.db.get_value("HD Article Category", art.category, "category_name")

        raw_content = art.content or ""
        clean_excerpt = clean_html(raw_content)[:180]

        results.append({
            "name": art.name,
            "title": art.title,
            "category": category_name or art.category,
            "excerpt": clean_excerpt,
        })

    return results


@frappe.whitelist(allow_guest=True)
def submit_widget_ticket(subject, description, email, name=None):
    """Ingest a support query from an external embeddable widget with contact & CGD auto-mapping."""
    if not subject or not subject.strip():
        frappe.throw(_("Subject is required."))
    if not description or not description.strip():
        frappe.throw(_("Description is required."))
    if not email or not validate_email_address(email.strip()):
        frappe.throw(_("A valid email address is required."))

    res = submit_guest_ticket(
        subject=subject.strip(),
        description=description.strip(),
        email=email.strip().lower(),
        full_name=name.strip() if name else None,
    )

    return {
        "success": True,
        "ticket_name": res["ticket"],
        "guest_token": res["guest_token"],
        "tracking_url": res["tracking_url"],
        "message": res["message"],
    }
