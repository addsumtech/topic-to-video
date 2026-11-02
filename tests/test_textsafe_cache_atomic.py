"""text_safe's beat cache survives a writer that dies half-way (or another process writing it at the same moment).

WHY. Running the delivery gates in parallel lanes was tried and measured on a real 25-beat film (2026-11-02): each
census gate already drives cores/2 Chrome tabs, so three of them at once oversubscribed a 10-core machine — the run
took 997 s against ~1070 serial and two gates hit their timeouts (verdicts that differed from the serial run), so
the lanes were not kept. The cache write it exposed stays atomic: its three modes may still be run side by side."""
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))


def test_the_text_safe_beat_cache_is_written_atomically(tmp_path, monkeypatch):
    """text_safe's three modes now run at the same time and share `._textsafe_cache.json`; a write torn by another
    writer (or a crash) must leave the previous cache whole, never a half file."""
    import json
    import text_safe_qa as ts
    ts._save_beat_cache(str(tmp_path), {"a": 1})
    real = json.dump

    def torn(obj, fh, **kw):
        fh.write('{"half')
        raise OSError("disk full")
    monkeypatch.setattr(ts.json, "dump", torn)
    ts._save_beat_cache(str(tmp_path), {"a": 2, "b": 3})
    monkeypatch.setattr(ts.json, "dump", real)
    assert ts._load_beat_cache(str(tmp_path)) == {"a": 1}
    assert not [p for p in os.listdir(tmp_path) if p.endswith(".tmp")]
