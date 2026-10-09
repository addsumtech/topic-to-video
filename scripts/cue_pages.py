#!/usr/bin/env python3
"""Propose (or write) `data-cue` + `data-cue-index` on an HTML-tier film's revealable text elements.

An HTML page that carries no anchors reveals on its own animation clock, so text lands seconds after
(or before) the voice names it. Hand-writing every anchor is the chore this removes: for each beat's page
it finds the elements seek.js can move (a `reveal*` / `settle` / `count-up` class), matches each element's
text to the narration with sync_qa.match_spoken — the SAME matcher the sync gate judges with — and gives
the element the phrase the voice says plus an index in spoken order.

  python3 cue_pages.py <out_dir>            # print the proposal, touch nothing
  python3 cue_pages.py <out_dir> --write --retarget   # also re-point a hand-written anchor that lands >1 s late
  python3 cue_pages.py <out_dir> --write    # rewrite pages/scene_NN.html in place (first .bak kept)

Never overwrites an anchor an author wrote unless --retarget is given (a late one is reported either way): an element that already has data-cue / data-cue-index is left
as it is (existing indices are only renumbered, consistently, so new anchors can slot into spoken order).
An element the voice never says is NOT cued — it is listed, and the author decides."""
import argparse, json, os, re, shutil, sys
from html.parser import HTMLParser
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cues as _cues
import sync_qa as _sq

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
REVEAL = re.compile(r"^(reveal[\w-]*|settle|count-up)$")
LATE_DISPUTE = 1.0  # s: an existing anchor this far after its own text is spoken is reported (the gate's LATE bar is 1.5)
TOL = 0.6          # s: a proposed phrase must resolve (as the render resolves it) this close to the matched word


class _Page(HTMLParser):
    """Every start tag with its byte span, classes, attrs and (descendant-inclusive) visible text."""
    def __init__(self, src):
        super().__init__(convert_charrefs=True)
        self.src, self.els, self.stack, self.skip = src, [], [], 0
        self.lines = [0]
        for ln in src.split("\n"):
            self.lines.append(self.lines[-1] + len(ln) + 1)

    def _off(self):
        l, c = self.getpos()
        return self.lines[l - 1] + c

    def handle_starttag(self, tag, attrs):
        raw = self.get_starttag_text()
        a = self._off()
        if tag in ("script", "style"):
            self.skip += 1
        el = {"tag": tag, "a": a, "b": a + len(raw), "attrs": dict(attrs), "text": [], "own": [], "kids": [], "parent": None}
        if self.stack:
            el["parent"] = self.stack[-1]
            self.stack[-1]["kids"].append(el)
        self.els.append(el)
        if tag not in VOID and not raw.endswith("/>"):
            self.stack.append(el)

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.skip:
            self.skip -= 1
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i]["tag"] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data):
        if self.skip:
            return
        for el in self.stack:
            el["text"].append(data)
        if self.stack:
            self.stack[-1]["own"].append(data)


def _text(el):
    return re.sub(r"\s+", " ", "".join(el["text"])).strip()


def _classes(el):
    return (el["attrs"].get("class") or "").split()


def scan(src):
    p = _Page(src)
    p.feed(src)
    p.close()
    return p.els


def _anchored(el):
    return "data-cue-index" in el["attrs"] or "data-cue" in el["attrs"]


def _bad_phrase(s):
    return (not s) or any(ch in s for ch in "\"'<>&")


def _literal(said, narration):
    """The narration's OWN spelling of what the matcher said (it lowercases and spaces units: '的 ai 模型'),
    because validate wants an anchor that is a literal substring of the narration. '' if it can't be found."""
    chars = [c for c in said if not c.isspace()]
    if not chars or not narration:
        return ""
    m = re.search(r"[\W_]*".join(re.escape(c) for c in chars), narration, re.IGNORECASE)
    if not m:
        return ""
    # stop at the first punctuation: the voice's word stream carries none, so an anchor spanning "OpenAI，参与"
    # would never match it (and the render would interpolate instead of firing on the word)
    head = re.match(r"[\w\s]+", m.group(0).strip())
    return (head.group(0) if head else m.group(0)).strip()


def _phrases(tg, narration):
    """Candidate anchors for a target, best first: the narration's own wording of it, then the element's text.
    Only a phrase that IS in the narration is a candidate."""
    out = []
    for x in (_literal(tg[1], narration), tg[2]):
        if x and not _bad_phrase(x) and _cues._anchor_pos(narration, x) >= 0 and x not in out:
            out.append(x)
    return out


