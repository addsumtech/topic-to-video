// The device a DeviceDemo / DeviceHero beat is performed on — its geometry and its three looks.
//
// deviceGeometry() is THE one definition of where a device and its screen sit. The drawing below, the camera
// and the gestures in the registers, and scripts/device_geometry.py (the legibility gate) all use it; a parity
// test holds the Python port to it. Numbers come from deviceSpec.json, shared with the Python side.
import React from 'react';
import spec from './deviceSpec.json';
import {CONTENT_TOP, contentBottom} from './layout';
import {mix, type DesignDNA} from './dna';
import {keyOf} from './light';

export type DeviceKind = 'phone' | 'tablet' | 'laptop' | 'monitor';
export type DeviceLook = 'flat' | 'real' | 'screen';
export type Placement = 'center' | 'left' | 'right';
export type Rect = {x: number; y: number; w: number; h: number};
export type DeviceGeom = {
  kind: DeviceKind; look: DeviceLook; body: Rect; screen: Rect; bezel: number; radius: number;
  island: Rect | null; base: Rect | null; strip: Rect | null;
};

type Body = {bezel: number; radius: number; base: number; overhang: number; strip: number};
const RATIO = spec.screenRatio as Record<DeviceKind, number[]>;
const BODY = spec.body as Record<DeviceLook, Record<DeviceKind, Body>>;
const PLACE = spec.placementX as Record<Placement, number>;

export const isTouch = (kind: DeviceKind): boolean => Boolean((spec.touch as Record<string, boolean>)[kind]);

