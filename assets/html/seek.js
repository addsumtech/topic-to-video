/* slides-to-video — freeze CSS reveals at progress ?p=0..1 for deterministic frame capture.
   Each animated element is frozen at local time (p*total − itsDelay) and paused, so staggered
   reveals render correctly at any p. total = max(delay+duration) across animated elements. */
(function () {
  function sec(v) { v = parseFloat(v); return isNaN(v) ? 0 : v; }
  var els = [].slice.call(document.querySelectorAll('*')).filter(function (el) {
    var n = getComputedStyle(el).animationName; return n && n !== 'none';
  });
  var spans = els.map(function (el) {
    var cs = getComputedStyle(el);
    return { el: el, d: sec(cs.animationDelay), dur: sec(cs.animationDuration) };
  });
  var total = spans.reduce(function (m, s) { return Math.max(m, s.d + s.dur); }, 0.001);
  var p = parseFloat(new URLSearchParams(location.search).get('p'));
  if (isNaN(p)) p = 1;
  var T = p * total;
  spans.forEach(function (s) {
    s.el.style.animationDelay = (s.d - T) + 's';
    s.el.style.animationPlayState = 'paused';
  });
})();
