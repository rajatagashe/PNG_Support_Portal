import csv
import io
import json
import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import frappe
from frappe import _
from frappe.desk.form.assign_to import clear as clear_all_assignments
from frappe.utils import (
    add_days,
    cint,
    format_datetime,
    get_datetime,
    get_user_info_for_avatar,
    now_datetime,
    nowdate,
)
from helpdesk.utils import agent_only


@frappe.whitelist()
@agent_only
def sync_support_emails(account_name=None):
    """
    On-demand email synchronization for incoming support mailboxes.
    Retrieves latest unread support emails and processes them into tickets without full page reload.
    """
    filters = {"enable_incoming": 1}
    if account_name:
        filters["name"] = account_name

    accounts = frappe.get_all("Email Account", filters=filters, fields=["name", "email_id", "service"])
    synced_accounts = []
    total_new_emails = 0
    errors = []

    for acc in accounts:
        try:
            email_account = frappe.get_doc("Email Account", acc.name)
            # Inbound mail receive fetches and processes unread messages
            received_mails = email_account.receive() or []
            new_count = len(received_mails)
            total_new_emails += new_count
            synced_accounts.append({
                "account": acc.name,
                "email_id": acc.email_id,
                "new_emails": new_count,
                "status": "success",
            })
        except Exception as e:
            # Secure error logging - never expose passwords or credentials in response
            error_msg = str(e)
            frappe.log_error(
                title=f"Support Email Sync Error: {acc.name}",
                message=frappe.get_traceback(),
            )
            errors.append({
                "account": acc.name,
                "email_id": acc.email_id,
                "status": "failed",
                "message": error_msg[:120],
            })

    return {
        "success": len(errors) == 0 or total_new_emails > 0,
        "total_new_emails": total_new_emails,
        "synced_accounts": synced_accounts,
        "errors": errors,
        "synced_at": now_datetime().isoformat(),
    }


@frappe.whitelist()
@agent_only
def get_support_emails(
    page=1,
    page_length=20,
    cgd=None,
    sender=None,
    team=None,
    user=None,
    status=None,
    date_from=None,
    date_to=None,
    search_text=None,
):
    """
    Retrieve and display incoming support emails with sender details, Message-ID,
    associated CGD organization, and assignment details.
    """
    page = cint(page) or 1
    page_length = min(cint(page_length) or 20, 100)
    offset = (page - 1) * page_length

    conditions = ["1=1"]
    values = {}

    if cgd:
        conditions.append("t.customer = %(cgd)s")
        values["cgd"] = cgd
    if sender:
        conditions.append("(t.raised_by LIKE %(sender)s OR c.sender LIKE %(sender)s)")
        values["sender"] = f"%{sender}%"
    if team:
        conditions.append("t.agent_group = %(team)s")
        values["team"] = team
    if user:
        conditions.append("t._assign LIKE %(user)s")
        values["user"] = f"%{user}%"
    if status:
        conditions.append("t.status = %(status)s")
        values["status"] = status
    if date_from:
        conditions.append("t.creation >= %(date_from)s")
        values["date_from"] = date_from
    if date_to:
        conditions.append("t.creation <= %(date_to)s")
        values["date_to"] = date_to
    if search_text:
        conditions.append("(t.subject LIKE %(search)s OR t.name LIKE %(search)s OR t.raised_by LIKE %(search)s)")
        values["search"] = f"%{search_text}%"

    where_clause = " AND ".join(conditions)

    count_query = f"""
        SELECT COUNT(DISTINCT t.name) as total
        FROM `tabHD Ticket` t
        LEFT JOIN `tabCommunication` c ON c.reference_doctype = 'HD Ticket' AND c.reference_name = t.name
        WHERE {where_clause}
    """
    total_count = frappe.db.sql(count_query, values, as_dict=True)[0].total or 0

    query = f"""
        SELECT 
            t.name as ticket_id,
            t.subject,
            t.raised_by as sender_email,
            t.customer as cgd_id,
            cust.customer_name as cgd_name,
            cust.is_vip as cgd_is_vip,
            t.agent_group as team_id,
            t.agent_group as team_name,
            t._assign as assignees_json,
            t.status,
            t.priority,
            t.creation as received_datetime,
            t.modified as last_modified,
            t.resolution_date,
            c.message_id as original_message_id,
            SUBSTRING(REPLACE(REPLACE(COALESCE(c.content, t.description, ''), '<br>', ' '), '\n', ' '), 1, 150) as preview
        FROM `tabHD Ticket` t
        LEFT JOIN `tabHD Customer` cust ON cust.name = t.customer
        LEFT JOIN `tabCommunication` c ON c.reference_doctype = 'HD Ticket' AND c.reference_name = t.name AND c.sent_or_received = 'Received'
        WHERE {where_clause}
        GROUP BY t.name
        ORDER BY t.creation DESC
        LIMIT %(limit)s OFFSET %(offset)s
    """
    values["limit"] = page_length
    values["offset"] = offset

    raw_rows = frappe.db.sql(query, values, as_dict=True)
    emails = []

    for r in raw_rows:
        # Resolve assignee display
        assignees = []
        if r.assignees_json:
            try:
                assignees = json.loads(r.assignees_json)
            except Exception:
                assignees = []

        assignee_label = ", ".join(assignees) if assignees else "Unassigned"

        emails.append({
            "ticket_id": r.ticket_id,
            "subject": r.subject or _("No Subject"),
            "sender_email": r.sender_email,
            "sender_name": r.sender_email.split("@")[0] if r.sender_email else _("Unknown"),
            "cgd_id": r.cgd_id,
            "cgd_name": r.cgd_name or r.cgd_id or _("Unassigned CGD"),
            "is_vip": bool(r.cgd_is_vip),
            "team_id": r.team_id,
            "team_name": r.team_name or _("Unassigned Team"),
            "assignees": assignees,
            "assignee_label": assignee_label,
            "status": r.status,
            "priority": r.priority,
            "received_datetime": str(r.received_datetime),
            "received_date": format_datetime(r.received_datetime, "yyyy-MM-dd"),
            "received_time": format_datetime(r.received_datetime, "HH:mm:ss"),
            "resolution_date": str(r.resolution_date) if r.resolution_date else None,
            "original_message_id": r.original_message_id or f"msg-{r.ticket_id}@mypng.local",
            "preview": (r.preview or "").strip(),
        })

    return {
        "emails": emails,
        "total_count": total_count,
        "page": page,
        "page_length": page_length,
        "has_more": (offset + len(emails)) < total_count,
    }


