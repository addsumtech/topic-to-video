#!/usr/bin/env python3
"""Does this register's TYPE still hold together when the copy is Chinese? — asked of the DOM.

    python3 scripts/cjk_type_qa.py --library            # sweep every register with CJK copy
    python3 scripts/cjk_type_qa.py <out_dir>            # this film's beats, with their real copy
    python3 scripts/cjk_type_qa.py --only Shot1,Shot2   # a few registers
    python3 scripts/cjk_type_qa.py --library --json

WHY THIS EXISTS. In one evening, on one real Chinese film, three registers set their copy into an
unreadable pile and every gate was green:

    BrutalistType      two title blocks laid on top of each other; the statements ran through them
    MagazineSpread     a headline wrapped to three lines at a leading that put line 2 inside line 1,
                       with the standfirst buried underneath

A THIRD was blamed and was innocent, which is why the controls below exist. `KineticManifesto` was
condemned off one still — blurred, oversized, running off both edges — and swapped out of the film. It is
a Z-axis flythrough: each phrase approaches, holds sharp at reading size, then rushes past at 1.9x under a
26px motion blur. The probe frame (0.88 of the clip) lands inside that departure by construction. Judging
a moving register by one frame is how a correct register gets replaced, and this gate would have repeated
the mistake if its controls had not disagreed with the person who wrote them.

`text_safe_qa` passed all three, and it was right to: nothing was CUT OFF. The copy sat inside the frame
and was still unreadable. That is a different defect and it has one cause — the library is authored with
short English demo strings. 58 of the 152 registers carry Latin sample copy, and a face set at
`line-height: 0.85` is confident Latin display typography and a collision in Chinese, because Latin glyphs
sit well inside their em box and CJK glyphs fill it. Nothing in the pipeline had ever rendered these
registers with Chinese text.

WHAT IT MEASURES, and how sure each answer is:

  leading   ONE element's own wrapped lines overlap each other. Never intentional — nobody sets a
            paragraph to collide with itself — so this is an ERROR.
  overlap   TWO different elements' type overlaps. Sometimes the technique (a brutalist stack, a glitch's
            offset copies), so this is reported for a human to look at, never as a failure.
A THIRD FINDING WAS ATTEMPTED IN THE DOM AND WITHDRAWN, which is worth recording. "Does the DECLARED face
actually draw this text" cannot be asked of `document.fonts.check()` — it answers "are the fonts needed to
render this loaded", counting fallbacks, and returned true for Chinese set in Space Grotesk. Measuring the
string against a sentinel stack instead false-positived on every monospace face (a `$` is the same width in
JetBrains Mono and in the generic monospace) and still missed the case it was built for. The question is
answered exactly and statically by `bundled_cjk_coverage()` below — read the font files, not the layout.

THE COPY IT USES. Real registers take real props, so a fixture is generated per register from its own
declared prop signature: a `kicker` gets a short label, a `tagline` gets a sentence, an `items` array gets
list entries — Chinese throughout, at the lengths a real film actually writes. A register whose props this
cannot shape keeps its own defaults and is reported as UNTESTED rather than silently passed, because a
register nobody could feed is exactly where this defect hides.

THE INSTRUMENT IS CONTROLLED BEFORE IT IS BELIEVED. `--controls` renders a synthetic frame that is
deliberately mis-set (`TypeCollisionProbe`: Chinese copy at 0.55 leading) and must catch it, plus six real
registers it must NOT flag — including the two repaired above, so a regression in either shows up here. A
gate that has not been shown to separate its classes is a gate that teaches people to ignore it.

ONE MORE FALSE POSITIVE IS WORTH RECORDING, because it nearly shipped. `getClientRects()` returns one rect
per FONT RUN, not per line, and a mixed CJK+Latin string is at least two runs sharing a baseline in two
different faces. Compared raw, a folio reading `交付可验收的成果.CO — 01` — visibly one clean line — was
reported as a 31px collision. Runs are grouped into lines first.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

_ROOT = os.path.dirname(_HERE)
_REMOTION = os.path.join(_ROOT, "remotion")
_SHOTS = os.path.join(_REMOTION, "src", "shots")
TAG = "TYPE-COLLISIONS "
DEFAULT_DNA = "product"

# The copy, by the ROLE a prop name announces. Lengths are what a real film writes, not minimums: the
# defect only appears once a line has to WRAP, so a tagline that fits on one line would test nothing.
_SHORT = "交付物"
_LABEL = "自主循环"
_TITLE = "交付可验收的成果"
_LONG = "它自主拆解任务、在你授权的目录里真正动文件，并把重复动作沉淀成可复用的技能"
_MED = "办公的产物本身就是文件，不是一段还要你二次加工的文字"
_ITEMS = ["自动拆解任务", "规划执行步骤", "调用工具执行", "交付可验收成果", "沉淀为可复用技能"]

_ROLE = [
    (r"^(kicker|meta|unit|issue|sectionLabel|wordmark|colophon|doneLabel|tag|cmd|root|hub|time)$", _SHORT),
    (r"^(label|heading|focalLabel|titleTop|titleBottom|word|value|query)$", _LABEL),
    (r"^(title|hero|headline|name)$", _TITLE),
    (r"^(tagline|caption|deck|answer|note|callout|heroNote|statement1|statement2|pitch|body)$", _LONG),
]


def _string_for(prop):
    for pat, val in _ROLE:
        if re.match(pat, prop):
            return val
    return _MED


def prop_signature(name):
    """{prop: type-text} straight from the register's own React.FC<{…}> declaration."""
    try:
        src = open(os.path.join(_SHOTS, name + ".tsx"), encoding="utf-8").read()
    except OSError:
        return {}, ""
    m = re.search(r"export const %s: React\.FC<\{(.*?)\}>\s*=" % re.escape(name), src, re.S)
    if not m:
        return {}, src
    body, out, depth, cur = m.group(1), {}, 0, ""
    for ch in body:                                    # split on top-level ';' only (nested {} survive)
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        if ch == ";" and depth == 0:
            out.update(_one_prop(cur)); cur = ""
        else:
            cur += ch
    out.update(_one_prop(cur))
    return out, src


