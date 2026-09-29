# 共通設定 (他のスクリプトから source される)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM_URL="${UPSTREAM_URL:-https://github.com/Aratako/Irodori-TTS.git}"
UPSTREAM_REF="${UPSTREAM_REF:-main}"          # タグやコミットで固定可能
UPSTREAM_DIR="${UPSTREAM_DIR:-$ROOT/Irodori-TTS}"
# cu128 | cpu | rocm | xpu
BACKEND="${BACKEND:-cu128}"
# 他: Aratako/Irodori-TTS-v4.1-Small-MF (少ステップ), Aratako/Irodori-TTS-v4-Small
MODEL="${MODEL:-Aratako/Irodori-TTS-v4.1-Small}"