@frappe.whitelist()
@agent_only
def get_email_dashboard_analytics(
    view_mode="daily",
    selected_date=None,
    date_from=None,
    date_to=None,
    cgd=None,
    sender=None,
    team=None,
    user=None,
    status=None,
):
    """
    Generate daily, weekly, and monthly support email analytics with period-over-period comparison,
    CGD breakdown, team distribution, and itemized drill-down records.
    """
    now = get_datetime(selected_date) if selected_date else now_datetime()
    today_str = now.strftime("%Y-%m-%d")

    # Establish period boundaries and comparison previous period
    if view_mode == "daily":
        start_curr = f"{today_str} 00:00:00"
        end_curr = f"{today_str} 23:59:59"
        prev_date = add_days(today_str, -1)
        start_prev = f"{prev_date} 00:00:00"
        end_prev = f"{prev_date} 23:59:59"
        period_label = f"Daily ({today_str})"
        comp_label = f"vs Yesterday ({prev_date})"
    elif view_mode == "weekly":
        start_curr = f"{add_days(today_str, -6)} 00:00:00"
        end_curr = f"{today_str} 23:59:59"
        start_prev = f"{add_days(today_str, -13)} 00:00:00"
        end_prev = f"{add_days(today_str, -7)} 23:59:59"
        period_label = "Trailing 7 Days"
        comp_label = "vs Previous 7 Days"
    elif view_mode == "monthly":
        start_curr = f"{add_days(today_str, -29)} 00:00:00"
        end_curr = f"{today_str} 23:59:59"
        start_prev = f"{add_days(today_str, -59)} 00:00:00"
        end_prev = f"{add_days(today_str, -30)} 23:59:59"
        period_label = "Trailing 30 Days"
        comp_label = "vs Previous 30 Days"
    else:  # Custom
        start_curr = date_from or f"{add_days(today_str, -29)} 00:00:00"
        end_curr = date_to or f"{today_str} 23:59:59"
        start_prev = start_curr
        end_prev = end_curr
        period_label = f"{start_curr[:10]} to {end_curr[:10]}"
        comp_label = "Custom Period"

    # Base filter criteria
    def build_query_filter(prefix="t"):
        conds = []
        vals = {}
        if cgd:
            conds.append(f"{prefix}.customer = %(cgd)s")
            vals["cgd"] = cgd
        if sender:
            conds.append(f"{prefix}.raised_by LIKE %(sender)s")
            vals["sender"] = f"%{sender}%"
        if team:
            conds.append(f"{prefix}.agent_group = %(team)s")
            vals["team"] = team
        if user:
            conds.append(f"{prefix}._assign LIKE %(user)s")
            vals["user"] = f"%{user}%"
        if status:
            conds.append(f"{prefix}.status = %(status)s")
            vals["status"] = status
        return conds, vals

    base_conds, base_vals = build_query_filter("t")

    # Helper to calculate KPI counts in a given window
    def get_period_kpis(start_dt, end_dt):
        conds = [f"t.creation >= %(start_dt)s", f"t.creation <= %(end_dt)s"] + base_conds
        vals = {"start_dt": start_dt, "end_dt": end_dt, **base_vals}
        where = " AND ".join(conds)

        sql = f"""
            SELECT 
                COUNT(t.name) as total_received,
                SUM(CASE WHEN (t.agent_group IS NULL OR t.agent_group = '') AND (t._assign IS NULL OR t._assign = '' OR t._assign = '[]') THEN 1 ELSE 0 END) as unassigned,
                SUM(CASE WHEN (t.agent_group IS NOT NULL AND t.agent_group != '') OR (t._assign IS NOT NULL AND t._assign != '' AND t._assign != '[]') THEN 1 ELSE 0 END) as assigned,
                SUM(CASE WHEN t.status IN ('Open', 'Pending', 'Replied') THEN 1 ELSE 0 END) as in_progress,
                SUM(CASE WHEN t.status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) as resolved
            FROM `tabHD Ticket` t
            WHERE {where}
        """
        row = frappe.db.sql(sql, vals, as_dict=True)[0]
        return {
            "total_received": int(row.total_received or 0),
            "unassigned": int(row.unassigned or 0),
            "assigned": int(row.assigned or 0),
            "in_progress": int(row.in_progress or 0),
            "resolved": int(row.resolved or 0),
        }

    current_kpis = get_period_kpis(start_curr, end_curr)
    previous_kpis = get_period_kpis(start_prev, end_prev)

    # Compute deltas
    def compute_delta(curr, prev):
        diff = curr - prev
        pct = round((diff / prev * 100.0), 1) if prev > 0 else (100.0 if curr > 0 else 0.0)
        return {"diff": diff, "pct": pct, "trend": "up" if diff > 0 else ("down" if diff < 0 else "flat")}

    summary_cards = {
        "total_received": {
            "value": current_kpis["total_received"],
            "comparison": compute_delta(current_kpis["total_received"], previous_kpis["total_received"]),
            "label": _("Total Emails Received"),
        },
        "unassigned": {
            "value": current_kpis["unassigned"],
            "comparison": compute_delta(current_kpis["unassigned"], previous_kpis["unassigned"]),
            "label": _("New / Unassigned"),
        },
        "assigned": {
            "value": current_kpis["assigned"],
            "comparison": compute_delta(current_kpis["assigned"], previous_kpis["assigned"]),
            "label": _("Assigned Emails"),
        },
        "in_progress": {
            "value": current_kpis["in_progress"],
            "comparison": compute_delta(current_kpis["in_progress"], previous_kpis["in_progress"]),
            "label": _("Currently In Progress"),
        },
        "resolved": {
            "value": current_kpis["resolved"],
            "comparison": compute_delta(current_kpis["resolved"], previous_kpis["resolved"]),
            "label": _("Resolved / Closed"),
        },
    }

    # CGD Entity Distribution in current period
    cgd_conds = [f"t.creation >= %(start_dt)s", f"t.creation <= %(end_dt)s"] + base_conds
    cgd_vals = {"start_dt": start_curr, "end_dt": end_curr, **base_vals}
    cgd_where = " AND ".join(cgd_conds)

    cgd_query = f"""
        SELECT 
            COALESCE(NULLIF(t.customer, ''), 'Unassigned') as cgd_id,
            COALESCE(NULLIF(cust.customer_name, ''), t.customer, 'Unassigned CGD') as cgd_name,
            COALESCE(cust.is_vip, 0) as is_vip,
            COUNT(t.name) as count,
            SUM(CASE WHEN t.status IN ('Open', 'Pending', 'Replied') THEN 1 ELSE 0 END) as open_count,
            SUM(CASE WHEN t.status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) as resolved_count
        FROM `tabHD Ticket` t
        LEFT JOIN `tabHD Customer` cust ON cust.name = t.customer
        WHERE {cgd_where}
        GROUP BY cgd_id
        ORDER BY count DESC
    """
    cgd_distribution = frappe.db.sql(cgd_query, cgd_vals, as_dict=True)

    # Team & Responsible User Distribution in current period
    team_query = f"""
        SELECT 
            COALESCE(NULLIF(t.agent_group, ''), 'Unassigned') as team_name,
            COUNT(t.name) as count,
            SUM(CASE WHEN t.status IN ('Open', 'Pending', 'Replied') THEN 1 ELSE 0 END) as open_count,
            SUM(CASE WHEN t.status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) as resolved_count
        FROM `tabHD Ticket` t
        WHERE {cgd_where}
        GROUP BY team_name
        ORDER BY count DESC
    """
    team_distribution = frappe.db.sql(team_query, cgd_vals, as_dict=True)

    # Time series trend data
    if view_mode == "daily":
        time_query = f"""
            SELECT 
                DATE_FORMAT(t.creation, '%%H:00') as time_slot,
                COUNT(t.name) as received_count,
                SUM(CASE WHEN t.status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) as resolved_count
            FROM `tabHD Ticket` t
            WHERE {cgd_where}
            GROUP BY time_slot
            ORDER BY time_slot ASC
        """
    else:
        time_query = f"""
            SELECT 
                DATE_FORMAT(t.creation, '%%Y-%%m-%%d') as time_slot,
                COUNT(t.name) as received_count,
                SUM(CASE WHEN t.status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) as resolved_count
            FROM `tabHD Ticket` t
            WHERE {cgd_where}
            GROUP BY time_slot
            ORDER BY time_slot ASC
        """
    time_series = frappe.db.sql(time_query, cgd_vals, as_dict=True)

    return {
        "view_mode": view_mode,
        "period_label": period_label,
        "comparison_label": comp_label,
        "date_range": {"from": start_curr, "to": end_curr},
        "summary": summary_cards,
        "cgd_distribution": cgd_distribution,
        "team_distribution": team_distribution,
        "time_series": time_series,
    }


