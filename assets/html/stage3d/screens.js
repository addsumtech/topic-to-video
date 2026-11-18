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
    if (textRects.length) ink.push({el, rects: textRects, text: true});
    if (bg) ink.push({el, rects: [el.getBoundingClientRect()], text: false});
    // text outside the screen, or cut by a clipping ancestor
    for (const r of textRects) {
      let clipped = false;
      for (let a = el; a && a.id !== '__r'; a = a.parentElement) { const ac = getComputedStyle(a);
        if (ac.overflow !== 'visible' && ac.textOverflow !== 'ellipsis' && !a.hasAttribute('data-clip-ok')) { const b = a.getBoundingClientRect();
          if (r.right > b.right + 1 || r.bottom > b.bottom + 1 || r.left < b.left - 1 || r.top < b.top - 1) { clipped = true; break; } } }
      if (clipped) { issues.push({kind: 'clipped', a: label(el)}); break; }
      if (r.left < R.left - 1 || r.top < R.top - 1 || r.right > R.right + 1 || r.bottom > R.bottom + 1) { issues.push({kind: 'off-screen', a: label(el)}); break; }
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
  host.remove();
  const res = {screen: rec.name, issues, texts};
  lintCache.set(key, res); return res;
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

export {screen, lintScreens, screenTexts, brackets, registry as screenRegistry};
