"""
=============================================================================
main.py — Streamlit Dashboard Entry Point
=============================================================================

PURPOSE
-------
The user-facing application. Orchestrates DB queries, chart rendering,
and narrative explanations into a single-page dashboard.

STRUCTURE
---------
1. Sidebar — load JSON results, select run, show audit info
2. Hero section — winner declaration + composite gauges
3. Radar chart — neural signature comparison across all ads
4. Heatmap — ROI × ad activation matrix
5. ROI deep dive — per-ROI ranked bar charts with explanations
6. Brain spotlight — top HCP regions per ad
7. Methodology note — transparency about what the model is and isn't
"""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

import db
import charts
from roi_labels import ROI_META, ROI_ORDER, HERO_ROIS

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title = "Neural Ad Scorer | TRIBE v2",
    page_icon  = "🧠",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
# Dark neuro-scientific aesthetic — deep space background, cyan accents
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #070B14;
    color: #C8D6E5;
}

h1, h2, h3 {
    font-family: 'Space Mono', monospace;
    letter-spacing: -0.02em;
}

.main-header {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B2838 100%);
    border: 1px solid rgba(67, 97, 238, 0.3);
    border-radius: 12px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
}

.winner-card {
    background: linear-gradient(135deg, rgba(6, 214, 160, 0.1) 0%, rgba(6, 214, 160, 0.05) 100%);
    border: 1px solid rgba(6, 214, 160, 0.4);
    border-radius: 10px;
    padding: 1.5rem;
    text-align: center;
}

.winner-name {
    font-family: 'Space Mono', monospace;
    font-size: 2.5rem;
    font-weight: 700;
    color: #06D6A0;
}

.metric-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 1rem 1.2rem;
}

.roi-section {
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.06);
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}

.section-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: #4361EE;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 0.3rem;
}

.explain-text {
    font-size: 0.85rem;
    color: #8899AA;
    line-height: 1.6;
}

.stButton > button {
    background: rgba(67, 97, 238, 0.15);
    border: 1px solid rgba(67, 97, 238, 0.4);
    color: #C8D6E5;
    border-radius: 6px;
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
}

.stButton > button:hover {
    background: rgba(67, 97, 238, 0.3);
    border-color: #4361EE;
}

[data-testid="stMetricValue"] {
    font-family: 'Space Mono', monospace;
    color: #4361EE;
}