@frappe.whitelist()
@agent_only
def assign_email_ticket(ticket_id, team=None, agent=None, notes=None, new_status=None):
    """
    Atomically assign or reassign a support email/ticket to a team and/or agent,
    maintaining an auditable history record in HD Assignment Log.
    """
    if not ticket_id:
        frappe.throw(_("Ticket ID is required."))

    frappe.has_permission("HD Ticket", "write", doc=ticket_id, throw=True)
    ticket = frappe.get_doc("HD Ticket", ticket_id)

    if agent and hasattr(agent, "name"):
        agent = agent.name
    if team and hasattr(team, "name"):
        team = team.name

    # Previous states
    from_team = ticket.agent_group
    from_agent = ticket.get_assigned_agent()
    from_status = ticket.status

    # Target states
    to_team = team if team is not None else from_team
    to_agent = agent if agent is not None else from_agent
    to_status = new_status if new_status is not None else from_status

    # Apply team assignment
    if team is not None:
        ticket.agent_group = team

    # Apply agent assignment
    if agent is not None:
        if agent:
            if not frappe.db.exists("HD Agent", agent) and not frappe.db.exists("User", agent):
                frappe.throw(_("Assignee must be a valid User or Agent."))
            ticket.assign_agent(agent)
        else:
            # Clear assignment
            clear_all_assignments("HD Ticket", ticket.name)
            ticket._assign = "[]"

    # Apply status update if specified
    if new_status:
        ticket.status = new_status

    ticket.save()

    # Determine original email / message id
    original_comm = frappe.db.get_value(
        "Communication",
        {"reference_doctype": "HD Ticket", "reference_name": ticket.name, "sent_or_received": "Received"},
        ["message_id", "creation"],
        as_dict=True,
    )
    email_id = original_comm.message_id if original_comm else f"msg-{ticket.name}@mypng.local"
    received_date = original_comm.creation if original_comm else ticket.creation

    # Insert immutable audit record in HD Assignment Log
    assignment_log = frappe.get_doc({
        "doctype": "HD Assignment Log",
        "ticket": ticket.name,
        "email_id": email_id,
        "sender": ticket.raised_by,
        "received_date": received_date,
        "from_team": from_team,
        "to_team": to_team,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "assigned_by": frappe.session.user,
        "assignment_datetime": now_datetime(),
        "from_status": from_status,
        "to_status": to_status,
        "reassignment_notes": notes or "",
    }).insert(ignore_permissions=True)

    # Add visible comment to ticket activity timeline
    timeline_comment = f"Assignment updated by {frappe.session.user}: "
    if from_team != to_team:
        timeline_comment += f"Team: {from_team or 'None'} → {to_team or 'None'}. "
    if from_agent != to_agent:
        timeline_comment += f"Agent: {from_agent or 'None'} → {to_agent or 'None'}. "
    if from_status != to_status:
        timeline_comment += f"Status: {from_status} → {to_status}. "
    if notes:
        timeline_comment += f"Note: {notes}"

    ticket.add_comment("Comment", timeline_comment.strip(), comment_email=frappe.session.user)

    return {
        "success": True,
        "ticket_id": ticket.name,
        "assignment_log": assignment_log.name,
        "team": to_team,
        "agent": to_agent,
        "status": to_status,
    }


