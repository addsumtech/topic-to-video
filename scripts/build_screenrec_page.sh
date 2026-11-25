#!/bin/sh
# Bundle assets/html/screenrec/src.js + the Remotion tier's focus track (remotion/src/runtime/focusTrack.ts: one copy
# of the tuned code) into ONE classic script, assets/html/screenrec.js, exposing window.ScreenRec.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
"$ROOT/remotion/node_modules/.bin/esbuild" "$ROOT/assets/html/screenrec/src.js" --bundle --minify --format=iife \
  --global-name=ScreenRec --log-level=warning --outfile="$ROOT/assets/html/screenrec.js"
echo "[screenrec] built $ROOT/assets/html/screenrec.js ($(wc -c < "$ROOT/assets/html/screenrec.js") bytes)"
