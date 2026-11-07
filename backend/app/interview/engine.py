"""D. Interview engine: ask only for what is missing, 1-2 questions at a time, never twice."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import NavSession
from app.interview import memory
from app.interview.fields import DERIVED, FIELDS, ORDER
from app.interview.validators import MESSAGES

LANGS = ("en", "bn", "hi")


def _lang(language: str) -> str:
    return language if language in LANGS else "en"


def question_for(key: str, language: str) -> dict:
    f = FIELDS[key]
    lang = _lang(language)
    return {
        "key": key, "question": f.q[lang], "label": f.label[lang], "sensitive": f.sensitive,
        "options": list(f.options), "group": f.group,
    }


def error_message(code: str, language: str) -> str:
    return MESSAGES[_lang(language)].get(code, MESSAGES["en"].get(code, code))


async def state(db: AsyncSession, ns: NavSession, required: set[str], *, max_questions: int = 2, include_skipped: bool = False) -> dict:
    answers = await memory.get_answers(db, ns.id)
    skipped = set(ns.skipped or [])
    need = {k for k in required if k in FIELDS and k not in DERIVED}
    missing = sorted((k for k in need if k not in answers), key=lambda k: ORDER[k])
    pending = [k for k in missing if k not in skipped]
    queue = pending if (pending or not include_skipped) else [k for k in missing if k in skipped]
    batch: list[str] = []
    for k in queue:
        if FIELDS[k].sensitive:  # sensitive fields are always asked alone
            if not batch:
                batch.append(k)
            break
        if batch and FIELDS[batch[0]].group != FIELDS[k].group:
            break
        batch.append(k)
        if len(batch) >= max_questions:
            break
    total = len(need)
    answered = len(need & set(answers))
    return {
        "questions": [question_for(k, ns.language) for k in batch],
        "progress": {"answered": answered, "total": total, "skipped": sorted(skipped & set(missing)), "percent": 100 if total == 0 else round(100 * answered / total)},
        "complete": not missing,
        "ready_for_review": not pending,  # skipped items allowed to be left for later, flagged at review
        "missing": missing,
    }


async def submit(db: AsyncSession, ns: NavSession, answers: dict[str, str]) -> dict:
    ok, errors = {}, {}
    for key, raw in answers.items():
        try:
            val = await memory.set_answer(db, ns.id, key, str(raw))
            ok[key] = "***" if FIELDS[key].sensitive else val
        except memory.AnswerError as exc:
            errors[key] = {"code": exc.code, "message": error_message(exc.code, ns.language)}
    return {"saved": ok, "errors": errors}
