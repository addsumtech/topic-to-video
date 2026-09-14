#!/usr/bin/env python3
"""measure_ground_luma — MEASURE which DNA token each shot actually paints its ground from.

The model this replaces was a DECLARATION: a boolean set (`DNA_GROUND`) saying "this shot takes its
ground from the DNA", which `dnaGroundLum` then read as "…therefore its ground luminance is
luminance(dna.bg)". That is false for any shot whose ground comes from a DIFFERENT token.
KineticManifesto paints `linear-gradient(135deg, dna.accent, dna.accent2)` — an accent flood — and was
in the set, so the model reported it DARK while the pixels were BRIGHT. Two things read that answer:
caption ink, and pickPresentation's luminance-safe seam. The seam therefore computed a gap of ZERO
across a measured 20.8 -> 149.3 jump and applied no safety: a visible flash.

So: render each shot under a PROBE DNA whose tokens are deliberately far apart in luminance, measure
the frame's actual outer-border luminance (the ground is full-bleed; content is central), and infer
the token from the pixels. The measurement is the authority — a shot whose ground matches no token is
reported UNCLASSIFIED, never guessed.

  python3 scripts/measure_ground_luma.py            # measure all, print the table
  python3 scripts/measure_ground_luma.py --only A,B # measure a few (method check)
  python3 scripts/measure_ground_luma.py --emit     # write DNA_GROUND_TOKEN into shotLuma.ts
  python3 scripts/measure_ground_luma.py --check    # non-zero when the committed table has drifted
  python3 scripts/measure_ground_luma.py --luma            # measure SHOT_LUMA (each shot on its OWN defaults)
  python3 scripts/measure_ground_luma.py --luma --emit     # write it into shotLuma.ts
  python3 scripts/measure_ground_luma.py --luma --check    # non-zero when SHOT_LUMA has drifted
"""
import json, os, re, subprocess, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image
import _common as _c
import dna_audit

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")
_SHOTLUMA = os.path.join(_REMOTION, "src", "runtime", "shotLuma.ts")

# Tokens chosen so their RELATIVE LUMINANCES are far apart and unambiguous.
PROBE_TOKENS = {"bg": "#050505", "surface": "#7a7a7a", "accent2": "#b4b4b4", "accent": "#fafafa"}
PROBE_DNA = {
    "id": "lumprobe",
    "fontDisplay": "Inter, system-ui, sans-serif", "fontBody": "Inter, system-ui, sans-serif",
    "fontMono": '"JetBrains Mono", ui-monospace, monospace',
    "bg": PROBE_TOKENS["bg"], "fg": "#ff2ec4", "dim": "#c86ab0",
    "accent": PROBE_TOKENS["accent"], "accent2": PROBE_TOKENS["accent2"], "onAccent": "#101010",
    "surface": PROBE_TOKENS["surface"], "surfaceBorder": "#4d4d4d", "line": "#3a3a3a",
    "radius": 10, "borderWidth": 1, "motion": "smooth", "decoration": [],
    "uppercaseLabels": False, "labelSpacing": "0.08em",
}


def _srgb_lum(rgb):
    def ch(v):
        c = v / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb[:3]
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)


def token_lums():
    return {k: _srgb_lum(tuple(int(v[i:i + 2], 16) for i in (1, 3, 5))) for k, v in PROBE_TOKENS.items()}


