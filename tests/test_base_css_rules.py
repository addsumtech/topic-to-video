"""base.css is parsed as CSS, not read as prose: a comment that closes early swallows the rule after it.

Measured on a QR-code film (2026-11-04): the comment above the component-motion rules said `(.reveal*/.draw)`, its `*/`
closed the comment there, the rest of the sentence became a selector, and the `.grow-w` rule behind it was dropped — every
page's growing bar sat at full width from frame 0. And the grow/draw rules filled `forwards` only, so a bar cued for later
showed its END state before its cue (a fact on screen before the voice says it)."""
import os
import re

CSS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "html", "base.css")


def _rules():
    s = re.sub(r"/\*.*?\*/", "", open(CSS, encoding="utf-8").read(), flags=re.S)
    return [(sel.strip(), body) for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", s)]


def test_no_comment_closes_early():
    """With the comments stripped, every selector is a selector: a comment that closed early leaves its sentence as the
    selector of the next rule (the browser drops that rule, silently)."""
    for sel, _body in _rules():
        words = [t for t in re.split(r"\s+", sel) if re.fullmatch(r"[A-Za-z]{2,}[,.;)]?", t)]
        assert len(words) < 4, "prose became a selector (a comment closed early): %r" % sel[:100]


def test_the_component_motion_rules_exist_and_hold_their_start_until_their_cue():
    sel = {s: b for s, b in _rules()}
    for name in (".grow-w", ".grow-h", ".rail-fill", ".draw-down"):
        assert name in sel, "%s is not a rule base.css applies" % name
        assert re.search(r"animation:[^;]*\bboth\b", sel[name]), (
            "%s fills forwards only: before its cue it shows its END state" % name)
