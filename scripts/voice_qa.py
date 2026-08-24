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
      - antithesis density: the share of beats built on a NEGATION contrast (surface form only — it
        under-reports contrast carried by meaning alone, so the human read is still required).
      - balanced-pair share: two or three clauses of near-equal length set against each other, which is
        the same move with no negation word in it and therefore invisible to every vocabulary list.
      - connective density: the share of beats carrying any 但/所以/其实/不过 … at all.
      - aphorism ending: the share of beats whose LAST sentence is a contrast/definition punchline.

HONEST LIMIT, and it matters: rules remove maybe half of it. Published practice reports 40-50%, and
over-applying rules produces its own artificiality — a "rule voice" that dodges every listed pattern and
still is not a person. Treat every number here as a place to LOOK, not a target to optimise. A beat that
trips a check and reads well is fine; a beat that passes everything and reads dead is still dead.
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

# ── (B) rhythm tells ─────────────────────────────────────────────────────────────────────────────────
# A negation CONTRAST, in the several surface forms a punchy explainer actually uses. The textbook
# "不是X而是Y" is only one of them, which is why a checklist that greps for it alone reports zero.
# PER LANGUAGE. The first version of this file was calibrated on a Chinese film and every rhythm pattern
# below was Chinese-only — including the SENTENCE SPLITTER, which listed 。！？!? but not a full stop. On an
# English script nothing ever split, so "sentence length" silently measured whole BEATS, "balanced pair"
# could never fire, and the connective share was 0% on every English film by construction: three metrics
# reporting confidently about something they were not measuring.
ANTITHESIS = {
    "zh": r"不是.{1,16}[，,。]?\s*(而是|是)|不在.{1,16}[，,。]?\s*在于|(?<![一-鿿])没(说|有).{1,16}[。，]|不看.{1,14}[。，]|不去.{1,14}[。，]|(?<![一-鿿])不(是|会|在)[^。]{0,14}。",
    # English puts the negation on either side: "not X but Y" and, just as often, the TRAILING form
    # "…how strong the tests are, not how correct the code is".
    "en": r",\s*not\b|\bnot\b[^.;]{0,60}\bbut\b|\b(?:it'?s|is|was)\s+not\b[^.;]{0,40}(?:,|but)|\brather than\b|\bisn'?t (?:about|that)\b|\bnot (?:what|how|whether)\b",
}
CONNECTIVES = {
    "zh": r"但|可是|不过|所以|因为|于是|结果|而且|然后|其实|反而|只要|一旦|除非|哪怕",
    "en": r"\b(but|so|because|though|although|however|yet|actually|still|then|once|unless|even if|which is why|turns out|that is why)\b",
}
# A full stop only ends a sentence when it is not sitting inside a number (19.3) or an abbreviation.
SENT_SPLIT = {"zh": r"[。！？!?]+", "en": r"(?<!\d)[.!?]+(?!\d)|[。！？]+"}


def _strip(t):
    return re.sub(r"[，。、；：！？「」（）()·,.;:!?\s]", "", t)


def _sentences(t, lang="zh"):
    return [s for s in re.split(SENT_SPLIT[lang], t) if s.strip()]


