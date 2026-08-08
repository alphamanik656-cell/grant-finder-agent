"""
Scrapes publicly accessible grant pages from a curated list of private foundations
known to fund youth entrepreneurship, education, and workforce development.

Note: Some foundation sites use JavaScript rendering — those pages may return
limited content. The scraper falls back gracefully and notes when a page
couldn't be read.
"""

import re
import time

import requests
from bs4 import BeautifulSoup

# Foundations with known interest in youth entrepreneurship / education / workforce dev.
# URLs point to their grants, apply, or giving-priorities pages.
FOUNDATIONS = [
    {
        "name": "Ewing Marion Kauffman Foundation",
        "url": "https://www.kauffman.org/grants/",
        "about": "One of the largest foundations dedicated to entrepreneurship and education; funds youth entrepreneur programs nationally",
    },
    {
        "name": "T-Mobile Hometown Grants",
        "url": "https://www.t-mobile.com/community/hometown-grants",
        "about": "Quarterly grants up to $50,000 for nonprofits in underserved communities; open application",
    },
    {
        "name": "Citi Foundation",
        "url": "https://www.citifoundation.com/apply-for-a-grant/",
        "about": "Funds economic empowerment, workforce development, and financial inclusion programs for youth",
    },
    {
        "name": "Wells Fargo Foundation",
        "url": "https://www.wellsfargo.com/about/corporate-responsibility/community-giving/foundation/",
        "about": "Economic empowerment, financial literacy, and small business development",
    },
    {
        "name": "JPMorgan Chase Foundation",
        "url": "https://www.jpmorganchase.com/impact/philanthropy",
        "about": "Workforce development, small business, and economic opportunity — strong focus on underserved youth",
    },
    {
        "name": "Walmart Foundation",
        "url": "https://walmart.org/foundation/applying-for-grants",
        "about": "Workforce development, community resilience, and economic mobility grants",
    },
    {
        "name": "Bank of America Charitable Foundation",
        "url": "https://about.bankofamerica.com/en/making-an-impact/charitable-foundation-funding",
        "about": "Economic mobility, workforce development, and community building",
    },
    {
        "name": "Prudential Foundation",
        "url": "https://www.prudential.com/links/about/corporate-social-responsibility/prudential-foundation",
        "about": "Financial wellness, workforce development, and economic empowerment",
    },
    {
        "name": "MetLife Foundation",
        "url": "https://www.metlife.com/metlife-foundation/",
        "about": "Financial health, inclusion, and economic opportunity programs",
    },
    {
        "name": "Annie E. Casey Foundation",
        "url": "https://www.aecf.org/work/grants",
        "about": "Youth and family economic success; workforce and employment programs for young people",
    },
    {
        "name": "W.K. Kellogg Foundation",
        "url": "https://www.wkkf.org/grants",
        "about": "Youth development, education, and economic opportunity for underserved communities",
    },
    {
        "name": "Lumina Foundation",
        "url": "https://www.luminafoundation.org/grants/",
        "about": "Education beyond high school, workforce credentials, and career pathways for youth",
    },
    {
        "name": "Charles Schwab Foundation",
        "url": "https://www.schwabmoneywise.com/about/schwab-foundation",
        "about": "Financial literacy and economic education programs",
    },
    {
        "name": "Walton Family Foundation",
        "url": "https://www.waltonfamilyfoundation.org/grants",
        "about": "K-12 education reform and community development programs",
    },
    {
        "name": "Tory Burch Foundation",
        "url": "https://www.toryburchfoundation.org/programs/",
        "about": "Women entrepreneurs and small business development programs",
    },
    {
        "name": "Verizon Foundation",
        "url": "https://www.verizon.com/about/responsibility/giving",
        "about": "Digital skills, STEM education, and economic empowerment for youth",
    },
    {
        "name": "FedEx Foundation",
        "url": "https://www.fedex.com/en-us/csr/grants-and-foundation-giving.html",
        "about": "Community and economic opportunity; small business and entrepreneurship support",
    },
    {
        "name": "Lowe's Foundation",
        "url": "https://newsroom.lowes.com/lowes-foundation",
        "about": "Skilled trades education and workforce development for young people",
    },
    {
        "name": "Google.org",
        "url": "https://www.google.org/",
        "about": "Technology, education, and economic opportunity — occasionally funds entrepreneur education programs",
    },
    {
        "name": "America's Promise Alliance",
        "url": "https://www.americaspromise.org/",
        "about": "Youth development, graduation, and career readiness programs",
    },
    {
        "name": "National 4-H Foundation",
        "url": "https://4-hfund.org/grants/",
        "about": "Youth development including entrepreneurship and life skills programs",
    },
    {
        "name": "US Chamber of Commerce Foundation",
        "url": "https://www.uschamberfoundation.org/workforce-development",
        "about": "Workforce development and youth entrepreneurship programs",
    },
    {
        "name": "Junior Achievement USA",
        "url": "https://www.juniorachievement.org/web/ja-usa/partnerships",
        "about": "Youth entrepreneurship and financial literacy — may have partnership/grant opportunities",
    },
    {
        "name": "Joyce Foundation",
        "url": "https://www.joycefdn.org/apply",
        "about": "Workforce, education, and economic opportunity in the Midwest",
    },
    {
        "name": "Rockefeller Brothers Fund",
        "url": "https://www.rbf.org/grants/applying-for-a-grant",
        "about": "Democratic practice, global challenges, and sustainable development including youth empowerment",
    },
]

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

_CONTENT_LIMIT = 200  # chars per foundation page — keeps prompts small for faster CPU inference


def _scrape(url: str) -> str:
    """Fetch a page and return cleaned plain text, capped at _CONTENT_LIMIT chars."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=12)
        r.raise_for_status()
    except requests.exceptions.SSLError:
        return "(SSL error — could not fetch page)"
    except requests.exceptions.ConnectionError:
        return "(Connection error — site may be down or blocking scrapers)"
    except requests.exceptions.Timeout:
        return "(Timeout — site did not respond in time)"
    except requests.exceptions.HTTPError as e:
        return f"(HTTP {e.response.status_code} — page not accessible)"
    except Exception as e:
        return f"(Error: {e})"

    soup = BeautifulSoup(r.text, "html.parser")

    # Remove noise tags
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()

    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:_CONTENT_LIMIT]


def fetch_all(verbose: bool = True) -> list[dict]:
    """
    Scrape all foundation grant pages and return a list of dicts with
    name, about, url, and scraped page content.
    """
    results = []
    total = len(FOUNDATIONS)

    for i, f in enumerate(FOUNDATIONS, 1):
        if verbose:
            print(f"  [{i}/{total}] {f['name']}")
        content = _scrape(f["url"])
        results.append(
            {
                "name": f["name"],
                "about": f["about"],
                "url": f["url"],
                "page_content": content,
            }
        )
        time.sleep(0.75)  # polite crawl delay

    return results
