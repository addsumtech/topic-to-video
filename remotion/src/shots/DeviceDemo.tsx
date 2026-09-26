// SHOT · DeviceDemo — one operation, performed on a drawn device, on the words the narration says. Family A.
//
// THE ARGUMENT SHAPE: "here, this is what you do." A product film that says "search last week's feedback,
// open the summary, scroll to the pattern" makes a claim about an interface — that it works in these steps.
// This shows the product's OWN screens (the user's screenshots or recording) inside a phone, tablet, laptop
// or monitor, and performs each step when the voice names it
// (docs/superpowers/specs/2026-09-26-device-layer-design.md).
//
// The script is PREPARED before it reaches here (scripts/device_script.py): every target is a point on the
// screen, every step has its window (t0, ta, t1), every gesture its text height and the caption height it must
// reach, every typed field its box and colours. This register draws that schedule and invents none of it.
// Without `steps` it draws its own demo — skeleton bars on a code-drawn screen, no text — so a standalone
// preview renders and no demo copy exists that could leak into a film.

import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, useAnimSpan, ENTRY_T, ReducedMotionContext, clamp01, seg, easeInOutCubic, easeCursor} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {camAt, clampToPage, type CamKey} from '../runtime/pageCam2D';
import {textWidthPx, TITLE_Y} from '../runtime/layout';
import {deviceGeometry, deviceFace, defaultLook, isTouch, Device, type DeviceKind, type DeviceLook, type Placement, type Rect} from '../runtime/device';
import {ScreenImage, ScreenVideo, scrollRangePx, flingAt, type VideoSpan} from '../runtime/screen';
import {typeChunks, typedCount, caretOn, framesBetween, TapRipple, CursorArrow} from '../runtime/gesture';
import spec from '../runtime/deviceSpec.json';

export const DURATION = 180;

type Pt = [number, number];
type Field = {box: [number, number, number, number]; bg: string; ink: string; textFrac: number | null};
type ScreenSrc = {image?: string; video?: string; page?: 'demo'; from?: number; to?: number};
export type Step = {
  screen?: ScreenSrc; via?: 'push' | 'fade';
  type?: string | string[]; into?: Pt; tap?: Pt; click?: Pt; scroll?: number; drag?: {from: Pt; to: Pt};
  mark?: Pt; at?: number; video?: number;
  // written by scripts/device_script.prepare — never authored
  t0?: number; ta?: number; t1?: number; focus?: Pt; textFrac?: number; captionPx?: number;
  field?: Field; imageW?: number; imageH?: number; spans?: VideoSpan[];
};

const DEMO_STEPS: Step[] = [{screen: {page: 'demo'}}, {tap: [0.5, 0.355]}];
const KINDS = ['screen', 'type', 'tap', 'click', 'scroll', 'drag', 'mark'] as const;
const kindOf = (s: Step): string => KINDS.find((k) => k in s) ?? '';

/** The prepared schedule. A film's script carries it on EVERY step: one step without it used to re-time the
 *  whole script by an even spread, silently, and a tap drew nothing at the words the narration names. Only
 *  the standalone demo (no script given) is spread evenly. */
const scheduled = (steps: Step[], demo: boolean): Step[] => {
  if (demo) {
    const slot = (1 - ENTRY_T) / steps.length;
    return steps.map((s, i) => ({...s, t0: ENTRY_T + i * slot, ta: ENTRY_T + (i + 0.35) * slot, t1: ENTRY_T + (i + 0.9) * slot}));
  }
  steps.forEach((s, i) => {
    if (typeof s.t0 !== 'number' || typeof s.ta !== 'number' || typeof s.t1 !== 'number') {
      throw new Error(`DeviceDemo: step ${i + 1} has no prepared time (t0/ta/t1) — scripts/device_script.py ` +
        "prepares every step on the narration's words; a script without them would be re-timed by guesswork.");
    }
  });
  return steps;
};

/** The zoomed camera kept ON the device's face (its screen and bezel — runtime/device.tsx deviceFace): along
 *  an axis where the face is larger than the view, the view stays inside it; where it is smaller (a phone's
 *  width at 3x), the view centres on it. Clamped to the frame instead, a push-in near the device's top edge
 *  showed a third of the frame as empty background with the target pushed off-centre; clamped to the BODY, a
 *  laptop's base (wider than its lid) let a push-in on the lid's edge show 280 px of background beside it, and
 *  a monitor's stand let one on its bottom row show the stand's empty surround. Applied to the zoomed KEYS, so
 *  the move from rest stays one smooth path. */
