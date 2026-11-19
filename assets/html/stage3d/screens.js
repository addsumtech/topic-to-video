// screens.js — app screens laid out by the BROWSER (HTML + CSS), drawn onto a canvas that a device or panel shows,
// and checked: nothing in a screen overlaps or is cut off. WHY: hand-placed canvas UIs collided (the Grok Bot deck
// slide drew its yellow bar over its legend lines, 2026-11-18) and no check could see inside a texture.
//
//   await Stage3D.screen(canvas, `<div class="inbox">...</div>`, {size: [390, 844], css: APP_CSS,
//                                fonts: {'Inter': 'fonts/Inter-Var.woff2'}, name: 'phone-inbox'});
//
// `size` is the screen's own layout size in CSS px (a phone's points, 390 x 844; a 14" laptop's, 1512 x 982); the
// canvas is drawn at its own pixel size, so text stays vector-sharp at any resolution. Images and fonts referenced
// in the markup are inlined (an SVG image may load nothing itself). Same markup -> the cached picture (cheap to call
// every frame from seek(t)). Await it: window.seek may be async.
// Stage3D.lintScreens() (run by scripts/stage_contacts_qa.py) lays each screen that is SHOWN right now out again in
// the page and reports overlapping ink and text cut off; Stage3D.screenTexts() gives their words to film_copy_qa.
// Mark a deliberate overlap (a badge on an avatar) with data-overlap-ok on either element.

const registry = new Map();   // canvas -> {html, css, size, name, fontsCss}
const pics = new Map();       // svg string -> decoded Image
const inlined = new Map();    // url -> data URL

async function dataUrl(url) {
  if (url.startsWith('data:')) return url;
  if (!inlined.has(url)) inlined.set(url, (async () => {
    const r = await fetch(url); if (!r.ok) throw new Error('Stage3D.screen: cannot load ' + url + ' (' + r.status + ')');
    const b = await r.blob();
    return await new Promise((res) => { const fr = new FileReader(); fr.onload = () => res(fr.result); fr.readAsDataURL(b); });
  })());
  return inlined.get(url);
}

