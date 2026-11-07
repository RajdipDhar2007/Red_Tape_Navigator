import io

import pymupdf
import pytest
from pydantic import ValidationError
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas

from app.forms import filler
from app.forms.context import build_context
from app.forms.registry import FieldMap, FormTemplate, get_template, load_templates, required_keys_for
from app.forms.transforms import apply


def vals(**kw):
    base = {k: {"value": v, "source": "user", "sensitive": k in ("aadhaar", "pan", "bank_account_number")} for k, v in kw.items()}
    return filler.build_values(base, build_context({"activity": "bakery", "city": "Kolkata", "state": "West Bengal"}))


FULL = dict(
    business_name="Sweet Crumbs", applicant_name="asha roy", father_name="ravi roy", mobile="9876543210",
    email="a@b.com", residence_address="12 Park St", premises_address="5 College St", premises_pincode="700073",
    food_products="Bread, cakes", annual_turnover="1500000", premises_ownership="rented", aadhaar="234567890124",
    residence_pincode="700016",
)


def test_three_templates_load_and_are_marked_placeholder():
    ts = load_templates()
    assert {"fssai_form_a", "udyam_details", "trade_licence"} <= set(ts)
    for t in ts.values():
        assert t.placeholder and t.pdf_path.exists()
        text = pymupdf.open(t.pdf_path)[0].get_text()
        assert "PLACEHOLDER" in text
        names = {w.field_name for p in pymupdf.open(t.pdf_path) for w in p.widgets()}
        assert {f.pdf_field for f in t.fields if f.keys} <= names, t.id


def test_union_of_required_fields_across_forms():
    union = required_keys_for(["fssai_form_a", "udyam_details", "trade_licence"])
    assert "applicant_name" in union and "pan" in union and "bank_ifsc" in union
    # reused once: one key serves all three forms
    assert "city" not in union and "state" not in union  # derived, never asked
    assert sum(1 for k in union if k == "applicant_name") == 1
    for fid in ("fssai_form_a", "udyam_details", "trade_licence"):
        assert get_template(fid).required_keys() <= union


def test_template_validation_rejects_bad_maps():
    with pytest.raises(ValidationError):
        FieldMap(pdf_field="x", label="x", source="not_a_key")
    with pytest.raises(ValidationError):
        FieldMap(pdf_field="x", label="x", source="mobile", transform="nope")
    with pytest.raises(KeyError):
        get_template("missing")


def test_transforms():
    assert apply("rupees", "1500000") == "15,00,000"
    assert apply("rupees", "950") == "950"
    assert apply("date_ddmmyyyy", "2026-03-05") == "05/03/2026"
    assert apply("checkbox_if:rented", "rented") == "on" and apply("checkbox_if:rented", "owned") == "off"
    assert apply("digits_spaced", "234567890124") == "2345 6789 0124"
    assert apply("label", "sole_proprietor") == "Sole Proprietor"


def test_fill_acroform_report_and_values():
    t = get_template("fssai_form_a")
    res = filler.fill_form(t, vals(**FULL))
    got = filler.read_field_values(res.pdf)
    assert got["applicant_name"] == "Asha Roy" and got["annual_turnover"] == "15,00,000"
    assert got["photo_id_aadhaar"] == "2345 6789 0124"
    by = {r.pdf_field: r for r in res.report}
    # sensitive values never appear in the report in full
    assert "2345 6789 0124" not in str(res.report_dicts()) and by["photo_id_aadhaar"].value.endswith("0124")
    assert by["applicant_name"].status == "filled" and by["applicant_name"].source == "user answer"
    assert by["city"].source == "derived from your goal" and by["city"].status == "filled"
    assert by["kind_of_business"].status == "doubtful"  # confirm=True
    assert by["signature"].status == "unmapped" and by["signature"].value is None
    assert by["email"].status == "filled"
    assert res.warnings and "12 lakh" in res.warnings[0]  # turnover tier warning
    assert res.placeholder


def test_missing_never_guessed():
    t = get_template("fssai_form_a")
    res = filler.fill_form(t, vals(applicant_name="Asha Roy"))
    by = {r.pdf_field: r for r in res.report}
    assert by["mobile"].status == "missing" and by["mobile"].value is None
    assert filler.read_field_values(res.pdf).get("mobile", "") in ("", "None")
    assert res.summary()["missing"] >= 5


def test_non_latin_and_overlong_flagged_not_guessed():
    t = get_template("fssai_form_a")
    res = filler.fill_form(t, vals(**{**FULL, "applicant_name": "আশা রায়", "food_products": "x" * 200}))
    by = {r.pdf_field: r for r in res.report}
    assert by["applicant_name"].status == "doubtful" and "English" in by["applicant_name"].note
    assert by["food_products"].status == "doubtful" and "longer" in by["food_products"].note
    got = filler.read_field_values(res.pdf)
    assert got.get("applicant_name", "") in ("", "None") and got.get("food_products", "") in ("", "None")


def test_checkbox_and_bad_format():
    t = get_template("trade_licence")
    res = filler.fill_form(t, vals(**FULL, premises_area_sqft="400", num_employees="3", date_of_commencement="not-a-date"))
    by = {r.pdf_field: r for r in res.report}
    assert by["date_of_commencement"].status == "doubtful"
    doc = pymupdf.open(stream=res.pdf, filetype="pdf")
    states = {w.field_name: w.field_value for p in doc for w in p.widgets()}
    assert states["premises_rented"] not in ("Off", False) and states["premises_owned"] in ("Off", False)
    assert by["authority"].value.startswith("Kolkata Municipal")


def test_unmapped_pdf_field_reported():
    t = get_template("udyam_details")
    buf = io.BytesIO()
    c = canvas.Canvas(buf)
    c.drawString(10, 100, 'form')
    c.acroForm.textfield(name="extra_unknown_field", x=10, y=10, width=100, height=15)
    c.acroForm.textfield(name="applicant_name", x=10, y=40, width=100, height=15)
    c.save()
    res = filler.fill_form(t, vals(**FULL), pdf_bytes=buf.getvalue())
    assert any(r.pdf_field == "extra_unknown_field" and r.status == "unmapped" for r in res.report)


def test_flat_pdf_overlay_fallback():
    t = FormTemplate(id="flat", title="Flat", authority="x", version="1", pdf="x.pdf", kind="flat", fields=[
        FieldMap(pdf_field="name", label="Name", source="applicant_name", x=100, y=700),
        FieldMap(pdf_field="rent", label="Rent", source="premises_ownership", transform="checkbox_if:rented", x=100, y=650),
    ])
    w = PdfWriter()
    w.add_blank_page(595, 842)
    buf = io.BytesIO()
    w.write(buf)
    res = filler.fill_form(t, vals(applicant_name="asha roy", premises_ownership="rented"), pdf_bytes=buf.getvalue())
    text = PdfReader(io.BytesIO(res.pdf)).pages[0].extract_text()
    assert "asha roy" in text and "[X]" in text


def test_preview_png():
    res = filler.fill_form(get_template("udyam_details"), vals(**FULL))
    png = filler.render_preview_png(res.pdf)
    assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_placeholder_generator_builds_fillable_pdf():
    from app.forms.placeholder import build_placeholder_pdf

    t = get_template("trade_licence")
    pdf = build_placeholder_pdf(t)
    names = {w.field_name for p in pymupdf.open(stream=pdf, filetype="pdf") for w in p.widgets()}
    assert {f.pdf_field for f in t.fields if f.keys} <= names