.methodology-box {
    background: rgba(255, 183, 3, 0.05);
    border: 1px solid rgba(255, 183, 3, 0.2);
    border-radius: 8px;
    padding: 1rem 1.5rem;
    font-size: 0.82rem;
    color: #AAB8C2;
    line-height: 1.7;
}
</style>
""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown('<div class="section-label">Data Source</div>', unsafe_allow_html=True)

    # Option 1: load from JSON file in results/
    results_dir  = Path("/app/results")
    json_files   = sorted(results_dir.glob("roi_scores*.json"), reverse=True)

    if json_files:
        selected_file = st.selectbox(
            "Results file",
            options  = json_files,
            format_func = lambda p: p.name,
        )
        if st.button("Load into database"):
            with st.spinner("Loading..."):
                run_id = db.load_results_from_json(selected_file)
                st.success(f"Loaded run: {run_id}")
                st.session_state["active_run_id"] = run_id

    st.divider()

    # Option 2: select from already-loaded runs
    st.markdown('<div class="section-label">Scoring Run</div>', unsafe_allow_html=True)
    all_runs = db.get_all_run_ids()

    if all_runs:
        active_run = st.selectbox("Select run", options=all_runs)
        st.session_state["active_run_id"] = active_run
    else:
        st.info("No runs loaded yet. Drop roi_scores.json into results/ and click Load.")

    st.divider()
    st.markdown('<div class="section-label">About</div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="explain-text">
    TRIBE v2 is Meta FAIR's open-source brain encoding model.
    It predicts fMRI activation from video, audio, and text stimuli.
    <br><br>
    Scores are <strong>predicted neural activations</strong>, not
    actual brain measurements. Higher = stronger predicted engagement
    in that brain region.
    <br><br>
    Model: <code>facebook/tribev2</code><br>
    License: CC BY-NC 4.0
    </div>
    """, unsafe_allow_html=True)


# ── Main dashboard ────────────────────────────────────────────────────────────

run_id = st.session_state.get("active_run_id")

if not run_id:
    # Empty state — guide the user
    st.markdown("""
    <div class="main-header">
        <h1>🧠 Neural Ad Engagement Scorer</h1>
        <p style="color:#8899AA; margin:0; font-size:1.1rem;">
            TRIBE v2 · Predicted fMRI · Ad Creative Comparison
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.info("← Load your roi_scores.json from the sidebar to begin.")
    st.stop()

# Load data
df_wide    = db.get_roi_scores(run_id)
df_regions = db.get_top_regions(run_id)

if df_wide.empty:
    st.error(f"No ROI score data found for run {run_id}.")
    st.stop()

ad_names = df_wide["ad_name"].tolist()

# ── Header ─────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="main-header">
    <h1>🧠 Neural Ad Engagement Scorer</h1>
    <p style="color:#8899AA; margin:0.5rem 0 0 0; font-size:0.95rem;">
        Run: <code>{run_id}</code> &nbsp;·&nbsp; {len(ad_names)} ad variants &nbsp;·&nbsp;
        TRIBE v2 · fsaverage5 cortical surface · 20,484 vertices
    </p>
</div>
""", unsafe_allow_html=True)


# ── Section 1: Winner + Composite Gauges ──────────────────────────────────
st.markdown("### Composite Neural Engagement Score")
st.markdown(
    '<div class="explain-text" style="margin-bottom:1rem">'
    'Weighted composite across 8 brain ROI groups. '
    'Memory (30%) + Attention (25%) + Emotion (20%) + Decision (15%) + sensory (10%). '
    'Normalised to 0–100 across the scored set.</div>',
    unsafe_allow_html=True
)

gauge_fig, norm_scores = charts.make_winner_gauge(df_wide)
st.plotly_chart(gauge_fig, use_container_width=True)

# Winner card
winner = max(norm_scores, key=norm_scores.get)
winner_score = norm_scores[winner]
st.markdown(f"""
<div class="winner-card">
    <div class="section-label">Recommended Creative</div>
    <div class="winner-name">{winner.replace('_', ' ').upper()}</div>
    <div style="color:#8899AA; margin-top:0.5rem; font-size:0.9rem;">
        Neural Engagement Score: <strong style="color:#06D6A0">{winner_score:.0f}/100</strong>
        &nbsp;·&nbsp; Predicted strongest memory encoding and attentional activation
    </div>
</div>
""", unsafe_allow_html=True)

st.divider()


# ── Section 2: Radar chart ─────────────────────────────────────────────────
st.markdown("### Neural Signature — All Ad Variants")
st.markdown(
    '<div class="explain-text" style="margin-bottom:1rem">'
    'Each polygon is one ad variant. The shape reveals its neural profile. '
    'A memory+attention dominant ad looks different from a visual+emotion dominant one. '
    'Larger overall area = stronger whole-brain engagement.</div>',
    unsafe_allow_html=True
)

radar_fig = charts.make_radar_chart(df_wide)
st.plotly_chart(radar_fig, use_container_width=True)

st.divider()


# ── Section 3: Heatmap ─────────────────────────────────────────────────────
st.markdown("### Activation Heatmap — Ad × Brain Region")
st.markdown(
    '<div class="explain-text" style="margin-bottom:1rem">'
    'Z-score normalised per ROI column. Brighter = stronger predicted activation '
    'relative to the other ads in this set. '
    'Reveals which ad dominates which region.</div>',
    unsafe_allow_html=True
)

heatmap_fig = charts.make_comparison_heatmap(df_wide)
st.plotly_chart(heatmap_fig, use_container_width=True)

st.divider()


# ── Section 4: ROI Deep Dive ───────────────────────────────────────────────
st.markdown("### ROI Deep Dive")
st.markdown(
    '<div class="explain-text" style="margin-bottom:1.5rem">'
    'Select a brain region group to see ranked ad performance and understand '
    'what that region means for advertising effectiveness.</div>',
    unsafe_allow_html=True
)

selected_roi = st.selectbox(
    "Brain region",
    options    = [r for r in ROI_ORDER if r in df_wide.columns],
    format_func= lambda r: f"{ROI_META[r]['icon']}  {ROI_META[r]['label']} — {ROI_META[r]['ad_angle']}",
)

col_chart, col_explain = st.columns([1, 1])

with col_chart:
    bar_fig = charts.make_roi_bar_chart(df_wide, selected_roi)
    st.plotly_chart(bar_fig, use_container_width=True)

with col_explain:
    meta = ROI_META[selected_roi]
    st.markdown(f"""
    <div class="roi-section">
        <div class="section-label">Neuroscience</div>
        <p class="explain-text">{meta['explain']}</p>
        <br>
        <div class="section-label">For Advertisers</div>
        <p class="explain-text">{meta['marketing']}</p>
        <br>
        <div class="section-label">HCP MMP Regions</div>
        <p class="explain-text" style="font-family: monospace">
            {' · '.join(meta['hcp_regions'])}
        </p>
        <div class="explain-text">Brain area: {meta['brain_area']}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()


# ── Section 5: Brain Spotlight ─────────────────────────────────────────────
if not df_regions.empty:
    st.markdown("### Brain Spotlight — Top Activated HCP Regions")
    st.markdown(
        '<div class="explain-text" style="margin-bottom:1rem">'
        'The 10 highest-activated HCP MMP parcels for each ad. '
        'These are named cortical regions from the Human Connectome Project atlas '
        '(~360 regions total). This is the neuroscience deep-dive view.</div>',
        unsafe_allow_html=True
    )

    cols = st.columns(len(ad_names))
    for i, ad_name in enumerate(ad_names):
        with cols[i]:
            st.markdown(f"**{ad_name.replace('_', ' ').upper()}**")
            region_fig = charts.make_top_regions_chart(df_regions, ad_name)
            st.plotly_chart(region_fig, use_container_width=True)

    st.divider()


# ── Section 6: Methodology note ───────────────────────────────────────────
st.markdown("### Methodology & Limitations")
st.markdown("""
<div class="methodology-box">
<strong>What TRIBE v2 predicts</strong><br>
TRIBE v2 was trained on fMRI data from multiple public neuroscience datasets
(Algonauts 2025, Lahner 2024, Lebel 2023, and others). Given any video, audio,
or text stimulus, it predicts the cortical fMRI response an average subject would
show. Predictions live on the fsaverage5 surface (~20,484 vertices), covering the
entire cortex at ~4mm resolution.
<br><br>
<strong>What these scores mean</strong><br>
Scores represent mean predicted fMRI activation (BOLD signal proxy) across
the vertices in each ROI group and across time. They are meaningful in
<em>relative comparison</em> across ad variants scored in the same run.
Absolute values should not be compared across different experiments.
<br><br>
<strong>Limitations</strong><br>
(1) TRIBE v2 predicts responses for an "average subject" — individual differences
in neural response are not captured. (2) The model was trained on naturalistic film
and speech content, not commercial advertisements specifically. (3) Predicted fMRI
activation is a proxy for neural engagement, not a direct measure of purchase intent.
(4) This tool is intended for portfolio demonstration and research exploration only.
Commercial use is prohibited under the CC BY-NC 4.0 license.
<br><br>
<strong>Model</strong>: <code>facebook/tribev2</code> &nbsp;·&nbsp;
<strong>License</strong>: CC BY-NC 4.0 &nbsp;·&nbsp;
<strong>Paper</strong>: d'Ascoli et al. 2026
</div>
""", unsafe_allow_html=True)
