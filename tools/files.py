import re
from datetime import datetime
from pathlib import Path

_BASE = Path(__file__).parent.parent / "output"
REPORTS_DIR = _BASE / "reports"
DRAFTS_DIR = _BASE / "drafts"


def save_report(content: str, filename: str) -> str:
    """Save a grant report Markdown file to output/reports/."""
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    if not filename.endswith(".md"):
        filename = f"{filename}.md"
    path = REPORTS_DIR / filename
    path.write_text(content, encoding="utf-8")
    return str(path)


def save_draft(content: str, grant_name: str) -> str:
    """Save a draft application Markdown file to output/drafts/."""
    DRAFTS_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^a-z0-9]+", "-", grant_name.lower()).strip("-")
    date = datetime.now().strftime("%Y-%m-%d")
    path = DRAFTS_DIR / f"draft-{safe}-{date}.md"
    path.write_text(content, encoding="utf-8")
    return str(path)
