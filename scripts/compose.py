#!/usr/bin/env python3
"""Compose the "From Heat to Comfort" ad.

Reads config/edl.json and config/brand.json, cuts the generated clips, applies a
unified grade, renders the phone UI inserts, Arabic supers and the end card, and
writes a silent H.264 picture track plus the matching clip-foley stem.

Usage: compose.py WORKDIR [--preview]
WORKDIR must contain clips/cNN.mp4, fonts/, config/ (edl.json, brand.json).
"""
import json
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

WORK = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
PREVIEW = "--preview" in sys.argv
EDL = json.load(open(os.path.join(WORK, "config/edl.json"), encoding="utf-8"))
BRAND = json.load(open(os.path.join(WORK, "config/brand.json"), encoding="utf-8"))
W, H, FPS = EDL["width"], EDL["height"], EDL["fps"]
NFRAMES = int(round(EDL["duration"] * FPS))
SRC_FPS = 24
AUDIO_SR = 48000
C = BRAND["colors"]


def hexrgb(h, a=255):
    h = h.lstrip("#")
    return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a)


# ---------------------------------------------------------------- typography
_fonts = {}


def font(weight, size):
    key = (weight, size)
    if key not in _fonts:
        path = os.path.join(WORK, BRAND["fonts"][weight])
        _fonts[key] = ImageFont.truetype(path, size, layout_engine=ImageFont.Layout.RAQM)
    return _fonts[key]


def text(draw, xy, s, weight, size, fill, anchor="mm"):
    """Draw shaped right-to-left Arabic text."""
    draw.text(xy, s, font=font(weight, size), fill=fill, anchor=anchor,
              direction="rtl", language="ar")


def text_w(s, weight, size):
    l, t, r, b = font(weight, size).getbbox(s, direction="rtl", language="ar")
    return r - l


def placeholder(value, label):
    return value if value else f"[{label}]"


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3


def ease_in_out(x):
    x = min(max(x, 0.0), 1.0)
    return 3 * x * x - 2 * x * x * x


def prog(t, a, b):
    return min(max((t - a) / (b - a), 0.0), 1.0)


# ---------------------------------------------------------------- source video
def decode(src, t_in, seconds):
    """Decode a clip span to uint8 frames (cover-scaled to W x H) at the source rate."""
    path = os.path.join(WORK, "clips", src + ".mp4")
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t_in:.3f}", "-i", path, "-t", f"{seconds + 0.2:.3f}",
           "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase:flags=lanczos,crop={W}:{H}",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    frames = np.frombuffer(raw, np.uint8).reshape(-1, H, W, 3)
    return frames


def still(src, t):
    return Image.fromarray(decode(src, t, 0.05)[0])


