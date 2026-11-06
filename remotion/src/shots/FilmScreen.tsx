// SHOT · Film Screen — a delivered film or a recording shown as ITSELF: playing on a program monitor at no more than its
// own pixels, from the second the beat names, its stretch marked on a scrub bar of the whole thing. It can come in
// close (`region`: part of the picture, still at its own pixels), mask the clip's own burned caption strip (`crop`), pin
// one note to a point of the picture by a leader, run the film's own beats past beneath it (`run`: one settled frame
// per beat, a steady strip — the film running), or light one frame per beat in turn beside it so their count is seen
// (`reel`). Built for the topic-to-video promo (2026-11-03), where showing the skill's real films as stills read as a
// slideshow (film_energy_qa motion p75 0.0027) and playing them was the single biggest lift.
//
// Every word is a prop (the film's `name`, the `note`); every picture is the film's own file, its size read off the file
// by render_remotion (register_props), never typed. With no clip the register draws its own text-free skeleton, which
// no film ever sees.
import React from 'react';
import {AbsoluteFill, Img, OffthreadVideo, Sequence, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {useT, seg, clamp01, easeOutCubic, easeInOutCubic, SceneDurationContext} from '../runtime/motion';
import {CONTENT_TOP, contentBottom, fitTextPx} from '../runtime/layout';
import {focusAt, checkFocusTrack, type FocusKey} from '../runtime/focusTrack';
import {useDNA, mix} from '../runtime/dna';
import {useCues, REACH_CUBIC} from '../runtime/cue';
import {drawOn} from '../runtime/draw';

export const DURATION = 180; // 6 s

/** the lean-in: the clip's content comes this much closer over the beat, inside its own frame */
const LEAN = 1.05;

/** a file in the film's own folder — a picture's or a clip's path, never copy the viewer reads */
type FilePath = string;
type Clip = {src: FilePath; w: number; h: number; seconds: number};
type Frames = {frames: FilePath[]; w: number};

export const FilmScreen: React.FC<{
  /** the film or recording — `src` in the film's public dir; `w`, `h`, `seconds` are read off the file by the render */
  video?: Clip;
  /** the second of the clip the beat starts on */
  from?: number;
  /** the film's own name, over the monitor (mono) */
  name?: string;
  /** share of the clip's height to mask off its bottom — a delivered film's burned caption strip (0.185 at 16:9) */
  crop?: number;
  /** a close-up: the part of the picture shown, as shares of its width (`w`) from its left and top (`x`, `y`) */
  region?: {x: number; y: number; w: number};
  /** the close-up FOLLOWS the action: its centre over the beat [{t: s into the beat, x, y: shares of the clip}] at
   *  the region's own size (runtime/focusTrack) — smoothed, and refused when it would whip across the frame */
  focusTrack?: FocusKey[];
  /** one line pinned to a point of the picture (`noteAt`, shares of the clip's frame) by a leader */
  note?: string;
  noteAt?: {x: number; y: number};
  /** the film's beats passing beneath, one settled frame each — `w` is the frames' own pixel width */
  run?: Frames;
  /** one frame per beat in a grid beside the monitor, lit in turn, the count under it */
  reel?: Frames;
}> = ({video, from = 0, name = '', crop = 0, region, focusTrack, note = '', noteAt, run, reel} = {}) => {
  const dna = useDNA();
  const t = useT();
  const cue = useCues();
  const frame = useCurrentFrame();
  const {width: W, height: H, fps, durationInFrames} = useVideoConfig();
  const dur = React.useContext(SceneDurationContext) ?? durationInFrames;
  const U = Math.min(W, H);
  const portrait = H > W;
  if (video && !(video.w > 0 && video.h > 0 && video.seconds > 0)) {
    throw new Error(`FilmScreen: the clip needs its size and length (w, h, seconds), got ${JSON.stringify(video)} — the render reads them off the file`);
  }
  if (video && (!(from >= 0) || from + dur / fps > video.seconds + 0.05)) {
    throw new Error(`FilmScreen: ${from}s + ${(dur / fps).toFixed(1)}s runs outside the clip (${video.seconds}s)`);
  }
  if (!(crop >= 0 && crop < 0.5)) throw new Error(`FilmScreen: \`crop\` is a share of the clip's height under 0.5, got ${crop}`);
  if (region && (!(region.w > 0) || region.x < 0 || region.y < 0 || region.x + region.w > 1)) {
    throw new Error(`FilmScreen: region ${JSON.stringify(region)} is outside the picture`);
  }
  if (focusTrack && !region) throw new Error('FilmScreen: a focus track moves a close-up — give it a `region` (its size)');
  if (focusTrack && region) checkFocusTrack(focusTrack, region, fps);
  for (const [k, f] of [['run', run], ['reel', reel]] as const) {
    if (f && (!Array.isArray(f.frames) || f.frames.length < 2 || !(f.w > 0))) {
      throw new Error(`FilmScreen: \`${k}\` needs 2+ frames and their pixel width`);
    }
  }
  const BG = dna?.bg ?? '#0d1117', FG = dna?.fg ?? '#e6edf3', DIM = dna?.dim ?? '#7d8590';
  const LINE = dna?.line ?? '#30363d', SURF = dna?.surface ?? '#161b22';
  const ACC = dna?.accent ?? '#e8590c', ACC2 = dna?.accent2 ?? '#0f766e';
  const MONO = dna?.fontMono ?? '"JetBrains Mono", ui-monospace, monospace';
  const top = CONTENT_TOP, bot = contentBottom(W, H);
  const side = Math.round(W * (portrait ? 0.06 : 0.05));

  // ── the frame's parts, top to bottom (landscape: the reel stands to the right) ──
  const vw0 = video ? video.w : 1920, vh0 = video ? video.h : 1080;
  const headH = name ? Math.round(U * 0.045) : 0;
  const barGap = Math.round(U * 0.022), barH = Math.max(4, Math.round(U * 0.006));
  const runH = run ? Math.round(U * (portrait ? 0.11 : 0.085)) : 0, runGap = run ? Math.round(U * 0.022) : 0;
  const reelBeside = !!reel && !portrait;
  const reelW = reel ? Math.round(portrait ? W - 2 * side : W * 0.3) : 0;
  const reelBelowH = reel && portrait ? Math.round(U * 0.5) : 0;
  const availW = W - 2 * side - (reelBeside ? reelW + U * 0.04 : 0);
  const availH = bot - top - headH - barGap - barH - runGap - runH - (reelBelowH ? reelBelowH + U * 0.03 : 0) - U * 0.01;
  // shown: the region's part of the picture (or all of it) above the masked caption strip
  const rw = region ? region.w : 1;
  const shownH = region ? Math.min(1 - crop - region.y, (rw * vw0 * 9) / 16 / vh0) : 1 - crop;
  // the close-up's place this frame: the board's region, or where the focus track has carried it (same size)
  const rgn = region && focusTrack
    ? {...region, ...focusAt(focusTrack, frame / fps, region, shownH, 1 - crop - shownH)} : region;
  const mwMax = Math.min(rw * vw0 / LEAN, availW, (availH / (shownH * vh0)) * (rw * vw0));
  const k = mwMax / (rw * vw0);                          // drawn px per clip px — ≤ 1/LEAN, so the lean-in stays sharp
  const vw = vw0 * k, vh = vh0 * k, mw = rw * vw, mh = shownH * vh;
  const mx = side + (availW - mw) / 2, my = top + headH + (availH - mh) / 2;
  const on = easeOutCubic(clamp01(seg(t, 0, 0.08)));
  const lean = 1 + (LEAN - 1) * easeInOutCubic(clamp01(t));
  const ox = rgn ? rgn.x + rgn.w / 2 : 0.5, oy = rgn ? rgn.y + shownH / 2 : (1 - crop) * 0.45;

  // ── the note ──
  const noteOn = note ? easeOutCubic(clamp01(seg(t, ...cue.win('note', 0.3, 0.45, REACH_CUBIC)))) : 0;
  const notePx = note ? fitTextPx(note, W * 0.3, Math.round(U * 0.028)) : 0;
  const px = noteAt ? mx + (noteAt.x - (rgn ? rgn.x : 0)) * vw : 0;
  const py = noteAt ? my + (noteAt.y - (rgn ? rgn.y : 0)) * vh : 0;
  const toRight = noteAt ? px < mx + mw / 2 : true;
  const nx = toRight ? Math.min(mx + mw - U * 0.02, px + mw * 0.28) : Math.max(mx + U * 0.02, px - mw * 0.28);
  const ny = Math.max(my + U * 0.04, py - mh * 0.16);

  // ── the run: the film's beats passing beneath, ~3.5 % of the short side a frame ──
  const runEl = run ? (() => {
    const tw = (runH * 16) / 9, gap = Math.round(U * 0.008), pitch = tw + gap, n = run.frames.length;
    if (tw > run.w * 1.02) throw new Error('FilmScreen: a run frame drawn past its own pixels');
    const shift = (frame * U * 0.0035) % (n * pitch);
    const ry = my + mh + barGap + barH + runGap;
    return (
      <div style={{position: 'absolute', left: mx, width: mw, top: ry, height: runH, overflow: 'hidden', opacity: on,
        borderRadius: 6, WebkitMaskImage: 'linear-gradient(90deg, transparent, #000 6%, #000 94%, transparent)'}}>
        {Array.from({length: Math.ceil(mw / pitch) + 2}, (_, j) => (
          <Img key={j} src={staticFile(run.frames[(Math.floor(shift / pitch) + j) % n])}
            style={{position: 'absolute', left: j * pitch - (shift % pitch), top: 0, width: tw, height: runH, borderRadius: 3,
              objectFit: 'cover', boxShadow: `0 0 0 1px ${LINE}`}} />
        ))}
      </div>
    );
  })() : null;

  // ── the reel: one frame per beat, lit in turn ──
  const reelEl = reel ? (() => {
    const n = reel.frames.length, cols = portrait ? 9 : 6, rows = Math.ceil(n / cols);
    const g = Math.round(U * 0.006);
    const tw = (reelW - (cols - 1) * g) / cols, th = (tw * 9) / 16;
    if (tw > reel.w * 1.02) throw new Error('FilmScreen: a reel frame drawn past its own pixels');
    const rx0 = portrait ? side : W - side - reelW;
    const ry0 = portrait ? my + mh + barGap + barH + U * 0.03 : my + (mh - (rows * th + (rows - 1) * g)) / 2;
    const lit = clamp01(seg(t, 0.12, 0.85)) * n;
    const countPx = Math.round(U * 0.026);
    return (
      <>
        {reel.frames.map((src, i) => {
          const l = clamp01(lit - i);
          return (
            <div key={i} style={{position: 'absolute', left: rx0 + (i % cols) * (tw + g), top: ry0 + Math.floor(i / cols) * (th + g),
              width: tw, height: th, borderRadius: 3, overflow: 'hidden', opacity: on * (0.25 + 0.75 * l),
              boxShadow: `0 0 0 ${l > 0.5 ? 2 : 1}px ${l > 0.5 ? ACC2 : LINE}`}}>
              <Img src={staticFile(src)} style={{width: tw, height: th, display: 'block', objectFit: 'cover'}} />
            </div>
          );
        })}
        {/* @fixed-text: the count of frames lit — the reel's own length, counted as it lights */}
        <div style={{position: 'absolute', left: rx0, top: ry0 + rows * (th + g) + U * 0.012, opacity: on,
          font: `600 ${countPx}px/1 ${MONO}`, color: DIM}}>{Math.round(Math.min(lit, n))}</div>
      </>
    );
  })() : null;

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? BG}}>
      {name ? (
        <div style={{position: 'absolute', left: mx, top: my - headH, width: mw, height: headH, display: 'flex',
          alignItems: 'center', gap: U * 0.012, opacity: on, font: `600 ${Math.round(U * 0.026)}px/1 ${MONO}`, color: FG,
          whiteSpace: 'nowrap', overflow: 'hidden'}}>
          <div style={{flex: 'none', width: U * 0.012, height: U * 0.012, borderRadius: '50%', background: ACC}} />
          {name}
        </div>
      ) : null}
      <div style={{position: 'absolute', left: mx, top: my, width: mw, height: mh, overflow: 'hidden', borderRadius: 10,
        background: '#000', opacity: on, boxShadow: `0 0 0 1px ${LINE}, 0 ${U * 0.02}px ${U * 0.06}px #0009`}}>
        {video ? (
          <Sequence from={0} durationInFrames={Math.max(1, dur)} layout="none">
            <OffthreadVideo src={staticFile(video.src)} muted trimBefore={Math.round(from * fps)}
              style={{position: 'absolute', left: -(rgn ? rgn.x : 0) * vw, top: -(rgn ? rgn.y : 0) * vh, width: vw,
                height: vh, transform: `scale(${lean})`, transformOrigin: `${ox * 100}% ${oy * 100}%`}} />
          </Sequence>
        ) : (
          <AbsoluteFill style={{background: mix(BG, SURF, 0.6)}}>
            {/* @decor: the skeleton's own panels — no film ever sees them */}
            {[0.12, 0.42, 0.66].map((y, i) => (
              <div key={i} style={{position: 'absolute', left: '8%', top: `${y * 100}%`, width: `${[52, 70, 38][i]}%`,
                height: `${[10, 6, 6][i]}%`, borderRadius: 6, background: mix(SURF, FG, 0.08 + 0.04 * i)}} />
            ))}
          </AbsoluteFill>
        )}
      </div>
      {/* the scrub bar: where this stretch sits in the whole clip */}
      <div style={{position: 'absolute', left: mx, width: mw, top: my + mh + barGap, height: barH, borderRadius: barH,
        background: SURF, boxShadow: `inset 0 0 0 1px ${LINE}`, opacity: on}}>
        {video ? <div style={{position: 'absolute', left: `${(from / video.seconds) * 100}%`, top: 0, bottom: 0, borderRadius: barH,
          width: `${((dur / fps) * clamp01(t) / video.seconds) * 100}%`, background: ACC}} /> : null}
      </div>
      {note && noteAt ? (
        <>
          <svg width={W} height={H} style={{position: 'absolute', inset: 0}}>
            <path d={`M ${px} ${py} L ${nx} ${ny}`} stroke={FG} strokeWidth={Math.max(2, U * 0.002)} {...drawOn(noteOn)} />
            <circle cx={px} cy={py} r={U * 0.008} fill={ACC} opacity={noteOn} />
          </svg>
          <div style={{position: 'absolute', top: ny - notePx * 0.9, ...(toRight ? {left: nx} : {right: W - nx}),
            padding: `${U * 0.01}px ${U * 0.016}px`, borderRadius: 8, background: mix(BG, '#000000', 0.2),
            boxShadow: `0 0 0 1px ${ACC}`, opacity: noteOn, font: `600 ${notePx}px/1.2 ${MONO}`, color: FG,
            whiteSpace: 'nowrap'}}>{note}</div>
        </>
      ) : null}
      {runEl}
      {reelEl}
    </AbsoluteFill>
  );
};
export default FilmScreen;
