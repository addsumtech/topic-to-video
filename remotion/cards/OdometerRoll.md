# OdometerRoll

**Identity:** one big figure where every digit is a mechanical reel that spins two full turns and snaps onto its digit, column after column, each with a small pulse as it locks; a spaced label sits above and an accent underline draws beneath.

**Use when:** the beat's payoff is ONE sourced number and it should land physically. **Not when:** there are several numbers to compare (use a comparison register), the figure is long (each digit is a wide reel), or the number is not sourced — then at least set `roll: false`.

**Motion core:** the label rises in over 0.05–0.22; digit k rolls over 0.06 + 0.03·k to 0.26 + 0.03·k with a quick-out ease and pulses briefly when it locks; the underline draws over 0.55–0.85. With `roll: false` every digit is locked from the first frame and nothing pulses.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `value` | the figure, as a string, split character by character | every digit becomes a fixed 150px reel; commas, points, `+` and other non-digits stand as static glyphs in the DNA's ink. There is no fit-to-width, so a long figure runs off narrow frames |
| `label` | the line above the figure | always uppercased and widely tracked in a fixed grey; a few words read as a dashboard caption |
| `unit` | a suffix after the digits, in the accent | `%`, `ms`, `×` — large and coloured; empty draws nothing |
| `roll` | whether the reels spin | `true` (default) is the register's character; `false` locks the sourced figure from frame one so no parade of other digits flashes past |

**Known traps:**
- Omitting `value` / `label` prints an invented statistic: `1,240` "active teams this week".
- Digits used to land late (the sixth at t=0.87), so the mid-scene frame the delivery gate captures showed a sourced 19.3–28.9 as "19.3–16.5"; they now land early, but every extra digit still lands 0.03 later.
- The `+` on a `100+` used to be hard white and vanished on a light DNA (a viewer read "exactly 100"); non-digits now take the DNA's ink — keep qualifiers inside `value` rather than in the label.
- With `roll: false` the landing pulse used to amplify instead of decay and the cells overlapped; only a real landing pulses now.

**Reference:** `remotion/src/shots/OdometerRoll.tsx`
