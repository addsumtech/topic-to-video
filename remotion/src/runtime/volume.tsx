// VOLUME — light IN a volume, drawn as the line-of-sight integral a real one is: an aurora curtain (one folded sheet
// of emitting gas, field-aligned rays, coloured by the altitude it glows at), light shafts (sky through the gaps of
// an occluder, scattered by the air toward the lens), a nebula (a domain-warped emission cloud with dust in front of
// it), a flame (heat advected upward, coloured by temperature) and a layer (one glowing stratum — WorldStage's band).
//
// WHY A FRAGMENT SHADER (measured, 2026-10-24; tests/test_volume.py and the round-4 sheets hold the numbers).
// bench-aurora spent its largest build block on an SVG curtain and shipped "barcode rays on a flat wall": a sheet
// drawn as N rects is N bars, however soft. What makes a curtain read as gas is per-PIXEL: the sheet's crossings of a
// pixel's line of sight, each weighted by 1/|dX/ds| (an edge-on fold is a long path through the sheet, so it is bright
// — the fold brightens itself), a lower border that is sharp because the emission ends there, a top that fades. That
// integral is a loop over the sheet for every pixel, which is a fragment shader's whole job and a DOM's worst one.
//
// DETERMINISM — the rules this file keeps, each from the effects research (round2/fx_research.md):
//   * ONE GL backend per film (render_remotion pins it; remotion_segments.default_gl). The same frame on angle vs
//     swangle differs; on one backend it is bit-identical re-rendered.
//   * NO STATE SURVIVES A DRAW. A Canvas2D context that kept globalCompositeOperation between frames made 29 of 30
//     frames depend on render order. So every draw: sizes the buffer, sets the viewport, disables blending, clears,
//     sets EVERY uniform (arrays zero-padded — a uniform keeps its last value, so a draw that skipped one would inherit
//     the previous volume's keep-out), draws, and copies into the target with the 2D context's state reset.
//   * ONE CONTEXT PER TAB, shared by every volume on the page. A context per canvas meets Chrome's live-context limit
//     on a long film (the oldest is LOST — a blank canvas mid-film); a shared one never does. Compiled programs are
//     the only thing kept, and a program is a pure function of its source.
//   * Everything the shader sees is (spec, seed, seconds): `seconds` is frame / fps, never a clock.
//   * No context at all is a LOUD error (E9): a volume that silently draws nothing is a beat with its subject gone.
//
// NEVER OVER TYPE: `keepOut` rects (the type's boxes) are cleared inside the shader by the same feathered ellipses
// runtime/optics uses for a glow (volumeCore.keepOutRows).
import React from 'react';
import {useCurrentFrame, useVideoConfig} from 'remotion';
import {ReducedMotionContext} from './motion';
import {checkVolume, keepOutRows, linearRGB, curtainFit, AURORA_BANDS, AURORA_LOWER_KM, AURORA_TOP_KM,
  CURTAIN_DEPTH_SWING, NEBULA_EMISSION, blackbody, FLAME_KELVIN, VOLUME_MAX_KEEPOUT, VOLUME_MAX_BANDS, VOLUME_KEEP_FLOOR,
  checkBands,
  type VolumeSpec, type Rect, type Band} from './volumeCore';

export * from './volumeCore';

// ── GLSL (ES 1.00: runs in a WebGL1 or a WebGL2 context alike) ──────────────────────────────────────────────────
const VERT = `attribute vec2 a_p; void main(){ gl_Position = vec4(a_p, 0.0, 1.0); }`;

