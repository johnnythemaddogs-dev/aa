"""「猫のミステリー」30 秒版。10 秒版（render_mystery.py）の部品を使い回して 5 ショットにする。

構成:
  1. 岩肌＋挿絵カード      … 何もない場所を見つめる猫（導入）
  2. ティールの資料画面    … 人と猫の可聴域（Heffner & Heffner 1985）
  3. 岩肌＋カード 2 枚     … 暗闇で光る目と、網膜の裏の反射層（タペタム）
  4. ティールの資料画面    … 見える光の範囲と紫外線の可能性（Douglas & Jeffery 2014）
  5. 岩肌＋カード 2 枚     … 問いかけで締める

使い方: python3 render_mystery30.py <出力.mp4>
        python3 render_mystery30.py <preview.png> <秒> <秒> ...   （確認用の静止画）
"""
import math
import subprocess
import sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import render_mystery as rm
from render_mystery import (BAR, CH, FB, FM, FPS, SR, W, H, bg_zoom, card_corner, card_eyes, dashed_rect,
                            hatch_fill, paper, put, ramp, scaled, spaced_text, window, with_shadow)

DUR = 30.0
WHITE = (238, 234, 226, 255)
GREY = (170, 166, 160, 255)
TEAL_GREY = (160, 176, 172, 255)

# 各ショットの区間（前後 0.6 秒はディゾルブで重なる）
SHOTS = [(0.0, 6.0), (5.4, 12.2), (11.6, 18.2), (17.6, 24.2), (23.6, 30.0)]
XF = 0.6

SUBS = [
    (0.40, 1.50, "みなさんは、"),
    (1.60, 2.90, "猫が何もない空間を、"),
    (3.00, 4.20, "じっと見つめる姿を"),
    (4.30, 5.60, "見たことがあるでしょうか。"),
    (5.90, 6.90, "実は、"),
    (7.00, 9.20, "猫の耳は、人には聞こえない高い音まで聞きとっています。"),
    (9.40, 11.60, "壁の向こうの小さな物音も、届いているのかもしれません。"),
    (12.00, 13.30, "そして、その目。"),
    (13.40, 15.40, "網膜の裏には、光をはね返す層があり、"),
    (15.50, 17.60, "わずかな光でも、ものを見ることができます。"),
    (17.90, 19.20, "さらに近年の研究では、"),
    (19.30, 21.40, "猫が紫外線を感じとれる可能性も"),
    (21.50, 23.50, "指摘されています。"),
    (23.90, 25.20, "人には聞こえない音。"),
    (25.30, 26.60, "人には見えない光。"),
    (26.80, 28.10, "猫はいったい何を"),
    (28.20, 29.40, "見ているのでしょうか…"),
]

A = {}


# ------------------------------------------------------------ 追加の図版
def card_eye_diagram():
    """猫の目の断面図（版画風）。光が入り、網膜の裏の反射層ではね返る。"""
    w, h = 980, 700
    img = paper(w, h, seed=23)
    d = ImageDraw.Draw(img)
    ink = (46, 40, 36, 255)
    d.rectangle([28, 28, w - 28, h - 28], outline=ink, width=3)
    dashed_rect(d, (40, 40, w - 40, h - 40), ink, width=3)
    cx, cy, r = 560, 330, 215
    # 反射層（タペタム）: 眼球の奥の三日月をハッチング
    m = Image.new("L", (w, h), 0)
    md = ImageDraw.Draw(m)
    md.pieslice([cx - r, cy - r, cx + r, cy + r], -70, 70, fill=255)
    md.ellipse([cx - r + 26, cy - r + 26, cx + r - 26, cy + r - 26], fill=0)
    hatch_fill(img, m, spacing=5, angle=45, width=2, color=ink)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ink, width=4)
    d.arc([cx - r + 26, cy - r + 26, cx + r - 26, cy + r - 26], -80, 80, fill=ink, width=2)
    # 角膜と水晶体
    d.arc([cx - r - 60, cy - 120, cx - r + 120, cy + 120], 120, 240, fill=ink, width=4)
    d.ellipse([cx - r + 40, cy - 85, cx - r + 120, cy + 85], outline=ink, width=3)
    # 光の線（入る → 反射して戻る）
    for k in (-60, 0, 60):
        d.line([(70, cy + k * 1.4), (cx - r + 80, cy + k * 0.8)], fill=ink, width=2)
        d.line([(cx - r + 80, cy + k * 0.8), (cx + r - 30, cy + k * 0.3)], fill=ink, width=2)
        ax = 70 + 40
        d.polygon([(ax, cy + k * 1.4 - 7), (ax + 16, cy + k * 1.39), (ax, cy + k * 1.4 + 7)], fill=ink)
    for k in (-40, 40):
        y0 = cy + k * 0.3
        x = cx + r - 40
        while x > cx - r + 100:
            d.line([(x, y0 + (cx + r - 40 - x) * k / 900), (x - 16, y0 + (cx + r - 56 - x) * k / 900)], fill=ink, width=2)
            x -= 28
    f = ImageFont.truetype(FM, 26)
    for (tx, ty), (lx, ly), s in [((cx - r + 60, 110), (cx - r + 80, cy - 85), "水晶体"),
                                   ((cx + 50, 70), (cx + 120, cy - 150), "網膜"),
                                   ((cx + 190, 600), (cx + r - 12, cy + 120), "反射層（タペタム）")]:
        d.line([(tx, ty + 18), (lx, ly)], fill=ink, width=1)
        d.text((tx, ty), s, font=f, fill=ink, anchor="mm")
    fs = ImageFont.truetype(FM, 22)
    d.text((w / 2, h - 66), "S T R U C T U R E   O F   T H E   F E L I N E   E Y E", font=fs, fill=ink, anchor="mm")
    return img


