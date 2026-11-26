// devices.js — the phone, tablet and laptop of a product film, built once at their real proportions so every film
// shows the same believable hardware (SKILL.md step 6). WHY: each film used to make its own from boxes; the Grok Bot
// film's phone was a black slab and its laptop a grey box ("太假了", 2026-11-18), and a desktop page was cropped into
// the phone. Here: a metal band with rounded edges, a glass front that REFLECTS the room over a display that EMITS,
// the display's real aspect enforced (a picture made for another screen is refused, or letterboxed on request),
// buttons, camera, notch, keys, trackpad, hinge.
//
//   const ph = st.phone(canvas, {width: 0.71, finish: 'black'});          // canvas at the phone's aspect (e.g. 1179x2556)
//   const lp = st.laptop(canvas, {width: 3.13, open: 1.9});               // canvas at 3024x1964's aspect; lp.userData.setLid(a)
//   const tb = st.tablet(canvas, {width: 1.78});
//   ...draw on the canvas, then ph.userData.refresh() (every frame it changes)
//
// Sizes default to decimetres (a phone 0.71 wide), the scale of a desk scene; pass `width` for any other. Each device
// stands with its BACK on y = 0 facing +z (phone, tablet) or its base on y = 0 opening toward +z (laptop); place and
// rotate the returned group. Options: finish (see FINISH), brightness (display, default 0.95), glare (the glass's
// reflectivity, default 0.06), fit: 'contain' (letterbox a picture of another aspect, as an app shows a landscape
// view), off: true (screen dark: black glass), island: false (phone pictures that already include the Dynamic
// Island). Registered for contacts() as a panel (its front face).
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import {ExtrudeGeometry} from './extrude_r169.js';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';

// real dimensions in millimetres (iPhone 15 Pro class, iPad Pro 13 class — the App Store's 2064 x 2752 iPad screenshots —,
// MacBook Pro 14 class); display = active area
const SPEC = {
  phone: {w: 70.6, h: 146.6, d: 8.25, r: 11.6, band: 1.1, disp: {w: 65.1, h: 141.1, r: 9.1, px: [1179, 2556]}},
  tablet: {w: 215.5, h: 281.6, d: 5.1, r: 17.0, band: 0.9, disp: {w: 198.1, h: 264.1, r: 11.0, px: [2064, 2752]}},
  laptop: {w: 312.6, dep: 221.2, base: 9.3, lid: 6.2, r: 9.5, disp: {w: 302.5, h: 196.5, r: 5.0, px: [3024, 1964], top: 5.4}},
};
const FINISH = {
  'natural': {color: '#a9a59e', roughness: 0.34}, 'black': {color: '#3a3a3c', roughness: 0.38},
  'white': {color: '#e6e4df', roughness: 0.32}, 'blue': {color: '#3f4d5e', roughness: 0.36},
  'silver': {color: '#d2d4d7', roughness: 0.3}, 'space-black': {color: '#2c2d30', roughness: 0.42},
};
const ASPECT_TOL = 0.02;

function rrShape(w, h, r) {
  r = Math.min(r, w / 2 - 1e-6, h / 2 - 1e-6); const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.absarc(x + w - r, y + r, r, -Math.PI / 2, 0, false);
  s.lineTo(x + w, y + h - r); s.absarc(x + w - r, y + h - r, r, 0, Math.PI / 2, false);
  s.lineTo(x + r, y + h); s.absarc(x + r, y + h - r, r, Math.PI / 2, Math.PI, false);
  s.lineTo(x, y + r); s.absarc(x + r, y + r, r, Math.PI, Math.PI * 1.5, false); return s;
}
// a flat rounded rectangle whose uv runs 0..1 over its own bounds (a picture fills it exactly)
function rrPlane(w, h, r) {
  const g = new THREE.ShapeGeometry(rrShape(w, h, r), 24), uv = g.attributes.uv, p = g.attributes.position;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, p.getX(i) / w + 0.5, p.getY(i) / h + 0.5); return g;
}
// a rounded slab w x h, thickness d, its edge rounded by bevel b, centred on the origin, faces along z
function slab(w, h, d, r, b) {
  b = Math.min(b, d / 2 - 1e-6);
  const g = new ExtrudeGeometry(rrShape(w - 2 * b, h - 2 * b, Math.max(1e-4, r - b)),
    {depth: Math.max(1e-6, d - 2 * b), bevelEnabled: true, bevelThickness: b, bevelSize: b, bevelSegments: 6, curveSegments: 32});
  g.translate(0, 0, -(d - 2 * b) / 2); g.computeVertexNormals(); return g;
}

