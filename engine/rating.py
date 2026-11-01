"""Party rating against the frozen benchmark set.

A party's rating for an opponent type is the encounter XP at which its chance
of defeat (TPK, or every PC still standing dominated or out of the fight)
reaches a threshold, 5% by default. Each type's ladder in the benchmark is run
from full resources, and the rating is interpolated linearly in XP between the
last ladder step below the threshold and the first at or above it. A party
that crosses on the first step is rated "below" that step's XP, and one that
never crosses is rated "above" the last step's. The overall rating is the
geometric mean of the type ratings, using those bounds for censored types.

Ratings are reported in total XP, XP per character, and as a multiple of the
2024 DMG High budget per character for the party's level (1.00x means the
party reaches the threshold exactly at High).

    python -m engine.rating --party fighter_5 cleric_5 rogue_5 wizard_5
    python -m engine.rating --party fighter_5 cleric_5 rogue_5 wizard_5 --strategy nova --write
"""
import argparse
from concurrent.futures import FIRST_COMPLETED, Future, ProcessPoolExecutor, wait
from dataclasses import asdict, dataclass, field
import json
import math
import os
import random
import sys

from .benchmark import default_version, encounter_xp, load_benchmark
from .calibration import BUDGETS, REPORTS
from .day_options import MORALE
from .encounters import party_sheets, run_encounter, wilson
from .policy import STRATEGIES

THRESHOLD = 0.05


# Sampling for one ladder step, in 50-run batches: stop once the defeat interval
# clears the threshold, or it is pinned to +/-2 points, or at 800 runs.
BATCH, MIN_RUNS, MAX_RUNS, PRECISION = 50, 50, 800, 0.02


@dataclass
class TypeRating:
    kind: str
    xp: float            # rating in total encounter XP (a bound when censored)
    censored: str = ""   # "", "below" or "above"
    steps: list = field(default_factory=list)  # [encounter, xp, defeat, runs, ci]


@dataclass
class PartyRating:
    builds: list
    level: int
    size: int
    threshold: float
    seed: int
    strategy: str
    morale: str
    benchmark: int
    types: dict
    xp: float
    runs: int

    @property
    def high(self):
        return BUDGETS[self.level][2]

    def per_char(self, xp): return xp / self.size

    def multiple(self, xp): return xp / self.size / self.high


def crossing(steps, threshold):
    """Interpolated XP where defeat first reaches the threshold, and censoring."""
    for i, (_, xp, defeat, *_rest) in enumerate(steps):
        if defeat >= threshold:
            if i == 0: return xp, "below"
            _, xp0, d0, *_r = steps[i - 1]
            return xp0 + (threshold - d0) / (defeat - d0) * (xp - xp0), ""
    return steps[-1][1], "above"


def batch_seed(seed, encounter, index):
    """Deterministic seed for one 50-run batch of one ladder step."""
    return random.Random(f"{seed}:{encounter}:{index}").getrandbits(64)


def _probe(task):
    builds, encounter, seed, runs, strategy, morale = task
    return run_encounter(builds, [encounter], runs, seed, morale=morale, strategy=strategy)


