#!/usr/bin/env python3
"""
Y Combinator company seeder.

Pulls the full YC company directory from the maintained yc-oss public dataset
(no login / no key), filters to companies that are actively hiring, then tries
each company's slug as a Greenhouse / Lever / Ashby board token and VALIDATES
against the live API. Working boards are merged into companies.csv.

Validation runs concurrently (thread pool) so ~1500 companies finish in minutes.

Run:
    python yc_seed.py            # hiring companies only (default, ~1500)
    python yc_seed.py --all      # try every YC company (~6000, slower)
Then:
    python scrape.py
"""
import csv
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

import detect as D  # reuse validate() + load_existing()

ROOT = Path(__file__).parent
DATASET = "https://yc-oss.github.io/api/companies/all.json"
PLATFORMS = ("greenhouse", "ashby", "lever")  # try in this order
WORKERS = 16


def candidate_tokens(company):
    """Yield plausible board tokens for a YC company."""
    seen = set()
    for t in (company.get("slug"), (company.get("name") or "").lower().replace(" ", "")):
        t = (t or "").strip().lower()
        if t and t not in seen:
            seen.add(t)
            yield t


def probe(company):
    """Return (platform, token, name, jobs) for the first board that validates."""
    name = company.get("name", "")
    for tok in candidate_tokens(company):
        for plat in PLATFORMS:
            n = D.validate(plat, tok)
            if n > 0:
                return (plat, tok, name, n)
    return None


def main():
    hiring_only = "--all" not in sys.argv
    print(f"Downloading YC dataset...")
    companies = requests.get(DATASET, timeout=120).json()
    if hiring_only:
        companies = [c for c in companies if c.get("isHiring")]
    print(f"Probing {len(companies)} YC companies "
          f"({'hiring only' if hiring_only else 'ALL'}) across {PLATFORMS}...\n")

    rows, have = D.load_existing()
    found, total_jobs = 0, 0

    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        futures = {ex.submit(probe, c): c for c in companies}
        done = 0
        for fut in as_completed(futures):
            done += 1
            if done % 200 == 0:
                print(f"  ...{done}/{len(companies)} probed, {found} boards found")
            res = fut.result()
            if not res:
                continue
            plat, tok, name, n = res
            key = (plat.lower(), tok.lower())
            if key in have:
                continue
            have.add(key)
            rows.append({"platform": plat, "token": tok, "company_name": name})
            found += 1
            total_jobs += n
            print(f"  + {plat:10} {tok:24} {name:28} {n:>4} jobs")

    with (ROOT / "companies.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["platform", "token", "company_name"])
        w.writeheader()
        w.writerows(rows)

    print(f"\nDone. {found} new YC boards added (~{total_jobs} jobs). "
          f"companies.csv now has {len(rows)} companies.")


if __name__ == "__main__":
    main()
