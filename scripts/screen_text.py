#!/usr/bin/env python3
"""Find the words a step names inside a screenshot.

A step may target `{"text": "反馈汇总"}` instead of coordinates. That is resolved here, at build time, and the
coordinates are written into the props — so the per-beat render cache keys on them. macOS Vision (a compiled
Swift helper, Chinese and English) when on a Mac; tesseract when it is installed; otherwise the step must use
coordinates, and the error says so. Results are cached per screenshot content hash.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata

import device_script as ds

_HERE = os.path.dirname(os.path.abspath(__file__))
_SWIFT = os.path.join(_HERE, "ocr_macos.swift")
_BIN_DIR = os.path.join(os.path.expanduser("~"), ".cache", "slides-to-video")


def _sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def available():
    if sys.platform == "darwin" and shutil.which("swiftc"):
        return "vision"
    if shutil.which("tesseract"):
        return "tesseract"
    return None


def _replace(path, write):
    """Write through a uniquely named temporary file beside `path` and rename it into place: a reader never
    sees half a file, and racing writers — processes or threads — each land a whole one. A write the disk
    refuses is a DeviceScriptError naming the path."""
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), prefix=os.path.basename(path) + ".",
                                   suffix=".tmp")
        os.close(fd)
        write(tmp)
        os.replace(tmp, path)
    except OSError as e:
        raise ds.DeviceScriptError(["cannot write %s: %s" % (path, e)])
    finally:
        if tmp and os.path.exists(tmp):
            os.remove(tmp)


def _compile(exe):
    os.makedirs(_BIN_DIR, exist_ok=True)

    def build(tmp):
        r = subprocess.run(["swiftc", "-O", _SWIFT, "-o", tmp], capture_output=True, text=True)
        if r.returncode != 0:
            raise ds.DeviceScriptError(["compiling the text-recognition helper failed: %s" % r.stderr.strip()[-300:]])
        os.chmod(tmp, 0o755)
    _replace(exe, build)


def _vision(path):
    exe = os.path.join(_BIN_DIR, "ocr_macos-" + _sha(_SWIFT)[:16])
    if not os.path.exists(exe):
        _compile(exe)
    try:
        r = subprocess.run([exe, path], capture_output=True, text=True)
    except OSError:                          # a helper left unrunnable (a torn write from an older build): rebuild once
        _compile(exe)
        try:
            r = subprocess.run([exe, path], capture_output=True, text=True)
        except OSError as e:
            raise ds.DeviceScriptError(["cannot run the text-recognition helper %s: %s" % (exe, e)])
    if r.returncode != 0:
        raise ds.DeviceScriptError(["text recognition failed on %s: %s" % (path, r.stderr.strip()[-200:])])
    return [{"text": o["text"], "box": [float(v) for v in o["box"]]} for o in json.loads(r.stdout or "[]")]


def _tesseract(path):
    from PIL import Image
    with Image.open(path) as im:
        W, H = im.size
    langs = subprocess.run(["tesseract", "--list-langs"], capture_output=True, text=True).stdout
    lang = "chi_sim+eng" if "chi_sim" in langs else "eng"
    r = subprocess.run(["tesseract", path, "stdout", "-l", lang, "tsv"], capture_output=True, text=True)
    if r.returncode != 0:
        raise ds.DeviceScriptError(["text recognition (tesseract) failed on %s: %s" % (path, r.stderr.strip()[-200:])])
    lines = {}
    for row in r.stdout.splitlines()[1:]:
        c = row.split("\t")
        if len(c) < 12 or not c[11].strip():
            continue
        key = (c[2], c[3], c[4])
        x, y, w, h = (int(v) for v in c[6:10])
        cur = lines.setdefault(key, {"text": "", "box": [x, y, x + w, y + h]})
        cur["text"] += c[11].strip()
        b = cur["box"]
        cur["box"] = [min(b[0], x), min(b[1], y), max(b[2], x + w), max(b[3], y + h)]
    return [{"text": v["text"], "box": [v["box"][0] / W, v["box"][1] / H, v["box"][2] / W, v["box"][3] / H]}
            for v in lines.values()]


def recognize(path, cache_dir=None):
    if not os.path.isfile(path):
        raise ds.DeviceScriptError(["the screenshot %s does not exist or is not a file" % path])
    backend = available()
    if backend is None:
        raise ds.DeviceScriptError(["a text target needs text recognition, and this machine has none (macOS "
                                    "Vision needs `swiftc`; elsewhere install tesseract) — give the target as "
                                    "[x, y] instead"])
    cache = os.path.join(cache_dir or _BIN_DIR, "screen_text")
    os.makedirs(cache, exist_ok=True)
    memo = os.path.join(cache, "%s-%s.json" % (_sha(path), backend))
    if os.path.exists(memo):
        try:
            with open(memo, encoding="utf-8") as fh:
                return json.load(fh)
        except (OSError, ValueError):
            pass                                            # a torn or corrupt entry: recognise again
    lines = _vision(path) if backend == "vision" else _tesseract(path)

    def write(tmp):
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(lines, fh, ensure_ascii=False)
    _replace(memo, write)
    return lines


def _norm_map(s):
    """(`s` without whitespace, width- and case-blind; for each of its characters, the index of the character
    of `s` it came from, counting only non-space ones; how many non-space characters `s` has). NFKC folds
    full-width punctuation and letters (设置： is 设置:, ＡＩ is AI) but can lengthen a character (㎡ becomes
    m2), so a match's share of its line is counted in the line's own characters, not the folded ones. The line
    is composed (NFC) before it is folded character by character: folding one code point at a time could never
    join a letter and the combining accent after it, so an OCR'd decomposed e-acute missed a typed composed one."""
    out, owner, n = [], [], 0
    for c in unicodedata.normalize("NFC", str(s)):          # compose first: e + U+0301 is one é, as typed
        if c.isspace():
            continue
        f = "".join(unicodedata.normalize("NFKC", c).casefold().split())
        out.append(f)
        owner += [n] * len(f)
        n += 1
    return "".join(out), owner, n


