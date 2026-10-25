"""DMG 2024 encounter-budget calibration sweep.

For each party level with preset builds, a four-character party (Fighter,
Cleric, Rogue, Wizard) fights single encounters sized to the 2024 DMG XP
budgets (Low / Moderate / High, plus an over-budget probe). Encounters are
homogeneous groups of one monster type whose total XP lands between 75% and
100% of the budget. Each encounter runs from full resources with the current
default DayOptions.

    python -m engine.calibration --runs 200 --write          # baseline: engine defaults
    python -m engine.calibration --area dmg --grab data --write   # pre-2026-10-24 defaults
    python -m engine.calibration --compare                    # side-by-side area-rule report
    python -m engine.calibration --compare-grab               # side-by-side grab-cap report
    python -m engine.calibration --adaptive --write           # adaptive run counts (*_adaptive reports)

--area and --grab swap the no-grid area-of-effect rule and the multi-target
grab cap for one sweep. Their defaults are the engine defaults
(party_spread and grab_half); every rule name always means the same rule,
so report file names stay comparable across default changes.
"""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict
import json
import math
from statistics import mean
import sys

from .encounters import DEFEATS, TRACKED, Adaptive, half_widths, needs_more, run_encounter, wilson  # noqa: F401 (re-exported)
from .loader import ROOT, load_sheet
from .policy import FEET_PER_TARGET, dmg_area_heuristic, is_grab, printed_grab_count

LEVELS = (1, 3, 5, 7, 10)
CLASSES = ("fighter", "cleric", "rogue", "wizard")

# 2024 DMG, XP budget per character.
BUDGETS = {
    1: (50, 75, 100), 2: (100, 150, 200), 3: (150, 225, 400), 4: (250, 375, 500),
    5: (500, 750, 1100), 6: (600, 1000, 1400), 7: (750, 1300, 1700), 8: (1000, 1700, 2100),
    9: (1300, 2000, 2600), 10: (1600, 2300, 3100),
}
DIFFICULTIES = ("low", "moderate", "high", "over")
OVER_FACTOR = 1.5  # probe beyond High; not a DMG category

XP_BY_CR = {
    "0": 10, "1/8": 25, "1/4": 50, "1/2": 100, "1": 200, "2": 450, "3": 700, "4": 1100,
    "5": 1800, "6": 2300, "7": 2900, "8": 3900, "9": 5000, "10": 5900, "11": 7200,
    "12": 8400, "13": 10000, "14": 11500, "15": 13000, "16": 15000, "17": 18000,
}
MIN_FILL, MAX_COUNT, PER_CELL = 0.75, 8, 6

REPORTS = ROOT.parent / "reports"
COMPARE_MD = REPORTS / "calibration_area_compare.md"
GRAB_COMPARE_MD = REPORTS / "calibration_grab_compare.md"
DEFAULT_AREA, DEFAULT_GRAB = "party_spread", "grab_half"


MORALE_COMPARE_MD = REPORTS / "calibration_morale_compare.md"
MORALE_RULES = {
    "none": "Engine default: monsters fight to the last.",
    "dmg": "Optional DMG morale: at half HP, and when the side is down to half its number, DC 10 Wisdom save or flee.",
    "rout": "Upper bound: the same triggers, but the monster flees with no save.",
}


def report_paths(area, grab="data", morale="none", adaptive=False):
    """Named by rule, not by default: calibration_dmg is the DMG area table with printed grabs."""
    stem = ("calibration_dmg" + ("" if area == "dmg" else f"_area_{area}")
            + ("" if grab == "data" else f"_grab_{grab.removeprefix('grab_')}")
            + ("" if morale == "none" else f"_morale_{morale}")
            + ("_adaptive" if adaptive else ""))
    return REPORTS / f"{stem}.json", REPORTS / f"{stem}.md"


# Area-rule variants. Each returns a target count like engine.policy.area_heuristic
# and opts in to its ally avoidance, so only the count differs between rules.
def _dmg_count(shape, size_ft):
    return max(1, math.ceil(size_ft / FEET_PER_TARGET.get(shape, 5)))


def _half(shape, size_ft, eligible, caster=None):
    return min(eligible, max(1, math.ceil(_dmg_count(shape, size_ft) / 2)))


