import pytest

from engine import Combat, Combatant, load_spells
from engine.policy import Policy, NovaPolicy, ConservativePolicy, RationedPolicy, BudgetedPolicy
from engine.state import Effect, SpellInstance


@pytest.fixture(scope="module")
def spells(): return load_spells()


def encounter(spells, policy=None):
    attack = {"name":"Sword","kind":"melee","to_hit":5,"effects":[{"damage":{"dice":"2d6","type":"slashing"}}]}
    pc = Combatant("pc",team="party",attacks=[attack])
    other, grappler = Combatant("a",ac=15), Combatant("z",ac=15)
    combat = Combat([pc,other,grappler],spells,policy=policy)
    combat.monster_instance(grappler,"Grab",[])
    pc.effects.append(Effect("apply_condition",{"condition":"grappled","escape_dc":10,"linked":True,"caster_id":grappler.id},1,"grab"))
    combat.begin_turn(pc)
    return combat,pc,other,grappler


@pytest.mark.parametrize("policy",[Policy,NovaPolicy,ConservativePolicy,RationedPolicy,BudgetedPolicy])
def test_plain_grapple_keeps_action_for_grappler(spells,policy):
    combat,pc,other,grappler = encounter(spells,policy())
    combat.policy.take_turn(combat,pc)
    assert not any(e["event"] == "escape" for e in combat.log)
    assert any(e["event"] == "attack" and e["defender"] == grappler.id for e in combat.log)


@pytest.mark.parametrize("rider",["restrained","poisoned","prone"])
def test_escape_linked_rider(spells,rider):
    combat,pc,other,grappler = encounter(spells)
    pc.effects.append(Effect("apply_condition",{"condition":rider,"linked":True,"caster_id":grappler.id},1,"grab"))
    combat.policy.take_turn(combat,pc)
    assert any(e["event"] == "escape" for e in combat.log)
    assert not any(e["event"] == "attack" and e["attacker"] == pc.id for e in combat.log)


def test_unrelated_rider_does_not_trigger_escape(spells):
    combat,pc,other,grappler = encounter(spells)
    pc.effects.append(Effect("apply_condition",{"condition":"poisoned","linked":True,"caster_id":other.id},2,"other"))
    assert not combat.policy.should_escape(combat,pc)


def test_weapon_target_and_estimate_respect_grapple(spells):
    combat,pc,other,grappler = encounter(spells)
    assert combat.expected_weapon_damage(pc,other) < combat.expected_weapon_damage(pc,grappler)
    assert combat.policy.weapon_target(combat,pc,[other,grappler]) is grappler
    combat.weapon_action(pc)
    assert next(e for e in combat.log if e["event"] == "attack")["defender"] == grappler.id


def test_attack_spell_targets_grappler_and_matches_estimate(spells):
    combat,pc,other,grappler = encounter(spells)
    pc.spells = ["Fire Bolt"]
    spec = combat.cantrip_spec(pc,"Fire Bolt")
    probe = SpellInstance(0,spec,pc,0,0,0)
    block = spec["effects"][0]
    assert combat.policy.targets(combat,probe,block,[other,grappler],1) == [grappler]
    value = combat.expected_spell_damage(pc,spec,other,horizon=1)
    other.immunities = ["fire"]
    assert combat.expected_spell_damage(pc,spec,other,horizon=1) == value
    combat.cast(pc,"Fire Bolt")
    assert next(e for e in combat.log if e["event"] == "attack")["defender"] == grappler.id


@pytest.mark.parametrize("spell",["Sacred Flame","Cure Wounds"])
def test_unaffected_spell_does_not_escape(spells,spell):
    combat,pc,other,grappler = encounter(spells)
    pc.attacks = []
    pc.spells = [spell]
    pc.spell_slots = {1:1}
    pc.hp = 20
    assert not combat.policy.should_escape(combat,pc)


def test_escape_only_when_success_weighted_gain_repays_action(spells):
    combat,pc,other,grappler = encounter(spells)
    grappler.immunities = ["slashing"]
    other.ac = 21
    pc.effects[0].data["escape_dc"] = 1
    assert combat.policy.should_escape(combat,pc)
    pc.effects[0].data["escape_dc"] = 30
    assert not combat.policy.should_escape(combat,pc)


def test_monster_still_escapes_plain_grapple(spells):
    combat,pc,other,grappler = encounter(spells)
    pc.team,grappler.team = "enemy","party"
    combat.policy.take_turn(combat,pc)
    assert any(e["event"] == "escape" for e in combat.log)


def test_advantage_cancels_grapple_disadvantage(spells):
    combat,pc,other,grappler = encounter(spells)
    base = combat.hit_probability(pc,grappler,5)
    assert combat.hit_probability(pc,other,5) == pytest.approx(base**2)
    pc.effects.append(Effect("advantage",{"on":"attack_rolls","scope":"all"},0,"aim"))
    assert combat.hit_probability(pc,other,5) == base


def test_memo_invalidates_when_grapple_ends(spells):
    combat,pc,other,grappler = encounter(spells)
    before = combat.at_will_damage_rate(pc,other)
    pc.effects.clear()
    assert combat.at_will_damage_rate(pc,other) > before


def test_standalone_weapon_option_targets_grappler(spells):
    combat,pc,other,grappler = encounter(spells)
    combat.perform_option(pc,"Sword")
    assert next(e for e in combat.log if e["event"] == "attack")["defender"] == grappler.id


def test_second_grapple_prevents_repaying_escape(spells):
    combat,pc,other,grappler = encounter(spells)
    grappler.immunities = ["slashing"]
    third = Combatant("third",ac=21)
    combat.combatants.append(third)
    other.immunities = ["slashing"]
    combat.monster_instance(other,"Grab",[])
    pc.effects.append(Effect("apply_condition",{"condition":"grappled","escape_dc":1,"linked":True,"caster_id":other.id},2,"grab"))
    pc.effects[0].data["escape_dc"] = 1
    assert not combat.policy.should_escape(combat,pc)


def test_rogue_cannot_estimate_sneak_attack_through_grapple_disadvantage(spells):
    combat,pc,other,grappler = encounter(spells)
    pc.attacks[0]["properties"] = ["finesse"]
    pc.features["sneak_attack"] = "3d6"
    combat.combatants.append(Combatant("ally",team="party",attacks=pc.attacks))
    assert combat.sneak_eligible(pc,grappler,pc.attacks[0])
    assert not combat.sneak_eligible(pc,other,pc.attacks[0])


@pytest.mark.parametrize("status",["engulfed","swallowed"])
def test_escape_dangerous_status(spells,status):
    combat,pc,other,grappler = encounter(spells)
    pc.statuses[status] = {}
    assert combat.policy.should_escape(combat,pc)
