# PageWrite

**Identity:** a real captured page is filmed through a 2D camera that opens close on its first body block and pulls out to the whole page, while the page's body blocks uncover in reading order behind a single accent caret, as if being written.

**Use when:** the claim is "this is the actual artefact" — a real document or page the product produced, captured with `scripts/capture_page.py` (texture plus layout boxes). **Not when:** there is no captured page (it refuses) — a drawn product window belongs to a UI register — or the page is to be panned across without its layout.

**Motion core:** the camera holds on the first body block over 0–0.10, then eases out until the whole page fits by 0.80 and holds there; the body blocks uncover top-to-bottom (then left-to-right), their starts spread evenly from 0.06 to 0.72 by the block count and each wipe (at most 0.16 long) overlapping the next, each mask retracting to the right; the caret rides the leading edge of the one block being written; 0.72–1 is the finished page.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `src` | the captured page texture | the whole premise; framed inside the content zone so the caption band keeps the film's ground |
| `pageW` | the captured page's width in its own pixels | the coordinate space of the texture and of every block; must match the capture |
| `pageH` | the captured page's height | as `pageW` |
| `bg` | the colour the masks are painted in — the page's own ground, recorded by the capture | the right ground makes text appear to arrive; any other colour turns every reveal into a bar sliding across the document |
| `blocks` | the capture's layout boxes `{x, y, w, h}` | only blocks wider than 18% of the page and at least 10px tall write; nav entries and dates are there from the start. A few blocks each get a slow, legible wipe; many share the same window, so each wipe gets shorter |

**Known traps:**
- A `bg` that is not the page's recorded ground makes the reveal a coloured bar travelling across the page (the header's reason for recording it).
- The texture is drawn at exactly `pageW` × `pageH`; leave the 1400 × 900 defaults on a capture of another size and the picture stretches while the boxes no longer sit on the text.
- The camera used to cover the whole frame, so a white page ran under the burned caption (white on white); it now fills only the content zone — don't expect the page to reach the bottom edge.
- Small blocks never animate by design; a page whose body sits in narrow columns may have little that writes.

**Refuses:** a missing or blank `src` (it names `scripts/capture_page.py`); `blocks` with no block large enough to count as body text.

**Reference:** `remotion/src/shots/PageWrite.tsx`
