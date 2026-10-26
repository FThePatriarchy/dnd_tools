"""Persistent adventuring days, 2024 rests, and seeded Monte Carlo summaries."""
import argparse
from collections import Counter
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import random
import re
from statistics import mean

from . import dice
from .combat import Combat
from .loader import ROOT, Validator, load_sheet, load_spells, read_yaml
from .policy import Policy, STRATEGIES, strategy_policy
from .state import Combatant, compare_deadline
from .day_options import MORALE, DayOptions, day_options


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
    v.obj(data, "$", "name steps", "options")
    if "options" in data:
        try: day_options(data["options"])
        except ValueError as exc: v.fail("options", str(exc))
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


def cleanup_encounter(combat, *, preserve_death=False):
    """The gap exceeds every spell/effect duration, even detached end effects."""
    for identifier in list(combat.instances): combat.end_spell(identifier)
    combat.instances.clear()
    for actor in combat.combatants:
        stable = preserve_death and actor.has_status("stable")
        actor.concentration = None
        actor.effects.clear()
        actor.conditions.clear()
        actor.exhaustion_level = 0
        actor.statuses.clear()
        if stable: actor.statuses["stable"] = {}
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


def take_rest(party, kind, rng, policy=None, *, log=None):
    if kind not in {"short", "long"}: raise ValueError("rest must be short or long")
    policy = policy or Policy()
    for actor in party:
        if not actor.alive: continue
        if kind == "long":
            exceptions = actor.statuses.get("long_rest_no_restore", {})
            if not exceptions.get("max_hp") and actor.base_max_hp < actor.original_max_hp:
                actor.base_max_hp = actor.original_max_hp
            for ability, normal in actor.original_abilities.items():
                if not exceptions.get(ability) and actor.abilities[ability] < normal:
                    actor.abilities[ability] = normal
            if not exceptions.get("exhaustion"):
                actor.exhaustion_level = max(0, actor.exhaustion_level - 1)
                if not actor.exhaustion_level: actor.conditions.discard("exhaustion")
            actor.hp = actor.max_hp
            actor.temp_hp = 0
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
        if kind == "short":
            from .class_mechanics import arcane_recovery, memorize_spell
            arcane_recovery(actor, policy, log)
            memorize_spell(actor, policy, log)


class ClockRest:
    """Explicit start/interrupt/resume/finish lifecycle on a Combat's round clock.

    Completion declares the printed sleep/light-activity requirements satisfied.
    Specific non-sleeping/concentration features override ordinary sleep, not time.
    """
    def __init__(self, combat, party, kind, policy=None):
        if kind not in {"short", "long"}: raise ValueError("rest must be short or long")
        if getattr(combat, "resting", None) is not None: raise ValueError("a rest is already in progress")
        self.combat, self.kind, self.policy = combat, kind, policy or combat.policy
        self.party = [a for a in party if a.alive]
        start = combat.time_rounds
        if kind == "long" and any(a.last_long_rest_end is not None and compare_deadline(start, a.last_long_rest_end + 9600) < 0 for a in self.party):
            raise ValueError("must wait 16 hours after finishing a Long Rest before starting another")
        self.deadlines = {a.id: start + (4800 if kind == "long" else 600) for a in self.party}
        self.segment_start = dict.fromkeys(self.deadlines, start)
        self.interrupted = {}
        combat.resting = self
        self.sleep()

    def sleep(self):
        if self.kind == "long":
            for a in self.party:
                if not (a.features.get("no_sleep") or a.has_status("no_sleep") or a.features.get("concentration_while_asleep")) and a.concentration is not None:
                    self.combat.end_spell(a.concentration)

    def interrupt(self, reason, actor=None, *, exertion_rounds=0):
        if getattr(self.combat, "resting", None) is not self: raise ValueError("rest is not in progress")
        if reason not in {"initiative", "spell", "damage", "exertion"}: raise ValueError("unknown rest interruption")
        if reason == "exertion" and (self.kind == "short" or exertion_rounds < 600): return
        for a in self.party:
            if actor is not None and a is not actor or a.id in self.interrupted: continue
            now = self.combat.time_rounds
            if self.kind == "long" and compare_deadline(now, self.segment_start[a.id] + 600) >= 0:
                take_rest([a], "short", self.combat.rng, self.policy)
            self.interrupted[a.id] = now
            self.combat.record("rest_interrupted", actor=a.id, reason=reason, time_rounds=now)

    def resume(self):
        if getattr(self.combat, "resting", None) is not self: raise ValueError("rest is not in progress")
        if self.kind != "long": raise ValueError("an interrupted Short Rest must start over")
        for identifier, stopped in self.interrupted.items():
            self.deadlines[identifier] += self.combat.time_rounds - stopped + 600
            self.segment_start[identifier] = self.combat.time_rounds
        self.interrupted.clear()
        self.sleep()

    def finish(self):
        if getattr(self.combat, "resting", None) is not self: raise ValueError("rest is not in progress")
        if self.interrupted: raise ValueError("interrupted rest: resume the Long Rest or abort and start over")
        if any(compare_deadline(self.combat.time_rounds, deadline) < 0 for deadline in self.deadlines.values()):
            raise ValueError("rest has not lasted long enough")
        take_rest(self.party, self.kind, self.combat.rng, self.policy)
        if self.kind == "long":
            for a in self.party:
                if a.alive: a.last_long_rest_end = self.combat.time_rounds
        self.abort()

    def abort(self):
        if getattr(self.combat, "resting", None) is self: self.combat.resting = None


