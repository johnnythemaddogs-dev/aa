"""「猫のミステリー」10 秒クリップ。参考動画の雰囲気をまねて作る。

雰囲気の要素:
  シネスコの黒帯 / 暗い岩肌の背景 / 紙の資料カードとドロップシャドウ /
  ゆっくりしたズーム / ディゾルブでの場面転換 / 字間を空けた明朝体の字幕 /
  左上にタイトルと小さな説明、右上に出典表記 / 暗いティール色の資料画面 /
  ラベルが時間差で出てくる演出 / 上部中央に問いかけのテキスト

使い方: python3 render_mystery.py <出力.mp4>
フォント: fonts/ に Shippori Mincho（OFL）が必要（fetch_fonts.sh で取得）。
"""
import math
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

HERE = Path(__file__).parent
FB = str(HERE / "fonts/ShipporiMincho-Bold.ttf")
FM = str(HERE / "fonts/ShipporiMincho-Medium.ttf")
FX = str(HERE / "fonts/ShipporiMincho-ExtraBold.ttf")

W, H = 1920, 1080
BAR = 128                 # シネスコの黒帯（上下）
CH = H - 2 * BAR          # 映像部分の高さ
FPS = 30
DUR = 10.0
SR = 48000


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ramp(t, a, b):
    return ease((t - a) / (b - a)) if b > a else float(t >= a)


def window(t, a, b, fade=0.35):
    """a〜b 秒で表示（前後 fade 秒でフェード）。"""
    return min(ramp(t, a, a + fade), 1 - ramp(t, b - fade, b))


