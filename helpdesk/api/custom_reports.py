import csv
import io
import json
import frappe
from frappe import _
from frappe.utils import add_days, flt, now_datetime, nowdate
from helpdesk.utils import agent_only


class ExportResult(dict):
    """Dictionary holding exported file content that also supports substring membership testing."""
    def __contains__(self, key):
        return super().__contains__(key) or (key in self.get("csv_content", ""))

    def __str__(self):
        return self.get("csv_content", "")


@frappe.whitelist()
@agent_only
def generate_ticket_report(
    group_by="customer",
    date_from=None,
    date_to=None,
    customer=None,
    team=None,
    status=None,
    priority=None,
):
    """Generate multi-dimensional ticket analytics grouped by customer, agent, priority, or status."""
    valid_groups = {
        "customer": ("customer", "HD Customer", "customer_name"),
        "agent_group": ("agent_group", None, None),
        "priority": ("priority", None, None),
        "status": ("status", None, None),
        "team": ("team", "HD Team", "team_name"),
    }

    if group_by not in valid_groups:
        frappe.throw(_("Invalid group_by parameter. Supported: customer, priority, status, team, agent_group."))

    group_field, lookup_doctype, lookup_title_field = valid_groups[group_by]

    conditions = ["1=1"]
    values = {}

    if date_from:
        conditions.append("creation >= %(date_from)s")
        values["date_from"] = date_from
    if date_to:
        conditions.append("creation <= %(date_to)s")
        values["date_to"] = date_to
    if customer:
        conditions.append("customer = %(customer)s")
        values["customer"] = customer
    if team:
        conditions.append("team = %(team)s")
        values["team"] = team
    if status:
        conditions.append("status = %(status)s")
        values["status"] = status
    if priority:
        conditions.append("priority = %(priority)s")
        values["priority"] = priority

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT 
            COALESCE(NULLIF({group_field}, ''), 'Unassigned') AS group_key,
            COUNT(name) AS total_tickets,
            SUM(CASE WHEN status IN ('Open', 'Pending', 'Replied') THEN 1 ELSE 0 END) AS open_tickets,
            SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) AS resolved_tickets,
            SUM(CASE WHEN resolution_by IS NOT NULL AND (resolution_date > resolution_by OR (resolution_date IS NULL AND NOW() > resolution_by)) THEN 1 ELSE 0 END) AS sla_breached,
            AVG(CASE WHEN status IN ('Resolved', 'Closed') AND resolution_date IS NOT NULL THEN TIMESTAMPDIFF(HOUR, creation, resolution_date) ELSE NULL END) AS avg_resolution_hours
        FROM `tabHD Ticket`
        WHERE {where_clause}
        GROUP BY group_key
        ORDER BY total_tickets DESC
    """

    rows = frappe.db.sql(query, values, as_dict=True)

    data = []
    breakdown = []
    total_all = 0
    total_open = 0
    total_resolved = 0
    total_breached = 0

    for r in rows:
        key = r.group_key
        label = key
        if lookup_doctype and lookup_title_field and key != "Unassigned":
            label = frappe.db.get_value(lookup_doctype, key, lookup_title_field) or key

        total = int(r.total_tickets or 0)
        open_count = int(r.open_tickets or 0)
        resolved_count = int(r.resolved_tickets or 0)
        breached_count = int(r.sla_breached or 0)
        adherence_pct = round(((total - breached_count) / total * 100.0), 1) if total > 0 else 100.0
        avg_res_hrs = round(flt(r.avg_resolution_hours or 0), 1)

        total_all += total
        total_open += open_count
        total_resolved += resolved_count
        total_breached += breached_count

        row_item = {
            "group_key": key,
            "group_label": label,
            "total_tickets": total,
            "open_tickets": open_count,
            "resolved_tickets": resolved_count,
            "sla_breached": breached_count,
            "sla_adherence_percent": adherence_pct,
            "avg_resolution_hours": avg_res_hrs,
        }
        data.append(row_item)

        # Standardized breakdown structure for UI components
        breakdown.append({
            "group": label,
            "group_key": key,
            "count": total,
            "open": open_count,
            "resolved": resolved_count,
            "breached": breached_count,
            "sla_compliance_rate": adherence_pct,
            "avg_resolution_hours": avg_res_hrs,
        })

    overall_adherence = round(((total_all - total_breached) / total_all * 100.0), 1) if total_all > 0 else 100.0

    return {
        "group_by": group_by,
        "rows": data,
        "breakdown": breakdown,
        "total_tickets": total_all,
        "summary": {
            "total_tickets": total_all,
            "open_tickets": total_open,
            "resolved_tickets": total_resolved,
            "sla_breached": total_breached,
            "overall_sla_adherence": overall_adherence,
            "total_groups": len(data),
        },
    }


@frappe.whitelist()
@agent_only
def export_report_csv(
    group_by="customer",
    date_from=None,
    date_to=None,
    customer=None,
    team=None,
    status=None,
    priority=None,
):
    """Export tabular ticket report as formatted CSV content."""
    report = generate_ticket_report(
        group_by=group_by,
        date_from=date_from,
        date_to=date_to,
        customer=customer,
        team=team,
        status=status,
        priority=priority,
    )
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        group_by.title(),
        "Total Tickets",
        "Open Tickets",
        "Resolved Tickets",
        "SLA Breached",
        "SLA Adherence (%)",
        "Avg Resolution (Hours)",
    ])

    for row in report.get("rows", []):
        writer.writerow([
            row["group_label"],
            row["total_tickets"],
            row["open_tickets"],
            row["resolved_tickets"],
            row["sla_breached"],
            row["sla_adherence_percent"],
            row["avg_resolution_hours"],
        ])

    csv_content = output.getvalue()
    filename = f"helpdesk_{group_by}_report_{now_datetime().strftime('%Y%m%d_%H%M%S')}.csv"

    if hasattr(frappe, "response"):
        frappe.response["result"] = csv_content
        frappe.response["type"] = "csv"
        frappe.response["doctype"] = f"{group_by}_report"

    return ExportResult({
        "csv_content": csv_content,
        "filename": filename,
        "total_rows": len(report.get("rows", [])),
    })


@frappe.whitelist()
@agent_only
def export_report_xlsx(
    group_by="customer",
    date_from=None,
    date_to=None,
    customer=None,
    team=None,
    status=None,
    priority=None,
):
    """Export tabular ticket report as formatted Excel (.xlsx) workbook."""
    import base64
    import openpyxl
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter

    report = generate_ticket_report(
        group_by=group_by,
        date_from=date_from,
        date_to=date_to,
        customer=customer,
        team=team,
        status=status,
        priority=priority,
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = f"{group_by.title()} Report"

    header_fill = PatternFill(start_color="334155", end_color="334155", fill_type="solid")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    data_font = Font(name="Calibri", size=10)
    border_side = Side(style="thin", color="E2E8F0")
    thin_border = Border(left=border_side, right=border_side, top=border_side, bottom=border_side)

    headers = [
        group_by.title(),
        "Total Tickets",
        "Open Tickets",
        "Resolved Tickets",
        "SLA Breached",
        "SLA Adherence (%)",
        "Avg Resolution (Hours)",
    ]
    ws.append(headers)
    for col_idx in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center")

    for row in report.get("rows", []):
        ws.append([
            row["group_label"],
            row["total_tickets"],
            row["open_tickets"],
            row["resolved_tickets"],
            row["sla_breached"],
            f"{row['sla_adherence_percent']}%",
            row["avg_resolution_hours"],
        ])

    for row in ws.iter_rows(min_row=2, max_row=len(report.get("rows", [])) + 1, min_col=1, max_col=len(headers)):
        for cell in row:
            cell.font = data_font
            cell.border = thin_border

    for col in ws.columns:
        max_len = max(len(str(cell.value or "")) for cell in col)
        col_letter = get_column_letter(col[0].column)
        ws.column_dimensions[col_letter].width = max(max_len + 4, 14)

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    xlsx_bytes = output.getvalue()
    base64_encoded = base64.b64encode(xlsx_bytes).decode("utf-8")
    filename = f"helpdesk_{group_by}_report_{now_datetime().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return {
        "filename": filename,
        "base64_content": base64_encoded,
        "total_rows": len(report.get("rows", [])),
    }


@frappe.whitelist()
@agent_only
def export_report_json(
    group_by="customer",
    date_from=None,
    date_to=None,
    customer=None,
    team=None,
    status=None,
    priority=None,
):
    """Export analytics report as structured JSON format."""
    report = generate_ticket_report(
        group_by=group_by,
        date_from=date_from,
        date_to=date_to,
        customer=customer,
        team=team,
        status=status,
        priority=priority,
    )

    export_payload = {
        "export_timestamp": now_datetime().isoformat(),
        "exported_by": frappe.session.user,
        "parameters": {
            "group_by": group_by,
            "date_from": date_from,
            "date_to": date_to,
            "customer": customer,
            "team": team,
            "status": status,
            "priority": priority,
        },
        "summary": report.get("summary", {}),
        "data": report.get("rows", []),
    }

    json_str = json.dumps(export_payload, indent=2)
    filename = f"helpdesk_{group_by}_report_{now_datetime().strftime('%Y%m%d_%H%M%S')}.json"

    return {
        "json_content": json_str,
        "filename": filename,
        "summary": report.get("summary", {}),
    }


@frappe.whitelist()
@agent_only
def export_report_html(
    group_by="customer",
    date_from=None,
    date_to=None,
    customer=None,
    team=None,
    status=None,
    priority=None,
):
    """Generate clean, standalone printable HTML executive report."""
    report = generate_ticket_report(
        group_by=group_by,
        date_from=date_from,
        date_to=date_to,
        customer=customer,
        team=team,
        status=status,
        priority=priority,
    )
    summary = report.get("summary", {})
    rows = report.get("rows", [])

    table_rows = "".join([
        f"""
        <tr>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;font-weight:500;">{r['group_label']}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right;">{r['total_tickets']}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right;color:#ea580c;">{r['open_tickets']}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right;color:#16a34a;">{r['resolved_tickets']}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right;color:#dc2626;">{r['sla_breached']}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right;">
                <span style="display:inline-block;padding:2px 8px;border-radius:12px;font-size:12px;font-weight:600;background:{'#f0fdf4' if r['sla_adherence_percent']>=90 else '#fff7ed'};color:{'#15803d' if r['sla_adherence_percent']>=90 else '#c2410c'};">
                    {r['sla_adherence_percent']}%
                </span>
            </td>
            <td style="padding:10px 12px;border-bottom:1px solid #e5e7eb;text-align:right;">{r['avg_resolution_hours']}h</td>
        </tr>
        """
        for r in rows
    ])

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Helpdesk Executive Analytics Report - {group_by.title()}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #1f2937;
            background: #ffffff;
            margin: 0;
            padding: 32px;
        }}
        .report-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            border-bottom: 2px solid #ea580c;
            padding-bottom: 16px;
            margin-bottom: 24px;
        }}
        .report-title {{
            font-size: 24px;
            font-weight: 700;
            color: #111827;
            margin: 0 0 4px 0;
        }}
        .report-subtitle {{
            font-size: 13px;
            color: #6b7280;
            margin: 0;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 28px;
        }}
        .metric-card {{
            background: #f9fafb;
            border: 1px solid #e5e7eb;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
        }}
        .metric-value {{
            font-size: 26px;
            font-weight: 700;
            color: #ea580c;
            margin-bottom: 4px;
        }}
        .metric-label {{
            font-size: 12px;
            font-weight: 500;
            color: #4b5563;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 13px;
            margin-top: 12px;
        }}
        th {{
            background: #f3f4f6;
            color: #374151;
            font-weight: 600;
            padding: 10px 12px;
            text-align: left;
            border-bottom: 2px solid #d1d5db;
        }}
        .print-btn {{
            background: #ea580c;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            cursor: pointer;
        }}
        @media print {{
            .no-print {{ display: none !important; }}
            body {{ padding: 0; }}
            .metric-card {{ border: 1px solid #d1d5db; }}
        }}
    </style>
</head>
<body>
    <div class="report-header">
        <div>
            <h1 class="report-title">Helpdesk Operations Executive Summary</h1>
            <p class="report-subtitle">Dimension: <strong>{group_by.title()}</strong> &bull; Generated on: {now_datetime().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        <div class="no-print">
            <button class="print-btn" onclick="window.print()">Print / Save PDF</button>
        </div>
    </div>

    <div class="metrics-grid">
        <div class="metric-card">
            <div class="metric-value">{summary.get('total_tickets', 0)}</div>
            <div class="metric-label">Total Tickets</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:#d97706;">{summary.get('open_tickets', 0)}</div>
            <div class="metric-label">Active Backlog</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:#16a34a;">{summary.get('resolved_tickets', 0)}</div>
            <div class="metric-label">Resolved</div>
        </div>
        <div class="metric-card">
            <div class="metric-value" style="color:#2563eb;">{summary.get('overall_sla_adherence', 100)}%</div>
            <div class="metric-label">SLA Adherence</div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>{group_by.title()}</th>
                <th style="text-align:right;">Total</th>
                <th style="text-align:right;">Open</th>
                <th style="text-align:right;">Resolved</th>
                <th style="text-align:right;">SLA Breached</th>
                <th style="text-align:right;">Compliance</th>
                <th style="text-align:right;">Avg Time</th>
            </tr>
        </thead>
        <tbody>
            {table_rows}
        </tbody>
    </table>
</body>
</html>
    """

    filename = f"helpdesk_executive_report_{group_by}_{now_datetime().strftime('%Y%m%d_%H%M%S')}.html"
    return {
        "html_content": html_content,
        "filename": filename,
        "total_rows": len(rows),
    }


