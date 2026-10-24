# EquationMorph

**Identity:** the beat's equation WRITTEN on — each glyph's outline drawn, then filled, staggered through the expression (Manim's Write) — then carried through its next forms the way a derivation is worked on a board: the marks two forms share travel to their new places, the marks a step consumes shrink away and the ones it introduces grow in, a constant that changes sides travels OVER the equals sign on an arc, and every form's relation sign sits on one vertical. At the end the term the narration is about is circled, swells once and keeps the accent; its label takes the label line under the equation. Real typeset maths: the film's TeX, MathJax 3.2.2's TeX fonts, drawn from the glyph outlines.

**Use when:** the next form IS the last one rearranged — solving, simplifying, substituting values, deriving a result — or one formula with a term to point at. Hide the caption and the motion still says which parts survived the step (they slid), which were consumed (they shrank away) and which the step introduced (they grew in). **Not when:** the content is a quantity's history (a chart), several unrelated formulas (several beats), or prose that merely mentions a formula.

**Motion core:** form 1 written over t 0.05–0.22 (outline draw-on 0–60% of each glyph's window, fill 35–90%, outline fades once the fill holds — the settled frame is the plain typeset equation). Each later form gets an equal slot to t 0.80: held for 42% (the form is read), transformed over the rest (TransformMatchingTex in `runtime/mathCore`: named terms matched first, then the longest run of shared marks in reading order, ties broken by travel measured where the glyphs are drawn; leaving glyphs fade linearly over the first 65% while shrinking, arriving ones over the last 65% while growing, travellers in between with a 14% LaggedStart). The step labels flip as each form lands. Highlight over t 0.81–0.92: a rounded frame draws on round the term, the term swells 16% and settles in the accent, a leader drops to its label. A `live` slot runs its number over the stretch after the last form lands (ease-out).

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `kicker` | a small label over the equation | context for the derivation, never a second claim |
| `steps` | 1–4 forms `{tex, label}`, in order | `\class{name}{…}` names a term — the same name in two forms is matched as the same term; two DIFFERENT names never trade a glyph (the square's exponent 2 will not fly into a ±2 the film named as another term). Label every form or none |
| `highlight` | `{term, label}` — a class of the LAST form, and what it is | the frame + swell + accent; the label takes the label line |
| `live` | `{term, from, to}` — a `\class{live…}{00.0}` slot in the last form, and the film's two values | the settled frame prints `to` exactly; the template must be as wide as the widest value (wider throws) |
| `align` | `equals` (default) or `center` | `equals` keeps every relation sign on one vertical when the frame allows, so `=` never moves; else each form is centred |
| `title`, `kicker` | the heading | the demo's title and highlight belong to the demo's forms: a film's own steps get neither unless it writes them |

**Known traps:**
- The first render's transforms faded out in the first half and in over the second: the middle frame held only the travellers — "x +  2  = 0" — an equation with holes in it. Then smooth-eased fades were just as disjoint (0.3% and 1% opacity at p = 0.5). Both fades now run linearly over overlapping 65% windows.
- Travel was first measured as a share of each form's own width, and `=` — which sits on one vertical under equals alignment — was sent on the arc while the `3` that really crossed it slid straight through. Travel is measured in frame px from the placements, and who takes the arc is decided by GEOMETRY: a pair whose left-to-right order flips against another arcs (the further traveller), whichever phase matched it — a term the film named in both forms (`\class{b}{b}` in `a + b = c → a = c − b`) still changes sides.
- At 9:16 the label line sat a third of the screen below its equation: the equation and its label are one group, centred in the room under the heading.
- A form too wide for the frame is REFUSED below 4% of the short side an em (43 px at 1080) rather than shrunk until unreadable — split the derivation or use `aligned`.
- CJK inside the TeX is refused by the typesetter (it would be set in whatever face the browser finds); words go in `label`.

**Refuses:** no forms or more than 4; a form with no `tex`; labels on some forms but not others; a `highlight.term` / `live.term` that is not a class of the last form; a `live` value that is not one plain number, or wider than its slot; TeX nobody typeset (the render cancels naming `scripts/mathtex.py`); TeX MathJax cannot parse (MathJax's message, at prep).

**Reference:** `remotion/src/shots/EquationMorph.tsx` · runtime `mathMorph` / `mathCore`

**Measured:** 4.4% ink (clip median) · 35.1% footprint · 0.0009 motion · reach 0.567 (product DNA, the demo at its own 11 s). QUIET by construction — the library's floors are 0.0037 motion / 12% ink: a derivation is held to be read. Intercut with a dense register.

**Review:** NOT critic-reviewed — built and looked at by its author: settled and mid-transform frames at 16:9 (Latin demo), 9:16 (Chinese labels, a film's own TeX fetched from its public dir, a live number), 1:1.

**Provenance:** scientific. **Family:** MA.
