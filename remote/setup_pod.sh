#!/bin/bash
# =============================================================================
# RunPod Pod Setup Script — TRIBE v2 Neural Engagement Scorer
# =============================================================================
#
# Run this ONCE after SSH-ing into your RunPod A100 pod.
# Installs all dependencies and creates the working directory.
#
# Usage:
#   bash setup_pod.sh
#
# After this completes, upload your ad files and run_tribe.py:
#   scp -P <port> remote/run_tribe.py root@<ip>:~/tribe_scorer/
#   scp -P <port> creatives/*.mp4 root@<ip>:~/tribe_scorer/creatives/
#   cd ~/tribe_scorer && python run_tribe.py
# =============================================================================

set -e   # exit immediately if any command fails

echo "=============================================="
echo " TRIBE v2 Pod Setup"
echo "=============================================="

# ── System dependencies ───────────────────────────────────────────────────────
# ffmpeg is required by moviepy (video frame extraction) and WhisperX (audio)
echo "[1/5] Installing system packages..."
apt-get update -qq
apt-get install -y ffmpeg git curl

# ── uv package manager ────────────────────────────────────────────────────────
# uv is significantly faster than pip — consistent with your other projects
echo "[2/5] Installing uv..."
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc

# ── Working directory ─────────────────────────────────────────────────────────
echo "[3/5] Creating project directories..."
mkdir -p ~/tribe_scorer/creatives ~/tribe_scorer/results ~/tribe_scorer/cache
cd ~/tribe_scorer

# ── Python dependencies ───────────────────────────────────────────────────────
# tribev2[plotting] installs the full package including brain visualisation deps:
#   nibabel, nilearn, seaborn, pyvista, scikit-image
# whisperx is separate — it handles speech-to-text with word-level timestamps
# mne is needed by utils_fmri.py for the HCP MMP atlas download
echo "[4/5] Installing Python packages (this takes ~5 minutes)..."
uv pip install --system \
    "tribev2[plotting] @ git+https://github.com/facebookresearch/tribev2.git"

uv pip install --system \
    whisperx \
    mne \
    huggingface_hub

# ── HuggingFace authentication ────────────────────────────────────────────────
# The facebook/tribev2 model weights are hosted on HuggingFace.
# You need a read-scope token from https://huggingface.co/settings/tokens
# The HF_TOKEN env var is the non-interactive way to authenticate.
echo "[5/5] HuggingFace authentication..."
if [ -n "$HF_TOKEN" ]; then
    huggingface-cli login --token "$HF_TOKEN"
    echo "      Authenticated with HF_TOKEN env var."
else
    echo "      HF_TOKEN not set — running interactive login..."
    huggingface-cli login
fi

# ── Verify GPU ────────────────────────────────────────────────────────────────
echo ""
echo "Verifying GPU availability..."
python -c "
import torch
if torch.cuda.is_available():
    print(f'  GPU: {torch.cuda.get_device_name(0)}')
    print(f'  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB')
    print(f'  CUDA: {torch.version.cuda}')
else:
    print('  WARNING: No GPU detected — inference will be extremely slow')
"

echo ""
echo "=============================================="
echo " Setup complete!"
echo " Next steps:"
echo "   scp your ad MP4s into ~/tribe_scorer/creatives/"
echo "   scp run_tribe.py into ~/tribe_scorer/"
echo "   python run_tribe.py"
echo "=============================================="
