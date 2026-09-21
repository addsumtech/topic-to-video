#!/usr/bin/env python3
"""measure_ground_reach — MEASURE which registers a declared per-beat ground actually reaches.

WHY THIS FILE EXISTS. `GROUND_FOLLOWS_MEASURED` (remotion/src/runtime/shotLuma.ts) is the allow list
runtime/light.tsx consults before it lets a beat re-ground: a register that is not on it is REFUSED, so
the set is a load-bearing safety guard. It was produced by a throwaway script that was never committed —
the procedure survived only as prose in the table's comment — so nobody, including whoever adds register
150, could re-derive it. The table directly above it in the same file has had a committed command since
the day it was written (measure_ground_luma.py); this one has this.

WHAT IT MEASURES, AND WHY IT IS WIDER THAN THE SET IT REPLACES. The first sweep asked one question — does
the CAPTION BAND's luminance follow the declared ground, so the burned subtitle picks the right ink — and
that let through registers whose own content is destroyed by the ground it admits. Measured on the
committed list: GlitchDatamosh's display word 'SIGNAL' stays pure white on paper (1.14:1), HoloFoil's
subtitle 1.01:1, StarfieldWarp's trails 1.11:1, and GearTrain / HudReticle / ClothWave keep a hardcoded
dark vignette so the declared gallery white survives only as a rim (0.0%, 0.7%, 0.8% of the frame at the
declared luminance). Each one passes the band test and each one is a broken frame.

So a register FOLLOWS only when all three hold, measured from the SAME two renders — the shot as a
one-beat film under the two extreme grounds (#ffffff and #000000), installed exactly the way a declared
ground installs them (light.tsx `dnaWithGround(dna, groundFrom(dna, {bg}))`, asked of the real runtime,
never restated here) — AND it is not on the hand-measured refusal list below:

  1. BAND INK — the caption band's median luminance deserves the ink the declared ground picks, both ways.
     The original criterion, kept: it is the property the burned caption depends on.
  2. FIELD    — the CONTENT region's median luminance classifies light under the light ground and dark
     under the dark one. This is the "declared ground never becomes the frame" case: GearTrain measures
     0.240 under a white ground, so the gallery white survives as a rim around the register's own vignette.
  3. MOVED    — at least MOVED_MIN of the content pixels change between the two renders. A register that
     repaints a panel and keeps the rest is not re-grounded, it is smeared.

WHAT IT DOES NOT COVER, AND WHY THE REFUSAL LIST EXISTS. These three measure whether the declared GROUND
reaches the frame. They do NOT measure whether every glyph on it survived, and three pixel-only metrics
were tried for that and every one of them misranked a register that had been checked by eye:

  * stuck ink vs the DECLARED GROUND — flags a white glyph on paper, and equally flags white type inside a
    coloured chip that is perfectly legible (CollaborativeCursors, 0.65%, verified by opening the render).
  * stuck ink vs a BLURRED LOCAL background — the blur is contaminated by the ink itself, so the same chip
    text still measures 2.6:1 and the ranking does not clear: GlitchDatamosh, whose frame under a white
    ground is EMPTY (its display word is #ffffff), scores 0.27% against CollaborativeCursors' 0.49%.
  * fraction of INK pixels that move — SwissEditorial (verified perfect on paper) scores 68.4% against
    GlitchDatamosh's 58.3%. No threshold separates them.

Pixels cannot tell a glyph that vanished from a glyph that was always on its own chip; that needs the
element's own colour and the pixels behind it, which is a DOM measurement (runtime/textSafe.tsx already
enumerates glyph runs, and does not yet report their colours). Until that exists, the registers whose OWN
TYPE was measured illegible under a declared ground are refused BY NAME here, each with the measurement,
so the reason lives in the same file as the sweep instead of in a review comment. That list is the honest
part of this table: it is hand-measured, it is certainly incomplete, and a register absent from it has NOT
been shown to keep its type legible — only shown to hand its frame over to the ground.

It also measures one point in a large space: 1920x1080, frame 110 of a 150-frame beat, the `product` DNA.
Another aspect, another settled frame, or a DNA whose two inks sit closer together can surface ink this
sweep did not see. And it says nothing about MEANING — a register may follow a ground perfectly and still
be the wrong register for a paper beat.

  python3 scripts/measure_ground_reach.py             # measure all, print the table
  python3 scripts/measure_ground_reach.py --only A,B  # measure a few (method check)
  python3 scripts/measure_ground_reach.py --check     # non-zero when the committed set has drifted
  python3 scripts/measure_ground_reach.py --emit      # write GROUND_FOLLOWS_MEASURED into shotLuma.ts
  python3 scripts/measure_ground_reach.py --keep=DIR  # keep the probe PNGs, to LOOK at what was measured
  python3 scripts/measure_ground_reach.py --from=DIR  # re-derive the verdict from a kept sweep, no renders
"""
import json, os, re, shutil, subprocess, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from PIL import Image
import _common as _c
import dna_audit

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")
_RUNTIME = os.path.join(_REMOTION, "src", "runtime")
_SHOTLUMA = os.path.join(_RUNTIME, "shotLuma.ts")

