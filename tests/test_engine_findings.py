"""Regression cases for the verified review findings (round 1)."""
from copy import deepcopy

import pytest

from engine import Combat, Combatant, load_spells, load_sheet
from engine.loader import ROOT, Validator, ValidationError
from engine.policy import Policy
from engine.sheets import effect_block, validate_sheet
from engine.state import Effect


@pytest.fixture(scope="module")
def spells():
    return load_spells()


class NoReactions(Policy):
    def reaction(self, *args): return False


def arena(spells, name, seed=1, policy=None):
    caster = Combatant("caster", team="party", max_hp=1000, abilities={"wis": 18},
                       spells=list(spells), spell_slots={i: 10 for i in range(1, 10)},
                       spell_attack_bonus=100, spell_dc=100)
    target = Combatant("target", max_hp=1000, ac=1)
    combat = Combat([caster, target], spells, seed=seed, policy=policy or NoReactions())
    combat.begin_turn(caster)
    return combat, caster, target


@pytest.mark.parametrize("name", ["Shield of Faith", "Bless"])
@pytest.mark.parametrize("ended", ["older", "newer"])
def test_finding1_same_spell_benefits_do_not_stack_and_survive_cleanup(spells, name, ended):
    b, c, target = arena(spells, name)
    other = Combatant("other", team="party", spells=[name], spell_slots={1: 2})
    b.combatants.append(other)
    first = b.cast(c, name, targets=[target])
    b.begin_turn(other)
    second = b.cast(other, name, targets=[target])
    assert first.active and second.active
    assert {e.source for e in target.active_effects} == {second.id}
    if name == "Shield of Faith":
        assert b.armor_class(target) == target.ac + 2
    else:
        assert set(b.modifier(target, "attack_roll") for _ in range(100)) == {1, 2, 3, 4}
        assert set(b.modifier(target, "save") for _ in range(100)) == {1, 2, 3, 4}
    ending, remaining = (first, second) if ended == "older" else (second, first)
    b.end_spell(ending.id)
    assert remaining.active and remaining.caster.concentration == remaining.id
    assert {e.source for e in target.active_effects} == {remaining.id}
    if name == "Shield of Faith": assert b.armor_class(target) == target.ac + 2
    else: assert 1 <= b.modifier(target, "attack_roll") <= 4
    b.end_spell(remaining.id)
    assert b.armor_class(target) == target.ac and b.modifier(target, "attack_roll") == 0


def test_finding1_potency_beats_recency_and_durations_remain_independent(spells):
    b, c, target = arena(spells, "Spirit Guardians")
    target.save_bonuses["wis"] = -100
    other = Combatant("other", team="party", spells=["Spirit Guardians"], spell_slots={3: 1})
    b.combatants.append(other)
    stronger = b.cast(c, "Spirit Guardians", slot=4)
    b.time_rounds = 50
    b.begin_turn(other)
    newer = b.cast(other, "Spirit Guardians", slot=3)
    assert {e.source for e in target.active_effects} == {stronger.id}
    b.begin_turn(target)
    b.end_turn(target)
    assert len([e for e in b.log if e["event"] == "damage" and e["target"] == target.id]) == 1
    # The older, more potent instance expires first, exposing the newer one.
    b.time_rounds = 100
    b.begin_turn(target)
    assert not stronger.active and newer.active
    assert {e.source for e in target.active_effects} == {newer.id}
    before = len([e for e in b.log if e["event"] == "damage"])
    b.end_turn(target)
    assert len([e for e in b.log if e["event"] == "damage"]) == before + 1


def test_finding1_upcasting_target_count_is_not_greater_potency(spells):
    b, c, target = arena(spells, "Bless")
    other = Combatant("other", team="party", spells=["Bless"], spell_slots={1: 1})
    b.combatants.append(other)
    first = b.cast(c, "Bless", slot=4, targets=[target])
    b.begin_turn(other)
    second = b.cast(other, "Bless", targets=[target])
    assert {e.source for e in target.active_effects} == {second.id}
    b.end_spell(second.id)
    assert {e.source for e in target.active_effects} == {first.id}


