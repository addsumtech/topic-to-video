#!/usr/bin/env python3
"""Does this register's TYPE still hold together when the copy is Chinese? — asked of the DOM.

    python3 scripts/cjk_type_qa.py --library            # sweep every register with CJK copy
    python3 scripts/cjk_type_qa.py <out_dir>            # this film's beats, with their real copy
    python3 scripts/cjk_type_qa.py --only Shot1,Shot2   # a few registers
    python3 scripts/cjk_type_qa.py --library --all-aspects   # ...at every aspect, not just 16:9
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

RUN IT SERIALLY. A library sweep is 153 browser renders and the obvious speed-up is to shard it across
processes. Measured: four concurrent shards reported FIVE registers as RENDER FAILURES that render fine on
their own, called TWELVE registers "drew almost nothing" that draw fine on their own — and MISSED findings
the serial re-run then reported (`TermBars` tight and orphaned, `FocalIsolation` orphaned). A starved render
produces a partial frame, and every measurement here is of a frame. So the concurrency does not just cost
accuracy at the margin; it moves findings in both directions, which is the one thing a gate may not do.

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

AND ONE THAT DID SHIP, WHICH IS WORSE. A client rect is AXIS-ALIGNED, so for type drawn on a TILT it is the
bounding box of a tilted line — taller than the line by `width·|sin θ|`. `CardStack3D` fans its cards ±13°,
and a card label whose three Chinese lines are visibly separate was reported on a delivered film as a 64px
collision; the same label in the same register with ONE card, where the fan angle is zero, reported clean.
The whole 64px was the tilt. Mutating the rotation guard out proves the instrument was wrong in BOTH
directions on tilted type — a well-set tilted block read as a 148px collision, and a deliberately mis-set
one read as clean, because consecutive tilted boxes overlap enough to be grouped into a single line. 27 of
the 153 registers rotate something. Rotated type is now measured with an instrument that has no orientation
at all (`metricLeading`: the font's own box height against the resolved `line-height`), and two permanent
synthetic probes — `TiltedTypeCollisionProbe` and `TiltedTypeCleanProbe` — hold it to both answers.

THE "DREW NOTHING" GUARD LEARNED THE SAME LESSON. Its first arbiter compared a suspicious frame's ink with
the register's own demo defaults, and it convicted the first legitimately sparse frame it met: a four-panel
`QuadSplit` on a warm-white product palette, 3% ink, all five of its strings plainly on screen. Ink is a
proxy; the DOM knows the answer. Low ink is still the cheap TRIGGER, but the verdict now comes from asking
the render which of the strings we fed actually reached the screen (`auditFedText`).
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
# LIST ENTRIES ARE THE LENGTH A REAL FILM WRITES, WHICH IS LONGER THAN A DEMO LABEL — and that is the
# whole precondition for the defect. At 6 characters these never wrapped in a card or a panel, so the
# sweep reported `CardStack3D` clean and the same register broke on a delivered film whose card read
# 「行业 Buddy 应用 · 更新日志 5.5.0」. Mixed lengths, because a real list has both.
_ITEMS = ["自动拆解任务", "规划执行步骤并调用工具", "在授权目录里真正动文件", "交付可验收的成果",
          "把重复动作沉淀成可复用技能"]

# One pool per length ROLE. The first entry of each is what a single-prop register gets, so it is the entry
# that has to be a real test — see the LABEL pool below for what happens when it is the shortest one.
_SHORT_V = [_SHORT, "自动归档", "按类型分流", "沉淀为技能"]
# A LABEL POOL WHOSE EVERY ENTRY IS THE SAME LENGTH TESTS ONE LENGTH. All four of these were exactly four
# glyphs, and this pool feeds `word`, `label`, `heading`, `focalLabel` — the DISPLAY props, the ones set at
# 130-260px. Four Han glyphs at 240px is 960px, which clears a 1080-wide frame by sixty, so the sweep proved
# 28 literal-display-type registers survive four glyphs and reported every one of them clean. Handed eight,
# InflateType sliced its word 450px on the left and ElasticType 412px each side (`5e08043`). It is the same
# lesson `_ITEMS` already carries one pool above: mixed lengths, because a real film writes both.
# ...AND THE FIRST ENTRY IS THE ONE THAT GETS TESTED. `word` is the first prop a display register declares,
# so it takes pool[0] and nothing else — lengthening the tail changed which strings the FOURTH scalar of a
# register sees and left the display props exactly where they were. Four glyphs is not a hard case for type
# set at 240px; six is a hero word a Chinese film actually writes, and it is longer than the four that hid
# `InflateType` and `ElasticType`. The rest of the pool runs longer still, for registers that take several.
# EVERY ENTRY IS A HARD CASE, not just the first. Varying by the prop's ordinal spreads the pool across the
# library, which is what stops sibling props being identical — but it also means a register's display prop
# gets whichever entry its POSITION happens to select, and `OdometerRoll.label` landed on the four-glyph one:
# the exact length that hid `InflateType` and `ElasticType`. A pool whose shortest member is soft tests some
# registers softly, at random. Six glyphs is a hero word a Chinese film actually writes; none is shorter.
_LABEL_V = ["自主循环运转", "持续稳定运行", "在授权目录动手", "自主循环持续运转"]
# THE SAME RULE AS THE LABEL POOL, AND THIS ONE STILL HAD A SOFT MEMBER: 26, 11, 11 and EIGHT glyphs. Eight
# is a label, in the pool that feeds `note`, `caption`, `tagline`, `answer`, `body` and every unnamed string
# — so whichever register's ordinal landed on it was tested with a caption a third the length of a real one,
# and a reserve sized for that passes. A pool is only as strong as its shortest member.
_MED_V = [_MED,
          "它自己拆解任务、调用工具、改动文件，最后交出可验收的结果",
          "同样的输入框，同样的一段回答，变的是谁在动手做完这件事",
          "重复三次以上的动作会被记下来，下一次不必再从头讲一遍"]
# TITLE had no pool of its own, so `_variant` fell through to searching every pool for the string by
# MEMBERSHIP — and `_TITLE` is also the fourth entry of `_MED_V`, so varying a title silently handed it a
# MED-length sentence. A role's variants belong to that role.
_TITLE_V = [_TITLE, "产物本身就是文件", "它自己动手交付", "把重复沉淀成技能"]
_LONG_V = [_LONG, "它读取你授权的目录，按类型分流并归档，最后交付一份可验收的成果",
           "重复三次以上的动作会被沉淀成技能，下一次不必再从头讲一遍"]

# Each role names its OWN pool. Keyed to a single string it needed `_variant` to find that string again by
# searching every pool, which is how a title came to be varied into a MED sentence.
# A ROLE IS MATCHED ON THE NAME'S TAIL, NOT ON THE WHOLE NAME. These were exact matches, so `label` took the
# label role and `underLabel`, `leftLabel`, `metricLabel` and twenty-four others fell through to the MED
# fallback and were handed a 26-glyph CAPTION. That is not a harder test, it is the wrong test: it measures
# a legend swatch against a sentence no film would put there, and `PlanPalimpsest` answered by growing its
# legend past the whole content zone. A prop whose name ends in `Label` is a label. The leading `[a-z]*` is
# what makes the tail match, and the roles stay in order so `doneLabel` and `sectionLabel` keep the SHORT
# role they are listed with rather than being re-read as labels.
_ROLE = [
    (r"^[a-z]*(kicker|meta|unit|issue|sectionLabel|wordmark|colophon|doneLabel|tag|cmd|root|hub|time|date|"
     r"hash|ref|status|filename|glyph|kind|side)$", _SHORT_V),
    # ...and the role word can lead as well as trail: `underLabel` and `labelLeft` are both labels.
    (r"^[a-z]*(label|heading|focalLabel|titleTop|titleBottom|word|value|query)$"
     r"|^(label|heading|word)[A-Z][a-zA-Z]*$", _LABEL_V),
    (r"^[a-z]*(title|hero|headline|name)$", _TITLE_V),
    (r"^[a-z]*(tagline|caption|deck|answer|note|callout|heroNote|statement1|statement2|pitch|body)$"
     r"|^(note|caption|answer|body)[A-Z][a-zA-Z]*$", _LONG_V),
]


# A READOUT IS A NUMBER, and copy is the wrong fixture for one. `VelocitySnap` hands its `metric` to the
# shared `Figure` atom, which sets numerals at 0.86-0.9 leading — correct for digits, and reported as tight
# Chinese the moment the fixture fed it a sentence. `TermCounter` simply drew nothing for a `value` it
# could not read as a number. Neither is a register defect; both are this file feeding prose to a dial.
# Detected from the register's own source rather than from a list of prop names, because `value` is real
# copy on some registers and a dial on others.
_READOUT = "88"


def _is_readout(prop, local, src):
    """Does this register read the prop as a NUMBER?

    The strongest signal is the register's own DEFAULT: `value = '100'` says the field is a dial, in the
    declaration, without pattern-matching a body that may reach the number three different ways
    (`parseFloat(String(value)...)`, `<Figure value={shown}`, `.toLocaleString()`).
    """
    if not src or not local:
        return False
    dflt = re.search(r"\b%s\s*(?::\s*[A-Za-z_$][\w$]*\s*)?=\s*'([^']*)'" % re.escape(prop), src)
    if dflt and re.fullmatch(r"[\d][\d.,%+\-\s]*", dflt.group(1).strip()):
        return True
    esc = re.escape(local)
    return bool(re.search(r"<Figure\b[^>]*\bvalue=\{%s\b" % esc, src, re.S)
                or re.search(r"\b(?:Number|parseFloat|parseInt)\([^)]*\b%s\b" % esc, src)
                or re.search(r"\b%s\s*\.\s*toLocaleString\(" % esc, src))


def _local_of(prop, src):
    """The identifier a prop BINDS to — `metric: METRIC = …` renders through METRIC, not through `metric`."""
    m = re.search(r"\b%s\s*:\s*([A-Za-z_$][\w$]*)" % re.escape(prop), src or "")
    return m.group(1) if m else prop


# ROW N GETS A DIFFERENT SENTENCE FROM ROW N-1.
#
# Every row of a synthesised object array used to carry the identical string, and that made a whole section
# of this report untrustworthy: `ProfileGrowth` stacks a label above each growth state, and three of them
# handed «自主循环» three times sit at the same x with adjacent heights, so the audit reported them
# overlapping each other. Rendered with three DIFFERENT labels — which is what any real film supplies — the
# composition is clean. The register was never wrong; the fixture was repeating itself and the instrument was
# reading the repetition as a collision.
#
def _string_for(prop, local=None, src="", i=0):
    if _is_readout(prop, local or prop, src):
        return _READOUT
    for pat, pool in _ROLE:
        if re.match(pat, prop, re.I):
            return pool[i % len(pool)]
    return _MED_V[i % len(_MED_V)]


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
    scalars = 0
    for prop, ty in sig.items():
        t = ty.replace(" ", "")
        # `page` selects WHICH page shape a surface draws (cards / chart / table / form) — plumbing, like
        # `aspect` and `dna`, not copy. Left off this list it was reported as untestable on every register
        # that takes one, which is a permanent line in the gate's output that means nothing.
        if prop in ("accent", "accent2", "imageAspect", "aspect", "dna", "page") or re.match(r"^src[A-Z]?", prop):
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
            # EVERY SIBLING SCALAR GOT THE SAME SENTENCE. `i` is the row index inside a shaped array, and
            # nothing passed one for a top-level prop, so each took its pool's first entry: `RackFocus`
            # declares before / after / beforeNote / afterNote / pivot and rendered ONE sentence five times.
            # A sweep cannot judge a multi-prop register that way — and it cannot tell a dropped string from
            # a duplicated one either, which is the same reason the ARRAY side was given row-varying copy.
            # The variants keep the ROLE, so a label stays label-length and a note stays note-length; only
            # the words differ, which is the one thing that must.
            props[prop] = _string_for(prop, _local_of(prop, src), src, scalars)
            scalars += 1
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
# A field whose type this cannot honour is OMITTED, never guessed at. `_synth_field` returns it.
_OMIT = object()

_UNION_CACHE = {}


def _named_union_member(alias, src):
    """The first member of `type Alias = 'a' | 'b' | …`, wherever that alias is declared.

    A field typed as a NAMED alias is not copy and must not be fed a sentence. QuadSplit's panels declare
    `icon?: IconName`, the shaper handed it a Chinese sentence, and the Icon registry threw — correctly, it
    is written to fail loud. The register then reported as a RENDER FAILURE, which the controls counted as
    a clean known-GOOD, so the sweep was quietly measuring 29 registers and calling it 30. Resolve the
    alias instead: the register's own source first, then the runtime it imports from.
    """
    if alias in _UNION_CACHE:
        return _UNION_CACHE[alias]
    pool = [src] if src else []
    pool += [open(f, encoding="utf-8").read()
             for f in sorted(glob.glob(os.path.join(_REMOTION, "src", "runtime", "*.ts*")))]
    got = None
    for text in pool:
        m = re.search(r"(?:export\s+)?type\s+%s\s*=\s*([^;]+);" % re.escape(alias), text, re.S)
        if not m:
            continue
        lit = re.search(r"'([^']+)'", m.group(1))
        if lit:
            got = lit.group(1)
            break
    _UNION_CACHE[alias] = got
    return got


def _synth_field(name, ty, src="", i=0):
    t = ty.replace(" ", "").rstrip(";")
    # A LIST FIELD IS TESTED BEFORE THE SCALAR IT IS SPELLED WITH. `"string[]".startswith("string")` is true,
    # so a `string[]` INSIDE an object row was filled with one sentence: `SurfaceCarousel`'s
    # `{label, page, items: string[]}` came back with `items` as a bare string, the register called
    # `.filter` on it, and the sweep printed "SurfaceCarousel FAILED TO RENDER" — a fixture bug wearing a
    # register's name, which is the whole thing this synthesiser exists to stop.
    if t.startswith("string[]"):
        return list(_ITEMS[:3])
    if t.startswith("number[]"):
        return [3, 5, 4, 8, 7, 11, 9, 14]
    if t.startswith("string"):
        return _string_for(name, name, src, i)
    if t.startswith("number"):
        # a 0..1 field given a 3 breaks the animation it drives (a `delay` of 3 puts the row off the clip),
        # and a magnitude given a 0.62 draws nothing. Name decides which, since the type cannot.
        #
        # AND IT VARIES BY ROW, for the same reason the STRINGS do. A flat 0.45 gave every row of a timeline
        # the same timestamp, so a register that shows one phase at a time — which is what a timeline IS —
        # correctly drew one, and the gate reported it as having dropped the other two: `VoiceSignal`,
        # "2 of 3 strings it was given never reached the screen", at every aspect, for as long as the
        # fixture has existed. That is the same defect the string side already carries a fix for (three
        # identical labels once produced spurious self-overlaps on ProfileGrowth), in the numeric field.
        # Spread across the clip's middle so no row sits at an endpoint, where a `seg` window is degenerate.
        if re.search(r"^(at|delay|start|end|progress)$", name, re.I):
            return round(0.18 + (i % 5) * 0.16, 3)
        if re.search(r"^(fill|frac|ratio|opacity|w|h|x|y)$", name, re.I):
            return round(0.34 + (i % 5) * 0.13, 3)
        return 62 + (i % 5) * 17
    if t.startswith("boolean"):
        return name in ("find", "hero", "done", "ok")
    m = re.match(r"^'([^']+)'", t)                       # an INLINE string-literal union: first member
    if m:
        return m.group(1)
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)(\|undefined)?$", t)
    if m:                                                # a NAMED type — resolve it, never invent copy
        member = _named_union_member(m.group(1), src)
        return member if member is not None else _OMIT
    return _string_for(name, name, src)


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


# A field that names a COLOUR is not copy, at any nesting depth. The top-level skip covered `accent` and
# `accent2`; a row's own `tone` sat below it, so `TermBars` was handed a Chinese sentence as the colour of
# every bar. Omitted, so the register keeps its own default.
_NON_COPY_FIELDS = re.compile(r"^(tone|color|colour|accent\d?|bg|background|ink|hue|fill|shade|stroke)$", re.I)
# ...and a DATA ROW's readout is a number. A row that also declares a numeric `pct` or `fill` is a measured
# row, so its `value` is the figure beside the bar — `TermBars` drew nothing for the word it was given.
_ROW_READOUT = re.compile(r"^(value|amount|metric|count|total|num)$", re.I)


def _shaped_row(fields, src, i=0):
    """One element of a shaped array, with every field this cannot honour left out rather than guessed."""
    measured = any(re.match(r"^(pct|fill|ratio|frac|percent)$", k, re.I)
                   and str(v).replace(" ", "").startswith("number") for k, v in fields.items())
    row = {}
    for k, v in fields.items():
        if _NON_COPY_FIELDS.match(k) and str(v).replace(" ", "").startswith("string"):
            continue
        if measured and _ROW_READOUT.match(k) and str(v).replace(" ", "").startswith("string"):
            row[k] = _READOUT
            continue
        val = _synth_field(k, v, src, i)
        if val is not _OMIT:
            row[k] = val
    return row


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
            return [_shaped_row(fields, src, i) for i in range(n)]
        return None
    m = re.match(r"^\{(.+)\}\[\]$", t)                                      # an INLINE object array
    if m:
        fields = {}
        for chunk in m.group(1).split(";"):
            f = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\??:(.+)", chunk)
            if f:
                fields[f.group(1)] = f.group(2)
        if fields:
            return [_shaped_row(fields, src, i) for i in range(n)]
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
# Han, kana, Hangul and CJK punctuation — the same set `runtime/cjkType.ts` tests for, so the gate and
# the registers cannot drift apart on what "is this Chinese" means.
_HAS_CJK = re.compile("[\u1100-\u11ff\u2e80-\u9fff\uac00-\ud7af\uf900-\ufaff\ufe30-\ufe4f\uff00-\uffef]")

SUSPECT_INK = 0.05          # below this, ask the second question — above it, nothing was missed
# ...and this much less ink than its own defaults means the fixture never landed. MEASURED on TermTree, the
# register that exposed the hole, at the same frame and DNA:
#     correct fixture 6.14%   wrong-shaped fixture 0.63%   its own defaults 1.39%
#     -> correct = 4.42x defaults,  wrong = 0.45x defaults
# The first threshold was 0.45 and sat exactly ON the wrong case, so the negative control still reported
# clean. 0.75 separates them with margin on both sides. A correctly-fed register draws roughly what its demo
# copy draws or more — CJK glyphs are wider than the short English samples the library ships with.
# Kept as the FALLBACK arbiter only — for a register this fixture could shape no CJK copy for, where there
# is nothing to look for in the DOM and the ink yardstick is all that is left.
UNFED_RATIO = 0.75
# HALF the copy gone means the register was not reached; a few strings gone means it dropped them.
UNFED_MISSING_FRAC = 0.5


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


FED_TAG = "FED-TEXT "

# A MEASUREMENT TAKEN WHILE THE INSTRUMENT IS BEING TAKEN APART IS NOT A MEASUREMENT. The load-bearing test
# for the rotation guard proves itself by MUTATING `runtime/textSafe.tsx` on disk for the length of two
# renders. A sweep running at the same time renders against whatever is in the file at that instant, so it
# would report numbers from the broken instrument and look exactly like a normal run. This happened. The
# mutator holds this sentinel; every render refuses while it is there, loudly, instead of returning a lie.
_MUTATING = os.path.join(_REMOTION, ".textsafe-mutating")


def _refuse_if_instrument_is_mutated():
    """The sentinel names the PID that OWNS the mutation, so the mutator's own two renders go through and
    every other process stops. A sentinel that simply existed would have to be dropped for those renders,
    which is the whole window it was meant to cover."""
    try:
        owner = open(_MUTATING, encoding="utf-8").read().strip()
    except OSError:
        return
    if owner != str(os.getpid()):
        raise RuntimeError(
            "remotion/src/runtime/textSafe.tsx is deliberately mutated right now — pid %s holds %s — so a "
            "render started here would measure the broken instrument and look like a normal run. Wait for "
            "that run to finish, or delete the sentinel if a crash left it behind."
            % (owner or "?", _MUTATING))


def _string_leaves(obj, out=None):
    """Every string anywhere in a props tree — the copy a register was actually handed."""
    if out is None:
        out = []
    if isinstance(obj, str):
        out.append(obj)
    elif isinstance(obj, dict):
        for v in obj.values():
            _string_leaves(v, out)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            _string_leaves(v, out)
    return out


def _fed_missing(shot, props, frame, tmp, dna, aspect, fed):
    """Which of `fed` never reached the DOM — asked of the render, not inferred from ink.

    Returns a list, or None when the question could not be put (the render failed). One extra render, and
    only when a frame already looks suspiciously empty."""
    pf = tmp + ".fed.json"
    payload = dict(props)
    payload["fedText"] = fed
    payload["dna"] = dna
    if aspect:
        payload["aspect"] = aspect
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, allow_nan=False)
    png = tmp + ".fed.png"
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", shot, png, "--frame=%d" % frame,
                        "--gl=angle", "--log=error", "--props=" + os.path.abspath(pf),
                        "--public-dir=" + os.path.join(_REMOTION, "public")],
                       cwd=_REMOTION, capture_output=True, text=True)
    for f in (pf, png):
        if os.path.exists(f):
            os.remove(f)
    err = (r.stderr or "") + (r.stdout or "")
    if FED_TAG not in err:
        return None
    try:
        return (json.JSONDecoder().raw_decode(err.split(FED_TAG, 1)[1])[0] or {}).get("missing")
    except json.JSONDecodeError:
        return None


def audit(shot, props, frame, tmp, dna=DEFAULT_DNA, aspect=None):
    """[] clean · [collision…] · None when the render itself failed."""
    _refuse_if_instrument_is_mutated()
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
    if got >= SUSPECT_INK:
        return []
    # LOW INK IS THE TRIGGER, NOT THE VERDICT. Comparing the ink against the register's own demo defaults
    # was the first arbiter and it convicted the first legitimately sparse frame it met: four `QuadSplit`
    # panels on a warm-white product palette, 3% ink, every one of its five strings plainly on screen. Ask
    # the DOM which of the strings we fed actually reached the screen — that is the question, exactly.
    fed = [x for x in _string_leaves(props) if _HAS_CJK.search(x)]
    if fed:
        missing = _fed_missing(shot, props, frame, tmp, dna, aspect, fed)
        if missing is None:
            return [{"kind": "unfed", "depth": 0, "font": "", "cls": "",
                     "text": "(drew %.2f%% ink and the re-render that would say whether its copy reached "
                             "the screen failed — nothing is known about this frame)" % (got * 100)}]
        if not missing:
            return []
        # HOW MUCH OF THE COPY VANISHED DECIDES WHAT THIS IS, and the first version made one claim for both.
        # A register that drew 9 of the 11 strings it was given HAS been reached — it capped a list, or a
        # panel is conditional on a prop the fixture cannot shape. Saying "the fixture did not reach this
        # register" of that frame is false, and it failed the gate for it. Saying nothing is worse: a
        # register that silently drops copy a film supplied is worth knowing about. So they are two
        # findings. Measured on the four the library actually has: KineticManifesto 2 of 4 at 0.00% ink
        # (its phrases have flown past the probe frame — nothing is on screen), against EdCompare 2 of 11,
        # TermCounter 1 of 4 and TermTable 1 of 10, which all drew.
        frac = len(missing) / float(len(fed))
        if frac >= UNFED_MISSING_FRAC:
            return [{"kind": "unfed", "depth": 0, "font": "", "cls": "",
                     "text": "(drew %.2f%% ink, and %d of %d strings it was given never reached the screen: "
                             "%s)" % (got * 100, len(missing), len(fed), " / ".join(missing[:3]))}]
        return [{"kind": "dropped", "depth": 0, "font": "", "cls": "",
                 "text": "(drew %.2f%% ink and dropped %d of %d strings: %s)"
                         % (got * 100, len(missing), len(fed), " / ".join(missing[:3]))}]
    # No CJK copy was fed at all (a register whose props this fixture could not shape), so fall back to the
    # ink yardstick — a comparison against its own defaults is all that is left to ask.
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
    tmp = os.path.join(_REMOTION, ".cjk_type_probe.%d.png" % os.getpid())
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
# {probe: the finding KIND it must produce}. Each is synthetic, permanent and paired below with a probe
# that differs in exactly one property and must come back clean — which is what makes a catch evidence
# rather than a coincidence.
CONTROLS_BAD = {"TypeCollisionProbe": "leading",          # Chinese at 0.55 leading
                "TiltedTypeCollisionProbe": "leading",    # the same, on a 13° tilt
                "OrphanLineProbe": "orphan",              # 15 characters in a box 7 wide: 7 / 7 / 1
                "TightLeadingProbe": "tight"}             # wrapped Chinese at 0.95
# {probe: the kind its partner produces, which this one must NOT}
CONTROLS_CLEAN = {"TiltedTypeCleanProbe": "leading",      # well-set, same tilt
                  "BalancedLineProbe": "orphan",          # the same copy with `text-wrap: balance`
                  "FlooredLeadingProbe": "tight"}         # the same copy at EXACTLY the floor
# KineticManifesto is deliberately here on the GOOD side — see the header. It reports clean and that is the
# right answer; it was a mis-diagnosis off a single mid-flythrough frame.
# REAL registers that must not report a `leading` collision — the two repaired ones included, so a
# regression in either shows up here.
CONTROLS_GOOD = ["CinematicTitle", "TermTable", "QuadSplit", "KineticManifesto",
                 "MagazineSpread", "BrutalistType"]


def unfed_control():
    """The guard that catches a fixture which never reached its register — proved on a REAL wrong shape.

    It regressed once already: the first threshold landed exactly on the measured wrong case and the control
    reported clean. Handing TermTree a list of strings where it declares {name, note, tag} is the actual bug
    that shipped, so that is what this replays."""
    wrong = {"cmd": _SHORT, "root": _SHORT, "items": list(_ITEMS[:3])}
    tmp = os.path.join(_REMOTION, ".cjk_type_probe.%d.png" % os.getpid())
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
    names = list(CONTROLS_BAD) + list(CONTROLS_CLEAN) + CONTROLS_GOOD
    res = sweep(names)
    bad = {n: [h for h in res[n]["hits"] if h["kind"] == k] for n, k in CONTROLS_BAD.items()}
    clean = {n: [h for h in res[n]["hits"] if h["kind"] == k] for n, k in CONTROLS_CLEAN.items()}
    good = {n: [h for h in res[n]["hits"] if h["kind"] == "leading"] for n in CONTROLS_GOOD}
    # A CONTROL THAT NEVER RENDERED IS NOT A CONTROL. `QuadSplit` threw on a fixture that fed a Chinese
    # sentence to an icon name, and a failed render carries no hits — so it read as "known-GOOD, 0
    # collisions" and the controls passed while measuring one register fewer than they claimed.
    dead = [n for n in names if res[n]["failed"]]
    print("[cjk_type] CONTROLS — synthetic frames it must catch, their one-property-different twins it must "
          "not, and\n           real registers it must not flag:")
    for n, k in CONTROLS_BAD.items():
        print("   known-BAD  %-24s %d %s finding(s)%s"
              % (n, len(bad[n]), k, "" if bad[n] else "   <- NOT CAUGHT"))
    for n, k in CONTROLS_CLEAN.items():
        print("   its twin   %-24s %d %s finding(s)%s"
              % (n, len(clean[n]), k, "   <- FALSE POSITIVE" if clean[n] else ""))
    for n in CONTROLS_GOOD:
        print("   known-GOOD %-24s %s"
              % (n, "DID NOT RENDER   <- NOT A CONTROL" if res[n]["failed"]
                 else "%d leading collision(s)%s" % (len(good[n]),
                                                     "   <- FALSE POSITIVE" if good[n] else "")))
    print("[cjk_type] CONTROLS — and the guard for a fixture that never reaches its register:")
    fed = unfed_control()
    ok = (all(bad[n] for n in CONTROLS_BAD) and not any(clean[n] for n in CONTROLS_CLEAN)
          and not any(good[n] for n in CONTROLS_GOOD) and not dead and fed)
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
    ap.add_argument("--all-aspects", action="store_true",
                    help="every aspect the renderer offers, not just the landscape one")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.controls:
        return controls()
    if getattr(a, "all_aspects", False):
        # THE ONE GATE THAT CAN SEE A MISSING ELEMENT ONLY EVER RAN AT ONE ASPECT. `text_safe_qa` reports
        # type CUT OFF by the frame, which means it can only see ink that exists; a phrase a register
        # declined to draw is invisible to it and reported as clean. This audit asks a different question —
        # did the strings the fixture FED the register reach the screen — and it is the only one that can
        # answer it. WordTunnel held its final phrase at 1.4x and fitted it to the bare frame width, so at
        # 1:1 in Chinese that phrase was culled for width and the shot played its ending on an empty frame.
        # text_safe_qa said 0 findings at all five aspects in both languages. THIS said "DREW ALMOST
        # NOTHING" — but only when handed `--aspect=1:1`, which nothing did. The list is read from the
        # renderer, like text_safe_qa's, so a sixth aspect is covered the day it is added.
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import _caption_band as _cb
        rest = [x for x in argv if not x.startswith("--aspect=") and x != "--all-aspects"]
        worst = 0
        for asp in _cb.aspect_table():
            print("### aspect %s" % asp, flush=True)
            worst = max(worst, main(rest + ["--aspect=" + asp]))
        return worst
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
    tight = {n: [h for h in v["hits"] if h["kind"] == "tight"] for n, v in res.items()}
    tight = {n: h for n, h in tight.items() if h}
    orph = {n: [h for h in v["hits"] if h["kind"] == "orphan"] for n, v in res.items()}
    orph = {n: h for n, h in orph.items() if h}
    unfed = {n: v for n, v in res.items() if any(h["kind"] == "unfed" for h in v["hits"])}
    # A rotated element the orientation-free instrument could not read is not a pass — it is an element
    # NOTHING is known about. It fails, because the only way to reach it is a renderer that cannot measure
    # font metrics, and then every rotated register in the sweep is unmeasured and the run means nothing.
    drop = {n: [h for h in v["hits"] if h["kind"] == "dropped"] for n, v in res.items()}
    drop = {n: h for n, h in drop.items() if h}
    unmeas = {n: [h for h in v["hits"] if h["kind"] == "unmeasured"] for n, v in res.items()}
    unmeas = {n: h for n, h in unmeas.items() if h}
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
        if tight:
            print("\nWRAPPED CHINESE UNDER THE LEADING FLOOR — nothing collides, and there is no air either "
                  "(fix with\n  `leading(text, latin)` from runtime/cjkType; the call is a no-op on Latin "
                  "copy):")
            for n in sorted(tight, key=lambda k: -max(h["depth"] for h in tight[k]))[:20]:
                h = max(tight[n], key=lambda x: x["depth"])
                print("    %-22s %s  «%s»" % (n, h["font"], h["text"]))
        if orph:
            print("\nA LAST LINE HOLDING ONE CHARACTER — Chinese breaks between any two glyphs, so a label a "
                  "unit too\n  wide for its box drops one onto a line of its own (fix with "
                  "`textWrap: 'balance'` on the label):")
            for n in sorted(orph)[:20]:
                h = orph[n][0]
                print("    %-22s «%s» ends on a line holding «%s»" % (n, h["text"], h.get("other", "?")))
        if untest:
            print("\nNOT TESTED — no CJK copy could be shaped for these props (add the shape to _ARRAY_SHAPES):")
            for n in sorted(untest)[:14]:
                print("    %-22s %s" % (n, ", ".join(untest[n])))
        if unfed:
            print("\nDREW ALMOST NOTHING — the fixture did not reach these registers, so a clean result here "
                  "would\n  be a measurement of an empty frame, not of the register:\n    %s"
                  % ", ".join(sorted(unfed)[:16]))
        if drop:
            print("\nDREW A SPARSE FRAME AND DROPPED SOME OF THE COPY — the register was reached, and some "
                  "of what it\n  was given did not appear (a capped list, or a panel conditional on a prop). "
                  "A report, not a failure:")
            for n in sorted(drop):
                print("    %-22s %s" % (n, drop[n][0]["text"]))
        if unmeas:
            print("\nCOULD NOT BE MEASURED — these are drawn on a TILT and the orientation-free instrument "
                  "could not\n  read them, so this run says nothing about them either way:")
            for n in sorted(unmeas)[:14]:
                print("    %-22s %s  «%s»" % (n, unmeas[n][0].get("why", "?"), unmeas[n][0]["text"]))
        if failed:
            print("\nFAILED TO RENDER: %s" % ", ".join(sorted(failed)[:14]))
        if not lead:
            print("\nNo register sets Chinese copy into itself.")
    return 1 if (lead or unfed or unmeas) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
