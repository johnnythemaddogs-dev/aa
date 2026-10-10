"""手相ショート動画「太陽線があるのにお金がない理由」(Instagram リール 9:16)。

使い方:
  python video/tesou_taiyousen.py ナレーション.wav 手のひら.png [-o 出力.mp4]
  python video/tesou_taiyousen.py ナレーション.wav 手のひら.png --preview   # 静止画で確認だけ

- テロップの改行位置は CUES に書いた位置だけ (自動で折り返さない)。[ ] で囲んだ語は金色で強調
- テロップの表示タイミングは音声の無音区間から自動で決め、同名の .srt にも書き出す
  ずれる場合は .srt を直して --timings で渡すと、その時間で作り直す
- 太陽線の位置は --sunline で画像内の割合 (左上0,0 / 右下1,1) を指定。--preview の格子画像で確認できる
"""
from __future__ import annotations

import argparse
import math
import random
import re
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "app"))

from shortvideo import (  # noqa: E402
    FPS, GOTHIC, GOTHIC_BOLD, H, MINCHO, W, LineLayer, VideoWriter, bezier, circle_path, clamp, ease_back,
    ease_in_out, ease_out, find_font, font, hex_rgb, paste, plain, prog, radial_glow, read_wav, render_telop,
    rotate, smooth, sparkle, star5, text_image, vertical_gradient,
)
from subtitles import Cue, align_weights, to_srt, weight  # noqa: E402

# (テロップ, 読み上げ原稿)  テロップの \n が改行位置。読み上げ原稿は時間配分の目安に使う
CUES = [
    ("[無料鑑定]で\nこんな相談をいただきました", "無料鑑定で、こんな相談をいただきました。"),
    ("「両手に[太陽線]があるのに\n全然お金も人気もありません…」", "「両手に太陽線があるのに、全然お金もにんきもありません…」"),
    ("実は 同じように悩んでいる人\nすごく多いんです", "実は、同じように悩んでいる人、すごく多いんです。"),
    ("でも 安心してください", "でも安心してください。"),
    ("あなたの手相が間違っている\nわけではありません", "あなたの手相が間違っているわけではありません。"),
    ("[太陽線]は", "太陽線は、"),
    ("「勝手に大金持ちになる線」\nではなく", "「勝手に大金持ちになる線」ではなく、"),
    ("「あなたの[良さ]が\n人に伝わった瞬間に", "「あなたの良さが人に伝わった瞬間に、"),
    ("[爆発的にお金が巡る線]」\nなんです", "爆発的にお金が巡る線」なんです。"),
    ("今 お金がないと\n感じているなら", "今お金がないと感じているなら、"),
    ("それは 才能がないのではなく", "それは才能がないのではなく、"),
    ("「自分の良さが出せない環境」\nにいるだけ", "「自分の良さが出せない環境」にいるだけ。"),
    ("ただ決められた作業を\nこなす場所から", "ただ決められた作業をこなす場所から、"),
    ("あなたの人柄やセンスが\n人に伝わる場所に変わった瞬間", "あなたの人柄やセンスが人に伝わる場所に変わった瞬間、"),
    ("一気に[評価]と[お金]が\nついてきますよ", "一気に評価とお金がついてきますよ。"),
    ("あなたの手には\n[太陽線]がありましたか？", "あなたの手には、太陽線がありましたか？"),
    ("あった人はコメント欄に\n「[太陽]」と書いてね", "あった人はコメント欄に「太陽」と書いてね。"),
    ("あなた自身の手相を\nもっと詳しく知りたい方は", "あなた自身の手相をもっと詳しく知りたい方は、"),
    ("プロフィールのリンクから\n[公式LINE]で[無料鑑定]しています", "プロフィールのリンクから、公式LINEで無料鑑定しています。"),
]

TITLE = "太陽線があるのに お金がない理由"

GOLD = "#F4D58D"
IVORY = "#FFF4DC"
SUN = "#FFB443"
BG_TOP, BG_BOTTOM = "#130E36", "#33205A"

TELOP_Y = 1430          # テロップ中心 (リールの下部 UI にかからない高さ)
PALM_BOX = (880, 980)   # 手のひら画像の最大サイズ
PALM_CENTER = (540, 800)
XFADE = 0.45            # 場面転換のクロスフェード秒


# ================================================================ helpers

def rrect_path(x0, y0, x1, y1, r):
    """角丸四角の線 (上辺中央から時計回り)。"""
    pts = [((x0 + x1) / 2, y0), (x1 - r, y0)]
    pts += circle_path(x1 - r, y0 + r, r, -90, 90, 12)
    pts += [(x1, y1 - r)]
    pts += circle_path(x1 - r, y1 - r, r, 0, 90, 12)
    pts += [(x0 + r, y1)]
    pts += circle_path(x0 + r, y1 - r, r, 90, 90, 12)
    pts += [(x0, y0 + r)]
    pts += circle_path(x0 + r, y0 + r, r, 180, 90, 12)
    pts += [((x0 + x1) / 2, y0)]
    return pts


