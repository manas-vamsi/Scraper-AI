#!/usr/bin/env python3
"""
Multi-source job scraper.

Pulls jobs from worldwide job-board APIs + per-company ATS boards,
filters by your keywords / countries (excludes Pakistan), de-dupes,
and writes everything to jobs.csv.

Usage:
    pip install -r requirements.txt
    python scrape.py
"""
import csv
import json
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8"))
UA = {"User-Agent": "Mozilla/5.0 (job-scraper; personal use)"}
TIMEOUT = 25

# unified job record keys
FIELDS = ["source", "company", "title", "location", "remote", "url",
          "posted", "tags", "description", "status"]


# --------------------------------------------------------------------------- #
#  helpers
# --------------------------------------------------------------------------- #
def get(url, **kw):
    kw.setdefault("headers", UA)
    kw.setdefault("timeout", TIMEOUT)
    r = requests.get(url, **kw)
    r.raise_for_status()
    return r


def strip_html(s):
    if not s:
        return ""
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def matches_keywords(text):
    t = text.lower()
    inc = CFG["keywords_any"]
    exc = CFG["keywords_exclude"]
    if inc and not any(k.lower() in t for k in inc):
        return False
    if any(k.lower() in t for k in exc):
        return False
    return True


def location_ok(location, remote):
    loc = (location or "").lower()
    for bad in CFG["locations_exclude"]:
        if bad.lower() in loc:
            return False
    if remote and CFG.get("prefer_remote"):
        return True
    allow = CFG["countries_allow"]
    if not allow:
        return True
    if not loc:                       # unknown location -> keep, you decide
        return True
    return any(a.lower() in loc for a in allow)


