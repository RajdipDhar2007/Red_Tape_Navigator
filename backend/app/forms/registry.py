"""Form template registry. Each official form = JSON field map + PDF.

Template JSON schema (see docs/INTEGRATIONS.md "Adding a real form"):
  id, title, authority, version, placeholder (bool), pdf (filename next to the JSON), kind ("acroform"|"flat"),
  warnings: [{when:{key,gt}, message}], fields: [{pdf_field, label, source | sources, transform, validate,
  required, confirm, max_len, page, x, y, size}]
`source` is a key from the interview field catalogue or a context key (city, state, business_type, ...).
"""
import json
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

from app.forms.transforms import TRANSFORMS, parse_transform
from app.interview.fields import DERIVED, FIELDS

TEMPLATE_DIR = Path(__file__).parent / "templates"
CONTEXT_KEYS = DERIVED | {"business_type_label", "authority", "today", "state", "city"}


class FieldMap(BaseModel):
    pdf_field: str
    label: str
    source: str | None = None  # None => intentionally unmapped (e.g. signature)
    sources: list[str] | None = None
    transform: str = "identity"
    required: bool = True
    confirm: bool = False  # value is derived/uncertain: flag as doubtful so the user confirms it
    max_len: int | None = None
    note: str | None = None
    page: int = 0
    x: float | None = None  # overlay position (points from bottom-left) for flat PDFs
    y: float | None = None
    size: float = 10

    @model_validator(mode="after")
    def _check(self) -> "FieldMap":
        name, _ = parse_transform(self.transform)
        if name not in TRANSFORMS:
            raise ValueError(f"unknown transform {self.transform}")
        for s in ([self.source] if self.source else []) + (self.sources or []):
            if s not in FIELDS and s not in CONTEXT_KEYS:
                raise ValueError(f"unknown source key {s}")
        return self

    @property
    def keys(self) -> list[str]:
        return self.sources or ([self.source] if self.source else [])


class Warning_(BaseModel):
    key: str
    gt: int
    message: str


class FormTemplate(BaseModel):
    id: str
    title: str
    authority: str
    version: str
    placeholder: bool = True
    pdf: str
    kind: str = "acroform"
    portal_url: str | None = None
    warnings: list[Warning_] = Field(default_factory=list)
    fields: list[FieldMap]

    @property
    def pdf_path(self) -> Path:
        return TEMPLATE_DIR / self.pdf

    def required_keys(self) -> set[str]:
        """Interview keys this form needs (context/derived keys are never asked)."""
        out: set[str] = set()
        for f in self.fields:
            if f.required:
                out |= {k for k in f.keys if k in FIELDS}
        return out

    def optional_keys(self) -> set[str]:
        return {k for f in self.fields if not f.required for k in f.keys if k in FIELDS}


@lru_cache
def load_templates() -> dict[str, FormTemplate]:
    out = {}
    for p in sorted(TEMPLATE_DIR.glob("*.json")):
        t = FormTemplate.model_validate(json.loads(p.read_text(encoding="utf-8")))
        if t.id != p.stem:
            raise ValueError(f"template id {t.id} must match filename {p.name}")
        out[t.id] = t
    return out


def get_template(form_id: str) -> FormTemplate:
    try:
        return load_templates()[form_id]
    except KeyError as exc:
        raise KeyError(f"unknown form {form_id}") from exc


def required_keys_for(form_ids: list[str]) -> set[str]:
    """Union of fields required across all forms - what the interview must collect."""
    keys: set[str] = set()
    for fid in form_ids:
        keys |= get_template(fid).required_keys()
    return keys
