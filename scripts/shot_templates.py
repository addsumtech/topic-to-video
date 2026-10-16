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
        "keywords_zh": ['产品', '工具', '平台', '应用', '软件', '助手', '智能体', '自动化', '效率', '办公', '工作台', '仪表盘', '流程'],
        "keywords": ["software", "app", "tool", "saas", "product", "platform", "workflow", "dashboard",
                     "api", "automation", "productivity", "assistant", "agent", "cloud", "no-code", "crm"],
    },
    "kinetic-editorial": {
        "pitch": "bold type-forward film — kinetic statements, editorial grids, a chrome/neon wordmark",
        "families": ["C", "H"],
        "hero": "LiquidChrome",
        "keywords_zh": ['宣言', '观点', '主张', '品牌', '发布', '口号', '态度'],
        "keywords": ["brand", "manifesto", "launch", "pitch", "vision", "idea", "announce", "campaign",
                     "fashion", "design", "agency", "statement", "identity", "rebrand", "positioning"],
    },
    "cinematic-craft": {
        "pitch": "atmospheric, tactile film — a real 3D hero, fluid light, hand-made craft textures",
        "families": ["E", "F", "G"],
        "hero": "MaterialHero",
        "keywords_zh": ['工艺', '材质', '手工', '质感', '器物', '匠', '实物', '自然'],
        "keywords": ["story", "consumer", "lifestyle", "food", "travel", "art", "craft", "emotion", "people",
                     "community", "nature", "health", "wellness", "sustainability", "human", "experience"],
    },
    "data-story": {
        "pitch": "evidence-forward film — live charts, a knowledge graph, an orrery of your metrics",
        "families": ["D", "F", "H"],
        "hero": "ChartLive",
        "keywords_zh": ['数据', '指标', '增长', '统计', '图表', '分析', '实验', '结果', '测量'],
        "keywords": ["data", "analytics", "metrics", "research", "report", "study", "finance", "market",
                     "growth", "results", "science", "statistics", "insight", "benchmark", "survey", "trend"],
    },
    "retro-playful": {
        "pitch": "nostalgic, fun film — a pixel build, a neon grid, a split-flap board, cartoon pops",
        "families": ["C", "G", "I"],
        "hero": "NeonGrid",
        "keywords_zh": ['复古', '像素', '怀旧', '游戏', '趣味', '八十年代'],
        "keywords": ["game", "gaming", "fun", "culture", "meme", "kids", "youth", "music", "entertainment",
                     "retro", "nostalgia", "playful", "social", "creator", "arcade", "toy"],
    },
    "terminal-technical": {
        "pitch": "code-native film — a live IDE, a decoding terminal, an exploded schematic",
        "families": ["A", "C", "D"],
        "hero": "CodeCompose",
        "keywords_zh": ['终端', '命令行', '代码', '编译', '日志', '内核', '协议', '系统', '编程'],
        "keywords": ["dev", "developer", "code", "engineering", "infrastructure", "ml", "model", "cli",
                     "terminal", "open source", "protocol", "system", "technical", "security", "database", "llm"],
    },
}
DEFAULT_ORDER = ["product-demo", "kinetic-editorial", "cinematic-craft"]   # a diverse fallback trio
# `remotion still` captures FRAME 0 by default — where an animated shot is un-started (a blank command
# palette, a half-formed wordmark). Every hero DURATION is >=150f, so frame 110 lands in the SETTLED zone
# (reveal complete, exit not begun) for all six — ALWAYS render the contest still with `--frame=CONTEST_FRAME`.
CONTEST_FRAME = 110

# Contest WIDTH by audacity — mirrors the html register-contest (SKILL.md 3.55): the risk budget scales how
# MANY directions diverge. conservative SKIPS the contest; the rest widen. These 6 templates are SEEDS — at
# bold/experimental the shot-director CONCEIVES extra bespoke topic-specific directions to reach the width.
AUDACITY_WIDTH = {"conservative": 0, "balanced": 3, "bold": 5, "experimental": 7}


def contest_width(audacity="balanced"):
    """How many contest directions to offer, by the meta.audacity risk budget."""
    return AUDACITY_WIDTH.get((audacity or "balanced").lower(), 3)


def route(topic, n=None, audacity="balanced"):
    """Return the best template SEEDS for the topic (whole-word keyword hits), padded with a diverse fallback.
    Width = `n` if given, else contest_width(audacity). Only 6 templates exist, so a width >6 returns all 6 —
    the shot-director then CONCEIVES the remaining directions bespoke to the topic (see shot-director.md Step 0)."""
    n = n if n is not None else contest_width(audacity)
    if n <= 0:
        return []
    return matched_seeds(topic)[:n]