def _one_prop(chunk):
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\??\s*:\s*(.+)", chunk.replace("\n", " "), re.S)
    return {m.group(1): m.group(2).strip()} if m else {}


def cjk_props(name):
    """(props, untestable) — CJK copy shaped to this register's own signature."""
    sig, src = prop_signature(name)
    props, untestable = {}, []
    for prop, ty in sig.items():
        t = ty.replace(" ", "")
        if prop in ("accent", "accent2", "src", "imageAspect", "aspect", "dna"):
            continue                                   # colours / images / plumbing, not copy
        if t.startswith("string[]") or t.startswith("(string|"):
            props[prop] = list(_ITEMS[:4])
        elif t.startswith("string"):
            props[prop] = _string_for(prop)
        elif t.startswith("boolean"):
            continue
        elif t.startswith("number") or t.startswith("number|null"):
            continue
        elif "[]" in t:
            shaped = _shape_array(prop, ty)
            if shaped is None:
                untestable.append(prop)
            else:
                props[prop] = shaped
        else:
            untestable.append(prop)
    return props, untestable


# The object-shaped array props the library actually declares. Each is written out rather than inferred,
# because a wrong SHAPE renders nothing and would read as "this register is fine in Chinese".
_ARRAY_SHAPES = {
    "messages": [{"side": "you", "text": "帮我把这周的工作写成一份周报", "at": 0.1},
                 {"side": "wb", "text": "好的，我先拆解任务并规划步骤，再动你的文件", "at": 0.45}],
    "nodes": [{"time": "一句话", "label": "下达任务"}, {"time": "自动", "label": "拆解规划"},
              {"time": "交付", "label": "可验收成果"}],
    "panels": [{"label": "自动拆解任务"}, {"label": "规划执行步骤"}, {"label": "调用工具执行"},
               {"label": "交付可验收成果"}],
    "items": list(_ITEMS[:4]),
    "layers": [{"label": "知识库", "depth": "独立隔离"}, {"label": "数据库", "depth": "独立隔离"},
               {"label": "运行环境", "depth": "独享", "find": True}],
    "sources": [{"t": "执行计划", "d": "待确认"}, {"t": "授权目录", "d": "未改动"}],
    "rows": [["自动拆解任务", "规划执行步骤"], ["调用工具执行", "交付可验收成果"]],
    "headers": ["它做什么", "产出是什么"],
    "marks": [],
}


def _shape_array(prop, ty):
    if prop in _ARRAY_SHAPES:
        return _ARRAY_SHAPES[prop]
    if prop == "rows" and "string[]" in ty.replace(" ", ""):
        return list(_ITEMS[:3])
    return None


