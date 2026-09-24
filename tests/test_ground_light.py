"""Per-beat GROUND and exposure key — runtime/light.tsx, and the two things it must not break.

WHY THIS FILE EXISTS. A film had exactly ONE ground: Film.tsx resolved `theme?.bg ?? dna?.bg ?? '#05060a'`
once for the whole TransitionSeries, and the brightest ground the eight presets can name is Y=0.0053. So a
30-beat film painted one identical near-black ground thirty times (measured library luminance range 0.013
against Figma's 0.903), and applying a DNA — which every delivered film does — DELETED the library's light
half: SwissEditorial, black type on cream, rendered white-on-near-black.

Most of what follows runs the REAL TypeScript through esbuild + node, the way
test_remotion.py::test_atoms_are_total_across_every_dna_and_edge_case does. A test that only greps the
source cannot tell a working light key from a light key that returns the dark one, and this repo's own rule
is that a test which merely checks the code exists is not a test.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REMOTION = os.path.join(ROOT, "remotion")
RUNTIME = os.path.join(REMOTION, "src", "runtime")
LIGHT_TSX = os.path.join(RUNTIME, "light.tsx")
FILM_TSX = os.path.join(REMOTION, "src", "Film.tsx")
SHOTLUMA_TS = os.path.join(RUNTIME, "shotLuma.ts")


def _src(path):
    return open(path, encoding="utf-8").read()


# ── running the real runtime ──────────────────────────────────────────────────────────────────────────
# ── THE ROSTER IS DERIVED, NOT LISTED ──────────────────────────────────────────────────────────────────
#
# Twice now a test here has named a register as "the one that cannot take a ground" and been overtaken by
# the register being repaired: `MaterialHero` (its floor bounces the film's ground since 2026-09-20) and
# then `ExplodedSchematic`, whose hardcoded navy became `dna?.bgGrad ?? dna?.bg` in 4b99a6c. Both times the
# test went red for the best possible reason — the library got better — and both times the red looked like
# a regression. Worse, the allow list had been DENYING ExplodedSchematic a capability it regained months
# earlier, because re-measuring cost a full sweep and so nobody did it.
#
# So the examples now come from the committed measurement. The rule under test never changes; only which
# registers illustrate it, and that is the thing that was never anyone's to hand-maintain.
def _measured(follows, n=2):
    """`n` registers the committed sweep measured as following / not following a declared ground."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "remotion", "_ground_reach.json")
    if not os.path.exists(path):
        pytest.skip("no ground-reach manifest committed")
    rows = json.load(open(path, encoding="utf-8")).get("rows") or []
    got = sorted(r["shot"] for r in rows if bool(r.get("ok")) is bool(follows))
    assert len(got) >= n, ("the sweep records fewer than %d register(s) that %s a ground — the rule these "
                           "tests pin has no example left: %r"
                           % (n, "follow" if follows else "refuse", got))
    return got[:n]


