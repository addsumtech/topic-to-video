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
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
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
      key.shadow.camera.top = 12; key.shadow.camera.bottom = -12; key.shadow.radius = 6; key.shadow.bias = -0.0004;
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

export {create, ease, easeOut, lerp, lerp3, clamp01, THREE};
