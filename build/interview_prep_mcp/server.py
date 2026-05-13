"""
Interview Prep MCP Server
DSA / LLD / HLD tracking with SM-2 spaced repetition and session wrap-up.
"""
import os
from datetime import datetime, date

from mcp.server.fastmcp import FastMCP

import db
import scheduler

mcp = FastMCP("interview-prep")


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _active_session_id() -> int | None:
    v = db.get_state("active_session_id")
    return int(v) if v else None


def _fmt_problem_row(r, next_rev=None) -> str:
    base = f"**{r['name']}** [{r['difficulty'].upper()}] [{r['category'].upper()}] — {r['topic']}"
    if r['pattern']:
        base += f" / {r['pattern']}"
    if next_rev:
        base += f" | next review: {next_rev}"
    return base


# ---------------------------------------------------------------------------
# 1. log_problem
# ---------------------------------------------------------------------------

@mcp.tool()
def log_problem(
    name: str,
    topic: str,
    category: str,
    difficulty: str,
    result: str,
    pattern: str = "",
    source: str = "",
    url: str = "",
    time_minutes: int = 0,
    notes: str = "",
) -> str:
    """
    Log a problem attempt. Auto-schedules SM-2 review and links to active session.

    Args:
        name: Problem name (e.g. "Two Sum", "Design a URL Shortener")
        topic: High-level topic (e.g. "graphs", "caching", "object modelling")
        category: "dsa" | "lld" | "hld"
        difficulty: "mh" (medium-hard) | "h" (hard)
        result: "solved" | "hint" | "stuck" | "reviewed"
        pattern: Specific pattern (e.g. "Two Pointers", "Observer Pattern")
        source: Origin (e.g. "leetcode", "meta onsite", "faang report")
        url: Optional link
        time_minutes: Time spent
        notes: Observations or key insights
    """
    category   = category.lower()
    difficulty = difficulty.lower()
    result     = result.lower()

    if category not in db.VALID_CATEGORIES:
        return f"Invalid category '{category}'. Use: {', '.join(db.VALID_CATEGORIES)}"
    if difficulty not in db.VALID_DIFFICULTIES:
        return f"Invalid difficulty '{difficulty}'. Use: mh | h"
    if result not in db.VALID_RESULTS:
        return f"Invalid result '{result}'. Use: {', '.join(db.VALID_RESULTS)}"

    problem_id = db.upsert_problem(name, topic, difficulty, category, pattern, source, url)
    db.log_attempt(problem_id, result, time_minutes, notes)

    # SM-2
    review = db.get_review(problem_id)
    q = scheduler.result_to_quality(result)
    reps = review["repetitions"] if review else 0
    ef   = review["ease_factor"]  if review else 2.5
    intv = review["interval"]     if review else 1
    reps, ef, intv, next_rev = scheduler.sm2(q, reps, ef, intv)
    db.upsert_review(problem_id, intv, reps, ef, next_rev)

    # Link to active session
    sid = _active_session_id()
    session_note = ""
    if sid:
        db.link_problem_to_session(sid, problem_id)
        session_note = f"\nLinked to session #{sid}."

    icon = {"solved": "✅", "hint": "🟡", "stuck": "❌", "reviewed": "🔄"}.get(result, "")
    return (
        f"{icon} **{name}** [{difficulty.upper()}] [{category.upper()}] — {result}\n"
        f"Topic: {topic}" + (f" | Pattern: {pattern}" if pattern else "") + "\n"
        f"Next review: **{next_rev}** (in {intv} day{'s' if intv != 1 else ''})"
        + session_note
    )


# ---------------------------------------------------------------------------
# 2. update_review
# ---------------------------------------------------------------------------

@mcp.tool()
def update_review(problem_name: str, quality: int) -> str:
    """
    Update SM-2 quality after active recall.

    Args:
        problem_name: Partial name match
        quality: 0=blackout … 5=perfect
    """
    if not 0 <= quality <= 5:
        return "Quality must be 0-5."
    row = db.get_problem_by_name(problem_name)
    if not row:
        return f"No problem matching '{problem_name}'. Log it first."

    review = db.get_review(row["id"])
    reps, ef, intv, next_rev = scheduler.sm2(
        quality,
        review["repetitions"] if review else 0,
        review["ease_factor"]  if review else 2.5,
        review["interval"]     if review else 1,
    )
    db.upsert_review(row["id"], intv, reps, ef, next_rev)

    label = ["Blackout 🔴","Incorrect 🔴","Incorrect (recalled) 🟠",
             "Correct w/ effort 🟡","Correct 🟢","Perfect 🏆"][quality]
    return (
        f"Review updated: **{row['name']}**\n"
        f"Quality: {quality}/5 — {label}\n"
        f"Next review: **{next_rev}** (interval: {intv}d, EF: {ef:.2f})"
    )


