from copy import deepcopy

import pytest

from engine import Combat, Combatant, load_spells
from engine.day import load_day, run_day, simulate_day
from engine.policy import Policy, NovaPolicy, ConservativePolicy
from test_engine_day import character, definition


def test_nova_spends_early_and_conservative_keeps_resources():
    spells = load_spells()
    day = load_day("goblin_warren")
    results = []
    for policy in (NovaPolicy(), ConservativePolicy()):
        party = [character(), character("cleric5")]
        results.append(run_day(party, day, spells, seed=1, policy=policy))
    nova, conservative = (r.encounters[0] for r in results)
    nova_spent = sum(sum(c["resources_spent"].values()) for c in nova.end.values())
    conservative_spent = sum(sum(c["resources_spent"].values()) for c in conservative.end.values())
    assert nova_spent > conservative_spent
    assert nova.end["cleric5"]["slots"][3] < conservative.end["cleric5"]["slots"][3]
    assert nova.end["fighter5"]["resources"]["action_surge"] == 0
    assert conservative.end["fighter5"]["resources"]["action_surge"] == 1


def test_strategy_slot_selection_and_remaining_encounter_budget():
    actor = character("cleric5")
    enemy = Combatant("enemy", team="enemy", max_hp=10000)
    spells = load_spells()
    combat = Combat([actor, enemy], spells, policy=NovaPolicy())
    assert combat.available_slot(actor, spells["Guiding Bolt"]) == 3
    combat.policy = Policy()
    assert combat.available_slot(actor, spells["Guiding Bolt"]) == 1
    combat.policy = ConservativePolicy()
    combat.encounters_remaining = 7
    combat.slots_at_start = {actor.id: actor.spell_slots.copy()}
    # Force danger with a strong, high-HP weapon enemy, not knowledge of dice.
    enemy.attacks = [{"name": "Hit", "to_hit": 12, "effects": [{"damage": {"dice": "4d10", "bonus": 5, "type": "force"}}]}]
    assert combat.policy.dangerous(combat, actor)
    assert combat.policy.allow_spell(combat, actor, spells["Guiding Bolt"])
    actor.spell_slots[1] -= 2  # ceil(9 / 7) == 2: this encounter's budget is exhausted
    assert not combat.policy.allow_spell(combat, actor, spells["Guiding Bolt"])
    combat.encounters_remaining = 1
    assert combat.policy.allow_spell(combat, actor, spells["Guiding Bolt"])
    actor.hp = 1
    combat.encounters_remaining = 7
    assert combat.policy.allow_spell(combat, actor, spells["Guiding Bolt"])  # emergency override


def assert_policy_routing():
    seen = set()

    class Tracking(Policy):
        def __init__(self, team): self.team = team

        def check(self, hook, actor):
            assert actor.team == self.team, f"{hook} misrouted"
            seen.add((hook, self.team))

        def take_turn(self, combat, actor):
            self.check("turn", actor)
            super().take_turn(combat, actor)

        def targets(self, combat, instance, block, eligible, n):
            self.check("targets", instance.caster)
            return super().targets(combat, instance, block, eligible, n)

        def slot(self, combat, actor, spec, slots):
            self.check("slot", actor)
            return slots[0] if self.team == "party" else slots[-1]

        def reaction(self, combat, actor, spell, trigger):
            self.check("reaction", actor)
            return super().reaction(combat, actor, spell, trigger)

        def optional(self, combat, instance, block):
            self.check("optional", instance.caster)
            return True

    # Both are actual slot casters, not the Fanatic's slotless innate spells.
    actors = [Combatant(team, team=team, max_hp=1000, spells=["Spiritual Weapon"],
                        spell_slots={1: 2, 2: 2}) for team in ("party", "enemy")]
    combat = Combat(actors, load_spells(), seed=1, policy=Tracking("party"), monster_policy=Tracking("enemy"))
    for actor in actors:
        combat.begin_turn(actor)
        combat.policy_for(actor).take_turn(combat, actor)
        assert actor.resources_spent["slot_2"] == 1
        assert any(e["event"] == "cast" and e["caster"] == actor.id and e["spell"] == "Spiritual Weapon" for e in combat.log)
    for actor in actors: actor.spells.append("Shield")
    for reactor, attacker in (actors, actors[::-1]):
        combat.begin_turn(attacker)  # a fresh global turn permits the reactor's slot
        combat.offer_reactions("on_attack_provisional_hit", attacker=attacker, defender=reactor,
                               attack={"natural": 10, "total": reactor.ac + 1})
        assert reactor.resources_spent.get("slot_1", 0) == (1 if reactor.team == "party" else 0)
        assert reactor.resources_spent["slot_2"] == (1 if reactor.team == "party" else 2)
        assert reactor.reaction == 0
    assert seen == {(hook, team) for hook in ("turn", "targets", "slot", "reaction", "optional")
                    for team in ("party", "enemy")}
    # Retain the day-level wiring check as well as the forced hook scenarios.
    seen.clear()
    result = run_day([character(), character("cleric5")], definition({"encounter": ["cultist_fanatic"]}),
                     load_spells(), seed=1, policy=Tracking("party"), monster_policy=Tracking("enemy"))
    assert result.survived
    assert {("turn", "party"), ("turn", "enemy")} <= seen