def test_finding1_instant_damage_does_not_strengthen_lingering_advantage(spells):
    b, c, target = arena(spells, "Guiding Bolt")
    first = b.cast(c, "Guiding Bolt", slot=4, targets=[target])
    other = Combatant("other", team="party", spells=["Guiding Bolt"], spell_slots={1: 1}, spell_attack_bonus=100)
    b.combatants.append(other)
    b.begin_turn(other)
    second = b.cast(other, "Guiding Bolt", targets=[target])
    # Restore the consumed first marker to isolate overlapping lingering benefits.
    effect = Effect("advantage", {"on": "attack_rolls", "scope": "all", "against": "target", "recipient": "any_attacker", "uses": 1}, first.id, "bolt", uses=1)
    target.effects.append(effect)
    b.refresh_spell_effects()
    assert effect.suppressed
    assert {e.source for e in target.active_effects} == {second.id}


@pytest.mark.parametrize("older_bonus,newer_bonus", [(5, 2), (2, 5)])
def test_finding1_most_potent_ac_bonus_applies(spells, older_bonus, newer_bonus):
    specs = deepcopy(spells)
    modifier = specs["Shield of Faith"]["effects"][0]["apply"][0]["modify"]
    modifier["value"] = older_bonus
    b, c, target = arena(specs, "Shield of Faith")
    other = Combatant("other", team="party", spells=["Shield of Faith"], spell_slots={1: 1})
    b.combatants.append(other)
    first = b.cast(c, "Shield of Faith", targets=[target])
    modifier["value"] = newer_bonus
    Validator("fixture").spell(specs["Shield of Faith"])
    b.begin_turn(other)
    second = b.cast(other, "Shield of Faith", targets=[target])
    stronger, weaker = (first, second) if older_bonus > newer_bonus else (second, first)
    assert b.armor_class(target) == target.ac + 5
    b.end_spell(stronger.id)
    assert weaker.active and b.armor_class(target) == target.ac + 2


def test_finding2_concentration_ends_before_counterspell(spells):
    class CheckTiming(Policy):
        def reaction(self, combat, reactor, spell, trigger):
            assert c.concentration is None and not old.active
            return super().reaction(combat, reactor, spell, trigger)

    b, c, target = arena(spells, "Bless", policy=CheckTiming())
    old = b.cast(c, "Bless", targets=[c])
    b.begin_turn(c)
    c.save_bonuses["con"] = -100
    target.spells, target.spell_slots = ["Counterspell"], {3: 1}
    before = c.spell_slots[2]
    assert b.cast(c, "Hold Person", targets=[target]) is None
    assert not old.active and c.concentration is None and not c.effects
    assert c.spell_slots[2] == before and c.action == 0
    assert [e["event"] for e in b.log if e["event"] in {"spell_end", "countered"}][-2:] == ["spell_end", "countered"]


def test_finding2_haste_callback_cannot_establish_new_concentration(spells):
    b, c, target = arena(spells, "Haste")
    haste = b.cast(c, "Haste", targets=[c])
    b.begin_turn(c)
    assert b.cast(c, "Bless", targets=[c]) is None
    assert not haste.active and c.has_condition("incapacitated")
    assert c.concentration is None
    assert not any(i.active and i.spec["name"] == "Bless" for i in b.instances.values())


@pytest.mark.parametrize("name,slot", [("Spiritual Weapon", 9), ("Spiritual Weapon", 1), ("Hold Person", 3)])
def test_finding3_innate_upcast_rejected_before_resources(spells, name, slot):
    fanatic = Combatant.from_sheet(load_sheet(ROOT / "monsters/cultist_fanatic.yaml"), "fanatic", "enemy")
    target = Combatant("target", team="party", max_hp=1000)
    b = Combat([fanatic, target], spells, policy=NoReactions())
    b.begin_turn(fanatic)
    before = deepcopy((fanatic.limited_uses, fanatic.spell_slots, fanatic.resources_spent))
    assert not b.can_cast(fanatic, name, slot=slot)
    assert b.cast(fanatic, name, slot=slot, targets=[target]) is None
    assert (fanatic.limited_uses, fanatic.spell_slots, fanatic.resources_spent) == before
    assert fanatic.action == fanatic.bonus_action == 1 and not b.instances
    permitted = spells[name]["level"]
    assert b.cast(fanatic, name, slot=permitted, targets=[target]).slot == permitted


