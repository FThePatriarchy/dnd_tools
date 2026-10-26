"""Rationed strategy: daily slot budget, short-rest features and Hit Dice shares."""
import math

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
