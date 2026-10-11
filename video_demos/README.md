# 猫の愛情表現で見る動画編集デモ（31種・各約5秒）

`index.html` をブラウザで開くと一覧で再生できます。

- `scripts/render_cats.py` … 猫のアニメーション素材（6シーン）を描画して `src/` に出力
- `scripts/make_audio.py` / `scripts/make_stickers.py` … BGM・効果音・ステッカー画像を生成
- `scripts/edit_demos.sh [番号...]` … ffmpeg で各編集デモを `out/` に書き出し

```bash
cd video_demos
for s in blink headbump knead tail green closeup; do python3 scripts/render_cats.py src $s; done
python3 scripts/make_audio.py src && python3 scripts/make_stickers.py src
scripts/edit_demos.sh        # 全部。scripts/edit_demos.sh 03 17 のように個別も可
```
