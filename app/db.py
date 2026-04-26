"""
=============================================================================
db.py — Database connection and JSON ingestion
=============================================================================

PURPOSE
-------
Two responsibilities:
1. get_connection() / get_engine() — provide database access to all other modules
2. load_results_from_json() — parse roi_scores.json and INSERT into PostgreSQL

WHY A SEPARATE db.py?
----------------------
Separating DB concerns from UI code is standard engineering practice.
If you swap PostgreSQL for DuckDB tomorrow, only this file changes.
The Streamlit dashboard just calls functions from here — it doesn't know
or care what database engine is underneath.

DESIGN DECISION — Why load JSON into PostgreSQL at all?
--------------------------------------------------------
You could read the JSON directly in Streamlit without a database.
But using PostgreSQL + dbt gives you:
  - Audit trail (scoring_runs table)
  - dbt transformations for normalisation and comparison logic
  - Portfolio consistency with Projects 02 and 03
  - Query layer that works with Metabase if you want to add it later
"""

import json
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text

# ── Connection setup ──────────────────────────────────────────────────────────

def get_database_url() -> str:
    """
    Read DATABASE_URL from environment.
    Inside Docker: set by docker-compose.yml
    Outside Docker (local dev): falls back to localhost:5435
    """
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://tribe:tribe_scorer_dev@localhost:5435/tribe_scorer"
    )


def get_engine():
    """
    SQLAlchemy engine — used for pandas read_sql and bulk inserts.
    SQLAlchemy is the standard Python ORM/DB toolkit. The engine is
    a connection pool — it doesn't open a connection until you use it.
    """
    return create_engine(get_database_url())


def get_connection():
    """
    Raw psycopg2 connection — used for simple single statements.
    psycopg2 is the native PostgreSQL adapter for Python.
    """
    return psycopg2.connect(get_database_url())


# ── JSON ingestion ────────────────────────────────────────────────────────────

def load_results_from_json(json_path: str | Path) -> str:
    """
    Parse roi_scores.json output from run_tribe.py and load into PostgreSQL.

    Returns the run_id string so the dashboard can query it.

    The JSON structure matches exactly what run_tribe.py writes:
    {
      "ad_a": {
        "run_id": "2026-04-25T14:30",
        "roi_scores": {"visual": 0.48, "memory": 0.36, ...},
        "top_10_rois": ["V1", "A1", ...],
        "global": {"mean": 0.38, "peak": 1.21, "p95": 0.89},
        "n_seconds": 30,
        "n_vertices": 20484
      },
      ...
    }
    """
    with open(json_path) as f:
        data = json.load(f)

    # All ads in this file share the same run_id
    run_id = list(data.values())[0]["run_id"]
    engine = get_engine()

    roi_rows    = []   # will insert into raw_roi_scores
    region_rows = []   # will insert into top_regions

    for ad_name, ad_data in data.items():
        n_seconds  = ad_data.get("n_seconds")
        n_vertices = ad_data.get("n_vertices")
        g          = ad_data.get("global", {})

        # One row per ROI group per ad
        for roi_group, score in ad_data["roi_scores"].items():
            if score is None:
                continue
            roi_rows.append({
                "run_id":      run_id,
                "ad_name":     ad_name,
                "roi_group":   roi_group,
                "score":       score,
                "n_seconds":   n_seconds,
                "n_vertices":  n_vertices,
                "global_mean": g.get("mean"),
                "global_peak": g.get("peak"),
                "global_p95":  g.get("p95"),
            })

        # Top regions (ranked)
        for rank, region_name in enumerate(ad_data.get("top_10_rois", []), start=1):
            region_rows.append({
                "run_id":      run_id,
                "ad_name":     ad_name,
                "rank":        rank,
                "region_name": region_name,
            })

    # Bulk insert using pandas .to_sql()
    # if_exists="append" adds to existing rows — "replace" would drop the table
    if roi_rows:
        pd.DataFrame(roi_rows).to_sql(
            "raw_roi_scores", engine, if_exists="append", index=False
        )
    if region_rows:
        pd.DataFrame(region_rows).to_sql(
            "top_regions", engine, if_exists="append", index=False
        )

    # Log the scoring run
    n_ads = len(data)
    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO scoring_runs (run_id, n_ads_scored, notes)
            VALUES (:run_id, :n_ads, :notes)
            ON CONFLICT (run_id) DO NOTHING
        """), {"run_id": run_id, "n_ads": n_ads, "notes": f"Loaded from {Path(json_path).name}"})
        conn.commit()

    return run_id


# ── Query helpers (called by main.py) ─────────────────────────────────────────

def get_latest_run_id() -> str | None:
    """Return the most recent run_id from the audit log."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT run_id FROM scoring_runs ORDER BY created_at DESC LIMIT 1"
        ))
        row = result.fetchone()
        return row[0] if row else None


def get_roi_scores(run_id: str) -> pd.DataFrame:
    """
    Load all ROI scores for a given run as a wide DataFrame.
    Columns: ad_name, visual, motion, auditory, language, memory, attention, emotion, decision
    This is the shape the dashboard charts expect.
    """
    engine = get_engine()
    df = pd.read_sql("""
        SELECT DISTINCT ON (ad_name, roi_group) ad_name, roi_group, score
        FROM raw_roi_scores
        WHERE run_id = %(run_id)s
        ORDER BY ad_name, roi_group, loaded_at DESC
    """, engine, params={"run_id": run_id})

    # Pivot: rows=ads, columns=roi_groups
    return df.pivot(index="ad_name", columns="roi_group", values="score").reset_index()


def get_top_regions(run_id: str) -> pd.DataFrame:
    """Load top brain regions per ad for the deep-dive view."""
    engine = get_engine()
    return pd.read_sql("""
        SELECT ad_name, rank, region_name
        FROM top_regions
        WHERE run_id = %(run_id)s
        ORDER BY ad_name, rank
    """, engine, params={"run_id": run_id})


def get_all_run_ids() -> list[str]:
    """List all run IDs for the run selector in the dashboard."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT run_id FROM scoring_runs ORDER BY created_at DESC"
        ))
        return [row[0] for row in result.fetchall()]
