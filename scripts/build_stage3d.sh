#!/bin/sh
# Bundle the 3D stage into classic scripts a film page loads from file:// with a plain <script>:
#   assets/html/stage3d.js        src.js + three.js                 -> window.Stage3D
#   assets/html/stage3d_splat.js  Spark (Gaussian splats), optional -> window.Stage3DSplat; uses Stage3D's own THREE
# three, Spark and esbuild come from the stage's OWN pinned toolchain (assets/html/stage3d/package.json), not from
# remotion/'s three, which Remotion pins (Spark needs three r180+). Install it once: cd assets/html/stage3d && npm ci
# Usage: build_stage3d.sh [out_dir]   (default assets/html; a check builds into a temporary folder and compares)
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
D="$ROOT/assets/html/stage3d"
NM="$D/node_modules"
OUT="${1:-$ROOT/assets/html}"
if [ ! -x "$NM/.bin/esbuild" ] || [ ! -f "$NM/three/build/three.module.js" ] || [ ! -d "$NM/@sparkjsdev/spark" ]; then
  echo "[stage3d] the stage's toolchain is not installed: cd $D && npm ci" >&2; exit 1
fi
"$NM/.bin/esbuild" "$D/src.js" --bundle --minify --format=iife \
  --global-name=Stage3D --log-level=warning --outfile="$OUT/stage3d.js" \
  --alias:three="$NM/three/build/three.module.js" \
  --alias:three/examples="$NM/three/examples"
# Spark imports 'three' and 'three/addons/...': both resolve to the core bundle's THREE (one three in the page, or a
# SplatMesh is not an Object3D of the stage's scene)
"$NM/.bin/esbuild" "$D/splat.js" --bundle --minify --format=iife \
  --global-name=Stage3DSplat --log-level=warning --outfile="$OUT/stage3d_splat.js" \
  --alias:three="$D/three_global.cjs" \
  --alias:three/addons="$NM/three/examples/jsm"
echo "[stage3d] built $OUT/stage3d.js ($(wc -c < "$OUT/stage3d.js") bytes), $OUT/stage3d_splat.js ($(wc -c < "$OUT/stage3d_splat.js") bytes)"