def run_probe(body):
    """Bundle `body` against the REAL light.tsx/dna.tsx/shotLuma.ts and run it, returning its JSON.

    The probe is written to a temp dir and imports by absolute path, so nothing is added to the repo;
    react/remotion stay external and are resolved at run time out of remotion/node_modules via NODE_PATH
    (light.tsx imports remotion for AbsoluteFill, but nothing here calls a hook).
    """
    if not shutil.which("npx") or not shutil.which("node"):
        pytest.skip("npx/node unavailable")
    if not os.path.isdir(os.path.join(REMOTION, "node_modules")):
        pytest.skip("remotion/node_modules not installed")
    tmp = tempfile.mkdtemp(prefix="ground_probe_")
    try:
        entry = os.path.join(tmp, "probe.tsx")
        header = (
            "import * as L from %s;\n"
            "import * as D from %s;\n"
            "import * as S from %s;\n"
            "const out: any = {};\n"
            "const fail = (k: string, e: unknown) => { out[k] = {threw: String(e)}; };\n"
        ) % (json.dumps(os.path.join(RUNTIME, "light")), json.dumps(os.path.join(RUNTIME, "dna")),
             json.dumps(os.path.join(RUNTIME, "shotLuma")))
        open(entry, "w", encoding="utf-8").write(header + body + "\nconsole.log(JSON.stringify(out));\n")
        out = os.path.join(tmp, "probe.cjs")
        b = subprocess.run(["npx", "esbuild", entry, "--bundle", "--platform=node",
                            "--external:react", "--external:remotion", "--outfile=" + out,
                            "--log-level=error"], cwd=REMOTION, capture_output=True, text=True)
        assert b.returncode == 0, "esbuild failed:\n" + b.stdout + b.stderr
        env = dict(os.environ, NODE_PATH=os.path.join(REMOTION, "node_modules"))
        r = subprocess.run(["node", out], cwd=REMOTION, capture_output=True, text=True, env=env)
        assert r.returncode == 0, r.stdout + r.stderr
        return json.loads(r.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _Y(hexc):
    """sRGB relative luminance — the same formula shotLuma.ts uses, replicated here so the test measures
    the rendered colour independently instead of asking the code under test what it thinks."""
    h = hexc.lstrip("#")
    ch = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255.0
        ch.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * ch[0] + 0.7152 * ch[1] + 0.0722 * ch[2]


def _contrast(a, b):
    return (max(a, b) + 0.05) / (min(a, b) + 0.05)


def _hue(hexc):
    import colorsys
    h = hexc.lstrip("#")
    r, g, b = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return colorsys.rgb_to_hls(r, g, b)[0] * 360


def _chroma(hexc):
    h = hexc.lstrip("#")
    v = [int(h[i:i + 2], 16) for i in (0, 2, 4)]
    return max(v) - min(v)


PRESETS = ["terminal", "neutral", "editorial", "product", "blueprint", "cinematic", "data", "retro"]


# ── 1. the ground is still one constant unless a beat says otherwise ──────────────────────────────────
def test_a_beat_that_declares_nothing_resolves_no_ground_at_all():
    """The backward-compatibility contract, at its source. `groundAt` must return null — not "the film's
    ground, resolved" — because the whole no-declaration path (no provider value change, no <Ground> paint)
    hangs off null. A version that helpfully returned the resolved native ground would still LOOK right and
    would repaint every existing film through the derived-token path."""
    r = run_probe("""
      for (const p of %s) {
        const dna = D.DNA_PRESETS[p];
        out[p] = {none: L.groundAt(dna, {}, 0, 150), withCaption: L.groundAt(dna, {ground: undefined}, 7, 150)};
      }
      out.noDna = L.groundAt(null, {}, 0, 150);
    """ % json.dumps(PRESETS))
    for p in PRESETS:
        assert r[p]["none"] is None, "%s: an undeclared beat resolved a ground" % p
        assert r[p]["withCaption"] is None
    assert r["noDna"] is None


def test_declaring_the_films_own_key_is_the_films_own_tokens_verbatim():
    """`key:'dark'` on a dark film must be the SAME PIXELS as declaring nothing, so the two ways of saying
    "this beat is lit like the film" cannot diverge. Verbatim, not "derived and it happens to match": the
    derivation rounds, and a rounded surface is a different colour."""
    r = run_probe("""
      for (const p of %s) {
        const dna = D.DNA_PRESETS[p];
        out[p] = {ground: L.groundAt(dna, {key: L.keyOf(dna)}, 0, 150), dna: {
          bg: dna.bg, bgGrad: dna.bgGrad, fg: dna.fg, dim: dna.dim, surface: dna.surface,
          surfaceBorder: dna.surfaceBorder, line: dna.line, accent: dna.accent, accent2: dna.accent2,
          onAccent: dna.onAccent}};
      }
    """ % json.dumps(PRESETS))
    for p in PRESETS:
        g, d = r[p]["ground"], r[p]["dna"]
        for k, v in d.items():
            if v is None:
                continue
            assert g[k] == v, "%s: key:'%s' changed %s (%s -> %s)" % (p, g["key"], k, v, g[k])


# ── 2. the light key: exposure moves, hue does not ────────────────────────────────────────────────────
def test_every_preset_has_a_light_key_that_is_actually_light():
    r = run_probe("""
      for (const p of %s) out[p] = L.groundAt(D.DNA_PRESETS[p], {key: 'light'}, 0, 150);
      out._floor = L.LIGHT_KEY_Y;
    """ % json.dumps(PRESETS))
    floor = r["_floor"]
    assert floor == 0.35, "the light-key boundary moved; the acceptance measurement is stated against 0.35"
    for p in PRESETS:
        g = r[p]
        y = _Y(g["bg"])
        assert g["key"] == "light" and y > floor, "%s light key is Y=%.3f, not on the light side" % (p, y)
        # the library's own dark grounds are all under Y=0.006, so a light key has to be a real jump
        assert y > 0.6, "%s light key is only Y=%.3f — a grey, not a paper" % (p, y)


def test_the_light_key_keeps_the_films_hue_and_only_moves_exposure():
    """A light key is not an inverted palette. Hue is the film's identity — a terminal film's mint accent
    must still be mint on paper, only darker — so the accents may change exposure and nothing else."""
    r = run_probe("""
      for (const p of %s) {
        const dna = D.DNA_PRESETS[p];
        out[p] = {light: L.groundAt(dna, {key: 'light'}, 0, 150), acc: dna.accent, acc2: dna.accent2};
      }
    """ % json.dumps(PRESETS))
    for p in PRESETS:
        g = r[p]
        for before, after in ((g["acc"], g["light"]["accent"]), (g["acc2"], g["light"]["accent2"])):
            if _chroma(after) < 12 or _chroma(before) < 12:
                continue                      # a near-neutral has no meaningful hue
            d = abs(_hue(before) - _hue(after))
            d = min(d, 360 - d)
            assert d <= 2.0, "%s: accent hue moved %.1f deg (%s -> %s) — a light key must only re-expose" % (
                p, d, before, after)


def test_a_light_key_ground_is_legible_for_ink_accents_and_chips():
    """The three contrast facts a re-grounded beat depends on, measured on the resolved colours rather than
    asserted: the ink reads on the ground, each accent clears the graphics floor, and the ink chosen for an
    accent fill reads on THAT accent (the DNA's own `onAccent` is dark in all eight presets, so a shaded
    accent would otherwise be dark-on-dark)."""
    r = run_probe("""
      for (const p of %s) out[p] = L.groundAt(D.DNA_PRESETS[p], {key: 'light'}, 0, 150);
    """ % json.dumps(PRESETS))
    for p in PRESETS:
        g = r[p]
        gy = _Y(g["bg"])
        assert _contrast(_Y(g["fg"]), gy) >= 7.0, "%s: ink on its light key is only %.1f:1" % (
            p, _contrast(_Y(g["fg"]), gy))
        for k in ("accent", "accent2"):
            c = _contrast(_Y(g[k]), gy)
            assert c >= 2.95, "%s: %s measures %.2f:1 on the light ground — a hairline in it disappears" % (p, k, c)
        c = _contrast(_Y(g["onAccent"]), _Y(g["accent"]))
        assert c >= 3.0, "%s: onAccent measures %.2f:1 on the accent it is drawn on" % (p, c)
        # dim is metadata, not decoration: the library's own presets put it 0.59 of the way to the ink
        assert _contrast(_Y(g["dim"]), gy) >= 2.4, "%s: dim is %.2f:1 — unreadable metadata" % (
            p, _contrast(_Y(g["dim"]), gy))


def test_the_light_key_is_derived_so_a_bespoke_dna_gets_one_too():
    """The eight presets are not the population: every topic-conceived film ships a bespoke DNA. The light
    key must be derived from what the film declares, and it must be SYMMETRIC — a film authored light gets a
    dark key from the same call."""
    r = run_probe("""
      const bespoke = {...D.NEUTRAL_DNA, id: 'bespoke', bg: '#1a0f22', fg: '#ffe9d6', accent: '#ff7a3d',
                       accent2: '#3dd6c4'};
      const lightFilm = {...D.NEUTRAL_DNA, id: 'lit', bg: '#f2efe6', fg: '#191512', accent: '#b3402a',
                         accent2: '#2f5d50'};
      out.bespokeNative = L.keyOf(bespoke);
      out.bespokeLight = L.groundAt(bespoke, {key: 'light'}, 0, 150);
      out.litNative = L.keyOf(lightFilm);
      out.litDark = L.groundAt(lightFilm, {key: 'dark'}, 0, 150);
      out.litLight = L.groundAt(lightFilm, {key: 'light'}, 0, 150);
    """)
    assert r["bespokeNative"] == "dark" and r["litNative"] == "light"
    assert _Y(r["bespokeLight"]["bg"]) > 0.6, r["bespokeLight"]
    assert r["litDark"]["key"] == "dark" and _Y(r["litDark"]["bg"]) < 0.05, r["litDark"]
    # a light film asked for its own key gets its own tokens back, unchanged
    assert r["litLight"]["bg"] == "#f2efe6"


# ── 3. the caption ink follows the ground, including across a ramp ────────────────────────────────────
def test_caption_ink_is_picked_by_measured_contrast_not_by_a_bucket():
    """The old rule asked the three-bucket Lum class, whose boundary is Y=0.5, while the crossover between
    the two burned inks is at Y=0.19. Everything in between got the LESS legible ink — white on Y=0.40
    measures 2.33:1 against the dark ink's 8.1:1. A film-wide preset ground never lands in that band; a
    ramp spends its whole crossing there."""
    ys = [0.0, 0.02, 0.10, 0.19, 0.22, 0.30, 0.40, 0.50, 0.70, 0.95, 1.0]
    r = run_probe("out.ink = %s.map((y) => L.captionInk(y)); out.dark = L.CAPTION_INK_DARK; "
                  "out.light = L.CAPTION_INK_LIGHT;" % json.dumps(ys))
    dark, light = _Y(r["dark"]), _Y(r["light"])
    for y, ink in zip(ys, r["ink"]):
        best = r["dark"] if _contrast(dark, y) >= _contrast(light, y) else r["light"]
        assert ink == best, "ink on Y=%.2f is %s (%.2f:1) when %s measures %.2f:1" % (
            y, ink, _contrast(_Y(ink), y), best, _contrast(_Y(best), y))
    assert r["ink"][ys.index(0.40)] == r["dark"], "the 0.19-0.5 band still gets the light ink"


def test_a_ground_that_ramps_across_the_boundary_flips_the_caption_ink_at_the_crossing():
    """The one thing a static per-register luminance table can never do. A beat ramps dark -> paper; the
    ink must be light while the ground is dark, dark once it is paper, and flip EXACTLY where the measured
    crossover is — not at the ramp's midpoint, and not once per frame."""
    dur = 150
    r = run_probe("""
      const dna = D.DNA_PRESETS['product'];
      const scene = {ground: {from: '#05060a', to: 'paper'}};
      out.frames = [];
      for (let f = 0; f < %d; f++) {
        const g = L.groundAt(dna, scene, f, %d);
        out.frames.push({f, bg: g.bg, y: g.y, ink: L.captionInk(g.y), key: g.key});
      }
    """ % (dur, dur))
    fr = r["frames"]
    assert len(fr) == dur
    inks = [f["ink"] for f in fr]
    flips = [i for i in range(1, len(inks)) if inks[i] != inks[i - 1]]
    assert len(flips) == 1, "the ink changed %d times across one ramp — %r" % (len(flips), flips)
    assert inks[0] != inks[-1], "the ink never changed at all: the ramp is not crossing the boundary"
    # every frame's ink is the more legible of the two, measured on that frame's actual ground
    for f in fr:
        y = _Y(f["bg"])
        other = "#ffffff" if f["ink"].lower() == "#141414" else "#141414"
        assert _contrast(_Y(f["ink"]), y) >= _contrast(_Y(other), y), \
            "frame %d: %s on %s is the less legible ink" % (f["f"], f["ink"], f["bg"])
    # the ground is PARKED at both ends, so a cross-dissolve never runs over a moving ground
    assert fr[0]["bg"] == fr[1]["bg"] and fr[-1]["bg"] == fr[-2]["bg"], "the ramp is not parked at the seams"


def test_the_ramp_is_deterministic_and_monotone():
    """Every frame is a pure function of the frame number (no Date.now, no Math.random anywhere in
    remotion/), and the light moves one way — a ramp that overshoots reads as a flicker, not a change."""
    r = run_probe("""
      const dna = D.DNA_PRESETS['editorial'];
      const scene = {ground: {from: 0, to: 'gallery'}};
      const once = [], twice = [];
      for (let f = 0; f < 90; f++) once.push(L.groundAt(dna, scene, f, 90).y);
      for (let f = 0; f < 90; f++) twice.push(L.groundAt(dna, scene, f, 90).y);
      out.once = once; out.twice = twice;
    """)
    assert r["once"] == r["twice"], "two identical calls disagreed — something in the ramp is not pure"
    ys = r["once"]
    assert all(b >= a - 1e-9 for a, b in zip(ys, ys[1:])), "the ramp is not monotone"
    assert ys[-1] - ys[0] > 0.6, "the ramp barely moved: %.3f -> %.3f" % (ys[0], ys[-1])
    src = _src(LIGHT_TSX)
    assert "Date.now" not in src and "Math.random" not in src, "light.tsx is not deterministic"


# ── 4. everything it refuses ──────────────────────────────────────────────────────────────────────────
def test_an_unhonourable_ground_fails_loudly_instead_of_quietly_keeping_the_films_own():
    """A ground the runtime cannot honour must throw. Silently keeping the film's ground looks exactly like
    a beat that was never authored — the failure mode that hides longest, and the reason `bgLum:'light'`
    could mean "a still-dark frame" for as long as it did."""
    r = run_probe("""
      const dna = D.DNA_PRESETS['product'];
      const cases: Array<[string, any, any]> = [
        ['unknownName', dna, {ground: 'papyrus'}],
        ['indexTooHigh', dna, {ground: 99}],
        ['indexNegative', dna, {ground: -1}],
        ['indexFractional', dna, {ground: 1.5}],
        ['noBg', dna, {ground: {fg: '#fff'}}],
        ['bgNotAHex', dna, {ground: {bg: 'rebeccapurple'}}],
        ['bgIsAGradient', dna, {ground: {bg: 'linear-gradient(#fff,#000)'}}],
        ['noDnaAtAll', null, {ground: 'paper'}],
        ['rampHalfUnknown', dna, {ground: {from: 'paper', to: 'nope'}}],
      ];
      for (const [name, d, scene] of cases) {
        try { out[name] = {ok: L.groundAt(d, scene, 0, 150)}; } catch (e) { fail(name, (e as Error).message); }
      }
    """)
    for name, res in r.items():
        assert "threw" in res, "%s was accepted and resolved to %r" % (name, res.get("ok"))
        assert len(res["threw"]) > 40, "%s threw a message with nothing actionable in it: %r" % (name, res["threw"])


def test_a_ground_is_refused_on_a_register_it_cannot_reach():
    """MEASURED HAZARD, not a hypothetical. `DNA_GROUND_TOKEN` records 148 of 149 registers grounding on
    `bg`, and that table is what the audit's leverage estimate rests on — but it is matched from a border
    ring, so it has false positives. Rendered under a declared ground, 12 registers do not follow it in the
    band the caption sits on: ExplodedSchematic paints a hardcoded navy, MaterialHero's 3D floor stays black
    under a paper key. On those the caption's ink flips to dark over pixels that are still black. The
    runtime cannot see the canvas, so it refuses the ground instead of shipping an unreadable subtitle.

    THE ROSTER HAS MOVED TWICE, WHICH IS WHY IT IS NO LONGER WRITTEN DOWN. `MaterialHero` was the second
    example until its floor and hemisphere were made to bounce the film's ground (2026-09-20). Then
    `ExplodedSchematic` was, until `4b99a6c` replaced its hardcoded navy with `dna?.bgGrad ?? dna?.bg` —
    and because re-measuring cost a full 185-shot sweep, nobody re-ran it, so the allow list went on
    DENYING that register a capability it had regained months earlier. Both times a hand-written roster
    turned a library improvement into a red test that read like a regression.

    So the examples are now read from the committed sweep (`_measured`). The rule is untouched: a register
    the pixels say cannot carry a declared ground must be refused one, because the runtime cannot see the
    canvas and the alternative is shipping a caption whose ink was picked for a ground that is not there."""
    refuse, follow = _measured(False), _measured(True, 3)
    r = run_probe("""
      const dna = D.DNA_PRESETS['product'];
      for (const shot of %s) {
        try { out[shot] = {ok: !!L.groundAt(dna, {ground: 'paper'}, 0, 150, shot)}; }
        catch (e) { fail(shot, (e as Error).message); }
      }
    """ % json.dumps(refuse + follow))
    for shot in refuse:
        assert "threw" in r[shot], "%s accepted a ground the sweep measured it cannot render" % shot
        assert shot in r[shot]["threw"], "the refusal does not name the register"
    for shot in follow:
        assert r[shot].get("ok"), "%s was refused a ground the sweep measured it DOES follow: %r" % (shot, r[shot])


def test_a_beat_cannot_describe_one_ground_and_paint_another():
    """`bgLum` DESCRIBES the ground (the hint the caption pick and the seam guard read); `ground`/`key`
    COMMAND one. When they disagree the film tells itself two stories and the caption believes the wrong
    one. Film.tsx refuses the pair rather than letting a stale hint outvote the pixels."""
    film = _src(FILM_TSX)
    body = film[film.index("export const Film:"):]
    assert re.search(r"lumFromY\(g\.y\)\s*!==\s*sc\.bgLum", body), \
        "Film.tsx no longer compares a beat's declared bgLum against the ground it actually paints"
    assert "throw new Error(`scene ${i}" in body, "the disagreement is not refused, only noticed"


# ── 5. the wiring, and what must not have moved ───────────────────────────────────────────────────────
def test_the_dna_is_provided_inside_each_sequence_not_once_for_the_whole_series():
    """The mechanism itself. Provided outside the TransitionSeries, `bg` is a film-wide constant and no beat
    can change the light — which is the defect. It has to be provided INSIDE the Sequence."""
    film = _src(FILM_TSX)
    seq = film[film.index("<TransitionSeries.Sequence"):film.index("</TransitionSeries.Sequence>")]
    assert "<BeatGround" in seq, "the per-beat ground provider is not inside the Sequence"
    assert re.search(r"<BeatGround[^>]*\bscene=\{sc\}", seq), "BeatGround is not given the beat's own spec"
    light = _src(LIGHT_TSX)
    beat = light[light.index("export const BeatGround"):]
    assert "DesignDNAContext.Provider" in beat and "GroundContext.Provider" in beat, \
        "BeatGround no longer provides the beat's DNA and ground"


def test_the_seam_guard_and_the_veil_read_the_beats_ground_not_the_films():
    """A dark->paper cut is a luminance gap the seam grammar must see, and a film that opens on paper must
    not fade in from the film's near-black. Both used a film-wide constant that per-beat grounds made
    obsolete."""
    film = _src(FILM_TSX)
    assert re.search(r"pickPresentation\(sc, scenes\[i \+ 1\], width, height, activeDna,\s*\n?\s*"
                     r"edgeGround\(sc, 'out'\)", film), \
        "pickPresentation is no longer given the two beats' resolved grounds"
    assert "dnaGroundY(prev.shot, prevG)" in film and "dnaGroundY(next.shot, nextG)" in film, \
        "the seam luminance gap is still measured against the film-wide ground"
    assert "const veilBg = outro > intro" in film, "the intro/outro veil is not the first/last beat's ground"


def test_the_caption_inks_are_not_restated_in_the_film():
    """Four disagreeing copies of the caption band is a scar this codebase still carries. The two burned
    inks now have two callers (the legacy bucket pick and the resolved-ground pick), so they live in one
    place and Film.tsx imports them."""
    film = _src(FILM_TSX)
    assert "CAPTION_INK_DARK" in film and "CAPTION_INK_LIGHT" in film
    caption = film[film.index("const CaptionTrack"):film.index("// CARRY")]
    assert "'#141414'" not in caption and "'#ffffff'" not in caption, \
        "the caption ink is written out as a literal again"


def test_the_luminance_buckets_have_exactly_one_definition():
    """`Y > 0.5 ? 'light' : Y > 0.18 ? 'mid' : 'dark'` was written out three times in shotLuma.ts for the
    same question, and per-beat grounds added a fourth caller."""
    src = _src(SHOTLUMA_TS)
    # count in CODE only — the definition's own comment quotes the expression it replaced
    code = "\n".join(l for l in src.split("\n") if not l.lstrip().startswith(("//", "*", "/*")))
    assert code.count("? 'light' :") == 1, "the luminance bucket boundaries are restated"
    assert "export const lumFromY" in src
    for name in ("lumOf", "dnaGroundLum"):
        body = src[src.index("export const " + name):]
        body = body[:body.index("\n};")]
        assert "lumFromY" in body, "%s no longer classifies through the single definition" % name
    # and the EXPOSURE key, whose rule had four callers within a page of each other in light.tsx
    lit = "\n".join(l for l in _src(LIGHT_TSX).split("\n") if not l.lstrip().startswith(("//", "*", "/*")))
    assert lit.count("LIGHT_KEY_Y") == 2, (
        "the light-key boundary is read in %d places — it has one definition and one classifier"
        % lit.count("LIGHT_KEY_Y"))
    assert lit.count("export const keyFromY") == 1


def test_every_registered_shot_is_classified_for_ground_reach():
    """Coverage, so a NEW register cannot default into being re-groundable without anyone measuring it.
    The classification itself is a render measurement (see the table's own comment); what belongs in pytest
    is the structural floor, the same split test_remotion.py makes for DNA_GROUND_TOKEN."""
    src = _src(SHOTLUMA_TS)
    block = src[src.index("GROUND_FOLLOWS_MEASURED"):]
    block = block[:block.index("]);")]
    listed = set(re.findall(r"'(\w+)'", block))
    reg = _src(os.path.join(REMOTION, "src", "registry.ts"))
    body = reg.split("export const REGISTRY")[1].split("{", 1)[1].split("};")[0]
    shots = set(re.findall(r"\b([A-Z]\w+)\b", body))
    assert len(shots) > 140, "the registry did not parse (%d)" % len(shots)
    unknown = listed - shots
    assert not unknown, "GROUND_FOLLOWS_MEASURED names shots that are not registered: %r" % sorted(unknown)
    # The set is the ALLOW list, so an unmeasured new shot is refused a ground rather than silently allowed.
    # That is the safe default; this asserts the two sets have not drifted into nonsense.
    assert len(listed) >= 100, "only %d registers are measured as ground-following" % len(listed)


def test_named_grounds_ship_a_light_half_and_a_chromatic_one():
    """The three moves the launch-film study names that this library could not make: a paper field, a
    gallery white, and a saturated chromatic ground that is the ground itself rather than an accent laid on
    top. At least two have to be on the light side of the key boundary or the film has no light half."""
    r = run_probe("""
      out.presets = {};
      for (const [k, v] of Object.entries(L.GROUND_PRESETS)) out.presets[k] = (v as any).bg;
      out.floor = L.LIGHT_KEY_Y;
    """)
    g = r["presets"]
    assert len(g) >= 3, g
    light = [k for k, v in g.items() if _Y(v) > r["floor"]]
    assert len(light) >= 2, "only %r are on the light side of Y=%s" % (light, r["floor"])
    chromatic = [k for k, v in g.items() if _chroma(v) >= 60]
    assert chromatic, "no saturated chromatic ground: %r" % g


def test_a_film_has_a_ground_vocabulary_with_no_authoring_at_all():
    """`dna.grounds` omitted is not "no grounds": the set is DERIVED from what the film already declares —
    its native ground, its opposite key, and a chromatic ground per accent — so index 0..3 mean something on
    every film, preset or bespoke, and nothing in the set is a copy of a colour stated elsewhere. The
    chromatic ones are pressed toward the film's DARK end, which is its ground on a dark film and its INK on
    a light one; pressing toward `bg` on a light film hands back the ground it already has."""
    r = run_probe("""
      const dark = D.DNA_PRESETS['retro'];
      const lit = {...D.NEUTRAL_DNA, id: 'lit', bg: '#f2efe6', fg: '#191512', accent: '#c8442a',
                   accent2: '#2f5d50'};
      for (const [name, dna] of [['dark', dark], ['lit', lit]] as Array<[string, any]>) {
        out[name] = {native: dna.bg, accent: dna.accent, accent2: dna.accent2,
                     g: [0, 1, 2, 3].map((i) => L.groundAt(dna, {ground: i}, 0, 150, 'SwissEditorial'))};
      }
    """)
    for name in ("dark", "lit"):
        g = r[name]["g"]
        assert g[0]["bg"].lower() == r[name]["native"].lower(), "%s: index 0 is not the film's own ground" % name
        assert g[1]["key"] != g[0]["key"], "%s: index 1 does not cross the exposure boundary" % name
        for i, seed in ((2, r[name]["accent"]), (3, r[name]["accent2"])):
            y = _Y(g[i]["bg"])
            assert y <= 0.16, "%s: chromatic ground %d is Y=%.3f — a highlight, not a field" % (name, i, y)
            if _chroma(g[i]["bg"]) >= 12 and _chroma(seed) >= 12:
                d = abs(_hue(g[i]["bg"]) - _hue(seed))
                assert min(d, 360 - d) <= 3.0, "%s: chromatic ground %d left the film's hue" % (name, i)
            # and it must still be a ground you can draw on
            assert _contrast(_Y(g[i]["fg"]), y) >= 4.5, "%s: nothing reads on chromatic ground %d" % (name, i)


def test_reduced_motion_freezes_the_ground_where_it_freezes_the_shot():
    """Under the accessibility mode every register is held at REDUCED_MOTION_T (motion.ts `useT`). A ground
    that kept ramping would then be the ONLY thing moving on the frame — and the largest moving area on it.
    It must freeze at the same point, and the caption HUD (a sibling of the reduced-motion provider, so it is
    handed the flag rather than reading it) must freeze with it or the ink would disagree with the ground."""
    r = run_probe("""
      const dna = D.DNA_PRESETS['product'];
      const scene = {ground: {from: '#05060a', to: 'paper'}};
      out.moving = [0, 30, 60, 89].map((f) => L.groundAt(dna, scene, f, 90, 'SwissEditorial', false)!.bg);
      out.frozen = [0, 30, 60, 89].map((f) => L.groundAt(dna, scene, f, 90, 'SwissEditorial', true)!.bg);
      out.settled = L.groundAt(dna, scene, 89, 90, 'SwissEditorial', false)!.bg;
    """)
    assert len(set(r["moving"])) == 4, "the ramp is not moving at all: %r" % r["moving"]
    assert len(set(r["frozen"])) == 1, "reduced motion still ramps the ground: %r" % r["frozen"]
    # frozen near the end of the ramp, like useT's REDUCED_MOTION_T = 0.86 — a settled frame, not the start
    assert _Y(r["frozen"][0]) > 0.6, "reduced motion froze the ground at its dark start: %s" % r["frozen"][0]


# ── 6. the edges, which were all silent ───────────────────────────────────────────────────────────────
# Everything below reproduces a defect a skeptic found in the first version of this feature. The pattern
# is one pattern: the CORE of the ground vocabulary refuses what it cannot honour, and every EDGE of it —
# a malformed window, a mistyped key, a derived value nobody checked — used to shrug and paint something
# confidently wrong. A silently wrong colour is worse than a crash here, because the frame still renders.
def test_a_malformed_ramp_window_throws_instead_of_poisoning_every_token():
    """MEASURED: `groundAt(product, {ground: {from, to, at: '0.2'}}, ...)` returned every token as the
    invalid css colour `#NaNNaNNaN`, and rendered — SwissEditorial painting black on black, headline,
    rules and ticker all invisible, no error anywhere. `const [t0, t1] = g.at ?? rampWindow(durF)`
    destructures a STRING into t0='0', t1='.'; a one-element array leaves t1 undefined; `t1 - t0` is NaN,
    `clamp01(NaN)` is NaN and `Math.round(NaN).toString(16)` is the string 'NaN'. `lumValue` then returns
    null for all nine tokens, so the beat reported y=0 and key='dark' and the caption picked ink for a
    ground that was never painted."""
    r = run_probe("""
      const dna = D.DNA_PRESETS['product'];
      const ramp = (at: any) => ({ground: {from: '#05060a', to: 'paper', at}});
      const cases: Array<[string, any]> = [
        ['aString', ramp('0.2')], ['oneElement', ramp([0.2])], ['reversed', ramp([0.8, 0.2])],
        ['equalBounds', ramp([0.5, 0.5])], ['aNaN', ramp([NaN, 1])], ['pastOne', ramp([0, 1.4])],
        ['negative', ramp([-0.2, 1])], ['threeElements', ramp([0, 0.5, 1])], ['anObject', ramp({t0: 0})],
        ['strings', ramp(['0', '1'])],
      ];
      for (const [name, scene] of cases) {
        try { out[name] = {ok: L.groundAt(dna, scene, 50, 100, 'SwissEditorial', false)}; }
        catch (e) { fail(name, (e as Error).message); }
      }
      out.valid = L.groundAt(dna, ramp([0.2, 0.8]), 50, 100, 'SwissEditorial', false);
      out.omitted = L.groundAt(dna, {ground: {from: '#05060a', to: 'paper'}}, 50, 100, 'SwissEditorial', false);
    """)
    for name in ("aString", "oneElement", "reversed", "equalBounds", "aNaN", "pastOne", "negative",
                 "threeElements", "anObject", "strings"):
        assert "threw" in r[name], "at=%s was accepted and resolved to %r" % (name, r[name].get("ok"))
        assert "at" in r[name]["threw"] and "start" in r[name]["threw"], \
            "the refusal does not name the field or its legal shape: %r" % r[name]["threw"]
    # and a window that IS legal still ramps — the guard must not have closed the door on the feature
    for k in ("valid", "omitted"):
        for tok, v in r[k].items():
            if isinstance(v, str) and v.startswith("#"):
                assert re.fullmatch(r"#[0-9a-fA-F]{6}", v), "%s.%s is %r, not a colour" % (k, tok, v)


def test_an_unknown_key_is_refused_instead_of_meaning_the_opposite_exposure():
    """MEASURED: `key:'ligth'` rendered a beat in the LIGHT key — modal RGB (246,248,252) over 86.2% of the
    frame — because the decision was `scene.key === keyOf(dna) ? native : flip`, so ANY string that is not
    the film's own key flipped it. A typo repainted the largest area on the frame and said nothing.
    Nothing else validates the field: validate.py does not know it, and the bgLum cross-check only fires
    when the beat also declares bgLum."""
    r = run_probe("""
      const dna = D.DNA_PRESETS['product'];
      for (const k of ['ligth', 'Light', 'LIGHT', 'bright', 'dark ', ' light', 'day', '', null, 0, true]) {
        try { out[JSON.stringify(k)] = {ok: L.groundAt(dna, {key: k} as any, 0, 150, 'SwissEditorial')}; }
        catch (e) { fail(JSON.stringify(k), (e as Error).message); }
      }
      out.legal = {dark: !!L.groundAt(dna, {key: 'dark'}, 0, 150, 'SwissEditorial'),
                   light: !!L.groundAt(dna, {key: 'light'}, 0, 150, 'SwissEditorial')};
    """)
    legal = r.pop("legal")
    assert legal["dark"] and legal["light"], "the two legal keys stopped working: %r" % legal
    for k, res in r.items():
        assert "threw" in res, "key %s was accepted and resolved to %r" % (k, res.get("ok"))
        assert "'dark'" in res["threw"] and "'light'" in res["threw"], \
            "the refusal for key %s does not name the two legal values: %r" % (k, res["threw"])


def test_a_light_key_is_actually_light_on_a_dna_whose_ink_is_not_near_white():
    """MEASURED: `flipKeySpec` lifted the film's ink by a fixed 30% and nothing checked where it landed, so
    `key:'light'` returned a DARK ground on any DNA whose ink is not near-white — every fg from #555555 to
    #757575 gave a ground whose own key was 'dark' (fg #6d6d6d -> #999999, Y=0.319), and just above that
    boundary it gave a mid grey nothing could be read on (fg #7d7d7d -> #a4a4a4, Y=0.371). That is
    `bgLum:'light'` — a declaration that never repaints a pixel — reintroduced one layer up. The eight
    presets all have near-white inks, so the general case was unguarded and untested."""
    inks = ["#111111", "#333333", "#555555", "#6d6d6d", "#757575", "#7a7a7a", "#7d7d7d", "#999999",
            "#bbbbbb", "#4a3b2c", "#2c3a4a", "#e8e2d8"]
    r = run_probe("""
      out.light = {}; out.dark = {};
      for (const fg of %s) {
        const dark = {...D.NEUTRAL_DNA, id: 'x', bg: '#050608', fg};
        const lit = {...D.NEUTRAL_DNA, id: 'y', bg: '#f4f0e6', fg};
        try { out.light[fg] = L.groundAt(dark as any, {key: 'light'}, 0, 150); }
        catch (e) { out.light[fg] = {threw: (e as Error).message}; }
        try { out.dark[fg] = L.groundAt(lit as any, {key: 'dark'}, 0, 150); }
        catch (e) { out.dark[fg] = {threw: (e as Error).message}; }
      }
      out.floor = L.LIGHT_KEY_Y;
    """ % json.dumps(inks))
    for fg in inks:
        g = r["light"][fg]
        assert "threw" not in g, "a light key was refused for ink %s: %s" % (fg, g.get("threw"))
        y = _Y(g["bg"])
        assert g["key"] == "light" and y > r["floor"], \
            "ink %s: 'light' resolved a %s ground (%s, Y=%.3f)" % (fg, g["key"], g["bg"], y)
        # not a technicality either — a ground a hair over the boundary is a mid grey, not a room
        assert y >= 0.60, "ink %s: the light key is Y=%.3f, a mid grey rather than a lit field" % (fg, y)
        d = r["dark"][fg]
        assert "threw" not in d, "a dark key was refused for ink %s: %s" % (fg, d.get("threw"))
        assert d["key"] == "dark" and _Y(d["bg"]) <= 0.10, \
            "ink %s: 'dark' on a light film resolved %s (Y=%.3f)" % (fg, d["bg"], _Y(d["bg"]))


def test_every_ground_the_vocabulary_can_produce_clears_the_legibility_floors():
    """The floors were asserted for ONE path — `key:'light'` on the eight presets — while the identical
    `groundFrom` produces the four named presets, every index into the derived vocabulary and any `#hex`.
    Measured over those: the shipped `clay` preset broke the very floor the light key was tested against
    (dim 2.18:1 on terminal, 2.37:1 on blueprint) and an accent on a mid ground landed on #ffffff at
    2.85:1 — under this file's own ACCENT_CONTRAST_MIN — because the exposure ladder walked toward the ink
    the KEY named rather than the one that measures more.

    So: run it over every path, and read the floors from the runtime rather than restating them."""
    greys = ["#%02x%02x%02x" % (v, v, v) for v in range(0, 256, 12)]
    hexes = ["#8b1e3f", "#0b6e4f", "#c8a415", "#2b3a67", "#d94f30", "#7a5c3e", "#008080", "#ff00ff",
             "#b8412e", "#4d5b2a", "#999999", "#737373"]
    r = run_probe("""
      out.floors = {ink: L.INK_CONTRAST_MIN, dim: L.DIM_CONTRAST_MIN, accent: L.ACCENT_CONTRAST_MIN};
      out.g = {};
      for (const p of %s) {
        const dna = D.DNA_PRESETS[p];
        const row: any = {};
        for (const k of ['dark', 'light']) row['key:' + k] = L.groundAt(dna, {key: k as any}, 0, 150);
        for (const name of Object.keys(L.GROUND_PRESETS)) row[name] = L.groundAt(dna, {ground: name}, 0, 150);
        for (let i = 0; i < 4; i++) row['index' + i] = L.groundAt(dna, {ground: i}, 0, 150);
        for (const h of %s.concat(%s)) row[h] = L.groundAt(dna, {ground: h}, 0, 150);
        out.g[p] = row;
      }
    """ % (json.dumps(PRESETS), json.dumps(greys), json.dumps(hexes)))
    f = r["floors"]
    assert f["ink"] >= 4.5 and f["dim"] >= 2.4 and f["accent"] >= 3.0, f
    n = 0
    for p, row in r["g"].items():
        for name, g in row.items():
            gy = _Y(g["bg"])
            n += 1
            for tok, floor in (("fg", f["ink"]), ("dim", f["dim"]),
                               ("accent", f["accent"]), ("accent2", f["accent"])):
                c = _contrast(_Y(g[tok]), gy)
                assert c >= floor - 1e-9, "%s / %s: %s measures %.2f:1 on %s (floor %s)" % (
                    p, name, tok, c, g["bg"], floor)
            c = _contrast(_Y(g["onAccent"]), _Y(g["accent"]))
            assert c >= f["ink"] - 1e-9, "%s / %s: onAccent measures %.2f:1 on its own accent" % (p, name, c)
    assert n >= 8 * 30, "the sweep only covered %d grounds" % n


def test_declaring_the_films_own_key_is_a_no_op_even_on_a_register_that_refuses_grounds():
    """`key:'dark'` on a dark film is documented as the same pixels as declaring nothing — but the reach
    REFUSAL ran before the no-op check, so it threw on the twelve registers that do not follow a ground.
    An EDL pass that stamps a key on every beat (the obvious next step for this vocabulary) would have
    crashed the film on exactly those beats, for a declaration that changes nothing about them."""
    refuse, follow = _measured(False), _measured(True, 1)
    r = run_probe("""
      const dna = D.DNA_PRESETS['product'];
      out.noop = {}; out.flip = {};
      // the refusers and the follower are read from the committed sweep — see _measured.
      for (const shot of %s) {
        try { out.noop[shot] = {ok: L.groundAt(dna, {key: 'dark'}, 0, 150, shot)}; }
        catch (e) { out.noop[shot] = {threw: (e as Error).message}; }
        try { out.flip[shot] = {ok: !!L.groundAt(dna, {key: 'light'}, 0, 150, shot)}; }
        catch (e) { out.flip[shot] = {threw: (e as Error).message}; }
      }
      out.dna = {bg: dna.bg, fg: dna.fg, dim: dna.dim, accent: dna.accent};
    """ % json.dumps(refuse + follow + ["NotARegister"]))
    for shot in refuse + follow:
        g = r["noop"][shot].get("ok")
        assert g, "key:'dark' on %s threw: %s" % (shot, r["noop"][shot].get("threw"))
        for k, v in r["dna"].items():
            assert g[k] == v, "%s: the no-op key changed %s (%s -> %s)" % (shot, k, v, g[k])
    # the FLIP still has to be refused there — the no-op is a no-op, not a way past the measurement
    for shot in refuse:
        assert "threw" in r["flip"][shot], "%s accepted a light key it cannot render" % shot
        assert shot in r["flip"][shot]["threw"] and "key: 'light'" in r["flip"][shot]["threw"], \
            "the refusal mis-describes the input as a ground: %r" % r["flip"][shot]["threw"]
    # A no-op does not consult the reach table at all, so it does not care whether the id is a register —
    # nothing is repainted, and Film.tsx's own REGISTRY lookup is what answers for a mistyped shot.
    assert r["noop"]["NotARegister"].get("ok"), r["noop"]["NotARegister"]
    # But where the table IS consulted, an id that is not a register is named as one rather than blamed on
    # the measurement — "this register does not follow one" sends the author to re-measure a shot that
    # does not exist.
    assert "unknown register" in r["flip"]["NotARegister"].get("threw", ""), r["flip"]["NotARegister"]


def test_a_hex_ground_has_exactly_one_definition():
    """There were two and they disagreed. `resolveRef` accepted /^#[0-9a-fA-F]{3,8}$/ and passed the string
    through verbatim; Film.tsx's caption tested /^#[0-9a-fA-F]{6}$/ and, when that failed, drew the
    caption's separation shadow in a colour computed from the FILM's DNA instead of the beat's. Measured on
    two beats of the same shot at the same local frame, one grounded `#fff` and one `#ffffff`: the `#fff`
    beat carried 77% more mid-grey fringe pixels in the caption strip — the dark-smudge mirror of the
    white-halo bug the line above it forbids."""
    film = _src(FILM_TSX)
    assert "/^#[0-9a-fA-F]{6}$/" not in film, "Film.tsx still decides for itself what a hex ground is"
    assert "hexGround(" in film, "Film.tsx does not use the shared definition"
    r = run_probe("""
      out.canon = {};
      for (const c of ['#fff', '#FFF', '#ffffff', '#FFFFFF', ' #f4f0e6 ', '#f4f0e6ff', '#ffff',
                       'rebeccapurple', 'linear-gradient(#fff,#000)', '#12345', null, 42])
        out.canon[JSON.stringify(c)] = L.hexGround(c as any);
      const dna = D.DNA_PRESETS['product'];
      out.short = L.groundAt(dna, {ground: '#fff'}, 0, 150, 'SwissEditorial');
      out.long = L.groundAt(dna, {ground: '#FFFFFF'}, 0, 150, 'SwissEditorial');
      try { out.alpha = {ok: L.groundAt(dna, {ground: '#f4f0e6ff'}, 0, 150, 'SwissEditorial')}; }
      catch (e) { out.alpha = {threw: (e as Error).message}; }
      try { out.alphaSpec = {ok: L.groundAt(dna, {ground: {bg: '#f4f0e6ff'}}, 0, 150, 'SwissEditorial')}; }
      catch (e) { out.alphaSpec = {threw: (e as Error).message}; }
    """)
    for c in ('"#fff"', '"#FFF"', '"#ffffff"', '"#FFFFFF"'):
        assert r["canon"][c] == "#ffffff", "%s canonicalised to %r" % (c, r["canon"][c])
    assert r["canon"]['" #f4f0e6 "'] == "#f4f0e6"
    for c in ('"#f4f0e6ff"', '"#ffff"', '"rebeccapurple"', '"linear-gradient(#fff,#000)"', '"#12345"',
              "null", "42"):
        assert r["canon"][c] is None, "%s was accepted as a hex ground (%r)" % (c, r["canon"][c])
    # the resolved ground stores the CANONICAL form, so the film tier never re-decides
    assert r["short"]["bg"] == r["long"]["bg"] == "#ffffff", (r["short"]["bg"], r["long"]["bg"])
    # a TRANSLUCENT ground is refused rather than silently opaque: lumValue drops the alpha, so a
    # #ffffff00 ground would report Y=1.0 while painting nothing at all
    for k in ("alpha", "alphaSpec"):
        assert "threw" in r[k], "a translucent ground was accepted: %r" % r[k].get("ok")
        assert "opaque" in r[k]["threw"], r[k]["threw"]


def test_a_malformed_grounds_vocabulary_throws_rather_than_falling_through():
    """(a) A non-array `dna.grounds` was silently dropped — `Array.isArray(dna.grounds) && length` fell
    through to the DERIVED vocabulary, so `ground: 0` resolved to the film's own ground and the colour the
    author declared was never painted anywhere. (b) `ground: 1.5` was reported as "outside this film's 4
    grounds (0..3)", which is a lie about a number inside that range."""
    r = run_probe("""
      const mk = (grounds: any) => D.coerceDna({id: 'x', bg: '#05060a', fg: '#eeeeee', grounds} as any);
      const cases: Array<[string, any]> = [
        ['object', mk({bg: '#123456'})], ['string', mk('#123456')], ['empty', mk([])],
        ['number', mk(3)], ['nullEntry', mk([null])], ['noBg', mk([{name: 'a'}])],
        ['bgNotString', mk([{bg: 16}])],
      ];
      for (const [name, dna] of cases) {
        try { out[name] = {ok: L.groundAt(dna, {ground: 0}, 0, 150, 'SwissEditorial')}; }
        catch (e) { fail(name, (e as Error).message); }
      }
      out.good = L.groundAt(mk([{bg: '#123456'}]), {ground: 0}, 0, 150, 'SwissEditorial');
      const p = D.DNA_PRESETS['product'];
      for (const [name, i] of [['fractional', 1.5], ['nan', NaN], ['inf', Infinity]] as Array<[string, number]>) {
        try { out[name] = {ok: L.groundAt(p, {ground: i}, 0, 150, 'SwissEditorial')}; }
        catch (e) { fail(name, (e as Error).message); }
      }
    """)
    good = r.pop("good")
    assert good["bg"] == "#123456", "a declared ground vocabulary is not being used: %r" % good
    for name in ("object", "string", "empty", "number", "nullEntry", "noBg", "bgNotString"):
        assert "threw" in r[name], "grounds=%s was ignored and resolved %r" % (name, r[name].get("ok"))
        assert "grounds" in r[name]["threw"], "the refusal does not name the field: %r" % r[name]["threw"]
    for name in ("fractional", "nan", "inf"):
        assert "threw" in r[name], "%s index was accepted" % name
        assert "whole number" in r[name]["threw"], \
            "%s is still reported as a RANGE error: %r" % (name, r[name]["threw"])


def test_the_ground_reach_measurement_is_a_committed_command():
    """The 149x2 sweep behind GROUND_FOLLOWS_MEASURED was run by a throwaway script that was never
    committed, so a load-bearing safety guard — it decides which beats are refused — could not be
    re-derived by anyone, including whoever adds register 150. The table directly above it in the same file
    has had a committed command since the day it was written."""
    script = os.path.join(ROOT, "scripts", "measure_ground_reach.py")
    assert os.path.exists(script), "the ground-reach sweep is still uncommitted prose"
    src = _src(script)
    for flag in ("--check", "--emit", "--only"):
        assert flag in src, "%s has no %s" % (os.path.basename(script), flag)
    # it must be able to READ BACK what it writes, or --check can never disagree with the file
    import importlib.util
    spec = importlib.util.spec_from_file_location("mgr", script)
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:                       # numpy/PIL absent in a bare env
        pytest.skip("measure_ground_reach imports unavailable: %s" % e)
    listed = mod.read_set()
    assert len(listed) > 50, "the committed set did not parse back: %d names" % len(listed)
    shot_luma = _src(SHOTLUMA_TS)
    assert "measure_ground_reach.py" in shot_luma, \
        "the table does not name the command that regenerates it"


def test_the_reach_measurement_covers_the_registers_own_ink_not_only_the_caption_band():
    """The first criterion asked ONE question — does the caption band's luminance follow the declared
    ground — and admitted registers whose own content the ground destroys. Measured as one-beat films with
    a legal declared ground: GlitchDatamosh's display word 'SIGNAL' stays pure white on paper (1.14:1),
    HoloFoil's subtitle 1.01:1, StarfieldWarp's trails 1.11:1, and GearTrain / HudReticle / ClothWave keep
    a hardcoded dark vignette so a gallery-white ground survives only as a rim (0.0%, 0.7%, 0.8% of the
    frame at the declared luminance). Every one of them was ON the allow list, and FocalIsolation — the
    register the feature used as its own `ground` example — was too.

    GEARTRAIN AND HUDRETICLE HAVE SINCE BEEN REPAIRED, and the roster moved with the measurement rather
    than the other way round. The vignette they held was `radial-gradient(<near-black literal>, ${BG})` —
    only the OUTER stop followed the DNA, so a paper film kept a navy pool in the middle of the page. Both
    now take `dna?.bgGrad ?? dna?.bg` (the house pattern nine other registers already use) and their ink
    reads from the film's, measured on a warm-white DNA at 5.33:1 median for both (2026-09-20,
    scripts/ink_contrast_qa.py). `measure_ground_reach.py --only=GearTrain,HudReticle,ClothWave` then
    reports both as FOLLOWING and ClothWave — untouched — as still refused, which is the control.

    GLITCHDATAMOSH IS NOW REFUSED BY DESIGN RATHER THAN BY DEFECT, and the 1.14:1 above is no longer
    reproducible. It declares `@dark-world` (2026-09-20) and takes its ground through `darkGround`, so under a
    declared paper ground it paints its OWN near-black rather than the film's warm white: its tear is two
    offset copies of the word composited with `mixBlendMode: 'screen'`, and screen over white is
    arithmetically nothing, so inverting the ink would not be a repair but a different picture. It must stay
    off this list for the same reason as before — the frame would be its night while the burned caption picked
    ink for the paper the beat declared.

    The rule this test states is unchanged: a register whose own content a declared ground destroys must not
    be on the list. Only the roster is a measurement, and measurements move when the code is repaired."""
    shot_luma = _src(SHOTLUMA_TS)
    block = shot_luma[shot_luma.index("GROUND_FOLLOWS_MEASURED"):]
    block = block[:block.index("]);")]
    listed = set(re.findall(r"'(\w+)'", block))
    for shot in ("GlitchDatamosh", "HoloFoil", "StarfieldWarp", "ClothWave",
                 "FocalIsolation", "EmberFlame", "CodeRain"):
        assert shot not in listed, \
            "%s is still allow-listed: its own type drops below the contrast floor under a declared ground" % shot
    # ...and the two that were repaired are on it, or the repair was undone and nothing said so
    for shot in ("GearTrain", "HudReticle"):
        assert shot in listed, \
            "%s was repaired to follow a declared ground and is no longer allow-listed — re-measure with " \
            "scripts/measure_ground_reach.py before assuming the list is wrong" % shot
    # and the runtime actually refuses them
    r = run_probe("""
      const dna = D.DNA_PRESETS['product'];
      for (const shot of ['GlitchDatamosh', 'HoloFoil', 'FocalIsolation', 'ClothWave', 'SwissEditorial',
                          'ChatThread', 'BlueprintGrid']) {
        try { out[shot] = {ok: !!L.groundAt(dna, {ground: 'paper'}, 0, 150, shot)}; }
        catch (e) { fail(shot, (e as Error).message); }
      }
    """)
    for shot in ("GlitchDatamosh", "HoloFoil", "FocalIsolation", "ClothWave"):
        assert "threw" in r[shot], "%s is still handed a ground it cannot honour" % shot
    for shot in ("SwissEditorial", "ChatThread", "BlueprintGrid"):
        assert r[shot].get("ok"), "%s was refused a ground it does follow: %r" % (shot, r[shot])


def test_a_ground_that_is_a_colour_resolves_without_a_dna():
    """A GROUND THE REGISTER PAINTS ITSELF is not a token, and the table has to be able to say so.

    `PaperSlot` adopts the film's ground only when it is light enough to pass for stock, and every one of the
    eight shipped presets is dark — so under all of them it prints on its own `#efe9dd`. Declared as `'bg'`,
    the caption HUD resolved the film's near-black and drew #ffffff on that paper: measured 1.22:1 in a
    rendered frame, legible only as the hollow outline behind it, and the seam guard scored a cut into it at
    a gap of ~0 while the pixels went 0.002 -> 0.811.

    Two properties, and the second is what makes the first load-bearing: a literal answers with NO palette
    at all (that is what makes it literal), while a token declaration still answers `null` without one.
    """
    r = run_probe("""
      out.litY      = S.dnaGroundY('PaperSlot', null);
      out.litLum    = S.dnaGroundLum('PaperSlot', undefined, null);
      out.litOnDark = S.dnaGroundLum('PaperSlot', undefined, D.DNA_PRESETS['terminal']);
      out.tokenY    = S.dnaGroundY('SwissEditorial', null);
      out.tokenDark = S.dnaGroundLum('SwissEditorial', undefined, D.DNA_PRESETS['terminal']);
    """)
    assert r["litY"] is not None, (
        "dnaGroundY answered null for a ground declared as a colour — the caption ink then falls back to the "
        "coarse bucket for a register whose exact luminance the table knows")
    assert abs(r["litY"] - 0.8185) < 0.002, "a literal ground did not resolve to its own luminance: %r" % r["litY"]
    assert r["litLum"] == "light", "a light literal classified as %r" % r["litLum"]
    assert r["litOnDark"] == "light", (
        "PaperSlot reports %r under a dark preset — that is the value that put white caption ink on its "
        "paper" % r["litOnDark"])
    # the control: without it the test passes with the literal branch deleted, because a `bg` declaration
    # under a dark preset ALSO answers 'dark' and the shot-vs-token distinction would never be exercised
    assert r["tokenY"] is None, "a TOKEN declaration resolved with no DNA — then nothing is literal"
    assert r["tokenDark"] == "dark"


# ── the one ladder ────────────────────────────────────────────────────────────────────────────────────
def test_the_readability_ladder_answers_the_question_it_is_asked():
    """`readsOn` is the library's single answer to "deepen this until it reads on that".

    It was four answers: `GFactorNoise` walked 12 rungs capped at 0.75, `FractalTree` 18 rungs capped at
    0.9 against two surfaces, `KSpaceAnatomy` took one fixed `tint(c, 0.6)` that overshoots 3:1 to 8.45:1,
    and this file's own `exposeTo` was a fifth that nobody could import. Four ladders are four different
    numbers for one question, and the register that gets it right is the one whose author measured that day.

    Every case here is a claim about the OUTPUT's contrast, not about which rung it landed on — a test that
    pins the rung pins the implementation and says nothing about whether the mark reads.
    """
    out = run_probe("""
      const C = (a: string, b: string) => D.contrastOf(a, b);
      // 1. a mark that already reads comes back VERBATIM — the ladder never touches what works
      out.verbatim = L.readsOn('#15181d', '#f6f3ee', 3.0) === '#15181d';
      // 2. a mark that does not read is walked until it does, on either polarity of ground
      const onPaper = L.readsOn('#7dd3fc', '#f6f3ee', 3.0);
      const onNight = L.readsOn('#1a2540', '#0b0d12', 3.0);   // a dark blue on a dark ground: 1.6:1
      out.paper = {c: C(onPaper, '#f6f3ee'), moved: onPaper !== '#7dd3fc'};
      out.night = {c: C(onNight, '#0b0d12'), moved: onNight !== '#1a2540'};
      // 3. the direction is DERIVED, not named: #999999 (Y=0.319) is a "dark" ground by the key boundary
      //    and yet black reads 7.4:1 on it where white reads 2.85:1. The ladder must go to black.
      const mid = L.readsOn('#8a8a8a', '#999999', 3.0);
      out.mid = {c: C(mid, '#999999'), darker: D.pilL(mid) < D.pilL('#999999')};
      // 4. SEVERAL surfaces: the mark has to clear all of them, which is what a line crossing two fills
      //    needs. A floor against one of them is what left FractalTree's twigs at 1.06:1 on the blossom.
      const both = L.readsOn('#7b876f', ['#918254', '#f6f3ee'], 3.0);
      out.both = {a: C(both, '#918254'), b: C(both, '#f6f3ee')};
      // 5. KEEP_HUE stops before the colour stops being itself: a warn red comes back red, not black
      const red = L.readsOn('#ff5d6c', '#f6f3ee', 4.5, L.KEEP_HUE);
      const [rr, gg, bb] = [1, 3, 5].map((i) => parseInt(red.slice(i, i + 2), 16));
      out.keepHue = {red: rr > gg + 30 && rr > bb + 30, notInk: red !== '#000000', c: C(red, '#f6f3ee')};
      // ...and without it, a colour that cannot clear the floor becomes ink rather than staying invisible
      out.fallsToInk = L.readsOn('#f6f3ee', ['#000000', '#ffffff'], 7.0) === '#000000'
                    || L.readsOn('#f6f3ee', ['#000000', '#ffffff'], 7.0) === '#ffffff';
      // 6. it degrades the way every colour helper in this codebase degrades
      out.passThrough = L.readsOn('currentColor', '#f6f3ee', 3.0) === 'currentColor'
                     && L.readsOn('#ff5d6c', 'not-a-colour', 3.0) === '#ff5d6c'
                     && L.readsOn('#ff5d6c', [], 3.0) === '#ff5d6c';
      // 7. `keep <= 0` means the caller asked for the colour not to move
      out.keepZero = L.readsOn('#7dd3fc', '#f6f3ee', 3.0, 0) === '#7dd3fc';
      // 8. DETERMINISTIC: the same question twice is the same answer
      out.stable = L.readsOn('#7dd3fc', '#f6f3ee', 3.0) === L.readsOn('#7dd3fc', '#f6f3ee', 3.0);
    """)
    assert out["verbatim"], "a mark that already reads is being moved"
    assert out["paper"]["moved"] and out["paper"]["c"] >= 3.0, out["paper"]
    assert out["night"]["moved"] and out["night"]["c"] >= 3.0, out["night"]
    assert out["mid"]["darker"] and out["mid"]["c"] >= 3.0, \
        "on a mid ground the ladder climbed toward the weaker ink: %r" % (out["mid"],)
    assert out["both"]["a"] >= 3.0 and out["both"]["b"] >= 3.0, \
        "a mark asked to clear two surfaces cleared one: %r" % (out["both"],)
    assert out["keepHue"]["red"] and out["keepHue"]["notInk"], \
        "the warn red came back as ink, which loses the semantics silently: %r" % (out["keepHue"],)
    assert out["fallsToInk"], "a colour that cannot clear its floor must still become visible"
    assert out["passThrough"], "the ladder does not degrade like the other colour helpers"
    assert out["keepZero"], "`keep <= 0` moved the colour anyway"
    assert out["stable"], "the ladder is not deterministic"


def test_the_ladder_did_not_change_what_exposeTo_already_answered():
    """`exposeTo` is now the one-surface case of the same ladder, and every derived token in this file goes
    through it. The ground vocabulary is measured, committed and depended on, so the migration has to be a
    refactor and not a re-tuning: every shipped preset's derived ground must come back byte-identical."""
    out = run_probe("""
      const PRESETS = Object.keys(D.DNA_PRESETS ?? {});
      out.presets = PRESETS.length;
      out.grounds = {};
      for (const p of PRESETS) {
        const dna = (D.DNA_PRESETS as any)[p];
        const rows: any = {};
        for (const [name, spec] of Object.entries(L.GROUND_PRESETS)) {
          try {
            const g = L.groundFrom(dna, spec as any);
            rows[name] = [g.bg, g.fg, g.accent, g.dim, g.line];
          } catch (e) { rows[name] = String(e); }
        }
        out.grounds[p] = rows;
      }
    """)
    assert out["presets"] >= 5, "no presets were read, so this test proves nothing"
    # A SNAPSHOT IS ONLY WORTH ITS SOURCE: this is the committed vocabulary, captured from the ladder's
    # single-surface path, so a later change to the ladder that moves a shipped ground fails here.
    import hashlib
    import json as _json
    digest = hashlib.sha256(_json.dumps(out["grounds"], sort_keys=True).encode()).hexdigest()[:16]
    # Recorded from the COMMITTED light.tsx before `exposeTo` became the one-surface case of `ladderTo`,
    # and unchanged after it — which is what makes the migration a refactor.
    assert digest == "f24b7dcbcbe9b037", (
        "a shipped preset's derived ground moved (%s). If that is intended, re-record the digest and say "
        "in the commit which ground changed and by how much." % digest)


def test_the_film_has_a_pale_end_and_it_is_not_always_fg():
    """`fg` is the light end on all eight shipped presets, because all eight are dark — so a register that
    wants a near-white object reaches for it and is right a hundred times, then draws a black cloud in a
    pale sky on the hundred-and-first. It is high-contrast, so no ink gate can see it."""
    out = run_probe("""
      const dark = {bg: '#0b0d12', fg: '#f2f5fa'} as any;
      const light = {bg: '#f6f3ee', fg: '#15181d'} as any;
      out.dark = {pale: L.paleEnd(dark, '#fff'), deep: L.deepEnd(dark, '#000')};
      out.light = {pale: L.paleEnd(light, '#fff'), deep: L.deepEnd(light, '#000')};
      out.nullDna = {pale: L.paleEnd(null, '#abcdef'), deep: L.deepEnd(null, '#123456')};
      // a DNA this file cannot measure is not a guess to make — the caller's own literal comes back
      const bad = {bg: 'var(--sky)', fg: '#15181d'} as any;
      out.unmeasurable = {pale: L.paleEnd(bad, '#abcdef'), deep: L.deepEnd(bad, '#123456')};
      // the ends are always the film's OWN two colours — never a hue it did not name
      const ok = (d: any, v: string) => v === d.bg || v === d.fg;
      out.ownColours = ok(dark, out.dark.pale) && ok(dark, out.dark.deep)
                    && ok(light, out.light.pale) && ok(light, out.light.deep);
      // ...and every shipped preset agrees with itself
      out.presets = Object.values(D.DNA_PRESETS ?? {}).map((d: any) =>
        [L.paleEnd(d, '#fff'), L.deepEnd(d, '#000')]);
    """)
    assert out["dark"]["pale"] == "#f2f5fa" and out["dark"]["deep"] == "#0b0d12", out["dark"]
    assert out["light"]["pale"] == "#f6f3ee" and out["light"]["deep"] == "#15181d", \
        "on a light film the pale end is the GROUND, not `fg`: %r" % (out["light"],)
    assert out["nullDna"] == {"pale": "#abcdef", "deep": "#123456"}, \
        "with no DNA the register's own original literal must come back unchanged"
    assert out["ownColours"], "an end came back as a colour the film never declared"
    assert out["unmeasurable"] == {"pale": "#abcdef", "deep": "#123456"}, \
        "a DNA whose ends cannot be measured was guessed at instead of falling back: %r" % (out["unmeasurable"],)
    assert out["presets"], "no presets were read, so this test proves nothing"
    for pale, deep in out["presets"]:
        assert pale != deep, "a preset whose two ends are the same colour has no axis at all"


def test_two_regions_covering_a_light_frame_stay_inside_the_palette():
    """`separatedPair`'s fallback put a hue back as a 12% wash, and on PAPER that is where the palette leaks.

    A film's two accents sit on opposite sides of a light ground by construction — measured on a real one,
    深蓝 #133C9A reads 8.41:1 on #F2EDE3 and 青绿 #00D6B9 reads 1.59:1 — so the normal path cannot separate
    them and EVERY light film lands in the fallback. There a grey lifted toward the ground plus 12% of a hue
    is neither accent: that film's `VersusSplit` beats came back cold grey and sage green, two hues its DNA
    never declares, across the only three non-paper frames it had.

    What this pins is not a rung but the CLAIM: on a light ground both halves stay on a hue the film
    DECLARES — the ground's or an accent's — and neither becomes a neutral.

    THE BOUND WAS ONCE "within 12 deg of the ACCENT", and that was two mistakes in one line. It forbade
    the most in-palette answer there is (a half that is literally the paper, one step back, at the
    ground's own hue), and it EXCUSED the actual defect, because a neutral has no hue to compare and the
    probe's `hue()` returned -1 for it, which `dh` scored as no conflict. So the shipped derivation --
    which walked the near half 8% from a warm ground toward a cold accent and stopped on
    (215,216,218), hue 220 at CHROMA 3 -- passed this test while covering half of a cream frame in a
    grey the DNA never declares. Only looking at the render caught it. The claim below is the one that
    was meant: EVERY declared hue is in the palette, and a neutral on a chromatic ground is a finding,
    not an exemption.
    """
    out = run_probe("""
      const paper = '#F2EDE3', navy = '#133C9A', teal = '#00D6B9';
      const [a, b] = D.separatedPair(paper, navy, teal);
      const hue = (hex: string) => {
        const m = hex.replace('#','');
        const [r, g, bl] = [0,2,4].map((i) => parseInt(m.slice(i,i+2),16)/255);
        const mx = Math.max(r,g,bl), mn = Math.min(r,g,bl), d = mx-mn;
        if (d === 0) return -1;                       // a neutral has no hue to compare
        let h = mx===r ? ((g-bl)/d)%6 : mx===g ? (bl-r)/d+2 : (r-g)/d+4;
        return (((h*60)%360)+360)%360;
      };
      const dh = (x: number, y: number) => {
        if (x < 0 || y < 0) return 0;                 // neutral vs anything: no hue conflict
        const d = Math.abs(x-y); return Math.min(d, 360-d);
      };
      out.halves = [a, b];
      out.hues = [hue(a), hue(b)];
      out.navyHue = hue(navy);
      // Each half is EITHER neutral or ON the film's own hue. The bound is MEASURED, not chosen: the
      // fallback this replaces returned #85a0a1 at 182 deg against the accent's 222 — a 40.4 deg miss, so
      // a "<= 40" test slipped past it by four tenths of a degree. The single-hue ramp returns 222.5 deg,
      // 0.8 off. Anything under ~10 is the same hue; anything near 40 is a hue the film never named.
      // Against EVERY hue the DNA declares, not just the accent: the paper is the film's too.
      const declared = [paper, navy, teal].map(hue).filter((x) => x >= 0);
      const missOf = (c: string) => (hue(c) < 0 ? 999 : Math.min(...declared.map((d) => dh(hue(c), d))));
      out.worstHueMiss = Math.max(...[a, b].map(missOf));
      // A NEUTRAL IS NOT AN EXEMPTION. `chroma` is max-min over 0..255; the ground here is 15 wide, so a
      // half at 3 is grey, and grey is exactly what this test failed to see the first time.
      const chroma = (hex: string) => {
        const m = hex.replace('#','');
        const v = [0,2,4].map((i) => parseInt(m.slice(i,i+2),16));
        return Math.max(...v) - Math.min(...v);
      };
      out.chromas = [a, b].map(chroma);
      out.groundChroma = chroma(paper);
      out.inPalette = out.worstHueMiss <= 12
        && out.chromas.every((c: number) => c >= out.groundChroma * 0.5);
      // ...and they still read as two regions
      out.step = Math.abs(D.pilL(a) - D.pilL(b));
      // the dark path is untouched: on a near-black ground the pair still separates
      const [da, db] = D.separatedPair('#0b0d12', '#5ac8fa', '#ff9f0a');
      out.darkStep = Math.abs(D.pilL(da) - D.pilL(db));
      out.darkPair = [da, db];
    """)
    assert out["inPalette"], (
        "a half of a light film's split frame is outside the declared palette: %r — worst miss %.1f deg "
        "from any declared hue (hues %r), chromas %r against the ground's %d"
        % (out["halves"], out["worstHueMiss"], [round(h) for h in out["hues"]],
           out["chromas"], out["groundChroma"]))
    assert out["step"] >= 0.12, "the two halves no longer read as two regions: %r" % (out["halves"],)
    assert out["darkStep"] >= 0.12, "the dark-ground path regressed: %r" % (out["darkPair"],)


def test_a_plane_cut_from_a_surface_keeps_that_surface_s_hue():
    """`plane` is the "more of the same material, one step back" rule, and the thing it replaces is a mix
    toward the INK. That mix stays inside the palette only while ground and ink share a temperature; a warm
    paper and a cold ink CANCEL, and the result is the one grey mass on a one-hue page. Inscription's
    dressed face shipped that way — measured (213,212,211) off #FBF8F1 and #101A33.

    Measured independently here (colorsys on the returned hex), at both ends and over every preset, so the
    test cannot be satisfied by the code agreeing with itself. The pair asserted is BOTH halves of the
    rule: hue is kept AND the step is real, because a `plane` that returned its input would pass a
    hue check perfectly and draw nothing."""
    r = run_probe("""
      const cases: any = {};
      const pairs: [string, string][] = [
        ['#FBF8F1', '#101A33'],   // warm paper, cold ink — the cancelling pair that produced the defect
        ['#0E1730', '#F2EDE3'],   // the same film's night ground, inks swapped
        ['#00D6B9', '#101A33'],   // a saturated ground
        ['#808080', '#000000'],   // a neutral surface: nothing to keep, and it must still step
      ];
      for (const [s, ink] of pairs) {
        cases[s] = {plane: D.plane(s, 0.16), mixToInk: D.mix(s, ink, 0.16)};
      }
      for (const p of %s) {
        const dna = D.DNA_PRESETS[p];
        cases['preset:' + p] = {surface: dna.surface, plane: D.plane(dna.surface, 0.16),
                                mixToInk: D.mix(dna.surface, dna.fg, 0.16)};
      }
      out.cases = cases;
    """ % json.dumps(PRESETS))
    cases = r["cases"]

    def dh(a, b):                                   # hue distance on the circle
        d = abs(_hue(a) - _hue(b)) % 360
        return min(d, 360 - d)

    cancelled = 0
    for key, c in cases.items():
        src = c.get("surface", key if key.startswith("#") else None)
        assert src, key
        got, step = c["plane"], abs(_Y(c["plane"]) - _Y(src))
        # a neutral source has no hue to keep, but every source must MOVE
        assert step > 0.004, "%s: plane(%s) = %s did not step off its source (dY=%.4f)" % (key, src, got, step)
        # CHROMA IS THE MEASURE HERE, NOT HUE ANGLE. The colour this defect ruins is a near-white paper
        # whose whole cast is 10 units of chroma wide, and at that width the hue ANGLE is rounding noise:
        # the `editorial` preset's #181512 (chroma 6) reads 6 deg off after a one-unit rounding, while
        # staying visibly the same brown. What the eye sees is the cast SURVIVING or not — the mix toward
        # the ink left that paper with 20% of it. So chroma retention is asked of every source, and the
        # hue angle only where there is enough chroma for the angle to mean anything.
        if _chroma(src) >= 4:
            assert _chroma(got) >= _chroma(src) * 0.75, (
                "%s: plane(%s) = %s kept only %.0f%% of the source's chroma" % (
                    key, src, got, 100.0 * _chroma(got) / _chroma(src)))
        if _chroma(src) >= 12:
            assert dh(got, src) <= 4.0, "%s: plane(%s) = %s drifted %.1f deg off its source" % (
                key, src, got, dh(got, src))
        if _chroma(src) >= 4 and _chroma(c["mixToInk"]) < _chroma(src) * 0.6:
            cancelled += 1
    # ...and the probe is only load-bearing if the derivation it replaces really does cancel somewhere.
    assert cancelled >= 1, ("no case in this probe cancels under a mix toward the ink — the test would "
                            "pass against the very code it was written to catch")


def test_two_regions_on_paper_both_stay_the_film_s_own_hues():
    """`separatedPair` covers a frame with TWO regions, and on a light film both must stay in the palette.

    The light branch used to walk BOTH halves toward the accent — a small step first, a larger one after.
    From a WARM ground toward a COLD accent the small step is spent crossing the ground's own hue and
    stops on neutral: measured on a cream/navy film the near half was (215,216,218), hue 220° at CHROMA 3,
    half a frame of a grey the DNA never declares, on a page of hue 40° chroma 15.

    Asserted here on EVERY preset plus the real film's pair, measured independently (colorsys on the
    returned hex), and BOTH halves are checked: the near one must keep the ground's cast, the far one must
    carry the accent's hue, and the two must still separate — a pair that passed the palette by returning
    the ground twice would draw one region, not two."""
    r = run_probe("""
      const out2: any = {};
      const pairs: [string, string, string][] = [
        ['#F2EDE3', '#133C9A', '#00D6B9'],     // the real film: warm paper, cold accents — the failing case
        ['#FBF8F1', '#9c3b1e', '#2e5e4e'],     // warm paper, WARM accent — must not regress
        ['#eef2f8', '#b8412e', '#133C9A'],     // cool paper
      ];
      for (const [g, a, b] of pairs) out2[g] = D.separatedPair(g, a, b);
      for (const p of %s) {
        const dna = D.DNA_PRESETS[p];
        if (D.pilL(dna.bg) > 0.5) out2['preset:' + p] = D.separatedPair(dna.bg, dna.accent, dna.accent2);
      }
      out.pairs = out2;
    """ % json.dumps(PRESETS))

    def dh(a, b):
        d = abs(_hue(a) - _hue(b)) % 360
        return min(d, 360 - d)

    checked = 0
    for key, pair in r["pairs"].items():
        ground = key.split(":", 1)[-1] if key.startswith("preset:") else key
        if key.startswith("preset:"):
            continue                                   # the probe returns only the pair; ground checked below
        near, far = pair
        # the two regions must still be two
        assert abs(_Y(near) - _Y(far)) > 0.02, "%s: the pair collapsed to one region (%s / %s)" % (key, near, far)
        # the NEAR half is the paper, one step back — it keeps the ground's cast
        if _chroma(ground) >= 4:
            assert _chroma(near) >= _chroma(ground) * 0.75, (
                "%s: near half %s kept only %.0f%% of the ground's chroma — it crossed into neutral" % (
                    key, near, 100.0 * _chroma(near) / _chroma(ground)))
        if _chroma(ground) >= 12:
            assert dh(near, ground) <= 6.0, "%s: near half %s drifted %.1f deg off the ground" % (
                key, near, dh(near, ground))
        checked += 1
    assert checked >= 3, "the probe measured only %d light pairs" % checked
