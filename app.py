"""
YEA Today Grant Finder — Streamlit Frontend
"""

import os
import re
from datetime import datetime

import streamlit as st

from agent import SYSTEM_PROMPT, format_federal_grants, format_foundation_data
from config import SEARCH_QUERIES, ORG_PROFILE
from tools.files import report_as_docx_bytes, report_as_pdf_bytes
from tools.foundations import FOUNDATIONS, fetch_all as fetch_foundations
from tools.propublica import find_foundation_prospects, format_for_ai as format_prospects
from tools.search import clean_query, deduplicate, search_grants_gov

st.set_page_config(
    page_title="YEA Today Grant Finder",
    page_icon="🔍",
    layout="wide",
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.0-flash"

DEFAULT_QUERIES_TEXT = "\n".join(SEARCH_QUERIES)


# ── AI helper ──────────────────────────────────────────────────────────────────

def gemini(prompt: str) -> str | None:
    """Call Gemini. Returns None on any failure so callers can skip gracefully."""
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        client   = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{SYSTEM_PROMPT}\n\n{prompt}",
        )
        return response.text or None
    except Exception:
        return None


# ── Report builders (always run, no AI needed) ────────────────────────────────

def build_federal_section(grants: list[dict], queries_used: list[str]) -> str:
    query_list = ", ".join(f'"{q}"' for q in queries_used)
    if not grants:
        return (
            f"## Federal Grant Opportunities\n"
            f"_No grants found for: {query_list}_\n\n"
            "Try broader or different search terms.\n"
        )
    lines = [
        "## Federal Grant Opportunities",
        f"**{len(grants)} grants found on Grants.gov**",
        f"**Search terms used:** {query_list}",
        f"\nClick each link to see the full listing including award amounts.\n",
    ]
    for i, g in enumerate(grants, 1):
        lines += [
            f"### {i}. {g['title']}",
            f"- **Agency:** {g['agency']}",
            f"- **Opportunity #:** {g.get('opportunity_number', '')}",
            f"- **Deadline:** {g.get('close_date') or 'TBD'}",
            f"- **Status:** {g.get('status', 'Unknown')}",
        ]
        if g.get("cfda"):
            lines.append(f"- **CFDA #:** {g['cfda']}")
        lines.append(
            f"- **Full listing (award amount + how to apply):** [{g['url']}]({g['url']})"
        )
        lines.append("")
    return "\n".join(lines)


def build_foundations_section(foundations: list[dict], note: str = "") -> str:
    if not foundations:
        return "_No foundation data available._\n"
    lines = [
        "## Private Foundation Grant Pages",
        f"**{len(foundations)} foundations reviewed** — click each link to check for open applications",
        "",
    ]
    if note:
        lines += [f"> {note}", ""]
    for f in foundations:
        lines += [
            f"### {f['name']}",
            f"- **What they fund:** {f['about']}",
            f"- **Grant portal:** [{f['url']}]({f['url']})",
            "",
        ]
    return "\n".join(lines)


def build_report(today: str, queries_used: list[str], federal_grants: list[dict],
                 foundations: list[dict], ai_federal: str | None,
                 ai_foundations: str | None) -> str:
    federal_raw     = build_federal_section(federal_grants, queries_used)
    foundations_raw = build_foundations_section(
        foundations,
        note=(
            "These 25 foundations are curated for youth entrepreneurship nonprofits. "
            "Check each link for open applications relevant to your specific focus area."
        ),
    )

    ai_block = ""
    if ai_federal or ai_foundations:
        ai_block = (
            "## AI Fit Analysis\n"
            + (ai_federal or "") + "\n\n"
            + (ai_foundations or "") + "\n\n---\n\n"
        )

    query_line = ", ".join(f'"{q}"' for q in queries_used)
    return f"""# YEA Today — Grant Opportunities Report
**Generated:** {today}
**Search terms:** {query_line}
**Sources:** Grants.gov (federal) | {len(foundations)} private foundation websites | ProPublica 990 data

---

{ai_block}{federal_raw}

---

{foundations_raw}

---

## How to Apply
- **Federal grants:** click the Grants.gov link for the full listing, then click "Apply" — you will need a SAM.gov registration
- **Foundation grants:** click each grant portal link to check whether an application is currently open
- Verify all deadlines directly on the funder's website before submitting
"""