// one room environment per renderer, for devices on a stage that has none (metal with nothing to reflect renders black)
const envs = new WeakMap();
function envFor(renderer) {
  if (!envs.has(renderer)) { const pm = new THREE.PMREMGenerator(renderer); envs.set(renderer, pm.fromScene(new RoomEnvironment(), 0.04).texture); }
  return envs.get(renderer);
}

// the display's picture: the canvas itself when it has the display's aspect; letterboxed into a canvas of that aspect
// with fit: 'contain'; anything else is refused (a page made for another screen, cropped, is how the Grok Bot phone
// came to show a cut-off desktop)
function displaySource(kind, src, o) {
  const [pw, ph] = SPEC[kind].disp.px, want = pw / ph, have = src.width / src.height;
  if (Math.abs(have / want - 1) <= ASPECT_TOL) return {canvas: src, draw: () => {}};
  if (o.fit !== 'contain') throw new Error('stage3d.' + kind + ': its display is ' + pw + 'x' + ph + ' (aspect ' + want.toFixed(3)
    + '), this picture is ' + src.width + 'x' + src.height + ' (' + have.toFixed(3) + '). Show the layout made FOR this device '
    + '(the phone app\'s own screens on a phone), or pass fit: \'contain\' to letterbox it whole — never crop another screen into it');
  const c = document.createElement('canvas'), k = Math.min(1, 2048 / Math.max(pw, ph)) * Math.max(1, Math.max(src.width, src.height) / Math.max(pw, ph));
  c.width = Math.round(pw * k); c.height = Math.round(ph * k); c.__src = src;
  const g = c.getContext('2d');
  const draw = () => { g.fillStyle = o.letterbox || '#000'; g.fillRect(0, 0, c.width, c.height);
    const s = Math.min(c.width / src.width, c.height / src.height), dw = src.width * s, dh = src.height * s;
    g.drawImage(src, (c.width - dw) / 2, (c.height - dh) / 2, dw, dh); };
  draw(); return {canvas: c, draw};
}

function screenMaterials(renderer, kind, src, o) {
  const {canvas, draw} = displaySource(kind, src, o);
  const tex = new THREE.CanvasTexture(canvas); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
  const b = o.brightness == null ? 0.95 : o.brightness;
  const display = new THREE.MeshBasicMaterial({map: tex, toneMapped: false, color: new THREE.Color(b, b, b)});
  // the cover glass: adds a faint reflection of the room (additive over the emitting display) and takes NO highlight
  // from the scene's lights: an anti-reflective display does not bloom white (a lit MeshPhysical glass washed the
  // picture out where the key light reflected)
  const glass = new THREE.MeshBasicMaterial({color: '#000000', envMap: envFor(renderer), combine: THREE.AddOperation,
    reflectivity: o.glare == null ? 0.06 : o.glare, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false});
  const refresh = () => { draw(); tex.needsUpdate = true; };
  return {display, glass, tex, refresh, canvas};
}

function metal(st, o, fallback) {
  const f = FINISH[o.finish || fallback] || FINISH[fallback];
  const m = new THREE.MeshPhysicalMaterial({color: f.color, metalness: 1, roughness: f.roughness, clearcoat: 0.2, clearcoatRoughness: 0.4});
  if (!st.scene.environment) m.envMap = envFor(st.renderer);
  return m;
}
const darkGlass = (st) => { const m = new THREE.MeshPhysicalMaterial({color: '#050506', roughness: 0.12, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.03});
  if (!st.scene.environment) m.envMap = envFor(st.renderer); return m; };

