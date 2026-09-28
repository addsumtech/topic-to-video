"""A built thing takes every word from the film's props — asked of the rendered DOM, not inferred from source.

The static scan (scripts/jsx_words.cjs) sees words written into the code; it cannot see a word that reaches the
screen through a constant list, a single-word default, or a wrapped library register's own copy. The frame can.

The matching rule (runtime/textSafe.tsx auditUnfedText) compares TOKENS, not pooled letters: a token is a
maximal run of characters of one class — CJK, digit, or letter, so a value joined to its unit ("9bar") splits
at the boundary — and a WORD or CJK token is fed when it is found among the words of every fed string pooled
together, wherever it appears, not a chunk search inside one fed string. When the run ends in an ellipsis, its
last token may instead be a prefix of a fed token of the same class. A figure-shaped numeral must match a fed
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
    <div>{WORD[0]}</div>
    {/* @fixed-text: the SI symbol of the quantity the film names */}
    <div>bar</div>
  </div>
);
"""

# Baked words chosen to spell DNA tokens ('motion: smooth', '…system-ui…'): a fixture whose baked words are
# NOT among them would pass whether or not DNA text is excluded from the fed pool, so it would not be load
# bearing.
DNA_LEAK_SHOT = """import React from 'react';
import {AbsoluteFill} from 'remotion';
export const DURATION = 60;
export const GROUND = 'bg';
export const PROVENANCE = 'industrial';
export const %(name)s: React.FC<{}> = () => (
  <AbsoluteFill style={{background: '#101010', color: '#dddddd', fontSize: 40}}>
    <div>Smooth</div>
    <div>System</div>
  </AbsoluteFill>
);
"""

# By-path id exclusion: a caption prop and an object's id that happen to share the same word.
CAPTIONED_SHOT = """import React from 'react';
import {AbsoluteFill} from 'remotion';
import {ObjectSlot, type ObjectRef} from '@runtime/objectSlot';
export const DURATION = 60;
export const GROUND = 'bg';
export const PROVENANCE = 'industrial';
export const %(name)s: React.FC<{caption?: string; object?: ObjectRef}> = ({caption = '', object}) => (
  <AbsoluteFill style={{background: '#101010', color: '#dddddd', fontSize: 40}}>
    <div>{caption}</div>
    {object ? <ObjectSlot object={object} box={{x: 900, y: 200, w: 400, h: 400}} /> : null}
  </AbsoluteFill>
);
"""
GRINDER_OBJECT = """import React from 'react';
import type {ObjectProps, ObjectMeta} from '@runtime/objectSlot';
export const META: ObjectMeta = {aspect: 1, provenance: 'industrial'};
export const %(name)s: React.FC<ObjectProps> = ({w, h}) => <div style={{width: w, height: h}} />;
"""

# Thirteen distinct baked words, none fed — one past MAX_REPORTED (12).
MANY_WORDS_SHOT = """import React from 'react';
import {AbsoluteFill} from 'remotion';
export const DURATION = 60;
export const GROUND = 'bg';
export const PROVENANCE = 'industrial';
const WORDS = ['Alpha', 'Bravo', 'Charlie', 'Delta', 'Echo', 'Foxtrot', 'Golf', 'Hotel', 'India', 'Juliet',
              'Kilo', 'Lima', 'Mike'];
export const %(name)s: React.FC<{}> = () => (
  <AbsoluteFill style={{background: '#101010', color: '#dddddd', fontSize: 26}}>
    {WORDS.map((w, i) => <div key={w} style={{position: 'absolute', left: 40, top: 20 + i * 40}}>{w}</div>)}
  </AbsoluteFill>
);
"""

# One unfed word 50 characters long — past the report's own 40-character cap.
LONG_WORD_SHOT = """import React from 'react';
import {AbsoluteFill} from 'remotion';
export const DURATION = 60;
export const GROUND = 'bg';
export const PROVENANCE = 'industrial';
export const %(name)s: React.FC<{}> = () => (
  <AbsoluteFill style={{background: '#101010', color: '#dddddd', fontSize: 16}}>
    <div>{'a'.repeat(50)}</div>
  </AbsoluteFill>
);
"""

