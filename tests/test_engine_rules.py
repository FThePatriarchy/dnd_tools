import random

import pytest

from engine import Combat, Combatant, load_spells, load_sheet
from engine.loader import ROOT
from engine.dice import d20
from engine.state import Effect
from engine.policy import Policy


@pytest.fixture(scope="module")
def spells(): return load_spells()


def test_advantage_disadvantage_cancel_one_roll_not_pair():
    for seed in range(100):
        normal, cancel = random.Random(seed), random.Random(seed)
        assert d20(normal) == d20(cancel, True, True)
        assert normal.getstate() == cancel.getstate()
    trials = [d20(random.Random(seed), True) for seed in range(10000)]
    assert sum(x >= 11 for x in trials) / len(trials) == pytest.approx(.75, abs=.015)


def test_damage_mitigation_and_healing_and_temp_hp(spells):
    c = Combatant("c", max_hp=100, temp_hp=7, resistances=["fire"], immunities=["poison"], vulnerabilities=["cold"])
    b = Combat([c], spells)
    b.damage(c, 15, "fire")
    assert c.hp == 100 and c.temp_hp == 0
    b.damage(c, 10, "poison")
    assert c.hp == 100
    b.damage(c, 5, "cold")
    assert c.hp == 90
    c.resistances.append("cold")
    b.damage(c, 5, "cold")
    assert c.hp == 86  # floor resistance before vulnerability
    b.heal(c, 100)
    assert c.hp == c.max_hp


def test_2024_slot_per_global_turn_including_reactions(spells):
    c = Combatant("c", team="party", spells=["Healing Word", "Guiding Bolt", "Sacred Flame", "Shield"], spell_slots={1: 5}, spell_attack_bonus=100)
    d = Combatant("d", max_hp=1000)
    b = Combat([c, d], spells)
    b.begin_turn(c)
    assert b.cast(c, "Healing Word", targets=[c])
    assert not b.can_cast(c, "Guiding Bolt") and not b.can_cast(c, "Shield")
    assert b.cast(c, "Sacred Flame", targets=[d])
    b.begin_turn(d)
    assert b.can_cast(c, "Shield")
    b.cast(c, "Shield")
    assert c.reaction == 0
    b.begin_turn(c)
    assert c.reaction == 1 and b.can_cast(c, "Guiding Bolt")


def test_concentration_replaced_and_incapacitation_ends_it(spells):
    c = Combatant("c", team="party", spells=["Bless", "Shield of Faith", "Hold Person"], spell_slots={1: 3, 2: 2}, spell_dc=100)
    d = Combatant("d", spells=["Hold Person"], spell_slots={2: 2}, spell_dc=100)
    b = Combat([c, d], spells)
    b.begin_turn(c)
    first = b.cast(c, "Bless", targets=[c])
    b.begin_turn(c)
    second = b.cast(c, "Shield of Faith", targets=[c])
    assert not first.active and c.concentration == second.id
    b.begin_turn(d)
    b.cast(d, "Hold Person", targets=[c])
    assert c.has_condition("incapacitated") and not second.active and c.concentration is None
    assert not b.can_cast(c, "Bless")


def test_paralyzed_melee_crits_and_conditions(spells):
    a = Combatant("a", team="party")
    d = Combatant("d", max_hp=1000, conditions={"paralyzed"})
    b = Combat([a, d], spells, seed=4)
    crits = []
    b.attack(a, d, 100, lambda critical, roll: crits.append(critical))
    assert crits == [True]
    assert not b.attack(d, a, 100, lambda *args: pytest.fail("incapacitated attack"))
    d.conditions = {"restrained"}
    d.save_bonuses["dex"] = 0
    assert b.roll_flags(d, "saves", "dex") == (False, False)  # condition applied by save resolver
    d.conditions = {"poisoned"}
    d.effects.append(Effect("disadvantage", {"on": "ability_checks", "scope": "all", "against": None}, 0, "test"))
    assert b.roll_flags(d, "ability_checks")[1]


def test_fighter_extra_attack_graze_second_wind_and_action_surge(spells):
    f = Combatant.from_sheet(load_sheet(ROOT / "characters" / "fighter5.yaml"), "f", "party")
    d = Combatant("d", max_hp=10000, ac=1000)
    b = Combat([f, d], spells, seed=1)
    b.begin_turn(f)
    f.hp = 1
    assert b.use_action(f, "Second Wind")
    assert 7 <= f.hp <= 16 and f.bonus_action == 0
    assert f.limited_uses["second_wind"] == 2
    b.weapon_action(f)
    assert d.hp == d.max_hp - 8  # both misses graze for Str modifier
    assert b.use_action(f, "Action Surge")
    b.weapon_action(f)
    assert sum(e["event"] == "attack" for e in b.log) == 4
    assert not b.use_action(f, "Action Surge")


