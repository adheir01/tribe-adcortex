"""
=============================================================================
pages/1_Creatives.py — Creative Management Page
=============================================================================

PURPOSE
-------
Manages the ad creative MP4 files that get scored.

FEATURES
--------
1. Upload MP4s via drag and drop
2. Preview / play uploaded videos
3. Label each ad with a friendly name (instead of ad_a, ad_b)
4. Delete videos
5. Show what's currently in the creatives/ folder

HOW LABELS WORK
---------------
Labels are stored in a JSON file: creatives/labels.json
Format: {"ad_a": "Chocolate Campaign", "ad_b": "Salad Hero", ...}
The inference script and dashboard both read this file to
display friendly names instead of ad_a, ad_b, ad_c.
"""

import json
import os
from pathlib import Path

import streamlit as st

st.set_page_config(
    page_title = "Creatives | tribe-adcortex",
    page_icon  = "🎬",
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
.creative-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.file-name {
    font-family: 'Space Mono', monospace;
    font-size: 0.9rem;
    color: #4361EE;
}
.file-meta {
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
.delete-btn > button {
    background: rgba(220,38,38,0.1);
    border: 1px solid rgba(220,38,38,0.3);
    color: #FCA5A5;
}
</style>
""", unsafe_allow_html=True)

# ── Paths ─────────────────────────────────────────────────────────────────────
CREATIVES_DIR = Path("/app/creatives")
LABELS_FILE   = CREATIVES_DIR / "labels.json"
CREATIVES_DIR.mkdir(exist_ok=True)

# ── Label helpers ─────────────────────────────────────────────────────────────

def load_labels() -> dict:
    if LABELS_FILE.exists():
        try:
            return json.loads(LABELS_FILE.read_text())
        except Exception:
            return {}
    return {}

def save_labels(labels: dict):
    LABELS_FILE.write_text(json.dumps(labels, indent=2))

def get_mp4_files() -> list[Path]:
    return sorted(CREATIVES_DIR.glob("*.mp4"))

def next_ad_name(existing: list[Path]) -> str:
    """Generate next ad_x name: ad_a, ad_b, ad_c ..."""
    used = {f.stem for f in existing}
    for char in "abcdefghijklmnopqrstuvwxyz":
        name = f"ad_{char}"
        if name not in used:
            return name
    return f"ad_{len(existing)}"

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🎬 Creative Manager")
st.markdown(
    '<div style="color:#6B7280; margin-bottom:1.5rem">Upload, label, preview and manage the ad MP4 files that get scored by TRIBE v2.</div>',
    unsafe_allow_html=True
)

# ── Upload section ────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Upload new creatives</div>', unsafe_allow_html=True)

uploaded_files = st.file_uploader(
    label      = "Drag and drop MP4 files here",
    type       = ["mp4"],
    accept_multiple_files = True,
    label_visibility = "collapsed",
    help       = "Recommended: 15–30 seconds each. Multiple files accepted.",
)

if uploaded_files:
    # Use file names as a key to detect if these are genuinely new uploads
    upload_key = "_".join(sorted(f.name for f in uploaded_files))
    if st.session_state.get("last_upload_key") != upload_key:
        existing = get_mp4_files()
        labels   = load_labels()
        saved    = []
        for uf in uploaded_files:
            ad_name   = next_ad_name(existing)
            save_path = CREATIVES_DIR / f"{ad_name}.mp4"
            save_path.write_bytes(uf.read())
            existing  = get_mp4_files()
            labels[ad_name] = uf.name.replace(".mp4", "")
            saved.append(ad_name)
        save_labels(labels)
        st.session_state["last_upload_key"] = upload_key
        st.success(f"Uploaded {len(saved)} file(s): {', '.join(saved)}")
        st.rerun()

st.divider()

# ── Existing creatives ────────────────────────────────────────────────────────
mp4_files = get_mp4_files()
labels    = load_labels()

if not mp4_files:
    st.info("No creatives uploaded yet. Drag and drop MP4 files above to get started.")
    st.stop()

st.markdown(
    f'<div class="section-label">Current creatives — {len(mp4_files)} file(s)</div>',
    unsafe_allow_html=True
)

labels_changed = False

for mp4 in mp4_files:
    ad_name     = mp4.stem
    file_size   = mp4.stat().st_size / 1e6
    current_label = labels.get(ad_name, ad_name)

    with st.container():
        st.markdown(f'<div class="creative-card">', unsafe_allow_html=True)

        col_info, col_preview, col_actions = st.columns([2, 3, 1])

        with col_info:
            st.markdown(f'<div class="file-name">{ad_name}.mp4</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="file-meta">{file_size:.1f} MB</div>', unsafe_allow_html=True)

            # Editable label
            new_label = st.text_input(
                "Label",
                value       = current_label,
                key         = f"label_{ad_name}",
                placeholder = "e.g. Chocolate Campaign",
                label_visibility = "collapsed",
            )
            if new_label != current_label:
                labels[ad_name] = new_label
                labels_changed  = True

        with col_preview:
            # Inline video player
            try:
                video_bytes = mp4.read_bytes()
                st.video(video_bytes)
            except Exception as e:
                st.caption(f"Preview unavailable: {e}")

        with col_actions:
            st.markdown('<div style="height:1.5rem"></div>', unsafe_allow_html=True)
            if st.button("🗑 Delete", key=f"delete_{ad_name}"):
                mp4.unlink()
                if ad_name in labels:
                    del labels[ad_name]
                save_labels(labels)
                st.warning(f"Deleted {ad_name}.mp4")
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

# Save label changes
if labels_changed:
    save_labels(labels)
    st.success("Labels saved.")

st.divider()

# ── Summary table ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Summary</div>', unsafe_allow_html=True)

import pandas as pd
summary = []
for mp4 in mp4_files:
    summary.append({
        "File":  mp4.name,
        "Label": labels.get(mp4.stem, mp4.stem),
        "Size":  f"{mp4.stat().st_size / 1e6:.1f} MB",
    })

st.dataframe(
    pd.DataFrame(summary),
    hide_index   = True,
    use_container_width = True,
)
