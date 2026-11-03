"""Build search: improve one party member's build, one decision at a time.

Starting from a member of your party, each round tries every one-change
neighbour of the current build (a kit, a spell list, a feat, an ability/ASI
plan, a subclass option, a species), measures them in the party with the focused paired
method (engine.focused), and accepts the best change only when its 95%
interval lies above zero. It repeats from the improved build until no change
helps, so changes combine (for example a feat on top of a better kit).

Each round:
1. screen every neighbour with a short focused run (--screen-runs per step);
2. measure the best --finalists, plus up to as many more whose screen interval
   still reaches above the leader's lower bound, with --runs per step;
3. accept the finalist with the highest estimate whose interval excludes zero.

The changes come from engine.compare's generators (variants, feats,
abilities), each turned into the set of recipe fields it changes relative to
the standard build. A change that touches the same fields as another
replaces it (two kits, two ASI plans) rather than stacking.

    python -m engine.optimize --party fighter_5 cleric_5 rogue_5 wizard_5 --member fighter_5
    python -m engine.optimize --party paladin_5 bard_5 monk_5 sorcerer_5 --member sorcerer_5 --write my_sorcerer
"""
import argparse
from copy import deepcopy
from dataclasses import dataclass, field
import json
import sys

import yaml

from .loader import ROOT

DEFAULT_RUNS, DEFAULT_SCREEN_RUNS, DEFAULT_FINALISTS, MAX_ROUNDS = 400, 100, 3, 6


def recipe_of(member):
    """A build name or an in-memory recipe -> a recipe dict with a name."""
    if isinstance(member, dict): return deepcopy(member)
    data = yaml.safe_load((ROOT / "builds" / f"{member}.yaml").read_text(encoding="utf-8"))
    return {"name": member, **data}


def fields_of(recipe):
    """The decision fields of a recipe: (section, key) -> value."""
    out = {("abilities",): recipe.get("abilities"), ("equipment",): recipe.get("equipment")}
    for k, v in (recipe.get("choices") or {}).items(): out["choices", k] = v
    return out


def change_between(base, variant):
    """The fields variant sets differently from base (a change that can be applied to another recipe)."""
    a, b = fields_of(base), fields_of(variant)
    return {k: deepcopy(b[k]) for k in b if a.get(k) != b[k]}


def apply_change(recipe, change, name):
    r = deepcopy(recipe)
    for key, value in change.items():
        if key[0] == "choices": r.setdefault("choices", {})[key[1]] = deepcopy(value)
        else: r[key[0]] = deepcopy(value)
    r["name"] = name
    return r


def legal(recipe):
    from .builder import build
    try: build(recipe["class"], recipe["level"], recipe["subclass"], recipe["abilities"], recipe["equipment"], recipe["choices"])
    except Exception: return False
    return True


def candidate_changes(cls, level):
    """[(label, change)] from compare's generators, relative to the class's standard build; no duplicates."""
    from .compare import ability_variants, species_variants, standard_recipe, variants
    base = standard_recipe(cls, level)
    out, seen = [], set()
    for v in variants(cls, level)[1:] + ability_variants(cls, level)[1:] + species_variants(base):
        change = change_between(base, v)
        key = json.dumps(sorted((list(k), x) for k, x in change.items()), sort_keys=True, default=str)
        if change and key not in seen:
            seen.add(key); out.append((v["name"], change))
    return out


def neighbours(current, changes, applied, visited=()):
    """One-change neighbours of current: each change not already in effect, applied on top.
    Builds in visited (sheet keys of builds the search already stood on) are skipped, so it cannot cycle."""
    out = []
    from .compare import sheet_key
    seen = {sheet_key(current), *visited}
    for label, change in changes:
        if label in applied: continue
        trial = apply_change(current, change, label)
        if not legal(trial): continue
        k = sheet_key(trial)
        if k in seen: continue  # no effect on the sheet, or the same as another neighbour
        seen.add(k); out.append((label, trial))
    return out


@dataclass
class Step:
    round: int
    accepted: str | None
    rating: float                      # the current build's party rating (total XP) at the start of the round
    screened: list = field(default_factory=list)   # [(label, est, lo, hi)]
    finalists: list = field(default_factory=list)  # [(label, est, lo, hi, per-type)]


