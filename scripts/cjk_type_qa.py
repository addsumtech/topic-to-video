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
    (r"^(kicker|meta|unit|issue|sectionLabel|wordmark|colophon|doneLabel|tag|cmd|root|hub|time|date|"
     r"hash|ref|status|filename|glyph|kind|side)$", _SHORT),
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
        if prop in ("accent", "accent2", "imageAspect", "aspect", "dna") or re.match(r"^src[A-Z]?", prop):
            # colours / images / plumbing, not copy. The `src` test is a PREFIX: KSpaceAnatomy declares
            # srcK / srcLow / srcHigh, an exact-match skip fed all three a Chinese sentence as a URL, and
            # the register reported as a RENDER FAILURE for it. evidence_props() fills them properly.
            continue
        if t.startswith("string[][]"):
            # a TABLE, and it must be routed BEFORE the plain string[] rule that startswith() also matches:
            # TermTable took a flat list, threw `(r ?? []).map is not a function`, and reported as a RENDER
            # FAILURE — a fixture bug wearing a register's name.
            props[prop] = _ARRAY_SHAPES.get(prop, [list(_ITEMS[:2]), list(_ITEMS[2:4])])
        elif t.startswith("string[]") or t.startswith("(string|"):
            props[prop] = list(_ITEMS[:4])
        elif t.startswith("string"):
            props[prop] = _string_for(prop)
        elif t.startswith("boolean"):
            continue
        elif t.startswith("number") or t.startswith("number|null"):
            continue
        elif "[]" in t:
            shaped = _shape_from_type(prop, ty, src) or _shape_array(prop, ty)
            if shaped is None:
                untestable.append(prop)
            else:
                props[prop] = shaped
        elif prop in _ARRAY_SHAPES:
            props[prop] = _ARRAY_SHAPES[prop]            # an OBJECT-shaped prop (a side, a group, a range)
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
    # ── the object shapes the first sweep could not feed. 14 registers reported UNTESTED, which the gate's
    # own doctrine calls the place this defect hides — a register nobody can feed is never checked. Each
    # shape is written from the register's own type declaration, because a WRONG shape renders nothing and
    # would read as "this register is fine in Chinese".
    "data": [{"label": "自动拆解任务", "value": 62, "delay": 0}, {"label": "规划执行步骤", "value": 48, "delay": 0.1},
             {"label": "交付可验收成果", "value": 81, "delay": 0.2}],
    "lines": [{"text": "读取授权目录里的表格", "kind": "run"}, {"text": "按类型分类归档", "kind": "ok"},
              {"text": "交付可验收的成果", "kind": "info"}],
    "left": {"label": "传统 AI 对话", "points": ["只能对话，提供建议", "输出文字回复", "单步骤简单任务"],
             "head": "传统 AI 对话", "body": "只能对话，提供建议，输出的是文字回复", "hero": False},
    "right": {"label": "WorkBuddy", "points": ["能够实际执行任务", "交付可验收的结果", "多步骤复杂任务"],
              "head": "WorkBuddy", "body": "能够实际执行任务，交付可验收的结果", "hero": True},
    "entries": [{"date": "第一步", "title": "自动拆解任务", "note": "把一句话拆成可执行的步骤"},
                {"date": "第二步", "title": "调用工具执行", "note": "在授权目录里真正动文件"}],
    "gauges": [{"label": "自动拆解任务", "fill": 0.72}, {"label": "规划执行步骤", "fill": 0.55}],
    "items": list(_ITEMS[:4]),
    "fail": {"label": "只回答问题", "note": "产出停在文字上", "a": None, "b": None},
    "pass": {"label": "交付成果", "note": "产出落进文件里", "a": None, "b": None},
    "domain": [0, 100],
    "tiles": [{"label": "自动拆解任务", "note": "把一句话拆开"}, {"label": "调用工具执行", "note": "在授权目录里"},
              {"label": "交付可验收成果", "note": "产出是文件"}],
    "xAxis": ["只回答", "真执行"],
    "yAxis": ["单步骤", "多步骤"],
    "states": [{"label": "只回答问题", "w": 0.4, "h": 0.35, "note": "产出停在文字"},
               {"label": "交付可验收成果", "w": 0.8, "h": 0.7, "note": "产出落进文件"}],
    "shared": {"label": "两者都会的", "a": "理解自然语言", "b": "生成文字内容", "note": "这一半不是分界线"},
    "independent": {"label": "只有它会的", "a": "在授权目录里动文件", "b": "交付可验收的成果",
                    "note": "这一半才是"},
    "phases": [{"at": 0.15, "label": "听懂一句话"}, {"at": 0.45, "label": "拆解并规划"},
               {"at": 0.78, "label": "交付可验收成果"}],
    "commits": [{"hash": "a1b2c3d", "ref": "主线", "msg": "自动拆解任务并规划步骤"},
                {"hash": "e4f5a6b", "ref": "", "msg": "在授权目录里读写文件"}],
}