# The matching-rule matrix — every listed case batched into one frame. Fed against
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
    <div style={{position: 'absolute', left: 340, top: 140}}>均</div>
  </AbsoluteFill>
);
"""
ROAST_FED = ["研磨更细", "压粉均匀"]

# Ground-claim fixtures.
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
    # and a baked word under opacity 0 ("Draft", still read — zero opacity does not exempt a word from the
    # audit).
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
def test_a_single_character_fed_cjk_token_covers_a_piece_at_any_position(tmp_path):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    env = _env(ws.workshop_dir(out))
    fed = ["Grind", "Tamp", "研磨", "与", "压粉"]
    got = _unfed("WsLabels", {"label": "研磨与压粉", "unfedText": fed, "unfedScope": "all"}, env, tmp_path / "e.png")
    assert got == [], got
    fed2 = ["Grind", "Tamp", "新", "咖啡豆"]
    got2 = _unfed("WsLabels", {"label": "新咖啡豆", "unfedText": fed2, "unfedScope": "all"}, env, tmp_path / "f.png")
    assert got2 == [], got2


@needs_toolchain
def test_a_value_and_its_unit_split_at_the_letter_digit_boundary(tmp_path):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    env = _env(ws.workshop_dir(out))
    got = _unfed("WsLabels", {"label": "5ms", "unfedText": ["Grind", "Tamp", "5", "ms"], "unfedScope": "all"},
                 env, tmp_path / "g.png")
    assert got == [], got
    # "ms" not fed: "5" still passes untested (a plain integer, no figure mark of its own) and only the
    # unfed unit is named.
    got2 = _unfed("WsLabels", {"label": "5ms", "unfedText": ["Grind", "Tamp"], "unfedScope": "all"},
                  env, tmp_path / "h.png")
    assert got2 == ["ms"], got2


@needs_toolchain
def test_the_letter_x_is_a_figure_mark_only_directly_against_a_numeral(tmp_path):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    env = _env(ws.workshop_dir(out))
    got = _unfed("WsLabels", {"label": "Box 3", "unfedText": ["Grind", "Tamp", "Box"], "unfedScope": "all"},
                 env, tmp_path / "i.png")
    assert got == [], got


@needs_toolchain
def test_a_numeral_no_parser_reads_compares_as_a_string_not_nan(tmp_path):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    env = _env(ws.workshop_dir(out))
    got = _unfed("WsLabels", {"label": "٨٧%", "unfedText": ["Grind", "Tamp", "٣"], "unfedScope": "all"},
                 env, tmp_path / "j.png")
    assert got == ["٨٧"], got


@needs_toolchain
def test_under_an_ellipsis_the_cjk_dp_s_final_piece_may_be_a_prefix(tmp_path):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    env = _env(ws.workshop_dir(out))
    fed = ["Grind", "Tamp", "研磨更细", "压粉均匀"]
    got = _unfed("WsLabels", {"label": "研磨更细压…", "unfedText": fed, "unfedScope": "all"}, env, tmp_path / "k.png")
    assert got == [], got


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
    atom keywords). Baking a word those strings do not themselves spell is not load bearing — it passes
    whether or not the object is excluded from the fed pool. "Smooth" and "System" are words this object's own
    tokens DO spell ('motion: smooth', '…system-ui…'), so only excluding `dna` — not merely the object ref's
    id — keeps them correctly unfed."""
    out = _workshop(tmp_path, shots={"WsDnaLeak": DNA_LEAK_SHOT})
    dna_object = {
        "fontDisplay": ('"Space Grotesk", "Noto Sans SC", "PingFang SC", "Hiragino Sans", "Microsoft YaHei", '
                        '"Noto Sans CJK SC", system-ui, sans-serif'),
        "bg": "#060709", "bgGrad": "radial-gradient(120% 120% at 50% 0%, #14161d, #060709 72%)",
        "accent": "#5b8cff", "accent2": "#a06bff", "motion": "smooth", "radius": 22,
    }
    _board(out, {}, dna=dna_object, shot="WsDnaLeak")
    sp.main([out])
    printed = capsys.readouterr().out
    line = next((ln for ln in printed.splitlines() if "no prop supplied" in ln), "")
    assert "'Smooth'" in line and "'System'" in line, printed[-2000:]


