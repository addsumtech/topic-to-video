# RackFocus

**Identity:** two readings of one subject stand at different depths — the obvious one near, large and sharp, the one that matters further back, small and soft — and halfway through the lens racks: the near reading recedes (softer, dimmer, smaller, less saturated) while the far one comes into focus, a faint plane-of-focus glow travelling with it.

**Use when:** the beat TURNS — "not this, that": what it looks like versus what it is, the apparent cause versus the real one, where the viewer must still see what they are being turned away from. **Not when:** the two sides are equal alternatives to weigh (a versus register), or one phrase simply needs emphasis with nothing to turn from (`FocalIsolation`).

**Motion core:** holds on the near reading, then one eased rack 0.40–0.62, then holds on the far one. The optional pivot line fades in 0.44–0.60 between the two. Throughout, a slow lateral camera breath moves the near plane and the far plane at different rates (the far one about a third as much), which is both the life in the holds and the parallax that says the readings are at different depths.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `before` | the near reading — sharp first, then receding | fitted to its box (lower, wider): a few words set very large, a sentence comes down in size; omitted, the demo `What it looks like` prints |
| `after` | the far reading — soft first, then in focus | fitted to a smaller, higher box, so it is always set a little smaller than `before`; omitted, the demo `What it is` prints |
| `beforeNote` | a small dim line under the near reading | empty draws nothing; long copy wraps and the pair is re-centred in the zone to fit it |
| `afterNote` | a small dim line under the far reading | as `beforeNote` |
| `pivot` | a short spaced mono caps line between the two readings, in the accent | empty draws nothing; a word or two ("actually", "look again") names the turn as it happens. It sits in the gap between the readings, which is not sized for it — long copy wraps into them |

**Known traps:**
- The receding reading never leaves the frame — the focus floors keep it at reduced opacity and scale. Blurred out of existence it would be a cut, not a rack, and the beat would read as two unrelated frames.
- Hold–rack–hold measured as a still by the library's motion instrument (three quarters of the frames identical); the lateral breath fixed that. Shortening the holds instead would make the turn unreadable.
- The breath is bounded by the widest box's margin: at 9:16 the near reading has little side room, and an unbounded travel walked it off the frame.
- The pair used to be packed against the top, leaving dead frame below it at 9:16; it is now centred in the content zone.
- The sharp reading gets no CSS filter at all, on purpose, so it is not resampled; keep it that way if the focus code changes.

**Refuses:** an empty `before` or `after`.

**Reference:** `remotion/src/shots/RackFocus.tsx`
