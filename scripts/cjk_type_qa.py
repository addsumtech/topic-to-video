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
from onscreen_text_qa import _strip_comments   # the ONE comment stripper
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
# AND ONE OF THEM CARRIES AN OPENING BRACKET, which nothing in this fixture did until now. A line may not
# END with one, so the browser carries it down — measured on the real face, the same nine glyphs take three
# lines with `「` where a line would have ended and two without. `wrapLines` implements both halves of the
# rule now; no fixture string exercised the second, so the sweep could not have caught it being wrong.
#
# WHERE THE BRACKET SITS IS THE WHOLE POINT, and the first string written here did not know that. It opened
# `把「重复…`, two glyphs in — and a line can only END at that bracket in a column narrower than two glyphs,
# which no register has. Swept against the rule turned off, across every realistic size (px 24-72, columns 4
# to 20 glyphs wide), it changed the predicted line count in exactly ZERO of them: a fixture that exercises
# nothing, which is the thing it was added to stop being. Moved to the middle of the sentence it changes 54.
# It is deliberately the SAME sentence as the entry above it without the brackets, so the pool carries its
# own control.
_MED_V = [_MED,
          "它自己拆解任务、调用工具、改动文件，最后交出可验收的结果",
          "同样的输入框，同样的一段回答，变的是谁在动手做完这件事",
          "重复三次以上的动作会被记下来，下一次不必再从头讲一遍",
          "重复三次以上的动作会被记下来，「下一次」不必再从头讲一遍"]
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
# A UNIT IS ONE OR TWO GLYPHS. `unit` was matched by the kicker rule and handed 4-6 — eleven registers
# declare one (`ChartLive`, `MadeOf`, `OdometerRoll`, `VelocitySnap`, …) and every one of them prints it
# hard against its figure, so `MadeOf` drew «26沉淀为技能» and was reported under the leading floor at 81px
# about a string no film would ever write there. A unit is 件 / 次 / 份 / %, and the gate's own doctrine is
# the lengths a real film uses, not the longest string the pool holds.
_UNIT_V = ["件", "次", "份", "%"]

_ROLE = [
    (r"^[a-z]*(unit|per|each)$|^unit[A-Z][a-zA-Z]*$", _UNIT_V),
    (r"^[a-z]*(kicker|meta|issue|sectionLabel|wordmark|colophon|doneLabel|tag|cmd|root|hub|time|date|"
     r"hash|ref|status|filename|glyph|kind|side|stamp|seal|badge|code|plateNo|verdict|pronunciation|chip)$",
     _SHORT_V),
    # ...and the role word can lead as well as trail: `underLabel` and `labelLeft` are both labels.
    (r"^[a-z]*(label|heading|focalLabel|titleTop|titleBottom|word|value|query|display)$"
     r"|^(label|heading|word)[A-Z][a-zA-Z]*$", _LABEL_V),
    # A PLATE'S SUBJECT IS A PROPER NOUN. `place` matched nothing and fell to the medium-sentence default,
    # so MapPlate's centre mark — set as display type against the plate — was a 26-glyph sentence that wrapped
    # to four lines through the middle of the map. The pools are deliberately hard cases, but a hard case for
    # a NAME is a long name, not a paragraph: fed a sentence, every register that centres its subject reports
    # an overlap that no film could ever produce.
    (r"^[a-z]*(title|hero|headline|name|place|city|subject|who)$", _TITLE_V),
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
    if (re.search(r"<Figure\b[^>]*\bvalue=\{%s\b" % esc, src, re.S)
            or re.search(r"\b(?:Number|parseFloat|parseInt)\([^)]*\b%s\b" % esc, src)
            or re.search(r"\b%s\s*\.\s*toLocaleString\(" % esc, src)):
        return True
    # THE SAME TEST THE ROW LEVEL ALREADY MAKES, one level up. `_ROW_READOUT` says a row's `value` is a
    # figure when the row is a MEASURED one, and that rule was never applied to a top-level prop: the same
    # names — `total`, `count`, `amount` — fell through to the sentence pool. `TallyLedger.total` ("the
    # figure the ledger adds up to, ruled off at the foot") was handed a 26-glyph sentence and overlapped
    # its own neighbours three ways. The register's default is `''`, so there is no evidence in it to read;
    # the evidence is that the register counts — it declares numbers — and that this prop is named for the
    # result of counting.
    return bool(_ROW_READOUT.match(prop) and re.search(r":\s*number\b", src))


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
def _turn(n, off):
    """How far to actually rotate a list of `n` for `off` — never zero when a shift was asked for.

    `off % n` is 0 whenever the length divides the offset, and the offset this library uses is 2, so EVERY
    two-element list came back unrotated: `ChatThread`'s two messages are the whole content of that
    register, so its "second prop set" was the first one, `prop_reach` rendered the identical frame twice
    and measured the register's reach as 0.000 — reported as UNTRUSTED, which is honest, and still a
    measurement nobody could take. A no-op is not a rotation."""
    if not n or not off:
        return 0
    return (off % n) or 1


def _rotate(seq, off):
    """The same list, started at a different place. `offset` has to reach the FIXED lists too, or two prop
    sets that are meant to be different topics hand a register the identical `items` twice and the
    measurement built on them reads 'this register ignores its props' about a register that was never
    given two different ones."""
    seq = list(seq)
    k = _turn(len(seq), off)
    return seq[k:] + seq[:k] if seq else seq


def _string_for(prop, local=None, src="", i=0):
    if _is_readout(prop, local or prop, src):
        return _READOUT
    for pat, pool in _ROLE:
        if re.match(pat, prop, re.I):
            return pool[i % len(pool)]
    return _MED_V[i % len(_MED_V)]




# WHICH NUMBER PROPS ARE AN INDEX, read from the register's OWN documentation rather than a list of names.
#
# This was `prop in ("focal", "target")`. Both of those are real, and the list was right on the day it was
# written — which is the whole problem: `HeldInstant` requires `held`, an index into its `steps`, refused to
# render without one, and the sweep reported a COVERAGE HOLE at all five aspects. A register no gate can
# feed is a register nobody checks, and it fails silently in the direction that looks like nothing happened.
# This repo has fixed the same shape in `evidence_props` (parse the `requireEvidence` call sites, never list
# the registers) and in `register_energy.register_maps` (structure, never a restated list of keys).
#
# The signal is the prose the author already writes: a required index is documented as an index, because
# whoever wrote the prop had to explain which list it points into. Optional SELECTORS (hero, winner,
# highlight, active) stay unset on purpose — their neutral state is what a film that omits them gets — and
# they are not documented as indices, so the same test leaves them alone.
_INDEX_DOC = re.compile(r"\bindex(es)?\b|\bwhich (one|of)\b", re.I)


def _is_an_index(prop, src):
    """True when `prop`'s own comment in the register's source says it names a position in a list."""
    # The REFUSAL test first, because it needs no particular layout. Anchoring on a declaration at the
    # start of a line returned False for `FocalIsolation` before either test ran: it declares all three
    # props on one line, so the prop is never at a line start and the early return swallowed it.
    # The backtick may be ESCAPED. A refusal written in a template literal has to write \` for a backtick,
    # and a refusal in a single-quoted string does not — so `FocalIsolation` matched a bare-backtick pattern
    # and `CrashZoom`, which says exactly the same sentence inside a template literal, did not. Its row went
    # from measured to "refused to render" and only the real sweep caught it; the unit test named three
    # registers and CrashZoom was not one of them.
    if re.search(r"pass\s+\\?`%s\\?`" % re.escape(prop), src or ""):
        return True
    m = re.search(r"^([ \t]*)%s\s*\??\s*:" % re.escape(prop), src or "", re.M)
    if not m:
        return False
    head = (src or "")[:m.start()].rstrip()
    # walk back over the contiguous comment block directly above the declaration
    doc = []
    for line in reversed(head.splitlines()):
        st = line.strip()
        if st.endswith("*/"):
            doc.append(st)
            for ln in reversed(head.splitlines()[:len(head.splitlines()) - len(doc)]):
                doc.append(ln.strip())
                if ln.strip().startswith("/*"):
                    break
            break
        if st.startswith("//"):
            doc.append(st)
            continue
        break
    # ...OR ITS OWN DOCUMENTATION SAYS SO, which is what a register written since the content contract
    # carries: whoever wrote a required index had to explain which list it points into. Optional SELECTORS
    # (hero, winner, highlight, active) stay unset on purpose — their neutral state is what a film that
    # omits them gets — and none of them is documented as an index or refused without.
    return bool(_INDEX_DOC.search(" ".join(doc)))


def _refused_without(prop, src):
    """True when the register's own refusal names `prop` — it will throw unless the fixture supplies it.

    Shares the signal `_is_an_index` reads, for the same reason: a register that requires something says
    so in the sentence it throws, and that sentence is structural where a list of prop names is a copy
    that goes stale. The backtick may be escaped, because a refusal written in a template literal has to
    write a backslash before one."""
    return bool(re.search(r"(?:pass|marked|needs at least one[^.]{0,40}?)\s*\\?`%s\\?`"
                          % re.escape(prop), src or ""))


def prop_signature(name):
    """{prop: type-text} straight from the register's own React.FC<{…}> declaration."""
    try:
        src = open(os.path.join(_SHOTS, name + ".tsx"), encoding="utf-8").read()
    except OSError:
        return {}, ""
    # TWO MORE WAYS TO BE INVISIBLE, both found by asking which registers this gate feeds NOTHING. The old
    # pattern demanded the props be written inline AND `}>` to be adjacent, so:
    #   AcceptanceStamp  `React.FC<Props>`   — its four props live in a named alias above the component
    #   MRIPipeline      `React.FC<{...} >`  — one space before the closing angle
    # were swept with their English demo defaults ('Condition one', 'ACCEPTED', 'Always computed') and
    # reported 0 findings, which is the same silence the JSDoc blindness produced: a register nobody can
    # feed is never checked, and the output says nothing about it either way.
    m = re.search(r"export const %s: React\.FC<\s*\{(.*?)\}\s*>\s*=" % re.escape(name), src, re.S)
    if not m:
        a = re.search(r"export const %s: React\.FC<\s*([A-Za-z_][A-Za-z0-9_]*)\s*>\s*=" % re.escape(name),
                      src)
        if a:
            d = re.search(r"(?:type\s+%s\s*=\s*|interface\s+%s\s*)\{(.*?)\}\s*;?\s*$"
                          % (re.escape(a.group(1)), re.escape(a.group(1))), src, re.S | re.M)
            if d:
                m = d
    if not m:
        return {}, src
    # COMMENTS COME OFF BEFORE THE SPLIT, not after. `_one_prop` strips them too, but by then the damage is
    # done: this loop breaks the body at every top-level `;`, and a semicolon inside a comment splits mid
    # sentence — so the NEXT prop's chunk begins with the comment's tail, `_one_prop` anchors on an
    # identifier at the start, finds a backtick, and the prop is dropped in silence. Nine registers lost a
    # prop this way AFTER the JSDoc fix, every one of them to a `;` a human wrote inside an explanation:
    # StrataColumn `// top (surface) -> bottom; `find` marks the layer`, DollyZoom `/** `in` = ...; `out` =
    # ... */`, SectionRoute, GazetteerEntry, InOrder, Inscription, LastLeg, PointerTour, ProfileGrowth.
    # Stripping first also fixes the depth counter, which was counting braces inside prose.
    body, out, depth, cur = _strip_comments(m.group(1)), {}, 0, ""
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


# COMMENTS ARE STRIPPED BEFORE A PROP IS READ, and for a long time they were not. `_one_prop` anchors on
# an identifier at the START of its chunk, so a prop preceded by a JSDoc comment — which is the house style
# for documenting one — never matched and was dropped in SILENCE. Measured across the library the day a new
# register made it visible: TWO registers were invisible to this gate entirely (their every prop is
# documented, so `cjk_props` returned {} and the sweep reported "0 findings" about a frame rendered from the
# register's own demo defaults) and TWENTY-FIVE were read only in part — `GrantedTree` 1 prop of 6,
# `MadeOf` 1 of 5, `Inscription` 1 of 4.
#
# That silence also produced a false FACT. `prop_reach` fed those crippled sets, measured almost no change,
# and the number was written into LIBRARY.md as "a register whose only authorable prop is a kicker". MadeOf
# declares five. The gate was not describing the register, it was describing what it could see of it.
#
# `_strip_comments` is the ONE stripper in this repo and two other parsers were already fixed to use it.
def _one_prop(chunk):
    m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\??\s*:\s*(.+)",
                 _strip_comments(chunk).replace("\n", " "), re.S)
    return {m.group(1): m.group(2).strip()} if m else {}


