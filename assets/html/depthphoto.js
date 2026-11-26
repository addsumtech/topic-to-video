// depthphoto.js — a real photo that moves in 3D (the documentary 2.5D look): one still + its depth map
// (scripts/photo_depth.py) drawn as a displaced grid mesh in WebGL2, a pure function of t.
//
//   const dp = DepthPhoto.create({canvas});                        // one GL context for every photo of the film
//   const lm = await dp.photo('img/lm.jpg', 'img/lm.depth.png', {
//     from: {zoom: 1, x: 0, y: 0}, to: {zoom: 1.06, x: -20, y: 0},  // keyframes of the camera
//     focus: 0.5, dolly: 1, center: [0.5, 0.5], start: 0, dur: 1.0, ease: 'inout'});
//   window.seek = (t) => dp.draw(lm, t - shotStart);                // t in the shot's own seconds
//
// THE MOVE. The photo covers the frame about `center` (the photo point at the frame centre, 0..1). A pixel at depth n
// (0 far .. 1 near, the depth map) is scaled by zoom^(1 + dolly*(n - focus)) about the frame centre (a push: near
// things grow faster than the focus plane, far ones slower) and shifted by [x, y]*(n - focus): x and y are the
// parallax in px between the nearest and the farthest plane, so the `focus` plane stays put (focus at the subject =
// an orbit round it; focus 0 = the background holds and the foreground slides, a drift). from -> to runs over `dur`
// seconds from `start` with `ease` ('inout', 'out' or 'linear'), then HOLDS. Keep it short and decisive, starting at
// the cut: the slow landing of a move is a creep, and a grainy scan shimmers through it (film_qc glide). Measured on
// Apollo scans (2026-11-26): a 1.6 s inout ease shimmered 10-25 % (red over 3 %), and so did the same push resampled
// ideally (Lanczos on the CPU, 11 %), so it is the move, not the drawing; 1.0 s from the cut passed.
//
// REFUSES (photo() rejects, so the page's filmReady fails and film_frames stops) a move that would:
//   - draw the photo past its native pixels (screen px per photo px over 1 anywhere, at either keyframe);
//   - show the photo's edge (it must cover the frame at every t);
//   - stretch the picture at a depth edge by more than DepthPhoto.MAX_STRETCH px. A displaced mesh has no pixels
//     behind a foreground edge, so the triangles that span the edge stretch; the depth is dilated toward the near
//     side first (a max filter), so what stretches is the BACKGROUND's texture, never the foreground's edge dragged
//     into a rubber sheet. Stretch over flat ground (a black sky, a plain wall) is invisible and not counted.
// shot.report = {magnification, stretch, at} says what was measured. The browser decodes the 16-bit depth PNG at 8
// bits: 256 levels, ~0.1 px of parallax a level at a 28 px move (not seen on the demo's smooth lunar ground).
//
// No blur anywhere, no depth of field: the photo is drawn sharp (mipmapped, supersampled 2x like Stage3D's
// pixelRatio). The page needs the frames served over http (film_frames.py does): WebGL refuses file:// images.
window.DepthPhoto = (() => {
  const CELL = 4;          // mesh cell, in frame px at the cover scale
  const DILATE = 2;        // cells the near side of every depth edge is grown by (the edge-aware fill)
  const REACH = 3;         // cells over which a depth edge's stretch is measured (a soft edge spans 2-3)
  const FLAT = 0.04;       // luminance range (0..1) under which the stretched background counts as flat ground
  const EASE = {
    linear: (p) => p,
    out: (p) => 1 - Math.pow(1 - p, 3),
    inout: (p) => (p < 0.5 ? 4 * p * p * p : 1 - Math.pow(-2 * p + 2, 3) / 2),
  };
  const VS = `#version 300 es
    in vec2 uv; in float n; out vec2 v;
    uniform vec2 frame, size, center, shift; uniform float zoom, dolly, focus;
    void main() {
      vec2 p = frame * 0.5 + (uv - center) * size * pow(zoom, 1.0 + dolly * (n - focus)) + shift * (n - focus);
      gl_Position = vec4(p.x / frame.x * 2.0 - 1.0, 1.0 - p.y / frame.y * 2.0, 0.5 - 0.5 * n, 1.0);
      v = uv; }`;
  const FS = `#version 300 es
    precision highp float; in vec2 v; uniform sampler2D photo; out vec4 o;
    void main() { o = vec4(texture(photo, v).rgb, 1.0); }`;

  async function bitmap(src) {
    const r = await fetch(src);
    if (!r.ok) throw new Error('DepthPhoto: cannot load ' + src + ' (' + r.status + ')');
    return createImageBitmap(await r.blob(), {colorSpaceConversion: 'none', premultiplyAlpha: 'none'});
  }
  // an image's pixels at w x h (area-averaged by the browser), as Uint8ClampedArray RGBA
  function pixels(bmp, w, h) {
    const c = new OffscreenCanvas(w, h), g = c.getContext('2d');
    g.imageSmoothingQuality = 'high';
    g.drawImage(bmp, 0, 0, w, h);
    return g.getImageData(0, 0, w, h).data;
  }

  function create(o) {
    const canvas = o.canvas, W = o.width || 1920, H = o.height || 1080, pr = o.pixelRatio || 2;
    canvas.width = W * pr; canvas.height = H * pr;
    canvas.style.width = W + 'px'; canvas.style.height = H + 'px';
    const gl = canvas.getContext('webgl2', {antialias: true, preserveDrawingBuffer: true, alpha: false});
    if (!gl) throw new Error('DepthPhoto: WebGL2 unavailable');
    const sh = (type, src) => { const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error('DepthPhoto shader: ' + gl.getShaderInfoLog(s)); return s; };
    const prog = gl.createProgram();
    gl.attachShader(prog, sh(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, sh(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error('DepthPhoto link: ' + gl.getProgramInfoLog(prog));
    const U = {}; for (const k of ['frame', 'size', 'center', 'shift', 'zoom', 'dolly', 'focus', 'photo']) U[k] = gl.getUniformLocation(prog, k);

    // the move's state at shot time t
    function state(m, t) {
      const p = EASE[m.ease](Math.max(0, Math.min(1, m.dur > 0 ? (t - m.start) / m.dur : 1)));
      const L = (k) => m.from[k] + (m.to[k] - m.from[k]) * p;
      return {zoom: L('zoom'), x: L('x'), y: L('y')};
    }

    async function photo(src, depthSrc, move) {
      const m = Object.assign({focus: 0.5, dolly: 1, center: [0.5, 0.5], start: 0, dur: 1.0, ease: 'inout'}, move);
      m.from = Object.assign({zoom: 1, x: 0, y: 0}, m.from); m.to = Object.assign({}, m.from, m.to);
      if (!EASE[m.ease]) throw new Error('DepthPhoto: ease must be ' + Object.keys(EASE).join(', '));
      const [img, dimg] = await Promise.all([bitmap(src), bitmap(depthSrc)]);
      const iw = img.width, ih = img.height;
      if (Math.max(iw, ih) > gl.getParameter(gl.MAX_TEXTURE_SIZE)) throw new Error('DepthPhoto: ' + src + ' is larger than this GPU takes');
      const cover = Math.max(W / iw, H / ih), size = [iw * cover, ih * cover];
      const cols = Math.ceil(size[0] / CELL), rows = Math.ceil(size[1] / CELL), nx = cols + 1, ny = rows + 1;
      // depth and luminance per vertex; then the near side grown by DILATE cells (max filter, separable)
      const dp = pixels(dimg, nx, ny), lp = pixels(img, nx, ny);
      let n = new Float32Array(nx * ny); const lum = new Float32Array(nx * ny);
      for (let i = 0; i < nx * ny; i++) { n[i] = dp[4 * i] / 255; lum[i] = (0.299 * lp[4 * i] + 0.587 * lp[4 * i + 1] + 0.114 * lp[4 * i + 2]) / 255; }
      for (const [dx, dy] of [[1, 0], [0, 1]]) {
        const out = new Float32Array(nx * ny);
        for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
          let v = 0;
          for (let k = -DILATE; k <= DILATE; k++) {
            const a = Math.min(nx - 1, Math.max(0, i + k * dx)), b = Math.min(ny - 1, Math.max(0, j + k * dy));
            v = Math.max(v, n[b * nx + a]);
          }
          out[j * nx + i] = v;
        }
        n = out;
      }
      // the screen position of every vertex at a keyframe, as the vertex shader computes it
      const uvOf = (i, j) => [Math.min(1, i / cols), Math.min(1, j / rows)];
      const at = (s, i, j) => { const [u, v] = uvOf(i, j), z = Math.pow(s.zoom, 1 + m.dolly * (n[j * nx + i] - m.focus));
        return [W / 2 + (u - m.center[0]) * size[0] * z + s.x * (n[j * nx + i] - m.focus),
                H / 2 + (v - m.center[1]) * size[1] * z + s.y * (n[j * nx + i] - m.focus)]; };
      const rigid = (s, i, j) => { const [u, v] = uvOf(i, j);     // the same point on the focus plane
        return [W / 2 + (u - m.center[0]) * size[0] * s.zoom, H / 2 + (v - m.center[1]) * size[1] * s.zoom]; };
      let nmin = 1, nmax = 0; for (const v of n) { nmin = Math.min(nmin, v); nmax = Math.max(nmax, v); }
      const report = {magnification: 0, stretch: 0, at: null};
      for (const s of [m.from, m.to]) {
        // native pixels: screen px per photo px, the largest plane scale
        for (const v of [nmin, nmax]) report.magnification = Math.max(report.magnification, cover * Math.pow(s.zoom, 1 + m.dolly * (v - m.focus)));
        // the photo covers the frame: every border vertex stays outside it
        for (let i = 0; i < nx; i++) {
          if (at(s, i, 0)[1] > 0.01 || at(s, i, rows)[1] < H - 0.01) throw new Error('DepthPhoto: the move shows the top or bottom edge of ' + src + ': zoom in or move less');
        }
        for (let j = 0; j < ny; j++) {
          if (at(s, 0, j)[0] > 0.01 || at(s, cols, j)[0] < W - 0.01) throw new Error('DepthPhoto: the move shows the left or right edge of ' + src + ': zoom in or move less');
        }
        // stretch at depth edges: how far two vertices REACH cells apart separate beyond the focus plane's rigid move,
        // counted only where the background between them has texture to smear
        const off = new Float32Array(2 * nx * ny);
        for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
          const a = at(s, i, j), r = rigid(s, i, j), k = 2 * (j * nx + i); off[k] = a[0] - r[0]; off[k + 1] = a[1] - r[1];
        }
        for (const [dx, dy] of [[1, 0], [0, 1]]) {
          for (let j = 0; j + REACH * dy < ny; j++) for (let i = 0; i + REACH * dx < nx; i++) {
            const A = j * nx + i, B = (j + REACH * dy) * nx + i + REACH * dx;
            const d = Math.hypot(off[2 * A] - off[2 * B], off[2 * A + 1] - off[2 * B + 1]);
            if (d <= report.stretch) continue;
            // the far side of the pair is what stretches: its luminance over REACH cells beyond it
            const far = n[A] < n[B] ? A : B, sx = far === A ? -dx : dx, sy = far === A ? -dy : dy;
            let lo = 1, hi = 0;
            for (let k = 0; k <= REACH; k++) {
              const ii = Math.min(nx - 1, Math.max(0, (far % nx) + k * sx)), jj = Math.min(ny - 1, Math.max(0, Math.floor(far / nx) + k * sy));
              const l = lum[jj * nx + ii]; lo = Math.min(lo, l); hi = Math.max(hi, l);
            }
            if (hi - lo < FLAT) continue;
            report.stretch = d; report.at = [+((A % nx) / cols).toFixed(3), +(Math.floor(A / nx) / rows).toFixed(3)];
          }
        }
      }
      if (report.magnification > 1 + 1e-6) {
        throw new Error('DepthPhoto: the move draws ' + src + ' at ' + report.magnification.toFixed(2) +
          'x its native pixels (max 1): zoom less, or use a larger original');
      }
      if (report.stretch > DepthPhoto.MAX_STRETCH) {
        throw new Error('DepthPhoto: the move stretches ' + src + ' by ' + report.stretch.toFixed(1) + ' px at a depth edge (uv ' +
          report.at + '; max ' + DepthPhoto.MAX_STRETCH + '): move less, or put the focus plane at that edge');
      }
      // the mesh
      const verts = new Float32Array(nx * ny * 3);
      for (let j = 0; j < ny; j++) for (let i = 0; i < nx; i++) {
        const k = 3 * (j * nx + i), [u, v] = uvOf(i, j); verts[k] = u; verts[k + 1] = v; verts[k + 2] = n[j * nx + i];
      }
      const idx = new Uint32Array(cols * rows * 6);
      for (let j = 0, q = 0; j < rows; j++) for (let i = 0; i < cols; i++, q += 6) {
        const a = j * nx + i, b = a + 1, c = a + nx, d = c + 1;
        idx.set([a, c, b, b, c, d], q);
      }
      const vao = gl.createVertexArray(); gl.bindVertexArray(vao);
      const vb = gl.createBuffer(); gl.bindBuffer(gl.ARRAY_BUFFER, vb); gl.bufferData(gl.ARRAY_BUFFER, verts, gl.STATIC_DRAW);
      const lu = gl.getAttribLocation(prog, 'uv'), ln = gl.getAttribLocation(prog, 'n');
      gl.enableVertexAttribArray(lu); gl.vertexAttribPointer(lu, 2, gl.FLOAT, false, 12, 0);
      gl.enableVertexAttribArray(ln); gl.vertexAttribPointer(ln, 1, gl.FLOAT, false, 12, 8);
      const ib = gl.createBuffer(); gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ib); gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, idx, gl.STATIC_DRAW);
      gl.bindVertexArray(null);
      const tex = gl.createTexture(); gl.bindTexture(gl.TEXTURE_2D, tex);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false); gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
      gl.pixelStorei(gl.UNPACK_COLORSPACE_CONVERSION_WEBGL, gl.NONE);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA8, gl.RGBA, gl.UNSIGNED_BYTE, img);
      gl.generateMipmap(gl.TEXTURE_2D);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR_MIPMAP_LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      img.close(); dimg.close();
      return {src, move: m, size, report, vao, tex, count: idx.length};
    }

    function draw(shot, t) {
      const s = state(shot.move, t), m = shot.move;
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.clearColor(0, 0, 0, 1); gl.clearDepth(1); gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
      gl.enable(gl.DEPTH_TEST); gl.depthFunc(gl.LEQUAL);
      gl.useProgram(prog);
      gl.uniform2f(U.frame, W, H); gl.uniform2f(U.size, shot.size[0], shot.size[1]);
      gl.uniform2f(U.center, m.center[0], m.center[1]); gl.uniform2f(U.shift, s.x, s.y);
      gl.uniform1f(U.zoom, s.zoom); gl.uniform1f(U.dolly, m.dolly); gl.uniform1f(U.focus, m.focus);
      gl.activeTexture(gl.TEXTURE0); gl.bindTexture(gl.TEXTURE_2D, shot.tex); gl.uniform1i(U.photo, 0);
      gl.bindVertexArray(shot.vao); gl.drawElements(gl.TRIANGLES, shot.count, gl.UNSIGNED_INT, 0); gl.bindVertexArray(null);
      gl.finish();
    }

    return {photo, draw, state, gl};
  }

  return {create, MAX_STRETCH: 12};
})();