def test_party_and_monster_policies_route_all_decisions():
    assert_policy_routing()


def test_step1_fix2_monster_hooks_are_invoked():
    assert_policy_routing()


@pytest.mark.parametrize("method,hook", [("available_slot", "slot"), ("offer_reactions", "reaction"),
                                         ("resolve_block", "optional")])
def test_step1_fix2_misrouting_each_monster_hook_is_detected(monkeypatch, method, hook):
    import inspect
    import textwrap

    original = getattr(Combat, method)
    source = textwrap.dedent(inspect.getsource(original))
    routed = f"self.policy_for({'instance.caster' if hook == 'optional' else 'actor'}).{hook}("
    assert routed in source
    namespace = {}
    exec(compile(source.replace(routed, f"self.policy.{hook}("), "<routing mutation>", "exec"),
         original.__globals__, namespace)
    monkeypatch.setattr(Combat, method, namespace[method])
    with pytest.raises(AssertionError, match=f"{hook} misrouted"):
        assert_policy_routing()


@pytest.mark.parametrize("strategy", ["default", "nova", "conservative"])
def test_seeded_day_reproducibility(strategy):
    first = simulate_day(day="goblin_warren", runs=20, seed=57, strategy=strategy)
    assert first == simulate_day(day="goblin_warren", runs=20, seed=57, strategy=strategy)
    assert first != simulate_day(day="goblin_warren", runs=20, seed=58, strategy=strategy)


def test_1000_run_standard_day_strategy_comparison():
    nova = simulate_day(day="goblin_warren", runs=1000, seed=1, strategy="nova")
    conservative = simulate_day(day="goblin_warren", runs=1000, seed=1, strategy="conservative")
    assert (nova.survived, conservative.survived) == (128, 163)
    assert nova.encounters_cleared_distribution == {2: 11, 3: 98, 5: 431, 6: 332, 7: 128}
    assert conservative.encounters_cleared_distribution == {1: 1, 2: 59, 3: 192, 4: 1, 5: 412, 6: 172, 7: 163}
    # Fixed before comparison: .07 exceeds 3 * sqrt(2 * .25 / 1000), the
    # worst-case independent-binomial SE bound; no tuning to seeded outcomes.
    assert conservative.survival_probability + .07 >= nova.survival_probability
    assert nova.encounters[1]["mean_slots_start"][3] < conservative.encounters[1]["mean_slots_start"][3]
    assert nova.encounters[1]["mean_resources_start"]["action_surge"] < conservative.encounters[1]["mean_resources_start"]["action_surge"]
    for summary in (nova, conservative):
        assert sum(summary.encounters_cleared_distribution.values()) == 1000
        assert len(summary.encounters) == 7
        assert summary.encounters[0]["mean_start_hp_percent"] == 100
        assert summary.encounters[-1]["mean_start_hp_percent"] < 100
        assert 0 <= summary.survived <= 1000


def scoring_combat(monster="ogre", policy=None):
    from engine import load_sheet
    from engine.loader import ROOT

    cleric = character("cleric5")
    fighter = character()
    enemy = Combatant.from_sheet(load_sheet(ROOT / "monsters" / (monster + ".yaml")), "enemy", "enemy")
    combat = Combat([fighter, cleric, enemy], load_spells(), policy=policy)
    combat.begin_turn(cleric)
    return combat, cleric, enemy


def spell_score(combat, actor, name, target):
    spec = combat.spells[name]
    return combat.expected_spell_damage(actor, combat.scale(actor, spec, combat.available_slot(actor, spec)), target)


def test_step1_fix3_spiritual_weapon_outranks_guiding_bolt_in_long_fight():
    combat, cleric, ogre = scoring_combat()
    ogre.hp = ogre.max_hp = 100
    assert combat.expected_remaining_rounds(cleric) >= 3
    weapon = combat.expected_weapon_damage(cleric, ogre)
    assert spell_score(combat, cleric, "Spiritual Weapon", ogre) + weapon > spell_score(combat, cleric, "Guiding Bolt", ogre)
    cleric.spells = ["Spiritual Weapon", "Guiding Bolt"]
    combat.policy.take_turn(combat, cleric)
    assert any(e["event"] == "cast" and e["spell"] == "Spiritual Weapon" for e in combat.log)
    assert any(e["event"] == "action" and e["name"] == "Attack" for e in combat.log)