def snapshot(party):
    return {c.id: {"hp": c.hp, "max_hp": c.max_hp, "temp_hp": c.temp_hp,
                   "slots": c.spell_slots.copy(), "resources": c.limited_uses.copy(),
                   "hit_dice": c.hit_dice, "resources_spent": c.resources_spent.copy(),
                   "dead": c.dead, "deaths": c.deaths, "stable": c.has_status("stable")}
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
    deaths: int = 0
    start_seconds: float = 0
    end_seconds: float = 0
    fled: int = 0


@dataclass(frozen=True)
class DayResult:
    survived: bool
    encounters_cleared: int
    encounters: list[EncounterResult]
    failure_reason: str | None = None
    elapsed_seconds: float = 0
    end_state: dict = field(default_factory=dict)


def day_monsters(day):
    names = {name for step in day["steps"] if "encounter" in step for name in encounter_names(step["encounter"])}
    return {name: load_sheet(ROOT / "monsters" / (name + ".yaml")) for name in sorted(names)}


def _run_legacy_day(party, day, spells, seed=1, *, policy=None, monster_policy=None, max_rounds=100, monster_sheets=None, area=None, target_cap=None):
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
        combat = Combat(party + enemies, spells, seed=rng.getrandbits(64), policy=policy, area=area, monster_policy=monster_policy or Policy(), target_cap=target_cap)
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


def run_day(party, day, spells, seed=1, *, policy=None, monster_policy=None, max_rounds=100, monster_sheets=None, options=None, area=None, target_cap=None):
    """New defaults; use DayOptions.legacy() for the exact prior day model."""
    opts = day_options(day.get("options") if options is None else options)
    if opts == DayOptions.legacy():
        return _run_legacy_day(party, day, spells, seed, policy=policy, monster_policy=monster_policy,
                               max_rounds=max_rounds, monster_sheets=monster_sheets, area=area, target_cap=target_cap)
    validate_day(day)
    if not party or len({c.id for c in party}) != len(party) or any(c.team != "party" for c in party):
        raise ValueError("day needs a nonempty party with unique ids and team='party'")
    if max_rounds < 1: raise ValueError("max_rounds must be positive")
    policy = policy or Policy()
    monsters = day_monsters(day) if monster_sheets is None else monster_sheets
    rng = random.Random(seed)
    combat = Combat(party[:], spells, seed=rng.getrandbits(64), policy=policy, area=area, monster_policy=monster_policy or Policy(), target_cap=target_cap)
    combat.record_log = False
    combat.day_options = opts
    combat.death_rules = opts.death
    results = []
    cleared = 0

    def forecast(index):
        # Known schedule, unknown dice. Three-round encounters are a planning
        # prior only; the actual clock always uses the realized combat rounds.
        when = 0
        combat.future_encounters = []
        combat.encounters_remaining = 0
        # Encounters before the next rest of either kind (short-rest resources come back then).
        upcoming = day["steps"][index:]
        first_rest = next((i for i, f in enumerate(upcoming) if "rest" in f), len(upcoming))
        combat.encounters_until_rest = sum("encounter" in f for f in upcoming[:first_rest])
        for future in day["steps"][index:]:
            if future.get("rest") == "long": break
            if future.get("rest") == "short": when += 600
            elif "encounter" in future:
                combat.future_encounters.append((when, 3))
                combat.encounters_remaining += 1
                when += 3 + opts.gap_minutes * 10
        combat.forecast_enemies = []
        next_encounter = next((s for s in day["steps"][index:] if "encounter" in s), None)
        if next_encounter:
            combat.forecast_enemies = [Combatant.from_sheet(monsters[n], f"forecast_{i}", "enemy") for i, n in enumerate(encounter_names(next_encounter["encounter"]))]

    def buff(phase):
        if opts.prebuffs and combat.future_encounters: policy.precombat_buffs(combat, party, phase)

    forecast(0)
    buff("day_start")
    for step_index, step in enumerate(day["steps"]):
        if "rest" in step:
            # A downed PC cannot begin a rest. Safe rest steps first wait for
            # stabilized companions to wake, then provide the full rest time.
            wakes = [c.stable_wake_at for c in party if not c.dead and c.hp == 0 and c.stable_wake_at is not None]
            if wakes: combat.advance_time(max(0, max(wakes) - combat.time_rounds))
            if hasattr(policy, "before_rest"):
                # Short rests still to come (this one included) before a long rest or the day's end.
                after = day["steps"][step_index:]
                until_long = next((i for i, f in enumerate(after) if f.get("rest") == "long"), len(after))
                policy.before_rest(combat, party, step["rest"], sum(f.get("rest") == "short" for f in after[:until_long]))
            rest = ClockRest(combat, party, step["rest"], policy)
            combat.advance_time(600 if step["rest"] == "short" else 4800)
            rest.finish()
            forecast(step_index + 1)
            buff("after_rest")
            continue
        forecast(step_index)
        buff("before_encounter")
        names = encounter_names(step["encounter"])
        enemies = [Combatant.from_sheet(monsters[name], f"enc{len(results)}_enemy_{i}", "enemy") for i, name in enumerate(names)]
        # Keep summoned allies and spell instances, not defeated enemies.
        summons = [c for c in combat.combatants if c.summoner_id and c.alive and c.team == "party"]
        combat.combatants = [*party, *summons, *enemies]
        combat.initialize_monsters()
        combat.rng.seed(rng.getrandbits(64))
        combat.round = 1
        combat.damage_dealt.clear()
        combat.slots_at_start = {c.id: c.spell_slots.copy() for c in party}
        start = snapshot(party)
        before_downs = {c.id: c.downs for c in party}
        before_deaths = sum(c.deaths for c in party)
        start_time = combat.time_rounds
        outcome = combat.run(max_rounds) if any(c.alive for c in party) else {"winner":"enemy", "rounds":0}
        combat.time_rounds = start_time + outcome["rounds"]
        for c in party: combat.expire("clock", c)
        end_time = combat.time_rounds
        end = snapshot(party)
        downs = {c.id: c.downs - before_downs[c.id] for c in party}
        won = outcome["winner"] == "party"
        if won: cleared += 1
        tpk = not any(c.alive for c in party)
        if not opts.clock: cleanup_encounter(combat,preserve_death=opts.death)
        if won and not tpk:
            combat.combatants = [*party, *summons]
            policy.recover_downed(combat, party)
            combat.settle_downed(party)
            if not opts.clock: cleanup_encounter(combat,preserve_death=opts.death)
        deaths = sum(c.deaths for c in party) - before_deaths
        fled = sum(e.has_status("fled") for e in enemies)
        results.append(EncounterResult(len(results)+1, names, outcome["rounds"], won, start, end,
                                       snapshot(party), sum(downs.values()), downs, deaths, start_time*6, end_time*6, fled))
        if not won:
            reason = "tpk" if tpk else "round_limit" if outcome["winner"] is None else "party_unavailable"
            return DayResult(False, cleared, results, reason, combat.time_rounds*6, snapshot(party))
        combat.combatants = [*party, *summons]
        combat.current = None
        if any("encounter" in s for s in day["steps"][step_index+1:]):
            combat.advance_time(opts.gap_minutes*10)
    survived = not any(c.dead or c.permanently_removed for c in party)
    return DayResult(survived, cleared, results, None if survived else "pc_death", combat.time_rounds*6, snapshot(party))


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
    mean_deaths: float = 0
    mean_downs: float = 0
    mean_slots_end: float = 0
    mean_elapsed_hours: float = 0
    options: dict = field(default_factory=dict)


def simulate_day(party=("fighter5", "cleric5"), day="goblin_warren", runs=1000, seed=1, *, strategy="default", monster_strategy="default", max_rounds=100, options=None):
    if runs < 1: raise ValueError("runs must be positive")
    if max_rounds < 1: raise ValueError("max_rounds must be positive")
    if not party: raise ValueError("party must not be empty")
    definition = load_day(day) if not isinstance(day, dict) else day
    validate_day(definition)
    opts = day_options(definition.get("options") if options is None else options)
    sheets = []
    for entry in party:
        position = None
        if isinstance(entry, dict):
            if set(entry) - {"build", "position"} or "build" not in entry: raise ValueError("party entry needs build and optional position")
            name, position = entry["build"], entry.get("position")
        else:
            name, separator, position = entry.partition(":")
            position = position if separator else None
        if position is not None and position not in {"front", "back"}: raise ValueError("position must be front or back")
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name): raise ValueError(f"invalid sheet name: {name}")
        from .builder import load_character
        sheet = load_character(name, background=opts.backgrounds)
        if position: sheet["position"] = position
        elif "position" not in sheet:
            sheet["position"] = "front" if sheet["ac"] >= 16 and any(a["kind"] == "melee" for a in sheet.get("attacks", [])) else "back"
        sheets.append(sheet)
    monsters = day_monsters(definition)
    spells = load_spells()
    policy, monster_policy = strategy_policy(strategy), strategy_policy(monster_strategy)
    rng = random.Random(seed)
    results = []
    for _ in range(runs):
        actors = [Combatant.from_sheet(sheet, f"party_{i}", "party") for i, sheet in enumerate(sheets)]
        results.append(run_day(actors, definition, spells, rng.getrandbits(64), policy=policy,
                               monster_policy=monster_policy, max_rounds=max_rounds, monster_sheets=monsters, options=opts))
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
                           "mean_deaths": mean(r.deaths for r in reached) if count else None,
                           "mean_rounds": mean(r.rounds for r in reached) if count else None})
    survived = sum(r.survived for r in results)
    distribution = dict(sorted(Counter(r.encounters_cleared for r in results).items()))
    final_states = [r.end_state or (r.encounters[-1].after_healing if r.encounters else {}) for r in results]
    return DaySummary(definition["name"], runs, seed, strategy, monster_strategy, survived, survived / runs, distribution, encounters,
                      mean(sum(c["deaths"] for c in state.values()) for state in final_states),
                      mean(sum(e.downs for e in r.encounters) for r in results),
                      mean(sum(sum(c["slots"].values()) for c in state.values()) for state in final_states),
                      mean(r.elapsed_seconds/3600 for r in results), asdict(opts))


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
    parser.add_argument("--legacy", action="store_true", help="all six realism switches off")
    for name in ("clock", "prebuffs", "death", "backgrounds", "engagement", "spending"):
        parser.add_argument("--"+name, action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--gap-minutes", type=float)
    parser.add_argument("--screen", type=int)
    parser.add_argument("--targeting", choices=("focus_low_hp", "threat", "random"))
    parser.add_argument("--attack-downed", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--morale", choices=MORALE, help="optional DMG morale rule (default: none, fight to the last)")
    args = parser.parse_args()
    try:
        opts = asdict(DayOptions.legacy() if args.legacy else day_options(load_day(args.day).get("options")))
        for key in opts:
            if getattr(args, key, None) is not None: opts[key] = getattr(args, key)
        summary = simulate_day(args.party, args.day, args.runs, args.seed, strategy=args.strategy,
                               monster_strategy=args.monster_strategy, max_rounds=args.max_rounds, options=opts)
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
    print(f"Deaths/day: {summary.mean_deaths:.3f}; downs/day: {summary.mean_downs:.3f}; slots at end: {summary.mean_slots_end:.3f}")


if __name__ == "__main__": main()
