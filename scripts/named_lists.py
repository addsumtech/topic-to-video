#!/usr/bin/env python3
"""The lists a voice names, and whether the board says how each item is shown.

WHY. The WorkBuddy film (2026-11-08): beat 2 said "A report. A spreadsheet. A deck." over three identical blank cards,
and beat 8 named the list again, differently ("a spreadsheet, a report, a dashboard"). The user: 最开始的三个空白，但是
你说的是report，sheet，deck，没有相应显示内容，而且后面有一个frame也又提到了这三个. The decodability rule lived in prose
(references/remotion-shot-authoring.md: "a tile's picture should be decodable as THAT thing with the label hidden");
the beat's own ideal — written by the director — contradicted its voice, and nothing compared them.

WHAT A LIST IS. Three or more objects named in a row: English noun phrases each led by an article ("a report, a
spreadsheet, a deck"; "A report. A spreadsheet."; "…, and a font"), short Chinese nouns joined by 、/和/与/及 with at
least one 、. A run of adjectives ("fast, cheap and good") and a list of two are not lists. Each item's `key` is its
phrase without the article, lower-cased.

WHAT A BEAT SAYS. `shot_fit.shows`: {item: [words the picture carries] | {"by": "picture" | "voice", ...}} — the
words named_objects_qa reads off the rendered frame (a file name, a heading), or a picture with no words (the critic
judges it), or an item the voice names and the picture deliberately does not show (`why` says so).

lint(board) -> warnings: a named list with no `shows`, an item it leaves out, a `by` it does not know, and a list named
twice that does not agree (two lists sharing at least two items are the same list).
"""
import re

ARTICLE = r"(?:a|an|the)"
_SEG_EN = re.compile(r"[,.;:!?—–]+|\s+-\s+")
_ITEM_EN = re.compile(r"^\s*(?:and\s+|or\s+)?" + ARTICLE + r"\s+((?:[A-Za-z][\w'-]*)(?:\s+[A-Za-z][\w'-]*){0,2})\s*$",
                      re.I)
_LEAD_EN = re.compile(r"^.*?\b" + ARTICLE + r"\s+((?:[A-Za-z][\w'-]*)(?:\s+[A-Za-z][\w'-]*){0,2})\s*$", re.I)
_SEG_ZH = re.compile(r"[，。；：！？—]+")
_ITEM_ZH = re.compile(r"^[一-鿿]{1,8}$")
BY = ("picture", "voice")


def _key(phrase):
    return " ".join(phrase.lower().split())


def _en_lists(text):
    out, run = [], []
    for seg in _SEG_EN.split(text):
        # "a report and a deck" inside one segment: split on the joining word too
        parts = re.split(r"\s+(?:and|or)\s+(?=" + ARTICLE + r"\s)", seg, flags=re.I)
        for part in parts:
            # the FIRST item may follow a lead-in ("Pick a template, …"); every later one is the bare phrase
            m = _ITEM_EN.match(part) or (None if run else _LEAD_EN.match(part))
            if m:
                run.append({"key": _key(m.group(1)), "said": part.strip()})
                continue
            if part.strip():
                if len(run) >= 3:
                    out.append(run)
                run = []
    if len(run) >= 3:
        out.append(run)
    return out


def _zh_lists(text):
    out = []
    for seg in _SEG_ZH.split(text):
        if "、" not in seg:
            continue
        # the run of items: split on 、 then on the last joining word; the lead-in before the first item is dropped
        head, _, tail = seg.rpartition("、")
        pieces = head.split("、") + re.split(r"[和与及]", tail, maxsplit=1)
        first = pieces[0]
        for lead in ("能做", "包括", "有", "做", "是"):           # a short verb lead-in before the first noun
            if lead in first:
                first = first.split(lead)[-1]
        pieces[0] = first
        items = [p.strip() for p in pieces if p.strip()]
        if len(items) >= 3 and all(_ITEM_ZH.match(p) for p in items):
            out.append([{"key": p, "said": p} for p in items])
    return out


def lists_in(text):
    """The lists a narration names: [[{key, said}, …], …] in the order spoken."""
    text = text or ""
    return _en_lists(text) + _zh_lists(text)


def _label(slide, i):
    return slide.get("index", i + 1)


def lint(board):
    """Warnings for the named lists of a board."""
    warnings = []
    slides = board.get("slides") or []
    named = []                                   # (beat label, [keys])
    for i, s in enumerate(slides):
        lists = lists_in(s.get("narration") or "")
        if not lists:
            continue
        shows = ((s.get("shot_fit") or {}).get("shows")) or {}
        b = _label(s, i)
        for lst in lists:
            keys = [it["key"] for it in lst]
            named.append((b, keys))
            if not shows:
                warnings.append("named list (beat %s): the voice names %s — say how the picture shows each, "
                                "shot_fit.shows {item: [words the frame carries] | {\"by\": \"picture\"|\"voice\", "
                                "…}}; named_objects_qa reads them off the frame" % (b, ", ".join(keys)))
                continue
            missing = [k for k in keys if k not in shows]
            if missing:
                warnings.append("named list (beat %s): shot_fit.shows says nothing of %s" % (b, ", ".join(missing)))
            for k, how in shows.items():
                if isinstance(how, dict) and how.get("by") not in BY:
                    warnings.append("named list (beat %s): shows[%r].by %r — one of %s" % (b, k, how.get("by"),
                                                                                           ", ".join(BY)))
    for x in range(len(named)):
        for y in range(x + 1, len(named)):
            (b1, k1), (b2, k2) = named[x], named[y]
            common = set(k1) & set(k2)
            if len(common) >= 2 and set(k1) != set(k2):
                warnings.append("named list: beat %s names %s and beat %s names %s — the same list told twice must "
                                "agree (or name it differently enough to be another list)"
                                % (b1, ", ".join(k1), b2, ", ".join(k2)))
    return warnings