def _tuple_len(ty):
    """`[string, string, string]` declares THREE. Feeding four is not a harder test — the fourth cannot be
    drawn by a register whose type has three slots, and it was reported as a dropped string on
    `IsometricAssembly` at every aspect it was swept at."""
    t = ty.replace(" ", "").rstrip(";")
    if not (t.startswith("[") and t.endswith("]")):
        return None
    parts = [x for x in t[1:-1].split(",") if x]
    return len(parts) if parts and all(x == "string" for x in parts) else None


def _declared_keys(ty, src):
    """The keys an object-typed prop actually declares — inline, or through a named alias.

    `_ARRAY_SHAPES` is keyed by PROP NAME, and one name serves registers with different shapes: `left` is a
    `Col {head, body, hero}` on EdCompare and something else on VersusSplit, so the shared entry carries the
    union of both. The extra keys are not a fixture bug, but handing them to a register that cannot read
    them is — EdCompare reported 2 of 11 strings dropped at four aspects, and both were `points` entries,
    a key its own type does not have."""
    t = ty.strip().rstrip(";").strip()
    body = None
    if t.startswith("{") and t.endswith("}"):
        body = t[1:-1]
    elif re.match(r"^[A-Z][A-Za-z0-9_]*$", t):
        m = re.search(r"type\s+%s\s*=\s*\{([^}]*)\}" % re.escape(t), src, re.S)
        if m:
            body = m.group(1)
    if body is None:
        return None
    return {k for k in re.findall(r"([A-Za-z_][A-Za-z0-9_]*)\s*\??\s*:", body)}


