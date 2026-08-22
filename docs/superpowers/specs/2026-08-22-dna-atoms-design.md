# Design DNA · Content Atoms

**Date:** 2026-08-22 · **Status:** approved, not implemented · **Scope:** remotion (bespoke-shot) tier

## Problem

A Design DNA currently reaches a shot as *tokens* — colour, type, radius, motion character. For 132 of
134 registered shots that means a themed film is a **recolour**: the components stay identical, only
their hues change. A grep for a DNA-conditional branch (`dna.id` / `dnaHas(`) across `src/shots` returns
exactly two files — `CinematicTitle` and `ConveyorBelt` — so everything else substitutes tokens and
nothing more. The component-level difference between styles lives entirely in the 11 style-native shots
(`Term*`, `Ed*`), which are separate shots rather than variants of one.

The consequence, in the user's words: switching from `terminal` to `editorial` looks like the same frame
in different colours, because it is.

**Goal:** let the *content atoms* a shot is built from take a different FORM per DNA, so one design
language has a genuine variant per style — a quantity bar is `████░` under terminal, a ruled scale row
under editorial, a dimensioned measure under blueprint, a pixel bar under retro.

## Non-goals

- **Layout re-arrangement per DNA.** A shot's composition stays fixed; only its atoms change form.
  (Explicitly rejected during design: it forces a per-DNA branch into every shot and scales with shot
  count.)
- **Generative / 3D / illustration / fluid registers (~52 shots).** Fluid fields, particle systems,
  three.js heroes, cut-paper dioramas and clay stacks do not decompose into bars and labels. They keep
  the existing behaviour: ground + accent follow the DNA, everything else is theirs.
- **Making `atoms` mandatory.** A DNA that declares no atoms is valid and renders exactly as today.
- **Bulk-migrating all ~58 atom-composable shots.** Nine shots are in scope (see Migration); the rest
  upgrade opportunistically when someone is already working in them.
- **The `new_shot.py` scaffold.** A separate task that has been described but **not approved**; it must
  not be implemented as part of this work. This design does not depend on it — a new shot can import the
  atoms by hand.

## Approach (chosen)

**The DNA declares which FORM it speaks for each atom; the atom renders that form.** This is the same
shape as the existing `decoration` array — a DNA has always declared "which cues I speak" — extended
from decoration to content parts.

Two approaches were rejected:
- *Atom switches on `dna.id`* — every new DNA would mean editing every atom file, and `dna.id` is
  already flagged as behaviour-bearing-but-unvalidated.
- *DNA carries render functions* — breaks JSON serialisability, and `meta.design_dna` lives in the
  storyboard as JSON. It would also become unvalidatable.

## Design

### 1 · Token

In `remotion/src/runtime/dna.tsx`:

```ts
export type AtomForms = {
  bar?:     'block' | 'solid' | 'ruled' | 'pixel' | 'dimension';
  figure?:  'mono' | 'serif' | 'display' | 'segment';
  list?:    'tree' | 'ruled' | 'bullet' | 'numbered';
  label?:   'prompt' | 'kicker' | 'spec' | 'chip';
  divider?: 'scanline' | 'hairline' | 'dimension' | 'dotted';
  marker?:  'caret' | 'triangle' | 'crosshair' | 'arrow';
};
// added to DesignDNA:
atoms?: AtomForms;      // optional — an omitted atom falls back to its neutral form
```

Per-preset declarations (complete; an implementer copies these, no guessing):

| preset | bar | figure | list | label | divider | marker |
|---|---|---|---|---|---|---|
| `TERMINAL_DNA`  | block     | mono    | tree      | prompt | scanline  | caret     |
| `EDITORIAL_DNA` | ruled     | serif   | ruled     | kicker | hairline  | triangle  |
| `PRODUCT_DNA`   | solid     | display | bullet    | chip   | hairline  | triangle  |
| `BLUEPRINT_DNA` | dimension | mono    | numbered  | spec   | dimension | crosshair |
| `CINEMATIC_DNA` | solid     | serif   | bullet    | kicker | hairline  | triangle  |
| `DATA_DNA`      | ruled     | mono    | numbered  | spec   | hairline  | crosshair |
| `RETRO_DNA`     | pixel     | segment | bullet    | chip   | dotted    | arrow     |
| `NEUTRAL_DNA`   | *(omit `atoms` entirely — exercises the fallback path in the default preset)* |

### 2 · Atom components

New file `remotion/src/runtime/atoms.tsx`, a sibling of `dna.tsx`. Six components:

```tsx
<Bar     value={0.88} label="Alpha" tag="PASS" tone?={color} />   // value is 0..1
<Figure  value="88" unit="%" />
<List    items={['a','b','c']} root?="~/project" />
<Label   text="BY THE NUMBERS" />
<Divider width?={120} />
<Marker  />
```

A shot declares *what the part is*, never how it looks. No atom takes a form as a prop — the form comes
from the DNA. `tone` exists only so a shot can give one series a different hue (a hero bar); it never
changes the form.

Interface details that would otherwise be guessed:
- `Bar.value` is a fraction `0..1`. `label` and `tag` are optional; a form that has no place for a tag
  (e.g. `dimension`) ignores it rather than inventing one.
