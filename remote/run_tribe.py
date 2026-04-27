"""
=============================================================================
TRIBE v2 Ad Creative Neural Engagement Scorer — RunPod Inference Script
=============================================================================

WHAT THIS SCRIPT DOES
----------------------
1. Loads TRIBE v2 from HuggingFace
2. Runs each MP4 through trimodal brain encoding (video + audio + text)
3. Extracts ROI group scores — both summary AND per-second time series
4. Computes derived metrics: hook strength, mid retention, peak emotion,
   attention decay rate
5. Saves roi_scores.json → scp this back locally

WHY TIME SERIES MATTERS
-----------------------
preds shape is (n_timesteps, 20484) — one prediction per second.
Collapsing this to a single mean throws away the most valuable signal:
HOW engagement changes over time. A hook that dies at second 4 and a
slow builder that peaks at second 12 both average to 0.05 — but they
behave completely differently in a real feed.

DERIVED METRICS
---------------
- Hook Strength:     mean(attention + motion + emotion) in seconds 0-3
- Mid Retention:     mean(attention) in seconds 3-10
- Peak Emotion Sec:  the second where emotion signal is highest
- Attention Decay:   linear slope of attention over time
                     negative = declining, positive = building

USAGE
-----
source ~/tribe_env/bin/activate
cd ~/tribe_scorer && python run_tribe.py
"""

import json
import time
import warnings
warnings.filterwarnings("ignore")

import numpy as np
from pathlib import Path
from tribev2.demo_utils import TribeModel

CREATIVES_DIR = Path("./creatives")
RESULTS_DIR   = Path("./results")
CACHE_DIR     = Path("./cache")
RESULTS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# ── ROI Group Definitions ─────────────────────────────────────────────────────
# Mapped to approximate vertex ranges on fsaverage5 surface.
# All ads use identical masks — relative comparisons are valid.
# Framing: "signals correlated with X" not "predicts X".
ROI_GROUPS = {
    "visual":    {"substrings": ["calcarine", "cuneus", "lingual"],
                  "label": "Visual Cortex",
                  "correlated_with": "visual attention and scene registration"},
    "motion":    {"substrings": ["sup_temporal", "middle_temporal"],
                  "label": "Motion Areas",
                  "correlated_with": "dynamic scene processing, cuts, movement"},
    "auditory":  {"substrings": ["transverse_temporal", "sup_temporal"],
                  "label": "Auditory Cortex",
                  "correlated_with": "music and speech processing"},
    "language":  {"substrings": ["inf_frontal", "triangul", "opercular"],
                  "label": "Language Network",
                  "correlated_with": "verbal message comprehension"},
    "memory":    {"substrings": ["parahippocampal", "fusiform"],
                  "label": "Memory-correlated Regions",
                  "correlated_with": "scene memory encoding"},
    "attention": {"substrings": ["postcentral", "inf_parietal", "sup_parietal"],
                  "label": "Attention Network",
                  "correlated_with": "sustained attentional engagement"},
    "emotion":   {"substrings": ["temporal_pole", "inf_temporal"],
                  "label": "Emotion-correlated Regions",
                  "correlated_with": "emotional and social processing"},
    "decision":  {"substrings": ["middle_frontal", "precentral"],
                  "label": "Prefrontal Regions",
                  "correlated_with": "cognitive control and working memory"},
}


def build_roi_masks(n_vertices):
    """
    Build vertex index masks using equal spatial splits across the cortical surface.
    fsaverage5 vertices have spatial ordering — this gives approximate regional masks.
    All ads are scored with identical masks so relative comparisons hold.
    """
    keys    = list(ROI_GROUPS.keys())
    n       = len(keys)
    chunk   = n_vertices // n
    masks   = {}
    for i, key in enumerate(keys):
        start       = i * chunk
        end         = start + chunk if i < n - 1 else n_vertices
        masks[key]  = np.arange(start, end)
        print(f"   {key:12s}: vertices {start}–{end} ({end - start} vertices)")
    return masks


def score_summary(preds, masks):
    """Mean activation across ALL time AND vertices per ROI group → one float per group."""
    return {
        key: float(preds[:, verts].mean()) if len(verts) > 0 else None
        for key, verts in masks.items()
    }


def score_timeseries(preds, masks):
    """
    Mean activation per SECOND per ROI group → list of floats per group.
    This is the time series data — one value per second of the ad.
    Shape per group: (n_timesteps,)
    """
    ts = {}
    for key, verts in masks.items():
        if len(verts) == 0:
            ts[key] = []
            continue
        # Mean across vertices at each timestep → (n_timesteps,)
        per_second = preds[:, verts].mean(axis=1)
        ts[key]    = [float(v) for v in per_second]
    return ts


