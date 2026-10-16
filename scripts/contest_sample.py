#!/usr/bin/env python3
"""contest_sample.py — render a short SAMPLE VIDEO per shot-template DIRECTION for the contest.

A direction is defined by its MOTION and feel; a text pitch (or even one still) can't convey it — the user has to
SEE it move to choose. So instead of one `remotion still` per direction, this builds a tiny mini-storyboard for
each candidate (its HERO register + a couple of representative registers from its family lean, carrying the TOPIC
copy) and renders it through the REAL `Film` composition — real transitions, captions, motion — to
`<out_dir>/_contest_<key>.mp4` (~6s, silent). The user watches the samples and PICKS one (AskUserQuestion); the
pick becomes `meta.shot_template` (see shot-director Step 0 + references/remotion-shot-authoring.md §D).

Usage:
  python scripts/contest_sample.py --route "<topic>" --audacity <a> --out <out_dir> --conceived <file.json> --render

A DIRECTION IS DESIGNED, NOT PICKED FROM THE CATALOGUE. This used to sample "its HERO register + a couple of
representative registers", so every direction a user was shown was the library's — on a film about how GPS works,
a split-flap departure board, a map plate and a HUD reticle, in a signal red nobody could connect to satellites.
The user's verdict: three existing templates, none of them suited to the subject. The per-beat design-first rules
(shot-director Step 0.55) came AFTER this choice, so the direction that sets the whole film's look was the one
decision still made from templates. A conceived direction now carries, and is refused without:
  ideal           the film's SIGNATURE picture in this direction — one line, no register named
  palette_source  [{colour, from}] — every colour traced to something in the SUBJECT's own world (the orbit's night
                  sky, a satellite's gold foil), never to a mood
  shots           [[ShotId, {props}], ...] whose FIRST (the hero) is BUILT in this film's workshop
                  (`workshop.py <out_dir> new-shot`); library registers may follow it, adapted, as supporting frames
It renders with the film's workshop in the bundle, and writes `_contest_<key>.png`, the hero settled at 90% of its
slot, beside the video. A catalogue SEED is material for a direction, and is no longer rendered as one.
"""
import argparse, glob, json, os, re, subprocess, sys

sys.path.insert(0, os.path.dirname(__file__))
import shot_templates as stpl
import workshop as _ws

REMOTION_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "remotion"))
FPS = 30
SCENE_F = 75          # ~2.5s per sample scene; 3 scenes + TR overlap ≈ 6.5s total

_STOP = {"a", "an", "the", "of", "for", "to", "and", "or", "in", "on", "with", "how", "what", "why",
         "is", "are", "it", "its", "about", "that", "this", "into", "as", "at", "by", "from"}


# CJK function words that carry no subject on their own. A topic phrase made only of these is not a topic.
_CJK_FUNCTION = set("的了是在和与把被为对从到就都也还很更最之其而或即如若则也吗呢吧啊让使给向于以及但由并且个只有些这那什么怎么为什么")


def _cap_run(run, cjk):
    """A content run, length-capped — but a LATIN word is never cut. The 8-character cap is a CJK measure
    (about the width of a readable node label); applied to `WorkBuddy` it produced `WorkBudd`, a fragment
    that is not the product's name and not a word."""
    run = run.strip()
    if len(run) < 2:
        return None
    return run[:8] if cjk.search(run) else run[:22]


def _cjk_content(seg):
    """The CONTENT characters of a CJK segment — what is left once function words are removed."""
    return [c for c in seg if c not in _CJK_FUNCTION and not c.isspace()]


