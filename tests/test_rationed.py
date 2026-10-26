"""Rationed strategy: daily slot budget, short-rest features and Hit Dice shares."""
import math

import pytest

from engine import Combat, Combatant
from engine.day import run_day
from engine.day_options import DayOptions
from engine.loader import ROOT, load_sheet, load_spells
from engine.policy import STRATEGIES, RationedPolicy

SPELL = {"name": "Test Bolt", "level": 1}


def setup(slots, start=None, remaining=3, enemy_hp=500):
    caster = Combatant("caster", team="party", max_hp=40, spell_slots=dict(slots), max_spell_slots=dict(slots))
    foe = Combatant("foe", team="enemy", max_hp=enemy_hp)
    combat = Combat([caster, foe], load_spells(), seed=1)
    combat.encounters_remaining = remaining
    combat.slots_at_start = {"caster": dict(start or slots)}
    return combat, caster, foe


def test_registered():
    assert STRATEGIES["rationed"] is RationedPolicy


def test_budget_is_an_equal_share_of_slot_levels_per_encounter():
    p = RationedPolicy()
    combat, caster, _ = setup({1: 4, 2: 3, 3: 2})            # 4 + 6 + 6 = 16 slot levels
    assert p.within_budget(combat, caster, 3)                # share ceil(16 / 3) = 6
    caster.spell_slots = {1: 4, 2: 3, 3: 1}                  # spent 3 this encounter
    assert p.within_budget(combat, caster, 3) and not p.within_budget(combat, caster, 4)
    combat.encounters_remaining = 1                          # last encounter: everything is available
    caster.spell_slots = {1: 0, 2: 0, 3: 1}
    assert p.within_budget(combat, caster, 3)


def test_allow_spell_cantrips_emergency_and_won_fights(monkeypatch):
    p = RationedPolicy()
    combat, caster, foe = setup({1: 2}, remaining=6)
    assert p.allow_spell(combat, caster, {"name": "Fire Bolt", "level": 0})
    monkeypatch.setattr(p, "within_budget", lambda *a: False)
    monkeypatch.setattr(p, "needs_resources", lambda *a: False)
    assert not p.allow_spell(combat, caster, SPELL)          # over budget, no need
    caster.hp = 5                                            # below 25%: emergency frees slots
    assert p.allow_spell(combat, caster, SPELL)
    caster.hp = caster.max_hp
    monkeypatch.setattr(p, "within_budget", lambda *a: True)
    monkeypatch.setattr(combat, "at_will_damage_rate", lambda actor, target: 5)
    foe.hp = 5                                               # at-will damage already covers the enemy
    assert not p.allow_spell(combat, caster, SPELL)


def test_incapacitated_allies_deal_no_forecast_damage(monkeypatch):
    p = RationedPolicy()
    combat, caster, foe = setup({1: 2}, remaining=6)
    monkeypatch.setattr(combat, "at_will_damage_rate", lambda actor, target: 5)
    foe.hp = 5
    assert p.already_won(combat, caster)
    caster.conditions.add("stunned")                         # petrified/stunned allies cannot finish the fight
    assert not p.already_won(combat, caster)


def test_losing_fight_releases_everything(monkeypatch):
    p = RationedPolicy()
    combat, caster, foe = setup({1: 2, 2: 1}, remaining=6)
    ally = Combatant("ally", team="party", max_hp=40)
    combat.combatants.append(ally)
    monkeypatch.setattr(combat, "at_will_damage_rate", lambda actor, target: 1)
    foe.hp = 10                                              # a cheap fight: about 2.5 HP forecast loss
    monkeypatch.setattr(p, "within_budget", lambda *a: False)
    monkeypatch.setattr(p, "needs_resources", lambda *a: False)
    assert not p.losing(combat, caster) and not p.allow_spell(combat, caster, SPELL)
    assert p.slot(combat, caster, SPELL, [1, 2]) == 1         # normally the lowest slot
    ally.conditions.add("paralyzed")                         # half the party out of action
    assert p.losing(combat, caster) and p.allow_spell(combat, caster, SPELL)
    assert p.slot(combat, caster, SPELL, [1, 2]) == 2         # released: full strength
    ally.hp = 15                                             # below half HP: heal when losing
    assert p.allow_healing(combat, caster, ally)
    assert p.short_rest_feature(combat, caster)


def test_losing_when_the_forecast_costs_half_the_party(monkeypatch):
    p = RationedPolicy()
    combat, caster, foe = setup({1: 2}, remaining=6)
    monkeypatch.setattr(p, "at_will_fight", lambda c, a: (40, 100, 10, 19))
    assert not p.losing(combat, caster)
    monkeypatch.setattr(p, "at_will_fight", lambda c, a: (40, 100, 10, 20))
    assert p.losing(combat, caster)


def control_block(condition, *, repeat=False, upgrade=None, control=False, select="single", dc=30):
    data = {"condition": condition}
    if repeat: data["repeat_save"] = {"ability": "con", "timing": "end_of_turn", "on_success": "end"}
    if upgrade: data["upgrade_on_failure"] = upgrade
    if control: data["control"] = True
    target = {"select": select, "filter": ["creature"], "affects": "enemy"}
    if select == "area": target.update(shape="emanation", size_ft=30)
    return {"id": "main", "event": "on_cast", "target": target, "attack": None,
            "save": {"ability": "con", "dc": dc, "on_success": "negate"}, "on_hit": [], "on_fail": [{"apply_condition": data}],
            "on_success": [], "apply": []}


