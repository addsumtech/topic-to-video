"""Optics (runtime/optics.tsx), lit material grounds (runtime/material.tsx) and the determinism harness that holds them.

What is pinned, and why each is load-bearing:
  * the VOCABULARY is one list, read by validate.py out of optics.tsx itself, so the two cannot disagree;
  * a register that OFFERS an optic actually ANCHORS it (calls the hook, mounts the primitive) — an `OPTICS` export
    with no anchor would pass validate.py and draw nothing;
  * validate.py refuses every board the runtime would throw on (unknown kind, intensity past its cap, an optic the
    register cannot anchor, a leak with no seam, an optic on a stage-run beat, two disagreeing declarations);
  * render_remotion lifts `shot_props.optic` out of the register's props into the beat;
  * RENDERED: every optic and material is deterministic by scripts/determinism_qa.py's floor, the harness catches a
    real state leak and names its layer (the positive control, E7), each optic DRAWS (off != on), `optic: 'none'` is
    the frame with no optic, and the material span the register picks its ink from is what the pixels measure.
The rendering tests bundle once and render stills on the film's own GL backend; run them under the render lock.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import validate as v                    # noqa: E402

_SHOTS = os.path.join(_REM, "src", "shots")
_ANCHOR = {"bloom": ("OpticSource", "GlowCopy"), "halation": ("OpticSource", "GlowCopy"), "sweep": ("LightSweep",),
           "aberration": ("Aberration",)}


def _offering():
    out = {}
    for f in sorted(os.listdir(_SHOTS)):
        if f.endswith(".tsx"):
            o = v.register_optics(f[:-4])
            if o:
                out[f[:-4]] = o
    return out


# ── the vocabulary and the registers that offer it ─────────────────────────────────────────────────────────────
def test_the_vocabulary_is_read_from_the_runtime():
    kinds, caps = v.optic_vocabulary()
    assert kinds == ["bloom", "halation", "sweep", "aberration", "leak"]
    # the research's measured ceilings (references/craft-research.md, fx_research): bloom <= 0.3, halation <= 0.15,
    # chromatic aberration 1-2 px
    assert caps["bloom"] <= 0.3 and caps["halation"] <= 0.15 and caps["aberration"] <= 2


def anchor_problems(shot, src, kinds):
    """Why a register that offers `kinds` does not anchor them, [] when it does."""
    out = []
    if "useBeatOptic(OPTICS)" not in src:
        out.append("%s exports OPTICS but never asks for the beat's optic" % shot)
    if "leak" in kinds:
        out.append("%s offers 'leak', which the Film draws — a register cannot anchor it" % shot)
    for k in kinds:
        if k in _ANCHOR and not any("<%s" % a in src for a in _ANCHOR[k]):
            out.append("%s offers %r and mounts no %s" % (shot, k, "/".join(_ANCHOR[k])))
    return out


def test_every_register_that_offers_an_optic_anchors_it():
    offering = _offering()
    assert set(offering) >= {"StarfieldWarp", "SpotlightStage", "EmberFlame", "DeviceHero"}, offering
    for shot, kinds in offering.items():
        src = open(os.path.join(_SHOTS, shot + ".tsx"), encoding="utf-8").read()
        assert anchor_problems(shot, src, kinds) == []


def test_the_anchor_check_fails_on_an_offer_with_no_anchor():
    """E7 — the check above, mutated: StarfieldWarp offering 'sweep' (which it never mounts) must be reported, and so
    must a register that drops its hook call."""
    src = open(os.path.join(_SHOTS, "StarfieldWarp.tsx"), encoding="utf-8").read()
    assert any("mounts no LightSweep" in m for m in anchor_problems("StarfieldWarp", src, ("bloom", "sweep")))
    unhooked = src.replace("useBeatOptic(OPTICS)", "null")
    assert unhooked != src and anchor_problems("StarfieldWarp", unhooked, ("bloom",))


# ── the validator ──────────────────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("slide,shot,prev,want", [
    ({"optic": "bloom"}, "StarfieldWarp", None, None),
    ({"optic": "none"}, "TermTable", None, None),
    ({}, "TermTable", None, None),
    ({"optic": {"kind": "aberration", "intensity": 2}}, "StarfieldWarp", None, None),
    ({"optic": "glow"}, "StarfieldWarp", None, "not one of"),
    ({"optic": {"kind": "bloom", "intensity": 0.5}}, "StarfieldWarp", None, "intensity must be in"),
    ({"optic": {"kind": "bloom", "intensity": True}}, "StarfieldWarp", None, "intensity must be in"),
    ({"optic": {"kind": "bloom", "amount": 0.2}}, "StarfieldWarp", None, "unknown key"),
    ({"optic": "sweep"}, "StarfieldWarp", None, "cannot anchor"),
    ({"optic": "bloom"}, "TermTable", None, "cannot anchor"),
    ({"optic": "leak"}, "TermTable", None, "first beat"),
    ({"optic": "leak"}, "TermTable", {"shot": "TermTable"}, None),
    ({"optic": "leak", "stage": {"run": "r"}}, "CardStage", {"stage": {"run": "r"}}, "continues stage run"),
    ({"optic": "bloom", "stage": {"run": "r"}}, "CardStage", {"stage": {"run": "q"}}, "stage-run beat"),
    ({"optic": "bloom", "shot_props": {"optic": "aberration"}}, "StarfieldWarp", None, "one beat, one optic"),
    ({"shot_props": {"optic": "sweep"}}, "DeviceHero", None, None),
])
def test_the_validator_refuses_what_the_runtime_would_throw_on(slide, shot, prev, want):
    got = v.optic_problems(slide, shot, prev)
    if want is None:
        assert got == [], got
    else:
        assert got and any(want in m for m in got), got


def test_render_remotion_lifts_the_optic_out_of_the_props(tmp_path):
    import render_remotion as rr
    (tmp_path / "audio").mkdir()
    (tmp_path / "audio" / "01.mp3").write_bytes(b"")
    (tmp_path / "audio" / "02.mp3").write_bytes(b"")
    slides = [{"index": 1, "shot": "StarfieldWarp", "duration": 3, "audio": "audio/01.mp3", "narration": "一",
               "optic": "bloom", "shot_props": {"title": "A"}},
              {"index": 2, "shot": "SpotlightStage", "duration": 3, "audio": "audio/02.mp3", "narration": "二",
               "shot_props": {"optic": "halation", "wordmark": "K"}}]
    scenes = rr.build_scenes(slides, str(tmp_path), {"StarfieldWarp", "SpotlightStage"})
    assert scenes[0]["optic"] == "bloom" and "optic" not in scenes[0]["props"]
    assert scenes[1]["optic"] == "halation" and scenes[1]["props"] == {"wordmark": "K"}, scenes[1]
    slides[1]["optic"] = "bloom"                          # two disagreeing declarations on one beat
    with pytest.raises(RuntimeError, match="one beat, one optic"):
        rr.build_scenes(slides, str(tmp_path), {"StarfieldWarp", "SpotlightStage"})


# ── rendered ───────────────────────────────────────────────────────────────────────────────────────────────────
needs_toolchain = pytest.mark.skipif(
    not (shutil.which("npx") and os.path.isdir(os.path.join(_REM, "node_modules"))),
    reason="needs the remotion toolchain")


@pytest.fixture(scope="module")
def serve():
    work = tempfile.mkdtemp(prefix="optics_test_")
    b = os.path.join(work, "bundle")
    subprocess.run(["npx", "remotion", "bundle", "src/index.ts", "--out-dir=" + b, "--log=error"], cwd=_REM,
                   check=True, capture_output=True)
    yield work, b
    shutil.rmtree(work, ignore_errors=True)


def _still(serve, comp, frame, props, name):
    work, b = serve
    pf = os.path.join(work, name + ".json")
    with open(pf, "w", encoding="utf-8") as fh:
        json.dump(props, fh)
    out = os.path.join(work, name + ".png")
    r = subprocess.run(["npx", "remotion", "still", b, comp, out, "--frame=%d" % frame, "--gl=angle",
                        "--image-format=png", "--props=" + pf, "--log=error"], cwd=_REM, capture_output=True, text=True)
    assert r.returncode == 0, (r.stdout + r.stderr)[-800:]
    return out


def _arr(p):
    np = pytest.importorskip("numpy")
    from PIL import Image
    return np.asarray(Image.open(p).convert("RGB")).astype(float)


@needs_toolchain
def test_every_optic_and_material_is_deterministic():
    """Twice, concurrency 1 vs 3, and frame N cold vs after M..N-1 — over frames where the sweep and the leak are
    both in flight (the probe's SWEEP_START / SEAM_START are 30)."""
    import determinism_qa as dq
    rep = dq.run("OpticsProbe", {}, 30, 35, scale=0.5)
    bad = [x for x in rep["results"] if x["fail"]]
    assert rep["ok"], bad
    assert len(rep["results"]) == 6 + 6 + 1


@needs_toolchain
def test_the_harness_catches_a_state_leak_and_names_the_layer():
    """The positive control: a module-level counter makes a frame depend on how many frames its tab drew first. The
    harness must FAIL it — cold vs warm at least — and attribute it to the layer whose removal makes it agree."""
    import determinism_qa as dq
    rep = dq.run("OpticsProbe", {"stateLeak": True}, 30, 33, scale=0.5,
                 layers=[("optics", {"layers": {"bloom": False, "halation": False, "sweep": False,
                                                "aberration": False, "leak": False}}),
                         ("stateLeak", {"stateLeak": False})])
    assert not rep["ok"]
    failed = {x["test"] for x in rep["results"] if x["fail"]}
    assert "cold" in failed, rep["results"]
    assert all(rep["blame"][t] == "stateLeak" for t in failed), rep["blame"]


@needs_toolchain
def test_each_optic_draws_and_none_draws_nothing(serve):
    """A layer that renders nothing passes a determinism check trivially, so each one must change the frame — and
    `optic: 'none'` must be byte-identical to declaring no optic at all."""
    np = pytest.importorskip("numpy")
    on = _arr(_still(serve, "OpticsProbe", 36, {}, "probe_on"))
    for layer in ("bloom", "halation", "sweep", "aberration", "leak", "material"):
        off = _arr(_still(serve, "OpticsProbe", 36, {"layers": {layer: False}}, "probe_off_" + layer))
        changed = float((np.abs(on - off).max(axis=2) > 2).mean())
        assert changed > 0.0005, "%s changed only %.5f of the frame — it draws nothing" % (layer, changed)
    a = _still(serve, "StarfieldWarp", 100, {"dna": "product"}, "star_absent")
    b = _still(serve, "StarfieldWarp", 100, {"dna": "product", "optic": "none"}, "star_none")
    assert open(a, "rb").read() == open(b, "rb").read()


def _span_from_source():
    src = open(os.path.join(_REM, "src", "runtime", "material.tsx"), encoding="utf-8").read()
    body = src[src.index("export const MATERIAL_SPAN"):]
    body = body[:body.index("};")]
    out = {}
    for m, mul0, mul1, add0, add1 in re.findall(
            r"(\w+): \{mul: \[([\d.]+), ([\d.]+)\], add: \[([\d.]+), ([\d.]+)\]\}", body):
        out[m] = ((float(mul0), float(mul1)), (float(add0), float(add1)))
    assert set(out) == {"paper", "water", "metal", "clay"}, out
    return out


@needs_toolchain
def test_the_material_span_the_ink_is_picked_from_is_what_the_pixels_measure(serve):
    """LitMedium picks its ink against MATERIAL_SPAN. Re-measured here over its type column on its own light path, at
    the start and end of the drift, at both aspects: the rendered 2nd/98th percentiles must sit inside it."""
    np = pytest.importorskip("numpy")
    span = _span_from_source()
    box = {"16:9": (0.09, 0.71, 0.18, 0.82), "9:16": (0.08, 0.92, 0.22, 0.78)}
    travel = {"16:9": [0.66, 0.96], "9:16": [0.3, 0.7]}
    for m, ((mul0, mul1), (add0, add1)) in span.items():
        for aspect in ("16:9", "9:16"):
            x0, x1, y0, y1 = box[aspect]
            for base, what in (("#808080", "mul"), ("#000000", "add")):
                vals = []
                for fr in (0, 89):
                    a = _arr(_still(serve, "OpticsProbe", fr, {"aspect": aspect, "materialFull": {
                        "material": m, "base": base, "travel": travel[aspect]}}, "span_%s_%s_%s_%d" % (
                            m, aspect.replace(":", "x"), what, fr))) / 255
                    H, W = a.shape[:2]
                    vals.append(a[int(y0 * H):int(y1 * H), int(x0 * W):int(x1 * W), 1].ravel())
                vals = np.concatenate(vals)
                lo, hi = np.percentile(vals, 2), np.percentile(vals, 98)
                if what == "mul":
                    lo, hi = lo / (128 / 255), hi / (128 / 255)
                    if add1 > 0:          # a specular medium: the gray base carries its highlight too; skip mul
                        continue
                    assert mul0 - 0.02 <= lo and hi <= mul1 + 0.02, (m, aspect, lo, hi, (mul0, mul1))
                else:
                    assert lo >= add0 - 0.02 and hi <= add1 + 0.02, (m, aspect, lo, hi, (add0, add1))


# ── contrast where the type sits ───────────────────────────────────────────────────────────────────────────────
def type_contrast(with_copy, other_copy, test):
    """(contrast in `with_copy`, contrast in `test`) of the TYPE against its local ground — the type found as the
    pixels two renders with different copy disagree on, the ink as those of them farther from the ground than the
    ground's own spread, the ground as the unchanged pixels inside the type's bounding box."""
    np = pytest.importorskip("numpy")
    A, B, T = with_copy, other_copy, test

    def lum(x):
        c = x / 255
        c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
        return c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722
    LA, LB, LT = lum(A), lum(B), lum(T)
    d = np.abs(A - B).max(axis=2) > 12
    ys, xs = np.nonzero(d)
    assert len(ys), "the two copies rendered identically — no type was found to measure"
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    box = (slice(y0, y1), slice(x0, x1))
    ground = ~d[box]
    gA, gT = np.median(LA[box][ground]), np.median(LT[box][ground])
    ink_mask = d[box] & (np.abs(LA[box] - gA) > np.abs(LB[box] - gA))   # where A's own glyphs are
    iA, iT = np.median(LA[box][ink_mask]), np.median(LT[box][ink_mask])
    c = lambda a, b: (max(a, b) + 0.05) / (min(a, b) + 0.05)
    return c(iA, gA), c(iT, gT)


_TYPE_CASES = [
    ("StarfieldWarp", 140, {"title": "Lightspeed", "tagline": "the next era, now"},
     {"title": "Orbit far", "tagline": "into the far dark"}, ("bloom", "aberration")),
    ("SpotlightStage", 165, {"items": ["PLAN", "BUILD", "SHIP"], "wordmark": "WORKBUDDY"},
     {"items": ["MAKE", "TEST", "SEND"], "wordmark": "NORTHWIND"}, ("bloom", "halation")),
    ("EmberFlame", 140, {"title": "Ignite", "tagline": "built with fire"},
     {"title": "Forged", "tagline": "made in the heat"}, ("bloom", "halation")),
    ("DeviceHero", 130, {"kicker": "THE PRODUCT"}, {"kicker": "ONE SCREEN"}, ("bloom",)),
]


@needs_toolchain
@pytest.mark.parametrize("shot,frame,copy_a,copy_b,optics", _TYPE_CASES)
def test_an_optic_leaves_the_type_s_contrast_where_it_was(serve, shot, frame, copy_a, copy_b, optics):
    """`text contrast must be unchanged where type sits`: measured on the settled frame, with and without each optic
    the register offers, at 16:9 and 9:16. The floor is 95% of the contrast the type had without the optic."""
    for aspect in ("16:9", "9:16"):
        base = {"dna": "product", "aspect": aspect}
        tag = "%s_%s" % (shot, aspect.replace(":", "x"))
        A = _arr(_still(serve, shot, frame, dict(base, **copy_a), tag + "_a"))
        B = _arr(_still(serve, shot, frame, dict(base, **copy_b), tag + "_b"))
        for o in optics:
            T = _arr(_still(serve, shot, frame, dict(base, optic=o, **copy_a), tag + "_" + o))
            c0, c1 = type_contrast(A, B, T)
            print("CONTRAST %s %s %s: %.2f -> %.2f (%.1f%%)" % (shot, aspect, o, c0, c1, 100 * c1 / c0))
            assert c1 >= 0.95 * c0, "%s %s %s: the type's contrast fell from %.2f to %.2f" % (shot, aspect, o, c0, c1)
