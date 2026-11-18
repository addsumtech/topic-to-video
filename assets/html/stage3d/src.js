// stage3d — a lit 3D stage for a film page (SKILL.md step 6, the default for product films): real screens become
// physical panels with thickness, rounded edges and contact shadows under a studio light; a camera with optional depth
// of field; every frame a pure function of the state you pass to render() — no clock, no animation loop.
// Built into assets/html/stage3d.js (one classic script, works from file://) by `npm run build` in this folder's
// sibling script: scripts/build_stage3d.sh. Usage in a page:
//
//   <canvas id="c" width="1920" height="1080"></canvas>
//   <script src="stage3d.js"></script>
//   const st = Stage3D.create({canvas: document.getElementById('c'), background: '#0c0e12', dof: {aperture: 0.002}});
//   st.studio();                       // key + rim + fill + a room environment for reflections
//   st.floor({color: '#15181d'});      // a ground that takes soft shadows
//   const a = st.panel('screens/home.png', {width: 6.4, x: 0, y: 1.9, rotY: -0.25});
//   await st.ready();                  // images loaded
//   window.seek = (t) => { a.rotation.y = -0.25 + 0.1 * Stage3D.ease(t / 4);
//     st.render({pos: [0, 2.2, 9 - t], look: [0, 1.9, 0], fov: 32, focus: 9 - t}); };
//
// Units are scene metres; a 16:9 screen 6.4 wide is about a laptop display at the default camera. The panel's front
// face shows the image at its own aspect (height follows the image unless given). Colour is sRGB in, ACES out.
import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import {RoomEnvironment} from 'three/examples/jsm/environments/RoomEnvironment.js';
import {EffectComposer} from 'three/examples/jsm/postprocessing/EffectComposer.js';
import {RenderPass} from 'three/examples/jsm/postprocessing/RenderPass.js';
import {BokehPass} from 'three/examples/jsm/postprocessing/BokehPass.js';
import {OutputPass} from 'three/examples/jsm/postprocessing/OutputPass.js';

const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const ease = (x) => { x = clamp01(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
const easeOut = (x) => 1 - Math.pow(1 - clamp01(x), 3);
const lerp = (a, b, k) => a + (b - a) * k;
const lerp3 = (a, b, k) => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)];

