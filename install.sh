#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
echo "KAYRA installer — Apple Silicon/macOS"
if [[ "$(uname -s)" != "Darwin" ]]; then echo "Warning: designed for macOS; continuing."; fi
if [[ "$(uname -m)" != "arm64" ]]; then echo "Warning: Apple Silicon not detected."; fi
command -v python3 >/dev/null || { echo "Python 3.11+ required. Install from python.org or Homebrew."; exit 1; }
PY_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')
if (( PY_MINOR < 11 )); then echo "Python 3.11+ required; found $(python3 --version)"; exit 1; fi
command -v ffmpeg >/dev/null || { echo "FFmpeg missing. Install with: brew install ffmpeg"; exit 1; }
command -v ffprobe >/dev/null || { echo "ffprobe missing. Install with: brew install ffmpeg"; exit 1; }
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
mkdir -p input output temp logs models assets/logo assets/music
echo
echo "Installed. Add your original logo at assets/logo/kayra_logo.png."
echo "Add licensed instrumental music to assets/music/."
echo "See README.md for local model setup and LTX-2.3 MLX adapter contract."
