"""Encounter and day finder search logic (Phase 4), on synthetic difficulty curves."""
import pytest

from engine.finder import (DAY_SCALES, ENCOUNTER_METRICS, ENCOUNTER_SCALES, bracket, choose, day_for, parse_limit,
                           parse_plan, parse_target, search)
from engine.templates import TEMPLATES

evaluated = []


def curve(job):
    """Synthetic outcome: someone down = scale/2, defeat = 10% per scale unit above 1."""
    scale, runs = job
    evaluated.append(job)
    return {"down": min(1.0, scale / 2), "defeat": max(0.0, (scale - 1) * 0.1), "runs": runs, "failed_runs": 0, "errors": {}}


def make(scale):
    return f"enc@{scale:.4f}", f"scale {scale:.2f}", lambda runs: (scale, runs)


def test_target_is_matched_and_refined():
    best, points = search(make, curve, ENCOUNTER_SCALES, ("down", 0.5), [])
    assert abs(best.metrics["down"] - 0.5) < 0.02 and best.runs == 400  # refined with the larger sample
    assert {p.runs for p in points} == {100, 400}


def test_limits_only_gives_the_hardest_feasible_scale():
    best, _ = search(make, curve, ENCOUNTER_SCALES, None, [("defeat", "<=", 0.02)])
    assert best.metrics["defeat"] <= 0.02 and best.scale > 1.1  # boundary is 1.2


def test_limit_beats_target():
    best, _ = search(make, curve, ENCOUNTER_SCALES, ("down", 0.9), [("defeat", "<=", 0.02)])
    assert best.metrics["defeat"] <= 0.02 and 1.1 < best.scale <= 1.2


def test_impossible_limits_give_no_answer():
    best, _ = search(make, curve, ENCOUNTER_SCALES, None, [("down", "<=", 0.01)])
    assert best is None


def test_identical_encounters_are_simulated_once_per_sample_size():
    evaluated.clear()
    bucket = lambda s: ("same", "same", lambda runs: (1.0, runs))
    search(bucket, curve, ENCOUNTER_SCALES, ("down", 0.5), [])
    assert evaluated == [(1.0, 100)]  # one fill for every scale: no bracket, no refinement


def test_no_fill_scales_are_skipped():
    gappy = lambda s: None if s < 0.5 else make(s)
    _, points = search(gappy, curve, ENCOUNTER_SCALES, ("down", 0.5), [])
    assert min(p.scale for p in points) >= 0.5


def test_choose_and_bracket_helpers():
    from engine.finder import Point
    pts = [Point(s, str(s), "", {"down": s / 2, "defeat": 0.0}, 100) for s in (0.5, 1.0, 2.0)]
    same = [Point(s, "one fill", "", {"down": s / 2, "defeat": 0.0}, 100) for s in (0.5, 1.0, 2.0)]
    assert bracket(same, ("down", 0.75), []) is None
    assert choose(pts, ("down", 0.45), []).scale == 1.0
    assert bracket(pts, ("down", 0.75), []) == (1.0, 2.0)
    assert bracket(pts, None, [("down", "<=", 0.6)]) == (1.0, 2.0)


def test_report_lists_each_fill_once_and_flags_a_missed_target():
    from engine.finder import Point, report
    pts = [Point(0.5, "a", "fill A", {"down": 0.1}, 100), Point(0.6, "a", "fill A", {"down": 0.1}, 400),
           Point(0.8, "b", "fill B", {"down": 0.9}, 100)]
    text = report("encounter", "T", pts[1], pts, ("down", 0.5), [], ("down",), "unit")
    rows = [line for line in text.splitlines() if line.startswith("| 0.")]
    assert rows[0].startswith("| 0.50–0.60 | 400 |") and len(rows) == 2
    assert "Note: no tested encounter lands within 10%" in text
    assert "Note:" not in report("encounter", "T", pts[1], pts, ("down", 0.15), [], ("down",), "unit")


def test_parsers():
    assert parse_target("down=0.5", ENCOUNTER_METRICS) == ("down", 0.5)
    assert parse_limit("defeat<=0.02", ENCOUNTER_METRICS) == ("defeat", "<=", 0.02)
    assert parse_limit(" win >= 0.9 ", ENCOUNTER_METRICS) == ("win", ">=", 0.9)
    for bad in ("down", "luck=0.5"):
        with pytest.raises(ValueError): parse_target(bad, ENCOUNTER_METRICS)
    with pytest.raises(ValueError): parse_limit("defeat<0.02", ENCOUNTER_METRICS)
    assert parse_plan("e e s e l e") == ["E", "E", "S", "E", "L", "E"]
    for bad in ("S S", "E X", ""):
        with pytest.raises(ValueError): parse_plan(bad)


def test_day_for_fills_each_encounter_with_its_own_seed():
    day, labels = day_for(["E", "E", "S", "E"], [TEMPLATES["swarm"], TEMPLATES["solo"]], 3600, seed=1)
    kinds = [next(iter(s)) for s in day["steps"]]
    assert kinds == ["encounter", "encounter", "rest", "encounter"] and day["steps"][2] == {"rest": "short"}
    assert len(day["steps"][1]["encounter"]) == 1 and len(labels) == 4  # second encounter uses the solo shape
    assert day_for(["E"], [TEMPLATES["solo"]], 5, seed=1) is None  # below the cheapest monster (CR 0, 10 XP)
    assert ENCOUNTER_SCALES[0] == DAY_SCALES[0] == 0.25
