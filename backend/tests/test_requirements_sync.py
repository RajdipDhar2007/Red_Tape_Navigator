"""requirements*.txt must list exactly what pyproject.toml declares, so `pip install -r` and `pip install -e` never diverge."""

import tomllib
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]


def _lines(name: str) -> list[str]:
    out = []
    for raw in (BACKEND / name).read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#") and not line.startswith("-r "):
            out.append(line)
    return out


def _project() -> dict:
    return tomllib.loads((BACKEND / "pyproject.toml").read_text(encoding="utf-8"))["project"]


def test_runtime_requirements_match_pyproject():
    assert sorted(_lines("requirements.txt")) == sorted(_project()["dependencies"])


def test_dev_requirements_match_pyproject():
    assert sorted(_lines("requirements-dev.txt")) == sorted(_project()["optional-dependencies"]["dev"])


def test_dev_requirements_include_runtime_file():
    assert "-r requirements.txt" in (BACKEND / "requirements-dev.txt").read_text(encoding="utf-8")


def test_root_requirements_point_to_backend():
    assert "-r backend/requirements.txt" in (BACKEND.parent / "requirements.txt").read_text(encoding="utf-8")
