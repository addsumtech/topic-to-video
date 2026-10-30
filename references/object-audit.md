# Object audit — is every real thing the library draws TRUE to the thing?

Rule 7 of `references/object-authoring.md` holds a film's built objects to the thing they depict. This file holds the
LIBRARY to the same rule: every register in `remotion/src/shots/` and object in `remotion/src/objects/` that draws a
real physical thing, triaged, and the audit of the first batch.

**How a library register declares its record.** An object puts it in `META.fidelity`; a library register exports
the same record as `export const FIDELITY = {…}` (read by `scripts/fidelity.py register_fidelity()`, held valid by
`tests/test_fidelity.py`), marks each defining part `data-part="…"`, and its sheet is
`python3 scripts/workshop.py <any out_dir> fidelity <Register>`. Reference paths are relative to the skill root;
images live in `references/object-refs/<Name>/` with their imagefetch sidecars.

**What a record costs.** Any byte changed in a register moves its measured source hash, so adding a record, a
`data-part` mark or a fix means re-measuring that register's rows (`measure_ground_reach --only=X --emit`,
`measure_ground_luma --only=X --luma --emit` and `--emit`, `record_spot([X])`, `register_energy --only=X`,
`prop_reach --only=X`). An object's edit moves the hash of every register that IMPORTS it (`GpsSatellite` →
`LightShellOrbit`, `OrbitClockGain`). That is why an audited register whose verdict is "true as drawn" was left
byte-identical in this batch: its references and verdict are below, and it takes its record the next time it is
edited for any other reason.

## Triage

Ranked by how often the shot director casts it (`CANDIDATES` intent lists, `REACH` routes, `CLIMAX`, or a film's
explicit pick only) and how recognisable the thing is — how bad an inaccuracy would look. Priority 1 = cast by a
common intent AND instantly recognisable; 3 = rarely cast or loosely depicted. Abstract / data / typographic
registers (charts, type, UI, metaphor shapes, style treatments) are left out; so are the device registers
(`DeviceHero`/`DeviceDemo`, rebuilt elsewhere), the object HOSTS (`ObjectStage`, `ObjectCompare`, `ObjectPath`,
`ObjectTurntable`, `TechnicalPlate`, `ExplodedSchematic`, `MaterialHero` — they draw the film's object, which carries
its own record) and the registers that composite a REAL image (`PhotoPlate`, `RealVersus`, `KSpaceReal`, `Aliasing`,
`ScanReconstruct`, …).

