from pathlib import Path

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

    ledger = []
    running_balance = Decimal("0.00")
    chronological = sorted(
        filtered,
        key=lambda item: (transaction_date(item) or date.min, record_created_at(item), str(item.get("_id", "")))
    )
    for item in chronological:
        t = normalize_transaction_type(item.get("type"))
        amount = money(item.get("amount"))
        inc = amount if t == "income" else Decimal("0.00")
        exp = amount if t == "expense" else Decimal("0.00")
        if t == "income":
            running_balance += amount
        elif t == "expense":
            running_balance -= amount
        ledger.append((item, inc, exp, running_balance))

    buffer = io.BytesIO()
    try:
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            topMargin=12 * mm, bottomMargin=14 * mm,
            leftMargin=12 * mm, rightMargin=12 * mm,
            title="Expense Tracker Financial Report",
            author=normalize_text(session.get("first_name", "User"), 80),
        )
        styles = getSampleStyleSheet()
        title = ParagraphStyle("rt", parent=styles["Title"], fontSize=18, leading=22,
                               textColor=colors.HexColor("#0f172a"), spaceAfter=5)
        section = ParagraphStyle("rs", parent=styles["Heading3"], fontSize=11.5, leading=14,
                                 fontName="Helvetica-Bold", textColor=colors.HexColor("#2563eb"),
                                 spaceBefore=9, spaceAfter=5)
        meta = ParagraphStyle("rm", parent=styles["Normal"], fontSize=8.5, leading=11,
                              textColor=colors.HexColor("#475569"), spaceAfter=8)
        cell = ParagraphStyle("rc", parent=styles["Normal"], fontSize=7.2, leading=9,
                              textColor=colors.HexColor("#0f172a"))
        head = ParagraphStyle("rh", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
        right = ParagraphStyle("rr", parent=cell, alignment=2)
        inc_style = ParagraphStyle("ri", parent=right, textColor=colors.HexColor("#059669"), fontName="Helvetica-Bold")
        exp_style = ParagraphStyle("re", parent=right, textColor=colors.HexColor("#e11d48"), fontName="Helvetica-Bold")
        bal_style = ParagraphStyle("rb", parent=right, textColor=colors.HexColor("#2563eb"), fontName="Helvetica-Bold")
        value = ParagraphStyle("rv", parent=styles["Normal"], fontSize=10.5, leading=13,
                               fontName="Helvetica-Bold", alignment=2)
        final_head = ParagraphStyle("fh", parent=styles["Normal"], fontSize=8.5, leading=10,
                                    fontName="Helvetica-Bold", textColor=colors.HexColor("#0f172a"))
        final_val = ParagraphStyle("fv", parent=styles["Normal"], fontSize=10, leading=12,
                                   fontName="Helvetica-Bold", alignment=2)

        elements = [
            Paragraph("Expense Tracker — Financial Report", title),
            Paragraph(
                f"<b>Prepared for:</b> {escape(normalize_text(session.get('first_name','User'),80))} &nbsp;&nbsp; "
                f"<b>Period:</b> {escape(view_type.capitalize())}<br/>"
                f"<b>Transactions:</b> {len(ledger)} &nbsp;&nbsp; <b>Generated:</b> "
                f"{datetime.now().strftime('%d %b %Y, %I:%M %p')}", meta
            ),
        ]

        # Simple summary table: no large/fancy top cards.
        summary = Table([
            [Paragraph("Total Income", head), Paragraph("Total Expense", head), Paragraph("Final Balance", head)],
            [Paragraph(f"Rs {total_income:,.2f}", ParagraphStyle("si", parent=value, textColor=colors.HexColor("#059669"))),
             Paragraph(f"Rs {total_expense:,.2f}", ParagraphStyle("se", parent=value, textColor=colors.HexColor("#e11d48"))),
             Paragraph(f"Rs {running_balance:,.2f}", ParagraphStyle("sb", parent=value, textColor=colors.HexColor("#2563eb")))],
        ], colWidths=[58 * mm, 58 * mm, 58 * mm])
        summary.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#f1f5f9")),
            ("GRID", (0,0), (-1,-1), .5, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("TOPPADDING", (0,0), (-1,0), 6), ("BOTTOMPADDING", (0,0), (-1,0), 6),
            ("TOPPADDING", (0,1), (-1,1), 8), ("BOTTOMPADDING", (0,1), (-1,1), 8),
        ]))
        elements += [summary, Spacer(1, 4), Paragraph("Category-wise Summary", section)]

        cats = []
        for category, value_data in category_totals.items():
            ci = money(value_data.get("income")); ce = money(value_data.get("expense"))
            total = ci + ce
            if active_tab == "income": total = ci
            elif active_tab == "expense": total = ce
            cats.append((category, ci, ce, total))
        cats.sort(key=lambda x: x[3], reverse=True)

        cat_data = [[Paragraph("Category", head), Paragraph("Income (Rs)", head), Paragraph("Expense (Rs)", head), Paragraph("Total (Rs)", head)]]
        for category, ci, ce, total in cats:
            cat_data.append([
                Paragraph(escape(category), cell),
                Paragraph(f"{ci:,.2f}" if ci else "—", inc_style),
                Paragraph(f"{ce:,.2f}" if ce else "—", exp_style),
                Paragraph(f"{total:,.2f}", bal_style),
            ])
        if len(cat_data) == 1:
            cat_data.append([Paragraph("No category records", cell), Paragraph("—", right), Paragraph("—", right), Paragraph("—", right)])
        cat_table = Table(cat_data, colWidths=[70 * mm, 40 * mm, 40 * mm, 40 * mm], repeatRows=1)
        cat_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2563eb")),
            ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ("ALIGN", (1,1), (-1,-1), "RIGHT"),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("LEFTPADDING", (0,0), (-1,-1), 5), ("RIGHTPADDING", (0,0), (-1,-1), 5),
            ("TOPPADDING", (0,0), (-1,-1), 5), ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ]))
        elements += [cat_table, Spacer(1, 5), Paragraph("Transaction Ledger", section)]

        data = [[Paragraph("#", head), Paragraph("Date / Time", head), Paragraph("Description", head),
                 Paragraph("Category", head), Paragraph("Income (Rs)", head), Paragraph("Expense (Rs)", head), Paragraph("Balance (Rs)", head)]]
        for index, (item, ia, ea, balance) in enumerate(ledger, 1):
            desc = normalize_text(item.get("description"), 90) or normalize_text(item.get("party"), 60) or "—"
            category = normalize_category(item.get("category"))
            created = record_created_at(item)
            dt = str(item.get("date", "—"))
            if created != datetime.min.replace(tzinfo=timezone.utc):
                dt += f" {created.astimezone().strftime('%I:%M %p')}"
            data.append([Paragraph(str(index), cell), Paragraph(escape(dt), cell), Paragraph(escape(desc), cell),
                           Paragraph(escape(category), cell), Paragraph(f"{ia:,.2f}" if ia else "—", inc_style),
                           Paragraph(f"{ea:,.2f}" if ea else "—", exp_style), Paragraph(f"{balance:,.2f}", bal_style)])
        if len(data) == 1:
            data.append([Paragraph("—", cell), Paragraph("—", cell), Paragraph("No transactions", cell), Paragraph("—", cell),
                         Paragraph("—", right), Paragraph("—", right), Paragraph("0.00", bal_style)])

        ledger_table = Table(data, colWidths=[8*mm, 31*mm, 42*mm, 32*mm, 27*mm, 27*mm, 30*mm], repeatRows=1)
        ledger_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#0f172a")),
            ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#cbd5e1")),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f8fafc")]),
            ("VALIGN", (0,0), (-1,-1), "TOP"), ("ALIGN", (4,1), (-1,-1), "RIGHT"),
            ("LEFTPADDING", (0,0), (-1,-1), 3), ("RIGHTPADDING", (0,0), (-1,-1), 3),
            ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ]))
        elements += [ledger_table, Spacer(1, 9), Paragraph("Final Summary", section)]

        final = Table([
            [Paragraph("Total Income", final_head), Paragraph("Total Expense", final_head), Paragraph("Final Balance", final_head)],
            [Paragraph(f"Rs {total_income:,.2f}", ParagraphStyle("f1", parent=final_val, textColor=colors.HexColor("#059669"))),
             Paragraph(f"Rs {total_expense:,.2f}", ParagraphStyle("f2", parent=final_val, textColor=colors.HexColor("#e11d48"))),
             Paragraph(f"Rs {running_balance:,.2f}", ParagraphStyle("f3", parent=final_val, textColor=colors.HexColor("#2563eb")))],
        ], colWidths=[58 * mm, 58 * mm, 58 * mm])
        final.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e2e8f0")),
            ("BACKGROUND", (0,1), (0,1), colors.HexColor("#ecfdf5")),
            ("BACKGROUND", (1,1), (1,1), colors.HexColor("#fff1f2")),
            ("BACKGROUND", (2,1), (2,1), colors.HexColor("#eff6ff")),
            ("BOX", (0,0), (-1,-1), .6, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0,0), (-1,-1), .4, colors.HexColor("#cbd5e1")),
            ("TOPPADDING", (0,0), (-1,0), 7), ("BOTTOMPADDING", (0,0), (-1,0), 7),
            ("TOPPADDING", (0,1), (-1,1), 8), ("BOTTOMPADDING", (0,1), (-1,1), 8),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ]))
        elements.append(final)

        def footer(canvas, document):
            canvas.saveState()
            canvas.setFont("Helvetica", 7)
            canvas.setFillColor(colors.HexColor("#64748b"))
            canvas.drawRightString(A4[0] - 12 * mm, 7 * mm, f"Page {document.page}")
            canvas.restoreState()

        doc.build(elements, onFirstPage=footer, onLaterPages=footer)
    except Exception:
        app.logger.exception("PDF report generation error")
        buffer.close()
        flash("Unable to generate the PDF report. Please try again.", "danger")
        return redirect(url_for("summary"))

    buffer.seek(0)
    return send_file(buffer, mimetype="application/pdf", as_attachment=True,
                     download_name=f"financial_report_{view_type}_{datetime.now().strftime('%Y%m%d')}.pdf")

'''
path.write_text(text[:start] + new_route + text[end:], encoding="utf-8")
print("PDF report route simplified")
