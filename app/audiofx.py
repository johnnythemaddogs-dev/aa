"""音程を変えずに再生時間だけ変える (位相ボコーダ, numpy のみ)。"""
from __future__ import annotations

import numpy as np


def _stretch_mono(y: np.ndarray, rate: float, n_fft: int = 2048, hop: int = 512) -> np.ndarray:
    win = np.hanning(n_fft + 1)[:-1].astype(np.float64)
    pad = n_fft // 2
    x = np.pad(y.astype(np.float64), (pad, pad + n_fft), mode="reflect")
    n_frames = 1 + (len(x) - n_fft) // hop
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n_frames)[:, None]
    spec = np.fft.rfft(x[idx] * win, axis=1).T  # (bins, frames)
    bins = spec.shape[0]
    steps = np.arange(0, spec.shape[1] - 1, rate)
    adv = np.linspace(0, np.pi * hop, bins)
    phase = np.angle(spec[:, 0])
    out = np.empty((bins, len(steps)), dtype=np.complex128)
    for t, step in enumerate(steps):
        i = int(step)
        frac = step - i
        a, b = spec[:, i], spec[:, i + 1]
        mag = (1 - frac) * np.abs(a) + frac * np.abs(b)
        out[:, t] = mag * np.exp(1j * phase)
        d = np.angle(b) - np.angle(a) - adv
        d -= 2 * np.pi * np.round(d / (2 * np.pi))
        phase = phase + adv + d
    frames = np.fft.irfft(out.T, n=n_fft, axis=1) * win
    length = hop * (len(steps) - 1) + n_fft
    y_out = np.zeros(length)
    norm = np.zeros(length)
    for t in range(len(steps)):
        s = t * hop
        y_out[s : s + n_fft] += frames[t]
        norm[s : s + n_fft] += win**2
    y_out /= np.maximum(norm, 1e-8)
    target = int(round(len(y) / rate))
    y_out = y_out[pad : pad + target]
    if len(y_out) < target:
        y_out = np.pad(y_out, (0, target - len(y_out)))
    return y_out.astype(np.float32)


def time_stretch(y: np.ndarray, rate: float) -> np.ndarray:
    """rate>1 で短く(速く)、rate<1 で長く(ゆっくり)。"""
    if abs(rate - 1.0) < 1e-3:
        return y
    if y.ndim == 1:
        return _stretch_mono(y, rate)
    return np.stack([_stretch_mono(y[:, c], rate) for c in range(y.shape[1])], axis=1)