const COMMON = `
precision highp float;
uniform vec2 u_res;        // the drawing buffer, px
uniform vec2 u_box;        // the volume's box in layout px — every shape is sized in these, so res never changes it
uniform float u_time;      // seconds x speed
uniform float u_seed;
uniform float u_intensity;
uniform float u_fade;
uniform vec4 u_keep[${VOLUME_MAX_KEEPOUT}];
uniform float u_keepQ[${VOLUME_MAX_KEEPOUT}];
uniform int u_nkeep;
uniform float u_keepFloor;
uniform float u_soft;       // 1: the volume lives in a box in a world — its light thins out before the box's edges
vec2 boxPos(){ return vec2(gl_FragCoord.x, u_res.y - gl_FragCoord.y) / u_res * u_box; }
// Dave Hoskins' hash (no sin: the large-argument sin hash is precision-fragile)
float hash12(vec2 p){ vec3 p3 = fract(vec3(p.xyx) * 0.1031); p3 += dot(p3, p3.yzx + 33.33); return fract((p3.x + p3.y) * p3.z); }
float hash11(float p){ p = fract(p * 0.1031); p *= p + 33.33; p *= p + p; return fract(p); }
float vnoise(vec2 p){ vec2 i = floor(p), f = fract(p); vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash12(i), hash12(i + vec2(1.0, 0.0)), u.x), mix(hash12(i + vec2(0.0, 1.0)), hash12(i + vec2(1.0, 1.0)), u.x), u.y); }
float vnoise1(float x){ float i = floor(x), f = fract(x); float u = f * f * (3.0 - 2.0 * f); return mix(hash11(i), hash11(i + 1.0), u); }
float fbm(vec2 p){ float a = 0.5, s = 0.0; for (int i = 0; i < 5; i++){ s += a * vnoise(p); p = p * 2.03 + vec2(17.1, 9.7); a *= 0.5; } return s / 0.96875; }
float fbm3(vec2 p){ float a = 0.5, s = 0.0; for (int i = 0; i < 3; i++){ s += a * vnoise(p); p = p * 2.03 + vec2(17.1, 9.7); a *= 0.5; } return s / 0.875; }
float fbm1(float x){ float a = 0.5, s = 0.0; for (int i = 0; i < 4; i++){ s += a * vnoise1(x); x = x * 2.07 + 13.7; a *= 0.5; } return s / 0.9375; }
float keepOut(vec2 p){ float a = 1.0;
  for (int i = 0; i < ${VOLUME_MAX_KEEPOUT}; i++){ if (i >= u_nkeep) break; vec4 r = u_keep[i];
    float d = length((p - r.xy) / r.zw); float u = clamp((d - u_keepQ[i]) / max(1e-6, 1.0 - u_keepQ[i]), 0.0, 1.0);
    a *= u * u * (3.0 - 2.0 * u); }
  return u_keepFloor + (1.0 - u_keepFloor) * a; }
// linear light in, display out: an exposure into a soft shoulder (light saturates toward white like a sensor's, it
// does not clip into a flat plate), then the sRGB encode
float softBox(vec2 p){ vec2 u = p / u_box;
  float s = smoothstep(0.0, 0.16, u.x) * smoothstep(0.0, 0.16, 1.0 - u.x) * smoothstep(0.0, 0.06, u.y) * smoothstep(0.0, 0.1, 1.0 - u.y);
  return mix(1.0, s, u_soft); }
vec4 finish(vec3 lin, vec2 p){ vec3 c = 1.0 - exp(-lin * u_intensity); c = pow(clamp(c, 0.0, 1.0), vec3(1.0 / 2.2));
  return vec4(c * keepOut(p) * softBox(p) * u_fade, 1.0); }
`;

