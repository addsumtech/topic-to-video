# FrequencyEncode

**Identity:** a row of slice columns each gets its own wave, slow on the left to fast on the right; they sum into one measured signal below; a Fourier transform then splits that signal back into one equal peak per column.

**Use when:** position encoded as frequency — MRI frequency encoding, a whole axis read out as one signal. **Not when:** the columns carry different amounts of signal (the peaks are equal by construction), or the beat is the field tilting (GradientTilt) or phase encoding (PhaseEncodeStep).

**Motion core:** three stages — the columns take their pitches (0.06–0.34), they sum into the readout (0.36–0.56), the transform raises the peaks (0.58–0.90). The waves keep travelling for the whole clip.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `cols` | how many columns / frequencies | an integer 2–8; more columns are narrower and the fastest wave denser |
| `label` | the title above | 40px, not fitted |
| `accent` | alternate columns and peaks, the ramp arrow, the transform label | a hex literal, not the DNA |
| `accent2` | the other alternate columns and peaks | same |

**Known traps:**
- The peaks used to vary as `0.6 + 0.4·sin(i)`, "recovering" one column at twice another's strength and contradicting the equal-amplitude encoding above them. They are equal now; per-column amplitudes need a different register.
- The wave phase was once authored as `t * 6`, so the readout advanced less than one cycle over the whole clip; it runs in real seconds now.
- The stage labels are fixed English MRI vocabulary ("low freq", "high freq · readout gradient", "one measured signal", "one Fourier transform → columns").
- Omitting `label` prints 'Position becomes frequency'.

**Refuses:** `cols` that is not an integer from 2 to 8.

**Reference:** `remotion/src/shots/FrequencyEncode.tsx`
