#!/usr/bin/env python3
"""Al Faytri 10th-anniversary count-up (1 -> 10) on a chroma-key green background.

Fast white count 1..9 with a gold progress ring, then a luxurious gold "10"
(metallic gradient, hard 3D shadow, shine sweep, double ring, star twinkles).
Only solid, hard-edged elements are drawn over the green: no glows or opacity
fades, so CapCut's chroma key removes the background cleanly.

Every frame is a pure function of time; randomness is seeded.

Usage: countup.py FONT_DIR OUT_DIR [--alpha]
Writes OUT_DIR/alfaytri_10_countup_green.mp4, ..._green_sanawat.mp4,
       OUT_DIR/countup_sound.wav and OUT_DIR/contact_sheet.jpg; with --alpha also transparent
       ProRes 4444 .mov, VP9 .webm and PNG-sequence .zip versions (no background).
"""
import math
import os
import subprocess
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT_DIR, OUT = sys.argv[1], sys.argv[2]
W, H, FPS, DUR = 1080, 1920, 30, 5.0
NF = int(DUR * FPS)
GREEN = (0, 255, 0)
CX, CY = W // 2, 900
RING = 450                                   # gold ring radius (px)

# ---------------------------------------------------------------- timing
D = np.linspace(0.30, 0.16, 9)              # 1..9 speed up as they climb
STARTS = 0.10 + np.concatenate([[0], np.cumsum(D)[:-1]])
T10 = 0.10 + D.sum() + 0.03                  # the hit


def font(weight, size):
    return ImageFont.truetype(os.path.join(FONT_DIR, f"Changa-{weight}.ttf"), size,
                              layout_engine=ImageFont.Layout.RAQM)


def ease_out(x, p=3):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** p


def ease_out_back(x, s=1.9):
    x = min(max(x, 0.0), 1.0) - 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


# ---------------------------------------------------------------- sprites
def text_mask(s, f, pad=60, stroke=0):
    l, t, r, b = f.getbbox(s, stroke_width=stroke)
    m = Image.new("L", (r - l + 2 * pad, b - t + 2 * pad), 0)
    ImageDraw.Draw(m).text((pad - l, pad - t), s, font=f, fill=255, stroke_width=stroke, stroke_fill=255)
    return m


def layered_sprite(s, f, fill_img_fn, stroke, stroke_rgb, shadow_off, shadow_rgb):
    """Solid text sprite: hard shadow + stroke + fill, all fully opaque."""
    outer = text_mask(s, f, stroke=stroke)
    inner = text_mask(s, f, stroke=0)
    ox, oy = shadow_off
    sw, sh = outer.width + ox, outer.height + oy
    spr = Image.new("RGBA", (sw, sh), (0, 0, 0, 0))
    spr.paste(Image.new("RGBA", outer.size, shadow_rgb + (255,)), (ox, oy), outer)
    spr.paste(Image.new("RGBA", outer.size, stroke_rgb + (255,)), (0, 0), outer)
    spr.paste(fill_img_fn(inner.size), (0, 0), inner)
    return spr, inner


def gold_gradient(size):
    w, h = size
    stops = [(0.00, (255, 243, 176)), (0.26, (232, 197, 90)), (0.48, (184, 134, 43)),
             (0.60, (242, 210, 122)), (0.82, (201, 153, 47)), (1.00, (140, 100, 24))]
    y = np.linspace(0, 1, h)
    cols = np.zeros((h, 3))
    for c in range(3):
        cols[:, c] = np.interp(y, [s[0] for s in stops], [s[1][c] for s in stops])
    arr = np.repeat(cols[:, None, :], w, 1).astype(np.uint8)
    return Image.fromarray(arr, "RGB").convert("RGBA")


def solid(rgb):
    return lambda size: Image.new("RGBA", size, rgb + (255,))


NUM_FONT = font("ExtraBold", 560)
TEN_FONT = font("ExtraBold", 500)
WORD_FONT = font("Bold", 150)
WHITE_NUMS = [layered_sprite(str(n), NUM_FONT, solid((255, 255, 255)), 12, (214, 175, 55), (10, 14), (26, 22, 14))[0]
              for n in range(1, 10)]
TEN, TEN_INNER = layered_sprite("10", TEN_FONT, gold_gradient, 16, (110, 78, 14), (14, 20), (43, 29, 5))
WORD, WORD_INNER = layered_sprite("سنوات", WORD_FONT, gold_gradient, 8, (110, 78, 14), (6, 9), (43, 29, 5))


