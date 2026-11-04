"""The budgeted strategy: resources budgeted until they come back, and priced spell slots."""
from engine import Combat, Combatant
from engine.builder import load_character
from engine.loader import ROOT, load_sheet, load_spells
from engine.policy import BudgetedPolicy, STRATEGIES

SPELLS = load_spells()


def setup(name, until_rest, remaining, foe="goblin_minion"):
    pc = Combatant.from_sheet(load_character(name), "p0", "party")
    enemy = Combatant.from_sheet(load_sheet(ROOT / "monsters" / f"{foe}.yaml"), "e0", "enemy")
    policy = BudgetedPolicy()
    combat = Combat([pc, enemy], SPELLS, seed=1, policy=policy)
    combat.encounters_until_rest, combat.encounters_remaining = until_rest, remaining
    combat.uses_at_start = {pc.id: dict(pc.limited_uses)}
    combat.slots_at_start = {pc.id: dict(pc.spell_slots)}
    combat.begin_turn(pc)
    return combat, pc, policy


def test_registered():
    assert STRATEGIES["budgeted"] is BudgetedPolicy


def test_short_rest_feature_is_shared_until_the_next_rest(monkeypatch):
    combat, pc, policy = setup("fighter_5", until_rest=2, remaining=4)
    monkeypatch.setattr(policy, "needs_resources", lambda *a: False)
    assert policy.allow_resource(combat, pc, "second_wind")          # share of 2 fights: 2 of 3 uses... at least one
    pc.limited_uses["second_wind"] -= 2
    assert not policy.allow_resource(combat, pc, "second_wind")      # its share for this fight is spent
    combat.encounters_until_rest = 1
    assert policy.allow_resource(combat, pc, "second_wind")          # last fight before the rest: spend freely


def test_slot_price_rises_with_level_and_vanishes_before_the_refresh():
    combat, wizard, policy = setup("wizard_5", until_rest=3, remaining=3)
    assert policy.level_price(combat, wizard, 3) > policy.level_price(combat, wizard, 1) > 0
    combat.encounters_remaining = 1
    assert policy.level_price(combat, wizard, 3) == 0


def test_pact_slots_refresh_on_a_short_rest():
    combat, warlock, policy = setup("warlock_5", until_rest=1, remaining=4)
    assert policy.level_price(combat, warlock, 3) == 0                # pact slots come back at the next rest
    combat2, wizard, policy2 = setup("wizard_5", until_rest=1, remaining=4)
    assert policy2.level_price(combat2, wizard, 3) > 0                # wizard slots only after the long rest