function create(o) {
  o = o || {};
  const canvas = o.canvas;
  const W = o.width || canvas.width || 1920, H = o.height || canvas.height || 1080;
  const renderer = new THREE.WebGLRenderer({canvas, antialias: true, preserveDrawingBuffer: true, alpha: !!o.transparent});
  renderer.setPixelRatio(1);
  renderer.setSize(W, H, false);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  // ACES (default) is filmic and desaturates bright colours; 'neutral' keeps brand colours true (product films, a cast
  // of coloured characters, logos)
  renderer.toneMapping = o.toneMapping === 'neutral' ? THREE.NeutralToneMapping : THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = o.exposure == null ? 1.0 : o.exposure;
  renderer.shadowMap.enabled = o.shadows !== false;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;

  const scene = new THREE.Scene();
  if (!o.transparent) scene.background = new THREE.Color(o.background || '#0c0e12');
  if (o.fog) scene.fog = new THREE.Fog(o.fog.color || o.background || '#0c0e12', o.fog.near || 10, o.fog.far || 40);
  const camera = new THREE.PerspectiveCamera(o.fov || 35, W / H, 0.05, 200);
  camera.position.set(0, 2, 10);

  let composer = null, bokeh = null;
  if (o.dof) {
    composer = new EffectComposer(renderer);
    composer.setPixelRatio(1);
    composer.setSize(W, H);
    composer.addPass(new RenderPass(scene, camera));
    bokeh = new BokehPass(scene, camera, {focus: 10, aperture: o.dof.aperture || 0.002, maxblur: o.dof.maxblur || 0.008});
    composer.addPass(bokeh);
    composer.addPass(new OutputPass());
  }

  const pending = [];
  const loader = new THREE.TextureLoader();
  const texture = (src) => {
    if (src instanceof HTMLCanvasElement || src instanceof HTMLImageElement) {
      const t = new THREE.Texture(src); t.colorSpace = THREE.SRGBColorSpace; t.needsUpdate = true;
      t.anisotropy = renderer.capabilities.getMaxAnisotropy(); return Promise.resolve(t);
    }
    return new Promise((res, rej) => loader.load(src, (t) => {
      t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = renderer.capabilities.getMaxAnisotropy(); res(t);
    }, undefined, () => rej(new Error('stage3d: cannot load ' + src))));
  };

  const loadImage = (src) => (src instanceof HTMLImageElement && src.complete ? Promise.resolve(src) : new Promise((res, rej) => {
    const im = new Image(); im.onload = () => res(im); im.onerror = () => rej(new Error('stage3d: cannot load ' + src)); im.src = src.src || src; }));

  const st = {
    THREE, scene, camera, renderer,
    // a three-point studio: warm key from the upper left, cool rim from behind, soft fill; plus a room environment
    // so glossy edges and glass catch real reflections. Strengths scale the whole rig.
    studio(s) {
      s = s || {};
      const pm = new THREE.PMREMGenerator(renderer);
      scene.environment = pm.fromScene(new RoomEnvironment(), 0.04).texture;
      scene.environmentIntensity = s.env == null ? 0.35 : s.env;
      const key = new THREE.DirectionalLight(s.keyColor || '#fff4e6', s.key == null ? 2.2 : s.key);
      key.position.set(-6, 9, 7); key.castShadow = true;
      key.shadow.mapSize.set(2048, 2048); key.shadow.camera.left = -12; key.shadow.camera.right = 12;
      key.shadow.camera.top = 12; key.shadow.camera.bottom = -12; key.shadow.radius = 6; key.shadow.bias = -0.0004; key.shadow.normalBias = 0.02;   // no self-shadow acne (striped rims) on curved bodies
      const rim = new THREE.DirectionalLight(s.rimColor || '#cfe3ff', s.rim == null ? 1.4 : s.rim);
      rim.position.set(5, 4, -8);
      const fill = new THREE.HemisphereLight('#ffffff', '#20242b', s.fill == null ? 0.35 : s.fill);
      scene.add(key, rim, fill);
      return {key, rim, fill};
    },
    // a spotlight that finds a subject: the one placed light (taste-notes: "light is placed, not sprayed")
    spot(target, s) {
      s = s || {};
      // soft by default: a narrow hard spot leaves a hot oval on a glossy floor (seen on the first keyframes)
      const L = new THREE.SpotLight(s.color || '#ffffff', s.intensity == null ? 40 : s.intensity, 0, s.angle || 0.35,
                                    s.penumbra == null ? 0.9 : s.penumbra, 1.6);
      L.position.set(...(s.from || [0, 9, 6])); L.castShadow = true; L.shadow.mapSize.set(2048, 2048);
      L.target = target; scene.add(L); return L;
    },
    floor(f) {
      f = f || {};
      const g = new THREE.PlaneGeometry(200, 200);
      // default: a dark, slightly glossy floor that catches soft reflections of the screens (it grounds them)
      const m = new THREE.MeshStandardMaterial({color: f.color || '#0e1013', roughness: f.roughness == null ? 0.38 : f.roughness,
                                                metalness: f.metalness == null ? 0.55 : f.metalness});
      const mesh = new THREE.Mesh(g, m); mesh.rotation.x = -Math.PI / 2; mesh.position.y = f.y || 0;
      mesh.receiveShadow = true; scene.add(mesh); return mesh;
    },
    // a real screen as a physical panel: rounded slab, the image on its front face, a darker body, shadows both ways
    panel(src, p) {
      p = p || {};
      const group = new THREE.Group();
      const w = p.width || 6.4, depth = p.depth == null ? 0.08 : p.depth, r = p.radius == null ? 0.12 : p.radius;
      p.bezel = p.bezel == null ? 0.03 : p.bezel;
      const body = new THREE.MeshStandardMaterial({color: p.edge || '#1a1d22', roughness: 0.4, metalness: 0.2});
      const job = texture(src).then((tex) => {
        const img = tex.image, h = p.height || w * (img.height / img.width);
        const slab = new THREE.Mesh(new RoundedBoxGeometry(w, h, depth, 6, Math.min(r, depth / 2 - 1e-4)), body);
        slab.castShadow = true; slab.receiveShadow = true;
        // the screen EMITS its picture (a real display is not lit by the room): unlit, exact colours, not tone-mapped,
        // with its own rounded corners; `dim` < 1 darkens it for a background panel
        const fw = w - p.bezel * 2, fh = h - p.bezel * 2, fr = Math.max(0.001, r - p.bezel * 0.5);
        const shape = new THREE.Shape();
        shape.moveTo(-fw / 2 + fr, -fh / 2); shape.lineTo(fw / 2 - fr, -fh / 2);
        shape.quadraticCurveTo(fw / 2, -fh / 2, fw / 2, -fh / 2 + fr); shape.lineTo(fw / 2, fh / 2 - fr);
        shape.quadraticCurveTo(fw / 2, fh / 2, fw / 2 - fr, fh / 2); shape.lineTo(-fw / 2 + fr, fh / 2);
        shape.quadraticCurveTo(-fw / 2, fh / 2, -fw / 2, fh / 2 - fr); shape.lineTo(-fw / 2, -fh / 2 + fr);
        shape.quadraticCurveTo(-fw / 2, -fh / 2, -fw / 2 + fr, -fh / 2);
        const fg = new THREE.ShapeGeometry(shape, 12);
        const uv = fg.attributes.uv, pos = fg.attributes.position;
        for (let i = 0; i < uv.count; i++) uv.setXY(i, pos.getX(i) / fw + 0.5, pos.getY(i) / fh + 0.5);
        const dim = p.dim == null ? 1 : p.dim;
        const face = new THREE.Mesh(fg, new THREE.MeshBasicMaterial({map: tex, toneMapped: false,
                                                                     color: new THREE.Color(dim, dim, dim)}));
        face.position.z = depth / 2 + 0.002;
        group.add(slab, face);
        group.userData.size = [w, h];
      });
      pending.push(job);
      group.position.set(p.x || 0, p.y == null ? 2 : p.y, p.z || 0);
      group.rotation.set(p.rotX || 0, p.rotY || 0, p.rotZ || 0);
      scene.add(group);
      return group;
    },
    // a flat character or mark (a PNG with transparency) as a soft, glossy 3D body: its outline inflated into a pillow
    // (flat face rolling to a round rim), its own artwork on the face redrawn crisp at any size (the picture's few
    // colours, snapped per pixel from a smooth upscale), its main colour on the back. For a product's mascot, a cast of
    // characters, an app icon's glyph. The outline must be star-shaped about its centre (blobs, drops, flowers, clouds).
    // Returns a group standing on its own y = 0; move/squash group.userData.body for acting (see hop()).
    inflate(src, p) {
      p = p || {};
      const group = new THREE.Group(), body = new THREE.Group(); group.add(body);
      const job = loadImage(src).then((img) => {
        const iw = img.naturalWidth || img.width, ih = img.naturalHeight || img.height;
        const c = document.createElement('canvas'); c.width = iw; c.height = ih;
        const cx2 = c.getContext('2d', {willReadFrequently: true}); cx2.drawImage(img, 0, 0);
        const px = cx2.getImageData(0, 0, iw, ih).data, A = (x, y) => {
          x = Math.max(0, Math.min(iw - 1, x)); y = Math.max(0, Math.min(ih - 1, y));
          const x0 = Math.floor(x), y0 = Math.floor(y), x1 = Math.min(iw - 1, x0 + 1), y1 = Math.min(ih - 1, y0 + 1), fx = x - x0, fy = y - y0;
          const a = (xx, yy) => px[(yy * iw + xx) * 4 + 3] / 255;
          return (a(x0, y0) * (1 - fx) + a(x1, y0) * fx) * (1 - fy) + (a(x0, y1) * (1 - fx) + a(x1, y1) * fx) * fy; };
        let n = 0, mx = 0, my = 0; const bins = new Map();
        for (let y = 0; y < ih; y++) for (let x = 0; x < iw; x++) { const i = (y * iw + x) * 4; if (px[i + 3] < 128) continue;
          n++; mx += x; my += y;
          if (px[i + 3] > 230) { const k = (px[i] >> 4) * 256 + (px[i + 1] >> 4) * 16 + (px[i + 2] >> 4), b = bins.get(k) || [0, 0, 0, 0];
            b[0]++; b[1] += px[i]; b[2] += px[i + 1]; b[3] += px[i + 2]; bins.set(k, b); } }
        if (!n) throw new Error('stage3d.inflate: ' + src + ' has no opaque pixels (it needs a transparent background)');
        const ccx = mx / n, ccy = my / n;
        // the outline as a radius per angle (px), marched out from the centre along the alpha edge
        const NA = 256, raw = [];
        for (let i = 0; i < NA; i++) { const a = i / NA * Math.PI * 2, dx = Math.cos(a), dy = -Math.sin(a); let r = 0;
          while (A(ccx + dx * r, ccy + dy * r) >= 0.5) { r += 0.25; const x = ccx + dx * r, y = ccy + dy * r;
            // the shape runs into the picture's edge: no outline to trace (an opaque tile, a cropped character)
            if (x < 0 || y < 0 || x > iw - 1 || y > ih - 1) throw new Error('stage3d.inflate: ' + src + ' touches the image edge; it needs '
              + 'the whole shape on a transparent background (cut it out, or pass a mark without its tile)'); }
          // the 0.5-alpha crossing between the last two steps (sub-pixel), not the step it was found on
          if (r > 0) { const a0 = A(ccx + dx * (r - 0.25), ccy + dy * (r - 0.25)), a1 = A(ccx + dx * r, ccy + dy * r);
            r = r - 0.25 + 0.25 * (a0 - 0.5) / Math.max(1e-6, a0 - a1); }
          raw.push(Math.max(1, r)); }
        // a traced outline carries pixel noise (+-0.5 px), which the steep rim of the dome turns into visible ridges on a
        // small cut-out: smooth it around the circle (gaussian over ~3 degrees, a few px of arc) before building the body
        const SIG = 2, KW = 6, rr = raw.map((_, i) => { let s = 0, w = 0;
          for (let k = -KW; k <= KW; k++) { const g = Math.exp(-k * k / (2 * SIG * SIG)); s += g * raw[(i + k + NA) % NA]; w += g; } return s / w; });
        // the traced outline must BE the shape. Holes: transparent pixels the picture's edge cannot reach (a background
        // removed by colour punches out white eyes). Lost parts: solid pixels outside the traced outline (a crescent's
        // horns, a second piece, anything not star-shaped about the centre).
        const reach = new Uint8Array(iw * ih), stack = [];
        const seed = (x, y) => { const i = y * iw + x; if (!reach[i] && px[i * 4 + 3] < 128) { reach[i] = 1; stack.push(i); } };
        for (let x = 0; x < iw; x++) { seed(x, 0); seed(x, ih - 1); } for (let y = 0; y < ih; y++) { seed(0, y); seed(iw - 1, y); }
        while (stack.length) { const i = stack.pop(), x = i % iw, y = (i - x) / iw;
          if (x > 0) seed(x - 1, y); if (x < iw - 1) seed(x + 1, y); if (y > 0) seed(x, y - 1); if (y < ih - 1) seed(x, y + 1); }
        let holes = 0, lost = 0;
        for (let y = 0; y < ih; y++) for (let x = 0; x < iw; x++) { const i = y * iw + x;
          if (px[i * 4 + 3] < 128) { if (!reach[i]) holes++; continue; }
          const ang = Math.atan2(-(y - ccy), x - ccx), f = ((ang + Math.PI * 2) % (Math.PI * 2)) / (Math.PI * 2) * NA, i0 = Math.floor(f) % NA;
          if (Math.hypot(x - ccx, y - ccy) > Math.max(rr[i0], rr[(i0 + 1) % NA]) + 1.5) lost++; }
        if (holes > n * 0.002) throw new Error('stage3d.inflate: ' + src + ' has transparent holes inside its shape (' + holes + ' px): '
          + 'a background removed by colour also removed parts of the face; cut it out with scripts/cutout.py (flood fill from the edge)');
        if (lost > n * 0.01) throw new Error('stage3d.inflate: ' + src + ' is not one star-shaped body (' + lost + ' of ' + n + ' solid px lie '
          + 'outside the outline traced from its centre): a crescent, a ring or several parts cannot be inflated');
        const R = Math.max(...rr), rOf = (a) => { a = ((a % (Math.PI * 2)) + Math.PI * 2) % (Math.PI * 2);
          const f = a / (Math.PI * 2) * NA, i0 = Math.floor(f) % NA, i1 = (i0 + 1) % NA, k = f - Math.floor(f);
          return (rr[i0] * (1 - k) + rr[i1] * k) / R; };
        // the picture's own colours (bins over 1.5% of the body), the largest is the body colour
        const tot = [...bins.values()].reduce((s, b) => s + b[0], 0);
        // small parts keep their colour (a four-colour logo on a white tile): a bin counts from 0.3% of the body or 4
        // pixels; near-duplicates (anti-aliased blends) merge into the larger colour
        const pal = [...bins.values()].filter((b) => b[0] >= Math.max(4, tot * 0.003)).sort((a, b) => b[0] - a[0]).map((b) => [b[1] / b[0], b[2] / b[0], b[3] / b[0]]);
        const merged = []; for (const q of pal) if (!merged.some((m) => Math.hypot(m[0] - q[0], m[1] - q[1], m[2] - q[2]) < 56)) merged.push(q);
        if (!merged.length) throw new Error('stage3d.inflate: ' + src + ' has no solid colour (every pixel is semi-transparent)');
        // flat art (a few colours) is snapped crisp; shaded art (a gradient, a photo) keeps its smooth upscale instead of banding
        const snap = merged.length <= 12;
        const bodyCol = p.color ? new THREE.Color(p.color) : new THREE.Color().setRGB(merged[0][0] / 255, merged[0][1] / 255, merged[0][2] / 255, THREE.SRGBColorSpace);
        // the face: a smooth upscale, each pixel snapped to the nearest palette colour (crisp edges at any size)
        const S = p.faceRes || 1024, half = R * 1.04, fc = document.createElement('canvas'); fc.width = fc.height = S;
        const f2 = fc.getContext('2d', {willReadFrequently: true}); f2.imageSmoothingEnabled = true; f2.imageSmoothingQuality = 'high';
        f2.fillStyle = '#' + bodyCol.getHexString(THREE.SRGBColorSpace); f2.fillRect(0, 0, S, S);
        // the cut-out's soft fringe carries the old background's colour (near white): painted as body colour instead, or it
        // snaps to the eye colour and rings the rim with white specks
        const sc0 = document.createElement('canvas'); sc0.width = iw; sc0.height = ih; const s0 = sc0.getContext('2d'), sd = s0.createImageData(iw, ih);
        const bs = new THREE.Color(bodyCol).convertLinearToSRGB();
        for (let i = 0; i < px.length; i += 4) { const solid = px[i + 3] >= 230; sd.data[i] = solid ? px[i] : Math.round(bs.r * 255);
          sd.data[i + 1] = solid ? px[i + 1] : Math.round(bs.g * 255); sd.data[i + 2] = solid ? px[i + 2] : Math.round(bs.b * 255); sd.data[i + 3] = 255; }
        s0.putImageData(sd, 0, 0);
        f2.drawImage(sc0, (ccx - half) / (2 * half) * -S, (ccy - half) / (2 * half) * -S, iw / (2 * half) * S, ih / (2 * half) * S);
        const fd = f2.getImageData(0, 0, S, S), d = fd.data;
        if (snap) for (let i = 0; i < d.length; i += 4) { let best = 0, bd = 1e9;
          for (let j = 0; j < merged.length; j++) { const m = merged[j], e = (d[i] - m[0]) ** 2 + (d[i + 1] - m[1]) ** 2 + (d[i + 2] - m[2]) ** 2; if (e < bd) { bd = e; best = j; } }
          d[i] = merged[best][0]; d[i + 1] = merged[best][1]; d[i + 2] = merged[best][2]; d[i + 3] = 255; }
        if (snap) f2.putImageData(fd, 0, 0);
        const tex = new THREE.CanvasTexture(fc); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = renderer.capabilities.getMaxAnisotropy();
        // the inflated body (outline radius 1 = R px): front dome `front`, back dome `back`, rings centre -> rim
        const front = p.front == null ? 0.42 : p.front, back = p.back == null ? 0.3 : p.back, N = 192, SR = 40;
        const prof = (s) => Math.pow(Math.max(0, 1 - Math.pow(s, 4)), 0.4);
        const pos = [], uv = [], idx = [], k = R / half;
        const ring = (side) => { const base = pos.length / 3;
          pos.push(0, 0, side * (side > 0 ? front : back)); uv.push(0.5, 0.5);
          for (let j = 1; j <= SR; j++) { const s = 1 - Math.pow(1 - j / SR, 2); for (let i = 0; i < N; i++) { const a = i / N * Math.PI * 2, r = rOf(a) * s;
            const x = Math.cos(a) * r, y = Math.sin(a) * r; pos.push(x, y, side * (side > 0 ? front : back) * prof(s)); uv.push(0.5 + x * k / 2, 0.5 + y * k / 2); } }
          const at = (j, i) => (j === 0 ? base : base + 1 + (j - 1) * N + (i % N)), start = idx.length;
          for (let i = 0; i < N; i++) side > 0 ? idx.push(at(0, 0), at(1, i), at(1, i + 1)) : idx.push(at(0, 0), at(1, i + 1), at(1, i));
          let mid = null;
          for (let j = 1; j < SR; j++) { if (mid == null && 1 - Math.pow(1 - j / SR, 2) >= 0.86) mid = idx.length;
            for (let i = 0; i < N; i++) { const a = at(j, i), b = at(j, i + 1), c2 = at(j + 1, i), e = at(j + 1, i + 1);
              side > 0 ? idx.push(a, c2, b, b, c2, e) : idx.push(a, b, c2, b, e, c2); } }
          return [start, mid, idx.length]; };
        const gF = ring(1), gB = ring(-1);
        const g = new THREE.BufferGeometry();
        g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
        g.setIndex(idx); g.computeVertexNormals(); // the face picture is projected straight on, so it covers the front of the dome only; on the steep rim it would
        // stretch each edge texel into a streak, so the rim (s >= 0.86, outside every face feature) and the back are body colour
        g.addGroup(gF[0], gF[1] - gF[0], 0); g.addGroup(gF[1], gF[2] - gF[1], 1); g.addGroup(gB[0], gB[2] - gB[0], 1);
        const mat = (map) => new THREE.MeshPhysicalMaterial({map, color: map ? 0xffffff : bodyCol, roughness: p.roughness == null ? 0.36 : p.roughness,
          metalness: 0, clearcoat: p.clearcoat == null ? 1 : p.clearcoat, clearcoatRoughness: 0.08});
        const mesh = new THREE.Mesh(g, [mat(tex), mat(null)]); mesh.castShadow = true; mesh.receiveShadow = true;
        // size: `width` is the outline's widest extent in scene units; the body sits ON y = 0 of the group (feet down)
        const xs = rr.map((r, i) => Math.cos(i / NA * Math.PI * 2) * r / R), ys = rr.map((r, i) => Math.sin(i / NA * Math.PI * 2) * r / R);
        const sc = (p.width || 1) / (Math.max(...xs) - Math.min(...xs));
        mesh.scale.setScalar(sc); mesh.position.set(-(Math.max(...xs) + Math.min(...xs)) / 2 * sc, -Math.min(...ys) * sc, 0);
        body.add(mesh); group.userData.size = [p.width || 1, (Math.max(...ys) - Math.min(...ys)) * sc]; group.userData.color = bodyCol;
      });
      pending.push(job);
      group.userData.body = body;
      group.position.set(p.x || 0, p.y || 0, p.z || 0); group.rotation.set(p.rotX || 0, p.rotY || 0, p.rotZ || 0);
      scene.add(group);
      return group;
    },
    ready() { return Promise.all(pending); },
    // one frame: camera position, where it looks, its fov, and the focus distance for depth of field
    render(c) {
      c = c || {};
      if (c.pos) camera.position.set(...c.pos);
      camera.lookAt(...(c.look || [0, 2, 0]));
      if (c.fov) { camera.fov = c.fov; camera.updateProjectionMatrix(); }
      if (bokeh) {
        const look = new THREE.Vector3(...(c.look || [0, 2, 0]));
        bokeh.uniforms.focus.value = c.focus == null ? camera.position.distanceTo(look) : c.focus;
        if (c.aperture != null) bokeh.uniforms.aperture.value = c.aperture;
        composer.render();
      } else {
        renderer.render(scene, camera);
      }
    },
  };
  return st;
}

