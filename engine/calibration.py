"""DMG 2024 encounter-budget calibration sweep.

For each party level with preset builds, a four-character party (Fighter,
Cleric, Rogue, Wizard) fights single encounters sized to the 2024 DMG XP
budgets (Low / Moderate / High, plus an over-budget probe). Encounters are
homogeneous groups of one monster type whose total XP lands between 75% and
100% of the budget. Each encounter runs from full resources with the current
default DayOptions; no modelling defaults are changed here.

    python -m engine.calibration --runs 200 --write
    python -m engine.calibration --area half_group --write   # one area-rule variant
    python -m engine.calibration --compare                    # side-by-side report

--area swaps the no-grid area-of-effect rule for the sweep only; the engine
default (the DMG "Targets in Areas of Effect" table) is unchanged.
"""
import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
import json
import math
import random
from statistics import mean
import sys

from .loader import ROOT, load_sheet
from .policy import FEET_PER_TARGET

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


def report_paths(area):
    stem = "calibration_dmg" if area == "dmg" else f"calibration_dmg_area_{area}"
    return REPORTS / f"{stem}.json", REPORTS / f"{stem}.md"


# Area-rule variants. Each returns a target count like engine.policy.area_heuristic
# and opts in to its ally avoidance, so only the count differs from the default.
def _dmg_count(shape, size_ft):
    return max(1, math.ceil(size_ft / FEET_PER_TARGET.get(shape, 5)))


def _half(shape, size_ft, eligible, caster=None):
    return min(eligible, max(1, math.ceil(_dmg_count(shape, size_ft) / 2)))


def _half_group(shape, size_ft, eligible, caster=None):
    return min(eligible, _dmg_count(shape, size_ft), max(1, math.ceil(eligible / 2)))


def _party_spread(shape, size_ft, eligible, caster=None):
    if caster is not None and caster.team != "party": return _half(shape, size_ft, eligible)
    return min(eligible, _dmg_count(shape, size_ft))


def _single(shape, size_ft, eligible, caster=None):
    return min(eligible, 1)


for _rule in (_half, _half_group, _party_spread, _single):
    _rule.avoids_allies = True
    _rule.wants_caster = True

AREA_RULES = {
    "dmg": (None, "Engine default: DMG table, cone size/10, line length/30, other shapes size/5."),
    "half": (_half, "DMG count halved, rounded up."),
    "half_group": (_half_group, "DMG count, but never more than half the target group (rounded up)."),
    "party_spread": (_party_spread, "Monster areas use the halved count (the party spreads out); party areas keep the DMG count."),
    "single": (_single, "Lower bound: every area hits one creature."),
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


_SPELLS = None


def run_cell(task):
    """One composition, many runs. Returns per-run metrics aggregated."""
    global _SPELLS
    from .builder import load_character
    from .day import run_day
    from .day_options import DayOptions
    from .loader import load_spells
    from .policy import Policy
    from .state import Combatant
    level, difficulty, monster, count, xp_total, runs, seed, area = task
    if _SPELLS is None: _SPELLS = load_spells()
    opts = DayOptions()
    sheets = []
    for cls in CLASSES:
        sheet = load_character(f"{cls}_{level}", background=opts.backgrounds)
        if "position" not in sheet:
            sheet["position"] = "front" if sheet["ac"] >= 16 and any(a["kind"] == "melee" for a in sheet.get("attacks", [])) else "back"
        sheets.append(sheet)
    day = {"name": "calibration", "steps": [{"encounter": [f"{monster} x{count}"]}]}
    monsters = {monster: load_sheet(ROOT / "monsters" / (monster + ".yaml"))}
    rng = random.Random(seed)
    rows = []
    errors = {}
    for _ in range(runs):
        party = [Combatant.from_sheet(s, f"party_{i}", "party") for i, s in enumerate(sheets)]
        base_hp = {c.id: c.max_hp for c in party}
        max_hp = sum(base_hp.values())
        max_slots = sum(sum(c.max_spell_slots.values()) for c in party)
        run_seed = rng.getrandbits(64)
        try:
            result = run_day(party, day, _SPELLS, run_seed, policy=Policy(), monster_policy=Policy(),
                             monster_sheets=monsters, options=opts, area=AREA_RULES[area][0])
        except Exception as exc:  # engine bugs are reported, not averaged in
            errors.setdefault(f"{type(exc).__name__}: {exc}", run_seed)
            continue
        enc = result.encounters[0]
        # Aid-style max HP increases are clamped so a buffed party cannot show negative loss.
        end_hp = sum(0 if c["dead"] else min(c["hp"], base_hp[i]) for i, c in enc.end.items())
        end_slots = sum(sum(c["slots"].values()) for c in enc.end.values())
        rows.append({
            "win": enc.cleared,
            "tpk": result.failure_reason == "tpk",
            "down": enc.downs > 0,
            "death": enc.deaths > 0,
            "downs": enc.downs,
            "deaths": enc.deaths,
            "hp_lost": 1 - end_hp / max_hp,
            "slots_spent": (1 - end_slots / max_slots) if max_slots else 0.0,
            "rounds": enc.rounds,
        })
    agg = {k: mean(float(r[k]) for r in rows) for k in rows[0]} if rows else dict.fromkeys(k for k, _ in METRICS)
    return {"level": level, "difficulty": difficulty, "monster": monster, "count": count, "area": area,
            "xp": xp_total, "budget": budget(level, difficulty), "runs": len(rows),
            "failed_runs": runs - len(rows), "errors": errors, **agg}


def sweep(runs=200, seed=1, levels=LEVELS, workers=None, area="dmg"):
    xp = monster_xp()
    tasks = []
    for level in levels:
        for difficulty in DIFFICULTIES:
            for monster, count, total in compositions(budget(level, difficulty), xp):
                tasks.append((level, difficulty, monster, count, total, runs, seed, area))
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run_cell, tasks))


