# YEA Today Grant Finder Agent

Finds and drafts federal grant applications for YEA Today's youth entrepreneurship programs.  
**No API keys. No subscription. Completely free.**

| Component | What it does | Cost |
|---|---|---|
| Grants.gov API | Searches all US federal grants | Free, no key needed |
| Foundation scraper | Fetches 25 private foundation grant pages | Free, no key needed |
| ProPublica 990 API | Finds foundations that fund similar nonprofits | Free, no key needed |
| Ollama | Runs AI locally on your PC to analyze everything | Free, open source |
| Llama 3.1 | The AI model that ranks grants and writes drafts | Free |

> **Coverage note:** Grants.gov covers all federal grants. The foundation scraper covers 25 curated private foundations. Paid databases like Candid cover thousands more — but the free sources here capture a solid majority of realistic targets for YEA Today.

---

## Live Demo

`app.py` is a Streamlit web version — same three live data sources, but ranks results with Gemini (cloud) instead of local Ollama so it works as a public deployment, and skips the CLI's draft-writing phase to keep a run under a minute.

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key   # free at aistudio.google.com
streamlit run app.py
```

---

## One-time Setup (CLI version)

### Step 1 — Install Python
You need Python 3.10 or newer.  
Download: https://www.python.org/downloads/  
Check your version: `python --version`

### Step 2 — Install dependencies
Open a terminal in this folder and run:
```
pip install -r requirements.txt
```
This installs two packages: `requests` (HTTP calls) and `beautifulsoup4` (HTML parsing for foundation sites).

### Step 3 — Install Ollama
Ollama runs an AI model on your own computer (no internet needed for AI, no account).

1. Download from **https://ollama.com** and install it
2. Open a terminal and download the AI model:
   ```
   ollama pull llama3.1
   ```
   This downloads ~5GB once. After that it runs locally.

3. Start Ollama (on Windows it usually starts automatically in the system tray)

**Which model to use?**

| Model | RAM needed | Quality | Speed |
|---|---|---|---|
| `llama3.1` | ~8 GB | Best (recommended) | Moderate |
| `llama3.2` | ~4 GB | Good | Fast |
| `mistral` | ~6 GB | Good | Moderate |

If you use a different model, edit the `MODEL` line near the top of `agent.py`.

---

## Running the Agent

```
python agent.py
```

Expected runtime: **10–20 minutes** — fetching 25 foundation sites takes ~30 seconds, then Ollama generates the report and 3 drafts which takes the bulk of the time.

When it finishes:
- Open `output/reports/` → ranked list of grant opportunities with fit scores
- Open `output/drafts/` → three draft application narratives ready to edit and submit

---

## Customizing

| What to change | Where |
|---|---|
| YEA Today's program descriptions or outcomes | `config.py` → `ORG_PROFILE` |
| Grant size range or focus areas | `config.py` → `GRANT_CRITERIA` |
| Search keywords for Grants.gov | `config.py` → `SEARCH_QUERIES` |
| AI model (e.g. switch to mistral) | `agent.py` → `MODEL = "mistral"` |
| Number of drafts generated | `agent.py` → `extract_top_grants(grants, n=3)` |

---

## Folder Structure

```
grant-finder-agent/
├── agent.py               ← Run this
├── config.py              ← YEA Today profile and grant criteria
├── tools/
│   ├── search.py          ← Grants.gov API (federal grants)
│   ├── foundations.py     ← Scraper for 25 private foundation sites
│   ├── propublica.py      ← ProPublica 990 data for prospect research
│   └── files.py           ← Saves reports and drafts
├── output/
│   ├── reports/           ← Combined grant opportunity reports
│   └── drafts/            ← Application draft narratives
├── CLAUDE.md              ← Full agent documentation
└── requirements.txt       ← requests + beautifulsoup4
```

---

## Tips

- **Run monthly** — federal grant deadlines rotate throughout the year
- **Edit the drafts** — they are strong starting points; add real program numbers, staff names, and outcome data from YEA Today's records before submitting
- **Update `config.py`** when YEA Today launches new programs or enters new states
- **For private foundation grants** (Kauffman, JP Morgan, etc.), you'll need to search manually via Candid/Foundation Directory or grant newsletter services — those databases don't have free APIs

## Troubleshooting

**"Cannot connect to Ollama"**  
Open the Ollama app from your Start menu, or run `ollama serve` in a terminal, then try again.

**"model not found" error**  
Run `ollama pull llama3.1` in a terminal to download the model.

**Slow responses**  
Your machine may be running the model on CPU (no GPU). This is slower but still works. Try a smaller model: `ollama pull llama3.2` and set `MODEL = "llama3.2"` in `agent.py`.

**No grants found**  
Check your internet connection. Grants.gov may occasionally be down for maintenance.