# A number that is plainly a 0..1 fraction gets one; anything else gets a small count. No figure this gate
# invents ever reaches a film — these props exist only to make the register DRAW so its type can be measured.
def _synth_field(name, ty):
    t = ty.replace(" ", "").rstrip(";")
    if t.startswith("string"):
        return _string_for(name)
    if t.startswith("number"):
        # a 0..1 field given a 3 breaks the animation it drives (a `delay` of 3 puts the row off the clip),
        # and a magnitude given a 0.62 draws nothing. Name decides which, since the type cannot.
        if re.search(r"^(at|delay|start|end|fill|frac|ratio|opacity|w|h|x|y|progress)$", name, re.I):
            return 0.45
        return 62
    if t.startswith("boolean"):
        return name in ("find", "hero", "done", "ok")
    m = re.match(r"^'([^']+)'", t)                       # a string-literal union: take the first member
    return m.group(1) if m else _string_for(name)


def _alias_fields(src, alias):
    """{field: type} for `type Alias = {a?: string; b?: number}` declared in the register's own source."""
    m = re.search(r"(?:export\s+)?type\s+%s\s*=\s*\{(.*?)\}\s*;" % re.escape(alias), src, re.S)
    if not m:
        return None
    out = {}
    for chunk in m.group(1).split(";"):
        f = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\??\s*:\s*(.+)", chunk.replace("\n", " "), re.S)
        if f:
            out[f.group(1)] = f.group(2).strip()
    return out or None


def _shape_from_type(prop, ty, src, n=3):
    """Build the array a register actually declares, FROM ITS OWN TYPE.

    The first version of this file kept a table keyed by prop NAME, and that is wrong in a way that hides
    the defect it exists to find: `items` is declared by many registers with different element shapes, so a
    list of strings handed to TermTree (whose items are {name, note, tag}) renders EMPTY ROWS without
    throwing — 0.67% ink — and the gate reported the register clean. That is the same lie as measuring an
    empty plate. Reading the alias means a new register is fed correctly the day it is written.
    """
    t = ty.replace(" ", "")
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)\[\]$", t)                       # Item[]
    if m:
        fields = _alias_fields(src, m.group(1))
        if fields:
            return [{k: _synth_field(k, v) for k, v in fields.items()} for _ in range(n)]
        return None
    m = re.match(r"^\{(.+)\}\[\]$", t)                                      # an INLINE object array
    if m:
        fields = {}
        for chunk in m.group(1).split(";"):
            f = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\??:(.+)", chunk)
            if f:
                fields[f.group(1)] = f.group(2)
        if fields:
            return [{k: _synth_field(k, v) for k, v in fields.items()} for _ in range(n)]
    return None


def _shape_array(prop, ty):
    t = ty.replace(" ", "")
    if prop == "items" and t.startswith("[string,string,string]"):
        return list(_ITEMS[:3])                          # a fixed-arity tuple, not an open list
    if prop == "lines" and "Tok" in ty:
        return ["读取授权目录里的表格", "按类型分类归档", "交付可验收的成果"]   # (Tok[] | string)[]
    if prop in _ARRAY_SHAPES:
        return _ARRAY_SHAPES[prop]
    if prop == "rows" and "string[]" in ty.replace(" ", ""):
        return list(_ITEMS[:3])
    return None


