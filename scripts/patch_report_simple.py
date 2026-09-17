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

    filtered, totals, category_totals = summarize_items(items, view_type, selected_date, from_date, to_date, active_tab, selected_category)
    total_income = totals["income"]
    total_expense = totals["expense"]

    ledger = []
    running_balance = Decimal("0.00")
    chronological = sorted(filtered, key=lambda item: (transaction_date(item) or date.min, record_created_at(item), str(item.get("_id", ""))))
    for item in chronological:
        t = normalize_transaction_type(item.get("type"))
        amount = money(item.get("amount"))
        inc = amount if t == "income" else Decimal("0.00")
        exp = amount if t == "expense" else Decimal("0.00")
        running_balance += inc - exp
        ledger.append((item, inc, exp, running_balance))

    buffer = io.BytesIO()
    try:
        doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=12*mm, bottomMargin=14*mm, leftMargin=12*mm, rightMargin=12*mm, title="Expense Tracker Financial Report")
        styles = getSampleStyleSheet()
        title = ParagraphStyle("rt", parent=styles["Title"], fontSize=18, leading=22, textColor=colors.HexColor("#0f172a"), spaceAfter=5)
        section = ParagraphStyle("rs", parent=styles["Heading3"], fontSize=11.5, leading=14, fontName="Helvetica-Bold", textColor=colors.HexColor("#2563eb"), spaceBefore=9, spaceAfter=5)
        meta = ParagraphStyle("rm", parent=styles["Normal"], fontSize=8.5, leading=11, textColor=colors.HexColor("#475569"), spaceAfter=8)
        cell = ParagraphStyle("rc", parent=styles["Normal"], fontSize=7.2, leading=9, textColor=colors.HexColor("#0f172a"))
        head = ParagraphStyle("rh", parent=cell, fontName="Helvetica-Bold", textColor=colors.white)
        right = ParagraphStyle("rr", parent=cell, alignment=2)
        inc_style = ParagraphStyle("ri", parent=right, textColor=colors.HexColor("#059669"), fontName="Helvetica-Bold")
        exp_style = ParagraphStyle("re", parent=right, textColor=colors.HexColor("#e11d48"), fontName="Helvetica-Bold")
        bal_style = ParagraphStyle("rb", parent=right, textColor=colors.HexColor("#2563eb"), fontName="Helvetica-Bold")

        elements = [Paragraph("Expense Tracker — Financial Report", title), Paragraph(f"<b>Period:</b> {escape(view_type.capitalize())} &nbsp;&nbsp; <b>Transactions:</b> {len(ledger)} &nbsp;&nbsp; <b>Generated:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}", meta)]

        # Plain accounting summary — no cards.
        summary = Table([
            [Paragraph("Total Income", head), Paragraph("Total Expense", head), Paragraph("Final Balance", head)],
            [Paragraph(f"Rs {total_income:,.2f}", inc_style), Paragraph(f"Rs {total_expense:,.2f}", exp_style), Paragraph(f"Rs {running_balance:,.2f}", bal_style)]
        ], colWidths=[58*mm,58*mm,58*mm])
        summary.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#2563eb")),("GRID",(0,0),(-1,-1),.5,colors.HexColor("#cbd5e1")),("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,0),6),("BOTTOMPADDING",(0,0),(-1,0),6),("TOPPADDING",(0,1),(-1,1),7),("BOTTOMPADDING",(0,1),(-1,1),7)]))
        elements += [summary, Spacer(1,5), Paragraph("Category-wise Summary", section)]

        cat_data = [[Paragraph("Category",head),Paragraph("Income (Rs)",head),Paragraph("Expense (Rs)",head),Paragraph("Total (Rs)",head)]]
        for category, vd in sorted(category_totals.items(), key=lambda x: money(x[1].get("income"))+money(x[1].get("expense")), reverse=True):
            ci, ce = money(vd.get("income")), money(vd.get("expense"))
            cat_data.append([Paragraph(escape(category),cell),Paragraph(f"{ci:,.2f}" if ci else "—",inc_style),Paragraph(f"{ce:,.2f}" if ce else "—",exp_style),Paragraph(f"{ci+ce:,.2f}",bal_style)])
        if len(cat_data)==1: cat_data.append([Paragraph("No category records",cell),Paragraph("—",right),Paragraph("—",right),Paragraph("—",right)])
        cat_table=Table(cat_data,colWidths=[70*mm,40*mm,40*mm,40*mm],repeatRows=1)
        cat_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#2563eb")),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#cbd5e1")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),("ALIGN",(1,1),(-1,-1),"RIGHT"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),5),("BOTTOMPADDING",(0,0),(-1,-1),5)]))
        elements += [cat_table, Spacer(1,5), Paragraph("Transaction Ledger", section)]

        data=[[Paragraph("#",head),Paragraph("Date / Time",head),Paragraph("Description",head),Paragraph("Category",head),Paragraph("Income (Rs)",head),Paragraph("Expense (Rs)",head),Paragraph("Balance (Rs)",head)]]
        for i,(item,inc,exp,balance) in enumerate(ledger,1):
            desc=normalize_text(item.get("description"),90) or normalize_text(item.get("party"),60) or "—"
            category=normalize_category(item.get("category")); dt=str(item.get("date","—")); created=record_created_at(item)
            if created != datetime.min.replace(tzinfo=timezone.utc): dt += f" {created.astimezone().strftime('%I:%M %p')}"
            data.append([Paragraph(str(i),cell),Paragraph(escape(dt),cell),Paragraph(escape(desc),cell),Paragraph(escape(category),cell),Paragraph(f"{inc:,.2f}" if inc else "—",inc_style),Paragraph(f"{exp:,.2f}" if exp else "—",exp_style),Paragraph(f"{balance:,.2f}",bal_style)])
        if len(data)==1: data.append([Paragraph("—",cell),Paragraph("—",cell),Paragraph("No transactions",cell),Paragraph("—",cell),Paragraph("—",right),Paragraph("—",right),Paragraph("0.00",bal_style)])
        ledger_table=Table(data,colWidths=[8*mm,31*mm,42*mm,32*mm,27*mm,27*mm,30*mm],repeatRows=1)
        ledger_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0f172a")),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#cbd5e1")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),("VALIGN",(0,0),(-1,-1),"TOP"),("ALIGN",(4,1),(-1,-1),"RIGHT"),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
        elements += [ledger_table, Spacer(1,8), Paragraph("Final Summary", section)]

        final=Table([[Paragraph("Total Income",head),Paragraph("Total Expense",head),Paragraph("Final Balance",head)],[Paragraph(f"Rs {total_income:,.2f}",inc_style),Paragraph(f"Rs {total_expense:,.2f}",exp_style),Paragraph(f"Rs {running_balance:,.2f}",bal_style)]],colWidths=[58*mm,58*mm,58*mm])
        final.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#2563eb")),("GRID",(0,0),(-1,-1),.5,colors.HexColor("#cbd5e1")),("ALIGN",(0,0),(-1,-1),"CENTER"),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
        elements.append(final)
        doc.build(elements)
    except Exception:
        app.logger.exception("PDF report generation error"); buffer.close(); flash("Unable to generate the PDF report. Please try again.","danger"); return redirect(url_for("summary"))
    buffer.seek(0)
    return send_file(buffer,mimetype="application/pdf",as_attachment=True,download_name=f"financial_report_{view_type}_{datetime.now().strftime('%Y%m%d')}.pdf")

'''
path.write_text(text[:start] + new_route + text[end:], encoding="utf-8")
print("PDF report replaced with simple accounting-style report")
