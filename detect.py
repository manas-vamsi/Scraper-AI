#!/usr/bin/env python3
"""
ATS auto-detector + company-list seeder.

What it does:
  1. Takes candidate companies from:
       - the built-in SEED list below, and
       - new_companies.txt (one careers-page URL per line, if the file exists)
  2. For each URL, figures out the ATS platform + board token
     (by URL pattern, or by fetching the page and sniffing embed scripts).
  3. VALIDATES every (platform, token) against the live public API --
     only entries that actually return jobs are kept.
  4. Merges the working ones into companies.csv (de-duped).

Run:
    python detect.py
Then:
    python scrape.py
"""
import csv
import re
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0 (job-scraper; personal use)"}
TIMEOUT = 20

# --------------------------------------------------------------------------- #
#  Seed list -- known companies on Greenhouse / Lever / Ashby hiring in
#  US / Europe / India / Japan / Australia / NZ. Bad/renamed tokens are
#  pruned automatically by validation, so over-inclusion is safe.
# --------------------------------------------------------------------------- #
SEED = [
    # platform, token, display name
    ("greenhouse", "anthropic", "Anthropic"),
    ("greenhouse", "stripe", "Stripe"),
    ("greenhouse", "databricks", "Databricks"),
    ("greenhouse", "airbnb", "Airbnb"),
    ("greenhouse", "coinbase", "Coinbase"),
    ("greenhouse", "gitlab", "GitLab"),
    ("greenhouse", "robinhood", "Robinhood"),
    ("greenhouse", "doordash", "DoorDash"),
    ("greenhouse", "instacart", "Instacart"),
    ("greenhouse", "dropbox", "Dropbox"),
    ("greenhouse", "brex", "Brex"),
    ("greenhouse", "figma", "Figma"),
    ("greenhouse", "retool", "Retool"),
    ("greenhouse", "discord", "Discord"),
    ("greenhouse", "lyft", "Lyft"),
    ("greenhouse", "pinterest", "Pinterest"),
    ("greenhouse", "asana", "Asana"),
    ("greenhouse", "benchling", "Benchling"),
    ("greenhouse", "samsara", "Samsara"),
    ("greenhouse", "affirm", "Affirm"),
    ("greenhouse", "cloudflare", "Cloudflare"),
    ("greenhouse", "hashicorp", "HashiCorp"),
    ("greenhouse", "twitch", "Twitch"),
    ("greenhouse", "reddit", "Reddit"),
    ("greenhouse", "elastic", "Elastic"),
    ("greenhouse", "gusto", "Gusto"),
    ("greenhouse", "udemy", "Udemy"),
    ("greenhouse", "thumbtack", "Thumbtack"),
    ("greenhouse", "airtable", "Airtable"),
    ("greenhouse", "scaleai", "Scale AI"),
    ("greenhouse", "wise", "Wise"),
    ("greenhouse", "monzo", "Monzo"),
    ("greenhouse", "gocardless", "GoCardless"),
    ("greenhouse", "deliveroo", "Deliveroo"),
    ("greenhouse", "babbel", "Babbel"),
    ("greenhouse", "razorpay", "Razorpay"),
    ("greenhouse", "postman", "Postman"),
    ("greenhouse", "freshworks", "Freshworks"),
    ("greenhouse", "canva", "Canva"),
    ("greenhouse", "atlassian", "Atlassian"),
    ("greenhouse", "rippling", "Rippling"),
    # Lever
    ("lever", "netflix", "Netflix"),
    ("lever", "spotify", "Spotify"),
    ("lever", "plaid", "Plaid"),
    ("lever", "ramp", "Ramp"),
    ("lever", "kraken", "Kraken"),
    ("lever", "leantaas", "LeanTaaS"),
    ("lever", "voleon", "Voleon"),
    ("lever", "matterport", "Matterport"),
    ("lever", "attentive", "Attentive"),
    ("lever", "fanatics", "Fanatics"),
    ("lever", "swordhealth", "Sword Health"),
    ("lever", "yougov", "YouGov"),
    # Ashby
    ("ashby", "ramp", "Ramp"),
    ("ashby", "linear", "Linear"),
    ("ashby", "vanta", "Vanta"),
    ("ashby", "posthog", "PostHog"),
    ("ashby", "replit", "Replit"),
    ("ashby", "mercury", "Mercury"),
    ("ashby", "runway", "Runway"),
    ("ashby", "deel", "Deel"),
    ("ashby", "notion", "Notion"),
    ("ashby", "browserbase", "Browserbase"),
    ("ashby", "openstore", "OpenStore"),
    ("ashby", "clipboardhealth", "Clipboard Health"),
    ("ashby", "hex", "Hex"),
    ("ashby", "modal", "Modal"),
    ("ashby", "elevenlabs", "ElevenLabs"),

    # ---- Indian startups (token guesses; validator prunes bad ones) ----
    ("greenhouse", "razorpaysoftwareprivatelimited", "Razorpay"),
    ("greenhouse", "cred", "CRED"),
    ("greenhouse", "meesho", "Meesho"),
    ("greenhouse", "groww", "Groww"),
    ("greenhouse", "sprinklr", "Sprinklr"),
    ("greenhouse", "innovaccer", "Innovaccer"),
    ("greenhouse", "whatfix", "Whatfix"),
    ("greenhouse", "browserstack", "BrowserStack"),
    ("greenhouse", "chargebee", "Chargebee"),
    ("greenhouse", "druva", "Druva"),
    ("greenhouse", "clevertap", "CleverTap"),
    ("greenhouse", "moengage", "MoEngage"),
    ("greenhouse", "mindtickle", "Mindtickle"),
    ("greenhouse", "hasura", "Hasura"),
    ("greenhouse", "zeta", "Zeta"),
    ("greenhouse", "eightfoldai", "Eightfold AI"),
    ("greenhouse", "fractalanalytics", "Fractal"),
    ("greenhouse", "gupshup", "Gupshup"),
    ("lever", "razorpay", "Razorpay"),
    ("lever", "dream11", "Dream11"),
    ("lever", "sharechat", "ShareChat"),
    ("lever", "phonepe", "PhonePe"),
    ("lever", "swiggy", "Swiggy"),
    ("ashby", "atlan", "Atlan"),
    ("ashby", "hasura", "Hasura"),

    # ---- Global remote-first companies ----
    ("greenhouse", "zapier", "Zapier"),
    ("greenhouse", "webflow", "Webflow"),
    ("greenhouse", "sentry", "Sentry"),
    ("greenhouse", "vercel", "Vercel"),
    ("greenhouse", "mozilla", "Mozilla"),
    ("greenhouse", "grafanalabs", "Grafana Labs"),
    ("greenhouse", "andela", "Andela"),
    ("greenhouse", "remotecom", "Remote.com"),
    ("greenhouse", "turing", "Turing"),
    ("greenhouse", "close", "Close"),
    ("greenhouse", "huggingface", "Hugging Face"),
    ("greenhouse", "twilio", "Twilio"),
    ("greenhouse", "doist", "Doist"),
    ("lever", "automattic", "Automattic"),
    ("lever", "toptal", "Toptal"),
    ("lever", "hopper", "Hopper"),
    ("ashby", "supabase", "Supabase"),
    ("ashby", "mercury", "Mercury"),
    ("ashby", "tldraw", "tldraw"),
    ("ashby", "cal", "Cal.com"),
    ("ashby", "resend", "Resend"),
    ("ashby", "trigger", "Trigger.dev"),

    # ---- Japan-HQ companies ----
    ("greenhouse", "mercari", "Mercari"),
    ("greenhouse", "rakuten", "Rakuten"),
    ("greenhouse", "smartnews", "SmartNews"),
    ("greenhouse", "wovenplanet", "Woven (Toyota)"),
    ("greenhouse", "woven", "Woven by Toyota"),
    ("lever", "paidy", "Paidy"),
    ("ashby", "tailor", "Tailor (Tokyo)"),
    ("greenhouse", "moneyforward", "Money Forward"),
    ("lever", "autify", "Autify"),
    ("greenhouse", "preferrednetworks", "Preferred Networks"),

    # ---- Australia / NZ companies ----
    ("greenhouse", "safetyculture", "SafetyCulture"),
    ("lever", "safetyculture", "SafetyCulture"),
    ("greenhouse", "airwallex", "Airwallex"),
    ("lever", "airwallex", "Airwallex"),
    ("greenhouse", "cultureamp", "Culture Amp"),
    ("lever", "cultureamp", "Culture Amp"),
    ("greenhouse", "linktree", "Linktree"),
    ("lever", "employmenthero", "Employment Hero"),
    ("greenhouse", "immutable", "Immutable"),
    ("lever", "go1", "Go1"),
    ("greenhouse", "rokt", "Rokt"),
    ("lever", "octopusdeploy", "Octopus Deploy"),

    # ---- Europe (deepen) ----
    ("greenhouse", "n26", "N26"),
    ("greenhouse", "adyen", "Adyen"),
    ("lever", "klarna", "Klarna"),
    ("greenhouse", "deepl", "DeepL"),
    ("lever", "mistralai", "Mistral AI"),
    ("greenhouse", "personio", "Personio"),
    ("greenhouse", "celonis", "Celonis"),
    ("lever", "qonto", "Qonto"),
    ("greenhouse", "pleo", "Pleo"),
    ("greenhouse", "traderepublic", "Trade Republic"),
    ("greenhouse", "glovo", "Glovo"),
    ("greenhouse", "contentful", "Contentful"),
    ("greenhouse", "doctolib", "Doctolib"),
    ("lever", "bolt", "Bolt"),

    # ---- Quantum computing companies ----
    ("greenhouse", "ionq", "IonQ"),
    ("greenhouse", "psiquantum", "PsiQuantum"),
    ("lever", "q-ctrl", "Q-CTRL"),
    ("greenhouse", "quantinuum", "Quantinuum"),
    ("greenhouse", "rigetticomputing", "Rigetti"),
    ("lever", "xanadu", "Xanadu"),
    ("greenhouse", "quera", "QuEra"),
    ("greenhouse", "queracomputing", "QuEra"),
    ("greenhouse", "classiq", "Classiq"),
    ("lever", "classiq", "Classiq"),
    ("greenhouse", "sandboxaq", "SandboxAQ"),
    ("greenhouse", "quantummachines", "Quantum Machines"),
    ("greenhouse", "infleqtion", "Infleqtion"),
    ("lever", "multiversecomputing", "Multiverse Computing"),
    ("lever", "pasqal", "Pasqal"),
    ("greenhouse", "atomcomputing", "Atom Computing"),
    ("greenhouse", "qpiai", "QpiAI"),
]


