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
  WARN   split    a line break inside a word (by the segmenter's own reading of the joined line)

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
      faults: p.lines ? cb.lineFaults(p.lines) : []}))});
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


def check(out_dir):
    """{'beats': [...], 'errors': [...], 'warnings': [...], 'skipped': reason|None} for the board in out_dir."""
    import render_remotion as _rr
    from _caption_band import aspect_wh
    board = json.load(open(os.path.join(out_dir, "storyboard.json"), encoding="utf-8"))
    meta = board.get("meta") or {}
    if meta.get("captions") is False:
        return {"beats": [], "errors": [], "warnings": [], "skipped": "captions are off"}
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
                msg = "beat %d: %s — %s" % (b["beat"], " / ".join(c["lines"]), {
                    "kinsoku": "line %d starts with closing punctuation" % (f["line"] + 1),
                    "orphan": "its last line is one glyph (%s)" % f["text"],
                    "split": "the break before line %d falls inside a word" % (f["line"] + 1)}[f["kind"]])
                (warnings if f["kind"] == "split" else errors).append(msg)
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
    print("[caption_breaks] OK — no line starts with closing punctuation, no caption ends on one glyph")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
