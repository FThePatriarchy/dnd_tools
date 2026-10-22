from statistics import mean
import random

import pytest

from engine import Combat, Combatant, load_spells
from engine.policy import Policy
from engine.state import Effect


@pytest.fixture(scope="module")
def spells(): return load_spells()


class NoReactions(Policy):
    def reaction(self, *args): return False


class AlwaysReactions(Policy):
    def reaction(self, *args): return True


def arena(spells, seed=1, name=None, level=1, enemies=1, policy=None, area=None):
    caster = Combatant("caster", team="party", max_hp=10000, ac=15,
                       abilities={"wis": 18}, level=level, spell_dc=15,
                       spell_attack_bonus=100, spells=[name] if name else list(spells),
                       spell_slots={i: 100 for i in range(1, 10)})
    dummies = [Combatant(f"dummy_{i}", max_hp=10000) for i in range(enemies)]
    combat = Combat([caster, *dummies], spells, seed, policy=policy or NoReactions(), area=area)
    combat.begin_turn(caster)
    return combat, caster, dummies


@pytest.mark.parametrize("name,slot,expected,dice_count", [
    ("Fireball", 3, 28, 8), ("Fireball", 5, 35, 10),
    ("Sacred Flame", 0, 4.5, 1), ("Sacred Flame", 0, 9, 2),
])
def test_save_damage_statistics(spells, name, slot, expected, dice_count):
    fail, success = [], []
    level = 5 if name == "Sacred Flame" and dice_count == 2 else 1
    for seed in range(800):
        for succeeds, samples in ((False, fail), (True, success)):
            b, c, (d,) = arena(spells, seed, name, level=level)
            d.save_bonuses["dex"] = 100 if succeeds else -100
            b.cast(c, name, slot=slot, targets=None if name == "Fireball" else [d])
            samples.append(d.max_hp - d.hp)
    assert mean(fail) == pytest.approx(expected, abs=.45)
    assert mean(success) == pytest.approx(expected / 2 - .25 if name == "Fireball" else 0, abs=.4)


@pytest.mark.parametrize("name,level,slot,expected,attacks", [
    ("Fire Bolt", 1, 0, 5.5, 1), ("Fire Bolt", 5, 0, 11, 1),
    ("Fire Bolt", 11, 0, 16.5, 1), ("Fire Bolt", 17, 0, 22, 1),
    ("Eldritch Blast", 5, 0, 11, 2), ("Scorching Ray", 1, 2, 21, 3),
    ("Scorching Ray", 1, 4, 35, 5), ("Guiding Bolt", 1, 1, 14, 1),
])
def test_attack_spell_statistics_and_independent_rolls(spells, name, level, slot, expected, attacks):
    samples = []
    for seed in range(600):
        b, c, (d,) = arena(spells, seed, name, level=level)
        b.cast(c, name, slot=slot, targets=[d] * attacks)
        samples.append(d.max_hp - d.hp)
        assert sum(e["event"] == "attack" for e in b.log) == attacks
    # At effectively guaranteed hit: 90% normal + 5% crit + 5% miss.
    assert mean(samples) == pytest.approx(expected, abs=max(.8, expected * .06))


def test_magic_missile_auto_hits_shared_roll_and_upcasting(spells):
    values = []
    for seed in range(600):
        b, c, (d,) = arena(spells, seed, "Magic Missile")
        d.ac = 1000
        b.cast(c, "Magic Missile", targets=[d] * 3)
        damage = [e["amount"] for e in b.log if e["event"] == "damage"]
        assert len(damage) == 3 and len(set(damage)) == 1
        assert not any(e["event"] in {"attack", "save"} for e in b.log)
        values.append(d.max_hp - d.hp)
    assert mean(values) == pytest.approx(10.5, abs=.4)
    b, c, (d,) = arena(spells, name="Magic Missile")
    b.cast(c, "Magic Missile", slot=3, targets=[d] * 5)
    assert sum(e["event"] == "damage" for e in b.log) == 5


@pytest.mark.parametrize("name,expected,slot", [("Cure Wounds", 13, 1), ("Cure Wounds", 31, 3), ("Healing Word", 9, 1), ("Healing Word", 19, 3)])
def test_healing_statistics_and_cap(spells, name, expected, slot):
    values = []
    for seed in range(600):
        b, c, (d,) = arena(spells, seed, name)
        c.hp = 1
        b.cast(c, name, targets=[c], slot=slot)
        values.append(c.hp - 1)
    assert mean(values) == pytest.approx(expected, abs=.65)
    b, c, _ = arena(spells, name=name)
    c.hp -= 1
    b.cast(c, name, targets=[c])
    assert c.hp == c.max_hp


