"""
=============================================================================
pages/3_History.py — Run History & Cross-Run Comparison
=============================================================================

PURPOSE
-------
Compare results across runs — filtered by campaign so you only
compare like with like.

Select a campaign first, then select which runs within it to compare.
"""

import pandas as pd
import plotly.express as px
import streamlit as st

import db
from roi_labels import ROI_META, ROI_ORDER

st.set_page_config(
    page_title = "History | tribe-adcortex",
    page_icon  = "📊",
    layout     = "wide",
    initial_sidebar_state = "expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
    background-color: #070B14;
    color: #C8D6E5;
}
h1, h2, h3 { font-family: 'Space Mono', monospace; }
.section-label {
    font-family: 'Space Mono', monospace;
    font-size: 0.7rem;
    color: #4361EE;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    margin-bottom: 0.5rem;
}
</style>
""", unsafe_allow_html=True)

# ── Ensure schema ─────────────────────────────────────────────────────────────
try:
    db.ensure_schema()
except Exception:
    pass

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 📊 Run History")
st.markdown(
    '<div style="color:#6B7280; margin-bottom:1.5rem">'
    'Compare neural engagement scores across runs within a campaign.</div>',
    unsafe_allow_html=True
)

# ── Campaign selector ─────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Select campaign</div>', unsafe_allow_html=True)

campaigns    = db.get_all_campaigns()
camp_options = campaigns["name"].tolist()

if not camp_options:
    st.info("No runs loaded yet. Go to Dashboard and load a roi_scores.json first.")
    st.stop()

selected_campaign_name = st.selectbox(
    "Campaign",
    options          = camp_options,
    label_visibility = "collapsed",
)

selected_campaign_row = campaigns[campaigns["name"] == selected_campaign_name].iloc[0]
selected_campaign_id  = selected_campaign_row["id"]   # None for Uncategorised

campaign_runs = db.get_runs_for_campaign(selected_campaign_id)

if not campaign_runs:
    st.info(f"No runs in '{selected_campaign_name}' yet. Assign runs on the Campaigns page.")
    st.stop()

st.divider()

# ── Run selector ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Select runs to compare</div>', unsafe_allow_html=True)

selected_runs = st.multiselect(
    "Runs",
    options          = campaign_runs,
    default          = campaign_runs,
    label_visibility = "collapsed",
)

if not selected_runs:
    st.info("Select at least one run.")
    st.stop()

st.divider()

# ── Composite scores ──────────────────────────────────────────────────────────
WEIGHTS = {
    "memory": 0.30, "attention": 0.25, "emotion": 0.20, "decision": 0.15,
    "visual": 0.025, "motion": 0.025, "auditory": 0.025, "language": 0.025,
}

st.markdown("### Composite Score — Across Runs")
st.markdown(
    '<div style="color:#6B7280; font-size:0.85rem; margin-bottom:1rem">'
    'Weighted composite score per ad per run within this campaign.</div>',
    unsafe_allow_html=True
)

composite_rows = []
for run_id in selected_runs:
    df = db.get_roi_scores(run_id)
    if df.empty:
        continue
    labels = db.get_ad_labels()
    for _, row in df.iterrows():
        score    = sum(WEIGHTS.get(roi, 0) * (row.get(roi) or 0) for roi in ROI_ORDER)
        ad_label = labels.get(row["ad_name"], row["ad_name"].upper())
        composite_rows.append({
            "Run":   run_id,
            "Ad":    ad_label,
            "Score": round(score, 5),
        })

if composite_rows:
    df_comp = pd.DataFrame(composite_rows)
    fig = px.bar(
        df_comp, x="Ad", y="Score", color="Run", barmode="group",
        color_discrete_sequence=["#4361EE", "#F72585", "#06D6A0", "#FFB703"],
    )
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E0E0E0", size=12),
        xaxis=dict(color="#E0E0E0", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(color="#E0E0E0", gridcolor="rgba(255,255,255,0.08)", title="Composite Score"),
        legend=dict(bgcolor="rgba(255,255,255,0.05)"),
        margin=dict(l=10, r=10, t=20, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)

st.divider()

# ── ROI comparison ────────────────────────────────────────────────────────────
st.markdown("### ROI Group Comparison")

selected_roi = st.selectbox(
    "Brain region",
    options     = [r for r in ROI_ORDER],
    format_func = lambda r: f"{ROI_META[r]['icon']}  {ROI_META[r]['label']}",
)

roi_rows = []
for run_id in selected_runs:
    df = db.get_roi_scores(run_id)
    if df.empty or selected_roi not in df.columns:
        continue
    labels = db.get_ad_labels()
    for _, row in df.iterrows():
        ad_label = labels.get(row["ad_name"], row["ad_name"].upper())
        roi_rows.append({"Run": run_id, "Ad": ad_label, "Score": row.get(selected_roi)})

if roi_rows:
    df_roi = pd.DataFrame(roi_rows).dropna(subset=["Score"])
    fig2   = px.bar(
        df_roi, x="Ad", y="Score", color="Run", barmode="group",
        title=f"{ROI_META[selected_roi]['label']} — across runs",
        color_discrete_sequence=["#4361EE", "#F72585", "#06D6A0", "#FFB703"],
    )
    fig2.update_layout(
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#E0E0E0", size=12),
        xaxis=dict(color="#E0E0E0", gridcolor="rgba(255,255,255,0.05)"),
        yaxis=dict(color="#E0E0E0", gridcolor="rgba(255,255,255,0.08)", title="Mean Activation"),
        legend=dict(bgcolor="rgba(255,255,255,0.05)"),
        margin=dict(l=10, r=10, t=40, b=10),
    )
    st.plotly_chart(fig2, use_container_width=True)

st.divider()

# ── Raw data ──────────────────────────────────────────────────────────────────
with st.expander("Show raw scores table"):
    all_data = []
    for run_id in selected_runs:
        df = db.get_roi_scores(run_id)
        if not df.empty:
            df["run_id"] = run_id
            all_data.append(df)
    if all_data:
        full_df = pd.concat(all_data, ignore_index=True)
        cols    = ["run_id", "ad_name"] + [r for r in ROI_ORDER if r in full_df.columns]
        st.dataframe(full_df[cols].round(5), hide_index=True, use_container_width=True)
