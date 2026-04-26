-- =============================================================================
-- mart_ad_comparison.sql — Mart model
-- =============================================================================
--
-- PURPOSE
-- -------
-- The mart layer is where business logic lives. This model takes the clean
-- staging data and produces the analysis-ready table the dashboard actually
-- queries for comparisons.
--
-- It answers: "For each ROI group, how does each ad compare to the baseline
-- (the average across all ads in the run)?"
--
-- OUTPUT SHAPE
-- ------------
-- One row per (run_id, ad_name, roi_group) with:
--   - raw activation score
--   - z-score within the run (how many std devs above/below average)
--   - percentage lift vs. run average
--   - rank within the run for that ROI group (1 = strongest)
--   - composite weighted score
--   - overall rank across all ROIs
--
-- MATERIALISED AS TABLE
-- ----------------------
-- Unlike staging views, mart models are pre-computed tables.
-- This makes dashboard queries fast — no recalculation on every page load.
-- Run `dbt run --models mart_ad_comparison --profiles-dir .` to refresh.
-- =============================================================================

with staging as (

    select * from {{ ref('stg_roi_scores') }}

),

-- Step 1: compute per-ROI statistics across all ads in the same run
-- This gives us the baseline to compare each ad against
roi_stats as (

    select
        run_id,
        roi_group,
        avg(roi_activation)    as roi_mean,
        stddev(roi_activation) as roi_stddev,
        min(roi_activation)    as roi_min,
        max(roi_activation)    as roi_max,
        count(distinct ad_name) as n_ads
    from staging
    group by run_id, roi_group

),

-- Step 2: join each ad's score back to the run-level stats
-- and compute normalised metrics
enriched as (

    select
        s.run_id,
        s.ad_name,
        s.ad_name_clean,
        s.roi_group,
        s.roi_activation,
        s.ad_duration_secs,
        s.whole_brain_mean,

        -- Z-score: how many standard deviations above/below the run average
        -- Formula: (value - mean) / stddev
        -- Interpretation: +1.5 means this ad activates this region 1.5 std devs
        -- more than the average ad in this set
        case
            when r.roi_stddev > 0
            then (s.roi_activation - r.roi_mean) / r.roi_stddev
            else 0
        end                                         as roi_zscore,

        -- Percentage lift vs. run average
        -- e.g. 0.15 means 15% stronger activation than the average ad
        case
            when r.roi_mean > 0
            then (s.roi_activation - r.roi_mean) / r.roi_mean
            else 0
        end                                         as roi_pct_lift,

        -- Rank within this run for this ROI group (1 = strongest activation)
        rank() over (
            partition by s.run_id, s.roi_group
            order by s.roi_activation desc
        )                                           as roi_rank,

        r.roi_mean                                  as run_roi_mean,
        r.roi_stddev                                as run_roi_stddev,
        r.n_ads

    from staging s
    left join roi_stats r
        on s.run_id = r.run_id
        and s.roi_group = r.roi_group

),

-- Step 3: compute the composite weighted score per ad per run
-- Weights match the gauge chart in charts.py — single source of truth is here
-- dbt ref weights so if you change them, one dbt run refreshes everything
composite as (

    select
        run_id,
        ad_name,

        -- Weighted sum across all ROI groups
        -- These weights are based on neuromarketing research linking
        -- brain regions to advertising recall and purchase intent outcomes
        sum(
            roi_activation * case roi_group
                when 'memory'    then 0.30
                when 'attention' then 0.25
                when 'emotion'   then 0.20
                when 'decision'  then 0.15
                when 'visual'    then 0.025
                when 'motion'    then 0.025
                when 'auditory'  then 0.025
                when 'language'  then 0.025
                else 0
            end
        )                                           as composite_score

    from staging
    group by run_id, ad_name

),

-- Step 4: rank ads by composite score within each run
composite_ranked as (

    select
        run_id,
        ad_name,
        composite_score,

        -- Overall rank: 1 = winner
        rank() over (
            partition by run_id
            order by composite_score desc
        )                                           as composite_rank,

        -- Min-max normalise to 0-1 range for interpretability
        (composite_score - min(composite_score) over (partition by run_id))
        /
        nullif(
            max(composite_score) over (partition by run_id)
            - min(composite_score) over (partition by run_id),
            0
        )                                           as composite_score_normalised

    from composite

)

-- Final join: bring everything together
select
    e.run_id,
    e.ad_name,
    e.ad_name_clean,
    e.roi_group,
    e.roi_activation,
    e.roi_zscore,
    e.roi_pct_lift,
    e.roi_rank,
    e.run_roi_mean,
    e.run_roi_stddev,
    e.ad_duration_secs,
    e.whole_brain_mean,
    e.n_ads,
    c.composite_score,
    c.composite_score_normalised,
    c.composite_rank,

    -- Convenience flag: is this the winning ad overall?
    case when c.composite_rank = 1 then true else false end  as is_winner

from enriched e
left join composite_ranked c
    on e.run_id = c.run_id
    and e.ad_name = c.ad_name

order by
    e.run_id,
    c.composite_rank,
    e.ad_name,
    e.roi_group
