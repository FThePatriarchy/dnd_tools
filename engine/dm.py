"""Command line for DMs: give it a party and a fight (or a day), get back the odds.

    python -m engine.dm fight --party fighter_5 cleric_5 rogue_5 wizard_5 --monsters "ogre x2" "goblin_warrior x4"
    python -m engine.dm fight --level 5 --profile casual --monsters young_red_dragon
    python -m engine.dm day --level 5 --steps "ogre x2" short "bandit x6, bandit_captain" long troll
    python -m engine.dm day --party fighter_5 cleric_5 --day goblin_warren
    python -m engine.dm monsters --max-cr 3

The party is build names (data/handwritten/builds) or a preset party (--level,
--profile). Monsters are file names in data/handwritten/monsters, each optionally
followed by xN. A fight runs adaptively until its yes/no results are within about
±5 points (95% confidence), or a fixed --runs. The XP line places the encounter
on the 2024 DMG budget for this party; the simulated odds are the answer, and
two encounters with the same XP can play very differently.
"""
import argparse
import json
import sys

from .presets import preset_levels
from .calibration import BUDGETS, XP_BY_CR
from .encounters import Adaptive, party_sheets, run_day_runs, run_encounter
from .loader import ROOT, load_sheet

STRATEGIES = ("default", "nova", "conservative", "rationed")
REST = {"short", "long", "s", "l"}


def monster_entries(tokens):
    """Monster entries from CLI tokens: "ogre x2", or "ogre" "x2", or "ogre x2, goblin_warrior x4"."""
    from .day import MONSTERS
    entries = []
    for token in tokens:
        for part in (p.strip() for p in token.split(",")):
            if not part: continue
            if part.startswith("x") and part[1:].isdigit():
                if not entries or " x" in entries[-1]: raise ValueError(f"{part} must follow a monster name")
                entries[-1] += " " + part
            else: entries.append(part)
    for entry in entries:
        if not MONSTERS.fullmatch(entry): raise ValueError(f"invalid monster entry: {entry!r} (expected name or name xN)")
        if not (ROOT / "monsters" / (entry.split(" x")[0] + ".yaml")).is_file():
            raise ValueError(f"unknown monster {entry.split(' x')[0]!r}; see python -m engine.dm monsters")
    return entries


def day_from_steps(tokens):
    """A day definition from steps: each token is a rest (short/long) or an encounter ("ogre x2, goblin_warrior")."""
    steps = []
    for token in tokens:
        if token.strip().lower() in REST: steps.append({"rest": "short" if token.strip().lower() in {"short", "s"} else "long"})
        else: steps.append({"encounter": monster_entries([token])})
    return {"name": "dm day", "steps": steps}


def encounter_xp(entries):
    from .day import encounter_names
    return sum(XP_BY_CR[str(load_sheet(ROOT / "monsters" / (name + ".yaml"))["cr"])] for name in encounter_names(entries))


def budget_line(xp, levels):
    """The encounter's XP against the summed 2024 DMG budgets of these PCs."""
    if any(level not in BUDGETS for level in levels): return f"{xp:,} XP"
    low, moderate, high = (sum(BUDGETS[level][k] for level in levels) for k in range(3))
    return f"{xp:,} XP = {xp / high:.2f}× DMG High (this party's budgets: Low {low:,} · Moderate {moderate:,} · High {high:,})"


def pct(p, ci=None):
    if p is None: return "—"
    return f"{p:6.1%}" + (f"  ±{ci:.1%}" if ci is not None else "")


def resource_text(spent):
    return ", ".join(f"{k} {v:.2f}" for k, v in spent.items()) or "—"


def party_from(args):
    from .presets import party
    builds = list(args.party) if args.party else party(args.level, args.profile)
    if args.items:
        from .items import with_items
        builds = with_items(builds, args.items)
    return builds


def names(builds):
    """Build names, with each PC's magic items when the party carries a kit."""
    out = []
    for b in builds:
        if isinstance(b, dict): out.append(b["name"] + (f" [{', '.join(b['choices'].get('items', []))}]" if b["choices"].get("items") else ""))
        else: out.append(b)
    return ", ".join(out)