def with_shine(spr, inner, pos, width=170, angle=24):
    """Bright diagonal band clipped to the text fill; pos in 0..1 across the sprite."""
    w, h = inner.size
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = xx + yy * math.tan(math.radians(angle))
    centre = -width + pos * (w + h * math.tan(math.radians(angle)) + 2 * width)
    band = np.clip(1 - np.abs(d - centre) / width, 0, 1) ** 1.5
    band *= np.asarray(inner, np.float32) / 255
    out = spr.copy()
    a = np.asarray(out).astype(np.float32)
    k = (band * 0.85)[..., None]
    a[:h, :w, :3] = a[:h, :w, :3] * (1 - k) + np.array([255, 253, 240]) * k
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def paste_center(canvas, spr, cx, cy, scale):
    if scale <= 0.01:
        return
    s = spr if abs(scale - 1) < 1e-3 else spr.resize((max(1, int(spr.width * scale)), max(1, int(spr.height * scale))),
                                                      Image.LANCZOS)
    canvas.alpha_composite(s, (int(cx - s.width / 2), int(cy - s.height / 2)))


# ---------------------------------------------------------------- vector bits (drawn 2x, downsampled)
SS = 2


def ring_layer(t, sanawat):
    lay = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    cx, cy = CX * SS, CY * SS
    gold, dark = (214, 175, 55, 255), (110, 78, 14, 255)
    if t < T10:
        # progress ring: fills n/10 of the way as the count climbs
        n = int(np.searchsorted(STARTS, t, side="right"))
        if n >= 1:
            prev = (n - 1) / 10
            k = ease_out((t - STARTS[n - 1]) / 0.12)
            frac = prev + (n / 10 - prev) * k
            r = RING * SS
            d.arc((cx - r, cy - r, cx + r, cy + r), -90, -90 + 360 * frac, fill=gold, width=16 * SS)
    else:
        u = t - T10
        k = ease_out(u / 0.45)
        r1 = (RING + 40 * (1 - k)) * SS
        d.ellipse((cx - r1, cy - r1, cx + r1, cy + r1), outline=dark, width=22 * SS)
        d.ellipse((cx - r1 + 4 * SS, cy - r1 + 4 * SS, cx + r1 - 4 * SS, cy + r1 - 4 * SS), outline=gold, width=14 * SS)
        r2 = (RING - 40 + 85 * ease_out(u / 0.6)) * SS
        if u > 0.05:
            d.ellipse((cx - r2, cy - r2, cx + r2, cy + r2), outline=gold, width=8 * SS)
        # four-point star twinkles on a seeded ring, each on its own cycle
        rng = np.random.default_rng(10)
        for i in range(12):
            ang = 2 * math.pi * i / 12 + rng.uniform(-0.18, 0.18)
            rad = rng.uniform(RING + 10, RING + 70)
            size = rng.uniform(26, 46)
            phase, period = rng.uniform(0, 1.3), rng.uniform(1.1, 1.6)
            if sanawat and math.sin(ang) > 0.55:      # keep the lower arc clear for the word
                continue
            v = u - 0.25 - phase * 0.4
            if v < 0:
                continue
            s = max(0.0, math.sin(math.pi * ((v % period) / period))) ** 2 * size * SS
            if s < 1:
                continue
            x, y = cx + math.cos(ang) * rad * SS, cy + math.sin(ang) * rad * SS
            if not 60 * SS < x < (W - 60) * SS:      # keep inside the frame
                continue
            pts = [(x, y - s), (x + s * 0.22, y - s * 0.22), (x + s, y), (x + s * 0.22, y + s * 0.22),
                   (x, y + s), (x - s * 0.22, y + s * 0.22), (x - s, y), (x - s * 0.22, y - s * 0.22)]
            d.polygon(pts, fill=(255, 246, 213, 255))
            d.polygon([(px * 0.5 + x * 0.5, py * 0.5 + y * 0.5) for px, py in pts], fill=gold)
    return lay.resize((W, H), Image.LANCZOS)