export const alpha = (hex: string, a: number): string => {
  const m = /^#([0-9a-f]{6})$/i.exec(String(hex || '').trim());
  if (!m) return hex;
  const n = parseInt(m[1], 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};

export const deviceGeometry = (kind: DeviceKind, look: DeviceLook, W: number, H: number,
                               placement: Placement = 'center', kicker = false): DeviceGeom => {
  const ratio = RATIO[kind], b = BODY[look]?.[kind];
  if (!ratio || !b) throw new Error(`device: no geometry for ${kind} / ${look}`);
  const [rw, rh] = ratio;
  const top = kicker ? CONTENT_TOP : Math.round(H * spec.zoneTopFrac);
  const zoneH = Math.max(1, contentBottom(W, H) - top);
  const zoneW = W * spec.zoneWidthFill;
  const shPerSw = rh / rw;
  const bwPerSw = 1 + 2 * b.bezel + 2 * b.overhang;
  const bhPerSw = shPerSw * (1 + b.strip) + 2 * b.bezel + b.base;
  const sw = Math.min(zoneW / bwPerSw, zoneH / bhPerSw);
  const sh = sw * shPerSw;
  const bodyW = sw * bwPerSw, bodyH = sw * bhPerSw;
  const margin = (W - zoneW) / 2;
  const bodyX = Math.min(Math.max(W * PLACE[placement] - bodyW / 2, margin), W - margin - bodyW);
  const bodyY = top + (zoneH - bodyH) / 2;
  const sx = bodyX + sw * (b.overhang + b.bezel);
  const sy = bodyY + sw * b.bezel + sh * b.strip;
  const R = Math.round;
  const rect = (x: number, y: number, w: number, h: number): Rect => ({x: R(x), y: R(y), w: R(w), h: R(h)});
  const isl = spec.island;
  return {
    kind, look,
    body: rect(bodyX, bodyY, bodyW, bodyH),
    screen: rect(sx, sy, sw, sh),
    bezel: R(sw * b.bezel),
    radius: R(sw * b.radius),
    island: kind === 'phone' && look !== 'screen'
      ? rect(sx + (sw * (1 - isl.w)) / 2, sy + sw * isl.top, sw * isl.w, sw * isl.h) : null,
    base: b.base > 0 ? rect(bodyX, sy + sh + sw * b.bezel, bodyW, sw * b.base) : null,
    strip: b.strip > 0 ? rect(sx, sy - sh * b.strip, sw, sh * b.strip) : null,
  };
};

/** The look a beat gets when it names none: realistic on a dark ground, flat on a light one. */
export const defaultLook = (dna: DesignDNA | null): DeviceLook => (dna && keyOf(dna) === 'dark' ? 'real' : 'flat');

const INK_D0 = '#14171c', BG_D0 = '#eef1f4';
// @decor: the metal of a realistic device body — a material, not a reading about anything the film named
const METAL_HI = '#e6e9ee', METAL_MID = '#8b919a', METAL_LO = '#5c636d';

export const Device: React.FC<{g: DeviceGeom; dna: DesignDNA | null; children?: React.ReactNode}> = ({g, dna, children}) => {
  const ink = dna?.fg ?? INK_D0;
  const bg = dna?.bg ?? BG_D0;
  const s = g.screen;
  const hi = mix(METAL_HI, bg, 0.1), mid = mix(METAL_MID, bg, 0.1), lo = mix(METAL_LO, bg, 0.1);
  const shadow = g.look === 'real' ? `0 ${Math.round(s.h * 0.05)}px ${Math.round(s.h * 0.1)}px rgba(0,0,0,0.45)`
    : `0 ${Math.round(s.h * 0.03)}px ${Math.round(s.h * 0.07)}px ${alpha(ink, g.look === 'screen' ? 0.22 : 0.16)}`;
  const lid: Rect = {x: s.x - g.bezel, y: s.y - g.bezel, w: s.w + 2 * g.bezel, h: s.h + 2 * g.bezel};
  const panelTop = g.strip ? g.strip.y : s.y;
  return (
    <>
      {g.look !== 'screen' ? (
        <div style={{position: 'absolute', left: lid.x, top: lid.y, width: lid.w, height: lid.h,
          borderRadius: g.radius + g.bezel, background: g.look === 'real' ? '#050608' : ink,
          boxShadow: g.look === 'real'
            ? `0 0 0 ${Math.max(2, Math.round(g.bezel * 0.35))}px ${hi}, 0 0 0 ${Math.max(3, Math.round(g.bezel * 0.6))}px ${lo}, ${shadow}`
            : shadow}} />
      ) : (
        <div style={{position: 'absolute', left: s.x, top: panelTop, width: s.w, height: s.y + s.h - panelTop,
          borderRadius: g.radius, background: mix(bg, '#ffffff', 0.85), boxShadow: shadow}} />
      )}
      {g.strip ? (
        <div style={{position: 'absolute', left: g.strip.x, top: g.strip.y, width: g.strip.w, height: g.strip.h,
          background: mix(bg, ink, 0.06), borderRadius: `${g.radius}px ${g.radius}px 0 0`}}>
          {[0, 1, 2].map((i) => (   // @positional: a window's three buttons are the same three on every window
            <span key={i} style={{position: 'absolute', top: g.strip!.h * 0.32, left: g.strip!.h * (0.5 + i * 0.55),
              width: g.strip!.h * 0.36, height: g.strip!.h * 0.36, borderRadius: '50%', background: mix(bg, ink, 0.25)}} />
          ))}
        </div>
      ) : null}
      <div style={{position: 'absolute', left: s.x, top: s.y, width: s.w, height: s.h, overflow: 'hidden',
        borderRadius: g.strip ? `0 0 ${g.radius}px ${g.radius}px` : g.radius, background: '#000'}}>
        {children}
        {g.look === 'real' ? (
          <div style={{position: 'absolute', inset: 0, pointerEvents: 'none',
            background: 'linear-gradient(118deg, rgba(255,255,255,0.14), rgba(255,255,255,0) 38%)'}} />
        ) : null}
      </div>
      {g.island ? (
        <div style={{position: 'absolute', left: g.island.x, top: g.island.y, width: g.island.w, height: g.island.h,
          borderRadius: g.island.h, background: g.look === 'real' ? '#000000' : ink}} />
      ) : null}
      {g.base && g.kind === 'laptop' ? (
        <div style={{position: 'absolute', left: g.base.x, top: g.base.y, width: g.base.w, height: g.base.h,
          background: g.look === 'real' ? `linear-gradient(180deg, ${hi}, ${mid} 60%, ${lo})` : ink,
          clipPath: 'polygon(0 0, 100% 0, 97% 100%, 3% 100%)'}} />
      ) : null}
      {g.base && g.kind === 'monitor' ? (
        <>
          <div style={{position: 'absolute', left: g.base.x + g.base.w * 0.44, top: g.base.y, width: g.base.w * 0.12,
            height: g.base.h * 0.82, background: g.look === 'real' ? `linear-gradient(90deg, ${lo}, ${hi}, ${lo})` : ink}} />
          <div style={{position: 'absolute', left: g.base.x + g.base.w * 0.32, top: g.base.y + g.base.h * 0.82,
            width: g.base.w * 0.36, height: g.base.h * 0.18, borderRadius: g.base.h * 0.09,
            background: g.look === 'real' ? `linear-gradient(180deg, ${hi}, ${mid})` : ink}} />
        </>
      ) : null}
    </>
  );
};