def _half_group(shape, size_ft, eligible, caster=None):
    return min(eligible, _dmg_count(shape, size_ft), max(1, math.ceil(eligible / 2)))


def _single(shape, size_ft, eligible, caster=None):
    return min(eligible, 1)


for _rule in (_half, _half_group, _single):
    _rule.avoids_allies = True
    _rule.wants_caster = True

# None means the engine default (engine.policy.area_heuristic / grab_cap).
AREA_RULES = {
    "dmg": (dmg_area_heuristic, "DMG table, cone size/10, line length/30, other shapes size/5 (engine default until 2026-10-24)."),
    "half": (_half, "DMG count halved, rounded up."),
    "half_group": (_half_group, "DMG count, but never more than half the target group (rounded up)."),
    "party_spread": (None, "Monster areas use the halved count (the party spreads out); party areas keep the DMG count (engine default)."),
    "single": (_single, "Lower bound: every area hits one creature."),
}


# Grab-cap variants for multi-target grabs (Engulf, Whelm): n_targets blocks whose
# failure grapples, restrains or engulfs (engine.policy.is_grab). Other n_targets
# blocks keep their count.
def _grab_one(instance, block, n, eligible):
    return min(n, 1) if is_grab(block) else n


GRAB_RULES = {
    "data": (printed_grab_count, "The printed count: Engulf up to 4, Whelm up to 2 (engine default until 2026-10-24)."),
    "grab_half": (None, "A grab reaches at most half the target group, rounded up: 2 of a party of 4 (engine default)."),
    "grab_one": (_grab_one, "Lower bound: a grab reaches one creature per use."),
}


def budget(level, difficulty, party_size=len(CLASSES)):
    low, moderate, high = BUDGETS[level]
    per = {"low": low, "moderate": moderate, "high": high, "over": high * OVER_FACTOR}[difficulty]
    return per * party_size


def monster_xp():
    result = {}
    for path in sorted((ROOT / "monsters").glob("*.yaml")):
        result[path.stem] = XP_BY_CR[str(load_sheet(path)["cr"])]
    return result


def compositions(total, xp):
    """Up to PER_CELL homogeneous groups, spread evenly across monster XP."""
    options = []
    for name, each in xp.items():
        count = int(total // each)
        if 1 <= count <= MAX_COUNT and count * each >= MIN_FILL * total:
            options.append((each, name, count))
    options.sort()
    if len(options) > PER_CELL:
        step = (len(options) - 1) / (PER_CELL - 1)
        options = [options[round(i * step)] for i in range(PER_CELL)]
    return [(name, count, count * each) for each, name, count in options]


def run_cell(task):
    """One composition, many runs (a fixed count or an Adaptive spec), aggregated."""
    level, difficulty, monster, count, xp_total, runs, seed, area, grab, *rest = task
    morale = rest[0] if rest else "none"
    result = run_encounter([f"{cls}_{level}" for cls in CLASSES], [f"{monster} x{count}"], runs, seed,
                           area=AREA_RULES[area][0], target_cap=GRAB_RULES[grab][0], morale=morale)
    return {"level": level, "difficulty": difficulty, "monster": monster, "count": count, "area": area, "grab": grab,
            "morale": morale, "xp": xp_total, "budget": budget(level, difficulty), **result}


def sweep(runs=200, seed=1, levels=LEVELS, workers=None, area="dmg", grab="data", monsters=None, morale="none"):
    """monsters restricts which compositions run; each composition keeps its own seed."""
    xp = monster_xp()
    tasks = []
    for level in levels:
        for difficulty in DIFFICULTIES:
            for monster, count, total in compositions(budget(level, difficulty), xp):
                if monsters and monster not in monsters: continue
                tasks.append((level, difficulty, monster, count, total, runs, seed, area, grab, morale))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run_cell, tasks))


METRICS = (("win", "Win"), ("down", "Any down"), ("death", "Any death"), ("tpk", "TPK"),
           ("defeat", "Defeat"), ("hp_lost", "HP lost"), ("slots_spent", "Slots spent"), ("rounds", "Rounds"),
           ("fled", "Fled"))


def pct(value): return "-" if value is None else f"{value:.0%}"


def fmt_metric(c, key):
    """Sweeps written before a metric existed show '-' for it."""
    value = c.get(key)
    return "-" if value is None else f"{value:.1f}" if key == "rounds" else pct(value)