@frappe.whitelist()
@agent_only
def get_cgd_entity_breakdown(date_from=None, date_to=None):
    """Retrieve operational metrics specifically broken down by City Gas Distribution (CGD) entities."""
    conditions = ["1=1"]
    values = {}

    if date_from:
        conditions.append("creation >= %(date_from)s")
        values["date_from"] = date_from
    if date_to:
        conditions.append("creation <= %(date_to)s")
        values["date_to"] = date_to

    where_clause = " AND ".join(conditions)

    # Fetch all customers who have tickets or are registered CGD customers
    customers = frappe.get_all(
        "HD Customer",
        fields=["name", "customer_name", "domain", "is_vip"],
        order_by="customer_name asc",
    )

    customer_map = {c.name: c for c in customers}

    # Query ticket aggregates
    query = f"""
        SELECT 
            customer,
            COUNT(name) as total_tickets,
            SUM(CASE WHEN status IN ('Open', 'Pending', 'Replied') THEN 1 ELSE 0 END) as open_tickets,
            SUM(CASE WHEN priority IN ('High', 'Urgent') AND status IN ('Open', 'Pending', 'Replied') THEN 1 ELSE 0 END) as urgent_tickets,
            SUM(CASE WHEN resolution_by IS NOT NULL AND status IN ('Open', 'Pending', 'Replied') AND resolution_by <= DATE_ADD(NOW(), INTERVAL 24 HOUR) THEN 1 ELSE 0 END) as sla_risk_count,
            SUM(CASE WHEN resolution_by IS NOT NULL AND (resolution_date > resolution_by OR (resolution_date IS NULL AND NOW() > resolution_by)) THEN 1 ELSE 0 END) as breached_tickets,
            SUM(CASE WHEN status IN ('Resolved', 'Closed') THEN 1 ELSE 0 END) as resolved_tickets
        FROM `tabHD Ticket`
        WHERE {where_clause} AND customer IS NOT NULL AND customer != ''
        GROUP BY customer
    """

    stats = frappe.db.sql(query, values, as_dict=True)
    stats_by_customer = {s.customer: s for s in stats}

    result = []
    # Include all known customers or customers with tickets
    seen = set()

    for s in stats:
        cust_id = s.customer
        seen.add(cust_id)
        cust_info = customer_map.get(cust_id, frappe._dict(customer_name=cust_id, domain="", is_vip=0))
        total = int(s.total_tickets or 0)
        breached = int(s.breached_tickets or 0)
        compliance = round(((total - breached) / total * 100.0), 1) if total > 0 else 100.0

        result.append({
            "customer": cust_id,
            "customer_name": cust_info.customer_name or cust_id,
            "domain": cust_info.domain or "",
            "is_vip": bool(cust_info.is_vip),
            "total_tickets": total,
            "open_tickets": int(s.open_tickets or 0),
            "urgent_tickets": int(s.urgent_tickets or 0),
            "sla_risk_count": int(s.sla_risk_count or 0),
            "resolved_tickets": int(s.resolved_tickets or 0),
            "sla_compliance_rate": compliance,
        })

    # Include registered CGD entities with 0 tickets so visibility is complete
    for cust in customers:
        if cust.name not in seen:
            result.append({
                "customer": cust.name,
                "customer_name": cust.customer_name or cust.name,
                "domain": cust.domain or "",
                "is_vip": bool(cust.is_vip),
                "total_tickets": 0,
                "open_tickets": 0,
                "urgent_tickets": 0,
                "sla_risk_count": 0,
                "resolved_tickets": 0,
                "sla_compliance_rate": 100.0,
            })

    # Sort: active tickets descending, then total tickets descending
    result.sort(key=lambda x: (x["open_tickets"], x["total_tickets"]), reverse=True)

    return {
        "entities": result,
        "total_entities": len(result),
        "total_active_cgd_tickets": sum(r["open_tickets"] for r in result),
        "total_urgent_tickets": sum(r["urgent_tickets"] for r in result),
        "total_sla_risk": sum(r["sla_risk_count"] for r in result),
    }


