"""
Job Application MCP Server
Scrapes Greenhouse / Lever / RemoteOK / HN / YC.
Tracks applications, stores resume, scores fit, drafts cover letters.
"""
from mcp.server.fastmcp import FastMCP
import db
import scrapers

mcp = FastMCP("job-tracker")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _fmt_job(j) -> str:
    loc = f" | {j['location']}" if j['location'] else ""
    src = j['source'].upper()
    return f"[#{j['id']}] **{j['title']}** @ {j['company']}{loc} ({src})\n   {j['url']}"


def _fmt_app(a) -> str:
    status_icon = {
        "saved": "📌", "applied": "📤", "screen": "📞",
        "onsite": "🏢", "offer": "🎉", "rejected": "❌",
        "ghosted": "👻", "withdrawn": "↩️",
    }.get(a["status"], "•")
    score = f" | fit: {a['fit_score']}/100" if a["fit_score"] else ""
    return f"{status_icon} [#{a['id']}] **{a['role']}** @ {a['company']} — {a['status'].upper()}{score}"


# ---------------------------------------------------------------------------
# 1. add_company
# ---------------------------------------------------------------------------

@mcp.tool()
def add_company(
    name: str,
    ats: str,
    board_slug: str,
    priority: int = 2,
    roles: str = "",
    locations: str = "",
    notes: str = "",
) -> str:
    """
    Add or update a company in your job watchlist.

    Args:
        name: Company name (e.g. "Stripe")
        ats: ATS platform — "greenhouse" | "lever" | "ashby" | "custom"
        board_slug: URL slug for the ATS board (e.g. "stripe" for boards-api.greenhouse.io/v1/boards/stripe/jobs)
        priority: 1=top, 2=target, 3=explore
        roles: Comma-separated role keywords (e.g. "backend,platform,infra")
        locations: Comma-separated location prefs (e.g. "remote,SF,NYC")
        notes: Any notes about why you want to work here
    """
    ats = ats.lower()
    if ats not in db.VALID_ATS:
        return f"Invalid ATS '{ats}'. Use: {', '.join(db.VALID_ATS)}"
    if priority not in db.VALID_PRIORITY:
        return f"Priority must be 1, 2, or 3."
    cid = db.upsert_company(name, ats, board_slug, priority, roles, locations, notes)
    return (
        f"✅ **{name}** added (priority {priority})\n"
        f"ATS: {ats} | Slug: `{board_slug}`\n"
        f"Roles: {roles or 'any'} | Locations: {locations or 'any'}"
    )


# ---------------------------------------------------------------------------
# 2. list_companies
# ---------------------------------------------------------------------------