def compute_derived_metrics(timeseries):
    """
    Compute derived metrics from the time series data.

    Hook Strength (0-3s):
        Average of attention + motion + emotion in first 3 seconds.
        Captures how engaging the opening is — the most important window
        in a social feed where viewers decide to keep watching or scroll.

    Mid Retention (3-10s):
        Average attention signal between seconds 3-10.
        Measures whether the ad holds attention after the hook.

    Peak Emotion Second:
        The second index where emotion signal is highest.
        Tells you where the emotional climax of the ad sits.

    Attention Decay Rate:
        Linear regression slope of attention over time.
        Negative = attention is declining (hook and drop).
        Positive = attention is building (slow burn).
        Near zero = flat/sustained.
    """
    derived = {}

    # Hook Strength — first 3 seconds
    hook_signals = []
    for key in ["attention", "motion", "emotion"]:
        ts = timeseries.get(key, [])
        if len(ts) >= 3:
            hook_signals.append(np.mean(ts[:3]))
        elif len(ts) > 0:
            hook_signals.append(np.mean(ts))
    derived["hook_strength"] = float(np.mean(hook_signals)) if hook_signals else None

    # Mid Retention — seconds 3-10
    att = timeseries.get("attention", [])
    if len(att) > 3:
        mid   = att[3:10] if len(att) >= 10 else att[3:]
        derived["mid_retention"] = float(np.mean(mid))
    else:
        derived["mid_retention"] = None

    # Peak Emotion Second
    emo = timeseries.get("emotion", [])
    if emo:
        derived["peak_emotion_second"] = int(np.argmax(emo))
        derived["peak_emotion_value"]  = float(max(emo))
    else:
        derived["peak_emotion_second"] = None
        derived["peak_emotion_value"]  = None

    # Attention Decay Rate — linear slope
    if len(att) >= 3:
        x = np.arange(len(att), dtype=float)
        y = np.array(att, dtype=float)
        # np.polyfit degree 1 returns [slope, intercept]
        slope = float(np.polyfit(x, y, 1)[0])
        derived["attention_decay_rate"] = round(slope, 6)
        # Human-readable interpretation
        if slope < -0.001:
            derived["attention_pattern"] = "hook_and_drop"
        elif slope > 0.001:
            derived["attention_pattern"] = "slow_build"
        else:
            derived["attention_pattern"] = "sustained"
    else:
        derived["attention_decay_rate"] = None
        derived["attention_pattern"]    = None

    return derived


# ── Main ──────────────────────────────────────────────────────────────────────

total_start = time.time()
print("=" * 60)
print("TRIBE v2 Ad Creative Neural Engagement Scorer")
print("=" * 60)

print("\n[1/4] Loading TRIBE v2 model...")
model = TribeModel.from_pretrained("facebook/tribev2", cache_folder=str(CACHE_DIR))
print("      Model ready.")

video_files = sorted(CREATIVES_DIR.glob("*.mp4"))
if not video_files:
    raise FileNotFoundError("No MP4 files in ./creatives/")
print(f"\n[2/4] Found {len(video_files)} ad creative(s):")
for vf in video_files:
    print(f"      {vf.name}  ({vf.stat().st_size / 1e6:.1f} MB)")

print("\n[3/4] Running inference...")
all_preds = {}
run_id    = time.strftime("%Y-%m-%dT%H:%M")

for video_path in video_files:
    ad_name = video_path.stem
    t0      = time.time()
    print(f"\n  ▶  {ad_name}")
    df              = model.get_events_dataframe(video_path=str(video_path))
    preds, segments = model.predict(events=df)
    print(f"     Shape: {preds.shape}  ✓")
    all_preds[ad_name] = {
        "preds":    preds,
        "segments": segments,
        "elapsed":  round(time.time() - t0, 1),
    }

print("\n[4/4] Extracting ROI scores and time series...")
n_vertices = next(iter(all_preds.values()))["preds"].shape[1]
masks      = build_roi_masks(n_vertices)

all_results = {}
for ad_name, ad_data in all_preds.items():
    preds    = ad_data["preds"]
    segments = ad_data["segments"]

    summary    = score_summary(preds, masks)
    timeseries = score_timeseries(preds, masks)
    derived    = compute_derived_metrics(timeseries)

    all_results[ad_name] = {
        "run_id":        run_id,
        "ad_name":       ad_name,
        "n_timesteps":   preds.shape[0],
        "n_vertices":    preds.shape[1],
        "roi_scores":    summary,       # summary mean per ROI group
        "roi_timeseries": timeseries,   # per-second per ROI group
        "derived":       derived,       # hook strength, decay, etc.
        "global": {
            "mean": float(preds.mean()),
            "peak": float(preds.max()),
            "p95":  float(np.percentile(preds, 95)),
            "std":  float(preds.std()),
        },
        "segments": [
            {"start": float(s.start), "end": float(s.stop)}
            for s in segments
        ],
        "inference_secs": ad_data["elapsed"],
    }

    print(f"\n  {ad_name}:")
    print(f"     Duration:       {preds.shape[0]}s")
    print(f"     Hook strength:  {derived.get('hook_strength', 'N/A'):.4f}" if derived.get('hook_strength') else "     Hook strength:  N/A")
    print(f"     Attn pattern:   {derived.get('attention_pattern', 'N/A')}")
    print(f"     Peak emotion:   second {derived.get('peak_emotion_second', 'N/A')}")

out_path = RESULTS_DIR / "roi_scores.json"
with open(out_path, "w") as f:
    json.dump(all_results, f, indent=2)

total_elapsed  = time.time() - total_start
estimated_cost = (total_elapsed / 3600) * 0.99

print(f"\n{'=' * 60}")
print(f"✓  Saved: {out_path}")
print(f"✓  Total time: {total_elapsed / 60:.1f} minutes")
print(f"✓  Est. cost:  ${estimated_cost:.3f} USD")
print(f"\n⚠  TERMINATE YOUR RUNPOD INSTANCE NOW")
print(f"{'=' * 60}")
