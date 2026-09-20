# GazetteerEntry

**Identity:** a dictionary or gazetteer entry sets itself — headword, pronunciation, an accent rule, an italic etymology, then numbered senses arriving in order, the last set bolder as the claim, and a source note at the foot.

**Use when:** the word is the evidence — a place name that means "river crossing", a term whose root gives away what it was for. **Not when:** the beat is a fact about the thing rather than a reading of its name, or it needs more than four senses.

**Motion core:** headword 0.03–0.22, rule 0.16–0.34, pronunciation and etymology 0.24–0.42, each sense 0.13 after the last starting at 0.40, the note 0.80–0.94; then it holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `headword` | the entry's big serif word | a fixed fraction of the frame width, not fitted; the stack below assumes one line |
| `pronunciation` | the bracketed respelling, in mono | '' removes the line and closes the gap |
| `origin` | the etymology, in italic | '' removes it and closes the gap |
| `senses` | the numbered senses, in order | 0–4; the LAST is set bolder, larger and in full ink as the claim, the rest dim |
| `note` | a small mono source / cross-reference line at the foot | when present, the senses end above it |

**Known traps:**
- Senses used to be cut to four, so a film giving five lost the one it argued for and promoted its fourth into the claim's bold. More than four now throws — put the claim last.
- Lines were once placed at fractions of two different quantities and collided when the caption band grew (the pronunciation printed through the etymology). They are now a running sum of each line's height — but one line each, so a headword or sense long enough to wrap is not given the room.
- The no-DNA ground is a light paper tone, and the headword defaults to the placeholder 'headword'.

**Refuses:** `senses` that is not an array or has more than four entries.

**Reference:** `remotion/src/shots/GazetteerEntry.tsx`