@needs_toolchain
def test_an_object_ref_s_id_is_excluded_by_path_not_by_value(tmp_path, capsys):
    """A beat's own label may legitimately equal an object's id (both named after the same real-world thing) —
    only the id AT ITS OWN PATH is wiring, not the string wherever it appears. A label "Grinder" on a beat that
    also holds the object `Grinder` must stay fed."""
    out = _workshop(tmp_path, shots={"WsCaptioned": CAPTIONED_SHOT}, objects={"Grinder": GRINDER_OBJECT})
    _board(out, {"caption": "Grinder", "object": {"id": "Grinder"}}, shot="WsCaptioned")
    sp.main([out])
    printed = capsys.readouterr().out
    assert "no prop supplied" not in printed, printed[-2000:]


@needs_toolchain
def test_the_unfed_list_is_capped_with_the_true_count(tmp_path, capsys):
    out = _workshop(tmp_path, shots={"WsManyWords": MANY_WORDS_SHOT})
    _board(out, {}, shot="WsManyWords")
    sp.main([out])
    printed = capsys.readouterr().out
    line = next((ln for ln in printed.splitlines() if "no prop supplied" in ln), "")
    assert "13 word(s)" in line, line
    assert line.count(" / ") == 11, line             # MAX_REPORTED (12) items shown = 11 separators
    assert "(1 more not shown)" in line, line


@needs_toolchain
def test_a_long_unfed_item_is_capped_at_40_characters(tmp_path, capsys):
    out = _workshop(tmp_path, shots={"WsLongWord": LONG_WORD_SHOT})
    _board(out, {}, shot="WsLongWord")
    sp.main([out])
    printed = capsys.readouterr().out
    line = next((ln for ln in printed.splitlines() if "no prop supplied" in ln), "")
    assert ("'" + "a" * 40 + "…'") in line, line
    assert "a" * 41 not in line, line


@needs_toolchain
def test_the_gave_no_answer_reason_carries_the_render_s_own_message(tmp_path, monkeypatch, capsys):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    _board(out, {"label": "研磨"})
    real_run = sp.subprocess.run

    def fake(cmd, **kw):
        if any(isinstance(a, str) and ".unfed." in a for a in cmd):
            return sp.subprocess.CompletedProcess(cmd, 1, "", "boom: the unfed render crashed")
        return real_run(cmd, **kw)
    monkeypatch.setattr(sp.subprocess, "run", fake)
    sp.main([out])
    printed = capsys.readouterr().out
    assert "the words-from-props check gave no answer" in printed and "boom" in printed, printed[-2000:]


@needs_toolchain
def test_the_ground_gap_boundary_itself_is_an_error(tmp_path, monkeypatch, capsys):
    """seam_plan's own seam guard treats a gap >= HARSH_GAP as a flash (`>=`, not `>`) — `_ground_claim`'s
    comparison must agree with it exactly at the boundary, not one float epsilon short of it. Mocking
    `seam_plan.ground_gap` itself (rather than reconstructing a luminance pair that rounds to the boundary
    through two `**` calls) is what makes the boundary exact, not approximately so."""
    import seam_plan
    out = _workshop(tmp_path, shots={"WsFlatGround": FLAT_GROUND})
    _ground_board(out, "WsFlatGround", {"fill": "#3a3a3a"}, {"design_dna": "product"})
    monkeypatch.setattr(seam_plan, "ground_gap", lambda a, b: seam_plan.HARSH_GAP)
    sp.main([out])
    printed = capsys.readouterr().out
    assert "declares GROUND" in printed, printed[-2000:]


