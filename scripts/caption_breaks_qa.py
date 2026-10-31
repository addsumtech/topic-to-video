#!/usr/bin/env python3
"""Does any burned caption line start with closing punctuation, split a word, or end the caption on one glyph?

  python3 scripts/caption_breaks_qa.py <out_dir>          # check every beat's caption as the film will burn it
  python3 scripts/caption_breaks_qa.py <out_dir> --json

WHY THIS EXISTS. The caption HUD let the browser wrap Chinese, and a browser breaks Chinese between ANY two
characters: two 2026-10-24 benchmark films burned 「交回成 / 片」, 「GPS 怎么 / 定位」, 「抓下 / 来的原文」 and
「…加速电 / 子。」 — words cut in half and a glyph orphaned — and only a delivery reviewer's eye caught them, because no
gate looked at a caption's line breaks. Film.tsx now draws a CJK caption in the lines `remotion/src/captionBreak.ts`
decides (word boundaries from Intl.Segmenter, kinsoku, balanced), and this gate runs THAT SAME FILE in node, with the
film's own frame, platform-safe profile and caption face, so what it checks is what is burned — not a re-derivation.

  ERROR  kinsoku  a line that starts with closing punctuation (。，、！？）」…)
  ERROR  orphan   a caption whose last line is ONE CJK glyph (with or without its punctuation)
  ERROR  split    a line break inside a word (by the segmenter's own reading of the re-joined line — ICU's words;
                  the breaker is stricter still and also keeps ICU's one-character fragments together)
  ERROR  number   a line break inside a number (负 / 四, 四百 / 五十, 3.8 / kg — remotion/src/captionGlue.json)

BOTH TIERS. A Remotion film is checked in node with Film.tsx's own captionBreak.ts; an HTML / image-tier film with
render.py's own chunks and PIL lines (html_beat_faults, scripts/caption_words.py — the same rules: ICU words in plain
node, the same number spans), including a chunk boundary the hard wrap put inside a word. validate.py runs the HTML
check on every HTML film. A validation film (2026-10-31) burned 「负 / 四」 on the Remotion tier — this gate passed it:
ICU reads 负|四 as two words — and 「正方 / 形」, 「四百 / 五十」 on the HTML tier, which had no break gate at all.

A caption that cannot be broken cleanly at its measure is fixed in the COPY — reword it, or give the beat a
`caption` that splits at a full stop. `captions: false` has nothing to check. Exit 1 on an ERROR.

It also exports `srt_lines`, which render_remotion.py uses to break out.srt's CJK cues at word boundaries
(16 glyphs a line, the zh subtitle convention) with the same code.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_HERE = os.path.dirname(os.path.abspath(__file__))
_REM = os.path.join(_HERE, "..", "remotion")
_SRC = os.path.join(_REM, "src", "captionBreak.ts")
SRT_LINE_EM = 16               # glyphs a line in a zh subtitle (the common platform/Netflix convention for zh-Hans)

_ENTRY = r"""
const cb = require(%(cb)s);
const sz = require(%(sz)s);
const job = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const out = {segmenter: cb.hasSegmenter(), beats: [], srt: []};
if (job.film) {
  const {W, H, safe, font, uniform} = job.film;
  const prof = sz.safeProfile(safe, W, H);
  for (const b of job.film.beats) {
    const plan = cb.captionPlan(b.caption, W, H, prof, font || undefined, !!uniform);
    out.beats.push({beat: b.beat, chunks: plan.map((p) => ({chunk: p.chunk, cjk: p.cjk, lines: p.lines,
      faults: p.lines ? cb.lineFaults(p.lines, p.chunk) : []}))});
  }
}
for (const t of job.srt || []) {
  out.srt.push(cb.isCJKText(t) ? cb.breakLines(t, job.srt_em, (ch) => (/[　-〿㐀-鿿豈-﫿぀-ヿ가-힯＀-￯]/.test(ch) ? 1 : 0.5)) : [t]);
}
process.stdout.write(JSON.stringify(out));
"""


def _bundle(workdir):
    """captionBreak.ts and safeZone.ts as node modules (esbuild, the toolchain's own) → their paths, or None."""
    if not shutil.which("npx") or not shutil.which("node"):
        return None
    paths = {}
    for name, src in (("cb", _SRC), ("sz", os.path.join(_REM, "src", "runtime", "safeZone.ts"))):
        dst = os.path.join(workdir, name + ".cjs")
        r = subprocess.run(["npx", "esbuild", os.path.abspath(src), "--bundle", "--platform=node", "--format=cjs",
                            "--log-level=error", "--outfile=" + dst], cwd=_REM, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("could not bundle %s: %s" % (src, (r.stderr or r.stdout)[-400:]))
        paths[name] = dst
    return paths


def _run(job):
    """Run the film's caption code on `job` in node → its answer, or None when node is not here."""
    with tempfile.TemporaryDirectory() as td:
        b = _bundle(td)
        if b is None:
            return None
        entry = os.path.join(td, "entry.cjs")
        open(entry, "w", encoding="utf-8").write(_ENTRY % {"cb": json.dumps(b["cb"]), "sz": json.dumps(b["sz"])})
        jf = os.path.join(td, "job.json")
        json.dump(job, open(jf, "w", encoding="utf-8"), ensure_ascii=False)
        r = subprocess.run(["node", entry, jf], capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError("caption code failed in node: %s" % (r.stderr or "")[-600:])
        return json.loads(r.stdout)


def srt_lines(texts, em=SRT_LINE_EM):
    """[[line, ...] per text]: a CJK cue broken at word boundaries into lines of at most `em` glyphs (balanced,
    kinsoku), a Latin cue left whole for the player to wrap. None when node is unavailable (the cues stay one line)."""
    if not texts:
        return []
    res = _run({"srt": list(texts), "srt_em": em})
    return None if res is None else res["srt"]


def _font(meta):
    """(fontBody, uniformType) of the film's DNA, as far as the board names them — the caption is set in fontBody."""
    dna = (meta or {}).get("design_dna")
    try:
        import seam_plan as _sp
        d = _sp._resolve_dna(dna) or {}
    except Exception:                                  # noqa: BLE001
        d = dna if isinstance(dna, dict) else {}
    uniform = bool(d.get("uniformType")) or d.get("uniformType") == "true" or d.get("id") == "terminal" \
        or dna == "terminal"
    return d.get("fontBody"), uniform


_FAULT = {
    "kinsoku": lambda f: "line %d starts with closing punctuation" % (f["line"] + 1),
    "orphan": lambda f: "its last line is one glyph (%s)" % f["text"],
    "split": lambda f: "the break before line %d falls inside a word" % (f["line"] + 1),
    "number": lambda f: "the break before line %d falls inside a number" % (f["line"] + 1),
}


def html_beat_faults(slide, lines_of):
    """[message] for one HTML/image-tier beat's caption AS render.py BURNS IT: its chunks (an authored `captions`
    track, else the narration split by render._split_caption_chunks, hard wrap included) and each chunk's lines
    (`lines_of(text)`: render._caption_layout at the film's frame — validate._caption_lines). A break inside a number
    or a word is an error wherever it falls: between two lines of a chunk, or between two chunks of one narration
    that the hard wrap cut where no clause mark is."""
    import caption_words as cw
    import render as rd
    caps = slide.get("captions") or []
    authored = len(caps) >= 2
    narration = (slide.get("narration") or (caps[0]["text"] if caps else "") or "").strip()
    chunks = [c.get("text", "") for c in caps] if authored else rd._split_caption_chunks(narration)
    chunks = [c.strip() for c in chunks if (c or "").strip()]
    cw.prime(chunks + [narration])
    out = []
    for c in chunks:
        lines = lines_of(c)
        for i, kind, text in cw.line_faults(lines, source=" ".join(c.split())):
            out.append("%s — %s" % (" / ".join(lines), {
                "kinsoku": "line %d starts with closing punctuation" % (i + 1),
                "orphan": "its last line is one glyph (%s)" % text,
                "split": "the break before line %d falls inside a word" % (i + 1),
                "number": "the break before line %d falls inside a number" % (i + 1)}[kind]))
    if not authored and len(chunks) > 1:
        # where each chunk sits in the narration: a cut with no punctuation or space at it must be a break point
        allowed, at = set(cw.word_starts(narration, joined=False)), 0
        for prev, c in zip(chunks, chunks[1:]):
            a = narration.find(prev, at)
            b = narration.find(c, a + len(prev)) if a >= 0 else -1
            if a < 0 or b < 0:
                break                                   # not a plain slice of the narration (normalised) — not judged
            gap = narration[a + len(prev):b]
            at = a + len(prev)
            inside = any(x < b < y for x, y in cw.glue_spans(narration))
            if not gap.strip(" ") and (b not in allowed or inside):
                out.append("「%s」 / 「%s」 — the caption is cut into two chunks inside a %s" % (
                    prev[-8:], c[:8], "number" if inside else "word"))
    return out


def check(out_dir):
    """{'beats': [...], 'errors': [...], 'warnings': [...], 'skipped': reason|None} for the board in out_dir."""
    import render_remotion as _rr
    from _caption_band import aspect_wh
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = board.get("meta") or {}
    if meta.get("captions") is False:
        return {"beats": [], "errors": [], "warnings": [], "skipped": "captions are off"}
    if not str(meta.get("renderer") or "local").lower().startswith("remotion"):
        # THE HTML / IMAGE TIER burns captions with PIL (render.py), not Film.tsx: judge the lines it draws
        import caption_words as cw
        import validate as _v
        W, H = int(meta.get("width") or 1920), int(meta.get("height") or 1080)
        errors, beats = [], []
        for i, s in enumerate(board.get("slides") or []):
            found = html_beat_faults(s, lambda text: _v._caption_lines(text, meta, W, H))
            beats.append({"beat": i + 1, "faults": found})
            errors += ["beat %d: %s" % (i + 1, f) for f in found]
        name, why = cw.backend()
        warnings = [] if name == "icu" else ["no word segmenter (%s): words were judged per character; numbers and "
                                             "kinsoku still held" % why]
        return {"beats": beats, "errors": errors, "warnings": warnings, "skipped": None, "frame": [W, H],
                "safe": None, "tier": "html"}
    aspect = str(meta.get("aspect") or "16:9")
    W, H = aspect_wh(aspect)
    try:
        safe = _rr.safe_zone(meta, aspect)
    except SystemExit:
        safe = None
    font, uniform = _font(meta)
    beats = []
    for i, s in enumerate(board.get("slides") or []):
        cap = (s.get("caption") or _rr._caption_for_eye(s.get("narration") or s.get("script") or "")).strip()
        if cap:
            beats.append({"beat": i + 1, "caption": cap})
    res = _run({"film": {"W": W, "H": H, "safe": safe, "font": font, "uniform": uniform, "beats": beats}})
    if res is None:
        return {"beats": [], "errors": [], "warnings": [], "skipped": "node/npx unavailable"}
    errors, warnings = [], []
    for b in res["beats"]:
        for c in b["chunks"]:
            for f in c["faults"]:
                errors.append("beat %d: %s — %s" % (b["beat"], " / ".join(c["lines"]), _FAULT[f["kind"]](f)))
    if not res["segmenter"]:
        warnings.append("Intl.Segmenter is not in this node — words were judged per character (kinsoku still held)")
    return {"beats": res["beats"], "errors": errors, "warnings": warnings, "skipped": None,
            "frame": [W, H], "safe": safe}


def main(argv):
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__.strip())
        return 0 if argv else 2
    rep = check(argv[0])
    if "--json" in argv:
        print(json.dumps(rep, ensure_ascii=False, indent=1))
    if rep["skipped"]:
        print("[caption_breaks] NOT CHECKED: %s" % rep["skipped"])
        return 0
    if rep.get("tier") == "html":
        print("[caption_breaks] %d beat(s) as render.py burns them at %dx%d (html/image tier)"
              % (len(rep["beats"]), rep["frame"][0], rep["frame"][1]))
    else:
        n = sum(1 for b in rep["beats"] for c in b["chunks"] if c["cjk"])
        tot = sum(len(b["chunks"]) for b in rep["beats"])
        print("[caption_breaks] %d caption chunk(s) on %d beat(s), %d CJK broken by captionBreak.ts at %dx%d%s"
              % (tot, len(rep["beats"]), n, rep["frame"][0], rep["frame"][1], " (platform-safe)" if rep["safe"] else ""))
    for w in rep["warnings"]:
        print("  WARN  " + w)
    for e in rep["errors"]:
        print("  ERROR " + e)
    if rep["errors"]:
        print("[caption_breaks] %d caption line fault(s) — reword the line, or give the beat a `caption` that splits "
              "at a full stop" % len(rep["errors"]))
        return 1
    print("[caption_breaks] OK — no break inside a word or a number, no line starts with closing punctuation, no "
          "caption ends on one glyph")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
