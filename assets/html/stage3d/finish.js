// The stage's lens and finish (st.finish, src.js): bloom on what EMITS past white, light shafts from one strong light,
// and one colour grade, applied to the frame in linear light before tone mapping (the grade after it, on the picture).
// Every pass is a pure function of the frame: no clock, no history, fixed taps.
//
// Pictures and text stay sharp: the user forbids blur on a real screen or photo, and small text must stay crisp; bloom
// is a blur. A protect mask (one extra render, flat colours) marks every face that carries a texture — a panel's or a
// device's display, a card, a drawn instrument's window, a label — and neither glow nor shafts land there: a lit
// display's digits FEED the glow, which falls on what is around it (its bezel, the console, the air), not over its
// own text. Real pictures (displays, cards) do not feed it at all. userData.crisp = false on a drawn display lets its
// glow fall over its own face (big digits, no small text); userData.crisp = true keeps any untextured surface clear.
import * as THREE from 'three';
import {FullScreenQuad} from 'three/examples/jsm/postprocessing/Pass.js';

const VS = 'precision highp float; uniform mat4 modelViewMatrix; uniform mat4 projectionMatrix; attribute vec3 position;'
  + ' attribute vec2 uv; varying vec2 vUv; void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }';
const raw = (fs, uniforms, defines) => new THREE.RawShaderMaterial({vertexShader: VS, fragmentShader: 'precision highp float; varying vec2 vUv;\n' + fs,
  uniforms, defines: defines || {}, depthTest: false, depthWrite: false});
const tgt = (w, h, samples) => new THREE.WebGLRenderTarget(Math.max(1, w), Math.max(1, h),
  {type: THREE.HalfFloatType, samples: samples || 0, minFilter: THREE.LinearFilter, magFilter: THREE.LinearFilter, depthBuffer: !!samples});
const rgb = (v, d) => (v == null ? [d, d, d] : typeof v === 'number' ? [v, v, v] : v);

const BLOOM = {strength: 0.6, threshold: 1.0, knee: 0.5, radius: 0.5};
const RAYS = {at: null, strength: 0.5, decay: 0.965, length: 0.75, radius: 0.3};   // fed by the bloom's bright pass (its threshold)
const GRADE = {lift: 0, gamma: 1, gain: 1, saturation: 1};

function check(name, given, known) {
  for (const k of Object.keys(given || {})) if (!(k in known)) throw new Error('Stage3D.finish: ' + (name ? name + '.' : '') + k + ' is not an option (' + Object.keys(known).join(', ') + ')');
}

