/* accents.js — small accent motions for a film page (the director path, SKILL.md step 6 "Accents"), each a PURE
 * function of time since the accent began (t, seconds) and a seed: the same t always gives the same frame, which is
 * what a page captured frame by frame needs (Math.random in a film page is a flash and a replay waiting to happen).
 *
 *   burst(t, {x, y, seed, colors, count, spread, power, life})  -> particles [{x, y, rot, scale, alpha, color, shape}]
 *   ring(t, {x, y, r0, r1, life})                               -> {r, alpha, width}  an expanding shockwave ring
 *   rays(t, {x, y, count, r0, len, life, seed})                 -> lines     [{x1, y1, x2, y2, alpha}]
 *   sparkle(t, {x, y, seed, count, radius, life})               -> stars     [{x, y, scale, alpha, rot}]
 *   A celebration (the 🎉 motion) = burst + ring + rays started on the same frame.
 *   pop(t, d)        -> {scale, alpha}   an element arriving (0.7 -> 1), NO overshoot
 *   drawOn(t, d)     -> 0..1             an underline / circle / tick drawing itself (stroke-dashoffset = 1 - value)
 *   countUp(t, from, to, d, decimals) -> number, rising monotonically and landing exactly on `to`
 *   blurSlide(t, i, {gap, d, rise, blur}) -> {y, blur, opacity}   the default text reveal for word i: one progress
 *                                    drives all three channels on one easing, words `gap` s apart (references/
 *                                    promo-shotcraft.md: "it surfaces out of focus" instead of "slides and fades")
 *   dealTimes(n, {first, last, rest}) -> [start s of each item ..., end s incl. the rest]   a batch that arrives
 *                                    faster and faster (first interval -> last interval), then rests
 *   drawParticles(ctx, particles)     -> draws burst() output on a 2D canvas
 *
 * NO OVERSHOOT, on purpose: an element that grows past full size and shrinks back is a picture going back, and
 * rewind_qa reports it (a Memphis film's label pops, 2026-11-17). Particles fly out and fade; nothing returns.
 * Usage in a page: <script src="accents.js"></script> then Accents.burst(...) inside window.seek(t).
 */
