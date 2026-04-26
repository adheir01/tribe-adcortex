"""
=============================================================================
charts.py — All Plotly chart definitions
=============================================================================

PURPOSE
-------
All visualisation logic lives here. main.py just calls these functions and
renders the returned figures. This keeps the Streamlit UI code clean and
makes the charts independently testable.

WHY PLOTLY?
-----------
Plotly renders interactive charts in Streamlit out of the box. You can hover,
zoom, and export — important for a portfolio demo. The alternative (matplotlib)
produces static images that look less professional in a web UI.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from roi_labels import ROI_META, ROI_ORDER, ROI_COLORS, ROI_SHORT_LABELS, HERO_ROIS

# ── Colour palette ────────────────────────────────────────────────────────────
# Consistent ad-variant colours across all charts
AD_COLORS = ["#4361EE", "#F72585", "#06D6A0", "#FFB703"]


def make_radar_chart(df_wide: pd.DataFrame) -> go.Figure:
    """
    Radar (spider) chart — one polygon per ad variant, all 8 ROI groups.

    df_wide: pivot table with columns [ad_name, visual, motion, ..., decision]

    Why radar? It shows the "neural signature" of each ad at a glance.
    A memory+attention-heavy ad looks visually distinct from a visual+emotion-heavy one.
    Recruiters and hiring managers immediately understand the comparative view.

    Technical note: Plotly radar charts need the first category repeated at the end
    to close the polygon — that's the `categories + [categories[0]]` pattern below.
    """
    categories = [ROI_META[r]["short"] for r in ROI_ORDER]
    categories_closed = categories + [categories[0]]   # close the polygon

    fig = go.Figure()

    for i, row in df_wide.iterrows():
        ad_name = row["ad_name"]
        values  = [row.get(roi, 0) or 0 for roi in ROI_ORDER]
        values_closed = values + [values[0]]   # close polygon

        color = AD_COLORS[i % len(AD_COLORS)]

        fig.add_trace(go.Scatterpolar(
            r           = values_closed,
            theta       = categories_closed,
            fill        = "toself",
            fillcolor   = f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},0.2)",
            line        = dict(color=color, width=2),
            name        = ad_name.replace("_", " ").upper(),
            hovertemplate = "<b>%{theta}</b><br>Activation: %{r:.4f}<extra></extra>",
        ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible    = True,
                showticklabels = False,
                gridcolor  = "rgba(255,255,255,0.1)",
            ),
            angularaxis=dict(
                gridcolor  = "rgba(255,255,255,0.15)",
                linecolor  = "rgba(255,255,255,0.3)",
            ),
            bgcolor = "rgba(0,0,0,0)",
        ),
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor  = "rgba(0,0,0,0)",
        font          = dict(color="#E0E0E0", size=12),
        legend        = dict(
            bgcolor     = "rgba(255,255,255,0.05)",
            bordercolor = "rgba(255,255,255,0.1)",
            borderwidth = 1,
        ),
        margin = dict(l=60, r=60, t=40, b=40),
    )
    return fig


def make_roi_bar_chart(df_wide: pd.DataFrame, roi_group: str) -> go.Figure:
    """
    Horizontal bar chart for a single ROI group, all ads ranked.
    Used in the "ROI deep dive" section.

    Sorting highest-first makes the winner immediately obvious.
    """
    meta  = ROI_META[roi_group]
    df    = df_wide[["ad_name", roi_group]].dropna().sort_values(roi_group, ascending=True)

    colors = [AD_COLORS[list(df_wide["ad_name"]).index(n) % len(AD_COLORS)] for n in df["ad_name"]]

    fig = go.Figure(go.Bar(
        x           = df[roi_group],
        y           = df["ad_name"].str.replace("_", " ").str.upper(),
        orientation = "h",
        marker_color= colors,
        hovertemplate = f"<b>%{{y}}</b><br>{meta['label']}: %{{x:.4f}}<extra></extra>",
    ))

    fig.update_layout(
        xaxis_title   = "Mean Predicted fMRI Activation",
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor  = "rgba(0,0,0,0)",
        font          = dict(color="#E0E0E0", size=12),
        xaxis         = dict(gridcolor="rgba(255,255,255,0.1)", color="#E0E0E0"),
        yaxis         = dict(gridcolor="rgba(255,255,255,0.0)", color="#E0E0E0"),
        margin        = dict(l=10, r=20, t=20, b=40),
    )
    return fig


def make_comparison_heatmap(df_wide: pd.DataFrame) -> go.Figure:
    """
    Heatmap: ads (rows) × ROI groups (columns), coloured by activation.

    This is the "at a glance" view — you can immediately see which ad
    dominates which brain region. Dark = low activation, bright = high.

    Uses z-score normalisation per ROI column so differences are visible
    even when absolute values vary across ROI groups.
    """
    roi_cols = [r for r in ROI_ORDER if r in df_wide.columns]
    matrix   = df_wide.set_index("ad_name")[roi_cols]

    # Z-score normalise each column (ROI group) independently
    # This makes cross-ROI comparison meaningful — otherwise auditory might
    # always dominate just because it has higher absolute activation values
    matrix_norm = (matrix - matrix.mean()) / (matrix.std() + 1e-9)

    short_labels = [ROI_META[r]["short"] for r in roi_cols]
    ad_labels    = [n.replace("_", " ").upper() for n in matrix_norm.index]

    fig = go.Figure(go.Heatmap(
        z            = matrix_norm.values,
        x            = short_labels,
        y            = ad_labels,
        colorscale   = "Viridis",
        showscale    = True,
        hovertemplate = "<b>%{y}</b> — %{x}<br>Z-score: %{z:.2f}<extra></extra>",
        colorbar     = dict(
        title      = dict(text="Z-score", font=dict(color="#E0E0E0")),
        tickfont   = dict(color="#E0E0E0"),
        ),
    ))

    fig.update_layout(
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor  = "rgba(0,0,0,0)",
        font          = dict(color="#E0E0E0", size=12),
        xaxis         = dict(color="#E0E0E0", side="bottom"),
        yaxis         = dict(color="#E0E0E0"),
        margin        = dict(l=10, r=10, t=20, b=10),
    )
    return fig


def make_winner_gauge(df_wide: pd.DataFrame) -> go.Figure:
    """
    Composite "Neural Engagement Score" gauge per ad.

    The composite score is a weighted average of the 8 ROI groups.
    Weights are based on neuroscience research linking these regions
    to advertising effectiveness outcomes:
      - Memory (0.30): strongest predictor of brand recall
      - Attention (0.25): sustained engagement
      - Emotion (0.20): affective response / purchase intent
      - Decision (0.15): cognitive processing of CTA
      - Others (0.10 split): baseline sensory processing

    The score is normalised to 0-100 for interpretability.
    """
    WEIGHTS = {
        "memory":    0.30,
        "attention": 0.25,
        "emotion":   0.20,
        "decision":  0.15,
        "visual":    0.025,
        "motion":    0.025,
        "auditory":  0.025,
        "language":  0.025,
    }

    scores = {}
    for _, row in df_wide.iterrows():
        weighted = sum(
            WEIGHTS.get(roi, 0) * (row.get(roi) or 0)
            for roi in ROI_ORDER
        )
        scores[row["ad_name"]] = weighted

    # Normalise to 0-100 range across the set
    min_s, max_s = min(scores.values()), max(scores.values())
    span = max_s - min_s if max_s != min_s else 1.0
    normalised = {k: ((v - min_s) / span) * 100 for k, v in scores.items()}

    n_ads = len(normalised)
    fig   = make_subplots(
        rows=1, cols=n_ads,
        specs=[[{"type": "indicator"}] * n_ads],
    )

    for i, (ad_name, score) in enumerate(normalised.items(), start=1):
        color = AD_COLORS[(i - 1) % len(AD_COLORS)]
        fig.add_trace(go.Indicator(
            mode  = "gauge+number",
            value = score,
            title = {"text": ad_name.replace("_", " ").upper(),
                     "font": {"color": "#E0E0E0", "size": 14}},
            gauge = dict(
                axis       = dict(range=[0, 100], tickcolor="#E0E0E0"),
                bar        = dict(color=color),
                bgcolor    = "rgba(255,255,255,0.05)",
                bordercolor= "rgba(255,255,255,0.2)",
                steps      = [
                    dict(range=[0, 33],  color="rgba(255,255,255,0.03)"),
                    dict(range=[33, 66], color="rgba(255,255,255,0.05)"),
                    dict(range=[66, 100],color="rgba(255,255,255,0.08)"),
                ],
            ),
            number = dict(font={"color": "#E0E0E0"}, suffix="/100"),
        ), row=1, col=i)

    fig.update_layout(
        paper_bgcolor = "rgba(0,0,0,0)",
        font          = dict(color="#E0E0E0"),
        height        = 220,
        margin        = dict(l=20, r=20, t=40, b=20),
    )
    return fig, normalised


def make_top_regions_chart(df_regions: pd.DataFrame, ad_name: str) -> go.Figure:
    """
    Horizontal bar chart of the top-10 HCP brain regions for a specific ad.

    Rank 1 is most activated. This gives the neuroscience deep-dive for
    anyone who wants to go beyond the grouped ROI view.
    """
    df = df_regions[df_regions["ad_name"] == ad_name].sort_values("rank")

    fig = go.Figure(go.Bar(
        x           = list(range(len(df), 0, -1)),
        y           = df["region_name"],
        orientation = "h",
        marker_color= AD_COLORS[0],
        hovertemplate = "<b>%{y}</b><br>Rank: #%{text}<extra></extra>",
        text        = df["rank"].astype(str),
    ))

    fig.update_layout(
        xaxis_title   = "← Most activated",
        paper_bgcolor = "rgba(0,0,0,0)",
        plot_bgcolor  = "rgba(0,0,0,0)",
        font          = dict(color="#E0E0E0", size=11),
        xaxis         = dict(visible=False),
        yaxis         = dict(color="#E0E0E0"),
        margin        = dict(l=10, r=10, t=10, b=10),
    )
    return fig