def _target(el, spoken):
    """(t, said, text) for the EARLIEST spoken moment among the text an element carries — an element has one
    reveal time, so it must land by the first of its lines the voice names, or that line is late. None when
    the voice names none of it."""
    best = None
    stack = [el]
    while stack:
        e = stack.pop()
        stack.extend(e["kids"])
        own = re.sub(r"\s+", " ", "".join(e["own"])).strip()
        if not own:
            continue
        hit = _sq.match_spoken(own, spoken)
        if hit is not None and (best is None or hit[1] < best[0]):
            best = (float(hit[1]), hit[2], own)
    return best


def plan_page(src, spoken, words, retarget=False, narration=""):
    """(inserts, unmatched, renumber, els, disputed) for one page.
    inserts: [{el, phrase, t, index, old}]; unmatched: [(text, reason)]; renumber: {old_index: new_index};
    disputed: [(text, anchor, lag, suggested)] — hand-written anchors that land late on their own text
    (changed only with retarget=True)."""
    els = scan(src)
    cand, unmatched, disputed = [], [], []
    groups = {}
    for el in els:
        ci = el["attrs"].get("data-cue-index")
        if ci is not None and ci.isdigit():
            g = groups.setdefault(int(ci), {"phrase": None, "els": []})
            g["els"].append(el)
            if el["attrs"].get("data-cue") and g["phrase"] is None:
                g["phrase"] = el["attrs"]["data-cue"]
    old = sorted(groups)
    old_t = {}
    if old:
        for i, t in zip(old, _cues.resolve_cues(words, [groups[i]["phrase"] or "" for i in old])):
            old_t[i] = t
    for el in els:
        if _anchored(el):
            continue
        if not any(REVEAL.match(c) for c in _classes(el)):
            continue
        tg = _target(el, spoken)
        if tg is None:
            if _text(el):
                unmatched.append((_text(el), "the voice never says it"))
            continue
        cand.append({"el": el, "t": tg[0], "texts": _phrases(tg, narration), "k": 0,
                     "text": _text(el), "old": None})
    # a hand-written anchor that lands well after the voice names its own text
    for i in old:
        g = groups[i]
        if not g["phrase"]:
            continue
        el = next((e for e in g["els"] if e["attrs"].get("data-cue") == g["phrase"]), None)
        tg = _target(el, spoken) if el else None
        if tg is None or old_t[i] - tg[0] <= LATE_DISPUTE:
            continue
        sug = next(iter(_phrases(tg, narration)), None)
        disputed.append((_text(el), g["phrase"], old_t[i] - tg[0], sug))
        if retarget and sug:
            cand.append({"el": el, "t": tg[0], "texts": _phrases(tg, narration), "k": 0,
                         "text": _text(el), "old": i})
    # a container revealed AFTER one of its own cued descendants would hide it: let the children carry the cues
    ids = {id(c["el"]): c for c in cand}
    for c in list(cand):
        p = c["el"]["parent"]
        while p is not None:
            pc = ids.get(id(p))
            if pc is not None and pc in cand and pc["old"] is None and pc["t"] > c["t"] + 0.1:
                cand.remove(pc)
                unmatched.append((pc["text"], "a container: its children are cued individually"))
            p = p["parent"]
    retargeted = {c["old"] for c in cand if c["old"] is not None}
    while True:                                        # pick phrases that RESOLVE where the voice says them
        for c in [c for c in cand if c["k"] >= len(c["texts"])]:
            cand.remove(c)
            if c["old"] is None:
                unmatched.append((c["text"], "no phrase of it resolves to the spoken word (repeated or normalised wording)"))
            else:
                retargeted.discard(c["old"])
        items = [("old", i, old_t[i]) for i in old if i not in retargeted] + [("new", c, c["t"]) for c in cand]
        items.sort(key=lambda x: x[2])
        phrases = [(groups[x[1]]["phrase"] or "") if x[0] == "old" else x[1]["texts"][x[1]["k"]] for x in items]
        res = _cues.resolve_cues(words, phrases) if items else []
        bad = next((x[1] for x, r in zip(items, res) if x[0] == "new" and abs(r - x[1]["t"]) > TOL), None)
        if bad is None:
            break
        bad["k"] += 1
    renumber, inserts = {}, []
    for n, x in enumerate(items):
        if x[0] == "old":
            renumber[x[1]] = n
        else:
            c = x[1]
            inserts.append({"el": c["el"], "phrase": c["texts"][c["k"]], "t": c["t"], "index": n, "old": c["old"]})
            if c["old"] is not None:
                renumber[c["old"]] = n
    return inserts, unmatched, renumber, els, disputed