def character_table(characters, scope):
    out = ["", f"Per character ({scope}):", "",
           f"  {'Character':<34} {'Down':>6} {'Dies':>6} {'HP left':>8}  Resources spent (mean)"]
    for c in characters:
        out.append(f"  {c['name']:<34} {c['down']:6.0%} {c['death']:6.0%} {c['hp_left']:8.0%}  {resource_text(c['spent'])}")
    return out


def fight_report(builds, entries, result, levels, args):
    ci = result["ci"]
    out = [f"Party: {names(builds)}",
           f"Encounter: {', '.join(entries)} — {budget_line(encounter_xp(entries), levels)}",
           f"Runs: {result['runs']}, seed {args.seed}, party strategy {args.strategy}, morale {args.morale}"
           + (", cover rules on" if getattr(args, "cover", False) else "") + (f", {args.items} item kit" if args.items else ""), "",
           f"  {'Outcome':<32} {'Chance':>6}  95% ±",
           f"  {'Party wins':<32} {pct(result['win'])}",
           f"  {'Defeat (TPK or all PCs out)':<32} {pct(result['defeat'], ci['defeat'])}",
           f"  {'  of which TPK':<32} {pct(result['tpk'])}",
           f"  {'Someone goes down':<32} {pct(result['down'], ci['down'])}",
           f"  {'Someone dies':<32} {pct(result['death'], ci['death'])}", "",
           f"  Mean rounds {result['rounds']:.1f} · party HP lost {result['hp_lost']:.0%} · spell slots spent {result['slots_spent']:.0%}"
           + (f" · monsters fled {result['fled']:.0%}" if args.morale != "none" else "")]
    out += character_table(result["characters"], "one fight")
    return out


def day_report(builds, day, result, levels, args):
    out = [f"Party: {names(builds)}",
           f"Day: {day['name']}, runs {result['runs']}, seed {args.seed}, party strategy {args.strategy}, morale {args.morale}", "",
           f"  {'Outcome':<32} {'Chance':>6}",
           f"  {'Whole day cleared, no deaths':<32} {pct(result['complete'])}",
           f"  {'Defeat (TPK or all PCs out)':<32} {pct(result['defeat'])}",
           f"  {'Someone dies':<32} {pct(result['death'])}", "",
           f"  At the end of the day: HP {min(1, result['hp_left']):.0%} · spell slots {result['slots_left']:.0%} · Hit Dice {result['hit_dice_left']:.0%} left; a PC dropped to 0 HP {result['downs']:.1f} times",
           "", f"  {'Step':<46} {'Reached':>8} {'Cleared':>8} {'Down':>6} {'Rounds':>7}"]
    fights = iter(result["encounters"])
    for i, step in enumerate(day["steps"], 1):
        if "rest" in step:
            out.append(f"  {i:>2}. {step['rest']} rest")
            continue
        e = next(fights)
        label = f"{', '.join(step['encounter'])} ({encounter_xp(step['encounter']):,} XP)"
        rounds = f"{e['rounds']:7.1f}" if e["rounds"] is not None else f"{'—':>7}"
        out.append(f"  {i:>2}. {label:<42} {e['reached']:8.0%} {e['cleared']:8.0%} {e['down']:6.0%} {rounds}")
    xp = sum(encounter_xp(s["encounter"]) for s in day["steps"] if "encounter" in s)
    out += ["", f"  Day total: {xp:,} XP; the DMG's adventuring-day guideline is about 3× the Moderate budget ({3 * sum(BUDGETS[l][1] for l in levels if l in BUDGETS):,} XP for this party)."]
    out += character_table(result["characters"], "whole day")
    return out


def monsters_report(min_cr, max_cr):
    from fractions import Fraction
    rows = []
    for path in sorted((ROOT / "monsters").glob("*.yaml")):
        sheet = load_sheet(path)
        cr = Fraction(str(sheet["cr"]))
        if min_cr <= cr <= max_cr: rows.append((cr, path.stem, sheet))
    out = [f"  {'Monster':<24} {'CR':>4} {'XP':>6} {'HP':>4} {'AC':>3}  Type"]
    for cr, name, sheet in sorted(rows, key=lambda r: (r[0], r[1])):
        out.append(f"  {name:<24} {str(sheet['cr']):>4} {XP_BY_CR[str(sheet['cr'])]:>6,} {sheet['max_hp']:>4} {sheet['ac']:>3}  {sheet.get('creature_type', '')}")
    return out


