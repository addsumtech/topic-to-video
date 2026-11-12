"""Every beat's SVG ids are its own (runtime/idScope.tsx).

WorkBuddy, 2026-11-11: beats 9 and 10 both drew the lit workspace, whose light pool is `url(#ws-pool)` fading in over
the beat. Through the seam beat 10 resolved its pool to beat 9's (fully lit, first in the document); when beat 9
unmounted it fell back to its own, not yet lit — the light switched off in one frame, and no gate saw it."""
import os

import pytest

import _tsprobe

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILM = open(os.path.join(ROOT, "remotion", "src", "Film.tsx"), encoding="utf-8").read()

FAKE_DOM = """
  class El {
    attrs: Record<string, string>; kids: El[];
    constructor(attrs: Record<string, string>, kids: El[] = []) { this.attrs = {...attrs}; this.kids = kids; }
    getAttribute(a: string) { return a in this.attrs ? this.attrs[a] : null; }
    setAttribute(a: string, v: string) { this.attrs[a] = v; }
    all(): El[] { return this.kids.flatMap((k) => [k, ...k.all()]); }
    querySelectorAll(sel: string) { const xs = this.all(); return sel === '[id]' ? xs.filter((x) => 'id' in x.attrs) : xs; }
  }
  const beat = () => new El({}, [
    new El({}, [new El({id: 'ws-pool'}), new El({id: 'arrow'})]),
    new El({fill: 'url(#ws-pool)'}),
    new El({style: "filter: url('#ws-pool'); mask: url(#elsewhere)"}),
    new El({'marker-end': 'url(#arrow)'}),
    new El({href: '#arrow'}),
    new El({href: '#lining-figures'}),
  ]);
"""


def _ts(body):
    if not _tsprobe.available():
        pytest.skip("node/esbuild not available")
    return _tsprobe.run_ts("import {scopeIds} from %s;" % _tsprobe.mod("idScope.tsx"), FAKE_DOM + body)


def test_two_beats_with_the_same_literal_ids_resolve_each_to_its_own():
    out = _ts("""
      const a = beat(), b = beat();
      scopeIds(a as any, 'b9'); scopeIds(b as any, 'b10');
      const ids = (r: El) => r.all().map((x) => x.getAttribute('id')).filter(Boolean);
      out.a = ids(a); out.b = ids(b);
      out.bRefs = b.all().map((x) => [x.getAttribute('fill'), x.getAttribute('style'), x.getAttribute('marker-end'),
                                       x.getAttribute('href')]).flat().filter(Boolean);
    """)
    assert out["a"] == ["ws-pool__b9", "arrow__b9"] and out["b"] == ["ws-pool__b10", "arrow__b10"]
    refs = " ".join(out["bRefs"])
    assert "url(#ws-pool__b10)" in refs and "url('#ws-pool__b10')" in refs and "url(#arrow__b10)" in refs
    assert "#arrow__b10" in out["bRefs"]
    assert "b9" not in refs


def test_a_reference_to_an_id_the_beat_does_not_define_is_left_alone():
    out = _ts("""
      const a = beat(); scopeIds(a as any, 'b3');
      out.refs = a.all().map((x) => [x.getAttribute('style'), x.getAttribute('href')]).flat().filter(Boolean);
    """)
    assert "#lining-figures" in out["refs"]                    # a document-level def (fonts.ts)
    assert any("url(#elsewhere)" in r for r in out["refs"])


def test_scoping_again_on_the_next_frame_changes_nothing_and_catches_what_react_rewrote():
    # React re-writes an attribute whose prop changed (an animated fill) with the literal id: the next pass scopes it
    out = _ts("""
      const a = beat(); scopeIds(a as any, 'b4');
      const once = JSON.stringify(a.all().map((x) => x.attrs));
      scopeIds(a as any, 'b4');
      out.same = once === JSON.stringify(a.all().map((x) => x.attrs));
      a.kids[1].setAttribute('fill', 'url(#ws-pool)');
      scopeIds(a as any, 'b4');
      out.fill = a.kids[1].getAttribute('fill');
    """)
    assert out["same"] is True and out["fill"] == "url(#ws-pool__b4)"


def test_every_beat_and_every_stage_run_is_scoped_in_the_film():
    seq = FILM.split("const beatSeq")[1].split("const runSeq")[0]
    assert "<IdScope scope={`b${i}`}>" in seq and "</IdScope>" in seq
    run = FILM.split("const runSeq")[1][:3000]
    assert "<IdScope scope={`r${first}`}>" in run and "</IdScope>" in run