def bundled_cjk_coverage():
    """[(face, has_cjk)] — can any face the renderer BUNDLES draw Chinese at all?

    This is the static half of the CJK floor, and it is the bigger half. `remotion/src/runtime/fonts.ts`
    exists because the tier "used to load NOTHING: every family named in a DNA was a bare CSS family name
    resolved against whatever the render host had installed... output therefore varied by machine — a
    determinism defect on a tier that otherwise pins seeds and hashes clips." That was fixed for Latin and
    left exactly as it was for CJK: none of the bundled faces carries a single Han glyph, so every Chinese
    character in every film is drawn by whatever the machine happens to have.

    MEASURED CONSEQUENCE, on one register and two DNAs whose display faces are as different as the library
    holds (editorial = Playfair Display, a didone serif; product = Space Grotesk, a geometric sans):

        the same title in English    1480px wide vs 1573px      — 93px apart, the face is doing its job
        the same title in Chinese    1383px wide vs 1383px      —  0px apart, the same fallback drew both

    So on a CJK film the Design DNA's TYPOGRAPHY — the first token it declares, and by its own documentation
    the strongest style signal it has — does nothing at all. Every direction renders Chinese identically.
    """
    import glob as _g
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None
    probe = (0x4E00, 0x6587, 0x4EF6, 0x81EA, 0x5FAA)      # 一 文 件 自 循
    out = []
    for f in sorted(_g.glob(os.path.join(_ROOT, "assets", "fonts", "*.ttf")) +
                    _g.glob(os.path.join(_ROOT, "assets", "fonts", "*.otf"))):
        try:
            cmap = TTFont(f, lazy=True).getBestCmap()
            out.append((os.path.basename(f), all(cp in cmap for cp in probe)))
        except Exception:                                 # noqa: BLE001 — an unreadable face is not a verdict
            continue
    return out


def durations():
    out = {}
    for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx"))):
        m = re.search(r"export const DURATION\s*=\s*(\d+)", open(f, encoding="utf-8").read())
        if m:
            out[os.path.basename(f)[:-4]] = int(m.group(1))
    return out


def audit(shot, props, frame, tmp, dna=DEFAULT_DNA, aspect=None):
    """[] clean · [collision…] · None when the render itself failed."""
    payload = dict(props)
    payload["typeCollisions"] = True
    payload["dna"] = dna
    if aspect:
        payload["aspect"] = aspect
    pf = tmp + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, allow_nan=False)
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", shot, tmp,
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + os.path.abspath(pf)],
                       cwd=_REMOTION, capture_output=True, text=True)
    err = (r.stderr or "") + (r.stdout or "")
    if TAG in err:
        raw = err.split(TAG, 1)[1]
        try:
            found, _ = json.JSONDecoder().raw_decode(raw)
            return found
        except json.JSONDecodeError:
            return [{"kind": "leading", "depth": 0, "text": "(unparseable payload)", "font": "", "cls": ""}]
    if r.returncode != 0:
        return None
    return []


def sweep(names, dna=DEFAULT_DNA, aspect=None, film_props=None):
    """{shot: {'hits': [...], 'untestable': [...], 'failed': bool}}"""
    durs = durations()
    out = {}
    tmp = os.path.join(_REMOTION, ".cjk_type_probe.png")
    for n in names:
        props, untestable = (film_props.get(n), []) if film_props else cjk_props(n)
        if props is None:
            props, untestable = cjk_props(n)
        frame = int(durs.get(n, 150) * 0.88)
        hits = audit(n, props, frame, tmp, dna, aspect)
        out[n] = {"hits": hits or [], "untestable": untestable, "failed": hits is None}
    for p in (tmp, tmp + ".props.json"):
        if os.path.exists(p):
            os.remove(p)
    return out


# The POSITIVE control is synthetic and permanent (`TypeCollisionProbe` in remotion/src/Root.tsx: Chinese
# copy at 0.55 leading). The first version used the two real registers that had broken a real film, and it
# worked exactly once — the moment both were repaired the controls reported "not caught" and the instrument
# could no longer show it detects anything. A control that needs production code to STAY broken is not one.
CONTROLS_BAD = ["TypeCollisionProbe"]
# KineticManifesto is deliberately here on the GOOD side — see the header. It reports clean and that is the
# right answer; it was a mis-diagnosis off a single mid-flythrough frame.
CONTROLS_GOOD = ["CinematicTitle", "TermTable", "QuadSplit", "KineticManifesto",
                 "MagazineSpread", "BrutalistType"]