# The two extreme grounds. The extremes are the point: a register that follows BOTH follows everything
# between them, and a register that keeps its own furniture shows it against at least one of them.
PROBE_GROUNDS = {"light": "#ffffff", "dark": "#000000"}
PROBE_DNA_ID = "product"
PROBE_W, PROBE_H = 1920, 1080
PROBE_SCALE = 0.5          # 960x540 — glyph strokes are still 4-8px wide, and it halves a 300-render sweep
PROBE_FRAME = 110          # the settled frame measure_ground_luma.py reads, for the same reason
PROBE_DUR = 150

# MOVED_MIN is a FLOOR, not a discovered boundary — said plainly because measure_ground_luma.py's
# thresholds sit in a genuinely empty band and these do not. Measured across the library the moved-fraction
# is continuous from 0% (ChartLive never reads a ground token at all) to 99.9%, with no gap to put a line
# in. 0.60 is therefore a statement rather than a finding: below it the frame is no longer MOSTLY the
# ground the beat asked for, whatever else it is.
MOVED_MIN = 0.60           # fraction of content pixels that must change with the ground
MOVED_DY = 0.10            # |dY| that counts as "this pixel followed the ground"

# REGISTERS WHOSE OWN TYPE IS DESTROYED BY A GROUND THEY OTHERWISE FOLLOW. Every one of these passes all
# three pixel criteria — the ground DOES become the frame — and then the register's hardcoded ink disappears
# into it. The ratios are glyph-pixel-against-the-pixels-behind-it measurements from the review that found
# this class; the two marked "(render read)" were re-confirmed here by rendering the pair and opening the
# PNGs (GlitchDatamosh's white-ground frame is empty apart from a cyan kicker; FocalIsolation's is a grey
# haze with a dark vignette in all four corners). See "WHAT IT DOES NOT COVER" above for why this is a list
# of names rather than a measurement, and treat its absence of a register as "not yet looked at".
INK_REFUSED = {
    "GlitchDatamosh": "display word 'SIGNAL' is #ffffff — 1.14:1 on paper; the frame is empty (render read)",
    "HoloFoil": "subtitle is #fff — 1.01:1 on paper",
    "StarfieldWarp": "6607 pure-white streak pixels at 1.10:1 on the light key",
    "EmberFlame": "'BUILT WITH FIRE' at 2.35:1, under ACCENT_CONTRAST_MIN",
    # Two of the three were repaired on 2026-09-21 (`4b99a6c`..): the sub-headline takes `fg` and the
    # vignette is scaled to the ground. The FIRST one stands and is deliberate — the receded cards are the
    # recede, and at the lens's own 0.18 opacity floor that label computes to 1.25:1 on this register's own
    # slate as well, not only on paper. A periphery you can read is not a periphery. So it stays refused.
    "FocalIsolation": "receded card labels 1.07:1 on their own card, by design (the sub-headline and the "
                      "#060910 vignette were repaired 2026-09-21) — render read",
    "CodeRain": "title+glow fall from 19.2:1 to 6.1:1 and the dark glow halo becomes a brown smudge on cream",
    # Found by RENDERING A WHOLE FILM with an authored light arc and looking at it, not by this sweep — which
    # is the honest measure of what the sweep still misses. The hub node's own label is hardcoded near-white,
    # so it survives the band test, the field test and the moved-fraction test and then vanishes: measured on
    # the delivered frame, 17.41:1 on the film's native dark, 1.07:1 on the light key.
    # REPAIRED 2026-09-21: the hub label and the node rims take `fg`. The entry stays until this sweep is
    # RE-RUN on it, because this list's whole claim is that every name in it carries a measurement — and the
    # measurement that would move it out has not been taken. Absence means "not looked at"; a stale presence
    # would mean "looked at and wrong", which is worse.
    "KnowledgeGraph": "hub label was hardcoded near-white (17.41:1 native, 1.07:1 on the light key, render "
                      "read); repaired 2026-09-21 and awaiting a re-measure by this sweep",
}

