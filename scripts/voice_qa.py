#!/usr/bin/env python3
"""VOICE QA — does the narration sound like a person, or like a machine imitating one?

Run:  python3 scripts/voice_qa.py <out_dir> [--json]

Two families of tell, because they fail differently:

(A) VOCABULARY tells — the well-known Chinese/English AI-slop registers (随着…的不断发展 / 赋能 /
    值得一提的是 / "delve" / "it's not just X, it's Y"). These are what every de-AI checklist lists.

(B) RHYTHM tells — the ones every checklist MISSES. A delivered 37-beat film scored ZERO on the whole
    (A) list and still read as machine-written, because the machine signature had moved: every beat was
    2-3 clipped subject-less declaratives of near-identical length, joined by nothing, and ending on an
    antithesis ("绿灯量的是测试有多强。不是代码有多对。"). Read once it is punchy; read 37 times in a
    row it is a template. Human explanatory speech varies its sentence length, carries connectives, and
    lets most sentences simply deliver information instead of landing an aphorism.

    So this script measures the DISTRIBUTION, not just the words:
      - sentence-length CV (spread / mean). Machine-uniform prose sits low; a person's varies.
      - antithesis density: the share of beats built on the rhetorical FIGURE — two comparable things set
        against each other, one negated. Ordinary negation ("that package does not exist") is not the
        figure and is filtered out by requiring the two sides to be parallel in length.
      - balanced-pair share: two or three clauses of near-equal length set against each other, which is
        the same move with no negation word in it and therefore invisible to every vocabulary list.
      - connective density: the share of beats carrying any 但/所以/其实 · but/so/actually … at all.
      - aphorism ending: the share of beats whose LAST sentence lands the figure.

    EVERYTHING BRANCHES ON SCRIPT, PER BEAT — never on one language flag for the whole film. What the
    metrics actually need to know is what ends a sentence, whether words are space-delimited, and whether
    a curated connective/antithesis list exists at all. Where one does not (kana, Hangul, Cyrillic today)
    those two checks report UNAVAILABLE. They do NOT report 0%: a zero would be a claim about the writing
    when it is a gap in this tool.

HONEST LIMIT, and it matters: rules remove maybe half of it. Published practice reports 40-50%, and
over-applying rules produces its own artificiality — a "rule voice" that dodges every listed pattern and
still is not a person. Treat every number here as a place to LOOK, not a target to optimise. A beat that
trips a check and reads well is fine; a beat that passes everything and reads dead is still dead.
This script is ADVISORY and always exits 0.

WHAT IS STILL NOT CALIBRATED: none of the five thresholds has been measured against a corpus of
human-written narration. They are anchored to ONE case — a delivered film its author found
machine-sounding — and to nothing else. The Latin figures are weaker still, because characters and words
are not the same unit. Every threshold is a named constant in THRESHOLDS so a test can probe both sides
of each boundary; that makes them load-bearing, not correct.
"""
import json
import os
import re
import statistics
import sys

# ── (A) vocabulary tells ─────────────────────────────────────────────────────────────────────────────
ZH_TELLS = {
    "时代背景开场": r"随着.{0,8}的?不断发展|在.{0,10}的大背景下|在这个.{0,6}的时代",
    "空转枢纽": r"需要注意的是|值得一提的是|值得思考的是|归根结底|说到底|核心在于|从本质上讲",
    "机械排比": r"首先.{0,60}其次|第一.{0,60}第二.{0,60}第三",
    "装饰性短语": r"通过.{1,10}的方式|在.{1,10}的情况下|由于.{1,8}的原因|在一定程度上|从某种意义上",
    "商务黑话": r"赋能|助力|打造|护航|抓手|闭环|底层逻辑|全方位|多维度",
    "弱动词": r"进行(讨论|分析|优化|处理)|开展(工作|研究)|实现.{0,4}突破",
    "破折号密度": r"——",
}
EN_TELLS = {
    "delve-register": r"\b(delve|tapestry|realm|landscape of|navigate the|underscore[sd]?|testament to)\b",
    "not-just-but": r"\bnot (just|only) [^.,;]{2,40}(,| but)\b",
    "empty-pivot": r"\b(it'?s worth noting|it is important to note|at the end of the day|ultimately,)",
    "triad-parallel": r"\bfirst,[^.]{0,80}second,[^.]{0,80}(third|finally),",
    "hedge-stack": r"\b(in a sense|to some extent|in many ways|arguably)\b",
}
# Half-width punctuation sitting between CJK characters — a translation/rendering residue.
MIXED_PUNCT = r"[一-鿿]\s*[,.;:?!]\s*[一-鿿]"

