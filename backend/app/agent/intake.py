"""A. Goal intake: parse a natural-language goal into intent, activity, state, city."""
import re

from pydantic import BaseModel

from app.agent.llm import LLM
from app.core.logging import get_logger
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
    activity_label: str | None = None  # what the citizen called it, when it is outside the rules pack


def _find(text: str, aliases: list[str]) -> bool:
    low = text.lower()
    return any(a.lower() in low for a in aliases)


def next_question(p: ParsedGoal, language: str = "en") -> str | None:
    """The single most useful missing detail: where (city/state) first, then what kind of business."""
    q = QUESTIONS.get(language, QUESTIONS["en"])
    if not p.city and not p.state:
        return q["city_state"]
    if not p.city:
        return q["city"]
    if not p.state:
        return q["state"]
    if not p.activity:
        return q["activity"]
    return None


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
        if m and m.group(1).lower() not in STATE_ALIASES:  # a captured state name is not a city
            city = m.group(1)
    intent = "start_business" if (_INTENT.search(goal) or activity) else "other"
    parsed = ParsedGoal(intent=intent, activity=activity, state=state, city=city, city_known=known)
    parsed.clarifying_question = next_question(parsed, language)
    return parsed


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
            parsed.clarifying_question = next_question(parsed, language)
        except Exception as exc:  # degrade to the rules result, but leave a trace
            get_logger("intake").warning("llm_intake_failed", error_type=type(exc).__name__)
    return parsed


def apply_general_fallback(parsed: ParsedGoal, answer: str) -> ParsedGoal:
    """After the citizen has answered, an activity we still cannot match is not a dead end: give them the baseline
    checklist (Udyam, trade licence, shop registration, GST) and let an officer confirm activity-specific licences.
    Only applies once the location is known, i.e. the business type is the only thing still missing."""
    if parsed.activity is None and parsed.city and parsed.state:
        parsed.activity = "general_business"
        parsed.activity_label = " ".join(answer.split())[:80]
        parsed.clarifying_question = None
    return parsed