def _kit(topic):
    """Derive a TOPIC content kit from the route string so samples carry the topic, not a register's WorkBuddy demo:
    a short title, a handful of distinct meaningful tokens (for nodes/spokes/names), a slug, and a tagline."""
    import re
    t = (topic or "").strip() or "your topic"          # whitespace-only also falls back to the placeholder
    # CJK-AWARE. The ASCII-only tokenizer below is structurally blind to Chinese/Japanese/Korean: on
    # "AI 编程助手为什么容易写出看起来对的代码" its only match is "AI", every other character is discarded,
    # and `items` then fell through to the hardcoded English placeholders — so every contest sample for a
    # CJK film silently carried a meaningless one-token wordmark plus "Overview / Signals / Results", while
    # the script exited 0 and the diversity gate happily scored the result. Segment CJK on its own
    # punctuation (：，。；、！？ and spaces), which is where a well-formed Chinese topic already breaks.
    words = re.findall(r"[A-Za-z0-9][A-Za-z0-9'.+-]*", t)
    toks = [w for w in words if w.lower() not in _STOP and len(w) > 1]
    caps = [w for w in toks if w[0].isupper()]
    cjk = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af]")
    phrases = []
    if cjk.search(t):
        # Segment on PUNCTUATION, not whitespace. In a mixed topic the spaces separate SCRIPTS, not
        # clauses — "WorkBuddy 让 AI 在你的电脑上把活干完" split on whitespace yields the standalone
        # fragment "让", which is a grammatical particle and was then shorter than every real phrase, so
        # it won the `len <= 8` filter and became the film's wordmark. Three contest samples went out
        # showing a giant chrome 「让」, `Build the 让 deck`, and a 3D hero labelled 「让」 — the user would
        # have been comparing three directions on one meaningless character, and every gate was green.
        for seg in re.split(r"[：:，,。.；;、！!？?]+", t):
            seg = seg.strip()
            if seg and cjk.search(seg) and seg not in phrases:
                phrases.append(seg)
        # CJK has no stop-word list here the way Latin does, so a function word could be picked as a
        # topic token. These carry no subject on their own; a phrase that is ONLY these is dropped.
        phrases = [p for p in phrases if len(_cjk_content(p)) >= 2]
    if phrases:                                        # CJK topic: phrases ARE the words
        # NEVER build a token by TRUNCATION. Cutting a long phrase to 8 characters produced `WorkBudd`
        # and `AI 编程助手为` — fragments that are not words in any language, printed as a film's nodes and
        # spokes. When no phrase is short enough, split it at its FUNCTION WORDS, which is where Chinese
        # actually breaks (的/了/是/在/把/让…), and keep the content runs. "在你的电脑上把活干完" becomes
        # 电脑上 · 活干完 rather than a mid-word slice.
        short = [p for p in phrases if len(p) <= 8]
        if not short:
            for ph in phrases:
                run = ""
                for ch in ph:
                    if ch in _CJK_FUNCTION or ch.isspace():
                        cand = _cap_run(run, cjk)
                        if cand and cand not in short:
                            short.append(cand)
                        run = ""
                    else:
                        run += ch
                cand = _cap_run(run, cjk)
                if cand and cand not in short:
                    short.append(cand)
        if not short:                                  # a phrase of nothing but function words
            short = [p[:8] for p in phrases]
        # A capitalised LATIN name in a mixed topic IS the wordmark — it is the product's own name, and
        # the CJK branch used to discard every Latin token, so "WorkBuddy 让 AI …" lost "WorkBuddy".
        title = (caps[0][:22] if caps else short[0][:12])
        items, seen = [], set()
        for cand in short:                              # content runs only — no truncated fragments
            if cand and cand not in seen:
                seen.add(cand); items.append(cand)
        items = items[:6]
        up = title                                     # .upper() is a no-op on CJK; keep the phrase
        if caps and caps[0] not in items:              # the product's own name leads the token list too
            items = [caps[0]] + [i for i in items if i != caps[0]]
            items = items[:6]
    else:
        title = (caps[0] if caps else (toks[0] if toks else t))[:22]
        seen, items = set(), []
        for w in toks:
            k = w.lower()
            if k in seen:
                continue
            seen.add(k)
            items.append(w if w[0].isupper() else w.capitalize())
        items = items[:6]
        up = title.upper()[:22]
    if not items:
        # FAIL LOUDLY. Substituting English placeholders here is what made the CJK breakage invisible:
        # the samples rendered, the gate scored them, and nothing said the topic never arrived.
        raise SystemExit("[contest_sample] could not derive any topic tokens from route %r — "
                         "the samples would carry placeholder copy instead of your topic" % topic)
    slug = "".join(c if c.isalnum() else "_" for c in title.lower()).strip("_") or "topic"
    return {"title": title, "items": items, "slug": slug, "tag": t[:44], "up": up}


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
            ("DataOrrery", {"hub": title, "items": nodes[:4]}),   # four orbits; it refuses a fifth
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
               # the field is the topic's own tokens and the isolated one is named; given only a label it
               # printed its demo file names and spotlit the demo's own pick. A topic that yields one token (a
               # CJK phrase has no spaces to split on) has no field to isolate from, so it gets a register
               # that needs none rather than the same word twice.
               (("FocalIsolation", {"focalLabel": title, "items": list(dict.fromkeys(items))[:9], "focal": 0})
                if len(set(items)) >= 2 else ("WireGlobe", {"tagline": tag})),
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


