#!/usr/bin/env python3
"""Technical QC of the final ad file: container/stream checks, loudness, and a contact
sheet of representative frames for visual review.

Usage: qc.py WORKDIR VIDEO
Writes WORKDIR/qc/report.json and WORKDIR/qc/contact_sheet.jpg
"""
import json
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

WORK, VIDEO = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
QC = os.path.join(WORK, "qc")
os.makedirs(QC, exist_ok=True)
SAMPLE_TIMES = [0.6, 1.8, 2.6, 3.3, 4.6, 5.5, 6.5, 7.5, 8.5, 9.5, 10.8, 12.4, 13.3, 14.9]


def probe():
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", VIDEO],
                         check=True, capture_output=True, text=True).stdout
    return json.loads(out)


def loudness():
    err = subprocess.run(["ffmpeg", "-hide_banner", "-i", VIDEO, "-map", "0:a", "-af", "ebur128=peak=true",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    summary = err[err.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", summary)
    tp = re.search(r"Peak:\s+(-?[\d.]+) dBFS", summary)
    return float(i.group(1)), float(tp.group(1)) if tp else None


def frame(t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", VIDEO, "-frames:v", "1",
                          "-vf", "scale=270:480", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         check=True, capture_output=True).stdout
    return Image.frombytes("RGB", (270, 480), raw)


def main():
    info = probe()
    v = next(s for s in info["streams"] if s["codec_type"] == "video")
    a = [s for s in info["streams"] if s["codec_type"] == "audio"]
    num, den = map(int, v["r_frame_rate"].split("/"))
    fps = num / den
    dur = float(info["format"]["duration"])
    lufs, tp = loudness() if a else (None, None)
    checks = {
        "file_exists": os.path.getsize(VIDEO) > 0,
        "duration_10_to_15s": 10.0 <= dur <= 15.05,
        "resolution_1080x1920": (v["width"], v["height"]) == (1080, 1920),
        "aspect_9_16": abs(v["width"] / v["height"] - 9 / 16) < 1e-3,
        "codec_h264": v["codec_name"] == "h264",
        "pix_fmt_yuv420p": v.get("pix_fmt") == "yuv420p",
        "fps_25_or_30": round(fps, 3) in (25.0, 30.0),
        "audio_present": bool(a),
        "audio_aac_48k_stereo": bool(a) and a[0]["codec_name"] == "aac" and a[0]["sample_rate"] == "48000"
                                and a[0]["channels"] == 2,
        "loudness_-14_LUFS_pm1": lufs is not None and abs(lufs + 14) <= 1.0,
        "true_peak_below_-0.5dBFS": tp is not None and tp <= -0.5,
    }
    report = {"file": os.path.basename(VIDEO), "size_mb": round(os.path.getsize(VIDEO) / 1e6, 2),
              "duration_s": round(dur, 3), "width": v["width"], "height": v["height"], "fps": fps,
              "video_codec": v["codec_name"], "profile": v.get("profile"), "bitrate_kbps": round(int(info["format"]["bit_rate"]) / 1000),
              "audio": {k: a[0].get(k) for k in ("codec_name", "sample_rate", "channels")} if a else None,
              "integrated_lufs": lufs, "peak_dbfs": tp, "checks": checks, "all_passed": all(checks.values())}
    json.dump(report, open(os.path.join(QC, "report.json"), "w"), indent=2)
    cols = 7
    rows = (len(SAMPLE_TIMES) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * 280 + 10, rows * 520 + 10), (24, 26, 30))
    d = ImageDraw.Draw(sheet)
    fnt = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 20) if os.path.exists(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") else ImageFont.load_default()
    for i, t in enumerate(SAMPLE_TIMES):
        x, y = 10 + (i % cols) * 280, 10 + (i // cols) * 520
        sheet.paste(frame(min(t, dur - 0.05)), (x, y))
        d.text((x + 4, y + 486), f"{t:05.2f}s", fill=(230, 230, 230), font=fnt)
    sheet.save(os.path.join(QC, "contact_sheet.jpg"), quality=86)
    print(json.dumps(report, indent=2))
    return 0 if report["all_passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
