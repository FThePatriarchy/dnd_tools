"""Encounter and day finder: search one difficulty setting until a party's risk hits a target.

Targets are a primary target (metric=value, matched as closely as possible)
and limits (metric<=value or metric>=value, which the answer must meet). With
limits only, the finder returns the hardest setting that meets them.

The single setting is a scale on the 2024 DMG budget. The encounter finder
scales the High budget and fills a template or shape (engine.templates). The
day finder scales the Moderate budget of every encounter in a day plan. The
search scans scales coarsely in parallel, then refines inside the bracket
where the target or a limit is crossed. Each distinct encounter or day is
simulated once per sample size, with a seed derived from its contents.

    python -m engine.finder encounter --level 5 --template boss_minions --target down=0.5 --limit defeat<=0.02
    python -m engine.finder day --level 5 --plan "E E S E E S E E" --template mixed --limit death<=0.05 --target slots_left=0.15
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
import json
import random
import re
import sys

from .calibration import BUDGETS, REPORTS, budget
from .encounters import DAY_METRICS, run_day_runs, run_encounter, wilson
from .policy import STRATEGIES
from .templates import DEFAULT_EXCLUDE, TEMPLATES, describe, encounter_entries, parse_shape, suggest

ENCOUNTER_METRICS = ("win", "tpk", "defeat", "down", "death", "hp_lost", "slots_spent", "rounds", "fled")
BINARY = {"win", "tpk", "defeat", "down", "death", "complete"}
ENCOUNTER_SCALES = tuple(round(0.25 * 1.3 ** i, 3) for i in range(10))   # 0.25x .. ~2.7x High
DAY_SCALES = tuple(round(0.25 * 1.3 ** i, 3) for i in range(9))          # 0.25x .. ~2.0x Moderate
COARSE_RUNS, FINE_RUNS, REFINE_ROUNDS, REFINE_POINTS = 100, 400, 2, 3
TOLERANCE = 0.1  # a recommendation further than this from the target gets an explanatory note


def parse_target(text, metrics):
    match = re.fullmatch(r"\s*([a-z_]+)\s*=\s*([0-9.]+)\s*", text)
    if not match or match.group(1) not in metrics: raise ValueError(f"target must be metric=value with metric in {', '.join(metrics)}")
    return match.group(1), float(match.group(2))


def parse_limit(text, metrics):
    match = re.fullmatch(r"\s*([a-z_]+)\s*(<=|>=)\s*([0-9.]+)\s*", text)
    if not match or match.group(1) not in metrics: raise ValueError(f"limit must be metric<=value or metric>=value with metric in {', '.join(metrics)}")
    return match.group(1), match.group(2), float(match.group(3))


@dataclass
class Point:
    scale: float
    key: str                      # the exact encounter or day, as text
    label: str
    metrics: dict
    runs: int
    detail: dict = field(default_factory=dict)


def meets(point, limits):
    return all(point.metrics[m] <= v if op == "<=" else point.metrics[m] >= v for m, op, v in limits)


def choose(points, target, limits):
    """The best point: meets every limit, then closest to the target (or the hardest scale)."""
    feasible = [p for p in points if meets(p, limits)]
    if not feasible: return None
    if target:
        m, v = target
        return min(feasible, key=lambda p: (abs(p.metrics[m] - v), -p.runs, p.scale))
    return max(feasible, key=lambda p: (p.scale, p.runs))


def bracket(points, target, limits):
    """Adjacent scales between which the target or the feasibility boundary is crossed."""
    pts = sorted({p.scale: p for p in points}.values(), key=lambda p: p.scale)  # latest (largest sample) per scale
    pairs = [(a, b) for a, b in zip(pts, pts[1:]) if a.key != b.key]  # same fill: nothing to refine
    if target:
        m, v = target
        for a, b in pairs:
            if (a.metrics[m] - v) * (b.metrics[m] - v) <= 0 and (meets(a, limits) or meets(b, limits)):
                return a.scale, b.scale
    for a, b in pairs:
        if meets(a, limits) and not meets(b, limits): return a.scale, b.scale
    return None


def search(make, evaluate, scales, target, limits, *, mapper=map, coarse_runs=COARSE_RUNS, fine_runs=FINE_RUNS,
           rounds=REFINE_ROUNDS, interior=REFINE_POINTS):
    """Coarse scan then refinement. make(scale) -> (key, label, job builder) or None when no fill
    exists; evaluate is the picklable job runner; mapper runs jobs (in parallel by default)."""
    cache, points = {}, []

    def run(scale_list, runs):
        fresh = []
        for s in scale_list:
            made = make(s)
            if made is None: continue
            key, label, job = made
            if (key, runs) not in cache:
                cache[key, runs] = None
                fresh.append((key, label, job(runs)))
        for (key, label, _), result in zip(fresh, mapper(evaluate, [j for _, _, j in fresh])):
            if result["errors"]: raise RuntimeError(f"{label}: engine errors {result['errors']}")
            cache[key, runs] = result
        for s in scale_list:
            made = make(s)
            if made is None: continue
            key, label, _ = made
            r = cache[key, runs]
            points.append(Point(s, key, label, {k: r[k] for k in r if k not in {"runs", "failed_runs", "errors", "ci"}}, r["runs"]))

    run(list(scales), coarse_runs)
    for _ in range(rounds):
        span = bracket(points, target, limits)
        if span is None: break
        lo, hi = span
        inner = [lo * (hi / lo) ** (i / (interior + 1)) for i in range(1, interior + 1)]
        run([round(s, 4) for s in inner] + [lo, hi], fine_runs)
    return choose(points, target, limits), points


def derived_seed(seed, key):
    return random.Random(f"{seed}:{key}").getrandbits(64)


def _run_encounter_job(job):
    builds, entries, runs, seed, morale, strategy = job
    return run_encounter(builds, entries, runs, seed, morale=morale, strategy=strategy)


def _run_day_job(job):
    builds, day, runs, seed, morale, strategy = job
    return run_day_runs(builds, day, runs, seed, morale=morale, strategy=strategy)


def find_encounter(builds, level, shape, *, target=None, limits=(), seed=1, morale="none", strategy="default",
                   exclude=DEFAULT_EXCLUDE, scales=ENCOUNTER_SCALES, mapper=None, workers=None):
    high = budget(level, "high", len(builds))

    def make(scale):
        picks = suggest(shape, scale * high, seed=seed, count=1, exclude=exclude)
        if not picks: return None
        fill, xp = picks[0]
        entries = encounter_entries(fill)
        key = " + ".join(entries)
        return key, f"{describe(fill, xp, scale * high)}", lambda runs: (list(builds), entries, runs, derived_seed(seed, key), morale, strategy)

    return _search(make, _run_encounter_job, scales, target, limits, mapper, workers)


def parse_plan(text):
    tokens = text.upper().split()
    if not tokens or set(tokens) - {"E", "S", "L"} or "E" not in tokens:
        raise ValueError("plan is a sequence of E (encounter), S (short rest) and L (long rest), e.g. 'E E S E E'")
    return tokens


def day_for(plan, shapes, total, seed, exclude=DEFAULT_EXCLUDE):
    """A day definition: every E filled at total XP, cycling through shapes, each with its own seed."""
    steps, labels, index = [], [], 0
    for token in plan:
        if token == "S": steps.append({"rest": "short"}); labels.append("short rest"); continue
        if token == "L": steps.append({"rest": "long"}); labels.append("long rest"); continue
        shape = shapes[index % len(shapes)]
        picks = suggest(shape, total, seed=seed + index, count=1, exclude=exclude)
        if not picks: return None
        fill, xp = picks[0]
        steps.append({"encounter": encounter_entries(fill)})
        labels.append(", ".join(f"{n} {m.replace('_', ' ')}" for _, m, n, _ in fill) + f" ({xp:,} XP)")
        index += 1
    return {"name": "finder day", "steps": steps}, labels


def find_day(builds, level, plan, shapes, *, target=None, limits=(), seed=1, morale="none", strategy="default",
             exclude=DEFAULT_EXCLUDE, scales=DAY_SCALES, mapper=None, workers=None):
    moderate = budget(level, "moderate", len(builds))

    def make(scale):
        made = day_for(plan, shapes, scale * moderate, seed, exclude)
        if made is None: return None
        day, labels = made
        key = json.dumps(day["steps"])
        return key, " | ".join(labels), lambda runs: (list(builds), day, runs, derived_seed(seed, key), morale, strategy)

    return _search(make, _run_day_job, scales, target, limits, mapper, workers)


def _search(make, evaluate, scales, target, limits, mapper, workers):
    if mapper is not None: return search(make, evaluate, scales, target, limits, mapper=mapper)
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return search(make, evaluate, scales, target, limits, mapper=lambda f, jobs: pool.map(f, jobs))


def fmt(metric, value, runs):
    if metric in BINARY:
        lo, hi = wilson(value, runs)
        return f"{value:.0%} (±{(hi - lo) / 2:.0%})"
    return f"{value:.1f}" if metric in {"rounds", "downs"} else f"{value:.0%}"


def report(kind, title, best, points, target, limits, metrics, unit):
    goal = ([f"{target[0]} ≈ {target[1]:g}"] if target else []) + [f"{m} {op} {v:g}" for m, op, v in limits]
    out = [f"# {title}", "", f"Goal: {', '.join(goal) or 'none'}. Scale is a multiple of the {unit}.", ""]
    if best is None:
        out += ["**No scale meets the limits.** The easiest point tried is shown first below; loosen a limit or change the shape.", ""]
    else:
        out += [f"**Recommended (scale {best.scale:.2f}×):** {best.label}", "",
                " · ".join(f"{m} {fmt(m, best.metrics[m], best.runs)}" for m in metrics) + f" ({best.runs} runs)", ""]
        if target and abs(best.metrics[target[0]] - target[1]) > TOLERANCE:
            out += [f"Note: no tested {kind} lands within {TOLERANCE:.0%} of the target. Fills change in steps as the "
                    "budget grows, so neighbouring scales can jump past it; the closest one that meets the limits is shown.", ""]
    out += ["## Difficulty curve", "", f"Each distinct {kind} once, at its largest sample, with the scales that produced it.", "",
            "| Scales | Runs | " + " | ".join(metrics) + " | " + kind + " |",
            "| --- | ---: | " + " | ".join("---:" for _ in metrics) + " | --- |"]
    for key, group in distinct(points):
        lo, hi = min(p.scale for p in group), max(p.scale for p in group)
        p = max(group, key=lambda p: p.runs)
        span = f"{lo:.2f}" if lo == hi else f"{lo:.2f}–{hi:.2f}"
        out.append(f"| {span} | {p.runs} | " + " | ".join(fmt(m, p.metrics[m], p.runs) for m in metrics) + f" | {p.label} |")
    return "\n".join(out) + "\n"


def distinct(points):
    """Points grouped by encounter or day, in order of smallest scale."""
    groups = {}
    for p in points: groups.setdefault(p.key, []).append(p)
    return sorted(groups.items(), key=lambda kv: min(p.scale for p in kv[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="kind", required=True)
    for kind in ("encounter", "day"):
        p = sub.add_parser(kind)
        who = p.add_mutually_exclusive_group(required=True)
        who.add_argument("--party", nargs="+", help="build names")
        who.add_argument("--level", type=int, choices=sorted(BUDGETS), help="use a preset party at this level")
        p.add_argument("--profile", choices=("casual", "standard", "optimized"), default="standard")
        shape = p.add_mutually_exclusive_group(required=True)
        shape.add_argument("--template", nargs="+", choices=list(TEMPLATES), help="template(s); a day cycles through them")
        shape.add_argument("--shape", nargs="+", help="custom shape(s), e.g. '1 boss, 6 goons'")
        p.add_argument("--target", help="primary target, e.g. down=0.5")
        p.add_argument("--limit", action="append", default=[], help="e.g. defeat<=0.02 (repeatable)")
        p.add_argument("--seed", type=int, default=1)
        p.add_argument("--strategy", default="default", choices=list(STRATEGIES))
        p.add_argument("--morale", default="none", choices=("none", "dmg", "rout"))
        p.add_argument("--exclude", nargs="*", default=list(DEFAULT_EXCLUDE))
        p.add_argument("--workers", type=int)
        p.add_argument("--write", metavar="NAME", help="write data/reports/finder_<NAME>.md")
        if kind == "day": p.add_argument("--plan", required=True, help="e.g. 'E E S E E S E E'")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    metrics = ENCOUNTER_METRICS if args.kind == "encounter" else DAY_METRICS
    try:
        target = parse_target(args.target, metrics) if args.target else None
        limits = [parse_limit(x, metrics) for x in args.limit]
        shapes = [TEMPLATES[t] for t in args.template] if args.template else [parse_shape(s) for s in args.shape]
        if args.party:
            from .encounters import party_sheets
            from .day_options import DayOptions
            builds = args.party
            level = round(sum(s["level"] for s in party_sheets(builds, DayOptions())) / len(builds))
        else:
            from .presets import party
            builds, level = party(args.level, args.profile), args.level
    except (ValueError, OSError) as exc: parser.error(str(exc))
    if not target and not limits: parser.error("give a --target, at least one --limit, or both")
    common = dict(target=target, limits=limits, seed=args.seed, morale=args.morale, strategy=args.strategy,
                  exclude=set(args.exclude), workers=args.workers)
    if args.kind == "encounter":
        if len(shapes) > 1: parser.error("an encounter takes one template or shape")
        best, points = find_encounter(builds, level, shapes[0], **common)
        title, unit = f"Encounter finder: {', '.join(builds)}", f"DMG High budget for {len(builds)} level-{level} PCs ({budget(level, 'high', len(builds)):,} XP)"
        shown = ("defeat", "down", "death", "hp_lost", "rounds")
    else:
        try: plan = parse_plan(args.plan)
        except ValueError as exc: parser.error(str(exc))
        best, points = find_day(builds, level, plan, shapes, **common)
        title, unit = f"Day finder ({' '.join(plan)}): {', '.join(builds)}", f"DMG Moderate budget per encounter ({budget(level, 'moderate', len(builds)):,} XP)"
        shown = ("complete", "defeat", "death", "cleared", "slots_left", "hp_left", "downs")
    for m in [t[0] for t in ([target] if target else [])] + [m for m, _, _ in limits]:
        if m not in shown: shown = (*shown, m)
    text = report(args.kind, title, best, points, target, limits, shown, unit)
    if args.write: (REPORTS / f"finder_{args.write}.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__": main()
