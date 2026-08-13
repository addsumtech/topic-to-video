#!/usr/bin/env python3
"""shot_templates — whole-film AESTHETIC DIRECTIONS for the remotion bespoke-shot tier, and a topic router.

The remotion analogue of the HTML register-contest (SKILL.md 3.55): rather than a uniform look, a "template"
is a coherent DIRECTION that biases which register FAMILIES the film leans on (each beat is still its own
design language — the template EMPHASIZES families, it does not make the film monotone). `route(topic)` returns
the best ~3 templates so the user PICKS one (via AskUserQuestion) from a rendered representative still each;
the pick becomes `meta.shot_template`, which `shot_director.assign_shots(..., template=…)` applies. See LIBRARY.md
for the families (A Product-UI · B Camera/space · C Kinetic type & title · D Data/technical · E 3D ·
F Fluid/generative · G Illustrated/craft · H Comparison · I Mechanical/physical).
"""
import argparse, json, re

TEMPLATES = {
    "product-demo": {
        "pitch": "clean SaaS product film — UI in motion, data that draws, a camera over your workspace",
        "families": ["A", "D", "B"],
        "hero": "CommandSummon",
        "keywords": ["software", "app", "tool", "saas", "product", "platform", "workflow", "dashboard",
                     "api", "automation", "productivity", "assistant", "agent", "cloud", "no-code", "crm"],
    },
    "kinetic-editorial": {
        "pitch": "bold type-forward film — kinetic statements, editorial grids, a chrome/neon wordmark",
        "families": ["C", "H"],
        "hero": "LiquidChrome",
        "keywords": ["brand", "manifesto", "launch", "pitch", "vision", "idea", "announce", "campaign",
                     "fashion", "design", "agency", "statement", "identity", "rebrand", "positioning"],
    },
    "cinematic-craft": {
        "pitch": "atmospheric, tactile film — a real 3D hero, fluid light, hand-made craft textures",
        "families": ["E", "F", "G"],
        "hero": "MaterialHero",
        "keywords": ["story", "consumer", "lifestyle", "food", "travel", "art", "craft", "emotion", "people",
                     "community", "nature", "health", "wellness", "sustainability", "human", "experience"],
    },
    "data-story": {
        "pitch": "evidence-forward film — live charts, a knowledge graph, an orrery of your metrics",
        "families": ["D", "F", "H"],
        "hero": "ChartLive",
        "keywords": ["data", "analytics", "metrics", "research", "report", "study", "finance", "market",
                     "growth", "results", "science", "statistics", "insight", "benchmark", "survey", "trend"],
    },
    "retro-playful": {
        "pitch": "nostalgic, fun film — a pixel build, a neon grid, a split-flap board, cartoon pops",
        "families": ["C", "G", "I"],
        "hero": "NeonGrid",
        "keywords": ["game", "gaming", "fun", "culture", "meme", "kids", "youth", "music", "entertainment",
                     "retro", "nostalgia", "playful", "social", "creator", "arcade", "toy"],
    },
    "terminal-technical": {
        "pitch": "code-native film — a live IDE, a decoding terminal, an exploded schematic",
        "families": ["A", "C", "D"],
        "hero": "CodeCompose",
        "keywords": ["dev", "developer", "code", "engineering", "infrastructure", "ml", "model", "cli",
                     "terminal", "open source", "protocol", "system", "technical", "security", "database", "llm"],
    },
}
DEFAULT_ORDER = ["product-demo", "kinetic-editorial", "cinematic-craft"]   # a diverse fallback trio
# `remotion still` captures FRAME 0 by default — where an animated shot is un-started (a blank command
# palette, a half-formed wordmark). Every hero DURATION is >=150f, so frame 110 lands in the SETTLED zone
# (reveal complete, exit not begun) for all six — ALWAYS render the contest still with `--frame=CONTEST_FRAME`.
CONTEST_FRAME = 110


def route(topic, n=3):
    """Return the best `n` template keys for the topic (whole-word keyword hits), padded with a diverse
    fallback so there are always `n` distinct candidates for the contest."""
    words = set(re.findall(r"[a-z0-9']+", (topic or "").lower()))
    scored = []
    for key, t in TEMPLATES.items():
        hits = sum(1 for kw in t["keywords"] if (" " in kw and kw in (topic or "").lower()) or kw in words)
        scored.append((hits, key))
    scored.sort(key=lambda x: (-x[0], list(TEMPLATES).index(x[1])))
    out = [k for h, k in scored if h > 0][:n]
    for k in DEFAULT_ORDER + list(TEMPLATES):     # pad to n with distinct fallbacks
        if len(out) >= n:
            break
        if k not in out:
            out.append(k)
    return out[:n]


def contest_still(key, topic):
    """A (register_id, props) to render as this template's representative CONTEST still — the template's HERO
    register carrying the TOPIC, so the user compares real, topic-bearing frames (never abstract defaults)."""
    t = (topic or "your topic").strip()
    up = t.upper()[:22]
    heroes = {
        "product-demo": ("CommandSummon", {"command": "Build the %s" % t[:40],
                                           "items": ["Plan it", "Pull the data", "Draft the deck", "Ship it"]}),
        "kinetic-editorial": ("LiquidChrome", {"word": up, "tagline": t.lower()[:40]}),
        "cinematic-craft": ("MaterialHero", {"title": t[:40]}),
        "data-story": ("ChartLive", {"label": t.lower()[:40]}),
        "retro-playful": ("NeonGrid", {"title": up, "tagline": t.lower()[:40]}),
        "terminal-technical": ("CodeCompose", {"filename": re.sub(r"[^a-z0-9]+", "_", t.lower())[:24] + ".py"}),
    }
    return heroes.get(key, ("CinematicTitle", {"title": t[:40]}))


def main():
    ap = argparse.ArgumentParser(description="Route a topic to remotion shot-template DIRECTIONS for the contest.")
    ap.add_argument("--route", metavar="TOPIC", required=True, help="the film's topic / subject")
    ap.add_argument("-n", type=int, default=3, help="number of candidate directions (default 3)")
    ap.add_argument("--out", metavar="OUT_DIR", default=None, help="out_dir for the printed still-png paths")
    ap.add_argument("--json", action="store_true", help="emit candidates + contest stills as JSON")
    a = ap.parse_args()
    cands = route(a.route, a.n)
    outdir = a.out or "<out_dir>"
    if a.json:
        out = []
        for k in cands:
            hero, props = contest_still(k, a.route)
            out.append({"key": k, "pitch": TEMPLATES[k]["pitch"], "families": TEMPLATES[k]["families"],
                        "hero": hero, "props": props, "frame": CONTEST_FRAME,
                        "still_png": "%s/_contest_%s.png" % (outdir, k)})
        print(json.dumps(out, ensure_ascii=False, indent=2)); return
    print("[shot_templates] %d directions for %r — render each still, montage, let the USER pick:" % (len(cands), a.route))
    for k in cands:
        hero, props = contest_still(k, a.route)
        print("  %-18s %s  (families %s)" % (k, TEMPLATES[k]["pitch"], TEMPLATES[k]["families"]))
        print("    cd remotion && npx remotion still src/index.ts %s %s/_contest_%s.png --frame=%d --props='%s'"
              % (hero, outdir, k, CONTEST_FRAME, json.dumps(props, ensure_ascii=False)))


if __name__ == "__main__":
    main()
