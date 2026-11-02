"""2024 species traits (builder.SPECIES) and their engine hooks."""
import pytest

from engine import Combat, Combatant, load_spells
from engine.builder import ORIGIN_FEATS, SPECIES, build
from engine.loader import ROOT, ValidationError, load_sheet

SPELLS = load_spells()


def pc(species=None, choice=None, cls="fighter", level=5, **choices):
    if species: choices["species"] = species
    if choice: choices["species_choice"] = choice
    return Combatant.from_sheet(build(cls, level, choices=choices), "p0", "party")


def ogre(i=0): return Combatant.from_sheet(load_sheet(ROOT / "monsters" / "ogre.yaml"), f"e{i}", "enemy")


def test_builder_applies_species_and_rejects_bad_choices():
    plain = build("fighter", 5)
    assert build("fighter", 5, choices={"species": "dwarf"})["max_hp"] == plain["max_hp"] + 5
    assert "poison" in build("fighter", 5, choices={"species": "dwarf"})["resistances"]
    assert build("fighter", 5, choices={"species": "halfling"})["size"] == "S"
    assert build("fighter", 5, choices={"species": "human", "species_choice": "tough"})["max_hp"] == plain["max_hp"] + 10
    orc = build("fighter", 5, choices={"species": "orc"})["limited_uses"]
    assert orc["adrenaline_rush"]["max"] == 3 and orc["relentless_endurance"]["max"] == 1
    assert build("fighter", 5, choices={"species": "goliath", "species_choice": "stone"})["limited_uses"]["stones_endurance"]["max"] == 3
    assert SPECIES["human"] == ORIGIN_FEATS
    for bad in ({"species": "elf"}, {"species": "goliath"}, {"species_choice": "stone"}, {"species": "dwarf", "species_choice": "fire"},
                {"species": "human", "species_choice": "lucky", "origin_feat": "lucky"}):
        with pytest.raises(ValidationError): build("fighter", 5, choices=bad)


def test_relentless_endurance_drops_to_one_once():
    orc = pc("orc")
    combat = Combat([orc, ogre()], SPELLS, seed=1)
    combat.apply_damage(orc, orc.hp + 5)
    assert orc.hp == 1 and orc.limited_uses["relentless_endurance"] == 0
    combat.apply_damage(orc, 5)
    assert orc.hp == 0


def test_halfling_luck_rerolls_ones(monkeypatch):
    halfling = pc("halfling")
    combat = Combat([halfling, ogre()], SPELLS, seed=1)
    rolls = iter([17])
    monkeypatch.setattr("engine.class_mechanics.dice.d20", lambda rng, **k: next(rolls))
    assert combat.heroic_reroll(halfling, 1, lambda n: n >= 10) == 17
    assert combat.heroic_reroll(pc(), 1, lambda n: False) == 1  # no Luck without the trait


def test_stones_endurance_reduces_a_big_hit_with_the_reaction():
    goliath = pc("goliath", "stone")
    foe = ogre()
    combat = Combat([goliath, foe], SPELLS, seed=2)
    typed = {(goliath, "bludgeoning"): 20}
    combat.stone_reduce(typed, (foe, goliath, {"name": "Greatclub"}))
    assert typed[goliath, "bludgeoning"] < 20 and goliath.reaction == 0 and goliath.limited_uses["stones_endurance"] == 2
    small = {(goliath, "bludgeoning"): 3}
    goliath.reaction = 1
    combat.stone_reduce(small, (foe, goliath, {"name": "Greatclub"}))
    assert small[goliath, "bludgeoning"] == 3  # not worth a use


def test_adrenaline_rush_uses_a_spare_bonus_action_for_temp_hp():
    orc = pc("orc")
    combat = Combat([orc, ogre()], SPELLS, seed=1)
    orc.bonus_action = 1
    combat.adrenaline_rush(orc)
    assert orc.temp_hp == orc.proficiency_bonus and orc.bonus_action == 0 and orc.limited_uses["adrenaline_rush"] == 2
    combat.adrenaline_rush(orc)  # no Bonus Action left
    assert orc.limited_uses["adrenaline_rush"] == 2


@pytest.mark.parametrize("species,choice,trait", [("orc", None, "Adrenaline Rush"), ("goliath", "fire", "Fire's Burn"),
                                                  ("goliath", "stone", "Stone's Endurance"), ("human", "lucky", "Resourceful")])
def test_traits_fire_in_real_fights(species, choice, trait):
    seen = 0
    for seed in range(10):
        combat = Combat([pc(species, choice), ogre(0), ogre(1)], SPELLS, seed=seed)
        combat.run(30)
        seen += sum(1 for e in combat.log if e.get("name") == trait)
    assert seen > 0


def test_gnome_tiefling_dragonborn():
    gnome = pc("gnome")
    combat = Combat([gnome, ogre()], SPELLS, seed=1)
    assert combat.roll_flags(gnome, "saves", "wis")[0] and not combat.roll_flags(gnome, "saves", "dex")[0]
    assert "necrotic" in build("fighter", 5, choices={"species": "tiefling", "species_choice": "chthonic"})["resistances"]
    sheet = build("fighter", 5, choices={"species": "dragonborn", "species_choice": "silver"})
    breath = next(a for a in sheet["actions"] if a["name"] == "Breath Weapon")
    block = breath["effects"][0]
    assert "cold" in sheet["resistances"] and sheet["limited_uses"]["breath_weapon"]["max"] == 3
    assert block["on_fail"][0]["damage"]["dice"] == "2d10" and block["on_fail"][0]["damage"]["type"] == "cold"
    assert block["save"]["dc"] == 8 + (sheet["abilities"]["con"] - 10) // 2 + 3


def test_single_attackers_use_the_breath_weapon():
    used = 0
    for seed in range(10):
        rogue = pc("dragonborn", "red", cls="rogue")
        goblins = [Combatant.from_sheet(load_sheet(ROOT / "monsters" / "goblin_warrior.yaml"), f"e{i}", "enemy") for i in range(4)]
        combat = Combat([rogue, *goblins], SPELLS, seed=seed)
        combat.run(20)
        used += sum(1 for e in combat.log if e.get("event") == "action" and e.get("name") == "Breath Weapon")
    assert used > 0
