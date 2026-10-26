#!/usr/bin/env python3
"""Storyboard board for the five scenes, built from frames of the final cut so it
matches the delivered edit exactly.

Usage: storyboard.py WORKDIR VIDEO
Writes WORKDIR/output/storyboard.jpg
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

WORK, VIDEO = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
EDL = json.load(open(os.path.join(WORK, "config/edl.json"), encoding="utf-8"))
BRAND = json.load(open(os.path.join(WORK, "config/brand.json"), encoding="utf-8"))
SCENES = {
    1: ("المشكلة والحرارة", "00:00–00:03"),
    2: ("طلب الصيانة عبر الهاتف", "00:03–00:05"),
    3: ("وصول الفني والصيانة والتنظيف", "00:05–00:10"),
    4: ("عودة الراحة والرضا", "00:10–00:11.5"),
    5: ("الدفع الإلكتروني والنهاية", "00:11.5–00:15"),
}
SHOT_AR = {
    "1A": "لقطة واسعة: الرجل يمسح العرق والمكيف ظاهر",
    "1B": "لقطة قريبة: فتحات المكيف وهواء دافئ ضعيف",
    "1C": "قريبة: يضغط جهاز التحكم بلا فائدة",
    "2A": "من خلف الكتف: يفتح التطبيق على الجوال",
    "2B": "واجهة الطلب: اختيار الخدمة وتأكيد الطلب",
    "3A": "وصول الفني بالزي والمعدات",
    "3B": "الفحص: فتح الغطاء الأمامي والجهاز مطفأ",
    "3C": "إخراج الفلتر وإظهار الأتربة",
    "3D": "غسل الفلتر بعيداً عن الكهرباء",
    "3E": "إغلاق الغطاء وتشغيل المكيف",
    "4A": "الرجل يسترخي ويبتسم مع عودة البرودة",
    "5A": "إشارة رضا للفني + واجهة الدفع والتأكيد",
    "5B": "بطاقة النهاية: الشعار والعبارة والدعوة",
}
TW, TH = 240, 427


def font(w, s):
    return ImageFont.truetype(os.path.join(WORK, BRAND["fonts"][w]), s, layout_engine=ImageFont.Layout.RAQM)


def rtl(d, xy, s, f, fill, anchor="ra"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor, direction="rtl", language="ar")


def frame(t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", VIDEO, "-frames:v", "1",
                          "-vf", f"scale={TW}:{TH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         check=True, capture_output=True).stdout
    return Image.frombytes("RGB", (TW, TH), raw)


def main():
    segs = EDL["segments"]
    by_scene = {}
    for s in segs:
        by_scene.setdefault(s["scene"], []).append(s)
    pad, gap, head = 40, 18, 110
    max_shots = max(len(v) for v in by_scene.values())
    row_h = 60 + TH + 120
    Wd = pad * 2 + max_shots * TW + (max_shots - 1) * gap
    Ht = head + len(by_scene) * (row_h + 24) + pad
    board = Image.new("RGB", (Wd, Ht), (246, 247, 248))
    d = ImageDraw.Draw(board)
    rtl(d, (Wd - pad, 30), "Storyboard — «من الحر إلى الراحة» • 9:16 • 15 ثانية", font("black", 40), (23, 33, 43))
    y = head
    for sc in sorted(by_scene):
        title, span = SCENES[sc]
        d.rounded_rectangle((pad - 12, y - 8, Wd - pad + 12, y + row_h), 18, fill=(255, 255, 255), outline=(222, 228, 232))
        rtl(d, (Wd - pad, y + 6), f"المشهد {sc}: {title}", font("black", 32), (14, 124, 134))
        d.text((pad, y + 12), span, font=font("bold", 26), fill=(107, 119, 133))
        x = Wd - pad - TW  # right-to-left reading order
        for s in by_scene[sc]:
            t = s["start"] + s["dur"] * 0.6
            board.paste(frame(t), (x, y + 56))
            d.text((x + 6, y + 60), f"{s['id']}  {s['start']:.2f}–{s['start'] + s['dur']:.2f}s",
                   font=font("bold", 20), fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
            words, line, lines = SHOT_AR[s["id"]].split(), "", []
            for w_ in words:
                trial = (line + " " + w_).strip()
                if font("medium", 22).getlength(trial, direction="rtl", language="ar") > TW - 8 and line:
                    lines.append(line)
                    line = w_
                else:
                    line = trial
            lines.append(line)
            for li, ln in enumerate(lines[:3]):
                rtl(d, (x + TW, y + 64 + TH + li * 30), ln, font("medium", 22), (23, 33, 43))
            x -= TW + gap
        y += row_h + 24
    os.makedirs(os.path.join(WORK, "output"), exist_ok=True)
    board.save(os.path.join(WORK, "output", "storyboard.jpg"), quality=88)
    print("storyboard", board.size)


if __name__ == "__main__":
    main()
