from copy import deepcopy
import json
import random
import subprocess
import sys

import pytest

from engine import Combat, Combatant, ValidationError, load_sheet, load_spells
from engine.day import cleanup_encounter, load_day, run_day, simulate_day, take_rest, validate_day
from engine.loader import ROOT
from engine.policy import Policy, NovaPolicy, ConservativePolicy
from engine.sheets import validate_sheet
from engine.state import Effect


@pytest.fixture(scope="module")
def spells(): return load_spells()


def character(name="fighter5", identifier=None):
    return Combatant.from_sheet(load_sheet(ROOT / "characters" / (name + ".yaml")), identifier or name, "party")


def definition(*steps):
    return {"name": "Test day", "steps": list(steps)}


@pytest.mark.parametrize("bad", [
    {"name": "Day", "steps": [], "typo": 1},
    {"name": "Day", "steps": []},
    {"name": "Day", "steps": [{"rest": "short"}]},
    definition({"rest": "overnight"}),
    definition({"encounter": ["ogre"], "rest": "short"}),
    definition({"encounter": ["ogre"], "typo": True}),
    definition({}), definition(None), definition({"encounter": []}),
    definition({"encounter": "ogre"}), definition({"encounter": [1]}),
    definition({"encounter": ["ogre x0"]}), definition({"encounter": ["ogre x-1"]}),
    definition({"encounter": ["../ogre"]}), definition({"encounter": ["ogre x2 extra"]}),
    definition({"encounter": [{"ogre": 2}]}),
])
def test_day_strict_validation(bad):
    with pytest.raises(ValidationError, match="broken.yaml:"):
        validate_day(bad, "broken.yaml")


def test_day_files_validate_and_reject_duplicates_and_unknown_monsters(tmp_path):
    for name in ("easy_day", "goblin_warren", "hard_day"):
        assert load_day(name)["steps"]
    path = tmp_path / "bad.yaml"
    path.write_text("name: Day\nname: Other\nsteps: []\n")
    with pytest.raises(ValidationError, match="duplicate key"): load_day(path)
    path.write_text("name: Day\nsteps:\n  - encounter: [missing_monster]\n")
    with pytest.raises(ValidationError, match="steps\\[0\\].encounter: unknown monster"): load_day(path)


@pytest.mark.parametrize("field,value", [
    ("hit_dice", {"die": "d20", "count": 5}),
    ("hit_dice", {"die": "d10", "count": True}),
    ("hit_dice", {"die": "d10", "count": 0}),
    ("hit_dice", {"die": "d10", "count": 5, "typo": 1}),
    ("limited_uses", {"second_wind": {"max": 3, "short_rest": -1}}),
    ("limited_uses", {"second_wind": {"max": 3, "short_rest": 4}}),
    ("limited_uses", {"second_wind": {"max": 3, "long_rest": "full"}}),
    ("limited_uses", {"second_wind": {"max": 3, "short_rest": True}}),
    ("limited_uses", {"second_wind": {"max": 3, "short_rezt": 1}}),
])
def test_character_recovery_validation(field, value):
    sheet = load_sheet(ROOT / "characters/fighter5.yaml")
    sheet[field] = value
    with pytest.raises(ValidationError): validate_sheet(sheet, "broken.yaml")


def test_character_normalization_is_independent_and_legacy_compatible():
    sheet = load_sheet(ROOT / "characters/fighter5.yaml")
    original = deepcopy(sheet)
    fighter = Combatant.from_sheet(sheet, "f", "party")
    fighter.limited_uses["second_wind"] = 0
    fighter.resource_recovery["second_wind"]["short_rest"] = 0
    assert sheet == original
    sheet["limited_uses"] = {"second_wind": 3, "action_surge": 1}
    sheet.pop("hit_dice")
    validate_sheet(sheet, "legacy")
    fighter = Combatant.from_sheet(sheet, "f", "party")
    fighter.limited_uses["second_wind"] = 0
    take_rest([fighter], "short", random.Random(1))
    assert fighter.limited_uses["second_wind"] == 0
    take_rest([fighter], "long", random.Random(1))
    assert fighter.limited_uses["second_wind"] == 3
    assert fighter.hit_dice == 0


