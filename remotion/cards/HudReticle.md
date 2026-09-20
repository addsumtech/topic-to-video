# HudReticle

**Identity:** a sci-fi targeting HUD. Corner brackets snap in around a name at the centre, a dashed scan ring spins, and status readouts slide in on the left. Then the system locks: the ring goes solid and changes colour, and "SCANNING…" becomes "● LOCKED".

**Use when:** targeting, analysing, "locked on": the moment a system finds or identifies its subject. **Not when:** the readouts would carry statistics (they are meant to be qualitative status words), or the beat is MR gradient encoding (GradientTilt was built to replace a reticle there).

**Motion core:** the title fades in over 0.03–0.16. Brackets, grid and crosshair snap in over 0.1–0.4. The ring rotates for the whole clip. The scan label fades in over 0.4–0.6. Readouts slide in one at a time from 0.42, each over 0.18, 0.1 apart for up to three and closer for more, so the last is always in by 0.84 (just before the settled frame at 0.86). At 0.76 it locks: the ring turns solid in the second accent, and the lock label comes in over 0.76–0.9.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `target` | the name at the centre, up to 84px (scaled with the ring) | fitted and balanced inside the ring's inner circle: a short name keeps 84px, a long one wraps into a block that stays inside the ring |
| `readouts` | status lines, each with an accent rule, 0–6 | a column left of the ring where it can hold the longest line at 20px or more (16:9); otherwise a block centred under the ring, with the ring scaled so both fit the content zone (9:16, 1:1, 4:3). 2–4 short status words read best |
| `title` | small spaced mono caps at the top | a quiet heading for the scan |
| `scanLabel` | the state word under the target before the lock | lets a film say "scanning" in its own language |
| `lockLabel` | the state word after the lock | the same, for "locked" |

**Known traps:**
- Leaving the props unset prints demo copy: `WorkBuddy`, the readouts `SIGNAL · strong / SCOPE · full workspace / STATUS · ready`, and `Locking on`.
- The geometry was fixed pixels composed for 1920 wide, so on a 1080-wide frame the readouts sat on the ring and ran through the target's name. It reflows now (column beside the ring, or readouts under a scaled ring). The faint grid also stops at the content zone instead of running into the caption band.
- Readout timing was a fixed 0.1 per line, so a fourth readout was still fading on the settled frame and a seventh never appeared. It is laid out for the count now.

**Refuses:** more than six `readouts`, or an empty readout.

**Reference:** `remotion/src/shots/HudReticle.tsx`
