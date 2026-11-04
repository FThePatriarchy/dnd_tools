"""Compare builds over an adventuring day instead of one fight from full resources.

A party rating starts every fight with every slot and feature, which favours
builds that spend everything at once. Real tables play several fights per long
rest (engine.day_presets), so a build's value also depends on how it lasts.

DayComparison runs the base party and each candidate through the same seeded
days (several random days from a preset, filled at the party's level) in
batches with shared seeds, and reports paired bootstrap 95% intervals over
the batches. The headline ("overall") is the change in the chance of finishing
the whole day without a death, in percentage points; the change in deaths,
defeats, drops to 0 HP, and HP and slots left at the end of the day come with
it. It has the interface engine.optimize expects (base_rating, measure, change),
so the build search can optimize for days.

A day the base party always or never completes cannot show a difference in
that headline; the report flags it, and the intensity (scale) should move.
"""
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
import os
import random

CONFIDENCE, BOOTSTRAP = 0.95, 2000
METRICS = ("complete", "death", "defeat", "downs", "hp_left", "slots_left")


def _job(task):
    builds, day, runs, seed, strategy = task
    from .encounters import run_day_runs
    r = run_day_runs(builds, day, runs, seed, strategy=strategy)
    if r["errors"]: raise RuntimeError(f"engine errors: {r['errors']}")
    return {k: r[k] for k in METRICS} | {"runs": r["runs"]}


@dataclass
class DayMeasure:
    name: str
    builds: list
    units: list = field(default_factory=list)   # one dict of metric means per (day, batch), in a fixed order

    def mean(self, key):
        return sum(u[key] * u["runs"] for u in self.units) / max(1, sum(u["runs"] for u in self.units))


@dataclass
class _Rating:
    xp: float          # the base party's day completion rate (named for engine.optimize's report)
    complete: float
    death: float

    def multiple(self, _): return self.complete


class DayComparison:
    def __init__(self, base, *, preset="typical", slots=None, scale=1.0, days=4, runs=100, batch=25, seed=1,
                 strategy="rationed", themes=None, workers=None, executor=None):
        from .day_options import DayOptions
        from .day_presets import make_day
        from .encounters import party_sheets
        levels = [s["level"] for s in party_sheets(base, DayOptions())]
        self.level = round(sum(levels) / len(levels))
        self.days = [make_day(preset, self.level, len(base), seed=seed + k, themes=themes, scale=scale, slots=slots) for k in range(days)]
        # At least four batches a day, so the paired bootstrap has units to resample even for short runs.
        self.batches = max(4, runs // batch)
        self.batch = max(5, runs // self.batches)
        self.seed, self.strategy = seed, strategy
        self.workers, self.executor = workers, executor
        self.preset, self.scale, self.runs = preset, scale, 0
        self.base = self.measure("base", base)
        self.base_rating = _Rating(self.base.mean("complete"), self.base.mean("complete"), self.base.mean("death"))

    def _units(self):
        return [(k, b) for k in range(len(self.days)) for b in range(self.batches)]

    def measure(self, name, builds):
        tasks = [(list(builds), self.days[k][0], self.batch, random.Random(f"{self.seed}:{k}:{b}").getrandbits(64), self.strategy)
                 for k, b in self._units()]
        if self.executor is not None: results = [self.executor.submit(_job, t).result() for t in tasks]
        else:
            with ProcessPoolExecutor(max_workers=self.workers or os.cpu_count() or 1) as pool:
                results = list(pool.map(_job, tasks, chunksize=1))
        self.runs += sum(r["runs"] for r in results)
        return DayMeasure(name, list(builds), results)

    def change(self, cand, *, confidence=CONFIDENCE, reps=BOOTSTRAP):
        """{"overall": (est, lo, hi) for complete in points, metric: (est, lo, hi, "")}; paired over (day, batch) units."""
        n = len(self.base.units)
        rng = random.Random(f"{self.seed}:{cand.name}")
        diff = lambda key, idx: (sum(cand.units[i][key] for i in idx) - sum(self.base.units[i][key] for i in idx)) / len(idx)
        out = {}
        a = (1 - confidence) / 2
        for key in METRICS:
            est = diff(key, range(n))
            draws = sorted(diff(key, [rng.randrange(n) for _ in range(n)]) for _ in range(reps))
            out[key] = (est, draws[int(a * reps)], draws[min(reps - 1, int((1 - a) * reps))], "")
        out["overall"] = out["complete"][:3]
        return out

    def flag(self):
        """A note when the base party's completion rate is too close to 0 or 1 to show differences."""
        c = self.base_rating.complete
        if c >= .95: return f"The base party completes {c:.0%} of these days: raise the intensity to separate builds."
        if c <= .05: return f"The base party completes only {c:.0%} of these days: lower the intensity to separate builds."
        return ""
