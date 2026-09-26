// SHOT · DeviceHero — the product on its device, its screen shown whole: the beat that says "this is it".
// Family A. The device rises into place and, in the realistic look, turns a few degrees toward the viewer and
// settles; nothing is performed on it (that is DeviceDemo). The screen is the user's screenshot or recording,
// prepared by scripts/device_script.py, or — standalone — the register's own skeleton page with no text.
import React from 'react';
import {AbsoluteFill, useVideoConfig} from 'remotion';
import {useT, seg, easeOutCubic, ENTRY_T} from '../runtime/motion';
import {useDNA, mix} from '../runtime/dna';
import {TITLE_Y} from '../runtime/layout';
import {deviceGeometry, defaultLook, Device, type DeviceKind, type DeviceLook, type Placement} from '../runtime/device';
import {ScreenImage, ScreenVideo, type VideoSpan} from '../runtime/screen';

export const DURATION = 150;

type HeroScreen = {image?: string; imageW?: number; imageH?: number; video?: string; spans?: VideoSpan[]; page?: 'demo'};

export const DeviceHero: React.FC<{
  device?: DeviceKind;   // phone | tablet | laptop | monitor
  look?: DeviceLook;     // flat | real | screen — absent: real on a dark beat, flat on a light one
  screen?: HeroScreen;   // the screenshot or recording, prepared by scripts/device_script.py
  placement?: Placement; // center | left | right
  kicker?: string;       // an optional spaced label above the device
}> = ({device = 'laptop', look, screen: SCREEN = {page: 'demo'}, placement = 'center', kicker = ''} = {}) => {
  const t = useT();
  const {width: W, height: H} = useVideoConfig();
  const dna = useDNA();
  const lk: DeviceLook = look ?? defaultLook(dna);
  const g = deviceGeometry(device, lk, W, H, placement, Boolean(kicker));
  const s = g.screen;
  const enter = easeOutCubic(seg(t, ENTRY_T, 0.32));
  // THE ENTRANCE NEVER LEAVES THE RECT deviceGeometry FITTED INSIDE THE CONTENT ZONE. It used to slide up from
  // 4% of the frame below — and the geometry fills the zone exactly, so a laptop at 16:9 entered 35 px deep in
  // the caption band while half opaque — and its perspective, centred on the FRAME, pushed the turned device's
  // near corner below its own bottom edge even once settled. Now it grows upward from its bottom edge, the
  // perspective is centred on that edge (a point on it projects onto itself), and in the realistic look it is
  // drawn just small enough that its largest turn still fits: a turn of θ magnifies the near edge by
  // p / (p − k·(w/2)·sin θ), so a scale k ≤ p / (p + (w/2)·sin θ) keeps the projection inside the rect.
  const TURN_FROM = 14, TURN_TO = 5;                                    // degrees, the realistic look only
  const turn = lk === 'real' ? TURN_FROM - (TURN_FROM - TURN_TO) * enter : 0;
  const persp = Math.round(W * 1.2);
  const b = g.body, ox = b.x + b.w / 2, oy = b.y + b.h;
  const fit = lk === 'real' ? persp / (persp + (b.w / 2) * Math.sin((TURN_FROM * Math.PI) / 180)) : 1;
  const k = fit * (0.94 + 0.06 * enter);
  const demo = !SCREEN.image && !SCREEN.video && SCREEN.page === 'demo';
  if (!demo && !SCREEN.image && !SCREEN.video) {
    throw new Error("DeviceHero: `screen` needs an image, a recording, or page 'demo' — got " + JSON.stringify(SCREEN) +
      '. A screen with none of them used to draw the demo skeleton, as if the film had asked for it.');
  }
  if (SCREEN.video && !(SCREEN.spans && SCREEN.spans.length)) {
    throw new Error('DeviceHero: a recording needs its `spans` — scripts/device_script.py maps the beat onto the ' +
      'recording; without them the screen would be black.');
  }
  if (SCREEN.image && (!SCREEN.imageW || !SCREEN.imageH)) {
    throw new Error('DeviceHero: a screen image needs its size (`imageW`, `imageH`) — scripts/device_script.py ' +
      'reads it from the file; render through render_remotion.py.');
  }
  const content = SCREEN.image
    ? <ScreenImage src={SCREEN.image} imageW={SCREEN.imageW!} imageH={SCREEN.imageH!} w={s.w} h={s.h} />
    : SCREEN.video
      ? <ScreenVideo src={SCREEN.video} spans={SCREEN.spans!} w={s.w} h={s.h} />
      : (
        <div style={{position: 'absolute', left: 0, top: 0, width: s.w, height: s.h, background: dna?.surface ?? '#ffffff'}}>
          {Array.from({length: 6}).map((_, i) => (   // @decor: skeleton rows of the register's own demo screen — no film ever sees them
            <div key={i} style={{position: 'absolute', left: s.w * 0.08, top: s.h * (0.14 + i * 0.12), width: s.w * 0.84,
              height: s.h * 0.07, borderRadius: s.h * 0.012, background: mix(dna?.surface ?? '#ffffff', dna?.fg ?? '#14171c', 0.07)}} />
          ))}
        </div>
      );
  return (
    <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? '#eef1f4', perspective: persp,
      perspectiveOrigin: `${ox}px ${oy}px`}}>
      <AbsoluteFill style={{opacity: enter, transformOrigin: `${ox}px ${oy}px`,
        transform: `scale(${k}) rotateY(${turn}deg)`}}>
        <Device g={g} dna={dna}>{content}</Device>
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
