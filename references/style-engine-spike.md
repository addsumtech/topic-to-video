# Style engine spike: the per-frame DOM pass, measured (2026-10-31)

The spec's settled point 1 asks a question before anything else is built: can a pass that restyles what registers
drew, after React drew it, stay deterministic and leave type exactly where it was? If not, the fallback is a codemod
to shared primitives. This is the measurement that decided it.

**Setup.**
- `scripts/style_spike.py` ran over `tests/fixtures/style/corpus.json`: 15 registers, each at ~90% of its length.
- The spec was `tests/fixtures/style/spike_spec.json`: `line.weight: 4`, `fill.mode: flat`. Those are the only two
  axes the spike pass implements.
- Each register was rendered:
  - unstyled;
  - styled twice as cold stills;
  - styled inside a 4-frame sequence across 4 tabs (out of order).
- The type census (`TYPE-GLIDE`) was taken styled and unstyled. Lines are matched by text and occurrence, because
  the style layer adds one element to every DOM path.

| register | twice | out of order | type moved (px) | lines | pixels changed |
|---|---|---|---|---|---|
| ClayStack | 0 | 0 | 0.0 | 1 | 94.8% |
| ChartLive | 0 | 0 | 0.0 | 3 | 48.0% |
| KnowledgeGraph | 0 | 0 | 0.0 | 8 | 76.7% |
| FlowSankey | 0 | 0 | 0.0 | 5 | 70.2% |
| AtomOrbital | 0 | 0 | 0.0 | 2 | 65.1% |
| CinematicTitle | 0 | 0 | 0.0 | 3 | 61.3% |
| CraneUp | 0 | 0 | 0.0 | 8 | 0.0% |
| TermSpace | 0 | 0 | 0.0 | 12 | 59.0% |
| WordTunnel | 0 | 0 | 0.0 | 1 | 89.9% |
| CartoonPop | 0 | 0 | 0.0 | 1 | 61.3% |
| HandDrawn | 0 | 0 | 0.0 | 3 | 0.9% |
| PortRail (canvas) | 0 | 0 | 0.0 | 7 | 0.0% |
| ObjectStage + GpsSatellite | 0 | 0 | 0.0 | 1 | 6.7% |
| PhotoPlate (fixture photo) | 0 | 0 | 0.0 | 2 | 0.0% |
| ElasticType (CJK) | 0 | 0 | 0.0 | 3 | 59.3% |

"twice" and "out of order" are the fraction of pixels differing by more than 2/255. Every one is 0.

**What the zeros mean** (side-by-side sheets looked at):
- **CraneUp**: its tiles are HTML boxes with solid fills, so there are no SVG strokes and no gradients. Borders are
  Task 3.
- **PortRail**: a canvas, exempt by design.
- **PhotoPlate**: the photograph is exempt, and the plate has no gradient.
- **HandDrawn**: its strokes are already close to 4 px.

Where the pass acted, the change is the one the spec asked for:
- gradients became flat fills (the clay's shading and every radial ground glow);
- strokes became 4 px (the GPS panel grid visibly heavier; ClayStack's thick tick visibly thinner).

**Decision: keep the DOM pass.** It is deterministic on all 15, type moved 0.0 px on all 15, and the visible change
matches the spec. No codemod.

**How the pass stays deterministic.**
- Three phases each time: put back every value of ours still in place, read the originals, then write.
- Our write is "still in place" when the property still reads exactly what we wrote. Otherwise React wrote since,
  and that value is the new original.
- It runs in a layout effect per frame, and again on any DOM mutation under the layer (child effects that land
  after it).

**Not measured here: render time.** The pass reads computed style for every element once per frame. The library
sweep (Task 11) records the styled/unstyled render time per register.