def test_short_rest_exact_recovery_hit_die_roll_and_cap():
    fighter, cleric = character(), character("cleric5")
    fighter.hp = 1
    fighter.limited_uses = {"second_wind": 0, "action_surge": 0}
    cleric.limited_uses["channel_divinity"] = 0
    cleric.spell_slots[1] = 0

    class OneDie(Policy):
        def spend_hit_die(self, actor): return actor.hit_dice == actor.max_hit_dice

    oracle = random.Random(12)
    expected = oracle.randint(1, 10) + fighter.mod("con")
    take_rest([fighter, cleric], "short", random.Random(12), OneDie())
    assert fighter.hp == 1 + expected
    assert fighter.hit_dice == 4 and fighter.resources_spent["hit_dice"] == 1
    assert fighter.limited_uses == {"second_wind": 1, "action_surge": 1}
    assert cleric.limited_uses["channel_divinity"] == 1
    assert cleric.spell_slots[1] == 0
    fighter.hp = fighter.max_hp - 1
    take_rest([fighter], "short", random.Random(3))
    assert fighter.hp == fighter.max_hp and fighter.hit_dice == 3
    assert fighter.limited_uses["second_wind"] == 2
    take_rest([fighter], "short", random.Random(3))
    assert fighter.limited_uses["second_wind"] == 3
    assert fighter.hit_dice == 3  # no dice spent at full HP; resource recovery still capped


def test_hit_die_minimum_one_and_policy_target():
    fighter = character()
    fighter.abilities["con"] = 1
    fighter.hp = fighter.max_hp - 1
    # Seed 2 rolls a natural 1 on d10; Con -5 still heals at least one.
    take_rest([fighter], "short", random.Random(2))
    assert fighter.hp == fighter.max_hp and fighter.hit_dice == 4
    fighter = character()
    fighter.hp = 1
    take_rest([fighter], "short", random.Random(4), ConservativePolicy())
    assert fighter.hp >= .85 * fighter.max_hp or fighter.hit_dice == 0
    assert fighter.resources_spent["hit_dice"] == 5 - fighter.hit_dice


@pytest.mark.parametrize("rest", ["short", "long"])
def test_downed_gets_no_rest_benefits(rest):
    fighter = character()
    fighter.hp = 0
    fighter.hit_dice = 1
    fighter.limited_uses = {"second_wind": 0, "action_surge": 0}
    before = deepcopy(fighter.__dict__)
    take_rest([fighter], rest, random.Random(1))
    assert fighter.__dict__ == before


def test_long_rest_restores_everything_but_does_not_erase_spending():
    fighter, cleric = character(), character("cleric5")
    for actor in (fighter, cleric):
        actor.hp = 1
        actor.hit_dice = 0
        actor.limited_uses = dict.fromkeys(actor.limited_uses, 0)
        actor.spend("hit_dice", 5)
    cleric.spell_slots = dict.fromkeys(cleric.spell_slots, 0)
    take_rest([fighter, cleric], "long", random.Random(1))
    for actor in (fighter, cleric):
        assert actor.hp == actor.max_hp and actor.hit_dice == 5
        assert actor.limited_uses == actor.max_limited_uses
        assert actor.resources_spent["hit_dice"] == 5
    assert cleric.spell_slots == {1: 4, 2: 3, 3: 2}


def test_carryover_long_rest_and_party_identity(spells, monkeypatch):
    party = [character(), character("cleric5")]
    original_run = Combat.run
    seen = []

    def track(self, *args):
        seen.append(self.combatants[:2])
        return original_run(self, *args)

    monkeypatch.setattr(Combat, "run", track)
    day = definition({"encounter": ["goblin_warrior x3"]}, {"encounter": ["goblin_warrior x3"]},
                     {"rest": "long"}, {"encounter": ["goblin_warrior"]})
    result = run_day(party, day, spells, seed=11, policy=NovaPolicy())
    assert result.survived and result.encounters_cleared == 3
    first, second, third = result.encounters
    assert first.end["cleric5"]["slots"][3] < 2
    assert second.start["cleric5"]["slots"] == first.end["cleric5"]["slots"]
    assert second.start["fighter5"]["resources"] == first.end["fighter5"]["resources"]
    assert third.start["cleric5"]["slots"] == {1: 4, 2: 3, 3: 2}
    assert all(state["hp"] == state["max_hp"] and state["hit_dice"] == 5 for state in third.start.values())
    assert third.start["fighter5"]["resources"] == {"second_wind": 3, "action_surge": 1}
    assert all(actors[0] is party[0] and actors[1] is party[1] for actors in seen)
    assert party[1].resources_spent["slot_3"] >= 2


def test_cleanup_ends_concentration_detached_effects_and_temp_hp(spells):
    cleric, fighter = character("cleric5"), character()
    combat = Combat([cleric, fighter], spells)
    combat.begin_turn(cleric)
    instance = combat.cast(cleric, "Shield of Faith", targets=[fighter])
    fighter.temp_hp = 8
    fighter.effects.append(Effect("status", {"id": "detached"}, -123, "test"))
    fighter.conditions.add("poisoned")
    fighter.statuses["test"] = {}
    fighter.slot_cast_turn = combat.turn_index + 1
    slots = cleric.spell_slots.copy()
    cleanup_encounter(combat)
    assert not instance.active and not combat.instances
    assert cleric.concentration is None and cleric.spell_slots == slots
    assert not fighter.effects and not fighter.statuses and not fighter.conditions
    assert fighter.temp_hp == 0 and fighter.slot_cast_turn is None