# ── (B) rhythm tells — driven by SCRIPT, not by a whole-film language flag ────────────────────────────
# The first version decided ONE language for a whole film from a Han-character ratio, then branched two
# ways. Three things were wrong with that and none of them announced itself:
#   * Chinese technical narration is full of Latin and digits ("pass@k 最多掉了 19.3 到 28.9%"), so the
#     ratio can fall under the threshold and route a Chinese film to the English rules.
#   * The test was the CJK IDEOGRAPH range only, so kana-heavy Japanese, Hangul Korean, Cyrillic — every
#     script that is not Han-dense — went to the English branch, where the connective list cannot match
#     and the report announced "0% of beats carry any connective" as if it were a finding.
#   * One flag for the film meant a mixed script was measured with the wrong splitter AND the wrong unit.
# What the metrics actually branch on is not "which language" but three script properties: what ends a
# sentence, whether words are space-delimited, and whether we HAVE a curated connective/antithesis list.
# So: classify each BEAT by script, and carry those properties in a profile. Where no curated list exists
# the check reports UNAVAILABLE — never 0%, which is a finding about the text rather than about us.
_SCRIPT_RANGES = [
    ("han", r"[\u4e00-\u9fff\u3400-\u4dbf]"),
    ("kana", r"[\u3040-\u30ff]"),
    ("hangul", r"[\uac00-\ud7af\u1100-\u11ff]"),
    ("cyrillic", r"[\u0400-\u04ff]"),
    ("greek", r"[\u0370-\u03ff]"),
    ("arabic", r"[\u0600-\u06ff]"),
    ("thai", r"[\u0e00-\u0e7f]"),
    ("devanagari", r"[\u0900-\u097f]"),
    ("latin", r"[A-Za-z\u00c0-\u024f]"),
]

