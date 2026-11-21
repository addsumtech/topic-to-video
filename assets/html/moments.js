/* moments.js — the small, exact motions that make a film feel crafted: ONE element keeps its identity while it changes
 * what it means (a typed tag becomes a pill and takes its slot; the chosen option stays while the rest fall away; a
 * price is struck and replaced; a title steps down into its section's label). Every function is a PURE function of
 * the film's time t (seconds), like accents.js: the same t is always the same picture (SKILL.md step 6).
 *
 * Organised by what HAPPENS to the element, not by the effect:
 *   choose(t, o)    one option is chosen: a one-frame press, it turns solid, the others dim IN PLACE
 *   become(t, o)    a thing turns into another thing on ONE hard frame, holds, then travels to its slot
 *   demote(t, o)    a title steps down into the label of the section it opened (it stays on screen)
 *   change(t, o)    a value changes: the old one holds, is struck and greyed, the new one arrives
 *   slot(t, o)      a sentence stays still while the word in its slot cycles (each landed word readable)
 *   reel(t, o)      the same, as a vertical roll: neighbours blurred and grey, only the landed word in the accent
 *   lead(t, o)      one word first, huge; it shrinks into its place and the sentence forms around it
 *   follow(t, o)    the words that follow a lead word, pushed into their places
 *   underline(t, o) a marker stroke under a key word, drawn in ~10 frames
 *   scan(t, o)      a machine reading: a line at constant speed; each region is bracketed and named AFTER it passes
 *   lock(t, o)      corner brackets fly in and bite onto a target ("look here" without stopping the flow)
 *   lift(h)/land(t, o)  a card's body: the shadow left on the table grows and softens as it rises; a landing dip
 *   type(t, o)      typing at a human pace, the caret solid while typing; retype(t, o) the plain word deleted
 *   list(t, o)      list items finding their places while the whole list drifts (no frame is dead)
 *   strip(t, o)     subtraction: the UI evaporates layer by layer from the edges to the one thing that matters
 *   carry(t, o)     no cut: a line runs on, turns its corners and draws the next scene's frame
 * and two of this skill's own, built from the film's real material rather than from a recipe:
 *   morph.*         REAL-STATE MORPH: write the product's screen in two states (before / after an action) as HTML
 *                   with data-k keys; the browser lays both out, and the diff is choreographed by one grammar —
 *                   leavers dim in place, survivors travel on one curve, changed text is struck then replaced,
 *                   newcomers arrive after (small ones pop, large ones rise). The motion IS the product's behaviour.
 *   perform(t, o)   THE KEYWORD PERFORMS: on the narration's own word clock (timeline.json), a key word on screen
 *                   does what it says while it is spoken — a number counts to its value, "split" parts, "join"
 *                   closes, "no"/"never" strikes itself out, a key word is marked.
 *
 * Timings are in frames at 30 fps (F = 1/30 s) where they were tuned in frames. Many starting values were tuned in
 * video-shotcraft (github.com/Vincentwei1021/video-shotcraft, Apache-2.0; see NOTICE): the one-frame press and the
 * 5-frame solid flip, the 18 % floor for unchosen options, the 1-frame "become" cut, the 26-frame title demotion, the
 * 21-frame slot beat, the reel's 0.7·outQuint + 0.3·outBack, the 2.3x lead word, the 10-frame marker, the scan
 * lag, the contact shadow. They are starting points: judge them on the rendered frames of THIS film.
 *
 * THIS SKILL'S FLOOR (rewind_qa): a BIG element never grows past its size and shrinks back. Overshoot is allowed only
 * on small things (a chip, a bracket, a pill under ~200 px) and stays tiny; everything else settles.
 * Usage: <script src="moments.js"></script>, then inside window.seek(t): Moments.apply(el, Moments.choose(t, {...})[i]).
 */