// THE CURTAIN. Each sheet is a ribbon hung along a path that folds: its screen x along the sheet, X(s), is a line
// plus two travelling waves big enough to turn it back on itself; its distance swings with the first wave a quarter
// turn out of phase (the ribbon curls toward and away from the lens), which scales its height and drops a near fold's
// lower edge. For each pixel the loop finds every segment of the sheet that crosses the pixel's column and adds that
// sheet point's emission at the pixel's altitude, x L/|dX/ds| — the path length through the sheet.
const CURTAIN = COMMON + `
uniform float u_k;          // px per km at the sheet's mean distance
uniform float u_yH;         // the horizon's y (box px, y down)
uniform float u_lowKm;
uniform float u_topKm;
uniform float u_x0;
uniform float u_x1;
uniform float u_surge;      // 0..1: a brightening that runs along the sheet
uniform float u_recede;     // how much farther the sheet's far end (s = 1) is: its scale there is (1 - recede)
uniform int u_sheets;
uniform vec4 u_band[${VOLUME_MAX_BANDS}];     // from, to, gain, 0
uniform vec3 u_bandCol[${VOLUME_MAX_BANDS}];
uniform int u_nband;
const int N = 220;
const float CAP = 5.0;
vec3 bandColour(float km, out float gain){
  vec3 c = vec3(0.0); gain = 0.0; float wsum = 0.0;
  for (int i = 0; i < ${VOLUME_MAX_BANDS}; i++){ if (i >= u_nband) break; vec4 b = u_band[i];
    // the emission turns from one band's colour to the next over up to ~60 km, as the sky does (no line at 200 km);
    // each BOUNDARY blends over a quarter of the thinner band beside it, so a thin band (the pink fringe) keeps its
    // colour and its neighbour's does not bleed into it (volumeCore.bandWeights is this, line for line)
    float th = b.y - b.x, thP = th, thN = th;
    for (int k = 0; k < ${VOLUME_MAX_BANDS}; k++){
      if (k == i - 1) thP = u_band[k].y - u_band[k].x;
      if (k == i + 1 && k < u_nband) thN = u_band[k].y - u_band[k].x; }
    float blL = min(30.0, 0.25 * min(th, thP)), blH = min(30.0, 0.25 * min(th, thN));
    float w = smoothstep(b.x - blL, b.x + blL, km) * (1.0 - smoothstep(b.y - blH, b.y + blH, km));
    if (i == 0) w = (1.0 - smoothstep(b.y - blH, b.y + blH, km)) * step(b.x - 6.0, km);
    c += u_bandCol[i] * w; gain += b.z * w; wsum += w; }
  if (wsum > 1e-4){ c /= wsum; gain /= wsum; }
  return c; }
void main(){
  vec2 p = boxPos();
  float L = u_x1 - u_x0;
  vec3 acc = vec3(0.0);
  vec3 glow = vec3(0.0);
  float sig = 0.035 * u_box.x;
  for (int j = 0; j < 3; j++){ if (j >= u_sheets) break;
    float fj = float(j);
    float ph = u_seed * 1.37 + fj * 2.1;
    float A1 = L * (0.088 - 0.014 * fj), A2 = L * 0.018, A0 = L * 0.11;
    float f1 = 2.2 + 0.45 * fj, f2 = 6.1 + 1.3 * fj;
    float w1 = 0.11 + 0.03 * fj, w2 = -0.19;
    float kj = u_k * (1.0 - 0.10 * fj);                   // a farther sheet: shorter, higher, fainter
    float bj = 1.0 - 0.35 * fj;
    float drift = u_time * (0.012 + 0.004 * fj);           // the rays travel along the arc
    float Xp = 0.0, kp = 0.0, hp = 0.0;
    for (int i = 0; i <= N; i++){
      float s = float(i) / float(N);
      float a1 = 6.2831853 * f1 * s + ph + w1 * u_time;
      // the sheet recedes toward its far end: its screen scale falls along it, so its far part is shorter, hangs
      // nearer the horizon and is compressed across the screen (perspective), where it overlaps itself more
      float persp = 1.0 - u_recede * s;
      float sx = (s - 0.5 * u_recede * s * s) / (1.0 - 0.5 * u_recede);
      float X = u_x0 + L * sx + persp * A1 * sin(a1) + A2 * sin(6.2831853 * f2 * s + ph * 1.7 + w2 * u_time)
        + A0 * sin(6.2831853 * 0.8 * s + ph * 0.6 + 0.03 * u_time);
      float k = kj * persp * (1.0 + ${CURTAIN_DEPTH_SWING.toFixed(3)} * cos(a1));
      float hl = u_lowKm + 4.0 * sin(6.2831853 * 3.3 * s + ph * 2.3 + 0.07 * u_time) + 6.0 * (fbm1(s * 5.0 + ph) - 0.5);
      if (i > 0){
        // the sheet's crossing of this column
        if ((p.x - Xp) * (p.x - X) <= 0.0 && abs(X - Xp) > 1e-5){
          float u = (p.x - Xp) / (X - Xp);
          float ss = (float(i - 1) + u) / float(N);
          float kk = mix(kp, k, u), hh = mix(hp, hl, u);
          float km = (u_yH - p.y) / kk;
          float slope = abs(X - Xp) * float(N);
          float path = min(CAP, persp * L / slope);
          // field-aligned rays: a ray is a column of the SHEET (a function of s, not of screen x), so a fold carries
          // its rays round with it; uneven, drifting, some reaching far higher than others
          float rn = fbm1(ss * 95.0 + drift * 60.0 + u_seed * 7.0 + fj * 31.0);
          float ray = 0.16 + 1.9 * pow(rn, 2.2);
          float env = 0.10 + 0.90 * smoothstep(0.30, 0.70, fbm1(ss * 3.4 + u_seed * 1.9 + fj * 4.3 + drift * 4.0));
          float reach = 70.0 + 230.0 * pow(fbm1(ss * 41.0 + drift * 25.0 + u_seed * 3.0 + 5.0), 1.6);
          float above = km - hh;
          float edge = smoothstep(-1.6, 1.6, above);                          // the abrupt lower border
          // brightest AT the lower border (the edge-on bottom of the sheet), the body fading up, a faint long tail
          float prof = 0.55 * exp(-max(0.0, above) / 5.0) + 0.85 * exp(-max(0.0, above) / 32.0)
            + 0.09 * exp(-max(0.0, above) / 170.0);
          float top = 1.0 - smoothstep(reach - 140.0, reach + 30.0, above);
          float streak = 0.78 + 0.44 * vnoise(vec2(ss * 420.0, km * 0.045 - u_time * 0.25));
          float surge = 1.0 + 1.6 * u_surge * smoothstep(0.0, 0.25, 1.0 - abs(ss - fract(0.15 + u_time * 0.05)) * 3.0);
          float gain;
          vec3 col = bandColour(km, gain);
          acc += col * gain * edge * prof * top * ray * env * streak * path * bj * surge * step(km, u_topKm + 40.0);
        }
        // the diffuse glow round the sheet (its light scattered a little: the curtain is not cut out of the sky)
        float dx = p.x - X;
        float kmG = (u_yH - p.y) / k;
        float aG = kmG - hl;
        float gainG;
        vec3 colG = bandColour(max(kmG, u_lowKm), gainG);
        float vert = smoothstep(-5.0, 2.0, aG) * (0.9 * exp(-max(0.0, aG) / 34.0) + 0.10 * exp(-max(0.0, aG) / 170.0));
        glow += colG * gainG * vert * exp(-dx * dx / (2.0 * sig * sig)) * bj;
      }
      Xp = X; kp = k; hp = hl;
    }
  }
  glow *= L / (float(N) * sig * 2.5066) * 0.006;
  gl_FragColor = finish(acc * 0.8 + glow, p);
}`;

