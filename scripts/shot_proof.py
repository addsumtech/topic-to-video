#!/usr/bin/env python3
"""SHOT PROOF SHEET — catch the mechanical half of a shot review BEFORE the full render.

Run:
  python3 scripts/shot_proof.py <out_dir>              # static checks only (~1s)
  python3 scripts/shot_proof.py <out_dir>              # static + RENDERED checks (~5s/beat) — the default
  python3 scripts/shot_proof.py <out_dir> --no-stills  # source-only, for a fast pass while authoring

WHY. A shot-critic pass over a finished 37-beat film cost a full render plus a long review and filed 15
findings. Sorting them by kind, more than half were things a script can decide:

  * a shot's own label sitting inside the burned-caption band, or content sliced by the frame edge
  * a colour outside the film's DNA (a hardcoded gradient stop put royal blue over ~25% of one frame in
    a green/amber film)
  * content parked in a narrow column with half the 16:9 frame dead
  * a register's DEMO DEFAULT left in shot_props on a real topic (a card's backLabel still reading
    「实际」 on the film's closing frame; a metric register still showing its sample figure)
  * two beats rendering the SAME picture because the same register got near-identical props

The other findings — does the design ENCODE the idea, is the number sourced, does the register fit the
beat — are judgment, and stay the critic's job. This script exists so the critic spends its pass on those
instead of re-finding the mechanical ones, and so a FIRST draft arrives with them already fixed.

It is a floor, not a verdict: passing here says nothing about whether the film is any good.
"""
import json
import os
import re
from onscreen_text_qa import _strip_comments   # the ONE comment stripper
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")
_SHOTS = os.path.join(_REMOTION, "src", "shots")

# Hue arc a colour must NOT fall in, expressed as "outside the film's own two accents by more than this
# many degrees". Computed per film from its DNA rather than hardcoded, so it works for any palette.
HUE_TOLERANCE = 28
OFF_SYSTEM_FRAC = 0.02      # >2% of the frame's chromatic ink outside the palette arc = a clash
NARROW_FRAC = 0.45          # content narrower than this share of the frame …
OFFSET_FRAC = 0.06          # … AND its centre this far off the frame's centre = a DEAD FRAME.
# Width alone is not the defect. Measured on a real film, "narrow" split cleanly in two: seven beats were
# narrow and dead-centre (a title, a cube, a counter — deliberate compositions), and four were narrow and
# pushed to one side, which is the thing a reviewer actually described as "half the frame is dead".
# Flagging on width alone reported 11 of 37 beats; a gate that cries wolf that often gets ignored.

# Registers whose colour is a CONVENTION, not the film's palette: a diff's removals are red and its
# additions green, a log's errors are red, an editor's syntax colours are its own system. Judging these
# against the DNA reports the convention as a defect. Keep the list short and say why.
SEMANTIC_COLOUR_SHOTS = {
    "TermDiff": "a diff is red/green by convention",
    "TermLog": "log levels are red/amber/green by convention",
    "TermGitLog": "commit/branch colouring is a convention",
    "CodeCompose": "syntax highlighting is its own colour system",
    "CodeRain": "terminal phosphor colour is the register",
    "AsciiField": "terminal phosphor colour is the register",
}
PROPS_SAME = 0.80           # two beats sharing a register with >=80% identical props = the same picture

# Registers that put a SOURCED FIGURE on screen. Every one of them animates it, and the delivery gate
# captures the MID-scene frame — so "settles eventually" is not good enough: a film shipped with a
# sourced 19.3-28.9 rendered as 19.3-16.5 and a sourced 19% rendered as 18%, digits caught mid-flight.
# ONLY the registers whose figure IS the frame's subject and whose only motion is that figure settling.
# The check compares the whole mid frame against the settled one, so it cannot tell a still-rolling digit
# from a chart that is legitimately still drawing: measured on their own demo props, ChartLive scores 201,
# ChartRace 200, BeforeAfterSlider 207 and GaugeCluster 118 — every one of them would be BLOCKED for
# animating exactly as designed. Those four display a figure too and are NOT covered here; separating the
# number from the graphic needs a region this check does not have, so their figures remain the critic's
# to verify. A gate that blocks four correct designs is worse than one that admits its reach.
FIGURE_SHOTS = ("OdometerRoll", "TermCounter", "EdStat")
FIGURE_SETTLE_BLOCK = 70    # max 32x32-block difference between the MID and SETTLED frames.
# Measured: a figure that lands early scores 0-34; one still moving at the midpoint scores 115-232. A
# whole-frame mean cannot separate them — one changed digit moves too few pixels (0.45 vs 0.00) — so the
# statistic is the worst LOCAL block, not the average.


