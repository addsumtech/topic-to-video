# TermSpace

**Identity:** up to four running consoles stand at hand-set positions in one 3D room, and the camera flies to each in turn, swinging the room round until that screen is square to the lens. The screen being faced types its status under a live caret while the ones behind hold theirs, and the shot closes by pulling back to show the whole room.

**Use when:** the claim is simultaneity: several things are all running at once in one place, and the film can say which are working and which are waiting (several agents, services or jobs side by side). **Not when:** the items are peers to compare or a list to read (a grid or list register), or they are places or cards rather than running processes (`SpatialSlides` is the non-console version of this camera).

**Motion core:** the tour runs over 0–0.74. The camera eases from screen to screen (easeInOutCubic per leg), backing off along each screen's own axis. The faced screen's border lights and its status types out behind a `→` and a blinking caret; the screens behind are dimmer and show a settled `●`. Every screen's name, and the faced screen's border and glow, are in that screen's own state colour — accent when working, dim when `waiting`. Over 0.74–0.93 the camera pulls back to a wide shot fitted so every screen sits inside the content box. The summary fades in over 0.80–0.95. Screens dim as they cross the frame edge instead of vanishing.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `screens` | the consoles, `{name, status, waiting?}`, in tour order, 1–4 | 2–4 screens make a tour with 1–3 legs. With one screen there is no travel, only the pull-back. `name` prints as `$ name` and `status` as the line under it. Each is set on one line, and every name shares one size, as does every status, fitted so the longest fits the screen width, so one long status shrinks them all. `waiting: true` makes the settled `●`, the name and (when faced) the border dim instead of the accent, meaning "this one is waiting on you". Leaving the demo in place prints `ingest` / `plan` / `run` with English statuses |
| `summary` | a closing line across the top, letter-spaced mono | arrives only with the pull-back. Empty draws nothing |

**Known traps:**
- The room has four hand-set positions. Past four screens the rest used to be dropped with no error (and entries with neither a name nor a status were silently filtered out); both now refuse.
- The name used to take the accent when faced, and after the pull-back the last screen visited stays "faced" — so a WAITING last screen ended with its name in the working colour beside its own grey dot. Names now follow their own state.
- The run-state glyph used to be a ✓ derived from the typewriter, so by the close every screen read "finished". The dim/accent `●` now carries the film's state (accent = working, dim = waiting). Keep that colour code consistent with any beat that states it in words. `waiting` was also once dropped by the row normaliser; it reaches the drawing now.
- Type is drawn flat over the 3D screens (glyph edge strength measured 91 flat vs 56 under `translateZ`) and carried onto each screen's plane by a 2D affine. It used to stay upright like a sticker while the windows tilted. Do not move the words into the stage.
- The camera once backed off along world z, which left the screen it had flown to 163px off-centre at 24°. It now steps back along the screen's own axis.
- The typing clock follows the tour, so the first screen starts almost fully typed, and a single screen never finishes typing until the pull-back begins.

**Refuses:** no `screens`, more than four, or an entry with neither a name nor a status.

**Reference:** `remotion/src/shots/TermSpace.tsx`
