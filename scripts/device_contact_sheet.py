#!/usr/bin/env python3
"""Every device x look x aspect of DeviceDemo on one sheet, settled — for a person to LOOK at before calling it
done. `device_contact_sheet.py <out.png> [kind ...]` — every kind by default."""
import json
import os
import shutil
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(_HERE, "..", "remotion")
FONT = os.path.join(_HERE, "..", "assets", "fonts", "NotoSansSC-Subset.ttf")


def _ui(path, w=1170, h=2532):
    """A code-drawn screen at a device's own pixel size: rows of labelled feedback, scaled to the screen."""
    im = Image.new("RGB", (w, h), "white")
    d = ImageDraw.Draw(im)
    u = w / 1170.0
    f = ImageFont.truetype(FONT, max(12, int(46 * u)))
    d.rounded_rectangle([int(60 * u), int(200 * u), int(w - 60 * u), int(320 * u)], radius=int(36 * u), fill=(238, 241, 244))
    for i in range(10):
        y = int((420 + i * 180) * u)
        if y > h - 60 * u:
            break
        d.text((int(90 * u), y), "第%d条反馈" % (i + 1), fill=(20, 23, 28), font=f)
    im.save(path)


KINDS = ("phone", "watch", "tablet", "tablet-landscape", "laptop", "monitor")


def _size(kind):
    """The pixel size a kind's screen is drawn for — its `like` model's own (deviceSpec.json `kinds`), so the sheet
    shows each kind as a real capture would fill it; a monitor has no model and keeps its generic ratio."""
    import device_script as ds
    like = ds.SPEC["kinds"].get(kind, {}).get("like")
    if not like:
        rw, rh = ds.SPEC["screenRatio"][kind]
        return 1920, int(round(1920 * rh / float(rw)))
    w, h = ds.SPEC["models"][like]["published"]["px"]
    return (h, w) if kind == "tablet-landscape" else (w, h)


def _render(tmp, look, aspect, kind="phone"):
    w, h = _size(kind)
    name = "ui-%s.png" % kind
    if not os.path.isfile(os.path.join(tmp, name)):
        _ui(os.path.join(tmp, name), w, h)
    props = {"device": kind, "look": look, "aspect": aspect, "dna": "product", "camera": "still",
             "steps": [{"screen": {"image": name}, "imageW": w, "imageH": h, "t0": 0.06,
                        "ta": 0.06, "t1": 0.2},
                       {"tap": [0.3, 0.2], "t0": 0.3, "ta": 0.4, "t1": 0.7}]}
    import device_script as ds
    like = ds.SPEC["kinds"].get(kind, {}).get("like")
    if like:
        props["model"] = like                              # drawn as the model its capture size names
    pf = os.path.join(tmp, "%s-%s-%s.json" % (kind, look, aspect.replace(":", "x")))
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(props, fh)
    png = pf[:-5] + ".png"
    try:
        r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "DeviceDemo", png, "--frame=72",
                            "--gl=angle", "--log=error", "--scale=0.5", "--props=" + pf, "--public-dir=" + tmp],
                           cwd=_REM, capture_output=True, text=True)
    except FileNotFoundError:
        raise SystemExit("device_contact_sheet: `npx` was not found — install Node and run `npm install` in remotion/")
    if r.returncode != 0:
        raise SystemExit("device_contact_sheet: the %s %s %s tile failed to render:\n%s"
                         % (kind, look, aspect, (r.stdout + r.stderr).strip()[-600:]))
    return Image.open(png).convert("RGB")                  # loaded now: the temp dir goes when the sheet is done


def main(out_png, kinds=KINDS):
    if not os.path.isfile(FONT):
        raise SystemExit("device_contact_sheet: the bundled font %s is missing" % FONT)
    unknown = [k for k in kinds if k not in KINDS]
    if unknown:
        raise SystemExit("device_contact_sheet: no device %s — one of %s" % (", ".join(unknown), ", ".join(KINDS)))
    sys.path.insert(0, _HERE)
    tmp = tempfile.mkdtemp(prefix="devsheet_")
    try:
        tiles = [("%s %s %s" % (kind, look, aspect), _render(tmp, look, aspect, kind))
                 for kind in kinds for aspect in ("16:9", "9:16") for look in ("flat", "real", "screen")]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    ims = [im for _, im in tiles]
    rows = len(ims) // 3
    w = max(i.width for i in ims)
    sheet = Image.new("RGB", (w * 3 + 40, sum(max(i.height for i in ims[r * 3:r * 3 + 3]) + 40 for r in range(rows))), "white")
    d, y = ImageDraw.Draw(sheet), 0
    for r in range(rows):
        row = ims[r * 3:r * 3 + 3]
        for c, im in enumerate(row):
            d.text((10 + c * (w + 10), y + 5), tiles[r * 3 + c][0], fill="black")
            sheet.paste(im, (10 + c * (w + 10), y + 30))
        y += max(i.height for i in row) + 40
    sheet.save(out_png)
    print(out_png)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("usage: device_contact_sheet.py <out.png> [kind ...] — every device, look and aspect of DeviceDemo "
                 "on one sheet")
    main(sys.argv[1], tuple(sys.argv[2:]) or KINDS)