def sampling(runs, cells):
    if not isinstance(runs, Adaptive): return f"{runs} runs per composition"
    counts = [c["runs"] + c["failed_runs"] for c in cells]
    return (f"adaptive runs per composition ({runs.min_runs}-{runs.max_runs} in batches of {runs.batch}, "
            f"until defeat, any down and any death are within ±{runs.precision:.0%} at 95% confidence and the defeat "
            f"interval excludes {', '.join(pct(t) for t in runs.thresholds)}; {sum(counts)} runs in total)")


def markdown(cells, runs, seed, area="dmg", grab="data", morale="none"):
    failed = [c for c in cells if c["failed_runs"]]
    cells = [c for c in cells if c["runs"]]
    by = defaultdict(list)
    for c in cells: by[c["level"], c["difficulty"]].append(c)
    out = ["# DMG 2024 budget calibration", "",
           f"Party: {', '.join(CLASSES)} at each level; single encounter from full resources; "
           f"default DayOptions; {sampling(runs, cells)}, seed {seed}. "
           f"Groups are one monster type, {MIN_FILL:.0%}-100% of budget, at most {MAX_COUNT} creatures. "
           f"'Over' is {OVER_FACTOR}x High, a probe beyond the DMG categories.", "",
           f"Area rule: `{area}` — {AREA_RULES[area][1]}", "",
           f"Grab rule: `{grab}` — {GRAB_RULES[grab][1]}", "",
           f"Morale: `{morale}` — {MORALE_RULES[morale]} Fled is the share of monsters that fled.", "",
           "TPK: every PC at 0 HP. Defeat: the party loses, either by TPK or with every PC still "
           "standing dominated or otherwise out of the fight.", "",
           "## Summary (mean across compositions, [min-max] in brackets)", "",
           "| Level | Difficulty | Groups | " + " | ".join(label for _, label in METRICS) + " |",
           "| ---: | --- | ---: | " + " | ".join("---:" for _ in METRICS) + " |"]
    for level in sorted({c["level"] for c in cells}):
        for difficulty in DIFFICULTIES:
            group = by.get((level, difficulty))
            if not group: continue
            row = [str(level), difficulty, str(len(group))]
            for key, _ in METRICS:
                values = [c[key] for c in group]
                fmt = (lambda v: f"{v:.1f}") if key == "rounds" else pct
                row.append(f"{fmt(mean(values))} [{fmt(min(values))}-{fmt(max(values))}]")
            out.append("| " + " | ".join(row) + " |")
    if isinstance(runs, Adaptive):
        counts = sorted(c["runs"] for c in cells)
        widest = max(cells, key=lambda c: max(c["ci"].values()))
        out += ["", "## Sampling", "",
                f"- Runs per composition: min {counts[0]}, median {median(counts):.0f}, max {counts[-1]}; "
                f"{sum(n == runs.min_runs for n in counts)} stopped at the minimum and "
                f"{sum(n >= runs.max_runs for n in counts)} reached the maximum.",
                f"- Widest 95% half-width: ±{max(widest['ci'].values()):.1%} "
                f"({widest['monster']} x{widest['count']}, level {widest['level']} {widest['difficulty']})."]
    out += ["", "## Per composition", "",
            "Runs is the number of runs used; ± is the 95% half-width of the defeat estimate.", "",
            "| Level | Difficulty | Encounter | XP / budget | Runs | ± | " + " | ".join(label for _, label in METRICS) + " |",
            "| ---: | --- | --- | ---: | ---: | ---: | " + " | ".join("---:" for _ in METRICS) + " |"]
    for c in sorted(cells, key=lambda c: (c["level"], DIFFICULTIES.index(c["difficulty"]), c["xp"] / c["count"])):
        vals = [fmt_metric(c, k) for k, _ in METRICS]
        ci = (c.get("ci") or {}).get("defeat")
        out.append(f"| {c['level']} | {c['difficulty']} | {c['monster']} x{c['count']} | "
                   f"{c['xp']:.0f} / {c['budget']:.0f} | {c['runs']} | {'-' if ci is None else f'{ci:.1%}'} | "
                   + " | ".join(vals) + " |")
    if failed:
        out += ["", "## Engine errors (runs excluded from the numbers above)", "",
                "| Level | Difficulty | Encounter | Failed runs | Error | First failing seed |",
                "| ---: | --- | --- | ---: | --- | ---: |"]
        for c in failed:
            for message, seed in c["errors"].items():
                out.append(f"| {c['level']} | {c['difficulty']} | {c['monster']} x{c['count']} | "
                           f"{c['failed_runs']} | {message} | {seed} |")
    return "\n".join(out) + "\n"


