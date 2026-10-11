"""デモ用の BGM と効果音を合成する（外部素材なし）。

bgm.wav   : オルゴール風のやさしいメロディ（8 秒）
chime.wav : ハートが出る瞬間の「キラン」
pop.wav   : ステッカーが出る「ポン」
"""
import sys
import wave
from pathlib import Path

import numpy as np

SR = 48000


def save(path, x):
    x = np.clip(x / (np.abs(x).max() + 1e-9) * 0.8, -1, 1)
    st = np.stack([x, x], axis=1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((st * 32767).astype(np.int16).tobytes())


def bell(freq, dur, decay=3.0):
    t = np.arange(int(dur * SR)) / SR
    env = np.exp(-decay * t) * np.minimum(1, t / 0.005)
    return env * (np.sin(2 * np.pi * freq * t) + 0.35 * np.sin(2 * np.pi * freq * 2.01 * t)
                  + 0.12 * np.sin(2 * np.pi * freq * 3.98 * t))


def note(n):
    return 440 * 2 ** ((n - 69) / 12)


def bgm(dur=8.0):
    out = np.zeros(int(dur * SR))
    beat = 0.375  # 160 BPM の 8 分音符
    melody = [76, 79, 84, 83, 79, 76, 77, 79, 81, 79, 77, 74, 72, 74, 76, 79,
              76, 79, 84, 86, 84, 83, 81, 79, 77, 76, 74, 72, 74, 72, 71, 72]
    bass = [48, 55, 53, 55, 45, 52, 53, 55]
    for i, m in enumerate(melody):
        s = int(i * beat * SR / 1.5 * 1.5)
        if s >= len(out):
            break
        b = bell(note(m), 1.2, 3.5) * 0.5
        e = min(len(out), s + len(b))
        out[s:e] += b[: e - s]
    for i, m in enumerate(bass):
        s = int(i * beat * 4 * SR)
        if s >= len(out):
            break
        b = bell(note(m), 1.6, 2.0) * 0.35
        e = min(len(out), s + len(b))
        out[s:e] += b[: e - s]
    return out


def chime():
    out = np.zeros(int(1.2 * SR))
    for i, m in enumerate([88, 91, 96]):
        s = int(i * 0.07 * SR)
        b = bell(note(m), 1.0, 5)
        out[s:s + len(b)] += b[: len(out) - s]
    return out


def pop():
    t = np.arange(int(0.18 * SR)) / SR
    f = 900 * np.exp(-18 * t) + 250
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-22 * t)


if __name__ == "__main__":
    d = Path(sys.argv[1])
    d.mkdir(parents=True, exist_ok=True)
    save(d / "bgm.wav", bgm())
    save(d / "chime.wav", chime())
    save(d / "pop.wav", pop())
    print("audio ok")
