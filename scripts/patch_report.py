from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

start = text.index('        summary = Table(')
end = text.index('        elements += [summary, Spacer(1,4), Paragraph("Category-wise Summary", section)]', start)

new_summary = '''        # PDF TOP CARDS — intentionally the same 3-box shape as Final Summary.
        summary = Table([[
            Paragraph("TOTAL INCOME", ParagraphStyle("sh1", parent=head, alignment=1)),
            Paragraph("TOTAL EXPENSE", ParagraphStyle("sh2", parent=head, alignment=1)),
            Paragraph("FINAL BALANCE", ParagraphStyle("sh3", parent=head, alignment=1))
        ], [
            Paragraph(f"Rs {total_income:,.2f}", ParagraphStyle("si", parent=value, textColor=colors.HexColor("#059669"), alignment=1)),
            Paragraph(f"Rs {total_expense:,.2f}", ParagraphStyle("se", parent=value, textColor=colors.HexColor("#e11d48"), alignment=1)),
            Paragraph(f"Rs {running_balance:,.2f}", ParagraphStyle("sb", parent=value, textColor=colors.HexColor("#2563eb"), alignment=1))
        ]], colWidths=[58*mm,58*mm,58*mm])
        summary.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#2563eb")),
            ("TEXTCOLOR", (0,0), (-1,0), colors.white),
            ("BACKGROUND", (0,1), (0,1), colors.HexColor("#ecfdf5")),
            ("BACKGROUND", (1,1), (1,1), colors.HexColor("#fff1f2")),
            ("BACKGROUND", (2,1), (2,1), colors.HexColor("#eff6ff")),
            ("BOX", (0,0), (-1,-1), .6, colors.HexColor("#cbd5e1")),
            ("INNERGRID", (0,0), (-1,-1), .4, colors.HexColor("#cbd5e1")),
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (0,0), (-1,-1), "CENTER"),
            ("TOPPADDING", (0,0), (-1,0), 7),
            ("BOTTOMPADDING", (0,0), (-1,0), 7),
            ("TOPPADDING", (0,1), (-1,1), 10),
            ("BOTTOMPADDING", (0,1), (-1,1), 10),
        ]))
'''

text = text[:start] + new_summary + text[end:]
path.write_text(text, encoding="utf-8")
print("PDF report: top summary cards now use the exact final-summary 3-box layout")
