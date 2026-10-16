# RangeSpheres

**Identity:** range spheres from several satellites meeting at the fix: three meet at exactly two points; four overshoot by one shared clock error and close on one point when it is taken off

**Use when:** a position is fixed from several measured distances — ranging, trilateration, an error every range shares.

**Motion core:** range legs swing out from each station, overshoot by one shared bracket, the bracket comes off and the arcs close on one point

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `bias` | 'bias': the shared bracket, as a fraction of the content zone's height | a drawing ratio |
| `biasLabel` | 'bias': what the shared bracket is (the phone's clock error) | — |
| `here` | 'bias': what is solved at the fix | — |
| `kicker` | a premise or a note, under the title | — |
| `limb` | the atmosphere's blue at Earth's limb (#hex) | — |
| `mode` | 'two' (three spheres meet at two points) or 'bias' (four ranges minus one shared error) | which argument the frame makes |
| `points` | 'two': the two crossings' names | the one on the ground first, then the one in space |
| `rangeLabel` | 'bias': what a leg measures (flight time × light speed) | — |
| `sat` | the satellites (the film's GpsSatellite); its props carry look and base pose | — |
| `sats` | the satellites' names, in order (names past the satellites drawn are not drawn) | — |
| `title` | the claim, in the title band | — |

**Known traps:**
- Promoted from the film gps, where it was judged against: caption hidden: (two) three circles visibly pass through the same two points, one on the ground; (bias) four arcs miss by the same blue stretch, then close. The first film that meets a trap here writes it down.

**Reference:** `remotion/src/shots/RangeSpheres.tsx`

**Measured:** 6.6% ink (clip median) · 76.9% footprint · 0.0026 motion. Measured on the register's own defaults.

**Review:** NOT critic-reviewed: the user waived the review of render 95df6db6b594.

**Provenance:** scientific. **Family:** S.