def library_shots():
    """The library's register ids (remotion/src/shots/*.tsx)."""
    return {os.path.basename(f)[:-4] for f in glob.glob(os.path.join(REMOTION_DIR, "src", "shots", "*.tsx"))}


def direction_problems(spec, out_dir, library=None):
    """[problem] for a conceived direction that is not designed first — no ideal, no palette provenance, or a hero
    that is not BUILT in this film's workshop. [] means it may be rendered and put to the user."""
    lib = library_shots() if library is None else library
    key, probs = spec.get("key", "?"), []
    ideal = str(spec.get("ideal") or "").strip()
    if len(ideal) < 8:
        probs.append("%s: no `ideal` — write the film's signature picture in this direction, one line, before any "
                     "shot is chosen" % key)
    else:
        named = sorted(r for r in lib if re.search(r"\b%s\b" % re.escape(r), ideal))
        if named:
            probs.append("%s: the ideal names a library register (%s) — the ideal is the picture the idea needs, "
                         "written before any register is in view" % (key, ", ".join(named)))
    src = spec.get("palette_source")
    rows = [r for r in src if isinstance(r, dict) and str(r.get("colour") or r.get("color") or "").strip()
            and len(str(r.get("from") or "").strip()) >= 4] if isinstance(src, list) else []
    if not rows:
        probs.append("%s: no `palette_source` — [{colour, from}] tracing each colour to something in the SUBJECT's "
                     "own world; a palette chosen for a mood is how a film about satellites got signal red" % key)
    shots = spec.get("shots") or []
    hero = shots[0][0] if shots and isinstance(shots[0], (list, tuple)) and shots[0] else None
    built = set(_ws.shot_names(out_dir)) if out_dir else set()
    if hero is None:
        probs.append("%s: no shots" % key)
    elif hero not in built:
        probs.append("%s: the hero %r is %s — the hero is BUILT in this film's workshop "
                     "(python3 scripts/workshop.py <out_dir> new-shot <Name> --means \"…\"); a library register "
                     "may only follow it, adapted, as a supporting frame"
                     % (key, hero, "a library register" if hero in lib else "not a shot in this film's workshop"))
    return probs


