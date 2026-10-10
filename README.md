# Irodori-TTS v4 環境

[Aratako/Irodori-TTS](https://github.com/Aratako/Irodori-TTS)（Flow Matching ベースの日本語 TTS、v4 / v4.1 系）を
すぐ使えるようにするセットアップ用ラッパーです。上流コードは `Irodori-TTS/` に取得されます（git 管理外）。

## Windows + NVIDIA GPU（かんたん）

1. `windows\setup.bat` をダブルクリック（初回のみ。git が必要。uv は無ければ自動インストール。数GBのダウンロード）
2. `windows\start.bat` をダブルクリック → 日本語UIがブラウザで開きます
3. 本家の英語UIを使いたい場合は `start_original.bat`、声質をテキストで指定するUIは `start_voicedesign.bat`

### 日本語UIの機能

- **声の保存**: 参照音声をアップロードして名前を付け「この声を保存」→ 次回から「保存済みの声」から選ぶだけ（`voices\` フォルダに保存）
- **長文対応**: 文章は自動で文ごとに分けて生成しつなげるため、30秒を超えても、長い文でも内容が崩れにくくなります
- **長さの調整**: 生成後、スライダー（0.5〜2.0倍）で音程を変えずに尺を変更。離すと即反映
- **字幕(SRT)出力**: 入力テキストを句読点で短く区切り、音声の無音区間に合わせて時間を割り当て。`outputs\` に音声と同名の `.srt` を保存（1行の最大文字数は画面で変更可）
- 生成した音声・SRTは `outputs\` に保存されます

※ `voices\` は自分の作業データです。ZIPを再ダウンロードして置き換えるときは、先にこのフォルダを退避してください。

モデルは `hf_cache\` に保存されます。別モデルを使うなら `set MODEL=Aratako/Irodori-TTS-v4-Small` してから `setup.bat` / `start.bat` を実行してください。

## 手相ショート動画（Instagram リール 9:16）

`video/tesou_taiyousen.py` は、ナレーション wav と手のひら画像から 1080x1920 / 30fps の mp4 を作ります
（台本「太陽線があるのにお金がない理由」用）。必要なのは `uv` だけで、TTS のセットアップは不要です。

1. ナレーション `.wav` と手のひら画像 `.png` を **2つまとめて** `windows\make_tesou_video.bat` にドラッグ＆ドロップ
2. wav と同じフォルダに `同じ名前.mp4` と、テロップの時間を書いた `同じ名前.srt` ができます

内容: 冒頭は LINE 風の相談トーク画面 → 蓮・月・曼荼羅などの金色の線画アニメーション → 手のひら画像に太陽線を描くアニメーション → コメント欄で「太陽」→ 公式LINE への誘導。
テロップは台本どおりの位置でだけ改行し（自動で折り返さない）、50代以上でも読みやすい大きめの太字＋縁取り＋暗い帯にしています。

調整のしかた（コマンドプロンプトで `set` してから bat にドロップ、または直接 `python video\tesou_taiyousen.py 音声.wav 画像.png ...`）:

| やりたいこと | 方法 |
|---|---|
| 動画を作る前に静止画で確認 | `set PREVIEW=1`（`--preview`）→ `名前_preview\` に各テロップの場面と `palm_grid.png`（目盛り付きの手のひら画像）ができる |
| 太陽線の位置を直す | `palm_grid.png` の目盛りを見て `set SUNLINE=0.62,0.68 0.61,0.43`（`--sunline`。画像の左上0,0・右下1,1 の割合。2点以上、手首側→指側） |
| テロップのタイミングを直す | 出力された `.srt` の時間を編集して `set TIMINGS=C:\...\名前.srt`（`--timings`） |
| テロップの文言・改行 | `video/tesou_taiyousen.py` の `CUES`（`\n` が改行、`[ ]` が金色の強調） |

## セットアップ（Linux / Mac）

前提: `git`, [`uv`](https://docs.astral.sh/uv/)、Hugging Face へアクセスできるネットワーク。

```bash
scripts/setup.sh                    # NVIDIA CUDA 12.8 (既定) + モデル取得
BACKEND=cpu scripts/setup.sh        # CPU / macOS。他に rocm, xpu
```

環境変数:

| 変数 | 既定値 | 説明 |
|---|---|---|
| `BACKEND` | `cu128` | PyTorch バックエンド |
| `MODEL` | `Aratako/Irodori-TTS-v4.1-Small` | HF チェックポイント。`...-v4.1-Small-MF`（少ステップ）, `...-v4-Small` など |
| `UPSTREAM_REF` | `main` | 上流のブランチ/タグ/コミット（再現性のため固定推奨） |
| `SKIP_MODEL` | `0` | `1` でモデル事前ダウンロードを省略 |

## 使い方

```bash
# 参照音声でボイスクローン
scripts/infer.sh --text "こんにちは、私はAIです。" --ref-wav /abs/path/ref.wav --output-wav "$PWD/outputs/a.wav"
# 参照なし
scripts/infer.sh --text "こんにちは" --no-ref --output-wav "$PWD/outputs/b.wav"
# VoiceDesign (キャプションで声質指定)
scripts/infer.sh --text "こんにちは" --caption "落ち着いた、近い距離感の女性話者" --no-ref --output-wav "$PWD/outputs/c.wav"

# Web UI
scripts/gradio.sh ja        # 日本語UI http://localhost:7860
scripts/gradio.sh           # 本家UI http://localhost:7860 (ボイスクローン)
scripts/gradio.sh design    # http://localhost:7861 (VoiceDesign)
```

`infer.sh` は上流ディレクトリ内で実行されるため、相対パスは `Irodori-TTS/` 基準です。参照音声・出力先は絶対パスを推奨します。
その他のオプション（`--num-steps`, `--duration-scale`, LoRA, Speaker Inversion 等）は上流 README を参照してください。

OpenAI 互換 API サーバが必要なら [Aratako/Irodori-TTS-Server](https://github.com/Aratako/Irodori-TTS-Server) が別途あります。
