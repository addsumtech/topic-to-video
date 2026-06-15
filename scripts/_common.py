"""Shared low-level helpers. No domain knowledge lives here."""
import json, os, shutil, subprocess

SOFFICE_CANDIDATES = [
    "soffice",
    "/Applications/LibreOffice.app/Contents/MacOS/soffice",
]

def run(cmd, **kw):
    """Run a command, raise on non-zero, return stdout (text)."""
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw).stdout

def have_tool(name):
    return shutil.which(name) is not None

def find_soffice():
    for cand in SOFFICE_CANDIDATES:
        if os.path.exists(cand) or shutil.which(cand):
            return cand
    return None

def audio_duration(path):
    """Seconds, via ffprobe. Source of truth for slide timing."""
    out = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "json", path])
    return float(json.loads(out)["format"]["duration"])
