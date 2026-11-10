"""Invoice PDF (reportlab). Seller details, GSTIN and SAC come from settings; blank values are shown as 'not set' rather than invented.
Marked DRAFT until the owner has set company details, because a tax invoice needs the seller's GSTIN and SAC code."""
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.core.config import Settings
from app.db.models import Invoice


def rupees(paise: int) -> str:
    return f"Rs {paise // 100:,}.{paise % 100:02d}"


def render_invoice(inv: Invoice, s: Settings, buyer_email: str) -> bytes:
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    complete = bool(s.company_name and s.company_address and s.company_gstin and s.invoice_sac_code)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, h - 60, "Tax invoice" if complete else "Invoice (DRAFT: seller GSTIN or SAC not set)")
    c.setFont("Helvetica", 10)
    y = h - 90
    for line in (
        f"Invoice number: {inv.number}", f"Date: {inv.issued_at:%d %b %Y}",
        f"Seller: {s.company_name or 'not set'}", f"Address: {s.company_address or 'not set'}",
        f"GSTIN: {s.company_gstin or 'not set'}    SAC: {s.invoice_sac_code or 'not set'}",
        f"Billed to: {buyer_email}", "",
        f"Description: {inv.description}", f"Taxable value: {rupees(inv.taxable_paise)}",
        f"GST @ {inv.gst_percent}%: {rupees(inv.gst_paise)}", f"Total: {rupees(inv.total_paise)}",
        f"Status: {inv.status}",
    ):
        c.drawString(50, y, line)
        y -= 16
    c.setFont("Helvetica-Oblique", 8)
    c.drawString(50, 60, "Red Tape Navigator gives guidance, not legal advice. Computer-generated invoice.")
    c.save()
    return buf.getvalue()
