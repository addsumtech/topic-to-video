# SpectrumPulse

**Identity:** a wordmark sits inside a circular spectrum; the ring's bars grow out and then move with the beat's own voice, longest at the top, while the wordmark and the core glow swell slightly on each syllable.

**Use when:** something is ALIVE and playing — a launch, a brand moment, a product that sounds like something, a title spoken over sound. **Not when:** the beat shows real audio analysis as evidence (the ring is styled, not a labelled spectrum), or it carries content beyond a name and a line.

**Motion core:** the ring reveals 0.04–0.40 as its bars grow out from the inner circle; the title fades in 0.30–0.55, the tagline 0.60–0.82. Throughout, bar lengths follow the voice (the film's narration; a synthetic voice in a standalone render), never dropping below a short corona, and the title scales slightly with the voice level.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the wordmark in the centre of the ring | fitted to the ring's inner width: a short name is set large, a long one comes down in size to stay inside the ring; omitted, the demo `On beat` prints |
| `tagline` | the spaced mono line under the wordmark | fitted to the same width, so long copy prints smaller; omitted, the demo `it moves with you` prints |
| `accent` | one of the two alternating bar colours | plumbing — the DNA accent replaces it |
| `accent2` | the other bar colour | plumbing — the DNA's second accent replaces it |

**Known traps:**
- The rig used to be fixed pixel sizes and ran 1200px wide at 9:16; it is now sized from the content zone and its outer radius is a hard limit — bar length is clamped, not multiplied (as a multiplier a loud syllable overshot the zone by 22%).
- The loud low end sits at 12 o'clock on purpose; reversed, the longest bars grow downward, read as melting and reach toward the caption band.
- The bar count follows the ring's circumference; a fixed count looked like a picket fence or a comb at other sizes.
- **`@dark-world`.** The subject is emitted light — a spectrum radiating out of a wordmark, every bar a drop-shadowed glow — and light only reads against a night, so inverting it would be a different picture rather than a repair. The ring takes the film's ground while that ground is DARK (all eight presets) and keeps its own `#080611` when the film's is paper. It used to take `dna.bg` whatever it was, which painted the gradient from a dark purple centre out to WHITE — a grey sludge with the wordmark on the one dark patch left (measured median 1.72:1 over 92% of its marks). A light film therefore gets one deliberately dark beat here, which `SHOT_LUMA`, the seam guard and the caption ink already handle.
- The type is fixed white and lilac for the dark centre the register paints, and does not take the DNA's `fg`/`dim` — which is only safe BECAUSE of the line above. The accents do follow the film, and are lifted toward their own tint if the film's picks are too dark to read on this night (a light film chooses them for paper).

**Reference:** `remotion/src/shots/SpectrumPulse.tsx`