def cjk_props(name, offset=0):
    """(props, untestable) — CJK copy shaped to this register's own signature.

    `offset` shifts every role pool by the same amount, so the SAME register can be fed two prop sets that
    are identically SHAPED and carry entirely different words. That is what `scripts/prop_reach.py` renders
    twice: a register whose picture barely moves between them is one whose picture is furniture, and the
    film only ever authored a caption on it. Default 0, so every existing caller is byte-identical."""
    sig, src = prop_signature(name)
    props, untestable, seen = {}, [], set()
    scalars = offset
    for prop, ty in sig.items():
        t = ty.replace(" ", "")
        # `page` selects WHICH page shape a surface draws (cards / chart / table / form) — plumbing, like
        # `aspect` and `dna`, not copy. Left off this list it was reported as untestable on every register
        # that takes one, which is a permanent line in the gate's output that means nothing.
        # `face` joins the list for the reason the others are on it: Inscription declares it as "override the
        # stone tone; defaults to a darker cut of the DNA's surface" — a COLOUR. It was handed a 26-glyph
        # sentence as a tone, which is the top-level twin of the `_NON_COPY_FIELDS` bug that fed TermBars a
        # sentence as the colour of every bar.
        if prop in ("accent", "accent2", "imageAspect", "aspect", "dna", "page",
                    "face") or re.match(r"^src[A-Z]?", prop):
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
            props[prop] = _rotate(list(_ITEMS), offset)[:4]
        elif _tuple_len(ty):
            props[prop] = _rotate(list(_ITEMS), offset)[:_tuple_len(ty)]
        elif t.startswith("string"):
            # EVERY SIBLING SCALAR GOT THE SAME SENTENCE. `i` is the row index inside a shaped array, and
            # nothing passed one for a top-level prop, so each took its pool's first entry: `RackFocus`
            # declares before / after / beforeNote / afterNote / pivot and rendered ONE sentence five times.
            # A sweep cannot judge a multi-prop register that way — and it cannot tell a dropped string from
            # a duplicated one either, which is the same reason the ARRAY side was given row-varying copy.
            # The variants keep the ROLE, so a label stays label-length and a note stays note-length; only
            # the words differ, which is the one thing that must.
            # NO TWO SIBLINGS GET THE SAME STRING. Varying by ordinal spreads the pool, but a pool of four
            # and five label-role props wraps: `BeforeAfterSlider` got «自主循环运转» for BOTH `heading` and
            # `afterLabel`, and the sweep reported an overlapping pair between them — the detector matches
            # elements by their text, so two elements carrying one string cannot be told apart and a phantom
            # pair is indistinguishable from a real one. It is the same reason the array side was given
            # row-varying copy: this gate cannot tell a DROPPED string from a DUPLICATED one.
            pick, tries = _string_for(prop, _local_of(prop, src), src, scalars), 0
            while pick in seen and tries < 8:
                tries += 1
                pick = _string_for(prop, _local_of(prop, src), src, scalars + tries)
            seen.add(pick)
            props[prop] = pick
            scalars += 1
        elif t.startswith("boolean"):
            continue
        elif t.startswith("number") or t.startswith("number|null"):
            # AN INDEX THE REGISTER REQUIRES is fed one. Under the content contract a register no longer picks
            # which of the film's items to spotlight (`focal`) or to land on (`target`) — it refuses to render
            # without the film's choice, so a sweep that left these unset reported GlowPick and FocalIsolation
            # as "failed to render" over a fixture that never said which item. 1 is inside every fixture list
            # (they all carry at least two rows). Optional selectors (hero, winner, highlight, active) stay
            # unset on purpose: their neutral state is what a film that omits them gets.
            if t.split("|")[0] == "number" and _is_an_index(prop, src):
                props[prop] = 1
            continue
        elif "[]" in t:
            # THE TYPE BEATS THE NAME TABLE, and it has to be asked FIRST. `_shape_array` is keyed by prop
            # name, so a type this could not read fell through to whatever `rows` or `items` means on some
            # OTHER register — which is how SplitFlap came to be swept with a two-column table it renders
            # as blank flaps. The table is the fallback for shapes the reader still cannot resolve, not the
            # first answer.
            # A LIST OF NUMBERS OR OF PAIRS IS DATA, NOT COPY. BeforeAfterSlider's `series?: (number | string)[]`
            # is a chart's values (a figure string at most) and KnowledgeGraph's `links?: [a, b][]` is which
            # nodes connect. Fed a Chinese sentence, both registers refuse it — they are the content contract's
            # new props, and their absence is exactly the case the contract draws (no chart, spokes only).
            elem = t[:-2] if t.endswith("[]") else t
            alias = re.fullmatch(r"[A-Z]\w*", elem) and re.search(
                r"\btype\s+%s\s*=\s*([^;\n]+)" % re.escape(elem), src)
            if alias:                                    # `GraphLink[]` → `[number | string, number | string]`
                elem = alias.group(1).replace(" ", "")
            if elem.startswith("[") or (elem.startswith("(number") and "{" not in elem):
                continue
            shaped = _shape_from_type(prop, ty, src, off=offset)
            if shaped is _NOT_COPY and prop in _COUPLED_GEOMETRY:
                # geometry this sweep must feed anyway, because the register refuses the copy without it
                props[prop] = _COUPLED_GEOMETRY[prop]
                continue
            if shaped is _NOT_COPY:
                continue                                 # geometry, not copy — keep the register's default
            # ...BUT THE TABLE WINS WHEN IT FITS, and "type first, always" was too blunt. The table exists
            # because a curated shape knows things a type cannot: `sources?: {t: string; d: string}[]` says
            # nothing about `t` being a four-glyph chip and `d` a short status, so the type route filled both
            # with 26-glyph sentences and `AnswerStream` orphaned a glyph off a source chip. What the type
            # route is FOR is the case where the table is wrong — `rows` means a two-column table there and
            # SplitFlap's rows are strings. So the test is COMPATIBILITY, asked of the declared keys, not
            # precedence: a table entry whose rows are objects keyed inside the register's own type is the
            # better fixture; anything else is the table describing a different register that shares a
            # prop name.
            # ...AND WHEN IT FITS, IT IS MERGED, NOT CHOSEN. The first version of this let a compatible table
            # REPLACE the type-derived shape, and "compatible" was a subset test: `panels` in the table carries
            # `{label}` only, QuadSplit's type also declares `icon: IconName`, `{label} <= {label, icon, ...}`
            # passed, and the table won — every icon came back None. That is the bug this whole shaper was
            # written to end (a field the register needs, silently absent) reintroduced by its own fix, and a
            # test pinned since QuadSplit first threw caught it. The table supplies curated VALUES for the keys
            # it has; the type supplies every field the table does not name. Neither is allowed to delete
            # what the other knows.
            if prop in _ARRAY_SHAPES and isinstance(shaped, list):
                keys = _declared_keys(ty.replace("[]", ""), src) or _declared_keys(ty, src)
                tbl = _ARRAY_SHAPES[prop]
                rows_ = tbl if isinstance(tbl, list) else [tbl]
                if keys and rows_ and all(isinstance(r, dict) and set(r) <= keys for r in rows_):
                    curated = _shape_array(prop, ty, off=offset) or []
                    shaped = [dict(shaped[i % len(shaped)], **curated[i]) if isinstance(curated[i], dict)
                              else curated[i] for i in range(len(curated))] if curated else shaped
            if shaped is None:
                shaped = _shape_array(prop, ty, off=offset)
            if shaped is None:
                untestable.append(prop)
            else:
                props[prop] = shaped
        elif re.fullmatch(r"(?:'[^']*'\|)+'[^']*'", t):
            # A UNION OF STRING LITERALS IS A SWITCH, not copy: `NeuralField.tone` picks WHICH accent the
            # live path wears. Reported untestable it read as unreachable copy; fed a sentence it would be
            # an undeclared value the register cannot honour. It gets its own FIRST declared literal, and
            # gets it identically at every `offset` — prop_reach renders two sets to ask how much of the
            # picture the film's WORDS author, and a switch that flipped between them would answer with a
            # colour change.
            props[prop] = t.split("|")[0].strip("'")
        elif t.startswith("{") or (_type_fields(ty, src) and prop not in _ARRAY_SHAPES):
            # AN OBJECT PROP THAT IS NOT AN ARRAY — `MapPlate.channel` is one object carrying a `label`,
            # two coordinate pairs and a width. Only the array side had a reader, so a lone object fell to
            # the bottom of this chain and was filed untestable although its label is exactly the copy this
            # gate exists to set in Chinese.
            got = _type_fields(ty, src)
            if got is None:
                untestable.append(prop)
            else:
                fields, bare = got
                if not _carries_copy(fields, bare):
                    continue                             # geometry again, one nesting level up
                props[prop] = _shaped_row(fields, src, offset) if fields else _string_for(prop, prop, src, offset)
        elif prop in _ARRAY_SHAPES:
            # an OBJECT-shaped prop (a side, a group, a range), TRIMMED TO THE KEYS THIS REGISTER DECLARES —
            # see `_declared_keys`. The shared entry carries the union of every register that uses the prop
            # name, and a key the type does not have is copy that cannot be drawn.
            shape = _ARRAY_SHAPES[prop]
            keys = _declared_keys(ty, src) if isinstance(shape, dict) else None
            props[prop] = {k: v for k, v in shape.items() if k in keys} if keys else shape
        else:
            untestable.append(prop)
    for prop, val in _REGISTER_COPY.get(name, {}).items():
        if val is None:
            props.pop(prop, None)
        elif prop in props:
            props[prop] = val
    # TWO SPELLINGS OF ONE SLOT MUST NOT BOTH BE FED. `// @supersedes groups: items` declares that `groups`
    # REPLACES `items` — they are the same rail, written two ways — and this shaper filled both because it
    # walks the signature prop by prop. PortRail then received `items` (4 modules) AND `groups` (3 groups of
    # 3), refused the 9 against its own 1-6 guard, and was recorded as FAILED TO RENDER for every sweep: a
    # fixture bug wearing a register's name, which is bug class 4 of the four this coverage pass exists for.
    #
    # The PROVIDER is the one dropped, and that is the general reason rather than a PortRail-shaped one: the
    # superseding spelling NESTS (a list of groups each holding a list), so the row count this shaper chose
    # is multiplied by the nesting depth and lands outside whatever arity the register accepts, while the
    # base spelling is the flat list whose length the shaper controls directly. The relation is READ from the
    # registers' own declarations — `demo_copy_qa.supersedes()`, the same parse validate.py uses; there is no
    # second list of names here.
    for provider in _supersedes().get(name, {}):
        props.pop(provider, None)
    return props, untestable