# A profile says how to CUT the text and what we can legitimately say about it.
#   unit            — 'char' for scripts written without spaces, 'word' for space-delimited ones
#   enders          — the sentence terminators of that script
#   connectives     — curated list, or None when we have none (then the check is UNAVAILABLE)
#   antithesis      — (pattern, has-two-capture-groups) or None, same rule
_PROFILES = {
    "han": {"unit": "char", "enders": "。！？!?…", "smart_latin": False,
            "connectives": r"但|可是|不过|所以|因为|于是|结果|而且|然后|其实|反而|只要|一旦|除非|哪怕",
            # The two sides must be the two PARALLEL CONSTITUENTS, so each is bounded by a clause
            # separator rather than "up to 24 characters back". Capturing the whole preceding half of the
            # sentence made every real antithesis look lopsided and the parallelism filter threw them all
            # out — 5 of 6 hand-judged contrasts were missed.
            "antithesis": [
                # 不是X，(而)是Y  ·  不在X，(而)在(于)Y
                r"不(?:是|在)([^，。：；！？]{2,24})[，,]\s*(?:而是|而在|在于|是|在)([^。！？]{2,24})",
                # X，(而/却/并/只)不是Y  ·  …不看Y  ·  …不找Y
                r"([^，。：；！？]{2,24})[，,]\s*(?:而|却|并|只)?不(?:是|在|看|找|靠)([^。！？]{2,24})",
                # X，没说/没有Y
                r"([^，。：；！？]{2,24})[，,]\s*没(?:说|有)([^。！？]{2,24})",
                # 不V X，(去)V Y — the verb repeats on both sides, which is the parallelism itself
                r"不(.)([^，。：；！？]{2,20})[，,]\s*(?:而|却)?(?:去)?\1([^。！？]{2,20})",
            ]},
    "kana": {"unit": "char", "enders": "。！？!?", "smart_latin": False,
             "connectives": None, "antithesis": None},
    "latin": {"unit": "word", "enders": ".!?…", "smart_latin": True,
              "connectives": r"\b(but|so|because|though|although|however|yet|actually|still|then|once|"
                             r"unless|even if|which is why|turns out|that is why|instead)\b",
              "antithesis": [r"\bnot\s+(.{2,60}?)\s*,?\s*but\s+(?:rather\s+)?(.{2,60})",
                             r"([^,.;]{2,60}),\s*not\s+([^.;]{2,60})",
                             r"\brather than\s+(.{2,60}?)\s*,\s*(.{2,60})"]},
    "hangul": {"unit": "word", "enders": ".!?。", "smart_latin": False,
               "connectives": None, "antithesis": None},
    "cyrillic": {"unit": "word", "enders": ".!?…", "smart_latin": False,
                 "connectives": None, "antithesis": None},
    # Each of these needs only its own sentence terminator to be measurable at all: the Devanagari danda,
    # the Arabic question mark, the Greek question mark (which is the semicolon). Declaring the script
    # range without them meant a Hindi beat was ONE sentence however long it ran, and the length metrics
    # reported a confident number for something never segmented.
    "devanagari": {"unit": "word", "enders": ".!?।", "smart_latin": False,
                   "connectives": None, "antithesis": None},
    "arabic": {"unit": "word", "enders": ".!?؟", "smart_latin": False,
               "connectives": None, "antithesis": None},
    "greek": {"unit": "word", "enders": ".!?;", "smart_latin": False,
              "connectives": None, "antithesis": None},
    # Thai is written WITHOUT word spaces and without a sentence-ending mark; its spaces are phrase
    # breaks. Counting "words" there produced 3 units for a whole paragraph. Segmenting it needs a
    # dictionary this script does not have, so it is marked UNSUPPORTED and its beats are left out of the
    # length metrics rather than given a plausible-looking wrong number.
    "thai": {"unit": "word", "enders": ".!?", "smart_latin": False,
             "connectives": None, "antithesis": None, "unsupported": True},
}
# Anything with no profile at all: measurable only if it happens to be space-delimited and use ASCII
# stops, which we cannot know. Treated as unsupported for the same reason as Thai.
_DEFAULT_PROFILE = {"unit": "word", "enders": ".!?。！？", "smart_latin": False,
                    "connectives": None, "antithesis": None, "unsupported": True}

# Every threshold is a NAMED constant so a test can walk them and probe each boundary. Inline literals
# are why a mutation audit could disable five thresholds one at a time and the suite stayed green.
THRESHOLDS = {
    "uniform_cv": 0.45,      # sentence-length CV BELOW this = template-uniform
    "antithesis": 0.35,      # share of beats built on a negation contrast ABOVE this
    "balanced": 0.35,        # share of beats that are a balanced pair ABOVE this
    "connective": 0.30,      # share of beats carrying any connective BELOW this
    "aphorism": 0.30,        # share of beats ending on an antithesis ABOVE this
}
BALANCED_TOL = 0.30          # two clauses count as "equal length" within this fraction
MIN_BEATS = 3                # below this there is not enough text to judge rhythm
MIN_SENTENCES = 6
PARALLEL_RATIO = 3.0         # the two sides of a real antithesis are comparable in length

# Latin abbreviations that end in a period without ending the sentence.
_ABBR = (r"e\.g|i\.e|etc|vs|cf|approx|al|Dr|Mr|Mrs|Ms|Prof|Sr|Jr|St|Fig|No|Inc|Ltd|Co|Jan|Feb|Mar|Apr|"
         r"Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec")


def _script_of(text):
    """The dominant script of one beat, ignoring digits, spaces and shared punctuation."""
    counts = {}
    for name, rng in _SCRIPT_RANGES:
        counts[name] = len(re.findall(rng, text))
    total = sum(counts.values())
    if not total:
        return "latin"
    top = max(counts, key=counts.get)
    # Han and kana travel together in Japanese; kana is the tell, so any meaningful kana wins.
    if counts.get("kana", 0) >= max(3, 0.15 * total):
        return "kana"
    return top


