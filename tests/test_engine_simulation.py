import json
import random
import subprocess
import sys

import pytest

from engine.simulate import simulate, expand_monsters
from engine import Combat, Combatant, load_sheet, load_spells
from engine.loader import ROOT
from engine.policy import Policy


@pytest.mark.parametrize("opponents", [("goblin_warrior", "x4"), ("ogre",)])
def test_1000_run_encounters_reproduce_exactly(opponents):
    first = simulate(monsters=opponents, runs=1000, seed=1)
    second = simulate(monsters=opponents, runs=1000, seed=1)
    assert first == second
    assert first.runs == 1000 and first.win_rate > .9 and first.draws == 0
    assert 1 <= first.mean_rounds <= 10
    assert 0 < first.mean_party_hp <= 87
    assert first.mean_resources_spent["action_surge"] <= 1


def test_cli_and_invalid_inputs():
    result = subprocess.run([sys.executable, "-m", "engine.simulate", "--party", "fighter5", "cleric5", "--monsters", "goblin_warrior", "x4", "--runs", "10", "--seed", "1", "--json"], check=True, capture_output=True, text=True)
    summary = json.loads(result.stdout)
    assert summary["runs"] == 10 and summary["seed"] == 1
    assert summary["mean_resources_spent"]
    with pytest.raises(ValueError): simulate(runs=0)
    with pytest.raises(ValueError): expand_monsters(["x4"])
    assert len(expand_monsters(["goblin_warrior", "x4", "ogre", "x2"])) == 6


def encounter_trace(opponents):
    actors = [Combatant.from_sheet(load_sheet(ROOT / "characters" / (name + ".yaml")), f"party_{i}", "party")
              for i, name in enumerate(("fighter5", "cleric5"))]
    actors += [Combatant.from_sheet(load_sheet(ROOT / "monsters" / (name + ".yaml")), f"enemy_{i}", "enemy")
               for i, name in enumerate(expand_monsters(opponents))]
    oracle = random.Random(1)
    expected_order = [c.id for c in sorted(actors, key=lambda c: (-(oracle.randint(1, 20) + c.mod("dex") + c.initiative_bonus), c.id))]
    combat = Combat(actors, load_spells(), seed=1)
    result = combat.run()
    return combat, result, expected_order


def assert_enemy_trace(combat, result, expected_order):
    assert next(e["order"] for e in combat.log if e["event"] == "initiative") == expected_order
    starts = [e for e in combat.log if e["event"] == "turn_start"]
    assert [e["actor"] for e in starts] == [expected_order[i % len(expected_order)] for i in range(len(starts))]
    turns = {e["turn"]: e["actor"] for e in starts}
    for e in combat.log:
        actor = e.get("actor") if e["event"] == "action" else e.get("attacker") if e["event"] == "attack" else e.get("caster") if e["event"] == "cast" else None
        if actor is not None: assert turns[e["turn"]] == actor
    assert any(e["event"] == "action" and e["actor"].startswith("enemy_") and e["name"] == "Attack" for e in combat.log), "enemies never act"
    assert any(e["event"] == "attack" and e["attacker"].startswith("enemy_") and e["hit"] for e in combat.log), "enemies never hit"
    enemy_damage = [e for e in combat.log if e["event"] == "damage" and (e["source"] or "").startswith("enemy_") and e["target"].startswith("party_")]
    assert sum(e["amount"] for e in enemy_damage) == 13
    assert result["hp"] == combat.party_hp() == 74  # damage reached real HP, not only the log


@pytest.mark.parametrize("opponents", [("goblin_warrior", "x4"), ("ogre",)])
def test_finding9_enemies_act_hit_damage_and_follow_initiative(opponents):
    assert_enemy_trace(*encounter_trace(opponents))


@pytest.mark.parametrize("opponents", [("goblin_warrior", "x4"), ("ogre",)])
def test_finding9_monsters_never_act_mutation_is_detected(monkeypatch, opponents):
    original = Policy.take_turn
    def inactive_enemies(self, combat, actor):
        if actor.team == "party": return original(self, combat, actor)
    monkeypatch.setattr(Policy, "take_turn", inactive_enemies)
    with pytest.raises(AssertionError, match="enemies never act"):
        assert_enemy_trace(*encounter_trace(opponents))
