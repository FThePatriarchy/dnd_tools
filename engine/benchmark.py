"""Frozen benchmark encounter set for party ratings.

The benchmark lists, for each party level and opponent type, a ladder of
encounters of increasing XP. It is generated once by fixed rules (--freeze)
and committed as data/benchmarks/benchmark_v<N>.yaml; ratings read only that
file, so later roster or monster changes need a new version, never an edit.

    python -m engine.benchmark --freeze --version 1

Freeze rules, for a party of four at each level 1-10:
- Count types (brute, ranged, caster, swarm, control) use one roster monster
  per level: the one whose XP is nearest, on a log scale, to the level's Low
  budget divided by 3 (swarm: by 6). Its ladder is the counts in COUNTS, up to
  the first that reaches 2.5x the High budget.
- The solo type is a ladder of single monsters from SOLO whose XP lies between
  a quarter of the Low budget and 3x the High budget.
"""
import argparse
from functools import lru_cache
import math

import yaml

from .calibration import BUDGETS, XP_BY_CR
from .day import encounter_names
from .loader import ROOT, load_sheet

BENCHMARKS = ROOT.parent / "benchmarks"
PARTY_SIZE = 4
COUNTS = (1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24)
REACH = 2.5  # ladders extend to 2.5x the High budget

TYPES = {
    "brute": ("Heavy melee hitters with no ranged attacks, spells or areas.", 3,
              ["worg", "brown_bear", "berserker", "ogre", "owlbear", "minotaur_of_baphomet", "troll", "gladiator", "wyvern", "bone_devil"]),
    "ranged": ("Monsters with ranged attacks that reach the back row.", 3,
               ["skeleton", "scout", "spy", "bandit_captain", "manticore", "barbed_devil", "assassin"]),
    "caster": ("Spellcasting monsters.", 3,
               ["cultist_fanatic", "priest", "mage_apprentice", "mage"]),
    "swarm": ("Many weaker bodies: a sixth of the Low budget each.", 6,
              ["kobold_warrior", "goblin_warrior", "hobgoblin_warrior", "bugbear_warrior", "warrior_veteran", "guard_captain"]),
    "control": ("Threat through conditions: paralysis, restraint, petrification, fear, life drain.", 3,
                ["ghoul", "giant_spider", "ghast", "basilisk", "mummy", "vampire_spawn", "chain_devil"]),
}
SOLO = ("One creature, laddered by challenge rating.",
        ["ogre", "owlbear", "troll", "young_white_dragon", "young_black_dragon", "young_green_dragon",
         "young_blue_dragon", "young_red_dragon", "adult_red_dragon"])


@lru_cache(maxsize=None)
def monster_xp(name):
    return XP_BY_CR[str(load_sheet(ROOT / "monsters" / (name + ".yaml"))["cr"])]


def encounter_xp(encounter):
    return sum(monster_xp(n) for n in encounter_names(encounter))


def freeze():
    """Build the benchmark from the freeze rules (see the module docstring)."""
    xp = {name: monster_xp(name) for _, _, roster in TYPES.values() for name in roster}
    xp.update({name: monster_xp(name) for name in SOLO[1]})
    levels = {}
    for level, (low, _, high) in BUDGETS.items():
        low_total, high_total = low * PARTY_SIZE, high * PARTY_SIZE
        ladders = {}
        for kind, (_, divisor, roster) in TYPES.items():
            unit = low_total / divisor
            monster = min(roster, key=lambda m: (abs(math.log(xp[m] / unit)), roster.index(m)))
            ladder = []
            for n in COUNTS:
                ladder.append(f"{monster} x{n}")
                if n * xp[monster] >= REACH * high_total: break
            ladders[kind] = ladder
        ladders["solo"] = [f"{m} x1" for m in sorted(SOLO[1], key=lambda m: (xp[m], SOLO[1].index(m)))
                           if low_total / 4 <= xp[m] <= 3 * high_total]
        levels[level] = ladders
    types = {k: {"description": d, "roster": r} for k, (d, _, r) in TYPES.items()}
    types["solo"] = {"description": SOLO[0], "roster": SOLO[1]}
    return {"party_size": PARTY_SIZE, "types": types, "levels": levels}


def path_for(version):
    return BENCHMARKS / f"benchmark_v{version}.yaml"


def load_benchmark(version=1):
    """The frozen benchmark, validated: every ladder rises in XP and every monster exists."""
    data = yaml.safe_load(path_for(version).read_text(encoding="utf-8"))
    if data.get("version") != version: raise ValueError(f"{path_for(version)} is not version {version}")
    for level, ladders in data["levels"].items():
        for kind, ladder in ladders.items():
            if kind not in data["types"]: raise ValueError(f"level {level}: unknown type {kind}")
            values = [encounter_xp([e]) for e in ladder]
            if values != sorted(values): raise ValueError(f"level {level} {kind}: ladder XP must not decrease")
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--freeze", action="store_true", help="write a new frozen benchmark version")
    parser.add_argument("--version", type=int, default=1)
    args = parser.parse_args()
    if not args.freeze: parser.error("nothing to do; pass --freeze")
    path = path_for(args.version)
    if path.exists(): parser.error(f"{path} is frozen; freeze a new --version instead of overwriting it")
    data = {"version": args.version, **freeze()}
    path.parent.mkdir(parents=True, exist_ok=True)
    header = (f"# Frozen benchmark v{args.version}, generated by `python -m engine.benchmark --freeze --version {args.version}`.\n"
              "# Do not edit; freeze a new version instead. Rules: engine/benchmark.py.\n")

    class Flow(yaml.SafeDumper): pass
    Flow.add_representer(list, lambda d, v: d.represent_sequence("tag:yaml.org,2002:seq", v, flow_style=True))
    path.write_text(header + yaml.dump(data, Dumper=Flow, sort_keys=False, width=200), encoding="utf-8")
    load_benchmark(args.version)
    print(f"wrote {path}")


if __name__ == "__main__": main()
