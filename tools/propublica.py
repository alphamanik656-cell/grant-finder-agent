"""
Uses ProPublica's free Nonprofit Explorer API (no key required) to find
foundations and funders that have historically given grants to organizations
similar to YEA Today.

Strategy:
  1. Search for nonprofits similar to YEA Today (youth entrepreneurship / workforce dev)
  2. For each match, fetch their 990 filing to see who funded them
  3. Aggregate that funder data into a prospect list
"""

import requests

_BASE = "https://projects.propublica.org/nonprofits/api/v2"

# NTEE codes for organizations similar to YEA Today
# S30 = Youth Development Programs
# J22 = Job Training
# S20 = Community Organizing
# B = Education (general)
_SEARCH_TERMS = [
    "youth entrepreneurship",
    "youth business education",
    "youth workforce development",
    "entrepreneurship education nonprofit",
]


def _search_orgs(query: str, state: str = "") -> list[dict]:
    """Search ProPublica for nonprofits matching a query."""
    params = {"q": query}
    if state:
        params["state[id]"] = state

    try:
        r = requests.get(f"{_BASE}/search.json", params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("organizations", [])
    except Exception:
        return []


def _get_990_filing(ein: str) -> dict | None:
    """Fetch the most recent 990 filing for a nonprofit by EIN."""
    try:
        r = requests.get(f"{_BASE}/organizations/{ein}.json", timeout=15)
        r.raise_for_status()
        data = r.json()
        filings = data.get("filings_with_data", [])
        return filings[0] if filings else None
    except Exception:
        return None


def find_foundation_prospects(max_orgs: int = 10) -> list[dict]:
    """
    Search for nonprofits similar to YEA Today, look at their 990 data
    to find which foundations have funded them, and return a deduplicated
    list of funder prospects.

    Returns a list of dicts: {name, city, state, revenue, ntee_code, url}
    representing similar funded organizations (useful context for Ollama analysis).
    """
    seen_eins = set()
    similar_orgs = []

    for query in _SEARCH_TERMS:
        orgs = _search_orgs(query)
        for org in orgs[:5]:  # top 5 per query
            ein = str(org.get("ein", "")).strip()
            if not ein or ein in seen_eins:
                continue
            seen_eins.add(ein)
            similar_orgs.append(
                {
                    "name": org.get("name", ""),
                    "city": org.get("city", ""),
                    "state": org.get("state", ""),
                    "ntee_code": org.get("ntee_code", ""),
                    "revenue": org.get("revenue_amount", 0),
                    "ein": ein,
                    "url": f"https://projects.propublica.org/nonprofits/organizations/{ein}",
                }
            )
            if len(similar_orgs) >= max_orgs:
                break
        if len(similar_orgs) >= max_orgs:
            break

    return similar_orgs


def format_for_ai(orgs: list[dict]) -> str:
    """Format the list of similar orgs for inclusion in an Ollama prompt."""
    if not orgs:
        return "No similar organizations found in ProPublica database."

    lines = [
        "The following nonprofits with similar missions to YEA Today were found in IRS 990 data. "
        "Use this to identify foundations likely to fund YEA Today based on their giving history "
        "to similar organizations.\n"
    ]
    for o in orgs:
        revenue = f"${o['revenue']:,}" if o['revenue'] else "N/A"
        lines.append(
            f"- {o['name']} ({o['city']}, {o['state']}) | "
            f"NTEE: {o['ntee_code']} | Revenue: {revenue} | "
            f"Profile: {o['url']}"
        )

    return "\n".join(lines)
