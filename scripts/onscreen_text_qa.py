#!/usr/bin/env python3
"""Text a register prints that the FILM never supplied.

  python3 scripts/onscreen_text_qa.py            # scan the whole library
  python3 scripts/onscreen_text_qa.py <Shot>…    # scan named registers

WHY. Four times in one film's review a viewer found words on screen that had nothing to do with the
subject: `WORKBUDDY™` on a title card, `©2026 · LOCAL` in a corner, `DASHBOARD` over a children's book
character, and `x:960  y:540` beside a cathedral — a screen coordinate presented as a measurement. Every
gate was green each time.

They were invisible for one reason: `shot_proof`'s demo-default check compares a beat's `shot_props`
against the register's PROP DEFAULTS, so it can only see text that is a prop. A string literal written
straight into the JSX is not a prop, has no default to differ from, and prints on every film that ever
reaches for that register whatever the film is about.

WHAT THIS DOES. It reads a register's source and finds text that reaches the screen without passing
through props. Two kinds of text are legitimate and must be declared, not guessed at:

  * a register's OWN CHROME or diagram labels — `REC` on a tape shot, `↵ run` on a command palette,
    `low spatial frequency` on a k-space axis. These belong to the form the way an axis belongs to a graph.
    Declare them:  export const INTRINSIC_TEXT = ['REC', '▶ PLAY'];
  * prop DEFAULTS, including ones declared as a module const and referenced in the destructuring. Those
    are already covered by the demo-default check, which fires when a film leaves them unset.

Anything else is reported. The fix is nearly always the same and it is worth stating: turn the literal
into a prop with the literal as its default. That keeps every existing film rendering identically AND
moves the string into the one check that already knows how to complain about it.

Exit 0 always — this is a library-hygiene report, not a per-film gate. `tests/test_remotion.py` holds the
line for NEW registers so the library cannot regrow the problem.
"""
import glob
import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_SHOTS = os.path.join(_HERE, "..", "remotion", "src", "shots")

# strings that are plainly CSS/geometry, never copy
_CSS = re.compile(r"(px|%|em|rem|deg|vh|vw|#[0-9a-fA-F]{3,8}|gradient|solid|dashed|dotted|none|absolute"
                  r"|relative|flex|center|left|right|column|row|hidden|nowrap|pointer|inherit|monospace"
                  r"|serif|sans-serif|translate|rotate|scale|blur|ease|linear|normal|bold|italic)")
# a fragment of code my reader picked up rather than copy
_CODE = re.compile(r"(&&|\|\||=>|\breturn\b|\.\w+\(|[{}();`$]|\bconst\b|\?\.|\d\.\d{2,}|\?\s?$"
                   r"|\?\s|\s:\s|===|!==|^\s*[:,]|\b[a-z]{2}-[A-Z]{2}\b)")
# TWO letters, not three. An abbreviation is copy: `No. 01` beside a Chinese headline, and `.CO — 01`
# composed into a fake domain, are exactly the class this file exists for, and both were silently dropped
# by a three-letter floor. `_CSS` and `_CODE` already carry the noise filtering; this only has to say
# "some letters are present", so a lone `·` or `—` (a form's own mark) still passes untouched.
_WORDY = re.compile(r"[A-Za-z]{2,}")
# Each quote style matched to its OWN closer. A single character class on both ends pairs the CLOSING
# quote of one string with the OPENING quote of the next, so `'north', x: 0.5, ... 'west'` yielded the
# code between them and none of the actual strings — every default in a list looked unsupplied.
_STR = re.compile(r"'([^'\n]{0,80})'|\"([^\"\n]{0,80})\"|`([^`\n]{0,80})`")


def _strings(text):
    return {(a or b or c).strip() for a, b, c in _STR.findall(text)}


def _strip_comments(src):
    src = re.sub(r"//[^\n]*", "", src)
    return re.sub(r"/\*.*?\*/", "", src, flags=re.S)


