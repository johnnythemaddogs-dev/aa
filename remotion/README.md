# 手相ショート動画（Remotion 版）

台本「太陽線があるのにお金がない理由」の Instagram リール（1080x1920 / 30fps）を Remotion で作ります。

## かんたん（Windows）

ナレーション `.wav` と手のひら画像 `.png` を **2つまとめて** `windows\make_tesou_remotion.bat` にドラッグ＆ドロップ。
wav と同じフォルダに同じ名前の `.mp4` ができます（要 Node.js。初回は `npm install` が走ります）。

プレビューしながら調整したいときは、コマンドプロンプトで `set STUDIO=1` してからドロップ → ブラウザで Remotion Studio が開きます。

## 手動

```bash
cd remotion
npm install
# public/narration.wav と public/palm.png を置く
npm run studio   # プレビュー
npm run render   # out/tesou_taiyousen.mp4
```

## 調整

| やりたいこと | 場所 |
|---|---|
| テロップの文言・改行位置 | `src/script.ts` の `CUES`（`\n` が改行。それ以外では改行しない。`[ ]` は金色強調） |
| 太陽線の位置 | `src/script.ts` の `DEFAULT_SUNLINE`（画像内の割合 左上0,0 / 右下1,1、手首側→指側）。Studio の右パネルの props でも変更可 |
| テロップの時間 | 自動（音声の無音区間に合わせる）。直したいときは `public/timings.json` に `[[開始秒, 終了秒], ...]` を19個書く |
| 場面の切り替え位置 | `src/script.ts` の `SCENE_AT` |

フォントは Google Fonts（Zen Maru Gothic / しっぽり明朝 / BIZ UDPゴシック）を描画時に読み込みます（ネット接続が必要）。
