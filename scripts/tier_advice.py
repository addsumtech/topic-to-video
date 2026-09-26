#!/usr/bin/env python3
"""WHICH TIER, FOR WHAT — recommend a renderer from what the video is FOR and what it is ABOUT.

    python3 scripts/tier_advice.py --purpose teach [--deck] [--keep-deck] [--data-dense yes|no]
    python3 scripts/tier_advice.py --check <out_dir>        # does the chosen tier fight the stated purpose?

WHY THIS EXISTS. The tier question used to be asked as a choice between three LOOKS, and the purpose question
right beside it only set the narrative arc — so nothing connected "what is this video for" to "which renderer
makes it". The skill's own text disagreed with itself about the default besides: the tool list called the
cinematic tier "RECOMMENDED" while the interview menu defaulted to designed HTML.

The tiers are not three looks. They are three different trade-offs, and every one of them is measured:

  slides   the user's OWN slide images, full-frame, gentle Ken Burns, a voice. `type:"slide"` in the board —
           no page is authored, no Chrome is needed (ffmpeg alone). Nothing is redesigned, so nothing drifts
           from the deck the user already approved. The fastest tier by construction.

  html     one authored page per beat, rendered by headless Chrome. Two capabilities the cinematic tier does
           not have: a multi-point page MUST bind each point to the word that names it (`data-cue`, fired on
           the edge-tts word timings), so a point appears as it is SPOKEN — 0 of the 185 cinematic registers
           read word timings; they animate on their own clock. And a one-beat edit re-renders one beat: the
           per-slide clip cache, plus a whole-film `--preview`. Any table, chart, code block or equation is
           laid out as the content needs rather than fitted to a register's capacity.

  remotion the bespoke-shot library — 185 hand-designed shot languages, luminance-safe seams, a carry
           match-cut, a design DNA for the whole film. The strongest register for launch, promo and story.
           It renders PER BEAT and keeps the beats an edit did not touch (remotion_segments.py): a VISUAL edit
           re-renders that beat and the next, but a NARRATION edit changes a beat's length and so re-renders
           every later one (the film's atmosphere pulses on the absolute frame). Before that cache it rendered
           the whole film in one pass, and on a 37-beat film that pass failed repeatedly at ~1 GB free, so a
           one-beat fix the user asked for never reached the delivered film. It still needs Node, its own
           Chrome and real memory.

So the recommendation follows the PURPOSE first and the TOPIC second, and it is ADVICE: it names the tier,
why, and what you give up — the user still chooses, and `--check` says so once if the choice fights the
purpose rather than silently overriding it.
"""
import argparse
import json
import os
import re
import sys

TIERS = ("slides", "html", "remotion")

# The interview's ① Purpose menu, with the spellings an agent or a user will actually write.
_PURPOSE_ALIASES = {
    "teach": ("teach", "explain", "explainer", "tutorial-concept", "讲解", "教学", "解释", "科普"),
    "howto": ("howto", "how-to", "walkthrough", "tutorial", "demo", "操作演示", "教程", "操作", "演示"),
    "research": ("research", "briefing", "research briefing", "report", "研究", "研究简报", "汇报", "论文"),
    "overview": ("overview", "intro", "introduction", "概览", "介绍", "简介", "总览"),
    "pitch": ("pitch", "persuade", "proposal", "说服", "路演", "提案"),
    "launch": ("launch", "announcement", "announce", "release", "发布", "发布会", "上线", "公告"),
    "promo": ("promo", "hype", "promotion", "ad", "trailer", "宣传", "推广", "广告", "预告"),
}

# What each purpose is FOR, and therefore which capability decides it. Kept as data so a test can walk it.
PURPOSE_TIER = {
    "teach": "html",       # a point appears as it is spoken; the content decides the layout
    "howto": "html",       # step N appears on "step N"; a wrong step is a one-beat re-render
    "research": "html",    # tables, figures, equations laid out as the content needs; cheap corrections
    "launch": "remotion",  # the register library, seams and DNA exist for exactly this
    "promo": "remotion",
    "pitch": None,         # decided by the TOPIC: evidence-heavy -> html, story/brand -> remotion
    "overview": None,
}