def _prop_default_text(body):
    """Every string a prop can default to — including defaults held in a module const.

    The destructuring line often reads `items: ITEMS = DEFAULT_ITEMS`, so the actual sample copy lives in
    a const above. Missing that reported a register's own defaults as unsupplied text, which is both wrong
    and the kind of noise that gets a checker ignored.
    """
    out = set()
    # GREEDY to the closing `} = {})`. Non-greedy stopped at the first inner `}`, so every default held in
    # a nested object or array — which is most of the interesting ones — looked like unsupplied text. A
    # checker that reports a register's own defaults is one nobody reads twice.
    m = re.search(r"=\s*\(\{(.*)\}\s*=\s*\{\}\)", body, re.S)
    inline = m.group(1) if m else ""
    out |= _strings(inline)
    # follow every identifier the destructuring defaults to, into its module-level const
    for ident in re.findall(r"=\s*([A-Z][A-Z0-9_]{2,})\b", inline):
        cm = re.search(r"const\s+%s\b[^=]*=\s*(.*?);\s*\n" % re.escape(ident), body, re.S)
        if cm:
            out |= _strings(cm.group(1))
    return out


def _intrinsic_readout(body):
    """A register whose numeric readout belongs to its FORM, not to any topic.

    A tape deck shows a running timecode; a frame counter counts frames. Those are the numeric analogue of
    the REC light in INTRINSIC_TEXT: they are the instrument depicting itself, not a measurement of the
    subject. Declared, never guessed:  export const INTRINSIC_READOUT = true;
    """
    return re.search(r"INTRINSIC_READOUT\s*(?::[^=]*)?=\s*true", body) is not None


def _intrinsic(body):
    """Text the register declares as belonging to its own form."""
    m = re.search(r"INTRINSIC_TEXT\s*(?::[^=]*)?=\s*\[(.*?)\]", body, re.S)
    if not m:
        return set()
    return _strings(m.group(1))


# A JSX text segment: everything between a `>` and the next `<`, allowing (non-nested) expression
# containers inside it, because a literal often sits right next to one.
# A JSX TEXT SEGMENT NEVER STARTS AT THE `>` OF AN ARROW. `(p) => p.spread <= 0.5` is ordinary TypeScript,
# and read as markup it yields the "copy" `p.spread` — which is what this gate reported about
# `OverlapSeparation`, a register that prints no such thing. A false name on a list whose whole value is that
# it is short and true teaches the reader to skim it, so the fix is on the instrument, not a suppression.
#
# Only `=` is excluded, and deliberately only `=`: `/>` opens real text (`<Foo /> then words <`), and `<>`
# is a fragment whose children are real text. Excluding either would lose findings this exists for.
_JSX_SEG = re.compile(r"(?<!=)>((?:[^<>{}]|\{[^{}]*\})*)<")


def hardcoded_defaults(path):
    """Strings a register writes BOTH as a prop default and as a bare literal on screen.

    A default exists to be overridden; a literal cannot be. When the same word is both, the register looks
    parameterised and is not — `MagazineSpread` declares `sectionLabel = 'FEATURE'` and then prints the word
    FEATURE into its image block, so a Chinese film carries an English word no prop can reach and every
    check reads it as the register's own default. Nothing else in the pipeline asks this question.
    """
    src = _strip_comments(open(path, encoding="utf-8").read())
    defaults = _prop_default_text(src) - _intrinsic(src)
    if not defaults:
        return []
    literal = set()
    for seg in _JSX_SEG.finditer(src):
        for t in re.split(r"\{[^{}]*\}", seg.group(1)):
            if t.strip():
                literal.add(t.strip())
    return sorted(defaults & literal)


