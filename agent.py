"""
YEA Today Grant Finder Agent
Searches three sources:
  1. Grants.gov         — federal grants (free public API, no key)
  2. Foundation scraper — 25 private foundation grant pages (scraped)
  3. ProPublica 990     — historical giving data to find foundation prospects

Uses Ollama to analyze results and generate a report + application drafts.

Setup:
  1. Install Ollama: https://ollama.com
  2. Pull a model:   ollama pull llama3.1
  3. Install deps:   pip install -r requirements.txt
  4. Run:            python agent.py
"""

import json
import sys
from datetime import datetime

import requests

from config import GRANT_CRITERIA, ORG_PROFILE, SEARCH_QUERIES
from tools.files import save_draft, save_report
from tools.foundations import fetch_all as fetch_foundations
from tools.propublica import find_foundation_prospects, format_for_ai as format_prospects
from tools.search import deduplicate, search_grants_gov

# ── Ollama config ─────────────────────────────────────────────────────────────

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "llama3.2"  # 3B model — much faster on CPU than llama3.1 (8B)

SYSTEM_PROMPT = f"""You are a grant research specialist helping YEA Today, a national 501(c)(3) nonprofit focused on youth entrepreneurship programs.

## YEA Today Profile
{ORG_PROFILE}

## Grant Criteria
{GRANT_CRITERIA}

Write in clear, professional nonprofit language. Be specific and tie everything to YEA Today's programs and outcomes. When assessing fit, consider both mission alignment AND practical eligibility."""

# ── Ollama helper ─────────────────────────────────────────────────────────────


def check_ollama() -> bool:
    try:
        requests.get("http://localhost:11434", timeout=5)
        return True
    except Exception:
        return False


def verify_model() -> str | None:
    """
    Send a tiny test message to confirm the model is downloaded and responding.
    Returns None on success, or an error string on failure.
    """
    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "messages": [{"role": "user", "content": "Reply with the word OK."}],
                "stream": False,
                "options": {"num_predict": 5},
            },
            timeout=60,
        )
        response.raise_for_status()
        return None
    except requests.exceptions.HTTPError as e:
        body = e.response.text[:200]
        if "not found" in body.lower() or "pull" in body.lower():
            return (
                f"Model '{MODEL}' is not downloaded.\n"
                f"Run this command in a terminal:  ollama pull {MODEL}\n"
                f"Then re-run python agent.py"
            )
        return f"Ollama error {e.response.status_code}: {body}"
    except requests.exceptions.Timeout:
        return f"Model '{MODEL}' timed out on a simple test. It may still be loading — wait 30 seconds and try again."
    except Exception as e:
        return f"Could not reach Ollama model: {e}"