def control_fight(block, *, recharge=None, allies=2):
    pcs = [Combatant(f"pc{i}", team="party", max_hp=40) for i in range(allies)]
    action = {"name": "Grip", "cost": "action", "effects": [block]}
    if recharge: action["recharge"] = recharge
    foe = Combatant("foe", team="enemy", max_hp=60, actions=[action])
    combat = Combat([*pcs, foe], load_spells(), seed=1)
    return combat, pcs, foe


def test_control_share_counts_incapacitation_upgrades_and_domination():
    p = RationedPolicy()
    def share(block, **kw):
        combat, pcs, foe = control_fight(block, **kw)
        return p.control_share(combat, pcs[0], pcs, [foe], outgoing=10)   # 6-round horizon
    assert share(control_block("restrained")) == 0                        # not incapacitating
    paralyze = share(control_block("paralyzed"))                         # certain save failure, whole fight
    assert paralyze == pytest.approx(min(p.MAX_CONTROL, 6 / 2))
    assert share(control_block("paralyzed", repeat=True, dc=0)) < paralyze  # repeat saves shorten it
    assert share(control_block("restrained", repeat=True, upgrade="petrified")) > 0
    # 25% to dominate (DC 6 vs +0), counted double for 2 rounds: 1 lost turn per round over 2 PCs.
    assert share(control_block("charmed", control=True, dc=6)) == pytest.approx(0.5)
    assert share(control_block("paralyzed"), recharge=6) < paralyze       # a recharge ability is not always ready
    single = share(control_block("paralyzed", repeat=True, dc=15), allies=4)
    assert share(control_block("paralyzed", repeat=True, dc=15, select="area"), allies=4) > single


def test_control_ignores_immune_allies_and_spent_recharges():
    p = RationedPolicy()
    combat, pcs, foe = control_fight(control_block("paralyzed"))
    for pc in pcs: pc.condition_immunities = ["paralyzed"]
    assert p.control_share(combat, pcs[0], pcs, [foe], outgoing=10) == 0
    combat, pcs, foe = control_fight(control_block("paralyzed"), recharge=5)
    foe.recharge_ready["Grip"] = False
    assert p.control_share(combat, pcs[0], pcs, [foe], outgoing=10) == 0


def test_heavy_control_counts_as_losing():
    p = RationedPolicy()
    combat, pcs, foe = control_fight(control_block("charmed", control=True), allies=2)
    assert p.losing(combat, pcs[0])
    combat, pcs, foe = control_fight(control_block("restrained"), allies=2)
    assert not p.losing(combat, pcs[0])


def test_healing_only_for_downed_or_badly_hurt():
    p = RationedPolicy()
    combat, caster, _ = setup({1: 1})
    target = Combatant("ally", team="party", max_hp=40)
    target.hp = 15
    assert not p.allow_healing(combat, caster, target)
    target.hp = 9
    assert p.allow_healing(combat, caster, target)
    target.hp = 0
    assert p.allow_healing(combat, caster, target)


def test_hit_dice_share_per_short_rest():
    p = RationedPolicy()
    a = Combatant("a", team="party", max_hp=40, hit_dice=4, max_hit_dice=4)
    p.before_rest(None, [a], "short", 2)                     # two short rests left: two dice now
    a.hp = 30
    spent = 0
    while a.hit_dice and p.spend_hit_die(a):
        spent += 1; a.hit_dice -= 1; a.hp += 3
    assert spent == 2
    a.hp = 10                                                # below half: may go beyond the share
    assert p.spend_hit_die(a)
    p.before_rest(None, [a], "long", 0)
    assert p.spend_hit_die(a) == (a.hp < a.max_hp)           # no short-rest schedule: default rule


def test_run_day_reports_the_schedule_to_the_policy():
    seen, rests = [], []

    class Probe(RationedPolicy):
        def precombat_buffs(self, combat, party, phase):
            seen.append((phase, combat.encounters_remaining, combat.encounters_until_rest))

        def before_rest(self, combat, party, kind, short_rests_left):
            rests.append((kind, short_rests_left))
            super().before_rest(combat, party, kind, short_rests_left)

    fighter = Combatant.from_sheet(load_sheet(ROOT / "characters/fighter5.yaml"), "pc", "party")
    day = {"name": "t", "steps": [{"encounter": ["goblin_minion"]}, {"rest": "short"}, {"encounter": ["goblin_minion"]},
                                  {"encounter": ["goblin_minion"]}, {"rest": "short"}, {"encounter": ["goblin_minion"]},
                                  {"rest": "long"}, {"encounter": ["goblin_minion"]}]}
    result = run_day([fighter], day, load_spells(), 1, policy=Probe(), options=DayOptions())
    assert result.encounters_cleared == 5
    assert rests == [("short", 2), ("short", 1), ("long", 0)]
    # (phase, encounters before the long rest, encounters before the next rest)
    assert seen[0] == ("day_start", 4, 1) and ("after_rest", 3, 2) in seen and ("after_rest", 1, 1) in seen