def scan(path):
    src = open(path, encoding="utf-8").read()
    body = _strip_comments(src)
    known = _prop_default_text(body) | _intrinsic(body)
    found = set()
    # LITERAL TEXT BETWEEN TAGS, INCLUDING TEXT THAT SITS BESIDE AN EXPRESSION CONTAINER. The first version
    # excluded `{}` with a character class, which also excluded every literal that shares a text node with
    # one — and that is where the worst of them live: `{TITLE}.CO — 01` composes a fake DOMAIN out of the
    # film's own title, and on a Chinese film a delivered frame read 「答得更好，交付没变.CO — 01」. The gate
    # whose whole job is to find words a register prints on every film could not see it. Segments may hold
    # containers now; the containers are removed and whatever text remains is the literal.
    for seg in _JSX_SEG.finditer(body):
        for t in re.split(r"\{[^{}]*\}", seg.group(1)):
            t = t.strip()
            if 2 <= len(t) <= 60 and _WORDY.search(t) and not _CSS.search(t) and not _CODE.search(t):
                found.add(t)
    # A literal inside a JSX EXPRESSION CONTAINER. The tag-text pass above excludes `{}` by construction,
    # so `{r === 0 ? ['Metric', 'Q2', 'Q3'][c] : ...}` was invisible to the one gate whose whole job is to
    # find words a register prints on every film. It put an empty English metrics table onto a Chinese
    # film's CLIMAX frame, and this module reported that register as clean.
    for expr in re.findall(r">\s*\{([^<]{0,400}?)\}\s*<", body):
        for m in _STR.finditer(expr):
            t = (m.group(1) or m.group(2) or m.group(3) or "").strip()
            # A container also holds IDENTIFIERS — `dnaHas(dna, 'prompt')` is a feature key, not a word on
            # screen, and reporting it would train the reader to skim this list. Copy a viewer reads is
            # capitalised, spaced, or non-ASCII; a bare lowercase word is a key.
            if not t or not (any(c.isupper() for c in t) or " " in t or any(ord(c) > 127 for c in t)):
                continue
            if _WORDY.search(t) and not _CSS.search(t) and not _CODE.search(t):
                found.add(t)
    # a literal assigned to a text-bearing key
    for t in re.findall(r"(?:txt|label|text|children|word|title|caption)\s*:\s*[`'\"]([^`'\"$]{4,60})[`'\"]", body):
        t = t.strip()
        if t and _WORDY.search(t) and not _CSS.search(t) and not _CODE.search(t):
            found.add(t)
    return sorted(found - known)


def _free_ids(text):
    """Identifiers that are genuinely REFERENCED — not property accesses, not object keys.

    Both distinctions were learned from false reports. `tok.t.slice(...)` is a token's text field, and
    `{t: 0.5}` is an object whose KEY happens to be `t`; reading either as the clock variable made the
    checker accuse a register of fabricating a statistic out of its own data. A checker that cries wolf on
    the library's own code is one nobody runs a second time.
    """
    out = set()
    for m in re.finditer(r"(?<![.\w$])([A-Za-z_$][\w$]*)", text):
        before = text[:m.start()].rstrip()
        if re.match(r"\s*:", text[m.end():]) and (before.endswith("{") or before.endswith(",")):
            continue                     # an object key, not a reference (a ternary's `? x :` is preceded by ?)
        out.add(m.group(1))
    return out


def _prop_names(body):
    """The register's own prop bindings — including a renamed one (`layers: LAYERS = ...` binds LAYERS)."""
    m = re.search(r"=\s*\(\{(.*)\}\s*=\s*\{\}\)", body, re.S)
    if not m:
        return set()
    out = set()
    for part in re.split(r",(?![^\[\{]*[\]\}])", m.group(1)):
        part = part.strip()
        if not part:
            continue
        mm = re.match(r"([A-Za-z_$][\w$]*)\s*:\s*([A-Za-z_$][\w$]*)", part)
        if mm:
            out |= {mm.group(1), mm.group(2)}
            continue
        mm = re.match(r"([A-Za-z_$][\w$]*)", part)
        if mm:
            out.add(mm.group(1))
    return out


def _bindings(body):
    """[(propName, localName)] from the destructuring, split on TOP-LEVEL commas only.

    Quotes count as depth, and that is not fussiness: a default of `'springy, gummy, alive'` split into
    three "props" and two of them were reported as never read.
    """
    m = re.search(r"=\s*\(\{(.*?)\}\s*=\s*\{\}\)", body, re.S)
    if not m:
        return []
    parts, depth, quote, cur = [], 0, "", ""
    for ch in m.group(1):
        if quote:
            if ch == quote:
                quote = ""
        elif ch in "'\"`":
            quote = ch
        elif ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        elif ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
            continue
        cur += ch
    parts.append(cur)
    out = []
    for part in parts:
        mm = re.match(r"^\s*([A-Za-z_$][\w$]*)\s*(?::\s*([A-Za-z_$][\w$]*))?\s*(=|$)", part)
        if mm:
            out.append((mm.group(1), mm.group(2) or mm.group(1)))
    return out