_SUPERSEDES_CACHE = {}


def _supersedes():
    """{register: {provider: [props it supplies]}} — one definition, parsed, shared with validate.py."""
    if not _SUPERSEDES_CACHE:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        # NOT WRAPPED IN A `try`. A swallowed import here returns an EMPTY relation, and an empty relation
        # feeds every register both spellings of its slot again — which is the fixture bug that recorded
        # PortRail as FAILED TO RENDER on every sweep. The module is a sibling in this directory; if it
        # cannot be imported the checkout is broken, and that must surface as an error rather than as a
        # register with a defect it does not have.
        import demo_copy_qa as _dc
        _SUPERSEDES_CACHE.update(_dc.supersedes() or {})
        _SUPERSEDES_CACHE.setdefault("", {})              # so a genuinely empty parse is not re-read forever
    return _SUPERSEDES_CACHE


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
    # EVERY POPULATION CARRIES ITS NUMBERS. `a: None` used to get the demo curves silently; OverlapSeparation
    # now refuses a population without a mean and a spread, so the fixture states both (0..1 domain).
    "fail": {"label": "只回答问题", "note": "产出停在文字上",
             "a": {"label": "旧流程", "mean": 0.5, "spread": 0.16}, "b": {"label": "新流程", "mean": 0.54, "spread": 0.16}},
    "pass": {"label": "交付成果", "note": "产出落进文件里",
             "a": {"label": "旧流程", "mean": 0.25, "spread": 0.08}, "b": {"label": "新流程", "mean": 0.78, "spread": 0.08}},
    # PhysicsStack draws heights, so its fixture carries values — `items` alone is refused.
    "bars": [{"label": "自动拆解任务", "value": 12}, {"label": "规划执行步骤", "value": 19},
             {"label": "交付可验收成果", "value": 27}],

    "domain": [0, 1],
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


# GEOMETRY THAT TRAVELS WITH COPY. `TechnicalPlate` numbers the film's `parts` on the object its `strokes`
# draw, and it now refuses parts without strokes — otherwise a film's part names landed on the demo bicycle.
# The sweep feeds parts, so it must feed an object for them to sit on; this is that object, in plate fractions.
_COUPLED_GEOMETRY = {
    "strokes": [{"kind": "circle", "x": 0.28, "y": 0.62, "r": 0.14}, {"kind": "circle", "x": 0.72, "y": 0.62, "r": 0.14},
                {"kind": "line", "x": 0.28, "y": 0.62, "x2": 0.5, "y2": 0.34}, {"kind": "line", "x": 0.5, "y": 0.34, "x2": 0.72, "y2": 0.62}],
}