def canonical_purpose(raw):
    """The canonical purpose key for whatever the interview recorded, or None."""
    s = str(raw or "").strip().lower()
    if not s:
        return None
    for key, names in _PURPOSE_ALIASES.items():
        if s == key or any(s == n.lower() for n in names):
            return key
    # A LABEL WITH EXTRA WORDS — "Teach / explain", "Launch/announcement" — resolves only when every alias it
    # contains points at ONE purpose. "product demo launch" contains a how-to alias and a launch alias, and
    # letting list order decide would silently answer a question the user did not answer; an ambiguous
    # purpose returns None, and the recommendation then says the purpose is unknown.
    hits = {key for key, names in _PURPOSE_ALIASES.items() if any(n.lower() in s for n in names if len(n) > 2)}
    return hits.pop() if len(hits) == 1 else None


def data_density(texts):
    """True when the material is evidence-heavy — numbers, tables, code, equations — else False.

    Measured, not guessed: the share of text units that carry a figure, plus structural markers. It answers
    one question only (does the layout need to follow the content?), and returns None on too little text to
    say, so a caller never gets a confident answer from three words.
    """
    units = [t for t in (str(x or "").strip() for x in (texts or [])) if t]
    if len(units) < 3:
        return None
    figure = sum(1 for t in units if re.search(r"\d", t))
    structure = sum(1 for t in units if re.search(r"(\|.*\|)|(```)|(\$[^$]+\$)|(\\frac|\\sum|=\s*\d)", t))
    return (figure / float(len(units)) >= 0.5) or structure >= 2


def recommend(purpose, has_deck=False, keep_deck=False, data_dense=None, remotion_ok=True, chrome_ok=True,
              lang="zh"):
    """{tier, why, trade, runner_up, basis} — the recommended tier and the honest reason for it."""
    p = canonical_purpose(purpose)
    zh = str(lang or "").lower().startswith("zh")

    def out(tier, why_zh, why_en, trade_zh, trade_en, runner, basis):
        return {"tier": tier, "why": why_zh if zh else why_en, "trade": trade_zh if zh else trade_en,
                "runner_up": runner, "basis": basis}

    # 1. A finished deck the user wants voiced as it is. Nothing to redesign, nothing to install.
    if has_deck and keep_deck:
        return out("slides",
                   "你要的是给现有的 deck 配音：用你自己的页面，不重新设计，只要 ffmpeg，最快。",
                   "You want your existing deck voiced: your own slides, nothing redesigned, ffmpeg only, fastest.",
                   "页面不会随口播逐条出现，也没有新的视觉设计。",
                   "Points do not appear as they are spoken, and nothing is newly designed.",
                   "html", "keep-deck")

    # 2. No Chrome: the page tiers cannot render. Slides (if there is a deck) or the programmatic safety net.
    if not chrome_ok:
        if has_deck:
            return out("slides", "这台机器没有 Chrome，页面分支渲染不了；有 deck 就用你自己的页面。",
                       "No Chrome on this machine, so the page tiers cannot render; with a deck, use your slides.",
                       "装上 Chrome 后可以改用设计过的 html 页面。",
                       "Install Chrome to get designed html pages instead.", None, "no-chrome")
        return out("html", "这台机器没有 Chrome：会自动退到简单的程序化画面（安全网，不是推荐的外观）。",
                   "No Chrome: rendering falls back to plain programmatic scenes (a safety net, not a look).",
                   "装上 Chrome 才有设计过的页面。", "Install Chrome for designed pages.", None, "no-chrome")

    tier = PURPOSE_TIER.get(p) if p else None
    basis = "purpose:%s" % p if p else "purpose:unknown"
    if tier is None and p in ("pitch", "overview"):
        if data_dense is True:
            tier, basis = "html", basis + "+data-dense"
        elif data_dense is False:
            tier, basis = "remotion", basis + "+story"
        else:
            tier, basis = "html", basis + "+topic-unassessed"
    if tier is None:
        tier, basis = "html", basis                         # unknown purpose: the cheap-to-correct default

    if tier == "remotion" and not remotion_ok:
        return out("html", "这个目的最适合电影感分支，但这台机器没装 remotion；html 能做，只是少了镜头语言库。",
                   "This purpose suits the cinematic tier, but remotion is not installed here; html can do it "
                   "without the shot-language library.",
                   "没有 185 种镜头语言和电影化接缝。", "No shot-language library, no cinematic seams.",
                   None, basis + "+remotion-missing")

    if tier == "html":
        return out("html",
                   "讲解类视频最要紧的是：每个要点在被说到的那一刻出现（html 逐条绑定口播），数据按内容排版；"
                   "改一拍只重渲那一拍。",
                   "An explainer lives on each point appearing the moment it is said (html binds points to the "
                   "spoken word), with data laid out as the content needs; editing one beat re-renders one beat.",
                   "少了电影感的镜头语言和接缝。", "Less cinematic motion and fewer designed seams.",
                   "remotion" if remotion_ok else "slides", basis)
    return out("remotion",
               "发布、宣传和讲故事靠的是镜头语言和节奏：185 种设计好的镜头、电影化接缝、统一的品牌 DNA。",
               "Launch, promo and story run on shot language and pace: 185 designed shots, cinematic seams, one "
               "brand DNA across the film.",
               "要点不会随口播逐条出现；改一拍的画面只重渲这一拍和下一拍，但改口播会让它后面的拍全部重渲；"
               "也更吃内存和时间。",
               "Points do not appear as they are spoken; a visual edit re-renders that beat and the next, but a "
               "narration edit re-renders every later beat; it needs more memory and time.",
               "html", basis)