// phone or tablet: a slab with a metal band, glass front and back, the display under the front glass
function handheld(st, kind, src, o) {
  o = o || {}; const S = SPEC[kind], k = (o.width || S.w / 100) / S.w, mm = (v) => v * k;
  const W = mm(S.w), H = mm(S.h), D = mm(S.d), R = mm(S.r), b = mm(S.band);
  const group = new THREE.Group(), band = metal(st, o, kind === 'phone' ? 'natural' : 'silver'), glassMat = darkGlass(st);
  if (!st.scene.environment) glassMat.envMap = envFor(st.renderer);
  const body = new THREE.Mesh(slab(W, H, D, R, b), [glassMat, band]);   // caps: glass front/back; sides + bevel: the band
  body.castShadow = true; body.receiveShadow = true; group.add(body);
  const sm = screenMaterials(st.renderer, kind, src, o), d = S.disp;
  const disp = new THREE.Mesh(rrPlane(mm(d.w), mm(d.h), mm(d.r)), sm.display); disp.position.z = D / 2 + mm(0.02); disp.visible = !o.off;
  const cover = new THREE.Mesh(rrPlane(W - 2 * b, H - 2 * b, R - b), sm.glass); cover.position.z = D / 2 + mm(0.05);
  group.add(disp, cover);
  if (kind === 'phone' && o.island !== false) {   // the Dynamic Island: a black pill 11 mm below the top of the display
    const isl = new THREE.Mesh(rrPlane(mm(19.5), mm(5.6), mm(2.8)), new THREE.MeshBasicMaterial({color: '#000000'}));
    isl.position.set(0, mm(d.h / 2 - 11 / 2 - 0.3) - mm(2.2), D / 2 + mm(0.03)); group.add(isl);
  }
  // buttons on the band (phone: action + volume on the left, side button on the right; tablet: top button + volume)
  const btn = (x, y, len, axis) => { const g = axis === 'y' ? new RoundedBoxGeometry(mm(0.9), mm(len), mm(D / k * 0.42), 2, mm(0.4))
    : new RoundedBoxGeometry(mm(len), mm(0.9), mm(D / k * 0.42), 2, mm(0.4)); const m = new THREE.Mesh(g, band); m.position.set(x, y, 0); group.add(m); };
  if (kind === 'phone') { const L = -W / 2 - mm(0.25), Rr = W / 2 + mm(0.25);
    btn(L, H / 2 - mm(31), 7, 'y'); btn(L, H / 2 - mm(45), 11, 'y'); btn(L, H / 2 - mm(59), 11, 'y'); btn(Rr, H / 2 - mm(50), 17, 'y'); }
  else { btn(W / 2 - mm(26), H / 2 + mm(0.25), 16, 'x'); btn(W / 2 + mm(0.25), H / 2 - mm(30), 14, 'y'); btn(W / 2 + mm(0.25), H / 2 - mm(48), 14, 'y'); }
  // the back camera: a raised glass plateau with lenses in metal rings (seen when the device turns)
  { // at the top-LEFT seen from the back = top-right in the front's coordinates
    const P = kind === 'phone' ? 34 : 22, px = W / 2 - mm(P / 2 + 4), py = H / 2 - mm(P / 2 + 4);
    const plate = new THREE.Mesh(slab(mm(P), mm(P), mm(1.4), mm(P * 0.26), mm(0.5)), glassMat); plate.position.set(px, py, -D / 2 - mm(0.5)); group.add(plate);
    const lens = (x, y, rr) => { const ring = new THREE.Mesh(new THREE.CylinderGeometry(mm(rr), mm(rr), mm(1.6), 40), band);
      ring.rotation.x = Math.PI / 2; ring.position.set(px + mm(x), py + mm(y), -D / 2 - mm(1.4)); const eye = new THREE.Mesh(new THREE.CircleGeometry(mm(rr * 0.72), 40), glassMat);
      eye.position.set(px + mm(x), py + mm(y), -D / 2 - mm(2.21)); eye.rotation.y = Math.PI; group.add(ring, eye); };
    if (kind === 'phone') { lens(7.4, 7.4, 6.6); lens(7.4, -7.4, 6.6); lens(-7.6, 0, 6.6); } else { lens(3.5, 3.5, 4.6); lens(3.5, -4.5, 3.6); } }
  // the back: matte glass in the finish's colour
  { const f = FINISH[o.finish || (kind === 'phone' ? 'natural' : 'silver')] || FINISH.natural;
    const back = new THREE.Mesh(rrPlane(W - 2 * b, H - 2 * b, R - b), new THREE.MeshPhysicalMaterial({color: f.color, roughness: 0.55, metalness: 0.1, clearcoat: 0.5, clearcoatRoughness: 0.6}));
    if (!st.scene.environment) back.material.envMap = envFor(st.renderer);
    back.rotation.y = Math.PI; back.position.z = -D / 2 - mm(0.02); group.add(back); }
  group.userData = {kind: 'panel', device: kind, size: [W, H], depth: D, display: {w: mm(d.w), h: mm(d.h)}, screen: sm.tex,
    canvas: sm.canvas, refresh: sm.refresh, faceZ: D / 2, setOn: (on) => { disp.visible = !!on; }};
  return group;
}