def profile_for(script):
    return _PROFILES.get(script, _DEFAULT_PROFILE)


def _strip(t):
    return re.sub(r"[，。、；：！？「」（）()·,.;:!?\s]", "", t)


def _latin_sentences(t):
    r"""Sentence split for a space-delimited script.

    The previous rule was `(?<!\d)[.!?]+(?!\d)`, which claimed in its own comment to handle
    abbreviations and did not, and which broke in the other direction too: requiring a non-digit BEFORE
    the stop meant a sentence that legitimately ENDS in a number ("It dropped to 19.3.") never
    terminated. Split only where a terminator is followed by whitespace-then-capital or end of text, and
    never inside a decimal, an initial, or a known abbreviation.
    """
    out, start = [], 0
    for m in re.finditer(r"[.!?]+", t):
        i, j = m.start(), m.end()
        # (No separate decimal guard: the following-context rule below already refuses to split "19.3",
        # because the character after that stop is a digit rather than whitespace. A guard that cannot
        # change any outcome is dead code, and a test written for it would be theatre.)
        before = t[:i]
        if re.search(r"(?:^|[\s(\"'])(?:%s)$" % _ABBR, before, re.I):
            continue                                              # e.g. / vs. / Dr.
        # An initial or a dotted initialism: "J. Smith", "U.S. Army". Matching a SINGLE capital only was
        # not enough — in "The U.S. Army" the S is preceded by a dot, not a space, so it split there.
        if re.search(r"(?:^|\s)(?:[A-Z]\.)*[A-Z]$", before):
            continue
        rest = t[j:]
        if rest.strip() and not re.match(r"\s+[\"'(\[]?[A-Z0-9]", rest):
            continue                                              # not a sentence boundary
        out.append(t[start:j])
        start = j
    tail = t[start:]
    if tail.strip():
        out.append(tail)
    return [x.strip() for x in out if x.strip()]


def _sentences(t, prof):
    if prof.get("smart_latin"):
        return _latin_sentences(t)
    return [x.strip() for x in re.split(r"[%s]+" % re.escape(prof["enders"]), t) if x.strip()]


def _units(t, prof):
    if prof["unit"] == "char":
        return len(_strip(t))
    return len([w for w in re.split(r"\s+", t.strip()) if w])


def _antithesis_pairs(text, prof):
    """The antithesis pairs in one beat, AFTER requiring the two sides to be parallel.

    Matching the negation alone made ordinary conversational negation ("so you never miss it", "it does
    not exist") count as the rhetorical figure, which inflated the share on hand-written prose. The
    figure sets two COMPARABLE things against each other; a bare negation has no counterpart. So both
    captured sides must be non-trivial and within PARALLEL_RATIO of each other in length.
    """
    pats = prof.get("antithesis")
    if not pats:
        return None                                    # UNAVAILABLE for this script — not "zero"
    hits = []
    for pat in pats:
        for m in re.finditer(pat, text, re.I):
            if m.lastindex is None or m.lastindex < 2:
                continue
            # The two SIDES are the last two captures. Taking groups 1 and 2 broke the verb-repeat
            # pattern, where group 1 is the repeated verb (one character) and the parallelism filter then
            # threw the match out for being lopsided.
            a = (m.group(m.lastindex - 1) or "").strip()
            b = (m.group(m.lastindex) or "").strip()
            la, lb = _units(a, prof), _units(b, prof)
            if la < 1 or lb < 1:
                continue
            if max(la, lb) > PARALLEL_RATIO * max(1, min(la, lb)):
                continue
            hits.append((a, b))
    return hits


