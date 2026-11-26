/* gsapseek.js — GSAP (assets/html/gsap/, 3.15.1, licence in gsap/LICENSE.md) on a film page whose every frame is a
 * pure function of t. GSAP normally runs on its own clock (a requestAnimationFrame ticker); here it never does: the
 * ticker's root update is removed when this file loads, every move is placed on ONE paused timeline, and the page's
 * window.seek(t) puts that timeline's playhead at t. The same t is always the same picture, in any order of seeks.
 *
 *   <script src="gsap/gsap.min.js"></script>              GSAP first (plugins you do not use may be left out)
 *   <script src="gsap/SplitText.min.js"></script> <script src="gsap/DrawSVGPlugin.min.js"></script>
 *   <script src="gsap/MorphSVGPlugin.min.js"></script> <script src="gsapseek.js"></script>
 *   window.filmReady = (async () => {
 *     await GsapSeek.ready();                             // every declared font loaded, plugins registered
 *     const film = GsapSeek.film();                       // the film's one paused timeline (never await it)
 *     GsapSeek.roll(film, '#code', {at: 0.3, value: '1202'});
 *     GsapSeek.trace(film, '#slots rect', {at: 1.9});
 *     GsapSeek.assemble(film, '#line', {at: 4.6});
 *     film.to('#slots rect', {fill: '#ff9f1a', stagger: 0.12, duration: 0.2}, 3.4);   // any GSAP tween, on the film
 *     window.seek = (t) => { GsapSeek.seek(film, t); drawTheRest(t); };   // Moments, a stage...
 *   })();
 *
 * THE SEEK RULE. Every tween goes on the film timeline (film.to / film.fromTo / a child timeline added to it) at an
 * absolute time; a tween made with gsap.to() outside it would never play (the ticker is off) and GsapSeek.seek
 * refuses it by name. No callbacks (onUpdate, onComplete, call()) for state: seeks suppress them. A per-frame drawing
 * that a tween cannot express goes in GsapSeek.draw(film, fn), run after every seek. Use fromTo (both ends written):
 * a from() reads the element's state on its first render, which depends on where the playhead was.
 *
 * TYPE THAT MOVES (Chrome snaps a text run's baseline to a whole pixel under an axis-aligned matrix: a slow move
 * steps; base.css "THE BASELINE UNLOCK"). Every moving letter or digit carries the unlock — a 1/1024 skew — in ITS OWN
 * transform, from the first frame and kept at rest, so its matrix is never axis-aligned and nothing re-snaps when it
 * lands. On the element itself, not on a parent: a letter whose own transform became a bare translate (at rest) was
 * then drawn a quarter pixel off on later frames, depending on which frame the page drew FIRST (measured: the same t
 * differed after a first seek past the landing; with the skew on each letter, identical in every order). Transforms
 * are 2D (force3D false): a 3D transform makes each letter its own composited layer, resampled, and GSAP's default
 * drops it on the last frame (a pop as the letter lands).
 *
 * THE MOVES (each tuned on rendered frames; tests/test_gsapseek.py):
 *   assemble(film, el, o)  a line of type assembles letter by letter: each rises out of its line's edge, tipping up
 *                          onto its baseline, staggered; it lands exactly in the line's kerned layout and holds
 *   roll(film, el, o)      a number rolls digit by digit to its value, each column landing after the one to its
 *                          left (an odometer); tabular lining figures, one column per digit
 *   trace(film, paths, o)  strokes draw themselves on (DrawSVG), one after another, and stop at the shape they name
 *   reshape(film, path, to, o)  one shape becomes another in one continuous motion (MorphSVG): a mark becomes the
 *                          icon it means, keeping its identity (the morph, not a cross-fade)
 */
