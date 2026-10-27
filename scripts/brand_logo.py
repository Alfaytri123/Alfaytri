#!/usr/bin/env python3
"""Interim Al Faytri logo: the house + screwdriver + wrench icon redrawn as clean
geometry measured from the staff polo print (assets/brand/uniform_back.jpg), with
the "AL FAYTRI / الفيتري" wordmark typeset under it.

The print is too small (~130 px) to trace cleanly. Replace this with the official
logo file as soon as it is available: set "logo_path" in config/brand.json to a
transparent PNG and compose.py uses that file instead.

Usage: brand_logo.py WORKDIR   -> writes WORKDIR/assets/brand/logo_{white,charcoal}.png
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

SS = 4  # supersampling factor


def draw_icon(size, color):
    """Icon on a transparent square-ish canvas. Coordinates are in a 528 x 540 design
    grid (4x the print's pixel grid) and scaled to `size` px wide."""
    gw, gh = 528, 540
    k = size * SS / gw
    im = Image.new("RGBA", (int(gw * k), int(gh * k)), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    P = lambda x, y: (x * k, y * k)

    def stroke(points, w):
        pts = [P(*p) for p in points]
        d.line(pts, fill=color, width=int(w * k), joint="curve")
        for p in pts:  # round caps and joins
            r = w * k / 2
            d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=color)

    W = 44  # outline stroke
    # house: inward-curled feet, walls, roof to apex
    stroke([(132, 448), (72, 448), (72, 190), (262, 40), (456, 190), (456, 448), (398, 448)], W)
    stroke([(128, 132), (128, 62)], 40)                     # chimney on the left roof slope
    clear = (0, 0, 0, 0)
    # screwdriver: tip, thin shaft, pear-shaped handle
    stroke([(200, 198), (200, 214)], 14)
    stroke([(200, 214), (200, 362)], 10)
    d.polygon([P(190, 360), P(210, 360), P(222, 392), P(228, 430), P(226, 505), P(174, 505), P(172, 430),
               P(178, 392)], fill=color)
    stroke([(200, 420), (200, 508)], 52)
    # wrench: flared open jaw head, tapering neck, straight shaft
    cx = 312
    d.ellipse((*P(cx - 56, 196), *P(cx + 56, 292)), fill=color)
    d.polygon([P(cx - 46, 180), P(cx + 46, 180), P(cx + 16, 240), P(cx - 16, 240)], fill=clear)
    d.ellipse((*P(cx - 16, 224), *P(cx + 16, 256)), fill=clear)
    d.polygon([P(cx - 36, 278), P(cx + 36, 278), P(cx + 16, 330), P(cx - 16, 330)], fill=color)
    stroke([(cx, 320), (cx, 510)], 32)
    return im.resize((size, int(gh * size / gw)), Image.LANCZOS)


def logo(work, color, width=520):
    brand = json.load(open(os.path.join(work, "config/brand.json"), encoding="utf-8"))
    f_lat = ImageFont.truetype(os.path.join(work, brand["fonts"]["bold"]), int(width * 0.205),
                               layout_engine=ImageFont.Layout.RAQM)
    f_ar = ImageFont.truetype(os.path.join(work, brand["fonts"]["medium"]), int(width * 0.22),
                              layout_engine=ImageFont.Layout.RAQM)
    icon = draw_icon(int(width * 0.62), color)
    h = icon.height + int(width * 0.62)
    out = Image.new("RGBA", (width, h), (0, 0, 0, 0))
    out.alpha_composite(icon, ((width - icon.width) // 2, 0))
    d = ImageDraw.Draw(out)
    y = icon.height + int(width * 0.04)
    d.text((width / 2, y), "AL FAYTRI", font=f_lat, fill=color, anchor="mt")
    d.text((width / 2, y + int(width * 0.22)), "الفيتري", font=f_ar, fill=color, anchor="mt",
           direction="rtl", language="ar")
    return out.crop(out.getbbox())


if __name__ == "__main__":
    work = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else ".")
    os.makedirs(os.path.join(work, "assets/brand"), exist_ok=True)
    for name, col in (("white", (255, 255, 255, 255)), ("charcoal", (58, 58, 60, 255))):
        logo(work, col).save(os.path.join(work, "assets/brand", f"logo_{name}.png"))
        draw_icon(480, col).save(os.path.join(work, "assets/brand", f"icon_{name}.png"))
    print("logo written")