# WHAT THIS LIST IS, said plainly because it is load-bearing. INK_REFUSED is HAND-WRITTEN. The sweep below
# measures whether the declared ground BECOMES THE FRAME; it does not measure every glyph the register paints
# on it, because a register can hardcode one colour and pass all three pixel criteria. Every name here was
# found by rendering the register and reading the result, and each carries its measurement. A register's
# ABSENCE from this list therefore means "not yet looked at", never "checked and safe" — and the entry above
# was added after a full film render, which is how you should expect the next one to be found too.


def _srgb_lum_array(a):
    """Relative luminance of an HxWx3 uint8 array — the same formula shotLuma.ts `lumValue` uses, applied
    to pixels rather than to a hex, so the measurement is independent of the code under test."""
    c = a.astype(np.float32) / 255.0
    c = np.where(c <= 0.03928, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * c[..., 0] + 0.7152 * c[..., 1] + 0.0722 * c[..., 2]


# ── asking the real runtime ───────────────────────────────────────────────────────────────────────────
def _node(body):
    """Bundle `body` against the REAL light.tsx/dna.tsx and run it, returning its JSON.

    Nothing about the ground vocabulary is restated in Python: the probe DNAs are built by the same
    `dnaWithGround(dna, groundFrom(...))` a beat's provider uses, the caption ink is picked by the real
    `captionInk`, and the luminance buckets are the real `lumFromY`. A python copy of any of them would be
    a second definition that can go stale exactly when the runtime changes — which is the failure this
    whole table exists to catch."""
    tmp = tempfile.mkdtemp(prefix="ground_reach_")
    try:
        entry = os.path.join(tmp, "probe.tsx")
        head = ("import * as L from %s;\nimport * as D from %s;\nconst out: any = {};\n"
                % (json.dumps(os.path.join(_RUNTIME, "light")), json.dumps(os.path.join(_RUNTIME, "dna"))))
        open(entry, "w", encoding="utf-8").write(head + body + "\nconsole.log(JSON.stringify(out));\n")
        out = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node", "--external:react",
                            "--external:remotion", "--outfile=" + out, "--log-level=error"],
                           cwd=_REMOTION, capture_output=True, text=True)
        if b.returncode != 0:
            raise SystemExit("esbuild failed:\n" + b.stdout + b.stderr)
        env = dict(os.environ, NODE_PATH=os.path.join(_REMOTION, "node_modules"))
        r = subprocess.run(["node", out], cwd=_REMOTION, capture_output=True, text=True, env=env)
        if r.returncode != 0:
            raise SystemExit(r.stdout + r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def probe_dnas():
    """The two probe DNAs, built by the runtime itself: exactly the tokens `BeatGround` installs for a beat
    that declares `ground: {bg}`. Never assembled here — a python copy of `groundFrom` would drift from the
    real one precisely when the real one changed."""
    r = _node("""
      const dna = D.coerceDna(%s)!;
      out.dna = {}; out.groundY = {}; out.groundInk = {};
      for (const [k, bg] of Object.entries(%s)) {
        const g = L.groundFrom(dna, {bg: bg as string, name: 'probe-' + k});
        out.dna[k] = L.dnaWithGround(dna, g);
        out.groundY[k] = g.y;
        out.groundInk[k] = L.captionInk(g.y);      // the ink the DECLARED ground picks
      }
    """ % (json.dumps(PROBE_DNA_ID), json.dumps(PROBE_GROUNDS)))
    r["band"] = _node("import * as Y from %s;\nout.band = Y.captionBand(%d, %d);"
                      % (json.dumps(os.path.join(_RUNTIME, "layout")), PROBE_W, PROBE_H))["band"]
    r["groundLum"] = _node("import * as S from %s;\nout.lum = {};\nfor (const [k, y] of "
                           "Object.entries(%s)) out.lum[k] = S.lumFromY(y as number);"
                           % (json.dumps(os.path.join(_RUNTIME, "shotLuma")),
                              json.dumps(r["groundY"])))["lum"]
    return r


def runtime_verdicts(rows):
    """Ask the runtime the two questions only it can answer about the MEASURED luminances: which caption ink
    each one deserves (`captionInk`) and which bucket it falls in (`lumFromY`). One call for the whole sweep."""
    ys = [y for r in rows for y in (r["bandY"]["light"], r["bandY"]["dark"],
                                    r["fieldY"]["light"], r["fieldY"]["dark"])]
    return _node("""
      import * as S from %s;
      const ys = %s as number[];
      out.ink = ys.map((y) => L.captionInk(y));
      out.lum = ys.map((y) => S.lumFromY(y));
    """ % (json.dumps(os.path.join(_RUNTIME, "shotLuma")), json.dumps(ys)))


# A REGISTER THAT REFUSES TO DRAW WITHOUT ITS ARTEFACT WAS NEVER MEASURABLE HERE, and the consequence is
# not a gap in a table — `GROUND_FOLLOWS_MEASURED` is a load-bearing safety guard, and a register that can
# never be listed in it makes `validate.py` reject any beat declaring a `ground` on that register with no
# fix available. That is the same catch-22 `tests/test_provenance.py` records for provenance, in the
# luminance guard. Measured when a new list-of-pictures register was added: PhotoPlate and RealVersus, which
# have carried the evidence guard for weeks, both report RENDER FAILED here and always have.
# `measure_ground_luma.py` already solved this with one import; this is the same import.
_FIXTURE_ERR = []


def _fixture_props():
    del _FIXTURE_ERR[:]
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import register_energy
        register_energy.ensure_fixture()
        return register_energy.evidence_props()
    except Exception as exc:                             # noqa: BLE001 — no fixture is not a verdict
        # ...BUT A SWALLOWED ONE IS BLAMED ON THE REGISTER. With no fixtures the guarded registers simply
        # refuse to render, and the sweep prints RENDER FAILED beside their names — the gate's own broken
        # input, recorded as a fact about the library.
        _FIXTURE_ERR.append("the sweep could not build its evidence fixtures (%s)" % exc)
        return {}


# ── the renders ───────────────────────────────────────────────────────────────────────────────────────
def render(shot, key, dna, td, fixtures=None):
    """One beat of `shot`, grounded. Captions OFF: the band criterion reads the band's own pixels, and a
    burned subtitle sitting in it would be measuring the caption instead of the ground under it."""
    props = os.path.join(td, "p_%s_%s.json" % (shot, key))
    png = os.path.join(td, "%s__%s.png" % (shot, key))
    scene = {"shot": shot, "durF": PROBE_DUR}
    if fixtures and shot in fixtures:
        scene["props"] = fixtures[shot]                  # its artefact, or it draws furniture around a hole
    json.dump({"scenes": [scene], "dna": dna, "captions": False, "camera": 0},
              open(props, "w"))
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", "Film", png,
                        "--frame=%d" % PROBE_FRAME, "--gl=angle", "--timeout=90000",
                        "--scale=%s" % PROBE_SCALE, "--log=error", "--props=" + props],
                       cwd=_REMOTION, capture_output=True, text=True)
    if not os.path.exists(png):
        # THE MESSAGE, not the last 300 characters of a stack. One reader, in _common.render_error.
        return None, "; ".join([_c.render_error(r.stdout, r.stderr)] + _FIXTURE_ERR)
    return png, None


