# TimelineTravel

**Identity:** a horizontal rail wider than the frame, which the camera travels along left to right. A progress fill follows the lens, and each dated milestone pops its time and label (alternating above and below the rail) and lights up as the lens reaches it.

**Use when:** the beat is a sequence of dated or timed steps (a roadmap, a day's run of events, a journey) and the passage of time is the point. **Not when:** there are more than six stops (it refuses), the steps are not ordered in time (a list register), or the stops need comparing as quantities. One or two stops work but barely travel.

**Motion core:** the camera pans over 0.10–0.92 (easeInOutCubic), from where the frame's left edge sits on the world's start to the LAST stop, at every aspect; a rail too short to travel holds on its end rather than panning backwards. On the settled frame (0.86) the lens is under 6px short of the last stop, which is lit and labelled. A stop's label pops up with an overshoot as the lens comes within 260px of it, and its node fills with the accent, rings and scales up once the lens reaches it. The rail's accent fill grows with the camera. The world bleeds past both frame edges on purpose.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `nodes` | the stops, `{time, label}`, in order, 1–6 | every stop sits a fixed 720px further along the rail, so more stops mean a longer world and a faster pan; the shot ends with the last stop at the frame's centre and the right half of a wide frame empty. `time` prints in 40px above a 46px `label` in a 380px column; a long label wraps. Above-rail labels have 200px of room, so one that wraps to three lines reaches the rail. Leaving the demo in place prints a 9:00–9:45 English workday (`You brief it` … `Shipped`) |

**Known traps:**
- The pan used to end with the lens W/2 short of the world's right edge, so at 1920 wide the final stop's label never appeared and its node never lit (it ended 440px right of the lens); with one or two stops the camera panned backwards. The travel now ends on the last stop at every aspect.
- The geometry is fixed pixels (720px pitch, 380px label columns, 40/46px type) and does not scale with the frame. At 9:16 about one and a half stops are in view at a time.

**Refuses:** no `nodes`, more than six, or a stop without a `label`.

**Reference:** `remotion/src/shots/TimelineTravel.tsx`
