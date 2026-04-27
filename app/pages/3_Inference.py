"""
=============================================================================
pages/2_Inference.py — RunPod Inference Automation Page
=============================================================================

PURPOSE
-------
Semi-automated inference pipeline. You launch the RunPod pod manually
(one click on runpod.io), paste the IP and port here, and the app handles:
  1. Uploading run_tribe.py and MP4 files via SSH/SCP
  2. Running the inference script on the pod
  3. Streaming live output back to the dashboard
  4. Downloading roi_scores.json when done
  5. Showing a reminder to terminate the pod

WHY SEMI-AUTOMATED?
-------------------
The pod IP and port change every time you launch a new RunPod pod —
there's no way to know them in advance. Everything else is fully automated.

LIBRARY: paramiko
-----------------
paramiko is the standard Python SSH library. It lets Python:
  - Open an SSH connection to a remote server
  - Execute commands and stream the output back
  - Upload/download files (SCP equivalent)
This replaces the manual bash terminal session entirely.
"""

import json
import time
from pathlib import Path

import paramiko
import streamlit as st

st.set_page_config(
    page_title = "Inference | tribe-adcortex",
    page_icon  = "⚡",
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
.terminal {
    background: #0D1117;
    border: 1px solid rgba(67,97,238,0.3);
    border-radius: 8px;
    padding: 1rem 1.2rem;
    font-family: 'Courier New', monospace;
    font-size: 0.8rem;
    color: #58D68D;
    min-height: 200px;
    max-height: 500px;
    overflow-y: auto;
    white-space: pre-wrap;
    line-height: 1.6;
}
.status-card {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 10px;
    padding: 1.2rem 1.5rem;
    margin-bottom: 1rem;
}
.cost-warning {
    background: rgba(255,183,3,0.08);
    border: 1px solid rgba(255,183,3,0.3);
    border-radius: 8px;
    padding: 0.8rem 1.2rem;
    font-size: 0.85rem;
    color: #FCD34D;
}
.stButton > button {
    background: rgba(67,97,238,0.15);
    border: 1px solid rgba(67,97,238,0.4);
    color: #C8D6E5;
    border-radius: 6px;
    font-family: 'Space Mono', monospace;
    font-size: 0.8rem;
}
</style>
""", unsafe_allow_html=True)

# ── Paths ─────────────────────────────────────────────────────────────────────
CREATIVES_DIR  = Path("/app/creatives")
RESULTS_DIR    = Path("/app/results")
REMOTE_SCRIPT  = Path("/app/remote/run_tribe.py")
SSH_KEY_PATH   = Path.home() / ".ssh" / "id_ed25519"

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# ⚡ Run Inference")
st.markdown(
    '<div style="color:#6B7280; margin-bottom:1.5rem">'
    'Connects to your RunPod pod, uploads files, runs TRIBE v2, and downloads results automatically.'
    '</div>',
    unsafe_allow_html=True
)

# ── Pre-flight checks ─────────────────────────────────────────────────────────
st.markdown('<div class="section-label">Pre-flight checks</div>', unsafe_allow_html=True)

mp4_files    = sorted(CREATIVES_DIR.glob("*.mp4"))
has_script   = REMOTE_SCRIPT.exists()
has_ssh_key  = SSH_KEY_PATH.exists()

col1, col2, col3 = st.columns(3)
with col1:
    if mp4_files:
        st.success(f"✓ {len(mp4_files)} creative(s) ready")
    else:
        st.error("✗ No MP4 files in creatives/ — go to Creatives page first")

with col2:
    if has_script:
        st.success("✓ run_tribe.py found")
    else:
        st.error("✗ remote/run_tribe.py missing")

with col3:
    if has_ssh_key:
        st.success("✓ SSH key found")
    else:
        st.warning("⚠ ~/.ssh/id_ed25519 not found — check SSH key path below")

if not mp4_files or not has_script:
    st.stop()

st.divider()

# ── Pod connection ────────────────────────────────────────────────────────────
st.markdown('<div class="section-label">RunPod connection</div>', unsafe_allow_html=True)
st.markdown(
    '<div style="color:#6B7280; font-size:0.85rem; margin-bottom:1rem">'
    'Launch your pod on runpod.io first, then paste the connection details from the Connect tab.</div>',
    unsafe_allow_html=True
)

col_ip, col_port, col_key = st.columns([3, 1, 3])
with col_ip:
    pod_ip = st.text_input("Pod IP", placeholder="103.196.86.227", key="pod_ip")
with col_port:
    pod_port = st.number_input("Port", min_value=1, max_value=65535, value=10259, key="pod_port")
with col_key:
    ssh_key_path = st.text_input(
        "SSH key path",
        value    = str(SSH_KEY_PATH),
        key      = "ssh_key_path",
    )

st.divider()

# ── Cost estimate ─────────────────────────────────────────────────────────────
total_size_mb = sum(f.stat().st_size for f in mp4_files) / 1e6
est_inference_mins = len(mp4_files) * 8    # rough estimate: ~8 min per ad
est_cost = ((est_inference_mins + 15) / 60) * 0.99   # +15 min for setup

st.markdown(f"""
<div class="cost-warning">
⚠  Estimated run cost: <strong>${est_cost:.2f} USD</strong>
&nbsp;·&nbsp; {len(mp4_files)} ad(s) · ~{est_inference_mins + 15} minutes total
&nbsp;·&nbsp; RTX 5090 @ $0.99/hr
&nbsp;·&nbsp; Remember to terminate the pod when done
</div>
""", unsafe_allow_html=True)

st.markdown('<div style="height:1rem"></div>', unsafe_allow_html=True)

# ── Run button ────────────────────────────────────────────────────────────────
if not pod_ip:
    st.info("Enter the pod IP address above to continue.")
    st.stop()

run_clicked = st.button("🚀  Start inference run", use_container_width=True)

if not run_clicked:
    st.stop()

# ── SSH execution ─────────────────────────────────────────────────────────────
log_placeholder = st.empty()
log_lines       = []

def log(msg: str, color: str = "#58D68D"):
    timestamp = time.strftime("%H:%M:%S")
    log_lines.append(f"[{timestamp}] {msg}")
    log_placeholder.markdown(
        f'<div class="terminal">{"<br>".join(log_lines)}</div>',
        unsafe_allow_html=True
    )

st.markdown('<div class="section-label">Live output</div>', unsafe_allow_html=True)

try:
    # ── Connect ──────────────────────────────────────────────────────────────
    log("Connecting to pod...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname    = pod_ip,
        port        = int(pod_port),
        username    = "root",
        key_filename= str(ssh_key_path),
        timeout     = 30,
    )
    log(f"Connected to {pod_ip}:{pod_port} ✓")

    sftp = ssh.open_sftp()

    # ── Create remote directories ─────────────────────────────────────────────
    log("Creating remote directories...")
    for cmd in [
        "mkdir -p ~/tribe_scorer/creatives ~/tribe_scorer/results ~/tribe_scorer/cache",
    ]:
        _, stdout, stderr = ssh.exec_command(cmd)
        stdout.channel.recv_exit_status()
    log("Directories ready ✓")

    # ── Upload run_tribe.py ───────────────────────────────────────────────────
    log("Uploading run_tribe.py...")
    sftp.put(str(REMOTE_SCRIPT), "/root/tribe_scorer/run_tribe.py")
    log("run_tribe.py uploaded ✓")

    # ── Upload MP4 files ──────────────────────────────────────────────────────
    log(f"Uploading {len(mp4_files)} creative(s)...")
    for mp4 in mp4_files:
        log(f"  Uploading {mp4.name} ({mp4.stat().st_size/1e6:.1f} MB)...")
        sftp.put(str(mp4), f"/root/tribe_scorer/creatives/{mp4.name}")
        log(f"  {mp4.name} ✓")

    # ── Check if venv exists, set up if not ───────────────────────────────────
    log("Checking Python environment...")
    _, stdout, _ = ssh.exec_command("test -d ~/tribe_env && echo exists || echo missing")
    venv_status  = stdout.read().decode().strip()

    if venv_status == "missing":
        log("Virtual environment not found — running setup (this takes ~5 min)...")
        setup_cmd = """
            apt-get update -qq && apt-get install -y ffmpeg git curl -qq &&
            curl -LsSf https://astral.sh/uv/install.sh | sh &&
            export PATH="$HOME/.local/bin:$PATH" &&
            python3 -m venv ~/tribe_env &&
            source ~/tribe_env/bin/activate &&
            pip install -q "tribev2[plotting] @ git+https://github.com/facebookresearch/tribev2.git" &&
            pip install -q whisperx mne huggingface_hub hf_transfer &&
            echo SETUP_DONE
        """
        _, stdout, stderr = ssh.exec_command(setup_cmd, timeout=600)
        for line in stdout:
            line = line.strip()
            if line:
                log(f"  {line}")
        log("Environment ready ✓")
    else:
        log("Virtual environment found ✓")

    # ── Run inference ─────────────────────────────────────────────────────────
    log("Starting TRIBE v2 inference...")
    log("─" * 50)

    inference_cmd = "source ~/tribe_env/bin/activate && cd ~/tribe_scorer && python run_tribe.py"
    transport     = ssh.get_transport()
    channel       = transport.open_session()
    channel.exec_command(inference_cmd)

    # Stream output line by line
    import select
    start_time = time.time()
    while True:
        if channel.exit_status_ready():
            break
        r, _, _ = select.select([channel], [], [], 1.0)
        if r:
            while channel.recv_ready():
                chunk = channel.recv(4096).decode("utf-8", errors="replace")
                for line in chunk.splitlines():
                    if line.strip():
                        log(line)
        elapsed = time.time() - start_time
        if elapsed > 3600:   # 1 hour hard timeout
            log("⚠ Timeout — inference taking too long")
            break

    exit_status = channel.recv_exit_status()
    log("─" * 50)

    if exit_status != 0:
        log(f"⚠ Inference exited with status {exit_status}")
        remaining = channel.recv_stderr(65535).decode("utf-8", errors="replace")
        if remaining:
            log(remaining)
    else:
        log("Inference complete ✓")

    # ── Download results ──────────────────────────────────────────────────────
    log("Downloading roi_scores.json...")
    RESULTS_DIR.mkdir(exist_ok=True)
    local_results = RESULTS_DIR / "roi_scores.json"
    sftp.get("/root/tribe_scorer/results/roi_scores.json", str(local_results))
    log(f"Results saved to results/roi_scores.json ✓")

    sftp.close()
    ssh.close()

    # ── Done ──────────────────────────────────────────────────────────────────
    elapsed_mins = (time.time() - start_time) / 60
    est_actual_cost = (elapsed_mins / 60) * 0.99

    log("=" * 50)
    log(f"Run complete in {elapsed_mins:.1f} minutes")
    log(f"Estimated cost: ${est_actual_cost:.3f} USD")
    log("=" * 50)

    st.success("✓ Inference complete — results downloaded to results/roi_scores.json")

    st.markdown(f"""
    <div class="cost-warning">
    ⚠  <strong>TERMINATE YOUR RUNPOD POD NOW</strong><br>
    Go to runpod.io → Your Pods → Stop<br>
    Estimated cost this run: <strong>${est_actual_cost:.3f} USD</strong>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(
        '<div style="margin-top:1rem; color:#6B7280">Go to the <strong>Dashboard</strong> page, '
        'load the new roi_scores.json from the sidebar, and explore your results.</div>',
        unsafe_allow_html=True
    )

except paramiko.AuthenticationException:
    st.error("Authentication failed — check your SSH key path and that the key is added to RunPod.")
except Exception as conn_err:
    if "Unable to connect" in str(conn_err) or "Connection refused" in str(conn_err):
        st.error(f"Could not connect to {pod_ip}:{pod_port} — check the IP and port from the RunPod Connect tab.")
    else:
        raise
except Exception as e:
    st.error(f"Error: {e}")
    log(f"ERROR: {e}")
