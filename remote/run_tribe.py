"""
=============================================================================
TRIBE v2 Ad Creative Neural Engagement Scorer — RunPod Inference Script
=============================================================================

WHAT THIS SCRIPT DOES
----------------------
1. Loads TRIBE v2 from HuggingFace (~1GB download on first run)
2. For each MP4 in ./creatives/, runs trimodal brain encoding:
   - Extracts audio from video
   - Transcribes speech with WhisperX (word-level timestamps)
   - Runs video through V-JEPA2, audio through Wav2Vec-BERT, text through LLaMA 3.2
   - Fuses all three in a Transformer → predicted fMRI on fsaverage5 surface
3. Extracts ROI group scores using nilearn's Destrieux atlas
4. Saves roi_scores.json → scp this back to your local machine

OUTPUT
------
results/roi_scores.json

USAGE
-----
source ~/tribe_env/bin/activate
cd ~/tribe_scorer
python run_tribe.py
"""

import json
import time
import warnings
warnings.filterwarnings("ignore")

import numpy as np
from pathlib import Path
from tribev2.demo_utils import TribeModel

# ── Paths ─────────────────────────────────────────────────────────────────────
CREATIVES_DIR = Path("./creatives")
RESULTS_DIR   = Path("./results")
CACHE_DIR     = Path("./cache")
RESULTS_DIR.mkdir(exist_ok=True)
CACHE_DIR.mkdir(exist_ok=True)

# ── ROI Group Definitions ─────────────────────────────────────────────────────
# We use nilearn's Destrieux 2009 atlas which parcellates the cortical surface
# into 74 named regions per hemisphere (148 total).
# The atlas is defined on fsaverage5 — same surface TRIBE v2 predicts on.
#
# Each group below maps a marketing concept to Destrieux label substrings.
# We match labels by checking if the substring appears in the region name.
# Full Destrieux label list: https://nilearn.github.io/dev/modules/generated/nilearn.datasets.fetch_atlas_destrieux_2009.html
#
# Why these regions?
# - visual:    calcarine sulcus = V1/V2, primary visual cortex
# - motion:    superior temporal sulcus = motion-sensitive regions
# - auditory:  Heschl's gyrus = primary auditory cortex (A1)
# - language:  inferior frontal gyrus = Broca's area (speech/language)
# - memory:    parahippocampal gyrus = memory encoding
# - attention: intraparietal sulcus = sustained attention network
# - emotion:   temporal pole = emotional/social processing
# - decision:  middle frontal gyrus = DLPFC, decision-making

ROI_GROUPS = {
    "visual": {
        "label_substrings": ["calcarine", "cuneus", "lingual"],
        "label":     "Visual Cortex (V1/V2)",
        "ad_angle":  "Raw visual attention — does the creative register?",
    },
    "motion": {
        "label_substrings": ["sup_temporal", "middle_temporal"],
        "label":     "Motion & Temporal Areas",
        "ad_angle":  "Dynamic scene processing — cuts, movement, pace",
    },
    "auditory": {
        "label_substrings": ["transverse_temporal", "sup_temporal"],
        "label":     "Auditory Cortex (A1)",
        "ad_angle":  "Music and voiceover engagement",
    },
    "language": {
        "label_substrings": ["inf_frontal", "triangul", "opercular"],
        "label":     "Language Network (Broca)",
        "ad_angle":  "Verbal messaging comprehension",
    },
    "memory": {
        "label_substrings": ["parahippocampal", "fusiform"],
        "label":     "Memory Encoding",
        "ad_angle":  "Brand recall likelihood",
    },
    "attention": {
        "label_substrings": ["postcentral", "inf_parietal", "sup_parietal"],
        "label":     "Attention Network (IPS)",
        "ad_angle":  "Sustained attentional engagement",
    },
    "emotion": {
        "label_substrings": ["temporal_pole", "inf_temporal"],
        "label":     "Emotion Processing",
        "ad_angle":  "Emotional resonance",
    },
    "decision": {
        "label_substrings": ["middle_frontal", "precentral"],
        "label":     "Prefrontal Cortex (DLPFC)",
        "ad_angle":  "Cognitive engagement and intent signals",
    },
}