# ── UI ─────────────────────────────────────────────────────────────────────────

st.title("🔍 YEA Today Grant Finder")
st.caption(
    "Search Grants.gov and 25 private foundation pages live. "
    "Enter your own search terms below, or use the YEA Today defaults."
)

# ── Search bar ────────────────────────────────────────────────────────────────
st.subheader("What are you looking for?")

col_input, col_tip = st.columns([2, 1])

with col_input:
    user_query_text = st.text_area(
        "Enter search terms — one per line",
        key="search_input",
        placeholder=(
            "Examples:\n"
            "youth entrepreneurship northeast\n"
            "children hearing loss disability\n"
            "women entrepreneurs small business\n"
            "workforce training rural communities"
        ),
        height=130,
        help="Each line is sent as a separate search to Grants.gov. More lines = more results.",
    )

with col_tip:
    st.info(
        "**Tips for better results:**\n\n"
        "- Be specific: _STEM high school nonprofits_\n"
        "- Include your population: _Latino youth_\n"
        "- Include geography: _rural Appalachia_\n"
        "- Include program type: _mentorship workforce_"
    )

# ── Query resolution — fixed logic ────────────────────────────────────────────
# Rule: if the user typed ANYTHING, use ONLY their terms.
# The checkbox only appears when custom terms are present, and defaults to OFF.
# This prevents the 8 hardcoded defaults from silently overriding a custom search.

has_custom = bool(user_query_text.strip())

if has_custom:
    add_yea_defaults = st.checkbox(
        "Also add YEA Today's 8 default searches (youth entrepreneurship, workforce, etc.)",
        value=False,           # explicitly OFF — user must opt in
        key="add_yea_defaults",
    )
else:
    add_yea_defaults = False
    st.caption("No search terms entered — will run YEA Today's 8 default grant searches.")


def resolve_queries(user_text: str, include_defaults: bool) -> list[str]:
    # clean_query strips filler like "find grants for" before sending to Grants.gov
    custom = [clean_query(q.strip()) for q in user_text.splitlines() if q.strip()]
    if not custom:
        return list(SEARCH_QUERIES)          # nothing typed → always use defaults
    if not include_defaults:
        return custom                         # typed something, defaults OFF → custom only
    # typed something AND defaults ON → merge, custom first
    seen   = {q.lower() for q in custom}
    merged = list(custom)
    for q in SEARCH_QUERIES:
        if q.lower() not in seen:
            merged.append(q)
    return merged


# ── Foundation relevance filter ────────────────────────────────────────────────

_FND_STOP = {
    "the", "and", "for", "with", "from", "this", "that", "are", "was", "has",
    "have", "been", "into", "also", "its", "our", "which", "will", "more",
    "find", "show", "get", "grants", "grant", "funding", "nonprofit", "nonprofits",
    "can", "you", "help", "search", "about", "all", "new", "not", "but",
}