@frappe.whitelist()
@agent_only
def get_ticket_assignment_history(ticket_id):
    """
    Retrieve the complete auditable history of assignments and reassignments for a ticket.
    """
    if not ticket_id:
        return []

    logs = frappe.get_all(
        "HD Assignment Log",
        filters={"ticket": ticket_id},
        fields=[
            "name",
            "ticket",
            "action_type",
            "email_id",
            "sender",
            "received_date",
            "from_team",
            "to_team",
            "from_agent",
            "to_agent",
            "assigned_by",
            "assignment_datetime",
            "from_status",
            "to_status",
            "reassignment_notes",
        ],
        order_by="assignment_datetime DESC",
    )

    for l in logs:
        l["formatted_datetime"] = format_datetime(l.assignment_datetime, "yyyy-MM-dd HH:mm:ss")
        l["assigned_by_name"] = frappe.db.get_value("User", l.assigned_by, "full_name") or l.assigned_by
        l["to_agent_name"] = (
            frappe.db.get_value("User", l.to_agent, "full_name") or l.to_agent if l.to_agent else _("Unassigned")
        )
        l["from_agent_name"] = (
            frappe.db.get_value("User", l.from_agent, "full_name") or l.from_agent if l.from_agent else _("None")
        )

    return logs


@frappe.whitelist()
@agent_only
def export_email_report_xlsx(
    date_from=None,
    date_to=None,
    cgd=None,
    sender=None,
    team=None,
    user=None,
    status=None,
):
    """
    Export detailed support email and assignment audit reports as a formatted multi-sheet Excel (.xlsx) file:
    - Sheet 1: Filtered Support Emails & Tickets
    - Sheet 2: Auditable Assignment & Reassignment History
    """
    # Fetch filtered tickets
    data = get_support_emails(
        page=1,
        page_length=5000,
        cgd=cgd,
        sender=sender,
        team=team,
        user=user,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    emails = data["emails"]
    ticket_ids = [e["ticket_id"] for e in emails]

    # Fetch corresponding assignment history
    assignment_logs = []
    if ticket_ids:
        assignment_logs = frappe.get_all(
            "HD Assignment Log",
            filters={"ticket": ["in", ticket_ids]},
            fields=[
                "ticket",
                "action_type",
                "email_id",
                "sender",
                "from_team",
                "to_team",
                "from_agent",
                "to_agent",
                "assigned_by",
                "assignment_datetime",
                "from_status",
                "to_status",
                "reassignment_notes",
            ],
            order_by="assignment_datetime DESC",
        )

    # Initialize workbook
    wb = openpyxl.Workbook()
    # Sheet 1: Emails
    ws_emails = wb.active
    ws_emails.title = "Support Emails & Tickets"

    header_font = Font(name="Arial", size=11, bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="EA580C", end_color="EA580C", fill_type="solid")
    header_align = Alignment(horizontal="center", vertical="center", wrap_text=True)

    email_headers = [
        "Ticket ID",
        "Original Message ID",
        "Subject",
        "Sender Name",
        "Sender Email",
        "Received Date",
        "Received Time",
        "CGD Organization",
        "Assigned Team",
        "Assigned Agent",
        "Current Status",
        "Resolution Date",
    ]
    ws_emails.append(email_headers)

    for col_num in range(1, len(email_headers) + 1):
        cell = ws_emails.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = header_align

    for em in emails:
        ws_emails.append([
            em["ticket_id"],
            em["original_message_id"],
            em["subject"],
            em["sender_name"],
            em["sender_email"],
            em["received_date"],
            em["received_time"],
            em["cgd_name"],
            em["team_name"],
            em["assignee_label"],
            em["status"],
            em["resolution_date"] or "Pending",
        ])

    # Sheet 2: Assignment History
    ws_history = wb.create_sheet(title="Assignment Audit History")
    history_fill = PatternFill(start_color="374151", end_color="374151", fill_type="solid")

    history_headers = [
        "Ticket ID",
        "Action Type",
        "Sender",
        "From Team",
        "To Team",
        "From Agent",
        "To Agent",
        "Assigned By",
        "Assignment Timestamp",
        "From Status",
        "To Status",
        "Reassignment Reason / Notes",
    ]
    ws_history.append(history_headers)

    for col_num in range(1, len(history_headers) + 1):
        cell = ws_history.cell(row=1, column=col_num)
        cell.font = header_font
        cell.fill = history_fill
        cell.alignment = header_align

    for log in assignment_logs:
        ws_history.append([
            log.ticket,
            log.action_type or "Assignment",
            log.sender or "",
            log.from_team or "None",
            log.to_team or "None",
            log.from_agent or "None",
            log.to_agent or "None",
            log.assigned_by,
            str(log.assignment_datetime),
            log.from_status or "",
            log.to_status or "",
            log.reassignment_notes or "",
        ])

    # Auto-fit column widths
    for sheet in [ws_emails, ws_history]:
        for col in sheet.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            col_letter = get_column_letter(col[0].column)
            sheet.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 40)

    # Save to memory stream
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    xlsx_bytes = output.getvalue()

    filename = f"Support_Email_Report_{now_datetime().strftime('%Y%m%d_%H%M%S')}.xlsx"

    if hasattr(frappe, "response"):
        frappe.response["filename"] = filename
        frappe.response["filecontent"] = xlsx_bytes
        frappe.response["type"] = "binary"

    import base64
    b64_content = base64.b64encode(xlsx_bytes).decode("utf-8")

    return {
        "filename": filename,
        "base64_content": b64_content,
        "total_emails": len(emails),
        "total_audit_records": len(assignment_logs),
    }