- `Figure.value` accepts a string or a number and renders it **as given**. Count-up animation stays in
  the shot, which passes the current value each frame — the atom is a pure renderer, so it cannot break
  a shot's timing. `unitScale` (default 0.36 of the figure size) exists because the library's shots size
  their unit differently (ChartLive 0.48, EdStat 0.28); a migrating shot passes its own ratio so its
  appearance does not change.
- `List.root` is only meaningful to the `tree` form (the path it hangs the listing under); other forms
  ignore it. `List.reveal` is a PER-ITEM array of 0..1, not one fraction — shots reveal items on their own
  staggered easing, and a single prefix fraction would flatten that into a hard cut.
- `Bar.cells` (default 18) is the cell count for the discrete forms (`block`, `pixel`); shots that already
  choose a resolution pass theirs.
- `Divider.width` is a length in px or a CSS length; a form that draws a full-width rule ignores it.

### 3 · Fallback (the rule that keeps the null-DNA guarantee)

Each atom resolves its form as:

```ts
const FORMS = ['block','solid','ruled','pixel','dimension'] as const;
const NEUTRAL = 'solid';
const f = dna?.atoms?.bar;
const form = (FORMS as readonly string[]).includes(f as string) ? f! : NEUTRAL;
```

Three cases must all reach the neutral form: **no DNA · no `atoms` · an unknown value.** Per-atom
neutral forms: `bar → solid`, `figure → display`, `list → bullet`, `label → kicker`,
`divider → hairline`, `marker → triangle`.

**The neutral form must render what the library renders today** — a rounded track with an accent fill,
a tabular-numeral display figure, and so on. If it does not, migrating a shot to the atoms silently
changes its un-themed appearance and breaks the standing "null DNA renders as before" guarantee (six
shots already had to be repaired for exactly that). Every atom must be total: a missing or malformed
`atoms` object may never throw (`decoration` crashing a whole render is the precedent).

The `kicker` label form respects `dna.uppercaseLabels` / `dna.labelSpacing`; every form takes its colour
from the DNA tokens as today.

### 4 · Migration (7 shots)

The first list for this section was chosen by family and by shot NAME. Reading what the shots actually
draw corrected it, and corrected a design assumption with it: **`Figure` — not `Bar` — is the
high-value atom.** A horizontal quantity bar appears in only two shots library-wide; a big number
appears in five.

| atom | reference implementation (migrated *inward* — its existing rendering becomes the shared form) | consumers |
|---|---|---|
| `bar` | **`TermBars`** → `block` | `ChartRace` |
| `figure` | **`TermCounter`** → `mono` · **`EdStat`** → `serif` | `VelocitySnap`, `ChartLive` *(the headline metric only — its line/area chart is untouched)* |
| `list` | *(none — written fresh in `atoms.tsx`)* | `BlockAssembly` |

Excluded after reading them, with the reason (each would have been damaged, not improved):

- `OdometerRoll` — the mechanical digit reel IS the design language; routing it through `Figure` would
  delete the thing that makes it that shot.
- `GaugeCluster` — a 270° arc instrument, not a bar.
- `BeforeAfterSlider` — its little column chart is decorative furniture inside a mock slide, not the
  shot's content atom.
- `TermTree` — found while writing the plan: its items are objects padded to a fixed name COLUMN, so it is
  a columnar `ls` listing rather than a list. Routing it through `List` would drop the column. The `tree`
  form is therefore written fresh in `atoms.tsx` with no reference shot to migrate inward.

`Label`, `Divider` and `Marker` ship with no migration: they exist for new shots and for opportunistic
use. That is deliberate — inventing consumers for them would be scope invented to justify the atom.

New shots: the atoms are the default way to draw these parts. `agents/shot-critic.md` S1 gains one line
— a new shot built from bars/figures/lists that does not use the atoms must say why.

### 5 · Gates

1. `scripts/validate.py` — validate `meta.design_dna.atoms` values against the enums; an unknown value
   is a **warning**, not an error, because the runtime falls back.
2. `tests/test_remotion.py` — one test rendering every atom across **7 presets × missing `atoms` ×
   an unknown value**, asserting each returns non-empty output and never throws.
3. `tests/test_remotion.py` — the existing `test_null_dna_preserves_every_original_colour` must stay
   green after the nine shots are migrated.
4. **Each migrated shot is rendered under at least three DNAs and looked at.** Three bulk shot edits in
   this project produced a scope crash, a contrast inversion and unreadable captions respectively; none
   was caught by a passing test suite.
5. `python scripts/dna_smoke.py` under two DNAs after the migration.

### 6 · Risks

- **Homogenisation.** If every shot is assembled from six atoms, shots start to resemble each other —
  trading monotony for a different monotony. *Mitigation:* atoms cover content parts only; composition,
  motion and a shot's bespoke elements stay with the shot. shot-critic S11 already asks whether a frame
  could be dropped into another style unnoticed; the same question catches atom sameness.
- **A form that only looks right in one DNA.** *Mitigation:* gate 4 — every migrated shot is seen under
  three DNAs before it lands.
- **Enum growth.** Each new form costs an implementation in one atom. *Mitigation:* the enums are
  deliberately narrow; adding a form is a deliberate act, not a side effect of adding a DNA.

### 7 · Rollback

`atoms` is optional and additive. Deleting the `atoms` declarations from the presets returns every
migrated shot to its neutral form, which is its pre-migration appearance. No storyboard, no authored
`design_dna` and no un-migrated shot is affected.
