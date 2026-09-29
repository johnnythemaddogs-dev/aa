#!/usr/bin/env bash
# Web UI 起動。  scripts/gradio.sh          → 標準(ボイスクローン) :7860
#                scripts/gradio.sh design   → VoiceDesign(キャプション) :7861
set -euo pipefail
source "$(dirname "$0")/env.sh"
cd "$UPSTREAM_DIR"
case "${1:-standard}" in
  design) exec uv run --no-sync python gradio_app_voicedesign.py --server-name "${HOST:-0.0.0.0}" --server-port "${PORT:-7861}" ;;
  *)      exec uv run --no-sync python gradio_app.py --server-name "${HOST:-0.0.0.0}" --server-port "${PORT:-7860}" ;;
esac
