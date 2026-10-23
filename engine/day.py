"""Persistent adventuring days, 2024 rests, and seeded Monte Carlo summaries."""
import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import random
import re
from statistics import mean

from . import dice
from .combat import Combat
from .loader import ROOT, Validator, load_sheet, load_spells, read_yaml
from .policy import Policy, STRATEGIES, strategy_policy
from .state import Combatant


MONSTERS = re.compile(r"([a-z][a-z0-9_]*)(?: x([1-9][0-9]*))?")


def encounter_names(entries):
    names = []
    for entry in entries:
        match = MONSTERS.fullmatch(entry)
        if not match: raise ValueError(f"invalid monster entry: {entry!r}")
        name, count = match.groups()
        names.extend([name] * int(count or 1))
    return names


def validate_day(data, path="<day>"):
    v = Validator(path)
    v.obj(data, "$", "name steps")
    v.text(data["name"], "name")
    v.sequence(data["steps"], "steps")
    v.check(bool(data["steps"]), "steps", "day must not be empty")
    for i, step in enumerate(data["steps"]):
        p = f"steps[{i}]"
        v.obj(step, p, optional="encounter rest")
        v.check(len(step) == 1, p, "expected exactly one encounter or rest")
        if "rest" in step:
            v.enum(step["rest"], {"short", "long"}, p + ".rest")
        else:
            v.sequence(step["encounter"], p + ".encounter")
            v.check(bool(step["encounter"]), p + ".encounter", "empty encounter")
            for j, entry in enumerate(step["encounter"]):
                q = f"{p}.encounter[{j}]"
                v.text(entry, q)
                v.check(MONSTERS.fullmatch(entry) is not None, q, "expected monster_name or monster_name xN (N > 0)")
    v.check(any("encounter" in step for step in data["steps"]), "steps", "day needs an encounter")


def load_day(path):
    path = Path(path)
    if path.suffix != ".yaml":
        if not re.fullmatch(r"[a-z][a-z0-9_]*", str(path)): raise ValueError("invalid day name")
        path = ROOT / "days" / (str(path) + ".yaml")
    data = read_yaml(path)
    validate_day(data, path)
    v = Validator(path)
    for i, step in enumerate(data["steps"]):
        for name in encounter_names(step.get("encounter", [])):
            v.check((ROOT / "monsters" / (name + ".yaml")).is_file(), f"steps[{i}].encounter", f"unknown monster {name}")
    return data


def cleanup_encounter(combat):
    """The gap exceeds every spell/effect duration, even detached end effects."""
    for identifier in list(combat.instances): combat.end_spell(identifier)
    combat.instances.clear()
    for actor in combat.combatants:
        actor.concentration = None
        actor.effects.clear()
        actor.conditions.clear()
        actor.exhaustion_level = 0
        actor.statuses.clear()
        actor.temp_hp = 0
        actor.removed = False  # temporary banishment ends; permanent removal is retained
        if actor.hp == 0: actor.conditions.update({"unconscious", "prone"})
        actor.extra_actions.clear()
        actor.action_grants.clear()
        actor.surge_actions = 0
        actor.blocked_economy.clear()
        actor.action = actor.bonus_action = actor.reaction = 1
        actor.slot_cast_turn = None
        actor.turns_taken = 0
        actor.recharge_ready.clear()
    combat.current = None


def take_rest(party, kind, rng, policy=None):
    if kind not in {"short", "long"}: raise ValueError("rest must be short or long")
    policy = policy or Policy()
    for actor in party:
        if not actor.alive: continue
        if kind == "long":
            actor.hp = actor.max_hp
            actor.spell_slots = actor.max_spell_slots.copy()
            actor.hit_dice = actor.max_hit_dice
        else:
            while actor.hit_dice and actor.hit_die and actor.hp < actor.max_hp and policy.spend_hit_die(actor):
                healing = max(1, dice.roll(rng, "1" + actor.hit_die) + actor.mod("con"))
                actor.hp = min(actor.max_hp, actor.hp + healing)
                actor.hit_dice -= 1
                actor.spend("hit_dice")
        for name, maximum in actor.max_limited_uses.items():
            recovery = actor.resource_recovery.get(name, {}).get(kind + "_rest", 0)
            actor.limited_uses[name] = maximum if recovery == "all" else min(maximum, actor.limited_uses[name] + recovery)


