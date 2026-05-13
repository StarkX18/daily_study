"""
Scrapers for: Greenhouse, Lever, RemoteOK, HN Who's Hiring, YC Work at a Startup.
Each returns (jobs: list[dict], error: str | None).
"""
import httpx
from datetime import datetime

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


def _get(url: str, timeout: int = 12) -> httpx.Response:
    return httpx.get(url, headers=HEADERS, timeout=timeout, follow_redirects=True)


# ---------------------------------------------------------------------------
# Greenhouse
# ---------------------------------------------------------------------------

def fetch_greenhouse(slug: str) -> tuple[list[dict], str | None]:
    url = f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
    try:
        r = _get(url)
        if r.status_code == 404:
            return [], f"Greenhouse board '{slug}' not found — check the slug"
        r.raise_for_status()
        jobs = []
        for j in r.json().get("jobs", []):
            loc = j.get("location", {})
            jobs.append({
                "external_id": str(j["id"]),
                "company":     slug,
                "title":       j["title"],
                "location":    loc.get("name", "") if isinstance(loc, dict) else "",
                "url":         j.get("absolute_url", ""),
                "source":      "greenhouse",
                "posted_at":   j.get("updated_at", ""),
                "description": "",
            })
        return jobs, None
    except Exception as e:
        return [], str(e)


def fetch_greenhouse_job_description(slug: str, job_id: str) -> str:
    """Fetch full description for a single Greenhouse job (on demand)."""
    try:
        r = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs/{job_id}")
        r.raise_for_status()
        data = r.json()
        content = data.get("content", "") or ""
        return _strip_html(content)[:3000]
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Lever
# ---------------------------------------------------------------------------

def fetch_lever(slug: str) -> tuple[list[dict], str | None]:
    url = f"https://api.lever.co/v0/postings/{slug}?mode=json"
    try:
        r = _get(url)
        if r.status_code == 404:
            return [], f"Lever board '{slug}' not found — check the slug"
        r.raise_for_status()
        jobs = []
        for j in r.json():
            ts = j.get("createdAt", 0)
            posted = datetime.fromtimestamp(ts / 1000).isoformat() if ts else ""
            jobs.append({
                "external_id": j["id"],
                "company":     slug,
                "title":       j.get("text", ""),
                "location":    (j.get("categories") or {}).get("location", ""),
                "url":         j.get("hostedUrl", ""),
                "source":      "lever",
                "posted_at":   posted,
                "description": (j.get("descriptionPlain") or "")[:600],
            })
        return jobs, None
    except Exception as e:
        return [], str(e)


# ---------------------------------------------------------------------------
# RemoteOK
# ---------------------------------------------------------------------------

def fetch_remoteok() -> tuple[list[dict], str | None]:
    try:
        r = _get("https://remoteok.com/api", timeout=15)
        r.raise_for_status()
        jobs = []
        for j in r.json():
            if not isinstance(j, dict) or not j.get("id"):
                continue
            jobs.append({
                "external_id": str(j["id"]),
                "company":     j.get("company", "Unknown"),
                "title":       j.get("position", ""),
                "location":    "Remote",
                "url":         j.get("url") or f"https://remoteok.com/jobs/{j['id']}",
                "source":      "remoteok",
                "posted_at":   j.get("date", ""),
                "description": _strip_html(j.get("description") or "")[:600],
            })
        return jobs, None
    except Exception as e:
        return [], str(e)


# ---------------------------------------------------------------------------
# HN Who's Hiring
# ---------------------------------------------------------------------------

def fetch_hn_hiring() -> tuple[list[dict], str | None]:
    try:
        r = _get(
            "https://hn.algolia.com/api/v1/search"
            "?query=Ask+HN%3A+Who+is+hiring%3F&tags=story&hitsPerPage=1"
        )
        hits = r.json().get("hits", [])
        if not hits:
            return [], "No HN hiring thread found"

        thread_id = hits[0]["objectID"]
        thread = _get(f"https://hn.algolia.com/api/v1/items/{thread_id}", timeout=20)
        data = thread.json()

        jobs = []
        for comment in (data.get("children") or []):
            text = comment.get("text") or ""
            if len(text) < 60:
                continue
            plain = _strip_html(text)
            first_line = plain.split("\n")[0][:200]
            jobs.append({
                "external_id": str(comment.get("id", "")),
                "company":     "HN",
                "title":       first_line.strip(),
                "location":    "",
                "url":         f"https://news.ycombinator.com/item?id={comment.get('id')}",
                "source":      "hn",
                "posted_at":   comment.get("created_at", ""),
                "description": plain[:600],
            })
        return jobs, None
    except Exception as e:
        return [], str(e)


# ---------------------------------------------------------------------------
# YC Work at a Startup
# ---------------------------------------------------------------------------

def fetch_yc() -> tuple[list[dict], str | None]:
    """
    Fetch YC Work at a Startup jobs via their search API.
    Tries the JSON search endpoint; falls back to the polyglot searcher.
    """
    jobs = []

    # Primary: WaaS job search endpoint
    try:
        r = httpx.post(
            "https://www.workatastartup.com/jobs/search",
            json={"role": "eng", "remote": "only", "order_by": "created_at", "limit": 200},
            headers={**HEADERS, "Accept": "application/json", "Content-Type": "application/json"},
            timeout=15,
        )
        if r.status_code == 200:
            data = r.json()
            raw = data if isinstance(data, list) else data.get("jobs", [])
            for j in raw:
                jobs.append(_waas_job(j))
            if jobs:
                return jobs, None
    except Exception:
        pass

    # Fallback: company polyglot searcher
    try:
        r = httpx.post(
            "https://www.workatastartup.com/company_polyglot_searcher",
            json={"query": "", "role": "eng", "remote": "yes", "limit": 150},
            headers=HEADERS,
            timeout=15,
        )
        r.raise_for_status()
        data = r.json()
        for company in data.get("startups", []):
            for j in company.get("jobs", []):
                jobs.append(_waas_job(j, company_name=company.get("name", "YC Startup")))
        if jobs:
            return jobs, None
    except Exception:
        pass

    return [], "YC WaaS returned no results — site may have changed its API"


def _waas_job(j: dict, company_name: str = "") -> dict:
    company = company_name or (j.get("company") or {}).get("name", "") or j.get("company_name", "YC Startup")
    remote  = j.get("remote_ok") or j.get("remote") or False
    loc     = "Remote" if remote else (j.get("location") or j.get("city") or "")
    return {
        "external_id": str(j.get("id", "")),
        "company":     company,
        "title":       j.get("title", "") or j.get("role", ""),
        "location":    loc,
        "url":         f"https://www.workatastartup.com/jobs/{j.get('id')}",
        "source":      "yc",
        "posted_at":   j.get("updated_at", "") or j.get("created_at", ""),
        "description": _strip_html(j.get("description") or "")[:600],
    }


# ---------------------------------------------------------------------------
# utils
# ---------------------------------------------------------------------------

def _strip_html(html: str) -> str:
    import re
    from html import unescape
    text = re.sub(r"<[^>]+>", " ", html)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()