// THE SHAFTS. The occluder (clouds, a canopy, the slats of a blind) stands between the lens and a bright sky round
// the source; the sky shows through its gaps, and the air between scatters that light toward the lens along each
// line from the source — the radial march below (GPU Gems 3, ch. 13, volumetric light scattering as a post-process).
const SHAFTS = COMMON + `
uniform vec2 u_src;          // the source, box px
uniform int u_occ;           // 0 clouds, 1 canopy, 2 slats
uniform float u_open;
uniform vec3 u_col;
uniform vec3 u_col2;
const int M = 72;
float occ(vec2 q){
  float s = u_box.y;
  if (u_occ == 2){
    // slats: tilted bars, the gap between them set by how open the blind is
    float ang = 0.18; vec2 r = vec2(cos(ang) * q.x - sin(ang) * q.y, sin(ang) * q.x + cos(ang) * q.y);
    float per = s * 0.085; float f = fract(r.y / per + 0.02 * fbm3(r / (s * 0.3)));
    float gap = mix(0.04, 0.62, u_open);
    return 1.0 - smoothstep(0.0, 0.035, f) * (1.0 - smoothstep(gap, gap + 0.035, f));
  }
  if (u_occ == 1){
    float n = fbm(q / (s * 0.07) + vec2(u_seed * 3.1, 0.0) + vec2(0.05, 0.02) * u_time);
    float th = mix(0.30, 0.66, u_open);
    return smoothstep(th - 0.05, th + 0.05, n);
  }
  vec2 drift = vec2(0.018, 0.004) * u_time;
  float n = fbm(q / (s * 0.26) + vec2(u_seed * 1.7, 2.3) + drift);
  float th = mix(0.30, 0.72, u_open);
  return smoothstep(th - 0.035, th + 0.035, n);
}
float sky(vec2 q){ vec2 d = (q - u_src) / u_box.y; float r2 = dot(d, d); return exp(-r2 / 0.05) + 0.05 * exp(-r2 / 0.4); }
void main(){
  vec2 p = boxPos();
  vec2 stp = (u_src - p) * (0.92 / float(M));
  float jit = hash12(p + u_seed) - 0.5;             // a per-pixel offset into the march: steps become grain, not rings
  vec2 q = p + stp * jit;
  // the AVERAGE along the line: a far pixel's line spends a smaller share of its length in the bright sky round the
  // source, so the shafts thin with distance the way light fanning out does
  float illum = 0.0;
  for (int i = 0; i < M; i++){
    q += stp;
    illum += (1.0 - occ(q)) * sky(q);
  }
  illum /= float(M);
  float dust = 0.72 + 0.56 * fbm3(p / (u_box.y * 0.35) + vec2(0.0, -0.012) * u_time + u_seed);
  float direct = (1.0 - occ(p)) * sky(p);
  float core = exp(-dot((p - u_src) / u_box.y, (p - u_src) / u_box.y) / 0.004);
  float distF = length(p - u_src) / length(u_box);
  vec3 col = mix(u_col, u_col2, clamp(distF * 1.4, 0.0, 1.0));
  vec3 lin = col * (illum * dust * 1.6 + direct * 0.18) + u_col * core * (1.0 - occ(u_src)) * 1.6;
  gl_FragColor = finish(lin, p);
}`;