(function (root) {
  'use strict';
  function rng(seed) {                       // mulberry32: a tiny seeded PRNG
    var a = (seed >>> 0) || 1;
    return function () {
      a = (a + 0x6D2B79F5) >>> 0;
      var r = Math.imul(a ^ (a >>> 15), 1 | a);
      r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
  }
  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
  function easeOutCubic(p) { p = clamp01(p); return 1 - Math.pow(1 - p, 3); }

  var DEFAULT_COLORS = ['#ff5a5f', '#ffb400', '#00a699', '#3d7bff', '#9b5de5'];

  function burst(t, o) {
    o = o || {};
    // defaults tuned on a rendered sheet (2026-11-17): at 0.9pi / 900 the confetti stayed a puff on the card
    var life = o.life || 1.2, n = o.count || 36, spread = o.spread == null ? Math.PI * 1.25 : o.spread;
    var power = o.power || 1500, colors = o.colors || DEFAULT_COLORS, g = o.gravity == null ? 1400 : o.gravity;
    var drag = 2.2, out = [];
    if (t < 0 || t >= life) return out;
    var r = rng(o.seed == null ? 7 : o.seed);
    for (var i = 0; i < n; i++) {
      var ang = -Math.PI / 2 + (r() - 0.5) * spread;          // fan upward
      var v = power * (0.45 + 0.55 * r());
      var vx = Math.cos(ang) * v, vy = Math.sin(ang) * v;
      var k = (1 - Math.exp(-drag * t)) / drag;                // drag-integrated distance factor
      var x = (o.x || 0) + vx * k;
      var y = (o.y || 0) + vy * k + 0.5 * g * t * t * 0.6;
      var spin = (r() - 0.5) * 14;
      var fadeStart = life * 0.55;
      out.push({ x: x, y: y, rot: spin * t, scale: 0.6 + 0.6 * r(),
                 alpha: t < fadeStart ? 1 : clamp01(1 - (t - fadeStart) / (life - fadeStart)),
                 color: colors[i % colors.length], shape: r() < 0.5 ? 'rect' : 'circle' });
    }
    return out;
  }

  function ring(t, o) {
    o = o || {};
    var life = o.life || 0.6, r0 = o.r0 == null ? 10 : o.r0, r1 = o.r1 || 160;
    if (t < 0 || t >= life) return null;
    var p = easeOutCubic(t / life);                            // grows only, fades out
    return { x: o.x || 0, y: o.y || 0, r: r0 + (r1 - r0) * p, alpha: 1 - clamp01(t / life),
             width: (o.width || 6) * (1 - 0.7 * p) };
  }

  function rays(t, o) {
    o = o || {};
    var life = o.life || 0.35, n = o.count || 10, r0 = o.r0 == null ? 30 : o.r0, len = o.len || 70, out = [];
    if (t < 0 || t >= life) return out;
    var r = rng(o.seed == null ? 5 : o.seed), p = easeOutCubic(t / life);
    for (var i = 0; i < n; i++) {
      var a = (i / n) * Math.PI * 2 + (r() - 0.5) * 0.3;
      var inner = r0 + len * p, outer = r0 + len * Math.min(1, p * 1.6);   // both ends travel outward
      out.push({ x1: (o.x || 0) + Math.cos(a) * inner, y1: (o.y || 0) + Math.sin(a) * inner,
                 x2: (o.x || 0) + Math.cos(a) * outer, y2: (o.y || 0) + Math.sin(a) * outer,
                 alpha: 1 - clamp01((t / life - 0.5) / 0.5) });
    }
    return out;
  }

  function sparkle(t, o) {
    o = o || {};
    var life = o.life || 0.8, n = o.count || 5, rad = o.radius || 60, out = [];
    if (t < 0 || t >= life) return out;
    var r = rng(o.seed == null ? 11 : o.seed);
    for (var i = 0; i < n; i++) {
      var a = r() * Math.PI * 2, d = rad * (0.4 + 0.6 * r()), delay = r() * life * 0.3;
      var p = clamp01((t - delay) / (life - delay));
      if (t < delay) continue;
      out.push({ x: (o.x || 0) + Math.cos(a) * d, y: (o.y || 0) + Math.sin(a) * d,
                 scale: 0.3 + 0.7 * easeOutCubic(p),                 // grows only
                 alpha: p < 0.5 ? 1 : clamp01(1 - (p - 0.5) / 0.5),  // then fades
                 rot: p * 0.6 });
    }
    return out;
  }

  function pop(t, d) {
    var p = easeOutCubic(t / (d || 0.35));
    return { scale: 0.7 + 0.3 * p, alpha: clamp01(t / ((d || 0.35) * 0.6)) };
  }

  function drawOn(t, d) { return easeOutCubic(t / (d || 0.45)); }

  function countUp(t, from, to, d, decimals) {
    var v = from + (to - from) * easeOutCubic(t / (d || 1));
    var f = Math.pow(10, decimals || 0);
    return t >= (d || 1) ? to : Math.round(v * f) / f;
  }

  function blurSlide(t, i, o) {
    o = o || {};
    var gap = o.gap == null ? 0.13 : o.gap, d = o.d || 0.6;
    var p = easeOutCubic((t - i * gap) / d);
    return { y: (o.rise == null ? 0.38 : o.rise) * (1 - p),          // in em
             blur: (o.blur == null ? 18 : o.blur) * (1 - p),         // px
             opacity: p };
  }

  function dealTimes(n, o) {
    o = o || {};
    var first = o.first == null ? 0.3 : o.first, last = o.last == null ? 0.08 : o.last;
    var out = [], t = 0;
    for (var i = 0; i < n; i++) {
      out.push(t);
      var k = n > 1 ? i / (n - 1) : 1;
      t += first * Math.pow(last / first, k);                     // intervals shrink geometrically
    }
    out.push(out[n - 1] + (o.rest == null ? 0.5 : o.rest));      // the batch ends with a still rest
    return out;
  }

  function drawParticles(ctx, ps) {
    for (var i = 0; i < ps.length; i++) {
      var q = ps[i];
      ctx.save();
      ctx.globalAlpha = q.alpha; ctx.fillStyle = q.color;
      ctx.translate(q.x, q.y); ctx.rotate(q.rot); ctx.scale(q.scale, q.scale);
      if (q.shape === 'rect') ctx.fillRect(-6, -3, 12, 6);
      else { ctx.beginPath(); ctx.arc(0, 0, 4, 0, Math.PI * 2); ctx.fill(); }
      ctx.restore();
    }
  }

  var api = { burst: burst, ring: ring, rays: rays, sparkle: sparkle, pop: pop, drawOn: drawOn, countUp: countUp,
              blurSlide: blurSlide, dealTimes: dealTimes,
              drawParticles: drawParticles, rng: rng };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Accents = api;
})(this);