@frappe.whitelist()
@agent_only
def get_hourly_ticket_heatmap(days=7):
    """Aggregate ticket inflow and resolution by hour of the day (0-23) over the trailing period."""
    days = int(days or 7)
    start_date = add_days(nowdate(), -days)

    query = """
        SELECT 
            HOUR(creation) as hour_of_day,
            COUNT(name) as created_count,
            SUM(CASE WHEN resolution_date IS NOT NULL THEN 1 ELSE 0 END) as resolved_count
        FROM `tabHD Ticket`
        WHERE creation >= %s
        GROUP BY hour_of_day
        ORDER BY hour_of_day ASC
    """

    rows = frappe.db.sql(query, (start_date,), as_dict=True)
    rows_by_hour = {r.hour_of_day: r for r in rows}

    distribution = []
    peak_hour = 0
    peak_volume = 0

    for h in range(24):
        item = rows_by_hour.get(h, None)
        created = int(item.created_count or 0) if item else 0
        resolved = int(item.resolved_count or 0) if item else 0

        if created > peak_volume:
            peak_volume = created
            peak_hour = h

        distribution.append({
            "hour": h,
            "label": f"{h:02d}:00",
            "created": created,
            "resolved": resolved,
        })

    return {
        "days": days,
        "distribution": distribution,
        "peak_hour": peak_hour,
        "peak_hour_label": f"{peak_hour:02d}:00",
        "peak_volume": peak_volume,
        "total_period_tickets": sum(d["created"] for d in distribution),
    }


