"""Encounter templates: fill a shape (boss, elites, minions) from an XP budget.

A shape gives a count per role. Each role gets XP in the ratio boss 6 : elite
3 : minion 1 per creature, uses a single monster type from the catalogue, and
the whole encounter must land at 75-100% of the budget (the calibration
sweep's window). Among the legal fills, a seeded choice picks from those
nearest the budget, so different seeds give different but equally good
suggestions.

    python -m engine.templates --level 5 --difficulty high --template boss_minions
    python -m engine.templates --level 7 --xp 6000 --shape "1 boss, 6 goons" --suggestions 5
    python -m engine.templates --level 5 --difficulty moderate --template swarm --simulate --profile casual
"""
import argparse
from functools import lru_cache
from itertools import product
import math
import random
import re
import sys

from .benchmark import monster_xp
from .calibration import BUDGETS, DIFFICULTIES, OVER_FACTOR, budget
from .loader import ROOT

ROLES = ("boss", "elite", "minion")
WEIGHTS = {"boss": 6, "elite": 3, "minion": 1}
ALIASES = {"bosses": "boss", "elites": "elite", "minions": "minion", "goon": "minion", "goons": "minion",
           "mook": "minion", "mooks": "minion"}
TEMPLATES = {
    "solo": {"boss": 1},
    "boss_minions": {"boss": 1, "minion": 4},
    "elite_pack": {"elite": 3},
    "swarm": {"minion": 8},
    "mixed": {"elite": 2, "minion": 4},
}
MIN_FILL = 0.75
TIERS_PER_ROLE = 3  # nearest XP tiers considered for each role (every monster in them)
# Calibration outliers left out unless asked for: the gelatinous cube is fearless and
# its Engulf wipes parties far beyond its XP (data/reports/calibration_grab_compare.md).
DEFAULT_EXCLUDE = ("gelatinous_cube",)


@lru_cache(maxsize=None)
def catalogue():
    """Every monster with its XP, smallest first."""
    return tuple(sorted(((monster_xp(p.stem), p.stem) for p in (ROOT / "monsters").glob("*.yaml"))))


def parse_shape(text):
    """'1 boss, 6 goons' -> {'boss': 1, 'minion': 6}."""
    shape = {}
    for part in re.split(r"[,+]| and ", text.lower()):
        part = part.strip()
        if not part: continue
        match = re.fullmatch(r"(\d+)\s*x?\s*([a-z]+)", part)
        if not match: raise ValueError(f"cannot read shape part {part!r}; use e.g. '1 boss, 6 minions'")
        count, role = int(match.group(1)), ALIASES.get(match.group(2), match.group(2))
        if role not in ROLES: raise ValueError(f"unknown role {match.group(2)!r}; roles are boss, elite, minion (goon, mook)")
        if count < 1: raise ValueError("role counts must be positive")
        shape[role] = shape.get(role, 0) + count
    if not shape: raise ValueError("empty shape")
    return shape


def fills(shape, total, *, exclude=DEFAULT_EXCLUDE, monsters=None):
    """Every legal fill of a shape within [MIN_FILL, 1] x total XP, nearest the budget first.

    A fill is a list of (role, monster, count, xp). Roles use distinct monsters."""
    pool = [(xp, name) for xp, name in (monsters or catalogue()) if name not in exclude]
    units = sum(WEIGHTS[r] * n for r, n in shape.items())
    options = {}
    for role, count in shape.items():
        target = total * WEIGHTS[role] / units
        tiers = sorted({xp for xp, _ in pool}, key=lambda xp: abs(math.log(xp / target)))[:TIERS_PER_ROLE]
        options[role] = [m for m in pool if m[0] in tiers]
    roles = list(shape)
    result = []
    for picks in product(*(options[r] for r in roles)):
        names = [name for _, name in picks]
        if len(set(names)) < len(names): continue
        xp = sum(m_xp * shape[r] for r, (m_xp, _) in zip(roles, picks))
        if MIN_FILL * total <= xp <= total:
            result.append(([(r, name, shape[r], m_xp) for r, (m_xp, name) in zip(roles, picks)], xp))
    result.sort(key=lambda f: (total - f[1], [m for _, m, _, _ in f[0]]))
    return result


def suggest(shape, total, *, seed=1, count=3, exclude=DEFAULT_EXCLUDE):
    """Up to count distinct fills: a seeded pick from the closest legal fills."""
    legal = fills(shape, total, exclude=exclude)
    pool = legal[:max(count * 3, count)]
    random.Random(seed).shuffle(pool)
    return sorted(pool[:count], key=lambda f: total - f[1])


def encounter_entries(fill):
    return [f"{name} x{n}" for _, name, n, _ in fill]


def describe(fill, xp, total):
    parts = ", ".join(f"{n} {name.replace('_', ' ')} ({role})" for role, name, n, _ in fill)
    return f"{parts}: {xp:,} XP ({xp / total:.0%} of budget)"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", type=int, required=True, choices=sorted(BUDGETS))
    parser.add_argument("--size", type=int, default=4, help="party size (default 4)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--difficulty", choices=DIFFICULTIES, help=f"DMG slot; 'over' is {OVER_FACTOR}x High")
    group.add_argument("--xp", type=int, help="explicit encounter XP budget")
    shape = parser.add_mutually_exclusive_group(required=True)
    shape.add_argument("--template", choices=list(TEMPLATES))
    shape.add_argument("--shape", help="custom shape, e.g. '1 boss, 6 goons'")
    parser.add_argument("--suggestions", type=int, default=3)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--exclude", nargs="*", default=list(DEFAULT_EXCLUDE),
                        help="monsters to leave out (default: the gelatinous cube; pass --exclude with no names to allow it)")
    parser.add_argument("--simulate", action="store_true", help="run each suggestion against a preset party")
    parser.add_argument("--profile", choices=("casual", "standard", "optimized"), default="standard")
    parser.add_argument("--runs", type=int, default=200)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    try:
        layout = TEMPLATES[args.template] if args.template else parse_shape(args.shape)
    except ValueError as exc: parser.error(str(exc))
    total = args.xp if args.xp else budget(args.level, args.difficulty, args.size)
    picks = suggest(layout, total, seed=args.seed, count=args.suggestions, exclude=set(args.exclude))
    label = args.template or args.shape
    print(f"Level {args.level}, {args.size} PCs, budget {total:,.0f} XP ({args.difficulty or 'explicit'}), shape {label}")
    if not picks:
        print("No fill lands within 75-100% of the budget; try a different shape or budget.")
        return
    party_builds = None
    if args.simulate:
        from .presets import party
        party_builds = party(args.level, args.profile)
        if args.size != 4: parser.error("--simulate uses the four-PC preset party; drop --size")
    for i, (fill, xp) in enumerate(picks, 1):
        line = f"{i}. {describe(fill, xp, total)}"
        if party_builds:
            from .encounters import run_encounter
            r = run_encounter(party_builds, encounter_entries(fill), args.runs, args.seed)
            line += f" | vs {args.profile} party: defeat {r['defeat']:.0%}, someone down {r['down']:.0%}, someone dies {r['death']:.0%}"
        print(line)


if __name__ == "__main__": main()
