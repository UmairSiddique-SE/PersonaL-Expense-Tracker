from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

start = text.index('        summary = Table(')
end = text.index('        elements += [summary, Spacer(1,4), Paragraph("Category-wise Summary", section)]', start)

new_summary = '''        summary = Table([[\n            Paragraph("Total Income", head),\n            Paragraph("Total Expense", head),\n            Paragraph("Final Balance", head)\n        ], [\n            Paragraph(f"Rs {total_income:,.2f}", ParagraphStyle("si", parent=value, textColor=colors.HexColor("#059669"))),\n            Paragraph(f"Rs {total_expense:,.2f}", ParagraphStyle("se", parent=value, textColor=colors.HexColor("#e11d48"))),\n            Paragraph(f"Rs {running_balance:,.2f}", ParagraphStyle("sb", parent=value, textColor=colors.HexColor("#2563eb")))\n        ]], colWidths=[58*mm,58*mm,58*mm])\n        summary.setStyle(TableStyle([\n            ("BACKGROUND",(0,0),(0,0),colors.HexColor("#2563eb")),\n            ("BACKGROUND",(1,0),(1,0),colors.HexColor("#2563eb")),\n            ("BACKGROUND",(2,0),(2,0),colors.HexColor("#2563eb")),\n            ("BACKGROUND",(0,1),(0,1),colors.HexColor("#ecfdf5")),\n            ("BACKGROUND",(1,1),(1,1),colors.HexColor("#fff1f2")),\n            ("BACKGROUND",(2,1),(2,1),colors.HexColor("#eff6ff")),\n            ("TEXTCOLOR",(0,0),(-1,0),colors.white),\n            ("BOX",(0,0),(-1,-1),.7,colors.HexColor("#cbd5e1")),\n            ("INNERGRID",(0,0),(-1,-1),.45,colors.HexColor("#cbd5e1")),\n            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),\n            ("ALIGN",(0,0),(-1,-1),"CENTER"),\n            ("TOPPADDING",(0,0),(-1,0),7),\n            ("BOTTOMPADDING",(0,0),(-1,0),7),\n            ("TOPPADDING",(0,1),(-1,1),10),\n            ("BOTTOMPADDING",(0,1),(-1,1),10),\n        ]))\n'''

text = text[:start] + new_summary + text[end:]
path.write_text(text, encoding="utf-8")
print("Applied forced top summary card layout to app.py")