def test_finding4_self_haste_grants_current_turn_once_and_one_next_turn(spells):
    b, c, target = arena(spells, "Haste", seed=0)
    c.attacks = [{"name": "Blade", "kind": "melee", "to_hit": 100,
                  "effects": [{"damage": {"dice": "1d6", "bonus": 2, "type": "slashing"}}]}]
    c.extra_attack = 2
    inst = b.cast(c, "Haste", targets=[c])
    assert c.action == 0 and len(c.extra_actions) == 1
    extra = c.extra_actions.pop()
    assert extra["attack_limit"] == 1 and "cast" not in extra["restricted_to"]
    assert b.weapon_action(c, granted=extra)
    assert len([e for e in b.log if e["event"] == "attack"]) == 1
    b.refresh_spell_effects()
    b.refresh_areas()
    assert not c.extra_actions
    b.end_turn(c)
    b.begin_turn(c)
    assert len(c.extra_actions) == 1
    b.refresh_spell_effects()
    assert len(c.extra_actions) == 1
    b.end_spell(inst.id)
    assert not c.extra_actions and c.has_condition("incapacitated")


@pytest.mark.parametrize("resistance,vulnerability,expected", [(True, False, 3), (False, True, 12), (True, True, 6)])
def test_finding5_goblin_components_combine_before_mitigation(spells, resistance, vulnerability, expected):
    goblin = Combatant.from_sheet(load_sheet(ROOT / "monsters/goblin_warrior.yaml"), "goblin", "enemy")
    goblin.effects.append(Effect("advantage", {"on": "attack_rolls", "scope": "all", "against": None}, 0, "test"))
    target = Combatant("target", team="party", ac=1,
                       resistances=["slashing"] if resistance else [],
                       vulnerabilities=["slashing"] if vulnerability else [])
    b = Combat([goblin, target], spells, seed=0)
    assert b.weapon_attack(goblin, target, goblin.attacks[0])
    # Seed 0: advantage 13/14, scimitar 1+2, rider 3 => six Slashing.
    assert target.max_hp - target.hp == expected
    assert [e["amount"] for e in b.log if e["event"] == "damage"] == [expected]


@pytest.mark.parametrize("succeeds,expected", [(False, 4), (True, 1)])
def test_finding5_spell_components_one_instance_and_one_concentration_save(spells, succeeds, expected):
    specs = deepcopy(spells)
    block = specs["Sacred Flame"]["effects"][0]
    specs["Sacred Flame"]["scaling"] = None
    block["save"]["on_success"] = "half"
    block["on_fail"] = [{"damage": {"dice": "1d1", "bonus": 2, "type": dtype}} for dtype in ("radiant", "radiant", "fire")]
    Validator("fixture").spell(specs["Sacred Flame"])
    b, c, target = arena(specs, "Sacred Flame")
    target.spells, target.spell_slots = ["Bless"], {1: 1}
    target.resistances = ["radiant", "fire"]
    target.save_bonuses = {"dex": 1000 if succeeds else -100, "con": 100}
    b.begin_turn(target)
    old = b.cast(target, "Bless", targets=[target])
    b.begin_turn(c)
    b.cast(c, "Sacred Flame", targets=[target])
    assert target.max_hp - target.hp == expected  # sum each type, save half, then resistance
    checks = [e for e in b.log if e["event"] == "save" and e["ability"] == "con"]
    assert len(checks) == 1 and old.active


def test_finding5_magic_missile_keeps_per_dart_concentration_checks(spells, monkeypatch):
    b, c, target = arena(spells, "Magic Missile")
    target.spells, target.spell_slots, target.save_bonuses = ["Bless"], {1: 1}, {"con": 100}
    b.begin_turn(target)
    b.cast(target, "Bless", targets=[target])
    b.begin_turn(c)
    target.resistances = ["force"]
    monkeypatch.setattr(b.rng, "randint", lambda low, high: high)
    b.cast(c, "Magic Missile", targets=[target] * 3)
    assert target.max_hp - target.hp == 6  # three separate floor((4+1)/2) darts
    assert len([e for e in b.log if e["event"] == "damage"]) == 3
    assert len([e for e in b.log if e["event"] == "save" and e["ability"] == "con"]) == 3


@pytest.mark.parametrize("guard", ["false", "attack.natural == 1", "target.hp < 0"])
def test_finding6_weapon_guard_false_suppresses_damage(spells, guard):
    sheet = load_sheet(ROOT / "monsters/ogre.yaml")
    sheet["attacks"][0]["effects"][0]["if"] = guard
    validate_sheet(sheet, "fixture")
    ogre = Combatant.from_sheet(sheet, "ogre", "enemy")
    target = Combatant("target", team="party", ac=1)
    b = Combat([ogre, target], spells, seed=1)
    assert b.weapon_attack(ogre, target, ogre.attacks[0])
    assert target.hp == target.max_hp and not any(e["event"] == "damage" for e in b.log)


