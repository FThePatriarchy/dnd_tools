"""The engine.monster_more batch: source drift, reviewed riders, and every monster fights without errors."""
import random

import pytest

from engine import Combat, Combatant
from engine.builder import load_character
from engine.loader import ROOT, load_sheet, load_spells
from engine.monster_import import check_sheet, slug
from engine.monster_more import ACTIONS, NAMES, RIDERS, sheets

SPELLS = load_spells()


@pytest.mark.parametrize("name", NAMES)
def test_sheet_on_disk_matches_the_generator_and_the_source(name):
    sheet = load_sheet(ROOT / "monsters" / f"{slug(name)}.yaml")
    assert check_sheet(sheet) == []
    assert sheet == sheets()[name] | {}  # the committed file is what the reviewed generator writes
    assert not any(n.startswith("Manual") for n in sheet["unsupported"])


def test_reviewed_riders_are_on_the_sheets():
    s = sheets()
    assert any("apply_condition" in e and e["apply_condition"]["condition"] == "prone"
               for e in next(a for a in s["Mastiff"]["attacks"] if a["name"] == "Bite")["effects"])
    spore = next(a for a in s["Violet Fungus Necrohulk"]["actions"] if a["name"] == "Spore Bomb")["effects"][0]
    assert spore["target"]["select"] == "area" and spore["target"]["size_ft"] == 20
    trample = next(a for a in s["Gorgon"]["actions"] if a["name"] == "Trample")["effects"][0]
    assert trample["target"]["eligible_if"] == "target.has_condition(prone)"
    assert set(ACTIONS) <= set(NAMES) and set(RIDERS) <= set(NAMES)


def test_trample_only_hits_prone_creatures():
    # Without a grid the Gore's charge never knocks anyone Prone, so Trample (the elephant's only
    # Bludgeoning damage) never finds a legal target and deals nothing.
    for seed in range(5):
        fighter = Combatant.from_sheet(load_character("fighter_5"), "p0", "party")
        elephant = Combatant.from_sheet(load_sheet(ROOT / "monsters" / "elephant.yaml"), "e0", "enemy")
        combat = Combat([fighter, elephant], SPELLS, seed=seed)
        combat.run(15)
        assert not any(e.get("event") == "damage" and e.get("source") == "e0" and e.get("type") == "bludgeoning" for e in combat.log)


@pytest.mark.parametrize("name", NAMES)
def test_every_new_monster_fights_a_party(name):
    rng = random.Random(name)
    party = [Combatant.from_sheet(load_character(f"{c}_5"), f"p{i}", "party") for i, c in enumerate(("fighter", "cleric", "rogue", "wizard"))]
    foes = [Combatant.from_sheet(load_sheet(ROOT / "monsters" / f"{slug(name)}.yaml"), f"e{i}", "enemy") for i in range(2)]
    result = Combat(party + foes, SPELLS, seed=rng.getrandbits(64)).run(30)
    assert result["winner"] in {"party", "enemy", None}