def dead_props(path):
    """Props a register DECLARES and never reads — copy a film supplies that vanishes without a word.

    `MagazineSpread` declared `sectionLabel` and drew the word FEATURE into its JSX instead, so a Chinese
    film's `sectionLabel` was accepted and discarded and an English word appeared on the frame. Nothing in
    the pipeline asked this: `validate.py` warns about EMPTY props, `shot_proof` compares props against
    defaults — both assume that a declared prop is drawn. A dead prop passes every one of them.
    """
    body = _strip_comments(open(path, encoding="utf-8").read())
    # ANCHORED ON THE REGISTER'S OWN DECLARATION. An unanchored search finds the first `({…} = {})` in the
    # file, which on four registers is an inner helper — and their helper's locals were reported as the
    # register's dead props.
    name = os.path.basename(path)[:-4]
    m = re.search(r"export const %s: React\.FC<.*?>\s*=\s*\(\{" % re.escape(name), body, re.S)
    if not m:
        return []
    body = body[m.start():]
    m2 = re.search(r"=\s*\(\{.*?\}\s*=\s*\{\}\)", body, re.S)
    if not m2:
        return []
    after = body[m2.end():]
    return sorted({p for p, local in _bindings(body) if not re.search(r"\b%s\b" % re.escape(local), after)})


def unsourced_numbers(path):
    """NUMBERS printed on screen that no prop feeds — the class the text scan above cannot see.

    `x:960 y:540` was caught by reading it as text. `{specN}` is not text: it is an identifier in a JSX
    slot, and `const specN = Math.round(lerp(0, 100, easeOutCubic(seg(t, ...))))` computes a percentage
    from the CLOCK. It counted to 100% over a beat whose whole claim was that the cathedral's nave was
    never built, and it would have printed a confident percentage over any topic that ever used the
    register. A word-shaped scan cannot see it: there are no letters in `100%`.

    So this follows PROVENANCE instead of shape. A local const is FILM-DERIVED if it mentions a prop, or
    mentions another film-derived local (to a fixpoint). A numeric local that is rendered in a JSX slot
    and is NOT film-derived is a number the film never supplied, and is reported. Non-numeric locals are
    left alone — a JSX fragment or an accumulator array is not a fabricated statistic.
    """
    body = _strip_comments(open(path, encoding="utf-8").read())
    if _intrinsic_readout(body):
        return []
    props = _prop_names(body)
    locs = {m.group(1): m.group(2)
            for m in re.finditer(r"\bconst\s+([A-Za-z_$][\w$]*)\s*=\s*([^;\n]*)", body)}
    derived = set()
    for _ in range(8):                       # fixpoint: props -> locals -> locals -> ...
        before = len(derived)
        for n, init in locs.items():
            if _free_ids(init) & (props | derived):
                derived.add(n)
        if len(derived) == before:
            break
    slots = (set(re.findall(r">\s*\{([A-Za-z_$][\w$]*)\}", body))
             | set(re.findall(r"\{([A-Za-z_$][\w$]*)\}\s*<", body)))
    out = []

    # THE INLINE FORM OF THE SAME DEFECT. The pass below follows NAMED locals, which is how the two known
    # cases happened to be written. Written inline — `<div>{Math.round(t * 100)}%</div>` — it is the exact
    # same fabricated percentage and the named-local walk cannot see it, so the fix would have covered the
    # two instances and not the class.
    #
    # The rule here is narrower and stronger: an expression rendered on screen that depends on the CLOCK and
    # on no prop is, definitionally, a number computed from how far the shot has played. That is never a
    # measurement of anything. Keeping it to clock-dependence is what keeps `{i + 1}` — an ordinal, a
    # position in a list, intrinsic to the form the way an axis tick is — out of the report.
    clock = {"t", "frame"}
    for _ in range(8):                       # locals derived from the clock are themselves the clock
        before = len(clock)
        for n, init in locs.items():
            if _free_ids(init) & clock:
                clock.add(n)
        if len(clock) == before:
            break
    for expr in (set(re.findall(r">\s*\{([^{}<>]{3,90})\}", body))
                 | set(re.findall(r"\{([^{}<>]{3,90})\}\s*<", body))):
        expr = expr.strip()
        if re.fullmatch(r"[A-Za-z_$][\w$]*", expr):
            continue                         # a bare identifier — the named-local walk owns that case
        ids = _free_ids(expr)
        # It must PRODUCE a number. A bare digit is not enough: `tok.t.slice(0, take)` is a typewriter
        # reveal — the `0` is an argument index — and reporting it as a fabricated statistic is the kind of
        # noise that gets a checker switched off. String operations are excluded outright.
        if re.search(r"\.(slice|split|join|replace|substring|substr|repeat|concat|trim)\(", expr):
            continue
        if not re.search(r"\bMath\.\w+\(|\blerp\(|\.toFixed\(|\d", expr):
            continue                         # not numeric
        if ids & (props | derived):
            continue                         # the film feeds it
        if ids & clock:
            out.append(("<inline>", expr[:60]))

    for n in sorted(slots):
        init = locs.get(n)
        if init is None or n in derived or n in props:
            continue
        # numeric-looking only: a digit or an arithmetic helper, and not a JSX fragment
        if "<" in init or not re.search(r"\bMath\.|\blerp\(|\d", init):
            continue
        out.append((n, init.strip()[:60]))
    return out