def border_luminance(png, band=14):
    """Median luminance of the outer ring — the ground, unobstructed by centred content."""
    im = Image.open(png).convert("RGB")
    w, h = im.size
    px = im.load()
    vals = []
    for x in range(0, w, 3):
        for y in list(range(0, band)) + list(range(h - band, h)):
            vals.append(_srgb_lum(px[x, y]))
    for y in range(band, h - band, 3):
        for x in list(range(0, band)) + list(range(w - band, w)):
            vals.append(_srgb_lum(px[x, y]))
    vals.sort()
    return vals[len(vals) // 2]


def classify(lum, lums, tol=0.06):
    """Return (token-or-mix, error). A MIX is a sorted 2-token list.

    The single-token model was not enough, and the measurement is what revealed it: KineticManifesto
    paints `linear-gradient(accent -> accent2)`, so its border luminance (0.665 under the probe) sits
    between the two and matches NEITHER. Rather than force it into the nearest token — which is the
    exact move that produced the original bug — treat a two-token blend as its own class and average
    the pair's luminance at runtime."""
    cands = [((k,), v) for k, v in lums.items()]
    keys = sorted(lums)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a, b = keys[i], keys[j]
            cands.append(((a, b), (lums[a] + lums[b]) / 2.0))
    ranked = sorted(cands, key=lambda kv: abs(kv[1] - lum))
    best, second = ranked[0], ranked[1]
    be, se = abs(best[1] - lum), abs(second[1] - lum)
    if be > tol:
        return None, be
    # SEPARATION IS ABSOLUTE *OR* RELATIVE, and it needs both tests because each one alone misjudges at one
    # end of the range. The flat 0.03 margin this used to carry refuses the clearest answers there are: a
    # ground measuring 0.198 matched `surface` (0.195) to three thousandths and the runner-up to thirty-one —
    # ten times worse — and was still declared ambiguous, because two small numbers cannot differ by 0.03.
    # Replacing it with a ratio alone is worse in the other direction, and the docstring above names the case
    # that proves it: KineticManifesto's 0.665 sits 0.041 from the accent/accent2 mix and 0.090 from the next
    # candidate — clearly separated, and yet inside any 2x ratio. So either test may carry it.
    if not (se - be >= 0.03 or se >= be * 3):
        return None, be                      # genuinely ambiguous — do not guess
    tok = best[0][0] if len(best[0]) == 1 else list(best[0])
    return tok, abs(best[1] - lum)


# ── READING THE TABLE BACK, so the gate can judge what it could not classify ─────────────────────────────
# `--check` used to compare only the shots `classify` could NAME a token for and skip the rest, which meant
# the entries most likely to be wrong were the only ones nobody checked. These read the declaration itself
# and turn it into the number its two consumers use, so an unnameable ground is still an answerable question.

def _rel_lum(hexstr):
    """Relative luminance of '#rgb' / '#rrggbb' — the same value shotLuma.ts's lumValue() returns."""
    h = str(hexstr).lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return _srgb_lum(tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)))


def _gap(a, b):
    """Display-encoded distance between two ground luminances — what Film.tsx's seam guard judges on."""
    return abs(a ** (1 / 2.2) - b ** (1 / 2.2))


def declared_tokens(src):
    """{shot: [token, ...] | '#rrggbb'} exactly as DNA_GROUND_TOKEN currently declares it."""
    body = src.split("DNA_GROUND_TOKEN", 1)[1].split("{", 1)[1].split("};")[0]
    out = {}
    for name, val in re.findall(r"^\s{2}(\w+):\s*(\[[^\]]*\]|'#?[a-zA-Z0-9]+')", body, re.M):
        lit = re.fullmatch(r"'(#[0-9a-fA-F]{3}|#[0-9a-fA-F]{6})'", val)
        if lit:
            out[name] = lit.group(1)
            continue
        toks = re.findall(r"'([a-zA-Z0-9]+)'", val)
        if toks:
            out[name] = toks
    return out


def harsh_gap(src):
    """Film.tsx's flash threshold, read from the runtime instead of re-typed here."""
    m = re.search(r"export const HARSH_GROUND_GAP\s*=\s*([0-9.]+)\s*;", src)
    if not m:
        raise SystemExit("[measure_ground_luma] runtime/shotLuma.ts no longer exports HARSH_GROUND_GAP — "
                         "this gate judges a declaration against the seam guard's own threshold and cannot "
                         "invent one")
    return float(m.group(1))


