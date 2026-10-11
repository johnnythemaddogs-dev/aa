"""猫の愛情表現をテーマにした素材クリップを手続き的に描画する。

外部素材を使わず PIL だけで描いたアニメ調の猫を、シーンごとに連番 PNG ではなく
ffmpeg へ直接パイプして mp4 にする。編集デモ（edit_demos.sh）の素材になる。

使い方: python3 render_cats.py <出力ディレクトリ>
"""
import math
import random
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W, H = 640, 360          # 出力解像度
SS = 2                   # スーパーサンプリング倍率（アンチエイリアス用）
FPS = 24
SR = 48000

ORANGE = dict(fur=(244, 164, 84), stripe=(214, 120, 52), belly=(255, 236, 214))
GRAY = dict(fur=(150, 156, 170), stripe=(110, 116, 132), belly=(236, 238, 244))
PINK = (246, 150, 170)
DARK = (52, 40, 40)


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------- 背景
def room_bg(green=False):
    w, h = W * SS, H * SS
    if green:
        return Image.new("RGB", (w, h), (0, 200, 60))
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    floor_y = int(h * 0.72)
    for y in range(floor_y):  # 壁のグラデーション
        k = y / floor_y
        d.line([(0, y), (w, y)], fill=(int(255 - 20 * k), int(240 - 25 * k), int(222 - 30 * k)))
    for y in range(floor_y, h):  # 木の床
        k = (y - floor_y) / (h - floor_y)
        d.line([(0, y), (w, y)], fill=(int(196 - 40 * k), int(146 - 35 * k), int(104 - 30 * k)))
    for x in range(0, w, 180):
        d.line([(x, floor_y), (x - 120, h)], fill=(170, 122, 86), width=3)
    # 窓
    wx, wy, ww, wh = int(w * 0.07), int(h * 0.1), int(w * 0.22), int(h * 0.4)
    d.rectangle([wx, wy, wx + ww, wy + wh], fill=(188, 222, 246), outline=(255, 255, 255), width=14)
    d.line([(wx + ww // 2, wy), (wx + ww // 2, wy + wh)], fill=(255, 255, 255), width=10)
    d.line([(wx, wy + wh // 2), (wx + ww, wy + wh // 2)], fill=(255, 255, 255), width=10)
    # 額縁
    fx, fy = int(w * 0.78), int(h * 0.14)
    d.rectangle([fx, fy, fx + 150, fy + 110], fill=(255, 250, 240), outline=(180, 130, 90), width=10)
    heart(d, fx + 75, fy + 58, 34, (240, 120, 140))
    # 光の差し込み
    glow = Image.new("L", (w, h), 0)
    ImageDraw.Draw(glow).polygon([(wx, wy), (wx + ww, wy), (wx + ww + 420, floor_y + 200), (wx + 120, floor_y + 200)], fill=60)
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    img = Image.composite(Image.new("RGB", (w, h), (255, 248, 220)), img, glow)
    return img


def heart(d, cx, cy, size, color):
    pts = []
    for i in range(60):
        t = i / 60 * 2 * math.pi
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * size / 32, cy + y * size / 32))
    d.polygon(pts, fill=color)


# ---------------------------------------------------------------- 猫
def draw_cat(p):
    """猫 1 匹を RGBA で返す。p は表情・ポーズのパラメータ dict。"""
    col = p.get("colors", ORANGE)
    S = 900
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = S // 2
    body_top, body_bot = 430, 860

    # しっぽ（体の後ろ）
    if p.get("tail_up"):
        q = p.get("tail_quiver", 0)
        pts = [(cx + 200 + i * 7 + 22 * math.sin(i * 0.5 + q) * (i / 12) - (40 * ((i - 9) / 3) ** 2 if i > 9 else 0),
                800 - i * 40) for i in range(13)]
    else:
        sway = p.get("tail_sway", 0)
        pts = []
        for i in range(14):
            k = i / 13
            ang = -0.2 + k * (1.6 + 0.6 * math.sin(sway))
            pts.append((cx + 160 + math.sin(ang) * 170 * k + 60 * k, 840 - math.cos(ang) * 190 * k * k))
    d.line(pts, fill=col["fur"], width=56, joint="curve")
    for x, y in (pts[0], pts[-1]):
        d.ellipse([x - 28, y - 28, x + 28, y + 28], fill=col["fur"])
    tx, ty = pts[-1]
    d.ellipse([tx - 28, ty - 28, tx + 28, ty + 28], fill=col["stripe"])

    # 体
    d.ellipse([cx - 200, body_top, cx + 200, body_bot + 60], fill=col["fur"])
    d.ellipse([cx - 110, body_top + 70, cx + 110, body_bot], fill=col["belly"])
    # 前足（ふみふみ）
    kn = p.get("knead", 0.0)
    for side, ph in ((-1, 0.0), (1, math.pi)):
        lift = max(0.0, math.sin(kn + ph)) * 80 if p.get("kneading") else 0
        px = cx + side * 70
        py = 800 - lift
        d.rounded_rectangle([px - 42, 620 - lift * 0.3, px + 42, py + 40], radius=40, fill=col["fur"])
        d.ellipse([px - 50, py, px + 50, py + 64], fill=col["belly"])
        for k in (-22, 0, 22):
            d.line([(px + k, py + 18), (px + k, py + 36)], fill=col["stripe"], width=5)

    # 頭（別レイヤーで描いて傾ける）
    head = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    h = ImageDraw.Draw(head)
    hy = 300
    for side in (-1, 1):  # 耳
        h.polygon([(cx + side * 70, hy - 120), (cx + side * 205, hy - 225), (cx + side * 205, hy - 20)], fill=col["fur"])
        h.polygon([(cx + side * 105, hy - 115), (cx + side * 185, hy - 180), (cx + side * 182, hy - 60)], fill=PINK)
    h.ellipse([cx - 230, hy - 190, cx + 230, hy + 190], fill=col["fur"])
    for k in (-40, 0, 40):  # 額の縞
        h.line([(cx + k, hy - 185), (cx + k * 0.8, hy - 110)], fill=col["stripe"], width=16)
    h.ellipse([cx - 120, hy + 10, cx + 120, hy + 175], fill=col["belly"])

    blink = p.get("blink", 0.0)   # 0=開 1=閉
    happy = p.get("happy", False)  # ^ ^ 目
    for side in (-1, 1):
        ex, ey = cx + side * 95, hy - 20
        if happy or blink > 0.92:
            h.arc([ex - 45, ey - 30, ex + 45, ey + 40], 200 if happy else 20, 340 if happy else 160, fill=DARK, width=12)
        else:
            eh = 58 * (1 - blink)
            h.ellipse([ex - 44, ey - eh, ex + 44, ey + eh], fill=(255, 250, 225))
            look = p.get("look", 0)
            h.ellipse([ex - 26 + look, ey - eh * 0.9, ex + 26 + look, ey + eh * 0.9], fill=DARK)
            if eh > 18:
                h.ellipse([ex - 12 + look, ey - eh * 0.6, ex + 4 + look, ey - eh * 0.6 + 16], fill="white")
            if blink > 0:  # まぶた
                h.rectangle([ex - 50, ey - 62, ex + 50, ey - eh], fill=col["fur"])
                h.rectangle([ex - 50, ey + eh, ex + 50, ey + 62], fill=col["fur"])
                h.line([(ex - 44, ey - eh), (ex + 44, ey - eh)], fill=DARK, width=6)
    # 頬・鼻・口・ひげ
    blush = p.get("blush", 0.6)
    cheeks = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    for side in (-1, 1):
        ImageDraw.Draw(cheeks).ellipse([cx + side * 165 - 40, hy + 40, cx + side * 165 + 40, hy + 80], fill=(250, 140, 150, int(200 * blush)))
    head.alpha_composite(cheeks)
    h.polygon([(cx - 22, hy + 50), (cx + 22, hy + 50), (cx, hy + 74)], fill=PINK)
    h.arc([cx - 50, hy + 60, cx, hy + 105], 0, 180, fill=DARK, width=7)
    h.arc([cx, hy + 60, cx + 50, hy + 105], 0, 180, fill=DARK, width=7)
    for side in (-1, 1):
        for k in (-18, 0, 18):
            h.line([(cx + side * 120, hy + 70 + k * 0.6), (cx + side * 260, hy + 50 + k * 1.6)], fill=(90, 70, 70), width=5)

    tilt = p.get("tilt", 0)
    head = head.rotate(tilt, resample=Image.BICUBIC, center=(cx, hy + 160))
    img.alpha_composite(head)
    if p.get("flip"):
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    return img


def place(frame, cat, x, y, scale):
    """猫画像を (x, y)=足元中央 に scale 倍で合成する（SS 座標系）。"""
    size = int(900 * scale * SS * 0.42)
    c = cat.resize((size, size), Image.LANCZOS)
    frame.paste(c, (int(x * SS - size / 2), int(y * SS - size * 0.97)), c)


def hearts(frame, t, origin, t0, n=5, seed=1):
    """t0 秒から origin 付近にハートを浮かび上がらせる。"""
    if t < t0:
        return
    rnd = random.Random(seed)
    d = ImageDraw.Draw(frame, "RGBA")
    for i in range(n):
        st = t0 + i * 0.25
        age = t - st
        if age < 0 or age > 2.2:
            continue
        x = origin[0] + rnd.uniform(-70, 70) + 12 * math.sin(age * 4 + i)
        y = origin[1] - age * 70
        a = int(255 * (1 - age / 2.2))
        s = rnd.uniform(14, 24) * min(1, age * 4)
        heart(d, x * SS, y * SS, s * SS, (240, 90, 130, a))


def blanket(frame):
    d = ImageDraw.Draw(frame)
    d.ellipse([140 * SS, 300 * SS, 500 * SS, 380 * SS], fill=(150, 190, 230))
    for k in range(5):
        d.arc([(160 + k * 60) * SS, 310 * SS, (230 + k * 60) * SS, 350 * SS], 180, 360, fill=(120, 160, 210), width=6)


# ---------------------------------------------------------------- シーン
def scene_blink(t):
    """ゆっくりまばたき（猫キス）。"""
    f = room_bg()
    b = 0.0
    for c in (1.2, 3.4):
        if c <= t < c + 1.4:
            b = math.sin((t - c) / 1.4 * math.pi)
    place(f, draw_cat(dict(blink=b, tail_sway=t * 1.5, look=0)), 320, 335, 1.0)
    hearts(f, t, (320, 70), 2.2, seed=3)
    return f


def scene_headbump(t):
    """2 匹で頭をすりすり。"""
    f = room_bg()
    approach = ease(t / 2.2)
    rub = math.sin(max(0, t - 2.2) * 5) * 6 if t > 2.2 else 0
    gx = 470 - 120 * approach
    place(f, draw_cat(dict(colors=GRAY, tilt=-18 * approach + rub, happy=t > 2.4, tail_sway=t * 2, flip=True)), gx, 340, 0.9)
    place(f, draw_cat(dict(tilt=16 * approach - rub, happy=t > 2.4, tail_sway=t * 1.7)), 220, 340, 0.95)
    hearts(f, t, (285, 80), 2.6, n=7, seed=5)
    return f


def scene_knead(t):
    """毛布の上でふみふみ。"""
    f = room_bg()
    blanket(f)
    place(f, draw_cat(dict(kneading=True, knead=t * 7, happy=True, blush=0.9, tail_sway=t)), 320, 345, 1.0)
    hearts(f, t, (320, 75), 1.0, n=8, seed=7)
    return f


def scene_tail(t):
    """しっぽをピンと立てて近づいてくる。"""
    f = room_bg()
    s = 0.55 + 0.5 * ease(t / 4.5)
    place(f, draw_cat(dict(tail_up=True, tail_quiver=t * 25, look=0, blink=0)), 320 + 40 * math.sin(t * 1.3) * (1 - s), 320 + 40 * s, s)
    hearts(f, t, (250, 90), 3.5, seed=9)
    return f


def scene_green(t):
    """クロマキー用：グリーンバックでまばたき＋ふみふみ。"""
    f = room_bg(green=True)
    b = math.sin((t - 1.5) / 1.4 * math.pi) if 1.5 <= t < 2.9 else 0
    place(f, draw_cat(dict(kneading=True, knead=t * 7, blink=b, tail_sway=t * 1.5)), 320, 350, 1.0)
    return f


def scene_closeup(t):
    """顔アップ（ズーム／モザイク用の高解像度寄り絵）。"""
    f = room_bg()
    b = math.sin((t - 2.0) / 1.6 * math.pi) if 2.0 <= t < 3.6 else 0
    place(f, draw_cat(dict(blink=b, tilt=8 * math.sin(t * 0.9), tail_sway=t)), 320, 520, 1.6)
    hearts(f, t, (320, 90), 3.0, seed=11)
    return f


# ---------------------------------------------------------------- 音
def purr(dur, seed=0):
    """ゴロゴロ音：低域ノイズを 25Hz で振幅変調。"""
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    t = np.arange(n) / SR
    noise = rng.standard_normal(n)
    k = 400
    low = np.convolve(noise, np.ones(k) / k, mode="same")
    low /= np.abs(low).max() + 1e-9
    env = (0.55 + 0.45 * np.sin(2 * np.pi * 25 * t)) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.45 * t))
    sig = low * env * 0.35
    fade = np.minimum(1, np.minimum(t / 0.3, (dur - t) / 0.3))
    return (sig * fade).astype(np.float32)


def render(scene, dur, out, audio=True):
    n = int(dur * FPS)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
           "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-"]
    wav = None
    if audio:
        wav = out.with_suffix(".purr.f32")
        purr(dur, seed=hash(out.name) % 1000).tofile(wav)
        cmd += ["-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", str(wav), "-c:a", "aac", "-b:a", "96k"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-shortest", str(out)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(n):
        frame = scene(i / FPS).resize((W, H), Image.LANCZOS)
        proc.stdin.write(frame.tobytes())
    proc.stdin.close()
    proc.wait()
    if wav:
        wav.unlink()
    print("rendered", out)


if __name__ == "__main__":
    outdir = Path(sys.argv[1])
    outdir.mkdir(parents=True, exist_ok=True)
    jobs = {
        "blink": (scene_blink, 6),
        "headbump": (scene_headbump, 6),
        "knead": (scene_knead, 6),
        "tail": (scene_tail, 6),
        "green": (scene_green, 6),
        "closeup": (scene_closeup, 6),
    }
    only = sys.argv[2:] or list(jobs)
    for name in only:
        fn, dur = jobs[name]
        render(fn, dur, outdir / f"{name}.mp4", audio=(name != "green"))
