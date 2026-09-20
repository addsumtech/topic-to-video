# AuroraFlow

**Identity:** five large, blurred colour bodies drift and blend over a dark ground like an aurora, while one or a few lines of heavy white type rise in, one after another, at the centre of the content zone.

**Use when:** the beat is a short, confident statement (a tagline, a promise, a closing line) that wants a premium, gradient-forward mood. **Not when:** the copy is long, or it's a list of things that must read as different (the lines are one stacked statement).

**Motion core:** the aurora drifts continuously (sine and cosine of the frame) under a fixed edge darkening; line i rises 40px and fades in over 0.16 + i·0.16 → +0.34. Two lines land by about 0.66.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `lines` | the stacked lines of type, top to bottom | the size starts at 150px and steps down 2px at a time until the wrapped stack fits the content zone. One or two short lines stay huge; more or longer lines set everything smaller together |

**Known traps:**
- Omitting `lines` prints the demo `Your AI team.` / `On your machine.`
- The lines enter 0.16 apart. A fifth is still settling on the last frame, a sixth is barely in, and a seventh never appears.
- A flat 150px Chinese stack, centred on the frame, landed 306px inside the caption band at 1:1. It's now fitted and centred on the content zone.
- The fit stops at a 24px floor. If the stack still doesn't fit at 24px, it draws anyway.
- The five aurora hues (blue, violet, pink, teal, amber) and the white type are fixed; only the ground under them follows the DNA.

**Reference:** `remotion/src/shots/AuroraFlow.tsx`