def _declared_y(decl, lums):
    """The ground luminance a TOKEN declaration predicts under the probe.

    Deliberately the RUNTIME's model — dnaGroundY averages the token luminances — and not a better one, so
    the gate judges the number the film will actually compute. A token the probe does not carry (`bgGrad`)
    returns None and is reported as unresolvable rather than scored against a guess.
    """
    if not decl or isinstance(decl, str):
        return None
    ys = [lums.get(t) for t in decl]
    if any(y is None for y in ys):
        return None
    return sum(ys) / len(ys)


# THE EVIDENCE REGISTERS ARE MEASURABLE, AND WERE BEING WRITTEN OFF. Five registers REFUSE to draw without
# a real artefact (runtime/evidence.ts) — which is the point of them — and both probes here rendered them on
# default props, so every sweep reported the same four (now five) as "RENDER FAILED" and left their ground
# tokens as declarations nobody has ever checked. A permanent failure line in a gate's output is worse than a
# gap: it is the line people learn to skip, and it was hiding the fact that those tokens are unverified.
# `register_energy` already builds the fixtures for exactly this; using them is one import.
def _fixture_props():
    try:
        sys.path.insert(0, _HERE)
        import register_energy
        register_energy.ensure_fixture()
        return register_energy.evidence_props()
    except Exception:
        return {}


def measure(shot, td, fixtures=None):
    props = os.path.join(td, "p.json")
    png = os.path.join(td, shot + ".png")
    scene = {"shot": shot, "durF": 150}
    ev = (fixtures or {}).get(shot)
    if ev:
        scene["props"] = ev
    json.dump({"scenes": [scene], "dna": PROBE_DNA,
               "captions": False, "camera": 0}, open(props, "w"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", png,
                        "--frame=110", "--gl=angle", "--timeout=90000", "--props=" + props],
                       cwd=_REMOTION, capture_output=True, text=True)
    if r.returncode != 0:
        return None, (r.stderr or "")[-300:]
    return border_luminance(png), None


# ── SHOT_LUMA: the shot's OWN ground class, with no DNA at all ───────────────────────────────────────────
# DNA_GROUND_TOKEN above answers "which DNA token does this shot paint its ground from". SHOT_LUMA answers
# a different question — "how bright is this shot on its OWN defaults" — and is the fallback the film reads
# when there is no DNA, plus the input to the shot-director's luminance variety.
#
# It was never derivable. `register_shot.py` writes `'dark'` for every new register as a placeholder and
# nothing ever came back to correct it, so a register was born with a confident value that looked exactly
# like a measurement. Nine registers added in one session were all cream-coloured and all declared dark;
# the luminance guard that exists to stop a bright-over-dark flash was reading the opposite of the truth.
#
# The empty band between the two populations is wide — measured across the library, `dark` shots sit at or
# below 0.042 relative luminance and `light` shots at or above 0.463 — so the thresholds are not a tuning
# choice, they sit in a gap with nothing in it.
LUMA_DARK_MAX = 0.06
LUMA_LIGHT_MIN = 0.40


def luma_bucket(lum):
    return "dark" if lum < LUMA_DARK_MAX else ("light" if lum > LUMA_LIGHT_MIN else "mid")


def measure_own(shot, td, fixtures=None):
    """The shot's ground with NO DNA — its own default palette, which is what SHOT_LUMA describes."""
    png = os.path.join(td, "own_" + shot + ".png")
    extra = []
    ev = (fixtures or {}).get(shot)
    if ev:
        pf = os.path.join(td, "own_" + shot + ".props.json")
        json.dump(ev, open(pf, "w"))
        extra = ["--props=" + pf]
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", shot, png,
                        "--frame=110", "--gl=angle", "--timeout=90000"] + extra,
                       cwd=_REMOTION, capture_output=True, text=True)
    if r.returncode != 0:                       # a shorter shot: fall back to a frame it certainly has
        r = subprocess.run(["npx", "remotion", "still", "src/index.ts", shot, png,
                            "--frame=30", "--gl=angle", "--timeout=90000"] + extra,
                           cwd=_REMOTION, capture_output=True, text=True)
    if not os.path.exists(png):
        return None, (r.stderr or "")[-300:]
    return border_luminance(png), None