export function makeFinish(renderer, scene, camera, W, H, PR) {
  const RW = Math.round(W * PR), RH = Math.round(H * PR);
  const hdr = tgt(RW, RH, 4), mask = tgt(RW, RH, 4), bright = tgt(RW, RH);
  // the bloom chain: halve from the render size, then FIVE levels at W/2, W/4 ... W/32 of the frame (CSS pixels), so the
  // glow has the same size in the frame at pixelRatio 1 or 2
  const extra = Math.max(0, Math.round(Math.log2(PR))), chain = [];
  for (let i = 1, w = RW, h = RH; i <= extra + 5; i++) { w = Math.max(1, w >> 1); h = Math.max(1, h >> 1); chain.push({a: tgt(w, h), b: tgt(w, h), w, h}); }
  const levels = chain.slice(extra);
  const raysT = tgt(levels[0].w, levels[0].h);
  const quad = new FullScreenQuad(null);
  const pass = (mat, target) => { quad.material = mat; renderer.setRenderTarget(target); quad.render(renderer); };

  // bright: what the emitters show past the threshold (soft knee); the source of glow and shafts
  const brightM = raw(`uniform sampler2D tSrc, tMask; uniform float threshold, knee; void main() {
    vec4 c = texture2D(tSrc, vUv); float b = max(c.r, max(c.g, c.b)); float k = max(knee, 1e-4);
    float s = clamp(b - threshold + k, 0.0, 2.0 * k); s = s * s / (4.0 * k);
    float w = max(s, b - threshold) / max(b, 1e-4);
    vec4 m = texture2D(tMask, vUv); gl_FragColor = vec4(c.rgb * w * (1.0 - m.b) * (1.0 - m.a), 1.0); }`,
  {tSrc: {value: null}, tMask: {value: mask.texture}, threshold: {value: 1}, knee: {value: 0.5}});
  // a 2x downsample: four bilinear taps, a 4x4 box
  const downM = raw(`uniform sampler2D tSrc; uniform vec2 texel; void main() {
    vec2 o = texel * 0.5; gl_FragColor = 0.25 * (texture2D(tSrc, vUv + vec2(-o.x, -o.y)) + texture2D(tSrc, vUv + vec2(o.x, -o.y))
      + texture2D(tSrc, vUv + vec2(-o.x, o.y)) + texture2D(tSrc, vUv + vec2(o.x, o.y))); }`, {tSrc: {value: null}, texel: {value: new THREE.Vector2()}});
  // a separable gaussian (sigma 2 texels, 9 taps)
  const blurM = raw(`uniform sampler2D tSrc; uniform vec2 dir; void main() {
    float w[5]; w[0] = 0.2042; w[1] = 0.1802; w[2] = 0.1238; w[3] = 0.0663; w[4] = 0.0276;
    vec4 s = texture2D(tSrc, vUv) * w[0];
    for (int i = 1; i < 5; i++) { s += (texture2D(tSrc, vUv + dir * float(i)) + texture2D(tSrc, vUv - dir * float(i))) * w[i]; }
    gl_FragColor = s; }`, {tSrc: {value: null}, dir: {value: new THREE.Vector2()}});
  // light shafts: march from each pixel toward the light's point on screen through the bright image (GPU Gems 3, ch. 13)
  const raysM = raw(`uniform sampler2D tSrc; uniform vec2 light; uniform float aspect, decay, len, radius; void main() {
    vec2 d = (vUv - light) * len / 64.0; vec2 p = vUv; float f = 1.0; vec3 s = vec3(0.0);
    for (int i = 0; i < 64; i++) { p -= d; vec2 q = (p - light) * vec2(aspect, 1.0);
      s += texture2D(tSrc, p).rgb * f * (1.0 - smoothstep(radius * 0.5, radius, length(q))); f *= decay; }
    gl_FragColor = vec4(s / 16.0, 1.0); }`,
  {tSrc: {value: null}, light: {value: new THREE.Vector2()}, aspect: {value: W / H}, decay: {value: 0.96}, len: {value: 0.75}, radius: {value: 0.3}});
  // the frame: glow and shafts added off the mask, tone mapped (not where the mask says the surface is not tone-mapped:
  // a display on a plain stage, as the renderer draws it), sRGB, then lift / gamma / gain and saturation on the picture
  const outM = raw(`uniform sampler2D tSrc, tMask, b0, b1, b2, b3, b4, tRays; uniform float bloom, rays;
    uniform float f0, f1, f2, f3, f4; uniform vec3 lift, gamma, gain; uniform float saturation; uniform bool keepUntoned;
    #include <tonemapping_pars_fragment>
    #include <colorspace_pars_fragment>
    void main() {
      vec4 c = texture2D(tSrc, vUv); vec4 m = texture2D(tMask, vUv);
      vec3 g = f0 * texture2D(b0, vUv).rgb + f1 * texture2D(b1, vUv).rgb + f2 * texture2D(b2, vUv).rgb + f3 * texture2D(b3, vUv).rgb + f4 * texture2D(b4, vUv).rgb;
      vec3 add = (bloom * g + rays * texture2D(tRays, vUv).rgb) * (1.0 - m.r);
      vec3 x = c.rgb + add, t = x;
      #if defined(LINEAR_TONE_MAPPING)
        t = LinearToneMapping(x);
      #elif defined(REINHARD_TONE_MAPPING)
        t = ReinhardToneMapping(x);
      #elif defined(CINEON_TONE_MAPPING)
        t = CineonToneMapping(x);
      #elif defined(ACES_FILMIC_TONE_MAPPING)
        t = ACESFilmicToneMapping(x);
      #elif defined(AGX_TONE_MAPPING)
        t = AgXToneMapping(x);
      #elif defined(NEUTRAL_TONE_MAPPING)
        t = NeutralToneMapping(x);
      #endif
      if (keepUntoned) t = mix(t, x, m.g);
      vec4 o = vec4(t, max(c.a, clamp(max(add.r, max(add.g, add.b)), 0.0, 1.0)));
      #ifdef SRGB_TRANSFER
        o = sRGBTransferOETF(o);
      #endif
      vec3 y = gain * (o.rgb + lift * (1.0 - o.rgb));
      if (gamma != vec3(1.0)) y = pow(max(y, vec3(0.0)), 1.0 / gamma);
      float l = dot(y, vec3(0.2126, 0.7152, 0.0722));
      o.rgb = mix(vec3(l), y, saturation);
      gl_FragColor = o; }`, {tSrc: {value: null}, tMask: {value: mask.texture}, tRays: {value: raysT.texture},
    b0: {value: levels[0].a.texture}, b1: {value: levels[1].a.texture}, b2: {value: levels[2].a.texture}, b3: {value: levels[3].a.texture}, b4: {value: levels[4].a.texture},
    f0: {value: 0}, f1: {value: 0}, f2: {value: 0}, f3: {value: 0}, f4: {value: 0}, toneMappingExposure: {value: 1}, bloom: {value: 0}, rays: {value: 0},
    lift: {value: new THREE.Vector3()}, gamma: {value: new THREE.Vector3(1, 1, 1)}, gain: {value: new THREE.Vector3(1, 1, 1)}, saturation: {value: 1}, keepUntoned: {value: false}});
  outM.premultipliedAlpha = false;
  let outKey = null;

  // the protect mask: R = keep crisp (no glow or shafts land here): every face that carries a picture or drawn text, a
  // texture; G = a surface the renderer does not tone-map; B = a real picture (a display, a card); A = NOT an emitter.
  // Only emitters feed the glow (an emissive material, an unlit one), never a real picture: a lit lamp or display
  // blooms, a metal highlight does not haze. userData.crisp on an object or a parent decides R for it (false lets glow
  // over a drawn display). Flat colours, the scene's own depth.
  const maskMats = new Map();
  const maskMat = (crisp, unt, pic, emit, side, skip, clear) => { const k = [crisp, unt, pic, emit, side, skip, clear].join();
    if (!maskMats.has(k)) maskMats.set(k, new THREE.MeshBasicMaterial({color: new THREE.Color(crisp, unt, pic), opacity: emit ? 0 : 1,
      blending: THREE.NoBlending, side, fog: false, toneMapped: false, colorWrite: !skip, depthWrite: !clear}));
    return maskMats.get(k); };
  const isEmitter = (m) => !!(m.isMeshBasicMaterial || (m.emissive && m.emissiveIntensity > 0 && (m.emissive.r + m.emissive.g + m.emissive.b) > 0));
  const isCrisp = (o, m) => { for (let e = o; e; e = e.parent) if (e.userData && e.userData.crisp != null) return !!e.userData.crisp; return !!m.map; };
  const isPicture = (o, m) => { if (!m.map) return false; if (m.toneMapped === false) return true;
    for (let e = o.parent; e; e = e.parent) if (e.userData && e.userData.kind === 'panel') return true; return false; };
  const renderMask = () => {
    const swapped = [], hidden = [];
    scene.traverseVisible((o) => {
      if (!o.isMesh) { if (o.isPoints || o.isLine || o.isSprite) { o.visible = false; hidden.push(o); } return; }
      // a see-through overlay is left out (additive glass, a highlight), unless it carries a texture: a label or a key
      // legend printed on a clear sheet is text, crisp like any face
      const one = (m) => { const clear = m.colorWrite === false || (m.transparent && (m.depthWrite === false || m.blending !== THREE.NormalBlending));
        const skip = clear && !(m.map && m.colorWrite !== false);
        return maskMat(isCrisp(o, m) ? 1 : 0, m.toneMapped === false ? 1 : 0, isPicture(o, m) ? 1 : 0, isEmitter(m) ? 1 : 0, m.side, skip, clear); };
      swapped.push([o, o.material]); o.material = Array.isArray(o.material) ? o.material.map(one) : one(o.material); });
    const bg = scene.background, au = renderer.shadowMap.autoUpdate, cc = renderer.getClearColor(new THREE.Color()), ca = renderer.getClearAlpha();
    scene.background = null; renderer.shadowMap.autoUpdate = false;
    renderer.setRenderTarget(mask); // the background is not a picture; a flat colour (or the clear colour) is not tone-mapped by the renderer, a texture is
    renderer.setClearColor(bg && !bg.isColor ? 0x000000 : 0x00ff00, 1);   // alpha 1: the clear colour is premultiplied
    renderer.clear(); renderer.render(scene, camera);
    scene.background = bg; renderer.shadowMap.autoUpdate = au; renderer.setClearColor(cc, ca);
    for (const [o, m] of swapped) o.material = m; for (const o of hidden) o.visible = true;
  };

  let P = null;
  const api = {
    hdr,
    // set (or change, frame by frame) the options; null turns the finish off
    set(f) {
      if (f == null) { P = null; return; }
      check('', f, {bloom: 1, rays: 1, grade: 1}); check('bloom', f.bloom, BLOOM); check('rays', f.rays, RAYS); check('grade', f.grade, GRADE);
      if (f.rays && !f.rays.at) throw new Error('Stage3D.finish: rays need `at`, the light\'s point [x, y, z] in the scene');
      P = {bloom: f.bloom ? {...BLOOM, ...f.bloom} : null, rays: f.rays ? {...RAYS, ...f.rays} : null, grade: {...GRADE, ...(f.grade || {})}};
    },
    get on() { return !!P; },
    // src: the frame in linear light (render-size texture); untoned: the plain stage, whose unlit displays skip tone mapping
    run(src, untoned) {
      const cc = renderer.getClearColor(new THREE.Color()), ca = renderer.getClearAlpha(), ac = renderer.autoClear;
      renderer.autoClear = true;
      renderMask();
      renderer.setClearColor(0x000000, 0);
      const needBright = P.bloom || P.rays;
      if (needBright) {
        const th = (P.bloom || BLOOM).threshold;
        brightM.uniforms.tSrc.value = src; brightM.uniforms.threshold.value = th; brightM.uniforms.knee.value = (P.bloom || BLOOM).knee;
        pass(brightM, bright);
        let prev = bright, pw = RW, ph = RH;
        for (const L of chain) { downM.uniforms.tSrc.value = prev.texture; downM.uniforms.texel.value.set(1 / pw, 1 / ph); pass(downM, L.a); prev = L.a; pw = L.w; ph = L.h; }
        for (const L of levels) {
          blurM.uniforms.tSrc.value = L.a.texture; blurM.uniforms.dir.value.set(1 / L.w, 0); pass(blurM, L.b);
          blurM.uniforms.tSrc.value = L.b.texture; blurM.uniforms.dir.value.set(0, 1 / L.h); pass(blurM, L.a);
        }
      }
      // the bloom's levels: small to wide; radius 0 keeps the glow tight, 1 spreads it (weights sum to 1)
      const r = P.bloom ? P.bloom.radius : 0, base = [1.0, 0.8, 0.6, 0.4, 0.2].map((f) => f + (1.2 - 2 * f) * r), sum = base.reduce((a, b) => a + b, 0);
      base.forEach((v, i) => { outM.uniforms['f' + i].value = v / sum; });
      outM.uniforms.bloom.value = P.bloom ? P.bloom.strength : 0;
      let raysOn = 0;
      if (P.rays) {
        camera.updateMatrixWorld();
        const q = new THREE.Vector3(...P.rays.at).applyMatrix4(camera.matrixWorldInverse);
        if (q.z < 0) {   // the light is in front of the camera: its point on screen
          const s = new THREE.Vector3(...P.rays.at).project(camera);
          raysM.uniforms.tSrc.value = levels[0].a.texture; raysM.uniforms.light.value.set((s.x + 1) / 2, (s.y + 1) / 2);
          raysM.uniforms.decay.value = P.rays.decay; raysM.uniforms.len.value = P.rays.length; raysM.uniforms.radius.value = P.rays.radius;
          pass(raysM, raysT); raysOn = P.rays.strength;
        }
      }
      outM.uniforms.rays.value = raysOn;
      const G = P.grade; outM.uniforms.lift.value.set(...rgb(G.lift, 0)); outM.uniforms.gamma.value.set(...rgb(G.gamma, 1));
      outM.uniforms.gain.value.set(...rgb(G.gain, 1)); outM.uniforms.saturation.value = G.saturation;
      outM.uniforms.tSrc.value = src; outM.uniforms.keepUntoned.value = !!untoned; outM.uniforms.toneMappingExposure.value = renderer.toneMappingExposure;
      const key = renderer.toneMapping + '|' + renderer.outputColorSpace;
      if (key !== outKey) { outKey = key; const d = {}, tm = renderer.toneMapping;
        if (THREE.ColorManagement.getTransfer(renderer.outputColorSpace) === THREE.SRGBTransfer) d.SRGB_TRANSFER = '';
        if (tm === THREE.LinearToneMapping) d.LINEAR_TONE_MAPPING = ''; else if (tm === THREE.ReinhardToneMapping) d.REINHARD_TONE_MAPPING = '';
        else if (tm === THREE.CineonToneMapping) d.CINEON_TONE_MAPPING = ''; else if (tm === THREE.ACESFilmicToneMapping) d.ACES_FILMIC_TONE_MAPPING = '';
        else if (tm === THREE.AgXToneMapping) d.AGX_TONE_MAPPING = ''; else if (tm === THREE.NeutralToneMapping) d.NEUTRAL_TONE_MAPPING = '';
        outM.defines = d; outM.needsUpdate = true; }
      pass(outM, null);
      renderer.setClearColor(cc, ca); renderer.autoClear = ac;
    },
  };
  return api;
}
