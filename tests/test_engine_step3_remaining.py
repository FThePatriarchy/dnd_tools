"""Focused regressions for the remaining spell batches."""
import pytest
from engine.loader import scaled_spell
from engine.state import Effect
from test_engine_step3 import arena, spell_specs


def test_step3_preparation_is_not_a_free_in_combat_action():
    b, c, ds = arena("Leomund's Tiny Hut")
    assert not b.can_cast(c, "Leomund's Tiny Hut")
    with pytest.raises(ValueError): b.prepare(c, "Leomund's Tiny Hut")
    b.current = None
    inst = b.prepare(c, "Leomund's Tiny Hut")
    assert inst and inst.cast_round == b.time_rounds == 10
    assert c.spell_slots[3] == 99
    assert c.spell_costs == {} and b.current is None
    assert not b.can_cast(c, "Leomund's Tiny Hut")


def test_step3_guidance_is_skill_not_ability_wide_and_enhance_can_differ():
    b, c, (d, *_) = arena("Guidance")
    b.cast(c, "Guidance", [d], choices={"skill": "athletics"})
    assert b.modifier(d, "ability_check", 0, ("str", "athletics")) in range(1, 5)
    assert b.modifier(d, "ability_check", 0, ("str", "other")) == 0
    assert b.modifier(d, "save", 0, "str") == 0
    b, c, (a, d, *_) = arena("Enhance Ability")
    b.cast(c, "Enhance Ability", [a, d], slot=3, choices={"ability": {a.id: "str", d.id: "dex"}})
    assert b.roll_flags(a, "ability_checks", "str") == (True, False)
    assert b.roll_flags(a, "ability_checks", "dex") == (False, False)
    assert b.roll_flags(d, "ability_checks", "dex") == (True, False)


def test_step3_defenses_heroism_freedom_and_repeated_temp_hp():
    b, c, (d, *_) = arena("Heroism")
    inst = b.cast(c, "Heroism", [d])
    assert b.condition_immune(d, "frightened")
    assert d.temp_hp == 0
    b.begin_turn(d); assert d.temp_hp == 4
    b.damage(d, 1, "fire"); assert d.temp_hp == 3
    b.begin_turn(d); assert d.temp_hp == 4
    b.end_spell(inst.id); assert not b.condition_immune(d, "frightened")
    b, c, (d, *_) = arena("Freedom of Movement")
    old = Effect("apply_condition", {"condition": "paralyzed", "magical": True}, 0, "old")
    d.effects.append(old)
    inst = b.cast(c, "Freedom of Movement", [d])
    assert not d.has_condition("paralyzed")
    assert b.condition_immune(d, "restrained", magical=True)
    assert not b.condition_immune(d, "restrained", magical=False)
    b.end_spell(inst.id); assert d.has_condition("paralyzed")


def test_step3_aura_life_zero_hp_ally_and_maximum_healing():
    b, c, (d, *_) = arena("Aura of Life")
    assert d.hp == 0
    b.cast(c, "Aura of Life")
    b.begin_turn(d)
    assert d.hp == 1 and not d.has_condition("unconscious")
    assert c.has_status("max_hp_protected")
    b, c, (d, *_) = arena("Beacon of Hope")
    b.cast(c, "Beacon of Hope", [d])
    d.hp -= 100; hp = d.hp
    b.begin_turn(c); c.spells.append("Cure Wounds")
    b.cast(c, "Cure Wounds", [d])
    assert d.hp - hp == 20


def test_step3_faerie_visibility_see_invisible_and_gas_restrictions():
    b, c, (d, *_) = arena("Faerie Fire")
    d.conditions.add("invisible")
    inst = b.cast(c, "Faerie Fire")
    assert not d.has_condition("invisible")
    assert b.roll_flags(c, "attack_rolls", against=d) == (True, False)
    c.conditions.add("blinded")
    assert b.roll_flags(c, "attack_rolls", against=d) == (False, False)
    b.end_spell(inst.id); assert d.has_condition("invisible")
    b, c, (d, *_) = arena("See Invisibility")
    d.conditions.add("invisible"); assert not d.visible_to(c)
    b.cast(c, "See Invisibility"); assert d.visible_to(c)
    b, c, (d, *_) = arena("Gaseous Form")
    b.cast(c, "Gaseous Form", [d]); b.begin_turn(d)
    d.spells = ["Fire Bolt"]
    assert not b.can_cast(d, "Fire Bolt")
    assert not b.attack(d, c, 100, lambda *args: None)
    assert b.condition_immune(d, "prone")
    assert b.damage(d, 10, "slashing") == 5
    assert b.modifier(d, "fly_speed", 0) == 10


def test_step3_restoration_and_spare_dying_do_not_invent_hp():
    b, c, (d, *_) = arena("Greater Restoration")
    d.exhaustion_level = 3
    b.cast(c, "Greater Restoration", [d], choices={"kind": "exhaustion"})
    assert d.exhaustion_level == 2
    b.begin_turn(c); d.max_hp -= 100
    b.cast(c, "Greater Restoration", [d], choices={"kind": "max_hp"})
    assert d.max_hp == d.original_max_hp
    b, c, (d, *_) = arena("Spare the Dying")
    b.cast(c, "Spare the Dying", [d])
    assert d.hp == 0 and d.has_status("stable")
    b.damage(d, 1, "fire"); assert not d.has_status("stable")
    for level, feet in [(1, 15), (5, 30), (11, 60), (17, 120)]:
        assert scaled_spell(spell_specs()["Spare the Dying"], 0, level)["range"]["feet"] == feet
