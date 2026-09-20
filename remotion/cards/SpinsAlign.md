# SpinsAlign

**Identity:** a cloud of sixty small spin arrows points every which way; as a dashed B₀ field line fades in, a small minority of them turns to point up along it while the rest stay random, and a bold net-magnetisation arrow M₀ grows up from below the cloud.

**Use when:** the beat explains how a net signal emerges from a small EXCESS — spins aligning in B₀, or more generally a few parts agreeing against a disordered crowd (pass the film's own share). **Not when:** the beat is about one spin (use `SpinningProton`), about precession (use `LarmorPrecession`), or needs an exact ratio drawn to scale.

**Motion core:** the title eases up from faint over the first quarter; then one steady, un-eased alignment 0.15–0.75: the chosen arrows swing to vertical while the B₀ line, the M₀ arrow (growing) and the note all fade in on the same curve. It holds from 0.75.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `label` | the title across the top | fixed-size, not fitted: one line; long copy wraps; omitted, the demo `Spins align in the field` prints |
| `note` | the accent mono line under the cloud | fitted to the frame width; `''` draws nothing. Omitted, the demo `~3 in a million tip the balance → net signal` prints — a physics figure |
| `alignedFraction` | the share of the sixty drawn arrows that end up along B₀ | in (0, 1]; rounded to a whole number of arrows, at least one. Default 0.1 = six arrows, a visible small minority; 0.5 is half the cloud; 1 is every arrow up. Which arrows align is arbitrary; how many is the claim |
| `accent` | the aligned arrows and the note | plumbing — the DNA accent does not replace it |
| `accent2` | the B₀ field line | plumbing — the DNA's second accent does not replace it |

**Known traps:**
- The note used to be a hardwired physics figure, and the cloud contradicted it: about HALF the arrows turned up under a sentence saying three in a million do. The note is a prop now (still defaulting to that figure) and the share is `alignedFraction` — keep the two saying the same thing.
- A real physical excess (parts per million) cannot be drawn with sixty arrows; the default draws the claim's direction, a few against a crowd, not its magnitude.
- M₀'s length is fixed — it does not grow with `alignedFraction`, so it cannot show "more alignment, more signal".
- The title, B₀ and M₀ labels and the unaligned arrows are fixed colours; only the ground follows the DNA.

**Refuses:** an `alignedFraction` that is not a finite number in (0, 1].

**Reference:** `remotion/src/shots/SpinsAlign.tsx`