_MSG = {
    "uniform": {
        "zh": "句长过于齐整 CV=%.2f(<%.2f)— 每拍都是同一种长度的短断句，读一整片就是模板。"
              "让一部分句子长一点、把两句并成一句带转折的长句。",
        "en": "sentence length is uniform, CV=%.2f (<%.2f) — every beat the same shape. Let some beats run "
              "one longer sentence with a turn in it and others be four words; uniformity is the tell.",
    },
    "antithesis": {
        "zh": "否定式对仗占 %.0f%%(>%.0f%%)— 「不是X，是Y」一旦成为默认，就是机器味最重的地方。"
              "留给真正需要纠正误解的那几拍。",
        "en": "%.0f%% of beats are built on a negation contrast (>%.0f%%) — \"not X, but Y\" as a default "
              "move is the loudest machine tic. Keep it for beats that correct a real misconception.",
    },
    "balanced": {
        "zh": "「两句等长对置」占 %.0f%%(>%.0f%%)— A。B。两句掰成同样长短互相衬托，"
              "是最不容易自觉的机器句式（没有任何禁用词，所以词表查不出来）。"
              "把一部分改成一句话说完，或让第二句明显长/短于第一句。",
        "en": "%.0f%% of beats are a balanced pair (>%.0f%%) — two clauses of near-equal length set against "
              "each other. It carries no banned word, so no vocabulary list can see it. Merge some into one "
              "sentence, or make the second clearly longer or shorter than the first.",
    },
    "connective": {
        "zh": "带连接词的拍只有 %.0f%%(<%.0f%%)— 通篇电报体、句与句之间没有「但/所以/其实」，"
              "像字幕条而不像人在讲。",
        "en": "only %.0f%% of beats carry any connective (<%.0f%%) — no but/so/actually/turns out anywhere. "
              "That is not concision, it is subtitle copy: connectives are how a listener learns how two "
              "facts relate.",
    },
    "aphorism": {
        "zh": "以警句收尾的拍占 %.0f%%(>%.0f%%)— 不是每一拍都要落一个金句；多数拍只要把信息交代清楚。",
        "en": "%.0f%% of beats end on an aphorism (>%.0f%%) — most beats only need to deliver their fact. "
              "Save the landing for the two or three that earned it.",
    },
    "note": {
        "zh": "提示：以上都是「去看一眼」的位置，不是要压到零。规则用过头会产生新的规则腔——"
              "一段触发了检查却读着自然的话，不用改。",
        "en": "note: each number marks a place to LOOK, never a target. Over-applying the rules produces its "
              "own artificiality; a beat that trips a check and reads well aloud is fine as it is.",
    },
}


