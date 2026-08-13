"""
Grant Finder — Streamlit Frontend
Search Grants.gov and 60+ private foundation pages for grant opportunities.
Applicable to any nonprofit for any funding need.
"""

import os
import re
from datetime import datetime

import streamlit as st

from agent import format_federal_grants, format_foundation_data
from tools.files import report_as_docx_bytes, report_as_pdf_bytes
from tools.foundations import FOUNDATIONS, fetch_all_light
from tools.propublica import find_foundation_prospects, format_for_ai as format_prospects
from tools.search import clean_query, deduplicate, search_grants_gov

st.set_page_config(
    page_title="Grant Finder",
    page_icon="🔍",
    layout="wide",
)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL   = "gemini-2.0-flash"


# ── AI helper ──────────────────────────────────────────────────────────────────

def gemini(prompt: str, system_prompt: str = "") -> str | None:
    if not GEMINI_API_KEY:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=full_prompt,
        )
        return response.text or None
    except Exception:
        return None


def build_ai_system_prompt(org_profile: str) -> str:
    if org_profile.strip():
        return (
            "You are a grant research specialist helping a nonprofit organization "
            "find relevant grant opportunities.\n\n"
            f"## Organization Profile\n{org_profile.strip()}\n\n"
            "When assessing grant fit, consider mission alignment and practical "
            "eligibility. Write in clear, professional nonprofit language."
        )
    return (
        "You are a grant research specialist helping nonprofit organizations "
        "find relevant grant opportunities. Write in clear, professional nonprofit language."
    )


# ── Report builders ────────────────────────────────────────────────────────────

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
        "\nClick each link to see the full listing including award amounts.\n",
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
        f"**{len(foundations)} foundations** — click each link to check for open applications",
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


