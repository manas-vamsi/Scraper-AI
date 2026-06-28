#!/usr/bin/env python3
"""
Rank scraped jobs against Manas's resume profile.

Scores every job in jobs.csv by weighted skill overlap (title hits count
more than description hits), applies a seniority fit penalty (early-career),
and writes a ranked matches.csv + prints the top matches.

Run:
    python match.py
"""
import csv
import re
from pathlib import Path

ROOT = Path(__file__).parent

# skill -> weight. Higher = more core to the profile.
SKILLS = {
    # core software
    "python": 5, "fastapi": 4, "sql": 2, "postgres": 2, "postgresql": 2,
    "elixir": 4, "phoenix": 4, "liveview": 3,
    "react": 4, "typescript": 4, "javascript": 3, "next.js": 3, "nextjs": 3,
    "full stack": 4, "full-stack": 4, "fullstack": 4, "backend": 4, "frontend": 2,
    "api": 1, "rest": 1,
    # AI / ML
    "machine learning": 5, "deep learning": 4, "nlp": 4, "ml ": 3,
    "llm": 5, "rag": 4, "langgraph": 4, "langchain": 3, "ollama": 3,
    "mcp": 3, "agent": 3, "ai engineer": 5, "ai ": 2, "data scien": 4,
    "data analy": 3, "data engineer": 3, "analytics": 2, "dashboard": 2,
    "pytorch": 3, "tensorflow": 3,
    # quantum
    "quantum": 6, "qiskit": 5, "pennylane": 5, "cirq": 5, "superconduct": 5,
    "qubit": 5,
}

# title signals that fit an early-career engineer (1-2 yrs)
GOOD_LEVEL = ["new grad", "graduate", "junior", "associate", "entry", "early career",
              "i ", " i,", "intern", "fellow", "apprentice", "trainee"]
BAD_LEVEL = ["senior", "sr.", "staff", "principal", "lead", "head ", "director",
             "vp ", "manager", "architect", "10+ years", "8+ years", "7+ years"]


def score(job):
    title = job["title"].lower()
    blob = f"{title} {job['description'].lower()} {job['tags'].lower()}"
    matched, s = [], 0
    for kw, w in SKILLS.items():
        if kw in blob:
            hit = w + (w if kw in title else 0)   # double-weight title hits
            s += hit
            matched.append(kw.strip())
    # seniority fit
    if any(b in title for b in BAD_LEVEL):
        s -= 8
    if any(g in title for g in GOOD_LEVEL):
        s += 4
    # remote bonus
    if job["remote"] == "True":
        s += 2
    return s, sorted(set(matched), key=len, reverse=True)


def main():
    rows = list(csv.DictReader((ROOT / "jobs.csv").open(encoding="utf-8")))
    scored = []
    for j in rows:
        s, matched = score(j)
        j2 = dict(j)
        j2["score"] = s
        j2["matched_skills"] = ", ".join(matched[:8])
        scored.append(j2)
    scored.sort(key=lambda x: x["score"], reverse=True)

    fields = ["score", "matched_skills", "title", "company", "location",
              "remote", "source", "url", "posted"]
    with (ROOT / "matches.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(scored)

    print(f"Ranked {len(scored)} jobs -> matches.csv\n")
    print(f"{'SCORE':>5}  {'TITLE':42}  {'COMPANY':20}  MATCHED")
    print("-" * 110)
    for j in scored[:25]:
        print(f"{j['score']:>5}  {j['title'][:42]:42}  {j['company'][:20]:20}  {j['matched_skills'][:40]}")


if __name__ == "__main__":
    main()