# PER-REGISTER COPY, only where a register's FORM bounds the copy and refuses more. SpotlightStage sets its
# words on ONE line with an arrow between each pair and throws when they cannot fit at a readable size (a
# flow of four 11-glyph sentences is not a word-flow). Fed the generic long phrases, the sweep reported the
# register as a render failure over an input no film should give it. Its fixture is words, as its type says.
# `None` REMOVES a prop the register no longer reads once another is given: PhysicsStack keeps `items` only to
# refuse it (labels without heights), so feeding both would report four strings "dropped" that it never draws.
_REGISTER_COPY = {
    "SpotlightStage": {"items": ["拆解任务", "调用工具", "交付成果"]},
    # one or two ceilings — the bar jams against the first; four is a list it refuses
    "SpeedLimit": {"limits": ["在授权目录里真正动文件", "交付可验收的成果"]},
    "PhysicsStack": {"items": None},
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


def _synth_field(name, ty, src="", i=0, rowIdx=0):
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
        # Registers in this library author in W/H FRACTIONS so they reflow at every aspect (SKILL.md), so a
        # geometry field is 0..1 unless its name says otherwise. `width` was not on this list and MapPlate's
        # channel — `(channel.width ?? 0.02) * PW` — was handed 62, which is sixty-two plate widths.
        # ...and a POSITION is not a THICKNESS. Both are 0..1 here and the same number cannot serve both:
        # MapPlate's channel `width` defaults to 0.02 and a 0.34 draws a band a third of the plate across.
        # The name nudge is the same one the coordinate pairs carry — one `i` reaches every field of a row,
        # so a part's `x` and `y` came back equal and every callout sat on the plate's diagonal.
        j = i + sum(ord(ch) for ch in name) % 4
        if re.search(r"^(fill|frac|ratio|opacity|x\d?|y\d?|cx|cy|inset|scale)$", name, re.I):
            return round(0.30 + (j % 5) * 0.13, 3)
        # A ROW'S `depth` is a tree LEVEL — 0 at the top, an integer — not a 0..1 thickness; GrantedTree refuses
        # a fraction because an indent is the tree's structure. Rows step 0, 1, 2 so the fixture is a tree.
        if name == "depth":
            return i % 3
        # A route stop's `level` is an INDEX into the section's levels — SectionRoute refuses 62. Two levels are
        # always there in any fixture that feeds one.
        if name == "level":
            return (i + 1) % 2
        # A TALLY count is strokes somebody drew: 62 / 79 / 96 at one stroke each overran TallyLedger's row and
        # it (rightly) refused to shrink the stroke silently when the film had named what a stroke counts.
        if name == "count":
            return 6 + (i % 5) * 5
        if re.search(r"^(w|h|r|rx|ry|width|height|size|gap|pad|thickness)$", name, re.I):
            return round(0.05 + (j % 4) * 0.03, 3)
        # a COUNTER is 1, 2, 3 — `TechnicalPlate` numbers its callouts on the plate the way a real sheet
        # does, and 62 / 79 / 96 is not a part list.
        if re.search(r"^(n|no|num|index|idx|step|order|rank|seq)$", name, re.I):
            return i + 1
        return 62 + (i % 5) * 17
    if t.startswith("boolean"):
        # `granted` marks a contiguous run (rows 2-3), so the sweep sees GrantedTree's bracket and a withheld row
        if name == "granted":
            return i in (1, 2)
        # A FLAG THE REGISTER REFUSES WITHOUT has to be set on SOMETHING, or the register throws and the
        # sweep reports a coverage hole instead of a finding. `NearTheLine` refuses unless one case is
        # `near` and `PulledThread` unless one thread `moves` — both deliberately, because a frame with
        # none of them marked argues the OPPOSITE of the beat, convincingly, past every gate. The signal
        # is the same one the numeric-index rule reads: the refusal names the prop it wants. Marking ONE
        # item is the minimum that satisfies such a register, and it is also the more interesting fixture
        # — a sweep where every row is flagged never renders the unflagged branch.
        # THE RAW ROW NUMBER, not the synthesis index. `i` is the row plus the sweep's OFFSET — the second
        # prop set of a `prop_reach` measurement shifts it — so a rule written as `i == 0` fired on the
        # first set and on NO row of the second, and both registers refused to render there. The row
        # number is threaded through for this, because "exactly one row" is a statement about rows.
        # Exactly one is also the better fixture: a sweep where every row is flagged never renders the
        # unflagged branch, which on these registers is half the picture.
        if _refused_without(name, src):
            return rowIdx == 0
        return name in ("find", "hero", "done", "ok")
    m = re.match(r"^\[([A-Za-z]+),([A-Za-z]+)\]$", t)    # a fixed PAIR — `from: [number, number]`
    if m and m.group(1) == m.group(2) == "number":
        # plate fractions, kept inside 0..1 and off the edges, and varied by row the way every other
        # numeric field here is: two rows given the same pair draw one line on top of another.
        # ...and it must differ from its SIBLING pair. `_shaped_row` passes one `i` to every field, so
        # `from` and `to` came back identical and MapPlate drew a channel from a point to itself. The name
        # contributes, so two coordinate pairs in one row are two different points.
        j = i + sum(ord(ch) for ch in name) % 3
        return [round(0.14 + (j % 4) * 0.19, 3), round(0.20 + (j % 3) * 0.21, 3)]
    if m and m.group(1) == m.group(2) == "string":
        return [_string_for(name, name, src, i), _string_for(name, name, src, i + 1)]
    m = re.match(r"^'([^']+)'", t)                       # an INLINE string-literal union: first member
    if m:
        return m.group(1)
    m = re.match(r"^([A-Za-z_][A-Za-z0-9_]*)(\|undefined)?$", t)
    if m:                                                # a NAMED type — resolve it, never invent copy
        member = _named_union_member(m.group(1), src)
        return member if member is not None else _OMIT
    return _string_for(name, name, src)


# Three answers, not two. A shaper that can only say "here is a fixture" or "I could not" has to file
# geometry under one of them, and both are wrong: a guess renders nonsense, and UNTESTABLE is a standing
# line in the output claiming unreachable copy that does not exist.
_NOT_COPY = object()


def _split_union(t):
    """Top-level `|` arms of a type, with nested braces/brackets/quotes left alone."""
    arms, depth, cur, q = [], 0, "", ""
    for ch in t:
        if q:
            cur += ch
            if ch == q:
                q = ""
            continue
        if ch in "\"'":
            q, cur = ch, cur + ch
            continue
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        if ch == "|" and depth == 0:
            arms.append(cur); cur = ""
        else:
            cur += ch
    arms.append(cur)
    return [a.strip() for a in arms if a.strip()]


def _fields_of_body(body):
    # A DOC COMMENT IS NOT A FIELD. A multi-line type whose fields carry `/** ... */` put the comment text in
    # front of the field name, and `label` came back as a field called after the last word of its own prose.
    body = re.sub(r"/\*.*?\*/", " ", body, flags=re.S)
    body = re.sub(r"//[^\n]*", " ", body)
    out = {}
    for chunk in body.split(";"):
        f = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*\??\s*:\s*(.+)", chunk.replace("\n", " "), re.S)
        if f:
            out.setdefault(f.group(1), f.group(2).strip())
    return out


# A UNION ALIAS IS STILL A SHAPE, and for a long time this reader stopped at the first `|`. `type FlapRow =
# string | {text: string; tone?: ...}` did not match `type X = {...};`, so `_shape_from_type` returned None
# and the prop fell through to the table keyed by prop NAME — where `rows` means a two-column TABLE. SplitFlap
# was swept with `[["...","..."],["...","..."]]`, its own `String(r?.text ?? '')` turned every array row into
# the empty string, and the register rendered a kicker over ONE EMPTY SLOT: measured 0.05% ink against 8.30%
# when fed rows it can read. The gate reported it clean at every aspect, for as long as the fixture existed.
# That is the same lie as measuring an empty plate, arriving through the exact door `_shape_from_type`'s own
# docstring warns about — the name table hiding a type it could not parse.
# A TYPE'S BODY ENDS AT ITS OWN CLOSING BRACE, NOT AT THE FIRST `;`. The alias reader took everything up to
# the first semicolon that ended a line, which is the FIRST FIELD of any type written across several lines:
#
#     export type FoldTask = {
#       /** the main task, as the companion lists it */
#       label: string;        <- the reader stopped here, on an unbalanced `{`
#       state?: 'working' | 'waiting';
#     };
#
# An unbalanced body resolves to nothing, so `TaskFold`'s whole `tasks` prop reported UNTESTABLE — the gate
# saying "nobody can feed this register Chinese" about a register whose rows are all copy. Single-line aliases
# are unaffected: the brace scan lands on the same text the old regex returned.
def _alias_rhs(name, src):
    m = re.search(r"(?:export\s+)?type\s+%s\s*=\s*" % re.escape(name), src)
    if not m:
        return None
    rest = src[m.end():]
    body = rest.lstrip()
    if body.startswith("{"):
        off = len(rest) - len(body)
        depth = 0
        for i, ch in enumerate(rest[off:], start=off):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return rest[off:i + 1]
        return None                                  # an unclosed brace is unreadable, and stays UNTESTABLE
    m2 = re.match(r"(.+?);[ \t]*(?://[^\n]*)?$", rest, re.S | re.M)
    return m2.group(1) if m2 else None


def _type_fields(ty, src, _depth=0):
    """({field: type}, bare_string_ok) for an object-shaped type — inline, named, or a UNION of either.

    None when the type cannot be resolved. That answer has to stay available: a shape this cannot read is
    exactly where the defect it hunts for hides, so an unreadable type is reported UNTESTABLE rather than
    fed a guess."""
    t = (ty or "").strip().rstrip(";").strip()
    if t.endswith("[]"):
        t = t[:-2].strip()
        if t.startswith("(") and t.endswith(")"):
            t = t[1:-1].strip()
    fields, bare, resolved = {}, False, False
    for arm in _split_union(t):
        if arm == "string":
            bare, resolved = True, True
        elif arm.startswith("{") and arm.endswith("}"):
            fields.update({k: v for k, v in _fields_of_body(arm[1:-1]).items() if k not in fields})
            resolved = True
        elif re.fullmatch(r"[A-Z][A-Za-z0-9_]*", arm) and _depth < 3:
            # `;` may be followed by a line comment: `type Node = {...};   // label + depth REQUIRED` went
            # unresolved, and GrantedTree's rows were filled from another register's timeline table.
            rhs = _alias_rhs(arm, src)
            if rhs is not None:
                sub = _type_fields(rhs, src, _depth + 1)
                if sub:
                    fields.update({k: v for k, v in sub[0].items() if k not in fields})
                    bare, resolved = bare or sub[1], True
    return (fields, bare) if resolved else None


# Copy is what this gate measures. A shape with no string in it is GEOMETRY — `TechnicalPlate`'s `Stroke` is
# a discriminated union of coordinates, and there is no Chinese to put in a radius. Feeding it anything is
# nonsense; calling it UNTESTABLE is worse, because that line claims the register has copy nobody can reach
# when every string it draws (kicker / object / plateNo / parts / note) is fed and measured. So it keeps the
# register's own default and says nothing — but ONLY once the type has actually been READ. A type this
# cannot parse is never called geometry; it is still untestable, and still loud.
def _carries_copy(fields, bare_string=False):
    if bare_string:
        return True
    return any(re.search(r"\bstring\b", str(v)) for v in fields.values())



# A field that names a COLOUR is not copy, at any nesting depth. The top-level skip covered `accent` and
# `accent2`; a row's own `tone` sat below it, so `TermBars` was handed a Chinese sentence as the colour of
# every bar. Omitted, so the register keeps its own default.
# `glyph`, `kind`, `state` and `el` NAME a picture, a board type, a status or an element — a closed set the
# register validates. Fed a sentence, the repaired registers refuse it (an unknown glyph must not draw the wrong
# picture), so the sweep reported PlatformSurfaces and QuadSplit as render failures over its own input. Left
# out, the row draws no picture, which is the case the content contract says a film without one gets.
_NON_COPY_FIELDS = re.compile(r"^(tone|color|colour|accent\d?|bg|background|ink|hue|fill|shade|stroke|glyph|kind|state|el)$", re.I)
# ...and a DATA ROW's readout is a number. A row that also declares a numeric `pct` or `fill` is a measured
# row, so its `value` is the figure beside the bar — `TermBars` drew nothing for the word it was given.
_ROW_READOUT = re.compile(r"^(value|amount|metric|count|total|num)$", re.I)


def _is_text(ty):
    return str(ty).replace(" ", "").startswith("string")


# `rowIdx` is the row NUMBER, kept distinct from the local `row` dict this builds — naming it
# `row` shadowed that dict and handed `_synth_field` a mapping where it expected an index, which
# silently switched the flag rule off in every prop set.
def _shaped_row(fields, src, i=0, rowIdx=0):
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
        # THE FIELD NAME CONTRIBUTES, exactly as it does for the numeric fields. One `i` reaches every field
        # of a row, so `{t, d}` came back carrying the SAME sentence twice — and the overlap detector matches
        # elements by their text, so a row whose two labels are one string cannot be told apart from a real
        # collision.
        val = _synth_field(k, v, src, i + (sum(ord(ch) for ch in k) % 3 if _is_text(v) else 0), rowIdx)
        if val is not _OMIT:
            row[k] = val
    return row


def _shape_from_type(prop, ty, src, n=3, off=0):
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
        got = _type_fields(m.group(1), src)
        if got is None:
            return None
        fields, bare = got
        if not _carries_copy(fields, bare):
            return _NOT_COPY
        if not fields:                                   # a list of bare strings, e.g. `type Row = string`
            return _rotate(list(_ITEMS), off)[:n]
        return [_shaped_row(fields, src, i + off, i) for i in range(n)]
    m = re.match(r"^\{(.+)\}\[\]$", t)                                      # an INLINE object array
    if m:
        fields = {}
        for chunk in m.group(1).split(";"):
            f = re.match(r"([A-Za-z_][A-Za-z0-9_]*)\??:(.+)", chunk)
            if f:
                fields[f.group(1)] = f.group(2)
        if fields:
            return [_shaped_row(fields, src, i + off, i) for i in range(n)]
    return None


# A SECOND PROP SET IS DIFFERENT WORDS, NOT A DIFFERENT SHAPE. Rotating a list of ROWS rotates everything
# in them, including the numbers — and in a list whose order IS its meaning that is not a new topic, it is
# an invalid board. `VoiceSignal` refuses phases that are not in time order (its own header says so), and at
# `offset=7` the fixture handed it 0.45, 0.78, 0.15: the register threw, and `prop_reach` recorded it as the
# one register of 170 it could not measure. A fixture bug wearing a register's name, which is the failure
# this file already carries three other fixes for.
#
# So a row's ORDERED fields stay where they are and only the copy travels. Ordered means: the field is
# numeric and the column it forms is monotonic in the shape as written — which is a property of the data,
# not a list of blessed field names, so a register added tomorrow with a `t`/`from`/`step` column gets it.
_MONOTONIC_MIN = 3


def _ordered_cols(rows):
    """The keys whose column is a monotonic run of numbers across `rows` — the order is the meaning."""
    if not isinstance(rows, list) or len(rows) < 2 or not all(isinstance(r, dict) for r in rows):
        return set()
    out = set()
    for k in rows[0]:
        col = [r.get(k) for r in rows]
        if len(col) < 2 or not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in col):
            continue
        if len(rows) >= _MONOTONIC_MIN or len(set(col)) == len(col):
            if all(a < b for a, b in zip(col, col[1:])) or all(a > b for a, b in zip(col, col[1:])):
                out.add(k)
    return out