// THE NEBULA. Domain-warped noise (fbm of fbm of fbm — Inigo Quilez's warp): gas that has been stirred, not tiled.
// Emission is hydrogen red, turning [O III] teal toward the hot star that ionises it; dust in front absorbs it in
// ragged lanes; stars sit in and behind it, dimmed where the dust is.
const NEBULA = COMMON + `
uniform vec3 u_c1;           // the outer emission (H-alpha)
uniform vec3 u_c2;           // the inner emission ([O III]), near the star
uniform vec3 u_c3;           // dust's own faint reflection
uniform vec2 u_star;
void main(){
  vec2 p = boxPos();
  float S = max(u_box.x, u_box.y);
  vec2 x = (p - 0.5 * u_box) / (S * 0.62) + vec2(u_seed * 0.71, u_seed * 0.37);
  float t = u_time * 0.006;
  vec2 q = vec2(fbm(x + vec2(0.0, 0.0) + t), fbm(x + vec2(5.2, 1.3) - t));
  vec2 r = vec2(fbm(x + 2.4 * q + vec2(1.7, 9.2) + 0.9 * t), fbm(x + 2.4 * q + vec2(8.3, 2.8) - 0.7 * t));
  float f = fbm(x + 2.2 * r);
  float envN = smoothstep(0.38, 0.7, fbm3(x * 0.45 + vec2(7.0, 2.0) + 0.6 * q));
  float dens = smoothstep(0.35, 0.92, f);
  dens = dens * dens * (0.5 + 0.9 * q.x) * envN;
  float dS = length((p - u_star) / S);
  float ion = exp(-dS / 0.16);
  vec3 em = mix(u_c1, u_c2, clamp(ion * 1.3 + 0.2 * r.y - 0.15, 0.0, 1.0)) * dens * 1.1;
  em += u_c2 * ion * ion * 0.35 * (0.4 + f) * (0.4 + envN);
  float dust = smoothstep(0.52, 0.78, fbm(x * 1.6 + 2.2 * r + vec2(11.0, 3.0)));
  em *= 1.0 - 0.88 * dust;
  em += u_c3 * dust * dens * 0.25;
  // stars: one per cell at most, on a jittered grid, brightness skewed (a few bright, many faint)
  vec2 cell = p / (S * 0.018);
  vec2 ci = floor(cell);
  float h = hash12(ci + u_seed * 11.0);
  vec2 sp = ci + vec2(hash12(ci + 3.1), hash12(ci + 7.7));
  float sd = length(cell - sp);
  float bright = pow(h, 9.0) * 1.8;
  vec3 star = vec3(1.0, 0.96, 0.9) * bright * exp(-sd * sd / 0.006) * (1.0 - 0.8 * dust);
  vec3 core = vec3(1.0, 0.97, 0.92) * (exp(-dS * dS / 0.00004) * 3.0 + exp(-dS / 0.02) * 0.25);
  gl_FragColor = finish(em + star + core, p);
}`;

// THE FLAME. Heat rises: turbulence is advected UP (noise sampled at y + t x speed), the body narrows and breaks into
// licks as it climbs, and its colour is a TEMPERATURE ramp through blackbody stops (ember red, flame orange, hot
// yellow-white core) — runtime/volumeCore blackbody.
const FLAME = COMMON + `
uniform vec2 u_base;
uniform float u_spread;
uniform vec3 u_t0;
uniform vec3 u_t1;
uniform vec3 u_t2;
void main(){
  vec2 p = boxPos();
  float w = u_spread * u_box.x;
  vec2 q = (p - u_base) / w;
  float up = -q.y;
  float n = fbm(vec2(q.x * 2.6 + u_seed, up * 1.9 - u_time * 1.7));
  float n2 = fbm(vec2(q.x * 5.3 - u_seed, up * 3.7 - u_time * 2.9));
  float sway = (n - 0.5) * 0.55 * max(0.0, up);
  float hw = 0.5 * (1.0 - smoothstep(-0.1, 2.6, up)) * (0.75 + 0.6 * n);
  float body = 1.0 - smoothstep(hw * 0.55, hw, abs(q.x + sway));
  float height = 1.0 - smoothstep(0.9, 2.4, up + 0.9 * (n2 - 0.5));
  float heat = body * height * smoothstep(-0.25, 0.05, up) * (0.65 + 0.7 * n2);
  vec3 col = heat < 0.5 ? mix(u_t0 * 0.15, u_t0, heat * 2.0) : (heat < 0.8 ? mix(u_t0, u_t1, (heat - 0.5) / 0.3)
    : mix(u_t1, u_t2, (heat - 0.8) / 0.2));
  vec3 lin = col * heat * 2.2;
  float g = exp(-dot(q - vec2(0.0, -0.5), q - vec2(0.0, -0.5)) / 0.9);
  lin += u_t0 * g * 0.22;
  gl_FragColor = finish(lin, p);
}`;

