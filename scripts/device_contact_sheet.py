#!/usr/bin/env python3
"""Every look x aspect of DeviceDemo on one sheet, settled — for a person to LOOK at before calling it done."""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(_HERE, "..", "remotion")
FONT = os.path.join(_HERE, "..", "assets", "fonts", "NotoSansSC-Subset.ttf")


def _ui(path):
    im = Image.new("RGB", (1170, 2532), "white")
    d = ImageDraw.Draw(im)
    f = ImageFont.truetype(FONT, 46)
    d.rounded_rectangle([60, 200, 1110, 320], radius=36, fill=(238, 241, 244))
    for i in range(10):
        d.text((90, 420 + i * 180), "第%d条反馈" % (i + 1), fill=(20, 23, 28), font=f)
    im.save(path)


def main(out_png):
    tmp = tempfile.mkdtemp(prefix="devsheet_")
    _ui(os.path.join(tmp, "ui.png"))
    tiles = []
    for aspect in ("16:9", "9:16"):
        for look in ("flat", "real", "screen"):
            props = {"device": "phone", "look": look, "aspect": aspect, "dna": "product", "camera": "still",
                     "steps": [{"screen": {"image": "ui.png"}, "imageW": 1170, "imageH": 2532, "t0": 0.06,
                                "ta": 0.06, "t1": 0.2},
                               {"tap": [0.3, 0.2], "t0": 0.3, "ta": 0.4, "t1": 0.7}]}
            pf = os.path.join(tmp, "%s-%s.json" % (look, aspect.replace(":", "x")))
            json.dump(props, open(pf, "w", encoding="utf-8"))
            png = pf[:-5] + ".png"
            subprocess.run(["npx", "remotion", "still", "src/index.ts", "DeviceDemo", png, "--frame=72",
                            "--gl=angle", "--log=error", "--scale=0.5", "--props=" + pf, "--public-dir=" + tmp],
                           cwd=_REM, check=True)
            tiles.append(("%s %s" % (look, aspect), png))
    ims = [Image.open(p).convert("RGB") for _, p in tiles]
    w = max(i.width for i in ims)
    sheet = Image.new("RGB", (w * 3 + 40, sum(max(i.height for i in ims[r * 3:r * 3 + 3]) + 40 for r in range(2))), "white")
    d, y = ImageDraw.Draw(sheet), 0
    for r in range(2):
        row = ims[r * 3:r * 3 + 3]
        for c, im in enumerate(row):
            d.text((10 + c * (w + 10), y + 5), tiles[r * 3 + c][0], fill="black")
            sheet.paste(im, (10 + c * (w + 10), y + 30))
        y += max(i.height for i in row) + 40
    sheet.save(out_png)
    print(out_png)


if __name__ == "__main__":
    main(sys.argv[1])
