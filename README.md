# Scraper-AI

A worldwide **job-automation pipeline** that scrapes software / data / ML / quantum roles from free sources, ranks them against a candidate profile, and produces an apply-ready queue with tailored résumés — plus a curated **directory of 686 quantum-technology organizations** worldwide.

> **Apply is human-driven by design.** The pipeline gets you to a one-click *Submit* (ranked queue + tailored résumé + screening-answer sheet). It never auto-submits applications — that violates portal ToS, trips CAPTCHAs, and the screening questions (visa, salary, "why us") are yours to answer.

---

## 1 · Job Automation Pipeline

Scrapes jobs across the USA, Europe, Japan, India, Australia & New Zealand (remote-friendly), matches them to a résumé profile, and builds a targeted apply queue.

### How it works — cheapest tier first

The scraper tries the cheapest, most structured source first and only escalates when needed:

1. **ATS public APIs** — Greenhouse / Lever / Ashby. Free, structured, covers ~70% of companies.
2. **JSON-LD `JobPosting`** embedded in static career pages — free, no LLM needed (`scrape_pages.py`).
3. **Worldwide job-board APIs** — RemoteOK, Remotive, Jobicy, Arbeitnow.
4. *(optional)* **Headless render → extract** for JS-only SPA career pages.
5. *(optional)* **LLM extraction** — last resort, needs an API key.

### Repo layout

| File | Purpose |
|---|---|
| `config.json` | keywords, allowed countries, excluded locations, source toggles, `max_age_days` |
| `scrape.py` | main multi-source scraper → `jobs.csv` |
| `scrape_pages.py` | JSON-LD `JobPosting` extractor for static career pages |
| `detect.py` | ATS auto-detector + seeder — validates tokens against the live API before adding |
| `yc_seed.py` | seeds boards from the Y Combinator company directory |
| `match.py` | scores every job by weighted skill overlap + seniority fit → ranked `matches.csv` |
| `apply_queue.py` | tier-aware queue: prioritizes roles the candidate can realistically win, drops senior/non-technical titles → `apply_queue.csv` |
| `make_html.py` | résumé Markdown → print-ready HTML (Ctrl+P → Save as PDF) |
| `companies.csv` | validated ATS boards (`platform,token,company_name`) |
| `careers.csv` | career-page URLs for the JSON-LD scraper |
| `jobs.csv` · `matches.csv` · `apply_queue.csv` | scraped data, rankings, and the apply tracker |

### Quick start

Requires **Python 3.10+** (developed on 3.14).

```bash
pip install -r requirements.txt   # only dependency: requests

python detect.py          # (re)seed & validate company ATS boards
python yc_seed.py         # add Y Combinator companies (--all for the full set)
python scrape.py          # pull jobs       → jobs.csv
python match.py           # rank vs profile → matches.csv
python apply_queue.py 25  # build top-N queue → apply_queue.csv
python make_html.py       # regenerate printable résumés
```

### The apply queue

`apply_queue.py` is **tier-aware**: roles the candidate can realistically win (home-country + truly-global-remote) lead the queue and are never truncated, while country-locked remote roles (e.g. "Remote – US") are kept below as a clearly-labelled *stretch* tier. Senior/staff/lead and non-engineering titles are filtered out.

### Configure it for yourself

Edit `config.json` — `keywords_any`, `keywords_exclude`, `countries_allow`, `locations_exclude`, `max_age_days`, and the per-source toggles. Matching weights and the "realistic-to-win" location logic live in `match.py` and `apply_queue.py`.

> **Privacy:** personal résumés (`resume/`) and the screening-answer sheet (`answers.md`) are intentionally **git-ignored** and never leave your machine.

---

## 2 · Quantum Technology Organizations — Worldwide Directory

📁 **[`quantum companies/README.md`](quantum%20companies/README.md)**

A comprehensive, link-verified directory of **686 organizations** working on quantum technologies worldwide — computing, hardware & chips, software & algorithms, sensing & metrology, cryptography (QKD/QRNG/PQC), networking, and defence — across companies (startups → MNCs), national & government labs, universities (with named professors), and consortia.

| Category | Count |  | Category | Count |
|---|--:|---|---|--:|
| Universities & Research Groups | 177 | | Cryptography — QKD/QRNG/PQC | 65 |
| National & Government Labs | 138 | | Sensing & Metrology | 57 |
| Computing & Hardware | 110 | | Consortia & Initiatives | 24 |
| Software, Algorithms & Cloud | 76 | | Networking & Communications | 22 |
|  |  | | Defence & Government-Facing | 17 |

Every entry has an official URL. Contributions welcome — open an issue or PR for corrections and additions.

---

*Built with a focus on free, structured data sources over expensive scraping. Contributions and corrections welcome.*
