# Narration Writing Guide

Narration lives in each slide's `narration` field in `storyboard.json`.
Edit it before running `tts.py`. The TTS engine reads it verbatim — **and the same text is
auto-derived into the on-screen subtitle**, so write words that are correct *both* spoken
and shown (see "Caption-safe spelling" below).

---

## Ground it in the material — don't narrate the slides
The slides are a *summary*; a good voice-over explains what they can't fit. Before writing,
work from the **comprehension brief** built in step 3 (from the paper/code/doc, or web
research when there's no material). For each slide ask: what is this *really* showing, why
does it matter, and what's the one point to land? Narrate that.

**Stay strictly faithful.** Every claim and number you speak must trace to the source. Don't
round "wins on average" up to "wins everywhere", don't invent a dataset size or a baseline
number, don't add a citation the source doesn't make. If you want to add a forward-looking
remark, flag it as your own ("a natural next step would be…"). The critic (step 5) will fail
the script on any unsupported claim — so get it right here.

## Write in the video's language (`meta.language`)
The narration — and therefore the subtitle — must be written in the language chosen in the
interview and recorded in `meta.language`. Write *natively*, not as a translation of the
English bullets: idiomatic phrasing for that language, correct technical terms, and natural
spoken rhythm. Keep proper nouns, model names, and units in their conventional form (often
Latin even inside CJK text, e.g. "用 PyTorch 训练" / "2D 分割"). The same caption-safe rules
below still apply — avoid raw math/markup regardless of language.

## Caption-safe spelling (the text is spoken AND shown)
Because the narration is also the subtitle, avoid spellings that fix pronunciation but look
wrong on screen: write **"2D"** not "two-D", **"19 datasets"** not "nineteen datasets",
**"ReG-SAM"** not "Reg dash Sam". Modern TTS reads "2D", "19", and hyphenated names
correctly, so you rarely need phonetic spelling — and when you do, prefer a form that still
reads cleanly as a caption. Never put raw math or markup in narration (`g_{Gi}`, `x^T`,
`\frac`) — it garbles both the speech and the caption; say it in words ("the query embedding").

---

## Rules for Spoken Narration

**Write for the ear, not the eye.**
- Never read slide bullets verbatim. Paraphrase and explain.
- One idea per sentence. Long sentences are harder to follow when heard.
- Address the viewer as "you": "Notice how you can…", "Here you'll see…"
- Expand every acronym on first use: "MRI — Magnetic Resonance Imaging".
- Use explicit transitions to bridge slides: "Next, let's look at…", "Now that we've covered X, we can…", "Building on that idea…"
- End each slide with a hook that pulls into the next: "In the next slide, you'll see how this applies in practice."

**Sound human, not AI** — this is what the audience feels first. Write like a sharp person
explaining the topic, not a model generating text: **vary the sentence rhythm** (mix short and
long — uniform measured sentences are the AI tell), **have a point of view** (lean in: "and that's
the catch"), stay **concrete** (the specific number/name over a generic abstraction), and cut every
machine tell — filler ("值得注意的是 / it's worth noting / in conclusion / let's dive in"),
over-hedging, balanced-triplet padding, and em-dash overuse. Read each line back: if it sounds like
a press release or a chatbot, rewrite it the way a person would say it out loud.

## Pacing Math

~140–160 words per minute ≈ ~2.5 words per second (English and other space-delimited
languages).

| Slide duration | Target word count |
|---|---|
| 8 s | ~20 words |
| 10 s | ~25 words |
| 15 s | ~37 words |
| 20 s | ~50 words |
| 30 s | ~75 words |

**CJK languages (Chinese / Japanese / Korean)** have no word spaces, so count **characters**,
not words. A natural spoken rate is ~4–6 characters per second — roughly: 8 s ≈ 35–45 chars,
15 s ≈ 70–90 chars, 30 s ≈ 140–180 chars. Treat these as a ceiling, not a target, and verify
against the real `duration` after TTS. (The critic's R2 word-count check is calibrated for
space-delimited text; for CJK, judge pacing by characters and by the rendered audio length.)

Count your words/characters before running TTS. The rendered clip length comes directly
from `ffprobe` timing of the audio file — there is no padding or trimming.

## BEFORE / AFTER Example

**Slide content (bullets on screen):**
> - Reconstruction: 4D flow MRI
> - Undersampling + compressed sensing
> - 10× speed-up vs. conventional

**BEFORE (bad — reads bullets):**
> "Reconstruction: 4D flow MRI. Undersampling plus compressed sensing. 10x speed-up versus conventional."

This sounds like someone reading a to-do list aloud. It's robotic and gives the
viewer nothing beyond what they can already read.

**AFTER (good — spoken style):**
> "4D flow MRI normally takes minutes — here we exploit undersampling and compressed sensing to reconstruct the same volume ten times faster. That speed-up is what makes real-time cardiac imaging practical for you."

Concrete benefit, second person, one sentence per idea. ~28 words ≈ ~11 s at 2.5 wps.

---

## Practical Checklist

- [ ] **Grounded in the material/brief — every claim & number traces to the source**
- [ ] **No invented facts; forward-looking asides flagged as your own**
- [ ] **Caption-safe spelling (2D not "two-D", 19 not "nineteen"); no raw math/markup**
- [ ] No bullet-list recitation
- [ ] Each sentence is one idea
- [ ] Transitions explicit ("Next…", "Now that…", "With that in mind…")
- [ ] Last sentence hooks into the next slide
- [ ] Word count matches target duration ±15%
- [ ] Acronyms expanded on first use across the full storyboard (not just per slide)
- [ ] Critic (step 5) returned PASS before TTS