def test_haste_action_is_one_attack_not_extra_attack_routine(spells):
    f = Combatant.from_sheet(load_sheet(ROOT / "characters" / "fighter5.yaml"), "f", "party")
    c = Combatant("c", team="party", spells=["Haste"], spell_slots={3: 1})
    d = Combatant("d", max_hp=10000)
    b = Combat([c, f, d], spells)
    b.begin_turn(c)
    b.cast(c, "Haste", targets=[f])
    b.begin_turn(f)
    b.weapon_action(f)
    extra = f.extra_actions.pop()
    b.weapon_action(f, granted=extra)
    assert sum(e["event"] == "attack" for e in b.log) == 3


def test_single_pluggable_area_heuristic_and_slow_noop(spells):
    calls = []
    def area(shape, size, n):
        calls.append((shape, size, n))
        return [n - 1] if n else []
    c = Combatant("c", team="party", spells=["Spirit Guardians"], spell_slots={3: 1})
    a, d = Combatant("a"), Combatant("d")
    b = Combat([c, a, d], spells, area=area)
    b.begin_turn(c)
    b.cast(c, "Spirit Guardians")
    assert calls and all(x[:2] == ("emanation", 15) for x in calls)
    assert not a.effects and d.effects
    assert d.speed == 30  # modification recorded but no speed/movement simulation


def test_round_duration_and_exact_next_turn_boundary(spells):
    c = Combatant("c", team="party", spells=["Guiding Bolt", "Shield of Faith"], spell_slots={1: 2}, spell_attack_bonus=100)
    d = Combatant("d", max_hp=1000)
    b = Combat([c, d], spells)
    b.begin_turn(c)
    bolt = b.cast(c, "Guiding Bolt", targets=[d])
    b.time_rounds = 2
    b.begin_turn(d)
    assert bolt.active  # exact next-turn boundary overrides nominal round duration
    b.begin_turn(c)
    assert bolt.active
    b.end_turn(c)
    assert not bolt.active
    b.begin_turn(c)
    faith = b.cast(c, "Shield of Faith", targets=[c])
    b.time_rounds = faith.cast_round + 100
    b.begin_turn(d)
    assert not faith.active and b.armor_class(c) == c.ac


def test_action_surge_does_not_grant_magic_action(spells):
    f = Combatant.from_sheet(load_sheet(ROOT / "characters" / "fighter5.yaml"), "f", "party")
    f.spells, f.spell_slots = ["Fire Bolt"], {}
    d = Combatant("d", max_hp=1000)
    b = Combat([f, d], spells)
    b.begin_turn(f)
    b.weapon_action(f)
    assert b.use_action(f, "Action Surge")
    assert not b.can_cast(f, "Fire Bolt")
    assert b.weapon_action(f)


def test_default_policy_heals_and_keeps_concentration(spells):
    c = Combatant.from_sheet(load_sheet(ROOT / "characters" / "cleric5.yaml"), "c", "party")
    ally = Combatant("ally", team="party", max_hp=100, hp=20)
    d = Combatant("d", max_hp=10000)
    b = Combat([c, ally, d], spells, seed=1)
    b.begin_turn(c)
    b.policy.take_turn(b, c)
    assert ally.hp > 20
    assert c.resources_spent == {"slot_1": 1}
    assert any(e["event"] == "cast" and e["spell"] == "Sacred Flame" for e in b.log)
    b.begin_turn(c)
    inst = b.cast(c, "Spirit Guardians")
    ally.hp = ally.max_hp
    b.begin_turn(c)
    b.policy.take_turn(b, c)
    assert inst.active and c.concentration == inst.id


def test_default_policy_declines_shield_on_natural_20_and_impossible_counterspell(spells):
    c = Combatant("c", team="party", spells=["Shield", "Counterspell"], spell_slots={1: 1, 3: 1})
    d = Combatant("d", save_bonuses={"con": 100})
    b = Combat([c, d], spells)
    assert not b.policy.reaction(b, c, spells["Shield"], {"attack": {"natural": 20, "total": 20}})
    assert not b.policy.reaction(b, c, spells["Counterspell"], {"caster": d, "spell": spells["Fireball"]})


def test_default_fanatic_uses_bonus_spell_plus_weapon(spells):
    c = Combatant.from_sheet(load_sheet(ROOT / "monsters" / "cultist_fanatic.yaml"), "c", "enemy")
    d = Combatant("d", team="party", max_hp=1000)
    b = Combat([c, d], spells)
    b.begin_turn(c)
    b.policy.take_turn(b, c)
    assert c.limited_uses["Spiritual Weapon"] == 1
    assert sum(e["event"] == "attack" for e in b.log) == 2
