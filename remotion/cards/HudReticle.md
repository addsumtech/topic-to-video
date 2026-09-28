# HudReticle

**Identity:** a sci-fi targeting HUD. Corner brackets snap in around a name at the centre, a dashed scan ring spins, and status readouts slide in on the left. Then the system locks: the ring goes solid and changes colour, and "SCANNING…" becomes "● LOCKED".

**Use when:** targeting, analysing, "locked on": the moment a system finds or identifies its subject. **Not when:** the readouts would carry statistics (they are meant to be qualitative status words), or the beat is MR gradient encoding (GradientTilt was built to replace a reticle there).

**Motion core:** the title fades in over 0.03–0.16. Brackets, grid and crosshair snap in over 0.1–0.4. The ring rotates for the whole clip. The scan label fades in over 0.4–0.6. Readouts slide in one at a time from 0.42, each over 0.18, 0.1 apart for up to three and closer for more, so the last is always in by 0.84 (just before the settled frame at 0.86). At 0.76 it locks: the ring turns solid in the second accent, and the lock label comes in over 0.76–0.9.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `target` | the name at the centre, up to 84px (scaled with the ring) | fitted and balanced inside the ring's inner circle: a short name keeps 84px, a long one wraps into a block that stays inside the ring |
| `object` | a thing the FILM drew (an object from its workshop), locked onto in the ring — the name moves under it, smaller | what is being identified, SHOWN rather than named; its t runs 0→1 while the system scans, 0.1–0.6, whole well before the lock at 0.76 |
| `readouts` | status lines, each with an accent rule, 0–6 | a column left of the ring where it can hold the longest line at 20px or more (16:9); otherwise a block centred under the ring, with the ring scaled so both fit the content zone (9:16, 1:1, 4:3). 2–4 short status words read best |
| `title` | small spaced mono caps at the top | a quiet heading for the scan |
| `scanLabel` | the state word under the target before the lock | lets a film say "scanning" in its own language |
| `lockLabel` | the state word after the lock | the same, for "locked" |

**Known traps:**
- Leaving the props unset prints demo copy: `WorkBuddy`, the readouts `SIGNAL · strong / SCOPE · full workspace / STATUS · ready`, and `Locking on`.
- The geometry was fixed pixels composed for 1920 wide, so on a 1080-wide frame the readouts sat on the ring and ran through the target's name. It reflows now (column beside the ring, or readouts under a scaled ring). The faint grid also stops at the content zone instead of running into the caption band.
- Readout timing was a fixed 0.1 per line, so a fourth readout was still fading on the settled frame and a seventh never appeared. It is laid out for the count now.
- The scan ring's `drop-shadow(0 0 8px)` and the target's 40px text bloom are lit-on-black effects: on a light film they spread the accent into a halo that is neither the ring nor the paper. Measured 8.3% of the register's ink under 3:1 on a warm-white ground, in one ring-shaped region 0.75% of the frame, while the ring's own stroke reads (median mark 5.33:1). Both are drawn only while the film's ground is dark now. The faint grid (0.12) and the inner dashed ring (0.3) are unchanged — they are as quiet on one ground as the other.
- With `object`, the name is set under the object inside the ring at up to 40px (scaled): a long name wraps, balanced, and stays inside the ring.
- An `object` with its own `META.aspect` is fit into its box by LETTERBOXING, not stretched: a wide object becomes a band in the upper part of the ring, with blank sheet above and below it inside the same box — it does not grow to fill the box vertically.

**Refuses:** more than six `readouts`, or an empty readout.

**Reference:** `remotion/src/shots/HudReticle.tsx`