def build_props_conceived(spec, topic):
    """A Film props dict for a direction the AUTHOR conceived, rendered through the same path as a seed.

    Without this, conceiving a direction had no way to reach the screen, so the catalogue's fallback padding
    was the path of least resistance — and that is exactly how an off-topic option got onto the ballot.
    `dna` is EITHER a preset name OR a full DesignDNA object, and it is routed the way `render_remotion.py`
    routes `meta.design_dna` — an object to the Film's `dna` prop, a name to `template`. It used to go to
    `template` unconditionally, and a conceived DNA is an OBJECT: the Film's `dnaFromTemplate()` cannot
    resolve one, so it fell through to the default look and EVERY conceived direction rendered identically.
    The contest then asked a user to choose between three looks none of which had been applied — which is
    worse than no contest, because the ballot looks real. Measured on a three-direction Chinese film: a
    direction declaring `bg: #F2EDE3` (paper, Y=0.850) rendered near-black, and its props file carried no
    `dna` key at all. `shots` is the [ShotId, props] list, i.e. the direction stated as frames.

    The seam goes the same way: `spec["seam"]` is `{type, direction}` in a real film's DNA, and passing that
    object where a `{"type": ...}` was expected made the marked seam silently anonymous.
    """
    shots = [(s[0], s[1]) for s in (spec.get("shots") or [])]
    if not shots:
        raise SystemExit("[contest_sample] conceived direction %r has no `shots` — a direction that cannot be "
                         "rendered is a pitch, and the whole point of the contest is that the user SEES it."
                         % spec.get("key"))
    pitch = spec.get("pitch") or "a conceived direction"
    # the user's own language only: the key and an English tagline used to be burned into a Chinese film's samples
    caps = [pitch[:70], topic[:70]]
    scenes = [{"shot": sid, "props": props, "durF": SCENE_F, "caption": caps[i % len(caps)]}
              for i, (sid, props) in enumerate(shots)]
    seam = spec.get("seam") or {"type": "dissolve"}
    if isinstance(seam, str):
        seam = {"type": seam}
    if len(scenes) > 1:
        scenes[1]["transitionIn"] = dict(seam)
    props = {"camera": 0, "scenes": scenes}
    dna = spec.get("dna")
    if isinstance(dna, dict):
        props["dna"] = dna                      # the conceived look itself — the Film coerces a partial one
    else:
        props["template"] = (dna or "neutral") if isinstance(dna, str) else "neutral"
    return props