// the laptop: base with keys, trackpad and grilles; the lid on a hinge at the back, the display on its inner side
function laptop(st, src, o) {
  o = o || {}; const S = SPEC.laptop, k = (o.width || S.w / 100) / S.w, mm = (v) => v * k;
  const W = mm(S.w), DP = mm(S.dep), BH = mm(S.base), LH = mm(S.lid), R = mm(S.r);
  const group = new THREE.Group(), alu = metal(st, o, 'silver'), black = new THREE.MeshStandardMaterial({color: '#0b0b0c', roughness: 0.55});
  // base (its top on y = BH): the slab lies with its faces along y
  const base = new THREE.Mesh(slab(W, DP, BH, R, mm(2.2)), alu); base.rotation.x = -Math.PI / 2; base.position.y = BH / 2;
  base.castShadow = true; base.receiveShadow = true; group.add(base);
  const top = BH + mm(0.02), onTop = (m, z) => { m.rotation.x = -Math.PI / 2; m.position.set(0, top, z); group.add(m); return m; };
  // keyboard: a black well and 78 keys (a function row of half-height keys and five full rows), set back from the trackpad
  const kbW = mm(276), kbD = mm(100), kbZ = -DP / 2 + mm(16) + kbD / 2;
  onTop(new THREE.Mesh(rrPlane(kbW + mm(4), kbD + mm(4), mm(3)), black), kbZ);
  const rows = [[14, 9], [14, 15.6], [14, 15.6], [13, 15.6], [12, 15.6], [11, 15.6]], gap = mm(2.2), vgap = mm(2.6);
  const keyGeo = new RoundedBoxGeometry(1, 1, 1, 2, 0.12), keyMat = new THREE.MeshStandardMaterial({color: '#141416', roughness: 0.62});
  const n = rows.reduce((a, r) => a + r[0], 0), keys = new THREE.InstancedMesh(keyGeo, keyMat, n); let i = 0, z = kbZ - kbD / 2;
  const M = new THREE.Matrix4();
  rows.forEach(([cnt, kh], ri) => { const h = mm(kh); const widths = ri === 0 || ri === 1 ? Array(cnt).fill(1) : ri === 2 ? [1.5, ...Array(cnt - 1).fill(1)]
      : ri === 3 ? [1.8, ...Array(cnt - 2).fill(1), 1.8] : ri === 4 ? [2.3, ...Array(cnt - 2).fill(1), 2.3] : [1, 1, 1, 1.3, 5.4, 1.3, 1, 1, 1, 1, 1].slice(0, cnt);
    const unit = (kbW - (cnt - 1) * gap) / widths.reduce((a, w) => a + w, 0); let x = -kbW / 2;
    for (const wu of widths) { const w = wu * unit; M.compose(new THREE.Vector3(x + w / 2, top + mm(0.45), z + h / 2), new THREE.Quaternion(), new THREE.Vector3(w, mm(0.9), h));
      keys.setMatrixAt(i++, M); x += w + gap; }
    z += h + vgap; });
  keys.count = i; keys.castShadow = true; keys.receiveShadow = true; group.add(keys);
  // trackpad: a smoother glass-like plate, flush, centred near the front
  const tpm = new THREE.MeshPhysicalMaterial({color: o.finish === 'space-black' ? '#26272a' : '#b4b7bb', metalness: 0.3, roughness: 0.42, clearcoat: 0.3, clearcoatRoughness: 0.5});
  if (!st.scene.environment) tpm.envMap = envFor(st.renderer);
  onTop(new THREE.Mesh(rrPlane(mm(135), mm(84), mm(6)), tpm), DP / 2 - mm(9) - mm(42));
  // speaker grilles either side of the keyboard: rows of fine dark holes
  { const c = document.createElement('canvas'); c.width = 64; c.height = 1024; const g = c.getContext('2d'); g.fillStyle = '#000';
    for (let yy = 6; yy < 1024; yy += 12) for (let xx = 6; xx < 64; xx += 12) { g.beginPath(); g.arc(xx + ((yy / 12) % 2) * 6, yy, 2.6, 0, 7); g.fill(); }
    const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace;
    for (const sx of [-1, 1]) { const m = onTop(new THREE.Mesh(new THREE.PlaneGeometry(mm(12), kbD), new THREE.MeshBasicMaterial({map: tx, transparent: true, opacity: 0.55})), kbZ);
      m.position.x = sx * (kbW / 2 + mm(9)); } }
  // the hinge: a dark cylinder along the back edge
  const hinge = new THREE.Mesh(new THREE.CylinderGeometry(mm(2.4), mm(2.4), W - mm(50), 24), black); hinge.rotation.z = Math.PI / 2;
  hinge.position.set(0, BH - mm(0.6), -DP / 2 + mm(2.6)); group.add(hinge);
  // the lid: pivots on the hinge; closed it lies on the base, opened by `open` radians (1.9 ~ 109 degrees)
  const pivot = new THREE.Group(); pivot.position.set(0, BH + mm(0.3), -DP / 2 + mm(3.5)); group.add(pivot);
  const lid = new THREE.Mesh(slab(W, DP, LH, R, mm(1.6)), alu); lid.rotation.x = -Math.PI / 2; lid.position.set(0, LH / 2, DP / 2 - mm(3.5));
  lid.castShadow = true; lid.receiveShadow = true; pivot.add(lid);
  // the inner side: one black glass panel edge to edge, the display under it, the notch at its top
  const sm = screenMaterials(st.renderer, 'laptop', src, o), d = S.disp, inner = (m, zOff, y) => { m.rotation.x = Math.PI / 2; m.position.set(0, -mm(y), DP / 2 - mm(3.5) + zOff); pivot.add(m); return m; };
  inner(new THREE.Mesh(rrPlane(W - mm(3), DP - mm(3), R - mm(1.5)), darkGlass(st)), 0, 0.01);
  const dz = DP / 2 - mm(d.top) - mm(d.h) / 2;   // display centre from the lid centre, toward the free edge (its top)
  const disp = inner(new THREE.Mesh(rrPlane(mm(d.w), mm(d.h), mm(d.r)), sm.display), dz, 0.03); disp.visible = !o.off;
  const notch = inner(new THREE.Mesh(rrPlane(mm(30), mm(6.2), mm(1.6)), new THREE.MeshBasicMaterial({color: '#000000'})), DP / 2 - mm(d.top) - mm(2.6), 0.05);
  inner(new THREE.Mesh(rrPlane(W - mm(3), DP - mm(3), R - mm(1.5)), sm.glass), 0, 0.07);
  notch.renderOrder = 1;
  const setLid = (a) => { pivot.rotation.x = -a; };
  setLid(o.open == null ? 1.9 : o.open);
  group.userData = {kind: 'laptop', device: 'laptop', size: [W, DP], top: BH + LH, baseTop: BH, pivot, lid, display: {w: mm(d.w), h: mm(d.h)},
    screen: sm.tex, canvas: sm.canvas, refresh: sm.refresh, setLid, setOn: (on) => { disp.visible = !!on; }};
  return group;
}

export {SPEC, FINISH, handheld, laptop, rrShape, rrPlane, slab};
