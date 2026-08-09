"""
YEA Today Grant Finder — Streamlit Frontend
Run with: streamlit run app.py

This is a scoped, cloud-friendly version of agent.py: it runs the same three
live data sources (Grants.gov, foundation scraper, ProPublica), but uses
Gemini instead of local Ollama for the AI ranking step (so it works on a
public deployment), and skips the CLI's draft-writing phase to keep a demo
run to well under a minute instead of ~15.
"""

import os
from datetime import datetime

import streamlit as st

from agent import SYSTEM_PROMPT, format_federal_grants, format_foundation_data
from config import SEARCH_QUERIES
from tools.foundations import FOUNDATIONS, fetch_all as fetch_foundations
from tools.propublica import find_foundation_prospects, format_for_ai as format_prospects
from tools.search import deduplicate, search_grants_gov

st.set_page_config(
    page_title="YEA Today Grant Finder",
    page_icon="🔍",
    layout="wide",
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = "gemini-2.0-flash"


def gemini(prompt: str) -> str:
    try:
        from google import genai

        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{SYSTEM_PROMPT}\n\n{prompt}",
        )
        return response.text or "*(Gemini returned an empty response.)*"
    except Exception as exc:
        return f"*(AI ranking failed: {exc})*"


st.title("🔍 YEA Today Grant Finder")
st.caption(
    "Searches Grants.gov, 25 private foundation grant pages, and ProPublica's "
    "nonprofit 990 filings live, then an AI ranks every match for fit — built "
    "for YEA Today, a national youth entrepreneurship nonprofit."
)

if not GEMINI_API_KEY:
    st.warning(
        "AI ranking isn't configured on this deployment (missing GEMINI_API_KEY). "
        "The live searches below still run — only the AI analysis step is skipped."
    )

run = st.button("🔍 Run Grant Search", type="primary")

if run:
    today = datetime.now().strftime("%B %d, %Y")

    with st.status("Searching Grants.gov for federal opportunities...", expanded=True) as status:
        federal_grants = []
        for q in SEARCH_QUERIES:
            federal_grants.extend(search_grants_gov(q, rows=20))
        federal_grants = deduplicate(federal_grants)
        st.write(f"Found **{len(federal_grants)}** unique federal grants.")

        status.update(label=f"Scraping {len(FOUNDATIONS)} private foundation grant pages...")
        progress = st.progress(0.0)

        def _on_progress(i, total, name):
            progress.progress(i / total, text=f"[{i}/{total}] {name}")

        foundation_data = fetch_foundations(verbose=False, on_progress=_on_progress)
        progress.empty()
        st.write(f"Reviewed **{len(foundation_data)}** foundations.")

        status.update(label="Cross-referencing ProPublica 990 filings...")
        similar_orgs = find_foundation_prospects(max_orgs=10)
        st.write(f"Found **{len(similar_orgs)}** similar nonprofits in IRS 990 data.")

        if GEMINI_API_KEY:
            status.update(label="Ranking opportunities with AI...")

            federal_prompt = f"""Today is {today}. Analyze these {len(federal_grants)} federal grant opportunities from Grants.gov for YEA Today.

{format_federal_grants(federal_grants)}

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
- **Fit assessment:** (2 sentences — why this matches YEA Today)
- **Fit score:** [X/10]

### Not a Match
(One-line note for any grants that clearly don't fit YEA Today's mission)"""
            federal_section = gemini(federal_prompt)

            foundations_prompt = f"""Today is {today}. Analyze these {len(foundation_data)} private foundations for YEA Today and write an entry for EACH ONE.

{format_foundation_data(foundation_data)}

Then, based on this ProPublica 990 data about similar nonprofits, add a final "## Foundation Leads from 990 Data" section:
{format_prospects(similar_orgs)}

Use this format for every foundation — do not skip any:

### [Foundation Name]
- **Focus area:** [what they fund]
- **Grant portal:** [exact URL from the data above]
- **Status:** [Open grant available | Warm prospect — no open RFP | Invitation only | Requires registration]
- **Fit for YEA Today:** (1 sentence)
- **Recommended action:** [Apply now | Submit LOI | Monitor quarterly | Low priority]"""
            foundations_section = gemini(foundations_prompt)
        else:
            federal_section = "*(AI ranking skipped — no GEMINI_API_KEY configured on this deployment.)*"
            foundations_section = "*(AI ranking skipped — no GEMINI_API_KEY configured on this deployment.)*"

        status.update(label="Done!", state="complete")

    st.session_state["result"] = {
        "today": today,
        "federal_count": len(federal_grants),
        "foundation_count": len(foundation_data),
        "prospect_count": len(similar_orgs),
        "federal_section": federal_section,
        "foundations_section": foundations_section,
    }

if "result" in st.session_state:
    r = st.session_state["result"]
    st.divider()

    c1, c2, c3 = st.columns(3)
    c1.metric("Federal Grants Found", r["federal_count"])
    c2.metric("Foundations Reviewed", r["foundation_count"])
    c3.metric("Similar Nonprofits (990 data)", r["prospect_count"])

    st.subheader("📋 Federal Grant Opportunities")
    st.markdown(r["federal_section"])

    st.divider()
    st.subheader("🏛️ Private Foundation Prospects")
    st.markdown(r["foundations_section"])

    st.divider()
    report = f"""# YEA Today — Grant Opportunities Report
**Generated:** {r['today']}
**Sources:** Grants.gov (federal) | {r['foundation_count']} private foundation websites | ProPublica 990 data

---

{r['federal_section']}

---

{r['foundations_section']}
"""
    st.download_button(
        "📥 Download Full Report (.md)",
        data=report,
        file_name=f"grant-report-{datetime.now().strftime('%Y-%m-%d')}.md",
        mime="text/markdown",
    )

    st.caption(
        "This is a live, scoped demo — it queries all three sources for real, in real time. "
        "The full CLI agent (same codebase) also drafts complete grant application narratives "
        "for the top matches."
    )