# ---------------------------------------------------------------------------
# 3. get_due_problems
# ---------------------------------------------------------------------------

@mcp.tool()
def get_due_problems(limit: int = 8, category: str = "") -> str:
    """
    Problems due for spaced repetition today (or overdue).

    Args:
        limit: Max to return
        category: Filter by "dsa" | "lld" | "hld" (blank = all)
    """
    today = date.today().isoformat()
    rows  = db.get_due_problems(today, limit, category)
    if not rows:
        label = f" in {category.upper()}" if category else ""
        return f"Nothing due today{label}. You're caught up!"
    lines = [f"## Due for review ({len(rows)})\n"]
    for r in rows:
        overdue = " ⚠️ OVERDUE" if r["next_review"] < today else ""
        lines.append(
            f"- {_fmt_problem_row(r)} | interval: {r['interval']}d{overdue}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 4. analyze_weak_spots
# ---------------------------------------------------------------------------

@mcp.tool()
def analyze_weak_spots(category: str = "") -> str:
    """
    Weak topics sorted by struggle rate, optionally filtered by category.

    Args:
        category: "dsa" | "lld" | "hld" | "" (all)
    """
    stats = db.get_topic_stats(category)
    if not stats:
        return "No attempts yet. Start with log_problem."

    lines = ["## Weak Spot Analysis\n"]
    lines.append(f"{'Cat':<6} {'Topic':<22} {'Pattern':<24} {'Att':>4} {'Solv':>5} {'Str':>5} {'%':>5}")
    lines.append("-" * 72)
    for s in stats:
        total = s["total_attempts"]
        pct   = round(s["struggles"] / total * 100) if total else 0
        bar   = "🔴" if pct >= 60 else ("🟡" if pct >= 30 else "🟢")
        lines.append(
            f"{s['category'].upper():<6} {s['topic']:<22} {(s['pattern'] or '-'):<24}"
            f" {total:>4} {s['solved']:>5} {s['struggles']:>5} {pct:>4}% {bar}"
        )

    recent = db.get_recent_attempts(5, category)
    if recent:
        lines.append("\n## Last 5 attempts")
        for a in recent:
            lines.append(f"- [{a['category'].upper()}] {a['name']} [{a['difficulty'].upper()}] — {a['result']} ({a['attempted_at']})")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 5. generate_problem
# ---------------------------------------------------------------------------

@mcp.tool()
def generate_problem(
    category: str = "dsa",
    topic: str = "",
    pattern: str = "",
    difficulty: str = "h",
    company: str = "",
) -> str:
    """
    Generate a targeted practice problem prompt aimed at your weak spots.

    Args:
        category: "dsa" | "lld" | "hld"
        topic: Leave blank to auto-pick your weakest topic
        pattern: Specific pattern (e.g. "Sliding Window")
        difficulty: "mh" | "h"
        company: Target company context (e.g. "meta", "google")
    """
    auto_note = ""
    if not topic and not pattern:
        stats = db.get_topic_stats(category)
        if stats:
            worst     = stats[0]
            topic     = worst["topic"]
            pattern   = worst["pattern"] or ""
            auto_note = f"(auto-selected weakest area: **{topic}**" + (f" / {pattern})" if pattern else ")")
        else:
            topic     = "arrays" if category == "dsa" else ("object modelling" if category == "lld" else "distributed storage")
            auto_note = "(no history yet — using default topic)"

    company_ctx = f" as seen in recent {company.title()} interviews" if company else ""
    pattern_ctx = f" using the **{pattern}** pattern" if pattern else ""
    diff_label  = "Medium-Hard" if difficulty == "mh" else "Hard"

    if category == "hld":
        prompt = (
            f"Generate a {diff_label} system design (HLD) interview question{company_ctx}.\n"
            f"Topic: **{topic}**.\n"
            f"Include: (1) Problem statement & scale requirements, (2) clarifying questions to ask, "
            f"(3) high-level architecture diagram (text), (4) key components & trade-offs, "
            f"(5) bottlenecks & follow-up deep-dives."
        )
    elif category == "lld":
        prompt = (
            f"Generate a {diff_label} low-level design (LLD) interview question{company_ctx}.\n"
            f"Topic: **{topic}**.\n"
            f"Include: (1) Problem statement with functional/non-functional requirements, "
            f"(2) class/interface diagram (text), (3) key design patterns used, "
            f"(4) edge cases, (5) follow-up: scaling or extending the design."
        )
    else:
        prompt = (
            f"Generate a {diff_label} DSA coding problem{pattern_ctx}{company_ctx}.\n"
            f"Topic: **{topic}**.\n"
            f"Include: (1) Problem statement with examples & constraints, "
            f"(2) hints (collapsible), (3) optimal solution with time/space complexity, "
            f"(4) common mistakes, (5) follow-up variant."
        )

    return (
        f"## Problem Generator {auto_note}\n\n"
        f"**Category:** {category.upper()} | **Topic:** {topic}"
        + (f" | **Pattern:** {pattern}" if pattern else "")
        + f"\n**Difficulty:** {diff_label}"
        + (f" | **Company:** {company}" if company else "") + "\n\n---\n\n"
        + prompt
    )


# ---------------------------------------------------------------------------
# 6. get_stats
# ---------------------------------------------------------------------------

@mcp.tool()
def get_stats() -> str:
    """Overall prep stats broken down by category (DSA / LLD / HLD)."""
    s     = db.get_streak_and_totals()
    today = date.today().isoformat()
    due   = len(db.get_due_problems(today, 50))
    rate  = round(s["solved"] / s["total_attempts"] * 100) if s["total_attempts"] else 0
    by_cat = s["by_category"]
    lines = [
        "## Interview Prep Stats\n",
        f"- Total attempts : **{s['total_attempts']}**",
        f"- Solved (clean) : **{s['solved']}** ({rate}% solve rate)",
        f"- Topics covered : **{s['topics']}**",
        f"- Active days    : **{s['active_days']}**",
        f"- Due today      : **{due}**",
        "\n### By Category",
    ]
    for cat in ("dsa", "lld", "hld"):
        n = by_cat.get(cat, 0)
        lines.append(f"  {cat.upper()}: {n} attempts")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 7. search_problem
# ---------------------------------------------------------------------------

@mcp.tool()
def search_problem(query: str = "", topic: str = "", category: str = "") -> str:
    """
    Search logged problems by name, topic, pattern, or category.

    Args:
        query: Free-text search
        topic: Filter by topic/pattern
        category: "dsa" | "lld" | "hld" | "" (all)
    """
    rows = db.search_problems(query, topic, category)
    if not rows:
        return f"No problems found for '{query or topic or category}'."
    lines = [f"## Results ({len(rows)})\n"]
    for r in rows:
        rev      = db.get_review(r["id"])
        next_rev = rev["next_review"] if rev else "not scheduled"
        lines.append(f"- {_fmt_problem_row(r, next_rev)}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 8. add_note
# ---------------------------------------------------------------------------

@mcp.tool()
def add_note(problem_name: str, note: str) -> str:
    """
    Append a note or insight to a problem.

    Args:
        problem_name: Partial match OK
        note: Key insight, gotcha, pattern reminder, etc.
    """
    row = db.get_problem_by_name(problem_name)
    if not row:
        return f"No problem matching '{problem_name}'. Log it first."
    db.add_note(row["id"], note)
    existing = db.get_notes(row["id"])
    lines = [f"Note saved for **{row['name']}**.\n\n### All notes:"]
    for n in existing:
        lines.append(f"- [{n['created_at']}] {n['content']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 9. start_session
# ---------------------------------------------------------------------------

@mcp.tool()
def start_session(category: str = "mixed", title: str = "") -> str:
    """
    Start a new study session. Subsequent log_problem calls auto-link to it.

    Args:
        category: "dsa" | "lld" | "hld" | "mixed"
        title: Optional session label (e.g. "Meta prep — graphs")
    """
    existing = _active_session_id()
    if existing:
        s = db.get_session(existing)
        return (
            f"Session #{existing} is already active ({s['category'].upper()}, started {s['started_at']}).\n"
            f"Call wrap_session first to close it."
        )
    sid = db.create_session(category.lower(), title)
    db.set_state("active_session_id", str(sid))
    label = f' — "{title}"' if title else ""
    return (
        f"✅ Session #{sid} started{label} [{category.upper()}]\n"
        f"Everything you log_problem now will be tracked to this session.\n"
        f"When done, call wrap_session."
    )


# ---------------------------------------------------------------------------
# 10. add_concept
# ---------------------------------------------------------------------------

@mcp.tool()
def add_concept(
    concept: str,
    concept_type: str = "keyword",
    importance: str = "important",
) -> str:
    """
    Add a keyword, pattern, or insight to the active session's concept log.
    Called mid-session whenever something important comes up.

    Args:
        concept: The concept/term/insight (e.g. "amortized O(1)", "saga pattern")
        concept_type: "keyword" | "pattern" | "technique" | "gotcha" | "insight"
        importance: "key" | "important" | "reference"
    """
    sid = _active_session_id()
    if not sid:
        return "No active session. Call start_session first."
    if concept_type not in db.VALID_CONCEPT_TYPES:
        concept_type = "keyword"
    db.add_session_concept(sid, concept, concept_type, importance)
    return f"Concept saved to session #{sid}: **{concept}** [{concept_type} / {importance}]"


# ---------------------------------------------------------------------------
# 11. wrap_session
# ---------------------------------------------------------------------------

@mcp.tool()
def wrap_session(extra_concepts: str = "", notes: str = "") -> str:
    """
    End the active session and write a Markdown summary file.
    Call this when you're done studying — or when you say "we're done".

    Args:
        extra_concepts: Comma-separated last-minute concepts to add
        notes: Any closing notes or reflections
    """
    sid = _active_session_id()
    if not sid:
        return "No active session. Start one with start_session."

    # Add any last-minute concepts
    if extra_concepts:
        for c in [c.strip() for c in extra_concepts.split(",") if c.strip()]:
            db.add_session_concept(sid, c, "keyword", "important")

    db.end_session(sid, notes)
    db.clear_state("active_session_id")

    session  = db.get_session(sid)
    problems = db.get_session_problems(sid)
    concepts = db.get_session_concepts(sid)

    # Build markdown
    now       = datetime.now()
    cat       = session["category"].upper()
    title     = session["title"] or f"{cat} Session"
    started   = session["started_at"] or now.isoformat()
    duration  = ""
    try:
        s = datetime.fromisoformat(started)
        mins = int((now - s).total_seconds() / 60)
        duration = f"{mins} min"
    except Exception:
        pass

    lines = [
        f"# {title}",
        f"**Date:** {now.strftime('%Y-%m-%d')}  |  **Category:** {cat}  |  **Duration:** {duration}",
        f"**Session ID:** #{sid}",
        "",
    ]

    # Problems
    lines += ["## Problems Covered", ""]
    if problems:
        for p in problems:
            icon = {"solved":"✅","hint":"🟡","stuck":"❌","reviewed":"🔄"}.get(p["result"] or "", "•")
            line = f"{icon} **{p['name']}** [{p['difficulty'].upper()}] — {p['topic']}"
            if p["pattern"]:
                line += f" / {p['pattern']}"
            if p["attempt_notes"]:
                line += f"\n   > {p['attempt_notes']}"
            lines.append(f"- {line}")
    else:
        lines.append("_No problems logged this session._")

    # Concepts by type
    lines += ["", "## Key Concepts & Keywords", ""]
    type_order = ["keyword", "pattern", "technique", "insight", "gotcha"]
    grouped: dict[str, list[str]] = {}
    for c in concepts:
        grouped.setdefault(c["type"], []).append(
            f"{'⭐ ' if c['importance'] == 'key' else ''}{c['concept']}"
        )
    for t in type_order:
        if t in grouped:
            lines.append(f"### {t.capitalize()}s")
            for item in grouped[t]:
                lines.append(f"- {item}")
            lines.append("")

    if not concepts:
        lines.append("_No concepts logged. Use add_concept mid-session next time._")

    # Notes
    if notes:
        lines += ["", "## Session Notes", "", notes]

    # Footer
    lines += [
        "", "---",
        f"_Generated by interview-prep MCP · {now.strftime('%Y-%m-%d %H:%M')}_",
    ]

    md = "\n".join(lines)

    # Save to file
    filename  = now.strftime(f"%Y-%m-%d_%H-%M") + f"_{session['category']}.md"
    filepath  = os.path.join(db.SESSIONS_DIR, filename)
    with open(filepath, "w") as f:
        f.write(md)

    prob_count    = len(problems)
    concept_count = len(concepts)
    return (
        f"## Session #{sid} wrapped ✅\n\n"
        f"- Problems: **{prob_count}**\n"
        f"- Concepts: **{concept_count}**\n"
        f"- Duration: {duration}\n"
        f"- Saved to: `{filepath}`\n\n"
        + md
    )


# ---------------------------------------------------------------------------
# 12. add_faang_intel
# ---------------------------------------------------------------------------

@mcp.tool()
def add_faang_intel(
    company: str,
    topic: str,
    description: str,
    pattern: str = "",
    difficulty: str = "h",
    category: str = "dsa",
    source: str = "",
    tags: str = "",
) -> str:
    """
    Add a problem or topic to the dynamic FAANG intel database.
    Use this whenever you find a real question from a report, blog, or interview experience.

    Args:
        company: e.g. "meta", "google", "stripe"
        topic: e.g. "graphs", "rate limiter", "LRU cache"
        description: Problem description or summary
        pattern: e.g. "BFS", "Observer pattern"
        difficulty: "mh" | "h"
        category: "dsa" | "lld" | "hld"
        source: Where you found it (e.g. "leetcode discuss", "levels.fyi", "blind")
        tags: Comma-separated tags (e.g. "2024, onsite, L5")
    """
    rid = db.add_faang_intel(
        company.lower(), topic, pattern, description,
        difficulty.lower(), category.lower(), source, tags
    )
    return (
        f"Added to FAANG intel #{rid}: **{company.title()} — {topic}**\n"
        f"[{category.upper()}] [{difficulty.upper()}]"
        + (f" | Pattern: {pattern}" if pattern else "")
        + (f"\nTags: {tags}" if tags else "")
    )


# ---------------------------------------------------------------------------
# 13. get_faang_intel
# ---------------------------------------------------------------------------

@mcp.tool()
def get_faang_intel(
    company: str = "",
    topic: str = "",
    category: str = "",
    difficulty: str = "",
) -> str:
    """
    Query the dynamic FAANG intel database. All filters are optional.

    Args:
        company: Filter by company (partial match)
        topic: Filter by topic/pattern/tags (partial match)
        category: "dsa" | "lld" | "hld" | "" (all)
        difficulty: "mh" | "h" | "" (all)
    """
    rows = db.query_faang_intel(company, topic, category, difficulty)
    if not rows:
        return "No FAANG intel found. Add entries with add_faang_intel."
    lines = [f"## FAANG Intel ({len(rows)} entries)\n"]
    for r in rows:
        lines.append(
            f"- **{r['company'].title()} — {r['topic']}** [{r['difficulty'].upper()}] [{r['category'].upper()}]"
            + (f" | {r['pattern']}" if r["pattern"] else "")
            + f"\n  {r['problem_description'][:120]}"
            + (f"\n  Tags: {r['tags']}" if r["tags"] else "")
            + f"\n  Source: {r['source']} · Added: {r['date_added']}"
        )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 14. get_session_history
# ---------------------------------------------------------------------------

@mcp.tool()
def get_session_history(limit: int = 10) -> str:
    """
    View recent sessions with problem and concept counts.
    Shows what was covered per session and cumulative by category.
    """
    sessions = db.get_recent_sessions(limit)
    if not sessions:
        return "No sessions yet. Start one with start_session."

    lines = [f"## Session History (last {len(sessions)})\n"]
    for s in sessions:
        status = "🟢 active" if not s["ended_at"] else f"ended {s['ended_at'][:16]}"
        lines.append(
            f"### #{s['id']} [{s['category'].upper()}] — {s['title'] or 'untitled'} ({status})"
        )
        lines.append(f"  Started: {s['started_at'][:16]} | Problems: {s['problem_count']} | Concepts: {s['concept_count']}")
        if s["notes"]:
            lines.append(f"  Notes: {s['notes'][:100]}")

    # Cumulative by category
    totals = db.get_streak_and_totals()
    lines += ["\n## Cumulative by Category"]
    for cat in ("dsa", "lld", "hld"):
        n = totals["by_category"].get(cat, 0)
        lines.append(f"  {cat.upper()}: {n} attempts")

    active = _active_session_id()
    if active:
        lines.append(f"\n⚡ Session #{active} is currently active.")
    return "\n".join(lines)


if __name__ == "__main__":
    mcp.run()