def median(values):
    values = sorted(values)
    mid = len(values) // 2
    return values[mid] if len(values) % 2 else (values[mid - 1] + values[mid]) / 2


def compare(rules):
    """Side-by-side report over every area rule that has a written sweep."""
    loaded = {}
    for rule in rules:
        path = report_paths(rule)[0]
        if path.exists(): loaded[rule] = json.loads(path.read_text(encoding="utf-8"))
    if "dmg" not in loaded: raise SystemExit("run the default sweep with --write first")
    rules = list(loaded)
    cells = {r: {(c["level"], c["difficulty"], c["monster"], c["count"]): c for c in d["cells"] if c["runs"]} for r, d in loaded.items()}
    levels = sorted({k[0] for k in cells["dmg"]})
    def cell_values(rule, level, difficulty, metric):
        return [c[metric] for k, c in cells[rule].items() if k[:2] == (level, difficulty)]
    runs = {r: d["runs"] for r, d in loaded.items()}
    out = ["# Area-rule comparison", "",
           "Same DMG budget sweep, same compositions and seeds; only the no-grid area-of-effect "
           "target count changes; multi-target grabs keep their printed count (`data`) throughout. "
           "Engine default is `party_spread` (it was `dmg` until 2026-10-24). Runs per composition: "
           + ", ".join(f"`{r}` {n}" for r, n in runs.items()) + ".", "",
           "| Rule | Meaning |", "| --- | --- |"]
    out += [f"| `{r}` | {AREA_RULES[r][1]} |" for r in rules]
    head = "| Level | Difficulty | " + " | ".join(f"`{r}`" for r in rules) + " |"
    sep = "| ---: | --- | " + " | ".join("---:" for _ in rules) + " |"
    for metric, title in (("tpk", "Median TPK chance"), ("down", "Median chance someone goes down"),
                          ("death", "Median chance someone dies"), ("win", "Mean win rate")):
        out += ["", f"## {title} (across the compositions in each slot)", "", head, sep]
        agg = mean if metric == "win" else median
        for level in levels:
            for difficulty in DIFFICULTIES:
                row = [pct(agg(cell_values(r, level, difficulty, metric))) if cell_values(r, level, difficulty, metric) else "-" for r in rules]
                out.append(f"| {level} | {difficulty} | " + " | ".join(row) + " |")
    out += ["", "## Shape checks", "",
            "- **Monotone levels:** levels where median TPK never falls from Low to Moderate to High to Over.",
            "- **Wipe outliers:** compositions in Low, Moderate or High with TPK of 50% or more.",
            "- **Spread:** mean (max − min) TPK across the compositions of a slot, Low to High.", "",
            "| Rule | Monotone levels | Wipe outliers | Spread |", "| --- | ---: | ---: | ---: |"]
    for r in rules:
        monotone = sum(all(a <= b for a, b in zip(m, m[1:])) for m in
                       ([median(cell_values(r, lv, d, "tpk")) for d in DIFFICULTIES] for lv in levels))
        outliers = sum(c["tpk"] >= 0.5 for k, c in cells[r].items() if k[1] != "over")
        spreads = [max(v) - min(v) for lv in levels for d in DIFFICULTIES[:3] if (v := cell_values(r, lv, d, "tpk"))]
        out.append(f"| `{r}` | {monotone} / {len(levels)} | {outliers} | {pct(mean(spreads))} |")
    flagged = sorted((k for k, c in cells["dmg"].items() if c["tpk"] >= 0.3),
                     key=lambda k: (k[0], DIFFICULTIES.index(k[1]), k[2]))
    out += ["", "## Encounters with TPK ≥ 30% under the default", "",
            "| Level | Difficulty | Encounter | " + " | ".join(f"`{r}`" for r in rules) + " |",
            "| ---: | --- | --- | " + " | ".join("---:" for _ in rules) + " |"]
    for k in flagged:
        vals = [pct(cells[r][k]["tpk"]) if k in cells[r] else "-" for r in rules]
        out.append(f"| {k[0]} | {k[1]} | {k[2]} x{k[3]} | " + " | ".join(vals) + " |")
    return "\n".join(out) + "\n"