def evaluate(narrations):
    """narrations: list of (beat_index, text). Returns a report dict.

    Each beat is classified by SCRIPT and measured with that script's profile, so a mixed-script film is
    not forced through one set of rules. A check with no curated list for a script reports UNAVAILABLE
    rather than 0% — reporting zero would be a claim about the writing when it is a gap in this tool.
    """
    warnings, notes = [], []
    beats = [(i, t, _script_of(t)) for i, t in narrations]
    scripts = {}
    for _, _, sc in beats:
        scripts[sc] = scripts.get(sc, 0) + 1
    dominant = max(scripts, key=scripts.get) if scripts else "latin"
    lang = "zh" if dominant == "han" else "en"          # the language the REPORT is written in
    if len(scripts) > 1:
        notes.append(("本片混用了 %s 两种以上文种；每拍按自己的文种切分和计量。" if lang == "zh" else
                      "this script mixes %s; each beat is segmented and counted by its own script.")
                     % ", ".join("%s x%d" % (k, v) for k, v in sorted(scripts.items(), key=lambda x: -x[1])))

    # (A) vocabulary — the list that matches the beat's own script
    vocab = {}
    for name, pat in (ZH_TELLS if dominant == "han" else EN_TELLS).items():
        hits = [(i, m.group(0)) for i, t, _ in beats for m in re.finditer(pat, t, re.I)]
        if hits:
            vocab[name] = hits
            warnings.append("%s x%d — %s" % (name, len(hits), " / ".join(h[1] for h in hits[:3])))
    if dominant == "han":
        mp = [(i, m.group(0)) for i, t, _ in beats for m in re.finditer(MIXED_PUNCT, t)]
        if mp:
            warnings.append("半角标点混入中文 x%d — %s" % (len(mp), mp[0][1]))

    # (B) rhythm — per beat, under that beat's profile
    sent, balanced, anti, endsharp, conn = [], [], [], [], []
    measurable_anti, measurable_conn = 0, 0
    unsupported_beats = []
    for i, t, sc in beats:
        prof = profile_for(sc)
        if prof.get("unsupported"):
            unsupported_beats.append((i, sc))
            continue                     # no segmenter for this script — measure nothing rather than guess
        ss = _sentences(t, prof)
        ls = [_units(x, prof) for x in ss]
        sent.extend(ls)
        if 2 <= len(ls) <= 3 and min(ls) >= 4 and (max(ls) - min(ls)) <= BALANCED_TOL * max(ls):
            balanced.append(i)
        pairs = _antithesis_pairs(t, prof)
        if pairs is not None:
            measurable_anti += 1
            if pairs:
                anti.append(i)
            if ss and _antithesis_pairs(ss[-1], prof):
                endsharp.append(i)
        if prof.get("connectives"):
            measurable_conn += 1
            if re.search(prof["connectives"], t, re.I):
                conn.append(i)
    cv = (statistics.pstdev(sent) / statistics.mean(sent)) if len(sent) > 1 and statistics.mean(sent) else 0.0
    n = max(1, len(beats))
    m = {
        "beats": len(beats),
        "scripts": scripts,
        "sentence_len_mean": round(statistics.mean(sent), 1) if sent else 0,
        "sentence_len_cv": round(cv, 3),
        "antithesis_share": round(len(anti) / measurable_anti, 3) if measurable_anti else None,
        "connective_share": round(len(conn) / measurable_conn, 3) if measurable_conn else None,
        "aphorism_ending_share": round(len(endsharp) / measurable_anti, 3) if measurable_anti else None,
        "balanced_pair_share": round(len(balanced) / n, 3),
    }
    if unsupported_beats:
        notes.append(("有 %d 拍使用了本工具无法切分的文种(%s)，这些拍不参与任何节奏指标。" if lang == "zh" else
                      "%d beat(s) are in a script this tool cannot segment (%s); they are left out of every "
                      "rhythm metric rather than given a number.")
                     % (len(unsupported_beats), ", ".join(sorted({sc for _, sc in unsupported_beats}))))
    unsupported = sorted({sc for _, _, sc in beats
                          if not profile_for(sc).get("unsupported") and not profile_for(sc).get("connectives")})
    if beats and unsupported and (m["connective_share"] is None or m["antithesis_share"] is None):
        notes.append(("没有针对「%s」文种的连接词/对仗词表，这两项本次不作判断（报 0%% 会把工具的空白说成文本的问题）。"
                      if lang == "zh" else
                      "no curated connective/antithesis list for the '%s' script, so those two checks are "
                      "UNAVAILABLE here — reporting 0%% would blame the writing for a gap in this tool.")
                     % ", ".join(unsupported))
    # Too little text to say anything about rhythm. A 0- or 1-beat film has CV 0.00 by construction, so
    # firing the thresholds on it produces confident nonsense.
    if len(sent) < MIN_SENTENCES or len(beats) < MIN_BEATS:
        notes.append(("只有 %d 拍 / %d 个句子，样本太小，节奏指标不作判断。" if lang == "zh" else
                      "only %d beat(s) / %d sentence(s) — too little text to judge rhythm; thresholds skipped.")
                     % (len(beats), len(sent)))
        return {"metrics": m, "warnings": warnings, "vocab": vocab, "notes": notes, "fired": [],
                "antithesis_beats": anti, "language": lang, "dominant_script": dominant}

    # THRESHOLDS. Set against a REAL measured case: a delivered 37-beat Chinese explainer that its author
    # found machine-sounding scored CV 0.30, balanced-pair 40%, connectives 11%, antithesis 24% — and ZERO
    # on every vocabulary list above. Those four numbers are what these sit around.
    #
    # NOT CALIBRATED, and it matters twice over: 0.45 is a judgement call rather than a figure measured
    # against human-written reference text, and it is LESS anchored for a space-delimited script than for
    # Chinese because the two count different units (characters vs words) and the same number does not
    # mean the same spread. Treat every figure as directional. Do NOT pad sentences to clear one — that is
    # precisely the "rule voice" the reference warns about. A script that trips only this and reads well
    # aloud should be accepted, out loud.
    #
    # They live in THRESHOLDS (a dict, not inline literals) so a test can walk every one of them and probe
    # both sides of each boundary. A mutation audit disabled five inline thresholds one at a time and the
    # whole suite stayed green.
    fired = []                       # which thresholds decided to speak — the testable decision
    if cv < THRESHOLDS["uniform_cv"]:
        fired.append("uniform_cv")
        warnings.append(_MSG["uniform"][lang] % (cv, THRESHOLDS["uniform_cv"]))
    if m["antithesis_share"] is not None and m["antithesis_share"] > THRESHOLDS["antithesis"]:
        fired.append("antithesis")
        warnings.append(_MSG["antithesis"][lang] % (100 * m["antithesis_share"], 100 * THRESHOLDS["antithesis"]))
    if m["balanced_pair_share"] > THRESHOLDS["balanced"]:
        fired.append("balanced")
        warnings.append(_MSG["balanced"][lang] % (100 * m["balanced_pair_share"], 100 * THRESHOLDS["balanced"]))
    if m["connective_share"] is not None and m["connective_share"] < THRESHOLDS["connective"]:
        fired.append("connective")
        warnings.append(_MSG["connective"][lang] % (100 * m["connective_share"], 100 * THRESHOLDS["connective"]))
    if m["aphorism_ending_share"] is not None and m["aphorism_ending_share"] > THRESHOLDS["aphorism"]:
        fired.append("aphorism")
        warnings.append(_MSG["aphorism"][lang] % (100 * m["aphorism_ending_share"], 100 * THRESHOLDS["aphorism"]))
    notes.append(_MSG["note"][lang])
    return {"metrics": m, "warnings": warnings, "vocab": vocab, "notes": notes, "fired": fired,
            "antithesis_beats": anti, "language": lang, "dominant_script": dominant}