class Step:
    """One ladder step's batches. The step's result is the shortest prefix of its
    batches (in batch order) that meets the stop rule, so extra batches run early
    on spare workers never change it."""

    def __init__(self, kind, index, encounter):
        self.kind, self.index, self.encounter = kind, index, encounter
        self.batches = {}      # batch index -> run_encounter result
        self.submitted = 0
        self.decided = None    # number of batches in the final prefix

    def totals(self, m):
        parts = [self.batches[b] for b in range(m)]
        n = sum(r["runs"] for r in parts)
        defeats = sum(r["defeat"] * r["runs"] for r in parts if r["runs"])
        errors = {}
        for r in parts: errors.update(r["errors"])
        return n, n + sum(r["failed_runs"] for r in parts), defeats, errors

    def evaluate(self, threshold):
        m = 0
        while self.decided is None and m in self.batches:  # contiguous prefix only
            m += 1
            n, attempted, defeats, errors = self.totals(m)
            if errors or attempted >= MAX_RUNS or n == 0: self.decided = m; break
            if attempted < MIN_RUNS: continue
            lo, hi = wilson(defeats / n, n)
            if not (lo < threshold < hi) or (hi - lo) / 2 <= PRECISION: self.decided = m

    def result(self):
        n, attempted, defeats, errors = self.totals(self.decided)
        lo, hi = wilson(defeats / n, n) if n else (0.0, 1.0)
        return {"defeat": defeats / n if n else 0.0, "runs": n, "failed_runs": attempted - n,
                "ci": {"defeat": (hi - lo) / 2}, "errors": errors}


def confirmed(result, threshold):
    """The step's defeat interval lies entirely at or above the threshold."""
    return result["runs"] > 0 and wilson(result["defeat"], result["runs"])[0] >= threshold


class _Inline:
    """Runs submitted work immediately; a stand-in executor for tests."""
    def __init__(self, workers=1): self.workers = workers
    def __enter__(self): return self
    def __exit__(self, *exc): return False
    def submit(self, fn, arg):
        f = Future(); f.set_result(fn(arg)); return f


def rate_party(builds, *, threshold=THRESHOLD, seed=1, strategy="default", morale="none", benchmark=None, workers=None,
               probe=_probe, executor=None):
    """Rate a party. probe and executor (a context-managed object with submit) can be replaced in tests."""
    from .day_options import DayOptions
    sheets = party_sheets(builds, DayOptions())
    level = round(sum(s["level"] for s in sheets) / len(sheets))
    if benchmark is None: benchmark = default_version(level)
    data = load_benchmark(benchmark)
    if level not in data["levels"]: raise ValueError(f"benchmark v{benchmark} has no level {level}")
    ladders = data["levels"][level]
    # Steps run smallest first, interleaved across types. Once a step is decided and
    # confidently at or above the threshold, larger steps of that type cannot change
    # the crossing, so they get no further batches and are left out of the report.
    steps = {(kind, i): Step(kind, i, e) for kind, ladder in ladders.items() for i, e in enumerate(ladder)}
    order = sorted(steps.values(), key=lambda st: (st.index, st.kind))
    limit = workers or os.cpu_count() or 1
    performed = 0

    def ceiling(kind):
        done = [st.index for st in order if st.kind == kind and st.decided is not None and confirmed(st.result(), threshold)]
        return min(done) if done else None

    def next_batch():
        live = [st for st in order if st.decided is None and (ceiling(st.kind) is None or st.index < ceiling(st.kind))]
        # First a batch every live step still needs (its first, or one past all it has), then spare batches.
        for st in live:
            if st.submitted == len(st.batches): return st
        for st in live:
            if st.submitted < MAX_RUNS // BATCH: return st
        return None

    with (executor or ProcessPoolExecutor(max_workers=workers)) as pool:
        running = {}
        while True:
            while len(running) < limit:
                st = next_batch()
                if st is None: break
                job = (list(builds), st.encounter, batch_seed(seed, st.encounter, st.submitted), BATCH, strategy, morale)
                running[pool.submit(probe, job)] = (st, st.submitted)
                st.submitted += 1
            if not running: break
            finished, _ = wait(running, return_when=FIRST_COMPLETED)
            for future in finished:
                st, index = running.pop(future)
                r = future.result()
                performed += r["runs"] + r["failed_runs"]
                st.batches[index] = r
                st.evaluate(threshold)
    by_kind = {kind: [] for kind in ladders}
    for kind, ladder in ladders.items():
        for i, encounter in enumerate(ladder):
            st = steps[kind, i]
            if st.decided is None: break
            r = st.result()
            if r["errors"]: raise RuntimeError(f"{encounter}: engine errors {r['errors']}")
            by_kind[kind].append([encounter, encounter_xp([encounter]), r["defeat"], r["runs"], r["ci"]["defeat"]])
            if confirmed(r, threshold): break
    types = {}
    for kind, steps_ in by_kind.items():
        xp, censored = crossing(steps_, threshold)
        types[kind] = TypeRating(kind, xp, censored, steps_)
    overall = math.exp(sum(math.log(t.xp) for t in types.values()) / len(types))
    return PartyRating(list(builds), level, len(builds), threshold, seed, strategy, morale, benchmark, types, overall,
                       performed)