// a character's hop over its own clock t01 in 0..1 (anticipation crouch, an arc, a landing squash, recovery) with its
// volume kept (sx * sx * sy == 1, x and z share sx). Apply to an inflate()'d group's `userData.body`:
//   const h = Stage3D.hop(u); body.position.y = h.y; body.scale.set(h.sx, h.sy, h.sx);
// Same curve as remotion/src/runtime/character.ts.
function hop(t01, o) {
  o = o || {}; const antic = o.antic == null ? 0.15 : o.antic, land = o.land == null ? 0.15 : o.land;
  const height = o.height == null ? 0.3 : o.height, squash = o.squash == null ? 0.25 : o.squash, stretch = o.stretch == null ? 0.1 : o.stretch;
  const t = clamp01(t01); if (t <= 0 || t >= 1) return {y: 0, sx: 1, sy: 1};
  let y = 0, sy = 1;
  if (t < antic) sy = 1 - squash * Math.sin(Math.PI * (t / antic));
  else if (t < 1 - land) { const u = (t - antic) / (1 - antic - land); y = height * Math.sin(Math.PI * u); sy = 1 + stretch * Math.abs(Math.sin(2 * Math.PI * u)); }
  else sy = 1 - squash * Math.sin(Math.PI * ((t - (1 - land)) / land));
  return {y, sx: 1 / Math.sqrt(sy), sy};
}