# The warnings are written in the language of the SCRIPT being judged: a Chinese report on an English film
# is a report nobody reads.
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
    """narrations: list of (beat_index, text). Returns a report dict."""
    warnings, notes = [], []
    joined = "\n".join(t for _, t in narrations)
    is_cjk = len(re.findall(r"[一-鿿]", joined)) > len(joined) * 0.3
    lang = "zh" if is_cjk else "en"

    # (A) vocabulary
    vocab = {}
    for name, pat in (ZH_TELLS if is_cjk else EN_TELLS).items():
        hits = [(i, m.group(0)) for i, t in narrations for m in re.finditer(pat, t, re.I)]
        if hits:
            vocab[name] = hits
            warnings.append("%s x%d — %s" % (name, len(hits), " / ".join(h[1] for h in hits[:3])))
    if is_cjk:
        mp = [(i, m.group(0)) for i, t in narrations for m in re.finditer(MIXED_PUNCT, t)]
        if mp:
            warnings.append("半角标点混入中文 x%d — %s" % (len(mp), mp[0][1]))

    # (B) rhythm
    def _units(x):                     # Chinese counts characters; English counts WORDS
        return len(_strip(x)) if is_cjk else len([w for w in re.split(r"\s+", x.strip()) if w])
    sent = [_units(s) for _, t in narrations for s in _sentences(t, lang)]
    cv = (statistics.pstdev(sent) / statistics.mean(sent)) if len(sent) > 1 and statistics.mean(sent) else 0.0
    anti = [i for i, t in narrations if re.search(ANTITHESIS[lang], t, re.I)]
    conn = [i for i, t in narrations if re.search(CONNECTIVES[lang], t, re.I)]
    # BALANCED PAIR — the template the antithesis regex misses. "读着合理的那种不出声。写崩的立刻报错。"
    # carries no negation word at all, yet it is the same machine move: two clauses of near-equal length
    # set against each other, subject dropped. Measured structurally, so it needs no vocabulary list.
    balanced = []
    for i, t in narrations:
        ls = [_units(s) for s in _sentences(t, lang)]
        if 2 <= len(ls) <= 3 and min(ls) >= 4 and (max(ls) - min(ls)) <= 0.3 * max(ls):
            balanced.append(i)
    endsharp = []
    for i, t in narrations:
        ss = _sentences(t, lang)
        if ss and re.search(ANTITHESIS[lang], ss[-1], re.I):
            endsharp.append(i)
    n = max(1, len(narrations))
    m = {
        "beats": len(narrations),
        "sentence_len_mean": round(statistics.mean(sent), 1) if sent else 0,
        "sentence_len_cv": round(cv, 3),
        "antithesis_share": round(len(anti) / n, 3),
        "connective_share": round(len(conn) / n, 3),
        "aphorism_ending_share": round(len(endsharp) / n, 3),
        "balanced_pair_share": round(len(balanced) / n, 3),
    }
    # Thresholds are set against a REAL measured case: a delivered 37-beat Chinese explainer that its
    # author found machine-sounding scored CV 0.30, balanced-pair 40%, connectives 11%, antithesis 24% —
    # and ZERO on every vocabulary list above. Those four numbers are what these thresholds sit around.
    # They mark where to LOOK; none of them is a target to drive to zero.
    # NOTE ON THIS THRESHOLD: 0.45 is a judgement call, not a figure measured against human-written
    # reference text — and it is LESS anchored for English than for Chinese, because the two count
    # different units (Chinese characters vs English words) and the same number does not mean the same
    # spread in both. Treat the English figure as directional only until someone measures it.
    # ORIGINAL NOTE: 0.45 is a judgement call, not a figure measured against human-written
    # reference text. The measured contrast it is anchored to is real (a script that read as machine-made
    # sat at 0.30; the same script rewritten with connectives and varied sentence length reached 0.39 and
    # read far better), but the line itself is not calibrated. Do NOT pad sentences to clear it — that is
    # precisely the "rule voice" this file warns about. If a script trips only this check and reads well
    # aloud, accept it and say so.
    if cv < 0.45:
        warnings.append(_MSG["uniform"][lang] % (cv, 0.45))
    if m["antithesis_share"] > 0.35:
        warnings.append(_MSG["antithesis"][lang] % (100 * m["antithesis_share"], 35))
    if m["balanced_pair_share"] > 0.35:
        warnings.append(_MSG["balanced"][lang] % (100 * m["balanced_pair_share"], 35))
    if m["connective_share"] < 0.30:
        warnings.append(_MSG["connective"][lang] % (100 * m["connective_share"], 30))
    if m["aphorism_ending_share"] > 0.30:
        warnings.append(_MSG["aphorism"][lang] % (100 * m["aphorism_ending_share"], 30))
    notes.append(_MSG["note"][lang])
    return {"metrics": m, "warnings": warnings, "vocab": vocab, "notes": notes,
            "antithesis_beats": anti, "language": "zh" if is_cjk else "en"}


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
    nar = [(s.get("index", i), str(s.get("narration") or "")) for i, s in enumerate(data.get("slides", []))]
    nar = [(i, t) for i, t in nar if t.strip()]
    r = evaluate(nar)
    if "--json" in argv:
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    m = r["metrics"]
    print("[voice_qa] %d beat(s), %s — 句长 mean=%.1f CV=%.2f | 否定对仗 %.0f%% | 连接词 %.0f%% | 警句收尾 %.0f%%"
          % (m["beats"], r["language"], m["sentence_len_mean"], m["sentence_len_cv"],
             100 * m["antithesis_share"], 100 * m["connective_share"], 100 * m["aphorism_ending_share"]))
    print("           两句等长对置 %.0f%%" % (100 * m["balanced_pair_share"]))
    for w in r["warnings"]:
        print("  warn : " + w)
    for nline in r["notes"]:
        print("  note : " + nline)
    print("[voice_qa] %s" % ("OK" if not r["warnings"] else "%d signal(s) to look at" % len(r["warnings"])))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