def apply(src, inserts, renumber, els):
    edits = []                                         # (a, b, replacement) on start tags, applied back to front
    new_by_el = {id(i["el"]): i for i in inserts}
    for el in els:
        raw = src[el["a"]:el["b"]]
        ci = el["attrs"].get("data-cue-index")
        if id(el) in new_by_el:
            i = new_by_el[id(el)]
            if i["old"] is not None:                    # --retarget: the author's own anchor, now pointing at the right words
                r = re.sub(r"""(data-cue\s*=\s*)(["'])[^"']*\2""", lambda m: '%s"%s"' % (m.group(1), i["phrase"]), raw, count=1)
                r = re.sub(r"""(data-cue-index\s*=\s*["'])\d+(["'])""", lambda m: m.group(1) + str(i["index"]) + m.group(2), r, count=1)
                edits.append((el["a"], el["b"], r))
                continue
            tail = "/>" if raw.endswith("/>") else ">"
            body = raw[:-len(tail)].rstrip()
            edits.append((el["a"], el["b"], '%s data-cue="%s" data-cue-index="%d"%s' % (body, i["phrase"], i["index"], tail)))
        elif ci is not None and ci.isdigit() and renumber.get(int(ci), int(ci)) != int(ci):
            new = re.sub(r"""(data-cue-index\s*=\s*["'])\d+(["'])""",
                         lambda m: m.group(1) + str(renumber[int(ci)]) + m.group(2), raw, count=1)
            edits.append((el["a"], el["b"], new))
    for a, b, r in sorted(edits, reverse=True):
        src = src[:a] + r + src[b:]
    return src


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("out_dir")
    ap.add_argument("--write", action="store_true", help="rewrite the pages in place (first .bak kept)")
    ap.add_argument("--retarget", action="store_true",
                    help="ALSO re-point a hand-written anchor that lands >1 s after its own text is spoken")
    a = ap.parse_args(argv)
    sb = json.load(open(os.path.join(a.out_dir, "storyboard.json"), encoding="utf-8"))
    total = changed = 0
    for s in sb.get("slides", []):
        if s.get("type") != "html" or not isinstance(s.get("index"), int):
            continue
        page = os.path.join(a.out_dir, "pages", "scene_%02d.html" % s["index"])
        words = _sq.words_for(a.out_dir, s)
        narr = _sq.narration_of(s)
        if not os.path.exists(page) or not words or not narr.strip():
            print("scene %02d: skipped (%s)" % (s["index"], "no page" if not os.path.exists(page) else "no word timings / narration"))
            continue
        src = open(page, encoding="utf-8").read()
        spoken, _ = _sq.spoken_units(narr, words, s.get("duration"))
        ins, un, ren, els, disp = plan_page(src, spoken, words, a.retarget, narr)
        moved = {k: v for k, v in ren.items() if k != v}
        print("scene %02d: %d to cue, %d left alone%s" % (s["index"], len(ins), len(un),
                                                         ", existing indices renumbered %s" % moved if moved and ins else ""))
        for i in sorted(ins, key=lambda i: i["index"]):
            print('  + data-cue-index=%d  data-cue="%s"  @%.2fs  <%s> %s' % (i["index"], i["phrase"], i["t"], i["el"]["tag"], _text(i["el"])[:40]))
        for txt, anchor, lag, sug in disp:
            print("  ! your anchor %r lands %.1fs after %r is spoken%s" % (anchor, lag, txt[:30], (" — suggest %r; --retarget applies it" % sug)
                  if sug and not a.retarget else ""))
        for txt, why in un:
            print("  ? left alone: %r — %s" % (txt[:40], why))
        total += len(ins)
        if ins and a.write:
            bak = page + ".bak"
            if not os.path.exists(bak):
                shutil.copy2(page, bak)
            open(page, "w", encoding="utf-8").write(apply(src, ins, ren, els))
            changed += 1
    print("%s %d element(s) across %d page(s)%s" % ("cued" if a.write else "would cue", total, changed if a.write else 0,
                                                    "" if a.write else " (re-run with --write to apply)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
