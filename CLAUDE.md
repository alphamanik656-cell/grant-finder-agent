# YEA Today Grant Finder Agent

## Purpose

Searches Grants.gov for federal grant opportunities aligned with YEA Today's youth entrepreneurship mission, then uses a local AI model (via Ollama) to rank, analyze, and draft application narratives. **No API keys or subscriptions required.**

---

## Organization: YEA Today

| Field | Detail |
|---|---|
| **Full Name** | YEA Today (Youth Entrepreneurship Alliance Today) |
| **Type** | 501(c)(3) National Nonprofit |
| **Mission** | Developing entrepreneurship programs for youth across the United States |
| **Target Population** | Youth ages 12–24, emphasis on underserved and underrepresented communities |
| **Geographic Reach** | National (US-wide programs and chapter network) |

### Core Programs
- Youth entrepreneurship workshops and bootcamps
- Mentorship programs connecting youth with business leaders
- Business plan competitions
- Financial literacy curriculum
- Student-run microenterprise programs

### Demonstrated Outcomes
- Youth completing full business plans and launching ventures
- Increased financial literacy scores among participants
- Youth employment and self-employment rates post-program
- Youth-led businesses operating 12 months after program completion

---

## Architecture

```
agent.py
  │
  ├── Phase 1a: Federal grants
  │     └── tools/search.py       →  Grants.gov API (free, no auth)
  │
  ├── Phase 1b: Private foundations
  │     └── tools/foundations.py  →  Scrapes 25 foundation grant pages
  │
  ├── Phase 1c: Foundation prospects
  │     └── tools/propublica.py   →  ProPublica 990 API (free, no auth)
  │
  ├── Phase 2: Combined report
  │     └── Ollama (local AI)     →  output/reports/
  │
  └── Phase 3: Draft applications
        └── Ollama (local AI)     →  output/drafts/
```

**No external API calls for AI** — Ollama runs entirely on the user's machine.  
**Three external data sources** — all free, all require no authentication.

---

## Data Sources

### 1. Grants.gov
- **URL:** https://apply07.grants.gov/grantsws/rest/opportunities/search/
- **Auth:** None required
- **Coverage:** All US federal grant opportunities
- **Limitation:** Federal grants only — private foundations not included
- **Search categories used:** YS (Youth Services), ED (Education), WD (Workforce Dev)

### 2. Foundation Scraper (tools/foundations.py)
- **Coverage:** 25 curated private foundation grant pages
- **Method:** HTTP fetch + BeautifulSoup text extraction → Ollama analysis
- **Limitation:** Some foundation sites use JS rendering; content may be limited. Many foundations don't post open RFPs publicly (invitation-only or rolling).
- **Output:** Open grants (if found) + warm prospect assessments

### 3. ProPublica Nonprofit Explorer API
- **URL:** https://projects.propublica.org/nonprofits/api/v2/
- **Auth:** None required
- **Coverage:** IRS 990 filings for all US nonprofits
- **Use:** Finds organizations similar to YEA Today; identifies foundations that have historically funded similar work
- **Limitation:** Historical data only — shows past giving, not current open grants

---

## AI Model: Ollama

- **Default model:** `llama3.1` (8B parameters)
- **Alternatives:** `llama3.2` (3B, faster), `mistral` (7B)
- **API:** `POST http://localhost:11434/api/chat`
- **Runs:** Entirely on the user's local machine — no internet required for AI

---

## Agent Phases

### Phase 1a — Federal Grant Search
Runs all queries in `config.py → SEARCH_QUERIES` against Grants.gov.  
Deduplicates by opportunity ID. Caps each query at 20 results.

### Phase 1b — Foundation Website Scraping
Fetches grant/apply pages for 25 curated private foundations. BeautifulSoup strips HTML noise; first 800 chars of text per page is kept and sent to Ollama.

### Phase 1c — ProPublica 990 Research
Searches IRS 990 data for nonprofits with similar missions. Returns a list of comparable organizations with ProPublica profile URLs — useful for identifying which foundations have funded work like YEA Today's.

### Phase 2 — Combined Report
All three data sources are sent to Ollama in one prompt. Ollama produces a ranked Markdown report covering:
- Top federal grant opportunities (with fit scores)
- Top private foundation opportunities (open grants + warm prospects)
- Foundation leads from 990 data
- Recommended next steps

Output: `output/reports/grant-report-YYYY-MM-DD.md`

### Phase 3 — Draft Applications
Generates 3 draft narratives: top 2 federal grants + top 1 foundation match.  
Each draft includes: org description, problem statement, program description, SMART goals, budget narrative, evaluation plan.

Output: `output/drafts/draft-[grant-name]-YYYY-MM-DD.md`

---

## Grant Criteria

**Primary focus:** $1,000–$25,000 grants open to 501(c)(3) nonprofits  
**Geography:** National (US-wide) or multi-state  
**Status:** Posted (currently open) or Forecasted (opening soon)

**Strong-fit focus areas:** youth entrepreneurship, workforce development, business education, financial literacy, youth economic empowerment, youth leadership

**Skip:** Grants requiring government fiscal agents, grants restricted to schools/LEAs only, grants with deadlines under 2 weeks, clear mission mismatch

---

## Customization

| What | File | Where |
|---|---|---|
| YEA Today's program descriptions | `config.py` | `ORG_PROFILE` |
| Grant criteria and focus areas | `config.py` | `GRANT_CRITERIA` |
| Federal search keywords | `config.py` | `SEARCH_QUERIES` |
| Add/remove foundations | `tools/foundations.py` | `FOUNDATIONS` list |
| AI model | `agent.py` | `MODEL = "llama3.1"` |
| Draft split (federal vs. foundation) | `agent.py` | `top_federal` / `top_foundation` slices |
| System prompt / AI behavior | `agent.py` | `SYSTEM_PROMPT` |

---

## Setup Requirements

- Python 3.10+
- `pip install -r requirements.txt` (just the `requests` library)
- Ollama installed and running: https://ollama.com
- Model downloaded: `ollama pull llama3.1`
- Internet connection (for Grants.gov searches only)

## Running

```bash
python agent.py
```

Expected runtime: 5–15 minutes.
