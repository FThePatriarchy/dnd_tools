"""Frozen benchmark set and party rating."""
import math

import pytest

from engine.benchmark import COUNTS, encounter_xp, freeze, load_benchmark
from engine.calibration import BUDGETS
from engine.rating import _Inline, crossing, markdown, rate_party

TYPES = {"brute", "ranged", "caster", "swarm", "control", "solo"}


def test_benchmark_v1_is_complete_and_rising():
    b = load_benchmark(1)
    assert b["version"] == 1 and b["party_size"] == 4 and set(b["types"]) == TYPES
    assert set(b["levels"]) == {level for level in BUDGETS if level <= 10}
    for level, ladders in b["levels"].items():
        assert set(ladders) == TYPES
        high_total = BUDGETS[level][2] * 4
        for kind, ladder in ladders.items():
            xp = [encounter_xp([e]) for e in ladder]
            assert xp == sorted(xp) and len(ladder) >= 2, (level, kind)
            if kind != "solo":
                # One monster per type and level, counts from COUNTS, reaching 2.5x High unless capped.
                assert len({e.split(" x")[0] for e in ladder}) == 1
                assert [int(e.split(" x")[1]) for e in ladder] == list(COUNTS[:len(ladder)])
                assert xp[-1] >= 2.5 * high_total or len(ladder) == len(COUNTS)


def test_freeze_rules_reproduce_v1():
    # v1 must stay reproducible from the committed rules; changing the rules means freezing v2.
    assert freeze()["levels"] == load_benchmark(1)["levels"]


def test_crossing_interpolates_and_censors():
    steps = [["a x1", 100, 0.0], ["a x2", 200, 0.02], ["a x3", 300, 0.08]]
    xp, censored = crossing(steps, 0.05)
    assert censored == "" and math.isclose(xp, 250)
    assert crossing([["a x1", 100, 0.3], ["a x2", 200, 0.9]], 0.05) == (100, "below")
    assert crossing([["a x1", 100, 0.0], ["a x2", 200, 0.01]], 0.05) == (200, "above")


def test_rate_party_uses_every_ladder_step(monkeypatch):
    # Synthetic probe: defeat rises linearly with encounter XP, reaching 5% at 1,000 XP.
    def probe(job):
        builds, encounter, seed, runs, strategy, morale = job
        assert builds == ["fighter_3", "cleric_3", "rogue_3", "wizard_3"] and runs == 50
        return {"defeat": encounter_xp([encounter]) / 20000, "runs": runs, "failed_runs": 0, "ci": {"defeat": 0.01}, "errors": {}}
    rating = rate_party(["fighter_3", "cleric_3", "rogue_3", "wizard_3"], probe=probe, executor=_Inline(), workers=1)
    assert rating.level == 3 and set(rating.types) == TYPES
    for t in rating.types.values():
        if not t.censored: assert math.isclose(t.xp, 1000)
    assert rating.multiple(1000) == 1000 / 4 / BUDGETS[3][2]
    text = markdown(rating)
    assert "Overall" in text and "### swarm" in text


def test_rate_party_skips_steps_past_a_confirmed_crossing():
    calls = []
    def probe(job):
        encounter = job[1]
        calls.append(encounter)
        defeat = 0.0 if encounter_xp([encounter]) < 1000 else 0.5  # confidently above 5% from 1,000 XP
        return {"defeat": defeat, "runs": 50, "failed_runs": 0, "ci": {"defeat": 0.01}, "errors": {}}
    rating = rate_party(["fighter_3", "cleric_3", "rogue_3", "wizard_3"], probe=probe, executor=_Inline(), workers=1)
    ladders = load_benchmark(1)["levels"][3]
    for kind, t in rating.types.items():
        first_high = next((i for i, e in enumerate(ladders[kind]) if encounter_xp([e]) >= 1000), None)
        expected = ladders[kind] if first_high is None else ladders[kind][:first_high + 1]
        assert [s[0] for s in t.steps] == expected
        assert list(dict.fromkeys(e for e in calls if e in ladders[kind])) == expected
    assert rating.runs == 50 * len(calls)


def test_batch_results_do_not_depend_on_completion_order():
    # Spare workers run extra batches; the result is the decided prefix in batch order.
    from engine.rating import Step
    st = Step("brute", 0, "worg x1")
    for b in (2, 1, 0):  # arrive out of order; 0 and 1 are enough to decide (0 defeats in 100 runs)
        st.batches[b] = {"defeat": 0.0 if b < 2 else 1.0, "runs": 50, "failed_runs": 0, "errors": {}}
        st.evaluate(0.05)
    assert st.decided == 2 and st.result()["defeat"] == 0.0 and st.result()["runs"] == 100


def test_batch_seeds_are_deterministic():
    from engine.rating import batch_seed
    assert batch_seed(1, "worg x1", 0) == batch_seed(1, "worg x1", 0) != batch_seed(1, "worg x1", 1)
    assert batch_seed(1, "worg x1", 0) != batch_seed(2, "worg x1", 0)


def test_rate_party_rejects_engine_errors():
    def probe(job):
        return {"defeat": 0.0, "runs": 1, "failed_runs": 0, "ci": {"defeat": 0.5}, "errors": {"ValueError: boom": 1}}
    with pytest.raises(RuntimeError, match="engine errors"):
        rate_party(["fighter_3", "cleric_3", "rogue_3", "wizard_3"], probe=probe, executor=_Inline(), workers=1)
