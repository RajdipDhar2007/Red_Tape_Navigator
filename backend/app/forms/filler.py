"""E. Form filler: map answers into official form PDFs and emit a field-by-field provenance report.

Never guesses: a missing value leaves the field blank and is reported as `missing`. Non-Latin text is not
transliterated automatically (that would be a guess); it is flagged `doubtful` and left blank.
"""
import io
from dataclasses import asdict, dataclass

import pymupdf
from pypdf import PdfReader, PdfWriter
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from app.core.crypto import mask
from app.forms import transforms
from app.forms.registry import FieldMap, FormTemplate
from app.interview.fields import FIELDS

SOURCE_LABELS = {"user": "user answer", "derived": "derived from your goal", "document": "document (DigiLocker)"}


@dataclass
class FieldReport:
    pdf_field: str
    label: str
    status: str  # filled | missing | doubtful | unmapped
    value: str | None  # display value (sensitive values masked)
    source: str | None  # user answer | document | derived
    source_keys: list[str]
    note: str | None = None


@dataclass
class FillResult:
    form_id: str
    title: str
    placeholder: bool
    pdf: bytes
    report: list[FieldReport]
    warnings: list[str]

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for r in self.report:
            counts[r.status] = counts.get(r.status, 0) + 1
        return counts

    def report_dicts(self) -> list[dict]:
        return [asdict(r) for r in self.report]


def _resolve(f: FieldMap, values: dict[str, dict]) -> tuple[str | None, str | None, bool, str | None]:
    """-> (raw_value, provenance, sensitive, problem)"""
    parts, srcs, sens = [], set(), False
    for k in f.keys:
        item = values.get(k)
        if not item or not str(item["value"]).strip():
            return None, None, False, None
        parts.append(str(item["value"]))
        srcs.add(item.get("source", "user"))
        sens = sens or bool(item.get("sensitive") or (k in FIELDS and FIELDS[k].sensitive))
    raw = ", ".join(parts)
    prov = "derived" if (len(parts) > 1 or srcs == {"derived"}) else next(iter(srcs))
    return raw, prov, sens, None


def build_values(answers: dict[str, dict], context: dict[str, str]) -> dict[str, dict]:
    vals = dict(answers)
    for k, v in context.items():
        vals.setdefault(k, {"value": v, "source": "derived", "sensitive": False})
    return vals


def plan_fields(t: FormTemplate, values: dict[str, dict]) -> tuple[dict[str, str], list[FieldReport], list[str]]:
    """Compute PDF field values + report without touching the PDF."""
    out: dict[str, str] = {}
    report: list[FieldReport] = []
    for f in t.fields:
        if not f.keys:
            report.append(FieldReport(f.pdf_field, f.label, "unmapped", None, None, [], f.note or "Not auto-filled: complete by hand (e.g. signature)."))
            continue
        raw, prov, sens, _ = _resolve(f, values)
        if raw is None:
            miss = "missing" if f.required else "unmapped"
            why = "Required value not provided; field left blank." if f.required else "Optional value not provided; left blank."
            report.append(FieldReport(f.pdf_field, f.label, miss, None, None, f.keys, why))
            continue
        try:
            val = transforms.apply(f.transform, raw)
        except (ValueError, KeyError) as exc:
            report.append(FieldReport(f.pdf_field, f.label, "doubtful", raw if not sens else mask(raw), SOURCE_LABELS.get(prov or "", prov), f.keys, f"Could not format value ({exc}); left blank."))
            continue
        shown = mask(val) if sens else val
        if not val.isascii() and not f.transform.startswith("checkbox"):
            report.append(FieldReport(f.pdf_field, f.label, "doubtful", shown, SOURCE_LABELS.get(prov or "", prov), f.keys, "Official PDF expects English letters; please re-enter in English. Left blank (not transliterated automatically)."))
            continue
        if f.max_len and len(val) > f.max_len:
            report.append(FieldReport(f.pdf_field, f.label, "doubtful", shown, SOURCE_LABELS.get(prov or "", prov), f.keys, f"Value is longer than the {f.max_len}-character box; left blank to avoid truncation."))
            continue
        status: str = "filled"
        note: str | None = None
        if f.confirm:
            status, note = "doubtful", "Derived or uncertain value: please confirm before signing."
        out[f.pdf_field] = val
        report.append(FieldReport(f.pdf_field, f.label, status, shown, SOURCE_LABELS.get(prov or "", prov), f.keys, note))
    warnings = []
    for w in t.warnings:
        item = values.get(w.key)
        if item and str(item["value"]).isdigit() and int(item["value"]) > w.gt:
            warnings.append(w.message)
    return out, report, warnings