def mandala(cx, cy, R, rot=0.0, petals=12):
    rings = [circle_path(cx, cy, R, rot - 90), circle_path(cx, cy, R * 0.93, rot - 90),
             circle_path(cx, cy, R * 0.58, rot - 90), circle_path(cx, cy, R * 0.3, rot - 90)]
    pet = []
    for i in range(petals):
        a = math.radians(rot + i * 360 / petals - 90)
        da = math.radians(180 / petals) * 0.95
        p_in = (cx + R * 0.58 * math.cos(a), cy + R * 0.58 * math.sin(a))
        tip = (cx + R * 0.93 * math.cos(a), cy + R * 0.93 * math.sin(a))
        for s in (-1, 1):
            c1 = (cx + R * 0.72 * math.cos(a + s * da), cy + R * 0.72 * math.sin(a + s * da))
            c2 = (cx + R * 0.86 * math.cos(a + s * da * 0.5), cy + R * 0.86 * math.sin(a + s * da * 0.5))
            pet.append(bezier(p_in, c1, c2, tip, 18))
        # 内側の小さな花弁
        b = a + math.radians(180 / petals)
        q_in = (cx + R * 0.3 * math.cos(b), cy + R * 0.3 * math.sin(b))
        q_tip = (cx + R * 0.55 * math.cos(b), cy + R * 0.55 * math.sin(b))
        for s in (-1, 1):
            c = (cx + R * 0.45 * math.cos(b + s * da * 0.9), cy + R * 0.45 * math.sin(b + s * da * 0.9))
            pet.append(bezier(q_in, c, c, q_tip, 12))
    return rings, pet


def lotus(cx, cy, s):
    base = (cx, cy + 0.55 * s)
    paths = []
    for tip_dx, tip_dy, wdt in [(0, -0.75, 0.32), (-0.42, -0.42, 0.3), (0.42, -0.42, 0.3),
                                 (-0.82, -0.05, 0.28), (0.82, -0.05, 0.28)]:
        tip = (cx + tip_dx * s, cy + tip_dy * s)
        ang = math.atan2(tip[1] - base[1], tip[0] - base[0]) + math.pi / 2
        nx, ny = math.cos(ang) * wdt * s, math.sin(ang) * wdt * s
        mid = ((base[0] + tip[0]) / 2, (base[1] + tip[1]) / 2)
        for k in (-1, 1):
            paths.append(bezier(base, (mid[0] + k * nx, mid[1] + k * ny), (tip[0] + k * nx * 0.25, tip[1] + k * ny * 0.25), tip, 24))
    waves = []
    for j, (wy, ww) in enumerate([(0.68, 1.0), (0.8, 0.75), (0.92, 0.5)]):
        pts = []
        for i in range(61):
            u = i / 60
            x = cx - ww * s + 2 * ww * s * u
            pts.append((x, cy + wy * s + math.sin(u * math.pi * 4 + j) * 0.03 * s))
        waves.append(pts)
    return paths, waves


def sun_icon(cx, cy, r, rays=12, rot=0.0):
    paths = [circle_path(cx, cy, r, rot - 90)]
    for i in range(rays):
        a = math.radians(rot + i * 360 / rays)
        L = r * (0.75 if i % 2 else 0.45)
        paths.append([(cx + (r * 1.25) * math.cos(a), cy + (r * 1.25) * math.sin(a)),
                      (cx + (r * 1.25 + L) * math.cos(a), cy + (r * 1.25 + L) * math.sin(a))])
    return paths


def crescent(cx, cy, r):
    outer = circle_path(cx, cy, r, 40, 280)
    inner = circle_path(cx + r * 0.42, cy - r * 0.2, r * 0.82, 40 + 33, 214)
    return [outer, inner[::-1]]


def fill_alpha(layer: LineLayer, pts, alpha=1.0):
    s = layer.SS
    layer.d.polygon([(x * s, y * s) for x, y in pts], fill=int(255 * clamp(alpha)))
    layer.dirty = True


# ================================================================ context