| # | name | depicts | real / abstract | cast by | priority | status |
|---|---|---|---|---|---|---|
| 1 | GpsSatellite (object) | GPS Block IIF satellite | real | default satellite of LightShellOrbit, OrbitClockGain, RangeSpheres | 1 | **fixed** (below) |
| 2 | PuckInSection (object example) | espresso bed in a 58 mm basket, section | real | the doc's teaching example | 1 | **fixed** (below) |
| 3 | DNAHelix | B-DNA double helix | real | statement, structure | 1 | **fixed** (below) |
| 4 | GearTrain | meshing spur gears | real | sequence | 1 | **fixed** (below) |
| 5 | SplitFlap | Solari split-flap board | real | statement, list, contrast | 1 | audited — finding open |
| 6 | MoleculeBallStick | ball-and-stick molecule | real (film geometry) | statement | 2 | **fixed** (below) |
| 7 | LightShellOrbit | GPS satellite over Earth's limb | real (scene) | film pick (GPS) | 2 | audited — true as a scene; re-measured |
| 8 | OrbitClockGain | Earth, orbit, satellite | real (scene) | film pick | 2 | audited — finding open; re-measured |
| 9 | RangeSpheres | satellites over Earth's limb | real (scene) | film pick | 2 | audited — true as a scene |
| 10 | AtomOrbital | an atom (planetary model) | real (conventional model) | statement | 2 | audited — conventional, kept |
| 11 | CircuitTrace | printed circuit board | real (stylised) | sequence, structure | 2 | audited — stylised, minor finding |
| 12 | AuroraCurtain | aurora curtain | real | film pick (natural-world) | 2 | audited — already sourced |
| 13 | OffsetClock (object) | a clock-comparison dial | abstract (declared) | OrbitClockGain's dial | 2 | audited — correctly abstract |
| 14 | GlobeFocus | the Earth, a place on it | real (Natural Earth data) | structure, reach:where | 2 | not yet — geography is data-true by construction |
| 15 | FlightArcs | Earth + great-circle routes | real (data) | structure, reach:route | 2 | not yet |
| 16 | EmberFlame | flame and embers | real phenomenon (decorative) | statement, climax, reach:light | 2 | not yet |
| 17 | OdometerRoll | mechanical odometer reels | real | metric, reach:one-quantity | 2 | not yet |
| 18 | ConveyorBelt | conveyor + stamp press | real (machine) | sequence | 2 | not yet |
| 19 | GaugeCluster | dial gauges | real (instrument) | metric | 3 | not yet |
| 20 | FractalTree | a tree growing | real (stylised) | statement | 3 | not yet |
| 21 | ClothWave | a flag of fabric | real | statement | 3 | not yet |
| 22 | RainGlass | rain on a window | real | statement | 3 | not yet |
| 23 | InkBloom | ink diffusing in water | real phenomenon | statement | 3 | not yet |
| 24 | StarfieldWarp | stars | real-ish (hyperspace effect) | statement, reach:light | 3 | not yet |
| 25 | SpotlightStage | a theatre spotlight | real | climax, reach:light | 3 | not yet |
| 26 | LightShafts | crepuscular rays | real phenomenon | film pick | 3 | not yet (header cites its physics) |
| 27 | NebulaField | emission nebula | real | film pick | 3 | not yet (header cites its physics) |
| 28 | WireGlobe | the Earth as a wire sphere | real (abstracted) | structure | 3 | not yet |
| 29 | MapPlate | an engraved map plate | real (data) | reach:where | 3 | not yet |
| 30 | StrataColumn | a stratigraphic column | real (film data) | film pick | 3 | not yet |
| 31 | EraStrata (object) | strata | real (film data) | film pick | 3 | not yet |
| 32 | Inscription | letters cut into stone | real | film pick | 3 | not yet |
| 33 | LitMedium | paper / water / metal / clay surfaces | real materials | statement, reach:medium | 3 | not yet |
| 34 | LarmorPrecession | a precessing magnetic moment | real physics | MRI films | 3 | not yet |
| 35 | SpinningProton | a spinning proton's dipole | real physics | MRI films | 3 | not yet |
| 36 | InducedFID | a receive coil and its signal | real physics | MRI films | 3 | not yet |
| 37 | GradientTilt | a gradient field | real physics | MRI films | 3 | not yet |
| 38 | MagnetizationTip | net magnetisation tipped by RF | real physics | MRI films | 3 | not yet |
| 39 | SpinsAlign | spins aligning in B0 | real physics | MRI films | 3 | not yet |
| 40 | MRIPipeline | acquisition → reconstruction, in miniatures | real (miniatures) | MRI films | 3 | not yet |
| 41 | IsometricAssembly | a factory workstation | metaphor with a machine | structure | 3 | not yet |
| 42 | PaperCutout | a cut-paper landscape | real craft (stylised) | film pick | 3 | not yet |

42 rows: 40 real things (two of them library objects), the object example, and one object correctly declared
abstract. 13 audited in this batch; 6 changed.

## The batch audited here

Every reference below was read for this audit (2026-10-30), not recalled. "Before/after" stills are in
`~/Desktop/库物体精细化 前后对比.png`.

### GpsSatellite — fixed
- **References:** NASA/Boeing IIF rendering (`references/object-refs/GpsSatellite/gps-iif.jpg`, Commons, PD — the same
  picture Gunter's Space Page credits to Boeing as "GPS-2F"); USAF "Navstar-2F" drawing (`navstar-2f.jpg`, Commons,
  PD, the Wikipedia GPS Block IIF infobox image — added); airforce-technology (2.23 m high, 2.48 m wide, 2.03 m
  deep; three-panel GaAs arrays; "thermal coatings, radiator blankets"); Air & Space Forces (9.6 × 6.5 × 12.9 ft,
  span 43.1 ft); US7388559B1 (4 inner + 8 outer helices); Gunter's Space Page (2 deployable arrays).
