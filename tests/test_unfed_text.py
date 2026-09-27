"""A built thing takes every word from the film's props — asked of the rendered DOM, not inferred from source.

The static scan (scripts/jsx_words.cjs) sees words written into the code; it cannot see a word that reaches the
screen through a constant list, a single-word default, or a wrapped library register's own copy. The frame can.

The matching rule (runtime/textSafe.tsx auditUnfedText) compares TOKENS, not pooled letters: a token is a
maximal run of letters/digits of one script class, a run is fed when its tokens split into chunks each found,
in order, inside one fed string (the run's last token may be a truncated prefix), a CJK token is covered by
pieces of a fed CJK token instead (CJK has no word boundaries), and a figure-shaped numeral must match a fed
numeral or a numeric prop value while a plain integer is presumed derived (an index, a tick) and passes."""
import json
import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_REM = os.path.join(_ROOT, "remotion")
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shot_proof as sp  # noqa: E402
import workshop as ws  # noqa: E402
from test_workshop_bundle import _env, _still  # noqa: E402

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

# The matching-rule matrix (I2/ruling R21), every listed case batched into one frame. Fed against
# BREW_FED = ["Grind finer", "Tamp evenly", "Heat the water to 93°C", "Before", "Output"].
BREW_NOTES = """import React from 'react';
import {AbsoluteFill} from 'remotion';
export const DURATION = 60;
export const GROUND = 'bg';
export const PROVENANCE = 'industrial';
export const %(name)s: React.FC<{}> = () => (
  <AbsoluteFill style={{background: '#101010', color: '#dddddd', fontSize: 40}}>
    <div style={{position: 'absolute', left: 40, top: 20}}>Step</div>
    <div style={{position: 'absolute', left: 40, top: 80}}>Step 1: Heat the water</div>
    <div style={{position: 'absolute', left: 40, top: 140}}>Grind · Tamp</div>
    <div style={{position: 'absolute', left: 40, top: 200}}>GRIND FINER</div>
    <div style={{position: 'absolute', left: 40, top: 260}}>Heat the wa…</div>
    <div style={{position: 'absolute', left: 40, top: 320}}>
      {['G', 'r', 'i', 'n', 'd'].map((c, i) => <span key={i}>{c}</span>)}
    </div>
    <div style={{position: 'absolute', left: 40, top: 380}}>
      {['N', 'E', 'W'].map((c, i) => <span key={i}>{c}</span>)}
    </div>
    <div style={{position: 'absolute', left: 40, top: 440}}>87%%</div>
    <div style={{position: 'absolute', left: 40, top: 500}}>93°C</div>
    <div style={{position: 'absolute', left: 40, top: 560}}>
      {['0', '25', '50'].map((c, i) => <span key={i}>{c}</span>)}
    </div>
    <div style={{position: 'absolute', left: 40, top: 620}}>3.2×</div>
    <div style={{position: 'absolute', left: 40, top: 680}}>Loading</div>
    <div style={{position: 'absolute', left: 40, top: 740}}>Before</div>
    <div style={{position: 'absolute', left: 40, top: 800, opacity: 0}}>Draft</div>
  </AbsoluteFill>
);
"""
BREW_FED = ["Grind finer", "Tamp evenly", "Heat the water to 93°C", "Before", "Output"]

# Fed against ROAST_FED = ["研磨更细", "压粉均匀"].
ROAST_NOTES = """import React from 'react';
import {AbsoluteFill} from 'remotion';
export const DURATION = 60;
export const GROUND = 'bg';
export const PROVENANCE = 'industrial';
export const %(name)s: React.FC<{}> = () => (
  <AbsoluteFill style={{background: '#101010', color: '#dddddd', fontSize: 40}}>
    <div style={{position: 'absolute', left: 40, top: 20}}>研磨·压粉</div>
    <div style={{position: 'absolute', left: 40, top: 80}}>
      {['研', '磨'].map((c, i) => <span key={i}>{c}</span>)}
    </div>
    <div style={{position: 'absolute', left: 40, top: 140}}>新</div>
    <div style={{position: 'absolute', left: 40, top: 200}}>均</div>
  </AbsoluteFill>
);
"""
ROAST_FED = ["研磨更细", "压粉均匀"]