def load_variant(area, grab):
    """Cells keyed by composition. A sweep restricted with --monsters is completed
    from the same area rule's full sweep: compositions without a grab action run
    the identical code path and seed, so their results are unchanged."""
    path = report_paths(area, grab)[0]
    if not path.exists(): return None
    data = json.loads(path.read_text(encoding="utf-8"))
    key = lambda c: (c["level"], c["difficulty"], c["monster"], c["count"])
    cells = {key(c): c for c in data["cells"] if c["runs"]}
    if data.get("monsters"):
        base = load_variant(area, "data")
        if base is None: return None
        cells = {**base["cells"], **cells}
    return {"runs": data["runs"], "monsters": data.get("monsters"), "cells": cells}


def shape_checks(cells, levels):
    def values(level, difficulty): return [c["tpk"] for k, c in cells.items() if k[:2] == (level, difficulty)]
    monotone = sum(all(a <= b for a, b in zip(m, m[1:])) for m in
                   ([median(values(lv, d)) for d in DIFFICULTIES] for lv in levels))
    outliers = sum(c["tpk"] >= 0.5 for k, c in cells.items() if k[1] != "over")
    spreads = [max(v) - min(v) for lv in levels for d in DIFFICULTIES[:3] if (v := values(lv, d))]
    return monotone, outliers, mean(spreads)


GRAB_VARIANTS = (("dmg", "data"), ("dmg", "grab_half"), ("dmg", "grab_one"),
                 ("party_spread", "data"), ("party_spread", "grab_half"))


def compare_grab():
    loaded = {}
    for area, grab in GRAB_VARIANTS:
        v = load_variant(area, grab)
        if v is not None: loaded[area, grab] = v
    if ("dmg", "data") not in loaded: raise SystemExit("run the default sweep with --write first")
    label = lambda v: f"`{v[0]}` + `{v[1]}`"
    base = loaded["dmg", "data"]["cells"]
    levels = sorted({k[0] for k in base})
    grabbers = sorted({m for v in loaded.values() for m in (v["monsters"] or [])})
    out = ["# Grab-cap comparison", "",
           "Same DMG budget sweep, compositions and seeds as the area-rule comparison. A grab rule lowers "
           "the target count of multi-target grabs only (n_targets actions whose failure grapples, restrains "
           "or engulfs): Engulf (gelatinous cube) and Whelm (water elemental). Grab variants were run only on "
           f"the compositions containing {', '.join(f'`{m}`' for m in grabbers) or 'grab monsters'}; every other "
           "composition takes the same area rule's full-sweep result, which is identical by construction.", "",
           "| Grab rule | Meaning |", "| --- | --- |"]
    out += [f"| `{g}` | {GRAB_RULES[g][1]} |" for g in GRAB_RULES]
    out += ["", "| Area rule | Meaning |", "| --- | --- |"]
    out += [f"| `{a}` | {AREA_RULES[a][1]} |" for a in dict.fromkeys(a for a, _ in loaded)]
    affected = sorted((k for k in base if k[2] in grabbers), key=lambda k: (k[0], DIFFICULTIES.index(k[1])))
    out += ["", "## Encounters with a grab action", ""]
    for k in affected:
        out += [f"### Level {k[0]} {k[1]}: {k[2]} x{k[3]}", "",
                "| Variant | " + " | ".join(label for _, label in METRICS) + " |",
                "| --- | " + " | ".join("---:" for _ in METRICS) + " |"]
        for v, data in loaded.items():
            c = data["cells"].get(k)
            if c is None: continue
            vals = [fmt_metric(c, m) for m, _ in METRICS]
            out.append(f"| {label(v)} | " + " | ".join(vals) + " |")
        out.append("")
    out += ["## Whole-sweep shape checks", "",
            "Same definitions as the area-rule comparison: monotone levels (median TPK never falls from Low "
            "to Over), wipe outliers (Low to High compositions with TPK of 50% or more), spread (mean max − min "
            "TPK within a Low to High slot).", "",
            "| Variant | Monotone levels | Wipe outliers | Spread |", "| --- | ---: | ---: | ---: |"]
    for v, data in loaded.items():
        monotone, outliers, spread = shape_checks(data["cells"], levels)
        out.append(f"| {label(v)} | {monotone} / {len(levels)} | {outliers} | {pct(spread)} |")
    out += ["", "## Median TPK chance by slot", "",
            "| Level | Difficulty | " + " | ".join(label(v) for v in loaded) + " |",
            "| ---: | --- | " + " | ".join("---:" for _ in loaded) + " |"]
    for level in levels:
        for d in DIFFICULTIES:
            row = [pct(median([c["tpk"] for k, c in data["cells"].items() if k[:2] == (level, d)])) for data in loaded.values()]
            out.append(f"| {level} | {d} | " + " | ".join(row) + " |")
    return "\n".join(out) + "\n"


