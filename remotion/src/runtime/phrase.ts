// PHRASE STEPS — an authored push or pull arrives on the voice's clauses, in steps, instead of as a creep.
//
// WHY. craft_qa measured our films holding a frame still for 5.0 s (median longest still, 22 films) against 2.5 s on
// 28 published launch films; the holds were spread over 30+ registers and began about a third of the way into the
// beat. An authored push spread over an 18.8 s beat moved under what a viewer sees (espresso: still 9.8 s through a
// push). So the move becomes EVENTS: scripts/phrase_steps.py places each step on a clause onset, and between steps
// the frame does not move. (Steps on unauthored beats were measured and withdrawn — Film.tsx PhraseCamera.)
//
// THE CURVE. Each of the n steps takes total/n of extra scale over PHRASE_STEP_S on an ease-IN-out. An ease-out was
// tried first and measured: it starts at full speed (0 -> ~6 px a frame in one frame on a 9:16 film), and jitter_qa found
// type trembling 0.10-0.15 px against its own drawing in the first 0.3 s of EVERY step (one ERROR, nine WARN on a film
// that had none) — the same start the library's own camera moves avoid with easeInOutCubic. Steps only add (the camera leans in through the explanation and never pumps back out),
// and the sum is the `total` the caller derived from the beat's camera budget — never more.

export const PHRASE_STEP_S = 0.6;

const easeInOut = (x: number) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2);

/** Extra camera scale at film frame `f` of the beat for steps at `steps` seconds, summing to `total`. */
export const phraseExtra = (f: number, fps: number, steps: number[], total: number): number => {
  if (!steps.length || !(total > 0)) return 0;
  const t = f / fps;
  const each = total / steps.length;
  let extra = 0;
  for (const s of steps) {
    if (t <= s) break;
    extra += each * easeInOut(Math.min(1, (t - s) / PHRASE_STEP_S));
  }
  return Math.min(total, extra);
};
