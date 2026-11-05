"""critic_brief --gates ran 18 delivery gates one after another (~20 min on the ANC film). The light gates (a decode of
out.mp4, a read of the board) run beside the heavy ones (those that render the Film again), which stay in one lane so
two renders never compete for the machine and time out; the printed order and the record are the board's order."""
import os
import sys
import time

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))
import critic_brief as cb  # noqa: E402


def test_light_gates_run_beside_the_heavy_lane_and_print_in_order(monkeypatch, capsys):
    rows = [("v", "validate.py", (), 60, True), ("ts", "text_safe_qa.py", (), 60, True),
            ("av", "check_av.py", (), 60, True), ("j", "jitter_qa.py", (), 60, True),
            ("e", "film_energy_qa.py", (), 60, True), ("f", "flash_qa.py", (), 60, True)]
    live, peak = [0], [0]
    heavy_live = [0]

    def fake(script, out_dir, args=(), timeout=240):
        live[0] += 1
        peak[0] = max(peak[0], live[0])
        if script in cb.HEAVY_GATES:
            heavy_live[0] += 1
            assert heavy_live[0] == 1, "two heavy gates rendered at once"
        time.sleep(0.4)
        if script in cb.HEAVY_GATES:
            heavy_live[0] -= 1
        live[0] -= 1
        return cb.GateOutput("[%s] ok" % script, 0)
    monkeypatch.setattr(cb, "_gate_run", fake)
    monkeypatch.setattr(cb, "_gate_rows", lambda out_dir: rows)
    t0 = time.time()
    outs = cb._run_gate_rows("/film", rows, {})
    took = time.time() - t0
    assert [s for s, _a, _o in outs] == [r[1] for r in rows]           # the board's order
    assert peak[0] >= 2 and took < 6 * 0.4 * 0.8, (peak[0], took)       # ran side by side
