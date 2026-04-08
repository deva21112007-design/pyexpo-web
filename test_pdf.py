from fpdf import FPDF
import os

PDF_BG_PATH = os.path.join("static", "pdf_bg.png")

pdf = FPDF()
pdf.set_auto_page_break(auto=False, margin=0)
pdf.add_page()
if os.path.exists(PDF_BG_PATH):
    pdf.image(PDF_BG_PATH, x=0, y=0, w=210, h=297)

pdf.set_xy(10, 12)
pdf.set_font("Arial", "B", 18)
pdf.cell(190, 10, "Test Title text", ln=True, align='C')

pdf.output("test_report.pdf")
print(f"PDF generated. Total pages: {pdf.page_no()}")
