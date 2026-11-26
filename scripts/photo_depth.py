#!/usr/bin/env python3
"""photo_depth — estimate a depth map for one still photo, locally, for the 2.5D "photo that moves in 3D" shot.

    python3 scripts/photo_depth.py <image> [--out <depth.png>]

Writes a 16-bit grayscale PNG (default `<image stem>.depth.png` beside the image): 65535 = nearest, 0 = farthest
(the model's relative inverse depth, stretched to the full range), at the model's own working resolution (short side
518, the image's aspect); the page helper `assets/html/depthphoto.js` maps it onto the photo by UV. Prints the
weights and their licence.

MODEL. Depth Anything V2 SMALL as ONNX (onnx-community/depth-anything-v2-small, pinned revision and sha256 below),
run with onnxruntime on the CPU (no PyTorch). Licence verified on both model cards 2026-11-26: Small is Apache-2.0
(commercial use fine); Base and Large are CC-BY-NC-4.0, so never swap them in for a film that may be used
commercially. Downloaded once (99 MB) to ~/.topic-to-video/models/depth-anything-v2-small/ (TTV_MODELS overrides the
folder), never into the repo.

Exit 0 written · 2 usage error, onnxruntime missing, or the model cannot be fetched (the message says what to do).
"""
import hashlib
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common as _c  # noqa: E402

_USAGE = "usage: photo_depth.py <image> [--out <depth.png>]"
REPO = "onnx-community/depth-anything-v2-small"
REV = "4472b7362082ad9968fee890ca0f1e5aca36b93d"
URL = "https://huggingface.co/%s/resolve/%s/onnx/model.onnx" % (REPO, REV)
SHA256 = "afb6a5c28f3b6bf1618c6e43f02073ef9dfdc70e937502d51603e57b0a1df10c"
LICENCE = ("Depth Anything V2 Small, ONNX weights %s @%s; licence Apache-2.0 "
           "(https://huggingface.co/%s, base model https://huggingface.co/depth-anything/Depth-Anything-V2-Small)"
           % (REPO, REV[:7], REPO))
SIDE = 518                      # the model's working size (preprocessor_config.json), sides a multiple of 14
MEAN, STD = (0.485, 0.456, 0.406), (0.229, 0.224, 0.225)


class Unavailable(RuntimeError):
    """The model or its runtime is not available on this machine; the message says how to get it."""


def model_path():
    d = os.environ.get("TTV_MODELS") or os.path.join(os.path.expanduser("~"), ".topic-to-video", "models")
    d = os.path.join(d, "depth-anything-v2-small")
    p = os.path.join(d, "model.onnx")
    if os.path.isfile(p):
        return p
    os.makedirs(d, exist_ok=True)
    part = p + ".part"
    print("[photo_depth] fetching the model once (99 MB): %s" % URL)
    try:
        h = hashlib.sha256()
        with urllib.request.urlopen(URL, timeout=60) as r, open(part, "wb") as f:
            while True:
                b = r.read(1 << 20)
                if not b:
                    break
                h.update(b)
                f.write(b)
    except Exception as e:
        if os.path.exists(part):
            os.remove(part)
        raise Unavailable("could not fetch the depth model (%s: %s). Check the network, or download %s by hand to %s"
                          % (type(e).__name__, e, URL, p))
    if h.hexdigest() != SHA256:
        os.remove(part)
        raise Unavailable("the downloaded model's sha256 %s is not the pinned %s; refusing it" % (h.hexdigest(), SHA256))
    os.replace(part, p)
    with open(os.path.join(d, "LICENCE.txt"), "w", encoding="utf-8") as f:
        f.write(LICENCE + "\n")
    return p


def work_size(w, h):
    """DPTImageProcessor with keep_aspect_ratio: scale by the factor closer to 1 that brings a side to 518, each side
    rounded to a multiple of 14 (so a large photo's SHORT side becomes 518)."""
    sw, sh = SIDE / w, SIDE / h
    s = sw if abs(1 - sw) < abs(1 - sh) else sh
    return max(14, int(round(w * s / 14)) * 14), max(14, int(round(h * s / 14)) * 14)


def estimate(img):
    """img: PIL image. Returns the depth as a float32 array (h', w') in [0, 1], 1 = nearest."""
    import numpy as np
    from PIL import Image
    try:
        import onnxruntime as ort
    except ImportError:
        raise Unavailable("onnxruntime is not installed: pip install onnxruntime")
    sess = ort.InferenceSession(model_path(), providers=["CPUExecutionProvider"])
    W, H = work_size(*img.size)
    x = np.asarray(img.convert("RGB").resize((W, H), Image.BICUBIC), dtype=np.float32) / 255.0
    x = ((x - np.array(MEAN, np.float32)) / np.array(STD, np.float32)).transpose(2, 0, 1)[None]
    d = sess.run(None, {"pixel_values": np.ascontiguousarray(x)})[0][0].astype(np.float64)
    lo, hi = float(d.min()), float(d.max())
    if not hi > lo:
        return np.zeros(d.shape, np.float32)      # a flat picture has no depth to show: every pixel the same plane
    return ((d - lo) / (hi - lo)).astype(np.float32)


def write_png16(depth, out):
    import numpy as np
    from PIL import Image
    from PIL.PngImagePlugin import PngInfo
    info = PngInfo()
    info.add_text("depth", "relative inverse depth, 65535 = nearest")
    info.add_text("model", LICENCE)
    Image.fromarray(np.round(depth * 65535).astype(np.uint16)).save(out, pnginfo=info)


def main(argv):
    _c.refuse_unknown(argv, valued=("out",), usage=_USAGE)
    out = _c.argflag(argv, "out")
    args = [a for a in argv if not a.startswith("--") and a != out]
    if len(args) != 1 or not os.path.isfile(args[0]):
        print(_USAGE if len(args) != 1 else "[photo_depth] no such image: %s" % args[0])
        return 2
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(Image.open(args[0]))      # the pixels as a viewer sees them
    out = out or os.path.splitext(args[0])[0] + ".depth.png"
    try:
        depth = estimate(img)
    except Unavailable as e:
        print("[photo_depth] %s" % e)
        return 2
    write_png16(depth, out)
    print("[photo_depth] %s -> %s (%dx%d, 16-bit, white = near)" % (args[0], out, depth.shape[1], depth.shape[0]))
    print("[photo_depth] weights: %s" % LICENCE)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
