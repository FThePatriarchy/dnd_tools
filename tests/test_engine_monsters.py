from copy import deepcopy
from statistics import mean

import pytest

from engine import Combat, Combatant, load_sheet, load_spells, ValidationError
from engine.loader import ROOT
from engine.monster_import import import_monsters, parse_monster


@pytest.fixture(scope="module")
def spells(): return load_spells()


def monster(name):
    return Combatant.from_sheet(load_sheet(ROOT / "monsters" / (name + ".yaml")), name, "enemy")


def test_imported_structured_fields_match_reviewed_monsters():
    parsed = import_monsters()
    for raw in parsed.values():
        stored = load_sheet(ROOT / "monsters" / (raw["name"].lower().replace(" ", "_") + ".yaml"))
        for key in ("ac", "max_hp", "hp_formula", "abilities", "save_bonuses", "save_proficiencies", "resistances", "immunities", "vulnerabilities", "proficiency_bonus", "cr", "attacks", "initiative_bonus"):
            assert stored[key] == raw[key], (stored["name"], key)
    assert parsed["Goblin Warrior"]["creature_type"] == "fey"
    assert parsed["Young Red Dragon"]["proficiency_bonus"] == 4
    assert parsed["Young Red Dragon"]["initiative_bonus"] == 4


def test_parser_rejects_unrecognized_weapon_damage():
    raw = {"name": "Fixture", "source": "XMM", "cr": "1", "ac": [12], "hp": {"average": 10, "formula": "2d8+1"}, "speed": {"walk": 30}, "type": "humanoid", **dict.fromkeys(("str", "dex", "con", "int", "wis", "cha"), 10), "action": [{"name": "Weapon", "entries": ["{@atkr m} {@hit 2} {@damage 1d6} unknown damage"]}]}
    with pytest.raises(ValueError, match="unparsed weapon damage"):
        parse_monster(raw)


def test_ogre_attack_hit_and_damage_math(spells):
    ogre = monster("ogre")
    target = Combatant("dummy", team="party", max_hp=1000000, ac=16)
    b = Combat([ogre, target], spells, seed=81)
    attacks = 12000
    hits = 0
    for _ in range(attacks):
        hits += b.weapon_attack(ogre, target, ogre.attacks[0])
    assert hits / attacks == pytest.approx(.55, abs=.015)
    # +6 vs AC16, 2d8+4: 50% normal hits, 5% crit (4d8+4).
    assert (target.max_hp - target.hp) / attacks == pytest.approx(.5 * 13 + .05 * 22, abs=.2)


def test_dragon_recharge_frequency_and_multiattack(spells):
    dragon = monster("young_red_dragon")
    target = Combatant("dummy", team="party", max_hp=1000000)
    b = Combat([dragon, target], spells, seed=17)
    recovered = 0
    trials = 12000
    for _ in range(trials):
        dragon.recharge_ready["Fire Breath"] = False
        b.begin_turn(dragon)
        recovered += dragon.recharge_ready["Fire Breath"]
    assert recovered / trials == pytest.approx(1 / 3, abs=.015)
    b.log.clear()
    b.weapon_action(dragon)
    assert sum(e["event"] == "attack" for e in b.log) == 3
    assert all(e["attacker"] == dragon.id for e in b.log if e["event"] == "attack")
    assert dragon.immunities == ["fire"]


def test_dragon_breath_uses_effect_blocks_and_consumes_recharge(spells):
    dragon = monster("young_red_dragon")
    target = Combatant("dummy", team="party", max_hp=1000, save_bonuses={"dex": -100})
    b = Combat([dragon, target], spells, seed=12)
    b.begin_turn(dragon)
    assert b.use_action(dragon, "Fire Breath")
    assert 16 <= target.max_hp - target.hp <= 96
    assert dragon.action == 0 and not dragon.recharge_ready["Fire Breath"]
    dragon.action = 1
    assert not b.use_action(dragon, "Fire Breath")


def test_goblin_advantage_rider_and_nimble_escape(spells):
    goblin = monster("goblin_warrior")
    target = Combatant("dummy", team="party", max_hp=1000, ac=-100)
    b = Combat([goblin, target], spells, seed=1)
    b.begin_turn(goblin)
    b.weapon_attack(goblin, target, goblin.attacks[0])
    assert sum(e["event"] == "damage" for e in b.log) == 1
    from engine.state import Effect
    goblin.effects.append(Effect("advantage", {"on": "attack_rolls", "scope": "all", "against": None}, 0, "test"))
    b.log.clear()
    b.weapon_attack(goblin, target, goblin.attacks[0])
    # Same-type components now form one mitigated packet (including the rider).
    damage = [e for e in b.log if e["event"] == "damage"]
    assert len(damage) == 1 and damage[0]["amount"] == 7
    assert b.use_action(goblin, "Nimble Escape")
    assert goblin.bonus_action == 0 and goblin.has_status("disengaged")


def test_fanatic_innate_spells_reference_specs_and_limited_uses(spells):
    fanatic = monster("cultist_fanatic")
    target = Combatant("dummy", team="party", max_hp=1000)
    b = Combat([fanatic, target], spells, seed=1)
    b.begin_turn(fanatic)
    assert b.cast(fanatic, "Spiritual Weapon", targets=[target])
    assert fanatic.limited_uses["Spiritual Weapon"] == 1
    assert fanatic.concentration is not None
    assert not fanatic.spell_slots
    b.begin_turn(fanatic)
    b.cast(fanatic, "Spiritual Weapon", targets=[target])
    b.begin_turn(fanatic)
    assert not b.can_cast(fanatic, "Spiritual Weapon")
