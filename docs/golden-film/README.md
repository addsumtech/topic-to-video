# Golden film — a cinematic product film produced by the real agent pipeline

This is a **reference film** for the cinematic (Remotion) tier, produced end-to-end by the skill's own
agent pipeline — not hand-authored. It exists to (a) prove the pipeline produces a premium film, (b) show
how a cinematic film is authored with the toolkit, and (c) anchor a regression test
(`tests/test_golden_film.py`).

**Subject:** the `slides-to-video` skill itself (chosen so every on-screen fact is verifiable — nothing is
fabricated; every claim traces to `brief.json`).

## How it was made (the real flow)

```
brief.json ──▶ content-planner ──▶ content_plan.json ──▶ design-director ──▶ storyboard.json
   (truthful)      (5 beats,           (pedagogy_qa OK)      (STEP-0 template       (validate 0 err)
                    narrative arc)                            CONTEST + toolkit)          │
                                                              scriptwriter ◀─────────────┘
                                                              (tightened 70s → 53s)
                                                                     │
                                          render_remotion ◀──────────┘
                                          (colour worlds + native components + shots)
                                                     │
                                          design-critic D12 ──▶ 6 findings ──▶ 3 applied (framing)
                                                     │
                                          re-render ──▶ out.mp4 (52.9s) — check_av OK, shot_qa 5/5
```

Every stage was gated: `brief_qa` → `pedagogy_qa` → `validate` → `rhythm_qa` → `shot_qa` → `check_av`.

## The film

- **Template (STEP-0 contest):** `command-surface` — winner over `defrag` and `ignition-monument`
  (recorded in `meta.template_contest`). The product *is* an agent around a CLI, so the caret→collapse→
  aperture grammar maps onto the story: opens on a cursor, closes on one.
- **Accent:** `#7C5CFF` (electric violet) — every colour world is a deterministic transform of it.
- **5 beats, each a distinct archetype** (the anti-"one card reframed" rule):

  | # | archetype | what it is | toolkit |
  |---|-----------|-----------|---------|
  | 1 | hero-on-void | terminal cold-open poses the tradeoff as two CLI commands → collapses to a line → `CONTROL OR POLISH` blooms | `terminal` (once) + `display` + collapse-to-line match-cut |
  | 2 | process-flow | one `storyboard.json` over the four wired agent nodes | `textblock` nodes + `connector` draw-on |
  | 3 | metric-wall | the named gates under a hunting→LOCK reticle, punching to a FREE callout | `hud` + `callout` |
  | 4 | metaphor-mechanic (climax) | scattered points converge to one; the aurora payoff blooms | `metaphor` (converging-scatter) + `colorWorld` card |
  | 5 | hero-on-void (close) | "Your topic, rendered." + the `$ ▮` caret returns (the bookend) | `colorWorld` card + `callout` |

- **Film knobs:** `hero_mark:"slides-to-video"` (continuity spine), `motion_personality:"precise"`,
  `sound_design:false` (narration-only).

See `frames/` for three representative stills.

## Known refinements (design-critic findings not applied)

The critic returned 6 findings; 3 framing fixes were applied (the hook no longer crops mid-word; the FREE
callout and the closing caret were lifted out of the caption band). Left as documented refinements:

- **Scenes 1–3 share one hue-world** (near-black void with green/lime accents) until the payoff blooms —
  on a `bold` dial, more distinct per-beat colour earlier would push further. (Green = terminal/PASS/go is
  semantically defensible, so it's a soft push, not a floor break.)
- **`sound_design` is off** — a launch film could carry the beat-synced two-track mix (the operator must
  audition it; the pipeline can't hear).

These are recorded rather than fixed so the fixture stays reproducible and the trade-offs are explicit.

## Reproduce

```bash
OUT=<a fresh dir>
cp docs/golden-film/{brief.json,content_plan.json,storyboard.json} "$OUT"/
python3 scripts/theme.py "$OUT" --accent "#7C5CFF" --mode dark
python3 scripts/tts.py "$OUT"
python3 scripts/validate.py "$OUT"          # 0 errors
python3 scripts/render_remotion.py "$OUT"   # -> out.mp4 (needs: cd remotion && npm install)
```
