# FrequencyEncode

**Identity:** a row of slice columns each gets its own wave, slow on the left to fast on the right; they sum into one measured signal below; a Fourier transform then splits that signal back into one equal peak per column.

**Use when:** position encoded as frequency — MRI frequency encoding, a whole axis read out as one signal. **Not when:** the columns carry different amounts of signal (the peaks are equal by construction), or the beat is the field tilting (GradientTilt) or phase encoding (PhaseEncodeStep).

**Motion core:** three stages — the columns take their pitches (0.06–0.34), they sum into the readout (0.36–0.56), the transform raises the peaks (0.58–0.90). The waves keep travelling for the whole clip.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `cols` | how many columns / frequencies | an integer 2–8; more columns are narrower and the fastest wave denser |
| `label` | the title above | 40px, not fitted |
| `accent` | alternate columns and peaks, the ramp arrow, the transform label | the film's `accent` unless a hex overrides it |
| `accent2` | the other alternate columns and peaks | the film's `accent2`, same rule |

**Known traps:**
- The peaks used to vary as `0.6 + 0.4·sin(i)`, "recovering" one column at twice another's strength and contradicting the equal-amplitude encoding above them. They are equal now; per-column amplitudes need a different register.
- The wave phase was once authored as `t * 6`, so the readout advanced less than one cycle over the whole clip; it runs in real seconds now.
- The stage labels are fixed English MRI vocabulary ("low freq", "high freq · readout gradient", "one measured signal", "one Fourier transform → columns").
- Omitting `label` prints 'Position becomes frequency'.
- Every mark outside the column boxes was a literal picked for a near-black ground, so on a warm-white film 42.3% of this register's marks measured under 3:1 with a connected hole 1.15% of the frame: the title, both axis ends, "one measured signal", the summed readout CURVE and every bar of the spectrum went, leaving seven dark boxes on paper and no data layer at all. A curve and a bar are claims as much as a word is, so all of it reads from the DNA now (`fg` for the title and the readout, `fg`→`dim` for the stage label, `dim` for the axis ends, `accent`/`accent2` for the bars).
- The seven COLUMN BOXES are not ink and do not follow the ground: each is a scope showing one column's oscillation, so they keep their own night, and a trace that would not clear 3:1 against that night is lifted until it does. On a light film the register is seven dark scopes on paper by design.

**Refuses:** `cols` that is not an integer from 2 to 8.

**Reference:** `remotion/src/shots/FrequencyEncode.tsx`
