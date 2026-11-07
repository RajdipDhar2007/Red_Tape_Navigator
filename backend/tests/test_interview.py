import pytest
from sqlalchemy import select

from app.db.models import Answer, NavSession, User
from app.db.session import maker
from app.interview import engine, memory
from app.interview import validators as v
from app.interview.fields import FIELDS


def test_validators():
    assert v.pincode("700 001") == "700001"
    for bad in ["012345", "12345", "abcdef", "7000011"]:
        with pytest.raises(ValueError):
            v.pincode(bad)
    assert v.pan("abcpe1234f") == "ABCPE1234F"
    for bad in ["ABCDE1234", "1234567890", "ABCXE1234F"]:
        with pytest.raises(ValueError):
            v.pan(bad)
    assert v.aadhaar(" ".join([make_valid_aadhaar()[i:i + 4] for i in (0, 4, 8)])) == make_valid_aadhaar()
    with pytest.raises(ValueError):
        v.aadhaar("123456789012")  # starts with 1
    with pytest.raises(ValueError):
        v.aadhaar("234567890123")  # bad checksum
    assert v.mobile("+91 98765-43210") == "9876543210"
    for bad in ["1234567890", "98765", "abcdefghij"]:
        with pytest.raises(ValueError):
            v.mobile(bad)
    assert v.email(" A@B.com ") == "a@b.com"
    with pytest.raises(ValueError):
        v.email("not-an-email")
    assert v.dob("01/02/1990") == "1990-02-01"
    for bad in ["31/02/1990", "01/01/2999", "01/01/2015", "x"]:
        with pytest.raises(ValueError):
            v.dob(bad)
    assert v.ifsc("sbin0001234") == "SBIN0001234"
    assert v.positive_int("12,50,000") == "1250000"
    assert v.yes_no("हां") == "yes"
    with pytest.raises(ValueError):
        v.text("<script>")


def make_valid_aadhaar() -> str:
    for n in range(10**9, 10**9 + 1000):
        s = "2" + str(n)[:10]
        for d in "0123456789":
            if v.verhoeff_ok(s + d):
                return s + d
    raise AssertionError


async def _session(language="en"):
    async with maker()() as db:
        u = User(email="i@example.com", password_hash="x")
        db.add(u)
        await db.commit()
        ns = NavSession(user_id=u.id, goal="bakery in Kolkata", language=language, parsed={"activity": "bakery", "city": "Kolkata", "state": "West Bengal"})
        db.add(ns)
        await db.commit()
        return ns.id


async def test_memory_reuse_encrypt_edit_never_twice(client):
    sid = await _session()
    aad = make_valid_aadhaar()
    async with maker()() as db:
        assert await memory.set_answer(db, sid, "pan", "abcpe1234f") == "ABCPE1234F"
        await memory.set_answer(db, sid, "aadhaar", aad)
        raw = (await db.execute(select(Answer).where(Answer.key == "pan"))).scalar_one()
        assert raw.sensitive and "ABCPE1234F" not in raw.value
        masked = await memory.get_answers(db, sid)
        assert masked["pan"]["value"].endswith("234F") and "ABCP" not in masked["pan"]["value"]
        assert aad not in str(masked)
        assert (await memory.get_answers(db, sid, reveal=True))["aadhaar"]["value"] == aad
        await memory.set_answer(db, sid, "pan", "AAAPA1111A")  # edit overwrites, no duplicate row
        assert len((await db.execute(select(Answer).where(Answer.key == "pan"))).scalars().all()) == 1
        with pytest.raises(memory.AnswerError) as e:
            await memory.set_answer(db, sid, "pan", "bad")
        assert e.value.code == "invalid_pan"
        with pytest.raises(memory.AnswerError):
            await memory.set_answer(db, sid, "is_admin", "true")  # no mass-assignment of unknown keys
        await memory.delete_answer(db, sid, "pan")
        assert "pan" not in await memory.get_answers(db, sid)


async def test_engine_asks_only_missing_two_at_a_time_and_resumes(client):
    sid = await _session("hi")
    required = {"applicant_name", "father_name", "mobile", "pan", "premises_pincode", "city"}
    async with maker()() as db:
        ns = await db.get(NavSession, sid)
        await memory.seed_derived(db, ns)
        st = await engine.state(db, ns, required)
        assert [q["key"] for q in st["questions"]] == ["applicant_name", "father_name"]
        assert st["questions"][0]["question"] == FIELDS["applicant_name"].q["hi"]
        assert "city" not in st["missing"]  # derived, never asked
        res = await engine.submit(db, ns, {"applicant_name": "Asha Roy", "father_name": "Ravi Roy", "mobile": "12"})
        assert set(res["saved"]) == {"applicant_name", "father_name"} and "mobile" in res["errors"]
        assert "मोबाइल" in res["errors"]["mobile"]["message"]
        st = await engine.state(db, ns, required)
        assert [q["key"] for q in st["questions"]] == ["pan"]  # identity first; sensitive asked alone
        await memory.skip(db, ns, "pan")  # skip for now
        st = await engine.state(db, ns, required)
        assert [q["key"] for q in st["questions"]] == ["mobile"]  # father/applicant not asked again
        await engine.submit(db, ns, {"mobile": "9876543210"})
        st = await engine.state(db, ns, required)
        assert [q["key"] for q in st["questions"]] == ["premises_pincode"]
        await engine.submit(db, ns, {"premises_pincode": "700001"})
        st = await engine.state(db, ns, required)
        assert st["questions"] == [] and not st["complete"] and st["ready_for_review"] and st["progress"]["skipped"] == ["pan"]
        st = await engine.state(db, ns, required, include_skipped=True)  # resume
        assert [q["key"] for q in st["questions"]] == ["pan"]
        await engine.submit(db, ns, {"pan": "ABCPE1234F"})
        st = await engine.state(db, ns, required)
        assert st["complete"] and st["progress"]["percent"] == 100
        with pytest.raises(memory.AnswerError):
            await memory.skip(db, ns, "nonsense")


def test_every_field_has_all_languages():
    for f in FIELDS.values():
        assert set(f.q) == set(f.label) == {"en", "bn", "hi"} and all(f.q.values())
    assert engine.error_message("invalid_pan", "xx") == v.MESSAGES["en"]["invalid_pan"]
