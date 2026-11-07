"""A. Goal intake: parse a natural-language goal into intent, activity, state, city."""
import re

from pydantic import BaseModel

from app.agent.llm import LLM
from app.kb.catalog import ACTIVITIES, ACTIVITY_KEYWORDS, CITIES, STATE_ALIASES

QUESTIONS = {
    "en": {
        "city_state": "Which city and state will the business be in?",
        "city": "Which city or municipality will the business be in?",
        "state": "Which state is that in?",
        "activity": "What kind of business or activity is this (for example bakery, restaurant, tailoring)?",
    },
    "bn": {
        "city_state": "ব্যবসাটি কোন শহর ও রাজ্যে হবে?",
        "city": "ব্যবসাটি কোন শহর বা পৌরসভায় হবে?",
        "state": "এটি কোন রাজ্যে?",
        "activity": "এটি কী ধরনের ব্যবসা (যেমন বেকারি, রেস্তোরাঁ, দর্জি)?",
    },
    "hi": {
        "city_state": "व्यवसाय किस शहर और राज्य में होगा?",
        "city": "व्यवसाय किस शहर या नगरपालिका में होगा?",
        "state": "यह किस राज्य में है?",
        "activity": "यह किस प्रकार का व्यवसाय है (जैसे बेकरी, रेस्टोरेंट, सिलाई)?",
    },
}
_INTENT = re.compile(r"\b(open|start|begin|set up|setup|launch|register|apply)\b|খুলতে|শুরু|खोल|शुरू", re.I)
_FREE_CITY = re.compile(r"\bin\s+([A-Z][A-Za-z]+(?:\s[A-Z][A-Za-z]+)?)")


class ParsedGoal(BaseModel):
    intent: str = "start_business"
    activity: str | None = None
    state: str | None = None
    city: str | None = None
    city_known: bool = False
    clarifying_question: str | None = None


def _find(text: str, aliases: list[str]) -> bool:
    low = text.lower()
    return any(a.lower() in low for a in aliases)


def parse_goal_rules(goal: str, language: str = "en") -> ParsedGoal:
    low = goal.lower()
    activity = None
    best = 0
    for act, words in ACTIVITY_KEYWORDS.items():
        for w in words:
            if w.lower() in low and len(w) > best:
                activity, best = act, len(w)
    city_key = None
    for key, c in CITIES.items():
        if _find(goal, c["aliases"]):
            city_key = key
            break
    state = None
    for alias, name in STATE_ALIASES.items():
        if alias in low:
            state = name
            break
    city = None
    known = False
    if city_key:
        city, known = CITIES[city_key]["label"], True
        state = state or CITIES[city_key]["state"]
    else:
        m = _FREE_CITY.search(goal)
        if m and m.group(1).lower() not in {a for a in STATE_ALIASES} and not state:
            city = m.group(1)
    intent = "start_business" if (_INTENT.search(goal) or activity) else "other"
    q = QUESTIONS.get(language, QUESTIONS["en"])
    question = None
    if not city and not state:
        question = q["city_state"]
    elif not city:
        question = q["city"]
    elif not state:
        question = q["state"]
    return ParsedGoal(intent=intent, activity=activity, state=state, city=city, city_known=known, clarifying_question=question)


class _LLMParse(BaseModel):
    intent: str
    activity: str | None
    state: str | None
    city: str | None


async def parse_goal(goal: str, language: str = "en", llm: LLM | None = None) -> ParsedGoal:
    """Rules first (deterministic, testable); the LLM only fills gaps and is validated against the catalogue."""
    parsed = parse_goal_rules(goal, language)
    if llm and llm.available and (parsed.activity is None or parsed.state is None or parsed.city is None):
        try:
            out = await llm.structured(
                "Extract fields from the user's goal. Activity must be one of: " + ", ".join(ACTIVITIES) + " or null. "
                "Use null when not stated; never guess.",
                f"<user_goal>{goal[:1000]}</user_goal>", _LLMParse,
            )
            if parsed.activity is None and out.activity in ACTIVITIES:
                parsed.activity = out.activity
            parsed.city = parsed.city or out.city
            parsed.state = parsed.state or out.state
            q = QUESTIONS.get(language, QUESTIONS["en"])
            parsed.clarifying_question = (
                q["city_state"] if not parsed.city and not parsed.state
                else q["city"] if not parsed.city else q["state"] if not parsed.state else None
            )
        except Exception:  # noqa: BLE001 - degrade to rules result
            pass
    return parsed
