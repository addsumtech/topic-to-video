"""A built thing takes every word from the film's props — asked of the rendered DOM, not inferred from source.

The static scan (scripts/jsx_words.cjs) sees words written into the code; it cannot see a word that reaches the
screen through a constant list, a single-word default, or a wrapped library register's own copy. The frame can."""
import json
import os
import re
import subprocess
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shot_proof as sp  # noqa: E402
import workshop as ws  # noqa: E402
from test_workshop_bundle import OBJECT, _env, _still  # noqa: E402

needs_toolchain = pytest.mark.skipif(not os.path.isdir(os.path.join(_REM, "node_modules")),
                                     reason="needs the remotion toolchain")

LABELS = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ObjectSlot, type ObjectRef} from '@runtime/objectSlot';
import {useDNA} from '@runtime/dna';
export const DURATION = 60;
export const GROUND = 'bg';
export const PROVENANCE = 'industrial';
const STEPS = ['Grind', 'Tamp'];
export const %(name)s: React.FC<{label?: string; a?: string; b?: string; object?: ObjectRef; paper?: boolean}> =
  ({label = '', a = '', b = '', object, paper = false}) => {
  const dna = useDNA();
  return (
    <AbsoluteFill style={{background: paper ? '#ffffff' : (dna?.bg ?? '#101010'), color: '#888888', fontSize: 60}}>
      <div style={{position: 'absolute', left: 100, top: 200}}>{label}</div>
      <div style={{position: 'absolute', left: 100, top: 300}}>{STEPS.map((s) => <span key={s}>{s} </span>)}</div>
      <div style={{position: 'absolute', left: 100, top: 400}}>{a && b ? `${a} · ${b}` : ''}</div>
      {object ? <ObjectSlot object={object} box={{x: 1100, y: 200, w: 500, h: 500}} /> : null}
    </AbsoluteFill>
  );
};
"""

INSIDE = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};
const WORD = ['INSIDE'];
export const %(name)s: React.FC<ObjectProps> = ({w, h}) => (
  <div style={{width: w, height: h, fontSize: 40, color: '#aaaaaa'}}>
    {WORD[0]}
    {/* @fixed-text: the SI symbol of the quantity the film names */}
    <span>bar</span>
  </div>
);
"""


def _workshop(tmp_path):
    out = tmp_path / "film"
    for kind, n, src in (("shots", "WsLabels", LABELS), ("objects", "WsInside", INSIDE)):
        d = out / "workshop" / kind
        d.mkdir(parents=True, exist_ok=True)
        (d / (n + ".tsx")).write_text(src % {"name": n}, encoding="utf-8")
    ws.write_index(str(out))
    return str(out)


def _unfed(comp, props, env, png):
    r = _still(comp, png, props, env, frame=40)
    blob = r.stdout + r.stderr
    assert sp.UNFED_TAG in blob, blob[-800:]
    return json.JSONDecoder().raw_decode(blob.split(sp.UNFED_TAG, 1)[1])[0]["unfed"]


def test_the_tag_is_the_runtime_s():
    src = open(os.path.join(_REM, "src", "runtime", "textSafe.tsx"), encoding="utf-8").read()
    assert "export const UNFED_TEXT_TAG = '%s';" % sp.UNFED_TAG in src


@needs_toolchain
def test_a_word_no_prop_supplied_is_found_on_the_frame(tmp_path):
    out = _workshop(tmp_path)
    env = _env(ws.workshop_dir(out))
    got = _unfed("WsLabels", {"label": "研磨", "unfedText": ["研磨"], "unfedScope": "all"}, env, tmp_path / "a.png")
    assert sorted(got) == ["Grind", "Tamp"], got


@needs_toolchain
def test_words_the_film_supplied_are_not_reported_even_when_joined(tmp_path):
    out = _workshop(tmp_path)
    env = _env(ws.workshop_dir(out))
    fed = ["研磨", "Grind", "Tamp", "萃取", "压力"]
    got = _unfed("WsLabels", {"label": "研磨", "a": "萃取", "b": "压力", "unfedText": fed, "unfedScope": "all"},
                 env, tmp_path / "b.png")
    assert got == [], got


@needs_toolchain
def test_the_slots_scope_asks_only_what_the_object_draws(tmp_path):
    out = _workshop(tmp_path)
    env = _env(ws.workshop_dir(out))
    props = {"label": "研磨", "object": {"id": "WsInside"}, "unfedText": ["研磨"], "unfedScope": "slots"}
    got = _unfed("WsLabels", props, env, tmp_path / "c.png")
    assert sorted(got) == ["INSIDE", "bar"], got
    props["unfedScope"] = "all"
    assert sorted(_unfed("WsLabels", props, env, tmp_path / "d.png")) == ["Grind", "INSIDE", "Tamp", "bar"]


def _board(out, props, dna="product"):
    board = {"meta": {"renderer": "remotion", "design_dna": dna, "language": "zh"},
             "slides": [{"index": 1, "shot": "WsLabels", "narration": "一", "shot_props": props}]}
    with open(os.path.join(out, "storyboard.json"), "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False)


@needs_toolchain
def test_shot_proof_names_the_words_no_prop_supplied_and_accepts_a_declared_one(tmp_path, capsys):
    out = _workshop(tmp_path)
    _board(out, {"label": "研磨", "object": {"id": "WsInside"}})
    sp.main([out])
    printed = capsys.readouterr().out
    line = next((l for l in printed.splitlines() if "no prop supplied" in l), "")
    assert "'Grind'" in line and "'Tamp'" in line and "'INSIDE'" in line, printed[-2000:]
    assert "'bar'" not in line, line                       # declared `@fixed-text` in the workshop code


@needs_toolchain
def test_a_ground_claim_the_frame_contradicts_is_an_error(tmp_path, capsys):
    out = _workshop(tmp_path)
    _board(out, {"label": "研磨", "paper": True})          # declares GROUND 'bg' (dark here) and paints white
    sp.main([out])
    printed = capsys.readouterr().out
    assert "declares GROUND 'bg'" in printed and "caption band renders at" in printed, printed[-2000:]
    _board(out, {"label": "研磨"})                         # paints dna.bg, as declared
    sp.main([out])
    assert "declares GROUND" not in capsys.readouterr().out


@needs_toolchain
def test_the_workshop_renders_a_shot_s_settled_frame_to_look_at(tmp_path):
    out = _workshop(tmp_path)
    _board(out, {"label": "研磨"})
    png = ws.still(out, "WsLabels")
    assert png == os.path.join(ws.workshop_dir(out), "_stills", "WsLabels.png") and os.path.getsize(png) > 1000