def test_postcombat_healing_enables_rest_and_counts_repeated_downs(spells, monkeypatch):
    fighter, cleric = character(), character("cleric5")
    identity = fighter
    monsters_seen = []

    def knock_down(self, *args):
        monsters_seen.append(self.combatants[-1])
        # Two independent transitions to 0 in one encounter, not just one downed PC.
        self.apply_damage(fighter, fighter.hp)
        self.heal(fighter, 1)
        self.apply_damage(fighter, 1)
        for enemy in self.combatants[2:]: enemy.hp = 0
        return {"winner": "party", "rounds": 1}

    monkeypatch.setattr(Combat, "run", knock_down)
    day = definition({"encounter": ["cultist_fanatic"]}, {"rest": "long"}, {"encounter": ["cultist_fanatic"]})
    result = run_day([fighter, cleric], day, spells, seed=1)
    first, second = result.encounters
    assert first.downs == 2 and first.downs_by_character["fighter5"] == 2
    assert first.end["fighter5"]["hp"] == 0
    assert first.after_healing["fighter5"]["hp"] > 0
    assert first.after_healing["cleric5"]["slots"][1] == 3
    assert second.start["fighter5"]["hp"] == 49
    assert second.start["cleric5"]["slots"][1] == 4
    assert fighter is identity
    assert monsters_seen[0] is not monsters_seen[1]
    assert monsters_seen[1].limited_uses == {"Hold Person": 1, "Spiritual Weapon": 2, "Command": 2}


def test_unhealed_downed_pc_stays_out_across_rests(spells, monkeypatch):
    fighter, cleric = character(), character("cleric5")
    cleric.spells = []

    def knock_down(self, *args):
        self.apply_damage(fighter, fighter.hp)
        return {"winner": "party", "rounds": 1}

    monkeypatch.setattr(Combat, "run", knock_down)
    day = definition({"encounter": ["ogre"]}, {"rest": "short"}, {"rest": "long"}, {"encounter": ["ogre"]})
    result = run_day([fighter, cleric], day, spells, seed=1)
    assert result.encounters[1].start["fighter5"]["hp"] == 0
    assert not fighter.alive and fighter.has_condition("unconscious")
    assert fighter.hit_dice == 5


def test_postcombat_healing_feature_spends_its_counter(spells, monkeypatch):
    fighter = character()
    healer = Combatant("healer", team="party", limited_uses={"rescue": 1}, actions=[
        {"name": "Rescue", "cost": "action", "resource": "rescue", "effects": deepcopy(spells["Cure Wounds"]["effects"])}])

    def knock_down(self, *args):
        self.apply_damage(fighter, fighter.hp)
        return {"winner": "party", "rounds": 1}

    monkeypatch.setattr(Combat, "run", knock_down)
    result = run_day([fighter, healer], definition({"encounter": ["ogre"]}), spells, seed=1)
    assert result.encounters[0].end["fighter5"]["hp"] == 0
    assert fighter.hp > 0
    assert healer.limited_uses["rescue"] == 0 and healer.resources_spent["rescue"] == 1


def test_tpk_stops_day_before_rest_and_counts_clears(spells, monkeypatch):
    party = [character(), character("cleric5")]
    calls = []

    def scripted(self, *args):
        calls.append(1)
        if len(calls) == 1: return {"winner": "party", "rounds": 2}
        for actor in party: self.apply_damage(actor, actor.hp)
        return {"winner": "enemy", "rounds": 3}

    monkeypatch.setattr(Combat, "run", scripted)
    day = definition({"encounter": ["ogre"]}, {"encounter": ["young_red_dragon"]}, {"rest": "long"}, {"encounter": ["ogre"]})
    result = run_day(party, day, spells, seed=1)
    assert not result.survived and result.failure_reason == "tpk"
    assert result.encounters_cleared == 1 and len(result.encounters) == 2
    assert result.encounters[-1].downs == 2
    assert all(c.hp == 0 for c in party)


def test_round_limit_fails_without_granting_a_clear(spells):
    class Idle(Policy):
        def take_turn(self, combat, actor): pass

    result = run_day([character()], definition({"encounter": ["ogre"]}), spells,
                     seed=1, policy=Idle(), monster_policy=Idle(), max_rounds=1)
    assert not result.survived and result.failure_reason == "round_limit"
    assert result.encounters_cleared == 0