@pytest.mark.parametrize("policy", [Policy, NovaPolicy, ConservativePolicy])
def test_step1_fix3_hold_person_chosen_for_weak_wis_humanoid_heavy_hitter(policy):
    combat, cleric, fanatic = scoring_combat("cultist_fanatic", policy())
    fanatic.save_bonuses["wis"] = -1
    # A durable heavy-hitter variant makes spending justified for conservative too.
    fanatic.hp = fanatic.max_hp = 120
    fanatic.extra_attack = 2
    combat.policy.take_turn(combat, cleric)
    assert any(e["event"] == "cast" and e["spell"] == "Hold Person" for e in combat.log)


def test_step1_fix3_hold_person_chosen_for_unmodified_fanatic_except_weak_save():
    combat, cleric, fanatic = scoring_combat("cultist_fanatic")
    fanatic.save_bonuses["wis"] = -1
    combat.policy.take_turn(combat, cleric)
    assert any(e["event"] == "cast" and e["spell"] == "Hold Person" for e in combat.log)


@pytest.mark.parametrize("policy", [Policy, NovaPolicy, ConservativePolicy])
def test_step1_fix3_hold_person_not_chosen_for_giant(policy):
    combat, cleric, ogre = scoring_combat(policy=policy())
    assert ogre.creature_type == "giant"
    assert spell_score(combat, cleric, "Hold Person", ogre) == 0
    combat.policy.take_turn(combat, cleric)
    assert not any(e["event"] == "cast" and e["spell"] == "Hold Person" for e in combat.log)


@pytest.mark.parametrize("name", ["Spiritual Weapon", "Spirit Guardians", "Hex", "Hunter's Mark"])
def test_step1_fix3_lasting_damage_horizon_duration_and_opportunity_cost(name):
    combat, cleric, ogre = scoring_combat()
    spec = combat.scale(cleric, combat.spells[name], combat.spells[name]["level"])
    short = combat.expected_spell_damage(cleric, spec, ogre, horizon=1)
    long = combat.expected_spell_damage(cleric, spec, ogre, horizon=3)
    assert long > short > 0
    capped = deepcopy(spec)
    capped["duration"] = {"type": "rounds", "n": 2}
    assert combat.expected_spell_damage(cleric, capped, ogre, horizon=3) == combat.expected_spell_damage(cleric, spec, ogre, horizon=2)
    free_concentration = deepcopy(spec)
    free_concentration["concentration"] = False
    assert long == pytest.approx(.9 * combat.expected_spell_damage(cleric, free_concentration, ogre, horizon=3))
    if name == "Spiritual Weapon":
        assert long == pytest.approx(short * (1 + .85 * 2))
    elif name in {"Hex", "Hunter's Mark"}:
        assert long == pytest.approx(short * 3)
        cleric.attacks = []
        cleric.spells = []
        assert combat.expected_spell_damage(cleric, spec, ogre, horizon=3) == 0


def test_step1_fix3_control_save_uptime_immunity_and_banishment():
    combat, cleric, fanatic = scoring_combat("cultist_fanatic")
    spec = combat.scale(cleric, combat.spells["Hold Person"], 2)
    q = combat.save_failure_probability(cleric, fanatic, "wis")
    one = combat.expected_spell_damage(cleric, spec, fanatic, horizon=1)
    three = combat.expected_spell_damage(cleric, spec, fanatic, horizon=3)
    assert one > 0
    assert three == pytest.approx(one * (1 + q + q*q))
    start_save = deepcopy(spec)
    start_save["effects"][0]["on_fail"][0]["apply_condition"]["repeat_save"]["timing"] = "start_of_turn"
    assert combat.expected_spell_damage(cleric, start_save, fanatic, horizon=3) == pytest.approx(three * q)
    fanatic.save_bonuses["wis"] = 100
    assert combat.expected_spell_damage(cleric, spec, fanatic, horizon=3) == 0
    fanatic.save_bonuses["wis"] = -1
    assert combat.expected_spell_damage(cleric, spec, fanatic, horizon=3) > three
    fanatic.condition_immunities = ["paralyzed"]
    assert combat.expected_spell_damage(cleric, spec, fanatic, horizon=3) == 0
    banish = combat.spells["Banishment"]
    assert combat.expected_spell_damage(cleric, banish, fanatic, horizon=3) > 0


def test_step1_fix3_scorer_is_rng_and_resource_free():
    combat, cleric, fanatic = scoring_combat("cultist_fanatic")
    before = deepcopy(cleric.__dict__)
    rng = combat.rng.getstate()
    for name in cleric.spells:
        spell_score(combat, cleric, name, fanatic)
    assert cleric.__dict__ == before
    assert combat.rng.getstate() == rng
    assert not combat.instances
