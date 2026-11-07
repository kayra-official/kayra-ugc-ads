#!/bin/bash
set -euo pipefail
cd "$(dirname "$0")"
[[ -d .venv ]] || { echo "Run ./install.sh first."; exit 1; }
source .venv/bin/activate
command -v ffmpeg >/dev/null || { echo "FFmpeg missing. Install with brew install ffmpeg"; exit 1; }
python -c 'import gradio, PIL, yaml' || { echo "Dependencies missing; run ./install.sh"; exit 1; }
exec python app.py
