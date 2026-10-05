# HTML tier: build what the film needs — design

Sub-project 2 of the adaptive build (see `2026-09-27-adaptive-build-design.md`). This spec covers only the
**workshop for the HTML (page) tier**. CSS 3D, camera and click are a later, separate piece of work.

## Why
Remotion films can build an object or shot the library lacks, check it, and promote it. HTML films can't: a
page only gets the forms in `assets/html/base.css`. A special diagram (a coffee puck in section, a scale's load
cell) has to be hand-written into one page. That page code can't be reused or checked as a unit, and it never
reaches the library.

## Decisions (made with the user, 2026-10-05)
1. **A component is a custom HTML element**, for example `<espresso-puck packed="1">`. It is one plain JS file
   plus one CSS file in the film's workshop.
   - JS builds the element's DOM once, at load.
   - Every animation is CSS keyframes, so the existing `seek.js` freeze-at-progress capture drives it
     unchanged.
2. **Film-local first, promotion by the user's choice.** This is the same rule as sub-project 1.
3. **Acceptance: two HTML films**, the espresso film and the smart-scale launch film, in Chinese, each building
   at least two components.
4. **No regression.** A film without `workshop/html/` renders byte-identically to today. Every existing gate
   stays, and the full suite stays green.

## The component contract
These rules are enforced by `workshop.py check`, and by tests where runtime behaviour matters.

- **Layout:**
  - `<out_dir>/workshop/html/<Name>.js` and `<Name>.css`.
  - The tag is the kebab form of the PascalCase name, and must contain a hyphen (`EspressoPuck` →
    `espresso-puck`).
  - The JS calls `customElements.define(tag, class extends HTMLElement {...})` exactly once.
- **Light DOM only.** No `attachShadow`, because `seek.js`, the glide census and keyframe_qa's geometry walk
  the light DOM.
- **Deterministic.** None of these may appear:
  - time: `Date`, `performance.now`, `setTimeout`, `setInterval`, `requestAnimationFrame`;
  - randomness: `Math.random`;
  - network: `fetch`, `XMLHttpRequest`, `import()`;
  - scripted animation: `el.animate` (the Web Animations API).

  Any pseudo-randomness must be seeded from attributes.
- **Build once, before seek.js.** The component scripts are linked in the page before `seek.js`. On define,
  the browser upgrades the parsed elements synchronously, so `seek.js` sees their animated children.
  `check` verifies the order in every page that uses a component.
- **Words come only from attributes.** Every visible word a component draws must appear in one of its
  attribute values; numbers count only if they are themselves attribute values.
  - The JS exports `static demo = {attr: value, ...}`: neutral demo attributes, never film copy.
  - `check` renders the component with those demo attributes and fails it if any visible text is not sourced
    from an attribute. This catches placeholder or film-specific words written into the code.
- **Sized by its box.**
  - The element fills the box its page gives it.
  - `check` renders it at a 16:9 content-column size and at a 9:16 column size. Any overflow fails it
    (scroll size larger than the client size on the element or any descendant).
- **Moving text glides.** Text moved by an animated transform carries the baseline unlock (see
  `references/html-pages.md`). The existing HTML glide census in keyframe_qa covers components automatically,
  and a test proves it does.
- **Reduced motion.** With `reduced-motion.css` linked, no component part may move. Only opacity may change.
  `check` measures this by rendering two progress values and confirming that no element's box moved.
- **Meaning first.** A component must have a `meta.build_list` entry before it is drawn: `kind: "component"`,
  `id` = the PascalCase name, `beats`, `means`, `accept`, and `slot: "page"`. The `means` must hold with the
  caption covered.

## Tooling
**`scripts/workshop.py`**
- `new-component <Name> --means "..."` scaffolds the two files with the contract's skeleton.
- `check` lints every component against the contract, then runs the runtime checks: words, size and reduced
  motion.
- `still <Name> [--attrs a.json] [--p 0.9] [--aspect 16:9|9:16]` renders a preview PNG into
  `workshop/_stills/`.
- The remotion paths are unchanged.

**`scripts/validate.py`** (HTML films)
- Every component in `workshop/html/` has a build-list entry.
- Every build-list component is used by at least one page, and those pages are the beats it lists.
- An unknown custom tag in a page (no workshop or library definition) is an ERROR.

**`scripts/keyframe_qa.py`**: no change in rules. Its existing checks cover pages that hold components. A test
proves that a component overflowing into the caption band is caught.

**`scripts/promote.py <out_dir> <Name>`** for a component:
- copies it to `assets/html/components/<Name>.js` and `.css`;
- adds its entry to a new `references/html-components.md` (what it means, its attributes, a still);
- points the film's pages at the library copy;
- re-runs `check` on the library copy.
- Refused if the film's tests or `check` fail.

**Docs**
- `references/html-pages.md` gets a "Building a component" section (the contract, with a worked example).
- SKILL.md's HTML step says when to build: the build-list step from sub-project 1 applies to the HTML tier.

## No-regression proof
- Render one existing HTML film's pages before and after the change; they must be byte-identical (jev-html,
  `.superpowers/films/jev-html` in the main checkout).
- The full suite must be green.

## Acceptance
Two films with Chinese narration, about 60–90 s each, 16:9, delivered to the user's Desktop:
- **Espresso:** how an espresso machine pulls a shot.
- **Smart scale:** a concept smart coffee scale and its app.

Each film must:
- build at least two components;
- clear every HTML-tier gate;
- be looked at frame by frame (one settled frame per beat, caption covered), so that each component's `means`
  reads without the caption.

Report every skill defect met, with a fix and a test where it belongs in this branch.