@mcp.tool()
def list_companies(priority: int = 0) -> str:
    """
    List companies in your watchlist.

    Args:
        priority: Filter by 1/2/3 (0 = all)
    """
    rows = db.get_companies(priority)
    if not rows:
        return "No companies in watchlist. Add with add_company."
    lines = [f"## Watchlist ({len(rows)} companies)\n"]
    for p in (1, 2, 3):
        group = [r for r in rows if r["priority"] == p]
        if not group:
            continue
        label = {1: "Top Priority", 2: "Target", 3: "Explore"}[p]
        lines.append(f"### {label}")
        for c in group:
            board = f"{c['ats']}:{c['board_slug']}" if c["board_slug"] else "no ATS configured"
            lines.append(f"- **{c['name']}** ({board}) | {c['roles'] or 'any role'} | {c['locations'] or 'any location'}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 3. remove_company
# ---------------------------------------------------------------------------

@mcp.tool()
def remove_company(name: str) -> str:
    """
    Remove (deactivate) a company from your watchlist.

    Args:
        name: Company name (partial match OK)
    """
    db.deactivate_company(name)
    return f"Removed '{name}' from active watchlist."


# ---------------------------------------------------------------------------
# 4. fetch_jobs
# ---------------------------------------------------------------------------

@mcp.tool()
def fetch_jobs(
    include_remoteok: bool = True,
    include_hn: bool = True,
    include_yc: bool = True,
    priority_filter: int = 0,
) -> str:
    """
    Scrape all configured company boards + selected free firehoses.
    New jobs are stored; already-seen jobs are deduplicated.

    Args:
        include_remoteok: Include RemoteOK global feed
        include_hn: Include HN Who's Hiring thread
        include_yc: Include YC Work at a Startup
        priority_filter: Only scrape companies with this priority (0 = all)
    """
    results = []
    total_new = 0

    # Company-specific boards
    companies = db.get_companies(priority_filter)
    for c in companies:
        if not c["board_slug"]:
            continue
        slug = c["board_slug"]
        ats  = c["ats"]

        if ats == "greenhouse":
            jobs, err = scrapers.fetch_greenhouse(slug)
        elif ats == "lever":
            jobs, err = scrapers.fetch_lever(slug)
        else:
            continue

        if err:
            results.append(f"⚠️  {c['name']}: {err}")
            continue

        new = 0
        for j in jobs:
            _, is_new = db.upsert_job(
                j["external_id"], j["company"], j["title"],
                j["location"], j["url"], j["source"],
                j["description"], j["posted_at"],
            )
            if is_new:
                new += 1
        total_new += new
        results.append(f"✅ {c['name']} ({ats}): {len(jobs)} total, {new} new")

    # Free firehoses
    if include_remoteok:
        jobs, err = scrapers.fetch_remoteok()
        if err:
            results.append(f"⚠️  RemoteOK: {err}")
        else:
            new = sum(1 for j in jobs if db.upsert_job(
                j["external_id"], j["company"], j["title"],
                j["location"], j["url"], j["source"],
                j["description"], j["posted_at"],
            )[1])
            total_new += new
            results.append(f"✅ RemoteOK: {len(jobs)} total, {new} new")

    if include_hn:
        jobs, err = scrapers.fetch_hn_hiring()
        if err:
            results.append(f"⚠️  HN Who's Hiring: {err}")
        else:
            new = sum(1 for j in jobs if db.upsert_job(
                j["external_id"], j["company"], j["title"],
                j["location"], j["url"], j["source"],
                j["description"], j["posted_at"],
            )[1])
            total_new += new
            results.append(f"✅ HN Who's Hiring: {len(jobs)} total, {new} new")

    if include_yc:
        jobs, err = scrapers.fetch_yc()
        if err:
            results.append(f"⚠️  YC WaaS: {err}")
        else:
            new = sum(1 for j in jobs if db.upsert_job(
                j["external_id"], j["company"], j["title"],
                j["location"], j["url"], j["source"],
                j["description"], j["posted_at"],
            )[1])
            total_new += new
            results.append(f"✅ YC Work at a Startup: {len(jobs)} total, {new} new")

    return (
        f"## Fetch complete — **{total_new} new jobs** added\n\n"
        + "\n".join(results)
        + f"\n\nRun get_new_jobs to browse them."
    )


# ---------------------------------------------------------------------------
# 5. get_new_jobs
# ---------------------------------------------------------------------------

@mcp.tool()
def get_new_jobs(
    limit: int = 20,
    company: str = "",
    keyword: str = "",
) -> str:
    """
    Show unseen jobs. Optionally filter by company or keyword.

    Args:
        limit: Max results
        company: Filter by company name
        keyword: Filter by keyword in title/description
    """
    rows = db.get_new_jobs(limit, company, keyword)
    if not rows:
        return "No new unseen jobs. Run fetch_jobs to scrape fresh listings."
    lines = [f"## New Jobs ({len(rows)} unseen)\n"]
    for j in rows:
        lines.append(_fmt_job(j))
    lines.append(f"\nCall mark_seen([id, id, ...]) after reviewing.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 6. mark_seen
# ---------------------------------------------------------------------------

@mcp.tool()
def mark_seen(job_ids: list[int]) -> str:
    """
    Mark jobs as seen so they don't show up in get_new_jobs tomorrow.

    Args:
        job_ids: List of job IDs to mark seen (e.g. [12, 15, 22])
    """
    db.mark_jobs_seen(job_ids)
    return f"Marked {len(job_ids)} job(s) as seen."


# ---------------------------------------------------------------------------
# 7. search_jobs
# ---------------------------------------------------------------------------

@mcp.tool()
def search_jobs(
    query: str = "",
    company: str = "",
    location: str = "",
    source: str = "",
) -> str:
    """
    Search all scraped jobs in the local database.

    Args:
        query: Keyword search across title, description, company
        company: Filter by company name
        location: Filter by location
        source: Filter by source (greenhouse / lever / remoteok / hn / yc)
    """
    rows = db.search_jobs(query, company, location, source)
    if not rows:
        return f"No jobs found. Try broader terms or run fetch_jobs first."
    lines = [f"## Search Results ({len(rows)})\n"]
    for j in rows:
        lines.append(_fmt_job(j))
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 8. track_application
# ---------------------------------------------------------------------------

@mcp.tool()
def track_application(
    company: str,
    role: str,
    job_url: str = "",
    notes: str = "",
) -> str:
    """
    Add a new application to your pipeline (status starts as 'saved').

    Args:
        company: Company name
        role: Job title
        job_url: Link to the posting
        notes: Any notes (referral, recruiter name, etc.)
    """
    aid = db.add_application(company, role, job_url, notes)
    return (
        f"📌 Tracked: **{role}** @ {company} [#{aid}]\n"
        f"Status: SAVED\n"
        f"Update with: update_application({aid}, status='applied')"
    )


# ---------------------------------------------------------------------------
# 9. update_application
# ---------------------------------------------------------------------------

@mcp.tool()
def update_application(
    app_id: int,
    status: str = "",
    notes: str = "",
) -> str:
    """
    Update an application's status or notes.

    Args:
        app_id: Application ID from track_application or get_pipeline
        status: New status — saved | applied | screen | onsite | offer | rejected | ghosted | withdrawn
        notes: Append notes (e.g. "Recruiter called, moving to onsite")
    """
    if status and status not in db.VALID_STATUSES:
        return f"Invalid status '{status}'. Use: {', '.join(db.VALID_STATUSES)}"
    db.update_application(app_id, status=status, notes=notes)
    return f"Updated application #{app_id}" + (f" → **{status.upper()}**" if status else "")


# ---------------------------------------------------------------------------
# 10. get_pipeline
# ---------------------------------------------------------------------------

@mcp.tool()
def get_pipeline() -> str:
    """
    View your full application pipeline with funnel stats.
    """
    apps   = db.get_pipeline()
    stats  = db.get_pipeline_stats()
    if not apps:
        return "No applications tracked yet. Use track_application to add one."

    lines = ["## Application Pipeline\n"]

    funnel = ["saved", "applied", "screen", "onsite", "offer", "rejected", "ghosted", "withdrawn"]
    stat_line = " → ".join(f"{s.upper()}:{stats.get(s, 0)}" for s in funnel if stats.get(s, 0) > 0)
    lines.append(f"**Funnel:** {stat_line}\n")

    for status in funnel:
        group = [a for a in apps if a["status"] == status]
        if not group:
            continue
        lines.append(f"### {status.upper()}")
        for a in group:
            lines.append(f"- {_fmt_app(a)}")
            if a["notes"]:
                lines.append(f"  > {a['notes'][:100]}")
        lines.append("")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 11. set_resume
# ---------------------------------------------------------------------------

@mcp.tool()
def set_resume(resume_text: str) -> str:
    """
    Store your resume text in the DB. Used automatically by score_job_fit and draft_cover_letter.
    Call this once — update it whenever your resume changes.

    Args:
        resume_text: Your full resume as plain text (paste it in)
    """
    db.set_profile("resume", resume_text)
    word_count = len(resume_text.split())
    return f"Resume saved ({word_count} words). Used automatically by score_job_fit and draft_cover_letter."


# ---------------------------------------------------------------------------
# 12. score_job_fit
# ---------------------------------------------------------------------------

@mcp.tool()
def score_job_fit(job_id: int) -> str:
    """
    Prepare a job + resume context for Claude to score your fit.
    Claude will read this output and return a score + reasoning.

    Args:
        job_id: Job ID from get_new_jobs or search_jobs
    """
    job    = db.get_job(job_id)
    resume = db.get_profile("resume")

    if not job:
        return f"Job #{job_id} not found."
    if not resume:
        return "No resume stored. Call set_resume first."

    # Fetch full description on-demand for Greenhouse jobs that were scraped without content
    description = job["description"]
    if not description and job["source"] == "greenhouse":
        description = scrapers.fetch_greenhouse_job_description(job["company"], job["external_id"])
        if description:
            db.update_job_description(job_id, description)

    return (
        f"## Fit Analysis — Job #{job_id}\n\n"
        f"**Role:** {job['title']} @ {job['company']}\n"
        f"**Source:** {job['source'].upper()} | **Location:** {job['location'] or 'N/A'}\n"
        f"**URL:** {job['url']}\n\n"
        f"### Job Description\n"
        f"{description or '(No description scraped — visit the URL above for full JD)'}\n\n"
        f"### Resume\n{resume}\n\n---\n\n"
        f"**Analyze the fit above and return:**\n"
        f"1. Fit score (0–100)\n"
        f"2. Top 3–5 matching strengths\n"
        f"3. Key gaps or missing keywords\n"
        f"4. Apply? yes / maybe / no — with one-sentence reason\n"
        f"5. If yes/maybe: what to emphasize in the application"
    )


# ---------------------------------------------------------------------------
# 13. draft_cover_letter
# ---------------------------------------------------------------------------

@mcp.tool()
def draft_cover_letter(job_id: int, extra_context: str = "") -> str:
    """
    Prepare a job + resume context for Claude to draft a tailored cover letter.

    Args:
        job_id: Job ID from get_new_jobs or search_jobs
        extra_context: Anything extra to weave in (referral name, why this company, etc.)
    """
    job    = db.get_job(job_id)
    resume = db.get_profile("resume")

    if not job:
        return f"Job #{job_id} not found."
    if not resume:
        return "No resume stored. Call set_resume first."

    description = job["description"]
    if not description and job["source"] == "greenhouse":
        description = scrapers.fetch_greenhouse_job_description(job["company"], job["external_id"])
        if description:
            db.update_job_description(job_id, description)

    return (
        f"## Cover Letter Draft — Job #{job_id}\n\n"
        f"**Role:** {job['title']} @ {job['company']}\n"
        f"**URL:** {job['url']}\n\n"
        f"### Job Description\n"
        f"{description or '(No description — visit the URL for full JD)'}\n\n"
        f"### Resume\n{resume}\n\n"
        + (f"### Extra Context\n{extra_context}\n\n" if extra_context else "")
        + "---\n\n"
        f"**Write a tailored cover letter for this role. Requirements:**\n"
        f"- 3 short paragraphs max\n"
        f"- Paragraph 1: why this specific company (not generic)\n"
        f"- Paragraph 2: the 2–3 most relevant experiences from the resume that match the JD\n"
        f"- Paragraph 3: one concrete thing you'd contribute in the first 90 days\n"
        f"- No fluff, no 'I am excited to apply' openers\n"
        f"- End with a direct ask for a conversation"
    )


# ---------------------------------------------------------------------------
# 14. get_stats
# ---------------------------------------------------------------------------

@mcp.tool()
def get_stats() -> str:
    """
    Application funnel stats + job DB overview.
    """
    pipeline  = db.get_pipeline_stats()
    companies = db.get_companies()
    resume    = db.get_profile("resume")

    total_apps = sum(pipeline.values())
    applied    = pipeline.get("applied", 0) + pipeline.get("screen", 0) + pipeline.get("onsite", 0)
    offers     = pipeline.get("offer", 0)
    response_r = round(applied / pipeline.get("applied", 1) * 100) if applied else 0

    lines = [
        "## Job Search Stats\n",
        f"- Companies tracked : **{len(companies)}**",
        f"- Resume stored     : {'Yes' if resume else 'No — call set_resume'}",
        f"\n### Application Funnel",
    ]
    funnel = ["saved", "applied", "screen", "onsite", "offer", "rejected", "ghosted"]
    for s in funnel:
        n = pipeline.get(s, 0)
        if n:
            lines.append(f"  {s.upper():<12}: {n}")
    if total_apps:
        lines.append(f"\n  Total tracked : {total_apps}")
        lines.append(f"  Offers        : {offers}")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
