import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "interview_prep.db")

SESSIONS_DIR = os.path.join(os.path.dirname(__file__), "sessions")
os.makedirs(SESSIONS_DIR, exist_ok=True)

VALID_DIFFICULTIES = ("mh", "h")
VALID_CATEGORIES   = ("dsa", "lld", "hld", "mixed")
VALID_RESULTS      = ("solved", "hint", "stuck", "reviewed")
VALID_CONCEPT_TYPES = ("keyword", "pattern", "technique", "gotcha", "insight")

SCHEMA = """
CREATE TABLE IF NOT EXISTS problems (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        TEXT    NOT NULL UNIQUE,
    topic       TEXT    NOT NULL,
    pattern     TEXT    DEFAULT '',
    difficulty  TEXT    NOT NULL DEFAULT 'mh',
    category    TEXT    NOT NULL DEFAULT 'dsa',
    source      TEXT    DEFAULT '',
    url         TEXT    DEFAULT '',
    created_at  TEXT    DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS attempts (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id   INTEGER NOT NULL REFERENCES problems(id),
    result       TEXT    NOT NULL,
    time_minutes INTEGER DEFAULT 0,
    notes        TEXT    DEFAULT '',
    attempted_at TEXT    DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS reviews (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id   INTEGER NOT NULL REFERENCES problems(id) UNIQUE,
    interval     INTEGER DEFAULT 1,
    repetitions  INTEGER DEFAULT 0,
    ease_factor  REAL    DEFAULT 2.5,
    next_review  TEXT    DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS notes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    problem_id INTEGER NOT NULL REFERENCES problems(id),
    content    TEXT    NOT NULL,
    created_at TEXT    DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS sessions (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    category   TEXT    NOT NULL DEFAULT 'mixed',
    title      TEXT    DEFAULT '',
    started_at TEXT    DEFAULT (datetime('now')),
    ended_at   TEXT,
    notes      TEXT    DEFAULT ''
);

CREATE TABLE IF NOT EXISTS session_problems (
    session_id INTEGER NOT NULL REFERENCES sessions(id),
    problem_id INTEGER NOT NULL REFERENCES problems(id),
    PRIMARY KEY (session_id, problem_id)
);

CREATE TABLE IF NOT EXISTS faang_intel (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    company             TEXT    NOT NULL,
    topic               TEXT    NOT NULL,
    pattern             TEXT    DEFAULT '',
    problem_description TEXT    DEFAULT '',
    difficulty          TEXT    DEFAULT 'h',
    category            TEXT    DEFAULT 'dsa',
    source              TEXT    DEFAULT '',
    tags                TEXT    DEFAULT '',
    date_added          TEXT    DEFAULT (date('now'))
);

CREATE TABLE IF NOT EXISTS session_concepts (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES sessions(id),
    concept    TEXT    NOT NULL,
    type       TEXT    DEFAULT 'keyword',
    importance TEXT    DEFAULT 'important',
    created_at TEXT    DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS app_state (
    key   TEXT PRIMARY KEY,
    value TEXT
);
"""

