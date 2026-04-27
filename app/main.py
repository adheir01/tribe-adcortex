"""
=============================================================================
main.py — Home / Welcome Screen
=============================================================================
This is the entry point Streamlit always loads first.
It serves as a workflow guide so new users know exactly where to start.
All dashboard functionality lives in pages/4_Dashboard.py.
"""

import streamlit as st

st.set_page_config(
    page_title = "tribe-adcortex",
    page_icon  = "🧠",
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
.hero {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B2838 100%);
    border: 1px solid rgba(67,97,238,0.3);
    border-radius: 12px;
    padding: 2.5rem 3rem;
    margin-bottom: 2rem;
}
.step-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 1.5rem;
    height: 100%;
    transition: border-color 0.2s;
}
.step-number {
    font-family: 'Space Mono', monospace;
    font-size: 2rem;
    font-weight: 700;
    margin-bottom: 0.5rem;
}
.step-title {
    font-size: 1rem;
    font-weight: 600;
    color: #C8D6E5;
    margin-bottom: 0.5rem;
}
.step-desc {
    font-size: 0.85rem;
    color: #6B7280;
    line-height: 1.6;
}
.arrow {
    display: flex;
    align-items: center;
    justify-content: center;
    color: rgba(67,97,238,0.5);
    font-size: 1.5rem;
    padding-top: 1.5rem;
}
.what-box {
    background: rgba(67,97,238,0.06);
    border: 1px solid rgba(67,97,238,0.2);
    border-radius: 10px;
    padding: 1.5rem 2rem;
    margin-bottom: 1rem;
}
.disclaimer {
    background: rgba(255,183,3,0.05);
    border: 1px solid rgba(255,183,3,0.2);
    border-radius: 8px;
    padding: 1rem 1.5rem;
    font-size: 0.82rem;
    color: #9CA3AF;
    line-height: 1.7;
}
</style>
""", unsafe_allow_html=True)

# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1 style="margin:0 0 0.5rem 0">🧠 tribe-adcortex</h1>
    <p style="color:#8899AA; margin:0; font-size:1.1rem">
        A time series diagnostic tool for ad creative testing
        using predicted fMRI brain signals.
    </p>
    <p style="color:#4B5563; margin:0.8rem 0 0 0; font-size:0.85rem">
        TRIBE v2 · Meta FAIR 2026 · fsaverage5 · 20,484 cortical vertices
    </p>
</div>
""", unsafe_allow_html=True)

# ── What it does ──────────────────────────────────────────────────────────────
st.markdown("### What this tool does")
col_l, col_r = st.columns(2)

