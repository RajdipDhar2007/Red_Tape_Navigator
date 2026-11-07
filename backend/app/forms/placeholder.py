"""Generate clearly-marked PLACEHOLDER fillable PDFs from template JSON.

Real forms: drop the official PDF next to the JSON, set "placeholder": false and fix the pdf_field names
(see docs/INTEGRATIONS.md). Run `python scripts/make_placeholder_forms.py` to regenerate placeholders.
"""
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.forms.registry import FormTemplate, load_templates

W, H = A4


def build_placeholder_pdf(t: FormTemplate) -> bytes:
    import io

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    c.setFillColorRGB(0.8, 0.1, 0.1)
    c.setFont("Helvetica-Bold", 11)
    c.drawString(40, H - 30, "PLACEHOLDER FORM - NOT AN OFFICIAL GOVERNMENT DOCUMENT - DO NOT SUBMIT")
    c.setFillColorRGB(0, 0, 0)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(40, H - 55, t.title[:90])
    c.setFont("Helvetica", 9)
    c.drawString(40, H - 70, f"Authority: {t.authority}   |   template {t.id} v{t.version}")
    y = H - 105
    for f in t.fields:
        if y < 60:
            c.showPage()
            y = H - 60
        c.setFont("Helvetica", 8.5)
        c.drawString(40, y + 12, f.label[:70])
        checkbox = f.transform.startswith("checkbox_if")
        if checkbox:
            c.acroForm.checkbox(name=f.pdf_field, x=40, y=y - 12, size=12, buttonStyle="check", borderWidth=1, forceBorder=True)
            y -= 34
        else:
            tall = f.max_len is not None and f.max_len > 80
            hgt = 26 if tall else 16
            c.acroForm.textfield(
                name=f.pdf_field, x=40, y=y - hgt, width=500, height=hgt, fontSize=9,
                borderWidth=1, forceBorder=True, maxlen=f.max_len or 200, fieldFlags="multiline" if tall else "",
            )
            y -= hgt + 26
    c.save()
    return buf.getvalue()


def write_all() -> list[str]:
    written = []
    for t in load_templates().values():
        t.pdf_path.write_bytes(build_placeholder_pdf(t))
        written.append(t.pdf)
    return written
