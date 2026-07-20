(function () {
  function sec(v) { v = parseFloat(v); return isNaN(v) ? 0 : v; }
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
    return { el: el, d: sec(cs.animationDelay), dur: sec(cs.animationDuration), ambient: ambient };
  });
  var useCues = cues && !isNaN(dur) && dur > 0;
  if (useCues) {
    spans.forEach(function (s) {
      if (s.ambient) return;   // ambient backdrops are progress-driven, never cue-anchored
      var ci = s.el.getAttribute('data-cue-index');
      if (ci !== null && cues[+ci] != null && !isNaN(cues[+ci])) {
        // data-cue-offset: seconds to LEAD (negative) or LAG (positive) the spoken word. Without it
        // an author's only temporal control is WHICH word fires an element — the reveal lands exactly
        // on the anchor and nothing can be phrased against it. A connector that should start drawing
        // just before its phrase, or a punchline that should land a beat after, had no expression.
        // Clamped to [0, dur] so an offset can never schedule a reveal off the scene.
        var off = parseFloat(s.el.getAttribute('data-cue-offset'));
        s.d = cues[+ci] + (isNaN(off) ? 0 : off);
        if (s.d < 0) s.d = 0;
        if (s.d > dur) s.d = dur;
      }
    });
  }
  // reveal-stagger envelope: max(delay+dur) over the REVEALS only (ambient backdrops excluded)
  var total = useCues ? dur : spans.reduce(function (m, s) {
    return s.ambient ? m : Math.max(m, s.d + s.dur);
  }, 0.001);
  var T = p * total;
  spans.forEach(function (s) {
    // ambient: sit at fraction p through its own keyframe (spans the whole scene). reveal: freeze at
    // absolute time T = p*total via a negative delay.
    s.el.style.animationDelay = (s.ambient ? -(p * s.dur) : (s.d - T)) + 's';
    s.el.style.animationPlayState = 'paused';
  });
})();
