"""Focused, paired build comparison: measure only the ladder steps that decide each rating.

A party rating (engine.rating) interpolates each opponent type's crossing
between the last ladder step below 5% defeat and the first at or above it.
The full rating stops sampling a step as soon as its interval clears 5%, so
the upper step of a bracket is often measured on 50-150 runs (36% +/- 13
points), and that single noisy point sets the crossing. This is why per-type
build values (notably level 5 control) swung by 10-14% for almost any change.

For a comparison only those bracket steps matter, so this module:

1. rates the base party once (the full rating) to find each type's bracket;
2. measures every candidate *and* the base on the bracket steps with the same
   fixed number of runs and the same batch seeds (common random numbers);
3. widens a candidate's bracket when its crossing falls outside it (a lower
   step already at or above the threshold, or an upper one still below);
4. reports each change with a paired bootstrap 95% interval over batches,
   instead of fixed noise bars.

Crossings use engine.rating.crossing on the measured steps, so the numbers are
ratings in the same sense, assuming defeat does not fall as encounters grow
(the full rating assumes the same when it stops at the first crossing).
"""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
import math
import os
import random

from .benchmark import default_version, encounter_xp, load_benchmark
from .encounters import party_sheets
from .rating import BATCH, THRESHOLD, _probe, batch_seed, crossing, rate_party

CONFIDENCE = 0.95
BOOTSTRAP = 2000


@dataclass
class Focused:
    """One party's measured bracket steps: {kind: {ladder index: [defeat per batch]}}."""
    name: str
    builds: list
    batches: dict = field(default_factory=dict)

    def steps(self, kind, ladder, pick=None):
        """[encounter, xp, defeat] for the measured steps of one type, in ladder order.
        pick maps a ladder index to the batch indices to use (a bootstrap draw)."""
        out = []
        for i in sorted(self.batches.get(kind, {})):
            values = self.batches[kind][i]
            chosen = values if pick is None else [values[b] for b in pick[kind, i]]
            out.append([ladder[i], encounter_xp([ladder[i]]), sum(chosen) / len(chosen)])
        return out

    def ratings(self, ladders, threshold, pick=None):
        """({kind: (xp, censored)}, overall geometric mean)."""
        types = {kind: crossing(self.steps(kind, ladder, pick), threshold) for kind, ladder in ladders.items()}
        overall = math.exp(sum(math.log(xp) for xp, _ in types.values()) / len(types))
        return types, overall


def _bracket(steps, ladder_len, threshold):
    """Ladder indices of the steps that decide a full rating's crossing."""
    for i, (_, _, defeat, *_r) in enumerate(steps):
        if defeat >= threshold: return [i] if i == 0 else [i - 1, i]
    return [min(len(steps), ladder_len) - 1]


class FocusedComparison:
    """Measure a base party and candidates on shared bracket steps."""

    def __init__(self, base, *, seed=1, runs=400, threshold=THRESHOLD, strategy="default", morale="none", cover=False,
                 benchmark=None, workers=None, base_rating=None, executor=None, probe=_probe):
        """probe and executor can be replaced in tests, as for engine.rating.rate_party."""
        self.probe = probe
        self.seed, self.threshold, self.strategy, self.morale, self.cover = seed, threshold, strategy, morale, cover
        self.n_batches = max(1, math.ceil(runs / BATCH))
        self.workers, self.executor = workers, executor
        from .day_options import DayOptions
        sheets = party_sheets(base, DayOptions())
        self.level = round(sum(s["level"] for s in sheets) / len(sheets))
        self.benchmark = benchmark or default_version(self.level)
        self.ladders = load_benchmark(self.benchmark)["levels"][self.level]
        self.base_rating = base_rating or rate_party(base, seed=seed, strategy=strategy, morale=morale, cover=cover,
                                                     benchmark=self.benchmark, workers=workers, executor=executor, probe=probe)
        self.start = {kind: _bracket(t.steps, len(self.ladders[kind]), threshold) for kind, t in self.base_rating.types.items()}
        self.runs = 0
        self.base = self.measure("base", base)

    def _run(self, builds, jobs):
        """jobs: [(kind, ladder index, batch index)] -> defeat fraction per job, in order."""
        tasks = [(list(builds), self.ladders[kind][i], batch_seed(self.seed, self.ladders[kind][i], k), BATCH,
                  self.strategy, self.morale, self.cover) for kind, i, k in jobs]
        if self.executor is not None:
            results = [self.executor.submit(self.probe, t).result() for t in tasks]
        else:
            with ProcessPoolExecutor(max_workers=self.workers or os.cpu_count() or 1) as pool:
                results = list(pool.map(self.probe, tasks, chunksize=1))
        out = []
        for task, r in zip(tasks, results):
            if r["errors"]: raise RuntimeError(f"{task[1]}: engine errors {r['errors']}")
            self.runs += r["runs"] + r["failed_runs"]
            out.append(r["defeat"] if r["runs"] else 0.0)
        return out

    def measure(self, name, builds):
        """Measure one party on the base brackets, widening any bracket its crossing leaves."""
        result = Focused(name, list(builds), {kind: {} for kind in self.ladders})
        want = {kind: set(idx) for kind, idx in self.start.items()}
        while any(want.values()):
            jobs = [(kind, i, k) for kind in sorted(want) for i in sorted(want[kind]) for k in range(self.n_batches)]
            for (kind, i, k), v in zip(jobs, self._run(builds, jobs)):
                result.batches[kind].setdefault(i, []).append(v)
            want = {kind: set() for kind in self.ladders}
            for kind, measured in result.batches.items():
                lo, hi = min(measured), max(measured)
                mean = lambda i: sum(measured[i]) / len(measured[i])
                if mean(lo) >= self.threshold and lo > 0: want[kind].add(lo - 1)       # the crossing is lower
                elif mean(hi) < self.threshold and hi < len(self.ladders[kind]) - 1: want[kind].add(hi + 1)  # or higher
        return result

    def change(self, cand, *, confidence=CONFIDENCE, reps=BOOTSTRAP, rng_seed=0):
        """Relative change of cand against the base: {"overall": (est, lo, hi), kind: (est, lo, hi, censored)}."""
        base_t, base_o = self.base.ratings(self.ladders, self.threshold)
        cand_t, cand_o = cand.ratings(self.ladders, self.threshold)
        rng = random.Random(f"{self.seed}:{rng_seed}:{cand.name}")
        keys = {(kind, i) for f in (self.base, cand) for kind, m in f.batches.items() for i in m}
        draws = {"overall": []} | {kind: [] for kind in self.ladders}
        for _ in range(reps):
            pick = {key: [rng.randrange(self.n_batches) for _ in range(self.n_batches)] for key in sorted(keys)}
            bt, bo = self.base.ratings(self.ladders, self.threshold, pick)
            ct, co = cand.ratings(self.ladders, self.threshold, pick)
            draws["overall"].append(co / bo - 1)
            for kind in self.ladders: draws[kind].append(ct[kind][0] / bt[kind][0] - 1)
        a = (1 - confidence) / 2
        def interval(values):
            values = sorted(values)
            return values[int(a * len(values))], values[min(len(values) - 1, int((1 - a) * len(values)))]
        out = {"overall": (cand_o / base_o - 1, *interval(draws["overall"]))}
        for kind in self.ladders:
            censored = cand_t[kind][1] or base_t[kind][1]
            out[kind] = (cand_t[kind][0] / base_t[kind][0] - 1, *interval(draws[kind]), censored)
        return out
