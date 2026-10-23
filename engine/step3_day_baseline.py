"""Measure the changed day baseline and prove its Command-only provenance."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

from . import day
from .policy import Policy


class WithoutCommand(Policy):
    def allow_spell(self, combat, actor, spec):
        return spec["name"] != "Command" and super().allow_spell(combat, actor, spec)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--runs", type=int, default=1000)
    p.add_argument("--seed", type=int, default=1)
    args = p.parse_args()
    factory = day.strategy_policy
    records = {}
    output = Path(__file__).with_name("step3_day_baselines.json")
    try:
        for phase in ("after", "command_disabled"):
            day.strategy_policy = factory if phase == "after" else lambda name: WithoutCommand() if name == "default" else factory(name)
            records[phase] = {}
            for strategy in ("nova", "conservative"):
                result = day.simulate_day(day="goblin_warren", runs=args.runs, seed=args.seed, strategy=strategy)
                records[phase][strategy] = asdict(result)
                output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf8")
                print(phase, strategy, result.survived, result.encounters_cleared_distribution, flush=True)
    finally:
        day.strategy_policy = factory
    if args.runs == 1000 and args.seed == 1:
        legacy = records["command_disabled"]
        assert (legacy["nova"]["survived"], legacy["conservative"]["survived"]) == (128, 163)
        assert legacy["nova"]["encounters_cleared_distribution"] == {2: 11, 3: 98, 5: 431, 6: 332, 7: 128}
        assert legacy["conservative"]["encounters_cleared_distribution"] == {1: 1, 2: 59, 3: 192, 4: 1, 5: 412, 6: 172, 7: 163}
    output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf8")


if __name__ == "__main__": main()