def shot_defaults(shot):
    """{prop: default} for a registered shot — reads the file and delegates."""
    try:
        src = open(os.path.join(_SHOTS, shot + ".tsx"), encoding="utf-8").read()
    except OSError:
        return {}
    return defaults_from_source(src, shot)


def defaults_from_source(src, shot):
    """{prop: default} parsed from a shot's destructuring defaults. Strings and numbers only — enough to
    catch a demo default left in place, which is what this is for. Pure, so a test can feed it BOTH
    destructuring forms; only the renamed one was parsed for a long time, which left 72 of 136 registers
    unchecked by the module's headline rule."""
    m = re.search(r"export const %s\s*:\s*React\.FC<" % re.escape(shot), src)
    if not m:
        return {}
    block = src[m.end():]
    stop = block.find("=> {")
    block = block[:stop if stop > 0 else 4000]
    out = {}
    # TWO destructuring forms are in use across the library and only the RENAMED one was parsed, so this
    # returned nothing at all for 72 of 136 registers — the demo-default check, this module's headline
    # reason for existing, was blind on more than half the library and said nothing.
    #   renamed:  title: TITLE = 'Your workspace'
    #   plain:    title = 'Your workspace'
    pats = [r"(\w+)\s*:\s*[A-Z_][A-Za-z0-9_]*\s*=\s*('([^']*)'|\"([^\"]*)\"|(-?[\d.]+))",
            # The plain form's name must start lowercase: prop names are camelCase and the RENAMED form's
            # alias is upper (`title: TITLE = 'x'`), so without this the alias came back as a phantom prop
            # called TITLE that no board can ever set.
            r"(?<![:\w])([a-z]\w*)\s*=\s*('([^']*)'|\"([^\"]*)\"|(-?[\d.]+))"]
    for pat in pats:
        for pm in re.finditer(pat, block):
            val = pm.group(3) if pm.group(3) is not None else (pm.group(4) if pm.group(4) is not None else pm.group(5))
            out.setdefault(pm.group(1), val)
    return out


def _flat(v, prefix=""):
    """Flatten shot_props to {path: scalar} so two beats' props can be compared and scanned."""
    out = {}
    if isinstance(v, dict):
        for k, x in v.items():
            out.update(_flat(x, prefix + "/" + str(k)))
    elif isinstance(v, list):
        for i, x in enumerate(v):
            out.update(_flat(x, prefix + "/%d" % i))
    else:
        out[prefix] = v
    return out


