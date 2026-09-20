# MaterialHero

**Identity:** a real WebGL scene seen from above — one turned-metal arc per part flies in along its own radius and seats into a single closed ring under a sweeping warm rake light, each arc marked by a thin glowing inlay and labelled just outside its metal, with the name of the whole set in the ring's hole.

**Use when:** the claim is "many pieces, ONE thing" — a product or system named as its 1–6 parts closing into one whole, in a premium hero-reveal register. **Not when:** the parts have sizes (use MadeOf), an order (use a list or flow register), or there are more than six.

**Motion core:** arcs seat one after another with a slight overshoot — arc i over 0.10 + 0.4·i/n to 0.40 + 0.4·i/n — and each label fades in only once its arc is nearly home; the title fades in over 0.55–0.75 and the note over 0.74–0.90. Throughout, the ring yaws gently back and forth (a settle, not a spin) and the warm light sweeps across the metal, so it never fully stops.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the name of the whole thing, in the ring's hole | fitted on one line to the hole's width in this frame, so a short name fills the hole and a sentence shrinks toward caption size |
| `items` | one arc of the ring each, with its label outside the arc | 1 part is one near-closed ring; 6 is six short arcs. Every arc is the same metal — only a thin inlay tone tells them apart. Labels are balanced in a box 15% of the frame wide and clamped inside the frame and above the caption band |
| `note` | a dim line under the title, inside the hole | a short supporting line; wraps within about a third of the frame width |

**Known traps:**
- Omitting `title` / `items` prints demo copy: "One tool. Your whole team." over Docs, Chat, Tasks, Code, Data, Calls.
- The arcs are deliberately one material — six dyed hues turned the object into a pie chart; the inlay is a mark to tell parts apart, not a claim about them.
- It was rebuilt from a torus knot that took only a `title` and argued nothing; the ring now IS the parts, so don't feed it filler items to make it look fuller.
- Labels of the arcs nearest the lens are clamped above the caption band, so a long (e.g. three-line Chinese) label there can sit crowded against its arc — at 16:9 the two nearest labels print on the metal itself, and the ring's near arc reaches down into the caption band.

**Refuses:** no `items`; more than six (parts are told apart only by their inlay tone, from a six-tone palette — a seventh would wear the first part's tone); an empty entry.

**Reference:** `remotion/src/shots/MaterialHero.tsx`