def chat(user_message: str, max_tokens: int = 3000, num_ctx: int = 8192) -> str:
    """
    Send a message to Ollama with streaming enabled.
    Tokens are printed to the terminal in real-time so you can see progress.
    Returns the full response as a string.
    """
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        "stream": True,
        "options": {
            "temperature": 0.3,
            "num_ctx": num_ctx,
            "num_predict": max_tokens,
        },
    }

    try:
        response = requests.post(OLLAMA_URL, json=payload, stream=True, timeout=360)
        response.raise_for_status()

        chunks = []
        for raw_line in response.iter_lines():
            if not raw_line:
                continue
            try:
                data = json.loads(raw_line)
            except ValueError:
                continue
            chunk = data.get("message", {}).get("content", "")
            if chunk:
                print(chunk, end="", flush=True)
                chunks.append(chunk)
            if data.get("done"):
                break
        print()  # newline after stream ends
        return "".join(chunks)

    except requests.exceptions.ConnectionError:
        sys.exit(
            "\nERROR: Cannot connect to Ollama at localhost:11434.\n"
            "Open Ollama from the Start menu, or run 'ollama serve' in a terminal.\n"
            "Then re-run: python agent.py"
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(
            "Ollama timed out. Try a smaller model: "
            "run 'ollama pull llama3.2' then set MODEL = 'llama3.2' at the top of agent.py"
        )
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(
            f"Ollama returned HTTP {e.response.status_code}: {e.response.text[:300]}"
        )
    except Exception as e:
        raise RuntimeError(f"Unexpected Ollama error: {e}")


# ── Phase 1: Grants.gov ───────────────────────────────────────────────────────


def collect_federal_grants() -> list[dict]:
    all_grants = []
    for query in SEARCH_QUERIES:
        print(f"    '{query}'")
        results = search_grants_gov(query, rows=20)
        all_grants.extend(results)
    return deduplicate(all_grants)


def format_federal_grants(grants: list[dict]) -> str:
    lines = []
    for i, g in enumerate(grants, 1):
        ceiling = (
            f"${g['award_ceiling']:,}"
            if isinstance(g["award_ceiling"], (int, float)) and g["award_ceiling"]
            else g["award_ceiling"] or "not specified"
        )
        lines.append(
            f"{i}. {g['title']}\n"
            f"   Agency: {g['agency']} | Award: {ceiling} | Deadline: {g['close_date'] or 'TBD'} | Status: {g['status']}\n"
            f"   URL: {g['url']}\n"
            f"   Description: {(g['description'] or 'No description')[:200]}\n"
        )
    return "\n".join(lines)


# ── Phase 2: Private foundation scraper ───────────────────────────────────────


def format_foundation_data(foundations: list[dict]) -> str:
    lines = []
    for f in foundations:
        lines.append(
            f"Foundation: {f['name']}\n"
            f"About: {f['about']}\n"
            f"Grant page: {f['url']}\n"
            f"Page content: {f['page_content']}\n"
        )
    return "\n---\n".join(lines)


# ── Phase 2: AI analysis — two focused calls ─────────────────────────────────


def generate_federal_section(federal_grants: list[dict], today: str) -> str:
    """Analyze federal grants from Grants.gov and return a Markdown section."""
    federal_text = format_federal_grants(federal_grants)

    prompt = f"""Today is {today}. Analyze these {len(federal_grants)} federal grant opportunities from Grants.gov for YEA Today.

{federal_text}

Write the following Markdown section. Rank ALL relevant grants — do not limit to a fixed number:

## Federal Grant Opportunities (Grants.gov)
**Total found:** {len(federal_grants)} | **Source:** grants.gov

### Ranked Opportunities
For each grant that has any relevance to YEA Today, write:

#### [Rank]. [Grant Title]
- **Agency:** [agency name]
- **Award amount:** [amount or "not specified"]
- **Deadline:** [date or "TBD"]
- **Status:** [posted / forecasted]
- **Link:** [full URL]
- **Fit assessment:** (2 sentences — why this matches YEA Today and how to position the application)
- **Fit score:** [X/10]

### Grants to Watch
(List any forecasted grants not yet open that are worth monitoring, with their expected open dates if available)

### Not a Match
(One-line note for any grants found that clearly don't fit YEA Today's mission)"""

    return chat(prompt, max_tokens=2000, num_ctx=8192)


def generate_foundations_section(
    foundation_data: list[dict], prospect_summary: str, today: str
) -> str:
    """
    Analyze all private foundations in batches of 5 so each Ollama call is
    small and fast. Streams output so progress is visible in the terminal.
    """
    batch_size = 5
    batches = [
        foundation_data[i : i + batch_size]
        for i in range(0, len(foundation_data), batch_size)
    ]
    n = len(foundation_data)
    batch_results = []

    for i, batch in enumerate(batches, 1):
        names = ", ".join(f["name"] for f in batch)
        print(f"\n  Batch {i}/{len(batches)}: {names}\n")

        batch_text = format_foundation_data(batch)
        prompt = f"""Today is {today}. Analyze these {len(batch)} private foundations for YEA Today and write an entry for EACH ONE.

{batch_text}

Use this format for every foundation — do not skip any:

### [Foundation Name]
- **Focus area:** [what they fund]
- **Grant portal:** [use the exact URL from the data above]
- **Status:** [Open grant available | Warm prospect — no open RFP | Invitation only | Requires registration]
- **Fit for YEA Today:** (1 sentence on why it matches youth entrepreneurship programs)
- **Recommended action:** [Apply now | Submit LOI | Monitor quarterly | Low priority]"""

        try:
            result = chat(prompt, max_tokens=800, num_ctx=4096)
            batch_results.append(result)
        except RuntimeError as e:
            print(f"\n  WARNING: Batch {i} failed — {e}")
            batch_results.append(
                "\n".join(
                    f"### {f['name']}\n- **Grant portal:** {f['url']}\n- *Could not analyze — see error above*\n"
                    for f in batch
                )
            )

    # ProPublica prospects — separate short call
    print("\n  Analyzing ProPublica 990 data for foundation leads...")
    try:
        prospects_result = chat(
            f"""Based on this ProPublica 990 data about nonprofits similar to YEA Today, list which foundations or funders are likely warm prospects worth approaching:

{prospect_summary}

Write a "## Foundation Leads from 990 Data" section. List each prospect foundation with one sentence on why they're relevant to YEA Today.""",
            max_tokens=800,
            num_ctx=4096,
        )
    except RuntimeError as e:
        prospects_result = f"## Foundation Leads from 990 Data\n*(Could not analyze — {e})*\n"

    header = f"## Private Foundation Prospects\n**Total foundations reviewed:** {n} | **Analyzed in {len(batches)} batches**\n"
    next_steps = (
        "\n## Recommended Next Steps\n"
        "1. **Within 2 weeks:** Apply to all foundations marked 'Apply now'\n"
        "2. **Within 30 days:** Submit LOIs to foundations marked 'Submit LOI'\n"
        "3. **Ongoing:** Set calendar reminders to check 'Monitor quarterly' foundations every 90 days\n"
        "4. Research the 990 foundation leads for warm introduction opportunities\n"
    )

    return header + "\n\n".join(batch_results) + "\n\n" + prospects_result + next_steps


def assemble_report(
    federal_section: str,
    foundations_section: str,
    federal_count: int,
    foundation_count: int,
    today: str,
) -> str:
    """Combine both AI-generated sections into a single Markdown report."""
    return f"""# YEA Today — Grant Opportunities Report
**Generated:** {today}
**Sources:** Grants.gov (federal) | {foundation_count} private foundation websites | ProPublica 990 data

---

## How to Use This Report
- **Federal grants** — apply directly on grants.gov using the opportunity number
- **Private foundation prospects** — click each grant portal link to check current open applications
- **Recommended action** tells you whether to apply now, submit a Letter of Intent, or monitor for future cycles
- Edit the draft applications in `output/drafts/` before submitting

---

{federal_section}

---

{foundations_section}

---

## Coverage Note
This report covers **{federal_count} federal grants** (Grants.gov) and **{foundation_count} private foundations** (scraped). It does not include thousands of smaller community foundations, state-level funders, or private foundations that do not publish grants online. For broader coverage, consider a paid database such as Candid Foundation Directory or Instrumentl.
"""


def generate_draft(grant_info: dict, source: str) -> str:
    today = datetime.now().strftime("%B %d, %Y")

    if source == "federal":
        ceiling = (
            f"${grant_info['award_ceiling']:,}"
            if isinstance(grant_info["award_ceiling"], (int, float)) and grant_info["award_ceiling"]
            else grant_info["award_ceiling"] or "see opportunity listing"
        )
        grant_header = (
            f"**Grant:** {grant_info['title']}\n"
            f"**Agency:** {grant_info['agency']}\n"
            f"**Award Amount:** {ceiling}\n"
            f"**Deadline:** {grant_info['close_date'] or 'TBD'}\n"
            f"**Opportunity Number:** {grant_info['opportunity_number']}\n"
            f"**URL:** {grant_info['url']}"
        )
        grant_name = grant_info["title"]
    else:
        grant_header = (
            f"**Foundation:** {grant_info['name']}\n"
            f"**About:** {grant_info['about']}\n"
            f"**Grant page:** {grant_info['url']}"
        )
        grant_name = grant_info["name"]

    prompt = f"""Write a complete draft grant application narrative for YEA Today for the following opportunity:

{grant_header}

Write the full narrative in Markdown format:

# Draft Application: {grant_name}
**Prepared for:** {grant_name}
**Date:** {today}
**Status:** DRAFT — review and customize before submitting

---

## 1. Organization Description
(YEA Today's mission, national reach, programs, and track record — 2-3 compelling paragraphs)

## 2. Problem Statement
(Why is the youth entrepreneurship gap a serious problem? Who is most affected and how? Use data/statistics where possible — 2 paragraphs)

## 3. Proposed Program
(Specifically what YEA Today will do with this grant — be concrete about activities, timeline, and geography — 2-3 paragraphs)

## 4. Goals and Measurable Outcomes
(4-6 SMART goals with specific numbers and 12-month timelines)

## 5. Budget Narrative
(How grant funds will be used — break down by category: personnel, program delivery, materials, travel, evaluation. Align to the grant amount or typical foundation range)

## 6. Evaluation Plan
(How YEA Today will measure and report success — data collected, frequency, reporting format)

## 7. Organizational Capacity
(Why YEA Today is qualified — staff expertise, national infrastructure, prior grants, partnerships)

---
*Draft only. Add specific staff names, actual budget figures, current outcome data, and any required attachments before submitting.*"""

    return chat(prompt)


# ── Main ─────────────────────────────────────────────────────────────────────


def run():
    print("YEA Today Grant Finder Agent")
    print("=" * 55)
    print(f"Started:      {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"AI model:     {MODEL} (local, via Ollama)")
    print(f"Sources:      Grants.gov + 25 foundation sites + ProPublica 990s")
    print()

    if not check_ollama():
        sys.exit(
            "ERROR: Ollama is not running.\n"
            "1. Open Ollama from the Start menu (or system tray)\n"
            "2. If first time: open a terminal and run:  ollama pull llama3.1\n"
            "3. Then re-run:  python agent.py"
        )

    print("Ollama: connected — verifying model is downloaded...")
    model_error = verify_model()
    if model_error:
        sys.exit(f"\nERROR: {model_error}")
    print(f"Model '{MODEL}': ready\n")

    today = datetime.now().strftime("%B %d, %Y")
    date_str = datetime.now().strftime("%Y-%m-%d-%H%M")  # includes time so each run gets its own file

    # ── Phase 1a: Federal grants ──
    print("Phase 1a — Searching Grants.gov (federal grants)...")
    federal_grants = collect_federal_grants()
    print(f"  -> {len(federal_grants)} unique federal grants found\n")

    # ── Phase 1b: Foundation scraping ──
    print("Phase 1b — Scraping private foundation grant pages...")
    print("  (fetching 25 foundation websites — takes ~30 seconds)\n")
    foundation_data = fetch_foundations(verbose=True)
    print(f"\n  -> {len(foundation_data)} foundation pages fetched\n")

    # ── Phase 1c: ProPublica prospect research ──
    print("Phase 1c — Searching ProPublica 990 data for foundation prospects...")
    similar_orgs = find_foundation_prospects(max_orgs=10)
    prospect_summary = format_prospects(similar_orgs)
    print(f"  -> {len(similar_orgs)} similar organizations found\n")

    # ── Phase 2: Generate report in two focused AI calls ──
    print("Phase 2a — Analyzing federal grants with AI...")
    try:
        federal_section = generate_federal_section(federal_grants, today)
        print(f"  -> Done ({len(federal_section)} chars)\n")
    except RuntimeError as e:
        print(f"  -> WARNING: Federal section failed — {e}\n")
        federal_section = f"> **Warning:** Federal grants section could not be generated.\n> Error: {e}\n"

    print(f"Phase 2b — Analyzing all {len(foundation_data)} foundations with AI...")
    try:
        foundations_section = generate_foundations_section(foundation_data, prospect_summary, today)
        print(f"  -> Done ({len(foundations_section)} chars)\n")
    except RuntimeError as e:
        print(f"  -> WARNING: Foundations section failed — {e}\n")
        foundations_section = f"> **Warning:** Foundations section could not be generated.\n> Error: {e}\n"

    report = assemble_report(
        federal_section, foundations_section,
        len(federal_grants), len(foundation_data), today
    )

    report_path = save_report(report, f"grant-report-{date_str}")
    print(f"  -> Report saved to: {report_path}\n")

    # ── Phase 3: Draft applications ──
    print("Phase 3 — Drafting applications for top opportunities...")

    # Top 2 federal grants + top 1 foundation = 3 drafts
    top_federal = federal_grants[:2]
    top_foundation = foundation_data[:1]

    for i, grant in enumerate(top_federal, 1):
        title = grant["title"][:60]
        print(f"  Drafting federal {i}/2: {title}...")
        draft = generate_draft(grant, source="federal")
        path = save_draft(draft, grant["title"])
        print(f"  -> {path}")

    for f in top_foundation:
        print(f"  Drafting foundation: {f['name']}...")
        draft = generate_draft(f, source="foundation")
        path = save_draft(draft, f["name"])
        print(f"  -> {path}")

    print(f"\nDone! {datetime.now().strftime('%H:%M')}")
    print(f"  Reports  -> output/reports/")
    print(f"  Drafts   -> output/drafts/")


if __name__ == "__main__":
    run()
