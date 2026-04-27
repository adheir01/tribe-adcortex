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

# Run schema migration on every startup — safe, uses IF NOT EXISTS
try:
    db.ensure_schema()
except Exception:
    pass
import charts
from roi_labels import ROI_META, ROI_ORDER, HERO_ROIS

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title = "Dashboard | tribe-adcortex",
    page_icon  = "📊",
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
                db.ensure_timeseries_schema()
                db.load_timeseries_from_json(selected_file, run_id)
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


# ── Timeline Charts ───────────────────────────────────────────────────────────
st.markdown("### 📈 Where Your Ad Loses People — Second by Second")
st.markdown(
    '<div class="explain-text" style="margin-bottom:1rem">'
    'Per-second predicted brain activation for attention, emotion, and memory-correlated signals. '
    'This is the primary diagnostic view. The yellow zone marks the hook window (first 3s) — '
    'commonly considered the most critical in short-form feeds. '
    'Look for drop-offs, dead zones, and whether the emotional peak arrives early enough.</div>',
    unsafe_allow_html=True
)

df_ts = db.get_timeseries(run_id, roi_groups=["attention", "emotion", "memory"])

if not df_ts.empty:
    selected_roi_ts = st.multiselect(
        "Signals to display",
        options = ["attention", "emotion", "memory", "visual", "motion", "auditory", "language", "decision"],
        default = ["attention", "emotion", "memory"],
        key     = "ts_roi_select",
    )
    ts_cols = st.columns(len(ad_names))
    ad_labels_ts = db.get_ad_labels()
    for i, ad_ts in enumerate(ad_names):
        with ts_cols[i]:
            label = ad_labels_ts.get(ad_ts, ad_ts.upper())
            st.markdown(f"**{label}**")
            ts_fig = charts.make_timeline_chart(df_ts, ad_ts, selected_roi_ts)
            st.plotly_chart(ts_fig, use_container_width=True)
else:
    st.info("No time series data — re-run inference with the updated run_tribe.py.")

st.divider()


# ── Derived Metrics ───────────────────────────────────────────────────────────
st.markdown("### Derived Engagement Metrics")
st.markdown(
    '<div class="explain-text" style="margin-bottom:1rem">'
    'Computed from the per-second time series. These are proxies — derived from predicted brain signals, '
    'not validated against real engagement or recall outcomes. '
    'Hook strength is a proxy for early attentional engagement (seconds 0–3), '
    'commonly considered critical in short-form feeds. '
    'Attention pattern classifies the trajectory of the attention signal over time.</div>',
    unsafe_allow_html=True
)

st.markdown("""
<div style='display:flex;gap:2rem;flex-wrap:wrap;margin-bottom:1rem;font-size:0.78rem;color:#6B7280'>
    <span><strong style='color:#FFB703'>Hook Strength</strong> — proxy for early scroll-stopping potential</span>
    <span><strong style='color:#06D6A0'>Mid Retention</strong> — proxy for sustained attention after the hook</span>
    <span><strong style='color:#F72585'>Peak Emotion</strong> — time of highest emotion-correlated signal</span>
    <span><strong style='color:#C8D6E5'>Attn Decay</strong> — how quickly attention signal drops (negative = declining)</span>
    <span><strong style='color:#4361EE'>Pattern</strong> — overall attention trajectory classification</span>
</div>
""", unsafe_allow_html=True)

db.ensure_timeseries_schema()
df_derived   = db.get_derived_metrics(run_id)
ad_labels    = db.get_ad_labels()
confidence   = db.get_confidence_indicators(run_id)

if not df_derived.empty:
    derived_fig = charts.make_derived_metrics_table(df_derived, ad_labels)
    st.plotly_chart(derived_fig, use_container_width=True)
    best_hook_idx = df_derived["hook_strength"].idxmax()
    best_hook     = df_derived.loc[best_hook_idx]
    best_label    = ad_labels.get(best_hook["ad_name"], best_hook["ad_name"].upper())
    best_pattern  = best_hook["attention_pattern"] or "N/A"
    st.markdown(
        f'<div style="background:rgba(255,183,3,0.08);border:1px solid rgba(255,183,3,0.3);'
        f'border-radius:8px;padding:1rem 1.5rem;font-size:0.85rem;color:#FCD34D">'
        f'⚡ <strong>Strongest hook:</strong> {best_label} '
        f'— score {best_hook["hook_strength"]:.4f} · pattern: {best_pattern}</div>',
        unsafe_allow_html=True
    )
