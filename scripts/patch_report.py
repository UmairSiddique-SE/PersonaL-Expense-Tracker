from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

start = text.index('        summary = Table(')
end = text.index('        elements += [summary, Spacer(1,4), Paragraph("Category-wise Summary", section)]', start)

new_summary = '''        # Top summary uses the exact same 3-box visual treatment as the final summary.\n        summary = Table([[\n            Paragraph("TOTAL INCOME", ParagraphStyle("sh1", parent=head, alignment=1)),\n            Paragraph("TOTAL EXPENSE", ParagraphStyle("sh2", parent=head, alignment=1)),\n            Paragraph("FINAL BALANCE", ParagraphStyle("sh3", parent=head, alignment=1))\n        ], [\n            Paragraph(f"Rs {total_income:,.2f}", ParagraphStyle("si", parent=value, textColor=colors.HexColor("#059669"), alignment=1)),\n            Paragraph(f"Rs {total_expense:,.2f}", ParagraphStyle("se", parent=value, textColor=colors.HexColor("#e11d48"), alignment=1)),\n            Paragraph(f"Rs {running_balance:,.2f}", ParagraphStyle("sb", parent=value, textColor=colors.HexColor("#2563eb"), alignment=1))\n        ]], colWidths=[58*mm,58*mm,58*mm])\n        summary.setStyle(TableStyle([\n            # Blue heading strip, matching the requested report style.\n            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2563eb")),\n            ("TEXTCOLOR", (0,0), (-1,0), colors.white),\n            # Keep the requested income/expense/balance colors.\n            ("BACKGROUND", (0,1), (0,1), colors.HexColor("#ecfdf5")),\n            ("BACKGROUND", (1,1), (1,1), colors.HexColor("#fff1f2")),\n            ("BACKGROUND", (2,1), (2,1), colors.HexColor("#eff6ff")),\n            ("BOX", (0,0), (-1,-1), .6, colors.HexColor("#cbd5e1")),\n            ("INNERGRID", (0,0), (-1,-1), .4, colors.HexColor("#cbd5e1")),\n            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),\n            ("ALIGN", (0,0), (-1,-1), "CENTER"),\n            ("TOPPADDING", (0,0), (-1,0), 7),\n            ("BOTTOMPADDING", (0,0), (-1,0), 7),\n            ("TOPPADDING", (0,1), (-1,1), 10),\n            ("BOTTOMPADDING", (0,1), (-1,1), 10),\n        ]))\n'''

text = text[:start] + new_summary + text[end:]
path.write_text(text, encoding="utf-8")
print("Applied final-style top summary boxes to PDF report")