def static_checks(board):
    errors, warns = [], []
    slides = board.get("slides", [])
    seen = {}
    for s in slides:
        beat = s.get("index", 0) + 1
        shot = s.get("shot")
        props = s.get("shot_props") or {}
        if not shot:
            continue
        # (1) a register's DEMO DEFAULT left in place on a real topic
        defs = shot_defaults(shot)
        flat = _flat(props)
        for key, dv in defs.items():
            if not isinstance(dv, str) or len(dv) < 2:
                continue
            for path, val in flat.items():
                if isinstance(val, str) and val.strip() == dv.strip():
                    warns.append("beat %d (%s): shot_props%s is the register's DEMO DEFAULT %r — a leftover "
                                 "default reads as mystery furniture on a real topic; pass real copy or drop it"
                                 % (beat, shot, path, dv))
        # a prop the beat never set but whose default is visible text: the register will draw ITS demo word
        for key, dv in defs.items():
            if key in ("title", "label", "backLabel", "heading", "kicker", "note", "unit") and key not in props:
                if isinstance(dv, str) and len(dv) >= 2 and re.search(r"[A-Za-z一-鿿]", dv):
                    warns.append("beat %d (%s): '%s' is not set, so the register draws its own demo word %r"
                                 % (beat, shot, key, dv))
        # (2) two beats rendering the same picture. The signal is an identical prop SHAPE — the same keys,
        # the same array lengths — regardless of the words in them. "The same picture with the words
        # swapped" is literally shape-identical and value-different, so requiring shared VALUES (an
        # earlier draft of this check did) looks for the opposite of the defect and finds nothing.
        seen.setdefault(shot, []).append((beat, tuple(sorted(flat))))

    # A register WELDED TO ONE FILM. The library only compounds if a new register carries an ARGUMENT
    # SHAPE ("two populations a measure cannot separate") with the topic arriving through props. If the
    # film's own copy is baked into the .tsx as a literal, the register is a one-off dressed as a library
    # entry: it inflates the catalogue and helps no later film. Checked against the film's OWN distinctive
    # strings, so it needs no vocabulary list and works in any language.
    # The topic set is built from the film's PROSE only. Prop VALUES are a mix of prose and API values —
    # glyph names, hex colours, code samples, enum keys — and feeding those in flagged 'checks', 'gutter',
    # 'f2b544' and even 'return' as "the film's own copy". A gate with false positives gets switched off.
    topic = set()
    for s in slides:
        cand = [s.get("narration", "")]
        for v in _flat(s.get("shot_props") or {}).values():
            # (No identifier/hex filter here: the extractors below take CJK runs of 4+ and Latin PHRASES
            # of two or more words, so a lone enum value or colour can never enter the topic set anyway.
            # A guard that cannot change an outcome is dead code, and a test written for it is theatre.)
            cand.append(str(v))
        for t in cand:
            for run in re.findall(r"[\u4e00-\u9fff]{4,}", str(t)):
                topic.add(run)
            for phrase in re.findall(r"[A-Za-z][A-Za-z0-9'\-]+(?: [A-Za-z][A-Za-z0-9'\-]+){1,4}", str(t)):
                if len(phrase) >= 10:
                    topic.add(phrase)          # a PHRASE, never a lone token: one word is never proof
    for shot in sorted({s.get("shot") for s in slides if s.get("shot")}):
        try:
            src = open(os.path.join(_SHOTS, shot + ".tsx"), encoding="utf-8").read()
        except OSError:
            continue
        # Only the register's STRING LITERALS count. Matching the whole source flagged 'return' and
        # 'reverse' — JS keywords that reached the topic set from a beat whose props legitimately carry a
        # code sample. Topic copy welded into a register always appears as a literal, never as code.
        # Strip BOTH comment forms. Filtering only lines that START with `//` left every continuation line
        # of a `/* … */` or JSX `{/* … */}` block in the text, so a comment DOCUMENTING a defect — quoting
        # the very copy it was about — was read as that copy being welded into the register. A false ERROR
        # blocks delivery on correct code, which is worse than the defect the check exists to catch, and it
        # is the second time this shape has appeared today. One implementation, shared.
        body = _strip_comments(src)
        lits = " ".join(re.findall(r"'([^'\n]{2,120})'|\"([^\"\n]{2,120})\"", body) and
                        [a or b for a, b in re.findall(r"'([^'\n]{2,120})'|\"([^\"\n]{2,120})\"", body)])
        welded = sorted({t for t in topic if len(t) >= 4 and t in lits})[:3]
        if welded:
            errors.append("%s hardcodes this film's own copy (%s) — a register must carry the ARGUMENT "
                          "SHAPE with the topic arriving through props, or it is a one-off in the library's "
                          "clothing. Move that text into shot_props." % (shot, ", ".join(repr(w) for w in welded)))

    # Report repetition GROUPED BY REGISTER — one line per register, not one per pair. A 37-beat film
    # produced seven pair-warnings, which reads as noise; "CardFlip3D carries beats 2, 27, 37 as the same
    # composition" is the sentence a person would actually write.
    for shot, uses in sorted(seen.items()):
        if len(uses) < 2:
            continue
        group = [uses[0][0]]
        base = set(uses[0][1])
        for beat, shape in uses[1:]:
            common = base | set(shape)
            if common and len(base & set(shape)) / len(common) >= PROPS_SAME:
                group.append(beat)
        if len(group) >= 2:
            warns.append("%s carries beats %s with the same prop shape — they will render the same "
                         "composition with the words swapped. Vary the modules per beat, or move one of "
                         "them to a different register."
                         % (shot, ", ".join(str(b) for b in group)))
    return errors, warns