else:
    st.info("No derived metrics — re-run inference with the updated run_tribe.py to generate time series data.")

st.divider()

# ── Creative Diagnosis ────────────────────────────────────────────────────────
st.markdown("### Creative Diagnosis")
st.markdown(
    '<div class="explain-text" style="margin-bottom:1rem">'
    'Pattern-based diagnostic flags derived from the time series and derived metrics. '
    'These are hypotheses based on predicted signal patterns — not verdicts.</div>',
    unsafe_allow_html=True
)

from roi_labels import PATTERN_META, DIAGNOSTIC_RULES

if not df_derived.empty:
    for _, ad_row in df_derived.iterrows():
        ad_n     = ad_row["ad_name"]
        label    = ad_labels.get(ad_n, ad_n.upper())
        pattern  = ad_row.get("attention_pattern")
        pmeta    = PATTERN_META.get(pattern, {})

        # Build roi scores dict for diagnostic rules
        roi_row  = df_wide[df_wide["ad_name"] == ad_n]
        roi_dict = {}
        if not roi_row.empty:
            for col in roi_row.columns:
                if col != "ad_name":
                    roi_dict[f"{col}_score"] = roi_row[col].values[0]
        roi_dict["hook_strength"]        = ad_row.get("hook_strength")
        roi_dict["peak_emotion_second"]  = ad_row.get("peak_emotion_second")

        conf       = confidence.get(ad_n, {})
        conf_tier  = conf.get('tier', 'Moderate')
        conf_reason = conf.get('reason', '')
        conf_color = {'High': '#06D6A0', 'Moderate': '#FFB703', 'Low': '#F72585'}.get(conf_tier, '#FFB703')
        conf_badge = f'<span style="font-size:0.7rem;background:{conf_color}22;color:{conf_color};'\
                      f'border:1px solid {conf_color}44;border-radius:4px;padding:0.1rem 0.4rem;'\
                      f'margin-left:0.5rem;font-family:monospace">{conf_tier} confidence</span>'
        with st.expander(f"{label} — {pmeta.get('label', pattern or 'No pattern data')}"):
            st.markdown(
                f'<div style="font-size:0.78rem;color:#6B7280;margin-bottom:0.8rem">'
                f'Signal confidence: '
                + conf_badge +
                f' &nbsp;·&nbsp; <span style="color:#4B5563">{conf_reason}</span></div>',
                unsafe_allow_html=True
            )
            if pmeta:
                st.markdown(
                    f'<div style="background:rgba(255,255,255,0.03);border-left:3px solid '
                    f'{pmeta["color"]};padding:0.8rem 1.2rem;border-radius:0 6px 6px 0;'
                    f'margin-bottom:0.8rem">'
                    f'<strong>{pmeta["summary"]}</strong><br>'
                    f'<span style="font-size:0.85rem;color:#8899AA">{pmeta["detail"]}</span>'
                    f'</div>',
                    unsafe_allow_html=True
                )
                st.markdown(
                    f'<div style="font-size:0.82rem;color:#6B7280;margin-top:0.5rem">'
                    f'💡 {pmeta["suggestion"]}</div>',
                    unsafe_allow_html=True
                )
                if pmeta.get('test_next'):
                    st.markdown(
                        f'<div style="font-size:0.82rem;color:#4361EE;margin-top:0.4rem">'
                        f'🔬 What to test next: {pmeta["test_next"]}</div>',
                        unsafe_allow_html=True
                    )

            # Check additional diagnostic rules
            flags = [r for r in DIAGNOSTIC_RULES if r["condition"](roi_dict)]
            if flags:
                st.markdown('<div style="margin-top:0.8rem;font-size:0.8rem;color:#4361EE">Additional flags:</div>', unsafe_allow_html=True)
                for flag in flags:
                    test_next_flag = flag.get('test_next', '')
                    extra = (f'<br><span style="color:#4361EE;margin-top:0.3rem;display:block">'
                             f'🔬 What to test next: {test_next_flag}</span>' if test_next_flag else '')
                    st.markdown(
                        f'<div style="background:rgba(67,97,238,0.06);border:1px solid rgba(67,97,238,0.2);'
                        f'border-radius:6px;padding:0.6rem 1rem;margin-top:0.4rem;font-size:0.82rem;color:#C8D6E5">'
                        f'<strong>{flag["label"]}</strong><br>'
                        f'<span style="color:#8899AA">{flag["detail"]}</span>'
                        + extra + '</div>',
                        unsafe_allow_html=True
                    )