(function (root) {
  'use strict';
  var F = 1 / 30;
  function clamp01(v) { return v < 0 ? 0 : v > 1 ? 1 : v; }
  function lerp(a, b, p) { return a + (b - a) * p; }
  function seg(t, t0, t1, ease) { var p = t1 > t0 ? clamp01((t - t0) / (t1 - t0)) : (t >= t1 ? 1 : 0); return ease ? ease(p) : p; }

  // ---- easing ---------------------------------------------------------------------------------------------------
  function bezier(x1, y1, x2, y2) {           // CSS cubic-bezier(x1, y1, x2, y2) as a function of progress
    function bx(s) { return 3 * x1 * s * (1 - s) * (1 - s) + 3 * x2 * s * s * (1 - s) + s * s * s; }
    function by(s) { return 3 * y1 * s * (1 - s) * (1 - s) + 3 * y2 * s * s * (1 - s) + s * s * s; }
    return function (p) {
      p = clamp01(p); if (p === 0 || p === 1) return p;      // exact ends: a held state is exactly still
      var lo = 0, hi = 1, s = p;
      for (var i = 0; i < 40; i++) { s = (lo + hi) / 2; if (bx(s) < p) lo = s; else hi = s; }
      return by(s);
    };
  }
  var E = {
    linear: function (p) { return clamp01(p); },
    outQuad: function (p) { p = clamp01(p); return p * (2 - p); },
    inQuad: function (p) { p = clamp01(p); return p * p; },
    outCubic: function (p) { p = clamp01(p); return 1 - Math.pow(1 - p, 3); },
    inCubic: function (p) { p = clamp01(p); return p * p * p; },
    outQuint: function (p) { p = clamp01(p); return 1 - Math.pow(1 - p, 5); },
    outExpo: function (p) { p = clamp01(p); return p === 1 ? 1 : 1 - Math.pow(2, -10 * p); },
    inOutSine: function (p) { p = clamp01(p); return -(Math.cos(Math.PI * p) - 1) / 2; },
    outBack: function (p, s) { p = clamp01(p); s = s == null ? 1.70158 : s; return 1 + (s + 1) * Math.pow(p - 1, 3) + s * Math.pow(p - 1, 2); },
    swift: bezier(0.4, 0, 0.2, 1),          // the general move
    travel: bezier(0.5, 0, 0.25, 1),        // one shared curve for position AND scale of a thing taking its slot
    demote: bezier(0.6, 0, 0.18, 1),        // decisive start, very soft landing
    shrink: bezier(0.5, 0, 0.05, 1),        // heavy in-out, no bounce (a lead word shrinking into its line)
    push: bezier(0.22, 0.8, 0.36, 1)        // fast start, long landing (words pushed into their slots)
  };
  E.reel = function (p) { return 0.7 * E.outQuint(p) + 0.3 * E.outBack(p); };
  // a damped spring from 0 to 1, t in seconds (mass 1; Remotion-style damping / stiffness)
  function spring(t, o) {
    o = o || {}; var k = o.stiffness || 100, c = o.damping || 10;
    if (t <= 0) return 0;
    var w = Math.sqrt(k), z = c / (2 * w);
    if (z >= 1) return 1 - Math.exp(-w * t) * (1 + w * t);
    var wd = w * Math.sqrt(1 - z * z);
    return 1 - Math.exp(-z * w * t) * (Math.cos(wd * t) + (z * w / wd) * Math.sin(wd * t));
  }

  // ---- choose: one of n options is chosen -------------------------------------------------------------------------
  // o: {at (s, the press), n, chosen, floor (0.18: the others' opacity), clear (s, optional: the others go to 0)}
  // -> per option {opacity, pressed (true on the ONE press frame), solid (0..1: blend the chosen to its solid look),
  //    scale}. The others NEVER move: an option that moves reads as the page reloading, not as "not chosen".
  function choose(t, o) {
    var at = o.at, out = [], floor = o.floor == null ? 0.18 : o.floor;
    for (var i = 0; i < o.n; i++) {
      if (i === o.chosen) {
        var pr = seg(t, at + F, at + 10 * F);
        out.push({ opacity: 1, pressed: t >= at && t < at + F, solid: seg(t, at + F, at + 6 * F),
                   scale: 1 + Math.sin(Math.PI * pr) * 0.04 });
      } else {
        var dim = lerp(1, floor, seg(t, at + F, at + 10 * F, E.outQuad));
        if (o.clear != null) dim *= 1 - seg(t, o.clear, o.clear + 9 * F, E.outQuad);
        out.push({ opacity: dim, pressed: false, solid: 0, scale: 1 });
      }
    }
    return out;
  }

  // ---- become: a thing turns into another on one hard frame, holds, travels to its slot --------------------------
  // o: {at (s, the cut), hold (s, 0.6), d (s, 14 f), from {x, y, w}, to {x, y, w}}   (top-left anchored; w = width)
  // -> {phase: 'before' | 'after', x, y, scale}: draw the SOURCE while phase is 'before', the RESULT from `at` on,
  //    placed at (x, y) with transform-origin 0 0. No cross-fade: a fade turns "it became" into "an effect".
  function become(t, o) {
    var hold = o.hold == null ? 0.6 : o.hold, d = o.d || 14 * F, t0 = o.at + hold;
    if (t < o.at) return { phase: 'before', x: o.from.x, y: o.from.y, scale: 1 };
    var p = seg(t, t0, t0 + d, E.travel), s1 = o.to.w / o.from.w;
    return { phase: 'after', x: lerp(o.from.x, o.to.x, p), y: lerp(o.from.y, o.to.y, p), scale: lerp(1, s1, p) };
  }

  // ---- demote: a title becomes its section's label ----------------------------------------------------------------
  // o: {at (s, it starts to step down: >= 0.6 s after it landed), d (26 f), from {x, y, size}, to {x, y, size}}
  // -> {x, y, scale, grow}: scale is to.size / from.size at the end; `grow` = when the section's content may start
  //    (12 f into the move: the content grows while the title is still flying — no dead frames between them).
  function demote(t, o) {
    var d = o.d || 26 * F, p = seg(t, o.at, o.at + d, E.demote);
    return { x: lerp(o.from.x, o.to.x, p), y: lerp(o.from.y, o.to.y, p),
             scale: lerp(1, o.to.size / o.from.size, p), grow: o.at + 12 * F };
  }

  // ---- change: a value changes (a price, a count, a status) -------------------------------------------------------
  // o: {at (s, the change; the old value must have been readable >= 18 f before)}
  // -> {old: {scale, grey (0..1), strike (0..1)}, next: {opacity, scale, y}}. The old value shrinks toward 0.6 as it
  //    is struck (6 f), the new one comes in from slightly large and settles (it only ever shrinks: no rewind).
  function change(t, o) {
    var p = seg(t, o.at, o.at + 6 * F, E.outCubic), q = seg(t, o.at + F, o.at + 13 * F, E.outCubic);
    return { old: { scale: lerp(1, 0.6, p), grey: p, strike: seg(t, o.at, o.at + 6 * F, E.outCubic) },
             next: { opacity: seg(t, o.at + F, o.at + 4 * F), scale: lerp(1.12, 1, q), y: lerp(0.25, 0, q) } };
  }

  // ---- slot / reel: the sentence stays, the word in its slot cycles ------------------------------------------------
  // slot o: {times: [s ...] when each word lands (>= 21 f apart), change (8 f), rise (px, 120), exit (px, 130)}
  // -> per word {y (px), blur (px), opacity}. Measure the slot from the WIDEST word and anchor the stem by its left
  //    edge (absolute, not flex-centred): a stem that moves with the word's width turns the list into noise.
  function slot(t, o) {
    var ch = o.change || 8 * F, rise = o.rise == null ? 120 : o.rise, ex = o.exit == null ? 130 : o.exit, out = [];
    for (var i = 0; i < o.times.length; i++) {
      var a = o.times[i], b = o.times[i + 1];
      var pin = seg(t, a - ch * 0.6, a, E.outCubic);        // arrives once the leaver is mostly gone
      var pout = b == null ? 0 : seg(t, b - ch, b - ch * 0.45, E.inCubic);
      var y = pout > 0 ? -ex * pout : rise * (1 - pin);
      var blur = pout > 0 ? 10 * pout : 14 * (1 - pin);
      out.push({ y: y, blur: blur, opacity: t < a - ch * 0.6 ? 0 : (1 - pout) * clamp01(pin * 3) });
    }
    return out;
  }
  // reel o: {times: [s] (one per change: word i+1 lands at times[i]), n (words), row (px), window (16 f)}
  // -> {offset (px: translateY of the strip), words: [{blur, opacity, tint (0..1 dim->accent)}]}
  function reel(t, o) {
    var w = o.window || 16 * F, p = 0, words = [];
    for (var i = 0; i < o.times.length; i++) p += E.reel(seg(t, o.times[i] - w, o.times[i]));
    for (var j = 0; j < o.n; j++) {
      var d = Math.abs(j - p);
      words.push({ blur: d < 1 ? 3 * d : 3 + 2 * Math.min(d - 1, 1),
                   opacity: d < 1 ? 1 - 0.65 * d : Math.max(0.1, 0.35 - 0.23 * (d - 1)),
                   tint: clamp01(1 - 2.4 * d) });
    }
    return { offset: -p * o.row, words: words };
  }

  // ---- lead / follow: one word first, then the sentence forms around it ------------------------------------------
  // lead o: {at (s), hold (12 f), from (2.3), push (1.06), d (12 f), slide (24 f), dx (px: how far right of its final
  //   place the word stands while centred)} -> {scale, x}. Pin transform-origin to THE WORD's centre and baseline,
  //   not the line box (or the baseline jitters as it shrinks).
  function lead(t, o) {
    var at = o.at, hold = o.hold || 12 * F, s0 = o.from || 2.3, pk = s0 * (o.push || 1.06), d = o.d || 12 * F;
    var scale = lerp(s0, pk, seg(t, at, at + hold, bezier(0.25, 1, 0.5, 1))) +
                (1 - pk) * seg(t, at + hold, at + hold + d, E.shrink);
    return { scale: scale, x: (o.dx || 0) * (1 - seg(t, at + hold, at + hold + (o.slide || 24 * F), E.shrink)) };
  }
  // follow o: {at (the lead's at), hold (12 f), i (1, 2, ...), delay (10 f), stagger (4 f), d (12 f)} -> {x (em), opacity}
  function follow(t, o) {
    var s = o.at + (o.hold || 12 * F) + (o.delay || 10 * F) + (o.i - 1) * (o.stagger || 4 * F);
    return { x: 0.5 * (1 - seg(t, s, s + (o.d || 12 * F), E.push)), opacity: seg(t, s, s + 2 * F) };
  }

  // ---- underline: a marker stroke -----------------------------------------------------------------------------------
  // o: {at (s: 4-8 f after the title landed), d (10 f)} -> 0..1 drawn. Sit it ~0.1 em under the glyphs; under an italic
  // it rises left to right with the slant (drawn the other way it reads fake at once).
  function underline(t, o) { return seg(t, o.at, o.at + (o.d || 10 * F), E.outCubic); }

  // ---- scan: a machine reading -------------------------------------------------------------------------------------
  // o: {t0, t1 (s: the line's run, CONSTANT speed), y0, y1 (px), regions: [{y, h}], gap (4 f), lag (5 f), cps (66)}
  // -> {y (the line), regions: [{fired, outset (px, 76 -> 0), labelChars}]}: a region fires when the line passes its
  //    lower edge; its brackets close from 76 px outside; its label types `lag` after (framed first, then named).
  function scan(t, o) {
    var y = lerp(o.y0, o.y1, seg(t, o.t0, o.t1)), out = [], prev = -1e9, gap = o.gap || 4 * F, lag = o.lag || 5 * F;
    for (var i = 0; i < o.regions.length; i++) {
      var r = o.regions[i];
      var ft = o.t0 + (r.y + r.h - o.y0) / (o.y1 - o.y0) * (o.t1 - o.t0);
      ft = Math.max(ft, prev + gap); prev = ft;
      out.push({ at: ft, fired: t >= ft, outset: 76 * (1 - spring(t - ft, { damping: 15, stiffness: 170 })),
                 labelChars: Math.max(0, Math.floor((t - ft - lag) * (o.cps || 66))) });
    }
    return { y: y, regions: out };
  }

  // ---- lock: brackets bite onto a target ---------------------------------------------------------------------------
  // o: {at, d (14 f), from (px, 1000)} -> {outset (px from the target's edge), flash (0..0.55 white over the target)}
  function lock(t, o) {
    var s = spring(t - o.at, { damping: 12, stiffness: 190 });
    var f = t < o.at + (o.d || 14 * F) * 0.7 ? 0 : 0.55 * Math.exp(-(t - o.at - (o.d || 14 * F) * 0.7) * 12);
    return { outset: (o.from || 1000) * (1 - s), flash: f };
  }

  // ---- lift / land: a body on a table ------------------------------------------------------------------------------
  // lift(h): h 0 (on the table) .. 1 (lifted) -> {y (px), scale, core: {alpha, blur}, ambient: {alpha, blur, dx, dy}}.
  // The shadow is a SEPARATE element that stays on the table (a box-shadow travels with the card and proves nothing).
  function lift(h) {
    h = clamp01(h);
    return { y: -28 * h, scale: 1 + 0.08 * h, core: { alpha: lerp(0.32, 0.14, h), blur: lerp(3, 25, h) },
             ambient: { alpha: lerp(0.09, 0.22, h), blur: lerp(14, 54, h), dx: 10 * h, dy: 18 * h } };
  }
  // land o: {at (s, contact)} -> scale: a 1 % dip for 2 f, back in 5 f (weight, without a bounce)
  function land(t, o) {
    if (t < o.at || t > o.at + 7 * F) return 1;
    return t < o.at + 2 * F ? lerp(1, 0.99, seg(t, o.at, o.at + 2 * F)) : lerp(0.99, 1, seg(t, o.at + 2 * F, o.at + 7 * F, E.outCubic));
  }

  // ---- type / retype ----------------------------------------------------------------------------------------------
  // type o: {at, text, step (3 f per char), seed (jitter: human, not a metronome)} -> {shown, caret ('solid'|'on'|'off'), done}
  function charTimes(text, at, step, seed) {
    var a = (seed >>> 0) || 7, ts = [], t = at;
    for (var i = 0; i < text.length; i++) {
      a = (a * 1664525 + 1013904223) >>> 0;
      t += step * (0.7 + 0.6 * (a / 4294967296)); ts.push(t);
    }
    return ts;
  }
  function type(t, o) {
    var ts = charTimes(o.text, o.at, o.step || 3 * F, o.seed), n = 0;
    while (n < ts.length && t >= ts[n]) n++;
    var end = ts.length ? ts[ts.length - 1] : o.at;
    var caret = t < end + 8 * F ? 'solid' : (Math.floor((t - end) / (8 * F)) % 2 ? 'off' : 'on');
    return { shown: o.text.slice(0, n), caret: caret, done: n === o.text.length, end: end };
  }
  // retype o: {at, plain, real, step (2 f), del (1.5 f), hesitate (12 f)} -> {shown, caret}: types the plain word,
  // hesitates (the caret blinks twice), deletes it, types the real claim faster with no hesitation.
  function retype(t, o) {
    var st = o.step || 2 * F, de = o.del || 1.5 * F, hz = o.hesitate || 12 * F;
    var a1 = o.at + o.plain.length * st, a2 = a1 + hz, a3 = a2 + o.plain.length * de;
    if (t < a1) return { shown: o.plain.slice(0, Math.floor((t - o.at) / st)), caret: 'solid' };
    if (t < a2) return { shown: o.plain, caret: Math.floor((t - a1) / (4 * F)) % 2 ? 'off' : 'on' };
    if (t < a3) return { shown: o.plain.slice(0, o.plain.length - Math.floor((t - a2) / de)), caret: 'solid' };
    var n = Math.min(o.real.length, Math.floor((t - a3) / (1.5 * F)));
    return { shown: o.real.slice(0, n), caret: n < o.real.length ? 'solid' : 'on' };
  }

  // ---- list: items find their places while the list drifts ---------------------------------------------------------
  // o: {at, i, stagger (10 f), d (24 f), drift (px/s, 24)} -> {y (px, incl. the drift), scale, blur, opacity}
  function list(t, o) {
    var s = o.at + o.i * (o.stagger || 10 * F), p = seg(t, s, s + (o.d || 24 * F)), e = E.outBack(p, 0.4);
    return { y: 44 * (1 - e) - (o.drift == null ? 24 : o.drift) * Math.max(0, t - o.at), scale: lerp(0.82, 1, Math.min(e, 1)),
             blur: 8 * (1 - E.outCubic(p)), opacity: clamp01(p * 2.2) };
  }

  // ---- strip: subtraction, from the edges inward -------------------------------------------------------------------
  // o: {at, layer (0 = outermost), stagger (4 f), d (14 f)} -> {opacity, push (0..1 of a 50-140 px move OUTWARD)}
  function strip(t, o) {
    var s = o.at + o.layer * (o.stagger || 4 * F), p = seg(t, s, s + (o.d || 14 * F), E.inCubic);
    return { opacity: 1 - p, push: p };
  }

  // ---- carry: a line that becomes the next scene's frame -----------------------------------------------------------
  // o: {at, path: [[x, y], ...] (right-angle corners), speed (px/s, 1020 = 34 px/frame)} -> {len, head: [x, y], done}
  function carry(t, o) {
    var L = 0, segs = [];
    for (var i = 1; i < o.path.length; i++) {
      var a = o.path[i - 1], b = o.path[i], l = Math.hypot(b[0] - a[0], b[1] - a[1]); segs.push([a, b, l]); L += l;
    }
    var len = Math.min(L, Math.max(0, (t - o.at) * (o.speed || 1020))), acc = 0, head = o.path[0];
    for (var j = 0; j < segs.length; j++) {
      if (acc + segs[j][2] >= len) { var q = (len - acc) / segs[j][2];
        head = [lerp(segs[j][0][0], segs[j][1][0], q), lerp(segs[j][0][1], segs[j][1][1], q)]; break; }
      acc += segs[j][2]; head = segs[j][1];
    }
    return { len: len, total: L, head: head, done: len >= L };
  }

  // ---- REAL-STATE MORPH (this skill's own) ------------------------------------------------------------------------
  // 1. Write the screen twice in the page, as two hidden containers with the SAME css: state A and state B, every
  //    element that matters carrying data-k="<key>" (the same key for the same thing in both states).
  // 2. In filmReady (after fonts): var A = Moments.morph.snapshot(a), B = Moments.morph.snapshot(b);
  //    var plan = Moments.morph.plan(A, B, {at: 3.2}); Moments.morph.stage(stageEl, plan);
  // 3. In seek(t): Moments.morph.draw(t, plan).
  // The grammar: LEAVERS (only in A) dim in place over 6 f (to `floor`, default 0: gone); SURVIVORS (in both) travel
  // A-rect -> B-rect on one curve (E.travel, 14 f) starting 4 f after the action, switching to their B look on that
  // frame (a hard switch, never a cross-fade); a survivor whose TEXT changed holds, is struck through and greyed, and
  // its new text rises in at the B place; NEWCOMERS (only in B) arrive after the survivors (from 12 f, 3 f apart),
  // a small one (< 120 px both ways) popping on a stiff spring, a large one rising 18 px out of a 6 px blur.
  function snapshot(container, attr) {
    attr = attr || 'data-k';
    var base = container.getBoundingClientRect(), out = {};
    var els = container.querySelectorAll('[' + attr + ']');
    for (var i = 0; i < els.length; i++) {
      var el = els[i], r = el.getBoundingClientRect(), k = el.getAttribute(attr);
      if (out[k]) throw new Error('moments.morph: key "' + k + '" appears twice in one state');
      out[k] = { el: el, x: r.left - base.left, y: r.top - base.top, w: r.width, h: r.height,
                 text: (el.textContent || '').replace(/\s+/g, ' ').trim() };
    }
    return out;
  }
  function plan(A, B, o) {
    o = o || {}; var at = o.at, items = [], keys = {}, k, n = 0;
    for (k in A) keys[k] = 1; for (k in B) keys[k] = 1;
    for (k in keys) {
      var a = A[k], b = B[k], kind = a && b ? (a.text !== b.text && b.el.children.length === 0 ? 'changed' : 'survivor')
                                         : a ? 'leaver' : 'newcomer';
      items.push({ key: k, kind: kind, a: a, b: b, order: kind === 'newcomer' ? n++ : 0 });
    }
    return { at: at, floor: o.floor || 0, items: items, travel: o.travel || 14 * F };
  }
  function cloneAt(src, r, stage) {
    var c = src.el.cloneNode(true);
    c.removeAttribute('data-k'); c.style.position = 'absolute'; c.style.margin = '0';
    var inner = c.querySelectorAll('[data-k]');                  // drawn by their own clones, not twice
    for (var i = 0; i < inner.length; i++) inner[i].parentNode.removeChild(inner[i]);
    c.style.left = r.x + 'px'; c.style.top = r.y + 'px'; c.style.width = r.w + 'px'; c.style.height = r.h + 'px';
    c.style.boxSizing = 'border-box'; c.style.transformOrigin = '0 0';
    stage.appendChild(c); return c;
  }
  function stage(stageEl, p) {
    for (var i = 0; i < p.items.length; i++) {
      var it = p.items[i];
      if (it.a) it.ca = cloneAt(it.a, it.a, stageEl);
      if (it.b) it.cb = cloneAt(it.b, it.b, stageEl);
      if (it.kind === 'changed') { it.strike = document.createElement('div');
        it.strike.style.cssText = 'position:absolute;height:3px;background:currentColor;transform-origin:0 50%;';
        it.ca.appendChild(it.strike); it.strike.style.left = '0'; it.strike.style.width = '100%'; it.strike.style.top = '50%'; }
    }
    return p;
  }
  function place(c, own, r, opacity) {   // a box morphs by its size (its text keeps its size and reflows), never by scale
    c.style.width = r.w + 'px'; c.style.height = r.h + 'px';
    c.style.transform = 'translate(' + (r.x - own.x) + 'px,' + (r.y - own.y) + 'px)';
    c.style.opacity = String(opacity);
  }
  function draw(t, p) {
    var at = p.at, t0 = at + 4 * F;
    for (var i = 0; i < p.items.length; i++) {
      var it = p.items[i], a = it.a, b = it.b;
      if (it.kind === 'leaver') {
        place(it.ca, a, a, lerp(1, p.floor, seg(t, at, at + 6 * F, E.outCubic)));
      } else if (it.kind === 'survivor') {
        var q = seg(t, t0, t0 + p.travel, E.travel);
        var r = { x: lerp(a.x, b.x, q), y: lerp(a.y, b.y, q), w: lerp(a.w, b.w, q), h: lerp(a.h, b.h, q) };
        var onB = t >= t0;
        place(it.ca, a, r, onB ? 0 : 1); place(it.cb, b, r, onB ? 1 : 0);
      } else if (it.kind === 'changed') {          // it rides with its container, is struck, then replaced
        var q2 = seg(t, t0, t0 + p.travel, E.travel), st = seg(t, at, at + 6 * F, E.outCubic);
        var nx = seg(t, at + 11 * F, at + 21 * F, E.outCubic);
        it.strike.style.transform = 'scaleX(' + st + ')';
        place(it.ca, a, { x: lerp(a.x, b.x, q2), y: lerp(a.y, b.y, q2), w: a.w, h: a.h },
              lerp(1, 0.45, st) * (1 - seg(t, at + 7 * F, at + 11 * F)));
        place(it.cb, b, { x: b.x, y: lerp(a.y, b.y, q2) + 12 * (1 - nx), w: b.w, h: b.h }, seg(t, at + 11 * F, at + 14 * F));
      } else {
        var s0 = at + 12 * F + it.order * 3 * F, small = b.w < 120 && b.h < 120;
        if (small) {
          var sp = spring(t - s0, { damping: 13, stiffness: 220 }), sc = t < s0 ? 0 : lerp(0.4, 1, sp);
          it.cb.style.transformOrigin = '50% 50%';
          it.cb.style.transform = 'scale(' + sc + ')'; it.cb.style.opacity = String(seg(t, s0, s0 + 3 * F));
        } else {
          var u = seg(t, s0, s0 + 14 * F, E.outExpo);
          place(it.cb, b, { x: b.x, y: b.y + 18 * (1 - u), w: b.w, h: b.h }, seg(t, s0, s0 + 5 * F));
          it.cb.style.filter = u < 1 ? 'blur(' + (6 * (1 - u)).toFixed(2) + 'px)' : 'none';
        }
      }
    }
  }

  // ---- THE KEYWORD PERFORMS (this skill's own) ---------------------------------------------------------------------
  // o: {at (s: the word's start in timeline.json), end (s: the next word's start, or the line's end), act, value}
  // acts: 'count' (a number counts to `value` while it is spoken: {text}); 'split' (its letters part: {spacing em});
  //   'join' (they close: {spacing em}); 'strike' (a line through it, then it dims: {strike, opacity});
  //   'mark' (a marker under it: {mark}); 'rise' (it surfaces out of focus on its word: {y em, blur, opacity});
  //   'weigh' (it gains weight as it is said: {weight 0..1 toward the bold cut}).
  // The word is ON screen before it is spoken (a caption or a headline); the act lands ON the word, never ahead of it.
  function perform(t, o) {
    var at = o.at, end = Math.max(o.end || at + 0.4, at + 0.4), p = seg(t, at, end, E.outCubic);
    switch (o.act) {
      case 'count': {
        var dec = o.decimals || 0, f = Math.pow(10, dec), v = o.value * p;
        return { text: (t >= end ? o.value : Math.round(v * f) / f).toFixed(dec) };
      }
      case 'split': return { spacing: 0.35 * p };
      case 'join': return { spacing: 0.6 * (1 - p) };
      case 'strike': { var s = seg(t, at, at + 8 * F, E.outCubic); return { strike: s, opacity: lerp(1, 0.45, seg(t, at + 8 * F, at + 16 * F)) }; }
      case 'mark': return { mark: seg(t, at + 2 * F, at + 12 * F, E.outCubic) };
      case 'rise': { var r = seg(t, at - 3 * F, at + 15 * F, E.outCubic); return { y: 0.38 * (1 - r), blur: 18 * (1 - r), opacity: r }; }
      case 'weigh': return { weight: p };
      default: throw new Error('moments.perform: unknown act "' + o.act + '"');
    }
  }
  // the start and end of the n-th occurrence of `word` in timeline.json (lines[].words[] {w, t}); throws when absent
  function wordTime(timeline, word, n) {
    function norm(x) { return String(x).toLowerCase().replace(/[^\p{L}\p{N}%.]/gu, '').replace(/^\.+|\.+$/g, ''); }
    var seen = 0, want = norm(word);
    for (var i = 0; i < timeline.lines.length; i++) {
      var L = timeline.lines[i], W = L.words || [];
      for (var j = 0; j < W.length; j++) {
        var w = norm(W[j].w);
        if (w === want && seen++ === (n || 0)) return { at: W[j].t, end: j + 1 < W.length ? W[j + 1].t : L.end };
      }
    }
    throw new Error('moments.wordTime: "' + word + '" (occurrence ' + (n || 0) + ') is not in the timeline');
  }

  // ---- apply: write a returned state onto an element ---------------------------------------------------------------
  // s: {x, y (px), scale, opacity, blur (px)} (any subset); origin defaults to whatever the element already has.
  function apply(el, s) {
    var tr = '';
    if (s.x != null || s.y != null) tr += 'translate(' + (s.x || 0) + 'px,' + (s.y || 0) + 'px) ';
    if (s.scale != null) tr += 'scale(' + s.scale + ')';
    if (tr) el.style.transform = tr;
    if (s.opacity != null) el.style.opacity = String(s.opacity);
    if (s.blur != null) el.style.filter = s.blur > 0.01 ? 'blur(' + s.blur.toFixed(2) + 'px)' : 'none';
    return el;
  }

  var api = { F: F, E: E, bezier: bezier, spring: spring, seg: seg, lerp: lerp,
              choose: choose, become: become, demote: demote, change: change, slot: slot, reel: reel,
              lead: lead, follow: follow, underline: underline, scan: scan, lock: lock, lift: lift, land: land,
              type: type, retype: retype, list: list, strip: strip, carry: carry,
              morph: { snapshot: snapshot, plan: plan, stage: stage, draw: draw },
              perform: perform, wordTime: wordTime, apply: apply };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Moments = api;
})(this);