- **Fixed, settled by the sources:** each wing is ONE continuous array of three butted panels (both drawings) — it
  was three gapped panels; every bus face is gold foil (both drawings) — the side faces were invented silver
  radiators with louvres; the helices stand on a dark frame under the bus (the NASA/Boeing drawing) — they stood on a
  pale disc; the boom-mounted antenna (L-boom, collar, bronze can, both drawings) is drawn — it was missing; the
  yoke is dark struts as drawn. The span is now derived from the sourced ratio (13.1 / 2.48) instead of three
  panel constants.
- **Body axes — not settled, recorded:** airforce-technology's 2.48 × 2.23 × 2.03 m names no Earth axis, and Air &
  Space Forces' 9.6 × 6.5 × 12.9 ft matches neither and names no axes. Drawn 1.22 : 1.10 : 1.00 with "wide" along the
  wings and "high" on the Earth axis, as both drawings pose it; the old drawing had the body TALLER than wide while
  taking the span ratio against the 2.48 m width — the two records now agree with each other. The wing chord has no
  spec; ~0.6 of body height is read off the drawing and says so. Which side of the real craft carries the boom
  antenna one drawing cannot say; it is drawn by the root of the wing nearer the viewer, as the drawing shows it.
- **Re-measured:** `LightShellOrbit`, `OrbitClockGain` (they import `nadirPoint`, whose geometry moved).
  `RangeSpheres` names the object by id only and its hash did not move.

### PuckInSection — fixed
- **References:** portafilter photo (`object-examples/refs/portafilter.jpg`, CC BY-SA 2.0); Bean Bros listing of
  the E&B Lab 58 mm basket (rim 70 mm, height 24 mm, 715 holes across 49 mm, flat bottom); Maxicoffee E&B Lab H24
  listing (58 mm ridgeless, 24 mm high, micro-perforated).
- **Fixed:** depth / diameter 0.75 → 0.41 (24 / 58); the floor is perforated across its middle 49 mm at the
  715-hole pitch (~1.75 mm) and solid at the edges — it was solid; the 70 mm rim's flange is drawn. The doc's image
  (`object-examples/PuckInSection.png`) is re-rendered by `scripts/object_examples.py`.

### DNAHelix — fixed
- **References:** DBCLS double-strand diagram (`object-refs/DNAHelix/dna-structure.png`, CC BY 4.0); Wikipedia
  "Nucleic acid double helix" (B-DNA: right-handed, 10.5 bp/turn, rise 3.32 Å, pitch 33.2 Å, diameter 20 Å, major
  groove 22 Å, minor 12 Å; "the strands are not directly opposite each other").
- **Found:** the strands were two sines half a turn apart sampled every 16 px at a phase step of 13 rad, so the
  helix on screen was an ALIAS — about seven rungs a turn, pitch a third of the true 1.7 × diameter, no grooves, no
  continuous backbone, and a handedness that held only by the accident of where 13 rad landed.
- **Fixed:** pitch = 1.7 × diameter, 10.5 base pairs a turn, the second backbone 12/34 of a turn behind (major and
  minor grooves), right-handed by construction (stated and derived in the source), continuous depth-shaded
  backbones with a phosphate at each base pair; radius derived from the frame (was a 1920-tuned constant).

### GearTrain — fixed
- **References:** two meshed involute spur gears (`object-refs/GearTrain/spur-gears.png`, CC BY-SA 4.0); KHK gear
  technical reference Table 4.1 (a = (z1 + z2) m / 2, d = z m, tip d + 2m, root d − 2.5m) and §3.1 (addendum 1.00 m,
  dedendum 1.25 m, pressure angle usually 20°).
- **Found:** square tabs on r = 156 round 150 px discs with centres 278 apart — the bodies OVERLAPPED by 22 px and
  every tooth at the mesh vanished inside its neighbour's body; no tooth ever entered a gap.
- **Fixed:** standard gears — module = spacing / z, tips at r + m, roots at r − 1.25 m, straight 20° flanks down to
  the base circle and radial below it, the tooth πm/2 thick at the reference circle; 16 teeth keeps the outer radius
  (156.4) the layout was fitted to, so labels, badge and fit are unchanged. Equal gears, equal speed, opposite
  directions, half-pitch phase between neighbours (already right).

