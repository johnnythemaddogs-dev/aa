#!/usr/bin/env bash
# Irodori-TTS (v4系) のセットアップ: 上流取得 → 依存インストール → モデル事前ダウンロード
set -euo pipefail
source "$(dirname "$0")/env.sh"

command -v uv >/dev/null || { echo "uv が必要です: https://docs.astral.sh/uv/" >&2; exit 1; }
command -v git >/dev/null || { echo "git が必要です" >&2; exit 1; }

if [ ! -d "$UPSTREAM_DIR/.git" ]; then
  git clone "$UPSTREAM_URL" "$UPSTREAM_DIR"
fi
git -C "$UPSTREAM_DIR" fetch --tags origin
git -C "$UPSTREAM_DIR" checkout "$UPSTREAM_REF"
[ "$UPSTREAM_REF" = main ] && git -C "$UPSTREAM_DIR" pull --ff-only origin main

cd "$UPSTREAM_DIR"
uv sync --extra "$BACKEND"

if [ "${SKIP_MODEL:-0}" != 1 ]; then
  uv run --no-sync python - <<PY
from huggingface_hub import snapshot_download
print("downloaded:", snapshot_download("$MODEL"))
PY
fi
echo "セットアップ完了 (backend=$BACKEND, model=$MODEL)"