# --------------------------------------------------------------------------- #
#  detection from a URL
# --------------------------------------------------------------------------- #
def detect_from_url(url):
    """Return (platform, token) or None from a careers URL pattern."""
    u = url.strip().rstrip("/")
    m = re.search(r"greenhouse\.io/(?:embed/job_board\?for=)?([A-Za-z0-9_-]+)", u)
    if "greenhouse.io" in u and m:
        tok = re.search(r"for=([A-Za-z0-9_-]+)", u)
        return ("greenhouse", (tok.group(1) if tok else m.group(1)))
    m = re.search(r"jobs\.lever\.co/([A-Za-z0-9_-]+)", u)
    if m:
        return ("lever", m.group(1))
    m = re.search(r"(?:jobs\.ashbyhq\.com|posting-api/job-board)/([A-Za-z0-9_-]+)", u)
    if m:
        return ("ashby", m.group(1))
    return None


def detect_from_html(url):
    """Fetch a generic careers page and sniff for an embedded ATS."""
    try:
        html = requests.get(url, headers=UA, timeout=TIMEOUT).text
    except Exception:
        return None
    for pat, plat in [
        (r"greenhouse\.io/embed/job_board\?for=([A-Za-z0-9_-]+)", "greenhouse"),
        (r"boards\.greenhouse\.io/([A-Za-z0-9_-]+)", "greenhouse"),
        (r"jobs\.lever\.co/([A-Za-z0-9_-]+)", "lever"),
        (r"jobs\.ashbyhq\.com/([A-Za-z0-9_-]+)", "ashby"),
        (r"api\.ashbyhq\.com/posting-api/job-board/([A-Za-z0-9_-]+)", "ashby"),
    ]:
        m = re.search(pat, html)
        if m:
            return (plat, m.group(1))
    return None