def stats(shot, pngs, band_px):
    """The three measurements, from the two renders of one shot."""
    Y = {k: _srgb_lum_array(np.asarray(Image.open(p).convert("RGB"))) for k, p in pngs.items()}
    h = Y["light"].shape[0]
    band = max(1, int(round(band_px * PROBE_SCALE)))
    content = slice(0, max(1, h - band))
    d = np.abs(Y["light"][content, :] - Y["dark"][content, :])
    return {"shot": shot,
            "bandY": {k: float(np.median(Y[k][h - band:, :])) for k in Y},
            "fieldY": {k: float(np.median(Y[k][content, :])) for k in Y},
            "moved": float((d >= MOVED_DY).mean())}


def verdict(row, ink, lum):
    """PASS/FAIL with the reason, from the three measurements plus the runtime's own two classifiers."""
    why = []
    for k in ("light", "dark"):
        if ink["band"][k] != ink["ground"][k]:
            why.append("band ink %s wants %s" % (k, ink["band"][k]))
        if lum["field"][k] != lum["ground"][k]:
            why.append("field %s reads %s" % (k, lum["field"][k]))
    if row["moved"] < MOVED_MIN:
        why.append("only %.0f%% of the frame moved" % (row["moved"] * 100))
    if row["shot"] in INK_REFUSED:
        why.append("ink: " + INK_REFUSED[row["shot"]])
    return (not why), why


