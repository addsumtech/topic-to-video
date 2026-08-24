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
