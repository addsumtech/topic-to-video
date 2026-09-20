# SourceDeal

**Identity:** a document fills the left of the frame, then shrinks in place to the side (to the top in portrait) and keeps slowly scrolling, visibly still being read, while the conclusions drawn from it are dealt out one at a time as pills that land with a spring — each with a note underneath that darkens word by word as it is read, then clears for the next.

**Use when:** the claim is "here are the findings FROM THIS" — conclusions, takeaways or decisions that must visibly come from a source (a report, a spec, a page), dealt at the pace of narration. **Not when:** the points have no source to show (a list register), or there are more than four.

**Motion core:** the source parks (shrinks toward its own left or top edge) 0.06–0.24 and scrolls through whole periods for the whole clip, so the last frame matches the first. Conclusions are dealt across 0.26–0.92 at even intervals (0.66/*n* apart): each pill is visible almost at once and settles with a spring; its note darkens over most of its slot and fades out just before the next pill lands. One sentence is on the frame at a time.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the drawn document's title | the name of the source; omitted, the demo `Source` prints |
| `items` | the conclusions, one pill each | 1–4: fewer means a longer, calmer slot per conclusion. All pills share one type size and one width, set by the widest label, so one long label shrinks every pill. Omitted, three demo labels (`Quick start`, …) print |
| `notes` | a sentence under each pill, matched by position — no more notes than `items` | each darkens as it is read, then clears; long or CJK notes are reserved for by breaking them, and when the rows cannot fit all type scales down together. Empty: pills only |
| `doc` | the rows of the drawn document (a table surface), up to 7 | the film's own lines make the source real; rows the film does not fill (and an empty `doc`) draw placeholder bars |
| `src` | a captured page image to show as the source instead of the drawn one | needs `blocks`, `pageW` and `pageH` as well (the whole capture scripts/capture_page.py writes), or it refuses |
| `pageW` | the capture's width | sets the image's aspect inside the parked box |
| `pageH` | the capture's height | as `pageW` |
| `blocks` | the capture's layout boxes | must be non-empty for the capture to be used; the boxes themselves are not otherwise read here |

**Known traps:**
- The source used to slide off its own edge, hiding the title and the START of every line (measured: every `doc` row cut at 16:9 and 4:3). It now shrinks in place; don't bring the slide back.
- A Chinese label once ran 343px off the frame because the label and its pill were fitted to two different widths; both now use one measure.
- The pill text colour was an if/else with two identical branches — near-black on every surface, black on near-black on a dark DNA. It now takes the film's ink when that is readable on the pill.
- At the old spacing each note was fully legible for about three frames; the deal interval is derived from the window that exists, and four is the most that leaves a readable slot (~0.96s each at 5.8s; five would get ~0.77s).
- The last note also clears before the clip ends (by 0.98), so the settled frame shows the pills without notes.

**Refuses:** no `items`, more than four, or an empty one; more `notes` than `items`; more than seven `doc` rows (the drawn table shows seven); a `src` without `pageW`, `pageH` and `blocks`.

**Reference:** `remotion/src/shots/SourceDeal.tsx`