def test_bless_rolls_fresh_d4_and_no_check_modifier(spells):
    b, c, (d,) = arena(spells, name="Bless")
    b.cast(c, "Bless", targets=[c, d])
    values = [b.modifier(c, "attack_roll") for _ in range(2000)]
    assert set(values) == {1, 2, 3, 4}
    assert mean(values) == pytest.approx(2.5, abs=.1)
    assert b.modifier(d, "save") in {1, 2, 3, 4}
    assert b.modifier(c, "ability_check") == 0


def test_hold_person_repeat_saves_are_per_target(spells):
    b, c, (a, d) = arena(spells, name="Hold Person", enemies=2)
    a.save_bonuses["wis"] = d.save_bonuses["wis"] = -100
    inst = b.cast(c, "Hold Person", slot=3, targets=[a, d])
    assert a.has_condition("paralyzed") and d.has_condition("paralyzed")
    assert not b.saving_throw(a, "str", -1000)
    assert not b.saving_throw(a, "dex", -1000)
    a.save_bonuses["wis"] = 100
    b.begin_turn(a)
    assert not b.weapon_action(a)
    b.end_turn(a)
    assert not a.has_condition("paralyzed") and d.has_condition("paralyzed")
    assert inst.active and c.concentration == inst.id
    b.end_spell(inst.id)
    assert not d.has_condition("paralyzed")


@pytest.mark.parametrize("name,status", [("Hex", "hexed"), ("Hunter's Mark", "hunters_marked")])
def test_marks_only_trigger_on_bound_target_and_rebind(spells, name, status):
    b, c, (a, d) = arena(spells, seed=4, name=name, enemies=2)
    inst = b.cast(c, name, targets=[a], choices={"ability": "str"})
    assert a.has_status(status) and not d.has_status(status)
    before = d.hp
    b.dispatch("on_attack_hit", attacker=c, defender=d, critical=False)
    assert d.hp == before
    before = a.hp
    b.dispatch("on_attack_hit", attacker=c, defender=a, critical=False)
    assert 1 <= before - a.hp <= 6
    b.damage(a, a.hp, "force", c)
    assert inst.bindings["mark"].target_dropped_to_zero
    # The death history is latched even if the creature is subsequently healed.
    b.heal(a, 10)
    c.bonus_action = 1
    transferred = b.command(inst, targets=[d])
    assert transferred == (name == "Hunter's Mark")
    if name == "Hex":
        b.begin_turn(c)
        assert b.command(inst, targets=[d])
    assert not a.has_status(status) and d.has_status(status)
    assert inst.cast_turn == 1
    assert not inst.bindings["mark"].target_dropped_to_zero
    if name == "Hex":
        assert not b.roll_flags(a, "ability_checks", "str")[1]
        assert b.roll_flags(d, "ability_checks", "str")[1]
        assert not b.roll_flags(d, "saves", "str")[1]


def test_confirmed_hit_extra_damage_crit_dice_and_single_concentration_check(spells):
    seed = next(s for s in range(100) if random.Random(s).randint(1, 20) == 20)
    b, c, (d,) = arena(spells, seed, "Hex")
    d.spells, d.spell_slots, d.save_bonuses = ["Bless"], {1: 1}, {"con": 100}
    b.begin_turn(d)
    b.cast(d, "Bless", targets=[d])
    b.begin_turn(c)
    b.cast(c, "Hex", targets=[d])
    assert b.attack(c, d, 100, lambda crit, roll: b.damage(d, 1, "slashing", c))
    damage = [x for x in b.log if x["event"] == "damage"]
    oracle = random.Random(seed)
    oracle.randint(1, 20)
    assert len(damage) == 2 and damage[-1]["amount"] == sum(oracle.randint(1, 6) for _ in range(2))
    assert sum(x["event"] == "attack" for x in b.log) == 1
    assert sum(x["event"] == "save" for x in b.log) == 1


def test_spirit_guardians_end_turn_only_limit_and_membership(spells):
    b, c, (a, d) = arena(spells, name="Spirit Guardians", enemies=2)
    a.save_bonuses["wis"] = d.save_bonuses["wis"] = -100
    inst = b.cast(c, "Spirit Guardians")
    assert inst.choices["spirit_damage"] == "radiant"
    assert a.hp == a.max_hp and d.hp == d.max_hp
    assert any(e.kind == "modify" and e.data["stat"] == "speed" for e in a.effects)
    b.begin_turn(a)
    assert a.hp == a.max_hp
    b.dispatch("on_creature_enters_aura", who=a)
    assert a.hp == a.max_hp  # movement events deliberately never fire
    b.dispatch("end_of_turn_in_aura", who=a)
    first = a.hp
    b.dispatch("end_of_turn_in_aura", who=a)
    b.end_turn(a)
    assert first < a.max_hp and a.hp == first and d.hp == d.max_hp
    b.begin_turn(d)
    b.dispatch("end_of_turn_in_aura", who=a)
    assert a.hp < first  # limit is per any creature's turn, not a round
    b.end_turn(d)
    assert d.hp < d.max_hp
    assert c.hp == c.max_hp


