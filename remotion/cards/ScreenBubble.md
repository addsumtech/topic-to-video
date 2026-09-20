# ScreenBubble

**Identity:** a Loom-style screen recording — an app window with a sidebar, a round camera bubble of a narrator in the corner marked REC, and a cursor that walks to the action button, clicks it (ripple), and moves to the new row that pops into the list.

**Use when:** a casual, human "let me show you" walkthrough of one action in an app — press this, and here is what you get. **Not when:** the beat tours several places on a screen (use `PointerTour`), or the product has no single action worth demonstrating.

**Motion core:** the cursor travels from rest to the button 0.10–0.34, the click ripple plays 0.34–0.44, then the cursor moves to the new row 0.44–0.70 as the row pops in with a slight overshoot 0.46–0.70. Window, sidebar and camera bubble hold still throughout.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `appTitle` | the window's title-bar text | a file or app name; omitted, the demo `workbuddy — untitled` (a product name) prints |
| `nav` | the sidebar entries, 1–6 | a few short labels read as a real app; CJK labels wrap and fill the sidebar sooner. Your own list gets an even sidebar with nothing lit unless you pass `active` |
| `active` | the index of the nav item being shown — lit, and used as the page heading | omitted or `null`: nothing highlighted and no page heading. Only the demo `nav` falls back to its own "Deliverables" page |
| `action` | the button's label, the thing clicked | a short verb ("+ New", "导出"); `''` draws no button and the cursor goes straight to the row with no click. Omitted, the English demo `+ New` prints |
| `deliverable` | the title of the row the action creates | the result of the click; omitted, the demo `Q3 board deck` prints |
| `note` | the dim line under that row | a timestamp or status; omitted, the demo `created just now` prints |

**Known traps:**
- The sidebar used to light `nav[2]` on every film and print it as the page heading — a selection nobody made. Pass `active` when a page is being shown.
- The click used to land inside the sidebar while the ripple played on the button; the click point is now measured from the button's label.
- Omitting the copy props prints English demo copy (`+ New`, `Q3 board deck`) — a Chinese walkthrough then clicks an English button.
- The window and camera bubble are placed by fixed pixel offsets, authored for 16:9: at 1080p the bottom of the window and the camera bubble reach into the band where the caption is burned.

**Refuses:** `nav` with fewer than 1 or more than 6 entries; an empty nav entry; an `active` that is not an integer index into `nav`.

**Reference:** `remotion/src/shots/ScreenBubble.tsx`
