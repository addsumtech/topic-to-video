# GlowPick

**Identity:** a working app surface tilts up into view; a pill of light hops across it toward one card, lands on it, and draws that card's outline, which cools from a hot glow into a thin accent border while the rest of the surface dims around it.

**Use when:** "look here": one element of a product interface matters, and the viewer should see it in its place without cutting away. **Not when:** several features need a tour (PointerTour), the thing to point at is not a card (tables, forms and charts throw), or the emphasis is a phrase rather than UI (FocalIsolation).

**Motion core:** short on purpose (96 frames, 3.2 s). The surface rises from a tilted, enlarged pose over 0–0.12 and keeps a slight drift. The light switches on at about 0.03–0.09 and hops in three steps to the target by 0.44, then fades out by 0.50. The outline draws from where the light landed (0.46–0.66) and thins into a border (0.66–0.84). The dim comes in over 0.50–0.68 and partly lifts over 0.84–0.97. The note fades in over 0.70–0.86.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `screen` | the heading above the surface and the window's own title | fitted to one line in 60% of the width, so a long name gets smaller instead of wrapping |
| `items` | card titles on a fixed 3×2 grid | 1–6 titles. Cards past the list draw as blank placeholders. All titles share one size, so one long title shrinks every card's type |
| `nav` | the sidebar entries | up to six. Left unset, the sidebar prints the demo `Home / Overview / Runs / Sources / Team / Settings` |
| `page` | which surface page is drawn | only `'cards'` works. Every other page throws, because only the cards page gives the light an element to land on |
| `series` | chart numbers | cannot be used here: passing it throws instead of dropping the numbers without a word |
| `target` | index into `items` of the card the light picks | the whole claim. It must be a real item. The light's path always ends on it |
| `note` | one line under the surface, landing after the border | when set, the surface shrinks to make room. The block is fitted, so long copy shrinks rather than overflowing |

**Known traps:**
- `target` used to default to 4, and a film with three items got the border on a blank placeholder card. It now has no default for a film.
- On table, form and chart pages the border was drawn across the middle of rows, which is why those pages now throw.
- Leaving out `items` gives the demo cards and the demo pick (`Access`). Leaving out `screen` or `nav` prints demo labels even with a film's items.
- Stretched to five seconds, it measured among the quietest registers in the library. The density of the four moves is the effect, so don't lengthen the clip.
- Under the surface's `perspective`, a blend mode comes out grey. The light is a solid core with a box-shadow glow, and it has to stay that way if restyled.

**Refuses:** no items; more than 6 items or more than 6 nav entries; an empty item; any `page` other than `'cards'`; any `series`; `items` passed without a `target`; a `target` that is not an integer index into `items`.

**Reference:** `remotion/src/shots/GlowPick.tsx`
