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
const ROOT = process.cwd();
const WORKSHOP = process.env.SLIDES_WORKSHOP;
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
    // Workshop files live OUTSIDE this project, so a bare `react` / `remotion` import from one would search the
    // film's folders for node_modules and find none. This project's own node_modules is searched first.
    modules: [path.join(ROOT, 'node_modules'), ...(c.resolve?.modules ?? ['node_modules'])],
  },
}));
