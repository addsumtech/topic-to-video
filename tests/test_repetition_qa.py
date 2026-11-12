"""repetition_qa — one staging over many beats (the lit-window pass the user called too deliberate, 2026-11-12)."""
import os
import sys

import pytest

np = pytest.importorskip("numpy")
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import critic_ledger as cl  # noqa: E402
import repetition_qa as rq  # noqa: E402


def _quad(seed):
    """A dark ground with one bright tilted page, its contents varying beat to beat."""
    rng = np.random.default_rng(seed)
    f = np.full((14, 32), 10.0)
    for y in range(2, 12):
        f[y, 3 + y // 4: 29 - y // 5] = 230
    f[4:9, 8:24] -= rng.uniform(0, 60, (5, 16))
    return ((f - f.mean()) / f.std()).ravel()


def _varied(seed):
    rng = np.random.default_rng(100 + seed)
    f = rng.uniform(0, 255, (14, 32))
    return ((f - f.mean()) / f.std()).ravel()


def test_many_beats_on_one_staging_are_found_and_a_varied_film_is_not():
    film = [_quad(i) if i % 2 == 0 else _varied(i) for i in range(20)]       # 10 of 20 staged alike
    group = rq.largest_staging(film)
    assert sorted(group) == list(range(0, 20, 2)) and rq.verdict(20, group)
    varied = [_varied(i) for i in range(20)]
    assert not rq.verdict(20, rq.largest_staging(varied))


def test_a_few_alike_beats_are_a_motif_not_a_device():
    film = [_quad(i) for i in range(5)] + [_varied(i) for i in range(19)]      # 5 of 24 (WorkBuddy's case)
    assert not rq.verdict(24, rq.largest_staging(film))


def test_it_is_an_advisory_gate():
    rows = [g for g in cl.DELIVERY_GATES["remotion"] if g[1] == "repetition_qa.py"]
    assert len(rows) == 1 and rows[0][4] is False
