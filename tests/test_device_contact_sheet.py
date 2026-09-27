"""The contact sheet is a tool a person runs by hand: run wrongly, it says how to run it."""
import os
import subprocess
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_run_without_a_path_it_prints_its_usage():
    r = subprocess.run([sys.executable, os.path.join(_ROOT, "scripts", "device_contact_sheet.py")],
                       capture_output=True, text=True)
    assert r.returncode != 0 and "usage: device_contact_sheet.py <out.png>" in r.stderr, (r.returncode, r.stderr)
