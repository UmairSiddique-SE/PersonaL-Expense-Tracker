"""Production PDF report override.

This module is imported by wsgi.py after the Flask app is created. It keeps
PDF generation aligned with the Summary page without changing the existing
application routes.
"""

import io
from datetime import date, datetime
from decimal import Decimal
from xml.sax.saxutils import escape

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


def _safe_pdf_text(value, max_length=500):
    """Normalize and XML-escape user/database text before ReportLab Paragraph use."""
    return escape(normalize_text(value, max_length))


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

    # Newest added record first, matching View Records and the dashboard flow.
    filtered = sort_by_added(filtered, newest_first=True)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
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
        fontSize=8.2,
        leading=11,
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
    cell_style = ParagraphStyle(
        "ReportCell",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#334155"),
    )
    cell_center_style = ParagraphStyle(
        "ReportCellCenter",
        parent=cell_style,
        alignment=1,
    )
    cell_right_style = ParagraphStyle(
        "ReportCellRight",
        parent=cell_style,
        alignment=2,
    )
    header_style = ParagraphStyle(
        "ReportHeader",
        parent=cell_style,
        textColor=colors.white,
        fontName="Helvetica-Bold",
        alignment=0,
    )

    period = view_type.capitalize()
    if view_type == "daily":
        period += f" ({_safe_pdf_text(selected_date, 20)})"
    elif view_type == "monthly":
        period += " (Current Month)"
    elif view_type == "weekly":
        period += " (Last 7 Days)"
    elif view_type == "range":
        period += f" ({_safe_pdf_text(from_date, 20)} to {_safe_pdf_text(to_date, 20)})"

    tab_label = {
        "expense": "Expenses Only",
        "income": "Income Only",
        "all": "Income & Expenses",
    }[active_tab]
    scope = selected_category if selected_category and selected_category.lower() != "all" else "All Categories"
    user_name = _safe_pdf_text(session.get("first_name", "User"), 80) or "User"

    elements = [Paragraph("Expense Tracker — Financial Statement", title_style)]
    elements.append(
        Paragraph(
            f"<b>User:</b> {user_name}"
            f" &nbsp;|&nbsp; <b>Period:</b> {period}"
            f" &nbsp;|&nbsp; <b>View:</b> {_safe_pdf_text(tab_label, 40)}"
            f" &nbsp;|&nbsp; <b>Category:</b> {_safe_pdf_text(scope, 80)}"
            f" &nbsp;|&nbsp; <b>Generated:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
            meta_style,
        )
    )

    if filtered:
        table_data = [[
            Paragraph("#", header_style),
            Paragraph("Date", header_style),
            Paragraph("Type", header_style),
            Paragraph("Category", header_style),
            Paragraph("Description", header_style),
            Paragraph("Amount (Rs)", ParagraphStyle("ReportHeaderRight", parent=header_style, alignment=2)),
        ]]

        for index, item in enumerate(filtered, 1):
            item_type = str(item.get("type", "expense")).capitalize()
            amount = f"{money(item.get('amount')):,.2f}"
            table_data.append([
                Paragraph(str(index), cell_center_style),
                Paragraph(_safe_pdf_text(item.get("date", "-"), 20) or "-", cell_center_style),
                Paragraph(_safe_pdf_text(item_type, 20), cell_center_style),
                Paragraph(_safe_pdf_text(normalize_category(item.get("category"), "-"), 60) or "-", cell_style),
                Paragraph(_safe_pdf_text(item.get("description"), 140) or "-", cell_style),
                Paragraph(amount, cell_right_style),
            ])

        # Total is 486pt, safely inside A4 printable width with 12mm margins.
        table = Table(
            table_data,
            colWidths=[22, 55, 55, 72, 192, 90],
            repeatRows=1,
            hAlign="LEFT",
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(table)
    else:
        elements.append(Spacer(1, 6))
        elements.append(Paragraph("No financial records found for this selection.", styles["Normal"]))

    # Professional statement totals are deliberately placed at the end.
    elements.append(Spacer(1, 12))
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
        totals_data = [
            ["Total Income", f"Rs {total_income:,.2f}"],
            ["Total Expense", f"Rs {total_expense:,.2f}"],
            ["Net Savings / Balance", f"Rs {net:,.2f}"],
            ["Records", str(len(filtered))],
        ]

    totals_table = Table(totals_data, colWidths=[135, 115], hAlign="RIGHT")
    totals_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ("BOX", (0, 0), (-1, -1), 0.8, colors.HexColor("#cbd5e1")),
        ("INNERGRID", (0, 0), (-1, -1), 0.45, colors.HexColor("#e2e8f0")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    elements.append(totals_table)
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "Generated by Expense Tracker • Financial event dates are used for period calculations.",
        meta_style,
    ))

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
