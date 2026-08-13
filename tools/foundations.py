"""
Curated list of private foundations and corporate giving programs covering a broad
range of funding areas — health, education, environment, arts, economic development,
social services, housing, veterans, disability, criminal justice, food security,
technology, animal welfare, and more.

Two fetch modes:
  fetch_all_light() — instant; returns curated metadata only (no HTTP requests)
  fetch_all()       — scrapes each grant page for live content (CLI agent use)
"""

import re
import time

import requests
from bs4 import BeautifulSoup

FOUNDATIONS = [
    # ── Major cross-sector foundations ─────────────────────────────────────────
    {
        "name": "Bill & Melinda Gates Foundation",
        "url": "https://www.gatesfoundation.org/about/how-we-work/grant-seeker-frequently-asked-questions",
        "about": "One of the world's largest private foundations; funds global health, infectious disease, poverty, K-12 education, teacher development, and early learning",
    },
    {
        "name": "Ford Foundation",
        "url": "https://www.fordfoundation.org/work/our-grants/",
        "about": "Funds economic inequality, racial justice, gender equality, arts and culture, freedom of expression, democracy, and human rights globally",
    },
    {
        "name": "MacArthur Foundation",
        "url": "https://www.macfound.org/grants/",
        "about": "Funds criminal justice reform, climate change, nuclear risk reduction, journalism, local Chicago initiatives, and awards MacArthur Fellowships",
    },
    {
        "name": "Rockefeller Foundation",
        "url": "https://www.rockefellerfoundation.org/grants/",
        "about": "Funds public health systems, food security and nutrition, clean energy access, urban resilience, economic opportunity, and pandemic preparedness",
    },
    {
        "name": "Kresge Foundation",
        "url": "https://kresge.org/grants-social-investments/",
        "about": "Funds arts and culture, education access, environment, climate, health care, human services, and community development in US cities",
    },
    {
        "name": "Pew Charitable Trusts",
        "url": "https://www.pewtrusts.org/en/about/funding-opportunities",
        "about": "Funds ocean conservation, environment, criminal justice reform, economic mobility, public health, civic research, and government accountability",
    },
    {
        "name": "Open Society Foundations",
        "url": "https://www.opensocietyfoundations.org/grants",
        "about": "Funds democracy, human rights, immigrant and refugee rights, racial justice, criminal justice reform, drug policy, education, and economic equity globally",
    },
    {
        "name": "Bloomberg Philanthropies",
        "url": "https://www.bloomberg.org/grant-initiatives/",
        "about": "Funds public health, environment, climate, arts, government innovation, gun violence prevention, and economic development in cities globally",
    },
    {
        "name": "Hewlett Foundation",
        "url": "https://hewlett.org/grants/",
        "about": "Funds environment and climate change, education quality, global development and economic growth, performing arts, and cybersecurity policy",
    },
    {
        "name": "Packard Foundation",
        "url": "https://www.packard.org/grants-and-investments/for-grant-seekers/",
        "about": "Funds conservation science, ocean health, climate solutions, children's health and development, reproductive health, science, and local California community grants",
    },
    {
        "name": "Rockefeller Brothers Fund",
        "url": "https://www.rbf.org/grants/applying-for-a-grant",
        "about": "Funds sustainable development, democratic practice, peacebuilding, climate change, nuclear policy, and social justice programs globally",
    },

    # ── Health & Medical ────────────────────────────────────────────────────────
    {
        "name": "Robert Wood Johnson Foundation",
        "url": "https://www.rwjf.org/en/grants.html",
        "about": "Largest health-focused private foundation in the US; funds public health, mental health, health equity, health care access, childhood obesity, and healthy communities",
    },
    {
        "name": "Susan G. Komen Foundation",
        "url": "https://www.komen.org/grants-programs/",
        "about": "Funds breast cancer research, early detection, treatment and support programs, and patient navigation for underserved communities",
    },
    {
        "name": "American Cancer Society",
        "url": "https://www.cancer.org/research/we-fund-cancer-research.html",
        "about": "Funds cancer research, oncology, clinical trials, cancer prevention, early detection, and patient support services for all types of cancer",
    },
    {
        "name": "American Heart Association",
        "url": "https://www.heart.org/en/professional/research/research-programs-and-funding",
        "about": "Funds cardiovascular disease research, heart disease prevention, stroke, cardiac care, and healthy lifestyle and wellness programs",
    },
    {
        "name": "March of Dimes",
        "url": "https://www.marchofdimes.org/research/grant-programs.aspx",
        "about": "Funds maternal and infant health, premature birth prevention, birth defects research, neonatal care, and infant mortality reduction",
    },
    {
        "name": "St. Baldrick's Foundation",
        "url": "https://www.stbaldricks.org/grants",
        "about": "Funds pediatric cancer research and childhood cancer treatment; focuses on leukemia, brain tumors, and other childhood and adolescent cancers",
    },
    {
        "name": "Mental Health America",
        "url": "https://mhanational.org/grants-and-funding",
        "about": "Funds mental health programs, behavioral health, mental illness awareness, suicide prevention, peer support, and community mental health services",
    },
    {
        "name": "National Multiple Sclerosis Society",
        "url": "https://www.nationalmssociety.org/Research/Research-Programs-and-Funding",
        "about": "Funds multiple sclerosis research, clinical trials, MS care programs, and quality of life programs for people living with MS and other neurological conditions",
    },
    {
        "name": "Simons Foundation",
        "url": "https://www.simonsfoundation.org/funding-opportunities/",
        "about": "Funds autism spectrum disorder research, neuroscience, brain science, genetics, mathematics, physics, and computational and life sciences",
    },
    {
        "name": "Conrad N. Hilton Foundation",
        "url": "https://www.hiltonfoundation.org/grants",
        "about": "Funds safe water access, substance use disorder prevention, homelessness among youth and families, foster care, and global humanitarian programs",
    },
    {
        "name": "Wellcome Trust",
        "url": "https://wellcome.org/grant-funding",
        "about": "Funds biomedical research, global infectious disease, mental health research, climate change and health, and science education programs globally",
    },

    # ── Education ───────────────────────────────────────────────────────────────
    {
        "name": "Lumina Foundation",
        "url": "https://www.luminafoundation.org/grants/",
        "about": "Funds higher education access and completion, college affordability, workforce credentials, adult learners, and equity for underrepresented students",
    },
    {
        "name": "Carnegie Corporation of New York",
        "url": "https://www.carnegie.org/grants/",
        "about": "Funds K-12 education, higher education, teacher development, adult literacy, immigration integration, democracy, and international peace",
    },
    {
        "name": "Spencer Foundation",
        "url": "https://www.spencer.org/grants",
        "about": "Funds education research, school improvement, learning sciences, equity in education, and evidence-based teaching and learning",
    },
    {
        "name": "Walton Family Foundation",
        "url": "https://www.waltonfamilyfoundation.org/grants",
        "about": "Funds K-12 education reform, charter schools, school choice, education innovation, and environmental conservation programs",
    },
    {
        "name": "Joyce Foundation",
        "url": "https://www.joycefdn.org/apply",
        "about": "Funds education, workforce development, gun violence prevention, democracy reform, and economic security programs in the Great Lakes region",
    },
    {
        "name": "Chan Zuckerberg Initiative",
        "url": "https://chanzuckerberg.com/grants-and-support/",
        "about": "Funds personalized learning, education technology, biomedical science, criminal justice reform, and affordable housing in California",
    },
    {
        "name": "Barr Foundation",
        "url": "https://www.barrfoundation.org/grants",
        "about": "Funds climate solutions, arts and culture, and education access programs in New England; supports college access and arts organizations in Boston",
    },

    # ── Environment & Climate ────────────────────────────────────────────────────
    {
        "name": "Environmental Defense Fund",
        "url": "https://www.edf.org/partnerships/grants",
        "about": "Funds climate change solutions, clean energy transition, air quality, sustainable fisheries, ocean conservation, and environmental health programs",
    },
    {
        "name": "Patagonia Environmental Grants",
        "url": "https://www.patagonia.com/how-we-fund-grassroots/",
        "about": "Funds grassroots environmental activism, land and water conservation, biodiversity protection, wilderness, and climate advocacy organizations",
    },
    {
        "name": "National Geographic Society",
        "url": "https://www.nationalgeographic.org/society/grants-and-investments/",
        "about": "Funds exploration, wildlife conservation, marine biology, ocean research, archaeology, cultural heritage preservation, and environmental education",
    },
    {
        "name": "Gordon and Betty Moore Foundation",
        "url": "https://www.moore.org/grants",
        "about": "Funds environmental conservation, marine and freshwater ecosystems, science research, patient care improvement, and local San Francisco Bay Area community programs",
    },
    {
        "name": "Bezos Earth Fund",
        "url": "https://www.bezosearthfund.org/grants",
        "about": "Funds climate change solutions, biodiversity protection, clean energy transition, sustainable food systems, and nature-based carbon solutions globally",
    },
    {
        "name": "Schmidt Futures",
        "url": "https://www.schmidtfutures.com/our-work/",
        "about": "Funds climate and clean energy technology, ocean health, scientific research, public interest technology, and programs at the intersection of science and policy",
    },

    # ── Arts & Culture ───────────────────────────────────────────────────────────
    {
        "name": "Mellon Foundation",
        "url": "https://www.mellon.org/grants",
        "about": "Funds arts and culture, performing arts organizations, museums, humanities scholarship, libraries, higher education, and literary arts programs",
    },
    {
        "name": "Doris Duke Charitable Foundation",
        "url": "https://www.ddcf.org/grant-programs/",
        "about": "Funds performing arts including jazz, contemporary dance, and theater; wildlife conservation, medical research, and child abuse prevention programs",
    },
    {
        "name": "Knight Foundation",
        "url": "https://knightfoundation.org/apply/",
        "about": "Funds journalism and independent media, arts and culture, community engagement, civic technology, and an informed and engaged citizenry",
    },

    # ── Social Services & Human Rights ──────────────────────────────────────────
    {
        "name": "Annie E. Casey Foundation",
        "url": "https://www.aecf.org/work/grants",
        "about": "Funds programs for at-risk children and families, foster care, juvenile justice reform, child welfare, family economic security, and poverty reduction",
    },
    {
        "name": "W.K. Kellogg Foundation",
        "url": "https://www.wkkf.org/grants",
        "about": "Funds vulnerable children, early childhood education, racial equity, food security, nutrition, community healing, and economic opportunity programs",
    },
    {
        "name": "Harry and Jeanette Weinberg Foundation",
        "url": "https://hjweinbergfoundation.org/grants/",
        "about": "Funds programs serving low-income, elderly, and vulnerable populations; covers hunger, housing, health care, education, and social services",
    },
    {
        "name": "Marguerite Casey Foundation",
        "url": "https://caseygrants.org/apply/",
        "about": "Funds low-income family economic success, racial justice, worker rights, policy advocacy, and community organizing to reduce inequality and poverty",
    },
    {
        "name": "Nathan Cummings Foundation",
        "url": "https://nathancummings.org/grants/",
        "about": "Funds racial and economic justice, climate change, arts and culture, democracy and civic engagement, and social justice advocacy",
    },

    # ── Economic Development & Workforce ────────────────────────────────────────
    {
        "name": "JPMorgan Chase Foundation",
        "url": "https://www.jpmorganchase.com/impact/philanthropy",
        "about": "Funds workforce development, job training, small business growth, financial inclusion, neighborhood revitalization, and economic mobility programs",
    },
    {
        "name": "Wells Fargo Foundation",
        "url": "https://www.wellsfargo.com/about/corporate-responsibility/community-giving/foundation/",
        "about": "Funds affordable housing, economic empowerment, small business, financial literacy, disaster relief, and community development programs",
    },
    {
        "name": "Bank of America Charitable Foundation",
        "url": "https://about.bankofamerica.com/en/making-an-impact/charitable-foundation-funding",
        "about": "Funds economic mobility, workforce development, affordable housing, food security, racial equality, and community development programs",
    },
    {
        "name": "Walmart Foundation",
        "url": "https://walmart.org/foundation/applying-for-grants",
        "about": "Funds workforce training and education, hunger relief, food access, environmental sustainability, disaster relief, and community economic opportunity",
    },
    {
        "name": "Ewing Marion Kauffman Foundation",
        "url": "https://www.kauffman.org/grants/",
        "about": "Funds entrepreneurship, small business development, youth entrepreneurship, startup ecosystems, higher education, and STEM programs",
    },
    {
        "name": "Citi Foundation",
        "url": "https://www.citifoundation.com/apply-for-a-grant/",
        "about": "Funds financial inclusion, economic empowerment, workforce development, and financial literacy programs for underserved communities globally",
    },

    # ── Youth & Children (broader) ───────────────────────────────────────────────
    {
        "name": "America's Promise Alliance",
        "url": "https://www.americaspromise.org/",
        "about": "Funds youth development, high school graduation, college and career readiness, mentoring, and youth employment and opportunity programs",
    },
    {
        "name": "National 4-H Foundation",
        "url": "https://4-hfund.org/grants/",
        "about": "Funds rural and urban youth development, STEM education, agriculture, food and nutrition, life skills, leadership, and 4-H community programs",
    },
    {
        "name": "Tory Burch Foundation",
        "url": "https://www.toryburchfoundation.org/programs/",
        "about": "Funds women entrepreneurs, women-owned small businesses, business education, access to capital, and economic empowerment for women",
    },
    {
        "name": "David Lucile Packard Foundation Children",
        "url": "https://www.packard.org/grants-and-investments/for-grant-seekers/",
        "about": "Funds children's health and development, pediatric health care, early childhood programs, and women's and reproductive health",
    },

    # ── Criminal Justice & Legal Aid ─────────────────────────────────────────────
    {
        "name": "Arnold Ventures",
        "url": "https://arnoldventures.org/grants",
        "about": "Funds criminal justice reform, pretrial justice, bail reform, reentry support, education access, health care policy, and public safety research",
    },
    {
        "name": "Vera Institute of Justice",
        "url": "https://www.vera.org/opportunities",
        "about": "Funds criminal justice system reform, jail and prison reduction, immigration legal services, reentry programs, and justice system transformation",
    },

    # ── Housing & Homelessness ───────────────────────────────────────────────────
    {
        "name": "Enterprise Community Partners",
        "url": "https://www.enterprisecommunity.org/financing-and-development/grants",
        "about": "Funds affordable housing development, homelessness prevention, community development, green building, and economic opportunity in low-income communities",
    },
    {
        "name": "NeighborWorks America",
        "url": "https://www.neighborworks.org/Funding-and-Grants",
        "about": "Funds affordable housing, homeownership programs, community development, foreclosure prevention, and neighborhood revitalization",
    },

    # ── Veterans & Military Families ─────────────────────────────────────────────
    {
        "name": "Gary Sinise Foundation",
        "url": "https://www.garysinisefoundation.org/programs/",
        "about": "Funds programs for veterans, active military, wounded warriors, first responders, and their families including adapted housing and wellness programs",
    },
    {
        "name": "Pat Tillman Foundation",
        "url": "https://pattillmanfoundation.org/apply-to-be-a-tillman-scholar/",
        "about": "Funds higher education scholarships for military veterans and active duty service members who demonstrate leadership and commitment to service",
    },

    # ── Disability & Accessibility ───────────────────────────────────────────────
    {
        "name": "Mitsubishi Electric America Foundation",
        "url": "https://www.meaf.org/grant-program/",
        "about": "Funds programs empowering youth and adults with disabilities through education, career development, independent living, and community inclusion",
    },
    {
        "name": "Christopher & Dana Reeve Foundation",
        "url": "https://www.christopherreeve.org/research/grants-and-funding",
        "about": "Funds spinal cord injury research, paralysis research, quality of life programs for people living with paralysis, and accessibility programs",
    },

    # ── Technology & Digital Access ──────────────────────────────────────────────
    {
        "name": "Mozilla Foundation",
        "url": "https://foundation.mozilla.org/en/what-we-fund/",
        "about": "Funds internet health, digital privacy, AI ethics, internet access equity, open source software, and online trust and safety programs",
    },
    {
        "name": "Verizon Foundation",
        "url": "https://www.verizon.com/about/responsibility/giving",
        "about": "Funds digital inclusion, internet access for underserved communities, STEM education, digital literacy, and first responder technology programs",
    },
    {
        "name": "Google.org",
        "url": "https://www.google.org/",
        "about": "Funds technology for social impact, AI for good, education technology, economic opportunity, racial equity, and crisis response programs globally",
    },

    # ── Food Security & Nutrition ────────────────────────────────────────────────
    {
        "name": "Whole Kids Foundation",
        "url": "https://www.wholekidsfoundation.org/programs/school-garden-grant",
        "about": "Funds school garden programs, healthy eating and nutrition education for children, salad bars in schools, and childhood nutrition programs",
    },
    {
        "name": "Feeding America",
        "url": "https://www.feedingamerica.org/our-work/partner-with-us",
        "about": "Funds food banks, hunger relief programs, food insecurity, food pantries, meal programs, and hunger advocacy for low-income families",
    },

    # ── Animal Welfare ───────────────────────────────────────────────────────────
    {
        "name": "PetSmart Charities",
        "url": "https://petsmartcharities.org/pro-center/get-funding",
        "about": "Funds pet adoption, spay and neuter programs, animal rescue, shelter operations, homeless pet programs, and companion animal welfare",
    },
    {
        "name": "Petco Foundation",
        "url": "https://petcofoundation.org/grants/",
        "about": "Funds animal welfare, pet adoption programs, animal rescue organizations, spay and neuter services, and lifesaving animal shelters",
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

_CONTENT_LIMIT = 200


def _scrape(url: str) -> str:
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
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:_CONTENT_LIMIT]


def fetch_all_light(on_progress=None) -> list[dict]:
    """
    Return foundation data instantly using only curated metadata — no HTTP requests.
    Use this in the Streamlit app for fast page loads.
    """
    results = []
    total = len(FOUNDATIONS)
    for i, f in enumerate(FOUNDATIONS, 1):
        if on_progress:
            on_progress(i, total, f["name"])
        results.append(
            {
                "name": f["name"],
                "about": f["about"],
                "url": f["url"],
                "page_content": "",
            }
        )
    return results


def fetch_all(verbose: bool = True, on_progress=None) -> list[dict]:
    """
    Scrape all foundation grant pages and return live content.
    Use this in the CLI agent where scraping time is acceptable.
    """
    results = []
    total = len(FOUNDATIONS)

    for i, f in enumerate(FOUNDATIONS, 1):
        if verbose:
            print(f"  [{i}/{total}] {f['name']}")
        if on_progress:
            on_progress(i, total, f["name"])
        content = _scrape(f["url"])
        results.append(
            {
                "name": f["name"],
                "about": f["about"],
                "url": f["url"],
                "page_content": content,
            }
        )
        time.sleep(0.75)

    return results
