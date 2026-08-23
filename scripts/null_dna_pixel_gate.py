#!/usr/bin/env python3
"""null_dna_pixel_gate — prove a change did not alter what an UN-THEMED film renders.

Layer C's whole safety argument is that `var(--f-body, <original list>)` with the variable unset
resolves to the original list. That is a claim about real CSS in a real browser, so it is checked by
hashing real renders - not by asserting that a variable is present.

THIS IS A ONE-SHOT MIGRATION-VERIFICATION INSTRUMENT, NOT A STANDING CI GATE. No baseline is
committed to this repo (the default store path is under /tmp, which is ephemeral and machine-local —
hashes are exact SHA-256 digests of PNG bytes, sensitive to the render host's GL driver/font
rasterizer, so a store saved on one machine should not be `--check`ed on another). There is nothing
for `--check` to compare against unless YOU ran `--save` yourself, in this same environment, against
the tree from before whatever change you are verifying. To use it around a change:

  python3 scripts/null_dna_pixel_gate.py --save   /tmp/before.json   # on the pre-change tree
  # ... make your change ...
  python3 scripts/null_dna_pixel_gate.py --check  /tmp/before.json   # on the post-change tree

Any differing shot is printed with its two hashes and the gate exits 1.
"""
import hashlib, json, os, subprocess, sys, tempfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REMOTION = os.path.join(_HERE, "..", "remotion")

# A stratified sample: the largest type, the smallest type, mono-heavy, mixed, and the shots that
# already read the DNA directly (which the codemod must have left alone). Also includes three of the
# 17 shots migrated via the SVG `fontFamily="..."` presentation-attribute rewrite (Task 9 scope (c))
# — the riskiest rewrite class in this task, added so the identity proof actually covers it.
SHOTS = ["EdStat", "TermCounter", "ChartLive", "VelocitySnap", "TermBars", "KnowledgeGraph",
         "CinematicTitle", "SwissEditorial", "MaterialHero", "BlueprintGrid", "ChatThread",
         "CodeCompose", "TermTable", "TermDiff", "AnswerStream", "TimelineTravel", "MapRoutes",
         "ExplodedSchematic", "NeonGrid", "ComicPanels",
         "SpinningProton", "KSpaceReal", "MRIPipeline",
         # Task 9 fix round: BlueprintGrid (already above) and CompressedSensingEq both hid a
         # hardcoded font family behind a module-level const (MONO / SERIF) that the codemod
         # misclassified as already-dynamic. CompressedSensingEq was missing from this sample
         # entirely — added so the identity proof actually covers the fix. RisoPrint hid the same
         # pattern behind a local `const font` (a full shorthand, not just a family list) that the
         # codemod's `font:`-anchored scan couldn't even see as a candidate — found by the fix-round
         # sweep the review asked for, not named in the original findings.
         "CompressedSensingEq", "RisoPrint",
         # Important-2 fix sites: LiquidChrome's `fontCss` and PositioningMatrix's hero/label font
         # were hardcoded families parked under `unrecognized-font-decl` — added to the sample so the
         # identity proof covers them too, not just the Critical-1 const-indirection sites.
         "LiquidChrome", "PositioningMatrix"]


def _hash_shot(shot, td):
    png = os.path.join(td, shot + ".png")
    r = subprocess.run(["npx", "remotion", "still", "src/index.ts", shot, png,
                        "--frame=100", "--gl=angle"],
                       cwd=_REMOTION, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit("render failed for %s\n%s" % (shot, r.stderr[-1500:]))
    return hashlib.sha256(open(png, "rb").read()).hexdigest()


def main(argv):
    mode = argv[0] if argv else "--check"
    store = argv[1] if len(argv) > 1 else "/tmp/null-dna-hashes.json"
    with tempfile.TemporaryDirectory() as td:
        now = {s: _hash_shot(s, td) for s in SHOTS}
    if mode == "--save":
        json.dump(now, open(store, "w"), indent=1)
        print("saved %d hashes to %s" % (len(now), store))
        return 0
    before = json.load(open(store))
    bad = [s for s in SHOTS if before.get(s) != now[s]]
    for s in bad:
        print("CHANGED %s\n  before %s\n  after  %s" % (s, before.get(s), now[s]))
    if bad:
        print("\nnull-DNA pixel gate FAILED on %d/%d shots" % (len(bad), len(SHOTS)))
        return 1
    print("null-DNA pixel gate: all %d shots render identically" % len(SHOTS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