def test_guardians_alignment_and_frozen_exemptions(spells):
    b, c, (d,) = arena(spells, name="Spirit Guardians")
    c.alignment = "evil"
    with pytest.raises(ValueError, match="illegal choice"):
        b.cast(c, "Spirit Guardians", choices={"spirit_damage": "radiant"})
    assert c.action == 1 and c.spell_slots[3] == 100 and c.concentration is None
    b, c, (d,) = arena(spells, name="Spirit Guardians")
    c.alignment = "evil"
    inst = b.cast(c, "Spirit Guardians")
    assert inst.choices["spirit_damage"] == "necrotic"
    assert c.id in inst.exclusions and d.id not in inst.exclusions


def test_shield_provisional_hit_and_next_turn_expiry(spells):
    b, c, (d,) = arena(spells, name="Shield", policy=Policy())
    c.spell_attack_bonus = 5
    d.spells = ["Shield"]
    d.spell_slots = {1: 3}
    d.ac = 15
    # Seed 1 yields a 5: total 15 provisionally hits AC 15, but not Shield AC 20.
    hit = b.attack(c, d, 10, lambda crit, roll: b.damage(d, 20, "force", c))
    assert not hit and d.hp == d.max_hp and b.armor_class(d) == 20
    assert d.reaction == 0 and d.spell_slots[1] == 2
    assert not any(e["event"] == "damage" for e in b.log)
    b.begin_turn(d)
    assert b.armor_class(d) == 15 and not d.has_status("shielded")


def test_shield_blocks_entire_magic_missile_volley(spells):
    b, c, (d,) = arena(spells, name="Magic Missile", policy=Policy())
    d.spells = ["Shield"]
    d.spell_slots = {1: 2}
    b.cast(c, "Magic Missile", targets=[d] * 3)
    assert d.hp == d.max_hp and d.has_status("shielded")
    b.damage(d, 5, "force", c)
    assert d.hp == d.max_hp - 5  # not a general force immunity


def test_counterspell_con_save_stops_pending_spell_without_slot_expense(spells):
    b, c, (d,) = arena(spells, name="Fireball", policy=Policy())
    c.save_bonuses["con"] = -100
    d.spells = ["Counterspell"]
    d.spell_slots = {3: 1}
    before = c.spell_slots[3]
    result = b.cast(c, "Fireball")
    assert result is None and c.action == 0 and c.spell_slots[3] == before
    assert d.spell_slots[3] == 0 and d.reaction == 0
    assert d.hp == d.max_hp
    assert any(e["event"] == "countered" for e in b.log)


def test_counterspell_successful_save_and_visibility(spells):
    for visible in (True, False):
        b, c, (d,) = arena(spells, name="Fireball", policy=AlwaysReactions())
        c.visible = visible
        c.save_bonuses["con"] = 100
        d.spells, d.spell_slots = ["Counterspell"], {3: 1}
        assert b.cast(c, "Fireball") is not None
        assert d.spell_slots[3] == (0 if visible else 1)


def test_haste_granted_attack_and_detached_lethargy(spells):
    b, c, (d,) = arena(spells, name="Haste")
    inst = b.cast(c, "Haste", targets=[d])
    assert b.armor_class(d) == d.ac + 2 and b.roll_flags(d, "saves", "dex")[0]
    b.begin_turn(d)
    assert len(d.extra_actions) == 1 and d.extra_actions[0]["attack_limit"] == 1
    b.end_spell(inst.id)
    assert b.armor_class(d) == d.ac and d.has_condition("incapacitated")
    b.end_turn(d)
    assert d.has_condition("incapacitated")
    b.begin_turn(d)
    b.end_turn(d)
    assert not d.has_condition("incapacitated")


def test_shield_of_faith_concentration_damage_cap_and_temp_hp(spells):
    b, c, (d,) = arena(spells, name="Shield of Faith")
    inst = b.cast(c, "Shield of Faith", targets=[d])
    assert b.armor_class(d) == d.ac + 2
    c.save_bonuses["con"] = -100
    c.temp_hp = 200
    b.damage(c, 100, "fire", d)
    assert c.hp == c.max_hp and c.temp_hp == 100
    saves = [x for x in b.log if x["event"] == "save"]
    assert saves[-1]["dc"] == 30
    assert not inst.active and c.concentration is None and b.armor_class(d) == d.ac