def optimize(party, member, *, seed=1, runs=DEFAULT_RUNS, screen_runs=DEFAULT_SCREEN_RUNS, finalists=DEFAULT_FINALISTS,
             max_rounds=MAX_ROUNDS, strategy="default", cover=False, workers=None, changes=None, comparison=None, log=print,
             max_extra=None):
    """Hill-climb one member's build in a party. Returns (final recipe, [Step]).

    comparison(builds, runs) -> a FocusedComparison-like object; replaceable in tests."""
    from .focused import FocusedComparison
    if comparison is None:
        comparison = lambda builds, n: FocusedComparison(builds, seed=seed, runs=n, strategy=strategy, cover=cover, workers=workers)
    index = party.index(member)
    current = recipe_of(member)
    current["name"] = current.get("name", "start")
    if changes is None: changes = candidate_changes(current["class"], current["level"])
    if max_extra is None: max_extra = finalists  # at most twice the top-N count gets the full measurement
    by_label = dict(changes)
    applied, steps = [], []  # labels of the changes in effect, in the order accepted
    from .compare import sheet_key
    visited = {sheet_key(current)}
    for rnd in range(1, max_rounds + 1):
        trial_party = lambda r: [r if i == index else b for i, b in enumerate(party)]
        options = neighbours(current, changes, applied, visited)
        if not options: break
        screen = comparison(trial_party(current), screen_runs)
        step = Step(rnd, None, screen.base_rating.xp)
        scored = []
        for label, r in options:
            ch = screen.change(screen.measure(label, trial_party(r)))["overall"]
            scored.append((label, r, *ch))
        scored.sort(key=lambda x: -x[2])
        step.screened = [(l, e, lo, hi) for l, _, e, lo, hi in scored]
        log(f"round {rnd}: screened {len(scored)} changes; best {scored[0][0]} {scored[0][2]:+.1%}")
        leader_lo = scored[0][3]
        # The top finalists, plus changes whose screen interval still reaches the leader's lower bound,
        # capped at max_extra (highest upper bound first): a 100-run screen is wide enough to let most through.
        extra = sorted((s for s in scored[finalists:] if s[4] > leader_lo), key=lambda s: -s[4])[:max_extra]
        chosen = scored[:finalists] + extra
        full = comparison(trial_party(current), runs)
        best = None
        for label, r, *_ in chosen:
            ch = full.change(full.measure(label, trial_party(r)))
            step.finalists.append((label, *ch["overall"], {k: v[:3] for k, v in ch.items() if k != "overall"}))
            est, lo, hi = ch["overall"]
            log(f"  {label}: {est:+.1%} ({lo:+.1%} to {hi:+.1%})")
            if lo > 0 and (best is None or est > best[1]): best = (label, est, r)
        steps.append(step)
        if best is None:
            log(f"round {rnd}: no change is clearly better; stopping")
            break
        step.accepted = best[0]
        log(f"round {rnd}: accepted {best[0]} ({best[1]:+.1%})")
        # A change that rewrites fields an earlier one set replaces it (e.g. an ASI plan over a feat's ASI).
        touched = set(by_label[best[0]])
        replaced = [a for a in applied if set(by_label[a]) & touched]
        if replaced: log(f"  {best[0]} replaces {', '.join(replaced)}")
        applied = [a for a in applied if a not in replaced] + [best[0]]
        current = deepcopy(best[2]); current["name"] = " + ".join(applied)
        visited.add(sheet_key(current))
    return current, steps


def markdown(party, member, final, steps, runs, screen_runs):
    from .compare import label
    out = [f"# Build search: {label(member)}", "",
           f"Party: {', '.join(label(b) for b in party)}. Each round tries every one-change neighbour of the current build, "
           f"screens them with a short focused run ({screen_runs} runs per bracket step), measures the leaders with {runs} runs per step "
           "(`engine.focused`, paired with shared seeds), and accepts the best change whose 95% interval is above zero.", ""]
    for s in steps:
        out += [f"## Round {s.round}", "", f"Party rating at the start: {s.rating:,.0f} XP.", "",
                "| Finalist | Change | 95% interval |", "| --- | ---: | --- |"]
        out += [f"| {l}{' **(accepted)**' if l == s.accepted else ''} | {e:+.1%} | {lo:+.1%} to {hi:+.1%} |" for l, e, lo, hi, _ in s.finalists]
        out += ["", f"<details><summary>Screen ({len(s.screened)} changes)</summary>", "", "| Change | Screen | Interval |", "| --- | ---: | --- |"]
        out += [f"| {l} | {e:+.1%} | {lo:+.1%} to {hi:+.1%} |" for l, e, lo, hi in s.screened]
        out += ["", "</details>", ""]
    accepted = [s.accepted for s in steps if s.accepted]
    out += ["## Result", "", (f"Accepted, in order: {', '.join(accepted)}. In effect: {final['name']}.") if accepted else
            "No change was clearly better than the starting build.", "", "```yaml",
            yaml.safe_dump({k: v for k, v in final.items() if k != "name"}, sort_keys=False).rstrip(), "```", ""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--party", nargs="+", required=True, help="build names")
    parser.add_argument("--member", required=True, help="the member of --party to improve")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="runs per bracket step for finalists")
    parser.add_argument("--screen-runs", type=int, default=DEFAULT_SCREEN_RUNS, help="runs per bracket step for the screen")
    parser.add_argument("--finalists", type=int, default=DEFAULT_FINALISTS)
    parser.add_argument("--rounds", type=int, default=MAX_ROUNDS)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--strategy", default="default")
    parser.add_argument("--cover", action="store_true")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--write", metavar="NAME", help="write data/reports/optimize_NAME.md and the final recipe as optimize_NAME.yaml")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.member not in args.party: parser.error("--member must be one of --party")
    log = lambda m: print(m, file=sys.stderr, flush=True)
    final, steps = optimize(args.party, args.member, seed=args.seed, runs=args.runs, screen_runs=args.screen_runs,
                            finalists=args.finalists, max_rounds=args.rounds, strategy=args.strategy, cover=args.cover,
                            workers=args.workers, log=log)
    text = markdown(args.party, args.member, final, steps, args.runs, args.screen_runs)
    if args.write:
        from .calibration import REPORTS
        (REPORTS / f"optimize_{args.write}.md").write_text(text, encoding="utf-8")
        (REPORTS / f"optimize_{args.write}.yaml").write_text(yaml.safe_dump({k: v for k, v in final.items() if k != "name"}, sort_keys=False), encoding="utf-8")
    print(text)


if __name__ == "__main__": main()
