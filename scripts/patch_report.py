from pathlib import Path
path=Path("app.py")
text=path.read_text(encoding="utf-8")
start=text.index('@app.route("/summary/report")')
end=text.index('@app.route("/sitemap.xml")',start)
new_route=r'''@app.route("/summary/report")
@login_required
def download_report():
    uid=session.get("user_id")
    view_type=request.args.get("type","overall").lower(); view_type=view_type if view_type in {"overall","weekly","monthly","daily","range"} else "overall"
    selected_date=request.args.get("date",date.today().isoformat()); selected_category=normalize_text(request.args.get("category"),80)
    active_tab=request.args.get("tab","all").lower(); active_tab=active_tab if active_tab in {"all","expense","income"} else "all"
    from_date=request.args.get("from_date",""); to_date=request.args.get("to_date","")
    try: items=list(expenses_collection.find({"user_id":uid}))
    except Exception: app.logger.exception("Report query error"); items=[]
    filtered,totals,category_totals=summarize_items(items,view_type,selected_date,from_date,to_date,active_tab,selected_category)
    total_income,total_expense=totals["income"],totals["expense"]
    ledger=[]; running_balance=Decimal("0.00")
    chronological=sorted(filtered,key=lambda item:(transaction_date(item) or date.min,record_created_at(item),str(item.get("_id",""))))
    for item in chronological:
        t=normalize_transaction_type(item.get("type")); amount=money(item.get("amount")); inc=amount if t=="income" else Decimal("0.00"); exp=amount if t=="expense" else Decimal("0.00")
        if t=="income": running_balance+=amount
        elif t=="expense": running_balance-=amount
        ledger.append((item,inc,exp,running_balance))
    buffer=io.BytesIO()
    try:
        doc=SimpleDocTemplate(buffer,pagesize=A4,topMargin=10*mm,bottomMargin=14*mm,leftMargin=10*mm,rightMargin=10*mm,title="Expense Tracker Financial Report",author=normalize_text(session.get("first_name","User"),80))
        styles=getSampleStyleSheet(); title=ParagraphStyle("rt",parent=styles["Title"],fontSize=19,leading=23,textColor=colors.HexColor("#0f172a"),spaceAfter=4)
        section=ParagraphStyle("rs",parent=styles["Heading3"],fontSize=11.5,leading=14,fontName="Helvetica-Bold",textColor=colors.HexColor("#0f172a"),spaceBefore=7,spaceAfter=5)
        meta=ParagraphStyle("rm",parent=styles["Normal"],fontSize=8.2,leading=10.5,textColor=colors.HexColor("#475569"),spaceAfter=7)
        cell=ParagraphStyle("rc",parent=styles["Normal"],fontSize=6.7,leading=8.2,textColor=colors.HexColor("#0f172a")); head=ParagraphStyle("rh",parent=cell,fontName="Helvetica-Bold",textColor=colors.white)
        right=ParagraphStyle("rr",parent=cell,alignment=2); inc_style=ParagraphStyle("ri",parent=right,textColor=colors.HexColor("#059669"),fontName="Helvetica-Bold"); exp_style=ParagraphStyle("re",parent=right,textColor=colors.HexColor("#e11d48"),fontName="Helvetica-Bold"); bal_style=ParagraphStyle("rb",parent=right,textColor=colors.HexColor("#2563eb"),fontName="Helvetica-Bold")
        card_label=ParagraphStyle("cl",parent=styles["Normal"],fontSize=7.3,leading=8.5,fontName="Helvetica-Bold",textColor=colors.white,alignment=1); card_value=ParagraphStyle("cv",parent=styles["Normal"],fontSize=10.5,leading=12,fontName="Helvetica-Bold",textColor=colors.white,alignment=1)
        elements=[Paragraph("Expense Tracker — Financial Report",title),Paragraph(f"<b>Prepared for:</b> {escape(normalize_text(session.get('first_name','User'),80))} &nbsp;&nbsp; <b>Period:</b> {escape(view_type.capitalize())}<br/><b>Transactions:</b> {len(ledger)} &nbsp;&nbsp; <b>Generated:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}",meta)]
        top=Table([[Paragraph("TOTAL INCOME",card_label),Paragraph("TOTAL EXPENSE",card_label),Paragraph("FINAL BALANCE",card_label)],[Paragraph(f"Rs {total_income:,.2f}",card_value),Paragraph(f"Rs {total_expense:,.2f}",card_value),Paragraph(f"Rs {running_balance:,.2f}",card_value)]],colWidths=[58*mm,58*mm,59*mm])
        top.setStyle(TableStyle([("BACKGROUND",(0,0),(0,-1),colors.HexColor("#059669")),("BACKGROUND",(1,0),(1,-1),colors.HexColor("#e11d48")),("BACKGROUND",(2,0),(2,-1),colors.HexColor("#2563eb")),("INNERGRID",(0,0),(-1,-1),.4,colors.white),("BOX",(0,0),(-1,-1),.6,colors.HexColor("#cbd5e1")),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
        elements += [top,Spacer(1,7),Paragraph("Category-wise Summary",section)]
        cats=[]
        for category,v in category_totals.items():
            ci,ce=money(v.get("income")),money(v.get("expense")); total=ci+ce
            if active_tab=="income": total=ci
            elif active_tab=="expense": total=ce
            cats.append((category,ci,ce,total))
        cats.sort(key=lambda x:x[3],reverse=True); rows=[]
        for i in range(0,len(cats),3):
            row=[]
            for category,ci,ce,total in cats[i:i+3]:
                kind="INCOME" if ci and not ce else ("EXPENSE" if ce and not ci else "MIXED"); bg="#059669" if kind=="INCOME" else ("#e11d48" if kind=="EXPENSE" else "#6366f1")
                box=Table([[Paragraph(escape(category),card_label)],[Paragraph(f"Rs {total:,.2f}",card_value)],[Paragraph(kind,card_label)]],colWidths=[58*mm])
                box.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor(bg)),("BOX",(0,0),(-1,-1),.5,colors.HexColor(bg)),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)])); row.append(box)
            while len(row)<3: row.append("")
            rows.append(row)
        if not rows: rows=[[Paragraph("No category records for this period.",cell),"",""]]
        ct=Table(rows,colWidths=[59*mm,59*mm,59*mm]); ct.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),2),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)]))
        elements += [ct,Spacer(1,4),Paragraph("Transaction Ledger",section)]
        data=[[Paragraph("Category",head),Paragraph("Description",head),Paragraph("Date / Time",head),Paragraph("Income (Rs)",head),Paragraph("Expense (Rs)",head),Paragraph("Balance (Rs)",head)]]
        for item,ia,ea,balance in ledger:
            desc=normalize_text(item.get("description"),90) or normalize_text(item.get("party"),60) or "—"; category=normalize_category(item.get("category")); created=record_created_at(item); dt=str(item.get("date","—"))
            if created != datetime.min.replace(tzinfo=timezone.utc): dt += f" {created.astimezone().strftime('%I:%M %p')}"
            data.append([Paragraph(escape(category),cell),Paragraph(escape(desc),cell),Paragraph(escape(dt),cell),Paragraph(f"{ia:,.2f}" if ia else "—",inc_style),Paragraph(f"{ea:,.2f}" if ea else "—",exp_style),Paragraph(f"{balance:,.2f}",bal_style)])
        if len(data)==1: data.append([Paragraph("—",cell),Paragraph("No transactions",cell),Paragraph("—",cell),Paragraph("—",right),Paragraph("—",right),Paragraph("0.00",bal_style)])
        table=Table(data,colWidths=[31*mm,49*mm,34*mm,25*mm,25*mm,25*mm],repeatRows=1)
        table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#0f172a")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),.35,colors.HexColor("#cbd5e1")),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f8fafc")]),("VALIGN",(0,0),(-1,-1),"TOP"),("ALIGN",(3,1),(-1,-1),"RIGHT"),("LEFTPADDING",(0,0),(-1,-1),4),("RIGHTPADDING",(0,0),(-1,-1),4),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
        elements.append(table)
        # Repeat a compact category-wise report card section at the very bottom, after the ledger.
        elements += [Spacer(1,8),Paragraph("Category-wise Report Cards",section)]
        bottom_rows=[]
        for i in range(0,len(cats),3):
            row=[]
            for category,ci,ce,total in cats[i:i+3]:
                kind="INCOME" if ci and not ce else ("EXPENSE" if ce and not ci else "MIXED"); bg="#059669" if kind=="INCOME" else ("#e11d48" if kind=="EXPENSE" else "#6366f1")
                detail=f"Income Rs {ci:,.2f}  |  Expense Rs {ce:,.2f}"
                box=Table([[Paragraph(escape(category),card_label)],[Paragraph(f"Rs {total:,.2f}",card_value)],[Paragraph(escape(detail),card_label)]],colWidths=[58*mm])
                box.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),colors.HexColor(bg)),("BOX",(0,0),(-1,-1),.5,colors.HexColor(bg)),("TOPPADDING",(0,0),(-1,-1),4),("BOTTOMPADDING",(0,0),(-1,-1),4)])); row.append(box)
            while len(row)<3: row.append("")
            bottom_rows.append(row)
        if bottom_rows:
            bottom=Table(bottom_rows,colWidths=[59*mm,59*mm,59*mm]); bottom.setStyle(TableStyle([("VALIGN",(0,0),(-1,-1),"TOP"),("LEFTPADDING",(0,0),(-1,-1),2),("RIGHTPADDING",(0,0),(-1,-1),2),("TOPPADDING",(0,0),(-1,-1),2),("BOTTOMPADDING",(0,0),(-1,-1),2)])); elements.append(bottom)
        def footer(canvas,document):
            canvas.saveState(); canvas.setFont("Helvetica",7); canvas.setFillColor(colors.HexColor("#64748b")); canvas.drawRightString(A4[0]-10*mm,7*mm,f"Page {document.page}"); canvas.restoreState()
        doc.build(elements,onFirstPage=footer,onLaterPages=footer)
    except Exception:
        app.logger.exception("PDF report generation error"); buffer.close(); flash("Unable to generate the PDF report. Please try again.","danger"); return redirect(url_for("summary"))
    buffer.seek(0); return send_file(buffer,mimetype="application/pdf",as_attachment=True,download_name=f"financial_report_{view_type}_{datetime.now().strftime('%Y%m%d')}.pdf")

'''
path.write_text(text[:start]+new_route+text[end:],encoding="utf-8")
print("Report route patched successfully")