@pytest.mark.parametrize("path", ["block", "primitive"])
@pytest.mark.parametrize("name,branch", [("Fire Bolt", "on_hit"), ("Sacred Flame", "on_fail"), ("Bless", "apply")])
def test_finding6_spell_guard_false_suppresses_each_path(spells, path, name, branch):
    specs = deepcopy(spells)
    block = specs[name]["effects"][0]
    for declaration in ([block] if path == "block" else block[branch]):
        declaration["if"] = "false"
    Validator("fixture").spell(specs[name])
    b, c, target = arena(specs, name)
    target.save_bonuses["dex"] = -100
    b.cast(c, name, targets=[target])
    assert target.hp == target.max_hp and not target.effects
    if path == "block": assert not any(e["event"] in {"attack", "save"} for e in b.log)


@pytest.mark.parametrize("path", ["block", "primitive"])
def test_finding6_continuous_area_guard_false_suppresses_effect(spells, path):
    specs = deepcopy(spells)
    block = next(b for b in specs["Spirit Guardians"]["effects"] if b["id"] == "slowing")
    (block if path == "block" else block["apply"][0])["if"] = "false"
    Validator("fixture").spell(specs["Spirit Guardians"])
    b, c, target = arena(specs, "Spirit Guardians")
    b.cast(c, "Spirit Guardians")
    b.refresh_areas()
    assert not target.effects and b.modifier(target, "speed", target.speed) == target.speed


def test_finding6_continuous_guard_rechecked_and_context_has_target(spells):
    specs = deepcopy(spells)
    block = next(b for b in specs["Spirit Guardians"]["effects"] if b["id"] == "slowing")
    block["if"] = "target.hp == target.max_hp and event == while_in_area"
    Validator("fixture").spell(specs["Spirit Guardians"])
    b, c, target = arena(specs, "Spirit Guardians")
    b.cast(c, "Spirit Guardians")
    assert b.modifier(target, "speed", 30) == 15
    target.hp -= 1
    b.refresh_areas()
    assert b.modifier(target, "speed", 30) == 30


def test_finding6_guarded_off_area_does_not_suppress_existing_spell(spells):
    specs = deepcopy(spells)
    b, c, target = arena(specs, "Spirit Guardians")
    first = b.cast(c, "Spirit Guardians")
    other = Combatant("other", team="party", spells=["Spirit Guardians"], spell_slots={3: 1})
    b.combatants.append(other)
    for block in specs["Spirit Guardians"]["effects"]: block["if"] = "false"
    Validator("fixture").spell(specs["Spirit Guardians"])
    b.begin_turn(other)
    second = b.cast(other, "Spirit Guardians")
    assert first.active and second.active
    assert {e.source for e in target.active_effects} == {first.id}
    b.begin_turn(target)
    b.end_turn(target)
    assert len([e for e in b.log if e["event"] == "damage" and e["target"] == target.id]) == 1


@pytest.mark.parametrize("path", ["block", "primitive"])
@pytest.mark.parametrize("kind", ["actions", "traits"])
def test_finding6_action_trait_guard_false_suppresses_damage(spells, kind, path):
    sheet = load_sheet(ROOT / "monsters/ogre.yaml")
    block = effect_block("guarded", apply=[{"damage": {"dice": "1d6", "bonus": 0, "type": "force"}}])
    (block if path == "block" else block["apply"][0])["if"] = "false"
    sheet[kind] = [{"name": "Guarded", "cost": "action", "effects": [block]}]
    validate_sheet(sheet, "fixture")
    actor = Combatant.from_sheet(sheet, "actor", "party")
    b = Combat([actor], spells)
    b.begin_turn(actor)
    assert b.use_action(actor, "Guarded")
    assert actor.hp == actor.max_hp and not any(e["event"] == "damage" for e in b.log)


def test_finding6_grants_action_rejects_unexecuted_guarded_effects():
    sheet = load_sheet(ROOT / "characters/fighter5.yaml")
    surge = next(a for a in sheet["actions"] if a.get("grants_action"))
    surge["effects"] = [effect_block("ignored", apply=[{"temp_hp": {"amount": 10}, "if": "false"}])]
    with pytest.raises(ValidationError, match="effects must be empty"):
        validate_sheet(sheet, "fixture")


