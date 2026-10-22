"""CLI and reusable deterministic Monte Carlo runner."""
import argparse
from collections import Counter
from dataclasses import asdict, dataclass
import json
import random
from statistics import mean

from .combat import Combat
from .loader import ROOT, load_sheet, load_spells
from .state import Combatant


@dataclass(frozen=True)
class Summary:
    runs: int
    seed: int
    wins: int
    draws: int
    win_rate: float
    mean_rounds: float
    mean_party_hp: float
    mean_resources_spent: dict[str, float]


def expand_monsters(tokens):
    result = []
    for token in tokens:
        if token.startswith("x") and token[1:].isdigit():
            if not result or int(token[1:]) < 1: raise ValueError("xN must follow a monster and N must be positive")
            result.extend([result[-1]] * (int(token[1:]) - 1))
        else: result.append(token)
    return result


def simulate(party=("fighter5", "cleric5"), monsters=("ogre",), runs=1000, seed=1, *, policy=None, area=None, max_rounds=100):
    if runs < 1: raise ValueError("runs must be positive")
    if max_rounds < 1: raise ValueError("max_rounds must be positive")
    if not party or not monsters: raise ValueError("both sides need at least one combatant")
    def sheets(folder, names):
        result = []
        for name in names:
            if not name.replace("_", "").isalnum(): raise ValueError(f"invalid sheet name: {name}")
            result.append(load_sheet(ROOT / folder / (name + ".yaml")))
        return result
    party_sheets = sheets("characters", party)
    monster_sheets = sheets("monsters", expand_monsters(monsters))
    spells = load_spells()
    seed_rng = random.Random(seed)
    results = []
    resources = Counter()
    for _ in range(runs):
        actors = [Combatant.from_sheet(s, f"party_{i}", "party") for i, s in enumerate(party_sheets)]
        actors += [Combatant.from_sheet(s, f"enemy_{i}", "enemy") for i, s in enumerate(monster_sheets)]
        combat = Combat(actors, spells, seed=seed_rng.getrandbits(64), policy=policy, area=area)
        combat.record_log = False
        result = combat.run(max_rounds)
        results.append(result)
        resources.update(result["resources"])
    wins = sum(r["winner"] == "party" for r in results)
    return Summary(runs, seed, wins, sum(r["winner"] is None for r in results), wins / runs,
                   mean(r["rounds"] for r in results), mean(r["hp"] for r in results),
                   {k: v / runs for k, v in sorted(resources.items())})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--party", nargs="+", required=True)
    parser.add_argument("--monsters", nargs="+", required=True)
    parser.add_argument("--runs", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--max-rounds", type=int, default=100)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        summary = simulate(args.party, args.monsters, args.runs, args.seed, max_rounds=args.max_rounds)
    except (ValueError, OSError) as exc: parser.error(str(exc))
    if args.json:
        print(json.dumps(asdict(summary), sort_keys=True))
    else:
        print(f"Win rate: {summary.win_rate:.1%} ({summary.wins}/{summary.runs}); draws: {summary.draws}")
        print(f"Mean rounds: {summary.mean_rounds:.3f}")
        print(f"Mean party HP remaining: {summary.mean_party_hp:.3f}")
        print("Mean resources spent: " + json.dumps(summary.mean_resources_spent, sort_keys=True))


if __name__ == "__main__": main()
