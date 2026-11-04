"""The DM command line: argument parsing, reports and per-character detail."""
import json

import pytest

from engine.dm import day_from_steps, main, monster_entries
from engine.encounters import run_day_runs, run_encounter


def test_monster_entries_accept_spaced_comma_and_split_counts():
    assert monster_entries(["ogre x2", "goblin_warrior", "x3"]) == ["ogre x2", "goblin_warrior x3"]
    assert monster_entries(["bandit x6, bandit_captain"]) == ["bandit x6", "bandit_captain"]
    with pytest.raises(ValueError, match="must follow"): monster_entries(["x2", "ogre"])
    with pytest.raises(ValueError, match="unknown monster"): monster_entries(["dragon"])


def test_day_from_steps_reads_rests_and_encounters():
    day = day_from_steps(["ogre x2", "short", "bandit x3, scout", "L", "troll"])
    assert day["steps"] == [{"encounter": ["ogre x2"]}, {"rest": "short"}, {"encounter": ["bandit x3", "scout"]},
                            {"rest": "long"}, {"encounter": ["troll"]}]


def test_detail_adds_characters_without_changing_metrics():
    plain = run_encounter(["fighter_3", "cleric_3"], ["ogre"], 20, 4)
    detailed = run_encounter(["fighter_3", "cleric_3"], ["ogre"], 20, 4, detail=True)
    assert {k: v for k, v in detailed.items() if k != "characters"} == plain
    fighter, cleric = detailed["characters"]
    assert fighter["name"].startswith("Fighter 3") and 0 <= fighter["down"] <= 1 and 0 <= cleric["hp_left"] <= 1
    assert detailed["down"] >= max(fighter["down"], cleric["down"])


def test_day_detail_lists_each_encounter():
    day = day_from_steps(["goblin_warrior x2", "short", "ogre"])
    plain = run_day_runs(["fighter_3", "cleric_3"], day, 10, 2)
    detailed = run_day_runs(["fighter_3", "cleric_3"], day, 10, 2, detail=True)
    assert {k: v for k, v in detailed.items() if k not in {"encounters", "characters"}} == plain
    first, second = detailed["encounters"]
    assert first["reached"] == 1 and second["reached"] <= first["cleared"]
    assert len(detailed["characters"]) == 2


def test_fight_and_day_reports(capsys):
    main(["fight", "--party", "fighter_3", "cleric_3", "--monsters", "ogre", "--runs", "10"])
    out = capsys.readouterr().out
    assert "ogre — 450 XP = " in out and "Someone goes down" in out and "Fighter 3" in out
    main(["day", "--level", "1", "--steps", "goblin_warrior x2", "short", "goblin_warrior x2", "--runs", "5"])
    out = capsys.readouterr().out
    assert "2. short rest" in out and "Day total: 200 XP" in out
    main(["fight", "--level", "1", "--monsters", "wolf", "--runs", "5", "--json"])
    assert json.loads(capsys.readouterr().out)["runs"] == 5
    main(["monsters", "--max-cr", "1/8"])
    assert "bandit" in capsys.readouterr().out


def test_bad_input_is_a_usage_error(capsys):
    with pytest.raises(SystemExit): main(["fight", "--level", "5", "--monsters", "dragon"])
    assert "unknown monster" in capsys.readouterr().err


def test_levels_without_presets_are_rejected_cleanly(capsys):
    import pytest
    from engine.dm import main
    with pytest.raises(SystemExit):
        main(["fight", "--level", "4", "--monsters", "ogre"])
    assert "invalid choice: '4'" in capsys.readouterr().err


def test_compare_party_must_contain_the_replaced_member(monkeypatch, capsys):
    import sys, pytest
    from engine import compare
    monkeypatch.setattr(sys, "argv", ["compare", "--level", "5", "--class", "fighter", "--candidates", "fighter_5",
                                      "--party", "cleric_5", "rogue_5", "--replace", "fighter_5"])
    with pytest.raises(SystemExit):
        compare.main()
    assert "--replace" in capsys.readouterr().err


def test_budget_line_names_the_dmg_band():
    from engine.dm import budget_line
    party = [5] * 4  # Low 2,000 · Moderate 3,000 · High 4,400
    assert ", Low (" in budget_line(1100, party) and ", Low (" in budget_line(2000, party)
    assert ", Moderate (" in budget_line(2500, party) and ", High (" in budget_line(4400, party)
    assert ", above High (" in budget_line(5000, party)
