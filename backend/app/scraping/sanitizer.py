"""Scraped content is untrusted DATA. Strip control chars, neutralise instruction-like text, delimit it."""
import hashlib
import re

_INJECTION = re.compile(
    r"(ignore (all |any )?(previous|prior|above) (instructions|prompts)|disregard .{0,40}instructions|"
    r"you are now|system prompt|new instructions?:|assistant:|<\s*/?\s*(system|assistant|tool)[^>]*>)",
    re.I,
)
_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f‪-‮⁦-⁩]")
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
