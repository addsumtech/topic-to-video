# VoiceSignal

**Identity:** a mirrored spectrum bank, low frequencies in the tall middle and sibilants fluttering at the edges, driven by the beat's own narration audio. It rises on stressed syllables and drops to a thin line in the gaps between phrases, while a large phase label beneath names what is happening ("Listening…", "Working…") and brightens with the voice.

**Use when:** the beat is about something being said or heard (a voice interface, a live agent, a call, a moment of listening), so the speaking itself should be the picture. **Not when:** the words matter more than the act of speaking (a text register), or the beat has no narration to drive it.

**Motion core:** the bars follow the live audio frame by frame, so real pauses are flat on screen, with a floor so the line never disappears. The label switches with a hard cut at each phase's `at`. Over 0.78–0.95 the whole bank settles to about a third of its height, so the beat lands on a held tone instead of just stopping.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `phases` | the running account, `{at, label, state?}`, in time order, with `at` as a fraction of the beat (0–1) | one label is shown at a time: the latest phase whose `at` has passed, or the first phase before any has. The label is fitted to one line across 86% of the width, so a long one shrinks. `state: 'done'` paints it in the success ink, `'failed'` in a warning ink, and no state leaves it neutral. Leaving the demo in place prints `Listening…` / `Working…` / `Done ✓` |

**Known traps:**
- Its header once claimed it read the real narration while the bars were three sines of the frame number, so it never went quiet. It now reads the beat's mp3 through `runtime/voice`. Rendered standalone it uses that module's synthetic voice, so a preview is not the film's voice.
- The label used to turn success-green whenever the last phase began, so a closing 「连接失败」 or "Call dropped" showed in the colour of success. Colour now comes only from the film's `state`.
- An untimed phase used to fall back to `at ?? 0` and land at the start. A missing or out-of-range `at`, or phases out of order, now throw.
- Its geometry was once literal: 72 bars at a 22px pitch spanned 1562px, off both edges of a 1080-wide frame. It is now sized from the frame and the caption band, and a portrait frame gets fewer bars, not thinner ones.

**Refuses:** `phases` empty or not an array; a phase with no `label`; an `at` that is missing, not a number, or outside 0–1; a `state` other than `done`/`failed`; phases not in ascending `at` order.

**Reference:** `remotion/src/shots/VoiceSignal.tsx`
