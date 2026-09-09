from pathlib import Path
import re

path = Path("app.py")
text = path.read_text(encoding="utf-8")

start = text.index('@app.route("/summary/report")')
end = text.index('@app.route("/sitemap.xml")', start)

new_route = r'''@app.route("/summary/report")
@login_required
def download_report():
    uid = session.get("user_id")
    view_type = request.args.get("type", "overall").lower()
    view_type = view_type if view_type in {"overall", "weekly", "monthly", "daily", "range"} else "overall"
    selected_date = request.args.get("date", date.today().isoformat())
    selected_category = normalize_text(request.args.get("category"), 80)
    active_tab = request.args.get("tab", "all").lower()
    active_tab = active_tab if active_tab in {"all", "expense", "income"} else "all"
    from_date = request.args.get("from_date", "")
    to_date = request.args.get("to_date", "")

    try:
        items = list(expenses_collection.find({"user_id": uid}))
    except Exception:
        app.logger.exception("Report query error")
        items = []

    filtered, totals, category_totals = summarize_items(
        items, view_type, selected_date, from_date, to_date, active_tab, selected_category
    )
    total_income = totals["income"]
    total_expense = totals["expense"]
    net = totals["net_income"]

    # The PDF ledger is intentionally chronological: oldest transaction first.
    # Running balance starts at zero and changes after every income/expense.
    ledger = []
    running_balance = Decimal("0.00")
    chronological = sorted(
        filtered,
        key=lambda item: (transaction_date(item) or date.min, record_created_at(item), str(item.get("_id", "")))
    )
    for item in chronological:
        t = normalize_transaction_type(item.get("type"))
        amount = money(item.get("amount"))
        income_amount = amount if t == "income" else Decimal("0.00")
        expense_amount = amount if t == "expense" else Decimal("0.00")
        if t == "income":
            running_balance += amount
        elif t == "expense":
            running_balance -= amount
        ledger.append((item, income_amount, expense_amount, running_balance))

    buffer = io.BytesIO()
    try:
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            topMargin=14 * mm,
            bottomMargin=14 * mm,
            leftMargin=12 * mm,
            rightMargin=12 * mm,
            title="Expense Tracker Financial Report",
            author=normalize_text(session.get("first_name", "User"), 80),
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle("StatementTitle", parent=styles["Title"], fontSize=19, leading=23, textColor=colors.HexColor("#0f172a"), spaceAfter=5)
        section_style = ParagraphStyle("Section", parent=styles["Heading3"], fontSize=11, leading=14, fontName="Helvetica-Bold", textColor=colors.HexColor("#0f172a"), spaceBefore=8, spaceAfter=5)
        meta_style = ParagraphStyle("StatementMeta", parent=styles["Normal"], fontSize=8.5, leading=12, textColor=colors.HexColor("#475569"), spaceAfter=10)
        cell_style = ParagraphStyle("StatementCell", parent=styles["Normal"], fontSize=7.1, leading=9, textColor=colors.HexColor("#0f172a"))
        header_style = ParagraphStyle("StatementHeader", parent=cell_style, fontName="Helvetica-Bold", textColor=colors.white)
        money_style = ParagraphStyle("MoneyCell", parent=cell_style, alignment=2)
        balance_style = ParagraphStyle("BalanceCell", parent=cell_style, alignment=2, fontName="Helvetica-Bold")
        total_label_style = ParagraphStyle("TotalLabel", parent=styles["Normal"], fontSize=9, leading=12, fontName="Helvetica-Bold", textColor=colors.HexColor("#0f172a"))
        total_value_style = ParagraphStyle("TotalValue", parent=total_label_style, alignment=2)

        elements = [Paragraph("Expense Tracker — Financial Report", title_style)]
        period = view_type.capitalize()
        elements.append(Paragraph(
            f"<b>Prepared for:</b> {escape(normalize_text(session.get('first_name', 'User'), 80))} &nbsp;&nbsp; "
            f"<b>Period:</b> {escape(period)}<br/>"
            f"<b>Transactions:</b> {len(ledger)} &nbsp;&nbsp; "
            f"<b>Generated:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}",
            meta_style,
        ))

        summary_data = [
            [Paragraph("Total Income", total_label_style), Paragraph(f"Rs {total_income:,.2f}", total_value_style)],
            [Paragraph("Total Expense", total_label_style), Paragraph(f"Rs {total_expense:,.2f}", total_value_style)],
            [Paragraph("Final Balance", total_label_style), Paragraph(f"Rs {running_balance:,.2f}", total_value_style)],
        ]
        summary_table = Table(summary_data, colWidths=[105 * mm, 70 * mm], hAlign="LEFT")
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ]))
        elements.extend([summary_table, Spacer(1, 10), Paragraph("Transaction Ledger", section_style)])

        table_data = [[
            Paragraph("#", header_style),
            Paragraph("Date", header_style),
            Paragraph("Description", header_style),
            Paragraph("Category", header_style),
            Paragraph("Income (Rs)", header_style),
            Paragraph("Expense (Rs)", header_style),
            Paragraph("Balance (Rs)", header_style),
        ]]
        for idx, (item, income_amount, expense_amount, balance) in enumerate(ledger, 1):
            description = normalize_text(item.get("description"), 90) or normalize_text(item.get("party"), 60) or "—"
            category = normalize_category(item.get("category"))
            table_data.append([
                Paragraph(str(idx), cell_style),
                Paragraph(escape(str(item.get("date", "—"))), cell_style),
                Paragraph(escape(description), cell_style),
                Paragraph(escape(category), cell_style),
                Paragraph(f"{income_amount:,.2f}" if income_amount else "—", money_style),
                Paragraph(f"{expense_amount:,.2f}" if expense_amount else "—", money_style),
                Paragraph(f"{balance:,.2f}", balance_style),
            ])
        if len(table_data) == 1:
            table_data.append([
                Paragraph("—", cell_style), Paragraph("—", cell_style), Paragraph("No transactions", cell_style),
                Paragraph("—", cell_style), Paragraph("—", money_style), Paragraph("—", money_style), Paragraph("0.00", balance_style)
            ])

        ledger_table = Table(
            table_data,
            colWidths=[12 * mm, 25 * mm, 46 * mm, 32 * mm, 25 * mm, 25 * mm, 30 * mm],
            repeatRows=1,
            hAlign="LEFT",
        )
        ledger_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ALIGN", (4, 1), (-1, -1), "RIGHT"),
            ("LEFTPADDING", (0, 0), (-1, -1), 4),
            ("RIGHTPADDING", (0, 0), (-1, -1), 4),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        elements.append(ledger_table)

        elements.extend([Spacer(1, 12), Paragraph("Final Summary", section_style)])
        final_data = [[
            Paragraph("Total Income", total_label_style),
            Paragraph("Total Expense", total_label_style),
            Paragraph("Final Balance", total_label_style),
        ], [
            Paragraph(f"Rs {total_income:,.2f}", total_value_style),
            Paragraph(f"Rs {total_expense:,.2f}", total_value_style),
            Paragraph(f"Rs {running_balance:,.2f}", total_value_style),
        ]]
        final_table = Table(final_data, colWidths=[58 * mm, 58 * mm, 59 * mm], hAlign="LEFT")
        final_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#f8fafc")),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("TOPPADDING", (0, 0), (-1, -1), 7),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        elements.append(final_table)

        def add_page_number(canvas, document):
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.HexColor("#64748b"))
            canvas.drawRightString(A4[0] - 12 * mm, 7 * mm, f"Page {document.page}")
            canvas.restoreState()

        doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)
    except Exception:
        app.logger.exception("PDF report generation error")
        buffer.close()
        flash("Unable to generate the PDF report. Please try again.", "danger")
        return redirect(url_for("summary"))

    buffer.seek(0)
    return send_file(
        buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"financial_report_{view_type}_{datetime.now().strftime('%Y%m%d')}.pdf",
    )

'''

text = text[:start] + new_route + text[end:]
path.write_text(text, encoding="utf-8")
print("Report route patched successfully")
