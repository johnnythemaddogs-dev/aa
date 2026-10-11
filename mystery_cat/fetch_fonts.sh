#!/usr/bin/env bash
# Shippori Mincho（SIL Open Font License）を fonts/ に取得する
set -euo pipefail
cd "$(dirname "$0")/fonts"
for f in Bold Medium ExtraBold; do
  curl -sSfL -o "ShipporiMincho-$f.ttf" "https://raw.githubusercontent.com/google/fonts/main/ofl/shipporimincho/ShipporiMincho-$f.ttf"
done
