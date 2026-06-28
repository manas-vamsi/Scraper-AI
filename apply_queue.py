#!/usr/bin/env python3
"""
Build a targeted apply queue from matches.csv for Manas (Hyderabad).

Rules:
  - Drop senior/staff/lead/principal/manager titles (early-career).
  - Keep only roles Manas can realistically win:
      * India-based (any), OR
      * remote (global / worldwide / anywhere / any remote flag).
    Non-India ON-SITE roles are dropped.
  - Prefer SMALL STARTUPS: big well-known companies are de-prioritized.
  - Diversify: at most 2 roles per company.

Run:  python apply_queue.py [N]   (default N=25)
"""
import csv
import sys
from pathlib import Path

ROOT = Path(__file__).parent
N = int(sys.argv[1]) if len(sys.argv) > 1 else 25

BAD_TITLE = ["senior", "sr.", "sr ", "staff", "principal", " lead", "lead ",
             "head ", "director", "vp ", "manager", "architect"]

# clearly non-engineering roles that slip in via company-wide board pulls
NON_TECH = ["account executive", "business development", "collections",
            "accounts receivable", "recruiter", "sales representative",
            "controller", "story teller", "storyteller", "account manager",
            "customer success", "marketing", "talent ", "people partner"]

INDIA = ["india", "hyderabad", "bangalore", "bengaluru", "mumbai", "delhi",
         "pune", "chennai", "gurgaon", "gurugram", "noida", "kolkata"]
GLOBAL_REMOTE = ["worldwide", "anywhere", "global", "remote - emea", "remote, emea"]

# big/established companies -> de-prioritise (we want small startups)
BIG = {"stripe", "databricks", "airbnb", "coinbase", "pinterest", "affirm",
       "netflix", "spotify", "atlassian", "cloudflare", "reddit", "lyft",
       "instacart", "dropbox", "nvidia", "gitlab", "elastic", "robinhood",
       "discord", "twitch", "samsara", "asana", "figma", "canva", "deel",
       "notion", "ramp", "brex", "scale ai", "doordash"}


def location_class(r):
    loc = r["location"].lower()
    remote = r["remote"] == "True"
    if any(k in loc for k in INDIA):
        return "india"
    if any(k in loc for k in GLOBAL_REMOTE):
        return "global-remote"
    if remote and not loc:                       # remote, location unspecified
        return "global-remote"
    if remote:                                   # remote but country-tagged (e.g. Remote US)
        return "remote-country-locked"
    return "onsite-foreign"                       # drop


def main():
    rows = list(csv.DictReader((ROOT / "matches.csv").open(encoding="utf-8")))
    picked, per_company = [], {}

    for r in rows:
        if any(b in r["title"].lower() for b in BAD_TITLE):
            continue
        if any(b in r["title"].lower() for b in NON_TECH):
            continue
        cls = location_class(r)
        if cls == "onsite-foreign":
            continue
        comp = r["company"].lower().strip()
        if per_company.get(comp, 0) >= 2:
            continue

        s = int(r["score"])
        if cls == "india": s += 8
        elif cls == "global-remote": s += 6
        elif cls == "remote-country-locked": s += 1   # keep but rank low
        if comp not in BIG: s += 5                     # startup preference
        else: s -= 4

        r2 = dict(r); r2["fit_score"] = s; r2["fit"] = cls
        picked.append(r2)
        per_company[comp] = per_company.get(comp, 0) + 1

    # Tier-aware ordering: roles Manas can realistically WIN lead the queue.
    # India + truly-global-remote are never truncated; US/Canada country-locked
    # roles are appended as a clearly-labeled stretch tier (filling up to N).
    TIER_RANK = {"india": 0, "global-remote": 1, "remote-country-locked": 2}
    realistic = sorted((r for r in picked if r["fit"] != "remote-country-locked"),
                       key=lambda x: (TIER_RANK[x["fit"]], -x["fit_score"]))
    locked = sorted((r for r in picked if r["fit"] == "remote-country-locked"),
                    key=lambda x: -x["fit_score"])
    picked = realistic + locked[:max(0, N - len(realistic))]

    fields = ["applied?", "fit", "fit_score", "title", "company", "location",
              "url", "matched_skills"]
    with (ROOT / "apply_queue.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in picked:
            r["applied?"] = "no"
            w.writerow(r)

    n_real = len(realistic)
    print(f"apply_queue.csv -> {len(picked)} roles "
          f"({n_real} realistic [India/global-remote] + "
          f"{len(picked) - n_real} country-locked stretch)\n")
    last_tier = None
    for i, r in enumerate(picked, 1):
        if r["fit"] == "remote-country-locked" and last_tier != "locked":
            print("  --- stretch: remote but country-locked (may filter non-locals) ---")
            last_tier = "locked"
        print(f"{i:>2}. [{r['fit_score']:>3}|{r['fit']:<20}] {r['title'][:40]:40} | "
              f"{r['company'][:18]:18} | {r['location'][:22]}")


if __name__ == "__main__":
    main()
