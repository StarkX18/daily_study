import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "job_tracker.db")

VALID_ATS      = ("greenhouse", "lever", "ashby", "custom")
VALID_STATUSES = ("saved", "applied", "screen", "onsite", "offer", "rejected", "ghosted", "withdrawn")
VALID_PRIORITY = (1, 2, 3)

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    ats         TEXT    DEFAULT '',
    board_slug  TEXT    DEFAULT '',
    priority    INTEGER DEFAULT 2,
    roles       TEXT    DEFAULT '',
    locations   TEXT    DEFAULT '',
    notes       TEXT    DEFAULT '',
    active      INTEGER DEFAULT 1,
    added_at    TEXT    DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT    NOT NULL,
    company     TEXT    NOT NULL,
    title       TEXT    NOT NULL,
    location    TEXT    DEFAULT '',
    url         TEXT    NOT NULL,
    source      TEXT    NOT NULL,
    description TEXT    DEFAULT '',
    posted_at   TEXT    DEFAULT '',
    scraped_at  TEXT    DEFAULT (datetime('now')),
    seen        INTEGER DEFAULT 0,
    UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS applications (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    company      TEXT    NOT NULL,
    role         TEXT    NOT NULL,
    job_url      TEXT    DEFAULT '',
    status       TEXT    DEFAULT 'saved',
    applied_at   TEXT,
    last_update  TEXT    DEFAULT (datetime('now')),
    notes        TEXT    DEFAULT '',
    cover_letter TEXT    DEFAULT '',
    fit_score    INTEGER,
    fit_notes    TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS profile (
    key        TEXT PRIMARY KEY,
    value      TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);
"""

# Pre-seeded companies with known working ATS slugs
_SEED_COMPANIES = [
    # (name, ats, slug, priority, roles, locations)
    ("Stripe",      "greenhouse", "stripe",      1, "backend,platform,infra",   "remote,SF,NYC"),
    ("Airbnb",      "greenhouse", "airbnb",      1, "backend,fullstack",        "remote,SF"),
    ("Cloudflare",  "greenhouse", "cloudflare",  1, "backend,systems,infra",    "remote,SF,Austin"),
    ("Anthropic",   "greenhouse", "anthropic",   1, "backend,ML,infra",         "remote,SF"),
    ("Figma",       "greenhouse", "figma",       1, "backend,fullstack",        "remote,SF,NYC"),
    ("Brex",        "greenhouse", "brex",        2, "backend,platform",         "remote,SF,NYC"),
    ("Ramp",        "greenhouse", "ramp",        2, "backend,fullstack",        "remote,NYC"),
    ("Vercel",      "greenhouse", "vercel",      2, "backend,infra,DX",         "remote"),
    ("Linear",      "greenhouse", "linear",      2, "backend,fullstack",        "remote"),
    ("Retool",      "greenhouse", "retool",      2, "backend,fullstack",        "remote,SF,NYC"),
    ("Scale AI",    "greenhouse", "scaleai",     2, "backend,ML",               "remote,SF"),
    ("Notion",      "greenhouse", "notionhq",    2, "backend,infra",            "remote,SF,NYC"),
    ("Lyft",        "lever",      "lyft",        2, "backend,platform",         "remote,SF,NYC"),
    ("Reddit",      "lever",      "reddit",      2, "backend,infra",            "remote,SF,NYC"),
    ("Coinbase",    "greenhouse", "coinbase",    2, "backend,infra",            "remote,SF,NYC"),
    ("DoorDash",    "greenhouse", "doordash",    2, "backend,platform",         "remote,SF,NYC,Seattle"),
    ("Databricks",  "greenhouse", "databricks",  2, "backend,data,infra",       "remote,SF"),
    ("OpenAI",      "greenhouse", "openai",      1, "backend,infra,ML",         "remote,SF"),
]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
    _seed_companies()


def _seed_companies():
    with get_conn() as conn:
        count = conn.execute("SELECT COUNT(*) as n FROM companies").fetchone()["n"]
        if count > 0:
            return
        for name, ats, slug, priority, roles, locs in _SEED_COMPANIES:
            conn.execute(
                "INSERT OR IGNORE INTO companies(name,ats,board_slug,priority,roles,locations) VALUES(?,?,?,?,?,?)",
                (name, ats, slug, priority, roles, locs),
            )


# ---------------------------------------------------------------------------
# companies
# ---------------------------------------------------------------------------

def upsert_company(name: str, ats: str, board_slug: str, priority: int,
                   roles: str, locations: str, notes: str) -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM companies WHERE name=?", (name,)).fetchone()
        if row:
            conn.execute(
                """UPDATE companies SET ats=?,board_slug=?,priority=?,roles=?,
                   locations=?,notes=?,active=1 WHERE name=?""",
                (ats, board_slug, priority, roles, locations, notes, name),
            )
            return row["id"]
        cur = conn.execute(
            "INSERT INTO companies(name,ats,board_slug,priority,roles,locations,notes) VALUES(?,?,?,?,?,?,?)",
            (name, ats, board_slug, priority, roles, locations, notes),
        )
        return cur.lastrowid


def get_companies(priority: int = 0, active_only: bool = True) -> list:
    with get_conn() as conn:
        clauses, params = [], []
        if active_only:
            clauses.append("active=1")
        if priority:
            clauses.append("priority=?"); params.append(priority)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return conn.execute(
            f"SELECT * FROM companies {where} ORDER BY priority ASC, name ASC", params
        ).fetchall()


def deactivate_company(name: str):
    with get_conn() as conn:
        conn.execute("UPDATE companies SET active=0 WHERE name LIKE ?", (f"%{name}%",))


# ---------------------------------------------------------------------------
# jobs
# ---------------------------------------------------------------------------

def upsert_job(external_id: str, company: str, title: str, location: str,
               url: str, source: str, description: str, posted_at: str) -> tuple[int, bool]:
    """Returns (id, is_new)."""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM jobs WHERE source=? AND external_id=?", (source, external_id)
        ).fetchone()
        if existing:
            return existing["id"], False
        cur = conn.execute(
            """INSERT INTO jobs(external_id,company,title,location,url,source,description,posted_at)
               VALUES(?,?,?,?,?,?,?,?)""",
            (external_id, company, title, location, url, source, description, posted_at),
        )
        return cur.lastrowid, True


def get_job(job_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM jobs WHERE id=?", (job_id,)).fetchone()


def get_new_jobs(limit: int = 20, company: str = "", keyword: str = "") -> list:
    with get_conn() as conn:
        clauses, params = ["seen=0"], []
        if company:
            clauses.append("LOWER(company) LIKE ?"); params.append(f"%{company.lower()}%")
        if keyword:
            clauses.append("(LOWER(title) LIKE ? OR LOWER(description) LIKE ?)")
            params += [f"%{keyword.lower()}%", f"%{keyword.lower()}%"]
        where = "WHERE " + " AND ".join(clauses)
        return conn.execute(
            f"SELECT * FROM jobs {where} ORDER BY scraped_at DESC LIMIT ?", params + [limit]
        ).fetchall()


def mark_jobs_seen(job_ids: list[int]):
    with get_conn() as conn:
        conn.executemany("UPDATE jobs SET seen=1 WHERE id=?", [(i,) for i in job_ids])


def search_jobs(query: str = "", company: str = "", location: str = "",
                source: str = "") -> list:
    with get_conn() as conn:
        clauses, params = [], []
        if query:
            clauses.append("(LOWER(title) LIKE ? OR LOWER(description) LIKE ? OR LOWER(company) LIKE ?)")
            params += [f"%{query.lower()}%"] * 3
        if company:
            clauses.append("LOWER(company) LIKE ?"); params.append(f"%{company.lower()}%")
        if location:
            clauses.append("LOWER(location) LIKE ?"); params.append(f"%{location.lower()}%")
        if source:
            clauses.append("source=?"); params.append(source)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return conn.execute(
            f"SELECT * FROM jobs {where} ORDER BY scraped_at DESC LIMIT 50", params
        ).fetchall()


def update_job_description(job_id: int, description: str):
    with get_conn() as conn:
        conn.execute("UPDATE jobs SET description=? WHERE id=?", (description, job_id))


# ---------------------------------------------------------------------------
# applications
# ---------------------------------------------------------------------------

def add_application(company: str, role: str, job_url: str, notes: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO applications(company,role,job_url,notes) VALUES(?,?,?,?)",
            (company, role, job_url, notes),
        )
        return cur.lastrowid


def update_application(app_id: int, status: str = "", notes: str = "",
                       cover_letter: str = "", fit_score: int = None, fit_notes: str = ""):
    with get_conn() as conn:
        updates, params = [], []
        if status:
            updates.append("status=?");        params.append(status)
            if status == "applied":
                updates.append("applied_at=date('now')")
        if notes:
            updates.append("notes=?");         params.append(notes)
        if cover_letter:
            updates.append("cover_letter=?");  params.append(cover_letter)
        if fit_score is not None:
            updates.append("fit_score=?");     params.append(fit_score)
        if fit_notes:
            updates.append("fit_notes=?");     params.append(fit_notes)
        updates.append("last_update=datetime('now')")
        conn.execute(
            f"UPDATE applications SET {', '.join(updates)} WHERE id=?",
            params + [app_id],
        )


def get_pipeline() -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM applications ORDER BY last_update DESC"
        ).fetchall()


def get_pipeline_stats() -> dict:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) as n FROM applications GROUP BY status"
        ).fetchall()
        return {r["status"]: r["n"] for r in rows}


# ---------------------------------------------------------------------------
# profile
# ---------------------------------------------------------------------------

def set_profile(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO profile(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
            (key, value),
        )


def get_profile(key: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM profile WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None


init_db()