def test_summary_means_use_only_runs_reaching_each_encounter(monkeypatch):
    seen = []
    original_run = run_day

    def track(*args, **kwargs):
        result = original_run(*args, **kwargs)
        seen.append(result)
        return result

    monkeypatch.setattr("engine.day.run_day", track)
    # The overwhelmingly lethal opener leaves the second encounter unreached.
    day = definition({"encounter": ["young_red_dragon x4"]}, {"encounter": ["ogre"]})
    summary = simulate_day(day=day, runs=3, seed=1)
    first, second = summary.encounters
    assert first["reached"] == 3 and first["mean_start_hp_percent"] == 100
    assert first["mean_resources_start"] == {"action_surge": 1, "channel_divinity": 2, "hit_dice": 10, "second_wind": 3}
    assert first["mean_downs"] == sum(r.encounters[0].downs for r in seen) / 3
    assert first["mean_rounds"] == sum(r.encounters[0].rounds for r in seen) / 3
    assert second["reached"] == 0 and second["mean_start_hp_percent"] is None
    assert second["mean_slots_start"] == {} and second["mean_resources_start"] == {}
    assert second["mean_rounds"] is None and second["mean_downs"] is None
    assert summary.survival_probability == 0 and summary.encounters_cleared_distribution == {0: 3}


def test_day_cli_json_and_text():
    cmd = [sys.executable, "-m", "engine.day", "--party", "fighter5", "cleric5", "--day", "easy_day",
           "--runs", "3", "--seed", "1", "--strategy", "conservative", "--monster-strategy", "nova"]
    result = subprocess.run(cmd + ["--json"], check=True, capture_output=True, text=True)
    summary = json.loads(result.stdout)
    assert summary["runs"] == 3 and summary["seed"] == 1
    assert summary["strategy"] == "conservative" and summary["monster_strategy"] == "nova"
    assert len(summary["encounters"]) == 3
    assert sum(summary["encounters_cleared_distribution"].values()) == 3
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    assert "P(survive)" in result.stdout and "Start HP%" in result.stdout


@pytest.mark.parametrize("kwargs", [{"runs": 0}, {"max_rounds": 0}, {"party": []},
                                        {"party": ["../fighter5"]}, {"strategy": "unknown"}])
def test_day_invalid_simulation_arguments(kwargs):
    with pytest.raises(ValueError): simulate_day(day="easy_day", **kwargs)


@pytest.mark.parametrize("fallback", [False, True])
def test_step1_fix1_humanoid_heal_skips_downed_beast_without_spending(spells, fallback):
    healer_sheet = load_sheet(ROOT / "characters/fighter5.yaml")
    effects = deepcopy(spells["Cure Wounds"]["effects"])
    effects[0]["target"]["filter"] = ["humanoid"]
    healer_sheet["actions"] = [{"name": "Humanoid rescue", "cost": "action", "resource": "rescue", "effects": effects}]
    healer_sheet["limited_uses"] = {"rescue": 1}
    if fallback:
        healer_sheet["actions"].append({"name": "Any rescue", "cost": "action", "resource": "any_rescue",
                                        "effects": deepcopy(spells["Cure Wounds"]["effects"])})
        healer_sheet["limited_uses"]["any_rescue"] = 1
    validate_sheet(healer_sheet, "healer")
    victim_sheet = load_sheet(ROOT / "characters/fighter5.yaml")
    victim_sheet["creature_type"] = "beast"
    validate_sheet(victim_sheet, "victim")
    healer = Combatant.from_sheet(healer_sheet, "healer", "party")
    victim = Combatant.from_sheet(victim_sheet, "victim", "party")
    victim.hp = 0
    result = run_day([healer, victim], definition({"encounter": ["goblin_warrior"]}), spells, seed=1)
    assert result.survived
    assert healer.limited_uses["rescue"] == 1
    assert healer.resources_spent.get("rescue", 0) == 0
    assert (victim.hp > 0) == fallback
    if fallback:
        assert healer.limited_uses["any_rescue"] == 0
        assert healer.resources_spent["any_rescue"] == 1


# These tests lock the accepted pre-realism day contract and exact seeded counts.
# New-default rules are tested independently in test_day_realism.py.
from engine.day import run_day as _legacy_run_day, simulate_day as _legacy_simulate_day
from engine.day_options import DayOptions


def run_day(*args, **kwargs):
    kwargs.setdefault("options", DayOptions.legacy())
    return _legacy_run_day(*args, **kwargs)


def simulate_day(*args, **kwargs):
    kwargs.setdefault("options", DayOptions.legacy())
    return _legacy_simulate_day(*args, **kwargs)