# ── the committed set ─────────────────────────────────────────────────────────────────────────────────
def read_set():
    src = open(_SHOTLUMA, encoding="utf-8").read()
    block = src.split("GROUND_FOLLOWS_MEASURED", 1)[1].split("new Set([", 1)[1].split("]);", 1)[0]
    return set(re.findall(r"'(\w+)'", block))


def write_set(names):
    src = open(_SHOTLUMA, encoding="utf-8").read()
    i = src.index("export const GROUND_FOLLOWS_MEASURED")
    a = src.index("new Set([", i) + len("new Set([")
    b = src.index("]);", a)
    names = sorted(names)
    lines = ["\n  " + " ".join("'%s'," % n for n in names[j:j + 4]) for j in range(0, len(names), 4)]
    open(_SHOTLUMA, "w", encoding="utf-8").write(src[:a] + "".join(lines) + "\n" + src[b:])
    return len(names)


def main(argv):
    # BOTH SPELLINGS, AND NOTHING SILENTLY IGNORED — see scripts/_common.argflag for what the `=`-only form
    # cost: `--only X` fell through to None in a sibling script and swept all 164 registers without a word.
    # ...AND THE SWITCHES HAVE TO BE DECLARED TOO. `--check` and `--emit` are documented at the top of this
    # file and were both REFUSED, because `switches=` was never passed — so the two flags that read and
    # write the allow list could not be run at all. `validate.py` prints "re-measure with
    # `measure_ground_reach.py --emit`" as the fix for a real error, and that instruction died on this line.
    # A next-command a gate hands you has to be a command that exists.
    _c.refuse_unknown(argv, valued=("only", "keep", "from"), switches=("check", "emit"),
                      usage="usage: measure_ground_reach.py [--only=A,B] [--check] [--emit] "
                            "[--keep=DIR] [--from=DIR]")
    only = _c.argflag_list(argv, "only")
    keep = _c.argflag(argv, "keep")
    reuse = _c.argflag(argv, "from")
    if reuse:
        keep = reuse
    registered = set(dna_audit.registered_shots())
    # A NAME IN THE REFUSAL LIST THAT IS NOT A REGISTER REFUSES NOTHING, and looks exactly like a refusal
    # that is working. This repo has shipped that shape (an opt-in check that scored 0 on the very deck that
    # produced it), so the typo is caught here rather than by someone wondering why the frame is still broken.
    unknown = sorted(set(INK_REFUSED) - registered)
    if unknown:
        raise SystemExit("INK_REFUSED names shots that are not registered, so they refuse nothing: %s"
                         % ", ".join(unknown))
    shots = only or sorted(registered)
    probe = probe_dnas()
    band_px = probe["band"]
    print("probe: dna=%s  grounds=%s  ground Y=%s  caption band=%dpx  frame=%d"
          % (PROBE_DNA_ID, PROBE_GROUNDS, {k: round(v, 3) for k, v in probe["groundY"].items()},
             band_px, PROBE_FRAME))

    rows, failed = [], {}
    fixtures = _fixture_props()
    for msg in _FIXTURE_ERR:
        print("  [ground_reach] %s — the registers that need one will not render" % msg)
    td = keep or tempfile.mkdtemp(prefix="ground_reach_png_")
    os.makedirs(td, exist_ok=True)
    try:
        for i, shot in enumerate(shots, 1):
            pngs, err = {}, None
            for k in PROBE_GROUNDS:
                # --from re-reads a sweep that is already on disk. The verdict is a pure function of the
                # two renders, so re-deriving it after a criterion changes must not cost 300 renders —
                # that cost is exactly why the first sweep was run by a throwaway script and thrown away.
                p, e = os.path.join(td, "%s__%s.png" % (shot, k)), None
                if not (reuse and os.path.exists(p)):
                    p, e = render(shot, k, probe["dna"][k], td, fixtures)
                if e:
                    err = e
                    break
                pngs[k] = p
            if err or len(pngs) != 2:
                failed[shot] = err or ("only %d of the 2 probe grounds rendered, with no error reported"
                                       % len(pngs))
                print("  [%3d/%d] %-24s NOT MEASURED — %s" % (i, len(shots), shot, failed[shot][:160]))
                continue
            try:
                row = stats(shot, pngs, band_px)
            except Exception as exc:                 # noqa: BLE001 — one shot, not a 340-render sweep
                failed[shot] = "both renders exist and measuring them raised: %r" % (exc,)
                print("  [%3d/%d] %-24s NOT MEASURED — %s" % (i, len(shots), shot, failed[shot]))
                continue
            rows.append(row)
            print("  [%3d/%d] %-24s band %.3f/%.3f  field %.3f/%.3f  moved %5.1f%%"
                  % (i, len(shots), shot, row["bandY"]["light"], row["bandY"]["dark"],
                     row["fieldY"]["light"], row["fieldY"]["dark"], row["moved"] * 100))
    finally:
        if not keep:
            shutil.rmtree(td, ignore_errors=True)

    if not rows:
        print("nothing measured")
        return 1
    r = runtime_verdicts(rows)
    ink, lum = r["ink"], r["lum"]
    follows, refused = [], []
    for n, row in enumerate(rows):
        v_ink = {"band": {"light": ink[4 * n], "dark": ink[4 * n + 1]},
                 "ground": probe["groundInk"]}
        v_lum = {"field": {"light": lum[4 * n + 2], "dark": lum[4 * n + 3]},
                 "ground": probe["groundLum"]}
        ok, why = verdict(row, v_ink, v_lum)
        row["ok"], row["why"] = ok, why
        (follows if ok else refused).append(row)

    print("\n%d follow · %d refused" % (len(follows), len(refused)))
    # COVERAGE, against the universe this gate claims: every registered shot, or the --only subset. A
    # register that would not render is not a register that does not follow — it is one whose entry in a
    # load-bearing safety guard nobody has checked, and that difference decides whether `validate.py` lets
    # a beat re-ground it.
    _c.coverage("ground_reach", len(rows), len(shots), failed)
    for row in sorted(refused, key=lambda r: r["shot"]):
        print("  REFUSED %-24s %s" % (row["shot"], "; ".join(row["why"])))
    # A SPOT CHECK MUST NOT DESTROY THE RECORD. This wrote unconditionally, before the --only early return
    # below, so a two-register method check replaced the 149-shot sweep that produced the committed allow
    # list — and it did: the file in the tree held four rows. The allow list is a load-bearing safety guard,
    # and a guard nobody can re-derive is the exact failure this file was added to end.
    if only:
        print("(--only run: the %d-row sweep manifest is left untouched)"
              % len((json.load(open(os.path.join(_REMOTION, "_ground_reach.json"), encoding="utf-8"))
                     .get("rows") or []) if os.path.exists(os.path.join(_REMOTION, "_ground_reach.json"))
                    else []))
    else:
        # SAY WHAT IS BEING REPLACED. `--check` reads as read-only and rewrites this file, so a run that
        # measured fewer shots than the record it overwrites silently shrinks the record — which is the same
        # loss the `--only` guard above exists to prevent, arriving by the other door. It happened while
        # this very gate was being repaired: a two-shot probe replaced the 170-row sweep.
        dest = os.path.join(_REMOTION, "_ground_reach.json")
        was = 0
        if os.path.exists(dest):
            try:
                was = len(json.load(open(dest, encoding="utf-8")).get("rows") or [])
            except (OSError, ValueError):
                was = 0
        json.dump({"rows": rows,
                   # {shot: why}, and the universe measured against: a list of bare names cannot tell a
                   # missing fixture from a register that throws, and those want opposite fixes.
                   "failed": failed, "universe": len(shots),
                   "inkRefused": INK_REFUSED,
                   "thresholds": {"MOVED_MIN": MOVED_MIN, "MOVED_DY": MOVED_DY}},
                  open(dest, "w"), indent=1)
        print("wrote _ground_reach.json: %d row(s)%s"
              % (len(rows), "  <- REPLACED a record of %d — this sweep saw fewer shots than the last one"
                 % was if was > len(rows) else ""))

    names = {r["shot"] for r in follows}
    committed = read_set()
    if only:
        for row in rows:
            was = "listed" if row["shot"] in committed else "refused"
            print("  %-24s measured %-8s committed %s" % (row["shot"], "follows" if row["ok"] else "refused", was))
        # MERGE, rather than refuse. Refusing outright was the fix for a spot check that had REPLACED the
        # 149-shot list with four rows, and it over-corrected in the way `register_energy` already recorded:
        # a partial run could not correct the very rows it had just measured, so a NEW register measured as
        # following the ground stayed refused forever and the only route to listing it was a 149-render
        # sweep. Merging keeps both properties — nothing this run did not look at is touched, and what it
        # did look at is written.
        if "--emit" in argv:
            n = write_set((committed - {r["shot"] for r in rows}) | {r["shot"] for r in rows if r["ok"]})
            print("GROUND_FOLLOWS_MEASURED: merged %d measured row(s) into %d name(s)%s"
                  % (len(rows), n, "; %d shot(s) were NOT measured and keep whatever they had"
                     % len(failed) if failed else ""))
            return 1 if failed else 0
        print("(--only run: spot check, the committed set is NOT written — add --emit to merge these rows)")
        return 1 if failed else 0
    gained, lost = sorted(names - committed), sorted(committed - names - set(failed))
    if "--emit" in argv:
        n = write_set(names | (committed & set(failed)))   # a shot that would not render keeps its entry
        print("GROUND_FOLLOWS_MEASURED: wrote %d name(s) (+%d, -%d)" % (n, len(gained), len(lost)))
        if failed:
            # A SHOT THAT WOULD NOT RENDER KEEPS ITS ENTRY — which is the safe choice and an INVISIBLE one:
            # an entry nobody measured stays in a load-bearing allow list, and `validate.py` reads it as
            # "this register was measured to follow a declared ground".
            kept = sorted(committed & set(failed))
            print("    %d shot(s) were NOT measured; %d of them keep an UNVERIFIED entry in the set: %s"
                  % (len(failed), len(kept), ", ".join(kept) or "-"))
            return 1
        return 0
    if "--check" in argv:
        if gained or lost:
            print("GROUND_FOLLOWS_MEASURED has DRIFTED from the pixels:")
            for g in gained:
                print("    + %s follows but is not listed" % g)
            for l in lost:
                print("    - %s is listed but does not follow" % l)
            print("re-run: python3 scripts/measure_ground_reach.py --emit")
            return 1
        if failed:
            # THE SET IS A SAFETY GUARD, AND THIS EXITED 0 OVER ANY NUMBER OF UNMEASURED SHOTS. `lost`
            # deliberately excludes them so a failure cannot silently REMOVE a name; the cost is that the
            # check then compares the committed set against a sweep with holes in it and calls it a match.
            kept = sorted(committed & set(failed))
            print("GROUND_FOLLOWS_MEASURED cannot be confirmed: %d shot(s) were not measured (named "
                  "above)%s" % (len(failed), "; %d of them are LISTED in the set on an unverified entry: %s"
                                % (len(kept), ", ".join(kept)) if kept else ""))
            return 1
        print("GROUND_FOLLOWS_MEASURED matches the measured pixels (%d shots)" % len(names))
        return 0
    print("committed %d · measured %d · +%s · -%s" % (len(committed), len(names), gained, lost))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