def snapshot(party):
    return {c.id: {"hp": c.hp, "max_hp": c.max_hp, "temp_hp": c.temp_hp,
                   "slots": c.spell_slots.copy(), "resources": c.limited_uses.copy(),
                   "hit_dice": c.hit_dice, "resources_spent": c.resources_spent.copy()}
            for c in party}


@dataclass(frozen=True)
class EncounterResult:
    index: int
    monsters: list[str]
    rounds: int
    cleared: bool
    start: dict
    end: dict
    after_healing: dict
    downs: int
    downs_by_character: dict[str, int]


@dataclass(frozen=True)
class DayResult:
    survived: bool
    encounters_cleared: int
    encounters: list[EncounterResult]
    failure_reason: str | None = None


def day_monsters(day):
    names = {name for step in day["steps"] if "encounter" in step for name in encounter_names(step["encounter"])}
    return {name: load_sheet(ROOT / "monsters" / (name + ".yaml")) for name in sorted(names)}


def run_day(party, day, spells, seed=1, *, policy=None, monster_policy=None, max_rounds=100, monster_sheets=None):
    """Mutates the supplied party in place; end snapshots precede cleanup/healing."""
    validate_day(day)
    if not party or len({c.id for c in party}) != len(party) or any(c.team != "party" for c in party):
        raise ValueError("day needs a nonempty party with unique ids and team='party'")
    if max_rounds < 1: raise ValueError("max_rounds must be positive")
    policy = policy or Policy()
    monsters = day_monsters(day) if monster_sheets is None else monster_sheets
    rng = random.Random(seed)
    results = []
    remaining = sum("encounter" in step for step in day["steps"])
    cleared = 0
    for step in day["steps"]:
        if "rest" in step:
            take_rest(party, step["rest"], rng, policy)
            continue
        names = encounter_names(step["encounter"])
        enemies = [Combatant.from_sheet(monsters[name], f"enemy_{i}", "enemy") for i, name in enumerate(names)]
        combat = Combat(party + enemies, spells, seed=rng.getrandbits(64), policy=policy, monster_policy=monster_policy or Policy())
        combat.record_log = False
        combat.encounters_remaining = remaining  # includes this encounter, even across a long rest
        combat.slots_at_start = {c.id: c.spell_slots.copy() for c in party}
        start = snapshot(party)
        before_downs = {c.id: c.downs for c in party}
        outcome = combat.run(max_rounds) if any(c.alive for c in party) else {"winner": "enemy", "rounds": 0}
        end = snapshot(party)
        downs = {c.id: c.downs - before_downs[c.id] for c in party}
        won = outcome["winner"] == "party"
        if won: cleared += 1
        tpk = all(c.hp == 0 for c in party)
        cleanup_encounter(combat)
        if not tpk and won:
            combat.combatants = party  # defeated/banished foes cannot react to postcombat healing
            policy.recover_downed(combat, party)
            cleanup_encounter(combat)
        results.append(EncounterResult(len(results) + 1, names, outcome["rounds"], won, start, end, snapshot(party), sum(downs.values()), downs))
        if not won:
            reason = "tpk" if tpk else "round_limit" if outcome["winner"] is None else "party_unavailable"
            return DayResult(False, cleared, results, reason)
        remaining -= 1
    return DayResult(True, cleared, results)


@dataclass(frozen=True)
class DaySummary:
    name: str
    runs: int
    seed: int
    strategy: str
    monster_strategy: str
    survived: int
    survival_probability: float
    encounters_cleared_distribution: dict[int, int]
    encounters: list[dict]