def describe(rating, xp, censored=""):
    mark = {"below": "< ", "above": "> "}.get(censored, "")
    return f"{mark}{xp:,.0f} XP ({mark}{rating.per_char(xp):,.0f} per PC, {mark}{rating.multiple(xp):.2f}x High)"


def markdown(rating):
    censored = [t.kind for t in rating.types.values() if t.censored]
    out = [f"# Party rating: {', '.join(rating.builds)}", "",
           f"Level {rating.level}, {rating.size} PCs; benchmark v{rating.benchmark}; defeat threshold {rating.threshold:.0%}; "
           f"party strategy `{rating.strategy}`; morale `{rating.morale}`; seed {rating.seed}; {rating.runs:,} runs.", "",
           "The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing "
           "dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per "
           f"character at level {rating.level} ({rating.high} XP).", "",
           f"**Overall: {describe(rating, rating.xp)}**, the geometric mean of the types"
           + (f" (bounds used for {', '.join(censored)})." if censored else "."), "",
           "| Opponent type | Rating | Per PC | × High |", "| --- | ---: | ---: | ---: |"]
    for t in rating.types.values():
        mark = {"below": "< ", "above": "> "}.get(t.censored, "")
        out.append(f"| {t.kind} | {mark}{t.xp:,.0f} | {mark}{rating.per_char(t.xp):,.0f} | {mark}{rating.multiple(t.xp):.2f} |")
    out += ["", "## Ladder results", "", "Defeat chance at each benchmark step, with its 95% half-width and run count.", ""]
    for t in rating.types.values():
        out += [f"### {t.kind}", "", "| Encounter | XP | Defeat | ± | Runs |", "| --- | ---: | ---: | ---: | ---: |"]
        out += [f"| {e} | {xp:,} | {d:.1%} | {ci:.1%} | {n} |" for e, xp, d, n, ci in t.steps]
        out.append("")
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--party", nargs="+", required=True, help="build names, e.g. fighter_5 cleric_5")
    parser.add_argument("--threshold", type=float, default=THRESHOLD, help="defeat chance that defines the rating")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--strategy", choices=list(STRATEGIES), default="default", help="party AI strategy")
    parser.add_argument("--morale", choices=MORALE, default="none")
    parser.add_argument("--benchmark", type=int, help="frozen benchmark version (default: 1 up to level 10, 2 above)")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--name", help="report name for --write (default: the build names)")
    parser.add_argument("--write", action="store_true", help="write data/reports/rating_<name>.{md,json}")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if not 0 < args.threshold < 1: parser.error("threshold must be between 0 and 1")
    try:
        rating = rate_party(args.party, threshold=args.threshold, seed=args.seed, strategy=args.strategy,
                            morale=args.morale, benchmark=args.benchmark, workers=args.workers)
    except (ValueError, OSError) as exc: parser.error(str(exc))
    text = markdown(rating)
    if args.write:
        name = args.name or "_".join(args.party)
        (REPORTS / f"rating_{name}.md").write_text(text, encoding="utf-8")
        data = asdict(rating)
        data["types"] = {k: asdict(v) for k, v in rating.types.items()}
        (REPORTS / f"rating_{name}.json").write_text(json.dumps(data, indent=1), encoding="utf-8")
    print(text)


if __name__ == "__main__": main()