def subset_coverage(text):
    """[(char, codepoint)] for characters the BUNDLED CJK faces cannot draw — they would render as tofu.

    The faces are subset to GB2312's 6763 Han plus kana, punctuation and Latin (10.05MB -> 2.20MB and
    14.10MB -> 3.05MB), which is every character normal Chinese prose uses and not every character that
    exists. A rare surname, a classical form or a Japanese kana would be a HOLE in the frame that no
    other gate looks at — a blank box beside correct type reads as a rendering bug, not as missing copy.
    So it is asked of the font file itself rather than assumed from the subset list.
    """
    faces = [os.path.join(_ROOT, "assets", "fonts", f)
             for f in ("NotoSansSC-Subset.ttf", "NotoSerifSC-Subset.ttf")]
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        return None                                      # no measurement is not a verdict
    covered = set()
    for f in faces:
        if os.path.exists(f):
            covered |= set(TTFont(f, lazy=True).getBestCmap())
    if not covered:
        return None
    out, seen = [], set()
    for ch in str(text or ""):
        cp = ord(ch)
        if cp < 0x2E80 or ch in seen:                    # Latin/digits are covered by the Latin faces
            continue
        seen.add(ch)
        if cp not in covered:
            out.append((ch, cp))
    return out


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


# An ABSOLUTE ink floor cannot separate these classes and the first version's 2% proved it: a wrong-fed
# TermTree measured 0.67%, but a correctly-fed TermLog is 2.65% and EdTimeline 3.84% — a log and a timeline
# are legitimately sparse, and the honest margin between "sparse" and "empty" is too narrow to name. So the
# comparison is RELATIVE: re-render the same register with its OWN defaults and compare. A fixture that
# reached the register draws about as much as its demo copy does; one that did not draws a fraction of it.
SUSPECT_INK = 0.05          # below this, ask the second question — above it, nothing was missed
# ...and this much less ink than its own defaults means the fixture never landed. MEASURED on TermTree, the
# register that exposed the hole, at the same frame and DNA:
#     correct fixture 6.14%   wrong-shaped fixture 0.63%   its own defaults 1.39%
#     -> correct = 4.42x defaults,  wrong = 0.45x defaults
# The first threshold was 0.45 and sat exactly ON the wrong case, so the negative control still reported
# clean. 0.75 separates them with margin on both sides. A correctly-fed register draws roughly what its demo
# copy draws or more — CJK glyphs are wider than the short English samples the library ships with.
UNFED_RATIO = 0.75


def _ink_fraction(png):
    try:
        from PIL import Image
        import numpy as np
        a = np.asarray(Image.open(png).convert("L"), dtype=float)
        return float((np.abs(a - np.median(a)) > 25).mean())
    except Exception:                                    # noqa: BLE001 — no measurement is not a verdict
        return 1.0


def _default_ink(shot, frame, tmp, dna, aspect):
    """The same register at the same frame with ITS OWN default props — the yardstick for 'did the fixture
    reach it'. Rendered only when a probe looks suspiciously empty, so it costs nothing on a healthy sweep."""
    pf = tmp + ".base.json"
    payload = {"dna": dna}
    if aspect:
        payload["aspect"] = aspect
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
    png = tmp + ".base.png"
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", shot, png, "--frame=%d" % frame,
                        "--gl=angle", "--log=error", "--props=" + os.path.abspath(pf),
                        "--public-dir=" + os.path.join(_REMOTION, "public")],
                       cwd=_REMOTION, capture_output=True, text=True)
    try:
        return _ink_fraction(png) if r.returncode == 0 and os.path.exists(png) else None
    finally:
        for f in (pf, png):
            if os.path.exists(f):
                os.remove(f)


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
                        "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + os.path.abspath(pf),
                        "--public-dir=" + os.path.join(_REMOTION, "public")],
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
    # A WRONG-SHAPED FIXTURE DOES NOT ALWAYS THROW. Handed a list of strings where it declares
    # {name, note, tag}, TermTree drew empty rows — 0.67% ink — and this gate called it clean. That is the
    # same lie as measuring an empty plate: nothing collided because nothing was drawn. So a probe that
    # renders almost nothing is reported as UNFED, never as a pass.
    got = _ink_fraction(tmp)
    if got < SUSPECT_INK:
        base = _default_ink(shot, frame, tmp, dna, aspect)
        if base is not None and base > 0 and got < base * UNFED_RATIO:
            return [{"kind": "unfed", "depth": 0,
                     "text": "(drew %.2f%% ink against %.2f%% on its own defaults — the fixture did not "
                             "reach this register)" % (got * 100, base * 100), "font": "", "cls": ""}]
    return []