def decode_audio(src, t_in, seconds):
    path = os.path.join(WORK, "clips", src + ".mp4")
    cmd = ["ffmpeg", "-v", "error", "-ss", f"{t_in:.3f}", "-i", path, "-t", f"{seconds + 0.1:.3f}",
           "-ac", "2", "-ar", str(AUDIO_SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, check=True, capture_output=True).stdout
    return np.frombuffer(raw, np.float32).reshape(-1, 2).copy()


# ---------------------------------------------------------------- grade
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
_r = np.sqrt(((_xx - W / 2) / (W / 2)) ** 2 + ((_yy - H / 2) / (H / 2)) ** 2)
VIGNETTE = (1.0 - 0.16 * np.clip(_r - 0.55, 0, None) ** 1.6)[..., None].astype(np.float32)
del _yy, _xx, _r
_rng = np.random.default_rng(7)
GRAIN = [(_rng.normal(0, 1, (H // 2, W // 2)).astype(np.float32)) for _ in range(6)]


def grade(img, temp, n):
    a = img.astype(np.float32) / 255.0
    # gentle filmic S-curve
    a = a + 0.06 * (a - 0.5) * (1 - np.abs(2 * a - 1))
    a[..., 0] *= 1 + temp
    a[..., 1] *= 1 + temp * 0.25
    a[..., 2] *= 1 - temp
    a *= VIGNETTE
    g = np.repeat(np.repeat(GRAIN[n % len(GRAIN)], 2, 0), 2, 1)[..., None]
    a += g * 0.010
    return (np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)


def push(img, z):
    """Centre digital push-in by factor z (>= 1)."""
    if z <= 1.0005:
        return img
    cw, ch = W / z, H / z
    x0, y0 = (W - cw) / 2, (H - ch) / 2
    return img.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + cw, y0 + ch))


# ---------------------------------------------------------------- phone UI
PW, PH = 760, 1560            # phone body
SW, SH = PW - 44, PH - 44     # screen
P_RAD, S_RAD = 104, 84


def rounded_mask(size, rad):
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rounded_rectangle((0, 0, size[0] - 1, size[1] - 1), rad, fill=255)
    return m


SCREEN_MASK = rounded_mask((SW, SH), S_RAD)


def phone(screen):
    """Wrap a screen image in a phone body with a soft drop shadow (RGBA)."""
    pad = 80
    out = Image.new("RGBA", (PW + 2 * pad, PH + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("L", out.size, 0)
    ImageDraw.Draw(sh).rounded_rectangle((pad, pad + 26, pad + PW, pad + PH + 26), P_RAD, fill=150)
    out.putalpha(sh.filter(ImageFilter.GaussianBlur(34)))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((pad, pad, pad + PW, pad + PH), P_RAD, fill=(18, 20, 24, 255))
    d.rounded_rectangle((pad + 6, pad + 6, pad + PW - 6, pad + PH - 6), P_RAD - 6,
                        outline=(70, 74, 82, 255), width=3)
    out.paste(screen.convert("RGB"), (pad + 22, pad + 22), SCREEN_MASK)
    d.rounded_rectangle((pad + PW / 2 - 92, pad + 44, pad + PW / 2 + 92, pad + 96), 26, fill=(8, 8, 10, 255))
    return out


def status_bar(d, dark=False):
    col = (255, 255, 255, 255) if not dark else hexrgb(C["ink"])
    d.text((SW - 70, 62), "4:15", font=font("bold", 34), fill=col, anchor="rm")
    x = 70
    d.rounded_rectangle((x, 48, x + 54, 76), 8, outline=col, width=3)
    d.rectangle((x + 6, 54, x + 42, 70), fill=col)
    d.rectangle((x + 56, 56, x + 60, 68), fill=col)


def app_header(d, title_sub):
    for i in range(330):
        k = i / 330
        c1, c2 = hexrgb(C["primary"]), hexrgb(C["primary_dark"])
        d.line((0, i, SW, i), fill=tuple(int(c1[j] * (1 - k) + c2[j] * k) for j in range(3)))
    status_bar(d)
    # logo placeholder
    cx, cy = SW - 110, 205
    d.ellipse((cx - 56, cy - 56, cx + 56, cy + 56), fill=(255, 255, 255, 255))
    text(d, (cx, cy + 2), "شعار", "bold", 28, hexrgb(C["primary"]))
    text(d, (cx - 84, cy - 22), placeholder(BRAND["company_name"], "اسم الشركة"), "black", 42,
         (255, 255, 255, 255), anchor="rm")
    text(d, (cx - 84, cy + 30), title_sub, "medium", 30, (220, 240, 242, 255), anchor="rm")


def snowflake(d, cx, cy, r, col, w=5):
    for k in range(3):
        a = math.pi / 3 * k + math.pi / 2
        dx, dy = math.cos(a) * r, math.sin(a) * r
        d.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=col, width=w)
        for s in (-1, 1):
            bx, by = cx + s * dx * 0.62, cy + s * dy * 0.62
            for b in (-0.6, 0.6):
                ang = a + (0 if s > 0 else math.pi)
                tx = bx + math.cos(ang + b) * r * 0.32
                ty = by + math.sin(ang + b) * r * 0.32
                d.line((bx, by, tx, ty), fill=col, width=w - 1)


def check(d, cx, cy, r, col, w):
    d.line((cx - r * 0.45, cy + r * 0.02, cx - r * 0.12, cy + r * 0.34), fill=col, width=w)
    d.line((cx - r * 0.12, cy + r * 0.34, cx + r * 0.5, cy - r * 0.32), fill=col, width=w)


def card(d, box, selected):
    x0, y0, x1, y1 = box
    if selected:
        d.rounded_rectangle(box, 30, fill=(230, 244, 245, 255), outline=hexrgb(C["primary"]), width=5)
    else:
        d.rounded_rectangle(box, 30, fill=(255, 255, 255, 255), outline=(222, 228, 232, 255), width=3)


def demo_label(d, y):
    text(d, (SW / 2, y), "عرض توضيحي • بيانات تجريبية", "medium", 24, (150, 158, 168, 255))


def booking_screen(t):
    img = Image.new("RGBA", (SW, SH), hexrgb(C["surface"]))
    d = ImageDraw.Draw(img)
    app_header(d, "صيانة وتنظيف المكيفات")
    text(d, (SW - 48, 400), "اختر الخدمة", "black", 44, hexrgb(C["ink"]), anchor="rm")
    items = [("تنظيف مكيف سبليت", "تنظيف الفلاتر والوحدة الداخلية", True),
             ("فحص وصيانة", "تشخيص المشكلة وفحص الأداء", False),
             ("إصلاح عطل", "بعد الفحص والتشخيص", False)]
    for i, (a, b, sel) in enumerate(items):
        y0 = 460 + i * 178
        card(d, (36, y0, SW - 36, y0 + 156), sel)
        icx, icy = SW - 112, y0 + 78
        d.ellipse((icx - 46, icy - 46, icx + 46, icy + 46),
                  fill=hexrgb(C["primary"]) if sel else (232, 238, 241, 255))
        snowflake(d, icx, icy, 26, (255, 255, 255, 255) if sel else hexrgb(C["primary"]), 5)
        text(d, (icx - 74, y0 + 56), a, "bold", 38, hexrgb(C["ink"]), anchor="rm")
        text(d, (icx - 74, y0 + 106), b, "medium", 27, hexrgb(C["muted"]), anchor="rm")
        if sel:
            d.ellipse((76, y0 + 52, 128, y0 + 104), fill=hexrgb(C["primary"]))
            check(d, 102, y0 + 78, 24, (255, 255, 255, 255), 6)
        else:
            d.ellipse((76, y0 + 52, 128, y0 + 104), outline=(200, 208, 214, 255), width=4)
    y0 = 1010
    d.rounded_rectangle((36, y0, SW - 36, y0 + 120), 30, fill=(255, 255, 255, 255), outline=(222, 228, 232, 255), width=3)
    text(d, (SW - 76, y0 + 60), "الموعد", "bold", 34, hexrgb(C["ink"]), anchor="rm")
    text(d, (76, y0 + 60), "اليوم • أقرب موعد متاح", "medium", 30, hexrgb(C["primary"]), anchor="lm")
    # call-to-action button with press + ripple
    bx0, by0, bx1, by1 = 36, 1190, SW - 36, 1318
    pressed = 0.40 <= t < 0.58
    d.rounded_rectangle((bx0, by0, bx1, by1), 64,
                        fill=hexrgb(C["primary_dark"] if pressed else C["primary"]))
    text(d, ((bx0 + bx1) / 2, (by0 + by1) / 2 + 2), "اطلب الفني الآن", "black", 46, (255, 255, 255, 255))
    demo_label(d, SH - 60)
    if 0.40 <= t < 0.75:
        k = prog(t, 0.40, 0.75)
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        cx, cy, r = SW / 2 + 90, (by0 + by1) / 2, 30 + 220 * ease_out(k)
        od.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, int(110 * (1 - k))))
        if t < 0.55:
            od.ellipse((cx - 34, cy - 34, cx + 34, cy + 34), fill=(255, 255, 255, 120))
        img = Image.alpha_composite(img, ov)
    if t >= 0.60:
        k = ease_out(prog(t, 0.60, 0.82))
        img = Image.alpha_composite(img, Image.new("RGBA", img.size, (10, 20, 25, int(120 * k))))
        sheet_h = 760
        top = SH - sheet_h * k
        sh = Image.new("RGBA", img.size, (0, 0, 0, 0))
        sd = ImageDraw.Draw(sh)
        sd.rounded_rectangle((0, top, SW, SH + 80), 64, fill=(255, 255, 255, 255))
        sd.rounded_rectangle((SW / 2 - 50, top + 22, SW / 2 + 50, top + 32), 5, fill=(214, 220, 224, 255))
        ck = ease_out(prog(t, 0.70, 0.90))
        cr = 92 * (0.6 + 0.4 * ck)
        cy = top + 190
        sd.ellipse((SW / 2 - cr, cy - cr, SW / 2 + cr, cy + cr), fill=hexrgb(C["success"], int(255 * max(ck, 0.15))))
        if ck > 0.3:
            check(sd, SW / 2, cy, cr * 0.9, (255, 255, 255, 255), 14)
        text(sd, (SW / 2, top + 360), "تم تأكيد طلبك", "black", 56, hexrgb(C["ink"]))
        text(sd, (SW / 2, top + 440), "الفني في الطريق إليك", "medium", 38, hexrgb(C["muted"]))
        demo_label(sd, SH - 60)
        img = Image.alpha_composite(img, sh)
    return img


def payment_screen(t):
    img = Image.new("RGBA", (SW, SH), hexrgb(C["surface"]))
    d = ImageDraw.Draw(img)
    app_header(d, "الدفع الإلكتروني")
    text(d, (SW - 48, 400), "ملخص الطلب", "black", 44, hexrgb(C["ink"]), anchor="rm")
    d.rounded_rectangle((36, 460, SW - 36, 800), 30, fill=(255, 255, 255, 255), outline=(222, 228, 232, 255), width=3)
    rows = [("الخدمة", "تنظيف مكيف سبليت"), ("الحالة", "تم الإنجاز"), ("المبلغ", "--- ر.ق")]
    for i, (k_, v) in enumerate(rows):
        y = 530 + i * 105
        text(d, (SW - 76, y), k_, "medium", 32, hexrgb(C["muted"]), anchor="rm")
        text(d, (76, y), v, "bold", 34, hexrgb(C["ink"]), anchor="lm")
        if i < 2:
            d.line((76, y + 52, SW - 76, y + 52), fill=(232, 236, 239, 255), width=2)
    y0 = 850
    d.rounded_rectangle((36, y0, SW - 36, y0 + 140), 30, fill=(230, 244, 245, 255), outline=hexrgb(C["primary"]), width=5)
    cx = SW - 120
    d.rounded_rectangle((cx - 48, y0 + 38, cx + 48, y0 + 102), 12, fill=hexrgb(C["primary"]))
    d.rectangle((cx - 48, y0 + 54, cx + 48, y0 + 66), fill=hexrgb(C["primary_dark"]))
    text(d, (cx - 80, y0 + 70), "بطاقة بنكية", "bold", 36, hexrgb(C["ink"]), anchor="rm")
    text(d, (76, y0 + 70), "•••• ••••", "bold", 30, hexrgb(C["muted"]), anchor="lm")
    bx0, by0, bx1, by1 = 36, 1190, SW - 36, 1318
    pressed = 0.30 <= t < 0.46
    d.rounded_rectangle((bx0, by0, bx1, by1), 64, fill=hexrgb(C["primary_dark"] if pressed else C["primary"]))
    text(d, ((bx0 + bx1) / 2, (by0 + by1) / 2 + 2), "ادفع الآن", "black", 48, (255, 255, 255, 255))
    demo_label(d, SH - 60)
    if 0.30 <= t < 0.60:
        k = prog(t, 0.30, 0.60)
        ov = Image.new("RGBA", img.size, (0, 0, 0, 0))
        od = ImageDraw.Draw(ov)
        cx, cy, r = SW / 2 - 60, (by0 + by1) / 2, 30 + 220 * ease_out(k)
        od.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(255, 255, 255, int(110 * (1 - k))))
        img = Image.alpha_composite(img, ov)
    if t >= 0.48:
        k = ease_out(prog(t, 0.48, 0.66))
        sh = Image.new("RGBA", img.size, (255, 255, 255, int(255 * k)))
        sd = ImageDraw.Draw(sh)
        ck = ease_out(prog(t, 0.52, 0.72))
        cr = 150 * (0.55 + 0.45 * ck)
        cy = SH * 0.36
        sd.ellipse((SW / 2 - cr, cy - cr, SW / 2 + cr, cy + cr), fill=hexrgb(C["success"], int(255 * k)))
        if ck > 0.3:
            check(sd, SW / 2, cy, cr * 0.9, (255, 255, 255, 255), 20)
        a = int(255 * k)
        text(sd, (SW / 2, cy + 280), "تم الدفع بنجاح", "black", 84, hexrgb(C["ink"], a))
        text(sd, (SW / 2, cy + 390), "شكراً لاختيارك خدمتنا", "medium", 46, hexrgb(C["muted"], a))
        demo_label(sd, SH - 60)
        img = Image.alpha_composite(img, sh)
    return img


# ---------------------------------------------------------------- supers
def pill_super(canvas, s, t, t0, t1, y=1420):
    a_in, a_out = prog(t, t0, t0 + 0.22), 1 - prog(t, t1 - 0.14, t1)
    a = min(a_in, a_out)
    if a <= 0:
        return
    size = 64
    tw = text_w(s, "black", size)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    dy = 26 * (1 - ease_out(a_in))
    x0, x1 = W / 2 - tw / 2 - 54, W / 2 + tw / 2 + 54
    d.rounded_rectangle((x0, y - 62 + dy, x1, y + 62 + dy), 62, fill=(12, 22, 28, int(150 * a)))
    d.rounded_rectangle((x1 - 14, y - 30 + dy, x1 - 6, y + 30 + dy), 4, fill=hexrgb(C["accent"], int(255 * a)))
    text(d, (W / 2, y + 4 + dy), s, "black", size, (255, 255, 255, int(255 * a)))
    canvas.alpha_composite(lay)


def chips_super(canvas, sup, t, y=1420):
    t0, t1 = sup["start"], sup["end"]
    a_in, a_out = prog(t, t0, t0 + 0.22), 1 - prog(t, t1 - 0.14, t1)
    a = min(a_in, a_out)
    if a <= 0:
        return
    active = next((i for s0, s1, i in sup["active"] if s0 <= t < s1), None)
    size, padx, gap = 56, 46, 26
    widths = [text_w(c, "black", size) + 2 * padx for c in sup["chips"]]
    total = sum(widths) + gap * (len(widths) - 1)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    dy = 26 * (1 - ease_out(a_in))
    x = W / 2 + total / 2   # right-to-left order
    for i, (c, w) in enumerate(zip(sup["chips"], widths)):
        on = i == active
        fill = hexrgb(C["primary"], int(235 * a)) if on else (12, 22, 28, int(140 * a))
        d.rounded_rectangle((x - w, y - 54 + dy, x, y + 54 + dy), 54, fill=fill)
        if on:
            d.rounded_rectangle((x - w, y - 54 + dy, x, y + 54 + dy), 54,
                                outline=(255, 255, 255, int(200 * a)), width=3)
        text(d, (x - w / 2, y + 4 + dy), c, "black", size,
             (255, 255, 255, int(255 * a * (1 if on else 0.72))))
        x -= w + gap
    canvas.alpha_composite(lay)


# ---------------------------------------------------------------- graphics segments
_cache = {}


def blurred_bg(seg):
    key = ("bg", seg["id"])
    if key not in _cache:
        im = still(seg["bg"], seg["bg_t"]).filter(ImageFilter.GaussianBlur(26))
        _cache[key] = im
    return _cache[key]


def booking_frame(seg, t):
    bg = blurred_bg(seg).copy().convert("RGBA")
    bg = Image.alpha_composite(bg, Image.new("RGBA", (W, H), (8, 16, 20, 120)))
    k = ease_out(prog(t, 0.0, 0.30))
    ph = phone(booking_screen(t))
    s = 0.90 + 0.08 * k + 0.012 * t
    ph = ph.resize((int(ph.width * s), int(ph.height * s)), Image.LANCZOS)
    x = (W - ph.width) // 2
    y = int((H - ph.height) / 2 + 200 * (1 - k)) - 10
    bg.alpha_composite(ph, (x, y))
    if t < 0.08:  # flash cut from live action
        bg = Image.blend(bg, Image.new("RGBA", (W, H), (255, 255, 255, 255)), 0.55 * (1 - t / 0.08))
    return bg.convert("RGB")


def payment_overlay(canvas, t):
    """Small phone with the payment flow, top-left where the frame is empty."""
    k = ease_out(prog(t, 0.0, 0.25))
    out_k = ease_in_out(prog(t, 1.36, 1.5))
    ph = phone(payment_screen(max(t - 0.25, 0) / 0.95))
    s = 0.56
    ph = ph.resize((int(ph.width * s), int(ph.height * s)), Image.LANCZOS)
    x = int(20 - (ph.width + 60) * (1 - k) - (ph.width + 60) * out_k)
    y = 170
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    lay.alpha_composite(ph, (max(x, -ph.width), y))
    d = ImageDraw.Draw(lay)
    a = int(255 * k * (1 - out_k))
    s_txt = "ادفع بسهولة من جوالك"
    tw = text_w(s_txt, "black", 58)
    d.rounded_rectangle((W / 2 - tw / 2 - 50, 1420 - 58, W / 2 + tw / 2 + 50, 1420 + 58), 58, fill=(12, 22, 28, int(150 * k * (1 - out_k))))
    d.rounded_rectangle((W / 2 + tw / 2 + 36, 1420 - 28, W / 2 + tw / 2 + 44, 1420 + 28), 4, fill=hexrgb(C["accent"], a))
    text(d, (W / 2, 1424), s_txt, "black", 58, (255, 255, 255, a))
    canvas.alpha_composite(lay)


def endcard_frame(seg, t, prev_rgb):
    key = ("end_bg", seg["id"])
    if key not in _cache:
        bg = blurred_bg(seg).convert("RGBA")
        grad = Image.new("RGBA", (W, H))
        gd = ImageDraw.Draw(grad)
        c1, c2 = hexrgb(C["primary_dark"]), hexrgb(C["primary"])
        for yy in range(H):
            k = yy / H
            gd.line((0, yy, W, yy), fill=(int(c1[0] * (1 - k) + c2[0] * k), int(c1[1] * (1 - k) + c2[1] * k),
                                          int(c1[2] * (1 - k) + c2[2] * k), int(205 + 30 * k)))
        _cache[key] = Image.alpha_composite(bg, grad)
    img = _cache[key].copy()
    d = ImageDraw.Draw(img)
    white = lambda a: (255, 255, 255, int(255 * a))
    # logo placeholder (or the real logo if supplied)
    a = ease_out(prog(t, 0.10, 0.40))
    cy = 640 - 30 * (1 - a)
    logo = BRAND.get("logo_path")
    if logo and os.path.exists(os.path.join(WORK, logo)):
        lg = Image.open(os.path.join(WORK, logo)).convert("RGBA")
        lg.thumbnail((340, 340))
        lg.putalpha(lg.getchannel("A").point(lambda v: int(v * a)))
        img.alpha_composite(lg, (int(W / 2 - lg.width / 2), int(cy - lg.height / 2)))
    else:
        s = 150
        d.rounded_rectangle((W / 2 - s, cy - s, W / 2 + s, cy + s), 56, outline=white(0.85 * a), width=5)
        snowflake(d, W / 2, cy - 34, 48, white(a), 8)
        text(d, (W / 2, cy + 62), "شعار الشركة", "bold", 40, white(0.9 * a))
    a = ease_out(prog(t, 0.22, 0.52))
    y = 930 + 40 * (1 - a)
    text(d, (W / 2, y), BRAND["tagline"], "black", 132, white(a))
    d.rounded_rectangle((W / 2 - 70, y + 92, W / 2 + 70, y + 102), 5, fill=hexrgb(C["accent"], int(255 * a)))
    a = ease_out(prog(t, 0.34, 0.62))
    text(d, (W / 2, 1120 + 30 * (1 - a)), BRAND["subline"], "medium", 54, white(0.92 * a))
    a = ease_out(prog(t, 0.46, 0.74))
    pulse = 1 + 0.025 * math.sin(max(t - 0.9, 0) * 2 * math.pi * 1.6) * (t > 0.9)
    cta = BRAND["cta"]
    bw = (text_w(cta, "black", 56) + 130) * pulse
    bh = 128 * pulse
    by = 1300 + 30 * (1 - a)
    d.rounded_rectangle((W / 2 - bw / 2, by - bh / 2, W / 2 + bw / 2, by + bh / 2), bh / 2, fill=white(a))
    text(d, (W / 2, by + 4), cta, "black", int(56 * pulse), hexrgb(C["primary_dark"], int(255 * a)))
    a = ease_out(prog(t, 0.58, 0.86))
    contact = f"{placeholder(BRAND['phone'], 'رقم التواصل')}   •   {placeholder(BRAND['website'], 'الموقع الإلكتروني')}"
    text(d, (W / 2, 1450 + 20 * (1 - a)), contact, "bold", 40, white(0.88 * a))
    rgb = img.convert("RGB")
    xf = seg.get("xfade", 0)
    if prev_rgb is not None and t < xf:
        rgb = Image.blend(prev_rgb, rgb, ease_in_out(t / xf))
    return rgb


# ---------------------------------------------------------------- render
def main():
    os.makedirs(os.path.join(WORK, "build"), exist_ok=True)
    out_video = os.path.join(WORK, "build", "picture.mp4")
    enc = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast" if PREVIEW else "slow",
           "-crf", "24" if PREVIEW else "15", "-pix_fmt", "yuv420p", "-profile:v", "high",
           "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
           "-movflags", "+faststart", out_video]
    proc = subprocess.Popen(enc, stdin=subprocess.PIPE)
    foley = np.zeros((int(EDL["duration"] * AUDIO_SR) + AUDIO_SR, 2), np.float32)
    segs = EDL["segments"]
    prev_rgb = None
    n = 0
    for si, seg in enumerate(segs):
        f0 = int(round(seg["start"] * FPS))
        f1 = int(round((seg["start"] + seg["dur"]) * FPS))
        speed = seg.get("speed", 1.0)
        frames = None
        if seg["type"] == "clip":
            frames = decode(seg["src"], seg["in"], seg["dur"] * speed)
            au = decode_audio(seg["src"], seg["in"], seg["dur"] * speed)
            if speed != 1.0:
                idx = np.arange(0, len(au) - 1, speed)
                au = np.stack([np.interp(idx, np.arange(len(au)), au[:, c]) for c in (0, 1)], 1)
            au = au[: int(seg["dur"] * AUDIO_SR)] * seg.get("foley_gain", 1.0)
            fade = min(len(au), int(0.012 * AUDIO_SR))
            env = np.ones(len(au), np.float32)
            env[:fade] = np.linspace(0, 1, fade)
            env[-fade:] = np.linspace(1, 0, fade)
            a0 = int(seg["start"] * AUDIO_SR)
            foley[a0:a0 + len(au)] += au * env[:, None]
        for f in range(f0, f1):
            t = f / FPS - seg["start"]
            if seg["type"] == "clip":
                si_ = min(int(round(t * speed * SRC_FPS)), len(frames) - 1)
                z0, z1 = seg.get("zoom", [1, 1])
                img = push(Image.fromarray(frames[si_]), z0 + (z1 - z0) * (t / seg["dur"]))
            elif seg["gfx"] == "booking":
                img = booking_frame(seg, t)
            else:
                img = endcard_frame(seg, t, prev_rgb)
            arr = grade(np.asarray(img), seg.get("temp", 0.0), f) if seg["type"] == "clip" else np.asarray(img)
            canvas = Image.fromarray(arr).convert("RGBA")
            tt = f / FPS
            for sup in EDL["supers"]:
                if sup["start"] <= tt < sup["end"]:
                    if "chips" in sup:
                        chips_super(canvas, sup, tt)
                    else:
                        pill_super(canvas, sup["text"], tt, sup["start"], sup["end"])
            if seg.get("overlay") == "payment":
                payment_overlay(canvas, t)
            rgb = canvas.convert("RGB")
            if seg["type"] == "clip":
                prev_rgb = rgb
            proc.stdin.write(rgb.tobytes())
            n += 1
            if PREVIEW and f in (int(seg["start"] * FPS) + int(seg["dur"] * FPS * 0.6),):
                rgb.resize((360, 640)).save(os.path.join(WORK, "build", f"pv_{seg['id']}.jpg"), quality=82)
            if f % 25 == 0:
                print(f"frame {f}/{NFRAMES}", flush=True)
        frames = None
    proc.stdin.close()
    proc.wait()
    assert n == NFRAMES, (n, NFRAMES)
    foley = foley[: int(EDL["duration"] * AUDIO_SR)]
    foley.astype("<f4").tofile(os.path.join(WORK, "build", "foley.f32"))
    print("done", out_video, n, "frames")


if __name__ == "__main__":
    main()