# I3's ground-claim fixtures.
FLAT_GROUND = """import React from 'react';
import {AbsoluteFill} from 'remotion';
export const DURATION = 30;
export const GROUND = '#3a3a3a';
export const PROVENANCE = 'industrial';
export const %(name)s: React.FC<{fill?: string}> = ({fill = '#3a3a3a'}) => (
  <AbsoluteFill style={{background: fill}} />
);
"""

TOKEN_GROUND = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useDNA} from '@runtime/dna';
export const DURATION = 30;
export const GROUND = ['accent', 'accent2'];
export const PROVENANCE = 'industrial';
export const %(name)s: React.FC<{which?: string}> = ({which = 'accent2'}) => {
  const dna = useDNA();
  const c = which === 'accent' ? dna?.accent : which === 'accent2' ? dna?.accent2 : '#808080';
  return <AbsoluteFill style={{background: c ?? '#000000'}} />;
};
"""

GRAD_GROUND = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {useDNA} from '@runtime/dna';
export const DURATION = 30;
export const GROUND = 'bgGrad';
export const PROVENANCE = 'industrial';
export const %(name)s: React.FC<{}> = () => {
  const dna = useDNA();
  return <AbsoluteFill style={{background: dna?.bgGrad ?? dna?.bg ?? '#101010'}} />;
};
"""


def _workshop(tmp_path, shots=None, objects=None):
    """A film's workshop holding exactly the given {name: %(name)s-templated .tsx source}."""
    out = tmp_path / "film"
    for kind, items in (("shots", shots or {}), ("objects", objects or {})):
        d = out / "workshop" / kind
        d.mkdir(parents=True, exist_ok=True)
        for n, src in items.items():
            (d / (n + ".tsx")).write_text(src % {"name": n}, encoding="utf-8")
    ws.write_index(str(out))
    return str(out)


def _unfed(comp, props, env, png):
    r = _still(comp, png, props, env, frame=40)
    blob = r.stdout + r.stderr
    assert sp.UNFED_TAG in blob, blob[-800:]
    return json.JSONDecoder().raw_decode(blob.split(sp.UNFED_TAG, 1)[1])[0]["unfed"]