def compare_morale(area=DEFAULT_AREA, grab=DEFAULT_GRAB):
    """Side-by-side report of the morale rules on the engine-default area and grab rules."""
    key = lambda c: (c["level"], c["difficulty"], c["monster"], c["count"])
    loaded = {}
    for morale in MORALE_RULES:
        path = report_paths(area, grab, morale)[0]
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            loaded[morale] = {"runs": data["runs"], "cells": {key(c): c for c in data["cells"] if c["runs"]}}
    if "none" not in loaded: raise SystemExit("run the baseline sweep with --write first")
    rules = list(loaded)
    base = loaded["none"]["cells"]
    levels = sorted({k[0] for k in base})
    def values(rule, level, difficulty, metric):
        return [c.get(metric) for k, c in loaded[rule]["cells"].items() if k[:2] == (level, difficulty) and c.get(metric) is not None]
    out = ["# Morale comparison", "",
           f"Same DMG budget sweep, compositions and seeds, on the engine-default `{area}` areas and `{grab}` grabs. "
           "Only the optional morale rule changes; the engine default is `none`. Runs per composition: "
           + ", ".join(f"`{r}` {d['runs']}" for r, d in loaded.items()) + ".", "",
           "A fleeing monster leaves the fight, and a fight in which every remaining monster fled counts as a win. "
           "Creatures immune to the frightened condition never check.", "",
           "| Rule | Meaning |", "| --- | --- |"]
    out += [f"| `{r}` | {MORALE_RULES[r]} |" for r in rules]
    head = "| Level | Difficulty | " + " | ".join(f"`{r}`" for r in rules) + " |"
    sep = "| ---: | --- | " + " | ".join("---:" for _ in rules) + " |"
    for metric, title, agg in (("defeat", "Median defeat chance", median), ("down", "Median chance someone goes down", median),
                               ("death", "Median chance someone dies", median), ("hp_lost", "Mean party HP lost", mean),
                               ("rounds", "Mean rounds", mean), ("fled", "Mean share of monsters that fled", mean)):
        out += ["", f"## {title} (across the compositions in each slot)", "", head, sep]
        for level in levels:
            for difficulty in DIFFICULTIES:
                row = []
                for r in rules:
                    v = values(r, level, difficulty, metric)
                    row.append("-" if not v else f"{agg(v):.1f}" if metric == "rounds" else pct(agg(v)))
                out.append(f"| {level} | {difficulty} | " + " | ".join(row) + " |")
    out += ["", "## Shape checks", "",
            "Same definitions as the other comparisons, using defeat (which includes TPK).", "",
            "| Rule | Monotone levels | Defeat outliers | Spread |", "| --- | ---: | ---: | ---: |"]
    for r in rules:
        cells = {k: {**c, "tpk": c["defeat"]} for k, c in loaded[r]["cells"].items()}
        monotone, outliers, spread = shape_checks(cells, levels)
        out.append(f"| `{r}` | {monotone} / {len(levels)} | {outliers} | {pct(spread)} |")
    if len(rules) > 1:
        other = rules[1]
        moved = sorted((k for k in base if k in loaded[other]["cells"]),
                       key=lambda k: -abs(loaded[other]["cells"][k]["defeat"] - base[k]["defeat"]))[:15]
        out += ["", f"## Largest defeat changes, `none` vs `{other}`", "",
                "| Level | Difficulty | Encounter | " + " | ".join(f"`{r}` defeat" for r in rules) + " | "
                + " | ".join(f"`{r}` fled" for r in rules[1:]) + " |",
                "| ---: | --- | --- | " + " | ".join("---:" for _ in rules) + " | " + " | ".join("---:" for _ in rules[1:]) + " |"]
        for k in moved:
            d = [pct(loaded[r]["cells"][k]["defeat"]) if k in loaded[r]["cells"] else "-" for r in rules]
            f = [pct(loaded[r]["cells"][k]["fled"]) if k in loaded[r]["cells"] else "-" for r in rules[1:]]
            out.append(f"| {k[0]} | {k[1]} | {k[2]} x{k[3]} | " + " | ".join(d) + " | " + " | ".join(f) + " |")
    return "\n".join(out) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=200, help="fixed runs per composition (ignored with --adaptive)")
    parser.add_argument("--adaptive", action="store_true", help="adaptive runs per composition; writes *_adaptive reports")
    parser.add_argument("--min-runs", type=int, default=Adaptive.min_runs)
    parser.add_argument("--max-runs", type=int, default=Adaptive.max_runs)
    parser.add_argument("--batch", type=int, default=Adaptive.batch)
    parser.add_argument("--precision", type=float, default=Adaptive.precision, help="target 95%% half-width, e.g. 0.05")
    parser.add_argument("--threshold", type=float, nargs="*", default=list(Adaptive.thresholds),
                        help="defeat rates the interval must exclude before stopping")
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--levels", type=int, nargs="+", default=list(LEVELS))
    parser.add_argument("--workers", type=int)
    parser.add_argument("--area", choices=list(AREA_RULES), default=DEFAULT_AREA, help="area-of-effect rule for this sweep only")
    parser.add_argument("--grab", choices=list(GRAB_RULES), default=DEFAULT_GRAB, help="multi-target grab cap for this sweep only")
    parser.add_argument("--morale", choices=list(MORALE_RULES), default="none", help="optional morale rule for this sweep only")
    parser.add_argument("--monsters", nargs="+", help="run only compositions of these monsters")
    parser.add_argument("--write", action="store_true", help="write the sweep to data/reports/")
    parser.add_argument("--compare", action="store_true", help="write the side-by-side area-rule report from written sweeps")
    parser.add_argument("--compare-grab", action="store_true", help="write the side-by-side grab-cap report from written sweeps")
    parser.add_argument("--compare-morale", action="store_true", help="write the side-by-side morale report from written sweeps")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # reports contain non-ASCII; Windows consoles default to cp1252
    if args.compare:
        text = compare(list(AREA_RULES))
        COMPARE_MD.write_text(text, encoding="utf-8")
        print(text)
        return
    if args.compare_morale:
        text = compare_morale()
        MORALE_COMPARE_MD.write_text(text, encoding="utf-8")
        print(text)
        return
    if args.compare_grab:
        text = compare_grab()
        GRAB_COMPARE_MD.write_text(text, encoding="utf-8")
        print(text)
        return
    if args.monsters and args.grab == "data" and args.write:
        parser.error("--monsters with --write is for grab variants; a printed-grab (data) sweep must be complete")
    if args.monsters and args.morale != "none" and args.write:
        parser.error("--monsters with --write is only for grab variants")
    try:
        runs = Adaptive(args.min_runs, args.max_runs, args.batch, args.precision, tuple(args.threshold)) if args.adaptive else args.runs
    except ValueError as exc: parser.error(str(exc))
    cells = sweep(runs, args.seed, tuple(args.levels), args.workers, args.area, args.grab, args.monsters, args.morale)
    text = markdown(cells, runs, args.seed, args.area, args.grab, args.morale)
    if args.write:
        json_path, md_path = report_paths(args.area, args.grab, args.morale, args.adaptive)
        json_path.write_text(json.dumps({"runs": asdict(runs) if args.adaptive else runs, "adaptive": args.adaptive, "seed": args.seed, "area": args.area, "grab": args.grab,
                                         "morale": args.morale, "monsters": args.monsters, "cells": cells}, indent=1), encoding="utf-8")
        md_path.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__": main()
