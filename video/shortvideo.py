"""縦型ショート動画 (1080x1920) を Pillow + ffmpeg で描くための部品。

- フォント検索 (Windows / Linux)
- テロップ: 改行は台本側で指定した位置だけ。収まらなければ折り返さず文字を小さくする
- 線画: 折れ線を「描いていく」アニメーション + 光のにじみ (glow)
- ffmpeg へ RGB フレームを流し込んで mp4 を作る
"""
from __future__ import annotations

import math
import os
import re
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H, FPS = 1080, 1920, 30

_WIN = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
GOTHIC_BOLD = [
    _WIN / "BIZ-UDGothicB.ttc", _WIN / "YuGothB.ttc", _WIN / "meiryob.ttc", _WIN / "msgothic.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
]
GOTHIC = [
    _WIN / "BIZ-UDGothicR.ttc", _WIN / "YuGothM.ttc", _WIN / "meiryo.ttc", _WIN / "msgothic.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
]
MINCHO = [
    _WIN / "BIZ-UDMinchoM.ttc", _WIN / "yumindb.ttf", _WIN / "yumin.ttf", _WIN / "msmincho.ttc",
    "/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc",
    "/usr/share/fonts/opentype/ipafont-mincho/ipam.ttf",
] + GOTHIC_BOLD


def find_font(candidates, override: str | None = None) -> str:
    for c in ([override] if override else []) + list(candidates):
        if c and Path(c).is_file():
            return str(c)
    sys.exit("日本語フォントが見つかりません。--font でフォントファイルを指定してください。")


_font_cache: dict[tuple[str, int], ImageFont.FreeTypeFont] = {}


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    key = (path, int(size))
    if key not in _font_cache:
        _font_cache[key] = ImageFont.truetype(path, int(size))
    return _font_cache[key]


# ---------------------------------------------------------------- easing

def clamp(x: float, a: float = 0.0, b: float = 1.0) -> float:
    return a if x < a else b if x > b else x


def prog(t: float, start: float, dur: float) -> float:
    return clamp((t - start) / dur) if dur > 0 else float(t >= start)


def ease_out(x: float) -> float:
    return 1 - (1 - clamp(x)) ** 3


def ease_in_out(x: float) -> float:
    x = clamp(x)
    return 4 * x ** 3 if x < 0.5 else 1 - (-2 * x + 2) ** 3 / 2


def ease_back(x: float) -> float:
    x = clamp(x)
    c = 1.70158
    return 1 + (c + 1) * (x - 1) ** 3 + c * (x - 1) ** 2


# ---------------------------------------------------------------- colors

def hex_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def vertical_gradient(top: str, bottom: str, size=(W, H)) -> Image.Image:
    a, b = np.array(hex_rgb(top), float), np.array(hex_rgb(bottom), float)
    k = np.linspace(0, 1, size[1])[:, None]
    col = (a * (1 - k) + b * k).astype(np.uint8)
    arr = np.repeat(col[:, None, :], size[0], axis=1)
    return Image.fromarray(arr, "RGB")


def radial_glow(radius: int, color: str, strength: float = 1.0) -> Image.Image:
    """中心が明るい丸い光 (RGBA)。"""
    n = radius * 2
    yy, xx = np.mgrid[0:n, 0:n]
    d = np.sqrt((xx - radius) ** 2 + (yy - radius) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 2 * 255 * strength
    img = Image.new("RGBA", (n, n), hex_rgb(color) + (0,))
    img.putalpha(Image.fromarray(a.astype(np.uint8), "L"))
    return img


def with_alpha(img: Image.Image, alpha: float) -> Image.Image:
    if alpha >= 0.999:
        return img
    out = img.copy()
    out.putalpha(out.getchannel("A").point(lambda v: int(v * clamp(alpha))))
    return out


def paste(frame: Image.Image, img: Image.Image, center: tuple[float, float], alpha: float = 1.0,
          scale: float = 1.0) -> None:
    if alpha <= 0.003 or scale <= 0.01:
        return
    if abs(scale - 1) > 1e-3:
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.LANCZOS)
    img = with_alpha(img, alpha)
    x, y = int(center[0] - img.width / 2), int(center[1] - img.height / 2)
    frame.alpha_composite(img, (x, y)) if frame.mode == "RGBA" else frame.paste(img, (x, y), img)


# ---------------------------------------------------------------- line art

def _seg_len(p, q):
    return math.hypot(q[0] - p[0], q[1] - p[1])


