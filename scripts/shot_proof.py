#!/usr/bin/env python3
"""SHOT PROOF SHEET — catch the mechanical half of a shot review BEFORE the full render.

Run:
  python3 scripts/shot_proof.py <out_dir>              # static checks only (~1s)
  python3 scripts/shot_proof.py <out_dir> --stills     # + render one settled still per beat (~5s/beat)

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


def shot_defaults(shot):
    """{prop: default} parsed from a shot's destructuring defaults. Strings and numbers only — enough to
    catch a demo default left in place, which is what this is for."""
    path = os.path.join(_SHOTS, shot + ".tsx")
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        return {}
    m = re.search(r"export const %s\s*:\s*React\.FC<" % re.escape(shot), src)
    if not m:
        return {}
    block = src[m.end():]
    stop = block.find("=> {")
    block = block[:stop if stop > 0 else 4000]
    out = {}
    for pm in re.finditer(r"(\w+)\s*:\s*[A-Z_][A-Za-z0-9_]*\s*=\s*('([^']*)'|\"([^\"]*)\"|(-?[\d.]+))", block):
        val = pm.group(3) if pm.group(3) is not None else (pm.group(4) if pm.group(4) is not None else pm.group(5))
        out[pm.group(1)] = val
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
            v = str(v)
            if re.fullmatch(r"[0-9a-fA-F]{3,8}|#?[0-9a-fA-F]{6}|[a-z][a-zA-Z0-9_]*", v.strip()):
                continue                       # an identifier, an enum value or a colour — not prose
            cand.append(v)
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
        body = "\n".join(l for l in src.split("\n") if not l.strip().startswith("//"))
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
        if not c:
            continue
        r, g, b = [int(c.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
        out.append(colorsys.rgb_to_hls(r, g, b)[0] * 360)
    return out


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    out_dir = argv[0]
    board_path = os.path.join(out_dir, "storyboard.json")
    if not os.path.exists(board_path):
        print("[shot_proof] no storyboard.json in %s" % out_dir)
        return 2
    board = json.load(open(board_path, encoding="utf-8"))
    if str(board.get("meta", {}).get("renderer", "")).lower() not in ("remotion", "remotion-bespoke"):
        print("[shot_proof] not a remotion deck — nothing to prove")
        return 0

    errors, warns = static_checks(board)

    if "--stills" in argv:
        import shot_still_qa
        dna_hues = _dna_hues(board)
        proof = os.path.join(out_dir, "_proof")
        os.makedirs(proof, exist_ok=True)
        dna_ref = board.get("meta", {}).get("design_dna") or board.get("meta", {}).get("shot_template")
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
            json.dump(payload, open(pj, "w", encoding="utf-8"), ensure_ascii=False)
            png = os.path.join(proof, "beat_%02d.png" % beat)
            r = subprocess.run(["npx", "remotion", "still", "src/index.ts", shot, png,
                                "--frame=%d" % frame, "--gl=angle", "--props=" + pj, "--log=error"],
                               cwd=_REMOTION, capture_output=True, text=True)
            if r.returncode != 0 or not os.path.exists(png):
                errors.append("beat %d (%s): the shot FAILED to render standalone — %s"
                              % (beat, shot, (r.stderr or "").strip().split("\n")[-1][:160]))
                continue
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
             "" if "--stills" in argv else "  (static only — add --stills for the rendered checks)"))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
