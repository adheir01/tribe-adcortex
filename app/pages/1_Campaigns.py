"""
=============================================================================
pages/4_Campaigns.py — Campaign Manager
=============================================================================

PURPOSE
-------
Groups scoring runs into named campaigns so you can compare like with like.

EXAMPLES
--------
- "Q2 Food Study" → runs testing chocolate vs salad vs social ads
- "BMW Launch" → runs testing different car ad concepts
- "Uncategorised" → runs made before this feature existed (your April 25 run)

HOW IT WORKS
------------
Campaigns live in the PostgreSQL campaigns table.
Each scoring run can be assigned to one campaign via campaign_id.
The History page filters by campaign so you only compare relevant runs.
"""

import pandas as pd
import streamlit as st

import db

st.set_page_config(
    page_title = "Campaigns | tribe-adcortex",
    page_icon  = "📁",
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
.campaign-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.campaign-name {
    font-family: 'Space Mono', monospace;
    font-size: 1rem;
    color: #C8D6E5;
}
.campaign-meta {
    font-size: 0.8rem;
    color: #6B7280;
    margin-top: 0.3rem;
}
.stButton > button {
    background: rgba(67,97,238,0.15);
    border: 1px solid rgba(67,97,238,0.4);
    color: #C8D6E5;
    border-radius: 6px;
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
}
</style>
""", unsafe_allow_html=True)

# ── Ensure schema is up to date ───────────────────────────────────────────────
# This runs the ALTER TABLE IF NOT EXISTS migration so the campaigns table
# and campaign_id column exist even on databases created before this feature.
try:
    db.ensure_schema()
except Exception as e:
    st.error(f"Schema migration failed: {e}")
    st.stop()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 📁 Campaigns")
st.markdown(
    '<div style="color:#6B7280; margin-bottom:1.5rem">'
    'Group your scoring runs into campaigns to keep comparisons meaningful. '
    'Only compare runs within the same campaign — comparing food ads vs car ads tells you nothing.</div>',
    unsafe_allow_html=True
)

# ── Create new campaign ───────────────────────────────────────────────────────
st.markdown('<div class="section-label">Create new campaign</div>', unsafe_allow_html=True)

col_name, col_desc, col_btn = st.columns([2, 3, 1])
with col_name:
    new_name = st.text_input("Campaign name", placeholder="Q2 Food Study", label_visibility="collapsed")
with col_desc:
    new_desc = st.text_input("Description (optional)", placeholder="Chocolate vs salad vs social — food brand creative test", label_visibility="collapsed")
with col_btn:
    if st.button("Create", use_container_width=True):
        if new_name.strip():
            campaign_id = db.create_campaign(new_name.strip(), new_desc.strip())
            st.success(f"Campaign created: {new_name}")
            st.rerun()
        else:
            st.warning("Enter a campaign name first.")

st.divider()

# ── Existing campaigns ────────────────────────────────────────────────────────
st.markdown('<div class="section-label">All campaigns</div>', unsafe_allow_html=True)

campaigns = db.get_all_campaigns()

if campaigns.empty:
    st.info("No campaigns yet. Create one above.")
    st.stop()

all_run_ids  = db.get_all_run_ids()
campaign_map = {
    str(row["id"]): row["name"]
    for _, row in campaigns.iterrows()
    if row["id"] is not None
}
# Add Uncategorised option for the run assignment dropdown
dropdown_options = {**{"none": "Uncategorised"}, **campaign_map}

for _, camp in campaigns.iterrows():
    import math
    camp_id   = None if (camp["id"] is None or (isinstance(camp["id"], float) and math.isnan(camp["id"]))) else camp["id"]
    camp_name = camp["name"]
    runs      = db.get_runs_for_campaign(camp_id)

    with st.container():
        st.markdown(f"""
        <div class="campaign-card">
            <div class="campaign-name">{"📁" if camp_id else "📂"} {camp_name}</div>
            <div class="campaign-meta">
                {camp["description"] or "No description"} &nbsp;·&nbsp;
                {len(runs)} run(s)
            </div>
        </div>
        """, unsafe_allow_html=True)

        if runs:
            with st.expander(f"Runs in this campaign ({len(runs)})"):
                for run_id in runs:
                    st.markdown(
                        f'<div style="font-family:monospace; font-size:0.85rem; '
                        f'color:#4361EE; padding:0.3rem 0">{run_id}</div>',
                        unsafe_allow_html=True
                    )

st.divider()

# ── Assign runs to campaigns ──────────────────────────────────────────────────
st.markdown('<div class="section-label">Assign runs to campaigns</div>', unsafe_allow_html=True)
st.markdown(
    '<div style="color:#6B7280; font-size:0.85rem; margin-bottom:1rem">'
    'Runs not assigned to a campaign show as Uncategorised. '
    'Your April 25 run is there by default — assign it to a campaign here.</div>',
    unsafe_allow_html=True
)

if not all_run_ids:
    st.info("No runs in database yet.")
    st.stop()

for run_id in all_run_ids:
    engine = db.get_engine()
    current = pd.read_sql("""
        SELECT campaign_id FROM scoring_runs WHERE run_id = %(run_id)s
    """, engine, params={"run_id": run_id})

    current_campaign_id = None
    if not current.empty and current["campaign_id"].iloc[0] is not None:
        current_campaign_id = str(int(current["campaign_id"].iloc[0]))

    col_run, col_select, col_assign = st.columns([2, 3, 1])

    with col_run:
        st.markdown(
            f'<div style="font-family:monospace; font-size:0.85rem; '
            f'color:#4361EE; padding:0.6rem 0">{run_id}</div>',
            unsafe_allow_html=True
        )

    with col_select:
        selected = st.selectbox(
            "Campaign",
            options      = list(dropdown_options.keys()),
            format_func  = lambda k: dropdown_options[k],
            index        = list(dropdown_options.keys()).index(current_campaign_id)
                           if current_campaign_id in dropdown_options else 0,
            key          = f"assign_{run_id}",
            label_visibility = "collapsed",
        )

    with col_assign:
        if st.button("Save", key=f"save_{run_id}"):
            new_campaign_id = int(selected) if selected != "none" else None
            db.assign_run_to_campaign(run_id, new_campaign_id)
            st.success("Saved")
            st.rerun()