class Ctx:
    def __init__(self, args, cues: list[Cue], duration: float):
        self.cues = cues
        self.duration = duration
        self.f_bold = find_font(GOTHIC_BOLD, args.font)
        self.f_reg = find_font(GOTHIC, args.font)
        self.f_min = find_font(MINCHO, args.title_font)
        self.bg = vertical_gradient(BG_TOP, BG_BOTTOM)
        self.halo = radial_glow(520, "#8A5CC8", 0.55)
        self.sun_halo = radial_glow(420, "#FFC266", 0.6)

        palm = Image.open(args.palm).convert("RGBA")
        k = min(PALM_BOX[0] / palm.width, PALM_BOX[1] / palm.height)
        palm = palm.resize((int(palm.width * k), int(palm.height * k)), Image.LANCZOS)
        m = Image.new("L", palm.size, 0)
        ImageDraw.Draw(m).rounded_rectangle((0, 0, palm.width - 1, palm.height - 1), radius=44, fill=255)
        palm.putalpha(Image.composite(palm.getchannel("A"), m, m))
        self.palm = palm
        self.palm_rect = (PALM_CENTER[0] - palm.width / 2, PALM_CENTER[1] - palm.height / 2,
                          PALM_CENTER[0] + palm.width / 2, PALM_CENTER[1] + palm.height / 2)
        pts = sorted(args.sunline, key=lambda p: -p[1])  # 手首側(下)から指側(上)へ描く
        x0, y0, x1, y1 = self.palm_rect
        self.sunline = smooth([(x0 + (x1 - x0) * u, y0 + (y1 - y0) * v) for u, v in pts], 14)

        self.telops = [render_telop(t, self.f_bold) for t, _ in CUES]
        self.title = text_image(TITLE, self.f_min, 58, color="#FFE9B0", stroke="#130E36", stroke_width=4)
        self.label = self._label("太陽線")
        rnd = random.Random(7)
        self.stars = [(rnd.uniform(20, W - 20), rnd.uniform(20, H - 20), rnd.uniform(1.2, 3.2), rnd.uniform(0, 6.28),
                       rnd.uniform(0.6, 1.6)) for _ in range(90)]
        self.rising = [(rnd.uniform(140, W - 140), rnd.uniform(0, 1), rnd.uniform(9, 22), rnd.uniform(0, 6.28))
                       for _ in range(26)]
        self.chat = ChatCard(self)
        self.comment_font = font(self.f_reg, 44)

    def _label(self, text):
        f = font(self.f_bold, 46)
        w = int(f.getlength(text)) + 56
        img = Image.new("RGBA", (w, 80), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.rounded_rectangle((0, 0, w - 1, 79), radius=40, fill=(30, 18, 60, 220), outline=hex_rgb(SUN), width=3)
        d.text((28, 14), text, font=f, fill="#FFE2A6")
        return img

    def cs(self, i):  # cue start
        return self.cues[i].start

    def ce(self, i):
        return self.cues[i].end


class Layers:
    def __init__(self):
        self.bg = LineLayer(GOLD, glow=0.5, glow_radius=6)
        self.gold = LineLayer(GOLD, glow=0.9, glow_radius=7)
        self.white = LineLayer(IVORY, glow=1.0, glow_radius=8)
        self.sun = LineLayer(SUN, glow=1.3, glow_radius=10)


# ================================================================ chat (LINE 風の相談画面)

class ChatCard:
    X0, Y0, X1, Y1 = 90, 300, 990, 1240

    def __init__(self, ctx: Ctx):
        self.ctx = ctx
        w, h = self.X1 - self.X0, self.Y1 - self.Y0
        base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(base)
        d.rounded_rectangle((0, 0, w - 1, h - 1), radius=44, fill="#8FA6CF")
        d.rounded_rectangle((0, 0, w - 1, 130), radius=44, fill="#273250")
        d.rectangle((0, 90, w - 1, 130), fill="#273250")
        fb = font(ctx.f_bold, 40)
        d.line([(62, 46), (44, 66), (62, 86)], fill="white", width=6, joint="curve")
        title = "公式LINE  手相の無料鑑定"
        d.text(((w - fb.getlength(title)) / 2, 44), title, font=fb, fill="white")
        d.rounded_rectangle((0, h - 120, w - 1, h - 1), radius=44, fill="#F3F4F7")
        d.rectangle((0, h - 120, w - 1, h - 80), fill="#F3F4F7")
        d.rounded_rectangle((110, h - 96, w - 110, h - 30), radius=33, fill="white", outline="#D5D8DE", width=2)
        d.text((140, h - 84), "メッセージを入力", font=font(ctx.f_reg, 32), fill="#A0A4AC")
        for cx in (55, w - 55):
            d.ellipse((cx - 22, h - 85, cx + 22, h - 41), outline="#9AA0AA", width=4)
        chip = "今日"
        fc = font(ctx.f_reg, 28)
        cw = fc.getlength(chip) + 40
        d.rounded_rectangle(((w - cw) / 2, 160, (w + cw) / 2, 206), radius=23, fill=(60, 75, 110, 120))
        d.text(((w - fc.getlength(chip)) / 2, 167), chip, font=fc, fill="white")
        self.base = base

        self.avatar = Image.new("RGBA", (92, 92), (0, 0, 0, 0))
        ad = ImageDraw.Draw(self.avatar)
        ad.ellipse((0, 0, 91, 91), fill="#E9D8F2")
        ad.ellipse((30, 16, 62, 48), fill="#A88CC0")
        ad.pieslice((14, 52, 78, 116), 180, 360, fill="#A88CC0")

        self.msg = self._bubble("両手に太陽線があるのに、\n全然お金も人気もありません…", "white", "#222222", tail="left")
        self.reply = self._bubble("ご相談ありがとうございます\n実は、よくあるお悩みなんです", "#8DE063", "#1E2A12", tail="right")
        self.typing = self._bubble("　　　", "white", "#222222", tail="left")
        self.name = text_image("ご相談者さま", ctx.f_reg, 28, color="#F5F7FF")
        self.t1 = text_image("23:03", ctx.f_reg, 24, color="#EEF2FA")
        self.t2 = text_image("既読\n23:05", ctx.f_reg, 24, color="#EEF2FA", align="right", line_gap=0.1)

    def _bubble(self, text, fill, color, tail):
        f = font(self.ctx.f_reg, 40)
        lines = text.split("\n")
        tw = max(f.getlength(ln) for ln in lines)
        lh = 56
        w, h = int(tw) + 64, lh * len(lines) + 40
        img = Image.new("RGBA", (w + 16, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        ox = 16 if tail == "left" else 0
        d.rounded_rectangle((ox, 0, ox + w - 1, h - 1), radius=34, fill=fill)
        if tail == "left":
            d.polygon([(ox + 8, 14), (0, 6), (ox + 18, 34)], fill=fill)
        else:
            d.polygon([(w - 8, 14), (w + 15, 6), (w - 18, 34)], fill=fill)
        for i, ln in enumerate(lines):
            d.text((ox + 32, 20 + i * lh), ln, font=f, fill=color)
        return img

    def draw(self, frame, L: Layers, t, a):
        ctx = self.ctx
        lt = t
        e = ease_back(prog(lt, 0.0, 0.7))
        alpha = a * clamp(prog(lt, 0.0, 0.4))
        card_s = 0.9 + 0.1 * e
        cx, cy = (self.X0 + self.X1) / 2, (self.Y0 + self.Y1) / 2
        card = self.base.copy()

        def put(img, x, y, s=1.0, al=1.0, anchor_left=True):
            if s <= 0.01 or al <= 0:
                return
            im = img if abs(s - 1) < 1e-3 else img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.LANCZOS)
            if al < 1:
                from shortvideo import with_alpha
                im = with_alpha(im, al)
            px = x if anchor_left else x - im.width
            card.alpha_composite(im, (int(px), int(y + (img.height - im.height) / 2)))

        c1 = ctx.cs(1)
        if lt < c1:  # 入力中…
            ta = prog(lt, 0.8, 0.25)
            if ta > 0:
                put(self.avatar, 28, 250, al=ta)
                put(self.typing, 134, 270, al=ta)
                dd = ImageDraw.Draw(card)
                for i in range(3):
                    ph = (lt * 3 - i * 0.33) % 1
                    r = 8 + 4 * max(0, math.sin(ph * math.pi))
                    x, y = 134 + 16 + 46 + i * 34, 270 + 48
                    dd.ellipse((x - r, y - r, x + r, y + r), fill=(150, 150, 160, int(255 * ta)))
        else:
            pe = ease_back(prog(lt, c1, 0.4))
            put(self.avatar, 28, 250)
            put(self.name, 136, 228)
            put(self.msg, 134, 270, s=pe)
            put(self.t1, 134 + self.msg.width + 10, 270 + self.msg.height - 34, al=prog(lt, c1 + 0.3, 0.3))
        c2 = ctx.cs(2)
        if lt >= c2 + 0.2:
            pe = ease_back(prog(lt, c2 + 0.2, 0.4))
            rx = (self.X1 - self.X0) - 30
            put(self.reply, rx, 540, s=pe, anchor_left=False)
            put(self.t2, rx - self.reply.width - 10, 540 + self.reply.height - 64, al=prog(lt, c2 + 0.6, 0.3), anchor_left=False)
        paste(frame, card, (cx, cy), alpha, card_s)
        # まわりにきらめき
        for i, (sx, sy, sr) in enumerate([(120, 285, 26), (975, 420, 20), (985, 1200, 30), (95, 1050, 18)]):
            tw = 0.5 + 0.5 * math.sin(t * 2.2 + i * 1.7)
            L.white.paths(sparkle(sx, sy, sr * (0.7 + 0.3 * tw)), prog(t, 0.6 + i * 0.2, 0.5), 2.5, a * (0.4 + 0.6 * tw))


# ================================================================ scenes

def scene_chat(ctx, frame, L, t, a):
    ctx.chat.draw(frame, L, t, a)


def scene_relief(ctx, frame, L, t, a):
    t0 = ctx.cs(3)
    lt = t - t0
    paste(frame, ctx.halo, (540, 820), a * 0.8 * ease_out(prog(lt, 0, 1.2)))
    petals, waves = lotus(540, 820, 300)
    L.gold.paths(petals, ease_in_out(prog(lt, 0.1, 2.4)), 4, a)
    L.gold.paths(waves, ease_out(prog(lt, 1.2, 1.4)), 3, a * 0.8, sequential=False)
    L.white.path(circle_path(540, 780, 380, -90), ease_in_out(prog(lt, 0.0, 2.8)), 2.5, a * 0.7)
    L.white.path(circle_path(540, 780, 400, 90), ease_in_out(prog(lt, 0.4, 2.8)), 1.5, a * 0.45)
    L.gold.paths(crescent(820, 420, 70), ease_out(prog(lt, 0.8, 1.5)), 3.5, a)
    for i, (sx, sy, sr) in enumerate([(250, 470, 26), (870, 1130, 22), (200, 1080, 18), (700, 340, 16)]):
        tw = 0.5 + 0.5 * math.sin(t * 2.5 + i * 2)
        L.white.paths(sparkle(sx, sy, sr * (0.7 + 0.3 * tw)), prog(lt, 1.0 + i * 0.25, 0.5), 2.5, a * (0.5 + 0.5 * tw))


def draw_palm(ctx, frame, L, lt, a, line_start, line_dur):
    paste(frame, ctx.halo, PALM_CENTER, a * 0.6)
    paste(frame, ctx.palm, PALM_CENTER, a * ease_out(prog(lt, 0, 0.6)), 1.04 - 0.04 * ease_out(prog(lt, 0, 1.2)))
    x0, y0, x1, y1 = ctx.palm_rect
    L.gold.path(rrect_path(x0 - 14, y0 - 14, x1 + 14, y1 + 14, 56), ease_in_out(prog(lt, 0.1, 1.4)), 3, a)
    L.gold.path(rrect_path(x0 - 26, y0 - 26, x1 + 26, y1 + 26, 66), ease_in_out(prog(lt, 0.3, 1.6)), 1.5, a * 0.6)
    for cx_, cy_ in [(x0 - 20, y0 - 20), (x1 + 20, y0 - 20), (x0 - 20, y1 + 20), (x1 + 20, y1 + 20)]:
        L.white.paths(sparkle(cx_, cy_, 22), prog(lt, 1.2, 0.5), 2.5, a)
    lp = ease_in_out(prog(lt, line_start, line_dur))
    L.sun.path(ctx.sunline, lp, 10, a)
    return lp


def sun_label(ctx, frame, L, lt, a, when):
    pa = ease_out(prog(lt, when, 0.5))
    if pa <= 0:
        return
    top = ctx.sunline[-1]
    left = top[0] > PALM_CENTER[0] + 60
    lx = top[0] + (-190 if left else 190)
    ly = top[1] - 70
    L.sun.path([(top[0] + (-14 if left else 14), top[1] - 8), (lx + (90 if left else -90), ly + 8)], pa, 3, a)
    paste(frame, ctx.label, (lx, ly - 10 * (1 - pa)), a * pa)


def scene_palm(ctx, frame, L, t, a):
    t0 = ctx.cs(5)
    lt = t - t0
    lp = draw_palm(ctx, frame, L, lt, a, 0.25, 1.8)
    sun_label(ctx, frame, L, lt, a, 1.9)
    line = ctx.sunline
    if lp >= 1:  # 線の上を光が流れる
        u = ((lt - 2.0) * 0.6) % 1
        p = line[min(len(line) - 1, int(u * (len(line) - 1)))]
        L.white.dot(p[0], p[1], 9, a * math.sin(u * math.pi))
    tb = ctx.cs(7) - t0   # 良さが伝わった瞬間に → 光が放たれる
    if lt > tb:
        top = line[-1]
        for k, ry in enumerate(sun_icon(top[0], top[1], 26, 12, rot=lt * 12)[1:]):
            L.sun.path(ry, ease_out(prog(lt, tb + k * 0.03, 0.6)), 4, a)
        paste(frame, ctx.sun_halo, top, a * 0.45 * ease_out(prog(lt, tb, 0.8)), 0.6)
    tc = ctx.cs(8) - t0   # 爆発的にお金が巡る → 光が手のまわりを巡る
    if lt > tc:
        k = ease_out(prog(lt, tc, 0.8))
        rx, ry = (ctx.palm_rect[2] - ctx.palm_rect[0]) * 0.56, (ctx.palm_rect[3] - ctx.palm_rect[1]) * 0.5
        for i in range(10):
            ang = (lt - tc) * 1.6 + i * math.tau / 10
            sx, sy = PALM_CENTER[0] + rx * math.cos(ang) * k, PALM_CENTER[1] + ry * math.sin(ang) * k
            L.white.paths(sparkle(sx, sy, 16 + 6 * math.sin(lt * 4 + i)), 1, 2.5, a * k)
        L.gold.path(circle_path(PALM_CENTER[0], PALM_CENTER[1], 520 * k, (lt - tc) * 60), 1, 2, a * (1 - prog(lt, tc + 0.8, 1.2)) * k)
        L.sun.path(line, 1, 10 + 4 * math.sin((lt - tc) * 6), a)


def box_paths(cx, cy, s):
    return [rrect_path(cx - s, cy - s, cx + s, cy + s, 30), rrect_path(cx - s - 18, cy - s - 18, cx + s + 18, cy + s + 18, 40)]


def bars(cx, cy, s, n=6):
    return [[(cx - s + (i + 1) * 2 * s / (n + 1), cy - s + 6), (cx - s + (i + 1) * 2 * s / (n + 1), cy + s - 6)] for i in range(n)]


def scene_box(ctx, frame, L, t, a):
    t0 = ctx.cs(9)
    lt = t - t0
    cx, cy, s = 540, 800, 250
    L.gold.paths(box_paths(cx, cy, s), ease_in_out(prog(lt, 0.0, 1.6)), 3.5, a * 0.85)
    tw = 0.5 + 0.5 * math.sin(t * 1.6)
    fill_alpha(L.white, star5(cx, cy, 46), a * (0.35 + 0.15 * tw) * prog(lt, 1.0, 0.8))
    L.white.path(star5(cx, cy, 46), ease_out(prog(lt, 0.9, 1.0)), 2.5, a * 0.7)
    tb = ctx.cs(11) - t0  # 良さが出せない環境 → 格子が下りる
    L.white.paths(bars(cx, cy, s), ease_in_out(prog(lt, tb, 1.2)), 3, a * 0.55, sequential=False)
    for i, (sx, sy) in enumerate([(230, 470), (860, 500), (850, 1110), (230, 1130)]):
        L.gold.paths(sparkle(sx, sy, 16), prog(lt, 0.8 + i * 0.2, 0.5), 2, a * 0.5)


def scene_change(ctx, frame, L, t, a):
    t0 = ctx.cs(12)
    lt = t - t0
    cx, cy, s = 540, 800, 250
    tb = ctx.cs(13) - t0  # 場所が変わった瞬間
    tc = ctx.cs(14) - t0  # 一気に評価とお金
    open_ = ease_in_out(prog(lt, tb, 0.9))
    L.gold.paths(box_paths(cx, cy, s), 1 - open_, 3.5, a * 0.85)
    L.white.paths(bars(cx, cy, s), 1, 3, a * 0.55 * (1 - prog(lt, tb - 0.3, 0.5)), sequential=False)
    g = ease_out(prog(lt, tb + 0.2, 1.2))
    sy = cy - 90 * g
    sr = 46 + 70 * g
    paste(frame, ctx.sun_halo, (cx, sy), a * (0.15 + 0.7 * g), 0.5 + 0.8 * g)
    fill_alpha(L.white, star5(cx, sy, sr, lt * 10 * g), a * (0.45 + 0.55 * g))
    L.white.path(star5(cx, sy, sr, lt * 10 * g), 1, 2.5, a)
    if g > 0:
        for i in range(16):
            ang = math.radians(i * 22.5 + lt * 8)
            r0, r1 = sr + 30, sr + 30 + (110 if i % 2 else 70) * g
            L.gold.path([(cx + r0 * math.cos(ang), sy + r0 * math.sin(ang)), (cx + r1 * math.cos(ang), sy + r1 * math.sin(ang))],
                        ease_out(prog(lt, tb + 0.4 + i * 0.03, 0.5)), 3.5, a)
        petals, waves = lotus(cx, sy + 290, 170)
        L.gold.paths(petals, ease_in_out(prog(lt, tb + 0.6, 1.6)), 3, a * 0.9)
    if lt > tc:
        k = lt - tc
        for i in range(3):  # 広がる波紋
            ph = ((k * 0.7) + i / 3) % 1
            L.gold.path(circle_path(cx, sy, sr + 60 + 420 * ph, -90), 1, 2, a * (1 - ph) * prog(k, 0, 0.4))
        for x, off, sz, ph in ctx.rising:  # 上へ昇る光
            yy = 1250 - ((k * 0.22 + off) % 1) * 1000
            tw = 0.5 + 0.5 * math.sin(k * 5 + ph)
            L.white.paths(sparkle(x, yy, sz * (0.6 + 0.4 * tw)), 1, 2.2, a * prog(k, 0, 0.5) * (0.4 + 0.6 * tw))


def scene_palm_again(ctx, frame, L, t, a):
    t0 = ctx.cs(15)
    lt = t - t0
    lp = draw_palm(ctx, frame, L, lt, a, 0.3, 1.0)
    sun_label(ctx, frame, L, lt, a, 1.2)
    if lp >= 1:
        pulse = 0.5 + 0.5 * math.sin((lt - 1.3) * 4)
        L.sun.path(ctx.sunline, 1, 10 + 5 * pulse, a)
        top = ctx.sunline[-1]
        paste(frame, ctx.sun_halo, top, a * 0.3 * pulse, 0.45)
    tb = ctx.cs(16) - t0  # コメント欄に「太陽」
    pa = ease_back(prog(lt, tb, 0.45))
    if pa > 0:
        box = Image.new("RGBA", (900, 120), (0, 0, 0, 0))
        d = ImageDraw.Draw(box)
        d.rounded_rectangle((0, 0, 899, 119), radius=60, fill=(255, 255, 255, 245))
        d.ellipse((18, 18, 102, 102), fill="#E9D8F2")
        d.ellipse((46, 30, 74, 58), fill="#A88CC0")
        d.pieslice((32, 62, 88, 118), 180, 360, fill="#A88CC0")
        n = int(clamp((lt - tb - 0.6) / 0.35, 0, 2))
        txt = "太陽"[:n]
        f = ctx.comment_font
        if n == 0:
            d.text((128, 34), "コメントを追加…", font=f, fill="#A0A4AC")
        else:
            d.text((128, 32), txt, font=f, fill="#222222")
        tx = 128 + f.getlength(txt)
        if int(lt * 2.5) % 2 == 0 or n < 2:
            d.rectangle((tx + 4, 30, tx + 7, 88), fill="#3B82F6")
        post = "投稿する"
        pf = font(ctx.f_bold, 38)
        d.text((870 - pf.getlength(post), 38), post, font=pf, fill="#3B82F6" if n == 2 else "#A9C4F5")
        paste(frame, box, (540, 1225), a * clamp(pa), 0.9 + 0.1 * pa)
        if n == 2:
            k = lt - tb - 1.3
            sx = 540 - 450 + 128 + f.getlength("太陽") + 70
            L.sun.paths(sun_icon(sx, 1225, 18, 10, rot=k * 30), ease_out(prog(k, 0, 0.6)), 3, a)


def scene_end(ctx, frame, L, t, a):
    t0 = ctx.cs(17)
    lt = t - t0
    cx, cy = 540, 640
    paste(frame, ctx.halo, (cx, cy), a * 0.8)
    rings, pet = mandala(cx, cy, 300, lt * 6)
    L.gold.paths(rings, ease_in_out(prog(lt, 0, 1.6)), 3, a, sequential=False)
    L.gold.paths(pet, ease_in_out(prog(lt, 0.3, 2.0)), 2.5, a, sequential=False)
    paste(frame, ctx.sun_halo, (cx, cy), a * 0.5 * prog(lt, 1, 1), 0.5)
    L.sun.paths(sun_icon(cx, cy, 44, 12, -lt * 10), ease_out(prog(lt, 0.8, 1.2)), 4, a)
    pa = ease_back(prog(lt, 0.6, 0.5))
    pulse = 1 + 0.035 * math.sin(lt * 4) * prog(lt, 1.2, 0.5)
    if pa > 0:
        btn = Image.new("RGBA", (800, 150), (0, 0, 0, 0))
        d = ImageDraw.Draw(btn)
        d.rounded_rectangle((0, 0, 799, 149), radius=75, fill="#06C755")
        f = font(ctx.f_bold, 54)
        s = "公式LINEで無料鑑定"
        d.text(((800 - f.getlength(s)) / 2, 40), s, font=f, fill="white")
        paste(frame, btn, (540, 1130), a * clamp(pa), pa * pulse)
        cap = text_image("プロフィールのリンクから", ctx.f_bold, 44, color=IVORY, stroke="#130E36", stroke_width=4)
        paste(frame, cap, (540, 1010), a * prog(lt, 0.9, 0.4))
    for i in range(3):  # ボタンを指す矢印
        y = 1225 + i * 30
        ph = (lt * 1.4 + i * 0.25) % 1
        L.gold.path([(500, y + 22), (540, y), (580, y + 22)], prog(lt, 1.2, 0.4), 4, a * (0.3 + 0.7 * math.sin(ph * math.pi)))


SCENES = [  # (開始テロップ番号, 描画関数)
    (0, scene_chat), (3, scene_relief), (5, scene_palm), (9, scene_box),
    (12, scene_change), (15, scene_palm_again), (17, scene_end),
]


# ================================================================ frame

def draw_background(ctx: Ctx, frame, L: Layers, t):
    for x, y, r, ph, sp in ctx.stars:
        tw = 0.5 + 0.5 * math.sin(t * sp + ph)
        L.bg.dot(x, y, r * (0.6 + 0.4 * tw), 0.25 + 0.6 * tw)
    rings, pet = mandala(540, 800, 500, t * 2.0, 16)
    k = ease_in_out(prog(t, 0, 3.0))
    L.bg.paths(rings, k, 2, 0.16, sequential=False)
    L.bg.paths(pet, k, 1.6, 0.12, sequential=False)


def render_frame(ctx: Ctx, t: float) -> Image.Image:
    frame = ctx.bg.copy().convert("RGBA")
    L = Layers()
    draw_background(ctx, frame, L, t)
    L.bg.composite(frame)

    starts = [0.0] + [ctx.cs(i) for i, _ in SCENES[1:]]
    idx = max(i for i, s in enumerate(starts) if t >= s)
    p = prog(t, starts[idx], XFADE)
    if idx > 0 and p < 1:
        SCENES[idx - 1][1](ctx, frame, L, t, 1 - p)
    SCENES[idx][1](ctx, frame, L, t, p if idx > 0 else 1.0)
    L.gold.composite(frame)
    L.sun.composite(frame)
    L.white.composite(frame)

    # タイトル (上部固定)
    ta = ease_out(prog(t, 0.2, 0.8))
    paste(frame, ctx.title, (540, 205 - 12 * (1 - ta)), ta)
    tl = LineLayer(GOLD, glow=0.6)
    w2 = ctx.title.width / 2
    tl.path([(540 - w2, 262), (540 + w2, 262)], ease_in_out(prog(t, 0.5, 1.2)), 2)
    tl.path(star5(540 - w2 - 24, 205, 12), prog(t, 1.2, 0.4), 2)
    tl.path(star5(540 + w2 + 24, 205, 12), prog(t, 1.2, 0.4), 2)
    tl.composite(frame)

    # テロップ
    for i, c in enumerate(ctx.cues):
        if c.start <= t < c.end:
            k = ease_out(prog(t, c.start, 0.22))
            paste(frame, ctx.telops[i], (540, TELOP_Y + 18 * (1 - k)), k)
            break
    return frame


# ================================================================ timing

_SRT_TIME = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")


def read_srt_times(path: str) -> list[tuple[float, float]]:
    out = []
    for m in _SRT_TIME.finditer(Path(path).read_text(encoding="utf-8-sig")):
        g = [int(x) for x in m.groups()]
        out.append((g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000, g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000))
    return out


def make_cues(args, y, sr) -> tuple[list[Cue], float]:
    audio_dur = len(y) / sr
    if args.timings:
        spans = read_srt_times(args.timings)
        if len(spans) != len(CUES):
            sys.exit(f"--timings の字幕数 ({len(spans)}) が台本 ({len(CUES)}) と違います。")
    else:
        spans = align_weights([weight(n) for _, n in CUES], y, sr)
    cues = [Cue(s, e, plain(t)) for (t, _), (s, e) in zip(CUES, spans)]
    for a, b in zip(cues, cues[1:]):  # 間の無音でもテロップを切らさない
        a.end = b.start
    duration = audio_dur + args.tail
    cues[0].start = 0.0
    cues[-1].end = duration
    return cues, duration


# ================================================================ main

def parse_points(s: str) -> list[tuple[float, float]]:
    pts = []
    for tok in re.split(r"[\s;]+", s.strip()):
        if tok:
            x, y = tok.split(",")
            pts.append((float(x), float(y)))
    if len(pts) < 2:
        raise argparse.ArgumentTypeError("2点以上を 'x,y x,y ...' の形で指定してください")
    return pts


def palm_grid(ctx: Ctx, out: Path) -> None:
    img = ctx.palm.copy()
    d = ImageDraw.Draw(img)
    f = font(ctx.f_reg, 22)
    for i in range(1, 10):
        x, y = img.width * i / 10, img.height * i / 10
        d.line([(x, 0), (x, img.height)], fill=(0, 200, 255, 160), width=1)
        d.line([(0, y), (img.width, y)], fill=(0, 200, 255, 160), width=1)
        d.text((x + 3, 3), f"{i / 10:.1f}", font=f, fill=(0, 120, 255))
        d.text((3, y + 3), f"{i / 10:.1f}", font=f, fill=(0, 120, 255))
    x0, y0 = ctx.palm_rect[:2]
    d.line([(x - x0, y - y0) for x, y in ctx.sunline], fill=(255, 120, 0, 255), width=6)
    img.save(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audio", help="ナレーション音声 (wav)")
    ap.add_argument("palm", help="手のひら画像 (png/jpg)")
    ap.add_argument("-o", "--output", help="出力 mp4 (既定: 音声と同じ場所・同じ名前)")
    ap.add_argument("--sunline", type=parse_points, default=parse_points("0.62,0.68 0.615,0.56 0.605,0.43"),
                    help="太陽線の点 (画像内の割合 x,y を空白区切り。例 '0.62,0.68 0.61,0.43')")
    ap.add_argument("--timings", help="テロップの時間を書いた .srt (自動で出したものを手直しして渡す)")
    ap.add_argument("--tail", type=float, default=1.5, help="ナレーション後に残す秒数")
    ap.add_argument("--font", help="テロップ用フォントファイル")
    ap.add_argument("--title-font", help="タイトル用フォントファイル")
    ap.add_argument("--preview", action="store_true", help="動画を作らず確認用の静止画だけ出す")
    ap.add_argument("--crf", type=int, default=18, help="画質 (小さいほど高画質)")
    args = ap.parse_args()

    y, sr = read_wav(args.audio)
    cues, duration = make_cues(args, y, sr)
    ctx = Ctx(args, cues, duration)
    out = Path(args.output) if args.output else Path(args.audio).with_suffix(".mp4")
    srt = out.with_suffix(".srt")
    srt.write_text(to_srt(cues), encoding="utf-8")
    print(f"テロップの時間: {srt}")
    for i, c in enumerate(cues):
        print(f"  {i + 1:2d}  {c.start:6.2f} - {c.end:6.2f}  {c.text.replace(chr(10), ' / ')}")

    if args.preview:
        pdir = out.with_name(out.stem + "_preview")
        pdir.mkdir(exist_ok=True)
        palm_grid(ctx, pdir / "palm_grid.png")
        for i, c in enumerate(cues):
            render_frame(ctx, min(c.end - 0.05, c.start + 1.6)).convert("RGB").save(pdir / f"{i + 1:02d}.jpg", quality=88)
        print(f"確認用画像: {pdir}")
        return

    n = int(math.ceil(duration * FPS))
    wr = VideoWriter(str(out), args.audio, duration, args.crf)
    t0 = time.time()
    for k in range(n):
        wr.write(render_frame(ctx, k / FPS))
        if k % FPS == 0 or k == n - 1:
            el = time.time() - t0
            eta = el / (k + 1) * (n - k - 1)
            print(f"\r  {k + 1}/{n} フレーム  残り約 {eta:4.0f} 秒 ", end="", flush=True)
    wr.close()
    print(f"\n完成: {out}")


if __name__ == "__main__":
    main()