else:
    st.info("Run inference with the updated run_tribe.py to generate diagnosis data.")

st.divider()

# ── Trade-off Cards ──────────────────────────────────────────────────────────
# Shows best-per-metric cards instead of a single winner.
# Each ad may lead on a different dimension — that's the honest story.

db.ensure_timeseries_schema()
df_derived  = db.get_derived_metrics(run_id)
ad_labels   = db.get_ad_labels()

st.markdown("### What Each Ad Does Best")
st.markdown(
    '<div class="explain-text" style="margin-bottom:1rem">'    'No single winner — only trade-offs. Each ad may lead on a different signal. '    'Use these to understand what each creative is optimised for.</div>',
    unsafe_allow_html=True
)

WEIGHTS = {
    "memory": 0.30, "attention": 0.25, "emotion": 0.20, "decision": 0.15,
    "visual": 0.025, "motion": 0.025, "auditory": 0.025, "language": 0.025,
}

from roi_labels import ROI_ORDER

# Compute composite scores
norm_scores = {}
raw_scores  = {}
if not df_wide.empty:
    for _, row in df_wide.iterrows():
        s = sum(WEIGHTS.get(roi, 0) * (row.get(roi) or 0) for roi in ROI_ORDER)
        raw_scores[row["ad_name"]] = s
    mn, mx = min(raw_scores.values()), max(raw_scores.values())
    span   = mx - mn if mx != mn else 1.0
    norm_scores = {k: ((v - mn) / span) * 100 for k, v in raw_scores.items()}

# Build trade-off dict
tradeoffs = {}

# Best hook
if not df_derived.empty and "hook_strength" in df_derived.columns:
    best_hook_row = df_derived.loc[df_derived["hook_strength"].idxmax()]
    tradeoffs["⚡ Best Hook (0–3s)"] = {
        "ad":    best_hook_row["ad_name"],
        "value": f'{best_hook_row["hook_strength"]:.4f}',
        "note":  "Proxy for early attentional engagement",
        "color": "#FFB703",
    }

# Best retention
if not df_derived.empty and "mid_retention" in df_derived.columns:
    best_ret_row = df_derived.loc[df_derived["mid_retention"].idxmax()]
    tradeoffs["🎯 Best Mid Retention (3–10s)"] = {
        "ad":    best_ret_row["ad_name"],
        "value": f'{best_ret_row["mid_retention"]:.4f}',
        "note":  "Proxy for sustained attentional signal",
        "color": "#06D6A0",
    }

# Strongest emotion peak
if not df_derived.empty and "peak_emotion_value" in df_derived.columns:
    best_emo_row = df_derived.loc[df_derived["peak_emotion_value"].idxmax()]
    tradeoffs["❤️ Strongest Emotion Peak"] = {
        "ad":    best_emo_row["ad_name"],
        "value": f'second {int(best_emo_row["peak_emotion_second"])}' if best_emo_row["peak_emotion_second"] is not None else "N/A",
        "note":  "Time of highest emotion-correlated signal",
        "color": "#F72585",
    }

# Best memory signal
if not df_wide.empty and "memory" in df_wide.columns:
    best_mem_row = df_wide.loc[df_wide["memory"].idxmax()]
    tradeoffs["🧠 Strongest Memory Signal"] = {
        "ad":    best_mem_row["ad_name"],
        "value": f'{best_mem_row["memory"]:.4f}',
        "note":  "Proxy for scene memory encoding",
        "color": "#4361EE",
    }

