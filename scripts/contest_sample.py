#!/usr/bin/env python3
"""contest_sample.py — render a short SAMPLE VIDEO per shot-template DIRECTION for the contest.

A direction is defined by its MOTION and feel; a text pitch (or even one still) can't convey it — the user has to
SEE it move to choose. So instead of one `remotion still` per direction, this builds a tiny mini-storyboard for
each candidate (its HERO register + a couple of representative registers from its family lean, carrying the TOPIC
copy) and renders it through the REAL `Film` composition — real transitions, captions, motion — to
`<out_dir>/_contest_<key>.mp4` (~6s, silent). The user watches the samples and PICKS one (AskUserQuestion); the
pick becomes `meta.shot_template` (see shot-director Step 0 + references/remotion-shot-authoring.md §D).

Usage:
  python scripts/contest_sample.py --route "<topic>" --audacity <a> --out <out_dir>          # print render commands
  python scripts/contest_sample.py --route "<topic>" --audacity <a> --out <out_dir> --render  # also run them
"""
import argparse, json, os, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
import shot_templates as stpl

REMOTION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "remotion"))
FPS = 30
SCENE_F = 75          # ~2.5s per sample scene; 3 scenes + TR overlap ≈ 6.5s total

# Per SEED direction: the hero + two representative registers (its family lean), each mapped to TEXT-friendly
# props so the sample carries the TOPIC without dragging in a register's number/demo-copy defaults (the sample is
# about LOOK + MOTION, not faithfulness). A bespoke (non-seed) direction falls back to GENERIC below.
def _sample_shots(key, topic):
    t = (topic or "your topic").strip()
    up = t.upper()[:22]
    low = t.lower()[:40]
    M = {
        "product-demo": [
            ("CommandSummon", {"command": "Build the %s" % t[:36], "items": ["Plan it", "Pull the data", "Draft it", "Ship it"]}),
            ("CollaborativeCursors", {"title": t[:36]}),
            ("MapRoutes", {"tagline": low}),
        ],
        "kinetic-editorial": [
            ("LiquidChrome", {"word": up, "tagline": low}),
            ("KineticManifesto", {"word": up, "tagline": low}),
            ("SwissEditorial", {"word": up}),
        ],
        "cinematic-craft": [
            ("MaterialHero", {"title": t[:36]}),
            ("ParticleForm", {"label": t[:28]}),
            ("InkBloom", {"title": t[:28], "tagline": low}),
        ],
        "data-story": [
            ("KnowledgeGraph", {"title": t[:36]}),
            ("DataOrrery", {"title": t[:36]}),
            ("WireGlobe", {"tagline": low}),
        ],
        "retro-playful": [
            ("NeonGrid", {"title": up, "tagline": low}),
            ("PixelBuild", {"label": t[:24]}),
            ("SplitFlap", {"rows": [up[:10], low[:10].upper(), "GO"]}),
        ],
        "terminal-technical": [
            ("CodeCompose", {"filename": "".join(c if c.isalnum() else "_" for c in t.lower())[:22] + ".py"}),
            ("AsciiField", {"message": up}),
            ("BlueprintGrid", {"title": t[:36]}),
        ],
    }
    generic = [("CinematicTitle", {"title": t[:36]}),
               ("FocalIsolation", {"focalLabel": t[:24]}),
               ("ParticleForm", {"label": t[:24]})]
    return M.get(key, generic)


def build_props(key, topic):
    """A Film props dict for this direction's sample: 3 scenes, camera locked, a short caption per scene."""
    shots = _sample_shots(key, topic)
    pitch = stpl.TEMPLATES.get(key, {}).get("pitch", "a bespoke direction")
    caps = ["%s — %s" % (topic, key.replace("-", " ")), pitch[:70], "one film, this look"]
    scenes = [{"shot": sid, "props": props, "durF": SCENE_F, "caption": caps[i % len(caps)]}
              for i, (sid, props) in enumerate(shots)]
    # mark the 2nd seam so the sample also shows a marked transition (the direction's motion character)
    if len(scenes) > 1:
        scenes[1]["transitionIn"] = {"type": "dissolve"}
    return {"camera": 0, "scenes": scenes}


def main():
    ap = argparse.ArgumentParser(description="Render a short sample video per shot-template direction.")
    ap.add_argument("--route", metavar="TOPIC", required=True)
    ap.add_argument("-n", type=int, default=None)
    ap.add_argument("--audacity", default="balanced", choices=["conservative", "balanced", "bold", "experimental"])
    ap.add_argument("--out", metavar="OUT_DIR", required=True)
    ap.add_argument("--render", action="store_true", help="actually run the renders (else just print the commands)")
    a = ap.parse_args()
    cands = stpl.route(a.route, a.n, a.audacity)
    if not cands:
        print("[contest_sample] audacity=conservative → contest SKIPPED (pick one direction directly)."); return
    out_dir = os.path.abspath(a.out)
    os.makedirs(out_dir, exist_ok=True)
    total_f = max(1, len(_sample_shots(cands[0], a.route)) * SCENE_F)
    print("[contest_sample] %d direction sample(s) for %r → _contest_<key>.mp4 (~%.1fs each):"
          % (len(cands), a.route, total_f / FPS))
    made = []
    for k in cands:
        props = build_props(k, a.route)
        pjson = os.path.join(out_dir, "_contest_%s.props.json" % k)
        with open(pjson, "w") as f:
            json.dump(props, f, ensure_ascii=False)
        mp4 = os.path.join(out_dir, "_contest_%s.mp4" % k)
        nframes = sum(s["durF"] for s in props["scenes"]) - (len(props["scenes"]) - 1) * 12
        cmd = ["npx", "remotion", "render", "src/index.ts", "Film", mp4,
               "--props=" + pjson, "--public-dir=" + out_dir, "--frames=0-%d" % (nframes - 1),
               "--gl=" + (os.environ.get("REMOTION_GL") or "angle"), "--log=error"]
        shots = " · ".join(s["shot"] for s in props["scenes"])
        print("  %-20s [%s]" % (k, shots))
        if a.render:
            try:
                subprocess.run(cmd, cwd=REMOTION_DIR, check=True)
                made.append(mp4)
            except subprocess.CalledProcessError as e:
                print("    render FAILED (%s) — try without --gl, or render this direction's still instead" % e)
        else:
            print("    cd remotion && " + " ".join(cmd))
    if a.render:
        print("[contest_sample] wrote %d sample(s): %s" % (len(made), ", ".join(os.path.basename(m) for m in made)))
        print("  → montage / present via AskUserQuestion; the user PICKS the direction (winner first).")


if __name__ == "__main__":
    main()
