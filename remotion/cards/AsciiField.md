# AsciiField

**Identity:** a field of amber monospace glyphs flickers across the frame. A bright scan-wave sweeps down it, lighting the rows it crosses, and one short message decodes character by character out of the noise at the centre of the field.

**Use when:** the beat resolves to one short word or phrase (a verdict, a status, a name) out of computation or noise. **Not when:** the message is a sentence — more than 32 characters is refused, and anything past a short phrase wraps into a block. Use `CodeRain` for falling-stream imagery.

**Motion core:** the glyphs re-roll every 3 frames throughout; the scan row travels from above the field to past its bottom over the clip; the message fades in 0.50–0.78, each character staggered behind the one before it. The stagger is laid out for the message's length, so the last character reaches full strength when the decode completes at 0.78, whatever the length. Nothing else moves.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `message` | the decoded text, 1–32 characters | fitted to 86% of the width and 92% of the height the field's centre allows without crossing the title band, up to about 0.194 of the short side, down to a 28px floor. It's monospace-aware (a Han glyph is two cells), so a short word is huge and a longer phrase wraps and shrinks |

**Known traps:**
- Only the first six or seven characters used to resolve (a fixed 0.12 step per character against a decode that stops at 1), and the fit sized the box for the whole string, so the visible part sat off-centre. The step is laid out for the length now. Once every character drew, a long message fitted to the field's full height showed its first line inside the title band (y = 40 at 16:9); it is fitted to the room about the field's centre now.
- `message` defaults to `DONE.`, which prints on any film that omits it.
- The field used to run to the bottom of the frame, and at 9:16 the type gate found 224 glyphs inside the caption band. It now stops above the band on a whole row.
- A long Chinese message once grew out of both ends of its box (369px at 1:1). It's now fitted in monospace cells, with the fitted width set on the box itself.
- **Dark world** (`@dark-world` in the shot). A glyph here is drawn by how much it GLOWS and the scan-wave's only action is to brighten the rows it crosses, so the register takes the film's ground only while that ground is DARK and keeps its own tube-dark when the film's is light. A light film gets one deliberately dark beat here, which the seam guard and the caption ink already handle.
- The glyphs and message are fixed amber and the scan glow is fixed mint; the ground follows the DNA while the DNA's ground is dark.

**Refuses:** a `message` with no visible character, or longer than 32 characters.

**Reference:** `remotion/src/shots/AsciiField.tsx`