// THE LAYER. One glowing stratum (an auroral band, an airglow layer, a lit cloud deck): brightest along its middle,
// fading through soft top and bottom edges whose height wanders, with faint field-aligned rays drifting through it and
// ragged ends — never a rectangle's straight edge.
const LAYER = COMMON + `
uniform vec3 u_c1;
void main(){
  vec2 p = boxPos();
  vec2 u = p / u_box;
  float wob = 0.10 * (fbm1(u.x * 4.0 + u_seed + u_time * 0.03) - 0.5);
  float d = (u.y - 0.5 - wob) / 0.5;
  float prof = exp(-d * d / 0.09) * (1.0 - smoothstep(0.75, 1.0, abs(d)));
  float ends = smoothstep(0.0, 0.16 + 0.08 * fbm1(u.y * 3.0 + u_seed), u.x) * smoothstep(0.0, 0.16 + 0.08 * fbm1(u.y * 3.0 + 9.0 + u_seed), 1.0 - u.x);
  float rays = 0.7 + 0.6 * pow(fbm1(u.x * 22.0 + u_time * 0.15 + u_seed * 5.0), 1.6);
  float body = 0.6 + 0.8 * fbm3(vec2(u.x * 3.0 + u_seed, u.y * 2.0 - u_time * 0.04));
  gl_FragColor = finish(u_c1 * prof * ends * rays * body * 0.75, p);
}`;

const SOURCES = {curtain: CURTAIN, shafts: SHAFTS, nebula: NEBULA, flame: FLAME, layer: LAYER} as const;

// ── the shared context ──────────────────────────────────────────────────────────────────────────────────────────
type Prog = {prog: WebGLProgram; loc: Record<string, WebGLUniformLocation | null>};
type Ctx = {canvas: HTMLCanvasElement; gl: WebGLRenderingContext; buf: WebGLBuffer; progs: Map<string, Prog>};
let CTX: Ctx | null = null;

const compile = (gl: WebGLRenderingContext, type: number, src: string, name: string): WebGLShader => {
  const sh = gl.createShader(type);
  if (!sh) throw new Error(`volume: could not create a ${name} shader`);
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
    throw new Error(`volume: the ${name} shader did not compile: ${gl.getShaderInfoLog(sh)}`);
  }
  return sh;
};

const context = (): Ctx => {
  if (CTX && !CTX.gl.isContextLost()) return CTX;
  if (typeof document === 'undefined') throw new Error('volume: no document — a volume draws in the browser only');
  const canvas = document.createElement('canvas');
  const attrs: WebGLContextAttributes = {preserveDrawingBuffer: true, premultipliedAlpha: false, alpha: false,
    antialias: false, depth: false, stencil: false};
  const gl = (canvas.getContext('webgl2', attrs) ?? canvas.getContext('webgl', attrs)) as WebGLRenderingContext | null;
  if (!gl) {
    throw new Error('volume: this browser gave no WebGL context — the volume cannot be drawn. Render with the film\'s ' +
      'pinned --gl backend (remotion_segments.default_gl); never let a volume beat ship as an empty sky.');
  }
  const buf = gl.createBuffer();
  if (!buf) throw new Error('volume: could not create the quad buffer');
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, -1, 1, 1, -1, 1, 1]), gl.STATIC_DRAW);
  CTX = {canvas, gl, buf, progs: new Map()};
  return CTX;
};

const UNIFORMS = ['u_res', 'u_box', 'u_time', 'u_seed', 'u_intensity', 'u_fade', 'u_keep', 'u_keepQ', 'u_nkeep', 'u_keepFloor', 'u_soft',
  'u_k', 'u_yH', 'u_lowKm', 'u_topKm', 'u_x0', 'u_x1', 'u_surge', 'u_recede', 'u_sheets', 'u_band', 'u_bandCol', 'u_nband',
  'u_src', 'u_occ', 'u_open', 'u_col', 'u_col2', 'u_c1', 'u_c2', 'u_c3', 'u_star', 'u_base', 'u_spread', 'u_t0',
  'u_t1', 'u_t2'];

const program = (c: Ctx, form: keyof typeof SOURCES): Prog => {
  const got = c.progs.get(form);
  if (got) return got;
  const gl = c.gl;
  const prog = gl.createProgram();
  if (!prog) throw new Error('volume: could not create a program');
  gl.attachShader(prog, compile(gl, gl.VERTEX_SHADER, VERT, 'vertex'));
  gl.attachShader(prog, compile(gl, gl.FRAGMENT_SHADER, SOURCES[form], form));
  gl.bindAttribLocation(prog, 0, 'a_p');
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error(`volume: the ${form} program did not link: ${gl.getProgramInfoLog(prog)}`);
  const loc: Prog['loc'] = {};
  for (const u of UNIFORMS) loc[u] = gl.getUniformLocation(prog, u);
  const p = {prog, loc};
  c.progs.set(form, p);
  return p;
};

/** Everything a draw needs, resolved from a spec: plain numbers, so the draw is a pure function of them. */
export type VolumeDraw = {spec: VolumeSpec; box: {w: number; h: number}; seconds: number; fade: number;
  keepOut?: Rect[]; surge?: number;
  /** the volume is an object IN a world (a box, not the frame): its light thins out before the box's edges, so no
   *  side of the box is ever seen as a line (WorldStage) */
  soft?: boolean;
  /** curtain only: where its lower border and its top land (box px, y down), at the mean distance */
  curtain?: {yTop: number; yLow: number; x0?: number; x1?: number;
    /** how much farther the far end is (0 = the sheet faces the lens square; default 0.4) — the scale there is
     *  (1 - recede) of the near end's, which is the end curtainFit's scale describes */
    recede?: number}};