def _rotate_rows(rows, off):
    """`rows` rotated for its COPY, with every ordered column left in place."""
    n = len(rows)
    if not n:
        return rows
    keep = _ordered_cols(rows)
    k = _turn(n, off)
    turned = rows[k:] + rows[:k]
    if not keep:
        return turned
    return [{**r, **{k: rows[i][k] for k in keep if k in rows[i]}} for i, r in enumerate(turned)]


def _shape_array(prop, ty, off=0):
    """`off` rotates the fixed lists the same way the role pools rotate, so a second prop set really is
    different copy rather than the same list twice — see cjk_props(offset=)."""
    def _rot(seq):
        seq = list(seq)
        if not seq:
            return seq
        if all(isinstance(r, dict) for r in seq):
            return _rotate_rows(seq, off)
        k = _turn(len(seq), off)
        return seq[k:] + seq[:k]
    t = ty.replace(" ", "")
    if prop == "items" and t.startswith("[string,string,string]"):
        return _rot(list(_ITEMS[:3]))                    # a fixed-arity tuple, not an open list
    if prop == "lines" and "Tok" in ty:
        return _rot(["读取授权目录里的表格", "按类型分类归档", "交付可验收的成果"])   # (Tok[] | string)[]
    if prop in _ARRAY_SHAPES:
        shape = _ARRAY_SHAPES[prop]
        return _rot(shape) if isinstance(shape, list) else shape
    if prop == "rows" and "string[]" in ty.replace(" ", ""):
        return _rot(list(_ITEMS[:3]))
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

