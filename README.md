# tribe-adcortex

> A time series diagnostic tool for ad creative testing using predicted fMRI brain signals.

Uses **TRIBE v2** (Meta FAIR, 2026) to predict second-by-second cortical brain responses to video ad creatives. Scores across 8 brain signal groups and computes derived engagement metrics — hook strength, attention decay, peak emotion timing — to help understand *how* engagement evolves over time, not just an overall score.

**Built by Tobi** · Python 3.12 · PostgreSQL · dbt · Streamlit · Docker · RunPod

---

## What it does

Takes 3–4 MP4 ad variants through TRIBE v2 on a rented GPU and outputs:

- **Per-second time series** — attention, emotion, memory signals over the duration of each ad
- **Derived metrics** — hook strength (0–3s), mid retention (3–10s), peak emotion second, attention decay rate
- **ROI group summaries** — 8 brain signal groups, mean activation across the full ad
- **Composite score** — exploratory summary across signal groups (not for outcome ranking)

The framing is diagnostic, not predictive: *"these signals are correlated with attention and memory processes"* — not *"this predicts purchase intent."*

---

## The time series insight

`preds` from TRIBE v2 has shape `(n_seconds, 20484)` — one prediction per second per cortical vertex. Collapsing this to a single mean discards the most actionable signal: how engagement changes over time.

Two ads can both average 0.05 but behave completely differently:
- **Ad A**: spikes at second 2, then drops — hook and drop pattern
- **Ad B**: slow build, peaks at second 12 — sustained engagement

The timeline view makes this visible. The derived metrics quantify it.

---

## Derived metrics

| Metric | Definition | Why it matters |
|---|---|---|
| Hook Strength | avg(attention + motion + emotion) in seconds 0–3 | The opening window — most critical in a feed |
| Mid Retention | avg(attention) in seconds 3–10 | Does the ad hold after the hook? |
| Peak Emotion Second | second index of highest emotion signal | Where the emotional climax sits |
| Attention Decay Rate | linear slope of attention over time | Negative = hook and drop, positive = slow build |
| Attention Pattern | hook_and_drop / slow_build / sustained | Human-readable classification |

---

## Honest framing

ROI vertex masks use approximate spatial splits — not named atlas parcels. Relative comparisons between ads scored in the same run are valid. Absolute values are not meaningful across experiments.

Safer language:
- ✓ "signals correlated with memory encoding"
- ✓ "predicted attentional activation"
- ✗ "predicts purchase intent"
- ✗ "measures brand recall"

---

## Stack

| Layer | Technology |
|---|---|
| Inference | TRIBE v2 · Python 3.12 · GPU (RunPod) |
| Database | PostgreSQL 16 · port 5435 |
| Transform | dbt (staging + mart) |
| Dashboard | Streamlit · port 8504 · 5 pages |
| Containers | Docker + docker-compose |

---

## App pages

| Page | What it does |
|---|---|
| **Main** | Dashboard — gauges, radar, heatmap, derived metrics, timeline charts, ROI deep dive |
| **Creatives** | Upload MP4s via drag and drop, label, preview, delete |
| **Inference** | Paste RunPod IP/port → one-click automated inference |
| **History** | Compare runs within a campaign |
| **Campaigns** | Create campaigns, assign runs, keep comparisons meaningful |

---

## Project structure

```
tribe-adcortex/
│
├── docker-compose.yml
├── .env.example
│
├── remote/
│   ├── run_tribe.py            # Inference + time series extraction → roi_scores.json
│   └── setup_pod.sh
│
├── results/
├── creatives/
│
├── scripts/
│   └── init.sql                # Schema: raw_roi_scores, roi_timeseries, derived_metrics, campaigns
│
├── app/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                 # Dashboard
│   ├── db.py                   # DB connection, JSON ingestion, timeseries queries
│   ├── charts.py               # Plotly charts incl. timeline and derived metrics table
│   ├── roi_labels.py
│   └── pages/
│       ├── 1_Creatives.py
│       ├── 2_Inference.py
│       ├── 3_History.py
│       └── 4_Campaigns.py
│
└── dbt/
    ├── dbt_project.yml
    ├── profiles.yml
    └── models/
        ├── sources.yml
        ├── staging/stg_roi_scores.sql
        └── mart/mart_ad_comparison.sql
```

---

## Running it

### Prerequisites

- Docker Desktop running
- RunPod account (~$5 credit)
- HuggingFace read token (`huggingface.co/settings/tokens`)
- SSH key at `~/.ssh/id_ed25519`

### Step 1 — Local setup

```bash
git clone https://github.com/adheir01/tribe-adcortex
cd tribe-adcortex
cp .env.example .env
# Edit .env: POSTGRES_PASSWORD and HF_TOKEN
docker-compose down && docker-compose up -d
# Dashboard at http://localhost:8504
```

### Step 2 — Creatives page

Upload MP4s via drag and drop. Label each one. Recommended: 15–30s each, vary one variable at a time (same concept, different hook / pacing / presence of human / motion).

### Step 3 — Inference page

Launch a RunPod pod (PyTorch 2.8, RTX 5090 or A100, 30GB disk, SSH enabled). Paste the IP and port. Click **Start inference run** — the app uploads files, runs TRIBE v2, streams live output, downloads results automatically.

Terminate the pod when done (~$0.60–$1.00 per run).

### Step 4 — Dashboard

Sidebar → select `roi_scores.json` → Load. Explore timeline charts, derived metrics, radar, heatmap, ROI deep dive.

### Step 5 — Campaigns

Create a campaign, assign the run to it. Use History to compare runs within the same campaign.

---

## Experiment design advice

The tool produces insight when you control variables. Compare:
- Same concept, different hook (first 3 seconds changed)
- Same concept, with vs without a person on screen
- Same concept, fast-cut vs slow pacing
- Same sport, different emotional tone

Avoid comparing completely different concepts — the scores tell you nothing actionable.

---

## The 8 brain signal groups

| Group | Correlated with |
|---|---|
| 👁 Visual | Visual attention and scene registration |
| ⚡ Motion | Dynamic scene processing — cuts, movement |
| 🎵 Auditory | Music and speech processing |
| 💬 Language | Verbal message comprehension |
| 🧠 Memory | Scene memory encoding |
| 🎯 Attention | Sustained attentional engagement |
| ❤️ Emotion | Emotional and social processing |
| ⚖️ Decision | Cognitive control and working memory |

Composite weights: Memory (30%) + Attention (25%) + Emotion (20%) + Decision (15%) + sensory (10%).

---

## Limitations

- Average subject prediction — individual and demographic variation not captured
- Trained on naturalistic film/speech, not commercial ads
- Approximate vertex splits, not named atlas parcels
- Scores meaningful within a run only — do not compare across experiments
- CC BY-NC 4.0 — non-commercial use only

---

## License note

Uses TRIBE v2 (`facebook/tribev2`) licensed under CC BY-NC 4.0. Portfolio and non-commercial research use only.

---

## Citation

```bibtex
@article{dAscoli2026TribeV2,
  title={A foundation model of vision, audition, and language for in-silico neuroscience},
  author={d'Ascoli, St{\'e}phane and Rapin, J{\'e}r{\'e}my and Benchetrit, Yohann
          and Brookes, Teon and Begany, Katelyn and Raugel, Jos{\'e}phine
          and Banville, Hubert and King, Jean-R{\'e}mi},
  year={2026}
}
```


