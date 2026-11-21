"""assets/html/moments.js: every moment is a pure function of t and keeps the promise its doc makes — the unchosen
never move, a thing BECOMES on one frame (no cross-fade), a value change shows the old before the new, the slot's
leaver is gone before its arrival is readable, a scan names a region only after the line passed it, subtraction runs
from the edges inward, a performed number lands exactly on its value, and an unknown act or word fails loudly."""
import json
import os
import shutil
import subprocess

import pytest

JS = os.path.join(os.path.dirname(__file__), "..", "assets", "html", "moments.js")

PROBE = r"""
const M = require(process.argv[2]), F = M.F, r = {};
const same = (f) => JSON.stringify(f()) === JSON.stringify(f());
// purity
r.pure = same(() => M.choose(2.05, {at: 2, n: 5, chosen: 1})) && same(() => M.scan(3, {t0: 1, t1: 4, y0: 0, y1: 900,
  regions: [{y: 100, h: 50}]})) && same(() => M.type(1.3, {at: 1, text: '#research', seed: 3}));
// choose: one press frame; the others dim to the floor and carry no motion at all
const c = (t) => M.choose(t, {at: 2, n: 3, chosen: 0});
r.press_one_frame = [1.99, 2.0, 2.0 + F, 2.0 + 2 * F].map(t => c(t)[0].pressed).join() === 'false,true,false,false';
r.others_floor = Math.abs(c(3)[1].opacity - 0.18) < 1e-9 && c(3)[1].scale === 1;
r.chosen_back_to_1 = Math.abs(c(3)[0].scale - 1) < 1e-9 && c(3)[0].solid === 1;
r.press_small = Math.max(...Array.from({length: 20}, (_, i) => c(2 + i * F)[0].scale)) <= 1.0400001;
// become: the result exists from the cut frame on, the source before it; it ends exactly in its slot
const b = (t) => M.become(t, {at: 1, hold: 0.6, from: {x: 0, y: 0, w: 400}, to: {x: 100, y: 50, w: 200}});
r.become_cut = b(1 - 1e-6).phase === 'before' && b(1).phase === 'after';
r.become_holds = b(1.5).x === 0 && b(1.5).scale === 1;
r.become_lands = b(3).x === 100 && b(3).y === 50 && Math.abs(b(3).scale - 0.5) < 1e-9;
// change: the struck old value is fully struck before the new one is fully in
const ch = M.change(2 + 6 * F, {at: 2});
r.change_order = ch.old.strike === 1 && M.change(2, {at: 2}).next.opacity === 0;
r.change_new_only_shrinks = (() => { let last = 9; for (let f = 0; f < 20; f++) { const s = M.change(2 + f * F, {at: 2}).next.scale;
  if (s > last + 1e-12) return false; last = s; } return Math.abs(last - 1) < 1e-9; })();
// slot: when a word is landed it is the only word visible; the leaver is gone before the arrival is half in
const times = [1, 2, 3];
const vis = (t) => M.slot(t, {times}).map(s => s.opacity > 0.02);
r.slot_landed_alone = [1.3, 2.3, 3.3].every((t, i) => vis(t).filter(Boolean).length === 1 && vis(t)[i]);
r.slot_lands_still = M.slot(2.0, {times}).every((s, i) => i !== 1 || (s.y === 0 && s.blur === 0));
// reel: only the landed word carries the accent
const rl = M.reel(5, {times: [1, 2, 3], n: 4, row: 44});
r.reel_tint = rl.words[3].tint === 1 && rl.words[2].tint === 0 && Math.abs(rl.offset + 3 * 44) < 1e-6;
// lead ends at its own size and place
const ld = M.lead(5, {at: 1, dx: 300});
r.lead_lands = Math.abs(ld.scale - 1) < 1e-9 && Math.abs(ld.x) < 1e-9;
// scan: a region fires only after the line passed its lower edge; labels start after the brackets
const sc = (t) => M.scan(t, {t0: 0, t1: 2, y0: 0, y1: 1000, regions: [{y: 300, h: 200}, {y: 300, h: 200}]});
r.scan_after_pass = !sc(0.99).regions[0].fired && sc(1.0).regions[0].fired && sc(1.0).y >= 500;
r.scan_spaced = sc(3).regions[1].at - sc(3).regions[0].at >= 4 * F - 1e-9;
r.scan_label_lags = sc(1.0 + 4 * F).regions[0].labelChars === 0;
r.scan_constant = Math.abs((sc(0.5).y - sc(0.25).y) - (sc(1.5).y - sc(1.25).y)) < 1e-9;
// strip: the outer layer leaves first; every layer is gone at the end
r.strip_order = M.strip(1.1, {at: 1, layer: 0}).opacity < M.strip(1.1, {at: 1, layer: 3}).opacity &&
  M.strip(5, {at: 1, layer: 5}).opacity === 0;
// carry: constant speed; the head ends on the last corner
const cy = M.carry(9, {at: 0, path: [[0, 0], [100, 0], [100, 100]]});
r.carry_ends = cy.done && cy.head[0] === 100 && cy.head[1] === 100;
// type: human jitter, never two equal gaps in a row for long words; caret solid while typing
const ty = M.type(1 + 6 * F, {at: 1, text: 'abcdefghij', seed: 5});
r.type_partial = ty.shown.length > 0 && ty.shown.length < 10 && ty.caret === 'solid';
r.type_done = M.type(9, {at: 1, text: 'abc'}).done;
// retype ends on the real claim
r.retype_ends = M.retype(9, {at: 0, plain: 'a slideshow', real: 'a film crew'}).shown === 'a film crew';
// land: a dip of at most 1 % and back to exactly 1
r.land = Math.min(...Array.from({length: 12}, (_, i) => M.land(1 + i * F, {at: 1}))) >= 0.99 - 1e-9 && M.land(2, {at: 1}) === 1;
// perform: counts land exactly; strike draws then dims; unknown act throws
r.count_lands = M.perform(3, {at: 1, end: 1.5, act: 'count', value: 42}).text === '42' &&
  M.perform(1.2, {at: 1, end: 1.5, act: 'count', value: 42}).text !== '42';
r.count_never_back = (() => { let l = -1; for (let f = 0; f < 30; f++) { const v = +M.perform(1 + f * F, {at: 1, end: 1.6, act: 'count', value: 97}).text;
  if (v < l) return false; l = v; } return true; })();
try { M.perform(1, {at: 1, act: 'wobble'}); r.unknown_act_throws = false; } catch (e) { r.unknown_act_throws = true; }
// wordTime: finds the n-th occurrence, its end is the next word's start; absent words throw
const tl = {lines: [{end: 3, words: [{w: 'It', t: 0.5}, {w: 'read', t: 0.7}, {w: '42', t: 1.0}, {w: 'sources.', t: 1.4}]},
                    {end: 6, words: [{w: 'Sources', t: 4.0}]}]};
const wt = M.wordTime(tl, '42'); r.word_time = wt.at === 1.0 && wt.end === 1.4;
r.word_nth = M.wordTime(tl, 'sources', 1).at === 4.0 && M.wordTime(tl, 'sources').end === 3;
try { M.wordTime(tl, 'never'); r.word_absent_throws = false; } catch (e) { r.word_absent_throws = true; }
// spring settles at 1
r.spring_settles = Math.abs(M.spring(3, {damping: 13, stiffness: 220}) - 1) < 1e-3 && M.spring(0) === 0;
console.log(JSON.stringify(r));
"""