@needs_toolchain
def test_a_broken_declared_word_scan_leaves_the_beat_unmeasured_not_falsely_unfed(tmp_path, monkeypatch, capsys):
    """`baked_words`'s `declared` comes back `[]` both when nothing is declared and when the scan itself could
    not run (node/tsc missing) — the two must not be treated alike, or a real `@fixed-text` declaration reads
    as a false unfed finding the moment the scan breaks. Only a `problems` entry ending in
    `workshop.NOTHING_CHECKED` means the latter — a scan HIT (a baked word the scan actually found) does not,
    and must not disable the frame check either (see the next test)."""
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    _board(out, {"label": "研磨", "object": {"id": "WsInside"}})
    monkeypatch.setattr(ws, "baked_words",
                        lambda *a, **k: {"problems": ["node is missing — %s" % ws.NOTHING_CHECKED], "declared": []})
    sp.main([out])
    printed = capsys.readouterr().out
    assert "the words-from-props check did not run" in printed and "node is missing" in printed, printed[-2000:]
    assert "no prop supplied" not in printed, printed[-2000:]


BAKED_WORD_SHOT = """import React from 'react';
import {AbsoluteFill} from 'remotion';
export const DURATION = 60;
export const GROUND = 'bg';
export const PROVENANCE = 'industrial';
export const %(name)s: React.FC<{label?: string}> = ({label = ''}) => (
  <AbsoluteFill style={{background: '#101010', color: '#dddddd', fontSize: 40}}>
    <div>{label}</div>
    <div>Step</div>
  </AbsoluteFill>
);
"""


@needs_toolchain
def test_a_baked_word_the_static_scan_finds_does_not_disable_the_frame_check(tmp_path, capsys):
    """`baked_words`'s `problems` also carries the scan's own HITS (a baked word it found written straight into
    the JSX) — a real finding, not a "could not run" reason, and the two must not be conflated: a workshop
    whose code writes "Step" gets both findings, the static one AND the frame's own, not the static one instead
    of the frame's."""
    out = _workshop(tmp_path, shots={"WsBakedWord": BAKED_WORD_SHOT})
    bw = ws.baked_words(out, ws.source_files(out))
    assert bw["problems"] and not any(p.endswith(ws.NOTHING_CHECKED) for p in bw["problems"]), bw["problems"]
    _board(out, {"label": "研磨"}, shot="WsBakedWord")
    sp.main([out])
    printed = capsys.readouterr().out
    line = next((ln for ln in printed.splitlines() if "no prop supplied" in ln), "")
    assert "'Step'" in line, printed[-2000:]


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


RUN_MODEL_FED = ["FORM", "FOLLOWS", "Grind", "Tamp", "Preview", "Grind finer", "A", "B", "C", "Steps",
                 "Output", "Café", "コーヒー", "数据中心", "中心化", "研磨更细", "研磨", "Tilt"]