# --------------------------------------------------------------------------- #
#  validation against the live API -> returns job count (0 = dead)
# --------------------------------------------------------------------------- #
def validate(platform, token):
    try:
        if platform == "greenhouse":
            r = requests.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs",
                             headers=UA, timeout=TIMEOUT)
            return len(r.json().get("jobs", [])) if r.ok else 0
        if platform == "lever":
            r = requests.get(f"https://api.lever.co/v0/postings/{token}?mode=json",
                             headers=UA, timeout=TIMEOUT)
            return len(r.json()) if r.ok and isinstance(r.json(), list) else 0
        if platform == "ashby":
            r = requests.get(f"https://api.ashbyhq.com/posting-api/job-board/{token}",
                             headers=UA, timeout=TIMEOUT)
            return len(r.json().get("jobs", [])) if r.ok else 0
    except Exception:
        return 0
    return 0


# --------------------------------------------------------------------------- #
#  main
# --------------------------------------------------------------------------- #
def load_existing():
    f = ROOT / "companies.csv"
    rows = []
    if f.exists():
        with f.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
    have = {(r["platform"].strip().lower(), r["token"].strip().lower()) for r in rows}
    return rows, have


def main():
    rows, have = load_existing()

    # gather candidates: seed list + any URLs in new_companies.txt
    candidates = list(SEED)
    urls_file = ROOT / "new_companies.txt"
    url_candidates = []
    if urls_file.exists():
        for line in urls_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            det = detect_from_url(line) or detect_from_html(line)
            if det:
                url_candidates.append((det[0], det[1], det[1]))
                print(f"detected {line} -> {det[0]}/{det[1]}")
            else:
                print(f"  ? could not detect ATS for {line}")
    candidates += url_candidates

    print(f"\nValidating {len(candidates)} candidates against live APIs...\n")
    added, dead, total_jobs = 0, 0, 0
    for plat, tok, name in candidates:
        key = (plat.lower(), tok.lower())
        if key in have:
            continue
        n = validate(plat, tok)
        time.sleep(0.25)
        if n > 0:
            rows.append({"platform": plat, "token": tok, "company_name": name})
            have.add(key)
            added += 1
            total_jobs += n
            print(f"  + {plat:10} {tok:22} {name:22} {n:>4} jobs")
        else:
            dead += 1
            print(f"  - {plat:10} {tok:22} {name:22}  (no jobs / bad token)")

    with (ROOT / "companies.csv").open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["platform", "token", "company_name"])
        w.writeheader()
        w.writerows(rows)

    print(f"\nDone. {added} companies added ({dead} pruned). "
          f"~{total_jobs} jobs reachable. companies.csv now has {len(rows)} companies.")


if __name__ == "__main__":
    main()
