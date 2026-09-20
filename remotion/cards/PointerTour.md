# PointerTour

**Identity:** one application screen, larger than the frame, is shown whole; then a single continuous camera flies to each named place on it in turn while a cursor travels with it and leaves a click ripple on arrival, the rest of the page falling out of focus around the cursor.

**Use when:** several features live in ONE place and the claim is where they sit relative to each other — a product walkthrough where four cuts would make the viewer re-locate themselves four times. Also films a real captured page (`src` + `blocks`). **Not when:** the surfaces are separate products (use `PlatformSurfaces`), or there is only one thing to point at.

**Motion core:** the overview holds 0–0.12; the cursor fades in just before the tour starts. Each stop then takes 0.20 of the clip — 0.12 of travel (camera and cursor move together, eased) and a pause on arrival, with a click ripple over the first 0.055 of the pause. The depth-of-field graze arrives with the first move (about 0.08–0.19) and follows the cursor. Four stops end at 0.92; with fewer stops the last one holds to the end.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `screen` | the drawn window's title in its chrome | a product or workspace name; omitted, the demo `Workspace` prints |
| `items` | the card titles on the drawn screen, in reading order | the screen has six cards (3×2): up to six titles are printed, all at one fitted size, and the camera visits the FIRST FOUR — so 1–4 items is a full tour, 5–6 adds cards that are seen but never visited, and cards past your list show placeholder bars. Ignored when a capture is given. Omitted, six demo words (`Overview`, `Reports`, …) print |
| `nav` | the drawn screen's sidebar entries | background context; a few short words read as a real app; omitted, demo words print |
| `src` | a captured page image (from `scripts/capture_page.py`) to film instead of the drawn screen | turns the tour into a fly-over of a real page; must come with `blocks`, `pageW` and `pageH` |
| `pageW` | the captured page's width in pixels | must match the capture; without it the capture is not used |
| `pageH` | the captured page's height in pixels | as `pageW` |
| `blocks` | the capture's layout boxes (`x, y, w, h`, optional `tag`, `text`) | the tour picks up to four LEAF boxes wider than 14% of the page, biggest first, non-overlapping, then visits them in reading order; a page of tiny boxes has nothing to visit |

**Known traps:**
- The camera fills the content zone, not the frame: a full-frame page once put a white page under the caption band mid-beat and a dark ground a beat later, so the subtitle went white-on-white.
- The cursor's target used to jump to the next card the instant a move began, leaving it off-frame for the whole travel; it now runs on the same keyframe table as the lens. Don't retarget it by "the stop we have passed".
- Ranking capture boxes by area toured the containers (nav, main column), so the cursor pointed at white space; stops are leaves now. A capture with poor `blocks` still produces a poor route.
- Given `src` and `blocks` but no `pageW`/`pageH`, the shot does not throw — it silently draws the demo surface from `items` instead of the capture.
- The blurred copy of the page carries `data-echo` so the type gates don't count every label twice; keep it if the graze is touched.

**Refuses:** neither a capture nor any non-empty `items`; `src` without `blocks`; a capture where no box is at least 14% of the page wide.

**Reference:** `remotion/src/shots/PointerTour.tsx`