def _in_palette(h, accents):
    """Is hue h inside the film's palette? A film's system is the ARC BETWEEN its two accents, not two
    points: a gradient blending accent into accent2 passes through every hue in between, and those are
    in-system by construction. Measuring distance to the two endpoints instead flagged a green-to-green
    hero card at 120 deg as off-system because the accent sits at 154."""
    if not accents:
        return True
    for a in accents:
        if min(abs(h - a), 360 - abs(h - a)) <= HUE_TOLERANCE:
            return True
    if len(accents) >= 2:
        lo, hi = accents[0], accents[1]
        d = (hi - lo) % 360
        inside = ((h - lo) % 360 <= d) if d <= 180 else ((h - hi) % 360 <= 360 - d)
        if inside:
            return True
    return False


def _block_diff(a, b):
    """The worst 32x32 block's mean absolute difference between two frames.

    The average over the whole frame cannot see one changed digit (0.45 vs 0.00 on a real case); the worst
    local block can (114 vs 0)."""
    from PIL import Image, ImageChops
    d = ImageChops.difference(Image.open(a).convert("L"), Image.open(b).convert("L"))
    w, h = d.size
    px = d.load()
    best = 0.0
    for by in range(0, max(1, h - 32), 32):
        for bx in range(0, max(1, w - 32), 32):
            s = sum(px[bx + x, by + y] for y in range(0, 32, 4) for x in range(0, 32, 4)) / 64.0
            if s > best:
                best = s
    return best


def _hues(png, min_chroma=45, min_val=70):
    import colorsys
    from PIL import Image
    im = Image.open(png).convert("RGB")
    w, h = im.size
    px = im.load()
    hs, tot = [], 0
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            r, g, b = px[x, y]
            if max(r, g, b) - min(r, g, b) >= min_chroma and max(r, g, b) >= min_val:
                hs.append(colorsys.rgb_to_hls(r / 255, g / 255, b / 255)[0] * 360)
            tot += 1
    return hs, tot


