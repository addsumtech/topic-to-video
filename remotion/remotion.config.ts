import {Config} from '@remotion/cli/config';
import fs from 'fs';
import path from 'path';

Config.setVideoImageFormat('jpeg');
Config.setOverwriteOutput(true);

// A FILM'S WORKSHOP — the objects and shots one film builds for itself (scripts/workshop.py) — enters the
// bundle through ONE alias, and nothing else about the library changes. `SLIDES_WORKSHOP` is set only by
// scripts/workshop.py, for a render scoped to one film; unset, `@workshop` is the tracked empty stub and the
// library bundles exactly as it did. A path that is set but holds no generated index is refused here rather
// than bundled as an empty workshop: a film whose built things silently vanish is the failure this prevents.
// (Every caller runs the CLI with cwd = this directory, so process.cwd() is the project root.)
//
// Resolved ONCE, here, and used everywhere below (the existence check, the alias, the module rule's `include`).
// A relative SLIDES_WORKSHOP checked against the cwd but handed to webpack unresolved is checked in one place
// and resolved in another — they need not agree.
const ROOT = process.cwd();
const WORKSHOP = process.env.SLIDES_WORKSHOP ? path.resolve(process.env.SLIDES_WORKSHOP) : undefined;
if (WORKSHOP && !fs.existsSync(path.join(WORKSHOP, 'index.ts'))) {
  throw new Error(`SLIDES_WORKSHOP=${WORKSHOP} has no index.ts — render through scripts/workshop.py (prepare), ` +
    'which generates it');
}
Config.overrideWebpackConfig((c) => ({
  ...c,
  resolve: {
    ...c.resolve,
    alias: {
      ...((c.resolve?.alias as Record<string, string>) ?? {}),
      '@workshop$': WORKSHOP ? path.join(WORKSHOP, 'index.ts') : path.join(ROOT, 'src', 'workshop', 'none.ts'),
      '@runtime': path.join(ROOT, 'src', 'runtime'),
      '@shots': path.join(ROOT, 'src', 'shots'),
    },
    // NOT a project-wide `resolve.modules` prepend — that one line put this project's node_modules ahead of
    // EVERY module's lookup, workshop or not, and flattened the library's own dependency tree onto it: r3f and
    // react-reconciler each carry their OWN nested `scheduler` (0.21.0), and the project-wide prepend resolved
    // every bare `scheduler` import to the top-level one (0.23.2) instead — in every library bundle, workshop
    // or none, confirmed from two bundles' source maps (`.superpowers/regression/bundle-sources/`). That broke
    // the no-regression constraint by construction: a film with no workshop must bundle exactly as before, and
    // "the library bundles exactly as it did" was the very comment this replaces.
    //
    // A rule's `resolve` REPLACES the global one for the modules it matches (webpack 5), so scoping it to a
    // rule whose `include` is the workshop's own directory reaches only requests made BY workshop files — a
    // bare `react`/`remotion`/`three` import from a film folder that has no node_modules of its own, or a
    // different copy of one — and leaves every other module's resolution (the whole library) untouched.
  },
  module: {
    ...c.module,
    rules: [
      ...(c.module?.rules ?? []),
      ...(WORKSHOP ? [{
        // webpack matches `include` against the RESOLVED path of the importing file. On macOS `/tmp` and
        // `/var/folders` (where pytest's tmp_path lives) are symlinks into `/private/...`, which is what that
        // resolution actually lands on — so `include` holds both the path as given and its realpath.
        include: [WORKSHOP, fs.realpathSync(WORKSHOP)],
        resolve: {modules: [path.join(ROOT, 'node_modules'), 'node_modules']},
      }] : []),
    ],
  },
}));
