"""
=============================================================================
db.py — Database connection and data loading
=============================================================================

PURPOSE
-------
1. get_connection() / get_engine() — database access for all modules
2. load_results_from_json() — parse roi_scores.json → PostgreSQL
3. Campaign helpers — create, list, assign campaigns to runs
4. Query helpers — called by dashboard pages

CAMPAIGNS
---------
A campaign groups scoring runs together. Example:
  Campaign: "Q2 Food Study"
    Run: 2026-04-25T19:52 (chocolate vs salad vs social)
    Run: 2026-04-26T10:15 (revised versions)

Runs without a campaign are shown as "Uncategorised".
Backward compatible — existing runs stay as-is.
"""

import json
import os
from pathlib import Path

import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text


def get_database_url() -> str:
    return os.environ.get(
        "DATABASE_URL",
        "postgresql://tribe:tribe_scorer_dev@localhost:5435/tribe_scorer"
    )

def get_engine():
    return create_engine(get_database_url())

def get_connection():
    return psycopg2.connect(get_database_url())


def ensure_schema():
    """
    Ensures campaign tables exist. Safe to run every startup.
    Handles databases created before campaigns were added.
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id          SERIAL PRIMARY KEY,
                name        TEXT        NOT NULL UNIQUE,
                description TEXT,
                created_at  TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            ALTER TABLE scoring_runs
                ADD COLUMN IF NOT EXISTS campaign_id INT REFERENCES campaigns(id)
        """))
        conn.commit()


def load_results_from_json(json_path, campaign_id=None):
    """
    Parse roi_scores.json and load into PostgreSQL.
    Optionally assigns the run to a campaign.
    Returns the run_id string.
    """
    with open(json_path) as f:
        data = json.load(f)

    run_id = list(data.values())[0]["run_id"]
    engine = get_engine()

    roi_rows    = []
    region_rows = []

    for ad_name, ad_data in data.items():
        n_seconds  = ad_data.get("n_seconds") or ad_data.get("n_timesteps")
        n_vertices = ad_data.get("n_vertices")
        g          = ad_data.get("global", {})

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

        for rank, region_name in enumerate(ad_data.get("top_10_rois", []), start=1):
            region_rows.append({
                "run_id":      run_id,
                "ad_name":     ad_name,
                "rank":        rank,
                "region_name": region_name,
            })

    if roi_rows:
        pd.DataFrame(roi_rows).to_sql(
            "raw_roi_scores", engine, if_exists="append", index=False
        )
    if region_rows:
        pd.DataFrame(region_rows).to_sql(
            "top_regions", engine, if_exists="append", index=False
        )

    with engine.connect() as conn:
        conn.execute(text("""
            INSERT INTO scoring_runs (run_id, n_ads_scored, campaign_id, notes)
            VALUES (:run_id, :n_ads, :campaign_id, :notes)
            ON CONFLICT (run_id) DO UPDATE SET
                campaign_id = COALESCE(EXCLUDED.campaign_id, scoring_runs.campaign_id)
        """), {
            "run_id":      run_id,
            "n_ads":       len(data),
            "campaign_id": campaign_id,
            "notes":       f"Loaded from {Path(json_path).name}",
        })
        conn.commit()

    return run_id


def create_campaign(name, description=""):
    """Create a new campaign. Returns the new campaign id."""
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text("""
            INSERT INTO campaigns (name, description)
            VALUES (:name, :description)
            ON CONFLICT (name) DO UPDATE SET description = EXCLUDED.description
            RETURNING id
        """), {"name": name, "description": description})
        campaign_id = result.fetchone()[0]
        conn.commit()
    return campaign_id


def get_all_campaigns():
    """
    Returns all campaigns plus a synthetic Uncategorised row
    for runs that have no campaign assigned.
    """
    engine = get_engine()

    campaigns = pd.read_sql("""
        SELECT id, name, description, created_at
        FROM campaigns
        ORDER BY created_at DESC
    """, engine)

    uncategorised_count = pd.read_sql("""
        SELECT COUNT(*) as n FROM scoring_runs WHERE campaign_id IS NULL
    """, engine)

    if uncategorised_count["n"].iloc[0] > 0:
        uncategorised = pd.DataFrame([{
            "id":          None,
            "name":        "Uncategorised",
            "description": "Runs with no campaign assigned",
            "created_at":  None,
        }])
        campaigns = pd.concat([campaigns, uncategorised], ignore_index=True)

    return campaigns


