#!/bin/sh
# Bundle assets/html/stage3d/src.js + three.js (remotion/node_modules, pinned there) into ONE classic script,
# assets/html/stage3d.js, exposing window.Stage3D — so a film page loads it from file:// with a plain <script>.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/remotion/node_modules/.bin/esbuild" "$ROOT/assets/html/stage3d/src.js" --bundle --minify --format=iife \
  --global-name=Stage3D --log-level=warning --outfile="$ROOT/assets/html/stage3d.js" \
  --alias:three="$ROOT/remotion/node_modules/three/build/three.module.js" \
  --alias:three/examples="$ROOT/remotion/node_modules/three/examples"
echo "[stage3d] built $ROOT/assets/html/stage3d.js ($(wc -c < "$ROOT/assets/html/stage3d.js") bytes)"
