#!/usr/bin/env python3
"""A beat's Blender plate: a 3D render a workshop shot draws under its own overlay.

    python3 scripts/blender_plate.py <out_dir> [--only ID] [--still F] [--yes]

Blender draws what 3D physicality is the content of — a real place or object, a material, a physical process, an
optical effect, a space to move through — and nothing else: words, captions, timing, data and layout stay in
Remotion (docs/superpowers/specs/2026-11-04-blender-plates-design.md, references/blender-plates.md). A plate is
`media/blender/<id>/`: plate.webm (VP9 with alpha), anchors.json, boxes.json, camera.json, plate.json.
"""
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

MIN_BLENDER = (5, 0)            # 5.0 renamed EEVEE's engine id to BLENDER_EEVEE and dropped scene.node_tree
_APP_PATHS = ("/Applications/Blender.app/Contents/MacOS/Blender",)


class PlateError(Exception):
    pass


def _runnable(p):
    return bool(p) and os.path.isfile(p) and os.access(p, os.X_OK)


def blender_bin(meta=None):
    """The Blender binary: meta.blender, then $TTV_BLENDER, then the macOS app, then `blender` on PATH; None if none."""
    for p in ((meta or {}).get("blender"), os.environ.get("TTV_BLENDER"), *_APP_PATHS):
        if _runnable(p):
            return p
    return shutil.which("blender")


def _version_line(binary):
    r = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=60)
    return (r.stdout or "").strip().splitlines()[0] if (r.stdout or "").strip() else ""


def blender_version(binary):
    """(major, minor, patch, is_release_candidate) from `blender --version`."""
    line = _version_line(binary)
    m = re.search(r"Blender\s+(\d+)\.(\d+)(?:\.(\d+))?", line)
    if not m:
        raise PlateError("%s --version printed no version line (%r)" % (binary, line[:80]))
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0), "release candidate" in line.lower()


def require_blender(meta=None):
    """The binary to run, or PlateError saying why there is none. A release candidate runs, with a WARN."""
    b = blender_bin(meta)
    if not b:
        raise PlateError("Blender not found — install Blender >= %d.%d (blender.org) or set TTV_BLENDER / "
                         "meta.blender to its binary" % MIN_BLENDER)
    v = blender_version(b)
    if v[:2] < MIN_BLENDER:
        raise PlateError("Blender %d.%d.%d at %s is older than %d.%d" % (v[0], v[1], v[2], b, *MIN_BLENDER))
    if v[3]:
        print("[blender_plate] WARN Blender %d.%d.%d is a release candidate — pin a release for delivery" % v[:3])
    return b