@frappe.whitelist()
@agent_only
def export_email_report_csv(
    date_from=None,
    date_to=None,
    cgd=None,
    sender=None,
    team=None,
    user=None,
    status=None,
):
    """
    Export detailed support email and ticket report as itemized CSV.
    """
    data = get_support_emails(
        page=1,
        page_length=5000,
        cgd=cgd,
        sender=sender,
        team=team,
        user=user,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )
    emails = data["emails"]

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Ticket ID",
        "Original Message ID",
        "Subject",
        "Sender Name",
        "Sender Email",
        "Received Date",
        "Received Time",
        "CGD Organization",
        "Assigned Team",
        "Assigned Agent",
        "Status",
        "Resolution Date",
    ])

    for em in emails:
        writer.writerow([
            em["ticket_id"],
            em["original_message_id"],
            em["subject"],
            em["sender_name"],
            em["sender_email"],
            em["received_date"],
            em["received_time"],
            em["cgd_name"],
            em["team_name"],
            em["assignee_label"],
            em["status"],
            em["resolution_date"] or "Pending",
        ])

    csv_content = output.getvalue()
    filename = f"Support_Email_Report_{now_datetime().strftime('%Y%m%d_%H%M%S')}.csv"

    if hasattr(frappe, "response"):
        frappe.response["result"] = csv_content
        frappe.response["type"] = "csv"
        frappe.response["doctype"] = "support_email_report"

    return {
        "csv_content": csv_content,
        "filename": filename,
        "total_rows": len(emails),
    }


def scheduled_sync_support_emails():
    """
    Background scheduler entrypoint to synchronize incoming support emails.
    Automatically polls active support email accounts and syncs new emails.
    """
    frappe.logger("helpdesk").info("[Scheduler] Starting scheduled sync of support emails.")
    try:
        res = sync_support_emails()
        frappe.logger("helpdesk").info(f"[Scheduler] Completed scheduled sync: {res}")
        return res
    except Exception as e:
        frappe.log_error(f"Failed scheduled support email sync: {str(e)}", "Support Email Scheduled Sync")
        return {"success": False, "error": str(e)}