def read_shot_luma():
    src = open(_SHOTLUMA, encoding="utf-8").read()
    body = src.split("SHOT_LUMA")[1].split("{", 1)[1].split("};")[0]
    return dict(re.findall(r"(\w+):\s*'(dark|mid|light)'", body))


def write_shot_luma(measured):
    """Rewrite SHOT_LUMA from a measurement. Only touches entries the measurement covers."""
    src = open(_SHOTLUMA, encoding="utf-8").read()
    head, rest = src.split("export const SHOT_LUMA", 1)
    body, tail = rest.split("};", 1)
    n = [0]

    def fix(m):
        name, val, comment = m.group(1), m.group(2), (m.group(3) or "")
        want = measured.get(name)
        if not want:
            return m.group(0)
        # A CONFIRMED PLACEHOLDER IS STILL A MEASURED ONE. This only rewrote entries whose value CHANGED,
        # so a scaffold placeholder the measurement happened to agree with kept its `// PROVISIONAL — never
        # measured` marker for ever, and `test_shot_luma_is_measured_not_guessed` could then never be
        # satisfied except by changing the register's design. AcceptanceStamp hit it on its first day: its
        # own ground is dark, the placeholder guessed dark, and --emit reported "wrote 0 entries" while the
        # test kept failing. The DNA_GROUND_TOKEN half of this file already drops the marker on write; this
        # half now does too, because "never measured" is a claim about history, not about the value.
        if want != val or "PROVISIONAL" in comment:
            n[0] += 1
            # NO trailing comment. Appending `// measured` to an entry that SHARES A LINE with others
            # commented its line-mates out — two shots vanished from the table and the sync test caught it.
            # The value is the record; a note that can eat its neighbours is not worth having.
            return "%s: '%s'," % (name, want)
        return m.group(0)

    body = re.sub(r"(\w+):\s*'(dark|mid|light)',(\s*//[^\n]*)?", fix, body)
    open(_SHOTLUMA, "w", encoding="utf-8").write(head + "export const SHOT_LUMA" + body + "};" + tail)
    return n[0]


def provisional_shots():
    """Entries `register_shot.py` wrote as a placeholder and nobody measured — in EITHER table.

    This scanned SHOT_LUMA alone, while the scaffold writes a placeholder into DNA_GROUND_TOKEN too — and
    that is the table the seam guard actually reads on a themed film (`dnaGroundY`). So the half that
    decides whether a cut flashes was exempt from the check written to stop exactly that.
    """
    src = open(_SHOTLUMA, encoding="utf-8").read()
    out = []
    for table in ("export const SHOT_LUMA", "export const DNA_GROUND_TOKEN"):
        if table not in src:
            continue
        body = src.split(table, 1)[1].split("};", 1)[0]
        out += re.findall(r"(\w+):\s*(?:'[\w-]+'|\[[^\]]*\]),\s*//\s*PROVISIONAL", body)
    return sorted(set(out))


