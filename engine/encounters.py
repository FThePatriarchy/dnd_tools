"""Shared Monte Carlo runner for single encounters from full resources.

Used by the DMG budget calibration sweep and the party rating. One call runs
one party against one encounter many times, either a fixed number of runs or
adaptively (see Adaptive), and returns the aggregated outcome metrics.
"""
from dataclasses import dataclass
import math
import random
from statistics import mean

from .loader import ROOT, load_sheet

# Defeat: the fight ends with the party beaten, either all at 0 HP (tpk) or with
# every PC still standing dominated or otherwise out of the fight
# (party_unavailable). Round-limit draws and wins with a PC death are not defeats.
DEFEATS = frozenset({"tpk", "party_unavailable"})

# Adaptive sampling. A composition runs in batches. In mode "all" it stops once
# every tracked yes/no metric's 95% Wilson interval is within +/- precision and the
# defeat interval no longer straddles a decision threshold. In mode "threshold" it
# stops as soon as the defeat interval excludes every threshold, or is within
# +/- precision. Either way it stops at max_runs, and clear-cut results stop at
# min_runs. Run seeds are drawn in the same order as a fixed run, so the first N
# adaptive runs are exactly a fixed N-run sample's runs.
TRACKED = ("defeat", "down", "death")
Z95 = 1.959964


@dataclass(frozen=True)
class Adaptive:
    min_runs: int = 50
    max_runs: int = 800
    batch: int = 50
    precision: float = 0.05
    thresholds: tuple = (0.5,)
    tracked: tuple = TRACKED
    mode: str = "all"

    def __post_init__(self):
        if not 1 <= self.min_runs <= self.max_runs or self.batch < 1 or not 0 < self.precision < 1:
            raise ValueError("need 1 <= min_runs <= max_runs, batch >= 1 and 0 < precision < 1")
        if self.mode not in {"all", "threshold"} or not set(self.tracked) <= set(TRACKED):
            raise ValueError("mode must be all or threshold, and tracked a subset of " + ", ".join(TRACKED))


def wilson(p, n, z=Z95):
    """95% Wilson score interval for a proportion p observed over n runs."""
    if n == 0: return 0.0, 1.0
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def half_widths(rows, metrics=TRACKED):
    n = len(rows)
    result = {}
    for m in metrics:
        lo, hi = wilson(sum(r[m] for r in rows) / n if n else 0.0, n)
        result[m] = (hi - lo) / 2
    return result


def needs_more(rows, attempted, spec):
    if attempted >= spec.max_runs: return False
    if attempted < spec.min_runs: return True
    if not rows: return False  # every run failed; more runs will not help
    lo, hi = wilson(sum(r["defeat"] for r in rows) / len(rows), len(rows))
    straddles = any(lo < t < hi for t in spec.thresholds)
    if spec.mode == "threshold":
        return straddles and (hi - lo) / 2 > spec.precision
    if any(h > spec.precision for h in half_widths(rows, spec.tracked).values()): return True
    return straddles


_SPELLS = None
_SHEETS = {}


def party_sheets(builds, options):
    """Character sheets for build names, with a default front/back position."""
    from .builder import load_character
    sheets = []
    for name in builds:
        cache_key = (name, options.backgrounds)
        if cache_key not in _SHEETS:
            sheet = load_character(name, background=options.backgrounds)
            if "position" not in sheet:
                sheet["position"] = "front" if sheet["ac"] >= 16 and any(a["kind"] == "melee" for a in sheet.get("attacks", [])) else "back"
            _SHEETS[cache_key] = sheet
        sheets.append(_SHEETS[cache_key])
    return sheets


def run_encounter(builds, encounter, runs, seed, *, area=None, target_cap=None, morale="none",
                  strategy="default", monster_strategy="default"):
    """Run a party (build names) against one encounter (entries like "ogre x3").

    runs is a fixed count or an Adaptive spec. area and target_cap are engine
    hooks (None means the engine default). Returns aggregated metrics: means of
    win, tpk, defeat, down, death, downs, deaths, hp_lost, slots_spent, rounds and
    fled, plus runs, failed_runs, errors and ci (95% half-widths).
    """
    global _SPELLS
    from .day import encounter_names, run_day
    from .day_options import DayOptions
    from .loader import load_spells
    from .policy import strategy_policy
    from .state import Combatant
    if _SPELLS is None: _SPELLS = load_spells()
    opts = DayOptions(morale=morale)
    sheets = party_sheets(builds, opts)
    names = encounter_names(encounter)
    day = {"name": "encounter", "steps": [{"encounter": list(encounter)}]}
    monsters = {name: load_sheet(ROOT / "monsters" / (name + ".yaml")) for name in set(names)}
    rng = random.Random(seed)
    rows, errors = [], {}
    spec = runs if isinstance(runs, Adaptive) else None

    def one_run():
        party = [Combatant.from_sheet(s, f"party_{i}", "party") for i, s in enumerate(sheets)]
        base_hp = {c.id: c.max_hp for c in party}
        max_hp = sum(base_hp.values())
        max_slots = sum(sum(c.max_spell_slots.values()) for c in party)
        run_seed = rng.getrandbits(64)
        try:
            result = run_day(party, day, _SPELLS, run_seed, policy=strategy_policy(strategy),
                             monster_policy=strategy_policy(monster_strategy), monster_sheets=monsters,
                             options=opts, area=area, target_cap=target_cap)
        except Exception as exc:  # engine bugs are reported, not averaged in
            errors.setdefault(f"{type(exc).__name__}: {exc}", run_seed)
            return
        enc = result.encounters[0]
        # Aid-style max HP increases are clamped so a buffed party cannot show negative loss.
        end_hp = sum(0 if c["dead"] else min(c["hp"], base_hp[i]) for i, c in enc.end.items())
        end_slots = sum(sum(c["slots"].values()) for c in enc.end.values())
        rows.append({
            "win": enc.cleared,
            "tpk": result.failure_reason == "tpk",
            "defeat": result.failure_reason in DEFEATS,
            "down": enc.downs > 0,
            "death": enc.deaths > 0,
            "downs": enc.downs,
            "deaths": enc.deaths,
            "hp_lost": 1 - end_hp / max_hp,
            "slots_spent": (1 - end_slots / max_slots) if max_slots else 0.0,
            "rounds": enc.rounds,
            "fled": enc.fled / len(names),
        })

    attempted, target = 0, (spec.min_runs if spec else runs)
    while True:
        while attempted < target:
            attempted += 1
            one_run()
        if spec is None or not needs_more(rows, attempted, spec): break
        target = min(spec.max_runs, attempted + spec.batch)
    metrics = ("win", "tpk", "defeat", "down", "death", "downs", "deaths", "hp_lost", "slots_spent", "rounds", "fled")
    agg = {k: mean(float(r[k]) for r in rows) for k in metrics} if rows else dict.fromkeys(metrics)
    return {"runs": len(rows), "failed_runs": attempted - len(rows), "errors": errors,
            "ci": half_widths(rows) if rows else dict.fromkeys(TRACKED), **agg}
