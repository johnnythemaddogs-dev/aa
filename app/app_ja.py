#!/usr/bin/env python3
"""Irodori-TTS 日本語 Web UI (参照音声の保存 / 尺の調整 / ショート用SRT出力)。"""
from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import gradio as gr
import numpy as np
import soundfile as sf

APP_DIR = Path(__file__).resolve().parent
ROOT = APP_DIR.parent
IRODORI_DIR = Path(os.environ.get("IRODORI_DIR", ROOT / "Irodori-TTS"))
if str(IRODORI_DIR) not in sys.path:
    sys.path.insert(0, str(IRODORI_DIR))

import voices  # noqa: E402
from audiofx import time_stretch  # noqa: E402
from subtitles import build_cues_segmented, chunk_text, to_srt  # noqa: E402

OUT_DIR = ROOT / "outputs"
MODEL = os.environ.get("MODEL", "Aratako/Irodori-TTS-v4.1-Small")
NO_VOICE = "(参照音声なし)"


# ---------------------------------------------------------------- 声ライブラリ
def _voice_choices() -> list[str]:
    return [NO_VOICE, *voices.list_voices()]


def save_voice_ui(name: str, uploaded: str | None):
    try:
        saved = voices.save_voice(name, uploaded)
    except ValueError as exc:
        raise gr.Error(str(exc)) from exc
    gr.Info(f"「{saved}」を保存しました。")
    return gr.update(choices=_voice_choices(), value=saved), None, ""


def delete_voice_ui(name: str):
    if not name or name == NO_VOICE:
        raise gr.Error("削除する声を選んでください。")
    voices.delete_voice(name)
    gr.Info(f"「{name}」を削除しました。")
    return gr.update(choices=_voice_choices(), value=NO_VOICE)


def preview_voice(name: str):
    return voices.voice_path(name) if name and name != NO_VOICE else None


# ---------------------------------------------------------------- 後処理 (尺・SRT)
def postprocess(gen, scale, max_chars, strip_punct):
    """gen = {"path": 元wav, "segments": [[text, start, end], ...]}"""
    if not gen:
        return gr.skip(), gr.skip(), gr.skip(), gr.skip()
    y, sr = sf.read(gen["path"], dtype="float32", always_2d=False)
    scale = float(scale)
    orig = Path(gen["path"])
    if abs(scale - 1.0) < 1e-3:
        final_path = orig
        y2 = y
    else:
        y2 = time_stretch(y, 1.0 / scale)  # 長さ倍率 scale → 速さ 1/scale
        final_path = orig.with_name(f"{orig.stem}_x{scale:.2f}.wav")
        sf.write(final_path, y2, sr)
    cues = build_cues_segmented(gen["segments"], y2, sr, int(max_chars), bool(strip_punct),
                                time_scale=len(y2) / len(y))
    srt_text = to_srt(cues)
    srt_path = final_path.with_suffix(".srt")
    srt_path.write_text(srt_text, encoding="utf-8")
    info = f"長さ: {len(y2) / sr:.2f} 秒 (元: {len(y) / sr:.2f} 秒) / 字幕: {len(cues)} 行"
    return str(final_path), info, srt_text, str(srt_path)


# ---------------------------------------------------------------- 音声生成
def _num(raw, cast, label):
    raw = (raw or "").strip()
    if not raw:
        return None
    try:
        return cast(raw)
    except ValueError as exc:
        raise gr.Error(f"{label}は数値で入力してください。") from exc