def _fill_acroform(pdf: bytes, fields: dict[str, str]) -> tuple[bytes, list[str]]:
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    seen: set[str] = set()
    for page in doc:  # type: ignore[attr-defined]
        for w in page.widgets() or []:
            seen.add(w.field_name)
            if w.field_name not in fields:
                continue
            v = fields[w.field_name]
            if w.field_type == pymupdf.PDF_WIDGET_TYPE_CHECKBOX:
                w.field_value = w.on_state() if v == "on" else "Off"
            else:
                w.field_value = v
            w.update()
    buf = io.BytesIO()
    doc.save(buf, garbage=3, deflate=True)
    doc.close()
    return buf.getvalue(), sorted(seen)


def _fill_overlay(pdf: bytes, t: FormTemplate, fields: dict[str, str]) -> bytes:
    """Fallback for flat (non-fillable) PDFs: draw text at template coordinates with reportlab and merge."""
    reader = PdfReader(io.BytesIO(pdf))
    writer = PdfWriter()
    by_page: dict[int, list[FieldMap]] = {}
    for f in t.fields:
        if f.pdf_field in fields and f.x is not None and f.y is not None:
            by_page.setdefault(f.page, []).append(f)
    for page in reader.pages:
        writer.add_page(page)
    for i, page in enumerate(writer.pages):
        if i not in by_page:
            continue
        w, h = float(page.mediabox.width), float(page.mediabox.height)
        buf = io.BytesIO()
        c = canvas.Canvas(buf, pagesize=(w, h) if w and h else A4)
        for f in by_page[i]:
            c.setFont("Helvetica", f.size)
            val = fields[f.pdf_field]
            c.drawString(f.x, f.y, "[X]" if val == "on" else "" if val == "off" else val)
        c.save()
        buf.seek(0)
        page.merge_page(PdfReader(buf).pages[0])
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def fill_form(t: FormTemplate, values: dict[str, dict], pdf_bytes: bytes | None = None, *, official: bool = False) -> FillResult:
    fields, report, warnings = plan_fields(t, values)
    pdf = pdf_bytes if pdf_bytes is not None else t.pdf_path.read_bytes()
    if t.kind == "acroform":
        filled, pdf_field_names = _fill_acroform(pdf, fields)
        mapped = {f.pdf_field for f in t.fields}
        for name in pdf_field_names:
            if name not in mapped:  # field exists in the PDF but the template does not map it
                report.append(FieldReport(name, name, "unmapped", None, None, [], "PDF field has no mapping in the template; left blank."))
    else:
        filled = _fill_overlay(pdf, t, fields)
    title = t.title.replace(" (PLACEHOLDER)", "") if official else t.title
    return FillResult(t.id, title, t.placeholder and not official, filled, report, warnings)


def render_preview_png(pdf: bytes, page: int = 0, zoom: float = 1.4) -> bytes:
    doc = pymupdf.open(stream=pdf, filetype="pdf")
    pix = doc[page].get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
    data = pix.tobytes("png")
    doc.close()
    return data


def read_field_values(pdf: bytes) -> dict[str, str]:
    return {k: str(v.get("/V", "")) for k, v in (PdfReader(io.BytesIO(pdf)).get_fields() or {}).items()}
