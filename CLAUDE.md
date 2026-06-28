# Job Automation Pipeline — Full Context

> Hand this to Claude Code (it auto-loads `CLAUDE.md` from the working dir).
> Project lives at `D:\scraper`. Python 3.14 on Windows. Owner: Manas (manasvamsi88@gmail.com).

## Goal
Scrape software/data/ML/quantum jobs worldwide, match them to Manas's resume, and
produce tailored, apply-ready resumes. Target countries: **USA, Europe, Japan, India,
Australia, New Zealand**. Exclude Pakistan. Remote-friendly.

**Apply step is human-driven.** Auto-submitting applications was rejected: it violates
portal ToS (ban risk), trips CAPTCHAs, and screening questions (visa, salary, "why us")
are human-only. The pipeline gets Manas to one-click submit; he clicks Submit himself.
(If the **Playwright** plugin is installed, browser-assisted form-filling becomes possible
in his own logged-in browser — still semi-auto, still needs his review per application.)

## Architecture — cheapest tier first (learned from studying ScrapeGraphAI)
1. **ATS public APIs** (Greenhouse / Lever / Ashby) — free, structured, ~70% of companies.
2. **JSON-LD `JobPosting`** in static HTML (`scrape_pages.py`) — free, many static sites.
3. **Worldwide job-board APIs** — RemoteOK, Remotive, Jobicy, Arbeitnow.
4. **Playwright render → extract** — only for JS-only SPA pages (needs Playwright plugin).
5. **LLM extraction** (true ScrapeGraphAI style) — last resort, needs an LLM key.

## Files
| File | Purpose |
|---|---|
| `config.json` | keywords_any / keywords_exclude, countries_allow, locations_exclude (Pakistan), max_age_days, source toggles, optional Adzuna key |
| `companies.csv` | 479 validated ATS boards (platform, token, company_name) |
| `careers.csv` | career-page URLs for the JSON-LD scraper |
| `new_companies.txt` | (optional) paste careers URLs; `detect.py` auto-resolves ATS + token |
| `scrape.py` | main scraper across all API sources → `jobs.csv` |
| `scrape_pages.py` | JSON-LD JobPosting extractor for career-page URLs |
| `detect.py` | ATS auto-detector + seeder; **validates tokens against live API before adding** |
| `yc_seed.py` | pulls YC directory (yc-oss.github.io/api), probes slugs → validated boards |
| `match.py` | scores `jobs.csv` against Manas's profile → ranked `matches.csv` |
| `apply_queue.py` | filters out senior/staff/lead → `apply_queue.csv` (top N + apply links + tracker) |
| `make_html.py` | resume .md → print-ready HTML (Ctrl+P → Save as PDF) |
| `answers.md` | screening-answer cheat-sheet (fill `[brackets]` once, copy-paste per app) |
| `resume/master.md` | canonical resume |
| `resume/tailored/*.md` | per-job tailored resumes |
| `resume/html/*.html` | printable versions |
| `jobs.csv` / `matches.csv` / `apply_queue.csv` | data + tracking |

## Standard workflow
```
python detect.py        # (re)seed/validate company boards
python yc_seed.py        # add YC companies (use --all for ~6000)
python scrape.py         # pull jobs → jobs.csv
python match.py          # rank → matches.csv
python apply_queue.py 20 # build apply_queue.csv
python make_html.py      # regenerate printable resumes
```

## Current status (2026-06-27)
- `companies.csv`: 491 boards (pruned dead Ashby token `abundant`, was 404ing each scrape).
- `jobs.csv`: 1011 matched jobs (16,910 scanned, re-scraped 2026-06-27 after config changes).
  `matches.csv`: 1011 ranked (match.py copies every job, so matches row-count == jobs row-count).
- `apply_queue.csv`: now **tier-aware** (open item #3 done). India + truly-global-remote roles lead
  and are never truncated; US/Canada "country-locked" roles kept as a labeled *stretch* tier below.
  Non-engineering titles (account exec, BDR, collections, recruiter…) filtered out. Current top 25 =
  12 realistic (India/global-remote) + 13 stretch.
- Tailored resumes (7): Ramp (Applied-AI Fullstack), Axle (DS Fellow), Affirm (SWE II Full-stack) —
  all US-locked — **plus 4 new India roles**: Postman (SWE Authorization, Hyderabad), Turing (Forward
  Deployed AI Engineer, Mumbai), HackerRank (AI Researcher, Bangalore), Netomi (Agentic Engineer, Remote-India).
  Level caveats: Turing asks 4–8 yrs, Postman asks 3 yrs (Manas has ~2) — strong skills/location fit, applied as stretches.

## Manas's profile (for tailoring/matching)
- **Education:** B.Tech ECE, NIT Andhra Pradesh.
- **Nexvista — Software Engineer (Jun 2024–present):** Elixir/Phoenix LiveView real-estate CRM;
  built analytics/reporting engine (pivot/flat, multi-table joins, type-safe filtering, field
  introspection+caching), real-time report & dashboard builders, VoIP integration, automated tests.
- **Wipro — Associate Engineer (Jul–Nov 2023):** data prep/cleaning/labeling for **Waymo**
  self-driving-car ML; annotation in the **Carta** tool. (Do NOT describe this as non-IT.)
- **iAssist Innovation Labs — Data Scientist Intern (May–Jul 2023):** dataset curation/labeling.
- **Projects:** QRIVARA (quantum chip-design platform, React/TS/Three.js + FastAPI, ~99% gate
  fidelity sim, GDS-II export, Qiskit digital twin); Quantum Codebook (Qiskit/Cirq/PennyLane edu
  platform); Nyra (offline local-first LLM voice agent — LangGraph + Ollama + MCP); NLP Resume-Job
  matching ATS (82%); Carbon Emissions of GPUs in LLM training (87%); COVID-19 pneumonia CV (92%).
- **Two angles:** (1) Backend/Full-stack SWE (Elixir/Phoenix, React/FastAPI), (2) Data Science/ML
  (NLP, DL, data pipelines, quantum). Tailor toward whichever each job emphasizes.
- **GitHub:** github.com/manas-vamsi (main, has QRIVARA/Nyra/etc.), github.com/Manasa-vamsi.
- **Level:** early-career (~2 yrs). Prefer roles without senior/staff/lead/principal in title.

## Open items / next steps
1. **Confirm Wipro year** (assumed Jul–Nov 2023 from timeline — verify).
2. **Finalize `answers.md`** with city, work-authorization, notice period, relocation, sponsorship.
3. ~~Re-filter `apply_queue.py` to prioritize India + truly-global-remote.~~ **DONE (2026-06-27)** —
   queue is tier-aware; realistic roles lead, country-locked kept as labeled stretch tier.
4. **PDF export** currently = HTML + manual Ctrl+P. Could automate with a headless converter later.
5. **Gmail/Google integration** (Manas has a Google OAuth client ID): scope it — likely reading
   job-reply emails. ⚠️ NEVER put client secret / API keys in chat; use a local `.env`.
6. If **Playwright** plugin installed: add a tier-4 fetcher for SPA career pages, and optionally a
   browser-assisted apply helper (Manas logged in; review each submit).

## Useful plugins (Manas is evaluating)
- **Playwright** ⭐ — browser automation for SPA scraping + assisted apply.
- **claude-mem** ⭐ — cross-session persistent memory for this ongoing project.
- **Superpowers** — dev methodology (planning/TDD/review) for building robustly.
- **security-guidance** — safe handling of OAuth/API credentials.
- Skip for now: typescript-lsp, mcp-server-dev (not needed for a Python pipeline).