def matched_seeds(topic):
    """The seeds this topic ACTUALLY matches, best first. Never padded.

    TWO DEFECTS MET HERE AND PRODUCED A FABRICATED OPTION. The scoring tokenised with `[a-z0-9']+`, which
    finds nothing in a Chinese topic — "WorkBuddy 让 AI 在你的电脑上把活干完" yields `workbuddy` and `ai` and
    that is all — so a CJK film was routed essentially unscored. Then the result was PADDED to the contest
    width from a fixed fallback order. On a film about an AI office agent that put `cinematic-craft` on the
    ballot: a 3D torus knot, offered to the user as a considered direction when it was there because the
    list needed a third row. The viewer's words were 有的还是感觉毫无关联.

    Padding is the worse half. The skill already says the seeds are SEEDS and that the remaining directions
    must be CONCEIVED for the topic; silently filling the gap with whatever came next in a list makes that
    instruction unreachable, because the slot looks filled. So this returns what genuinely matched and
    `conceive_gap()` says how many are still owed."""
    t = (topic or "").lower()
    words = set(re.findall(r"[a-z0-9']+", t))
    scored = []
    for key, tpl in TEMPLATES.items():
        hits = 0
        for kw in tpl["keywords"]:
            if " " in kw:
                hits += 1 if kw in t else 0
            else:
                hits += 1 if kw in words else 0
        # CJK carries no spaces, so a keyword can only be found by SUBSTRING. Without this every Chinese,
        # Japanese and Korean topic scored zero on every template and fell entirely through to the padding.
        for kw in tpl.get("keywords_zh", ()):
            hits += 1 if kw in (topic or "") else 0
        scored.append((hits, key))
    scored.sort(key=lambda x: (-x[0], list(TEMPLATES).index(x[1])))
    return [k for h, k in scored if h > 0]


def conceive_gap(topic, n=None, audacity="balanced"):
    """How many directions the author still owes, beyond what the seed catalogue could match.

    This number is the point of the change: a gap of 2 means two directions must be CONCEIVED for this
    subject, not that two rows of a table are empty."""
    n = n if n is not None else contest_width(audacity)
    return max(0, n - len(matched_seeds(topic)))


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
        # Not ChartLive: a topic string carries no figure and no series, and the register now draws neither
        # without one — the still used to be an invented "128k" over a made-up rising line.
        "data-story": ("WireGlobe", {"tagline": t.lower()[:40]}),
        "retro-playful": ("NeonGrid", {"title": up, "tagline": t.lower()[:40]}),
        "terminal-technical": ("CodeCompose", {"filename": re.sub(r"[^a-z0-9]+", "_", t.lower())[:24] + ".py"}),
    }
    return heroes.get(key, ("CinematicTitle", {"title": t[:40]}))


def main():
    ap = argparse.ArgumentParser(description="Route a topic to remotion shot-template DIRECTIONS for the contest.")
    ap.add_argument("--route", metavar="TOPIC", required=True, help="the film's topic / subject")
    ap.add_argument("-n", type=int, default=None, help="number of candidate directions (default: by --audacity)")
    ap.add_argument("--audacity", default="balanced", choices=["conservative", "balanced", "bold", "experimental"],
                    help="contest width: conservative skips · balanced 3 · bold 5 · experimental 7")
    ap.add_argument("--out", metavar="OUT_DIR", default=None, help="out_dir for the printed still-png paths")
    ap.add_argument("--json", action="store_true", help="emit candidates + contest stills as JSON")
    a = ap.parse_args()
    cands = route(a.route, a.n, a.audacity)
    outdir = a.out or "<out_dir>"
    width = a.n if a.n is not None else contest_width(a.audacity)
    # AN EMPTY CANDIDATE LIST HAS TWO CAUSES, AND THEY ARE OPPOSITE INSTRUCTIONS.
    #
    # This printed "audacity=conservative → contest SKIPPED" for BOTH, so a film whose subject the seed
    # catalogue simply has no keyword for was told its own risk setting had turned the contest off. The
    # author's correct move there is the opposite of skipping: CONCEIVE the directions. `conceive_gap()`
    # already computed exactly that number and nothing called it — the same shape as the seam plan that
    # was complete, tested, documented and unreached. Measured on the film that found this: a real topic
    # at audacity=balanced (width 3, zero seed matches) reported the contest as skipped by a setting the
    # author never chose.
    if width == 0:
        print("[shot_templates] audacity=conservative → contest SKIPPED (pick one direction directly)."); return
    if not cands:
        print("[shot_templates] %d direction(s) asked for at audacity=%s and NO seed template matched %r.\n"
              "                 The contest is NOT skipped — CONCEIVE all %d directions for this subject "
              "(shot-director Step 0),\n                 then render them: "
              "python3 scripts/contest_sample.py --route %s --audacity %s --conceived <file.json> --out %s --render"
              % (width, a.audacity, a.route, conceive_gap(a.route, a.n, a.audacity), json.dumps(a.route,
                 ensure_ascii=False), a.audacity, outdir))
        return
    if width > len(TEMPLATES):
        print("[shot_templates] width %d > %d seed templates — CONCEIVE %d more bespoke topic-directions (Step 0)."
              % (width, len(TEMPLATES), width - len(TEMPLATES)))
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
