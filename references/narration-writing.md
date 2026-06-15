# Narration Writing Guide

Narration lives in each slide's `narration` field in `storyboard.json`.
Edit it before running `tts.py`. The TTS engine reads it verbatim.

---

## Rules for Spoken Narration

**Write for the ear, not the eye.**
- Never read slide bullets verbatim. Paraphrase and explain.
- One idea per sentence. Long sentences are harder to follow when heard.
- Address the viewer as "you": "Notice how you can…", "Here you'll see…"
- Expand every acronym on first use: "MRI — Magnetic Resonance Imaging".
- Use explicit transitions to bridge slides: "Next, let's look at…", "Now that we've covered X, we can…", "Building on that idea…"
- End each slide with a hook that pulls into the next: "In the next slide, you'll see how this applies in practice."

## Pacing Math

~140–160 words per minute ≈ ~2.5 words per second.

| Slide duration | Target word count |
|---|---|
| 8 s | ~20 words |
| 10 s | ~25 words |
| 15 s | ~37 words |
| 20 s | ~50 words |
| 30 s | ~75 words |

Count your words before running TTS. The rendered clip length comes directly
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

- [ ] No bullet-list recitation
- [ ] Each sentence is one idea
- [ ] Transitions explicit ("Next…", "Now that…", "With that in mind…")
- [ ] Last sentence hooks into the next slide
- [ ] Word count matches target duration ±15%
- [ ] Acronyms expanded on first use across the full storyboard (not just per slide)
