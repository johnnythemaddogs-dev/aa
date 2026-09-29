"""テキストと音声から、ショート動画向けの SRT を作る (音声認識は使わない)。

1. テキストを句読点で短い字幕に分割する
2. 音声の無音区間を検出し、文字数に比例した位置を近くの無音区間に合わせる
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np

_EMOJI = re.compile("[\U0001F000-\U0001FAFF☀-➿️‍]")
_SENT_END = set("。！？!?")
_CLOSERS = set("」』）)】”")
_SOFT = set("、，,")
_STRIP_PUNCT = re.compile("[。、，,「」『』（）()【】]")
_PAUSE = {"。": 3.0, "！": 3.0, "？": 3.0, "!": 3.0, "?": 3.0, "、": 1.5, "，": 1.5, ",": 1.5, "…": 2.0}


@dataclass
class Cue:
    start: float
    end: float
    text: str


def _split_sentences(text: str) -> list[str]:
    out: list[str] = []
    buf = ""
    i = 0
    while i < len(text):
        ch = text[i]
        if ch == "\n":
            if buf.strip():
                out.append(buf)
            buf = ""
        else:
            buf += ch
            if ch in _SENT_END:
                while i + 1 < len(text) and (text[i + 1] in _SENT_END or text[i + 1] in _CLOSERS):
                    i += 1
                    buf += text[i]
                out.append(buf)
                buf = ""
        i += 1
    if buf.strip():
        out.append(buf)
    return [s.strip() for s in out if s.strip()]


_PARTICLES = set("はがをにでともへやかてね")
_NO_HEAD = set("ゃゅょっゎぁぃぅぇぉー～、。！？!?」』）")


def _split_balanced(p: str, max_chars: int) -> list[str]:
    """長い断片を、助詞の直後など自然な位置で中央付近から二分して再帰的に分ける。"""
    if len(p) <= max_chars:
        return [p]
    mid = len(p) / 2
    cands = [
        i for i in range(3, len(p) - 2)
        if p[i - 1] in _PARTICLES and p[i] not in _NO_HEAD
    ]
    if cands:
        cut = min(cands, key=lambda i: abs(i - mid))
    else:
        cut = math.ceil(len(p) / 2)
    return _split_balanced(p[:cut], max_chars) + _split_balanced(p[cut:], max_chars)


def _split_long(sentence: str, max_chars: int) -> list[str]:
    if len(sentence) <= max_chars:
        return [sentence]
    pieces: list[str] = []
    buf = ""
    for ch in sentence:
        buf += ch
        if ch in _SOFT:
            pieces.append(buf)
            buf = ""
    if buf:
        pieces.append(buf)
    merged: list[str] = []
    for p in pieces:
        if merged and len(merged[-1]) + len(p) <= max_chars:
            merged[-1] += p
        else:
            merged.append(p)
    out: list[str] = []
    for p in merged:
        if len(p) <= max_chars:
            out.append(p)
        else:
            out.extend(_split_balanced(p, max_chars))
    return out


def chunk_text(text: str, max_chars: int = 50) -> list[str]:
    """TTS用に、文の区切りを保ったまま max_chars 程度のかたまりに分ける。"""
    max_chars = max(10, int(max_chars))
    chunks: list[str] = []
    for sent in _split_sentences(text):
        for piece in _split_long(sent, max_chars):
            if chunks and len(chunks[-1]) + len(piece) <= max_chars:
                chunks[-1] += piece
            else:
                chunks.append(piece)
    return chunks


def _weight(raw: str) -> float:
    w = 0.0
    for ch in raw:
        if ch in _PAUSE:
            w += _PAUSE[ch]
        elif ch.isspace() or ch in "「」『』（）()【】":
            continue
        elif "一" <= ch <= "鿿":
            w += 2.2  # 漢字は読みが長め
        elif ch.isascii() and ch.isalnum():
            w += 1.5
        else:
            w += 1.0
    return max(w, 0.5)


def split_cues(text: str, max_chars: int = 14, strip_punct: bool = True) -> list[tuple[str, float]]:
    """(表示テキスト, 重み) のリスト。"""
    text = _EMOJI.sub("", text)
    cues: list[tuple[str, float]] = []
    for sent in _split_sentences(text):
        for piece in _split_long(sent, max(4, int(max_chars))):
            shown = _STRIP_PUNCT.sub("", piece) if strip_punct else piece
            shown = shown.strip()
            if shown:
                cues.append((shown, _weight(piece)))
    return cues


def analyze_audio(y: np.ndarray, sr: int) -> tuple[float, float, list[tuple[float, float]]]:
    """(発話開始, 発話終了, 内部の無音区間[(s,e)])。"""
    y = y if y.ndim == 1 else y.mean(axis=1)
    dur = len(y) / sr
    hop = max(1, int(sr * 0.01))
    n = len(y) // hop
    if n < 2:
        return 0.0, dur, []
    rms = np.sqrt((y[: n * hop].reshape(n, hop) ** 2).mean(axis=1))
    peak = float(rms.max())
    if peak <= 1e-6:
        return 0.0, dur, []
    silent = rms < peak * 10 ** (-38 / 20)
    runs: list[tuple[int, int]] = []
    i = 0
    while i < n:
        if silent[i]:
            j = i
            while j < n and silent[j]:
                j += 1
            runs.append((i, j))
            i = j
        else:
            i += 1
    start, end = 0.0, dur
    inner: list[tuple[float, float]] = []
    for a, b in runs:
        if a == 0:
            start = b * 0.01
        elif b == n:
            end = a * 0.01
        elif (b - a) >= 8:  # 80ms 以上
            inner.append((a * 0.01, b * 0.01))
    if end <= start:
        return 0.0, dur, []
    return start, end, inner


def build_cues(text: str, y: np.ndarray, sr: int, max_chars: int = 14, strip_punct: bool = True) -> list[Cue]:
    items = split_cues(text, max_chars, strip_punct)
    if not items:
        return []
    start, end, silences = analyze_audio(y, sr)
    total = sum(w for _, w in items)
    mids = [(s + e) / 2 for s, e in silences]
    used: set[int] = set()
    bounds = [start]
    cum = 0.0
    span = end - start
    for k, (_, w) in enumerate(items[:-1]):
        cum += w
        target = start + span * cum / total
        window = min(0.7, 0.45 * span * w / total + 0.25)
        best = None
        for idx, m in enumerate(mids):
            if idx in used or m <= bounds[-1] + 0.15 or m >= end - 0.15:
                continue
            d = abs(m - target)
            if d <= window and (best is None or d < best[0]):
                best = (d, idx, m)
        if best:
            used.add(best[1])
            bounds.append(best[2])
        else:
            bounds.append(max(target, bounds[-1] + 0.15))
    bounds.append(end)
    return [Cue(bounds[i], max(bounds[i + 1], bounds[i] + 0.1), items[i][0]) for i in range(len(items))]


def build_cues_segmented(segments, y: np.ndarray, sr: int, max_chars: int = 14,
                         strip_punct: bool = True, time_scale: float = 1.0) -> list[Cue]:
    """segments=[(text,start,end)] (元音声の秒)。各区間の実際の位置で字幕を作る。"""
    cues: list[Cue] = []
    for text, st, en in segments:
        a, b = int(st * time_scale * sr), int(en * time_scale * sr)
        part = y[a:b]
        if len(part) < sr * 0.05:
            continue
        for c in build_cues(text, part, sr, max_chars, strip_punct):
            cues.append(Cue(c.start + a / sr, c.end + a / sr, c.text))
    return cues


def _ts(sec: float) -> str:
    ms = int(round(sec * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def to_srt(cues: list[Cue]) -> str:
    blocks = [f"{i}\n{_ts(c.start)} --> {_ts(c.end)}\n{c.text}\n" for i, c in enumerate(cues, 1)]
    return "\n".join(blocks)