# The run-building cases (what one run of text is), batched into one frame.
RUN_MODEL = """import React from 'react';
import {AbsoluteFill} from 'remotion';
export const DURATION = 60;
export const GROUND = 'bg';
export const PROVENANCE = 'industrial';
const glyphRow = (s) => Array.from(s).map((c, i) => <span key={i}>{c}</span>);
export const %(name)s: React.FC<{}> = () => (
  <AbsoluteFill style={{background: '#101010', color: '#dddddd', fontSize: 32}}>
    {/* <br> breaks the run: two words either side must not fuse into one */}
    <div style={{position: 'absolute', left: 40, top: 0}}>FORM<br />FOLLOWS</div>
    {/* an inline child (not one grapheme, not empty) is absorbed with no separator of its own — the
        separator here is the SPAN's own text, not a rule inserted between elements */}
    <div style={{position: 'absolute', left: 40, top: 70}}>Grind<span> · </span>Tamp</div>
    {/* Pre<b>view</b> absorbs into one word */}
    <div style={{position: 'absolute', left: 40, top: 140}}>Pre<b>view</b></div>
    {/* per-glyph "Grind finer", the space written as its own SPAN (inline flow keeps every glyph close) */}
    <div style={{position: 'absolute', left: 40, top: 210}}>{glyphRow('Grind finer')}</div>
    {/* per-glyph "Grind finer", the space an empty flex-gap DIV (a real box, no rendered text) */}
    <div style={{position: 'absolute', left: 40, top: 280, display: 'flex'}}>
      {Array.from('Grind finer').map((c, i) => (c === ' '
        ? <div key={i} style={{width: 14, height: 0}} />
        : <div key={i}>{c}</div>))}
    </div>
    {/* per-glyph "Grind finer" with a trailing caret (an empty inline-block, a real box, no text) */}
    <div style={{position: 'absolute', left: 40, top: 350}}>
      {glyphRow('Grind finer')}<span style={{display: 'inline-block', width: 4, height: 32}} />
    </div>
    {/* per-glyph baked "NEW" next to the same kind of caret — unfed, reported as one word */}
    <div style={{position: 'absolute', left: 40, top: 420}}>
      {glyphRow('NEW')}<span style={{display: 'inline-block', width: 4, height: 32}} />
    </div>
    {/* one-letter labels WITH GAPS between them — sibling option letters, not one kinetic word */}
    <div style={{position: 'absolute', left: 40, top: 490}}>
      <span style={{marginRight: 160}}>A</span><span style={{marginRight: 160}}>B</span><span>C</span>
    </div>
    {/* a glyph nested in wrapper spans is still a glyph */}
    <div style={{position: 'absolute', left: 40, top: 560}}>
      {Array.from('Grind').map((c, i) => <span key={i}><span>{c}</span></span>)}
    </div>
    {/* an echo duplicate of a glyph run must not double it — the echo itself absolutely positioned, as a
        real echo overlay is (PointerTour softens a SECOND copy at the SAME place), so it never occupies
        normal-flow width that would push the real glyphs apart from one another */}
    <div style={{position: 'absolute', left: 40, top: 630}}>
      {Array.from('Grind').map((c, i) => (
        <React.Fragment key={i}>
          <span>{c}</span>
          <span aria-hidden data-echo="" style={{position: 'absolute', left: 0, top: 0}}>{c}</span>
        </React.Fragment>
      ))}
    </div>
    {/* display:contents has no box of its own; its child still joins the run */}
    <div style={{position: 'absolute', left: 40, top: 700}}>
      <div style={{display: 'contents'}}>Ghost</div>
    </div>
    {/* text overflowing a zero-size box is still read (a Range over the text node, not the container) */}
    <div style={{position: 'absolute', left: 40, top: 770, width: 0, height: 0, overflow: 'visible'}}>Overflow</div>
    <div style={{position: 'absolute', left: 40, top: 840}}>８７％</div>
    <div style={{position: 'absolute', left: 340, top: 840}}>{'Cafe\\u0301'}</div>
    <div style={{position: 'absolute', left: 40, top: 910}}>コーヒー</div>
    <div style={{position: 'absolute', left: 340, top: 910}}>Step 1</div>
    <div style={{position: 'absolute', left: 40, top: 980}}>Outp…</div>
    <div style={{position: 'absolute', left: 340, top: 980}}>O</div>
    <div style={{position: 'absolute', left: 40, top: 1050}}>数据中心化</div>
    {/* a flex column stacks one glyph per row; rows touch in the SAME COLUMN, so the glue gap is the
        vertical one, not the horizontal-only measurement that read every row alone */}
    <div style={{position: 'absolute', left: 40, top: 1120, display: 'flex', flexDirection: 'column'}}>
      {glyphRow('研磨更细')}
    </div>
    {/* writing-mode: vertical-rl stacks glyphs the same way, without flex */}
    <div style={{position: 'absolute', left: 340, top: 1120, writingMode: 'vertical-rl'}}>
      {glyphRow('研磨')}
    </div>
    {/* row-reverse: DOM order A,B,C but each next box sits to the LEFT of the one before it — a signed,
        left-to-right-only gap reads this as touching; the fix measures an absolute distance instead */}
    <div style={{position: 'absolute', left: 40, top: 1300, display: 'flex', flexDirection: 'row-reverse',
                  gap: 60}}>
      {glyphRow('ABC')}
    </div>
    {/* a per-glyph word set on an absolutely positioned "scrap" per letter, each scrap inheriting the
        frame's own font size while the letter itself is set much larger on an inner span — the glue
        distance is measured against the INNER size, not the scrap's */}
    <div style={{position: 'absolute', left: 40, top: 1450}}>
      {Array.from('Tilt').map((c, i) => (
        <div key={i} style={{position: 'absolute', left: i * 0.7 * 110, top: 0}}>
          <span style={{fontSize: 110}}>{c}</span>
        </div>
      ))}
    </div>
    {/* two multi-character chips set apart by a real margin — absorption is proximity gated the same as a
        glyph, so a wide-enough gap must not fuse them */}
    <div style={{position: 'absolute', left: 40, top: 1650, display: 'flex'}}>
      <span style={{marginRight: 40}}>Grind</span><span>Tamp</span>
    </div>
    {/* the library's own per-code-point idiom on an NFD string: the combining acute lands in its own span,
        commonly a zero-area one, and must still be read onto the "e" before it */}
    <div style={{position: 'absolute', left: 340, top: 1650}}>{glyphRow('Café')}</div>
  </AbsoluteFill>
);
"""