def chosen_tier(board):
    """The tier a storyboard will actually render with."""
    meta = board.get("meta") or {}
    if str(meta.get("renderer", "")).strip().lower() == "remotion":
        return "remotion"
    slides = board.get("slides") or []
    if slides and all(str(s.get("type", "slide")) == "slide" for s in slides):
        return "slides"
    return "html"


def mismatch(board):
    """A one-time note when the chosen tier fights the stated purpose, else None. Advice, never a block."""
    meta = board.get("meta") or {}
    p = canonical_purpose(meta.get("purpose"))
    if not p:
        return None
    want = PURPOSE_TIER.get(p)
    got = chosen_tier(board)
    if want is None or got == want:
        return None
    lang = str(meta.get("language") or "zh")
    zh = lang.lower().startswith("zh")
    if want == "html" and got == "remotion":
        return ("目的是「%s」，却选了电影感分支：要点不会随口播逐条出现，改口播会让它后面的拍全部重渲。"
                "这是可以的选择——只是要知道代价。" % p) if zh else (
                "Purpose is %r but the cinematic tier is chosen: points will not appear as they are spoken, and a "
                "narration edit re-renders every later beat. A legitimate choice — just a known cost." % p)
    if want == "remotion" and got in ("html", "slides"):
        return ("目的是「%s」，却选了%s：少了镜头语言库和电影化接缝，发布/宣传的节奏感会弱一些。"
                % (p, "原样配音" if got == "slides" else "html")) if zh else (
                "Purpose is %r but %s is chosen: no shot-language library or cinematic seams, so launch/promo pace "
                "will be flatter." % (p, got))
    return None


def main(argv):
    ap = argparse.ArgumentParser(description="Recommend a renderer tier from purpose and topic.")
    ap.add_argument("--purpose")
    ap.add_argument("--deck", action="store_true", help="the user supplied a deck")
    ap.add_argument("--keep-deck", action="store_true", help="the user wants the deck voiced as it is")
    ap.add_argument("--data-dense", choices=("yes", "no"))
    ap.add_argument("--no-remotion", action="store_true")
    ap.add_argument("--no-chrome", action="store_true")
    ap.add_argument("--lang", default="zh")
    ap.add_argument("--check", metavar="OUT_DIR")
    a = ap.parse_args(argv)
    if a.check:
        board = json.load(open(os.path.join(a.check, "storyboard.json"), encoding="utf-8"))
        note = mismatch(board)
        print("[tier_advice] chosen tier: %s" % chosen_tier(board))
        print("  note : " + note if note else "  ok   : the chosen tier fits the stated purpose (or none was recorded)")
        return 0
    if not a.purpose and not a.keep_deck:
        ap.error("--purpose is required (or --deck --keep-deck)")
    dd = None if a.data_dense is None else a.data_dense == "yes"
    r = recommend(a.purpose, has_deck=a.deck, keep_deck=a.keep_deck, data_dense=dd,
                  remotion_ok=not a.no_remotion, chrome_ok=not a.no_chrome, lang=a.lang)
    print(json.dumps(r, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