def filter_foundations_for_display(
    foundations: list[dict], queries: list[str]
) -> tuple[list[dict], str]:
    """
    Rank and filter the curated foundation list by keyword relevance.
    Returns (foundation_list, note_string).
    """
    keywords = set()
    for q in queries:
        for word in re.split(r"\W+", q.lower()):
            if len(word) > 2 and word not in _FND_STOP:
                keywords.add(word)

    if not keywords:
        return foundations, ""

    def score(f: dict) -> int:
        text = f"{f['name']} {f['about']}".lower()
        return sum(1 for kw in keywords if kw in text)

    scored = [(score(f), f) for f in foundations]
    scored.sort(key=lambda x: x[0], reverse=True)
    relevant = [f for s, f in scored if s > 0]

    if not relevant:
        return foundations, (
            "None of the 25 curated foundations closely match your search keywords — "
            "they focus on youth entrepreneurship and adjacent topics. "
            "All are shown below. For grants specific to your topic, also try "
            "**[Candid (Foundation Directory)](https://candid.org)**, "
            "**[GrantWatch](https://www.grantwatch.com)**, or "
            "**[Instrumentl](https://www.instrumentl.com)**."
        )

    if len(relevant) < len(foundations):
        return relevant, (
            f"{len(relevant)} of {len(foundations)} curated foundations are most relevant to your search. "
            "These foundations are curated for youth entrepreneurship nonprofits — check each link for "
            "open applications that may fit your specific focus."
        )

    return foundations, ""


queries_to_run = resolve_queries(user_query_text, add_yea_defaults)

# Show exactly what will be searched so there's no ambiguity
with st.expander(
    f"{'🔎 Custom search' if has_custom else '📋 YEA Today defaults'} — "
    f"{len(queries_to_run)} term(s) queued (click to see)",
    expanded=False,
):
    for q in queries_to_run:
        st.markdown(f"- `{q}`")

st.divider()
run = st.button("🔍 Run Grant Search", type="primary", use_container_width=False)

if run:
    today = datetime.now().strftime("%B %d, %Y")

    with st.status("Searching Grants.gov...", expanded=True) as status:

        # Phase 1: Federal grants using user-driven queries
        federal_grants = []
        for i, q in enumerate(queries_to_run, 1):
            status.update(label=f"Searching Grants.gov: '{q}' ({i}/{len(queries_to_run)})...")
            federal_grants.extend(search_grants_gov(q, rows=20))
        federal_grants = deduplicate(federal_grants)
        st.write(f"Found **{len(federal_grants)}** unique federal grants.")

        # Phase 2: Foundation scraping (always the curated list)
        status.update(label=f"Scraping {len(FOUNDATIONS)} private foundation grant pages...")
        progress = st.progress(0.0)

        def _on_progress(i, total, name):
            progress.progress(i / total, text=f"[{i}/{total}] {name}")

        foundation_data = fetch_foundations(verbose=False, on_progress=_on_progress)
        progress.empty()
        st.write(f"Reviewed **{len(foundation_data)}** foundations.")

        # Phase 3: ProPublica
        status.update(label="Cross-referencing ProPublica 990 filings...")
        similar_orgs     = find_foundation_prospects(max_orgs=10)
        prospect_summary = format_prospects(similar_orgs)
        st.write(f"Found **{len(similar_orgs)}** similar nonprofits in IRS 990 data.")

        # Phase 4: Optional AI ranking
        ai_federal = ai_foundations = None
        if GEMINI_API_KEY:
            status.update(label="Running AI fit analysis...")
            ai_federal = gemini(
                f"Today is {today}. For each federal grant below, write one short paragraph "
                f"assessing fit for YEA Today and give a fit score (X/10). Be concise.\n\n"
                f"{format_federal_grants(federal_grants)}"
            )
            ai_foundations = gemini(
                f"Today is {today}. For each foundation below, write one bullet with fit "
                f"assessment and recommended action (Apply now / Submit LOI / Monitor / Low priority).\n\n"
                f"{format_foundation_data(foundation_data[:15])}"
            )

        status.update(label="Done!", state="complete")

    st.session_state["result"] = {
        "today":           today,
        "queries_used":    queries_to_run,
        "federal_grants":  federal_grants,
        "foundation_data": foundation_data,
        "prospect_count":  len(similar_orgs),
        "ai_federal":      ai_federal,
        "ai_foundations":  ai_foundations,
        "has_custom":      has_custom,
    }


