#!/usr/bin/env node
// THE TYPE-GLIDE CENSUS, RENDERED — every frame of a composition walked, with no picture taken.
//
//   node glide_frames.cjs <remotion dir> <bundle dir> <jobs.json> <out.jsonl> [--gl=angle] [--concurrency=N]
//                         [--tag=MEDIA-RES_] [--every=N]   (a census other than the glide; every Nth frame)
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
// `--tag=` reads another census through the same runner (runtime/mediaRes.tsx logs `MEDIA-RES `)
const TAG = opt('tag', 'TYPE-GLIDE ').replace(/_/g, ' ');

// The renderer prints a thrown Error's message to this process's stderr ("[Tab 1, …] Error: …"); keep the last one so a
// cancelled job can say WHY instead of "a register threw".
let lastError = null;
const writeErr = process.stderr.write.bind(process.stderr);
process.stderr.write = (chunk, ...rest) => {
  const m = /\] (\w*Error: [^\n]+)/.exec(String(chunk));
  if (m) lastError = m[1].slice(0, 400);
  return writeErr(chunk, ...rest);
};

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
      // A REGISTER THAT THROWS ENDS THE JOB NOW. Measured: a beat whose register refuses its props (a declared ground
      // it does not follow) logged its Error on every tab and the census then waited out every frame's timeout —
      // 420 s, past the render lock's 300 s idle watchdog, so a delivery died as "a hung render" with the one
      // sentence that said why never shown. The first thrown Error cancels the job and is its `error`.
      const {cancelSignal, cancel} = R.makeCancelSignal();
      let thrown = null;
      try {
        const composition = await R.selectComposition({serveUrl, id: job.id, inputProps: job.props || {},
          puppeteerInstance: browser, chromiumOptions, logLevel: 'error'});
        const last = composition.durationInFrames - 1;
        const a = Math.max(0, job.from == null ? 0 : job.from);
        const b = Math.min(last, job.to == null ? last : job.to);
        await R.renderFrames({composition, serveUrl, inputProps: job.props || {}, imageFormat: 'none', outputDir: null,
          frameRange: [a, b], everyNthFrame: Number(opt('every', '1')), concurrency, puppeteerInstance: browser, chromiumOptions, logLevel: 'error',
          timeoutInMilliseconds: 120000, onStart: () => {}, onFrameUpdate: () => {},
          cancelSignal,
          onBrowserLog: (log) => {
            const text = log && log.text;
            // React reports a render that threw as console.error(errorObject): the log's text is only `JSHandle@error`,
            // and the sentence reaches us through the renderer's own stderr line (sniffed below).
            if (log && log.type === 'error' && typeof text === 'string'
                && (text === 'JSHandle@error' || /^(Uncaught )?\w*Error: /.test(text)) && thrown === null) {
              thrown = /^(Uncaught )?\w*Error: /.test(text) ? text.split('\n')[0].slice(0, 400) : (lastError || 'a register threw');
              cancel();
              return;
            }
            if (typeof text === 'string' && text.startsWith(TAG)) {
              write({tag: job.tag, ...JSON.parse(text.slice(TAG.length))});
              logged += 1;
            }
          }});
        write({tag: job.tag, done: true, frames: Math.floor((b - a) / Number(opt('every', '1'))) + 1, logged, ms: Date.now() - t0});
      } catch (e) {
        if (thrown === 'a register threw' && lastError) thrown = lastError;
        write({tag: job.tag, error: thrown || String((e && e.message) || e).split('\n')[0].slice(0, 400), logged,
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