with col_l:
    st.markdown("""
    <div class="what-box">
        <div style="font-size:0.8rem;color:#4361EE;font-family:monospace;
                    letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.8rem">
            What you get
        </div>
        <ul style="color:#C8D6E5;font-size:0.9rem;line-height:2;margin:0;padding-left:1.2rem">
            <li>Second-by-second attention, emotion &amp; memory signals</li>
            <li>Hook strength, mid-retention, attention decay metrics</li>
            <li>Pattern classification — hook &amp; drop, slow build, sustained</li>
            <li>Failure detection with actionable test suggestions</li>
            <li>Side-by-side comparison across ad variants</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

with col_r:
    st.markdown("""
    <div class="what-box">
        <div style="font-size:0.8rem;color:#F72585;font-family:monospace;
                    letter-spacing:0.1em;text-transform:uppercase;margin-bottom:0.8rem">
            What it is not
        </div>
        <ul style="color:#9CA3AF;font-size:0.9rem;line-height:2;margin:0;padding-left:1.2rem">
            <li>Not a prediction of purchase intent</li>
            <li>Not validated against real recall outcomes</li>
            <li>Not demographic-specific (average subject model)</li>
            <li>Not a replacement for human research</li>
            <li>Signals are proxies — treat as hypotheses, not verdicts</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Workflow steps ────────────────────────────────────────────────────────────
st.markdown("### How to use it — follow these steps in order")
st.markdown(
    '<div style="color:#6B7280;font-size:0.85rem;margin-bottom:1.5rem">'
    'Use the sidebar to navigate between pages.</div>',
    unsafe_allow_html=True
)

steps = [
    {
        "number": "01",
        "color":  "#4361EE",
        "page":   "📁 Campaigns",
        "title":  "Create a campaign",
        "desc":   "Group your scoring runs so comparisons stay meaningful. "
                  "Create one campaign per concept — don't compare food ads to car ads.",
    },
    {
        "number": "02",
        "color":  "#7209B7",
        "page":   "🎬 Creatives",
        "title":  "Upload your ad videos",
        "desc":   "Drag and drop your MP4 files. Label each one clearly. "
                  "Best results: 3–4 variants of the same concept, varying one element at a time.",
    },
    {
        "number": "03",
        "color":  "#F72585",
        "page":   "⚡ Inference",
        "title":  "Run TRIBE v2 scoring",
        "desc":   "Launch a RunPod GPU pod, paste the IP and port here, click Start. "
                  "The app uploads files, runs inference, and downloads results automatically. "
                  "Terminate the pod when done (~$0.20 per run).",
    },
    {
        "number": "04",
        "color":  "#06D6A0",
        "page":   "📊 Dashboard",
        "title":  "Explore the results",
        "desc":   "Load your roi_scores.json from the sidebar. "
                  "See timeline charts, derived metrics, failure patterns, "
                  "trade-off cards, and the full neural signal breakdown.",
    },
    {
        "number": "05",
        "color":  "#FFB703",
        "page":   "📈 History",
        "title":  "Compare across runs",
        "desc":   "Run inference again after modifying your creative. "
                  "The History page shows how signals changed between versions "
                  "within the same campaign.",
    },
]

# Render steps in a row with arrows between
cols = st.columns(9)   # 5 cards + 4 arrows
col_indices = [0, 2, 4, 6, 8]
arrow_indices = [1, 3, 5, 7]

for i, step in enumerate(steps):
    with cols[col_indices[i]]:
        st.markdown(f"""
        <div class="step-card">
            <div class="step-number" style="color:{step['color']}">{step['number']}</div>
            <div style="font-size:0.7rem;color:{step['color']};font-family:monospace;
                        letter-spacing:0.08em;margin-bottom:0.5rem">{step['page']}</div>
            <div class="step-title">{step['title']}</div>
            <div class="step-desc">{step['desc']}</div>
        </div>
        """, unsafe_allow_html=True)

for idx in arrow_indices:
    with cols[idx]:
        st.markdown('<div class="arrow">→</div>', unsafe_allow_html=True)

st.divider()

# ── Experiment design tip ─────────────────────────────────────────────────────
st.markdown("### Getting the most out of it")
st.markdown("""
<div style="background:rgba(6,214,160,0.05);border:1px solid rgba(6,214,160,0.2);
            border-radius:10px;padding:1.5rem 2rem;font-size:0.88rem;
            color:#C8D6E5;line-height:1.8">
    <strong style="color:#06D6A0">Control one variable at a time.</strong>
    The tool produces actionable insight when your ad variants share the same concept
    but differ in one element — the opening hook, the pacing, whether a person appears,
    the music choice, or the motion level.<br><br>
    <strong style="color:#06D6A0">Use it as a loop.</strong>
    Upload → Score → See where the ad loses people → Form a hypothesis →
    Modify the creative → Re-score → Compare in History.
    That iteration loop is where the value is.
</div>
""", unsafe_allow_html=True)

st.divider()

# ── Disclaimer ────────────────────────────────────────────────────────────────
st.markdown("""
<div class="disclaimer">
    <strong>Model:</strong> TRIBE v2 (<code>facebook/tribev2</code>) ·
    <strong>License:</strong> CC BY-NC 4.0 — non-commercial use only ·
    <strong>Paper:</strong> d'Ascoli et al. 2026<br>
    All scores are predicted neural activations for an average subject,
    not actual brain measurements. Signals are correlated with attention,
    emotion, and memory processes — not validated against advertising outcomes.
    Use as a diagnostic hypothesis tool, not a decision engine.
</div>
""", unsafe_allow_html=True)