def _emit(table=None):
    """Write the measured table into DNA_GROUND_TOKEN in shotLuma.ts.

    The docstring has advertised `--emit` since this script was written and the flag was never
    implemented: `--check` printed "re-run: ... --emit", and that re-run silently re-measured for ten
    minutes and wrote the JSON again, leaving the table untouched. A documented command that does
    nothing is worse than no command, because it looks like the table was updated.

    `--apply-json` applies the already-measured remotion/_ground_luma.json without re-rendering.

    A `// declared-only` entry is NEVER overwritten: it is declared precisely because the measurement
    cannot see that shot's ground.
    """
    dest = os.path.join(_REMOTION, "src", "runtime", "shotLuma.ts")
    if table is None:
        jp = os.path.join(_REMOTION, "_ground_luma.json")
        if not os.path.exists(jp):
            print("no measurement to apply: %s is missing (run without --apply-json first)" % jp)
            return 1
        table = json.load(open(jp, encoding="utf-8"))["table"]
    src = open(dest, encoding="utf-8").read()
    head = "export const DNA_GROUND_TOKEN"
    i = src.index(head)
    j = src.index("\n};", i) + 3
    block, kept, wrote = src[i:j], 0, 0
    lines = []
    for line in block.split("\n"):
        m = re.match(r"^  (\w+):\s*(.+?),(\s*//.*)?$", line)
        if not m:
            lines.append(line); continue
        shot, comment = m.group(1), (m.group(3) or "")
        # PROVISIONAL FIRST, and match the declared-only sentinel EXACTLY. The provisional marker's own
        # text reads "... NOT the declared-only marker" — so a substring test for "declared-only" matched
        # the very comment that says it is not one, and every placeholder was skipped as if it were a
        # deliberate declaration. Eleven entries stayed unmeasured through repeated --emit runs that
        # reported success. A sentinel you can only detect by substring is a sentinel that will one day
        # appear inside the prose explaining it.
        if "PROVISIONAL" not in comment and re.search(r"//\s*declared-only", comment):
            lines.append(line); kept += 1; continue
        # A LITERAL IS SELF-IDENTIFYING, and that is why it is not guarded by a comment. The sentinel bug
        # recorded above happened because a marker had to be spelled right in prose; `'#efe9dd'` cannot be
        # mis-spelled into a token. The measurement can never produce a literal (it only names probe
        # tokens), so writing over one would silently replace a ground the register paints unconditionally
        # with whichever token the probe happened to sit nearest.
        if re.match(r"^'#[0-9a-fA-F]{3,6}'$", m.group(2).strip()):
            lines.append(line); kept += 1; continue
        if shot not in table:
            lines.append(line); kept += 1; continue
        tok = table[shot]
        want = ("'%s'" % tok) if isinstance(tok, str) else ("[%s]" % ", ".join("'%s'" % x for x in tok))
        # A MEASURED ENTRY IS NO LONGER PROVISIONAL. The marker survived an --emit that CONFIRMED the
        # placeholder's guess, so eleven entries stayed flagged as unmeasured after being measured — and a
        # flag that outlives the thing it warns about trains everyone to ignore it. Dropped on write.
        if "PROVISIONAL" in comment:
            comment = ""
        lines.append("  %s: %s,%s" % (shot, want, comment)); wrote += 1
    known = {re.match(r"^  (\w+):", l).group(1) for l in block.split("\n") if re.match(r"^  (\w+):", l)}
    added = sorted(set(table) - known)
    if added:                                            # a NEW shot the table has never carried
        tail = lines.pop()                               # the closing "};"
        for shot in added:
            tok = table[shot]
            want = ("'%s'" % tok) if isinstance(tok, str) else ("[%s]" % ", ".join("'%s'" % x for x in tok))
            lines.append("  %s: %s," % (shot, want))
        lines.append(tail)
    open(dest, "w", encoding="utf-8").write(src[:i] + "\n".join(lines) + src[j:])
    print("DNA_GROUND_TOKEN: %d updated, %d added (%s), %d left as declared-only/unknown"
          % (wrote, len(added), ", ".join(added) or "-", kept))
    return 0


_USAGE = ("usage: measure_ground_luma.py [--only=A,B | --only A,B] [--luma] [--emit] [--check] "
          "[--apply-json]")


def _only_or_stop(argv):
    """The `--only` list, in EITHER spelling, or None for the whole library — and never silently neither.

    This read `a.startswith("--only")` and then, when the arg carried no `=`, set the filter to None: so
    `--only DollyZoom` did not narrow the sweep, it THREW THE FILTER AWAY and measured all 164 registers,
    about half an hour, with nothing in the output saying so. A flag that silently inverts its own meaning
    is worse than one that is not implemented. A name that matches no register stops the run rather than
    quietly becoming a full sweep too."""
    only = _c.argflag_list(argv, "only")
    if only:
        known = set(dna_audit.registered_shots())
        missing = [n for n in only if n not in known]
        if missing:
            raise SystemExit("[shot_luma] --only names %d register(s) that do not exist: %s"
                             % (len(missing), ", ".join(missing)))
    return only


