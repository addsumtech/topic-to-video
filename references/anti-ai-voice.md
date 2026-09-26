# Writing narration that sounds like a person

> **When to read this:** before writing or revising ANY narration or on-screen copy, in any language.
> The deterministic backstop is `python3 scripts/voice_qa.py <out_dir>` — run it after the script step
> and again after any rewrite. It reports where to look; it cannot tell you whether the result is good.

## The honest frame, first

Published practice on removing "AI flavour" reports that rules get you **roughly 40–50% of the way**, and
that **over-applying them creates its own artificiality** — a "rule voice" (規則腔) that dodges every listed
pattern and still is not a person. Two consequences for how this file is used:

1. Every check below marks a place to **look**, never a number to drive to zero. A sentence that trips a
   check and reads naturally is fine.
2. The last pass is a human read-aloud. If it cannot be read aloud in one breath the way a person would
   actually say it, the metrics do not matter.

Sources: [去 AI 味 skill (牛合天 wiki)](https://wiki.liuhetian.work/skills/writing/qu-ai-wei/) ·
[別抄 Prompt，建一套會自我更新的寫作 Skill (RAR)](https://rar.design/posts/de-ai-flavor-writing-skill-guide) ·
[10 个去 AI 味 skill 横评](https://blog.enovace.com/zh/ai/2026/06/25/humanize-ai-writing-skills/)

## Three layers

**1 · Prohibition — what never appears.** The vocabulary tells below. Cheap, mechanical, and the part every
checklist already covers. `voice_qa.py` greps these.

**2 · Voice — what this narrator sounds like.** Do NOT describe it as "professional but approachable"; that
produces the average of everything. Instead pin it to the *material*: who is speaking, to whom, and what
they would never say. For an explainer: a practitioner talking to a colleague who is smart but has not seen
this evidence. They cite what they read, they admit what they could not verify, and they do not perform.

**3 · Review — the self-check before hand-off.** Run `voice_qa.py`, then read the whole script aloud in one
pass. Both. The script catches distribution; only the read catches deadness.

## Layer 1 — the vocabulary tells (中文)

| Tell | Examples |
|---|---|
| 时代背景开场 | 随着…的不断发展 · 在…的大背景下 · 在这个…的时代 |
| 空转枢纽 | 需要注意的是 · 值得一提的是 · 归根结底 · 说到底 · 核心在于 |
| 商务黑话 | 赋能 · 助力 · 打造 · 护航 · 抓手 · 闭环 · 底层逻辑 · 全方位 · 多维度 |
| 装饰性短语 | 通过…的方式 · 在…的情况下 · 由于…的原因 · 在一定程度上 · 从某种意义上 |
| 弱动词 | 进行讨论 → 讨论 · 开展工作 → 工作 · 实现突破 → 做成了 / 跑通了 |
| 机械排比 | 首先/其次/最后 三段式 · 一律拆成三点 |
| 标点 | 中文正文只用全角 `，。！？；：「」`；破折号 `——` 在真实中文里密度接近零，高频出现就是机器痕迹 |

## Layer 1 — the vocabulary tells (English)

`delve` · `tapestry` · `realm` · `landscape of` · `navigate the` · `underscores` · `a testament to` ·
`it's worth noting` · `at the end of the day` · `not just X, but Y` as a default construction ·
`first…second…finally` triads · hedge stacks (`in a sense`, `to some extent`, `arguably`).

## Layer 1 — the tells no checklist lists (and the ones that actually got us)

A delivered 37-beat Chinese explainer scored **zero** on every table above and still read as machine-written.
The signature had moved from vocabulary to **rhythm**. Measured on that script:

| Measure | It scored | What it means |
|---|---|---|
| sentence-length CV | **0.30** | every sentence is the same length; 37 beats of it is a template |
| balanced-pair share | **40%** | `A。B。` — two clauses of near-equal length set against each other |
| connective share | **11%** | almost no 但/所以/其实/不过 — telegraphic, like subtitle cards, not speech |
| negation antithesis | **24%** | 「不是X，是Y」/「不看…，看…」 as the default move |

Read once, a clipped antithesis is punchy. Read thirty-seven times in a row, it is a machine tic. The fixes:

- **Vary sentence length on purpose.** Let some beats run one long sentence with a turn in the middle; let
  others be four words. Uniformity is the tell, not length.
- **Restore the connective tissue.** People say 但/所以/其实/结果/反而. A script with none of them is not
  concise, it is unnatural — the connectives are how a listener knows how two facts relate.
- **Stop landing every beat.** Most beats only need to deliver their fact. Save the aphorism for the two or
  three beats that have earned it — usually the thesis and the close.
- **Keep the antithesis for genuine correction.** 「不是X，是Y」 exists to fix a misconception. Where the
  listener holds no misconception, it is decoration.
- **Let a subject in.** Subject-dropping is natural in Chinese, but *unrelieved* subject-dropping reads as
  caption copy. 我们、它、这套检查 — naming the actor occasionally is what makes it sound spoken.

## What does NOT work

- Pasting a "de-AI" prompt. Everyone uses the same ones, so the output moves to a shared second-order style,
  not to a voice.
- Optimising the metrics. A script tuned to CV 0.5 and 35% connectives, sentence by sentence, produces the
  rule voice — technically varied, still nobody's.
- Asking the model to "be more human". It has no referent for that. Give it the *material* instead: the real
  constraint, the thing you actually could not verify, the sentence you would say to a colleague.

## The one move that reliably helps

Write the beat as if answering a colleague who just asked "wait, why?" — then cut what they already knew.
That produces uneven sentence length, real connectives, and an occasional first person, for free, because
that is what answering a question actually sounds like.

## Layer 4 — the script that cleared every number and still read as a machine

A 37-beat Chinese film measured CV 0.45, antithesis 8%, connectives 38%, aphorism endings 5%, balanced
pairs 5% — the whole panel clear — and the person who watched it said, on the first listen,
「脚本没有人的感觉，读起来也很机器」. Two things were wrong, and no metric here could see either.

**It was too finished to be speech.** Spoken language is defined by short, simple, *often incomplete*
sentences with **repetition, false starts and asides**; written language is what is coherent, ordered,
precise and regular. All 37 lines were complete, self-contained, maximally-compressed aphorisms — not one
half-sentence, not one repetition, not one aside. The script was not badly written. It was written to a
standard that no one talks in. Research on synthetic speech says the same thing from the other side:
listeners read localized irregularity — a filler, a pause, a small repetition, a mid-sentence correction —
as the marker of a human, and hear the regular version as the machine. **Imperfection is what reads as
authentic**, which means a line you cannot improve any further is often a line you have polished past a
person.

**And one good device became the template.** Seven beats opened on the same short denial answering the
previous beat's implied question — 「不会。」「不能。」「删不掉。」「不是匹配度。」. It is a genuinely
conversational shape; it earned its place the first two or three times. By the seventh it *is* the
formula, and a reviewer had said so in prose while every number stayed green. `voice_qa` now reports
`same_opener` for exactly this, because the lesson was that prose findings get filed as non-blocking and
numbers do not.

Both of these are tier-agnostic. Neither has anything to do with the renderer: they are properties of the
narration, which the html tier and the remotion tier share, and `voice_qa` reads the same
`storyboard.json` for both.

**The repair is not a ban list.** Published practice on this is blunt: prompting an AI with prohibitions
does not fix it, because the problem is not vocabulary — a model writes in the *average* of everything it
read, and "avoid X" never tells it whose voice to write in instead. What worked here was naming the
structural fault (too complete) and the specific tic (one opener, seven times), then rewriting with a
target register the user chose from rendered options. What did NOT work was the first pass over the
metrics, which produced a tighter script that still read as written.

**The last check is still a person reading it aloud, in order.** The numbers above mark places to look.
On this film every number looked fine and the film was not.


## Layer 5 — every line is speech and all of them are the same shape

The film from Layer 4 was rewritten and reads, line by line, like a person: 「纸上是挑不出毛病的，可守不守得住，
要到面试当场才知道」「四句人话，一轮就跑完了」. Read any beat aloud and it is speech. Read all 37 and it is a
template, and `voice_qa` says so — **句长过于齐整 CV=0.30**.

Measured on the delivered board:

| | |
|---|---|
| beats holding exactly ONE sentence | **33 of 37** |
| sentence length | median 22 chars, **CV 0.30** (target ≥ 0.45) |
| speaking rate | **4.1 chars/second**, flat across the film |
| beat durations | median 5.2s, CV 0.20 |

**One sentence per beat means no beat has any internal contrast.** Whatever rhythm the film has must then
come from beat differing from beat — nothing inside a single beat carries it, because there is nothing
inside a single beat to compare. That is the specific shape of this failure, and it is not visible to any
vocabulary check: every word is fine, every line is fine, and the 37th one arrives in the same rhythm as
the first.

Two directions are open, and both work:

1. **Write a few beats as a short line FOLLOWED BY a long one.** The shape then lives inside one beat, and
   the listener hears a change of pace without the film's structure moving at all.
2. **Let some sentences simply run much longer.** Duration FOLLOWS the text — `tts.py` is the only thing in
   this skill that writes `duration`, and it writes what it measured from the synthesised audio — so a
   longer line makes a longer beat, and the film's total length is recovered somewhere else.

### The correction this entry needed, recorded because the mistake is instructive

The first version of this section claimed the opposite of (2): that the sentence length *is* the beat
length, that the beat plan had fixed the duration two steps earlier, and that "vary the sentence rhythm"
was therefore advice the author could not follow. **That is backwards, and it shipped.** Nothing in the
skill sets a duration before TTS; `tts.py` measures the audio and writes the seconds it found. The text
decides the duration, not the other way round.

What produced the wrong conclusion was a real correlation read as a cause: duration CV 0.20 against
narration CV 0.23 with a flat 4.1 chars/second. Those numbers track **by construction** — the duration is
derived from the text — so they say nothing whatever about which one constrains the other. It was caught
by asking a different question ("does this hold for the html tier too?") and having to trace where
`duration` is actually written, which is the one check that settles it.

The lesson generalises past this file: **a correlation between two quantities where one is COMPUTED from
the other is not evidence of a constraint, and the direction of a causal claim has to be traced in the
code before it is written into advice.** Advice that tells someone their hands are tied, when they are not,
costs them the move they should have made.

