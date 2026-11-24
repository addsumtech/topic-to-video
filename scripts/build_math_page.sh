#!/bin/sh
# Bundle assets/html/math/src.js + the Remotion tier's maths core (remotion/src/runtime/mathCore.ts, pathCore.ts,
# mathKey.ts: one copy of the tuned code) into ONE classic script, assets/html/math.js, exposing window.MathFilm.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/remotion/node_modules/.bin/esbuild" "$ROOT/assets/html/math/src.js" --bundle --minify --format=iife \
  --global-name=MathFilm --log-level=warning --outfile="$ROOT/assets/html/math.js"
echo "[math] built $ROOT/assets/html/math.js ($(wc -c < "$ROOT/assets/html/math.js") bytes)"