def _main_shot_luma(argv):
    """Measure SHOT_LUMA — each shot rendered on its OWN defaults, no DNA."""
    only = _only_or_stop(argv)
    shots = only or sorted(dna_audit.registered_shots())
    fixtures = _fixture_props()
    declared = read_shot_luma()
    measured, failed = {}, []
    with tempfile.TemporaryDirectory() as td:
        for i, sh in enumerate(shots, 1):
            lum, err = measure_own(sh, td, fixtures)
            if err is not None or lum is None:
                failed.append(sh)
                print("  [%3d/%d] %-24s RENDER FAILED" % (i, len(shots), sh))
                continue
            b = luma_bucket(lum)
            measured[sh] = b
            flag = "" if declared.get(sh) == b else "   <- declared %r" % declared.get(sh)
            print("  [%3d/%d] %-24s %-5s (rel-lum %.3f)%s" % (i, len(shots), sh, b, lum, flag))

    drift = sorted(k for k, v in measured.items() if declared.get(k) != v)
    prov = provisional_shots()
    if prov:
        print("[shot_luma] %d entry(ies) are still PROVISIONAL placeholders written by register_shot.py "
              "(never measured): %s" % (len(prov), ", ".join(prov)))
    if failed:
        print("[shot_luma] %d shot(s) would not render; their entries are UNCHANGED: %s"
              % (len(failed), ", ".join(failed)))
    if "--emit" in argv:
        n = write_shot_luma(measured)
        print("[shot_luma] wrote %d corrected entry(ies) into shotLuma.ts" % n)
        return 0
    if "--check" in argv:
        if drift or prov:
            print("[shot_luma] FAIL — %d declared value(s) disagree with the pixels%s. Re-run with --emit."
                  % (len(drift), " and %d are unmeasured placeholders" % len(prov) if prov else ""))
            for k in drift:
                print("    %-24s declared %-5s  measured %s" % (k, declared.get(k), measured[k]))
            return 1
        print("[shot_luma] OK  %d shot(s), declaration matches the pixels" % len(measured))
        return 0
    print("[shot_luma] %d measured, %d disagree with the committed table" % (len(measured), len(drift)))
    return 0


