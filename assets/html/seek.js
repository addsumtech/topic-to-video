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
    return { el: el, d: sec(cs.animationDelay), dur: sec(cs.animationDuration) };
  });
  var useCues = cues && !isNaN(dur) && dur > 0;
  if (useCues) {
    spans.forEach(function (s) {
      var ci = s.el.getAttribute('data-cue-index');
      if (ci !== null && cues[+ci] != null && !isNaN(cues[+ci])) s.d = cues[+ci];
    });
  }
  var total = useCues ? dur : spans.reduce(function (m, s) { return Math.max(m, s.d + s.dur); }, 0.001);
  var T = p * total;
  spans.forEach(function (s) {
    s.el.style.animationDelay = (s.d - T) + 's';
    s.el.style.animationPlayState = 'paused';
  });
})();