METRICS = (("win", "Win"), ("down", "Any down"), ("death", "Any death"), ("tpk", "TPK"),
           ("hp_lost", "HP lost"), ("slots_spent", "Slots spent"), ("rounds", "Rounds"))


def pct(value): return f"{value:.0%}"


def markdown(cells, runs, seed, area="dmg"):
    failed = [c for c in cells if c["failed_runs"]]
    cells = [c for c in cells if c["runs"]]
    by = defaultdict(list)
    for c in cells: by[c["level"], c["difficulty"]].append(c)
    out = ["# DMG 2024 budget calibration", "",
           f"Party: {', '.join(CLASSES)} at each level; single encounter from full resources; "
           f"default DayOptions; {runs} runs per composition, seed {seed}. "
           f"Groups are one monster type, {MIN_FILL:.0%}-100% of budget, at most {MAX_COUNT} creatures. "
           f"'Over' is {OVER_FACTOR}x High, a probe beyond the DMG categories.", "",
           f"Area rule: `{area}` — {AREA_RULES[area][1]}", "",
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
    out += ["", "## Per composition", "",
            "| Level | Difficulty | Encounter | XP / budget | " + " | ".join(label for _, label in METRICS) + " |",
            "| ---: | --- | --- | ---: | " + " | ".join("---:" for _ in METRICS) + " |"]
    for c in sorted(cells, key=lambda c: (c["level"], DIFFICULTIES.index(c["difficulty"]), c["xp"] / c["count"])):
        vals = [f"{c[k]:.1f}" if k == "rounds" else pct(c[k]) for k, _ in METRICS]
        out.append(f"| {c['level']} | {c['difficulty']} | {c['monster']} x{c['count']} | "
                   f"{c['xp']:.0f} / {c['budget']:.0f} | " + " | ".join(vals) + " |")
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
           "target count changes. Engine default is `dmg`. Runs per composition: "
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


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runs", type=int, default=200)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--levels", type=int, nargs="+", default=list(LEVELS))
    parser.add_argument("--workers", type=int)
    parser.add_argument("--area", choices=list(AREA_RULES), default="dmg", help="area-of-effect rule for this sweep only")
    parser.add_argument("--write", action="store_true", help="write the sweep to data/reports/")
    parser.add_argument("--compare", action="store_true", help="write the side-by-side area-rule report from written sweeps")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")  # reports contain non-ASCII; Windows consoles default to cp1252
    if args.compare:
        text = compare(list(AREA_RULES))
        COMPARE_MD.write_text(text, encoding="utf-8")
        print(text)
        return
    cells = sweep(args.runs, args.seed, tuple(args.levels), args.workers, args.area)
    text = markdown(cells, args.runs, args.seed, args.area)
    if args.write:
        json_path, md_path = report_paths(args.area)
        json_path.write_text(json.dumps({"runs": args.runs, "seed": args.seed, "area": args.area, "cells": cells}, indent=1), encoding="utf-8")
        md_path.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__": main()