# The probe lands in the CLOSE on purpose — type that is never drawn is never cut off, so the frame the
# gate judges has to be the one that should be holding everything. It was a literal in one place and the
# alternate probes below need to derive from it, because two copies of this number would let them drift.
PROBE_FRAC = 0.88

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


# WHERE A REGISTER'S `src` RESOLVES. The library sweep's evidence fixtures live in remotion/public; a FILM's
# assets live in the film's own out_dir, which is what render_remotion serves (`--public-dir=<out_dir>`). This
# was always the library's folder, so in film mode every register drawing the film's own pictures failed to
# render — StateSheet's seventeen sprites were reported as "FAILED TO RENDER" on a film that rendered fine.
# text_safe_qa had the same blind spot and was fixed the same way (`audit_shot(..., public_dir=)`).
PUBLIC_DIR = os.path.join(_REMOTION, "public")


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
                        "--public-dir=" + PUBLIC_DIR],
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
                        "--public-dir=" + PUBLIC_DIR],
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


def _why_it_refused(blob):
    """The register's OWN message, not the last line of the stack.

    "It printed the last line of the failure, which is always `at process.processTicksAndRejections
    (node:internal/…)`" — the third of the four bugs behind this coverage pass, in the sibling ink gate.
    A remotion failure prints its reason on a line that carries `Error`; everything after it is the stack,
    and the stack names nothing a reader can act on. PortRail's real message — "seats 1-6 modules on its
    rail (got 9 across the groups)" — says the FIXTURE is wrong, which is the whole difference between a
    broken register and a broken gate."""
    lines = [l.strip() for l in (blob or "").splitlines() if l.strip()]
    named = [l for l in lines
             if ("Error" in l or "error" in l) and " at " not in l and not l.startswith("at ")]
    prose = [l for l in lines if not l.startswith("at ")]
    if named or prose:
        pick = (named or prose)[0]
        return re.sub(r"^\W*(Error|ERROR)\b\s*", "", pick)[:240]
    if not lines:
        return "(the render produced no output at all)"
    # EVERY LINE IS STACK. Say that, rather than printing one and letting it read as the reason — which is
    # the non-reason this function exists to stop ("at process.processTicksAndRejections (node:internal/…)").
    return "(the render printed %d line(s) of stack and no message: %s)" % (len(lines), lines[0][:150])