def _norm(s):
    return _norm_map(s)[0]


def find_text(lines, text, nth=None):
    """{"x", "y", "box"} (image fractions) of the nth place `text` appears. A match inside a longer line takes
    its share of the line's width."""
    if nth is not None and (isinstance(nth, bool) or not isinstance(nth, int) or nth < 1):
        raise ds.DeviceScriptError(["`nth` must be a whole number from 1 (the top-most place), not %r" % (nth,)])
    key = _norm(text)
    hits = []
    for ln in lines:
        t, owner, n = _norm_map(ln["text"])
        at = t.find(key)
        while key and at >= 0:
            x0, y0, x1, y1 = ln["box"]
            a, b = owner[at] / float(n), (owner[at + len(key) - 1] + 1) / float(n)
            hits.append([x0 + (x1 - x0) * a, y0, x0 + (x1 - x0) * b, y1])
            at = t.find(key, at + 1)
    hits.sort(key=lambda b: (round(b[1], 3), b[0]))
    if not hits:
        seen = ", ".join(repr(l["text"]) for l in lines[:12]) or "nothing"
        raise ds.DeviceScriptError(["%r not found in the screenshot — it shows %s" % (text, seen)])
    if nth is None and len(hits) > 1:
        raise ds.DeviceScriptError(["%r appears in %d places — say which with `nth` (1 = top-most, then left-most)"
                                    % (text, len(hits))])
    k = (nth or 1) - 1
    if k >= len(hits):
        raise ds.DeviceScriptError(["%r appears %d time(s); `nth` %d does not exist" % (text, len(hits), nth)])
    b = hits[k]
    return {"x": (b[0] + b[2]) / 2.0, "y": (b[1] + b[3]) / 2.0, "box": b}