# Show confidence summary above trade-off cards
if confidence:
    conf_items = []
    for an, cd in confidence.items():
        lbl   = ad_labels.get(an, an.upper())
        tier  = cd['tier']
        color = {'High': '#06D6A0', 'Moderate': '#FFB703', 'Low': '#F72585'}.get(tier, '#FFB703')
        conf_items.append(
            f'<span style="color:{color};font-family:monospace">'
            f'{lbl}: {tier}</span> '
            f'<span style="color:#4B5563;font-size:0.75rem">({cd["reason"]})</span>'
        )
    st.markdown(
        '<div style="font-size:0.78rem;color:#6B7280;margin-bottom:1rem">'
        'Signal confidence — ' + ' &nbsp;·&nbsp; '.join(conf_items) + '</div>',
        unsafe_allow_html=True
    )

if tradeoffs:
    t_cols = st.columns(len(tradeoffs))
    for i, (metric_label, meta) in enumerate(tradeoffs.items()):
        with t_cols[i]:
            label = ad_labels.get(meta["ad"], meta["ad"].upper())
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.03);border:1px solid {meta['color']}44;
                        border-top:3px solid {meta['color']};border-radius:8px;
                        padding:1rem;text-align:center">
                <div style="font-size:0.7rem;color:{meta['color']};font-family:monospace;
                            letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.5rem">
                    {metric_label}
                </div>
                <div style="font-size:1.3rem;font-weight:700;color:#C8D6E5;
                            font-family:monospace">{label}</div>
                <div style="font-size:0.85rem;color:#8899AA;margin-top:0.3rem">{meta['value']}</div>
                <div style="font-size:0.75rem;color:#4B5563;margin-top:0.3rem">{meta['note']}</div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info("Run inference to populate trade-off cards.")

# ── Conflict detection ────────────────────────────────────────────────────────
# If the composite summary disagrees with hook strength — show a warning.
# This teaches users not to blindly trust any single number.
if norm_scores and tradeoffs and "⚡ Best Hook (0–3s)" in tradeoffs:
    composite_winner = max(norm_scores, key=norm_scores.get)
    hook_winner      = tradeoffs["⚡ Best Hook (0–3s)"]["ad"]
    if composite_winner != hook_winner:
        comp_label = ad_labels.get(composite_winner, composite_winner.upper())
        hook_label = ad_labels.get(hook_winner, hook_winner.upper())
        st.markdown(f"""
        <div style="background:rgba(251,86,7,0.08);border:1px solid rgba(251,86,7,0.3);
                    border-radius:8px;padding:0.8rem 1.2rem;margin-top:1rem;
                    font-size:0.85rem;color:#FCA5A5">
        ⚠ <strong>Signal conflict:</strong> The exploratory composite index favours
        <strong>{comp_label}</strong>, but hook strength favours <strong>{hook_label}</strong>.
        These signals measure different things. Use the timeline view to understand why.
        </div>
        """, unsafe_allow_html=True)

st.divider()

# ── Exploratory Composite Index (secondary) ───────────────────────────────────
with st.expander("📊 Exploratory Composite Index — expand to view", expanded=False):
    st.markdown(
        '<div class="explain-text" style="margin-bottom:0.8rem">'        'Weighted aggregation across all 8 signal groups. Provided as a rough reference only — '        'not validated for ranking ad outcomes. Higher does not mean "better ad." '        'Use the trade-off cards and timeline above for actionable insight.</div>',
        unsafe_allow_html=True
    )
    if norm_scores:
        gauge_fig, _ = charts.make_winner_gauge(df_wide)
        st.plotly_chart(gauge_fig, use_container_width=True)

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
        <div class="section-label">Brain Area</div>
        <div class="explain-text">{meta['brain_area']}</div>
        <div class="explain-text" style="margin-top:0.4rem;font-size:0.78rem;color:#4B5563">
            Vertex mapping: approximate spatial split (fsaverage5)
        </div>
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