def evidence_props():
    """{register: {prop: fixture}} — the registers that REFUSE to draw without a real photograph.

    Five reported as RENDER FAILURES in the first sweep, which is the same lie `register_energy` records
    about measuring an empty plate: the register is fine, the fixture was missing. Reuse that module's
    deterministic drawn stand-in rather than keeping a second copy of the idea.
    """
    try:
        import register_energy as reg
        reg.ensure_fixture()
        return reg.evidence_props()
    except Exception:                                    # noqa: BLE001 — no fixture is not a verdict
        return {}


def sweep(names, dna=DEFAULT_DNA, aspect=None, film_props=None):
    """{shot: {'hits': [...], 'untestable': [...], 'failed': bool}}"""
    durs = durations()
    ev = evidence_props()
    out = {}
    tmp = os.path.join(_REMOTION, ".cjk_type_probe.png")
    for n in names:
        props, untestable = (film_props.get(n), []) if film_props else cjk_props(n)
        if props is None:
            props, untestable = cjk_props(n)
        if n in ev:
            props = dict(props, **ev[n])                 # a plate register needs its picture to draw at all
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


def unfed_control():
    """The guard that catches a fixture which never reached its register — proved on a REAL wrong shape.

    It regressed once already: the first threshold landed exactly on the measured wrong case and the control
    reported clean. Handing TermTree a list of strings where it declares {name, note, tag} is the actual bug
    that shipped, so that is what this replays."""
    wrong = {"cmd": _SHORT, "root": _SHORT, "items": list(_ITEMS[:3])}
    tmp = os.path.join(_REMOTION, ".cjk_type_probe.png")
    hit = audit("TermTree", wrong, 145, tmp) or []
    right, _ = cjk_props("TermTree")
    ok = audit("TermTree", right, 145, tmp) or []
    for f in (tmp, tmp + ".props.json"):
        if os.path.exists(f):
            os.remove(f)
    caught = any(h["kind"] == "unfed" for h in hit)
    clean = not any(h["kind"] == "unfed" for h in ok)
    print("   wrong-shaped fixture  %s" % ("reported UNFED" if caught else "reported clean   <- NOT CAUGHT"))
    print("   correct fixture       %s" % ("clean" if clean else "reported UNFED   <- FALSE POSITIVE"))
    return caught and clean


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
    print("[cjk_type] CONTROLS — and the guard for a fixture that never reaches its register:")
    fed = unfed_control()
    ok = all(bad[n] for n in CONTROLS_BAD) and not any(good[n] for n in CONTROLS_GOOD) and fed
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
    unfed = {n: v for n, v in res.items() if any(h["kind"] == "unfed" for h in v["hits"])}
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
        if unfed:
            print("\nDREW ALMOST NOTHING — the fixture did not reach these registers, so a clean result here "
                  "would\n  be a measurement of an empty frame, not of the register:\n    %s"
                  % ", ".join(sorted(unfed)[:16]))
        if failed:
            print("\nFAILED TO RENDER: %s" % ", ".join(sorted(failed)[:14]))
        if not lead:
            print("\nNo register sets Chinese copy into itself.")
    return 1 if (lead or unfed) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
