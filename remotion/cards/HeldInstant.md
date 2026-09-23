# HeldInstant

**Identity:** a playhead crosses a run of steps in one uncut move, and the shot's own clock is remapped so it crawls through the step the film marks and covers everything else briskly. What there was finally time to read appears under that step during the dwell, and stays — dimmer — afterwards.

**Use when:** a process went past and one moment inside it decided the outcome. "Most of this ran without anyone watching; this is where it turned." **Not when:** the claim is "this one matters" about things that are simply present — that is `FocalIsolation` (blur everything but the key item) or `RackFocus` (turn from one reading to another). Both say it in SPACE; this claim needs a RUN to point inside, and blur cannot say WHEN. Not when there is no run at all: two steps are a before and an after (`VersusSplit`).

**Motion core:** one clock, remapped. Everything on the frame reads `p = speedRamp(t, at, width, factor)` — the playhead, the step that lights up, the drawn track and the detail — so they cannot disagree about where the run is. The ramp is centred on the held step and its half-width is exactly half that step's share of the track, so the slow stretch IS the step and not a neighbourhood around it. The motion never stops and never jumps: stopping the playhead would be a cut in disguise, two static shots with a hold between them, and a viewer would read the marked step as a separate frame rather than as part of the same continuous thing.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `steps` | the run, in order — 3 to `MAX_STEPS` (7) | the whole thing the playhead crosses without cutting |
| `held` | the index of the moment the film is pointing at | **REQUIRED once a film passes its own `steps`.** Which moment it is IS the claim; a register that picks it has made the argument up. The demo keeps its own index so the preview still renders |
| `detail` | what there was finally time to read | set at a size that needs real seconds — which is what the ramp buys. It stays after the dwell, because once read it is known |
| `factor` | how much slower that stretch plays: `1` is no ramp, clamped to 20 | the FILM's claim, stated as a number it can say out loud: 4 means a quarter speed. Default 4 |
| `kicker` | the spaced label over the run | uppercase follows the DNA's `uppercaseLabels` |
| `note` | one line under the track, in the film's voice | where to say what the moment MEANT, which the frame shows but does not name |

**Known traps:**
- The dwell is MEASURED, not assumed: the register inverts `speedRamp` by bisection to find how many real seconds the held step gets, and refuses under `MIN_DWELL_S` (1.2s). A shot short enough makes even a fourfold ramp buy under a second, and a ramp that buys no reading time is decoration wearing a rhetorical name.
- The step labels are BOTTOM-anchored in CSS, never positioned from a computed line count. `wrapLines` is deliberately conservative and over-estimated the held label at two lines where the browser set one; a block positioned as `top − lines × px` then floats by exactly that error — measured 100px of daylight between the held label and its neighbours on the first render. Anchoring the bottom is immune to the estimator being wrong in either direction.
- The detail STAYS after the dwell instead of fading back out. Faded out it took the register's payoff off the settled frame — and the contact sheet, `shot_still_qa` and every reviewer read that frame. An argument only visible mid-clip is an argument nobody reviews.
- The held step is not accented until the playhead REACHES it. Before that it is a step like the others, because the film's point is that nobody could tell yet.

**Refuses:** fewer than 3 `steps`; more than `MAX_STEPS`; an empty step; a missing `held` once the film supplies its own steps; a `held` outside the list; and a dwell under `MIN_DWELL_S`, naming the measured seconds and the three levers (`factor`, fewer steps, a longer beat).

**Reference:** `remotion/src/shots/HeldInstant.tsx`