def generate(text, voice, uploaded, caption, seed_raw, steps_raw, cfg_text, cfg_speaker, cfg_caption,
             precision, chunk_chars, gap_sec, scale, max_chars, strip_punct, progress=gr.Progress()):
    text = (text or "").strip()
    if not text:
        raise gr.Error("読み上げるテキストを入力してください。")
    seed = _num(seed_raw, int, "シード")
    steps = _num(steps_raw, int, "ステップ数")

    ref = uploaded or (voices.voice_path(voice) if voice != NO_VOICE else None)
    try:
        from irodori_tts.inference_runtime import (
            RuntimeKey, SamplingRequest, default_runtime_device,
            download_hf_checkpoint, get_cached_runtime,
        )
    except ImportError as exc:
        raise gr.Error(f"Irodori-TTS が見つかりません。setup.bat を実行してください。({exc})") from exc

    progress(0.05, desc="モデルを準備中（初回は時間がかかります）")
    device = default_runtime_device()
    key = RuntimeKey(
        checkpoint=str(download_hf_checkpoint(MODEL)),
        model_device=device,
        model_precision=precision,
        codec_device=device,
        codec_precision="fp32",
    )
    runtime, _ = get_cached_runtime(key)

    chunks = chunk_text(text, int(chunk_chars))
    if not chunks:
        raise gr.Error("読み上げるテキストがありません。")
    parts: list[np.ndarray] = []
    segments: list[list] = []
    sr = None
    pos = 0.0
    used_seed = seed
    for i, chunk in enumerate(chunks):
        progress(0.1 + 0.8 * i / len(chunks), desc=f"音声を生成中 ({i + 1}/{len(chunks)})")
        result = runtime.synthesize(SamplingRequest(
            text=chunk,
            caption=(caption or "").strip() or None,
            ref_wavs=[ref] if ref else None,
            no_ref=ref is None,
            seed=used_seed,  # 2つ目以降は同じシードにして声質を揃える
            num_steps=steps,
            cfg_scale_text=float(cfg_text),
            cfg_scale_caption=float(cfg_caption),
            # 参照音声がないとき話者ガイダンスを効かせると音が崩れるため、本家UIと同様に0にする
            cfg_scale_speaker=float(cfg_speaker) if ref else 0.0,
            trim_tail=True,
        ), log_fn=lambda m: print(m, flush=True))
        used_seed = result.used_seed
        sr = result.sample_rate
        a = result.audios[0].float().cpu().numpy()
        a = a[0] if a.ndim == 2 and a.shape[0] == 1 else (a.mean(axis=0) if a.ndim == 2 else a)
        if parts:  # チャンク間の無音
            gap = np.zeros(int(sr * float(gap_sec)), dtype=np.float32)
            parts.append(gap)
            pos += len(gap) / sr
        segments.append([chunk, pos, pos + len(a) / sr])
        parts.append(a.astype(np.float32))
        pos += len(a) / sr

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    orig = OUT_DIR / f"{stamp}.wav"
    sf.write(orig, np.concatenate(parts), sr)
    gen = {"path": str(orig), "segments": segments}

    progress(0.95, desc="字幕を作成中")
    path, info, srt_text, srt_path = postprocess(gen, scale, max_chars, strip_punct)
    info = f"{info} / {len(chunks)} 分割で生成 / シード: {used_seed}"
    return path, gen, info, srt_text, srt_path


