// THE FILM'S OWN VOICE, AS A SIGNAL A SHOT CAN DRAW.
//
// One register in this library claimed to be audio-reactive and was not: `VoiceSignal`'s header said it "reads
// the real narration via @remotion/media-utils visualizeAudio" while the package was not a dependency and the
// bars were three summed sines of the frame number. It looked like a waveform and was a screensaver — the
// giveaway is that it never went quiet, because nothing it drew had any relationship to whether anyone was
// speaking. That is the failure this module exists to make impossible: here the levels come from the beat's
// OWN mp3, so silence is silent and a stressed syllable is tall.
//
// WHY A RENDER PROP AND NOT A HOOK. `useAudioData` THROWS on a falsy src, and hooks cannot be called
// conditionally — so "use the narration if there is one" cannot be written as one hook. The branch has to be a
// component boundary, which is what `<Voice>` is. A shot rendered standalone (`npx remotion still`) or swept by
// `register_energy` has no narration and gets a deterministic synthetic voice instead, so every register stays
// renderable on its own; a shot inside a film gets the real thing with no authoring change, because the film
// provides the path through context.
//
// WHAT MAKES THE LEVELS HONEST. `visualizeAudio` normalises against the CLIP's peak sample, not the frame's, so
// a value is comparable across frames of the same beat: quiet passages read quiet. A per-frame normalisation
// (the obvious way to make bars look lively) would make silence as tall as a shout and put us straight back to
// the screensaver.

import React from 'react';
import {staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useAudioData, visualizeAudio} from '@remotion/media-utils';
import {ReducedMotionContext, SceneDurationContext, clamp01} from './motion';

/** The beat's narration file, RELATIVE to the served public dir — the same string `Film.tsx` hands to `<Audio>`,
 *  so the picture is analysing exactly the file the viewer is hearing. Null outside a film. */
export const NarrationContext = React.createContext<string | null>(null);

export type VoiceLevels = {
  /** `samples` values in 0..1, low frequency → high. */
  bars: number[];
  /** one number for the whole frame in 0..1 — loudness, for anything that pulses rather than bars. */
  level: number;
  /** true when these came from the film's real narration; false for the synthetic stand-in. */
  live: boolean;
};

// THE CURVE, MEASURED — NOT CHOSEN BY EYE. `visualizeAudio` divides each magnitude by the FFT half-size AND by
// the clip's own peak sample, so a raw bucket on real narration sits around 1e-3 (median) with a 1e-1 tail:
// drawn linearly the bars are invisible except on a plosive. Loudness is perceived compressively, so the
// mapping is a power law with a soft ceiling. The two constants were fitted to measured bucket distributions,
// not to taste — see tests/test_voice.py, which pins the properties they were fitted for.
//
// On four mastered edge-tts Chinese clips and one raw English one the curve ALONE lands the median bucket at
// 0.26 and a frame's tallest at ~0.7, peaking at 0.87 — a range that uses the picture without pinning to a
// flat ceiling. (The bars a register finally draws sit higher, because the tilt below is applied first; these
// are the curve's own numbers.) Two properties matter more than any of them:
//   · SILENCE IS SILENT. The 10th percentile of a frame's tallest bar is 0.000 across every clip measured — the
//     gaps between phrases really do read as gaps, which is the entire difference from the sine bank this
//     replaced.
//   · IT IS GAIN-INVARIANT. Attenuating a clip by 20 dB reproduces the distribution to three decimals, because
//     the normalisation is against that clip's own peak. So a register looks the same whether the film was
//     mastered by `tts.py` or handed a raw file, and a quiet voice is not a short waveform.
const CURVE_GAIN = 2.4;
const CURVE_EXP = 0.35;
const curve = (x: number) => Math.tanh(CURVE_GAIN * Math.pow(Math.max(0, x), CURVE_EXP));

// The FFT wants a power of two; a shot wants however many bars its composition has room for. Resolve the
// mismatch here rather than in every caller — asking `visualizeAudio` for 72 throws
// `The argument "bars" must be a power of two`, which is a crash a register author would meet at render time.
const binsFor = (n: number) => Math.min(256, 1 << Math.ceil(Math.log2(Math.max(8, n))));