def fresh_enough(posted_iso):
    if not posted_iso:
        return True
    try:
        dt = datetime.fromisoformat(posted_iso.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    except Exception:
        return True
    age = datetime.now(timezone.utc) - dt
    return age <= timedelta(days=CFG.get("max_age_days", 30))


def keep(job):
    blob = f"{job['title']} {job['description']} {job['tags']}"
    return (matches_keywords(blob)
            and location_ok(job["location"], job["remote"])
            and fresh_enough(job["posted"]))


# --------------------------------------------------------------------------- #
#  source fetchers  (each returns a list of unified dicts)
# --------------------------------------------------------------------------- #
def src_remoteok():
    data = get("https://remoteok.com/api").json()
    out = []
    for j in data:
        if not isinstance(j, dict) or "id" not in j:
            continue          # first element is metadata
        out.append(dict(
            source="remoteok", company=j.get("company", ""),
            title=j.get("position", ""), location=j.get("location", "Remote"),
            remote=True, url=j.get("url", ""), posted=j.get("date", ""),
            tags=",".join(j.get("tags", [])), description=strip_html(j.get("description", "")),
            status="new"))
    return out


def src_remotive():
    data = get("https://remotive.com/api/remote-jobs").json()
    out = []
    for j in data.get("jobs", []):
        out.append(dict(
            source="remotive", company=j.get("company_name", ""),
            title=j.get("title", ""), location=j.get("candidate_required_location", "Remote"),
            remote=True, url=j.get("url", ""), posted=j.get("publication_date", ""),
            tags=",".join(j.get("tags", [])), description=strip_html(j.get("description", "")),
            status="new"))
    return out


def src_arbeitnow():
    out = []
    url = "https://www.arbeitnow.com/api/job-board-api"
    for _ in range(3):                       # a few pages
        data = get(url).json()
        for j in data.get("data", []):
            out.append(dict(
                source="arbeitnow", company=j.get("company_name", ""),
                title=j.get("title", ""), location=j.get("location", ""),
                remote=bool(j.get("remote")), url=j.get("url", ""),
                posted="", tags=",".join(j.get("tags", []) or []),
                description=strip_html(j.get("description", "")), status="new"))
        url = data.get("links", {}).get("next")
        if not url:
            break
    return out


def src_jobicy():
    data = get("https://jobicy.com/api/v2/remote-jobs?count=100").json()
    out = []
    for j in data.get("jobs", []):
        out.append(dict(
            source="jobicy", company=j.get("companyName", ""),
            title=j.get("jobTitle", ""), location=j.get("jobGeo", "Remote"),
            remote=True, url=j.get("url", ""), posted=j.get("pubDate", ""),
            tags=",".join(j.get("jobIndustry", []) or []),
            description=strip_html(j.get("jobExcerpt", "")), status="new"))
    return out


def _companies(platform):
    f = ROOT / "companies.csv"
    if not f.exists():
        return []
    with f.open(encoding="utf-8") as fh:
        return [row for row in csv.DictReader(fh)
                if row["platform"].strip().lower() == platform]


def src_greenhouse():
    out = []
    for row in _companies("greenhouse"):
        tok = row["token"].strip()
        try:
            data = get(f"https://boards-api.greenhouse.io/v1/boards/{tok}/jobs?content=true").json()
        except Exception as e:
            print(f"  ! greenhouse/{tok}: {e}")
            continue
        for j in data.get("jobs", []):
            out.append(dict(
                source="greenhouse", company=row["company_name"],
                title=j.get("title", ""),
                location=(j.get("location") or {}).get("name", ""),
                remote="remote" in ((j.get("location") or {}).get("name", "")).lower(),
                url=j.get("absolute_url", ""), posted=j.get("updated_at", ""),
                tags="", description=strip_html(j.get("content", "")), status="new"))
        time.sleep(0.3)
    return out


def src_lever():
    out = []
    for row in _companies("lever"):
        tok = row["token"].strip()
        try:
            data = get(f"https://api.lever.co/v0/postings/{tok}?mode=json").json()
        except Exception as e:
            print(f"  ! lever/{tok}: {e}")
            continue
        for j in data:
            cat = j.get("categories", {}) or {}
            out.append(dict(
                source="lever", company=row["company_name"],
                title=j.get("text", ""), location=cat.get("location", ""),
                remote="remote" in (cat.get("location", "") or "").lower(),
                url=j.get("hostedUrl", ""),
                posted=datetime.fromtimestamp(j.get("createdAt", 0) / 1000, timezone.utc).isoformat()
                       if j.get("createdAt") else "",
                tags=cat.get("team", ""),
                description=strip_html(j.get("descriptionPlain", "")), status="new"))
        time.sleep(0.3)
    return out


def src_ashby():
    out = []
    for row in _companies("ashby"):
        tok = row["token"].strip()
        try:
            data = get(f"https://api.ashbyhq.com/posting-api/job-board/{tok}?includeCompensation=true").json()
        except Exception as e:
            print(f"  ! ashby/{tok}: {e}")
            continue
        for j in data.get("jobs", []):
            out.append(dict(
                source="ashby", company=row["company_name"],
                title=j.get("title", ""), location=j.get("location", ""),
                remote=bool(j.get("isRemote")), url=j.get("jobUrl", ""),
                posted=j.get("publishedAt", ""), tags=j.get("department", ""),
                description=strip_html(j.get("descriptionPlain", "")), status="new"))
        time.sleep(0.3)
    return out


def src_adzuna():
    cfg = CFG.get("adzuna", {})
    if not cfg.get("app_id") or not cfg.get("app_key"):
        print("  ! adzuna enabled but app_id/app_key missing in config.json -> skipped")
        return []
    out = []
    what = " ".join(CFG["keywords_any"][:1]) or "developer"
    for country in cfg.get("countries", ["us"]):
        try:
            url = (f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
                   f"?app_id={cfg['app_id']}&app_key={cfg['app_key']}"
                   f"&results_per_page=50&what={what}&content-type=application/json")
            data = get(url).json()
        except Exception as e:
            print(f"  ! adzuna/{country}: {e}")
            continue
        for j in data.get("results", []):
            out.append(dict(
                source=f"adzuna:{country}", company=(j.get("company") or {}).get("display_name", ""),
                title=j.get("title", ""), location=(j.get("location") or {}).get("display_name", ""),
                remote="remote" in (j.get("title", "") + j.get("description", "")).lower(),
                url=j.get("redirect_url", ""), posted=j.get("created", ""),
                tags=(j.get("category") or {}).get("label", ""),
                description=strip_html(j.get("description", "")), status="new"))
        time.sleep(0.3)
    return out


SOURCES = {
    "remoteok": src_remoteok, "remotive": src_remotive, "arbeitnow": src_arbeitnow,
    "jobicy": src_jobicy, "greenhouse": src_greenhouse, "lever": src_lever,
    "ashby": src_ashby, "adzuna": src_adzuna,
}


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def load_existing():
    f = ROOT / "jobs.csv"
    if not f.exists():
        return {}, []
    with f.open(encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    seen = {r["url"] or f"{r['company']}|{r['title']}": r for r in rows}
    return seen, rows


def main():
    print("Job scraper starting...\n")
    seen, existing = load_existing()
    existing_urls = set(seen.keys())
    new_rows, raw = [], 0

    for name, enabled in CFG["sources"].items():
        if not enabled:
            continue
        fn = SOURCES.get(name)
        if not fn:
            continue
        print(f"-> {name} ...", end=" ", flush=True)
        try:
            jobs = fn()[: CFG.get("max_per_source", 200)]
        except Exception as e:
            print(f"FAILED ({e})")
            continue
        raw += len(jobs)
        kept = 0
        for j in jobs:
            if not keep(j):
                continue
            key = j["url"] or f"{j['company']}|{j['title']}"
            if key in existing_urls:
                continue
            existing_urls.add(key)
            new_rows.append(j)
            kept += 1
        print(f"{len(jobs)} fetched, {kept} new matches")

    all_rows = existing + new_rows
    with (ROOT / "jobs.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(all_rows)

    print(f"\nDone. {raw} scanned -> {len(new_rows)} new jobs added "
          f"-> {len(all_rows)} total in jobs.csv")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
