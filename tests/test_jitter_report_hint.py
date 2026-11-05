"""A jitter FAIL says how big the worst tremble is and how a user who watched it and accepts it waives it by name — the
ANC film's seven sub-pixel findings (0.12-0.26 px) needed a waiver nobody could find from the report."""
import io
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import jitter_qa as jq  # noqa: E402


def test_a_fail_names_the_worst_size_and_the_waiver():
    rep = {"lines": [("error", "scene 07 (P): 'A' (2D): trembles 0.15px RMS against its own geometry", None, {}),
                     ("error", "scene 12 (L): 'B' (2D): trembles 0.26px RMS against its own geometry", None, {})],
           "universe": 2, "measured": 2, "composited": 0, "skip": {}, "seconds": 1.0}
    out = io.StringIO()
    jq.report(rep, out)
    text = out.getvalue()
    assert "worst 0.26 px" in text and "delivery_waivers" in text