### MoleculeBallStick — fixed
- **References:** a ball-and-stick rendering (`object-refs/MoleculeBallStick/ball-and-stick.png`, Commons, PD);
  Wikipedia "CPK coloring"; Wikipedia "Van der Waals radius" (Bondi: H 1.2, C 1.7, N 1.55, O 1.52 Å).
- **Found:** every bond was drawn behind every atom while the header promised depth-sorted sticks — a front bond
  vanished behind a far ball.
- **Fixed:** bonds and atoms in one far-to-near order (a stick at its ends' mean depth). True as drawn: H : C radius
  18 : 26 = 0.69 against Bondi's 0.71; CPK colours, with carbon lifted to slate and Mg/Ca to a light green so they
  read on a dark ground (recorded in the FIDELITY).

### LightShellOrbit, RangeSpheres — true as a scene
The satellite is the GpsSatellite object (above), the Earth a limb. These are scenes, not scale drawings: no
distance or size is claimed on the frame, so the exaggerated satellite is the convention of the form. No change.

### OrbitClockGain — finding open
Its left panel draws the orbit at ~1.5 Earth radii from the Earth's centre (landscape: R = 0.62 H, orbit through a
point in the upper left). A GPS orbit is (20,460 + 6,371) / 6,371 = 4.2 Earth radii from the centre (Wikipedia "GPS
Block IIF": semi-synchronous MEO at about 20,460 km altitude; Wikipedia "Earth radius": mean 6,371 km). The register's claim is "far up, the pull is weak", and the
satellite is a prop (any orbit), so the ratio is a composition rather than a GPS statement — but a GPS film that
says "twenty thousand kilometres up" shows a third of that. Next: an `orbitRatio` prop (default composition, a film
passes 4.2) or a not-to-scale mark. Re-measured (its hash moved with the object).

### SplitFlap — finding open
Reference read: Wikipedia "Split-flap display" (its images: the Frankfurt Hbf board section, the Cifra 5
mechanism, the animation of how a flap falls). The board's defining motion — the upper half-flap falling about the
centre hinge to uncover the next character — is not drawn: the glyph swaps in place under a 4% squash, and the split
is a 2 px line at 70%. A true flip is a 3D half-flap carrying type (it must go through `glide()` and the jitter
gates), so it is left for its own change. Unchanged.

### AtomOrbital — conventional, kept
It draws the planetary (Rutherford–Bohr) icon: a nucleus and tilted electron rings, electrons per shell from the
film's `shells`. That is the recognised SYMBOL of an atom, not a claim about orbitals; the electron counts are the
film's. Kept; a quantum-orbital register is a different register.

### CircuitTrace — stylised, minor finding
Copper traces with 90° Manhattan bends between labelled pads. Board layout practice favours 45° corners (etching
over-cuts thin 90° outside corners; mitred corners at RF — PCBGOGO, Altium "PCB Routing Angle Myths", Hackaday
"What's the deal with square traces on PCBs"), and Altium's article shows 90° is not wrong below RF. A board with
45° mitres would read more like a real PCB; not wrong as drawn. Unchanged.

### AuroraCurtain — already sourced
Its colours by altitude come from `runtime/volume` `AURORA_BANDS`, which carries its own sources (green 557.7 nm
oxygen low, red 630 nm oxygen above, the pink lower border); the frame matches (pink border, green curtain, red
tops). Unchanged.

### OffsetClock — correctly abstract
Declared `depicts: 'abstract'` ("a measuring diagram, not a model of any real clock"); it draws no numerals and
claims no real clock. Correct.

## The instrument, corrected on the way (E3)

The part probe (`runtime/fidelity.tsx`) measured each part by its GEOMETRY box, so a horizontal stroked line — every
base pair, the basket's floor — measured zero pixels tall and the sheet reported a drawn part as MISSING. It now
widens a stroked shape by half its rendered stroke width and measures a flat node by its leaves.

## What is left

- Records for the audited-unchanged registers (SplitFlap, AtomOrbital, CircuitTrace, AuroraCurtain, RangeSpheres)
  when they are next edited; the open findings above (OrbitClockGain's orbit ratio, SplitFlap's flap).
- Rows 14–42 of the triage.
