"""
Uses ProPublica's free Nonprofit Explorer API (no key required) to find
organizations similar to the user's, based on their search terms.

Strategy:
  1. Search for nonprofits matching the user's topic keywords
  2. For each match, include their profile URL and basic financial info
  3. Return a list useful for the AI to identify likely foundation funders
"""

import requests

_BASE = "https://projects.propublica.org/nonprofits/api/v2"

_DEFAULT_SEARCH_TERMS = [
    "nonprofit community services",
    "charitable organization programs",
]


def _search_orgs(query: str, state: str = "") -> list[dict]:
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
    try:
        r = requests.get(f"{_BASE}/organizations/{ein}.json", timeout=15)
        r.raise_for_status()
        data = r.json()
        filings = data.get("filings_with_data", [])
        return filings[0] if filings else None
    except Exception:
        return None


def find_foundation_prospects(
    search_terms: list[str] | None = None, max_orgs: int = 10
) -> list[dict]:
    """
    Search ProPublica for nonprofits matching the user's search terms.
    Returns similar organizations useful for identifying who funds this type of work.

    search_terms: list of keyword strings from the user's search (e.g. ["pediatric cancer"])
    """
    terms = search_terms if search_terms else _DEFAULT_SEARCH_TERMS

    seen_eins = set()
    similar_orgs = []

    for query in terms:
        orgs = _search_orgs(query)
        for org in orgs[:5]:
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
    if not orgs:
        return "No similar organizations found in ProPublica database."

    lines = [
        "The following nonprofits with similar missions were found in IRS 990 data. "
        "Use this to identify foundations likely to fund similar work based on their "
        "giving history to comparable organizations.\n"
    ]
    for o in orgs:
        revenue = f"${o['revenue']:,}" if o["revenue"] else "N/A"
        lines.append(
            f"- {o['name']} ({o['city']}, {o['state']}) | "
            f"NTEE: {o['ntee_code']} | Revenue: {revenue} | "
            f"Profile: {o['url']}"
        )

    return "\n".join(lines)