def _board(out, props, dna="product", shot="WsLabels"):
    board = {"meta": {"renderer": "remotion", "design_dna": dna, "language": "zh"},
             "slides": [{"index": 1, "shot": shot, "narration": "一", "shot_props": props}]}
    with open(os.path.join(out, "storyboard.json"), "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False)


def _ground_board(out, shot, props, meta=None):
    board = {"meta": dict({"renderer": "remotion", "language": "zh"}, **(meta or {})),
             "slides": [{"index": 1, "shot": shot, "narration": "一", "shot_props": props}]}
    with open(os.path.join(out, "storyboard.json"), "w", encoding="utf-8") as fh:
        json.dump(board, fh, ensure_ascii=False)


def test_the_tag_is_the_runtime_s():
    src = open(os.path.join(_REM, "src", "runtime", "textSafe.tsx"), encoding="utf-8").read()
    assert "export const UNFED_TEXT_TAG = '%s';" % sp.UNFED_TAG in src


@needs_toolchain
def test_a_word_no_prop_supplied_is_found_on_the_frame(tmp_path):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    env = _env(ws.workshop_dir(out))
    got = _unfed("WsLabels", {"label": "研磨", "unfedText": ["研磨"], "unfedScope": "all"}, env, tmp_path / "a.png")
    assert sorted(got) == ["Grind", "Tamp"], got


@needs_toolchain
def test_words_the_film_supplied_are_not_reported_even_when_joined(tmp_path):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    env = _env(ws.workshop_dir(out))
    fed = ["研磨", "Grind", "Tamp", "萃取", "压力"]
    got = _unfed("WsLabels", {"label": "研磨", "a": "萃取", "b": "压力", "unfedText": fed, "unfedScope": "all"},
                 env, tmp_path / "b.png")
    assert got == [], got


@needs_toolchain
def test_the_slots_scope_asks_only_what_the_object_draws(tmp_path):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    env = _env(ws.workshop_dir(out))
    props = {"label": "研磨", "object": {"id": "WsInside"}, "unfedText": ["研磨"], "unfedScope": "slots"}
    got = _unfed("WsLabels", props, env, tmp_path / "c.png")
    assert sorted(got) == ["INSIDE", "bar"], got
    props["unfedScope"] = "all"
    assert sorted(_unfed("WsLabels", props, env, tmp_path / "d.png")) == ["Grind", "INSIDE", "Tamp", "bar"]


@needs_toolchain
def test_the_matching_rule_covers_every_listed_english_case(tmp_path):
    out = _workshop(tmp_path, shots={"WsBrewNotes": BREW_NOTES})
    env = _env(ws.workshop_dir(out))
    got = _unfed("WsBrewNotes", {"unfedText": BREW_FED, "unfedScope": "all"}, env, tmp_path / "brew.png")
    # unfed: a baked word ("Step", found twice, once alone and once inside "Step 1: Heat the water" — the
    # rest of that sentence is fed and only "Step" is named), a per-glyph run ("NEW"), two fabricated
    # figures ("87%", "3.2×" — reported as their numeral, not the adjacent mark), a baked word ("Loading"),
    # and a baked word under opacity 0 ("Draft", still read: rule 6 does not exempt it).
    # fed: a joined pair ("Grind · Tamp"), a re-cased whole match ("GRIND FINER"), a truncated prefix
    # ("Heat the wa…"), a per-glyph run of real copy ("Grind"), a plain unit reading ("93°C" — "93" is a
    # derived integer with no figure mark, "c" is a fed token), three plain-integer ticks (never copy), and
    # an exact match ("Before").
    assert sorted(got) == sorted(["Step", "NEW", "87", "3.2", "Loading", "Draft"]), got


@needs_toolchain
def test_the_matching_rule_covers_every_listed_cjk_case(tmp_path):
    out = _workshop(tmp_path, shots={"WsRoastNotes": ROAST_NOTES})
    env = _env(ws.workshop_dir(out))
    got = _unfed("WsRoastNotes", {"unfedText": ROAST_FED, "unfedScope": "all"}, env, tmp_path / "roast.png")
    # fed: two joined phrases sharing no fed string's own boundary ("研磨·压粉", each half a ≥2-char piece of
    # one fed CJK token) and a per-glyph run of the same ("研","磨"). unfed: a lone baked character never
    # spelled out in any fed string ("新"), and a lone baked character that IS a substring of a fed token but
    # not the WHOLE token ("均" — a single CJK character must match a fed token exactly, or nearly every
    # glyph in the language would pass).
    assert sorted(got) == sorted(["新", "均"]), got


@needs_toolchain
def test_shot_proof_names_the_words_no_prop_supplied_and_accepts_a_declared_one(tmp_path, capsys):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    _board(out, {"label": "研磨", "object": {"id": "WsInside"}})
    sp.main([out])
    printed = capsys.readouterr().out
    line = next((ln for ln in printed.splitlines() if "no prop supplied" in ln), "")
    assert "'Grind'" in line and "'Tamp'" in line and "'INSIDE'" in line, printed[-2000:]
    assert "'bar'" not in line, line                       # declared `@fixed-text` in the workshop code


@needs_toolchain
def test_a_design_dna_object_does_not_mask_baked_words(tmp_path, capsys):
    """meta.design_dna is typically an OBJECT (dna_from_deck.py writes one), not the preset NAME the other
    tests use — and an object carries some two dozen strings of its own (font stacks, a gradient, motion and
    atom keywords). None of them may leak into the fed pool and mask a baked word."""
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    dna_object = {
        "fontDisplay": ('"Space Grotesk", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", '
                        '"Noto Sans CJK SC", system-ui, sans-serif'),
        "bg": "#060709", "bgGrad": "radial-gradient(120% 120% at 50% 0%, #14161d, #060709 72%)",
        "accent": "#5b8cff", "accent2": "#a06bff", "motion": "smooth", "radius": 22,
    }
    _board(out, {"label": "研磨", "object": {"id": "WsInside"}}, dna=dna_object)
    sp.main([out])
    printed = capsys.readouterr().out
    line = next((ln for ln in printed.splitlines() if "no prop supplied" in ln), "")
    assert "'Grind'" in line and "'Tamp'" in line and "'INSIDE'" in line, printed[-2000:]
    assert "'bar'" not in line, line


@needs_toolchain
def test_a_broken_declared_word_scan_leaves_the_beat_unmeasured_not_falsely_unfed(tmp_path, monkeypatch, capsys):
    """`baked_words`'s `declared` comes back `[]` both when nothing is declared and when the scan itself could
    not run (node/tsc missing) — the two must not be treated alike, or a real `@fixed-text` declaration reads
    as a false unfed finding the moment the scan breaks."""
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    _board(out, {"label": "研磨", "object": {"id": "WsInside"}})
    monkeypatch.setattr(ws, "baked_words", lambda *a, **k: {"problems": ["node is missing"], "declared": []})
    sp.main([out])
    printed = capsys.readouterr().out
    assert "the words-from-props check did not run" in printed and "node is missing" in printed, printed[-2000:]
    assert "no prop supplied" not in printed, printed[-2000:]


@needs_toolchain
def test_a_ground_claim_the_frame_contradicts_is_an_error(tmp_path, capsys):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    _board(out, {"label": "研磨", "paper": True})          # declares GROUND 'bg' (dark here) and paints white
    sp.main([out])
    printed = capsys.readouterr().out
    assert "declares GROUND 'bg'" in printed and "caption band renders" in printed, printed[-2000:]
    _board(out, {"label": "研磨"})                         # paints dna.bg, as declared
    sp.main([out])
    assert "declares GROUND" not in capsys.readouterr().out


@needs_toolchain
def test_a_hex_ground_holds_and_fails(tmp_path, capsys):
    out = _workshop(tmp_path, shots={"WsFlatGround": FLAT_GROUND})
    _ground_board(out, "WsFlatGround", {"fill": "#3a3a3a"}, {"design_dna": "product"})
    sp.main([out])
    assert "declares GROUND" not in capsys.readouterr().out
    _ground_board(out, "WsFlatGround", {"fill": "#ffffff"}, {"design_dna": "product"})
    sp.main([out])
    printed = capsys.readouterr().out
    assert "declares GROUND '#3a3a3a'" in printed and "caption band renders" in printed, printed[-2000:]


@needs_toolchain
def test_a_list_ground_holds_against_any_one_token_not_only_the_average(tmp_path, capsys):
    """GROUND = ['accent', 'accent2'] with accent white and accent2 black: the band, painted exactly accent2,
    sits 0.73 from the pair's AVERAGE (mid-grey) — past the seam guard's own 0.34 flash threshold — and holds
    only because the check also asks each listed token on its own, the same two readings the caption ink and
    the seam guard themselves take."""
    out = _workshop(tmp_path, shots={"WsTokenGround": TOKEN_GROUND})
    dna_object = {"accent": "#ffffff", "accent2": "#000000"}
    _ground_board(out, "WsTokenGround", {"which": "accent2"}, {"design_dna": dna_object})
    sp.main([out])
    assert "declares GROUND" not in capsys.readouterr().out


@needs_toolchain
def test_a_bggrad_ground_is_unmeasured_not_silently_passed(tmp_path, capsys):
    out = _workshop(tmp_path, shots={"WsGradGround": GRAD_GROUND})
    _ground_board(out, "WsGradGround", {}, {"design_dna": "product"})
    sp.main([out])
    printed = capsys.readouterr().out
    assert "NOT MEASURED" in printed and "bgGrad" in printed, printed[-2000:]
    assert "declares GROUND" not in printed, printed[-2000:]


@needs_toolchain
def test_no_design_dna_at_all_is_unmeasured(tmp_path, capsys):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    _ground_board(out, "WsLabels", {"label": "研磨"}, {})
    sp.main([out])
    printed = capsys.readouterr().out
    assert "NOT MEASURED" in printed and "no Design DNA" in printed, printed[-2000:]


@needs_toolchain
def test_a_shot_template_alone_still_resolves_and_measures(tmp_path, capsys):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    _ground_board(out, "WsLabels", {"label": "研磨"}, {"shot_template": "product"})
    sp.main([out])
    printed = capsys.readouterr().out
    assert "could not be measured" not in printed and "declares GROUND" not in printed, printed[-2000:]


@needs_toolchain
def test_the_workshop_renders_a_shot_s_settled_frame_to_look_at(tmp_path):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    _board(out, {"label": "研磨"})
    png = ws.still(out, "WsLabels")
    assert png == os.path.join(ws.workshop_dir(out), "_stills", "WsLabels.png") and os.path.getsize(png) > 1000