def _content_box(png, thresh=26):
    """Bounding box of everything that departs from the frame's modal (background) luminance."""
    from PIL import Image
    g = Image.open(png).convert("L")
    w, h = g.size
    px = g.load()
    hist = {}
    for y in range(0, h, 4):
        for x in range(0, w, 4):
            hist[px[x, y] // 8] = hist.get(px[x, y] // 8, 0) + 1
    ground = (max(hist, key=hist.get) * 8 + 4) if hist else 0
    x0, x1 = w, 0
    for y in range(0, h, 3):
        for x in range(0, w, 3):
            if abs(px[x, y] - ground) > thresh:
                if x < x0:
                    x0 = x
                if x > x1:
                    x1 = x
    return (x0, x1, (x1 - x0) / float(w)) if x1 > x0 else (0, 0, 0.0)


def _dna_hues(board):
    """The film's own accent hues, from its DNA — the palette everything else is judged against."""
    import colorsys
    meta = board.get("meta", {})
    dna = meta.get("design_dna")
    accents = []
    if isinstance(dna, dict):
        accents = [dna.get("accent"), dna.get("accent2")]
    else:
        name = dna if isinstance(dna, str) else meta.get("shot_template")
        try:
            src = open(os.path.join(_REMOTION, "src", "runtime", "dna.tsx"), encoding="utf-8").read()
            key = re.search(r"^\s*'?%s'?\s*:\s*(\w+),\s*$" % re.escape(str(name)), src, re.M)
            preset = key.group(1) if key else None
            if preset:
                blk = src[src.index("export const %s: DesignDNA" % preset):][:1400]
                accents = [(re.search(r"accent:\s*'(#[0-9a-fA-F]{6})'", blk) or [None, None])[1],
                           (re.search(r"accent2:\s*'(#[0-9a-fA-F]{6})'", blk) or [None, None])[1]]
        except (OSError, ValueError, AttributeError):
            accents = []
    out = []
    for c in accents:
        # An authored DNA may hold any CSS colour. Assuming 6-digit hex crashed the whole proof sheet on
        # `#c33`, `rebeccapurple` or `rgb(...)` — a gate that dies is a gate that gets skipped.
        txt = str(c or "").strip()
        m6 = re.fullmatch(r"#?([0-9a-fA-F]{6})", txt)
        m3 = re.fullmatch(r"#?([0-9a-fA-F]{3})", txt)
        if m6:
            hx = m6.group(1)
        elif m3:
            hx = "".join(ch * 2 for ch in m3.group(1))
        else:
            continue
        r, g, b = [int(hx[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        out.append(colorsys.rgb_to_hls(r, g, b)[0] * 360)
    return out


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    # The still renderer runs with cwd=remotion, so a RELATIVE out_dir made it write beside the bundle
    # while existence was checked from the caller's directory — every beat then reported a failed render.
    out_dir = os.path.abspath(argv[0])
    board_path = os.path.join(out_dir, "storyboard.json")
    if not os.path.exists(board_path):
        print("[shot_proof] no storyboard.json in %s" % out_dir)
        return 2
    board = json.load(open(board_path, encoding="utf-8"))
    if str(board.get("meta", {}).get("renderer", "")).lower() not in ("remotion", "remotion-bespoke"):
        print("[shot_proof] not a remotion deck — nothing to prove")
        return 0

    errors, warns = static_checks(board)

    # THE RENDERED CHECKS RUN BY DEFAULT.
    #
    # They used to be behind `--stills`, and an opt-in gate is not a detector. The consequence was concrete:
    # two registers in a delivered film parked their own subtitle inside the band the renderer reserves for
    # the burned caption, this script owns the check that measures exactly that, it was run — and it printed
    # "OK (static only)". Nobody sees the flag they did not pass. The band violation was found by a human
    # looking at a frame, which is the one review that does not scale.
    #
    # The static checks read source; only a RENDER can see what the frame actually looks like, which is the
    # half that matters. `--no-stills` still exists for a fast source-only pass while authoring.
    if "--no-stills" not in argv:
        import shot_still_qa
        dna_hues = _dna_hues(board)
        proof = os.path.join(out_dir, "_proof")
        os.makedirs(proof, exist_ok=True)
        dna_ref = board.get("meta", {}).get("design_dna") or board.get("meta", {}).get("shot_template")
        aspect = board.get("meta", {}).get("aspect")
        for s in board.get("slides", []):
            beat = s.get("index", 0) + 1
            shot = s.get("shot")
            if not shot:
                continue
            src = ""
            try:
                src = open(os.path.join(_SHOTS, shot + ".tsx"), encoding="utf-8").read()
            except OSError:
                pass
            dm = re.search(r"export const DURATION\s*=\s*(\d+)", src)
            frame = int(int(dm.group(1)) * 0.88) if dm else 120
            pj = os.path.join(proof, "beat_%02d.json" % beat)
            payload = dict(s.get("shot_props") or {})
            if dna_ref:
                payload["dna"] = dna_ref
            # The proof sheet must render at the FILM'S aspect. Without this it rendered every shot at
            # 1920x1080 and then measured the caption band (150px, the 16:9 value) and the content width
            # against a frame the film will never show — a portrait film's proof sheet was checking
            # geometry that does not exist.
            if aspect:
                payload["aspect"] = aspect
            json.dump(payload, open(pj, "w", encoding="utf-8"), ensure_ascii=False)
            png = os.path.join(proof, "beat_%02d.png" % beat)
            # --public-dir is NOT optional here. Every register in the real-image tier resolves its
            # picture through staticFile(), which without a public dir points at a path that does not
            # exist — so those shots ALWAYS failed to render and this gate reported a hard error for a
            # beat that is fine in the film. Worse, it meant the proof sheet was blind to exactly the
            # class most likely to carry a wrong or broken image. The film render passes the out_dir;
            # so does this.
            r = subprocess.run(["npx", "remotion", "still", "src/index.ts", shot, png,
                                "--frame=%d" % frame, "--gl=angle", "--props=" + pj, "--log=error",
                                "--public-dir=" + os.path.abspath(out_dir)],
                               cwd=_REMOTION, capture_output=True, text=True)
            if r.returncode != 0 or not os.path.exists(png):
                errors.append("beat %d (%s): the shot FAILED to render standalone — %s"
                              % (beat, shot, (r.stderr or "").strip().split("\n")[-1][:160]))
                continue
            # A figure-bearing register must be showing the RIGHT figure at the frame the gate captures.
            if shot in FIGURE_SHOTS and dm:
                mid_png = os.path.join(proof, "beat_%02d_mid.png" % beat)
                rm = subprocess.run(["npx", "remotion", "still", "src/index.ts", shot, mid_png,
                                     "--frame=%d" % int(int(dm.group(1)) * 0.5), "--gl=angle",
                                     "--props=" + pj, "--log=error",
                                     "--public-dir=" + os.path.abspath(out_dir)],
                                    cwd=_REMOTION, capture_output=True, text=True)
                if rm.returncode == 0 and os.path.exists(mid_png):
                    d = _block_diff(mid_png, png)
                    if d > FIGURE_SETTLE_BLOCK:
                        errors.append("beat %d (%s): the figure is still moving at the mid-scene frame "
                                      "(block diff %.0f > %d) — that is the frame the delivery gate "
                                      "captures, so the film ships an unsourced number"
                                      % (beat, shot, d, FIGURE_SETTLE_BLOCK))
            m = shot_still_qa.measure(png)
            if m["edge"] > shot_still_qa.EDGE_FRAC_ERR:
                errors.append("beat %d (%s): %.1f%% of the action-safe border is content — something is "
                              "OFF-FRAME" % (beat, shot, 100 * m["edge"]))
            if m["caption"] > shot_still_qa.CAPTION_FRAC_ERR:
                errors.append("beat %d (%s): %.1f%% ink in the caption band — the burned subtitle will sit "
                              "on the shot's own content" % (beat, shot, 100 * m["caption"]))
            if dna_hues:
                hs, _ = _hues(png)
                if hs:
                    off = [h for h in hs if not _in_palette(h, dna_hues)]
                    if len(off) / len(hs) > OFF_SYSTEM_FRAC and shot not in SEMANTIC_COLOUR_SHOTS:
                        import statistics
                        warns.append("beat %d (%s): %.0f%% of the frame's chromatic ink is outside the film's "
                                     "palette (median hue %.0f deg vs accents %s) — a hardcoded colour is "
                                     "overriding the DNA"
                                     % (beat, shot, 100 * len(off) / len(hs), statistics.median(off),
                                        [round(a) for a in dna_hues]))
            x0, x1, frac = _content_box(png)
            if not frac:
                # NOTHING departs from the ground: the beat rendered an empty frame. Guarding the
                # dead-frame branch with `if frac and ...` let the emptiest possible result pass silently.
                errors.append("beat %d (%s): the frame is EMPTY — nothing departs from the background"
                              % (beat, shot))
            if frac and frac < NARROW_FRAC:
                m2 = shot_still_qa.measure(png)
                off = abs((x0 + x1) / 2 - m2["w"] / 2) / float(m2["w"])
                if off > OFFSET_FRAC:
                    warns.append("beat %d (%s): content spans %.0f%% of the width and sits %.0f%% off centre "
                                 "— one side of the frame is dead" % (beat, shot, 100 * frac, 100 * off))

    for e in errors:
        print("  ERROR: " + e)
    for w in warns:
        print("  warn : " + w)
    print("[shot_proof] %s  %d error(s), %d warning(s)%s"
          % ("FAIL" if errors else "OK", len(errors), len(warns),
             "  (static only — drop --no-stills for the rendered checks)" if "--no-stills" in argv else ""))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
