"""参照音声の保存ライブラリ (voices/ フォルダにファイルとして保存)。"""
from __future__ import annotations

import re
import shutil
from pathlib import Path

VOICE_DIR = Path(__file__).resolve().parent.parent / "voices"
AUDIO_EXT = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac"}


def _clean(name: str) -> str:
    name = re.sub(r'[\\/:*?"<>|\s]+', "_", (name or "").strip()).strip("._")
    if not name:
        raise ValueError("保存名を入力してください。")
    return name


def list_voices() -> list[str]:
    if not VOICE_DIR.exists():
        return []
    return sorted(p.stem for p in VOICE_DIR.iterdir() if p.suffix.lower() in AUDIO_EXT)


def voice_path(name: str) -> str | None:
    if not name:
        return None
    for p in VOICE_DIR.glob(f"{name}.*") if VOICE_DIR.exists() else []:
        if p.suffix.lower() in AUDIO_EXT and p.stem == name:
            return str(p)
    return None


def save_voice(name: str, src: str) -> str:
    if not src:
        raise ValueError("保存する参照音声をアップロードしてください。")
    name = _clean(name)
    VOICE_DIR.mkdir(parents=True, exist_ok=True)
    delete_voice(name)  # 同名は上書き
    dst = VOICE_DIR / f"{name}{Path(src).suffix.lower() or '.wav'}"
    shutil.copyfile(src, dst)
    return name


def delete_voice(name: str) -> None:
    p = voice_path(name)
    if p:
        Path(p).unlink()