/** Average `bins` down to `n` buckets. It never resamples UP by repetition, and that is a contract between
 *  three places, not a property of this function: `binsFor` caps at 256 because an FFT of a 30fps window has
 *  no more resolution to give, so `Voice` caps `samples` at the same 256 and every bucket then covers at
 *  least one bin. Ask for 400 bars without that cap and neighbouring buckets read the same bin — a fringe of
 *  identical twins that looks like an aliasing artefact and is one. */
function fold(src: number[], n: number): number[] {
  const out: number[] = [];
  for (let i = 0; i < n; i++) {
    const a = Math.floor((i / n) * src.length);
    const b = Math.max(a + 1, Math.floor(((i + 1) / n) * src.length));
    let s = 0;
    for (let k = a; k < b; k++) s += src[k] ?? 0;
    out.push(s / (b - a));
  }
  return out;
}

// TILT — the display correction every spectrum analyser has, and the reason this is a picture of a voice
// rather than a bass meter. Speech rolls off with frequency (roughly -6 dB an octave), so a bank drawn from
// raw magnitudes is three tall bars at one end and a flat line for the rest of its width: the thing on screen
// is dominated by the fundamental and says almost nothing about what is being said. A gain rising with
// frequency shows the spectrum's SHAPE instead. It is a display transform, not an invention: it is applied
// per bucket, it is monotone, and it multiplies — silence times any gain is still silence, which the tests
// check on the real pipeline rather than on `curve` alone.
//
// Measured on three narration clips, TILT = 6 lifts the median bar from 0.26 to 0.42 while the 10th
// percentile of a frame's mean stays exactly 0.000. The register it was fitted for lost two thirds of its ink
// when it stopped faking a permanently loud signal — most of that was a bass meter's empty width, and this is
// what gives it back honestly.
const TILT = 6;
const tilted = (bars: number[]) =>
  bars.map((v, i) => v * (1 + TILT * (i / Math.max(1, bars.length - 1))));

// THE SYNTHETIC STAND-IN is not decoration: it is what every standalone still and every energy sweep measures,
// so it has to behave like a voice rather than like a sine bank. Speech has a syllable rate (~4 Hz), a spectral
// tilt (low frequencies carry most of the energy), and — the part the old code missed entirely — GAPS. The
// envelope therefore drops to near zero between phrases, so a register that draws these bars is exercised
// against silence as well as against speech, which is exactly the case a live signal will hand it.
function synth(n: number, frame: number, fps: number, seed: number): number[] {
  const s = frame / Math.max(1, fps);
  const syll = 0.5 + 0.5 * Math.sin((s * 4.1 + seed * 0.7) * Math.PI * 2);
  // 1.60 is not a taste constant: with the 1.9 slope it puts the phrase envelope at zero for 18% of each
  // 2.4s cycle, which is roughly the share of a narrated beat that is actually between phrases. Pushed to
  // the obvious 0.55 the stand-in is silent 41% of the time and the register reads as broken half the time
  // it is measured; removed entirely it never stops, which is the defect this module replaced.
  const phrase = clamp01(Math.sin((s * 0.42 + seed * 0.31) * Math.PI * 2) * 1.9 + 1.60);
  const env = phrase * (0.35 + 0.65 * syll);
  return Array.from({length: n}, (_, i) => {
    const f = i / Math.max(1, n - 1);
    // gentle, because the LIVE path is tilt-compensated: a stand-in that kept a raw voice's -6 dB an
    // octave rolloff would draw a third of the bank the film draws, and the still would stop
    // describing the film again.
    const tilt = Math.exp(-f * 0.85);
    const grain = 0.55 + 0.45 * Math.sin(i * 1.7 + s * 9.3 + seed);
    return clamp01(env * tilt * grain * 3.6);
  });
}

// ONE LOUDNESS NUMBER, AND THE TWO PATHS MUST AGREE ON IT. `level` drives things a register modulates rather
// than draws — a label's opacity, a ring's swell — so if the synthetic stand-in and the real narration
// disagree about what "loud" means, a register pulses one way in a standalone still and another in the
// delivered film, and the still stops being evidence about the film. Each constant puts a typical speaking
// frame near 0.5: measured across four mastered Chinese clips and one raw English one the live mean-bar
// median is 0.463; across 400 frames of the stand-in it is 0.585.
//
// Those medians came from real narration and cannot be re-derived from a fixture, which is why the tests pin
// the ENDS (silence reaches zero, a loud frame reaches the top of the range) rather than the middle: what
// separates speech from a synthesised tone here is not its spectrum but its dynamics — a gated tone is either
// fully on or off, so its median frame IS its loudest, while a real voice spends most of its frames between
// the two. A fixture that reproduced that would be a model of speech, and the numbers would then be measuring
// the model.
const LIVE_LEVEL = 1.08;
const SYNTH_LEVEL = 0.85;
const levelOf = (bars: number[], k: number) =>
  clamp01((bars.reduce((a, b) => a + b, 0) / Math.max(1, bars.length)) * k);

