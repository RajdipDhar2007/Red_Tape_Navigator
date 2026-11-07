"""Scraped content is untrusted DATA. Strip control chars, neutralise instruction-like text, delimit it."""
import hashlib
import re

_INJECTION = re.compile(
    r"(ignore (all |any )?(previous|prior|above) (instructions|prompts)|disregard .{0,40}instructions|"
    r"you are now|system prompt|new instructions?:|assistant:|<\s*/?\s*(system|assistant|tool)[^>]*>)",
    re.I,
)
_CTRL_CODES = [*range(0x00, 0x09), 0x0B, 0x0C, *range(0x0E, 0x20), *range(0x202A, 0x202F), *range(0x2066, 0x206A)]
_CTRL = re.compile("[" + "".join(re.escape(chr(c)) for c in _CTRL_CODES) + "]")
MAX_CHARS = 60_000


def sanitize(text: str) -> tuple[str, bool]:
    """Return (clean_text, injection_suspected)."""
    text = _CTRL.sub("", text)[:MAX_CHARS]
    flagged = bool(_INJECTION.search(text))
    text = _INJECTION.sub("[removed-instruction-like-text]", text)
    return text, flagged


def content_hash(text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", " ", text).strip().encode()).hexdigest()


def wrap_untrusted(text: str, url: str) -> str:
    """Delimit for inclusion in an LLM prompt. The system prompt states this block is data only."""
    safe = text.replace("</untrusted_source>", "")
    return f'<untrusted_source url="{url}">\n{safe}\n</untrusted_source>'