const pad = (rows: number[][], n: number, w: number) => {
  const a = new Float32Array(n * w);
  rows.slice(0, n).forEach((r, i) => r.forEach((v, j) => (a[i * w + j] = v)));
  return a;
};

/** Draw one volume into `target` at `res` of its box. Every piece of GL and 2D state the draw depends on is set here,
 *  on every call. */
export const drawVolume = (target: HTMLCanvasElement, d: VolumeDraw, res: number, where = 'volume') => {
  const spec = checkVolume(d.spec, where);
  const bw = Math.max(1, Math.round(d.box.w * res)), bh = Math.max(1, Math.round(d.box.h * res));
  const c = context();
  const gl = c.gl;
  if (c.canvas.width !== bw) c.canvas.width = bw;
  if (c.canvas.height !== bh) c.canvas.height = bh;
  const P = program(c, spec.form);
  gl.viewport(0, 0, bw, bh);
  gl.disable(gl.BLEND); gl.disable(gl.DEPTH_TEST); gl.disable(gl.SCISSOR_TEST); gl.disable(gl.CULL_FACE);
  gl.colorMask(true, true, true, true);
  gl.clearColor(0, 0, 0, 1);
  gl.clear(gl.COLOR_BUFFER_BIT);
  gl.useProgram(P.prog);
  gl.bindBuffer(gl.ARRAY_BUFFER, c.buf);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  const L = P.loc;
  const f1 = (n: string, v: number) => L[n] && gl.uniform1f(L[n], v);
  const i1 = (n: string, v: number) => L[n] && gl.uniform1i(L[n], v);
  const f2 = (n: string, a: number, b: number) => L[n] && gl.uniform2f(L[n], a, b);
  const f3 = (n: string, v: [number, number, number]) => L[n] && gl.uniform3f(L[n], v[0], v[1], v[2]);
  f2('u_res', bw, bh); f2('u_box', d.box.w, d.box.h);
  f1('u_time', d.seconds * spec.speed); f1('u_seed', spec.seed % 977); f1('u_intensity', spec.intensity);
  f1('u_fade', Math.max(0, Math.min(1, d.fade)));
  // keep-out: ALWAYS all rows, zero-padded (a uniform array keeps whatever the last volume drawn wrote into it)
  const rows = keepOutRows(d.keepOut, {x: 0, y: 0}, 1, where);
  if (L.u_keep) gl.uniform4fv(L.u_keep, pad(rows.map((r) => [r.cx, r.cy, Math.max(1e-3, r.rx), Math.max(1e-3, r.ry)]), VOLUME_MAX_KEEPOUT, 4));
  if (L.u_keepQ) gl.uniform1fv(L.u_keepQ, pad(rows.map((r) => [r.q]), VOLUME_MAX_KEEPOUT, 1));
  i1('u_nkeep', rows.length);
  f1('u_keepFloor', VOLUME_KEEP_FLOOR);
  f1('u_soft', d.soft ? 1 : 0);
  const cols = (spec.colors ?? []).map((h) => linearRGB(h, where));
  if (spec.form === 'curtain' || spec.form === 'layer') {
    const bands: Band[] = checkBands(spec.bands ?? AURORA_BANDS, where);
    const lowKm = spec.bands ? bands[0].to > AURORA_LOWER_KM && bands[0].from < AURORA_LOWER_KM ? AURORA_LOWER_KM : bands[0].from : AURORA_LOWER_KM;
    const topKm = spec.bands ? bands[bands.length - 1].to : AURORA_TOP_KM;
    const cv = d.curtain ?? {yTop: d.box.h * 0.08, yLow: d.box.h * 0.66};
    const fit = curtainFit(cv.yTop, cv.yLow, lowKm, topKm);
    f1('u_k', fit.k); f1('u_yH', fit.yHorizon); f1('u_lowKm', lowKm); f1('u_topKm', topKm);
    f1('u_x0', cv.x0 ?? -0.1 * d.box.w); f1('u_x1', cv.x1 ?? 1.1 * d.box.w);
    f1('u_surge', Math.max(0, Math.min(1, d.surge ?? 0)));
    f1('u_recede', Math.max(0, Math.min(0.7, cv.recede ?? 0.4)));
    i1('u_sheets', spec.sheets ?? 2);
    if (L.u_band) gl.uniform4fv(L.u_band, pad(bands.map((b) => [b.from, b.to, b.gain ?? 1, 0]), VOLUME_MAX_BANDS, 4));
    if (L.u_bandCol) gl.uniform3fv(L.u_bandCol, pad(bands.map((b) => linearRGB(b.color, where)), VOLUME_MAX_BANDS, 3));
    i1('u_nband', bands.length);
    f3('u_c1', cols[0] ?? linearRGB(bands[Math.min(1, bands.length - 1)].color, where));
  } else if (spec.form === 'shafts') {
    const src = spec.source ?? [0.78, -0.12];
    f2('u_src', src[0] * d.box.w, src[1] * d.box.h);
    i1('u_occ', ['clouds', 'canopy', 'slats'].indexOf(spec.occluder ?? 'clouds'));
    f1('u_open', spec.open ?? 0.5);
    f3('u_col', cols[0] ?? linearRGB('#ffe7c2', where));
    f3('u_col2', cols[1] ?? cols[0] ?? linearRGB('#ffc98a', where));
  } else if (spec.form === 'nebula') {
    const st = spec.star ?? [0.62, 0.42];
    f2('u_star', st[0] * d.box.w, st[1] * d.box.h);
    f3('u_c1', cols[0] ?? linearRGB(NEBULA_EMISSION.halpha, where));
    f3('u_c2', cols[1] ?? linearRGB(NEBULA_EMISSION.oiii, where));
    f3('u_c3', cols[2] ?? linearRGB(NEBULA_EMISSION.dust, where));
  } else if (spec.form === 'flame') {
    const b = spec.base ?? [0.5, 0.86];
    f2('u_base', b[0] * d.box.w, b[1] * d.box.h);
    f1('u_spread', spec.spread ?? 0.22);
    const temps = cols.length === 3 ? cols : FLAME_KELVIN.map((k) => linearRGB(blackbody(k), where));
    f3('u_t0', temps[0]); f3('u_t1', temps[1]); f3('u_t2', temps[2]);
  }
  gl.drawArrays(gl.TRIANGLES, 0, 6);
  // the copy: the target's 2D state RESET, every draw (the research's measured leak)
  if (target.width !== bw) target.width = bw;
  if (target.height !== bh) target.height = bh;
  const t2 = target.getContext('2d');
  if (!t2) throw new Error(`${where}: the volume's canvas gave no 2D context`);
  t2.setTransform(1, 0, 0, 1, 0, 0);
  t2.globalAlpha = 1;
  t2.globalCompositeOperation = 'copy';
  t2.filter = 'none';
  t2.imageSmoothingEnabled = false;
  t2.drawImage(c.canvas, 0, 0);
  t2.globalCompositeOperation = 'source-over';
};

