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

_STOP = {"a", "an", "the", "of", "for", "to", "and", "or", "in", "on", "with", "how", "what", "why",
         "is", "are", "it", "its", "about", "that", "this", "into", "as", "at", "by", "from"}


def _kit(topic):
    """Derive a TOPIC content kit from the route string so samples carry the topic, not a register's WorkBuddy demo:
    a short title, a handful of distinct meaningful tokens (for nodes/spokes/names), a slug, and a tagline."""
    import re
    t = (topic or "").strip() or "your topic"          # whitespace-only also falls back to the placeholder
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'.+-]*", t)
    toks = [w for w in words if w.lower() not in _STOP and len(w) > 1]
    caps = [w for w in toks if w[0].isupper()]
    title = (caps[0] if caps else (toks[0] if toks else t))[:22]
    seen, items = set(), []
    for w in toks:
        k = w.lower()
        if k in seen:
            continue
        seen.add(k)
        items.append(w if w[0].isupper() else w.capitalize())
    items = items[:6] or ["Overview", "Signals", "Results"]
    slug = "".join(c if c.isalnum() else "_" for c in title.lower()).strip("_") or "topic"
    return {"title": title, "items": items, "slug": slug, "tag": t.lower()[:44], "up": title.upper()[:22]}


# Per SEED direction: the hero + two representative registers (its family lean). Every register is given its REAL
# content props (nodes/spokes/names/code lines/specs) filled from the topic kit — NOT just a title — so no
# register falls back to its WorkBuddy demo. The sample is about LOOK + MOTION (illustrative copy is fine), but it
# must read as THIS topic, never a leftover demo. A bespoke (non-seed) direction falls back to GENERIC below.
def _sample_shots(key, topic):
    K = _kit(topic)
    title, items, up, tag, slug = K["title"], K["items"], K["up"], K["tag"], K["slug"]
    nodes = items[:5]
    code = ["# %s" % slug, "from %s import model" % slug, "", "answer = model.run(prompt)", "print(answer)"]
    M = {
        "product-demo": [
            ("CommandSummon", {"command": "Build the %s deck" % title, "items": ["Plan it", "Pull the data", "Draft it", "Ship it"]}),
            ("CollaborativeCursors", {"names": items}),
            ("MapRoutes", {"hub": title, "items": nodes}),
        ],
        "kinetic-editorial": [
            ("LiquidChrome", {"word": up, "tagline": tag}),                                  # {word,tagline} — real props
            ("KineticManifesto", {"phrases": [up + ".", (items[0] if items else title).upper() + ".",
                                              (items[1] if len(items) > 1 else "the future").upper() + "."]}),  # {phrases[]}
            ("SwissEditorial", {"items": [up, (items[0] if items else title).upper(), "SHIP"],
                                "wordmark": up, "ticker": tag.upper() + " -- "}),             # {items,wordmark,ticker}
        ],
        "cinematic-craft": [
            ("MaterialHero", {"title": title}),
            ("ParticleForm", {"label": title}),
            ("InkBloom", {"title": title, "tagline": tag}),
        ],
        "data-story": [
            ("KnowledgeGraph", {"hub": title, "items": nodes}),
            ("DataOrrery", {"hub": title, "items": nodes}),
            ("WireGlobe", {"tagline": tag}),
        ],
        "retro-playful": [
            ("NeonGrid", {"title": up, "tagline": tag}),
            ("PixelBuild", {"label": "%s - COMPLETE" % up}),
            ("SplitFlap", {"rows": [up[:10], (items[0] if items else "GO")[:10].upper(), "GO"]}),
        ],
        "terminal-technical": [
            ("CodeCompose", {"filename": slug + ".py", "lines": code, "status": "- shipped"}),
            ("AsciiField", {"message": up}),
            ("BlueprintGrid", {"unit": "%s.core" % slug, "tag": (items[0] if items else "spec"),
                               "spec1": (items[1] if len(items) > 1 else "input"), "spec2": (items[2] if len(items) > 2 else "output"),
                               "metricLabel": "on the models"}),
        ],
    }
    generic = [("CinematicTitle", {"title": title}),
               ("FocalIsolation", {"focalLabel": title}),
               ("ParticleForm", {"label": title})]
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
    # Carry the DIRECTION as `template` so the sample renders through that direction's DESIGN DNA — the user must
    # approve the look they will actually get. Without it every sample rendered DNA-less (each register in its own
    # hardcoded palette), i.e. the contest showed a film that no longer exists once the direction is chosen.
    return {"camera": 0, "template": key, "scenes": scenes}


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
