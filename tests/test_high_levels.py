"""Levels 11-20: class tables, builds, high-level spells and monsters, benchmark v2."""
import pytest

from engine import Combat, Combatant, dice
from engine.benchmark import default_version, freeze, load_benchmark
from engine.builder import build, load_build
from engine.calibration import BUDGETS
from engine.classes import SUBCLASSES, load_class
from engine.loader import ROOT, load_sheet, load_spells
from engine.monster_high import DRAGONS, OTHERS
from engine.monster_import import check_sheet, slug
from engine.spell_high import spells as high_spells
from engine.spell_validation import source_errors


@pytest.mark.parametrize("name", sorted(SUBCLASSES))
def test_every_class_builds_to_level_20_with_no_pending_features(name):
    data = load_class(name)
    assert set(data["levels"]) == set(range(1, 21))
    assert not [f["name"] for f in data["features"] if "in progress" in f.get("unsupported", "")]
    for level in (11, 13, 15, 17, 20):
        for profile in ("", "_casual", "_optimized"):
            assert load_build(f"{name}_{level}{profile}")["level"] == level


def test_epic_boon_is_an_extra_asi_and_fortitude_can_pass_20():
    from engine.builder import DEFAULT_ABILITIES, default_asis
    asis = default_asis("fighter", 20, {**DEFAULT_ABILITIES["fighter"], "str": 17, "con": 15})
    assert 19 in asis
    standard = build("fighter", 20, choices={"asis": asis})
    boon = build("fighter", 20, choices={"asis": {**asis, 19: {"feat": "boon_of_fortitude", "ability": "str"}}})
    assert standard["abilities"]["str"] == 20 and boon["abilities"]["str"] == 21
    assert boon["max_hp"] - standard["max_hp"] == 40


def test_high_level_class_numbers():
    assert build("fighter", 20)["extra_attack"] == 4 and build("fighter", 11)["extra_attack"] == 3
    assert build("fighter", 15)["features"]["improved_critical"] == 18
    assert build("barbarian", 20)["abilities"]["str"] == 24
    wizard = build("wizard", 20)
    assert wizard["spell_levels"] == {"Magic Missile": 1, "Scorching Ray": 2}
    assert wizard["limited_uses"]["free_fireball"]["short_rest"] == "all"
    assert {"wis", "cha"} <= set(build("rogue", 15)["save_proficiencies"])
    assert sorted(build("monk", 14)["save_proficiencies"]) == sorted(["str", "dex", "con", "int", "wis", "cha"])
    warlock = build("warlock", 17)
    assert {"free_circle_of_death", "free_finger_of_death", "free_power_word_stun", "free_power_word_kill"} <= set(warlock["limited_uses"])


def test_high_level_spells_pass_the_source_gate():
    loaded = load_spells()
    for spec in high_spells():
        assert spec["name"] in loaded
        assert source_errors(loaded[spec["name"]]) == [], spec["name"]


def caster(spell):
    return Combatant("c", team="party", max_hp=100, spells=[spell], spell_slots={i: 2 for i in range(1, 10)}, spell_dc=30, spell_attack_bonus=30)


def test_power_word_kill_kills_at_100_hp_and_damages_above():
    for hp, dead in ((100, True), (101, False)):
        c, t = caster("Power Word Kill"), Combatant("t", team="enemy", max_hp=hp)
        b = Combat([c, t], load_spells(), seed=1)
        b.current = c
        b.cast(c, "Power Word Kill", [t])
        assert t.dead == dead and (dead or t.hp < hp)


def test_signature_spell_is_free_once_then_uses_a_slot():
    c = caster("Fireball")
    c.limited_uses["free_fireball"] = 1; c.max_limited_uses["free_fireball"] = 1
    c.spell_slots = {3: 1}
    t = Combatant("t", team="enemy", max_hp=1000)
    b = Combat([c, t], load_spells(), seed=1)
    b.current = c
    b.cast(c, "Fireball")
    assert c.limited_uses["free_fireball"] == 0 and c.spell_slots[3] == 1
    b.begin_turn(c)
    b.cast(c, "Fireball")
    assert c.spell_slots[3] == 0


def test_studied_attacks_gives_advantage_after_a_miss(monkeypatch):
    rolls = []
    monkeypatch.setattr(dice, "d20", lambda rng, advantage=False, disadvantage=False: rolls.append(advantage) or 2)
    attack = {"name": "Sword", "kind": "melee", "to_hit": 0, "reach_ft": 5, "effects": [{"damage": {"dice": "1d8", "bonus": 0, "type": "slashing"}}]}
    f = Combatant("f", team="party", max_hp=50, attacks=[attack], features={"studied_attacks": True})
    t = Combatant("t", team="enemy", max_hp=50, ac=30)
    b = Combat([f, t], load_spells(), seed=1)
    b.current = f
    b.weapon_attack(f, t, attack)
    b.weapon_attack(f, t, attack)
    assert rolls == [False, True]


@pytest.mark.parametrize("name", DRAGONS + OTHERS)
def test_high_cr_monsters_match_the_source(name):
    assert check_sheet(load_sheet(ROOT / "monsters" / (slug(name) + ".yaml"))) == []


def test_benchmark_v2_keeps_v1_and_adds_levels_11_to_20():
    v1, v2 = load_benchmark(1), load_benchmark(2)
    assert set(v2["levels"]) == set(BUDGETS)
    assert all(v2["levels"][level] == v1["levels"][level] for level in range(1, 11))
    assert freeze(2)["levels"] == v2["levels"]
    assert default_version(10) == 1 and default_version(11) == 2
