from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")
start = text.index('@app.route("/summary/report")')
end = text.index('@app.route("/sitemap.xml")', start)

# Keep the existing generated report logic, but replace only the top summary table styling
# so its three boxes visually match the final-summary boxes.
old = '''summary.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#f1f5f9")),("GRID",(0,0),(-1,-1),.5,colors.HexColor("#cbd5e1")),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,0),6),("BOTTOMPADDING",(0,0),(-1,0),6),("TOPPADDING",(0,1),(-1,1),8),("BOTTOMPADDING",(0,1),(-1,1),8)]))'''
new = '''summary.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(0,0),colors.HexColor("#059669")),
            ("BACKGROUND",(1,0),(1,0),colors.HexColor("#e11d48")),
            ("BACKGROUND",(2,0),(2,0),colors.HexColor("#2563eb")),
            ("BACKGROUND",(0,1),(0,1),colors.HexColor("#ecfdf5")),
            ("BACKGROUND",(1,1),(1,1),colors.HexColor("#fff1f2")),
            ("BACKGROUND",(2,1),(2,1),colors.HexColor("#eff6ff")),
            ("TEXTCOLOR",(0,0),(-1,0),colors.white),
            ("BOX",(0,0),(-1,-1),.7,colors.HexColor("#cbd5e1")),
            ("INNERGRID",(0,0),(-1,-1),.45,colors.HexColor("#cbd5e1")),
            ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
            ("ALIGN",(0,0),(-1,-1),"CENTER"),
            ("TOPPADDING",(0,0),(-1,0),7),
            ("BOTTOMPADDING",(0,0),(-1,0),7),
            ("TOPPADDING",(0,1),(-1,1),10),
            ("BOTTOMPADDING",(0,1),(-1,1),10),
        ]))'''
if old not in text:
    raise SystemExit("Expected summary styling block not found")
text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
