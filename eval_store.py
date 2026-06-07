"""
eval_store.py — SQLite Logging Layer
Reddit Post Generator

Logs every generation + evaluation to SQLite for dashboard analysis.
Enables tracking score trends over time and across subreddits.
"""

import sqlite3
import json
from datetime import datetime
from pathlib import Path
from evaluator import EvalResult

DB_PATH = Path(__file__).parent / "eval_results.db"


# ── Schema ────────────────────────────────────────────────────────────────────

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS generations (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp             TEXT NOT NULL,
    subreddit             TEXT NOT NULL,
    topic                 TEXT NOT NULL,
    post_type             TEXT NOT NULL,
    title                 TEXT NOT NULL,
    body                  TEXT NOT NULL,

    -- Eval scores
    rule_compliance       REAL,
    tone_match            REAL,
    title_clickability    REAL,
    authenticity          REAL,
    engagement_potential  REAL,
    overall_score         REAL,
    average_score         REAL,

    -- Eval reasoning (stored as JSON string)
    reasoning_json        TEXT,
    improvement           TEXT,

    -- User feedback
    user_rating           INTEGER DEFAULT NULL  -- 1=thumbs up, -1=thumbs down, NULL=no feedback
)
"""


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Create tables if they don't exist."""
    with get_connection() as conn:
        conn.execute(CREATE_TABLE)
        conn.commit()


# ── Write ─────────────────────────────────────────────────────────────────────

def log_generation(
    subreddit: str,
    topic: str,
    post_type: str,
    title: str,
    body: str,
    eval_result: EvalResult,
) -> int:
    """
    Log a generation + evaluation to SQLite.
    Returns the row ID for later feedback updates.
    """
    init_db()

    reasoning = {
        "rule_compliance":      eval_result.rule_compliance.reasoning,
        "tone_match":           eval_result.tone_match.reasoning,
        "title_clickability":   eval_result.title_clickability.reasoning,
        "authenticity":         eval_result.authenticity.reasoning,
        "engagement_potential": eval_result.engagement_potential.reasoning,
        "overall_score":        eval_result.overall_score.reasoning,
    }

    with get_connection() as conn:
        cursor = conn.execute("""
            INSERT INTO generations (
                timestamp, subreddit, topic, post_type, title, body,
                rule_compliance, tone_match, title_clickability,
                authenticity, engagement_potential, overall_score,
                average_score, reasoning_json, improvement
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.utcnow().isoformat(),
            subreddit, topic, post_type, title, body,
            eval_result.rule_compliance.score,
            eval_result.tone_match.score,
            eval_result.title_clickability.score,
            eval_result.authenticity.score,
            eval_result.engagement_potential.score,
            eval_result.overall_score.score,
            eval_result.average_score(),
            json.dumps(reasoning),
            eval_result.improvement_suggestion,
        ))
        conn.commit()
        return cursor.lastrowid


def update_feedback(row_id: int, rating: int):
    """Update user feedback (1 = thumbs up, -1 = thumbs down)."""
    init_db()
    with get_connection() as conn:
        conn.execute(
            "UPDATE generations SET user_rating = ? WHERE id = ?",
            (rating, row_id)
        )
        conn.commit()


# ── Read ──────────────────────────────────────────────────────────────────────

def get_all_generations(subreddit: str = None) -> list[dict]:
    """Fetch all logged generations, optionally filtered by subreddit."""
    init_db()
    with get_connection() as conn:
        if subreddit:
            rows = conn.execute(
                "SELECT * FROM generations WHERE subreddit = ? ORDER BY timestamp DESC",
                (subreddit,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM generations ORDER BY timestamp DESC"
            ).fetchall()
    return [dict(row) for row in rows]


def get_score_trends(subreddit: str = None) -> list[dict]:
    """Fetch timestamp + scores for trend plotting."""
    init_db()
    query = """
        SELECT timestamp, subreddit, average_score,
               rule_compliance, tone_match, title_clickability,
               authenticity, engagement_potential, overall_score
        FROM generations
        {}
        ORDER BY timestamp ASC
    """.format("WHERE subreddit = ?" if subreddit else "")

    with get_connection() as conn:
        if subreddit:
            rows = conn.execute(query, (subreddit,)).fetchall()
        else:
            rows = conn.execute(query).fetchall()
    return [dict(row) for row in rows]


def get_summary_stats(subreddit: str = None) -> dict:
    """Aggregate stats across all generations."""
    init_db()
    where = "WHERE subreddit = ?" if subreddit else ""
    params = (subreddit,) if subreddit else ()

    with get_connection() as conn:
        row = conn.execute(f"""
            SELECT
                COUNT(*)                        AS total,
                ROUND(AVG(average_score), 2)    AS avg_overall,
                ROUND(AVG(rule_compliance), 2)  AS avg_rule,
                ROUND(AVG(tone_match), 2)        AS avg_tone,
                ROUND(AVG(title_clickability), 2) AS avg_title,
                ROUND(AVG(authenticity), 2)      AS avg_auth,
                ROUND(AVG(engagement_potential), 2) AS avg_engage,
                SUM(CASE WHEN user_rating = 1  THEN 1 ELSE 0 END) AS thumbs_up,
                SUM(CASE WHEN user_rating = -1 THEN 1 ELSE 0 END) AS thumbs_down
            FROM generations {where}
        """, params).fetchone()
    return dict(row) if row else {}


def get_top_posts(n: int = 5, subreddit: str = None) -> list[dict]:
    """Return top N posts by average score."""
    init_db()
    where = "WHERE subreddit = ?" if subreddit else ""
    params = (subreddit,) if subreddit else ()
    with get_connection() as conn:
        rows = conn.execute(
            f"SELECT * FROM generations {where} ORDER BY average_score DESC LIMIT ?",
            (*params, n)
        ).fetchall()
    return [dict(row) for row in rows]
