# Irodori-TTS v4 環境

[Aratako/Irodori-TTS](https://github.com/Aratako/Irodori-TTS)（Flow Matching ベースの日本語 TTS、v4 / v4.1 系）を
すぐ使えるようにするセットアップ用ラッパーです。上流コードは `Irodori-TTS/` に取得されます（git 管理外）。

## セットアップ

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
scripts/gradio.sh           # http://localhost:7860 (ボイスクローン)
scripts/gradio.sh design    # http://localhost:7861 (VoiceDesign)
```

`infer.sh` は上流ディレクトリ内で実行されるため、相対パスは `Irodori-TTS/` 基準です。参照音声・出力先は絶対パスを推奨します。
その他のオプション（`--num-steps`, `--duration-scale`, LoRA, Speaker Inversion 等）は上流 README を参照してください。

OpenAI 互換 API サーバが必要なら [Aratako/Irodori-TTS-Server](https://github.com/Aratako/Irodori-TTS-Server) が別途あります。
