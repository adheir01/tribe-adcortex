-- =============================================================================
-- stg_roi_scores.sql — Staging model
-- =============================================================================
--
-- PURPOSE
-- -------
-- Staging models are the "cleaning layer" in dbt. They sit directly on top
-- of the raw source tables (populated by db.py) and apply:
--   1. Column renaming / type casting
--   2. NULL handling
--   3. Basic validation filters
--
-- They are materialised as VIEWS — meaning every time you query stg_roi_scores,
-- dbt runs this SQL live against raw_roi_scores. No data duplication.
--
-- WHY STAGING?
-- ------------
-- The raw table has one row per (run_id, ad_name, roi_group).
-- That's the right storage shape (normalised), but it's awkward to query.
-- Staging adds cleanliness; the mart layer adds business logic.
-- =============================================================================

with source as (

    select
        id,
        run_id,
        ad_name,
        roi_group,
        score,
        n_seconds,
        n_vertices,
        global_mean,
        global_peak,
        global_p95,
        loaded_at
    from raw_roi_scores
    where score is not null      -- exclude ROI groups that failed to resolve in the atlas

),

renamed as (

    select
        id                              as score_id,
        run_id,
        ad_name,

        -- Standardise ad names: lowercase, strip whitespace
        lower(trim(ad_name))            as ad_name_clean,

        roi_group,
        score                           as roi_activation,    -- mean predicted fMRI activation

        n_seconds                       as ad_duration_secs,
        n_vertices,
        global_mean                     as whole_brain_mean,
        global_peak                     as whole_brain_peak,
        global_p95                      as whole_brain_p95,
        loaded_at

    from source

)

select * from renamed