def partial(path: list[tuple[float, float]], t: float) -> list[tuple[float, float]]:
    """折れ線の先頭から長さの割合 t までを返す。"""
    t = clamp(t)
    if t >= 1 or len(path) < 2:
        return path
    lens = [_seg_len(path[i], path[i + 1]) for i in range(len(path) - 1)]
    goal = sum(lens) * t
    out = [path[0]]
    acc = 0.0
    for i, L in enumerate(lens):
        if acc + L >= goal:
            r = (goal - acc) / L if L else 0
            p, q = path[i], path[i + 1]
            out.append((p[0] + (q[0] - p[0]) * r, p[1] + (q[1] - p[1]) * r))
            return out
        acc += L
        out.append(path[i + 1])
    return out


def circle_path(cx, cy, r, start_deg=-90.0, sweep=360.0, n=None) -> list[tuple[float, float]]:
    n = n or max(24, int(abs(sweep) / 360 * r * 0.6))
    return [(cx + r * math.cos(math.radians(start_deg + sweep * i / n)),
             cy + r * math.sin(math.radians(start_deg + sweep * i / n))) for i in range(n + 1)]


def bezier(p0, p1, p2, p3, n=28) -> list[tuple[float, float]]:
    pts = []
    for i in range(n + 1):
        u = i / n
        a, b, c, d = (1 - u) ** 3, 3 * u * (1 - u) ** 2, 3 * u ** 2 * (1 - u), u ** 3
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return pts


def smooth(points: list[tuple[float, float]], n: int = 16) -> list[tuple[float, float]]:
    """Catmull-Rom で点列をなめらかな曲線にする。"""
    if len(points) < 3:
        return points
    p = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for k in range(n):
            u = k / n
            out.append(tuple(0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * u + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * u ** 2
                                    + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * u ** 3) for j in range(2)))
    out.append(points[-1])
    return out


def rotate(path, cx, cy, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in path]


def sparkle(cx, cy, r) -> list[list[tuple[float, float]]]:
    """4方向にのびるキラッとした星。"""
    k = r * 0.18
    pts = []
    for i in range(4):
        a = math.radians(i * 90 - 90)
        b = math.radians(i * 90 - 45)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
        pts.append((cx + k * math.cos(b), cy + k * math.sin(b)))
    pts.append(pts[0])
    return [pts]


def star5(cx, cy, r, rot=0.0) -> list[tuple[float, float]]:
    pts = []
    for i in range(11):
        rr = r if i % 2 == 0 else r * 0.42
        a = math.radians(-90 + rot + i * 36)
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