def audit(shot, props, frame, tmp, dna=DEFAULT_DNA, aspect=None, why=None):
    """[] clean · [collision…] · None when the render itself failed.

    `why` is an optional list the reason is appended to. The failure reason used to be discarded entirely —
    `sweep` recorded `failed: True` and the report printed a bare list of names, so a register the gate's
    own fixture had broken was indistinguishable from one that is broken."""
    _refuse_if_instrument_is_mutated()
    payload = dict(props)
    payload["typeCollisions"] = True
    payload["dna"] = dna
    if aspect:
        payload["aspect"] = aspect
    pf = tmp + ".props.json"
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, allow_nan=False)
    cmd = ["npx", "remotion", "still", "src/index.ts", shot, tmp,
           "--frame=%d" % frame, "--gl=angle", "--log=error", "--props=" + os.path.abspath(pf),
           "--public-dir=" + PUBLIC_DIR]
    # A FLAKY RENDER IS NOT A TYPE DEFECT, AND IT LEFT THE MEASUREMENT IN SILENCE. `StateSheet` came back
    # FAILED TO RENDER in a full 170-register sweep and rendered clean on its own seconds later — a browser
    # that dies under a loaded sweep, the failure mode `text_safe_qa.audit_shot` already retries for. One
    # retry, and what survives it is reported with its own message.
    for _attempt in (1, 2):
        r = subprocess.run(cmd, cwd=_REMOTION, capture_output=True, text=True)
        err = (r.stderr or "") + (r.stdout or "")
        if TAG in err or r.returncode == 0:
            break
    if why is not None and TAG not in err and r.returncode != 0:
        why.append(_why_it_refused(err))
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
        # A SEQUENTIAL REGISTER CANNOT HOLD EVERYTHING AT ONE FRAME, and asking it to is a question with a
        # wrong answer built in. `VoiceSignal` is a timeline that shows ONE phase at a time — that is what a
        # timeline IS — so at the close it draws the last label and two of three are legitimately absent.
        # The gate reported "2 of 3 strings never reached the screen" for as long as this fixture existed;
        # the fix applied last time varied the phases' timestamps, which changed WHICH label shows and not
        # that only one can, so the finding survived its own repair wearing a different label.
        #
        # The distinction is measurable, so it is measured rather than declared: probe two earlier frames
        # and take the UNION. A string that appears at some point was drawn — nothing was dropped. A string
        # that appears at NO probe is the WordTunnel case this branch exists for, and still reported. No
        # register is exempted by name, and the extra renders happen only on a frame that already looked
        # empty — three registers in the last full sweep.
        if missing:
            for frac_t in (0.45, 0.65):
                alt = int(round(frame / PROBE_FRAC * frac_t))
                if alt <= 0 or alt == frame:
                    continue
                seen_there = _fed_missing(shot, props, alt, tmp, dna, aspect, fed)
                if seen_there is None:
                    continue
                missing = [x for x in missing if x in seen_there]
                if not missing:
                    break
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
    """{shot: {'hits': [...], 'untestable': [...], 'failed': bool, 'why': str|None, 'cjk_fed': int}}

    `cjk_fed` IS THE COVERAGE, and it was the number nobody had. This gate's headline counted registers that
    RENDERED; a register renders perfectly well on its own English demo defaults, so a register the shaper
    fed no Chinese at all was swept, measured, found clean, and counted in a line that reads "rendered with
    Chinese copy". `audit()` only asks which fed strings reached the screen when the frame already looks
    empty — a busy frame short-circuits to clean before the question is put. Counting the CJK leaves that
    went in costs nothing and makes the claim checkable."""
    durs = durations()
    ev = evidence_props()
    out = {}
    tmp = os.path.join(_REMOTION, ".cjk_type_probe.%d.png" % os.getpid())
    for n in names:
        props, untestable = (film_props.get(n), []) if film_props else cjk_props(n)
        if props is None:
            props, untestable = cjk_props(n)
        if n in ev:
            # a plate register needs its picture to draw at all — but a FILM already gave it its own. The
            # fixture used to win over the film's props, so StateSheet's seventeen real sprites were replaced
            # by the library's stand-in, which lives in remotion/public and 404s under the film's asset root:
            # the film rendered fine and this gate reported it as FAILED TO RENDER. Fill only what is missing.
            given = film_props.get(n) if film_props else None
            props = dict(ev[n], **props) if given else dict(props, **ev[n])
        frame = int(durs.get(n, 150) * PROBE_FRAC)
        why = []
        hits = audit(n, props, frame, tmp, dna, aspect, why=why)
        out[n] = {"hits": hits or [], "untestable": untestable, "failed": hits is None,
                  "why": (why[0] if why else None),
                  "cjk_fed": len([x for x in _string_leaves(props) if _HAS_CJK.search(x)])}
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
    ap = argparse.ArgumentParser(
        description="Does the type hold together in Chinese? "
                    "EXIT 0 = measured its whole universe and found nothing · 1 = findings · "
                    "2 = part of the universe was NOT measured (a register that refused to render, one no "
                    "Chinese copy could be shaped for, a --only name that is not a register, a beat that "
                    "selects none). The headline is `measured N of M`, never a bare N.")
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
        worst, per = 0, []
        aspects = _cb.aspect_table()
        for asp in aspects:
            print("### aspect %s" % asp, flush=True)
            rc = main(rest + ["--aspect=" + asp])
            per.append((asp, rc))
            worst = max(worst, rc)
        # AN AGGREGATE, BECAUSE THE SUB-RUNS SCROLL PAST. Each aspect prints its own `measured N of M`, and
        # a reader who ran five of them sees the LAST one. `worst` already carried the exit code; this says
        # which aspect earned it, in the same honesty the per-aspect headline has.
        print("### %d aspect(s) swept: %s" % (len(aspects), " · ".join(
            "%s %s" % (a_, {0: "clean", 1: "FINDINGS", 2: "coverage hole"}.get(rc_, "rc=%d" % rc_))
            for a_, rc_ in per)))
        return worst
    film_props = None
    library = sorted(os.path.basename(f)[:-4] for f in glob.glob(os.path.join(_SHOTS, "*.tsx")))
    # WHICH UNIVERSE THIS RUN COVERS, said out loud. Three modes, three universes, and the same headline
    # was printed for all of them: the catalogue, one film's beats, and whatever `--only` named.
    universe, scope, left_out = len(library), "registers in shots/", []
    if a.only:
        names = [x.strip() for x in a.only.split(",") if x.strip()]
        # `--only` NAMED NOTHING BACK. A name that is not a register was swept anyway: `prop_signature`
        # returns ({}, "") for a file it cannot open, the render then dies on an unknown composition, and
        # the run reported it as a register that FAILED TO RENDER. `text_safe_qa --only` already refuses
        # this; the list it checks against is the shots directory, never a restated one.
        unknown = [n for n in names if n not in set(library)]
        if unknown:
            print("[cjk_type] --only names %d thing(s) that are not registers in shots/: %s"
                  % (len(unknown), ", ".join(unknown)))
            return 2
        universe, scope = len(names), "registers named by --only, of %d in shots/" % len(library)
    elif a.out_dir:
        global PUBLIC_DIR
        PUBLIC_DIR = os.path.abspath(a.out_dir)        # the film's own assets, as the renderer serves them
        board = json.load(open(os.path.join(a.out_dir, "storyboard.json"), encoding="utf-8"))
        names, film_props = [], {}
        beats = board.get("slides") or []
        for i, s in enumerate(beats, 1):
            if not s.get("shot"):
                left_out.append(("scene %02d" % i, "selects no register (a still or image beat) — this "
                                                   "audit reads a register's type and has none to read"))
                continue
            import render_remotion as _rr            # the renderer's own reading of a beat's props
            names.append(s["shot"]); film_props[s["shot"]] = _rr.film_shot_props(s, a.out_dir)
        a.aspect = a.aspect or (board.get("meta") or {}).get("aspect")
        names = sorted(set(names))
        # A FILM SWEEPS DISTINCT REGISTERS, NOT BEATS — two beats on one register are one render here.
        # The line must say so, or "measured 6" reads as six of the film's twelve beats.
        universe, scope = len(names), "distinct registers across %d beat(s)" % len(beats)
    else:
        names = library
    res = sweep(names, a.dna, a.aspect, film_props)
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
    # NOT MEASURED, by the only definition that means anything for THIS gate: a register whose frame carries
    # no Chinese the fixture put there. Three ways in, and each used to read as a pass:
    #   the render failed          — printed as a bare name, no reason, and did not affect the exit code
    #   no CJK copy was shaped     — swept in its own ENGLISH demo defaults and reported clean
    #   a prop could not be shaped — reported, but under a heading that does not reach the headline
    nofeed = [n for n, v in res.items() if not v["failed"] and not v.get("cjk_fed")]
    notmeasured = ([(n, "refused to render — %s" % (res[n].get("why") or "(the render gave no message)"))
                    for n in sorted(failed)]
                   + [(n, "no Chinese copy could be shaped for its props, so its frame was measured in its "
                          "own English demo defaults") for n in sorted(nofeed)]
                   + [(n, "props no Chinese copy could be shaped for: %s" % ", ".join(untest[n]))
                      for n in sorted(untest) if n not in set(failed) | set(nofeed)])
    # `left_out` is a BEAT-level item on a different axis from the register count (a film's universe here is
    # its DISTINCT registers), so it is counted in its own clause rather than subtracted from `of M` — where
    # "measured 1 of 1 · 1 not measured" would be arithmetic a reader cannot follow.
    measured = len(res) - len(failed) - len(nofeed)
    if a.json:
        print(json.dumps(dict(res, _coverage={"universe": universe, "scope": scope, "measured": measured,
                                              "not_measured": [list(x) for x in notmeasured],
                                              "beats_without_a_register": [list(x) for x in left_out]}),
                         ensure_ascii=False, indent=2))
    if not a.json:
        cov = bundled_cjk_coverage()
        if cov is not None and not any(has for _, has in cov):
            print("[cjk_type] NONE of the %d bundled faces can draw Chinese — every CJK glyph in every film "
                  "is\n           set by whatever font the render machine has installed, so the Design DNA's "
                  "typography\n           does nothing on a CJK film (measured: 0px apart across two DNAs; "
                  "93px in English).\n           Bundle a CJK face in assets/fonts + runtime/fonts.ts to fix "
                  "it." % len(cov))
        # MEASURED N OF M, NEVER A BARE N. "151 register(s) rendered with Chinese copy" has no denominator
        # in it, so the same sentence describes a full sweep and one that lost nineteen registers — and it
        # said "with Chinese copy" of every register that rendered, including any the shaper fed none.
        print("[cjk_type] measured %d of %d %s · %d not measured%s"
              % (measured, universe, scope, len(notmeasured),
                 " · %d beat(s) select no register" % len(left_out) if left_out else ""))
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
        # (the old standalone "NOT TESTED" block is gone — it listed the same registers, truncated at 14,
        #  under a heading the headline never referenced. They are in NOT MEASURED below, all of them.)
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
        if notmeasured or left_out:
            # ONE LIST, WITH A REASON PER LINE. "FAILED TO RENDER: PortRail, StateSheet" was the whole of
            # what a reader got, and neither name was a register defect: PortRail refused the gate's OWN
            # fixture (it was fed two spellings of one rail at once) and StateSheet was a browser that died
            # under a loaded sweep. A bare name cannot be acted on; the register's own message can.
            print("\nNOT MEASURED — this run says nothing about these (%d register(s) of %d%s):"
                  % (len(notmeasured), universe,
                     ", and %d beat(s) that select none" % len(left_out) if left_out else ""))
            for n, whynot in notmeasured + left_out:
                print("    %-22s %s" % (n, whynot))
        if not lead:
            print("\nNo register sets Chinese copy into itself.")
    # A COVERAGE HOLE IS NOT A CLEAN RUN. The exit code counted `lead or unfed or unmeas` only, so a sweep
    # that failed to render part of its universe — the 2 this pass found on the real library — returned 0.
    return 1 if (lead or unfed or unmeas) else (2 if (notmeasured or left_out) else 0)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
