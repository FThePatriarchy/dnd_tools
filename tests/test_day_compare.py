"""Day-based build comparison (engine.day_compare) with a fake day runner: no simulation."""
import random

import pytest

from engine import day_compare
from engine.day_compare import DayComparison
from engine.rating import _Inline

PARTY = ["fighter_5", "cleric_5", "rogue_5", "wizard_5"]


def fake_job(task):
    builds, day, runs, seed, strategy = task
    p = .5 + .2 * ("monk_5" in builds) - .2 * ("rogue_5_casual" in builds)
    rng = random.Random(seed)
    done = sum(rng.random() < p for _ in range(runs)) / runs
    return {"complete": done, "death": 1 - done, "defeat": (1 - done) / 2, "downs": 2 * (1 - done), "hp_left": .5, "slots_left": .3, "runs": runs}


@pytest.fixture
def comparison(monkeypatch):
    monkeypatch.setattr(day_compare, "_job", fake_job)
    return DayComparison(PARTY, days=2, runs=40, executor=_Inline())


def test_identical_party_has_zero_change(comparison):
    ch = comparison.change(comparison.measure("same", PARTY))
    assert ch["overall"] == (0, 0, 0)


def test_better_and_worse_members_move_the_headline(comparison):
    up = comparison.change(comparison.measure("monk", ["fighter_5", "cleric_5", "monk_5", "wizard_5"]))
    down = comparison.change(comparison.measure("casual", ["fighter_5", "cleric_5", "rogue_5_casual", "wizard_5"]))
    assert up["overall"][1] > 0 and down["overall"][2] < 0
    assert up["death"][0] < 0 and comparison.batches >= 4


def test_flag_when_the_base_always_or_never_completes(comparison):
    comparison.base_rating.complete = .99
    assert "raise the intensity" in comparison.flag()
    comparison.base_rating.complete = .5
    assert comparison.flag() == ""