def test_finding6_spell_success_and_end_callback_guards_false(spells):
    specs = deepcopy(spells)
    specs["Sacred Flame"]["effects"][0]["on_success"] = [{"temp_hp": {"amount": 10}, "if": "false"}]
    haste_apply = specs["Haste"]["effects"][0]["apply"]
    for p in next(p["on_spell_end"] for p in haste_apply if "on_spell_end" in p): p["if"] = "false"
    for name in ("Sacred Flame", "Haste"): Validator("fixture").spell(specs[name])
    b, c, target = arena(specs, "Sacred Flame")
    target.save_bonuses["dex"] = 1000
    b.cast(c, "Sacred Flame", targets=[target])
    assert target.temp_hp == 0
    b.begin_turn(c)
    inst = b.cast(c, "Haste", targets=[target])
    b.end_spell(inst.id)
    assert not target.effects and not target.has_condition("incapacitated")


def test_finding6_spell_attack_guard_receives_full_attack_context(spells):
    specs = deepcopy(spells)
    specs["Fire Bolt"]["effects"][0]["on_hit"][0]["if"] = "attacker == caster and defender == target and attack.natural == 5"
    Validator("fixture").spell(specs["Fire Bolt"])
    b, c, target = arena(specs, "Fire Bolt", seed=1)
    b.cast(c, "Fire Bolt", targets=[target])
    assert target.hp < target.max_hp


@pytest.mark.parametrize("natural", [1, 20])
@pytest.mark.parametrize("name,level,slot,attacks,count,sides", [
    ("Fire Bolt", 1, 0, 1, 1, 10), ("Fire Bolt", 5, 0, 1, 2, 10),
    ("Fire Bolt", 11, 0, 1, 3, 10), ("Fire Bolt", 17, 0, 1, 4, 10),
    ("Eldritch Blast", 5, 0, 2, 1, 10), ("Scorching Ray", 1, 2, 3, 2, 6),
    ("Scorching Ray", 1, 4, 5, 2, 6), ("Guiding Bolt", 1, 1, 1, 4, 6),
])
def test_finding8_cast_nat1_nat20_exact_dice(spells, natural, name, level, slot, attacks, count, sides):
    class MaximumDice:
        def __init__(self): self.calls = []
        def randint(self, low, high):
            self.calls.append((low, high))
            return natural if high == 20 else high

    specs = deepcopy(spells)
    # A flat spellcasting modifier must not double on a critical.
    specs[name]["effects"][0]["on_hit"][0]["damage"]["bonus"] = "spell_mod"
    Validator("fixture").spell(specs[name])
    b, c, target = arena(specs, name)
    c.level = level
    target.ac = 1000 if natural == 20 else 1
    b.rng = MaximumDice()
    b.cast(c, name, slot=slot, targets=[target] * attacks)
    rolls = [e for e in b.log if e["event"] == "attack"]
    assert len(rolls) == attacks
    assert all(e["natural"] == natural and e["hit"] == (natural == 20) for e in rolls)
    expected = attacks * (count * 2 * sides + c.spell_mod) if natural == 20 else 0
    assert target.max_hp - target.hp == expected
    assert b.rng.calls.count((1, sides)) == (attacks * count * 2 if natural == 20 else 0)
    assert b.rng.calls.count((1, 20)) == attacks


@pytest.mark.parametrize("name,slot,attacks", [("Fire Bolt", 0, 1), ("Eldritch Blast", 0, 2), ("Scorching Ray", 2, 3), ("Guiding Bolt", 1, 1)])
def test_finding8_cast_hit_rate_against_realistic_ac(spells, name, slot, attacks):
    hits = crits = total = 0
    for seed in range(800):
        b, c, target = arena(spells, name, seed=seed)
        c.level, c.spell_attack_bonus, target.ac = 5, 7, 16
        b.cast(c, name, slot=slot, targets=[target] * attacks)
        rolls = [e for e in b.log if e["event"] == "attack"]
        hits += sum(e["hit"] for e in rolls)
        crits += sum(e["critical"] for e in rolls)
        total += len(rolls)
    assert total == 800 * attacks
    assert hits / total == pytest.approx(.60, abs=.04)
    assert crits / total == pytest.approx(.05, abs=.025)


def test_finding8_missing_critical_dice_mutation_is_detected(spells, monkeypatch):
    from engine import dice
    original = dice.roll
    monkeypatch.setattr(dice, "roll", lambda rng, value, critical=False: original(rng, value, critical=False))
    with pytest.raises(AssertionError):
        test_finding8_cast_nat1_nat20_exact_dice(spells, 20, "Guiding Bolt", 1, 1, 1, 4, 6)