# ── Results display ────────────────────────────────────────────────────────────

if "result" in st.session_state:
    r = st.session_state["result"]

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Federal Grants Found",         len(r["federal_grants"]))
    c2.metric("Foundations Reviewed",          len(r["foundation_data"]))
    c3.metric("Similar Nonprofits (990 data)", r["prospect_count"])

    # Show which queries produced these results
    st.caption(
        "Search terms used: "
        + " · ".join(f"`{q}`" for q in r["queries_used"])
    )

    # AI analysis (only if it worked)
    if r["ai_federal"] or r["ai_foundations"]:
        with st.expander("✨ AI Fit Analysis", expanded=True):
            if r["ai_federal"]:
                st.markdown(r["ai_federal"])
            if r["ai_foundations"]:
                st.markdown(r["ai_foundations"])

    # Federal grants — always shown
    st.subheader(f"📋 Federal Grant Opportunities ({len(r['federal_grants'])} found)")
    if not r["federal_grants"]:
        st.info("No federal grants matched your search terms. Try broader or different keywords.")
    for i, g in enumerate(r["federal_grants"], 1):
        with st.expander(f"{i}. {g['title']}", expanded=False):
            col_a, col_b = st.columns(2)
            col_a.markdown(f"**Agency:** {g['agency']}")
            col_a.markdown(f"**Opportunity #:** {g.get('opportunity_number', '')}")
            col_b.markdown(f"**Deadline:** {g.get('close_date') or 'TBD'}")
            col_b.markdown(f"**Status:** {g.get('status', 'Unknown')}")
            if g.get("cfda"):
                st.markdown(f"**CFDA #:** {g['cfda']}")
            st.markdown(
                f"**Full listing (award amount + how to apply):** [{g['url']}]({g['url']})"
            )

    # Foundations — always shown; filtered by relevance when a custom search is active
    st.divider()
    if r.get("has_custom"):
        display_foundations, fnd_note = filter_foundations_for_display(
            r["foundation_data"], r["queries_used"]
        )
        fnd_label = f"🏛️ Private Foundation Grant Pages ({len(display_foundations)} of {len(r['foundation_data'])} shown)"
    else:
        display_foundations = r["foundation_data"]
        fnd_note = (
            "These 25 foundations are curated for youth entrepreneurship nonprofits. "
            "Enter a custom search above to see which are most relevant to your specific topic."
        )
        fnd_label = f"🏛️ Private Foundation Grant Pages ({len(display_foundations)} curated)"

    st.subheader(fnd_label)
    if fnd_note:
        st.info(fnd_note)

    for f in display_foundations:
        with st.expander(f["name"], expanded=False):
            st.markdown(f"**What they fund:** {f['about']}")
            st.markdown(f"**Grant portal:** [{f['url']}]({f['url']})")

    # Download buttons
    st.divider()
    st.markdown("### Download Full Report")

    report = build_report(
        r["today"], r["queries_used"], r["federal_grants"],
        r["foundation_data"], r["ai_federal"], r["ai_foundations"],
    )
    date_str = datetime.now().strftime("%Y-%m-%d")
    dl1, dl2, dl3 = st.columns(3)

    with dl1:
        try:
            st.download_button(
                "📥 Download as Word (.docx)",
                data=report_as_docx_bytes(report),
                file_name=f"grant-report-{date_str}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Word export failed: {e}")

    with dl2:
        try:
            st.download_button(
                "📥 Download as PDF",
                data=report_as_pdf_bytes(report),
                file_name=f"grant-report-{date_str}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"PDF export failed: {e}")

    with dl3:
        st.download_button(
            "📥 Download as Markdown",
            data=report,
            file_name=f"grant-report-{date_str}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    st.caption(
        "Federal grants link directly to Grants.gov. Foundation links go to each "
        "foundation's grant or apply page — check them for current open RFPs."
    )
