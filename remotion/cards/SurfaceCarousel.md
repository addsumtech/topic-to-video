# SurfaceCarousel

**Identity:** the product's own app windows (window chrome, a real sidebar, the film's labels) queue up in a corridor and step past in three beats. The centred window is sharp under its name pill; its neighbours sit at the frame edges, scaled down, sunk off the axis, darkened and blurred.

**Use when:** the beat is about one product with several screens, and the claim is that they are the same product seen one at a time. Four full-screen cuts would make the viewer re-locate themselves four times. **Not when:** there are more than four surfaces, the screens belong to different products (a comparison register), or one screen needs close reading.

**Motion core:** the corridor opens already settling from a small offset (0–0.19). Then it takes three eased steps: at 0.20 (run 0.185, with 15% of that travel arriving late on a slower tail to 0.48), at 0.483 and at 0.688 (0.15 each). Each step brings the next surface in `items` from the left to centre stage. In portrait (W/H < 0.95) the corridor turns vertical and the next surface comes from above. Pills sink faster than their windows as they recede. It holds after ~0.84.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | the surface names, one pill and window each, in the order they reach centre stage | 1–4 names. All pills share one text size, fitted so the longest name fits about a quarter of the width, so one long name shrinks every pill. Leaving the demo in place prints `Overview · Reports · Records · Settings` with the demo's own page rotation |
| `nav` | the sidebar entries on every window that has no `nav` of its own | the product's real sections. Leaving the demo in place prints `Home · Overview · Reports · Records · Team · Settings` in every window's sidebar |
| `surfaces` | what each window shows, paired with `items` by index: `{page?, items?, nav?, series?}` | `page` is `cards`, `chart`, `table` or `form`. A surface without `page` gets `chart` only if it has a real numeric `series` (plotted exactly as given), and otherwise every surface gets the same neutral `cards` page. Its `items` are the card titles, table rows or form labels. Entries past the length of `items` are ignored |

**Known traps:**
- Pages used to be assigned by position (second surface a chart, third a table, fourth a form), so a film naming 「首页 · 订单 · 设置」 drew 订单 as a settings form. A surface now shows only the page it is given. If the screens really look different, say so with `page`.
- Past four surfaces it throws. The corridor steps only three times, so a fifth would only ever be a blurred sliver at the edge. It used to keep six in silence. Split the surfaces across two beats.
- A blank name throws. It used to be skipped, which slid every later `surfaces[i]` under the wrong name. `surfaces` pairs with `items` strictly by index.
- With fewer than four surfaces the ring still wraps through three steps, so surfaces come round to centre stage again. With one surface, the arithmetic slides the same window out one side and back in the other, inside the frame.

**Refuses:** `items` empty or not an array; more than 4 `items`; a blank name in `items`.

**Reference:** `remotion/src/shots/SurfaceCarousel.tsx`
