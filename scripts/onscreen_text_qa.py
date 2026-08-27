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
_CODE = re.compile(r"(&&|\|\||=>|\breturn\b|\.\w+\(|[{}();]|\bconst\b|\?\.|\d\.\d{2,}|\?\s|\s:\s)")
_WORDY = re.compile(r"[A-Za-z]{3,}")
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


def _intrinsic(body):
    """Text the register declares as belonging to its own form."""
    m = re.search(r"INTRINSIC_TEXT\s*(?::[^=]*)?=\s*\[(.*?)\]", body, re.S)
    if not m:
        return set()
    return _strings(m.group(1))


def scan(path):
    src = open(path, encoding="utf-8").read()
    body = _strip_comments(src)
    known = _prop_default_text(body) | _intrinsic(body)
    found = set()
    # literal text between tags — an expression container {..} is excluded by the character class
    for t in re.findall(r">([^<>{}]{4,60})<", body):
        t = t.strip()
        if t and _WORDY.search(t) and not _CSS.search(t) and not _CODE.search(t):
            found.add(t)
    # a literal assigned to a text-bearing key
    for t in re.findall(r"(?:txt|label|text|children|word|title|caption)\s*:\s*[`'\"]([^`'\"$]{4,60})[`'\"]", body):
        t = t.strip()
        if t and _WORDY.search(t) and not _CSS.search(t) and not _CODE.search(t):
            found.add(t)
    return sorted(found - known)


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
    total, dirty, fixed_px = 0, 0, {}
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
    print("[onscreen_text] %d register(s) print text the film never supplied (%d string(s))."
          % (dirty, total))
    if dirty:
        print("                Make each one a prop whose DEFAULT is the current literal — every existing "
              "film then renders identically, and shot_proof's demo-default check starts seeing it. If the "
              "text belongs to the register's own form (an axis label, a REC light), declare it instead: "
              "export const INTRINSIC_TEXT = [...].")
    if fixed_px:
        n = sum(fixed_px.values())
        print("[onscreen_text] %d register(s) size type in bare px (%d sites) — that type does not scale "
              "with the frame, so it is proportionally ~1.8x larger at 9:16. Reported, not enforced; new "
              "registers should size off min(W, H)." % (len(fixed_px), n))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