// an object a character CARRIES rides on its real body: set every frame, after the character's pose, it sits on the top
// of the body as it is posed right now (hop height, squash and all) plus a small gap, follows its x/z, turns half as far,
// and tips with a squash. A carried card placed at a fixed height sinks into a hopping head (Grok Bot, 2026-11-18).
//   Stage3D.carry(card, bot, {h: cardHeight, gap: 0.08, dx: 0, dz: 0.1, tilt: 0});
// `character` is an inflate()'d group (its userData.size gives the body height); `h` is the object's own height at scale 1.
function carry(obj, character, o) {
  o = o || {}; const body = character.userData.body, size = character.userData.size;
  if (!body || !size) throw new Error('Stage3D.carry: the character is not an inflate()d group, or it has not loaded (await st.ready())');
  const top = character.position.y + character.scale.y * (body.position.y + size[1] * body.scale.y);
  obj.position.set(character.position.x + (o.dx || 0), top + (o.gap == null ? 0.08 : o.gap) + (o.h || 1) / 2 * obj.scale.y,
    character.position.z + (o.dz == null ? 0.1 : o.dz));
  obj.rotation.set(0, character.rotation.y * 0.5, (o.tilt || 0) + body.rotation.z + 0.25 * (body.scale.x - 1));
  return top;
}

export {create, ease, easeOut, lerp, lerp3, clamp01, hop, carry, THREE};