def main(argv):
    _c.refuse_unknown(argv, valued=("only",), switches=("luma", "emit", "check", "apply-json"), usage=_USAGE)
    if "--luma" in argv:
        return _main_shot_luma(argv)
    if "--apply-json" in argv:      # apply a PREVIOUS measurement; never re-render (that is --emit)
        return _emit(None)
    only = _only_or_stop(argv)
    shots = only or sorted(dna_audit.registered_shots())
    fixtures = _fixture_props()
    lums = token_lums()
    print("probe token luminances: " + ", ".join("%s=%.3f" % (k, v) for k, v in sorted(lums.items(), key=lambda kv: kv[1])))
    out, unclassified, failed, meas = {}, [], [], {}
    with tempfile.TemporaryDirectory() as td:
        for i, s in enumerate(shots, 1):
            lum, err = measure(s, td, fixtures)
            if err is not None:
                failed.append(s); print("  [%3d/%d] %-24s RENDER FAILED" % (i, len(shots), s)); continue
            meas[s] = lum
            tok, d = classify(lum, lums)
            if tok is None:
                unclassified.append((s, lum)); print("  [%3d/%d] %-24s lum=%.3f  UNCLASSIFIED" % (i, len(shots), s, lum))
            else:
                out[s] = tok; print("  [%3d/%d] %-24s lum=%.3f  -> %s" % (i, len(shots), s, lum, tok if isinstance(tok,str) else "+".join(tok)))
    print("\nmeasured %d · unclassified %d · failed %d" % (len(out), len(unclassified), len(failed)))
    if "--check" in argv:
        cur = open(os.path.join(_REMOTION, "src", "runtime", "shotLuma.ts"), encoding="utf-8").read()
        bad, off, ok_lit, ok_unc = [], [], 0, 0
        # A declared-only entry is declared PRECISELY because the measurement cannot see its ground
        # (content bleeds to the frame edge, so the border ring samples content). Comparing it against a
        # measurement would make this gate cry wolf forever — and a gate that always warns is ignored.
        declared_only = set(re.findall(r"^\s{2}(\w+):[^/\n]*//\s*declared-only", cur, re.M))
        declared = declared_tokens(cur)
        harsh = harsh_gap(cur)
        for shot in sorted(meas):
            if shot in declared_only:
                continue
            decl, lum = declared.get(shot), meas[shot]
            # A LITERAL DECLARATION IS CHECKED AS A LUMINANCE, always — never against the probe's tokens.
            # It says "this shot paints THIS colour whatever the palette is", so the only honest question is
            # whether the pixels are that colour; asking which token it resembles would report drift on a
            # register that is behaving exactly as declared, the moment a probe token drifted near it.
            if isinstance(decl, str):
                pred = _rel_lum(decl)
                d = _gap(lum, pred)
                if d >= harsh:
                    off.append((shot, lum, pred, d))
                else:
                    ok_lit += 1
                continue
            if shot in out:
                tok = out[shot]
                want = ("'%s'" % tok) if isinstance(tok, str) else ("[%s]" % ", ".join("'%s'" % x for x in tok))
                if ("  %s: %s," % (shot, want)) not in cur:
                    bad.append("%s -> %s" % (shot, tok if isinstance(tok, str) else "+".join(tok)))
                continue
            # UNCLASSIFIED USED TO MEAN UNCHECKED, and that is how the worst entry in the table survived.
            # `PaperSlot` prints on its own stock under every dark preset, so its border measured 0.811
            # while it declared `bg` (0.002 under this probe) — a ground the classifier could not name a
            # token for, so the loop below skipped it and the gate printed "matches the measured pixels".
            # The caption ink read that `bg` and drew #ffffff on #efe9dd paper: 1.22:1, in a delivered
            # frame. A classifier that cannot NAME the token can still say whether the DECLARED one is
            # anywhere near the pixels, and that is the question the two consumers actually ask.
            pred = _declared_y(decl, lums)
            if pred is None:
                off.append((shot, lum, None, None))
                continue
            d = _gap(lum, pred)
            if d >= harsh:
                off.append((shot, lum, pred, d))
            else:
                ok_unc += 1
        if bad or off:
            if bad:
                print("DNA_GROUND_TOKEN has DRIFTED from the pixels (%d shot(s)):" % len(bad))
                for b in bad:
                    print("  " + b)
            if off:
                print("DNA_GROUND_TOKEN declares a ground the pixels contradict (%d shot(s)) — the seam "
                      "guard calls a cut a flash at %.2f, so an entry off by that much can flip it alone:"
                      % (len(off), harsh))
                for shot, lum, pred, d in off:
                    if pred is None:
                        print("  %-24s measured %.3f, declaration %r cannot be resolved"
                              % (shot, lum, declared.get(shot)))
                    else:
                        print("  %-24s measured %.3f, declared %s = %.3f  (display gap %.3f)"
                              % (shot, lum, declared.get(shot), pred, d))
            print("re-run: python3 scripts/measure_ground_luma.py --emit")
            return 1
        print("DNA_GROUND_TOKEN matches the measured pixels (%d classified, %d literal, %d unclassified "
              "but consistent with their declaration)" % (len(out), ok_lit, ok_unc))
        return 0
    if "--emit" in argv:
        return _emit(out)
    dest = os.path.join(_HERE, "..", "remotion", "_ground_luma.json")
    if only:
        # A --only run is a SPOT CHECK; it must never overwrite the full-library table. It did once,
        # silently, and a 134-shot measurement was lost to a 1-shot rerun.
        print("(--only run: spot check, table NOT written)")
    else:
        json.dump({"table": out, "unclassified": [s for s, _ in unclassified], "failed": failed},
                  open(dest, "w"), indent=1)
        print("wrote " + os.path.relpath(dest, os.path.join(_HERE, "..")))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
