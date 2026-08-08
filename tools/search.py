import requests

GRANTS_GOV_URL = "https://apply07.grants.gov/grantsws/rest/opportunities/search/"

RELEVANT_CATEGORIES = "YS:ED:WD:OZ"  # Youth Services, Education, Workforce Dev, Other


def search_grants_gov(keyword: str, rows: int = 25) -> list[dict]:
    """
    Search Grants.gov for federal grant opportunities.
    Free public API — no key required.
    """
    payload = {
        "keyword": keyword,
        "oppStatuses": "posted:forecasted",
        "fundingCategories": RELEVANT_CATEGORIES,
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

    data = response.json()
    results = []

    for opp in data.get("oppHits", []):
        opp_id = opp.get("id", "")
        results.append(
            {
                "id": str(opp_id),
                "title": opp.get("title", ""),
                "agency": opp.get("agencyName", ""),
                "opportunity_number": opp.get("number", ""),
                "open_date": opp.get("openDate", ""),
                "close_date": opp.get("closeDate", ""),
                "description": (opp.get("synopsis") or "")[:400],
                "award_ceiling": opp.get("awardCeiling", ""),
                "award_floor": opp.get("awardFloor", ""),
                "estimated_funding": opp.get("estimatedTotalProgramFunding", ""),
                "expected_awards": opp.get("expectedNumberOfAwards", ""),
                "status": opp.get("oppStatus", ""),
                "url": f"https://www.grants.gov/search-results-detail/{opp_id}",
            }
        )

    return results


def deduplicate(grants: list[dict]) -> list[dict]:
    """Remove duplicate grants by opportunity ID."""
    seen = set()
    unique = []
    for g in grants:
        if g["id"] not in seen:
            seen.add(g["id"])
            unique.append(g)
    return unique
