# PourSync

**Identity:** a physical thing and the phone that mirrors it, live, on one clock: on one side (above, on a tall frame) the thing the film drew doing what it measures, on the other (below) a phone showing the screen the film drew for it, and between them a link with readings running from the thing to the phone. Both objects are handed the same clock and the same `shared` props, so the value they draw is one value shown twice — the frame cannot show them disagreeing.

**Use when:** what happens HERE shows up THERE, as it happens — a scale and its app, a sensor and its dashboard, a meter and its readout — and the film has drawn both ends. **Not when:** the beat is the app on its own (`DeviceDemo`, `DeviceHero`) or the thing on its own (`ObjectStage`, `TechnicalPlate` with `art`).

**Motion core:** both objects run on the beat's own clock from its first frame; the link draws on over 0.02–0.08 and, inside `linkWhen`, readings pulse along it from the thing to the phone, where a ring answers each arrival.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `thing` | the physical thing that measures — `{"id": …, "props": …}`, an object the film drew | required in a film; drawn as large as the room beside (above) the phone allows |
| `screen` | what the phone shows — an object the film drew for a screen | required in a film; set on the device layer's own phone (`runtime/device`) |
| `shared` | props merged into BOTH objects' own: the one value they both draw | put the reading or the state here, never in one object's props, or the two can disagree |
| `linkFrom` | where the link leaves the thing, `{x, y}` in fractions of its box | put it on the thing's antenna or port; default the middle of its right edge |
| `linkWhen` | when readings run along the link, `{from, to}` on the beat's clock | match it to the window the objects themselves move in; default 0.05–0.95 |
| `linkLabel` | the link's name, set above its arc | short: one line over the arc's middle |
| `kicker` | a small spaced label in the title band | one line |
| `title` | the claim, in the title band | fitted to 70% of the width (86% on a tall frame), one line |
| `look` | the phone's look: `flat`, `real` or `screen` | absent, `flat` |

**Known traps:**
- One value shown twice lives in `shared`: an amount put only in the thing's props leaves the phone's screen without it.
- The register reads no window from inside `shared`: when the objects move over part of the beat, say so in `linkWhen` too, or the readings run while nothing moves.
- On a tall frame (9:16, 4:5) the link runs from the thing down to the phone and its label sits beside the thing's edge — keep `linkLabel` to a word or two there, or leave it out. Words are 7.5% of what the frame draws (prop reach 0.075): the two objects carry the beat, the words only name it.
- `thing` and `screen` come together or not at all; standalone both are the stages' wordless DemoForm (`layers: 3`), so the preview shows the shape — one form, two places — and no topic.
- Promoted from the film 发布一款概念产品：一台智能咖啡秤和它的 App (a scale drawn in section and its brewing app, one pour shared between them through `shared`), where it was judged against: 遮住字幕：看得出秤上的读数和手机上的读数是同一个数、同时在涨；水流变细时手机上的线也放慢；一条连线把两者接起来，亮点沿线从秤跑到手机. The first film that meets a trap here writes it down.

**Refuses:** `thing` without `screen` or the reverse; a `linkFrom` that is not `{x, y}`; a `linkWhen` that is not `{from, to}` with 0 ≤ from < to ≤ 1; an object nobody defines.

**Measured:** 4.7% ink (clip median) · 43.8% footprint · 0.0014 motion. Measured on the register's own preview — objects/DemoForm on both sides — so the numbers describe the preview, not a film's objects.

**Reference:** `remotion/src/shots/PourSync.tsx`

**Provenance:** product-ui (a beat holding objects is judged on their own world). **Family:** A. **Ground:** `bg` (`DNA_GROUND_TOKEN`), measured light; it follows the film's ground across the frame.