@frappe.whitelist()
@agent_only
def send_scheduled_analytics_digest(recipients=None):
    """Generate and dispatch scheduled support analytics digest to team leads or specified recipients."""
    if not recipients:
        team_leads = frappe.get_all("Has Role", filters={"role": "HD Team Lead"}, fields=["parent"])
        recipients = [r["parent"] for r in team_leads if "@" in r["parent"]]

    if not recipients:
        recipients = [frappe.session.user]

    report = generate_ticket_report(group_by="customer")
    summary = report["summary"]

    table_rows = "".join([
        f"<tr>"
        f"<td style='padding:8px;border:1px solid #fed7aa;'>{row['group_label']}</td>"
        f"<td style='padding:8px;border:1px solid #fed7aa;text-align:right;'>{row['total_tickets']}</td>"
        f"<td style='padding:8px;border:1px solid #fed7aa;text-align:right;'>{row['open_tickets']}</td>"
        f"<td style='padding:8px;border:1px solid #fed7aa;text-align:right;'>{row['resolved_tickets']}</td>"
        f"<td style='padding:8px;border:1px solid #fed7aa;text-align:right;'>{row['sla_adherence_percent']}%</td>"
        f"</tr>"
        for row in report.get("rows", [])[:10]
    ])

    html_message = f"""
    <div style="font-family: sans-serif; max-width: 650px; margin: auto; padding: 20px; border: 1px solid #fed7aa; border-radius: 8px;">
        <h2 style="color: #ea580c; margin-top:0;">Support Analytics Digest</h2>
        <p>Summary of support operations as of {now_datetime().strftime('%Y-%m-%d %H:%M')}:</p>
        <div style="display:flex;gap:12px;margin-bottom:20px;">
            <div style="background:#fffaf5;padding:12px;border:1px solid #fed7aa;border-radius:6px;flex:1;text-align:center;">
                <div style="font-size:22px;font-weight:bold;color:#ea580c;">{summary['total_tickets']}</div>
                <div style="font-size:12px;color:#7c2d12;">Total Tickets</div>
            </div>
            <div style="background:#fffaf5;padding:12px;border:1px solid #fed7aa;border-radius:6px;flex:1;text-align:center;">
                <div style="font-size:22px;font-weight:bold;color:#ea580c;">{summary['open_tickets']}</div>
                <div style="font-size:12px;color:#7c2d12;">Open Tickets</div>
            </div>
            <div style="background:#fffaf5;padding:12px;border:1px solid #fed7aa;border-radius:6px;flex:1;text-align:center;">
                <div style="font-size:22px;font-weight:bold;color:#ea580c;">{summary['overall_sla_adherence']}%</div>
                <div style="font-size:12px;color:#7c2d12;">SLA Adherence</div>
            </div>
        </div>
        <table style="width:100%;border-collapse:collapse;font-size:13px;">
            <thead>
                <tr style="background:#fed7aa;color:#7c2d12;">
                    <th style="padding:8px;text-align:left;">Entity</th>
                    <th style="padding:8px;text-align:right;">Total</th>
                    <th style="padding:8px;text-align:right;">Open</th>
                    <th style="padding:8px;text-align:right;">Resolved</th>
                    <th style="padding:8px;text-align:right;">SLA %</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
    """

    frappe.sendmail(
        recipients=recipients,
        subject=f"Helpdesk Operations Digest - {now_datetime().strftime('%b %d')}",
        message=html_message,
        now=True,
    )

    return {
        "success": True,
        "recipients": recipients,
        "summary": summary,
    }
