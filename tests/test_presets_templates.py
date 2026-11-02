"""Casual/optimized party presets and encounter templates (Phase 3)."""
import pytest
import yaml

from engine.builder import load_build
from engine.classes import SUBCLASSES
from engine.loader import ROOT
from engine.presets import LEVELS, PRIMARY, PROFILES, party, preset_name, recipe
from engine.templates import DEFAULT_EXCLUDE, MIN_FILL, TEMPLATES, fills, parse_shape, suggest

PROFILE_ORDER = ("casual", "standard", "optimized")


@pytest.mark.parametrize("profile", list(PROFILES))
def test_committed_preset_files_match_their_rules(profile):
    for name in SUBCLASSES:
        for level in LEVELS:
            path = ROOT / "builds" / f"{preset_name(name, level, profile)}.yaml"
            assert yaml.safe_load(path.read_text(encoding="utf-8")) == recipe(name, level, profile), path


def test_primary_ability_rises_casual_standard_optimized():
    for name in SUBCLASSES:
        for level in LEVELS:
            scores = [load_build(preset_name(name, level, p))["abilities"][PRIMARY[name]] for p in PROFILE_ORDER]
            assert scores == sorted(scores) and scores[0] < scores[2], (name, level, scores)


def test_casual_wizard_avoids_reaction_spells_and_optimized_takes_shield():
    for level in LEVELS:
        casual = load_build(f"wizard_{level}_casual")["spells"]
        assert "Shield" not in casual and "Counterspell" not in casual
        assert "Shield" in load_build(f"wizard_{level}_optimized")["spells"]


def test_party_names():
    assert party(5) == ["fighter_5", "cleric_5", "rogue_5", "wizard_5"]
    assert party(7, "casual") == ["fighter_7_casual", "cleric_7_casual", "rogue_7_casual", "wizard_7_casual"]


def test_buff_planning_handles_all_targets():
    # Beacon of Hope (target n: all) in a prebuff plan used to crash slicing with "all".
    from engine.encounters import run_encounter
    assert "Beacon of Hope" in load_build("cleric_5_casual")["spells"]
    r = run_encounter(party(5, "casual"), ["owlbear x1"], 2, 1)
    assert r["runs"] == 2 and not r["errors"]


def test_parse_shape():
    assert parse_shape("1 boss, 6 goons") == {"boss": 1, "minion": 6}
    assert parse_shape("2 elites + 3 mooks and 1 boss") == {"elite": 2, "minion": 3, "boss": 1}
    assert parse_shape("4x minion") == {"minion": 4}
    for bad in ("1 dragon", "boss", "", "0 boss"):
        with pytest.raises(ValueError): parse_shape(bad)


@pytest.mark.parametrize("template", list(TEMPLATES))
def test_template_fills_respect_budget_and_roles(template):
    shape = TEMPLATES[template]
    total = 4400  # level 5 High for four PCs
    legal = fills(shape, total)
    assert legal, template
    for fill, xp in legal:
        assert MIN_FILL * total <= xp <= total
        assert [r for r, *_ in fill] == list(shape) and [n for _, _, n, _ in fill] == list(shape.values())
        names = [m for _, m, _, _ in fill]
        assert len(set(names)) == len(names) and not set(names) & set(DEFAULT_EXCLUDE)
    assert [x for _, x in legal] == sorted((x for _, x in legal), reverse=True)


def test_suggestions_are_seeded_and_cube_needs_opt_in():
    shape = {"minion": 8}
    assert suggest(shape, 4400, seed=3) == suggest(shape, 4400, seed=3)
    assert any(m == "gelatinous_cube" for f, _ in fills(shape, 4400, exclude=()) for _, m, _, _ in f)
    assert not any(m == "gelatinous_cube" for f, _ in fills(shape, 4400) for _, m, _, _ in f)


def test_impossible_budget_gives_no_fill():
    assert fills({"boss": 1}, 5) == []  # below the cheapest monster (CR 0, 10 XP)
