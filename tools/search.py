import requests

GRANTS_GOV_URL = "https://apply07.grants.gov/grantsws/rest/opportunities/search/"


def search_grants_gov(keyword: str, rows: int = 25) -> list[dict]:
    """
    Search Grants.gov for federal grant opportunities.
    Free public API — no key required.

    The search endpoint returns a limited set of fields per opportunity:
    id, number, title, agency, agencyCode, openDate, closeDate, oppStatus, cfdaList.
    Award amounts and descriptions are only on the individual detail pages.
    """
    payload = {
        "keyword": keyword,
        "rows": rows,
        "sortBy": "openDate|desc",
    }

    try:
        response = requests.post(
            GRANTS_GOV_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        response.raise_for_status()
    except requests.exceptions.ConnectionError:
        print("  Warning: Could not reach Grants.gov. Check your internet connection.")
        return []
    except requests.exceptions.HTTPError as e:
        print(f"  Warning: Grants.gov API error: {e}")
        return []

    data    = response.json()
    results = []

    for opp in data.get("oppHits", []):
        opp_id = str(opp.get("id", ""))
        # The search API returns "agency" (full name) and "agencyCode" (short code).
        agency = opp.get("agency") or opp.get("agencyCode") or ""
        cfda   = ", ".join(opp.get("cfdaList", []))
        results.append(
            {
                "id":                 opp_id,
                "title":              opp.get("title", ""),
                "agency":             agency,
                "opportunity_number": opp.get("number", ""),
                "open_date":          opp.get("openDate", ""),
                "close_date":         opp.get("closeDate", ""),
                "cfda":               cfda,
                "status":             opp.get("oppStatus", ""),
                "url":                f"https://www.grants.gov/search-results-detail/{opp_id}",
                # Award amounts are not in search results — only on the detail page.
                "award_ceiling":      "",
                "description":        "",
            }
        )

    return results


def deduplicate(grants: list[dict]) -> list[dict]:
    """Remove duplicate grants by opportunity ID."""
    seen   = set()
    unique = []
    for g in grants:
        if g["id"] not in seen:
            seen.add(g["id"])
            unique.append(g)
    return unique