async function inlineRefs(s) {
  const urls = new Set();
  s.replace(/\bsrc="([^"]+)"/g, (m, u) => { if (!u.startsWith('data:')) urls.add(u); return m; });
  s.replace(/url\((['"]?)([^'")]+)\1\)/g, (m, q, u) => { if (!u.startsWith('data:') && !u.startsWith('#')) urls.add(u); return m; });
  const map = new Map(); for (const u of urls) map.set(u, await dataUrl(u));
  return s.replace(/\bsrc="([^"]+)"/g, (m, u) => (map.has(u) ? 'src="' + map.get(u) + '"' : m))
    .replace(/url\((['"]?)([^'")]+)\1\)/g, (m, q, u) => (map.has(u) ? 'url("' + map.get(u) + '")' : m));
}

async function fontFaces(fonts) {
  let css = '';
  for (const [family, spec] of Object.entries(fonts || {})) {
    for (const f of (Array.isArray(spec) ? spec : [spec])) {
      const o = typeof f === 'string' ? {url: f} : f;
      css += '@font-face{font-family:"' + family + '";src:url("' + await dataUrl(o.url) + '");font-weight:' + (o.weight || '100 900')
        + ';font-style:' + (o.style || 'normal') + ';}';
    }
  }
  return css;
}

async function screen(canvas, html, o) {
  o = o || {};
  const [w, h] = o.size || [canvas.width, canvas.height];
  if (Math.abs((w / h) / (canvas.width / canvas.height) - 1) > 0.01) {
    throw new Error('Stage3D.screen: layout size ' + w + 'x' + h + ' does not have the canvas\'s aspect (' + canvas.width + 'x' + canvas.height + ')');
  }
  const fontsCss = await fontFaces(o.fonts), body = await inlineRefs(html), css = await inlineRefs(o.css || '');
  registry.set(canvas, {html, css: o.css || '', size: [w, h], name: o.name || canvas.id || 'screen', fontsCss});
  // the markup as XHTML inside the SVG (a browser rasterises an SVG image with a foreignObject as laid-out HTML)
  const root = document.createElement('div'); root.setAttribute('xmlns', 'http://www.w3.org/1999/xhtml');
  root.setAttribute('style', 'width:' + w + 'px;height:' + h + 'px;overflow:hidden;position:relative;margin:0');
  root.innerHTML = '<style>' + fontsCss + css + '</style>' + body;
  const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="' + canvas.width + '" height="' + canvas.height + '" viewBox="0 0 ' + w + ' ' + h
    + '"><foreignObject x="0" y="0" width="' + w + '" height="' + h + '">' + new XMLSerializer().serializeToString(root) + '</foreignObject></svg>';
  let im = pics.get(svg);
  if (!im) {
    im = new Image(); im.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
    await im.decode();
    if (pics.size > 400) pics.clear();
    pics.set(svg, im);
  }
  const g = canvas.getContext('2d'); g.clearRect(0, 0, canvas.width, canvas.height); g.drawImage(im, 0, 0, canvas.width, canvas.height);
  return canvas;
}

// the canvases a visible mesh shows right now (directly, or through a device's letterbox canvas)
function shownCanvases(stages) {
  const out = new Set();
  for (const st of stages) {
    st.scene.updateMatrixWorld(true);
    const fr = new st.THREE.Frustum().setFromProjectionMatrix(new st.THREE.Matrix4().multiplyMatrices(st.camera.projectionMatrix, st.camera.matrixWorldInverse));
    st.scene.traverseVisible((m) => {
      const im = m.material && m.material.map && m.material.map.image;
      if (!im || !(im instanceof HTMLCanvasElement)) return;
      m.geometry.computeBoundingSphere(); const s = m.geometry.boundingSphere.clone().applyMatrix4(m.matrixWorld);
      if (!fr.intersectsSphere(s)) return;
      for (let e = m; e; e = e.parent) if (!e.visible) return;
      out.add(im); if (im.__src) out.add(im.__src);
    });
  }
  return out;
}

const lintCache = new Map();
async function lintOne(rec) {
  const key = rec.fontsCss.length + '|' + rec.css + '|' + rec.html + '|' + rec.size;
  if (lintCache.has(key)) return lintCache.get(key);
  if (!document.getElementById('__s3d_fonts')) { const s = document.createElement('style'); s.id = '__s3d_fonts'; document.head.appendChild(s); }
  const fs = document.getElementById('__s3d_fonts'); if (!fs.textContent.includes(rec.fontsCss)) fs.textContent += rec.fontsCss;
  const host = document.createElement('div');
  host.style.cssText = 'position:fixed;left:0;top:0;width:' + rec.size[0] + 'px;height:' + rec.size[1] + 'px;visibility:hidden;pointer-events:none;z-index:-1;overflow:hidden';
  document.body.appendChild(host);
  const sh = host.attachShadow({mode: 'open'});
  sh.innerHTML = '<style>:host{all:initial}' + rec.css + '</style><div id="__r" style="width:' + rec.size[0] + 'px;height:' + rec.size[1] + 'px;position:relative;overflow:hidden">' + rec.html + '</div>';
  await document.fonts.ready;
  const R = sh.getElementById('__r').getBoundingClientRect(), issues = [], ink = [];
  const label = (el) => (el.textContent || el.getAttribute('alt') || '').trim().replace(/\s+/g, ' ').slice(0, 40)
    || (el.getAttribute('class') ? el.tagName.toLowerCase() + '.' + el.getAttribute('class').split(/\s+/)[0] : el.tagName.toLowerCase());
  const ok = (el) => { for (let e = el; e; e = e.parentElement) if (e.hasAttribute('data-overlap-ok')) return true; return false; };
  for (const el of sh.querySelectorAll('#__r *')) {
    if (el.tagName === 'STYLE') continue;
    const cs = getComputedStyle(el); if (cs.display === 'none' || parseFloat(cs.opacity) < 0.05) continue;
    const textRects = [];
    for (const n of el.childNodes) if (n.nodeType === 3 && n.textContent.trim()) { const r = document.createRange(); r.selectNodeContents(n); textRects.push(...r.getClientRects()); }
    const bg = (cs.backgroundColor !== 'rgba(0, 0, 0, 0)' && cs.backgroundColor !== 'transparent') || cs.backgroundImage !== 'none'
      || /^(IMG|SVG|svg|CANVAS)$/.test(el.tagName);

    // ink is only what shows: each box cut to every clipping ancestor (a page cropped inside a card is not under its
    // header just because its layout runs on beneath it)
    const shows = (r) => { let L = r.left, T = r.top, Rr = r.right, B = r.bottom;
      for (let a = el; a && a.id !== '__r'; a = a.parentElement) { if (getComputedStyle(a).overflow === 'visible') continue;
        const b = a.getBoundingClientRect(); L = Math.max(L, b.left); T = Math.max(T, b.top); Rr = Math.min(Rr, b.right); B = Math.min(B, b.bottom); }
      return Rr - L > 0.5 && B - T > 0.5 ? {left: L, top: T, right: Rr, bottom: B, width: Rr - L, height: B - T} : null; };
    const vis = textRects.map(shows).filter(Boolean);
    if (vis.length) ink.push({el, rects: vis, text: true});
    if (bg) { const b = shows(el.getBoundingClientRect()); if (b) ink.push({el, rects: [b], text: false}); }
    // text outside the screen, or cut by a clipping ancestor
    for (const r of textRects) {
      let clipped = false;
      for (let a = el; a && a.id !== '__r'; a = a.parentElement) { const ac = getComputedStyle(a);
        if (a.hasAttribute('data-clip-ok')) break;   // a deliberate crop owns what it cuts (and what its own box cuts after)
        if (ac.overflow !== 'visible' && ac.textOverflow !== 'ellipsis') { const b = a.getBoundingClientRect();
          if (r.right > b.right + 1 || r.bottom > b.bottom + 1 || r.left < b.left - 1 || r.top < b.top - 1) { clipped = true; break; } } }
      if (clipped) { issues.push({kind: 'clipped', a: label(el)}); break; }
      const v = shows(r); if (!v) continue;   // wholly cut away by a deliberate crop (data-clip-ok): not shown
      if (v.left < R.left - 1 || v.top < R.top - 1 || v.right > R.right + 1 || v.bottom > R.bottom + 1) { issues.push({kind: 'off-screen', a: label(el)}); break; }
    }
  }
  // a terminal program drawn by hand: its marks in a monospace face, in markup Stage3D.terminal did not make (an
  // imitated Claude Code read as fake, job-hunt 2026-11-19; scripts/term_capture.py records the real one)
  const TERM_SIGN = /[\u276f\u23fa\u23bf]|(^|\s)~ [%$#]( |$)|>_ OpenAI Codex|Welcome to Claude Code/;
  if (!sh.querySelector('[data-term]')) {
    for (const el of sh.querySelectorAll('#__r *')) {
      const own = Array.from(el.childNodes).filter((n) => n.nodeType === 3).map((n) => n.textContent).join('');
      if (!TERM_SIGN.test(own) && !TERM_SIGN.test(el.textContent.length < 60 ? el.textContent : '')) continue;
      if (/mono|menlo|monaco|courier|consolas|sf mono|fira code|jetbrains/i.test(getComputedStyle(el).fontFamily)) {
        issues.push({kind: 'imitated-terminal', a: label(el)}); break; }
    }
  }
  const area = (r) => Math.max(0, r.width) * Math.max(0, r.height);
  for (let i = 0; i < ink.length; i++) for (let j = i + 1; j < ink.length; j++) {
    const A = ink[i], B = ink[j];
    if (A.el === B.el || A.el.contains(B.el) || B.el.contains(A.el) || ok(A.el) || ok(B.el)) continue;
    let hit = false;
    for (const a of A.rects) { for (const b of B.rects) {
      const ow = Math.min(a.right, b.right) - Math.max(a.left, b.left), oh = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
      if (ow > 0.5 && oh > 0.5 && ow * oh > 0.1 * Math.min(area(a), area(b))) { hit = true; break; } } if (hit) break; }
    if (hit) issues.push({kind: 'overlap', a: label(A.el), b: label(B.el)});
  }
  const texts = []; const walker = document.createTreeWalker(sh.getElementById('__r'), NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) { if (n.parentElement && n.parentElement.tagName === 'STYLE') continue;
    const s = n.textContent.trim().replace(/\s+/g, ' '); if (s) texts.push(s); }
  // every element that holds words, by its whole text, and where its first line of words sits: one that keeps its words
  // and moves back and forth from frame to frame jitters (a caret joining the line box as it blinks; stage_contacts_qa
  // follows them over time). Each is named by its place in the markup (`p`), which neither a caret (it splits the
  // element's text node and the blink merges it again) nor typing (the words grow) changes; its words (`t`) tell a
  // line still being typed from another line that took its place.
  const lines = [], seen = {};
  for (const el of sh.querySelectorAll('#__r *')) {
    if (el.tagName === 'STYLE') continue; let first = null;
    for (const n of el.childNodes) if (n.nodeType === 3 && n.textContent.trim()) { first = n; break; }
    if (!first) continue; const r = document.createRange(); r.selectNodeContents(first); const rs = r.getClientRects(); if (!rs.length) continue;
    const t = el.textContent.trim().replace(/\s+/g, ' ').slice(0, 40), i = seen[t] = (seen[t] || 0) + 1;
    let path = ''; for (let e = el; e && e.id !== '__r'; e = e.parentElement) path = e.tagName + Array.prototype.indexOf.call(e.parentElement.children, e) + '/' + path;
    lines.push({t, n: i, p: path, x: +(rs[0].left - R.left).toFixed(2), y: +(rs[0].top - R.top).toFixed(2)}); }
  host.remove();
  const res = {screen: rec.name, issues, texts, lines};
  lintCache.set(key, res); return res;
}

// a text caret for an app screen's markup that can never move the text: a zero-height anchor on the baseline with the
// bar drawn absolutely from it, always in the markup and blinked by opacity. A caret laid out as an inline box taller
// than the text, or added and removed as it blinks, re-flows its line: the job-hunt film's CV line and Word document
// jumped 2-3 px on every blink. `block` reserves a terminal cell (a block cursor) instead of a thin bar.
function caret(on, o) {
  o = o || {}; const w = o.block ? (o.width || '0.6em') : '0';
  const bar = o.block ? 'left:0;width:' + w : 'left:-' + ((o.thickness || 2) / 2) + 'px;width:' + (o.thickness || 2) + 'px';
  return '<span data-overlap-ok style="display:inline-block;position:relative;width:' + w + ';height:0;vertical-align:baseline">'
    + '<span style="position:absolute;' + bar + ';bottom:' + (o.below || '-0.22em') + ';height:' + (o.height || '1.1em') + ';background:'
    + (o.color || 'currentColor') + ';opacity:' + (on ? 1 : 0) + '"></span></span>';
}

// a terminal frame captured by scripts/term_capture.py, as markup for Stage3D.screen: every cell's character and colours
// as the program drew them, wide (CJK) characters across two cells, inside an optional macOS window. Returns {html, css,
// size} (size in CSS px: give the canvas this aspect). o: font ('Menlo'), px (font size, 15), lh (row height in em,
// 1.25), pad, theme {bg, fg, ansi: {red: ..}}, title (a window title bar; null for none), radius. A run whose style
// has `a` is drawn with data-a="<a>" (an anchor a film can find: a thread tied to those words).
const ANSI = {black: '#000000', red: '#c91b00', green: '#00c200', brown: '#c7c400', blue: '#0225c7', magenta: '#ca30c7', cyan: '#00c5c7',
  white: '#c7c7c7', brightblack: '#686868', brightred: '#ff6e67', brightgreen: '#5ffa68', brightbrown: '#fffc67', brightblue: '#6871ff',
  brightmagenta: '#ff77ff', brightcyan: '#60fdff', brightwhite: '#ffffff'};
// [x, y, w, h] in half cells, for each block character: halves, quadrants, the full block
const Q = {UL: [0, 0, 1, 1], UR: [1, 0, 1, 1], LL: [0, 1, 1, 1], LR: [1, 1, 1, 1]};
const QUAD = {'\u2580': [[0, 0, 2, 1]], '\u2584': [[0, 1, 2, 1]], '\u2588': [[0, 0, 2, 2]], '\u258c': [[0, 0, 1, 2]], '\u2590': [[1, 0, 1, 2]],
  '\u2596': [Q.LL], '\u2597': [Q.LR], '\u2598': [Q.UL], '\u259d': [Q.UR], '\u2599': [Q.UL, Q.LL, Q.LR], '\u259a': [Q.UL, Q.LR],
  '\u259b': [Q.UL, Q.UR, Q.LL], '\u259c': [Q.UL, Q.UR, Q.LR], '\u259e': [Q.UR, Q.LL], '\u259f': [Q.UR, Q.LL, Q.LR]};
function terminal(frame, o) {
  o = o || {}; const px = o.px || 15, lh = o.lh || 1.25, pad = o.pad == null ? 14 : o.pad, cw = px * 0.6021, rh = Math.round(px * lh);
  const th = Object.assign({bg: '#1e1e1e', fg: '#e6e6e6'}, o.theme || {}), ansi = Object.assign({}, ANSI, th.ansi || {});
  const col = (c, dflt) => (c === 'default' || c == null ? dflt : /^[0-9a-f]{6}$/i.test(c) ? '#' + c : ansi[c] || dflt);
  const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const cols = frame.rows.length ? frame.rows[0].reduce((n, r) => n + (r[1].w ? 2 : r[0].length), 0) : 80;
  const W = Math.round(cols * cw + 2 * pad), bar = o.title === null ? 0 : 30, H = bar + frame.rows.length * rh + 2 * pad;
  let rows = '';
  for (const runs of frame.rows) {
    rows += '<div class="tr">';
    for (const [text, st] of runs) {
      let fg = col(st.fg, th.fg), bg = col(st.bg, 'transparent');
      if (st.r) { const f = fg; fg = bg === 'transparent' ? th.bg : bg; bg = f; }
      const look = 'color:' + fg + ';background:' + bg + (st.b ? ';font-weight:700' : '') + (st.i ? ';font-style:italic' : '') + (st.u ? ';text-decoration:underline' : '');
      // block characters (the Claude Code mascot is drawn in them) are cells filled by quadrant, as a terminal draws them
      // itself; a font's glyphs for them (Menlo lacks several) fall back to another face and miss the cell
      if (!st.w && /[\u2580-\u259f]/.test(text)) {
        for (const ch of text) {
          const q = QUAD[ch];
          if (!q) { rows += '<span style="width:' + cw.toFixed(3) + 'px;' + look + '">' + esc(ch) + '</span>'; continue; }
          rows += '<span style="width:' + cw.toFixed(3) + 'px;position:relative;background:' + bg + '">' + q.map(([x, y, w, h]) =>
            '<i style="position:absolute;left:' + x * 50 + '%;top:' + y * 50 + '%;width:' + w * 50 + '%;height:' + h * 50 + '%;background:' + fg + '"></i>').join('') + '</span>';
        }
        continue;
      }
      // a terminal fits every glyph into its cells: a symbol from a fallback face (⎿, ⏺) is cut to them, on purpose
      rows += '<span' + (st.a ? ' data-a="' + esc(st.a) + '"' : '') + (/[^\u0000-\u1fff]/.test(text) ? ' data-clip-ok' : '') + ' style="width:' + ((st.w ? 2 : text.length) * cw).toFixed(3) + 'px;' + look + '">' + esc(text) + '</span>';
    }
    rows += '</div>';
  }
  // the terminal's own cursor where the program left it (a steady block, macOS Terminal's default; o.cursor false hides it)
  let cur = '';
  if (o.cursor !== false && frame.cursor && frame.cursor[2] && frame.cursor[1] < frame.rows.length) {
    const [cx, cy] = frame.cursor; let x = 0, under = '';
    for (const [text, st] of frame.rows[cy]) { const n = st.w ? 2 : text.length; if (cx >= x && cx < x + n) { under = st.w ? text : text[cx - x]; break; } x += n; }
    cur = '<div data-overlap-ok style="position:absolute;left:' + (pad + cx * cw).toFixed(2) + 'px;top:' + (bar + pad + cy * rh) + 'px;width:' + cw.toFixed(2) + 'px;height:' + rh
      + 'px;background:' + (o.cursorColor || th.fg) + ';color:' + th.bg + ';text-align:center;font:' + px + 'px/' + rh + 'px ' + (o.font || 'Menlo') + ',monospace">'
      + esc((under || ' ').trim()) + '</div>';
  }
  const title = bar ? '<div class="tb"><i style="background:#ff5f57"></i><i style="background:#febc2e"></i><i style="background:#28c840"></i><b>'
    + esc(o.title || '') + '</b></div>' : '';
  const css = '.tw{position:absolute;inset:0;background:' + th.bg + ';border-radius:' + (o.radius == null ? 10 : o.radius) + 'px;overflow:hidden;'
    + 'box-shadow:inset 0 0 0 1px rgba(255,255,255,.12)} .tb{height:' + bar + 'px;display:flex;align-items:center;gap:8px;padding:0 12px;'
    + 'background:' + (o.barColor || '#2b2b2b') + ';font:500 13px -apple-system,"Helvetica Neue",sans-serif;color:#a8a8a8}'
    + ' .tb i{width:12px;height:12px;border-radius:6px} .tb b{flex:1;text-align:center;font-weight:500;margin-right:56px}'
    + ' .tg{padding:' + pad + 'px;font:' + px + 'px/' + rh + 'px ' + (o.font || 'Menlo') + ',"PingFang SC",monospace}'
    + ' .tr{height:' + rh + 'px;white-space:pre;display:flex}'
    + ' .tr span{display:inline-block;height:' + rh + 'px;overflow:hidden;text-align:center;flex:none}';
  return {html: '<div class="tw" data-term>' + title + '<div class="tg">' + rows + '</div>' + cur + '</div>', css, size: [W, H]};
}

async function lintScreens(stages) {
  const shown = shownCanvases(stages), out = [];
  for (const [canvas, rec] of registry) if (shown.has(canvas)) out.push(await lintOne(rec));
  return out;
}
async function screenTexts(stages) { return (await lintScreens(stages)).map((r) => ({screen: r.screen, texts: r.texts})); }

// corner brackets that follow an object's projected outline (a scanner locking onto a tilted code): quad = four
// [x, y] points in order round the shape (st.quad(obj) gives them); arm = each bracket's length as a share of its
// edge (or px when > 1); grow > 1 draws them that much larger about the centre (to close in from).
function brackets(g, quad, o) {
  o = o || {}; const grow = o.grow == null ? 1 : o.grow, cx = quad.reduce((a, p) => a + p[0], 0) / 4, cy = quad.reduce((a, p) => a + p[1], 0) / 4;
  const Q = quad.map(([x, y]) => [cx + (x - cx) * grow, cy + (y - cy) * grow]);
  g.save(); g.strokeStyle = o.color || 'rgba(255,255,255,0.94)'; g.lineWidth = o.lineWidth || 7; g.lineCap = 'round'; g.lineJoin = 'round';
  for (let i = 0; i < 4; i++) {
    const P = Q[i], A = Q[(i + 3) % 4], B = Q[(i + 1) % 4];
    const toward = (T) => { const dx = T[0] - P[0], dy = T[1] - P[1], L = Math.hypot(dx, dy), a = o.arm == null ? 0.18 : o.arm, len = a > 1 ? Math.min(a, L / 2) : L * a;
      return [P[0] + dx / L * len, P[1] + dy / L * len]; };
    const a = toward(A), b = toward(B); g.beginPath(); g.moveTo(a[0], a[1]); g.lineTo(P[0], P[1]); g.lineTo(b[0], b[1]); g.stroke();
  }
  g.restore();
}

export {screen, lintScreens, screenTexts, brackets, caret, terminal, registry as screenRegistry};
