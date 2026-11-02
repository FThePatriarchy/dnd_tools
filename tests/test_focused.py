"""Focused, paired build comparison (engine.focused) with a fake probe: no simulation."""
import random

import pytest

from engine.focused import FocusedComparison, Focused, _bracket
from engine.rating import _Inline, crossing

PARTY = ["fighter_1", "cleric_1", "rogue_1", "wizard_1"]


def count(encounter): return int(encounter.split(" x")[1])


def fake_probe(strength):
    """Defeat rises with the monster count and falls with the party's 'strength' (by build name);
    noise is drawn from the batch seed, so equal seeds give equal results (common random numbers)."""
    def probe(task):
        builds, encounter, seed, runs, *_ = task
        p = min(1, max(0, 0.08 * (count(encounter) - strength(builds))))
        rng = random.Random(seed)
        defeats = sum(rng.random() < p for _ in range(runs))
        return {"runs": runs, "failed_runs": 0, "defeat": defeats / runs, "errors": {}, "ci": {"defeat": 0}}
    return probe


def strength(builds):
    return 1.0 + sum(1.5 for b in builds if isinstance(b, str) and b.endswith("_strong")) - sum(1.5 for b in builds if isinstance(b, str) and b.endswith("_weak"))


@pytest.fixture
def comparison(monkeypatch):
    # Party sheets are real builds; only the probe is fake, and it reads candidate names, never sheets.
    return FocusedComparison(PARTY, runs=200, executor=_Inline(), probe=fake_probe(strength))


def test_bracket_picks_the_deciding_steps():
    steps = [["a", 1, 0.0], ["b", 2, 0.01], ["c", 3, 0.2], ["d", 4, 0.6]]
    assert _bracket(steps, 4, 0.05) == [1, 2]
    assert _bracket([["a", 1, 0.3]], 4, 0.05) == [0]          # crosses on the first step
    assert _bracket(steps[:2], 2, 0.05) == [1]                  # never crosses: the last step


def test_identical_candidate_has_zero_change_and_zero_width(comparison):
    same = comparison.measure("same", PARTY)
    ch = comparison.change(same, reps=200)
    assert ch["overall"] == (0.0, 0.0, 0.0)
    assert all(ch[k][:3] == (0.0, 0.0, 0.0) for k in comparison.ladders)


def test_stronger_and_weaker_candidates_move_the_right_way_and_widen_brackets(comparison):
    strong = comparison.measure("strong", ["fighter_1_strong"] + PARTY[1:])
    weak = comparison.measure("weak", ["fighter_1_weak"] + PARTY[1:])
    up, down = comparison.change(strong, reps=300), comparison.change(weak, reps=300)
    assert up["overall"][1] > 0 and down["overall"][2] < 0       # intervals exclude zero
    # The crossings moved off the base bracket, so the measure loop added steps beyond it.
    for kind, idx in comparison.start.items():
        if len(comparison.ladders[kind]) > max(idx) + 1 and up[kind][3] == "":
            assert max(strong.batches[kind]) >= max(idx)
    for kind in comparison.ladders:
        lo = min(weak.batches[kind])
        steps = weak.steps(kind, comparison.ladders[kind])
        assert steps[0][2] < 0.05 or lo == 0                       # the lowest measured step is below the threshold
        assert crossing(steps, 0.05)[0] > 0


def test_focused_steps_reproduce_crossing_semantics():
    f = Focused("x", [], {"t": {2: [0.0, 0.02], 3: [0.1, 0.3]}})
    ladder = ["ogre x1", "ogre x2", "ogre x3", "ogre x4"]
    steps = f.steps("t", ladder)
    assert [s[2] for s in steps] == [0.01, 0.2]
    assert [s[2] for s in f.steps("t", ladder, {("t", 2): [0, 0], ("t", 3): [1, 1]})] == [0.0, 0.3]