const onDevice = (x: number, y: number, s: number, b: Rect, W: number, H: number): {x: number; y: number} => {
  const axis = (c: number, lo: number, len: number, half: number) =>
    len <= half * 2 ? lo + len / 2 : Math.min(Math.max(c, lo + half), lo + len - half);
  return {x: axis(x, b.x, b.w, W / 2 / s), y: axis(y, b.y, b.h, H / 2 / s)};
};

const DemoPage: React.FC<{w: number; h: number; ink: string; ground: string}> = ({w, h, ink, ground}) => (
  <div style={{position: 'absolute', left: 0, top: 0, width: w, height: h, background: ground}}>
    {Array.from({length: 7}).map((_, i) => (   // @decor: skeleton rows of the register's own demo screen — no film ever sees them
      <div key={i} style={{position: 'absolute', left: w * 0.08, top: h * (0.12 + i * 0.1), width: w * 0.84,
        height: h * 0.07, borderRadius: h * 0.012, background: mix(ground, ink, 0.07)}} />
    ))}
  </div>
);

export const DeviceDemo: React.FC<{
  device?: DeviceKind;   // phone | tablet | laptop | monitor
  look?: DeviceLook;     // flat | real | screen — absent: real on a dark beat, flat on a light one
  steps?: Step[];        // the script, prepared by scripts/device_script.py — absent: the register's own demo
  camera?: 'still';      // turn the legibility push-in off
  placement?: Placement; // where the device stands: center | left | right
  kicker?: string;       // an optional spaced label above the device
}> = ({device = 'phone', look, steps: STEPS = DEMO_STEPS, camera, placement = 'center', kicker = ''} = {}) => {
  const t = useT();
  const span = useAnimSpan();
  const reduced = React.useContext(ReducedMotionContext);
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  if (!Array.isArray(STEPS) || !STEPS.length || kindOf(STEPS[0]) !== 'screen') {
    throw new Error('DeviceDemo needs `steps` opening with a `screen` step — the device would arrive showing ' +
      'nothing. Write the script in the storyboard; scripts/device_script.py checks and schedules it.');
  }
  const steps = scheduled(STEPS, STEPS === DEMO_STEPS);
  const lk: DeviceLook = look ?? defaultLook(dna);
  const g = deviceGeometry(device, lk, W, H, placement, Boolean(kicker));
  const s = g.screen;
  const INK = dna?.fg ?? '#14171c', GROUND = dna?.bg ?? '#eef1f4', ACC = dna?.accent ?? '#3563e9';
  const BODY_FONT = dna?.fontBody ?? '"Inter", "Noto Sans SC", system-ui, sans-serif';
  const touch = isTouch(device);

  // ── which screen is up, and how far each long screenshot has scrolled ─────────────────────────────────
  const screens = steps.map((st, i) => ({st, i})).filter((x) => kindOf(x.st) === 'screen');
  const curIdx = Math.max(0, screens.reduce((acc, x, k) => ((x.st.t0 ?? 0) <= t ? k : acc), 0));
  const cur = screens[curIdx], prev = screens[curIdx - 1];
  const change = prev ? clamp01(seg(t, cur.st.t0!, cur.st.t1!)) : 1;
  const nextScreenAt = (i: number) => steps.findIndex((x, k) => k > i && kindOf(x) === 'screen');
  const offsetFor = (i: number): number => {
    const sc = steps[i];
    if (!sc.screen?.image || !sc.imageW || !sc.imageH) return 0;
    const range = scrollRangePx(sc.imageW, sc.imageH, s.w, s.h);
    const end = nextScreenAt(i) < 0 ? steps.length : nextScreenAt(i);
    let off = 0;
    for (let k = i + 1; k < end; k++) {
      const st = steps[k];
      if (kindOf(st) !== 'scroll') continue;
      const to = Math.min(range, off + (st.scroll ?? 0) * range);
      off = off + (to - off) * flingAt(seg(t, st.ta!, st.t1!));
    }
    return off;
  };
  const layer = (x: {st: Step; i: number}) => {
    const src = x.st.screen!;
    if (src.image) {
      if (!x.st.imageW || !x.st.imageH) {
        throw new Error('DeviceDemo: a screen image needs its size (`imageW`, `imageH`) — scripts/device_script.py ' +
          'reads it from the file; render through render_remotion.py.');
      }
      return <ScreenImage src={src.image} imageW={x.st.imageW} imageH={x.st.imageH} w={s.w} h={s.h} offsetPx={offsetFor(x.i)} />;
    }
    if (src.video) {
      if (!x.st.spans || !x.st.spans.length) {
        throw new Error('DeviceDemo: a recording needs its `spans` — scripts/device_script.py maps the beat onto ' +
          'the recording; without them the screen would be black.');
      }
      return <ScreenVideo src={src.video} spans={x.st.spans} w={s.w} h={s.h} />;
    }
    return <DemoPage w={s.w} h={s.h} ink={INK} ground={dna?.surface ?? '#ffffff'} />;
  };
  const push = cur.st.via !== 'fade';

  // ── the gestures of the current screen ────────────────────────────────────────────────────────────────
  const end = nextScreenAt(cur.i) < 0 ? steps.length : nextScreenAt(cur.i);
  const gestures = steps.slice(cur.i + 1, end);
  const P = (p: Pt) => ({x: p[0] * s.w, y: p[1] * s.h});
  const cursorAt = (): {x: number; y: number; press: number} | null => {
    if (touch) return null;
    let pos = {x: s.w * 0.72, y: s.h * 0.86}, press = 0, seen = false;
    for (const st of gestures) {
      const k = kindOf(st);
      if (k !== 'click' && k !== 'tap' && k !== 'drag') continue;
      seen = true;
      const from = k === 'drag' ? P(st.drag!.from) : P((st.click ?? st.tap)!);
      const to = k === 'drag' ? P(st.drag!.to) : from;
      if (t < st.t0!) break;
      if (t < st.ta!) {
        const u = easeCursor(seg(t, st.t0!, st.ta!));
        return {x: pos.x + (from.x - pos.x) * u, y: pos.y + (from.y - pos.y) * u, press: 0};
      }
      const v = easeInOutCubic(seg(t, st.ta!, st.t1!));
      press = k === 'drag' ? (t <= st.t1! ? 1 : 0) : clamp01(1 - Math.abs(t - st.ta!) / Math.max(1e-6, (st.t1! - st.ta!) * 0.3));
      pos = {x: from.x + (to.x - from.x) * v, y: from.y + (to.y - from.y) * v};
    }
    return seen ? {...pos, press} : null;
  };
  const overlays: React.ReactNode[] = [];
  gestures.forEach((st, n) => {
    const k = kindOf(st);
    const u = seg(t, st.ta!, st.t1!);
    const size = touch ? s.w * 0.14 : s.w * 0.06;
    if (k === 'tap' || k === 'click' || k === 'mark') {
      const p = P((st.tap ?? st.click ?? st.mark)!);
      overlays.push(<TapRipple key={`g${n}`} x={p.x} y={p.y} u={u} color={ACC} size={size} />);
    } else if (k === 'drag' && touch && t >= st.ta! && t <= st.t1!) {
      const a = P(st.drag!.from), b = P(st.drag!.to), v = easeInOutCubic(u);
      overlays.push(<TapRipple key={`g${n}`} x={a.x + (b.x - a.x) * v} y={a.y + (b.y - a.y) * v} u={0.5} color={ACC} size={size} />);
    } else if (k === 'scroll' && touch && u > 0 && u < 0.35) {
      const v = u / 0.35;
      overlays.push(<TapRipple key={`g${n}`} x={s.w * 0.5} y={s.h * (0.72 - 0.3 * v)} u={0.5} color={ACC} size={size} />);
    } else if (k === 'type' && t >= st.ta!) {
      const f = st.field;
      if (!f) throw new Error('DeviceDemo: a `type` step needs its `field` — scripts/device_script.py measures it.');
      const chunks = typeChunks(st.type!);
      const text = chunks.slice(0, typedCount(t, st.ta!, st.t1!, chunks)).join('');   // @truncates: the typing reveal — every chunk is on screen by t1
      const [x0, y0, x1, y1] = f.box;
      const fw = (x1 - x0) * s.w, fh = (y1 - y0) * s.h;
      const px = f.textFrac ? f.textFrac * s.w : fh * 0.42;
      const pad = Math.min(fw, fh) * 0.35, caretW = Math.max(2, px * 0.08);
      const inset = Math.min(fw, fh) * 0.12;
      const shift = Math.max(0, textWidthPx(text, px) - (fw - 2 * pad - caretW * 3));
      const lit = caretOn(t < st.t1! ? null : framesBetween(st.t1!, t, span, ENTRY_T), reduced);
      overlays.push(
        <div key={`g${n}`} style={{position: 'absolute', left: x0 * s.w + inset, top: y0 * s.h + inset,
          width: fw - 2 * inset, height: fh - 2 * inset, background: f.bg, overflow: 'hidden',
          borderRadius: (fh - 2 * inset) * 0.3}}>
          <div style={{position: 'absolute', left: pad - inset - shift, top: 0, height: '100%', display: 'flex',
            alignItems: 'center', whiteSpace: 'pre', color: f.ink, font: `500 ${px}px/1 ${BODY_FONT}`}}>
            {text}
            <span style={{display: 'inline-block', width: caretW, height: px * 1.15, marginLeft: caretW,
              background: ACC, opacity: lit ? 1 : 0}} />
          </div>
        </div>);
    }
  });
  const cursor = cursorAt();
  if (cursor) overlays.push(<CursorArrow key="cursor" x={cursor.x} y={cursor.y} size={s.w * 0.035} press={cursor.press} />);

  // ── the legibility push-in, computed from what prepare() measured ─────────────────────────────────────
  const keys: CamKey[] = [{at: 0, x: W / 2, y: H / 2, s: 1}];
  if (camera !== 'still' && !reduced) {
    steps.forEach((st, i) => {
      if (!st.focus || !st.textFrac || !st.captionPx) return;
      const zoom = Math.min(spec.maxZoom, Math.max(1, st.captionPx / (st.textFrac * s.w)));
      if (zoom <= 1.01) return;
      const f = onDevice(s.x + st.focus[0] * s.w, s.y + st.focus[1] * s.h, zoom, deviceFace(g), W, H);
      const last = keys[keys.length - 1];
      keys.push({at: st.t0!, x: last.x, y: last.y, s: last.s});
      keys.push({at: st.ta!, x: f.x, y: f.y, s: zoom});
      keys.push({at: st.t1!, x: f.x, y: f.y, s: zoom});
      const next = steps[i + 1];
      if (!next || !next.focus) keys.push({at: Math.min(1, st.t1! + (st.ta! - st.t0!)), x: W / 2, y: H / 2, s: 1});
    });
  }
  const cam = clampToPage(camAt(keys, t, easeInOutCubic), W, H, W, H);

  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? GROUND, overflow: 'hidden'}}>
      <AbsoluteFill style={{transformOrigin: '0 0',
        transform: `translate(${W / 2 - cam.x * cam.s}px, ${H / 2 - cam.y * cam.s}px) scale(${cam.s})`}}>
        <Device g={g} dna={dna}>
          {prev && change < 1 ? (
            <div style={{position: 'absolute', inset: 0, transform: push ? `translateX(${-change * s.w * 0.3}px)` : undefined}}>
              {layer(prev)}
            </div>
          ) : null}
          <div style={{position: 'absolute', inset: 0, opacity: push ? 1 : change,
            transform: push && prev ? `translateX(${(1 - change) * s.w}px)` : undefined}}>
            {layer(cur)}
          </div>
          {overlays}
        </Device>
      </AbsoluteFill>
      {kicker ? (
        <div style={{position: 'absolute', left: 0, right: 0, top: TITLE_Y, textAlign: 'center', color: dna?.dim ?? '#5b6472',
          font: `600 ${Math.round(Math.min(W, H) * 0.022)}px/1 ${dna?.fontMono ?? 'ui-monospace, monospace'}`,
          letterSpacing: dna?.labelSpacing ?? '0.12em', textTransform: dna?.uppercaseLabels ? 'uppercase' : 'none'}}>
          {kicker}
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
