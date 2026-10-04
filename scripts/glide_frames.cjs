#!/usr/bin/env node
// THE TYPE-GLIDE CENSUS, RENDERED — every frame of a composition walked, with no picture taken.
//
//   node glide_frames.cjs <remotion dir> <bundle dir> <jobs.json> <out.jsonl> [--gl=angle] [--concurrency=N]
//
// jobs.json is [{"tag": label, "id": composition id, "props": {...}, "from": a, "to": b}] (from/to optional:
// the composition's own first and last frame). Each job is rendered with `imageFormat: 'none'` — the renderer
// seeks every frame, waits for its delayRenders, and skips the screenshot (renderer/dist/take-frame.js) — and every
// `TYPE-GLIDE` line the page logs (runtime/textSafe.tsx TypeGlideAudit) is written to out.jsonl with the job's tag.
// After each job one line {"tag", "done": true, "frames", "logged", "ms"} says how much of it was measured, or
// {"tag", "error"} why nothing was: a job that failed must read as unmeasured, never as clean.
//
// WHY THE NODE API AND NOT THE CLI. The census is read across frames, so it needs every frame of a range and no
// picture; the CLI refuses an image-less sequence and prints a bundle's console.log only at --log=verbose, mixed
// with the renderer's own chatter. The renderer is already installed (it is what @remotion/cli renders with), so
// this adds no dependency — it is resolved from the remotion project, not from here.
'use strict';
const fs = require('fs');

const [, , remotionDir, serveUrl, jobsPath, outPath, ...flags] = process.argv;
if (!remotionDir || !serveUrl || !jobsPath || !outPath) {
  console.error('usage: node glide_frames.cjs <remotion dir> <bundle dir> <jobs.json> <out.jsonl> [--gl=..] [--concurrency=N]');
  process.exit(2);
}
const opt = (name, dflt) => {
  const hit = flags.find((f) => f.startsWith(`--${name}=`));
  return hit ? hit.slice(name.length + 3) : dflt;
};
const R = require(require.resolve('@remotion/renderer', {paths: [remotionDir]}));
const TAG = 'TYPE-GLIDE ';

(async () => {
  const jobs = JSON.parse(fs.readFileSync(jobsPath, 'utf8'));
  const gl = opt('gl', 'angle');
  const concurrency = Number(opt('concurrency', '4'));
  const chromiumOptions = {gl};
  const out = fs.openSync(outPath, 'w');
  const write = (obj) => fs.writeSync(out, JSON.stringify(obj) + '\n');
  const browser = await R.openBrowser('chrome', {chromiumOptions, logLevel: 'error'});
  try {
    for (const job of jobs) {
      const t0 = Date.now();
      let logged = 0;
      try {
        const composition = await R.selectComposition({serveUrl, id: job.id, inputProps: job.props || {},
          puppeteerInstance: browser, chromiumOptions, logLevel: 'error'});
        const last = composition.durationInFrames - 1;
        const a = Math.max(0, job.from == null ? 0 : job.from);
        const b = Math.min(last, job.to == null ? last : job.to);
        await R.renderFrames({composition, serveUrl, inputProps: job.props || {}, imageFormat: 'none', outputDir: null,
          frameRange: [a, b], concurrency, puppeteerInstance: browser, chromiumOptions, logLevel: 'error',
          timeoutInMilliseconds: 120000, onStart: () => {}, onFrameUpdate: () => {},
          onBrowserLog: (log) => {
            const text = log && log.text;
            if (typeof text === 'string' && text.startsWith(TAG)) {
              write({tag: job.tag, ...JSON.parse(text.slice(TAG.length))});
              logged += 1;
            }
          }});
        write({tag: job.tag, done: true, frames: b - a + 1, logged, ms: Date.now() - t0});
      } catch (e) {
        write({tag: job.tag, error: String((e && e.message) || e).split('\n')[0].slice(0, 400), logged,
          ms: Date.now() - t0});
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
