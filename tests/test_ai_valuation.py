"""The AI's damage estimates respect resistance/immunity and don't count overkill (2026-11-02 audit, C1-C3)."""
import random

from engine import Combat, Combatant
from engine.builder import load_character
from engine.loader import ROOT, load_sheet, load_spells

SPELLS = load_spells()


def monster(name, i=0): return Combatant.from_sheet(load_sheet(ROOT / "monsters" / f"{name}.yaml"), f"enemy_{i}", "enemy")
def pc(name, i=0): return Combatant.from_sheet(load_character(name), f"party_{i}", "party")


def test_damage_factor_mirrors_mitigation():
    wizard, elemental, troll = pc("wizard_5"), monster("fire_elemental", 0), monster("troll", 1)
    combat = Combat([wizard, elemental, troll], SPELLS, seed=1)
    assert combat.damage_factor(elemental, "fire") == 0
    assert combat.damage_factor(elemental, "slashing") == .5
    assert combat.damage_factor(elemental, "cold") == 1
    assert combat.damage_factor(troll, "fire") == 1
    assert combat.damage_factor(elemental, None) == 1


def test_fireball_has_no_value_against_fire_immune_targets():
    wizard, a, b = pc("wizard_5"), monster("fire_elemental", 0), monster("fire_elemental", 1)
    combat = Combat([wizard, a, b], SPELLS, seed=1)
    fireball = combat.scale(wizard, combat.spells["Fireball"], 3)
    assert combat.expected_spell_damage(wizard, fireball, a) == 0


def test_overkill_caps_each_victim_at_its_hp():
    wizard, goblin = pc("wizard_5"), monster("goblin_warrior")
    combat = Combat([wizard, goblin], SPELLS, seed=1)
    goblin.hp = 1
    fireball = combat.scale(wizard, combat.spells["Fireball"], 3)
    assert combat.expected_spell_damage(wizard, fireball, goblin) > 10
    assert combat.expected_spell_damage(wizard, fireball, goblin, overkill=True) <= 1


def test_wizard_never_fireballs_fire_elementals():
    rng, casts = random.Random(1), 0
    for _ in range(30):
        actors = [pc("wizard_5", 0), pc("fighter_5", 1), monster("fire_elemental", 0), monster("fire_elemental", 1)]
        combat = Combat(actors, SPELLS, seed=rng.getrandbits(64))
        combat.run(30)
        casts += sum(1 for e in combat.log if e["event"] == "cast" and e["spell"] == "Fireball")
    assert casts == 0


def haste_value(enemy, count):
    party = [pc(f"{c}_10", i) for i, c in enumerate(("fighter", "cleric", "rogue", "wizard"))]
    foes = [monster(enemy, i) for i in range(count)]
    combat = Combat(party + foes, SPELLS, seed=1)
    wizard = party[3]
    combat.begin_turn(wizard)
    return combat, wizard, combat.scale(wizard, combat.spells["Haste"], 3)


def test_haste_values_its_extra_attack_and_charges_for_lethargy(monkeypatch):
    combat, wizard, haste = haste_value("hill_giant", 2)
    with_lethargy = combat.expected_buff_value(wizard, haste, slot=3)
    assert with_lethargy > 0
    # Certain concentration: no lethargy cost, so the value can only rise.
    monkeypatch.setattr(combat, "concentration_keep", lambda *a: 1.0)
    assert combat.expected_buff_value(wizard, haste, slot=3) > with_lethargy
    # Concentration that never survives a round: the extra attack is worth less than the lost turn.
    monkeypatch.setattr(combat, "concentration_keep", lambda *a: 0.0)
    assert combat.expected_buff_value(wizard, haste, slot=3) < with_lethargy