(function (root) {
  'use strict';
  var gsap = root.gsap;
  if (!gsap) throw new Error('gsapseek.js: load gsap/gsap.min.js before it');
  // THE CLOCK: GSAP's ticker advances the root timeline every animation frame (gsap.updateRoot). Removed here, at
  // load, before any tween exists: nothing on the page moves unless a seek moves it.
  gsap.ticker.remove(gsap.updateRoot);
  gsap.ticker.lagSmoothing(0);
  gsap.ticker.sleep();
  gsap.config({ force3D: false });
  var UNLOCK = 'matrix(1,0.0009765625,0,1,0,0)';         // a skewY of 1/1024 (base.css), as CSS
  var UNLOCK_DEG = 0.05595;                                 // the same skew in degrees, for GSAP's skewY (atan(1/1024))
  var films = [], isReady = false;

  // ---- ready, then the film timeline -----------------------------------------------------------------------------
  // ready() -> a promise, resolved once every FontFace the page declares is loaded (a face first used mid-film stays
  // 'unloaded' after document.fonts.ready otherwise) and none failed (it rejects naming the face); plugins registered.
  // film() -> a paused GSAP timeline, the film's one clock. Never returned from a promise or awaited: a GSAP timeline
  // is a thenable that resolves when it completes, so awaiting a paused one waits forever (measured: filmReady hung).
  function ready() {
    var faces = [];
    if (document.fonts) document.fonts.forEach(function (f) { faces.push(f); });
    return Promise.all(faces.map(function (f) { return f.status === 'unloaded' ? f.load().catch(function () {}) : null; }))
      .then(function () { return document.fonts && document.fonts.ready; })
      .then(function () {
        var bad = faces.filter(function (f) { return f.status === 'error'; })
                       .map(function (f) { return f.family + ' ' + f.weight; });
        if (bad.length) throw new Error('GsapSeek.ready: font(s) failed to load: ' + bad.join(', '));
        ['SplitText', 'DrawSVGPlugin', 'MorphSVGPlugin'].forEach(function (n) { if (root[n]) gsap.registerPlugin(root[n]); });
        isReady = true;
      });
  }
  function film() {
    if (!isReady) throw new Error('GsapSeek.film: call it after `await GsapSeek.ready()` (fonts, plugins)');
    var tl = gsap.timeline({ paused: true });
    tl.__draws = [];
    films.push(tl);
    return tl;
  }
  function draw(tl, fn) { tl.__draws.push(fn); return tl; }
  var checked = false;
  function seek(tl, t) {
    if (!checked) {
      checked = true;      // any animation on GSAP's root that is not a film and has length would never play: refuse it
      var stray = gsap.globalTimeline.getChildren(false, true, true).filter(function (c) {
        return films.indexOf(c) < 0 && c.duration() > 0;
      });
      if (stray.length) {
        var c = stray[0], tg = c.targets ? c.targets()[0] : null;
        throw new Error('GsapSeek.seek: ' + stray.length + ' animation(s) outside the film timeline (they never play: ' +
          'the ticker is off); add them to the film, e.g. film.to(...). First: ' +
          (tg && tg.id ? '#' + tg.id : tg && tg.tagName ? tg.tagName : 'a timeline'));
      }
    }
    tl.totalTime(Math.max(0, t), true);
    for (var i = 0; i < tl.__draws.length; i++) tl.__draws[i](t);
    // returns nothing: the frame tools await whatever seek returns, and a timeline is a thenable that never resolves
    // while paused (`window.seek = (t) => GsapSeek.seek(film, t)` must not hang the render)
  }

  // ---- shared -----------------------------------------------------------------------------------------------------
  function one(el, who) {
    var e = typeof el === 'string' ? document.querySelector(el) : el;
    if (!e) throw new Error('GsapSeek.' + who + ': no element ' + el);
    return e;
  }
  // splitting measures glyphs: in a fallback face the letters would land where the real font's do not
  function needFonts(el, who) {
    if (!isReady) throw new Error('GsapSeek.' + who + ': called before GsapSeek.ready() resolved (the fonts are not ' +
                                  'loaded yet; split after `await GsapSeek.ready()`)');
    var cs = getComputedStyle(el), font = cs.fontStyle + ' ' + cs.fontWeight + ' ' + cs.fontSize + ' ' + cs.fontFamily;
    if (document.fonts && !document.fonts.check(font, el.textContent))
      throw new Error('GsapSeek.' + who + ': the font of ' + (el.id ? '#' + el.id : el.tagName) + ' (' + font + ') is not loaded');
  }
  function graphemes(s) {
    if (typeof Intl !== 'undefined' && Intl.Segmenter)
      return Array.from(new Intl.Segmenter().segment(s), function (x) { return x.segment; });
    return Array.from(s);
  }

  // ---- assemble: a line of type assembles letter by letter ---------------------------------------------------------
  // o: {at (s), each (s between letters, 0.032), dur (s per letter, 0.8), rise (% of the letter's height it starts
  //   below its place, 115), tilt (deg it starts tipped back, 7), from ('start' | 'center' | 'end'), ease ('expo.out')}
  // -> the SplitText (chars, words, lines). One line per element (white-space: nowrap). Each letter is clipped at its
  //   line's lower edge only (it rises out of that edge; ascenders and accents are never cut), and is placed where the
  //   unsplit text's kerning put it (split letters lose their kerning pairs: measured before the split, restored by a
  //   static offset), so the settled line IS the line as typeset. No overshoot: a headline settles (rewind_qa).
  function assemble(tl, el, o) {
    o = o || {};
    el = one(el, 'assemble');
    needFonts(el, 'assemble');
    el.style.fontVariantLigatures = 'none';            // a ligature cannot be split into its letters
    var want = [];                                     // where each letter of the TYPESET line is
    var walk = document.createTreeWalker(el, NodeFilter.SHOW_TEXT), n, r = document.createRange();
    while ((n = walk.nextNode())) {
      var gs = graphemes(n.textContent), k = 0;
      for (var i = 0; i < gs.length; i++) {
        if (!/\s/.test(gs[i])) { r.setStart(n, k); r.setEnd(n, k + gs[i].length); want.push(r.getBoundingClientRect().left); }
        k += gs[i].length;
      }
    }
    var split = root.SplitText.create(el, { type: 'lines,words,chars', aria: 'auto' });
    if (split.chars.length !== want.length)
      throw new Error('GsapSeek.assemble: split ' + split.chars.length + ' letters, measured ' + want.length);
    split.chars.forEach(function (c, i) {
      var dx = want[i] - c.getBoundingClientRect().left;
      if (Math.abs(dx) > 0.01) c.style.left = dx.toFixed(3) + 'px';   // layout offset, not a transform: GSAP owns those
      c.style.transformOrigin = '0% 100%';                             // it tips up onto its own baseline corner
    });
    split.lines.forEach(function (ln) { ln.style.clipPath = 'inset(-1em -1em -0.06em -1em)'; });
    var stagger = { each: o.each == null ? 0.032 : o.each, from: o.from || 'start' };
    // a letter is not drawn before its own start: it waits under its line's edge anyway, and hidden it is not a box
    // stacked on its tipped neighbours (page_overlap_qa read the waiting letters as colliding)
    tl.fromTo(split.chars, { autoAlpha: 0 }, { autoAlpha: 1, duration: 0.001, ease: 'none', stagger: stagger,
                                               immediateRender: true }, o.at || 0);   // (duration 0 did not revert)
    tl.fromTo(split.chars, { yPercent: o.rise == null ? 115 : o.rise, rotation: o.tilt == null ? 7 : o.tilt, skewY: UNLOCK_DEG },
              { yPercent: 0, rotation: 0, skewY: UNLOCK_DEG, duration: o.dur || 0.8, ease: o.ease || 'expo.out',
                stagger: stagger, immediateRender: true }, o.at || 0);
    return split;
  }

  // ---- roll: a number rolls digit by digit ----------------------------------------------------------------------
  // o: {at (s), value (the string it lands on; default the element's text), from (the string it starts on, same
  //   length; default all zeros), dur (s, 1.1: the first column's roll), each (s, 0.14: each column lands this much
  //   after the one to its left), turns (0: extra full turns each column makes on its way), ease ('power3.out')}
  //   -> the columns. Each column rolls through the digits between its `from` and its value, no more: a spin of
  //   whole turns at this size crosses ~180 px a frame and strobes at 30 fps (pan_speed_qa's whip limit is 48 px a
  //   frame for 6 frames; measured on the 1202 demo with turns 1); give `turns` only to small figures.
  // Each column is a window one line tall showing two digits at once (the one leaving upward, the one arriving from
  // below): only those two exist, so no column of hidden digits overlaps the page. Non-digits (a comma, %) stay put.
  function roll(tl, el, o) {
    o = o || {};
    el = one(el, 'roll');
    needFonts(el, 'roll');
    var value = String(o.value == null ? el.textContent.trim() : o.value);
    var from = String(o.from == null ? value.replace(/\d/g, '0') : o.from);
    if (from.length !== value.length) throw new Error('GsapSeek.roll: from "' + from + '" and value "' + value + '" differ in length');
    el.textContent = '';
    el.setAttribute('aria-label', value);
    el.style.fontVariantNumeric = 'tabular-nums lining-nums';
    el.style.whiteSpace = 'nowrap';
    var lh = parseFloat(getComputedStyle(el).lineHeight);
    if (!(lh > 0)) throw new Error('GsapSeek.roll: give the element a line-height in px or a number (it is the window\'s height)');
    var cols = [], d = 0;
    for (var i = 0; i < value.length; i++) {
      var ch = value[i];
      if (!/\d/.test(ch)) { var s = document.createElement('span'); s.textContent = ch; el.appendChild(s); continue; }
      if (!/\d/.test(from[i])) throw new Error('GsapSeek.roll: from "' + from + '" has no digit where "' + value + '" has one');
      var col = document.createElement('span');
      col.style.cssText = 'display:inline-block;position:relative;vertical-align:top;height:' + lh + 'px;' +
                          'clip-path:inset(0 -0.3em 0 -0.3em)';
      var a = document.createElement('span'), b = document.createElement('span');
      a.style.cssText = 'display:block;height:' + lh + 'px';
      b.style.cssText = 'display:block;position:absolute;left:0;top:0;height:' + lh + 'px';
      col.appendChild(a); col.appendChild(b); el.appendChild(col);
      var f0 = +from[i], f1 = +ch, steps = (f1 - f0 + 10) % 10 + 10 * (o.turns || 0);
      var st = { el: col, a: a, b: b, f0: f0, steps: steps, p: { v: 0 } };
      a.textContent = String(f0); b.style.visibility = 'hidden'; b.textContent = String((f0 + 1) % 10);
      tl.fromTo(st.p, { v: 0 }, { v: steps, duration: (o.dur || 1.1) + d * (o.each == null ? 0.14 : o.each),
                                  ease: o.ease || 'power3.out', immediateRender: true }, o.at || 0);
      cols.push(st); d++;
    }
    function show(t) {
      for (var j = 0; j < cols.length; j++) {
        var c = cols[j], v = c.p.v, k = Math.floor(v + 1e-9), fr = v - k;
        if (fr < 1e-6) fr = 0;
        c.a.textContent = String((c.f0 + k) % 10);
        c.b.textContent = String((c.f0 + k + 1) % 10);
        c.a.style.transform = 'translateY(' + (-fr * lh).toFixed(3) + 'px) ' + UNLOCK;
        c.b.style.transform = 'translateY(' + ((1 - fr) * lh).toFixed(3) + 'px) ' + UNLOCK;
        c.b.style.visibility = fr > 0 ? 'visible' : 'hidden';
      }
    }
    show(0);
    draw(tl, show);
    return cols;
  }

  // ---- trace: strokes draw themselves on -------------------------------------------------------------------------
  // o: {at (s), dur (s per stroke, 0.7), each (s between strokes, 0.09), to ('100%': where the stroke stops — a
  //   line that runs to the box it names stops there), ease ('power2.inOut')} -> the tween.
  // Before `at` the strokes are not drawn at all. A rect, circle, line or path; the stroke starts where its geometry
  // starts (a rect at its top-left corner: write a path to start elsewhere).
  function trace(tl, paths, o) {
    o = o || {};
    if (!root.DrawSVGPlugin) throw new Error('GsapSeek.trace: load gsap/DrawSVGPlugin.min.js');
    return tl.fromTo(paths, { drawSVG: '0% 0%' },
                     { drawSVG: '0% ' + (o.to || '100%'), duration: o.dur || 0.7, ease: o.ease || 'power2.inOut',
                       stagger: o.each == null ? 0.09 : o.each, immediateRender: true }, o.at || 0);
  }

  // ---- reshape: one shape becomes another (MorphSVG) ---------------------------------------------------------------
  // o: {at (s), dur (s, 0.6), ease ('power3.inOut'), shapeIndex ('auto'), type ('linear' | 'rotational')} -> the tween.
  // `path` is a <path> (MorphSVGPlugin.convertToPath turns a circle or rect into one); `to` a path element, a selector
  // or path data. Draw both shapes in ONE style (the same stroke or the same fill): what changes is the shape.
  function reshape(tl, path, to, o) {
    o = o || {};
    if (!root.MorphSVGPlugin) throw new Error('GsapSeek.reshape: load gsap/MorphSVGPlugin.min.js');
    var p = one(path, 'reshape');
    if (p.tagName.toLowerCase() !== 'path') throw new Error('GsapSeek.reshape: ' + p.tagName + ' is not a <path> (MorphSVGPlugin.convertToPath)');
    return tl.to(p, { morphSVG: { shape: to, shapeIndex: o.shapeIndex == null ? 'auto' : o.shapeIndex, type: o.type || 'linear' },
                      duration: o.dur || 0.6, ease: o.ease || 'power3.inOut', immediateRender: false }, o.at || 0);
  }

  root.GsapSeek = { ready: ready, film: film, seek: seek, draw: draw, assemble: assemble, roll: roll, trace: trace, reshape: reshape,
                    UNLOCK: UNLOCK };
})(this);