def main(argv):
    if not argv:
        print(__doc__.strip())
        return 2
    out_dir = argv[0]
    board = os.path.join(out_dir, "storyboard.json")
    if not os.path.exists(board):
        print("[voice_qa] no storyboard.json in %s" % out_dir)
        return 2
    data = json.load(open(board, encoding="utf-8"))
    slides = data.get("slides") or []
    if not isinstance(slides, list):
        print("[voice_qa] storyboard.json has no usable `slides` list")
        return 2
    nar = [(s.get("index", i), str(s.get("narration") or ""))
           for i, s in enumerate(slides) if isinstance(s, dict)]
    nar = [(i, t) for i, t in nar if t.strip()]
    r = evaluate(nar)
    if "--json" in argv:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    m = r["metrics"]
    # A share is None when there is no curated list for that script (or nothing measurable at all).
    # Multiplying it by 100 in the headline crashed the CLI on exactly those films.
    def _pct(v):
        return "n/a" if v is None else "%.0f%%" % (100 * v)
    head = ("[voice_qa] %d beat(s), %s — 句长 mean=%.1f CV=%.2f | 否定对仗 %s | 连接词 %s | 警句收尾 %s"
            if r["language"] == "zh" else
            "[voice_qa] %d beat(s), %s — sentence len mean=%.1f CV=%.2f | antithesis %s | connectives %s | aphorism endings %s")
    print(head
          % (m["beats"], r["dominant_script"], m["sentence_len_mean"], m["sentence_len_cv"],
             _pct(m["antithesis_share"]), _pct(m["connective_share"]), _pct(m["aphorism_ending_share"])))
    print(("           两句等长对置 %.0f%%" if r["language"] == "zh" else
           "           balanced pairs %.0f%%") % (100 * m["balanced_pair_share"]))
    for w in r["warnings"]:
        print("  warn : " + w)
    for nline in r["notes"]:
        print("  note : " + nline)
    print("[voice_qa] %s" % ("OK" if not r["warnings"] else "%d signal(s) to look at" % len(r["warnings"])))
    # ADVISORY BY DESIGN: this always exits 0. The metrics mark places to LOOK, and a script that trips a
    # check can still be the right script — failing the build on them would produce the "rule voice" the
    # reference warns about. SKILL.md must therefore NOT list it among the gates that must exit 0.
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