class LineLayer:
    """線画を 2 倍解像度のマスクに描き、縮小してなめらかにしてから色と光をのせる。"""

    SS = 2

    def __init__(self, color: str, glow: float = 0.9, glow_radius: float = 7):
        self.color = hex_rgb(color)
        self.glow = glow
        self.glow_radius = glow_radius
        self.mask = Image.new("L", (W * self.SS, H * self.SS), 0)
        self.d = ImageDraw.Draw(self.mask)
        self.dirty = False

    def path(self, pts, t: float = 1.0, width: float = 3.0, alpha: float = 1.0) -> None:
        if t <= 0 or alpha <= 0.003 or len(pts) < 2:
            return
        pts = partial(pts, t)
        if len(pts) < 2:
            return
        s = self.SS
        sp = [(x * s, y * s) for x, y in pts]
        w = max(1, int(round(width * s)))
        self.d.line(sp, fill=int(255 * clamp(alpha)), width=w, joint="curve")
        if w >= 4:
            r = w / 2
            for x, y in (sp[0], sp[-1]):
                self.d.ellipse((x - r, y - r, x + r, y + r), fill=int(255 * clamp(alpha)))
        self.dirty = True

    def paths(self, paths, t: float = 1.0, width: float = 3.0, alpha: float = 1.0, sequential: bool = True) -> None:
        """複数の線を描く。sequential なら順番に、そうでなければ同時に描き進める。"""
        if not sequential:
            for p in paths:
                self.path(p, t, width, alpha)
            return
        lens = [sum(_seg_len(p[i], p[i + 1]) for i in range(len(p) - 1)) for p in paths]
        total = sum(lens) or 1
        goal = clamp(t) * total
        acc = 0.0
        for p, L in zip(paths, lens):
            if goal <= acc:
                break
            self.path(p, (goal - acc) / L if L else 1, width, alpha)
            acc += L

    def dot(self, x, y, r, alpha=1.0):
        s = self.SS
        self.d.ellipse(((x - r) * s, (y - r) * s, (x + r) * s, (y + r) * s), fill=int(255 * clamp(alpha)))
        self.dirty = True

    def composite(self, frame: Image.Image) -> None:
        if not self.dirty:
            return
        m = self.mask.resize((W, H), Image.BILINEAR)
        solid = Image.new("RGB", (W, H), self.color)
        if self.glow > 0:
            small = m.resize((W // 4, H // 4), Image.BILINEAR).filter(ImageFilter.GaussianBlur(self.glow_radius / 2))
            g = small.resize((W, H), Image.BILINEAR).point(lambda v: min(255, int(v * 2.2 * self.glow)))
            frame.paste(solid, (0, 0), g)
        frame.paste(solid, (0, 0), m)


# ---------------------------------------------------------------- telop

_MARK = re.compile(r"\[([^\]]+)\]")


def parse_marked(line: str) -> list[tuple[str, bool]]:
    """"あなたの[太陽線]" → [("あなたの", False), ("太陽線", True)]"""
    out, pos = [], 0
    for m in _MARK.finditer(line):
        if m.start() > pos:
            out.append((line[pos:m.start()], False))
        out.append((m.group(1), True))
        pos = m.end()
    if pos < len(line):
        out.append((line[pos:], False))
    return out


def plain(text: str) -> str:
    return _MARK.sub(r"\1", text)


def render_telop(text: str, font_path: str, size: int = 76, max_width: int = 960,
                 color="#FFFFFF", accent="#FFD976", stroke="#1B0F33",
                 band: str | None = "#160D2E", band_alpha: int = 165, line_gap: float = 0.32) -> Image.Image:
    """テロップ画像 (RGBA)。改行は text 内の \\n のみ。幅を超える行があれば全体を縮小する。"""
    lines = text.split("\n")
    while True:
        f = font(font_path, size)
        widths = [sum(f.getlength(s) for s, _ in parse_marked(ln)) for ln in lines]
        if max(widths) <= max_width or size <= 40:
            break
        size -= 2
    sw = max(4, size // 11)
    lh = int(size * (1 + line_gap))
    pad_x, pad_y = 44, 30
    bw = int(max(widths)) + pad_x * 2 + sw * 2
    bh = lh * len(lines) - int(size * line_gap) + pad_y * 2 + sw * 2
    img = Image.new("RGBA", (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if band:
        d.rounded_rectangle((0, 0, bw - 1, bh - 1), radius=min(40, bh // 3), fill=hex_rgb(band) + (band_alpha,))
    for i, ln in enumerate(lines):
        x = (bw - widths[i]) / 2
        y = pad_y + sw + i * lh
        for seg, hi in parse_marked(ln):
            d.text((x, y), seg, font=f, fill=accent if hi else color, stroke_width=sw, stroke_fill=stroke)
            x += f.getlength(seg)
    return img


def text_image(text: str, font_path: str, size: int, color="#FFFFFF", stroke=None, stroke_width=0,
               align="center", line_gap=0.3) -> Image.Image:
    f = font(font_path, size)
    lines = text.split("\n")
    widths = [f.getlength(ln) for ln in lines]
    lh = int(size * (1 + line_gap))
    sw = stroke_width
    img = Image.new("RGBA", (int(max(widths)) + sw * 2 + 4, lh * len(lines) - int(size * line_gap) + sw * 2 + 8), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        x = {"center": (img.width - widths[i]) / 2, "left": sw}.get(align, img.width - widths[i] - sw)
        d.text((x, sw + i * lh), ln, font=f, fill=color, stroke_width=sw, stroke_fill=stroke)
    return img


# ---------------------------------------------------------------- audio / output

def read_wav(path: str) -> tuple[np.ndarray, int]:
    try:
        import soundfile as sf
        y, sr = sf.read(path, dtype="float32", always_2d=False)
        return (y.mean(axis=1) if y.ndim == 2 else y), sr
    except ImportError:
        pass
    with wave.open(path, "rb") as w:
        sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
        raw = w.readframes(n)
    if sw == 2:
        y = np.frombuffer(raw, "<i2").astype(np.float32) / 32768
    elif sw == 4:
        y = np.frombuffer(raw, "<i4").astype(np.float32) / 2 ** 31
    elif sw == 1:
        y = (np.frombuffer(raw, np.uint8).astype(np.float32) - 128) / 128
    else:
        sys.exit("この WAV 形式は読めません。pip install soundfile を入れてください。")
    if ch > 1:
        y = y.reshape(-1, ch).mean(axis=1)
    return y, sr


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        pass
    exe = shutil.which("ffmpeg")
    if not exe:
        sys.exit("ffmpeg が見つかりません。pip install imageio-ffmpeg を入れてください。")
    return exe


class VideoWriter:
    def __init__(self, out: str, audio: str | None, duration: float, crf: int = 18):
        cmd = [ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
        if audio:
            cmd += ["-i", audio, "-af", "apad", "-c:a", "aac", "-b:a", "192k"]
        cmd += ["-t", f"{duration:.3f}", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
                "-pix_fmt", "yuv420p", "-movflags", "+faststart", out]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)

    def write(self, frame: Image.Image) -> None:
        self.proc.stdin.write(frame.convert("RGB").tobytes())

    def close(self) -> None:
        self.proc.stdin.close()
        if self.proc.wait() != 0:
            sys.exit("ffmpeg でのエンコードに失敗しました。")
