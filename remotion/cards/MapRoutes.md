# MapRoutes

**Identity:** glowing curved routes draw out from a central hub disc to pins set evenly around it on an ellipse, over a faint night-map grid; bright packets travel each arc and the pins pop in, pulse, and carry a small labelled tag.

**Use when:** the claim is reach from one centre — "it connects to all of these", a hub and the things it plugs into. **Not when:** position means something (the pins are spaced evenly, not placed — use MapPlate for real positions), or the items relate to each other rather than to the hub (use a graph register such as KnowledgeGraph).

**Motion core:** the hub is there from the first frame; pins pop in with an overshoot from 0.14, one every 0.05, each over 0.24, so even ten have landed by 0.83 (before the settled frame at 0.86); the routes draw on together over 0.12–0.7, each spoke finishing a little after the one before; from 0.3 (+0.05 per spoke) a packet rides each arc for half the clip and the pin's ring starts pulsing.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `items` | one spoke each, placed clockwise from the top, 1–10 | 3–4 give a sparse star with room to breathe; ten still read at every aspect, though they crowd the ellipse. Each tag takes the side of its pin that has room and its text is shrunk (from 26px) only as far as that room needs, on one line |
| `hub` | the word in the central disc | the disc is a fixed 130px: a short English word sits at 30px; Chinese is shrunk to fit and balanced across lines |
| `accent` | the routes, pins, glows and tag borders | the whole network's colour; what you pass wins, unset it is the film's DNA accent, and only an un-themed film gets the original teal |

**Known traps:**
- Omitting `items` / `hub` prints a product demo: GitHub, Slack, Notion, Drive, Jira, Gmail around `WorkBuddy`.
- There used to be no cap on `items`: pins start 0.05 apart and take 0.24 to land, so past about a dozen spokes the last pins were still popping when the clip ended. It is capped at ten now — at twelve, neighbouring labels (北京/上海, 重庆/武汉) overlapped on a 1:1 frame.
- Only Chinese hub text is fitted; a long English hub name keeps 30px and wraps out past the 130px disc.
- The tags take the film's surface and ink, the graticule its `line`, and the hub disc is a tint of the accent with its word measured against that disc. Before this the labels read on a paper film only because each carried its own dark chip, while every route, pin and packet — the connections the register exists to draw — measured under 1.5:1 and the graticule authored as a faint hint became a hard dark web across the page.
- Earlier versions set the layout on the frame's middle (the lowest node landed in the caption band), pinned every tag to the right of its pin (off the frame for Chinese), and drew packets up to 140px off their route; all three are fixed — keep labels short rather than fighting the fit.

**Refuses:** no `items`, more than ten, or an empty item.

**Reference:** `remotion/src/shots/MapRoutes.tsx`