/** The frame the SOUND is at. Audio runs in real time, so this is the raw frame — NOT `useT`, which compresses
 *  the shot's animation into the window between cross-dissolves and would slide the picture out of sync with
 *  the voice it is drawing. Under reduced motion it freezes, like every other clock in this library, at a frame
 *  inside the shot's own body rather than at 0 (which on a narrated beat is usually silence — a reduced-motion
 *  viewer would get a flat line and no idea what the shot was). */
function useSoundFrame(): number {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const sceneDur = React.useContext(SceneDurationContext);
  const reduced = React.useContext(ReducedMotionContext);
  if (!reduced) return frame;
  const dur = sceneDur ?? durationInFrames;
  return Math.max(0, Math.round((dur - 1) * 0.45));
}

const SynthVoice: React.FC<{samples: number; seed: number; children: (v: VoiceLevels) => React.ReactNode}> =
({samples, seed, children}) => {
  const frame = useSoundFrame();
  const {fps} = useVideoConfig();
  const bars = synth(samples, frame, fps, seed);
  return <>{children({bars, level: levelOf(bars, SYNTH_LEVEL), live: false})}</>;
};

const LiveVoice: React.FC<{src: string; samples: number; seed: number;
  children: (v: VoiceLevels) => React.ReactNode}> = ({src, samples, seed, children}) => {
  const frame = useSoundFrame();
  const {fps} = useVideoConfig();
  const data = useAudioData(staticFile(src));
  const bins = binsFor(samples);
  // `data` is null only on the very first render pass; `useAudioData` holds the frame open with delayRender
  // until the fetch lands, so nothing is ever CAPTURED from this branch. Falling back to the synthetic voice
  // rather than to zeros means that if that assumption ever stops holding, the frame shows a waveform instead
  // of a flat line — a wrong-looking shot is recoverable, a blank one is a delivered defect.
  // Too-short audio is the other real case: `visualizeAudio` throws when the clip has fewer samples than one
  // FFT window (~1.5ms of audio, so: a truncated or empty mp3). That is a broken asset, not a design case, and
  // it must not take the whole film down mid-render.
  let raw: number[] | null = null;
  if (data && data.channelWaveforms[0].length >= bins * 2) {
    raw = visualizeAudio({audioData: data, frame, fps, numberOfSamples: bins});
  }
  if (!raw) return <SynthVoice samples={samples} seed={seed}>{children}</SynthVoice>;
  const bars = tilted(fold(raw, samples)).map(curve);
  return <>{children({bars, level: levelOf(bars, LIVE_LEVEL), live: true})}</>;
};

/** Give me the voice for this beat.
 *
 *  ```tsx
 *  <Voice samples={72}>{({bars, level}) => <MyWaveform bars={bars} glow={level} />}</Voice>
 *  ```
 *
 *  Inside a film it is the beat's own narration; standalone it is a synthetic voice with the same shape, so the
 *  register renders — and is measured — either way. */
export const Voice: React.FC<{samples?: number; seed?: number;
  children: (v: VoiceLevels) => React.ReactNode}> = ({samples = 64, seed = 0, children}) => {
  const src = React.useContext(NarrationContext);
  const n = Math.max(1, Math.min(256, Math.round(samples)));   // see fold(): 256 is the FFT's resolution, not a style
  return src
    ? <LiveVoice src={src} samples={n} seed={seed}>{children}</LiveVoice>
    : <SynthVoice samples={n} seed={seed}>{children}</SynthVoice>;
};

// exported for the tests, which check the two properties that make this a signal rather than an ornament:
// silence stays low, and the synthetic stand-in has gaps.
export const _internals = {synth, fold, curve, binsFor, tilted, TILT, CURVE_GAIN, CURVE_EXP, levelOf, LIVE_LEVEL, SYNTH_LEVEL};
