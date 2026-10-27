#!/usr/bin/env python3
"""Turn the official Al Faytri logo (charcoal artwork on a white background) into
transparent PNGs in the brand colours, plus the icon on its own for small uses.

The alpha channel comes straight from the artwork's darkness, so shapes and the
"ALFAYTRI / الفيتري" lettering are kept exactly; nothing is redrawn.

Usage: official_logo.py LOGO.jpg WORKDIR
Writes WORKDIR/assets/brand/official/{logo,icon}_{white,charcoal,orange}.png
"""
import json
import os
import sys

import numpy as np
from PIL import Image

SRC, WORK = sys.argv[1], os.path.abspath(sys.argv[2])
OUT = os.path.join(WORK, "assets/brand/official")
brand = json.load(open(os.path.join(WORK, "config/brand.json"), encoding="utf-8"))
h = brand["colors"]["primary"].lstrip("#")
COLOURS = {"white": (255, 255, 255), "charcoal": (58, 58, 60), "orange": tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))}

a = np.asarray(Image.open(SRC).convert("L")).astype(np.float32)
# white paper -> 0, charcoal ink (~60) -> 1, anti-aliased edges in between
alpha = np.clip((235 - a) / (235 - 75), 0, 1)
alpha[alpha < 0.04] = 0
ys, xs = np.nonzero(alpha > 0.5)
box = (xs.min() - 6, ys.min() - 6, xs.max() + 7, ys.max() + 7)
alpha = alpha[box[1]:box[3], box[0]:box[2]]

# the icon is everything above the first fully empty band of rows under the house
rows = alpha.max(1) > 0.5
gap = next(y for y in range(int(len(rows) * 0.4), len(rows)) if not rows[y:y + 20].any())
icon_alpha = alpha[:gap]
iy, ix = np.nonzero(icon_alpha > 0.5)
icon_alpha = icon_alpha[:, max(ix.min() - 6, 0):ix.max() + 7]

os.makedirs(OUT, exist_ok=True)
for name, rgb in COLOURS.items():
    for kind, m in (("logo", alpha), ("icon", icon_alpha)):
        img = Image.new("RGBA", (m.shape[1], m.shape[0]), rgb + (0,))
        img.putalpha(Image.fromarray((m * 255).astype(np.uint8)))
        img.save(os.path.join(OUT, f"{kind}_{name}.png"))
print("official logo", alpha.shape[::-1], "icon", icon_alpha.shape[::-1])
