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


# ── Federal grant title relevance scoring ─────────────────────────────────────

def _federal_relevance_score(title: str, queries: list[str]) -> int:
    """
    Score a grant title against the user's search queries.
    Exact phrase match scores 10; individual whole-word matches score 1 each.
    Word-boundary matching prevents 'security' from matching inside 'cybersecurity'.
    """
    title_lower = title.lower()
    score = 0
    for q in queries:
        q_lower = q.lower()
        if q_lower in title_lower:
            score += 10
        else:
            for word in re.split(r"\W+", q_lower):
                if len(word) > 3 and re.search(r"\b" + re.escape(word) + r"\b", title_lower):
                    score += 1
    return score


# ── Foundation relevance filter ────────────────────────────────────────────────

# Words that appear in nearly every foundation description and would match
# indiscriminately — they carry no search signal in this context.
_FND_STOP = {
    # Common English function words
    "the", "and", "for", "with", "from", "this", "that", "are", "was", "has",
    "have", "been", "into", "also", "its", "our", "which", "will", "more",
    "not", "but", "all", "new", "can", "any", "who", "how",
    # Search-bar filler words
    "find", "show", "get", "help", "search",
    # Nonprofit / funding world generic terms
    # ("community" appears in almost every foundation's about text — no signal)
    "grants", "grant", "funding", "fund", "funds",
    "nonprofit", "nonprofits", "organization", "organizations",
    "foundation", "foundations",
    "community", "program", "programs", "service", "services",
    "support", "initiative", "initiatives",
    "national", "local", "global", "international",
    "access", "based", "include", "including", "focused",
    "people", "individuals", "families", "groups",
}


def _kw_matches(kw: str, text: str) -> bool:
    """True if keyword appears in text, with basic singular/plural tolerance."""
    if kw in text:
        return True
    # "gardens" → try "garden"; "services" → try "service"; "diseases" → try "disease"
    if kw.endswith("ies") and len(kw) > 4 and kw[:-3] + "y" in text:
        return True
    if kw.endswith("es") and len(kw) > 4 and kw[:-2] in text:
        return True
    if kw.endswith("s") and len(kw) > 3 and kw[:-1] in text:
        return True
    return False


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
        return sum(1 for kw in keywords if _kw_matches(kw, text))

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

        # Phase 1: Federal grants — fetch 50 per query, then sort by title relevance
        federal_grants = []
        for i, q in enumerate(queries_to_run, 1):
            status.update(label=f"Searching Grants.gov: '{q}' ({i}/{len(queries_to_run)})...")
            federal_grants.extend(search_grants_gov(q, rows=50))
        federal_grants = deduplicate(federal_grants)
        federal_grants.sort(
            key=lambda g: _federal_relevance_score(g.get("title", ""), queries_to_run),
            reverse=True,
        )
        # Limit to top 25 after relevance sort so the UI stays manageable
        federal_grants = federal_grants[:25]
        st.write(f"Found **{len(federal_grants)}** federal grants (sorted by title relevance).")

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
        "similar_orgs":        similar_orgs,
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
    c3.metric("Similar Nonprofits (990 data)", len(r.get("similar_orgs", [])))

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
    else:
        st.caption(
            "Sorted by title relevance — grants whose titles best match your search terms "
            "appear first. Grants.gov searches the full text of all grant documents, so some "
            "results may match because the topic appears in eligibility or program descriptions, "
            "not the grant title. Click each link to see award amounts and confirm the fit."
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

    # ProPublica similar nonprofits
    similar_orgs = r.get("similar_orgs", [])
    if similar_orgs:
        st.divider()
        st.subheader(f"🔬 Similar Nonprofits Found in IRS 990 Database ({len(similar_orgs)} found)")
        st.caption(
            "These nonprofits have missions similar to your search terms. "
            "Check their IRS 990 filings to see which foundations have funded comparable work — "
            "a strong signal for which foundations may fund yours."
        )
        for org in similar_orgs:
            revenue_str = f"${org['revenue']:,}" if org.get("revenue") else "Not reported"
            city_state = ", ".join(filter(None, [org.get("city", ""), org.get("state", "")]))
            label = f"{org['name']}" + (f" — {city_state}" if city_state else "")
            with st.expander(label, expanded=False):
                col_a, col_b = st.columns(2)
                col_a.markdown(f"**Location:** {city_state or 'N/A'}")
                col_a.markdown(f"**NTEE Code:** {org.get('ntee_code') or 'N/A'}")
                col_b.markdown(f"**Annual Revenue:** {revenue_str}")
                col_b.markdown(f"**EIN:** {org.get('ein') or 'N/A'}")
                url = org.get("url", "")
                if url:
                    st.markdown(f"**IRS 990 Profile:** [{url}]({url})")

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
