# FractalTree

**Identity:** a recursive tree grows up from the ground depth by depth — trunk, branches, twigs — then blossoms bloom at the tips and a title fades in above.

**Use when:** growth / branching out / "from one root, everything" as a techno-natural title beat. **Not when:** the branches must be named things (the tree takes no items — KnowledgeGraph or TermTree), or the title is long.

**Motion core:** branches draw on in order of depth, trunk first (each depth starting a little later, from 0.04 to ~0.54, each over 0.16); blossoms bloom at the tips 0.62–0.90, staggered; the title rises 0.60–0.82 and the tagline 0.70–0.90; then it holds.

| Prop | What it sets | Feel of turning it |
|---|---|---|
| `title` | the big word near the top | fixed 120px at a fixed top position, not fitted |
| `tagline` | the tracked mono line under it | fixed 30px, not fitted |
| `branch` | the colour of the trunk and branches (not the leaf twigs) | any CSS colour; not taken from the DNA |
| `blossom` | the colour of about half the blossoms | the other half stay a fixed yellow |

**Known traps:**
- The wood is walked until it clears the floor against BOTH blossoms AND the page — every surface it is actually drawn on. Naming only the blossoms inverts it: the shared ladder derives its direction from how much room each end has, the exposed blossoms are dark on a light film, so white had more room and the branches came out as a white line on white paper (median 2.01:1, 56% of marks under the floor — worse than the defect being repaired).
- The tree's shape is fixed — a seeded recursion from a fixed trunk length at a fixed height above the bottom — the same on every film and not scaled to the frame.
- A tree is a FORM, not a light — dark branches on pale paper is how one is drawn — so on a film that grounds on paper every one of its four hues (branch, leaf twig, and both blossoms) is walked along its own black-to-white axis until it clears the graphics floor. Hue is kept exactly; only the exposure moves, so a film that passes its own `branch`/`blossom` still gets that colour.
- The title takes the film's ink and the kicker its `dim`; the lit floor the trunk grows out of, and the title's separation shadow, follow the film's own paper on a light film instead of staying near-black.
- Each blossom's 6px glow is a dark-ground device and is dropped on a light one: on paper it is a halo of the blossom's own colour, and it was dissolving both the blossom's edge and every twig behind one.
- Exposing each of the four hues to one floor against the PAGE says nothing about what they do to EACH OTHER, and a contrast ratio is blind to hue: all four landed on one luminance, so the sage twigs and the amber blossoms measured about 1.0:1 against each other and every twig running through the canopy was read against the blossom sitting on it. `ink_contrast_qa` reported a median mark of 3.61:1 with 14.8% under the floor and a 0.30%-of-frame hole, and the hole was a patch of canopy, not a word. On a light film the wood is now walked down its own black axis until it clears 3:1 against both blossoms — the way anyone draws a tree on paper: the branches are the dark line, the blossom keeps its colour. On a DARK film those two tones still sit close together; that is the register's own palette, unchanged.
- The branch opacity ramps 0.5 → 1 with depth, so the TRUNK is the faintest stroke on either ground. That is the register's depth cue, not a contrast defect, but it does mean the trunk reads lightly on paper.
- Title and tagline sit at fixed pixel tops and are not fitted.
- Defaults print 'Grow' / 'from one root, everything'.

**Reference:** `remotion/src/shots/FractalTree.tsx`