@pytest.fixture(scope="module")
def probe(tmp_path_factory):
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    p = tmp_path_factory.mktemp("moments") / "probe.js"
    p.write_text(PROBE)
    out = subprocess.run([node, str(p), os.path.abspath(JS)], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


@pytest.mark.parametrize("key", [
    "pure", "press_one_frame", "others_floor", "chosen_back_to_1", "press_small", "become_cut", "become_holds",
    "become_lands", "change_order", "change_new_only_shrinks", "slot_landed_alone", "slot_lands_still", "reel_tint",
    "lead_lands", "scan_after_pass", "scan_spaced", "scan_label_lags", "scan_constant", "strip_order", "carry_ends",
    "type_partial", "type_done", "retype_ends", "land", "count_lands", "count_never_back", "unknown_act_throws",
    "word_time", "word_nth", "word_absent_throws", "spring_settles"])
def test_moment(probe, key):
    assert probe[key] is True, key


def test_reel_page_uses_only_the_library_api():
    """the example reel calls only functions the library exports (a renamed function breaks the regression reel)"""
    import re
    page = open(os.path.join(os.path.dirname(JS), "examples", "moments.html"), encoding="utf-8").read()
    src = open(JS, encoding="utf-8").read()
    api = re.search(r"var api = \{(.*?)\};", src, re.S).group(1)
    exported = set(re.findall(r"(\w+):", api))
    used = set(re.findall(r"\bM\.(\w+)", page))
    assert used <= exported, used - exported