@needs_toolchain
def test_the_run_model_covers_every_listed_case(tmp_path):
    out = _workshop(tmp_path, shots={"WsRunModel": RUN_MODEL})
    env = _env(ws.workshop_dir(out))
    got = _unfed("WsRunModel", {"unfedText": RUN_MODEL_FED, "unfedScope": "all"}, env, tmp_path / "runmodel.png")
    # unfed: the caret idiom baked with "NEW" (one word, not glued to the caret or split into three letters);
    # a display:contents wrapper's own baked word ("Ghost"); text overflowing its zero-size box ("Overflow");
    # a fabricated figure ("８７", the fullwidth "％" recognised as "%" once folded); "Step" (not licensed by
    # a fed "Steps" — short of an ellipsis, a short token is a different word, not a maybe-truncation); a bare
    # "O" (not licensed by a fed "Output" the same way). Every other case is fed (see the fixture's own
    # comments) — <br>, the absorbed inline separator and <b>, all three per-glyph spellings of "Grind finer",
    # sibling option letters kept apart by their gap, nested glyphs, the echo not doubling, an NFD "Café"
    # matching an NFC fed "Café", "コーヒー" surviving its own prolonged-sound mark, "Outp…" truncating into
    # "Output", "数据中心化" splitting 数据｜中心化 across two fed CJK tokens dynamic programming finds and a
    # greedy search missed, a flex column and a vertical-rl run gluing each own-column glyph along the
    # vertical gap, a row-reverse run gluing by absolute distance despite each next box sitting to the left
    # of the one before it, a per-glyph word on absolutely positioned scraps gluing by its own inner font
    # size, two margin-set-apart chips staying two words, and a per-code-point NFD run whose lone combining
    # mark still lands on the letter before it.
    assert sorted(got) == sorted(["NEW", "Ghost", "Overflow", "８７", "Step", "O"]), got


@needs_toolchain
def test_the_workshop_renders_a_shot_s_settled_frame_to_look_at(tmp_path):
    out = _workshop(tmp_path, shots={"WsLabels": LABELS}, objects={"WsInside": INSIDE})
    _board(out, {"label": "研磨"})
    png = ws.still(out, "WsLabels")
    assert png == os.path.join(ws.workshop_dir(out), "_stills", "WsLabels.png") and os.path.getsize(png) > 1000