# ------------------------------------------------------------ テクスチャ
def value_noise(w, h, cell, rng):
    g = rng.random((h // cell + 3, w // cell + 3)).astype(np.float32)
    img = Image.fromarray((g * 255).astype(np.uint8)).resize(((w // cell + 3) * cell, (h // cell + 3) * cell), Image.BICUBIC)
    return np.asarray(img, dtype=np.float32)[:h, :w] / 255


def fbm(w, h, rng, cells=(256, 128, 64, 32, 16, 8, 4)):
    out = np.zeros((h, w), np.float32)
    amp, tot = 1.0, 0.0
    for c in cells:
        out += value_noise(w, h, c, rng) * amp
        tot += amp
        amp *= 0.55
    return out / tot


def rock_texture(w, h, seed=3):
    """陰影をつけた岩肌（くすんだ灰色）。"""
    rng = np.random.default_rng(seed)
    hgt = fbm(w, h, rng)
    ridge = 1 - np.abs(fbm(w, h, rng, (180, 90, 45, 22)) * 2 - 1)
    hgt = hgt + 0.35 * ridge ** 3
    gy, gx = np.gradient(hgt)
    shade = np.clip(0.45 + (gx * -1.0 + gy * -0.6) * 40, 0, 1)
    base = 0.10 + 0.50 * shade ** 1.3 * (0.45 + 0.55 * hgt)
    base += (rng.random((h, w)).astype(np.float32) - 0.5) * 0.05
    rgb = np.stack([base * 0.98, base * 0.95, base * 0.90], -1)
    return Image.fromarray((np.clip(rgb, 0, 1) * 255).astype(np.uint8))


def teal_texture(w, h, seed=7):
    """資料画面用の暗いティールの海面風テクスチャ。"""
    rng = np.random.default_rng(seed)
    n = fbm(w, h, rng, (300, 150, 75, 37, 18))
    gy, gx = np.gradient(n)
    shade = np.clip(0.5 + gx * -30, 0, 1)
    v = 0.55 + 0.45 * shade
    yy = np.linspace(0, 1, h)[:, None]
    r = (14 + 10 * v) * (1 - 0.3 * yy)
    g = (44 + 30 * v) * (1 - 0.3 * yy)
    b = (50 + 30 * v) * (1 - 0.3 * yy)
    return Image.fromarray(np.clip(np.stack([r + 0 * n, g + 0 * n, b + 0 * n], -1), 0, 255).astype(np.uint8))


def paper(w, h, seed=1, tone=(232, 226, 210)):
    rng = np.random.default_rng(seed)
    n = fbm(w, h, rng, (120, 60, 30, 8, 3))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    edge = np.minimum(np.minimum(xx, w - 1 - xx), np.minimum(yy, h - 1 - yy))
    dark = 1 - 0.10 * np.exp(-edge / 40) - 0.05 * (1 - n)
    rgb = np.stack([np.full((h, w), c, np.float32) for c in tone], -1) * dark[..., None]
    return Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")


# ------------------------------------------------------------ 図版カード
def hatch_fill(img, mask, spacing=6, angle=60, width=2, color=(40, 34, 30, 255)):
    """mask の内側を斜線でハッチングする（版画風）。"""
    w, h = img.size
    layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    a = math.radians(angle)
    dx, dy = math.cos(a), math.sin(a)
    L = w + h
    for k in range(-L, L, spacing):
        cx, cy = w / 2 + k * -dy, h / 2 + k * dx
        d.line([(cx - dx * L, cy - dy * L), (cx + dx * L, cy + dy * L)], fill=color, width=width)
    img.paste(layer, (0, 0), ImageChops.multiply(layer.split()[3], mask))


def dashed_rect(d, box, color, dash=10, gap=6, width=3):
    x0, y0, x1, y1 = box
    for (ax, ay, bx, by) in [(x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)]:
        L = math.hypot(bx - ax, by - ay)
        s = 0
        while s < L:
            e = min(L, s + dash)
            d.line([(ax + (bx - ax) * s / L, ay + (by - ay) * s / L), (ax + (bx - ax) * e / L, ay + (by - ay) * e / L)], fill=color, width=width)
            s += dash + gap


def card_corner():
    """部屋の隅を見つめる猫の後ろ姿（版画風の挿絵カード）。"""
    w, h = 1100, 780
    img = paper(w, h, seed=11)
    d = ImageDraw.Draw(img)
    ink = (46, 40, 36, 255)
    d.rectangle([28, 28, w - 28, h - 28], outline=ink, width=3)
    dashed_rect(d, (40, 40, w - 40, h - 40), ink, width=3)
    # 部屋の隅（遠近）
    cx, top, bot = 700, 70, 470
    d.line([(cx, top), (cx, bot)], fill=ink, width=3)
    d.line([(cx, bot), (60, 690)], fill=ink, width=3)
    d.line([(cx, bot), (w - 60, 640)], fill=ink, width=3)
    wall = Image.new("L", (w, h), 0)
    ImageDraw.Draw(wall).polygon([(60, 60), (cx, 60), (cx, bot), (60, 690)], fill=255)
    hatch_fill(img, wall, spacing=11, angle=-15, width=1, color=(70, 62, 56, 150))
    # 壁の隅に「見えない何か」をほのめかす点線の輪
    for r in (30, 60, 95):
        for k in range(0, 360, 14):
            a = math.radians(k)
            x, y = cx - 40 + math.cos(a) * r, 230 + math.sin(a) * r * 1.1
            d.ellipse([x - 2.5, y - 2.5, x + 2.5, y + 2.5], fill=(60, 52, 46, 255 - r * 2))
    # 猫の後ろ姿（シルエット → ハッチング）
    m = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(m)
    bx, by = 400, 640
    md.ellipse([bx - 120, by - 230, bx + 120, by + 20], fill=255)
    md.ellipse([bx - 82, by - 330, bx + 82, by - 180], fill=255)
    md.polygon([(bx - 78, by - 270), (bx - 70, by - 368), (bx - 20, by - 318)], fill=255)
    md.polygon([(bx + 78, by - 270), (bx + 70, by - 368), (bx + 20, by - 318)], fill=255)
    tail = [(bx + 100, by - 10), (bx + 170, by + 5), (bx + 230, by - 10), (bx + 250, by - 45)]
    md.line(tail, fill=255, width=30, joint="curve")
    md.ellipse([bx + 236, by - 60, bx + 264, by - 32], fill=255)
    hatch_fill(img, m, spacing=5, angle=65, width=2, color=ink)
    hatch_fill(img, m.filter(ImageFilter.MinFilter(41)), spacing=5, angle=-25, width=2, color=ink)
    edge = ImageChops.subtract(m, m.filter(ImageFilter.MinFilter(5)))
    img.paste(Image.new("RGBA", (w, h), ink), (0, 0), edge)
    # 影
    d.ellipse([bx - 150, by + 5, bx + 170, by + 40], outline=(70, 62, 56, 255), width=2)
    f = ImageFont.truetype(FM, 26)
    text = "T H E   C A T   A N D   T H E   E M P T Y   C O R N E R"
    d.text((w / 2, h - 66), text, font=f, fill=ink, anchor="mm")
    return img


def card_eyes():
    """暗闇で光る目（写真プリント風カード）。"""
    w, h = 640, 760
    border = 18
    rng = np.random.default_rng(5)
    n = fbm(w, h, rng, (200, 80, 30, 6))
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    vig = np.exp(-(((xx - w / 2) / (w * 0.6)) ** 2 + ((yy - h * 0.45) / (h * 0.55)) ** 2))
    v = (8 + 18 * n) * (0.4 + 0.6 * vig)
    rgb = np.stack([v * 0.7, v * 0.8, v * 1.25], -1)
    photo = Image.fromarray(np.clip(rgb, 0, 255).astype(np.uint8)).convert("RGBA")
    glow = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for ex in (w / 2 - 105, w / 2 + 105):
        ey = h * 0.42
        gd.ellipse([ex - 70, ey - 44, ex + 70, ey + 44], fill=(200, 230, 90, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(26))
    photo.alpha_composite(glow)
    pd = ImageDraw.Draw(photo)
    for ex in (w / 2 - 105, w / 2 + 105):
        ey = h * 0.42
        pd.ellipse([ex - 62, ey - 38, ex + 62, ey + 38], fill=(214, 236, 120, 255))
        pd.ellipse([ex - 40, ey - 26, ex + 40, ey + 26], fill=(238, 250, 170, 255))
        pd.ellipse([ex - 9, ey - 36, ex + 9, ey + 36], fill=(10, 12, 14, 255))
        pd.ellipse([ex + 16, ey - 20, ex + 28, ey - 8], fill=(255, 255, 255, 230))
    card = Image.new("RGBA", (w + border * 2, h + border * 2), (236, 232, 220, 255))
    card.paste(photo, (border, border))
    return card


def with_shadow(card, angle):
    """回転＋ドロップシャドウ付きの RGBA を返す。"""
    pad = 70
    w, h = card.size
    base = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    sh = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([pad + 14, pad + 22, pad + w + 14, pad + h + 22], fill=(0, 0, 0, 190))
    base.alpha_composite(sh.filter(ImageFilter.GaussianBlur(22)))
    base.alpha_composite(card, (pad, pad))
    return base.rotate(angle, resample=Image.BICUBIC, expand=True)


# ------------------------------------------------------------ 文字
def spaced_text(text, font_path, size, color, spacing=0.12, shadow=True, stroke=0):
    """字間を空けた 1 行テキストを RGBA で返す（柔らかい影付き）。"""
    f = ImageFont.truetype(font_path, size)
    adv = [f.getlength(ch) + size * spacing for ch in text]
    tw = int(sum(adv) - size * spacing) + 1
    pad = int(size * 0.6)
    img = Image.new("RGBA", (tw + pad * 2, int(size * 1.5) + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad
    for ch, a in zip(text, adv):
        d.text((x, pad), ch, font=f, fill=color, stroke_width=stroke, stroke_fill=color)
        x += a
    if shadow:
        a = img.split()[3].filter(ImageFilter.GaussianBlur(size * 0.18))
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sh.putalpha(a.point(lambda v: min(255, int(v * 1.6))))
        sh.alpha_composite(img)
        img = sh
    return img


def put(frame, layer, x, y, alpha=1.0, anchor="lt"):
    if alpha <= 0.01:
        return
    if alpha < 1:
        layer = layer.copy()
        layer.putalpha(layer.split()[3].point(lambda v: int(v * alpha)))
    w, h = layer.size
    if anchor == "mt":
        x -= w // 2
    elif anchor == "rt":
        x -= w
    frame.alpha_composite(layer, (int(x), int(y)))


# ------------------------------------------------------------ 素材の用意
ASSETS = {}


def build_assets():
    A = ASSETS
    A["rock"] = rock_texture(2300, 1100).convert("RGBA")
    A["teal"] = teal_texture(2300, 1100).convert("RGBA")
    A["corner"] = with_shadow(card_corner(), -1.2)
    A["corner_s"] = with_shadow(card_corner().resize((640, 454), Image.LANCZOS), 1.5)
    A["eyes"] = with_shadow(card_eyes().resize((430, 509), Image.LANCZOS), -2.0)
    # 画面全体の暗いグラデーション（周辺減光＋字幕のための下部の暗さ）
    yy, xx = np.mgrid[0:CH, 0:W].astype(np.float32)
    vig = 1 - 0.55 * (((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - CH * 0.45) / (CH * 0.75)) ** 2)
    bottom = 1 - 0.55 * np.clip((yy - CH * 0.55) / (CH * 0.45), 0, 1) ** 1.4
    a = np.clip(1 - np.clip(vig, 0, 1) * bottom, 0, 1)
    A["shade"] = Image.fromarray((a * 255).astype(np.uint8))
    white = (238, 234, 226, 255)
    A["subs"] = [(a, b, spaced_text(s, FB, 54, white)) for a, b, s in SUBS]
    A["title1"] = spaced_text("猫が見つめる「何もない場所」", FB, 40, white, spacing=0.04)
    A["cap1"] = spaced_text("深夜、部屋の隅をじっと見つめる猫（イメージ図）", FM, 21, (200, 196, 188, 255), spacing=0.04)
    A["cred1"] = spaced_text("図：本動画のために作画", FM, 22, (170, 166, 160, 255), spacing=0.04)
    A["title2"] = spaced_text("人と猫が聞こえる音の範囲", FB, 40, white, spacing=0.04)
    A["cap2"] = spaced_text("可聴域の比較（周波数は対数目盛）", FM, 21, (200, 210, 206, 255), spacing=0.04)
    A["cred2"] = spaced_text("出典：Heffner & Heffner (1985) Hearing Research 19", FM, 22, (160, 176, 172, 255), spacing=0.02)
    A["q1"] = spaced_text("なぜ、何もない場所を見つめるのか？", FB, 30, white, spacing=0.06)
    A["q2"] = spaced_text("その答えは、まだ闇の中に。", FB, 30, white, spacing=0.06)
    A["lab_l"] = spaced_text("視線の先には、何もない", FB, 28, white, spacing=0.05)
    A["lab_r"] = spaced_text("わずかな光を集める目", FB, 28, white, spacing=0.05)
    A["cred3"] = spaced_text("左右とも：本動画のために作画", FM, 22, (170, 166, 160, 255), spacing=0.04)
    sm = (190, 214, 208, 255)
    A["ax"] = {f: spaced_text(lbl, FM, 22, (130, 158, 152, 255), spacing=0.02, shadow=False)
               for f, lbl in [(10, "10Hz"), (100, "100Hz"), (1000, "1kHz"), (10000, "10kHz"), (100000, "100kHz")]}
    A["human"] = spaced_text("人", FB, 34, white)
    A["cat"] = spaced_text("猫", FB, 34, white)
    A["h_lo"] = spaced_text("20Hz", FM, 24, sm, spacing=0.02)
    A["h_hi"] = spaced_text("20kHz", FM, 24, sm, spacing=0.02)
    A["c_lo"] = spaced_text("48Hz", FM, 24, sm, spacing=0.02)
    A["c_hi"] = spaced_text("85kHz", FM, 24, sm, spacing=0.02)
    A["zone"] = spaced_text("人には聞こえない音域", FB, 28, (150, 236, 220, 255), spacing=0.06)


SUBS = [
    (0.30, 1.30, "みなさんは、"),
    (1.40, 2.70, "猫が何もない空間を、"),
    (2.80, 3.95, "じっと見つめる理由を…"),
    (4.15, 5.00, "実は、"),
    (5.10, 6.95, "猫の耳は、人には聞こえない高い音まで聞きとっています。"),
    (7.45, 8.55, "では、いったい何を"),
    (8.65, 9.70, "見ているのでしょうか…"),
]


# ------------------------------------------------------------ 各ショット
def bg_zoom(tex, t, t0, t1, z0, z1, ox=0.0, oy=0.0):
    """テクスチャをゆっくりズーム／パンして映像部分サイズで返す。"""
    k = (t - t0) / (t1 - t0)
    z = z0 + (z1 - z0) * k
    tw, th = tex.size
    cw, chh = W / z, CH / z
    x = (tw - cw) / 2 + ox * k
    y = (th - chh) / 2 + oy * k
    return tex.transform((W, CH), Image.EXTENT, (x, y, x + cw, y + chh), Image.BICUBIC)


def scaled(img, s):
    return img.resize((int(img.width * s), int(img.height * s)), Image.BICUBIC)


def shot1(t):
    f = bg_zoom(ASSETS["rock"], t, 0, 4.4, 1.0, 1.05, ox=-40)
    s = 0.86 + 0.035 * t / 4.4
    c = scaled(ASSETS["corner"], s)
    f.alpha_composite(c, (int(W * 0.60 - c.width / 2 - 12 * t), int(CH * 0.53 - c.height / 2)))
    return f, "s1"


def freq_x(fr, k):
    lo, hi = math.log10(10), math.log10(200000)
    return int(220 + (math.log10(fr) - lo) / (hi - lo) * (W - 440) + k)


def shot2(t):
    lt = t - 3.7
    f = bg_zoom(ASSETS["teal"], lt, 0, 3.8, 1.04, 1.10, ox=60, oy=-20)
    pan = -25 * lt
    ov = Image.new("RGBA", f.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for fr, lbl in ASSETS["ax"].items():
        x = freq_x(fr, pan)
        d.line([(x, 200), (x, 585)], fill=(150, 200, 190, 50), width=2)
        put(ov, lbl, x, 592, alpha=0.9, anchor="mt")
    rows = [("human", 20, 20000, 300, 0.5, "h_lo", "h_hi", (210, 214, 200)),
            ("cat", 48, 85000, 430, 1.25, "c_lo", "c_hi", (120, 232, 214))]
    # 人に聞こえない帯域を強調
    za = ramp(lt, 2.2, 2.7)
    if za > 0:
        x0, x1 = freq_x(20000, pan), freq_x(85000, pan)
        d.rectangle([x0, 250, x1, 500], fill=(120, 232, 214, int(40 * za)))
        d.line([(x0, 250), (x0, 500)], fill=(150, 236, 220, int(160 * za)), width=2)
        put(ov, ASSETS["zone"], (x0 + x1) / 2, 512, alpha=za, anchor="mt")
    f.alpha_composite(ov)
    d = ImageDraw.Draw(f)
    for key, lo, hi, y, st, kl, kh, col in rows:
        p = ramp(lt, st, st + 0.9)
        if p <= 0:
            continue
        put(f, ASSETS[key], freq_x(lo, pan) - 90, y - 34, alpha=min(1, p * 2))
        x0 = freq_x(lo, pan)
        x1 = x0 + (freq_x(hi, pan) - x0) * p
        glow = Image.new("RGBA", f.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle([x0, y - 9, x1, y + 9], radius=9, fill=col + (200,))
        f.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
        d.rounded_rectangle([x0, y - 5, x1, y + 5], radius=5, fill=col + (255,))
        for xx, lab, show in ((x0, kl, p > 0.05), (x1, kh, p > 0.98)):
            if show:
                d.ellipse([xx - 9, y - 9, xx + 9, y + 9], fill=(245, 245, 235, 255))
                put(f, ASSETS[lab], xx, y + 16, anchor="mt")
    return f, "s2"


def shot3(t):
    lt = t - 6.9
    f = bg_zoom(ASSETS["rock"], lt, 0, 3.1, 1.06, 1.09, ox=30)
    l, r = ASSETS["corner_s"], ASSETS["eyes"]
    dl = ramp(lt, 0.0, 0.8)
    xl = int(W * 0.29 - l.width / 2 - 60 * (1 - dl))
    xr = int(W * 0.69 - r.width / 2 + 60 * (1 - ramp(lt, 0.2, 1.0)))
    f.alpha_composite(l, (xl, int(CH * 0.56 - l.height / 2)))
    f.alpha_composite(r, (xr, int(CH * 0.56 - r.height / 2 + 30)))
    put(f, ASSETS["lab_l"], xl + l.width / 2, int(CH * 0.56 - l.height / 2) + 8, alpha=ramp(lt, 0.5, 0.9), anchor="mt")
    put(f, ASSETS["lab_r"], xr + r.width / 2, int(CH * 0.56 - r.height / 2) - 6, alpha=ramp(lt, 0.7, 1.1), anchor="mt")
    return f, "s3"


def overlays(f, t, which):
    A = ASSETS
    if which == "s1":
        a = window(t, 0.4, 4.1, 0.5)
        put(f, A["title1"], 56, 18, a)
        put(f, A["cap1"], 60, 80, a)
        put(f, A["cred1"], W - 40, 22, a, anchor="rt")
    elif which == "s2":
        a = window(t, 4.2, 7.2, 0.5)
        put(f, A["title2"], 56, 18, a)
        put(f, A["cap2"], 60, 80, a)
        put(f, A["cred2"], W - 40, 22, a, anchor="rt")
    else:
        put(f, A["cred3"], W - 40, 22, ramp(t, 7.3, 7.8), anchor="rt")
        put(f, A["q1"], W / 2, 26, ramp(t, 7.7, 8.2), anchor="mt")
        put(f, A["q2"], W / 2, 72, ramp(t, 8.4, 8.9), anchor="mt")


def render_frame(i):
    t = i / FPS
    layers = []
    if t < 4.4:
        layers.append((shot1(t), 1 - ramp(t, 3.7, 4.4)))
    if 3.7 <= t < 7.4:
        layers.append((shot2(t), min(ramp(t, 3.7, 4.4), 1 - ramp(t, 6.9, 7.4))))
    if t >= 6.9:
        layers.append((shot3(t), ramp(t, 6.9, 7.4)))
    pic = Image.new("RGBA", (W, CH), (0, 0, 0, 255))
    for (img, which), a in layers:
        img = img.copy()
        overlays(img, t, which)
        pic = Image.blend(pic, img, a) if a < 1 else img
    black = Image.new("RGBA", (W, CH), (0, 0, 0, 255))
    pic = Image.composite(black, pic, ASSETS["shade"])
    for a, b, img in ASSETS["subs"]:
        al = window(t, a, b, 0.25)
        if al > 0:
            put(pic, img, W / 2, CH - 168, al, anchor="mt")
    # フェードイン／アウト
    k = min(ramp(t, 0.0, 0.6), 1 - ramp(t, 9.35, 10.0))
    if k < 1:
        pic = Image.blend(black, pic, k)
    # 粒子ノイズ
    arr = np.asarray(pic.convert("RGB"), dtype=np.int16)
    rng = np.random.default_rng(i)
    arr = np.clip(arr + rng.normal(0, 5, arr.shape[:2])[..., None], 0, 255).astype(np.uint8)
    out = Image.new("RGB", (W, H), (0, 0, 0))
    out.paste(Image.fromarray(arr), (0, BAR))
    return out.tobytes()


# ------------------------------------------------------------ 音
def soundtrack():
    n = int(DUR * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(2)
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * t / 9 - 1.2)
    drone = (np.sin(2 * np.pi * 55 * t) + 0.7 * np.sin(2 * np.pi * 55.4 * t)
             + 0.45 * np.sin(2 * np.pi * 82.4 * t + np.sin(2 * np.pi * 0.2 * t))) * 0.08 * swell
    wind = np.convolve(rng.standard_normal(n), np.ones(200) / 200, "same") * 0.9
    wind *= 0.5 + 0.5 * np.sin(2 * np.pi * 0.13 * t) ** 2
    out = drone + wind * 0.12
    for at in (0.05, 3.9, 6.95):  # 場面転換の低い「ドン」
        k = t >= at
        tt = t[k] - at
        out[k] += np.sin(2 * np.pi * (48 * tt - 14 * tt * tt)) * np.exp(-tt * 2.2) * 0.45
    for at, fr in ((5.0, 6200), (5.35, 7400)):  # 高い音の「キーン」
        k = t >= at
        tt = t[k] - at
        out[k] += np.sin(2 * np.pi * fr * tt) * np.exp(-tt * 1.6) * 0.035
    fade = np.minimum(1, np.minimum(t / 0.6, (DUR - t) / 0.7))
    out *= fade
    out = out / np.abs(out).max() * 0.5
    return np.stack([out, out], 1).astype(np.float32)


def main(dst):
    build_assets()
    wav = Path(dst).with_suffix(".f32")
    soundtrack().tofile(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", str(wav),
           "-c:v", "libx264", "-preset", "slow", "-crf", "24", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", dst]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for b in pool.imap(render_frame, range(int(DUR * FPS)), chunksize=4):
            p.stdin.write(b)
    p.stdin.close()
    p.wait()
    wav.unlink()
    print("done", dst)


if __name__ == "__main__":
    if len(sys.argv) > 2:  # プレビュー: render_mystery.py out.png t1 t2 ...
        build_assets()
        ims = [Image.frombytes("RGB", (W, H), render_frame(int(float(x) * FPS))).resize((960, 540)) for x in sys.argv[2:]]
        sheet = Image.new("RGB", (960 * 2, 540 * ((len(ims) + 1) // 2)))
        for k, im in enumerate(ims):
            sheet.paste(im, ((k % 2) * 960, (k // 2) * 540))
        sheet.save(sys.argv[1])
    else:
        main(sys.argv[1])