def fixed_px_font_sites(path):
    """Font sizes written as a bare px literal, which do not scale with the frame.

    The shot tier was written at 16:9. A `44px` caption is 2.3% of a 1920-wide frame and 4.1% of a
    1080-wide portrait one, so the same register's type is half again as large at 9:16 — the defect the
    burned caption itself shipped with. 291 sites across 128 registers carry this, so it is REPORTED rather
    than enforced: a blanket rewrite of that size cannot be verified in one pass, and the layouts around
    them already reflow through fractions. New registers are held to the rule by tests.
    """
    body = _strip_comments(open(path, encoding="utf-8").read())
    return len(re.findall(r"font:\s*[`'\"][^`'\"]*?\b\d{2,3}px\s*/", body))


def main(argv):
    names = argv or [os.path.basename(f)[:-4] for f in sorted(glob.glob(os.path.join(_SHOTS, "*.tsx")))]
    total, dirty, fixed_px, unsourced = 0, 0, {}, 0
    dead, shadowed = {}, {}
    for n in names:
        p = os.path.join(_SHOTS, n + ".tsx")
        if not os.path.exists(p):
            print("[onscreen_text] no such register: %s" % n)
            continue
        px = fixed_px_font_sites(p)
        if px:
            fixed_px[n] = px
        hits = scan(p)
        if hits:
            dirty += 1
            total += len(hits)
            print("  %-24s %s" % (n, " · ".join(repr(h) for h in hits[:6])))
        d = dead_props(p)
        if d:
            dead[n] = d
        sh = hardcoded_defaults(p)
        if sh:
            shadowed[n] = sh
        nums = unsourced_numbers(p)
        if nums:
            unsourced += len(nums)
            for ident, init in nums:
                print("  %-24s NUMBER %s = %s" % (n, ident, init))
    print("[onscreen_text] %d register(s) print text the film never supplied (%d string(s))."
          % (dirty, total))
    if dirty:
        print("                Make each one a prop whose DEFAULT is the current literal — every existing "
              "film then renders identically, and shot_proof's demo-default check starts seeing it. If the "
              "text belongs to the register's own form (an axis label, a REC light), declare it instead: "
              "export const INTRINSIC_TEXT = [...].")
    if dead:
        print("[onscreen_text] %d register(s) DECLARE a prop they never read — a film's copy is accepted "
              "and\n                discarded without a word:" % len(dead))
        for n in sorted(dead):
            print("  %-24s %s" % (n, ", ".join(dead[n])))
        print("                Draw the prop, or delete it from the signature. `MagazineSpread` declared "
              "`sectionLabel`\n                and printed the word FEATURE into its JSX, so a Chinese "
              "film carried an English word\n                no prop could reach and every other check "
              "read it as the register's own default.")
    if shadowed:
        print("[onscreen_text] %d register(s) write a prop's DEFAULT as a bare literal too, so the prop "
              "cannot\n                override it:" % len(shadowed))
        for n in sorted(shadowed):
            print("  %-24s %s" % (n, " · ".join(repr(x) for x in shadowed[n][:6])))
    if unsourced:
        print("[onscreen_text] %d rendered NUMBER(s) no prop feeds — computed from the clock and printed as "
              "though measured. Give the readout a prop and draw it only when supplied; a number is real or "
              "it is absent." % unsourced)
    if fixed_px:
        n = sum(fixed_px.values())
        print("[onscreen_text] %d register(s) size type in bare px (%d sites) — that type does not scale "
              "with the frame, so it is proportionally ~1.8x larger at 9:16. Reported, not enforced; new "
              "registers should size off min(W, H)." % (len(fixed_px), n))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