# ---------------------------------------------------------------- frame
def frame(t, sanawat, alpha=False):
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0) if alpha else GREEN + (255,))
    img.alpha_composite(ring_layer(t, sanawat))
    if t < T10:
        n = int(np.searchsorted(STARTS, t, side="right"))
        if n >= 1:
            u = t - STARTS[n - 1]
            scale = 0.55 + 0.45 * ease_out_back(u / 0.13)
            dy = -18 * ease_out(u / 0.2)
            paste_center(img, WHITE_NUMS[n - 1], CX, CY + dy, scale)
    else:
        u = t - T10
        scale = 1.0 + 0.4 * (1 - ease_out(u / 0.32, 4))        # slams in from big
        spr = TEN
        for start, dur in ((0.45, 0.75), (2.0, 0.55)):          # two shine passes
            if start <= u <= start + dur:
                spr = with_shine(TEN, TEN_INNER, (u - start) / dur)
        paste_center(img, spr, CX, CY - (30 if sanawat else 0), scale)
        if sanawat and u > 0.55:
            k = ease_out((u - 0.55) / 0.35)
            word = WORD
            if 0.9 <= u <= 1.4:
                word = with_shine(WORD, WORD_INNER, (u - 0.9) / 0.5, width=90)
            wy = CY + RING + 140 + 40 * (1 - k)
            # wipe reveal from the centre outwards (hard edge, no fade)
            vis = int(word.width * k)
            if vis > 2:
                crop = word.crop(((word.width - vis) // 2, 0, (word.width + vis) // 2, word.height))
                img.alpha_composite(crop, (int(CX - crop.width / 2), int(wy - word.height / 2)))
    return img if alpha else img.convert("RGB")


# ---------------------------------------------------------------- sound
SR = 48000


def fft_band(x, lo, hi):
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1 / SR)
    X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def sound():
    n = int(DUR * SR)
    out = np.zeros(n)
    rng = np.random.default_rng(7)
    tt = lambda sec: np.arange(int(sec * SR)) / SR

    def put(sig, at, gain=1.0):
        i = int(at * SR)
        sig = sig[: max(0, n - i)]
        out[i:i + len(sig)] += sig * gain

    # rising counter ticks: each number a semitone-pair higher, bright and short
    for k, s in enumerate(STARTS):
        f0 = 523.25 * 2 ** (2 * k / 12)                      # C5 rising by whole tones
        t = tt(0.16)
        env = np.exp(-t * 28)
        tone = (np.sin(2 * np.pi * f0 * t) + 0.45 * np.sin(2 * np.pi * 2 * f0 * t)
                + 0.2 * np.sin(2 * np.pi * 3.01 * f0 * t)) * env
        click = fft_band(rng.normal(0, 1, len(t)), 2500, 9000) * np.exp(-t * 300) * 0.6
        put(tone * 0.32 + click, s, 1.0)
    # riser under the count: sweeping noise + gliding sine, cut just before the hit
    rlen = T10 - 0.04
    t = tt(rlen)
    prog = t / rlen
    noise = rng.normal(0, 1, len(t))
    riser = np.zeros(len(t))
    blk = 2400
    for b in range(0, len(t), blk):
        p = prog[min(b + blk // 2, len(t) - 1)]
        lo = 300 + 4000 * p ** 2
        seg = noise[b:b + blk]
        riser[b:b + blk] = fft_band(seg, lo, lo * 2.2)
    glide = np.sin(2 * np.pi * np.cumsum(180 + 700 * prog ** 2) / SR)
    put((riser * 0.22 + glide * 0.10) * prog ** 2.2, 0.0)
    # the hit at 10: sub boom, metallic chime chord, shimmer
    t = tt(2.6)
    boom = np.sin(2 * np.pi * np.cumsum(45 + 70 * np.exp(-t * 18)) / SR) * np.exp(-t * 3.2)
    put(np.tanh(boom * 1.6) * 0.9, T10)
    chime = np.zeros(len(t))
    for i, f in enumerate([587.33, 739.99, 880.0, 1174.66, 1318.51]):   # D major add9, bright
        mod = np.sin(2 * np.pi * f * 3.5 * t) * 1.8 * np.exp(-t * 2.5)
        chime += np.sin(2 * np.pi * f * t + mod) * np.exp(-t * (1.6 + 0.3 * i)) / 5
    put(chime * 0.85, T10 + 0.01)
    shimmer = fft_band(rng.normal(0, 1, len(t)), 6000, 16000) * np.exp(-t * 2.2) * 0.22
    put(shimmer, T10)
    # sparkle pings timed with the second shine pass
    for k, f in enumerate([2349.3, 2637.0, 3135.9]):
        tp = tt(0.6)
        put(np.sin(2 * np.pi * f * tp) * np.exp(-tp * 9) * 0.08, T10 + 2.0 + 0.09 * k)
    # small room reverb on everything
    ir_t = tt(0.9)
    ir = rng.normal(0, 1, len(ir_t)) * np.exp(-ir_t * 6)
    ir = fft_band(ir, 200, 12000)
    wet = np.fft.irfft(np.fft.rfft(out, 2 * n) * np.fft.rfft(ir, 2 * n), 2 * n)[:n]
    mix = out + wet / np.abs(wet).max() * np.abs(out).max() * 0.18
    fade = int(0.3 * SR)
    mix[-fade:] *= np.linspace(1, 0, fade)
    mix /= np.abs(mix).max() / 0.9
    return np.stack([mix, mix], 1)


def write_wav(path, x):
    with wave.open(path, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())


# ---------------------------------------------------------------- render
def render(path, sanawat, wav):
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                            "-r", str(FPS), "-i", "-", "-i", wav, "-map", "0:v", "-map", "1:a",
                            "-c:v", "libx264", "-preset", "slow", "-crf", "12", "-pix_fmt", "yuv420p",
                            "-profile:v", "high", "-color_primaries", "bt709", "-color_trc", "bt709",
                            "-colorspace", "bt709", "-c:a", "aac", "-b:a", "256k", "-shortest",
                            "-movflags", "+faststart", path], stdin=subprocess.PIPE)
    for i in range(NF):
        enc.stdin.write(frame(i / FPS, sanawat).tobytes())
    enc.stdin.close()
    assert enc.wait() == 0


def render_alpha(stem, sanawat, wav):
    """Transparent versions: ProRes 4444 MOV (with sound), VP9 WebM (with sound), PNG frames."""
    png_dir = stem + "_png"
    os.makedirs(png_dir, exist_ok=True)
    for i in range(NF):
        frame(i / FPS, sanawat, alpha=True).save(os.path.join(png_dir, f"frame_{i:04d}.png"))
    seq = os.path.join(png_dir, "frame_%04d.png")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", seq, "-i", wav,
                    "-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le", "-alpha_bits", "16",
                    "-vendor", "apl0", "-c:a", "pcm_s16le", "-shortest", stem + ".mov"], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", seq, "-i", wav,
                    "-c:v", "libvpx-vp9", "-pix_fmt", "yuva420p", "-b:v", "0", "-crf", "18", "-row-mt", "1",
                    "-auto-alt-ref", "0", "-c:a", "libopus", "-b:a", "192k", "-shortest", stem + ".webm"], check=True)
    subprocess.run(["zip", "-qj", stem + "_png.zip"] + sorted(
        os.path.join(png_dir, f) for f in os.listdir(png_dir)), check=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    raw = os.path.join(OUT, "countup_sound_raw.wav")
    wav = os.path.join(OUT, "countup_sound.wav")
    write_wav(raw, sound())
    # social-loudness normalisation (-14 LUFS, -1 dBTP)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-af", "loudnorm=I=-14:TP=-1:LRA=11",
                    "-ar", str(SR), wav], check=True)
    os.remove(raw)
    render(os.path.join(OUT, "alfaytri_10_countup_green.mp4"), False, wav)
    render(os.path.join(OUT, "alfaytri_10_countup_green_sanawat.mp4"), True, wav)
    if "--alpha" in sys.argv:
        render_alpha(os.path.join(OUT, "alfaytri_10_countup_transparent"), False, wav)
        render_alpha(os.path.join(OUT, "alfaytri_10_countup_transparent_sanawat"), True, wav)
    # contact sheet for review: the count, the hit, the shine, the end
    times = [STARTS[0] + 0.1, STARTS[4] + 0.05, STARTS[8] + 0.05, T10 + 0.03, T10 + 0.8, T10 + 2.25, DUR - 0.05]
    tiles = [frame(t, s).resize((270, 480)) for s in (False, True) for t in times]
    sheet = Image.new("RGB", (270 * len(times), 480 * 2), (0, 0, 0))
    for i, tile in enumerate(tiles):
        sheet.paste(tile, ((i % len(times)) * 270, (i // len(times)) * 480))
    sheet.save(os.path.join(OUT, "contact_sheet.jpg"), quality=85)
    print("done", NF, "frames, 10 hits at", round(T10, 2), "s")


if __name__ == "__main__":
    main()
