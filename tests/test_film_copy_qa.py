"""film_copy_qa: words a film shows must come from its sources or be declared (with a reason) in copy_ok.json."""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "scripts", "film_copy_qa.py")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import _common as _c  # noqa: E402
import film_copy_qa as fcq  # noqa: E402

try:
    CHROME = _c.find_chrome()
except Exception:
    CHROME = None

DOCS = ("An approval card asks whether the Bot may take an action, with Allow once and Deny.\n"
        "Sales outbound. Owns account research, contact prioritization, and review-ready outreach.\n")

PAGE = """<!doctype html><html><body style="margin:0;background:#fff">
<canvas id="c" width="800" height="400"></canvas><div id="dom" style="position:absolute;left:10px;top:420px"></div>
<script>
const g = document.getElementById('c').getContext('2d');
g.font = '40px sans-serif'; g.fillText('Allow once', 20, 60); g.fillText('To: 5 account contacts', 20, 120);
window.seek = (t) => { const d = document.getElementById('dom');
  d.textContent = t < 0.4 ? 'Owns review-ready outreach'.slice(0, 6) : 'Owns review-ready outreach'; };
</script></body></html>"""


def _film(tmp_path, ok=None):
    (tmp_path / "input" / "sources").mkdir(parents=True)
    (tmp_path / "input" / "sources" / "docs.txt").write_text(DOCS)
    (tmp_path / "film.html").write_text(PAGE)
    (tmp_path / "timeline.json").write_text('{"duration": 1.0}')
    if ok is not None:
        (tmp_path / "copy_ok.json").write_text(json.dumps(ok))
    return tmp_path


def _run(d):
    r = subprocess.run([sys.executable, SCRIPT, str(d), "--every", "0.25", "--json"], capture_output=True, text=True,
                       timeout=300)
    return r, (json.loads(r.stdout) if r.stdout.strip().startswith("{") else None)


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
def test_invented_ui_text_is_flagged_and_sourced_text_passes(tmp_path):
    r, j = _run(_film(tmp_path))
    assert r.returncode == 1, r.stdout + r.stderr
    flagged = [u["text"] for u in j["unsourced"]]
    assert flagged == ["To: 5 account contacts"], flagged       # sourced, the excerpt and the typing partial all pass


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
def test_a_declared_string_passes_only_with_a_reason(tmp_path):
    r, j = _run(_film(tmp_path, ok={"To: 5 account contacts": "illustration of the docs' recipients field"}))
    assert r.returncode == 0, r.stdout + r.stderr
    (tmp_path / "copy_ok.json").write_text(json.dumps({"To: 5 account contacts": " "}))
    r, j = _run(tmp_path)
    assert r.returncode == 1 and j["ok_without_reason"] == ["To: 5 account contacts"], r.stdout


def test_excerpt_is_in_order_within_one_sentence_not_a_paraphrase():
    corp = fcq.norm(DOCS)
    sents = [x for x in corp.replace("\n", ".").split(".") if x.strip()]
    assert fcq.excerpt(fcq.norm("Owns review-ready outreach"), sents)
    assert not fcq.excerpt(fcq.norm("review-ready outreach owns"), sents)          # order matters
    assert not fcq.excerpt(fcq.norm("Deny review-ready outreach"), sents)          # words from two sentences
    assert fcq.norm("Pipeline → drafts") == fcq.norm("pipeline drafts")


@pytest.mark.skipif(not CHROME, reason="Chrome not installed")
def test_text_typed_a_letter_per_element_is_judged_as_its_line(tmp_path):
    # the Airbnb film typed its query a <span> per letter: every node had one letter and nothing was judged (2026-11-25)
    page = """<!doctype html><html><body style="margin:0;background:#fff"><div id="q" style="font:40px sans-serif"></div>
<script>window.seek = (t) => { const s = t < 0.4 ? 'Allow o' : 'Allow twice, said nobody';
  document.getElementById('q').innerHTML = [...s].map(c => '<span>' + (c === ' ' ? '&nbsp;' : c) + '</span>').join(''); };
</script></body></html>"""
    d = _film(tmp_path)
    (d / "film.html").write_text(page)
    r, j = _run(d)
    assert r.returncode == 1, r.stdout + r.stderr
    assert [u["text"] for u in j["unsourced"]] == ["Allow twice, said nobody"], j   # its partial "Allow o" is not judged