def assign_run_to_campaign(run_id, campaign_id):
    """Assign or remove a run from a campaign."""
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            UPDATE scoring_runs SET campaign_id = :campaign_id WHERE run_id = :run_id
        """), {"campaign_id": campaign_id, "run_id": run_id})
        conn.commit()


def get_runs_for_campaign(campaign_id):
    """
    Returns run_ids for a given campaign.
    campaign_id=None returns uncategorised runs.
    """
    if campaign_id is not None:
        campaign_id = int(campaign_id)
    engine = get_engine()
    if campaign_id is None:
        result = pd.read_sql("""
            SELECT run_id FROM scoring_runs
            WHERE campaign_id IS NULL
            ORDER BY created_at DESC
        """, engine)
    else:
        result = pd.read_sql("""
            SELECT run_id FROM scoring_runs
            WHERE campaign_id = %(campaign_id)s
            ORDER BY created_at DESC
        """, engine, params={"campaign_id": campaign_id})
    return result["run_id"].tolist()


def get_latest_run_id():
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT run_id FROM scoring_runs ORDER BY created_at DESC LIMIT 1"
        ))
        row = result.fetchone()
        return row[0] if row else None


def get_roi_scores(run_id):
    engine = get_engine()
    df = pd.read_sql("""
        SELECT DISTINCT ON (ad_name, roi_group) ad_name, roi_group, score
        FROM raw_roi_scores
        WHERE run_id = %(run_id)s
        ORDER BY ad_name, roi_group, loaded_at DESC
    """, engine, params={"run_id": run_id})
    if df.empty:
        return df
    return df.pivot(index="ad_name", columns="roi_group", values="score").reset_index()


def get_top_regions(run_id):
    engine = get_engine()
    return pd.read_sql("""
        SELECT ad_name, rank, region_name
        FROM top_regions
        WHERE run_id = %(run_id)s
        ORDER BY ad_name, rank
    """, engine, params={"run_id": run_id})


def get_all_run_ids():
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(text(
            "SELECT run_id FROM scoring_runs ORDER BY created_at DESC"
        ))
        return [row[0] for row in result.fetchall()]


def get_ad_labels():
    """
    Returns friendly labels from creatives/labels.json if it exists.
    Falls back to empty dict — callers use raw ad_name as fallback.
    """
    labels_file = Path("/app/creatives/labels.json")
    if labels_file.exists():
        try:
            return json.loads(labels_file.read_text())
        except Exception:
            pass
    return {}


def load_timeseries_from_json(json_path, run_id):
    """
    Load roi_timeseries and derived_metrics from roi_scores.json into PostgreSQL.
    Called after load_results_from_json() — same JSON file, different tables.
    """
    with open(json_path) as f:
        data = json.load(f)

    engine      = get_engine()
    ts_rows     = []
    derived_rows = []

    for ad_name, ad_data in data.items():
        # Time series
        timeseries = ad_data.get("roi_timeseries", {})
        for roi_group, values in timeseries.items():
            for second_index, activation in enumerate(values):
                ts_rows.append({
                    "run_id":       run_id,
                    "ad_name":      ad_name,
                    "roi_group":    roi_group,
                    "second_index": second_index,
                    "activation":   activation,
                })

        # Derived metrics
        derived = ad_data.get("derived", {})
        if derived:
            derived_rows.append({
                "run_id":               run_id,
                "ad_name":              ad_name,
                "hook_strength":        derived.get("hook_strength"),
                "mid_retention":        derived.get("mid_retention"),
                "peak_emotion_second":  derived.get("peak_emotion_second"),
                "peak_emotion_value":   derived.get("peak_emotion_value"),
                "attention_decay_rate": derived.get("attention_decay_rate"),
                "attention_pattern":    derived.get("attention_pattern"),
            })

    if ts_rows:
        pd.DataFrame(ts_rows).to_sql(
            "roi_timeseries", engine, if_exists="append", index=False
        )

    if derived_rows:
        df_d = pd.DataFrame(derived_rows)
        # Use upsert to avoid duplicate key errors on reload
        with engine.connect() as conn:
            for _, row in df_d.iterrows():
                conn.execute(text("""
                    INSERT INTO derived_metrics
                        (run_id, ad_name, hook_strength, mid_retention,
                         peak_emotion_second, peak_emotion_value,
                         attention_decay_rate, attention_pattern)
                    VALUES
                        (:run_id, :ad_name, :hook_strength, :mid_retention,
                         :peak_emotion_second, :peak_emotion_value,
                         :attention_decay_rate, :attention_pattern)
                    ON CONFLICT (run_id, ad_name) DO NOTHING
                """), row.to_dict())
            conn.commit()


def get_timeseries(run_id, roi_groups=None):
    """
    Load per-second activation data for a run.
    Returns DataFrame with columns: ad_name, roi_group, second_index, activation
    Optionally filter to specific roi_groups list.
    """
    engine = get_engine()
    if roi_groups:
        placeholders = ", ".join([f"'{r}'" for r in roi_groups])
        query = f"""
            SELECT ad_name, roi_group, second_index, activation
            FROM roi_timeseries
            WHERE run_id = %(run_id)s
              AND roi_group IN ({placeholders})
            ORDER BY ad_name, roi_group, second_index
        """
    else:
        query = """
            SELECT ad_name, roi_group, second_index, activation
            FROM roi_timeseries
            WHERE run_id = %(run_id)s
            ORDER BY ad_name, roi_group, second_index
        """
    return pd.read_sql(query, engine, params={"run_id": run_id})


def get_derived_metrics(run_id):
    """
    Load derived metrics for all ads in a run.
    Returns DataFrame with one row per ad.
    """
    engine = get_engine()
    return pd.read_sql("""
        SELECT ad_name, hook_strength, mid_retention,
               peak_emotion_second, peak_emotion_value,
               attention_decay_rate, attention_pattern
        FROM derived_metrics
        WHERE run_id = %(run_id)s
        ORDER BY ad_name
    """, engine, params={"run_id": run_id})


def ensure_timeseries_schema():
    """
    Create timeseries and derived_metrics tables if they don't exist.
    Safe to run on every startup.
    """
    engine = get_engine()
    with engine.connect() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS roi_timeseries (
                id           SERIAL PRIMARY KEY,
                run_id       TEXT    NOT NULL,
                ad_name      TEXT    NOT NULL,
                roi_group    TEXT    NOT NULL,
                second_index INT     NOT NULL,
                activation   FLOAT   NOT NULL,
                loaded_at    TIMESTAMPTZ DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_timeseries_run_ad
                ON roi_timeseries(run_id, ad_name)
        """))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS derived_metrics (
                id                    SERIAL PRIMARY KEY,
                run_id                TEXT    NOT NULL,
                ad_name               TEXT    NOT NULL,
                hook_strength         FLOAT,
                mid_retention         FLOAT,
                peak_emotion_second   INT,
                peak_emotion_value    FLOAT,
                attention_decay_rate  FLOAT,
                attention_pattern     TEXT,
                loaded_at             TIMESTAMPTZ DEFAULT NOW(),
                UNIQUE(run_id, ad_name)
            )
        """))
        conn.commit()


def get_confidence_indicators(run_id):
    """
    Compute a confidence tier for each ad's pattern classification.

    Confidence is derived from two signals already in the database:

    1. Signal strength — absolute mean activation across ROI groups.
       Very low absolute values mean the differences between ads are tiny
       and the pattern classification is based on weak signal.

    2. Pattern clarity — how steep the attention decay slope is.
       A near-zero slope that technically classifies as hook_and_drop
       is a borderline call. A steep slope is a clear classification.

    Tiers:
        High     — strong signal AND clear slope
        Moderate — one of the two is weak
        Low      — both are weak, or signal is near-zero

    Returns dict: {ad_name: {"tier": str, "reason": str}}
    """
    engine = get_engine()

    # Get mean absolute activation per ad (signal strength proxy)
    signal_df = pd.read_sql("""
        SELECT ad_name, AVG(ABS(score)) as mean_abs_activation
        FROM raw_roi_scores
        WHERE run_id = %(run_id)s
        GROUP BY ad_name
    """, engine, params={"run_id": run_id})

    # Get attention decay rate per ad (pattern clarity proxy)
    derived_df = get_derived_metrics(run_id)

    result = {}

    for _, row in signal_df.iterrows():
        ad_name    = row["ad_name"]
        signal_str = float(row["mean_abs_activation"])

        decay_rate = None
        pattern    = None
        if not derived_df.empty and ad_name in derived_df["ad_name"].values:
            ad_derived = derived_df[derived_df["ad_name"] == ad_name].iloc[0]
            decay_rate = ad_derived.get("attention_decay_rate")
            pattern    = ad_derived.get("attention_pattern")

        # Score signal strength
        # Thresholds based on observed ranges: >0.04 strong, 0.01-0.04 moderate, <0.01 weak
        if signal_str > 0.04:
            signal_tier = "strong"
        elif signal_str > 0.01:
            signal_tier = "moderate"
        else:
            signal_tier = "weak"

        # Score pattern clarity — how far from zero is the slope?
        if decay_rate is not None:
            slope_magnitude = abs(float(decay_rate))
            if slope_magnitude > 0.002:
                clarity_tier = "clear"
            elif slope_magnitude > 0.0005:
                clarity_tier = "moderate"
            else:
                clarity_tier = "borderline"
        else:
            clarity_tier = "borderline"

        # Combine into final tier
        if signal_tier == "strong" and clarity_tier == "clear":
            tier   = "High"
            reason = "Strong signal, clear pattern trajectory"
        elif signal_tier == "weak" and clarity_tier == "borderline":
            tier   = "Low"
            reason = "Weak signal — differences are small, pattern borderline"
        elif signal_tier == "weak":
            tier   = "Low"
            reason = "Low absolute activation — treat pattern with caution"
        elif clarity_tier == "borderline":
            tier   = "Moderate"
            reason = "Pattern slope near zero — classification is approximate"
        else:
            tier   = "Moderate"
            reason = "Moderate signal strength or pattern clarity"

        result[ad_name] = {
            "tier":            tier,
            "reason":          reason,
            "signal_strength": signal_tier,
            "slope_clarity":   clarity_tier,
            "mean_abs":        round(signal_str, 5),
            "decay_rate":      round(float(decay_rate), 6) if decay_rate is not None else None,
        }

    return result