def build():
    rm.build_assets()
    A.update(rm.ASSETS)
    A["corner_big"] = rm.ASSETS["corner"]
    A["eyes_big"] = with_shadow(card_eyes().resize((520, 616), Image.LANCZOS), 2.0)
    A["diagram"] = with_shadow(card_eye_diagram().resize((760, 543), Image.LANCZOS), -1.5)
    A["subs"] = [(a, b, spaced_text(s, FB, 54, WHITE)) for a, b, s in SUBS]
    T = lambda s: spaced_text(s, FB, 40, WHITE, spacing=0.04)
    C = lambda s, c=(200, 196, 188, 255): spaced_text(s, FM, 21, c, spacing=0.04)
    R = lambda s, c=GREY: spaced_text(s, FM, 22, c, spacing=0.03)
    L = lambda s: spaced_text(s, FB, 28, WHITE, spacing=0.05)
    A["hdr"] = [
        (T("猫が見つめる「何もない場所」"), C("深夜、部屋の隅をじっと見つめる猫（イメージ図）"), R("図：本動画のために作画")),
        (T("人と猫が聞こえる音の範囲"), C("可聴域の比較（周波数は対数目盛）", (200, 210, 206, 255)),
         R("出典：Heffner & Heffner (1985) Hearing Research 19", TEAL_GREY)),
        (T("暗闇で光る、猫の目"), C("網膜の裏にある反射層「タペタム」（イメージ図）"), R("図：本動画のために作画")),
        (T("人と猫が見える光の範囲"), C("波長（nm）。猫の紫外線域は可能性を示すイメージ", (200, 210, 206, 255)),
         R("出典：Douglas & Jeffery (2014) Proc. R. Soc. B 281", TEAL_GREY)),
        (None, None, R("左右とも：本動画のために作画")),
    ]
    A["lab3l"], A["lab3r"] = L("光をはね返す層"), L("暗闇で光る目")
    A["lab5l"], A["lab5r"] = L("視線の先には、何もない"), L("わずかな光を集める目")
    A["q1"] = spaced_text("なぜ、何もない場所を見つめるのか？", FB, 30, WHITE, spacing=0.06)
    A["q2"] = spaced_text("その答えは、まだ闇の中に。", FB, 30, WHITE, spacing=0.06)
    sm = (190, 214, 208, 255)
    S = lambda s: spaced_text(s, FM, 24, sm, spacing=0.02)
    A["nm_ax"] = {nm: spaced_text(f"{nm}nm", FM, 22, (130, 158, 152, 255), spacing=0.02, shadow=False) for nm in (300, 400, 500, 600, 700)}
    A["nm_lo"], A["nm_hi"] = S("約400nm"), S("約700nm")
    A["uv"] = spaced_text("紫外線", FB, 28, (186, 160, 255, 255), spacing=0.08)
    A["vis"] = spaced_text("目に見える光（可視光）", FB, 28, (220, 226, 214, 255), spacing=0.06)
    A["uvq"] = spaced_text("？", FB, 40, (186, 160, 255, 255))
    # 可視光のスペクトル（くすませた虹色）
    xs = np.linspace(0, 1, 600)
    hue = (0.78 - 0.78 * xs) % 1
    spec = Image.fromarray((np.stack([hue, np.full_like(xs, 0.55), np.full_like(xs, 0.9)], -1)[None].repeat(18, 0) * 255).astype(np.uint8), "HSV").convert("RGBA")
    A["spectrum"] = spec