def test_spiritual_weapon_scaling_commands_and_no_refresh(spells):
    b, c, (d,) = arena(spells, name="Spiritual Weapon")
    inst = b.cast(c, "Spiritual Weapon", slot=4, targets=[d])
    assert inst.spec["effects"][0]["on_hit"][0]["damage"]["dice"] == "3d8"
    c.bonus_action = 1
    assert not b.command(inst, targets=[d])  # later turn only
    b.begin_turn(c)
    assert b.command(inst, targets=[d])
    assert c.bonus_action == 0 and not b.command(inst)
    assert inst.cast_turn == 1 and inst.cast_round == 0
    assert sum(x["event"] == "attack" for x in b.log) == 2


@pytest.mark.parametrize("creature_type,full,returns", [("fey", False, True), ("fey", True, False), ("humanoid", True, True)])
def test_banishment_conditional_return_and_cleanup(spells, creature_type, full, returns):
    b, c, (d,) = arena(spells, name="Banishment")
    d.creature_type = creature_type
    d.save_bonuses["cha"] = -100
    inst = b.cast(c, "Banishment", targets=[d])
    assert d.removed and d.has_condition("incapacitated") and not d.alive
    b.time_rounds = 10 if full else 5
    b.end_spell(inst.id)
    assert not d.removed and d.permanently_removed != returns
    assert not d.has_condition("incapacitated")


def test_guiding_bolt_incoming_advantage_consumed_even_on_miss(spells):
    b, c, (d,) = arena(spells, seed=1, name="Guiding Bolt")
    b.cast(c, "Guiding Bolt", targets=[d])
    assert any(e.kind == "advantage" for e in d.effects)
    c.effects.append(Effect("disadvantage", {"on": "attack_rolls", "scope": "all", "against": None}, 0, "test"))
    assert not b.attack(c, d, -100, lambda *args: None)
    assert not any(e.kind == "advantage" for e in d.effects)
    # The recipient did not gain advantage on its own attacks.
    assert not b.roll_flags(d, "attack_rolls")[0]


def test_same_named_statuses_remain_source_scoped(spells):
    b, c, (a, d) = arena(spells, name="Hex", enemies=2)
    other = Combatant("other", team="party", spells=["Hex"], spell_slots={1: 1})
    b.combatants.append(other)
    first = b.cast(c, "Hex", targets=[a])
    b.begin_turn(other)
    second = b.cast(other, "Hex", targets=[a])
    b.end_spell(first.id)
    assert a.has_status("hexed") and second.active
    b.end_spell(second.id)
    assert not a.has_status("hexed")


def test_legal_target_filters_distinctness_and_optional_counts(spells):
    b, c, (a, d) = arena(spells, name="Hold Person", enemies=2)
    d.creature_type = "fey"
    with pytest.raises(ValueError, match="illegal target"):
        b.cast(c, "Hold Person", targets=[d])
    assert c.action == 1 and c.spell_slots[2] == 100
    b, c, (d,) = arena(spells, name="Bless")
    inst = b.cast(c, "Bless", targets=[])
    assert inst.active and not c.effects and not d.effects  # up_to includes declining
    b, c, (d,) = arena(spells, name="Bless")
    with pytest.raises(ValueError, match="distinctness"):
        b.cast(c, "Bless", targets=[d, d])


def test_repeated_successful_aura_save_consumes_limit(spells):
    b, c, (d,) = arena(spells, name="Spirit Guardians")
    d.save_bonuses["wis"] = 100
    b.cast(c, "Spirit Guardians")
    b.begin_turn(d)
    b.dispatch("end_of_turn_in_aura", who=d)
    b.dispatch("end_of_turn_in_aura", who=d)
    assert len([e for e in b.log if e["event"] == "save" and e["target"] == d.id]) == 1


def test_haste_end_callback_runs_once(spells):
    b, c, (d,) = arena(spells, name="Haste")
    inst = b.cast(c, "Haste", targets=[d])
    b.end_spell(inst.id)
    after = list(d.effects)
    b.end_spell(inst.id)
    assert d.effects == after and len(after) == 2


def test_optional_spiritual_weapon_attack_does_not_prevent_creation(spells):
    class DeclineInitial(NoReactions):
        def optional(self, combat, instance, block):
            return combat.turn_index > instance.cast_turn
    b, c, (d,) = arena(spells, name="Spiritual Weapon", policy=DeclineInitial())
    inst = b.cast(c, "Spiritual Weapon")
    assert inst.active and c.concentration == inst.id
    assert not any(e["event"] == "attack" for e in b.log)
    b.begin_turn(c)
    assert b.command(inst)
    assert any(e["event"] == "attack" for e in b.log)


def test_full_minute_banishment_with_fractional_round_clock(spells):
    b, c, (a, d) = arena(spells, name="Banishment", enemies=2)
    d.creature_type, d.save_bonuses = "fey", {"cha": -100}
    inst = b.cast(c, "Banishment", targets=[d])
    for _ in range(10):
        for actor in (c, a, d):
            b.begin_turn(actor)
            b.end_turn(actor)
    b.begin_turn(c)
    assert not inst.active and d.permanently_removed