/**
 * A VOLUME of light, filling its positioned parent (or `width` x `height` px). The canvas is SCREEN-blended over
 * whatever is under it — light adds to the sky, it does not paint over it — so put it on a ground, not under one.
 * `res` is the drawing-buffer scale (soft forms may draw at 0.5 and lose nothing; the curtain's rays want ~0.75+).
 * `blend: 'none'` leaves the canvas opaque for a parent that does its own blending (WorldStage's object wrapper).
 */
export const Volume: React.FC<{spec: VolumeSpec; width?: number; height?: number; res?: number; fade?: number;
  keepOut?: Rect[]; surge?: number; curtain?: VolumeDraw['curtain']; blend?: 'screen' | 'plus-lighter' | 'none';
  soft?: boolean;
  /** frame offset into the volume's own time (a stage beat continuing one volume) */
  timeFrom?: number; style?: React.CSSProperties; where?: string}> = ({spec, width, height, res = 0.75, fade = 1,
  keepOut, surge, curtain, blend = 'screen', soft = false, timeFrom = 0, style, where = 'Volume'}) => {
  const frame = useCurrentFrame();
  const {width: W, height: H, fps} = useVideoConfig();
  const reduced = React.useContext(ReducedMotionContext);
  const w = width ?? W, h = height ?? H;
  if (!(res > 0 && res <= 2)) throw new Error(`${where}: res must be in (0, 2], got ${res}`);
  const ref = React.useRef<HTMLCanvasElement>(null);
  // a reduced-motion render holds the volume still (the light is there; it does not move)
  const seconds = reduced ? 0 : (frame + timeFrom) / fps;
  const key = JSON.stringify([spec, w, h, res, fade, keepOut ?? null, surge ?? 0, curtain ?? null, soft, seconds]);
  React.useLayoutEffect(() => {
    if (!ref.current) return;
    drawVolume(ref.current, {spec, box: {w, h}, seconds, fade, keepOut, surge, curtain, soft}, res, where);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return <canvas ref={ref} aria-hidden data-volume={spec.form} style={{position: 'absolute', left: 0, top: 0,
    width: w, height: h, pointerEvents: 'none', mixBlendMode: blend === 'none' ? undefined : blend, ...style}} />;
};
