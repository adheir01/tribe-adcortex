# tribe-adcortex

> Predict which ad creative your audience's brain will actually engage with — before spending the media budget.

Uses **TRIBE v2** (Meta FAIR, 2026) to run predicted fMRI brain encoding on video ad creatives and scores them across 8 neurologically grounded regions: visual attention, motion processing, auditory engagement, language comprehension, memory encoding, sustained attention, emotional resonance, and prefrontal decision circuits.

**Built by Tobi** · Python 3.12 · PostgreSQL · dbt · Streamlit · Docker · RunPod

---

## What it does

Takes 3–4 MP4 ad variants, runs them through TRIBE v2 on a rented GPU, and outputs a dashboard showing which creative produces the strongest predicted neural engagement — specifically in the brain regions most associated with memory encoding and purchase intent.

The pipeline costs ~$2–3 in GPU compute per run.

---

## How TRIBE v2 works

TRIBE v2 is a multimodal brain encoding model trained on 500+ hours of real fMRI data from 700+ subjects. Given a video, it predicts the cortical brain response an average person would show — across 20,484 vertices on the fsaverage5 surface.

Three encoders process the stimulus in parallel:

| Encoder | Input | What it captures |
|---|---|---|
| V-JEPA2 | Video frames | Visual features, motion, scene content |
| Wav2Vec-BERT | Audio track | Speech, music, environmental sounds |
| LLaMA 3.2 | Transcript | Semantics, language meaning |

A Transformer fuses all three and outputs `preds` — shape `(n_seconds, 20484)`. One predicted fMRI value per second per cortical vertex.

Predictions represent an **average subject** — not demographic-specific. Individual variation is not captured.

---

## Stack

| Layer | Technology |
|---|---|
| Inference | TRIBE v2 · Python 3.12 · GPU (RunPod) |
| Database | PostgreSQL 16 · port 5435 |
| Transform | dbt (staging + mart) |
| Dashboard | Streamlit · port 8504 |
| Containers | Docker + docker-compose |

---

## Project structure

```
tribe-adcortex/
│
├── docker-compose.yml
├── .env.example
│
├── remote/
│   ├── run_tribe.py            # Inference + ROI extraction → roi_scores.json
│   └── setup_pod.sh            # One-time pod environment setup
│
├── results/                    # Drop roi_scores.json here after scp
├── creatives/                  # MP4 ad variants — not committed to git
│
├── scripts/
│   └── init.sql
│
├── app/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── db.py
│   ├── charts.py
│   └── roi_labels.py
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
- RunPod account with credits (~$5 is enough)
- HuggingFace account + read token (`huggingface.co/settings/tokens`)
- SSH key pair (`~/.ssh/id_ed25519`)

### Step 1 — Local setup

```bash
git clone https://github.com/adheir01/tribe-adcortex
cd tribe-adcortex

cp .env.example .env
# Edit .env: set POSTGRES_PASSWORD and HF_TOKEN

docker-compose down
docker-compose up -d
# Dashboard at http://localhost:8504
```

### Step 2 — Prepare creatives

Drop MP4 files into `creatives/`. Name them `ad_a.mp4`, `ad_b.mp4`, `ad_c.mp4` etc. Recommended: 15–30 seconds each.

### Step 3 — RunPod inference

**Launch a pod on runpod.io:**
- Template: PyTorch 2.8.0
- GPU: RTX 5090 or A100 PCIe (32GB+ VRAM)
- Container disk: 30GB · Volume disk: 0GB
- Enable SSH terminal access

**Pod setup (one time per pod):**
```bash
ssh root@<pod-ip> -p <port> -i ~/.ssh/id_ed25519

apt-get update -qq && apt-get install -y ffmpeg git curl
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
mkdir -p ~/tribe_scorer/creatives ~/tribe_scorer/results ~/tribe_scorer/cache

python3 -m venv ~/tribe_env && source ~/tribe_env/bin/activate
pip install "tribev2[plotting] @ git+https://github.com/facebookresearch/tribev2.git"
pip install whisperx mne huggingface_hub hf_transfer
hf auth login
```

**Upload files (local machine, second terminal):**
```bash
scp -P <port> -i ~/.ssh/id_ed25519 remote/run_tribe.py root@<pod-ip>:~/tribe_scorer/
scp -P <port> -i ~/.ssh/id_ed25519 creatives/*.mp4 root@<pod-ip>:~/tribe_scorer/creatives/
```

**Run inference:**
```bash
source ~/tribe_env/bin/activate
cd ~/tribe_scorer && python run_tribe.py
```

**Download results — then terminate the pod immediately:**
```bash
scp -P <port> -i ~/.ssh/id_ed25519 root@<pod-ip>:~/tribe_scorer/results/roi_scores.json ./results/
```

### Step 4 — Load results

1. Open `http://localhost:8504`
2. Sidebar → select `roi_scores.json` → **Load into database**
3. Sidebar → select the run timestamp

### Step 5 — dbt (optional)

```bash
pip install dbt-postgres
cd dbt && dbt run --profiles-dir .
```

---

## The 8 brain ROI groups

| Group | What it measures for ads |
|---|---|
| 👁 Visual | Raw visual attention |
| ⚡ Motion | Dynamic scene processing — cuts, movement |
| 🎵 Auditory | Music and voiceover engagement |
| 💬 Language | Verbal messaging comprehension |
| 🧠 Memory | Brand recall likelihood |
| 🎯 Attention | Sustained attentional engagement |
| ❤️ Emotion | Emotional resonance |
| ⚖️ Decision | Cognitive engagement and intent signals |

Composite score weights: Memory (30%) + Attention (25%) + Emotion (20%) + Decision (15%) + sensory (10%).

---

## Limitations

- Predicts for an **average subject** — individual and demographic variation not captured
- Trained on naturalistic film/speech, not commercial ads specifically
- ROI vertex masks use approximate spatial splits — valid for relative comparison, not exact named region attribution
- Scores are meaningful **within a run only**
- **CC BY-NC 4.0** — non-commercial use only

---

## License note

This project uses TRIBE v2 (`facebook/tribev2`) licensed under CC BY-NC 4.0. For portfolio and non-commercial research use only.

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
