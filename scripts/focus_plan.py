#!/usr/bin/env python3
"""Focus plan — which listed item LEADS the frame while the voice talks about it (Film.tsx FocusLayer draws it).

WHY. craft_qa (scripts/craft_qa.py) measured our beats letting several equal elements share the frame: the largest
element held 48% of the layout against 63% on 28 published launch films, 3 elements against 2, and 116 of 311 beats had
no element leading at all. Most of them are LISTS — callouts, steps, rows, parts — drawn at one weight for the whole
beat while the voice talks about one item at a time. An explainer's oldest answer is to light the item being talked
about and let the rest recede; the narration already says which one, so the plan is read from it, never authored.

THE RULES.
  * items    only the items of a LIST prop with two or more of them (`parts.0`, `steps.2` — sync_qa.item_texts is the one
             definition of an item and its text). A title, a kicker or a caption is not a candidate: dimming a list's
             siblings is a hierarchy between peers; dimming a headline is not.
  * peers    a sentence set as lines of type is not a list: props named for the narration's own text (`lines`,
             `words`, `tokens`, `context`, `headers`) are never focused, nor is any list most of whose items END
             in clause punctuation or carry the `*emphasis*` markup — measured on our corpus, HeadlineReveal and
             SkyPlate set one sentence as `lines`, and dimming the half of a headline the voice has passed breaks it.
  * naming   a clause names an item when the item's text is MENTIONED in it — sync_qa's own test (`best_match` with
             `_run_ok`, and the coverage rule `match_spoken` applies), so the sync audit, the cues and the focus can never
             disagree about what the voice said. Two named: the higher-scoring run, a tie to the one said first.
  * holding  a named item keeps the lead through the rest of its sentence (「热水从这里洒下」 after 「先看分水网」 is
             still about it); another named item takes it over; after a sentence ends (。！？； . ! ? ;), a clause that
             names nothing gives the frame back to every item. A lead that dropped on every unnamed clause would pump.
  * pace     no plan at all when any hand-over would come sooner than MIN_LEAD_S after the last: measured on
             bench-rams, five principles named 0.8 s apart made the lead hop every 0.8 s — flicker, not attention.
             A voice reading a list straight through presents it as one thing.
  * clock    each change is at its clause's first spoken word (the beat's clock, as capWords). No word times: no plan —
             a lead on a guessed word is worse than none.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sync_qa as _sq                                                            # noqa: E402

MIN_LEAD_S = 1.2
FOCUS_MIN_COVERAGE = 0.3      # a lead needs a MENTION, not a shared generic word (see _named)
_CLAUSE_END = re.compile(r"[,，。；;：:!！?？、…—]")
_SENTENCE_END = re.compile(r"[。！？；.!?;]")


NOT_PEERS = frozenset(("lines", "words", "tokens", "context", "headers", "chars", "letters"))
_FRAGMENT_END = re.compile(r"[,，。；;：:!！?？、…—]\s*$")


def _fragment(text):
    return bool(_FRAGMENT_END.search(text)) or "*" in text


# A terminal's or a program's `lines` are separate ENTRIES the voice walks through (craft_qa --type named eight terminal
# beats of one film: 4.2-4.9% type over 6-18 lines, nothing leading), unlike a headline's `lines`, which are one
# sentence set as lines. Named by register, because the prop is spelled the same in both. Measured on that film
# (hermes, before/after with only this switched): its longest hold 8.4 -> 5.8 s; jitter_qa reported more lines, and
# the pixels say it is the gate: the flagged input line's trajectory matched the before to 0.21 px, and a TermDiff beat
# whose layer refused to dim (its two columns did not separate) rendered pixel-identical and still went 1 -> 6 lines.
ENTRY_LINES = re.compile(r"^(Term[A-Z]\w*|CodeCompose)$")
# The item text fields: sync_qa's (the cue matcher's) plus a commit's message, which only the lead reads — adding it to
# the shared list would hand TermGitLog cues it never had.
FOCUS_TEXT_FIELDS = ("msg",)


def _items(props):
    out = list(_sq.item_texts(props))
    seen = {k for k, _t in out}
    for k, v in (props or {}).items():
        if isinstance(v, list):
            for i, x in enumerate(v):
                key = "%s.%d" % (k, i)
                if key not in seen and isinstance(x, dict):
                    f = next((f for f in FOCUS_TEXT_FIELDS if isinstance(x.get(f), str) and x[f].strip()), None)
                    if f:
                        out.append((key, x[f]))
    return out


def item_texts_for_focus(props, shot=None):
    """{path: text} — the items of every list prop holding two or more PEERS (not a sentence set as lines)."""
    entries = bool(shot and ENTRY_LINES.match(shot))
    groups = {}
    for k, t in _items(props):
        if "." in k:
            groups.setdefault(k.rsplit(".", 1)[0], []).append((k, t))
    out = {}
    for name, items in groups.items():
        base = name.split(".")[-1]
        if len(items) < 2 or (base in NOT_PEERS and not (entries and base == "lines")):
            continue
        if not entries and sum(_fragment(t) for _k, t in items) * 2 > len(items):
            continue
        out.update(items)
    return out


def focus_items(props, plan, shot=None):
    """{path: text} the layer dims between — the items of every list the PLAN names, and no other. A beat's other list
    is not their peer, and one the frame draws as no text (ids like `active: ["evap", …]`, measured on a fridge film)
    makes the layer find no element for it and refuse the whole beat."""
    named = {k["key"].rsplit(".", 1)[0] for k in plan or [] if k.get("key")}
    return {k: t for k, t in item_texts_for_focus(props, shot=shot).items() if k.rsplit(".", 1)[0] in named}


def _clauses(spans, caption):
    """[(onset seconds, clause text, ends a sentence)] in spoken order."""
    out = []
    spans = sorted((s for s in spans if "t" in s), key=lambda s: int(s.get("a", 0)))
    if not spans:
        return out
    bounds = [m.end() for m in _CLAUSE_END.finditer(caption)]
    start = 0
    for end in bounds + [len(caption)]:
        inside = [s for s in spans if start <= int(s["a"]) < end]
        if inside:
            text = caption[start:end]
            out.append((float(inside[0]["t"]), text, bool(_SENTENCE_END.search(text[-1:] or ""))))
        start = end
    return out


def _named(clause, items):
    """The path of the item this clause mentions, or None."""
    cu = _sq.units(clause)
    best = None
    for key, text in items.items():
        tu = _sq.units(text)
        hit = _sq.best_match(tu, cu)
        if hit is None:
            continue
        j0, k, i0 = hit
        sc = _sq._score(tu[i0:i0 + k])
        # stricter than the cue matcher's 15%: on hermes, 模型 alone (2 of 11 characters) lit the wrong line
        if sc < _sq.MIN_RUN_SCORE and sc < FOCUS_MIN_COVERAGE * _sq._score(tu):
            continue
        rank = (sc, -j0)
        if best is None or rank > best[0]:
            best = (rank, key)
    return best[1] if best else None


def focus_plan(props, spans, caption, duration, shot=None):
    """[{t, key}] — at second t the item `key` leads (None: every item at full weight again). [] for no plan."""
    items = item_texts_for_focus(props, shot=shot)
    if not items or not spans or not caption:
        return []
    plan, current, after_sentence = [], None, False
    for t, text, ends in _clauses(spans, caption):
        if t >= duration:
            break
        named = _named(text, items)
        if named is not None and named != current:
            plan.append({"t": round(t, 3), "key": named})
            current = named
        elif named is None and current is not None and after_sentence:
            plan.append({"t": round(t, 3), "key": None})
            current = None
        after_sentence = ends
    if any(b["t"] - a["t"] < MIN_LEAD_S for a, b in zip(plan, plan[1:])):
        return []
    return plan
