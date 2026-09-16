"""Legitimate, public internship sources. No LinkedIn, no HTML scraping.

Every fetcher returns a list of normalised lead dicts:
    {source, company, role, url, location, category, terms, date_posted}
Only postings whose title looks like an internship/co-op are returned.
"""
import json
import re
import urllib.error
import urllib.request
from datetime import date, datetime

USER_AGENT = "job-dash/0.1 (personal internship tracker; contact via GitHub)"
TIMEOUT = 40

# Word-boundary match so "Internal Audit" and "International" don't slip through.
INTERN_RE = re.compile(r"\b(intern|interns|internship|internships|co-?op|coop)\b", re.I)

# Community-maintained list (Simplify + open-source contributors). Public JSON in the repo.
SIMPLIFY_URLS = [
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2027-Internships/dev/.github/scripts/listings.json",
    "https://raw.githubusercontent.com/SimplifyJobs/Summer2026-Internships/dev/.github/scripts/listings.json",
]

# Public job-board APIs that companies expose on purpose to power their own careers pages.
PROVIDERS = {
    "greenhouse": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=false",
    "lever": "https://api.lever.co/v0/postings/{slug}?mode=json",
    "ashby": "https://api.ashbyhq.com/posting-api/job-board/{slug}",
}


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return json.load(resp)


def is_internship(title):
    return bool(INTERN_RE.search(title or ""))


def _iso_from_ts(ts):
    """Unix seconds or milliseconds -> ISO date, else None."""
    if not ts:
        return None
    try:
        ts = float(ts)
        if ts > 1e11:  # milliseconds
            ts /= 1000
        return date.fromtimestamp(ts).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def _iso_from_str(s):
    """'2026-09-07T01:44:20-04:00' -> '2026-09-07'."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        return str(s)[:10] if len(str(s)) >= 10 else None


def _lead(source, company, role, url, location="", category="", terms="", date_posted=None):
    return {
        "source": source,
        "company": (company or "").strip(),
        "role": (role or "").strip(),
        "url": (url or "").strip(),
        "location": (location or "").strip(),
        "category": (category or "").strip(),
        "terms": (terms or "").strip(),
        "date_posted": date_posted,
    }


# --------------------------------------------------------------------------

def fetch_simplify():
    last_err = None
    for url in SIMPLIFY_URLS:
        try:
            data = fetch_json(url)
            break
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
            last_err = e
    else:
        raise RuntimeError(f"Simplify feed unavailable: {last_err}")

    leads = []
    for row in data:
        if not row.get("active") or not row.get("is_visible", True):
            continue
        if not row.get("url") or not row.get("company_name") or not row.get("title"):
            continue
        leads.append(_lead(
            "simplify", row["company_name"], row["title"], row["url"],
            location="; ".join(row.get("locations") or []),
            category=row.get("category", ""),
            terms=", ".join(row.get("terms") or []),
            date_posted=_iso_from_ts(row.get("date_posted") or row.get("date_updated")),
        ))
    return leads


def fetch_greenhouse(slug, label=""):
    data = fetch_json(PROVIDERS["greenhouse"].format(slug=slug))
    leads = []
    for j in data.get("jobs", []):
        if not is_internship(j.get("title")):
            continue
        leads.append(_lead(
            "greenhouse", label or j.get("company_name") or slug, j["title"], j.get("absolute_url"),
            location=(j.get("location") or {}).get("name", ""),
            date_posted=_iso_from_str(j.get("first_published") or j.get("updated_at")),
        ))
    return leads


def fetch_lever(slug, label=""):
    data = fetch_json(PROVIDERS["lever"].format(slug=slug))
    leads = []
    for j in data:
        cats = j.get("categories") or {}
        title = j.get("text", "")
        if not (is_internship(title) or is_internship(cats.get("commitment", ""))):
            continue
        leads.append(_lead(
            "lever", label or slug, title, j.get("hostedUrl"),
            location="; ".join(cats.get("allLocations") or [cats.get("location", "")]),
            category=cats.get("team", ""),
            date_posted=_iso_from_ts(j.get("createdAt")),
        ))
    return leads


def fetch_ashby(slug, label=""):
    data = fetch_json(PROVIDERS["ashby"].format(slug=slug))
    leads = []
    for j in data.get("jobs", []):
        title = j.get("title", "")
        if not (is_internship(title) or j.get("employmentType") == "Intern"):
            continue
        if j.get("isListed") is False:
            continue
        locs = [j.get("location", "")] + [s.get("location", "") for s in j.get("secondaryLocations") or []]
        leads.append(_lead(
            "ashby", label or slug, title, j.get("jobUrl") or j.get("applyUrl"),
            location="; ".join(x for x in locs if x),
            category=j.get("department", ""),
            date_posted=_iso_from_str(j.get("publishedAt")),
        ))
    return leads


BOARD_FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
}


def check_board(provider, slug):
    """Returns (ok, message). Used when adding a board so typos fail fast."""
    fetcher = BOARD_FETCHERS.get(provider)
    if fetcher is None:
        return False, f"Unknown provider {provider!r}."
    try:
        leads = fetcher(slug)
    except urllib.error.HTTPError as e:
        return False, f"{provider} returned HTTP {e.code} for '{slug}'. Check the slug in the company's careers URL."
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        return False, f"Could not reach {provider} for '{slug}': {e}"
    return True, f"Board reachable, {len(leads)} internship posting(s) right now."
