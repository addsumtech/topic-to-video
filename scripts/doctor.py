"""Environment preflight for the topic-to-video pipeline. Reports which tools/libraries are
present and, for each missing one, what stage it gates and how to install it — so a missing
dependency surfaces in ~1s up front instead of mid-pipeline.

Each check is REQUIRED (core render path; absence -> exit 1) or OPTIONAL (a specific stage
degrades or is unavailable; absence -> warning only). Mirrors check_av.py: a pure
`evaluate(...)` over probe results, a `check()` IO wrapper, and a `main()` that prints a
human summary (or --json) and exits non-zero only when a REQUIRED check fails.
"""
import argparse, importlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _common

# (key, required, probe() -> bool, gates, install hint)
def _has_tool(name):
    return lambda: _common.have_tool(name)

def _has_module(mod):
    def probe():
        try:
            importlib.import_module(mod)
            return True
        except Exception:
            return False
    return probe

def _has_soffice():
    return _common.find_soffice() is not None

def _has_chrome():
    return _common.find_chrome() is not None

def _has_bundled_font():
    return os.path.exists(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                       "..", "assets", "fonts", "DejaVuSans.ttf"))

def _has_ocr():
    # scanned / image-only PDFs have no text layer; without OCR the only path is reading the page
    # as an IMAGE, which works for a handful of pages and not for a 200-page scan.
    return _common.have_tool("tesseract") or _has_module("pytesseract")()

def _has_transcribe():
    # a recorded talk / podcast / screen-capture carries its content in SPEECH. Without a
    # transcriber that content is simply unreachable — frames can be sampled, words cannot.
    return any(_has_module(m)() for m in ("whisper", "faster_whisper", "mlx_whisper"))

def _has_remotion():
    # the cinematic tier needs Node + the installed remotion/ project (the bespoke-shot library)
    node = _common.have_tool("npx")
    installed = os.path.isdir(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                           "..", "remotion", "node_modules"))
    return node and installed

CHECKS = [
    ("ffmpeg",      True,  _has_tool("ffmpeg"),   "rendering clips + concat",        "brew install ffmpeg"),
    ("ffprobe",     True,  _has_tool("ffprobe"),  "audio duration (slide timing)",   "comes with ffmpeg (brew install ffmpeg)"),
    ("PIL",         True,  _has_module("PIL"),    "captions + image fitting",        "pip install pillow"),
    ("PyMuPDF",     False, _has_module("fitz"),   "pdf/pptx -> frames (ingest)",     "pip install pymupdf"),
    ("python-pptx", False, _has_module("pptx"),   "pptx speaker notes (ingest)",     "pip install python-pptx"),
    ("edge-tts",    False, _has_module("edge_tts"), "neural voice + per-word timings", "pip install edge-tts (else falls back to macOS 'say')"),
    ("soffice",     False, _has_soffice,          "pptx -> pdf (ingest)",            "install LibreOffice (or export the deck to PDF yourself)"),
    ("Google Chrome", False, _has_chrome,         "html-pages tier (render_html + keyframe_qa)", "install Google Chrome (or use the programmatic scene tiers)"),
    ("bundled font", False, _has_bundled_font,    "default Latin captions",          "restore assets/fonts/DejaVuSans.ttf"),
    ("OCR (tesseract)", False, _has_ocr,       "text out of SCANNED / image-only PDFs at step 3 (grounding material)", "brew install tesseract && pip install pytesseract (without it a scan can only be READ AS IMAGES — fine for a few pages, not for a long document)"),
    ("transcription", False, _has_transcribe,   "audio/video source material at step 3 (a recorded talk, podcast, screen capture)", "pip install openai-whisper (or faster-whisper / mlx-whisper). WITHOUT IT SPEECH IS UNREACHABLE — say so in the interview rather than discovering it mid-pipeline"),
    ("remotion",    False, _has_remotion,         "bespoke-shot cinematic tier (meta.renderer=remotion)", "install Node.js, then `cd remotion && npm install` (else use the default local renderer)"),
]


def evaluate(results):
    """results: list of (key, required, present, gates, hint). Returns the report dict."""
    missing_required = [r for r in results if r[1] and not r[2]]
    missing_optional = [r for r in results if not r[1] and not r[2]]
    return {
        "ok": not missing_required,
        "present": [r[0] for r in results if r[2]],
        "missing_required": [{"name": r[0], "gates": r[3], "install": r[4]} for r in missing_required],
        "missing_optional": [{"name": r[0], "gates": r[3], "install": r[4]} for r in missing_optional],
    }


def check():
    return evaluate([(k, req, probe(), gates, hint) for (k, req, probe, gates, hint) in CHECKS])


def main():
    ap = argparse.ArgumentParser(description="Environment preflight for topic-to-video")
    ap.add_argument("--json", action="store_true", help="emit the result dict as JSON")
    a = ap.parse_args()
    r = check()
    if a.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
    else:
        print(f"[doctor] {'OK' if r['ok'] else 'FAIL'}  "
              f"{len(r['present'])} present, {len(r['missing_required'])} required missing, "
              f"{len(r['missing_optional'])} optional missing")
        print(f"  present: {', '.join(r['present']) or '(none)'}")
        for m in r["missing_required"]:
            print(f"  MISSING (required): {m['name']} — gates {m['gates']} — {m['install']}")
        for m in r["missing_optional"]:
            print(f"  missing (optional): {m['name']} — gates {m['gates']} — {m['install']}")
    sys.exit(0 if r["ok"] else 1)


if __name__ == "__main__":
    main()