# Columns added after initial schema — applied via migrate()
_MIGRATIONS = [
    ("problems", "category",   "TEXT NOT NULL DEFAULT 'dsa'"),
    ("problems", "difficulty", None),  # can't change CHECK but we drop the old one via recreate path
]


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _add_column_if_missing(conn, table: str, column: str, col_def: str):
    existing = [r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")


def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        # Migrate pre-existing problems table (may lack category column)
        _add_column_if_missing(conn, "problems", "category", "TEXT NOT NULL DEFAULT 'dsa'")


# ---------------------------------------------------------------------------
# app state (active session)
# ---------------------------------------------------------------------------

def set_state(key: str, value: str):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO app_state(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )


def get_state(key: str) -> str | None:
    with get_conn() as conn:
        row = conn.execute("SELECT value FROM app_state WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None


def clear_state(key: str):
    with get_conn() as conn:
        conn.execute("DELETE FROM app_state WHERE key=?", (key,))


# ---------------------------------------------------------------------------
# problems
# ---------------------------------------------------------------------------

def upsert_problem(name: str, topic: str, difficulty: str, category: str,
                   pattern: str = "", source: str = "", url: str = "") -> int:
    with get_conn() as conn:
        row = conn.execute("SELECT id FROM problems WHERE name=?", (name,)).fetchone()
        if row:
            return row["id"]
        cur = conn.execute(
            "INSERT INTO problems(name,topic,pattern,difficulty,category,source,url) VALUES(?,?,?,?,?,?,?)",
            (name, topic, pattern, difficulty, category, source, url),
        )
        return cur.lastrowid


def get_problem_by_name(name: str):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM problems WHERE name LIKE ?", (f"%{name}%",)).fetchone()


def search_problems(query: str = "", topic: str = "", category: str = "") -> list:
    with get_conn() as conn:
        clauses, params = [], []
        if category:
            clauses.append("p.category=?"); params.append(category)
        if topic:
            clauses.append("(p.topic LIKE ? OR p.pattern LIKE ?)")
            params += [f"%{topic}%", f"%{topic}%"]
        elif query:
            clauses.append("(p.name LIKE ? OR p.topic LIKE ? OR p.pattern LIKE ?)")
            params += [f"%{query}%", f"%{query}%", f"%{query}%"]
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return conn.execute(f"SELECT * FROM problems p {where} ORDER BY p.name", params).fetchall()


# ---------------------------------------------------------------------------
# attempts
# ---------------------------------------------------------------------------

def log_attempt(problem_id: int, result: str, time_minutes: int = 0, notes: str = ""):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO attempts(problem_id,result,time_minutes,notes) VALUES(?,?,?,?)",
            (problem_id, result, time_minutes, notes),
        )


# ---------------------------------------------------------------------------
# reviews (SM-2)
# ---------------------------------------------------------------------------

def get_review(problem_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM reviews WHERE problem_id=?", (problem_id,)).fetchone()


def upsert_review(problem_id: int, interval: int, repetitions: int,
                  ease_factor: float, next_review: str):
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO reviews(problem_id,interval,repetitions,ease_factor,next_review)
               VALUES(?,?,?,?,?)
               ON CONFLICT(problem_id) DO UPDATE SET
                 interval=excluded.interval, repetitions=excluded.repetitions,
                 ease_factor=excluded.ease_factor, next_review=excluded.next_review""",
            (problem_id, interval, repetitions, ease_factor, next_review),
        )


def get_due_problems(today: str, limit: int = 10, category: str = "") -> list:
    with get_conn() as conn:
        cat_clause = "AND p.category=?" if category else ""
        cat_param  = [category] if category else []
        return conn.execute(
            f"""SELECT p.*, r.next_review, r.interval, r.repetitions, r.ease_factor
                FROM reviews r JOIN problems p ON p.id=r.problem_id
                WHERE r.next_review<=? {cat_clause}
                ORDER BY r.next_review ASC LIMIT ?""",
            [today] + cat_param + [limit],
        ).fetchall()


# ---------------------------------------------------------------------------
# analytics
# ---------------------------------------------------------------------------

def get_topic_stats(category: str = "") -> list:
    with get_conn() as conn:
        cat_clause = "WHERE p.category=?" if category else ""
        return conn.execute(
            f"""SELECT p.category, p.topic, p.pattern,
                       COUNT(*) as total_attempts,
                       SUM(CASE WHEN a.result IN ('hint','stuck') THEN 1 ELSE 0 END) as struggles,
                       SUM(CASE WHEN a.result='solved' THEN 1 ELSE 0 END) as solved
                FROM attempts a JOIN problems p ON p.id=a.problem_id
                {cat_clause}
                GROUP BY p.category, p.topic, p.pattern
                ORDER BY struggles DESC""",
            [category] if category else [],
        ).fetchall()


def get_recent_attempts(limit: int = 20, category: str = "") -> list:
    with get_conn() as conn:
        cat_clause = "AND p.category=?" if category else ""
        return conn.execute(
            f"""SELECT p.name, p.topic, p.category, p.difficulty, a.result,
                       a.attempted_at, a.notes
                FROM attempts a JOIN problems p ON p.id=a.problem_id
                {cat_clause}
                ORDER BY a.attempted_at DESC LIMIT ?""",
            ([category] if category else []) + [limit],
        ).fetchall()


def get_streak_and_totals() -> dict:
    with get_conn() as conn:
        total  = conn.execute("SELECT COUNT(*) as n FROM attempts").fetchone()["n"]
        solved = conn.execute("SELECT COUNT(*) as n FROM attempts WHERE result='solved'").fetchone()["n"]
        by_cat = conn.execute(
            """SELECT p.category, COUNT(*) as n
               FROM attempts a JOIN problems p ON p.id=a.problem_id
               GROUP BY p.category"""
        ).fetchall()
        topics = conn.execute("SELECT COUNT(DISTINCT topic) as n FROM problems").fetchone()["n"]
        days   = conn.execute("SELECT COUNT(DISTINCT attempted_at) as n FROM attempts").fetchone()["n"]
        return {
            "total_attempts": total, "solved": solved,
            "topics": topics, "active_days": days,
            "by_category": {r["category"]: r["n"] for r in by_cat},
        }


# ---------------------------------------------------------------------------
# notes
# ---------------------------------------------------------------------------

def add_note(problem_id: int, content: str):
    with get_conn() as conn:
        conn.execute("INSERT INTO notes(problem_id,content) VALUES(?,?)", (problem_id, content))


def get_notes(problem_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT content, created_at FROM notes WHERE problem_id=? ORDER BY created_at DESC",
            (problem_id,),
        ).fetchall()


# ---------------------------------------------------------------------------
# sessions
# ---------------------------------------------------------------------------

def create_session(category: str, title: str = "") -> int:
    with get_conn() as conn:
        cur = conn.execute(
            "INSERT INTO sessions(category,title) VALUES(?,?)", (category, title)
        )
        return cur.lastrowid


def end_session(session_id: int, notes: str = ""):
    with get_conn() as conn:
        conn.execute(
            "UPDATE sessions SET ended_at=datetime('now'), notes=? WHERE id=?",
            (notes, session_id),
        )


def link_problem_to_session(session_id: int, problem_id: int):
    with get_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO session_problems(session_id,problem_id) VALUES(?,?)",
            (session_id, problem_id),
        )


def get_session(session_id: int):
    with get_conn() as conn:
        return conn.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()


def get_session_problems(session_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            """SELECT p.*, a.result, a.time_minutes, a.notes as attempt_notes
               FROM session_problems sp
               JOIN problems p ON p.id=sp.problem_id
               LEFT JOIN attempts a ON a.problem_id=p.id
               WHERE sp.session_id=?
               ORDER BY p.name""",
            (session_id,),
        ).fetchall()


def add_session_concept(session_id: int, concept: str,
                        concept_type: str = "keyword", importance: str = "important"):
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO session_concepts(session_id,concept,type,importance) VALUES(?,?,?,?)",
            (session_id, concept, concept_type, importance),
        )


def get_session_concepts(session_id: int) -> list:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM session_concepts WHERE session_id=? ORDER BY type, importance",
            (session_id,),
        ).fetchall()


def get_recent_sessions(limit: int = 10) -> list:
    with get_conn() as conn:
        return conn.execute(
            """SELECT s.*,
                      (SELECT COUNT(*) FROM session_problems sp WHERE sp.session_id=s.id) as problem_count,
                      (SELECT COUNT(*) FROM session_concepts sc WHERE sc.session_id=s.id) as concept_count
               FROM sessions s ORDER BY s.started_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()


# ---------------------------------------------------------------------------
# FAANG intel
# ---------------------------------------------------------------------------

def add_faang_intel(company: str, topic: str, pattern: str, description: str,
                    difficulty: str, category: str, source: str, tags: str) -> int:
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO faang_intel
               (company,topic,pattern,problem_description,difficulty,category,source,tags)
               VALUES(?,?,?,?,?,?,?,?)""",
            (company, topic, pattern, description, difficulty, category, source, tags),
        )
        return cur.lastrowid


def query_faang_intel(company: str = "", topic: str = "",
                      category: str = "", difficulty: str = "") -> list:
    with get_conn() as conn:
        clauses, params = [], []
        if company:    clauses.append("company LIKE ?");    params.append(f"%{company}%")
        if topic:      clauses.append("(topic LIKE ? OR pattern LIKE ? OR tags LIKE ?)"); params += [f"%{topic}%"]*3
        if category:   clauses.append("category=?");        params.append(category)
        if difficulty: clauses.append("difficulty=?");      params.append(difficulty)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        return conn.execute(
            f"SELECT * FROM faang_intel {where} ORDER BY date_added DESC", params
        ).fetchall()


init_db()
