#!/usr/bin/env python3
"""
Generic career-page scraper -- the "ScrapeGraphAI-style" part, done for free.

How it mirrors ScrapeGraphAI:
    ScrapeGraphAI:  fetch page -> shrink HTML -> ASK AN LLM to extract fields
    this script:    fetch page -> find embedded schema.org/JobPosting JSON-LD
                    -> extract fields directly (no LLM, no API key, no cost)

Most career sites embed JobPosting structured data (Google requires it to list
jobs in search), so this works on a huge range of pages with zero LLM calls.

Reads career-page URLs from careers.csv and appends matches to jobs.csv,
using the SAME filters/schema as scrape.py.

Usage:
    python scrape_pages.py
"""
import csv
import json
import re
from pathlib import Path

import requests

# reuse the helpers + filters already written in scrape.py
import scrape as S

ROOT = Path(__file__).parent


def find_jsonld_blocks(html):
    """Return every <script type=application/ld+json> payload, parsed."""
    blocks = []
    for m in re.finditer(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, re.DOTALL | re.IGNORECASE):
        raw = m.group(1).strip()
        try:
            blocks.append(json.loads(raw))
        except Exception:
            # some sites emit multiple JSON objects or trailing commas; try light repair
            try:
                blocks.append(json.loads(re.sub(r",\s*([}\]])", r"\1", raw)))
            except Exception:
                continue
    return blocks


def iter_jobpostings(obj):
    """Walk arbitrary JSON-LD and yield every JobPosting node."""
    if isinstance(obj, list):
        for x in obj:
            yield from iter_jobpostings(x)
    elif isinstance(obj, dict):
        t = obj.get("@type", "")
        types = t if isinstance(t, list) else [t]
        if "JobPosting" in types:
            yield obj
        # @graph and nested containers
        for v in obj.values():
            if isinstance(v, (list, dict)):
                yield from iter_jobpostings(v)


def location_of(jp):
    loc = jp.get("jobLocation")
    if isinstance(loc, list):
        loc = loc[0] if loc else {}
    if isinstance(loc, dict):
        addr = loc.get("address", {})
        if isinstance(addr, dict):
            parts = [addr.get("addressLocality"), addr.get("addressRegion"),
                     addr.get("addressCountry")]
            parts = [p.get("name") if isinstance(p, dict) else p for p in parts]
            return ", ".join(p for p in parts if p)
    if (jp.get("jobLocationType") or "").upper() == "TELECOMMUTE":
        return "Remote"
    return ""


def to_record(jp, company_fallback, url_fallback):
    org = jp.get("hiringOrganization", {})
    company = org.get("name") if isinstance(org, dict) else (org or company_fallback)
    loc = location_of(jp)
    return dict(
        source="careerpage", company=company or company_fallback,
        title=jp.get("title", ""), location=loc,
        remote=("remote" in loc.lower()
                or (jp.get("jobLocationType") or "").upper() == "TELECOMMUTE"),
        url=jp.get("url") or url_fallback,
        posted=jp.get("datePosted", ""), tags=jp.get("employmentType", "") or "",
        description=S.strip_html(jp.get("description", ""))[:4000], status="new")


def scrape_url(url, company):
    try:
        html = S.get(url).text
    except Exception as e:
        print(f"  ! {url}: {e}")
        return []
    out = []
    for block in find_jsonld_blocks(html):
        for jp in iter_jobpostings(block):
            out.append(to_record(jp, company, url))
    return out


def main():
    f = ROOT / "careers.csv"
    if not f.exists():
        print("careers.csv not found -- add career-page URLs to it.")
        return
    with f.open(encoding="utf-8") as fh:
        targets = list(csv.DictReader(fh))

    seen, existing = S.load_existing()
    existing_keys = set(seen.keys())
    new_rows, raw = [], 0

    print("Career-page scraper (JSON-LD / no LLM)\n")
    for row in targets:
        url, company = row["url"].strip(), row.get("company_name", "").strip()
        print(f"-> {company or url} ...", end=" ", flush=True)
        jobs = scrape_url(url, company)
        raw += len(jobs)
        kept = 0
        for j in jobs:
            if not S.keep(j):
                continue
            key = j["url"] or f"{j['company']}|{j['title']}"
            if key in existing_keys:
                continue
            existing_keys.add(key)
            new_rows.append(j)
            kept += 1
        print(f"{len(jobs)} JobPostings found, {kept} new matches")

    all_rows = existing + new_rows
    with (ROOT / "jobs.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=S.FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    print(f"\nDone. {raw} JobPostings scanned -> {len(new_rows)} new "
          f"-> {len(all_rows)} total in jobs.csv")


if __name__ == "__main__":
    main()
