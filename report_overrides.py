"""Production PDF report override.

This module is imported by wsgi.py after the Flask app is created. It keeps
PDF generation aligned with the Summary page without changing the existing
application routes.
"""

import io
from datetime import date, datetime
from decimal import Decimal

from flask import request, send_file, session
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from app import (
    app,
    expenses_collection,
    money,
    normalize_category,
    normalize_text,
    sort_by_added,
    summary_period_matches,
    transaction_date,
)


def _pdf_report_response():
    uid = session.get("user_id")
    view_type = request.args.get("type", "overall").lower()
    if view_type not in {"overall", "weekly", "monthly", "daily", "range"}:
        view_type = "overall"

    selected_date = request.args.get("date", date.today().isoformat())
    selected_category = normalize_text(request.args.get("category"), 80)
    active_tab = request.args.get("tab", "all").lower()
    if active_tab not in {"all", "expense", "income"}:
        active_tab = "all"
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")

    try:
        items = list(expenses_collection.find({"user_id": uid}))
    except Exception:
        app.logger.exception("PDF report query error")
        items = []

    today = date.today()
    filtered = []
    total_income = Decimal("0.00")
    total_expense = Decimal("0.00")

    for item in items:
        trans_date = transaction_date(item)
        trans_type = str(item.get("type", "expense")).lower()
        category = normalize_category(item.get("category"))

        if active_tab == "expense" and trans_type != "expense":
            continue
        if active_tab == "income" and trans_type != "income":
            continue
        if not summary_period_matches(trans_date, view_type, selected_date, from_date, to_date, today):
            continue
        if selected_category and selected_category.lower() != "all" and category.lower() != selected_category.lower():
            continue

        filtered.append(item)
        amount = money(item.get("amount"))
        if trans_type == "income":
            total_income += amount
        else:
            total_expense += amount

    # Keep report order consistent with the app's "newest added first" view.
    filtered = sort_by_added(filtered, newest_first=True)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        leftMargin=14 * mm,
        rightMargin=14 * mm,
        title="Expense Tracker Financial Statement",
        author="Expense Tracker",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Title"],
        textColor=colors.HexColor("#0284c7"),
        fontSize=18,
        leading=22,
        spaceAfter=5,
    )
    meta_style = ParagraphStyle(
        "ReportMeta",
        parent=styles["Normal"],
        textColor=colors.HexColor("#475569"),
        fontSize=8.5,
        leading=12,
        spaceAfter=10,
    )
    section_style = ParagraphStyle(
        "ReportSection",
        parent=styles["Heading2"],
        textColor=colors.HexColor("#0f172a"),
        fontSize=11,
        leading=14,
        spaceBefore=10,
        spaceAfter=7,
    )

    period = view_type.capitalize()
    if view_type == "daily":
        period += f" ({selected_date})"
    elif view_type == "monthly":
        period += " (Current Month)"
    elif view_type == "weekly":
        period += " (Last 7 Days)"
    elif view_type == "range":
        period += f" ({from_date} to {to_date})"

    tab_label = {"expense": "Expenses Only", "income": "Income Only", "all": "Income & Expenses"}[active_tab]
    scope = selected_category if selected_category and selected_category.lower() != "all" else "All Categories"

    elements = [Paragraph("Expense Tracker — Financial Statement", title_style)]
    elements.append(
        Paragraph(
            f"<b>User:</b> {normalize_text(session.get('first_name', 'User'), 80)}"
            f" &nbsp;|&nbsp; <b>Period:</b> {period}"
            f" &nbsp;|&nbsp; <b>View:</b> {tab_label}"
            f" &nbsp;|&nbsp; <b>Category:</b> {scope}"
            f" &nbsp;|&nbsp; <b>Generated:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
            meta_style,
        )
    )

    if not filtered:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("No financial records found for this selection.", styles["Normal"]))
    else:
        table_data = [["#", "Date", "Type", "Category", "Description", "Amount (Rs)"]]
        for index, item in enumerate(filtered, 1):
            table_data.append([
                str(index),
                item.get("date", "-"),
                str(item.get("type", "expense")).capitalize(),
                normalize_category(item.get("category"), "-"),
                normalize_text(item.get("description"), 100) or "-",
                f"{money(item.get('amount')):,.2f}",
            ])

        table = Table(table_data, colWidths=[20, 58, 55, 78, 184, 78], repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#cbd5e1")),
            ("ALIGN", (0, 0), (0, -1), "CENTER"),
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("ALIGN", (5, 0), (5, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(table)

    # Professional statement totals are deliberately placed at the end.
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Statement Totals", section_style))
    net = total_income - total_expense

    if active_tab == "expense":
        totals_data = [
            ["Total Expense", f"Rs {total_expense:,.2f}"],
            ["Records", str(len(filtered))],
        ]
    elif active_tab == "income":
        totals_data = [
            ["Total Income", f"Rs {total_income:,.2f}"],
            ["Records", str(len(filtered))],
        ]
    else:
        net_label = "Net Savings / Balance"
        totals_data = [
            ["Total Income", f"Rs {total_income:,.2f}"],
            ["Total Expense", f"Rs {total_expense:,.2f}"],
            [net_label, f"Rs {net:,.2f}"],
            ["Records", str(len(filtered))],
        ]

    totals_table = Table(totals_data, colWidths=[125, 105], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#e2e8f0")),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTNAME", (1, 0), (1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 8))
    elements.append(Paragraph("Generated by Expense Tracker • Financial event dates are used for period calculations.", meta_style))

    doc.build(elements)
    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"statement_{view_type}_{datetime.now().strftime('%Y%m%d')}.pdf",
    )


@app.before_request
def professional_pdf_report_override():
    if request.method == "GET" and request.path == "/summary/report" and session.get("user_id"):
        return _pdf_report_response()
