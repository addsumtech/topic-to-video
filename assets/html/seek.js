(function () {
  function sec(v) { v = parseFloat(v); return isNaN(v) ? 0 : v; }
  // an element may run SEVERAL animations: its delays and durations are lists, repeated to the number of names (as
  // CSS repeats them). Reading only the first delay and writing one back ran every animation on the first one's clock
  // — a module that faded in and flipped 1.45 s later flipped on its entrance (a QR-code film, 2026-11-04).
  function list(v, k) { var a = String(v || '0s').split(',').map(sec), o = []; for (var i = 0; i < k; i++) o.push(a[i % a.length]); return o; }
  var q = new URLSearchParams(location.search);
  var p = parseFloat(q.get('p')); if (isNaN(p)) p = 1;
  var dur = parseFloat(q.get('dur'));
  var cuesRaw = q.get('cues');
  var cues = cuesRaw ? cuesRaw.split(',').map(parseFloat) : null;
  var els = [].slice.call(document.querySelectorAll('*')).filter(function (el) {
    var n = getComputedStyle(el).animationName; return n && n !== 'none';
  });
  var spans = els.map(function (el) {
    var cs = getComputedStyle(el);
    // AMBIENT = a living backdrop (slow Ken-Burns / drift on a full-bleed .bg-soft/.bg-photo, or any
    // [data-ambient] element). It is driven by PROGRESS (0->1 over the whole scene), NOT by the reveal
    // clock — so it (a) breathes across the entire scene regardless of cue/blind mode and (b) is left
    // OUT of the reveal-stagger envelope below, so dropping one behind a page can never shift when a
    // reveal fires. Determinism is preserved either way.
    var ambient = el.matches('.bg-live, .bg-drift, [data-ambient]');
    // THE CUE HOST: the element itself when it carries data-cue-index, else its nearest ancestor that does.
    // An animated part INSIDE a cued element — a component's cells, built by its script; a .bar's fill inside
    // a cued card — is timed from that element's start, its own animation-delay an offset from there. Without
    // this a part kept its delay from the SCENE's start: a validation film's <tiling-patch> rippled its cells in
    // over the scene's first second while the patch itself sat at opacity 0 until its word — the ripple played
    // out unseen and the patch faded in already complete.
    var host = ambient ? null : el.closest('[data-cue-index]');
    var k = String(cs.animationName).split(',').length;
    var ds = list(cs.animationDelay, k), durs = list(cs.animationDuration, k);
    return { el: el, d: ds[0], dur: durs[0], ds: ds, durs: durs, ambient: ambient,
             host: host, own: host === el };
  });
  var useCues = cues && !isNaN(dur) && dur > 0;
  // when a cue host starts: its spoken cue (+ data-cue-offset, clamped to the scene) in cue mode, else its own
  // CSS animation-delay (0 when the host itself does not animate) — the stagger the page was authored with
  var hostStart = function (h) {
    if (useCues) {
      var ci = h.getAttribute('data-cue-index');
      if (ci !== null && cues[+ci] != null && !isNaN(cues[+ci])) {
        // data-cue-offset: seconds to LEAD (negative) or LAG (positive) the spoken word. Without it
        // an author's only temporal control is WHICH word fires an element — the reveal lands exactly
        // on the anchor and nothing can be phrased against it. A connector that should start drawing
        // just before its phrase, or a punchline that should land a beat after, had no expression.
        // Clamped to [0, dur] so an offset can never schedule a reveal off the scene.
        var off = parseFloat(h.getAttribute('data-cue-offset'));
        var t = cues[+ci] + (isNaN(off) ? 0 : off);
        return Math.min(dur, Math.max(0, t));
      }
      return null;                // an unanchored slot keeps the paced stagger (see html_capture_plan)
    }
    var n = getComputedStyle(h).animationName;
    return n && n !== 'none' ? sec(getComputedStyle(h).animationDelay) : 0;
  };
  spans.forEach(function (s) {
    if (!s.host) return;
    var start = hostStart(s.host);
    if (start === null) return;
    if (s.own) {                  // a host's own reveal: on its cue (paced: as authored); its later animations
      if (useCues) { var d0 = s.ds[0]; s.ds = s.ds.map(function (x) { return start + (x - d0); }); s.d = s.ds[0]; }
      return;                     // keep their offsets from the first
    }
    s.rel = s.d;                  // a part: its authored delays, now counted from the host's start
    s.ds = s.ds.map(function (x) { return start + x; });
    s.d = s.ds[0];
  });
  // reveal-stagger envelope: max(delay+dur) over the REVEALS only (ambient backdrops excluded)
  var total = useCues ? dur : spans.reduce(function (m, s) {
    if (s.ambient) return m;
    for (var i = 0; i < s.ds.length; i++) m = Math.max(m, s.ds[i] + s.durs[i]);
    return m;
  }, 0.001);
  var T = p * total;
  spans.forEach(function (s) {
    // ambient: sit at fraction p through its own keyframe (spans the whole scene). reveal: freeze at
    // absolute time T = p*total via a negative delay.
    s.el.style.animationDelay = s.ds.map(function (d, i) {
      return (s.ambient ? -(p * s.durs[i]) : (d - T)) + 's';
    }).join(', ');
    s.el.style.animationPlayState = 'paused';
  });
  // what was scheduled, for the checks that must agree with it (workshop.py measures a component's parts here)
  window.__seekSpans = spans.map(function (s) {
    return { el: s.el, start: s.d, rel: s.rel === undefined ? null : s.rel, dur: s.dur, ambient: s.ambient,
             host: s.host, own: s.own };
  });
})();
