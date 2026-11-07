"""Regenerate the clearly-marked placeholder PDFs for every template in backend/app/forms/templates."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.forms.placeholder import write_all  # noqa: E402

if __name__ == "__main__":
    print("wrote:", ", ".join(write_all()))
