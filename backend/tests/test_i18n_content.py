"""Hindi / Bengali backend translations: tables stay aligned with the English source, and a full session shows no English
text in the places the interface renders."""
import re

import pytest

from app.i18n_content import detect_language, localize_json, localize_text, pick_language, reminder_title
from app.i18n_content.core import _table
from app.i18n_content.source import SECTIONS, english_sources
from tests.test_api_flow import ANSWERS, start

SCRIPT = {"hi": re.compile(r"[ऀ-ॿ]"), "bn": re.compile(r"[ঀ-৿]")}
LATIN_ONLY_OK = {"PAN", "IFSC", "Aadhaar", "आधार"}  # acronyms and a label that is the same word in the target language


def data(lang):
    from app.i18n_content import data_bn, data_hi

    return {"hi": data_hi, "bn": data_bn}[lang]


@pytest.mark.parametrize("lang", ["hi", "bn"])
@pytest.mark.parametrize("section", SECTIONS)
def test_tables_have_one_entry_per_english_string_in_order(lang, section):
    rows, english = getattr(data(lang), section.upper()), english_sources()[section]
    assert len(rows) == len(english), f"{lang}/{section}: {len(rows)} translations for {len(english)} English strings; add or remove rows"
    for i, ((prefix, text), en) in enumerate(zip(rows, english, strict=True)):
        assert en.startswith(prefix), f"{lang}/{section}[{i}] is misaligned: {prefix!r} vs {en[:40]!r}"
        assert text.strip() and (SCRIPT[lang].search(text) or text in LATIN_ONLY_OK), f"{lang}/{section}[{i}] is not translated: {text[:40]!r}"


@pytest.mark.parametrize("lang", ["hi", "bn"])
def test_fixed_phrases_and_templates_are_translated(lang):
    d = data(lang)
    for en, text in d.FIXED.items():
        assert SCRIPT[lang].search(text), en
    for key in ("authority", "fee", "timeline", "documents", "form_link", "complete_first", "could_not_format", "reminder_status", "reminder_renewal"):
        assert SCRIPT[lang].search(d.TEMPLATES[key]), key
    assert set(d.CITIES) == {"Kolkata", "Mumbai", "Delhi", "Bengaluru", "Chennai", "Hyderabad", "Pune", "Ahmedabad", "Surat"}


def test_language_helpers():
    assert pick_language("hi") == "hi" and pick_language("bn-IN,en;q=0.8") == "bn" and pick_language("en") == "en" and pick_language(None) == "en"
    assert pick_language("fr") == "en"
    assert detect_language("अपने आवेदन") == "hi" and detect_language("আবেদন") == "bn" and detect_language("Check status") == "en"


def test_claim_sentences_translate_with_name_city_and_value():
    hi = localize_text("Fee for Udyam (MSME) Registration: Free of charge", "hi")
    assert hi == "उद्यम (MSME) पंजीकरण का शुल्क: निःशुल्क"
    bn = localize_text("Issuing authority for Fire Safety NOC in Kolkata: West Bengal Fire & Emergency Services", "bn")
    assert "অগ্নি নিরাপত্তা NOC (কলকাতা)" in bn and "পশ্চিমবঙ্গ দমকল" in bn
    docs = localize_text("Documents for Municipal Trade Licence: Trade licence copy; Photo ID", "hi")
    assert docs.startswith("नगरपालिका ट्रेड लाइसेंस के लिए दस्तावेज़:") and "ट्रेड लाइसेंस की प्रति; फोटो पहचान पत्र" in docs
    assert localize_text("Udyam (MSME) Registration: Free MSME identity; used by banks and for scheme eligibility.", "hi").startswith("उद्यम (MSME) पंजीकरण:")
    assert localize_text("Complete first: Udyam (MSME) Registration, GST Registration", "bn") == "আগে সম্পূর্ণ করুন: উদ্যম (MSME) নিবন্ধন, GST নিবন্ধন"
    assert localize_text("Could not format value (bad); left blank.", "hi").startswith("मान का प्रारूप नहीं बन सका (bad)")


def test_document_items_that_contain_semicolons_are_not_split_wrongly():
    item = next(d for d in english_sources()["docs"] if d.startswith("Proof of constitution of the firm (proprietorship declaration;"))
    out = localize_text(f"Documents for Retail Drug (Pharmacy) Licence in Delhi: {item}; Photo ID", "hi")
    assert "HUF विलेख)" in out and out.endswith("फोटो पहचान पत्र") and "(दिल्ली)" in out