def cr_value(text):
    from fractions import Fraction
    try: return Fraction(text)
    except ValueError: raise argparse.ArgumentTypeError(f"invalid CR {text!r}")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for command in ("fight", "day"):
        p = sub.add_parser(command, help="one encounter" if command == "fight" else "encounters and rests in order")
        who = p.add_mutually_exclusive_group(required=True)
        who.add_argument("--party", nargs="+", help="build names, e.g. fighter_5 cleric_5")
        who.add_argument("--level", type=int, choices=preset_levels(), help="the preset fighter/cleric/rogue/wizard party at this level")
        p.add_argument("--profile", choices=("casual", "standard", "optimized"), default="standard", help="preset party profile (with --level)")
        if command == "fight":
            p.add_argument("--monsters", nargs="+", required=True, help='e.g. "ogre x2" "goblin_warrior x4"')
        else:
            what = p.add_mutually_exclusive_group(required=True)
            what.add_argument("--steps", nargs="+", help='encounters and rests in order, e.g. "ogre x2" short "troll" long')
            what.add_argument("--day", help="a day file name in data/handwritten/days, or a .yaml path")
        p.add_argument("--runs", type=int, help="fixed number of runs (fight default: adaptive, 100-800; day default: 400)")
        p.add_argument("--seed", type=int, default=1)
        p.add_argument("--strategy", choices=STRATEGIES, default="default", help="party resource strategy")
        p.add_argument("--monster-strategy", choices=STRATEGIES, default="default")
        p.add_argument("--morale", choices=("none", "dmg", "rout"), default="none", help="DMG optional morale rule (default: fight to the last)")
        p.add_argument("--items", choices=("half", "full"), help="give the party a DMG-sized magic item kit (engine/items.py)")
        if command == "fight":
            p.add_argument("--cover", action="store_true", help="optional cover and ranged-in-melee rules (DayOptions.cover)")
        p.add_argument("--json", action="store_true", help="print the raw results as JSON")
    m = sub.add_parser("monsters", help="list the monsters that can be used, with CR and XP")
    m.add_argument("--min-cr", type=cr_value, default=cr_value("0"))
    m.add_argument("--max-cr", type=cr_value, default=cr_value("30"))
    args = parser.parse_args(argv)
    sys.stdout.reconfigure(encoding="utf-8")
    if args.command == "monsters":
        print("\n".join(monsters_report(args.min_cr, args.max_cr)))
        return
    if args.runs is not None and args.runs < 1: parser.error("--runs must be positive")
    try:
        from .day_options import DayOptions
        builds = party_from(args)
        levels = [s["level"] for s in party_sheets(builds, DayOptions())]
        common = dict(seed=args.seed, morale=args.morale, strategy=args.strategy, monster_strategy=args.monster_strategy)
        if args.command == "fight":
            entries = monster_entries(args.monsters)
            result = run_encounter(builds, entries, args.runs or Adaptive(min_runs=100), detail=True, cover=args.cover, **common)
            lines = fight_report(builds, entries, result, levels, args)
        else:
            from .day import load_day, validate_day
            day = day_from_steps(args.steps) if args.steps else load_day(args.day)
            validate_day(day)
            result = run_day_runs(builds, day, args.runs or 400, detail=True, **common)
            lines = day_report(builds, day, result, levels, args)
    except (ValueError, OSError) as exc: parser.error(str(exc))
    if not result["runs"]: parser.error("every run failed: " + "; ".join(result["errors"]))
    if args.json:
        print(json.dumps(result, indent=1, default=str))
        return
    if result["errors"]:
        lines += ["", f"Warning: {result['failed_runs']} runs hit an engine error and were left out:"]
        lines += [f"  {message} (seed {seed})" for message, seed in result["errors"].items()]
    print("\n".join(lines))


if __name__ == "__main__": main()
