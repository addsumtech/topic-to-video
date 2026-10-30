#!/usr/bin/env node
// THE FIDELITY SHEET'S STILLS — each job rendered to a PNG with the part probe's log captured beside it.
//
//   node fidelity_stills.cjs <remotion dir> <bundle dir> <jobs.json> <out.jsonl> [--gl=angle]
//
// jobs.json is [{"tag", "id": composition id, "props": {...}, "frame": n, "png": path}]. For each job one line
// {"tag", "parts": <the FIDELITY-PARTS record runtime/fidelity.tsx logged>} — or {"tag", "error"}. A job with no
// `parts` was not measured, whatever its picture shows.
//
// WHY THE NODE API: the CLI's `still` prints a page's console.log only for the composition-selection tab, not for
// the tab the frame is rendered in, so the probe's line never reached the caller (scripts/glide_frames.cjs says the
// same of its census). renderStill's onBrowserLog sees it.
'use strict';
const fs = require('fs');

const [, , remotionDir, serveUrl, jobsPath, outPath, ...flags] = process.argv;
if (!remotionDir || !serveUrl || !jobsPath || !outPath) {
  console.error('usage: node fidelity_stills.cjs <remotion dir> <bundle dir> <jobs.json> <out.jsonl> [--gl=..]');
  process.exit(2);
}
const opt = (name, dflt) => {
  const hit = flags.find((f) => f.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3) : dflt;
};
const R = require(require.resolve('@remotion/renderer', {paths: [remotionDir]}));
const TAG = 'FIDELITY-PARTS ';

(async () => {
  const jobs = JSON.parse(fs.readFileSync(jobsPath, 'utf8'));
  const chromiumOptions = {gl: opt('gl', 'angle')};
  const out = fs.openSync(outPath, 'w');
  const write = (obj) => fs.writeSync(out, JSON.stringify(obj) + '\n');
  const browser = await R.openBrowser('chrome', {chromiumOptions, logLevel: 'error'});
  try {
    for (const job of jobs) {
      let parts = null;
      try {
        const composition = await R.selectComposition({serveUrl, id: job.id, inputProps: job.props || {},
          puppeteerInstance: browser, chromiumOptions, logLevel: 'error'});
        await R.renderStill({composition, serveUrl, inputProps: job.props || {}, output: job.png,
          frame: Math.min(job.frame || 0, composition.durationInFrames - 1), imageFormat: 'png', overwrite: true,
          puppeteerInstance: browser, chromiumOptions, logLevel: 'error', timeoutInMilliseconds: 120000,
          onBrowserLog: (log) => {
            const text = log && log.text;
            if (typeof text === 'string' && text.startsWith(TAG)) parts = JSON.parse(text.slice(TAG.length));
          }});
        write({tag: job.tag, parts});
      } catch (e) {
        write({tag: job.tag, error: String((e && e.message) || e).split('\n')[0].slice(0, 600)});
      }
    }
  } finally {
    await browser.close({silent: true}).catch(() => {});
    fs.closeSync(out);
  }
})().catch((e) => {
  console.error(String((e && e.stack) || e));
  process.exit(1);
});