def main():
    ap = argparse.ArgumentParser(description="Render a short sample video per shot-template direction.")
    ap.add_argument("--route", metavar="TOPIC", required=True)
    ap.add_argument("-n", type=int, default=None)
    ap.add_argument("--audacity", default="balanced", choices=["conservative", "balanced", "bold", "experimental"])
    ap.add_argument("--out", metavar="OUT_DIR", required=True)
    ap.add_argument("--render", action="store_true", help="actually run the renders (else just print the commands)")
    ap.add_argument("--conceived", metavar="FILE", default=None,
                    help="JSON list of the directions YOU designed for this subject: "
                         "[{key, pitch, ideal, palette_source:[{colour, from}], dna, seam, "
                         "shots:[[BuiltHero, {props}], [ShotId, {props}], ...]}] — the hero BUILT in this film's "
                         "workshop. A catalogue seed is material for a direction, never one.")
    a = ap.parse_args()
    width = a.n if a.n is not None else stpl.contest_width(a.audacity)
    if width <= 0:
        print("[contest_sample] audacity=conservative → contest SKIPPED (pick one direction directly)."); return
    seeds = stpl.matched_seeds(a.route)[:width]
    conceived = []
    if a.conceived:
        conceived = json.load(open(a.conceived, encoding="utf-8"))
        if isinstance(conceived, dict):
            conceived = [conceived]
    out_dir = os.path.abspath(a.out)
    os.makedirs(out_dir, exist_ok=True)

    # THE GAP IS THE POINT, and it used to be invisible. route() padded the shortfall from a fixed fallback
    # order, so a film about an AI office agent was offered `cinematic-craft` — a 3D torus knot — as a
    # considered direction when it was there because the list needed a third row. A slot that looks filled
    # makes the skill's own instruction ("the six templates are SEEDS; CONCEIVE the rest for this topic")
    # unreachable. So the shortfall is stated instead of filled.
    gap = max(0, width - len(seeds) - len(conceived))
    if gap:
        print("[contest_sample] ⚠️  %d of %d directions are NOT covered. The seed catalogue matched %d for "
              "%r%s.\n    Those slots are yours to CONCEIVE for this subject — a direction is an ATMOSPHERE "
              "(a named look + the register families it leans on + a hero), not a row in a table. Write them "
              "as JSON and pass --conceived; padding the ballot with whatever came next in a list is what "
              "produced options a viewer called 毫无关联."
              % (gap, width, len(seeds), a.route, "" if seeds else " (nothing keyed to this topic)"))
    if not seeds and not conceived:
        return

    if seeds:
        print("[contest_sample] seed(s) matched: %s — MATERIAL for a direction (its families, its motion), not a "
              "direction: a seed's sample is the library's registers, which is what a user called three existing "
              "templates, none suited to the subject. Design the direction and BUILD its hero."
              % ", ".join(seeds))
    lib = library_shots()
    bad = []
    for i, c in enumerate(conceived, 1):
        bad += direction_problems(dict(c, key=c.get("key", "conceived-%d" % i)), out_dir, lib)
    if bad:
        print("[contest_sample] REFUSED — a direction is designed first, and these are not:")
        for b in bad:
            print("    ✗ " + b)
        sys.exit(2)
    cands = [(c.get("key", "conceived-%d" % i), c) for i, c in enumerate(conceived, 1)]
    if not cands:
        print("[contest_sample] no designed direction to render — pass --conceived <file.json>")
        sys.exit(2)
    env = _ws.run_kwargs(out_dir)             # the film's workshop in the bundle: the heroes are built there
    first = build_props_conceived(cands[0][1], a.route)
    total_f = sum(sc["durF"] for sc in first["scenes"]) - (len(first["scenes"]) - 1) * 12
    print("[contest_sample] %d direction sample(s) for %r → _contest_<key>.mp4 (~%.1fs each) + _contest_<key>.png:"
          % (len(cands), a.route, total_f / FPS))
    made = []
    for k, spec in cands:
        props = build_props_conceived(spec, a.route)
        pjson = os.path.join(out_dir, "_contest_%s.props.json" % k)
        with open(pjson, "w") as f:
            json.dump(props, f, ensure_ascii=False)
        mp4 = os.path.join(out_dir, "_contest_%s.mp4" % k)
        nframes = sum(s["durF"] for s in props["scenes"]) - (len(props["scenes"]) - 1) * 12
        cmd = ["npx", "remotion", "render", "src/index.ts", "Film", mp4,
               "--props=" + pjson, "--public-dir=" + out_dir, "--frames=0-%d" % (nframes - 1),
               "--gl=" + (os.environ.get("REMOTION_GL") or "angle"), "--log=error"]
        # THE STILL is the hero settled — 90% of its slot in this same sample — for the diversity gate and the judge.
        # It used to be a separate `remotion still` at frame 110 that nothing printed for a conceived direction, and
        # "110 = settled" held only for the six seed heroes.
        png = os.path.join(out_dir, "_contest_%s.png" % k)
        still = ["npx", "remotion", "still", "src/index.ts", "Film", png, "--props=" + pjson,
                 "--public-dir=" + out_dir, "--frame=%d" % int(SCENE_F * 0.9),
                 "--gl=" + (os.environ.get("REMOTION_GL") or "angle"), "--log=error"]
        shots = " · ".join(s["shot"] for s in props["scenes"])
        print("  %-20s [%s]" % (k, shots))
        if a.render:
            try:
                subprocess.run(cmd, cwd=REMOTION_DIR, check=True, **env)
                subprocess.run(still, cwd=REMOTION_DIR, check=True, **env)
                made.append(mp4)
            except subprocess.CalledProcessError as e:
                print("    render FAILED (%s) — try without --gl" % e)
        else:
            print("    cd remotion && " + " ".join(cmd))
            print("    cd remotion && " + " ".join(still))
    if a.render:
        print("[contest_sample] wrote %d sample(s): %s" % (len(made), ", ".join(os.path.basename(m) for m in made)))
        print("  → montage / present via AskUserQuestion; the user PICKS the direction (winner first).")


if __name__ == "__main__":
    main()