def simulate_day(party=("fighter5", "cleric5"), day="goblin_warren", runs=1000, seed=1, *, strategy="default", monster_strategy="default", max_rounds=100):
    if runs < 1: raise ValueError("runs must be positive")
    if max_rounds < 1: raise ValueError("max_rounds must be positive")
    if not party: raise ValueError("party must not be empty")
    sheets = []
    for name in party:
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name): raise ValueError(f"invalid sheet name: {name}")
        sheets.append(load_sheet(ROOT / "characters" / (name + ".yaml")))
    definition = load_day(day) if not isinstance(day, dict) else day
    validate_day(definition)
    monsters = day_monsters(definition)
    spells = load_spells()
    policy, monster_policy = strategy_policy(strategy), strategy_policy(monster_strategy)
    rng = random.Random(seed)
    results = []
    for _ in range(runs):
        actors = [Combatant.from_sheet(sheet, f"party_{i}", "party") for i, sheet in enumerate(sheets)]
        results.append(run_day(actors, definition, spells, rng.getrandbits(64), policy=policy,
                               monster_policy=monster_policy, max_rounds=max_rounds, monster_sheets=monsters))
    encounters = []
    for index in range(sum("encounter" in step for step in definition["steps"])):
        reached = [r.encounters[index] for r in results if len(r.encounters) > index]
        resources = Counter()
        slots = Counter()
        for result in reached:
            for state in result.start.values():
                resources.update(state["resources"])
                resources["hit_dice"] += state["hit_dice"]
                slots.update(state["slots"])
        count = len(reached)
        encounters.append({"index": index + 1, "reached": count,
                           "mean_start_hp_percent": mean(100 * sum(c["hp"] for c in r.start.values()) / sum(c["max_hp"] for c in r.start.values()) for r in reached) if count else None,
                           "mean_slots_start": {k: v / count for k, v in sorted(slots.items())},
                           "mean_resources_start": {k: v / count for k, v in sorted(resources.items())},
                           "mean_downs": mean(r.downs for r in reached) if count else None,
                           "mean_rounds": mean(r.rounds for r in reached) if count else None})
    survived = sum(r.survived for r in results)
    distribution = dict(sorted(Counter(r.encounters_cleared for r in results).items()))
    return DaySummary(definition["name"], runs, seed, strategy, monster_strategy, survived, survived / runs, distribution, encounters)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--party", nargs="+", required=True)
    parser.add_argument("--day", required=True)
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--strategy", choices=STRATEGIES, default="default")
    parser.add_argument("--monster-strategy", choices=STRATEGIES, default="default")
    parser.add_argument("--max-rounds", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        summary = simulate_day(args.party, args.day, args.runs, args.seed, strategy=args.strategy,
                               monster_strategy=args.monster_strategy, max_rounds=args.max_rounds)
    except (ValueError, OSError) as exc: parser.error(str(exc))
    if args.json:
        print(json.dumps(asdict(summary), sort_keys=True))
        return
    print(f"{summary.name}: P(survive) = {summary.survival_probability:.1%} ({summary.survived}/{summary.runs})")
    print("Encounters cleared: " + json.dumps(summary.encounters_cleared_distribution, sort_keys=True))
    print("Encounter  Reached  Start HP%  Slots left (level: mean)     Downs  Rounds")
    for encounter in summary.encounters:
        if not encounter["reached"]:
            print(f"{encounter['index']:9}        0  --         --                           --     --")
            continue
        slots = ", ".join(f"{k}: {v:.2f}" for k, v in encounter["mean_slots_start"].items())
        print(f"{encounter['index']:9}  {encounter['reached']:7}  {encounter['mean_start_hp_percent']:9.2f}  {slots:27}  {encounter['mean_downs']:5.2f}  {encounter['mean_rounds']:6.2f}")
    print("Per-encounter means are conditional on reaching that encounter.")


if __name__ == "__main__": main()