# ------------------------------------------------------------ ショット
def shot_corner(lt, dur):
    f = bg_zoom(A["rock"], lt, 0, dur, 1.0, 1.06, ox=-50)
    c = scaled(A["corner_big"], 0.86 + 0.04 * lt / dur)
    f.alpha_composite(c, (int(W * 0.60 - c.width / 2 - 12 * lt), int(CH * 0.53 - c.height / 2)))
    return f


def shot_hearing(lt, dur):
    f = bg_zoom(A["teal"], lt, 0, dur, 1.04, 1.12, ox=70, oy=-20)
    pan = -22 * lt
    fx = lambda fr: rm.freq_x(fr, pan)
    ov = Image.new("RGBA", f.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for fr, lbl in A["ax"].items():
        d.line([(fx(fr), 200), (fx(fr), 585)], fill=(150, 200, 190, 50), width=2)
        put(ov, lbl, fx(fr), 592, alpha=0.9, anchor="mt")
    za = ramp(lt, 3.6, 4.2)
    if za > 0:
        x0, x1 = fx(20000), fx(85000)
        d.rectangle([x0, 250, x1, 500], fill=(120, 232, 214, int(40 * za)))
        d.line([(x0, 250), (x0, 500)], fill=(150, 236, 220, int(160 * za)), width=2)
        put(ov, A["zone"], (x0 + x1) / 2, 512, alpha=za, anchor="mt")
    f.alpha_composite(ov)
    bars(f, [("human", fx(20), fx(20000), 300, 0.9, "h_lo", "h_hi", (210, 214, 200)),
             ("cat", fx(48), fx(85000), 430, 2.0, "c_lo", "c_hi", (120, 232, 214))], lt)
    return f


def bars(f, rows, lt, dashed=None):
    d = ImageDraw.Draw(f)
    for key, x0, xe, y, st, kl, kh, col in rows:
        p = ramp(lt, st, st + 1.0)
        if p <= 0:
            continue
        if key:
            put(f, A[key], x0 - 90, y - 34, alpha=min(1, p * 2))
        x1 = x0 + (xe - x0) * p
        glow = Image.new("RGBA", f.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).rounded_rectangle([x0, y - 9, x1, y + 9], radius=9, fill=col + (200,))
        f.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
        d.rounded_rectangle([x0, y - 5, x1, y + 5], radius=5, fill=col + (255,))
        for xx, lab, show in ((x0, kl, p > 0.05), (x1, kh, p > 0.98)):
            if show and lab:
                d.ellipse([xx - 9, y - 9, xx + 9, y + 9], fill=(245, 245, 235, 255))
                put(f, A[lab], xx, y + 16, anchor="mt")


def shot_eyes(lt, dur):
    f = bg_zoom(A["rock"], lt, 0, dur, 1.03, 1.08, ox=40, oy=10)
    l, r = A["diagram"], A["eyes_big"]
    pl, pr = ramp(lt, 0.2, 1.0), ramp(lt, 0.7, 1.5)
    yl = int(CH * 0.55 - l.height / 2)
    yr = int(CH * 0.52 - r.height / 2)
    xl = int(W * 0.33 - l.width / 2 - 80 * (1 - pl) - 6 * lt)
    xr = int(W * 0.73 - r.width / 2 + 80 * (1 - pr) + 6 * lt)
    if pl > 0:
        put(f, l, xl, yl, pl)
        put(f, A["lab3l"], xl + l.width / 2, yl + 18, ramp(lt, 1.0, 1.4), anchor="mt")
    if pr > 0:
        put(f, r, xr, yr, pr)
        put(f, A["lab3r"], xr + r.width / 2, yr + 12, ramp(lt, 1.5, 1.9), anchor="mt")
    return f


def nm_x(nm, pan):
    return int(260 + (nm - 280) / (760 - 280) * (W - 520) + pan)


def shot_light(lt, dur):
    f = bg_zoom(A["teal"], lt, 0, dur, 1.10, 1.04, ox=-60, oy=10)
    pan = 18 * lt
    ov = Image.new("RGBA", f.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(ov)
    for nm, lbl in A["nm_ax"].items():
        d.line([(nm_x(nm, pan), 200), (nm_x(nm, pan), 585)], fill=(150, 200, 190, 50), width=2)
        put(ov, lbl, nm_x(nm, pan), 592, alpha=0.9, anchor="mt")
    ua = ramp(lt, 0.4, 1.0)
    if ua > 0:  # 紫外線の領域（ほのかな紫）
        d.rectangle([nm_x(280, pan), 220, nm_x(400, pan), 560], fill=(150, 120, 255, int(28 * ua)))
        put(ov, A["uv"], (nm_x(280, pan) + nm_x(400, pan)) / 2, 226, ua, anchor="mt")
        put(ov, A["vis"], (nm_x(400, pan) + nm_x(700, pan)) / 2, 226, ua, anchor="mt")
    f.alpha_composite(ov)
    # 人: 可視光のスペクトル帯
    p = ramp(lt, 1.0, 2.0)
    x0, xe, y = nm_x(400, pan), nm_x(700, pan), 330
    if p > 0:
        put(f, A["human"], x0 - 90, y - 34, min(1, p * 2))
        wbar = max(2, int((xe - x0) * p))
        sp = A["spectrum"].resize((xe - x0, 18)).crop((0, 0, wbar, 18))
        glow = Image.new("RGBA", f.size, (0, 0, 0, 0))
        glow.alpha_composite(sp, (x0, y - 9))
        f.alpha_composite(glow.filter(ImageFilter.GaussianBlur(10)))
        f.alpha_composite(sp.resize((wbar, 10)), (x0, y - 5))
        d = ImageDraw.Draw(f)
        d.ellipse([x0 - 9, y - 9, x0 + 9, y + 9], fill=(245, 245, 235, 255))
        put(f, A["nm_lo"], x0, y + 16, anchor="mt")
        if p > 0.98:
            d.ellipse([xe - 9, y - 9, xe + 9, y + 9], fill=(245, 245, 235, 255))
            put(f, A["nm_hi"], xe, y + 16, anchor="mt")
    # 猫: 可視光の帯＋紫外線側へ点線で延びる「可能性」
    put(f, A["cat"], nm_x(300, pan) - 110, 460 - 34, ramp(lt, 2.2, 2.7))
    bars(f, [(None, nm_x(400, pan), nm_x(700, pan), 460, 2.2, None, None, (120, 232, 214))], lt)
    q = ramp(lt, 3.4, 4.6)
    if q > 0:
        d = ImageDraw.Draw(f)
        xa, xb = nm_x(400, pan), nm_x(318, pan)
        x = xa
        while x > xa - (xa - xb) * q:
            d.line([(x, 460), (max(x - 14, xb), 460)], fill=(186, 160, 255, 255), width=6)
            x -= 24
        put(f, A["uvq"], xb - 50, 428, ramp(lt, 4.4, 4.9))
    return f


def shot_final(lt, dur):
    f = bg_zoom(A["rock"], lt, 0, dur, 1.06, 1.10, ox=30)
    l, r = A["corner_s"], A["eyes"]
    xl = int(W * 0.29 - l.width / 2 - 60 * (1 - ramp(lt, 0.0, 0.8)))
    xr = int(W * 0.69 - r.width / 2 + 60 * (1 - ramp(lt, 0.2, 1.0)))
    yl, yr = int(CH * 0.56 - l.height / 2), int(CH * 0.56 - r.height / 2 + 30)
    f.alpha_composite(l, (xl, yl))
    f.alpha_composite(r, (xr, yr))
    put(f, A["lab5l"], xl + l.width / 2, yl + 8, ramp(lt, 0.5, 0.9), anchor="mt")
    put(f, A["lab5r"], xr + r.width / 2, yr - 6, ramp(lt, 0.7, 1.1), anchor="mt")
    put(f, A["q1"], W / 2, 26, ramp(lt, 2.6, 3.1), anchor="mt")
    put(f, A["q2"], W / 2, 72, ramp(lt, 3.4, 3.9), anchor="mt")
    return f


SHOT_FN = [shot_corner, shot_hearing, shot_eyes, shot_light, shot_final]


def render_frame(i):
    t = i / FPS
    pic = None
    for k, ((a, b), fn) in enumerate(zip(SHOTS, SHOT_FN)):
        if not (a <= t < b + 1e-6):
            continue
        img = fn(t - a, b - a)
        title, cap, cred = A["hdr"][k]
        ha = window(t, a + 0.5, b, 0.5) if k < 4 else ramp(t, a + 0.3, a + 0.8)
        if title is not None:
            put(img, title, 56, 18, ha)
            put(img, cap, 60, 80, ha)
        put(img, cred, W - 40, 22, ha, anchor="rt")
        al = min(ramp(t, a, a + XF) if k else 1.0, 1 - ramp(t, b - XF, b) if k < 4 else 1.0)
        pic = img if pic is None else Image.blend(pic, img, al)
    black = Image.new("RGBA", (W, CH), (0, 0, 0, 255))
    pic = Image.composite(black, pic, A["shade"])
    for a, b, img in A["subs"]:
        al = window(t, a, b, 0.25)
        if al > 0:
            put(pic, img, W / 2, CH - 168, al, anchor="mt")
    k = min(ramp(t, 0.0, 0.6), 1 - ramp(t, DUR - 0.7, DUR))
    if k < 1:
        pic = Image.blend(black, pic, k)
    arr = np.asarray(pic.convert("RGB"), dtype=np.int16)
    rng = np.random.default_rng(i)
    arr = np.clip(arr + rng.normal(0, 5, arr.shape[:2])[..., None], 0, 255).astype(np.uint8)
    out = Image.new("RGB", (W, H), (0, 0, 0))
    out.paste(Image.fromarray(arr), (0, BAR))
    return out.tobytes()


def init_worker():
    build()


# ------------------------------------------------------------ 音
def soundtrack():
    n = int(DUR * SR)
    t = np.arange(n) / SR
    rng = np.random.default_rng(2)
    swell = 0.6 + 0.4 * np.sin(2 * np.pi * t / 11 - 1.2)
    drone = (np.sin(2 * np.pi * 55 * t) + 0.7 * np.sin(2 * np.pi * 55.4 * t)
             + 0.45 * np.sin(2 * np.pi * 82.4 * t + np.sin(2 * np.pi * 0.2 * t))) * 0.08 * swell
    wind = np.convolve(rng.standard_normal(n), np.ones(200) / 200, "same") * 0.9
    wind *= 0.5 + 0.5 * np.sin(2 * np.pi * 0.11 * t) ** 2
    out = drone + wind * 0.12

    def add(at, sig):
        s = int(at * SR)
        e = min(n, s + len(sig))
        out[s:e] += sig[: e - s]

    tt = np.arange(int(3 * SR)) / SR
    boom = np.sin(2 * np.pi * (48 * tt - 14 * tt * tt)) * np.exp(-tt * 2.2) * 0.45
    for at in [0.05] + [a for a, _ in SHOTS[1:]]:
        add(at + 0.3, boom)
    # まばらなピアノ風の音（A マイナー）
    for at, midi in [(1.6, 57), (4.3, 60), (7.0, 64), (9.4, 59), (13.4, 57), (15.5, 62),
                     (19.3, 60), (21.5, 64), (25.3, 69), (26.8, 64), (28.2, 57)]:
        fr = 440 * 2 ** ((midi - 69) / 12)
        tn = np.arange(int(3.5 * SR)) / SR
        env = np.exp(-tn * 1.3) * np.minimum(1, tn / 0.01)
        add(at, (np.sin(2 * np.pi * fr * tn) + 0.3 * np.sin(4 * np.pi * fr * tn)) * env * 0.06)
    tn = np.arange(int(2 * SR)) / SR
    for at, fr in ((7.6, 6200), (8.0, 7400), (20.0, 5200)):  # 「キーン」
        add(at, np.sin(2 * np.pi * fr * tn) * np.exp(-tn * 1.6) * 0.03)
    out *= np.minimum(1, np.minimum(t / 0.6, (DUR - t) / 0.8))
    out = out / np.abs(out).max() * 0.5
    return np.stack([out, out], 1).astype(np.float32)


def main(dst):
    wav = Path(dst).with_suffix(".f32")
    soundtrack().tofile(wav)
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-f", "f32le", "-ar", str(SR), "-ac", "2", "-i", str(wav),
           "-c:v", "libx264", "-preset", "slow", "-crf", "24", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-shortest", dst]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4, initializer=init_worker) as pool:
        for b in pool.imap(render_frame, range(int(DUR * FPS)), chunksize=4):
            p.stdin.write(b)
    p.stdin.close()
    p.wait()
    wav.unlink()
    print("done", dst)


if __name__ == "__main__":
    if len(sys.argv) > 2:
        build()
        ims = [Image.frombytes("RGB", (W, H), render_frame(int(float(x) * FPS))).resize((960, 540)) for x in sys.argv[2:]]
        sheet = Image.new("RGB", (960 * 2, 540 * ((len(ims) + 1) // 2)))
        for k, im in enumerate(ims):
            sheet.paste(im, ((k % 2) * 960, (k // 2) * 540))
        sheet.save(sys.argv[1])
    else:
        main(sys.argv[1])
