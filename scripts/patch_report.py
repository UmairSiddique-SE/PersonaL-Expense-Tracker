from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

# Remove the injected top summary cards and leave the accounting sections:
# Category-wise Summary -> Transaction Ledger -> Final Summary.
for marker in [
    '        elements += [summary, Spacer(1,4), Paragraph("Category-wise Summary", section)]',
    '        elements += [summary, Spacer(1, 4), Paragraph("Category-wise Summary", section)]',
]:
    if marker in text:
        before, after = text.split(marker, 1)
        start = before.rfind('        summary = Table(')
        if start >= 0:
            text = before[:start] + '        elements += [Paragraph("Category-wise Summary", section)]' + after

# Remove an old duplicate category-card appendix if it exists.
card_start = text.find('        Paragraph("Category-wise Report Cards", section)')
if card_start >= 0:
    final_start = text.find('        Paragraph("Final Summary", section)', card_start)
    if final_start >= 0:
        text = text[:card_start] + text[final_start:]

path.write_text(text, encoding="utf-8")
print("PDF report simplified: no top cards; no duplicate category cards; category table, ledger and final summary retained")
