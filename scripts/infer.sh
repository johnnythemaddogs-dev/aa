#!/usr/bin/env bash
# 上流 infer.py のラッパー。引数はそのまま渡される。
#   scripts/infer.sh --text "こんにちは" --no-ref --output-wav "$PWD/outputs/a.wav"
#   scripts/infer.sh --text "こんにちは" --caption "落ち着いた女性" --no-ref --output-wav "$PWD/outputs/b.wav"
set -euo pipefail
source "$(dirname "$0")/env.sh"
mkdir -p "$ROOT/outputs"
cd "$UPSTREAM_DIR"
# 注意: 実行は上流ディレクトリ内。相対パスは Irodori-TTS/ 基準になるので、出力先は絶対パス推奨
exec uv run --no-sync python infer.py --hf-checkpoint "$MODEL" "$@"
