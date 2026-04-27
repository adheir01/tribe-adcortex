-- =============================================================================
-- Project 04 — TRIBE v2 Neural Engagement Scorer
-- Database initialisation script
-- Runs automatically when PostgreSQL container starts for the first time
-- =============================================================================

-- ── Raw ROI scores table ─────────────────────────────────────────────────────
-- This is the source-of-truth table. Every row = one ROI group score for one ad.
-- Populated by app/db.py after you drop roi_scores.json into results/

CREATE TABLE IF NOT EXISTS raw_roi_scores (
    id              SERIAL PRIMARY KEY,
    run_id          TEXT        NOT NULL,   -- timestamp-based batch ID, e.g. "2026-04-25T14:30"
    ad_name         TEXT        NOT NULL,   -- e.g. "ad_a", "ad_b"
    roi_group       TEXT        NOT NULL,   -- e.g. "memory", "attention", "visual"
    score           FLOAT       NOT NULL,   -- mean fMRI activation across ROI vertices and time
    n_seconds       INT,                    -- duration of the ad in seconds
    n_vertices      INT,                    -- number of cortical vertices (always 20484 for fsaverage5)
    global_mean     FLOAT,                  -- whole-brain mean activation
    global_peak     FLOAT,                  -- whole-brain peak activation
    global_p95      FLOAT,                  -- 95th percentile — useful for outlier detection
    loaded_at       TIMESTAMPTZ DEFAULT NOW()
);

-- ── Top regions table ────────────────────────────────────────────────────────
-- Stores the top-10 HCP brain region names per ad, for the "brain spotlight" section

CREATE TABLE IF NOT EXISTS top_regions (
    id          SERIAL PRIMARY KEY,
    run_id      TEXT    NOT NULL,
    ad_name     TEXT    NOT NULL,
    rank        INT     NOT NULL,   -- 1 = highest activation
    region_name TEXT    NOT NULL,   -- HCP MMP label, e.g. "V1", "A1", "MT"
    loaded_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ── Scoring audit log ────────────────────────────────────────────────────────
-- One row per full scoring run — tracks when inference happened, budget used, etc.
-- Standard audit trail pattern: always know when data was produced and at what cost.

CREATE TABLE IF NOT EXISTS scoring_runs (
    id              SERIAL PRIMARY KEY,
    run_id          TEXT        NOT NULL UNIQUE,
    n_ads_scored    INT,
    pod_type        TEXT,           -- e.g. "RunPod A100 PCIe 40GB"
    inference_mins  FLOAT,          -- how long inference took
    estimated_cost  FLOAT,          -- in USD
    notes           TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ── Indexes for dashboard query performance ───────────────────────────────────
CREATE INDEX IF NOT EXISTS idx_roi_scores_run_ad ON raw_roi_scores(run_id, ad_name);
CREATE INDEX IF NOT EXISTS idx_top_regions_run_ad ON top_regions(run_id, ad_name);

-- ── ROI time series table ─────────────────────────────────────────────────────
-- Stores per-second activation per ROI group per ad per run.
-- This is the time series data that enables timeline charts and derived metrics.
-- One row per (run_id, ad_name, roi_group, second_index).

CREATE TABLE IF NOT EXISTS roi_timeseries (
    id           SERIAL PRIMARY KEY,
    run_id       TEXT    NOT NULL,
    ad_name      TEXT    NOT NULL,
    roi_group    TEXT    NOT NULL,
    second_index INT     NOT NULL,   -- 0-based second within the ad
    activation   FLOAT   NOT NULL,   -- mean predicted fMRI activation at this second
    loaded_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_timeseries_run_ad
    ON roi_timeseries(run_id, ad_name);

-- ── Derived metrics table ─────────────────────────────────────────────────────
-- Stores computed metrics per ad per run.
-- These are calculated from the time series in run_tribe.py.

CREATE TABLE IF NOT EXISTS derived_metrics (
    id                    SERIAL PRIMARY KEY,
    run_id                TEXT    NOT NULL,
    ad_name               TEXT    NOT NULL,
    hook_strength         FLOAT,   -- avg(attention+motion+emotion) in first 3s
    mid_retention         FLOAT,   -- avg(attention) in seconds 3-10
    peak_emotion_second   INT,     -- second index of highest emotion activation
    peak_emotion_value    FLOAT,   -- value at peak emotion second
    attention_decay_rate  FLOAT,   -- linear slope of attention over time
    attention_pattern     TEXT,    -- hook_and_drop / slow_build / sustained
    loaded_at             TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(run_id, ad_name)
);