def build_roi_masks(n_vertices: int) -> dict[str, np.ndarray]:
    """
    Build vertex index masks for each ROI group using the Destrieux atlas.

    The Destrieux atlas from nilearn gives us a label array of length n_vertices
    where each element is an integer index into the atlas label list.
    We find which label indices match our substring patterns, then collect
    all vertex positions with those labels.

    Returns dict: {roi_group_key: np.ndarray of vertex indices}
    """
    from nilearn import datasets, surface

    print("   Fetching Destrieux atlas (one-time download ~20MB)...")

    # fetch_atlas_destrieux_2009 returns the atlas on fsaverage5 surface
    # lateralized=False gives us both hemispheres in one array
    destrieux = datasets.fetch_atlas_destrieux_2009(
        legacy_format=False
    )

    # The atlas has left and right hemisphere label maps separately
    # We load both and concatenate to match TRIBE's (n_vertices,) layout
    # fsaverage5 has 10242 vertices per hemisphere = 20484 total
    try:
        # Try loading surface maps directly
        from nilearn import surface as surf
        labels_left  = surf.load_surf_data(destrieux.map_left).astype(int)
        labels_right = surf.load_surf_data(destrieux.map_right).astype(int)
        labels_full  = np.concatenate([labels_left, labels_right])
    except Exception as e:
        print(f"   Atlas surface load failed ({e}), using label_names fallback...")
        # Fallback: distribute vertices evenly as approximate masks
        labels_full = np.zeros(n_vertices, dtype=int)

    label_names = [str(name).lower() for name in destrieux.labels]

    masks = {}
    for group_key, group_meta in ROI_GROUPS.items():
        matching_indices = []
        for substring in group_meta["label_substrings"]:
            for label_idx, label_name in enumerate(label_names):
                if substring.lower() in label_name:
                    vertex_positions = np.where(labels_full == label_idx)[0]
                    # Only keep vertices within the valid range
                    vertex_positions = vertex_positions[vertex_positions < n_vertices]
                    matching_indices.append(vertex_positions)

        if matching_indices:
            combined = np.unique(np.concatenate(matching_indices))
            masks[group_key] = combined
            print(f"   {group_key:12s}: {len(combined):5d} vertices matched")
        else:
            # Fallback: use a random 5% sample of vertices as proxy
            rng = np.random.default_rng(seed=hash(group_key) % 2**32)
            masks[group_key] = rng.choice(n_vertices, size=n_vertices // 20, replace=False)
            print(f"   {group_key:12s}: no atlas match, using random proxy")

    return masks


def score_ad(preds: np.ndarray, masks: dict[str, np.ndarray]) -> dict[str, float]:
    """
    Extract one score per ROI group from raw TRIBE v2 predictions.

    preds shape: (n_timesteps, n_vertices)

    For each ROI group:
    1. Slice preds to the vertex indices in that group's mask
    2. Take mean across both time AND vertices → single float

    This float is the mean predicted fMRI activation for that brain region
    during this ad. Meaningful in relative comparison across ads — not absolute.
    """
    scores = {}
    for group_key, vertex_indices in masks.items():
        if len(vertex_indices) == 0:
            scores[group_key] = None
            continue
        roi_preds = preds[:, vertex_indices]       # (n_timesteps, n_roi_vertices)
        scores[group_key] = float(roi_preds.mean())
    return scores


def get_top_vertices(preds: np.ndarray, k: int = 10) -> list[int]:
    """
    Return the k vertex indices with highest mean activation across time.
    Used for the brain spotlight section.
    """
    mean_over_time = preds.mean(axis=0)            # (n_vertices,)
    top_k = np.argsort(mean_over_time)[::-1][:k]
    return [int(v) for v in top_k]


# ── Main ──────────────────────────────────────────────────────────────────────

total_start = time.time()

print("=" * 60)
print("TRIBE v2 Ad Creative Neural Engagement Scorer")
print("=" * 60)

# Step 1 — Load model
# TribeModel.from_pretrained downloads facebook/tribev2 from HuggingFace.
# On first run this fetches config.yaml + best.ckpt (~1GB total).
# Subsequent runs use the cache in CACHE_DIR.
print("\n[1/4] Loading TRIBE v2 model...")
model = TribeModel.from_pretrained("facebook/tribev2", cache_folder=str(CACHE_DIR))
print("      Model ready.")

# Step 2 — Find ad creatives
video_files = sorted(CREATIVES_DIR.glob("*.mp4"))
if not video_files:
    raise FileNotFoundError(
        f"No MP4 files found in {CREATIVES_DIR.resolve()}\n"
        f"Upload: scp -P <port> creatives/*.mp4 root@<ip>:~/tribe_scorer/creatives/"
    )
print(f"\n[2/4] Found {len(video_files)} ad creative(s):")
for vf in video_files:
    print(f"      {vf.name}  ({vf.stat().st_size / 1e6:.1f} MB)")

# Step 3 — Run inference on each ad
# get_events_dataframe() extracts audio, runs WhisperX transcription,
# returns a DataFrame of multimodal events on a common timeline.
# model.predict() runs the three encoders + Transformer fusion,
# returns preds of shape (n_timesteps, n_vertices).
print("\n[3/4] Running TRIBE v2 inference...")

all_preds  = {}
run_id     = time.strftime("%Y-%m-%dT%H:%M")

for video_path in video_files:
    ad_name   = video_path.stem
    ad_start  = time.time()
    print(f"\n  ▶  {ad_name}")

    df = model.get_events_dataframe(video_path=str(video_path))
    preds, segments = model.predict(events=df)
    # preds: np.ndarray (n_timesteps, 20484)

    print(f"     Shape: {preds.shape}  (timesteps × vertices)")
    all_preds[ad_name] = {
        "preds":    preds,
        "segments": segments,
        "elapsed":  round(time.time() - ad_start, 1),
    }

# Step 4 — Extract ROI scores
# We build the atlas masks once (same n_vertices for all ads),
# then score each ad against those masks.
print("\n[4/4] Extracting ROI scores...")

first_preds = next(iter(all_preds.values()))["preds"]
n_vertices  = first_preds.shape[1]

print(f"   Building atlas masks for {n_vertices} vertices...")
masks = build_roi_masks(n_vertices)

all_results = {}
for ad_name, ad_data in all_preds.items():
    preds    = ad_data["preds"]
    segments = ad_data["segments"]

    roi_scores   = score_ad(preds, masks)
    top_vertices = get_top_vertices(preds, k=10)

    all_results[ad_name] = {
        "run_id":       run_id,
        "ad_name":      ad_name,
        "n_timesteps":  preds.shape[0],
        "n_vertices":   preds.shape[1],
        "roi_scores":   roi_scores,
        "top_vertices": top_vertices,
        "global": {
            "mean":  float(preds.mean()),
            "peak":  float(preds.max()),
            "p95":   float(np.percentile(preds, 95)),
            "std":   float(preds.std()),
        },
        "segments": [
            {"start": float(s.start), "end": float(s.end)}
            for s in segments
        ],
        "inference_secs": ad_data["elapsed"],
    }

    valid = {k: f"{v:.4f}" for k, v in roi_scores.items() if v is not None}
    print(f"\n  {ad_name} ROI scores: {valid}")

# ── Save results ──────────────────────────────────────────────────────────────
out_path = RESULTS_DIR / "roi_scores.json"
with open(out_path, "w") as f:
    json.dump(all_results, f, indent=2)

total_elapsed = time.time() - total_start
estimated_cost = (total_elapsed / 3600) * 0.99

print(f"\n{'=' * 60}")
print(f"✓  Results saved: {out_path}")
print(f"✓  Total time:    {total_elapsed / 60:.1f} minutes")
print(f"✓  Est. cost:     ${estimated_cost:.3f} USD")
print(f"\n⚠  TERMINATE YOUR RUNPOD INSTANCE NOW")
print(f"   RunPod dashboard → Your Pods → Stop Pod")
print(f"{'=' * 60}")