def controls():
    """Prove the instrument separates the classes before anyone believes a sweep."""
    res = sweep(CONTROLS_BAD + CONTROLS_GOOD)
    bad = {n: [h for h in res[n]["hits"] if h["kind"] == "leading"] for n in CONTROLS_BAD}
    good = {n: [h for h in res[n]["hits"] if h["kind"] == "leading"] for n in CONTROLS_GOOD}
    print("[cjk_type] CONTROLS — a synthetic mis-set frame it must catch, and registers it must not flag:")
    for n in CONTROLS_BAD:
        print("   known-BAD  %-18s %d leading collision(s)%s"
              % (n, len(bad[n]), "" if bad[n] else "   <- NOT CAUGHT"))
    for n in CONTROLS_GOOD:
        print("   known-GOOD %-18s %d leading collision(s)%s"
              % (n, len(good[n]), "   <- FALSE POSITIVE" if good[n] else ""))
    ok = all(bad[n] for n in CONTROLS_BAD) and not any(good[n] for n in CONTROLS_GOOD)
    print("[cjk_type] controls %s" % ("PASS — the instrument separates them" if ok else "FAIL — do not trust a sweep yet"))
    return 0 if ok else 1


def main(argv):
    ap = argparse.ArgumentParser(description="Does the type hold together in Chinese?")
    ap.add_argument("out_dir", nargs="?")
    ap.add_argument("--library", action="store_true")
    ap.add_argument("--only", default="")
    ap.add_argument("--controls", action="store_true")
    ap.add_argument("--dna", default=DEFAULT_DNA)
    ap.add_argument("--aspect", default=None)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.controls:
        return controls()
    film_props = None
    if a.only:
        names = [x.strip() for x in a.only.split(",") if x.strip()]
    elif a.out_dir:
        board = json.load(open(os.path.join(a.out_dir, "storyboard.json"), encoding="utf-8"))
        names, film_props = [], {}
        for s in board.get("slides", []):
            if s.get("shot"):
                names.append(s["shot"]); film_props[s["shot"]] = s.get("shot_props") or {}
        a.aspect = a.aspect or (board.get("meta") or {}).get("aspect")
        names = sorted(set(names))
    else:
        names = sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(_SHOTS, "*.tsx")))
    res = sweep(names, a.dna, a.aspect, film_props)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=2))
    lead = {n: [h for h in v["hits"] if h["kind"] == "leading"] for n, v in res.items()}
    lead = {n: h for n, h in lead.items() if h}
    over = {n: [h for h in v["hits"] if h["kind"] == "overlap"] for n, v in res.items()}
    over = {n: h for n, h in over.items() if h}
    failed = [n for n, v in res.items() if v["failed"]]
    untest = {n: v["untestable"] for n, v in res.items() if v["untestable"]}
    if not a.json:
        cov = bundled_cjk_coverage()
        if cov is not None and not any(has for _, has in cov):
            print("[cjk_type] NONE of the %d bundled faces can draw Chinese — every CJK glyph in every film "
                  "is\n           set by whatever font the render machine has installed, so the Design DNA's "
                  "typography\n           does nothing on a CJK film (measured: 0px apart across two DNAs; "
                  "93px in English).\n           Bundle a CJK face in assets/fonts + runtime/fonts.ts to fix "
                  "it." % len(cov))
        print("[cjk_type] %d register(s) rendered with Chinese copy" % (len(res) - len(failed)))
        if lead:
            print("\nLINES COLLIDING WITH THEMSELVES — a wrapped Chinese line set at a Latin leading:")
            for n in sorted(lead, key=lambda k: -max(h["depth"] for h in lead[k])):
                h = max(lead[n], key=lambda x: x["depth"])
                print("    %-22s %3dpx deep  %s  «%s»" % (n, h["depth"], h["font"], h["text"]))
        if over:
            print("\nTYPE OVERLAPPING OTHER TYPE (a candidate — some registers stack type on purpose):")
            for n in sorted(over, key=lambda k: -len(over[k]))[:14]:
                h = over[n][0]
                print("    %-22s %d pair(s)  «%s» × «%s»" % (n, len(over[n]), h["text"], h.get("other", "")))
        if untest:
            print("\nNOT TESTED — no CJK copy could be shaped for these props (add the shape to _ARRAY_SHAPES):")
            for n in sorted(untest)[:14]:
                print("    %-22s %s" % (n, ", ".join(untest[n])))
        if failed:
            print("\nFAILED TO RENDER: %s" % ", ".join(sorted(failed)[:14]))
        if not lead:
            print("\nNo register sets Chinese copy into itself.")
    return 1 if lead else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