# ---------------------------------------------------------------- UI
def build_ui() -> gr.Blocks:
    with gr.Blocks(title="Irodori-TTS 日本語UI") as demo:
        gr.Markdown("# Irodori-TTS 音声生成\nテキストを読み上げ、長さの調整とショート動画用の字幕(SRT)出力までできます。")
        gen_state = gr.State(None)

        with gr.Row():
            with gr.Column(scale=5):
                text = gr.Textbox(label="読み上げるテキスト", lines=6,
                                  placeholder="ここに文章を入力（長文は自動で分割して生成します）")

                with gr.Group():
                    gr.Markdown("### 声の選択")
                    voice = gr.Dropdown(label="保存済みの声", choices=_voice_choices(), value=NO_VOICE)
                    voice_preview = gr.Audio(label="選んだ声の試聴", interactive=False, type="filepath")
                    uploaded = gr.Audio(label="新しい参照音声（アップロードすると、こちらが優先されます）",
                                        type="filepath", sources=["upload", "microphone"])
                    with gr.Row():
                        save_name = gr.Textbox(label="保存する名前", scale=3, placeholder="例: 私の声")
                        save_btn = gr.Button("この声を保存", scale=1)
                        del_btn = gr.Button("選んだ声を削除", scale=1, variant="stop")

                caption = gr.Textbox(label="声のイメージ指示（任意）", lines=1,
                                     placeholder="例: 落ち着いた、近い距離感の女性話者")
                with gr.Accordion("詳細設定", open=False):
                    with gr.Row():
                        seed = gr.Textbox(label="シード（空欄でランダム）")
                        steps = gr.Textbox(label="ステップ数（空欄で標準）")
                        precision = gr.Dropdown(label="計算精度", choices=["fp32", "bf16"], value="fp32",
                                                info="bf16は高速・省メモリですが、CPUでは使えません")
                    with gr.Row():
                        chunk_chars = gr.Slider(20, 120, value=50, step=5, label="1回に生成する文字数",
                                                info="長い文章は自動で文ごとに分けて生成し、つなげます。短いほど内容は正確ですが、間が増えます。")
                        gap_sec = gr.Slider(0.0, 1.0, value=0.3, step=0.05, label="分割部分の無音（秒）")
                    cfg_text = gr.Slider(0, 10, value=3.0, step=0.1, label="テキストへの忠実さ")
                    cfg_speaker = gr.Slider(0, 10, value=5.0, step=0.1, label="参照音声への近さ")
                    cfg_caption = gr.Slider(0, 10, value=4.0, step=0.1, label="声のイメージ指示への忠実さ")
                gen_btn = gr.Button("音声を生成", variant="primary", size="lg")

            with gr.Column(scale=5):
                out_audio = gr.Audio(label="生成した音声", type="filepath", interactive=False)
                info = gr.Markdown("")
                scale = gr.Slider(0.5, 2.0, value=1.0, step=0.01, label="長さの調整（倍率）",
                                  info="1.0=そのまま / 0.8=短く(速く) / 1.2=長く(ゆっくり)。音程は変わりません。離すと反映されます。")
                gr.Markdown("### 字幕 (SRT)")
                with gr.Row():
                    max_chars = gr.Slider(6, 30, value=14, step=1, label="1行の最大文字数")
                    strip_punct = gr.Checkbox(value=True, label="句読点・かっこを字幕から除く")
                srt_text = gr.Textbox(label="SRTプレビュー", lines=10, interactive=False)
                srt_file = gr.File(label="SRTファイルをダウンロード", interactive=False)

        voice.change(preview_voice, voice, voice_preview)
        save_btn.click(save_voice_ui, [save_name, uploaded], [voice, uploaded, save_name])
        del_btn.click(delete_voice_ui, voice, voice)

        post_in = [gen_state, scale, max_chars, strip_punct]
        post_out = [out_audio, info, srt_text, srt_file]
        gen_btn.click(
            generate,
            [text, voice, uploaded, caption, seed, steps, cfg_text, cfg_speaker, cfg_caption,
             precision, chunk_chars, gap_sec, scale, max_chars, strip_punct],
            [out_audio, gen_state, info, srt_text, srt_file],
        )
        scale.release(postprocess, post_in, post_out)
        max_chars.release(postprocess, post_in, post_out)
        strip_punct.input(postprocess, post_in, post_out)
    return demo


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--server-name", default="127.0.0.1")
    ap.add_argument("--server-port", type=int, default=7860)
    ap.add_argument("--open", action="store_true", help="起動後にブラウザを開く")
    args = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    voices.VOICE_DIR.mkdir(parents=True, exist_ok=True)
    build_ui().queue().launch(server_name=args.server_name, server_port=args.server_port,
                              inbrowser=args.open,
                              allowed_paths=[str(OUT_DIR), str(voices.VOICE_DIR)])


if __name__ == "__main__":
    main()