def build_report(
    today: str,
    queries_used: list[str],
    federal_grants: list[dict],
    foundations: list[dict],
    ai_federal: str | None,
    ai_foundations: str | None,
    org_name: str = "",
) -> str:
    federal_raw     = build_federal_section(federal_grants, queries_used)
    foundations_raw = build_foundations_section(foundations)

    ai_block = ""
    if ai_federal or ai_foundations:
        ai_block = (
            "## AI Fit Analysis\n"
            + (ai_federal or "") + "\n\n"
            + (ai_foundations or "") + "\n\n---\n\n"
        )

    query_line = ", ".join(f'"{q}"' for q in queries_used)
    org_line   = f"**Organization:** {org_name}\n" if org_name.strip() else ""

    return f"""# Grant Opportunities Report
**Generated:** {today}
{org_line}**Search terms:** {query_line}
**Sources:** Grants.gov (federal) | {len(foundations)} private foundation pages | ProPublica 990 data

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
            "None of the curated foundations closely matched your search keywords. "
            "All are shown below. For broader foundation discovery, also try "
            "**[Candid (Foundation Directory)](https://candid.org)**, "
            "**[GrantWatch](https://www.grantwatch.com)**, or "
            "**[Instrumentl](https://www.instrumentl.com)**."
        )

    if len(relevant) < len(foundations):
        return relevant, (
            f"{len(relevant)} of {len(foundations)} foundations are most relevant to your search. "
            "Check each link for open applications."
        )

    return foundations, ""


# ── Query resolution ───────────────────────────────────────────────────────────

def resolve_queries(user_text: str) -> list[str]:
    return [clean_query(q.strip()) for q in user_text.splitlines() if q.strip()]


# ── UI ─────────────────────────────────────────────────────────────────────────

st.title("🔍 Grant Finder")
st.caption(
    "Search Grants.gov and 60+ private foundation pages for grant opportunities. "
    "Works for any nonprofit, any mission, any funding need."
)

# ── Org profile (optional) ────────────────────────────────────────────────────
with st.expander("📋 Organization Profile (optional — improves AI fit analysis)", expanded=False):
    org_name = st.text_input(
        "Organization name",
        key="org_name",
        placeholder="e.g. Bright Futures Community Center",
    )
    org_profile = st.text_area(
        "Describe your organization — mission, programs, population served",
        key="org_profile",
        placeholder=(
            "Example:\n"
            "We are a 501(c)(3) serving adults recovering from substance use disorder "
            "in rural Appalachia. Our programs include peer counseling, job training, "
            "and transitional housing. We serve 200 clients per year across three counties."
        ),
        height=120,
        help="Used to generate an AI fit analysis when results are ready. Leave blank to skip AI analysis.",
    )

# ── Search bar ────────────────────────────────────────────────────────────────
st.subheader("What are you searching for?")

col_input, col_tip = st.columns([2, 1])

with col_input:
    user_query_text = st.text_area(
        "Enter search terms — one per line",
        key="search_input",
        placeholder=(
            "Examples:\n"
            "pediatric cancer children research\n"
            "affordable housing low income families\n"
            "substance use recovery rural\n"
            "climate change environmental justice"
        ),
        height=140,
        help="Each line becomes a separate Grants.gov search. More specific terms = more relevant results.",
    )

with col_tip:
    st.info(
        "**Tips for better results:**\n\n"
        "- Use keywords, not sentences\n"
        "- Include your population: _elderly veterans_\n"
        "- Include your topic: _mental health crisis_\n"
        "- Include geography if relevant: _rural Midwest_\n"
        "- Try 2–3 lines for broader coverage"
    )

queries_to_run = resolve_queries(user_query_text)

if queries_to_run:
    with st.expander(
        f"🔎 {len(queries_to_run)} search term(s) queued (click to see)",
        expanded=False,
    ):
        for q in queries_to_run:
            st.markdown(f"- `{q}`")
else:
    st.caption("Enter search terms above to begin.")

st.divider()
run = st.button(
    "🔍 Run Grant Search",
    type="primary",
    use_container_width=False,
    disabled=not bool(queries_to_run),
)

if run and queries_to_run:
    today = datetime.now().strftime("%B %d, %Y")

    with st.status("Searching Grants.gov...", expanded=True) as status:

        # Phase 1: Federal grants
        federal_grants = []
        for i, q in enumerate(queries_to_run, 1):
            status.update(label=f"Searching Grants.gov: '{q}' ({i}/{len(queries_to_run)})...")
            federal_grants.extend(search_grants_gov(q, rows=20))
        federal_grants = deduplicate(federal_grants)
        st.write(f"Found **{len(federal_grants)}** unique federal grants.")

        # Phase 2: Foundation data (instant — no scraping)
        status.update(label=f"Loading {len(FOUNDATIONS)} foundation records...")
        foundation_data = fetch_all_light()
        st.write(f"Loaded **{len(foundation_data)}** foundations.")

        # Phase 3: Filter foundations by relevance
        display_foundations, fnd_note = filter_foundations_for_display(
            foundation_data, queries_to_run
        )

        # Phase 4: ProPublica (dynamic — uses user's search terms)
        status.update(label="Cross-referencing ProPublica 990 filings...")
        similar_orgs     = find_foundation_prospects(search_terms=queries_to_run, max_orgs=10)
        prospect_summary = format_prospects(similar_orgs)
        st.write(f"Found **{len(similar_orgs)}** similar nonprofits in IRS 990 data.")

        # Phase 5: Optional AI analysis (only when org profile is provided)
        ai_federal = ai_foundations = None
        sys_prompt = build_ai_system_prompt(org_profile)

        if GEMINI_API_KEY and org_profile.strip():
            status.update(label="Running AI fit analysis...")
            ai_federal = gemini(
                f"Today is {today}. For each federal grant below, write one short paragraph "
                f"assessing fit for this organization and give a fit score (X/10). Be concise.\n\n"
                f"{format_federal_grants(federal_grants)}",
                system_prompt=sys_prompt,
            )
            ai_foundations = gemini(
                f"Today is {today}. For each foundation below, write one bullet with fit "
                f"assessment and recommended action (Apply now / Submit LOI / Monitor / Low priority).\n\n"
                f"{format_foundation_data(display_foundations[:15])}",
                system_prompt=sys_prompt,
            )
        elif GEMINI_API_KEY and not org_profile.strip():
            st.write(
                "💡 Add your organization profile above to enable AI fit analysis."
            )

        status.update(label="Done!", state="complete")

    st.session_state["result"] = {
        "today":               today,
        "queries_used":        queries_to_run,
        "federal_grants":      federal_grants,
        "foundation_data":     foundation_data,
        "display_foundations": display_foundations,
        "fnd_note":            fnd_note,
        "prospect_count":      len(similar_orgs),
        "ai_federal":          ai_federal,
        "ai_foundations":      ai_foundations,
        "org_name":            org_name,
    }


# ── Results display ────────────────────────────────────────────────────────────

if "result" in st.session_state:
    r = st.session_state["result"]

    st.divider()
    c1, c2, c3 = st.columns(3)
    c1.metric("Federal Grants Found",         len(r["federal_grants"]))
    c2.metric("Foundations Matched",           len(r["display_foundations"]))
    c3.metric("Similar Nonprofits (990 data)", r["prospect_count"])

    st.caption(
        "Search terms used: "
        + " · ".join(f"`{q}`" for q in r["queries_used"])
    )

    # AI analysis (only if it ran)
    if r["ai_federal"] or r["ai_foundations"]:
        with st.expander("✨ AI Fit Analysis", expanded=True):
            if r["ai_federal"]:
                st.markdown(r["ai_federal"])
            if r["ai_foundations"]:
                st.markdown(r["ai_foundations"])

    # Federal grants
    st.subheader(f"📋 Federal Grant Opportunities ({len(r['federal_grants'])} found)")
    if not r["federal_grants"]:
        st.info(
            "No federal grants matched your search terms. "
            "Try more specific keywords, different terminology, or fewer words per line."
        )
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

    # Foundations
    st.divider()
    disp = r["display_foundations"]
    total_fnd = len(r["foundation_data"])
    if len(disp) < total_fnd:
        fnd_label = f"🏛️ Private Foundation Grant Pages ({len(disp)} of {total_fnd} matched your search)"
    else:
        fnd_label = f"🏛️ Private Foundation Grant Pages ({len(disp)} foundations)"

    st.subheader(fnd_label)
    if r["fnd_note"]:
        st.info(r["fnd_note"])

    for f in disp:
        with st.expander(f["name"], expanded=False):
            st.markdown(f"**What they fund:** {f['about']}")
            st.markdown(f"**Grant portal:** [{f['url']}]({f['url']})")

    # Download buttons
    st.divider()
    st.markdown("### Download Full Report")

    report = build_report(
        r["today"],
        r["queries_used"],
        r["federal_grants"],
        r["display_foundations"],
        r["ai_federal"],
        r["ai_foundations"],
        org_name=r.get("org_name", ""),
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