def test_unknown_text_and_user_data_are_left_alone():
    assert localize_text("Asha Roy", "hi") == "Asha Roy" and localize_text("My own sentence here", "bn") == "My own sentence here"
    assert localize_json({"a": ["x", 3, None], "b": {"c": "Verify with the authority"}}, "hi")["b"]["c"] == "प्राधिकरण से पुष्टि करें"
    assert localize_json({"b": "Verify with the authority"}, "en") == {"b": "Verify with the authority"}


def test_reminder_titles_follow_the_citizens_language():
    assert reminder_title("status", "GST Registration", "en") == "Check status of your GST Registration application"
    assert SCRIPT["hi"].search(reminder_title("renewal", "Fire Safety NOC", "hi")) and "अग्नि सुरक्षा NOC" in reminder_title("renewal", "Fire Safety NOC", "hi")
    assert "GST নিবন্ধন" in reminder_title("status", "GST Registration", "bn")


def all_licence_prose_is_translated(lang):
    from app.kb.catalog import LICENCES

    t = _table(lang)
    for lic in LICENCES.values():
        assert lic["name"] in t and lic["fee"] in t and lic["timeline"] in t and lic["why"] in t
        assert all(d in t for d in lic["documents"])


@pytest.mark.parametrize("lang", ["hi", "bn"])
def test_every_catalogue_licence_text_has_a_translation(lang):
    all_licence_prose_is_translated(lang)


def user_visible(obj, path=""):
    """Yield (path, string) for the text fields the interface renders."""
    show = ("text", "name", "title", "label", "note", "important", "disclaimer", "consent_statement", "fee", "timeline", "authority", "message")
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, str) and k in show:
                yield f"{path}.{k}", v
            elif k in ("documents", "actions") and isinstance(v, list):
                for i, s in enumerate(v):
                    if isinstance(s, str):
                        yield f"{path}.{k}[{i}]", s
            elif k not in ("data", "citations", "claims_meta"):
                yield from user_visible(v, f"{path}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from user_visible(v, f"{path}[{i}]")


@pytest.mark.parametrize("lang", ["hi", "bn"])
async def test_full_session_shows_no_english_in_the_rendered_fields(client, auth, lang):
    headers, _ = auth
    await client.post("/consent", json={"purpose": "service", "granted": True}, headers=headers)
    goal = {"hi": "मैं कोलकाता में बेकरी खोलना चाहता हूँ", "bn": "আমি কলকাতায় একটি বেকারি খুলতে চাই"}[lang]
    h = {**headers, "Accept-Language": lang}
    s = (await client.post("/sessions", json={"goal": goal, "language": lang}, headers=headers)).json()
    sid = s["id"]
    assert s["parsed"]["activity"] == "bakery", s["parsed"]
    await client.post(f"/sessions/{sid}/research", json={}, headers=headers)
    responses = {"plan": await client.get(f"/sessions/{sid}/checklist", headers=h)}
    for _ in range(40):
        st = (await client.get(f"/sessions/{sid}/interview", headers=headers)).json()
        if not st["questions"]:
            break
        keys = [q["key"] for q in st["questions"]]
        await client.post(f"/sessions/{sid}/interview", json={"answers": {k: ANSWERS[k] for k in keys}}, headers=headers)
    responses["review"] = await client.get(f"/sessions/{sid}/review", headers=h)
    await client.post(f"/sessions/{sid}/review", json={"confirm": True}, headers=headers)
    responses["submission"] = await client.get(f"/sessions/{sid}/submission-checklist", headers=h)
    responses["keyin"] = await client.get(f"/sessions/{sid}/forms/udyam_details/keyin", headers=h)

    leftovers = []
    for name, r in responses.items():
        assert r.status_code == 200, (name, r.text[:200])
        for path, text in user_visible(r.json()):
            if len(text) > 3 and not SCRIPT[lang].search(text) and not text.startswith(("http", "Rs ")) and not re.fullmatch(r"[A-Z]{2,6}", text):
                leftovers.append((name, path, text[:70]))
    assert not leftovers, "English text left in a translated session:\n" + "\n".join(map(str, leftovers[:25]))

    en = (await client.get(f"/sessions/{sid}/checklist", headers=headers)).json()  # English request is untouched
    assert en["plan"]["steps"][0]["name"] == "Udyam (MSME) Registration"


async def test_files_and_images_are_not_touched_by_the_translator(client, auth):
    headers, s = await start(client, auth)
    await client.post(f"/sessions/{s['id']}/research", json={}, headers=headers)
    r = await client.get(f"/sessions/{s['id']}/forms/fssai_form_a/preview.png", headers={**headers, "Accept-Language": "hi"})
    assert r.status_code == 200 and r.content[:4] == b"\x89PNG"
