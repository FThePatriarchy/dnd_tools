"""Build comparison: swap a build into a reference party and measure the change in rating.

A candidate's value is the change in the party rating (engine.rating) when it
replaces the reference party's member of the same class, overall and per
opponent type, as a percentage. Every candidate is rated with the same seed
and per-encounter batch seeds, so differences are measured on common random
numbers. Changes under NOISE overall, or TYPE_NOISE for one opponent type,
are marked as within noise (Phase 2 measured overall ratings agreeing within
about 2.3% across seeds, and single types moving by up to ~0.1x).

By default candidates are measured with engine.focused: the base party is
rated once, then base and candidates are run on the same ladder steps that
decide each crossing (the bracket), with --runs runs per step and shared
batch seeds, and each change gets a paired bootstrap 95% interval. A change
whose interval contains zero is marked ≈. --method full re-rates every
candidate from scratch with the fixed noise bars (the published reports).

--party and --replace swap candidates into your own party instead of a
reference one.

Candidates are build names, or --variants: recipes generated from a class's
main decisions at standard ability scores, so only the decision changes. A
cheap expected-damage x durability screen ranks generated variants, and the
top --finalists (plus the standard build) are rated. --feats rates the
standard build with each feat; --abilities rates other standard-array
placements and ASI plans for the standard build.

    python -m engine.compare --level 5 --class fighter --variants --references standard casual
    python -m engine.compare --level 5 --class cleric --abilities --finalists 5
    python -m engine.compare --level 5 --class wizard --candidates wizard_5 wizard_5_optimized wizard_5_casual
    python -m engine.compare --level 5 --class fighter --feats --party fighter_5 cleric_5 rogue_5 wizard_5 --replace fighter_5
"""
import argparse
from copy import deepcopy
from dataclasses import asdict
import json
import sys

import yaml

from .benchmark import default_version, load_benchmark
from .calibration import REPORTS
from .loader import ROOT, load_sheet
from .presets import PRIMARY, ordered, party, recipe as preset_recipe
from .rating import rate_party

REFERENCE_CLASSES = ("fighter", "cleric", "rogue", "wizard")
ROLES = {c:c for c in REFERENCE_CLASSES} | {"barbarian":"fighter", "paladin":"fighter", "warlock":"wizard", "bard":"cleric", "monk":"rogue", "ranger":"fighter", "druid":"cleric", "sorcerer":"wizard"}
CLASSES = tuple(ROLES)
NOISE = 0.03       # overall rating: Phase 2 seeds agreed within about 2.3%
TYPE_NOISE = 0.10  # one opponent type: Phase 2 seeds moved single types by up to ~0.1x
FIGHTER_KITS = (("greatsword", "chain_greatsword", "great_weapon_fighting", ["greatsword"]),
                ("sword and shield", "chain_sword_shield", "dueling", ["longsword"]),
                ("archer", "leather_archer", "archery", ["longbow"]))


def standard_recipe(cls, level):
    data = yaml.safe_load((ROOT / "builds" / f"{cls}_{level}.yaml").read_text(encoding="utf-8"))
    return {"name": "standard", **data}


def label(candidate):
    return candidate["name"] if isinstance(candidate, dict) else candidate


def variant(base, name, **changes):
    r = deepcopy(base)
    r["name"] = name
    for key, value in changes.items():
        if key == "equipment": r["equipment"] = value
        else: r["choices"][key] = value
    return r


def spell_profile(base, cls, level, profile):
    """The standard recipe with another preset profile's cantrip and spell choices."""
    if profile == "standard": return deepcopy(base)
    other = preset_recipe(cls, level, profile)["choices"]
    r = deepcopy(base)
    r["name"] = f"{profile} spells"
    for key in ("cantrips", "prepared_spells", "spellbook"):
        if key in other: r["choices"][key] = other[key]
    return r


FEAT_OPTIONS = {
    "druid": [("war_caster","wis",{}), ("resilient","con",{})],
    "sorcerer": [("war_caster","cha",{}), ("resilient","wis",{})],
    "monk": [("resilient","wis",{})],
    "ranger": [("sharpshooter","dex",{}), ("resilient","con",{})],
    "warlock": [("war_caster", "cha", {}), ("resilient","con",{})],
    "bard": [("war_caster", "cha", {}), ("resilient","con",{})],  # (feat, +1 ability, changes to the standard recipe)
    "barbarian": [("great_weapon_master", "str", {}), ("polearm_master","str",{"equipment":"unarmored_glaive","weapon_masteries":["glaive"]}), ("resilient","wis",{})],
    "paladin": [("great_weapon_master", "str", {"equipment":"chain_greatsword","weapon_masteries":["greatsword"]}),
                ("polearm_master","str",{"equipment":"chain_glaive","weapon_masteries":["glaive"]}), ("resilient","con",{})],
    "fighter": [("great_weapon_master", "str", {}),
                ("sharpshooter", "dex", {"equipment": "leather_archer", "fighting_style": ["archery"], "weapon_masteries": ["longbow"]}),
                ("polearm_master","str",{"equipment":"chain_glaive","weapon_masteries":["glaive"]}), ("resilient","wis",{})],
    "rogue": [("sharpshooter", "dex", {"equipment": "studded_shortbow", "weapon_masteries": ["shortbow", "rapier"]}), ("resilient","wis",{})],
    "cleric": [("war_caster", "wis", {}), ("resilient","con",{})],
    "wizard": [("war_caster", "int", {}), ("resilient","con",{})],
}
ORIGIN_OPTIONS = ("alert", "lucky", "tough")


def feat_variants(base, cls, level):
    """The standard build with a General feat in place of its first ASI, plus each origin feat.
    Illegal combinations (an unmet prerequisite) are dropped later by the builder check."""
    out = [variant(base, f"feat: {feat}", origin_feat=feat) for feat in ORIGIN_OPTIONS]
    asis = base["choices"].get("asis") or {}
    if not asis: return out
    first = min(asis)
    for feat, ability, changes in FEAT_OPTIONS[cls]:
        r = variant(base, f"feat: {feat.replace('_', ' ')}", **changes)
        if cls == "fighter" and "fighting_style" in changes and level >= 7: r["choices"]["fighting_style"] = changes["fighting_style"] + ["defense"]
        r["choices"]["asis"] = {**deepcopy(asis), first: {"feat": feat, "ability": ability}}
        out.append(r)
    options = {feat: (ability, changes) for feat, ability, changes in FEAT_OPTIONS[cls]}
    if len(asis) >= 2 and {"polearm_master", "great_weapon_master"} <= set(options):
        # The classic pairing: Pole Strike with the glaive, then Great Weapon Master at the next ASI.
        second = sorted(asis)[1]
        r = variant(base, "feat: polearm master + great weapon master", **options["polearm_master"][1])
        r["choices"]["asis"] = {**deepcopy(asis), first: {"feat": "polearm_master", "ability": "str"}, second: {"feat": "great_weapon_master", "ability": "str"}}
        out.append(r)
    return out


def species_variants(base):
    """The standard build as each species the builder supports (one per Human feat / Goliath ancestry)."""
    from .builder import DRACONIC, SPECIES
    out = []
    for species, options in sorted(SPECIES.items()):
        if species == "dragonborn":  # one colour per damage type: colours sharing a type play the same
            options = {min(c for c in DRACONIC if DRACONIC[c] == t) for t in set(DRACONIC.values())}
        for choice in sorted(options) if options else [None]:
            if species == "human" and choice == base["choices"].get("origin_feat"): continue
            name = f"species: {species}" + (f" ({choice})" if choice else "")
            changes = {"species": species, **({"species_choice": choice} if choice else {})}
            out.append(variant(base, name, **changes))
    return out


def variants(cls, level, feats_only=False):
    """Recipes for a class's main decisions at standard abilities; the first is the standard build."""
    base = standard_recipe(cls, level)
    out = [base]
    if feats_only: pass
    elif cls == "fighter":
        out = []
        for kit, equipment, style, masteries in FIGHTER_KITS:
            styles = [[style, "defense"]] if level >= 7 else [[style], ["defense"]]
            for chosen in styles:
                name = f"{kit} + {' + '.join(s.replace('_', ' ') for s in chosen)}"
                out.append(variant(base, name, equipment=equipment, fighting_style=chosen, weapon_masteries=masteries))
        standard = next(i for i, v in enumerate(out) if v["equipment"] == base["equipment"]
                        and set(v["choices"]["fighting_style"]) == set(base["choices"]["fighting_style"]))
        out.pop(standard)
        out.insert(0, base)  # the standard build itself (same choices, its own style order)
    elif cls in {"druid","sorcerer"}:
        out += [spell_profile(base,cls,level,p) for p in ("optimized","casual")]
        if cls=="sorcerer" and 2<=level<10:
            out.append(variant(base,"Metamagic: lasting control",metamagic=["heightened_spell","extended_spell"]))
    elif cls == "monk":
        if level>=5: out.append(variant(base,"Stunning Strike: reserve",stunning_budget="reserve"))
    elif cls == "ranger":
        changes={"equipment":"scale_sword_shield","weapon_masteries":["longsword"]}
        if level>=2: changes["fighting_style"]=["dueling"]
        out.append(variant(base,"melee sword and shield kit",**changes))
        if level>=3: out.append(variant(base,"Hunter's Prey: Horde Breaker",hunters_prey="horde_breaker"))
    elif cls == "barbarian":
        out.append(variant(base,"greatsword kit",equipment="unarmored_greatsword",weapon_masteries=["greatsword"]))
    elif cls == "paladin":
        for kit,equipment,style,masteries in [FIGHTER_KITS[0],FIGHTER_KITS[1],("sword and shield","chain_sword_shield","defense",["longsword"])]:
            changes = {"equipment":equipment,"weapon_masteries":masteries}
            if level>=2: changes["fighting_style"]=[style]
            out.append(variant(base,f"{kit} + {style.replace('_',' ')}",**changes))
        out += [spell_profile(base,cls,level,p) for p in ("optimized","casual")]
    elif cls == "rogue":
        cunning = base["choices"].get("cunning_strike")
        for equipment, masteries in (("studded_shortbow", ["shortbow", "rapier"]),):
            out.append(variant(base, "shortbow first", equipment=equipment, weapon_masteries=masteries))
        if cunning:
            for pair in (["trip", "withdraw"], ["poison", "withdraw"]):
                out.append(variant(base, f"cunning {' + '.join(pair)}", cunning_strike=pair))
    elif cls == "cleric":
        out.append(variant(base, "divine strike", blessed_strikes="divine_strike"))
        thaum = variant(base, "thaumaturge", divine_order="thaumaturge", equipment="scale_shield")
        from .builder import spell_options, _class
        options = {n: s for n, s in spell_options("cleric", level).items() if s["level"] == 0}
        count = _class("cleric")["levels"][level]["cantrips"] + 1
        thaum["choices"]["cantrips"] = ordered("cleric", base["choices"]["cantrips"], options)[:count]
        out.append(thaum)
        out += [spell_profile(base, cls, level, p) for p in ("optimized", "casual")]
    elif cls in {"warlock", "bard"}:
        out += [spell_profile(base,cls,level,p) for p in ("optimized","casual")]
        if cls=="warlock" and level>=2:
            out.append(variant(base,"invocations: defense",invocations=["armor_of_shadows","eldritch_mind"]))
            out.append(variant(base,"invocations: offense",invocations=["agonizing_blast","eldritch_mind"]))
    elif cls == "wizard":
        out += [spell_profile(base, cls, level, p) for p in ("optimized", "casual")]
    out += feat_variants(base, cls, level)
    from .builder import build
    legal = []
    for r in out:
        try: build(r["class"], r["level"], r["subclass"], r["abilities"], r["equipment"], r["choices"])
        except Exception: continue
        legal.append(r)
    return legal


# Abilities worth a high secondary score, per class (the primary always takes the 15).
SECONDARY = {"fighter": ("con", "dex", "wis"), "barbarian": ("con", "dex", "wis"), "paladin": ("con", "cha", "wis"),
             "rogue": ("con", "wis", "int"), "monk": ("wis", "con", "str"), "ranger": ("con", "wis", "str"),
             "wizard": ("con", "dex", "wis"), "sorcerer": ("con", "dex", "wis"), "warlock": ("con", "dex", "wis"),
             "bard": ("con", "dex", "wis"), "cleric": ("con", "str", "dex"), "druid": ("con", "dex", "int")}
ASI_PLANS = ("primary", "split", "con first")


def ability_variants(cls, level):
    """The standard build with the standard array's 14 and 13 on two of the class's secondary abilities
    (12, 10, 8 on the rest in the standard order), under each ASI plan: all to the primary (the
    default), +1 primary / +1 Con each time, or +2 Con at the first ASI. Builds whose sheets come out
    identical, or that the builder rejects, are dropped; the standard build is first."""
    from itertools import permutations
    from .builder import ABILITIES, build, default_asis
    base = standard_recipe(cls, level)
    primary = PRIMARY[cls]
    standard_order = sorted((a for a in ABILITIES if a != primary), key=lambda a: -base["abilities"][a])
    out, seen = [base], {sheet_key(base)}
    for high, mid in permutations(SECONDARY[cls], 2):
        rest = [a for a in standard_order if a not in {high, mid}]
        abilities = {primary: 15, high: 14, mid: 13, **dict(zip(rest, (12, 10, 8)))}
        for plan in ASI_PLANS:
            asis = default_asis(cls, level, {**abilities, primary: abilities[primary] + 2, "con": abilities["con"] + 1})
            if not asis and plan != "primary": continue
            if plan == "split": asis = {n: {primary: 1, "con": 1} for n in asis}
            if plan == "con first" and asis: asis[min(asis)] = {"con": 2}
            r = deepcopy(base)
            r["name"] = f"14 {high.title()}, 13 {mid.title()}" + ("" if plan == "primary" else f"; ASI {plan}")
            r["abilities"] = abilities
            r["choices"]["asis"] = asis
            try: build(r["class"], r["level"], r["subclass"], r["abilities"], r["equipment"], r["choices"])
            except Exception: continue
            key = sheet_key(r)
            if key in seen: continue
            seen.add(key); out.append(r)
    return out


def sheet_key(recipe):
    """What the simulation sees of a recipe: its built sheet with the scores reduced to modifiers."""
    from .builder import build
    sheet = build(recipe["class"], recipe["level"], recipe["subclass"], recipe["abilities"], recipe["equipment"], recipe["choices"])
    sheet = {**sheet, "abilities": {a: (s - 10) // 2 for a, s in sheet["abilities"].items()}}
    return json.dumps(sheet, sort_keys=True)


def screen_score(candidate, level):
    """Crude expected damage per round x effective HP against the level's benchmark brute."""
    from . import Combat, Combatant
    from .day_options import DayOptions
    from .encounters import party_sheets
    from .loader import load_spells
    sheet = party_sheets([candidate], DayOptions())[0]
    brute = load_benchmark(default_version(level))["levels"][level]["brute"][0].split(" x")[0]
    pc = Combatant.from_sheet(sheet, "pc", "party")
    foe = Combatant.from_sheet(load_sheet(ROOT / "monsters" / f"{brute}.yaml"), "foe", "enemy")
    combat = Combat([pc, foe], load_spells(), seed=1)
    offense = combat.at_will_damage_rate(pc, foe)
    spells = [n for n in pc.spells if combat.spells[n]["level"] and combat.can_cast(pc, n)]
    if spells:
        best = max(combat.expected_spell_damage(pc, combat.scale(pc, combat.spells[n], combat.spells[n]["level"]), foe) for n in spells)
        offense += best * sum(pc.spell_slots.values()) / 6  # slot spells spread over a six-encounter day
    to_hit = max((a["to_hit"] for a in foe.attacks), default=5)
    durability = pc.max_hp / max(0.05, combat.hit_probability(foe, pc, to_hit))
    return offense * durability


def focused_compare(level, cls, candidates, references=("standard",), *, seed=1, strategy="default", workers=None, cover=False,
                    runs=400, parties=None):
    """{reference: {"base": PartyRating, "member", "rows": [(label, change)], "focused": FocusedComparison}}.

    parties optionally maps a label to (party builds, index of the member to replace)."""
    from .focused import FocusedComparison
    results = {}
    targets = parties or {ref: (party(level, ref), REFERENCE_CLASSES.index(ROLES[cls])) for ref in references}
    for ref, (base_party, slot) in targets.items():
        fc = FocusedComparison(base_party, seed=seed, runs=runs, strategy=strategy, cover=cover, workers=workers)
        rows = []
        for candidate in candidates:
            trial = list(base_party); trial[slot] = candidate
            measured = fc.base if candidate == base_party[slot] else fc.measure(label(candidate), trial)
            rows.append((label(candidate), fc.change(measured)))
        results[ref] = {"base": fc.base_rating, "member": base_party[slot], "party": list(base_party), "rows": rows, "focused": fc}
    return results


def sim_screen(level, cls, found, *, seed=1, strategy="default", workers=None, cover=False, runs=100, parties=None):
    """Rank variants by a short focused run (runs per bracket step) in the first reference party."""
    results = focused_compare(level, cls, found, ("standard",), seed=seed, strategy=strategy, workers=workers, cover=cover,
                              runs=runs, parties=dict(list(parties.items())[:1]) if parties else None)
    rows = next(iter(results.values()))["rows"]
    return [(v, rows[i][1]["overall"][0]) for i, v in enumerate(found)]


def compare(level, cls, candidates, references=("standard",), *, seed=1, strategy="default", workers=None, cover=False):
    """{reference: {"base": PartyRating, "rows": [(label, PartyRating)]}} for each reference profile."""
    results = {}
    for ref in references:
        base_party = party(level, ref)
        slot = REFERENCE_CLASSES.index(ROLES[cls])
        base = rate_party(base_party, seed=seed, strategy=strategy, workers=workers, cover=cover)
        rows = []
        for candidate in candidates:
            if candidate == base_party[slot]:
                rows.append((label(candidate), base)); continue
            trial = list(base_party); trial[slot] = candidate
            rows.append((label(candidate), rate_party(trial, seed=seed, strategy=strategy, workers=workers, cover=cover)))
        results[ref] = {"base": base, "member": base_party[slot], "rows": rows}
    return results


def delta(new, old):
    return new / old - 1


def fmt_delta(d, noise=NOISE):
    return f"{d:+.0%}" + ("" if abs(d) >= noise else " ≈")


def fmt_change(est, lo, hi):
    """+3% (-1% to +7%), with ≈ when the interval contains zero."""
    return f"{est:+.0%}{' ≈' if lo <= 0 <= hi else ''} ({lo:+.0%} to {hi:+.0%})"


def focused_markdown(level, cls, results, screened=None, cover=False, runs=400):
    out = [f"# Build comparison: {cls}, level {level}", "",
           "Each row swaps the candidate into the party in place of the replaced member. The base party is rated once against "
           f"benchmark v{default_version(level)} (5% defeat threshold); then the base and every candidate are run on the ladder steps "
           f"that decide each crossing, {runs} runs per step with shared batch seeds (`engine.focused`). Values are the change in "
           "rating with a paired bootstrap 95% interval; ≈ marks an interval that contains zero."
           + (" Cover and ranged-in-melee rules on (`DayOptions.cover`)." if cover else ""), ""]
    if screened:
        out += ["## Screen", "", screened[0], "", "| Variant | Screen | Rated |", "| --- | ---: | --- |"]
        out += [f"| {name} | {score} | {'yes' if rated else 'no'} |" for name, score, rated in screened[1]]
        out.append("")
    for ref, data in results.items():
        base, fc = data["base"], data["focused"]
        kinds = list(base.types)
        out += [f"## Party: {ref} ({', '.join(label(b) for b in data['party'])}; replacing {label(data['member'])})", "",
                f"Base rating {base.xp:,.0f} XP ({base.multiple(base.xp):.2f}× High). Focused runs: {fc.runs:,}.", "",
                "| Candidate | Overall | " + " | ".join(kinds) + " |", "| --- | ---: | " + " | ".join("---:" for _ in kinds) + " |"]
        for name, ch in sorted(data["rows"], key=lambda row: -row[1]["overall"][0]):
            cells = [fmt_change(*ch[k][:3]) + ("†" if ch[k][3] else "") for k in kinds]
            out.append(f"| {name} | {fmt_change(*ch['overall'])} | " + " | ".join(cells) + " |")
        out += ["", "† the crossing is at the edge of its benchmark ladder (a bound), so the change is a bound too.", ""]
    return "\n".join(out)


def markdown(level, cls, results, screened=None, cover=False):
    out = [f"# Build comparison: {cls}, level {level}", "",
           "Each row swaps the candidate into the reference party in place of its "
           f"{ROLES[cls]} and re-rates the party against benchmark v{default_version(level)} (5% defeat threshold, same seeds). "
           f"Values are the change in rating; ≈ marks changes within noise: under {NOISE:.0%} overall and "
           f"under {TYPE_NOISE:.0%} for a single opponent type, whose rating rests on one interpolated crossing."
           + (" Cover and ranged-in-melee rules on (`DayOptions.cover`)." if cover else ""), ""]
    if screened:
        out += ["## Screen", "", "Expected damage × effective HP against the level's benchmark brute; the top variants were rated.", "",
                "| Variant | Screen score | Rated |", "| --- | ---: | --- |"]
        out += [f"| {name} | {score:,.0f} | {'yes' if rated else 'no'} |" for name, score, rated in screened]
        out.append("")
    for ref, data in results.items():
        base = data["base"]
        kinds = list(base.types)
        out += [f"## Reference party: {ref} ({', '.join(label(b) for b in party(level, ref))})", "",
                f"Base rating {base.xp:,.0f} XP ({base.multiple(base.xp):.2f}× High).", "",
                "| Candidate | Overall | " + " | ".join(kinds) + " |", "| --- | ---: | " + " | ".join("---:" for _ in kinds) + " |"]
        for name, r in sorted(data["rows"], key=lambda row: -row[1].xp):
            cells = [fmt_delta(delta(r.types[k].xp, base.types[k].xp), TYPE_NOISE) + ("†" if r.types[k].censored or base.types[k].censored else "")
                     for k in kinds]
            out.append(f"| {name} | {fmt_delta(delta(r.xp, base.xp))} ({r.multiple(r.xp):.2f}×) | " + " | ".join(cells) + " |")
        out += ["", "† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.", ""]
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--level", type=int, required=True)
    parser.add_argument("--class", dest="cls", choices=CLASSES, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--candidates", nargs="+", help="build names of the same class")
    group.add_argument("--variants", action="store_true", help="generate variants of the class's main decisions")
    group.add_argument("--feats", action="store_true", help="the standard build and its feat variants only")
    group.add_argument("--abilities", action="store_true", help="the standard build with other ability arrays and ASI plans")
    group.add_argument("--species", action="store_true", help="the standard build as each supported species")
    parser.add_argument("--finalists", type=int, default=4, help="variants rated after the screen (plus standard)")
    parser.add_argument("--only", nargs="+", metavar="NAME", help="keep only the variants with these names (plus standard)")
    parser.add_argument("--references", nargs="+", default=["standard"], choices=["casual", "standard", "optimized"])
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--strategy", default="default")
    parser.add_argument("--cover", action="store_true", help="optional cover and ranged-in-melee rules (DayOptions.cover)")
    parser.add_argument("--workers", type=int)
    parser.add_argument("--method", choices=["focused", "full"], default="focused",
                        help="focused: paired runs on the deciding ladder steps with intervals (default); full: re-rate every candidate")
    parser.add_argument("--runs", type=int, default=400, help="focused: runs per bracket step (default 400)")
    parser.add_argument("--screen", choices=["sim", "ev"], default="sim",
                        help="variant screen with --method focused: a short focused run (sim, default) or expected damage x HP "
                             "against a brute (ev, always used by --method full)")
    parser.add_argument("--screen-runs", type=int, default=100, help="sim screen: runs per bracket step (default 100)")
    parser.add_argument("--party", nargs="+", help="your own party (build names) instead of the reference parties")
    parser.add_argument("--replace", help="with --party: the member to replace (default: the first of the candidate's class)")
    parser.add_argument("--write", metavar="NAME", help="write data/reports/compare_<NAME>.md")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    parties = None
    if args.party:
        if args.method == "full": parser.error("--party needs --method focused")
        member = args.replace or next((b for b in args.party if b.split("_")[0] == args.cls), None)
        if member not in args.party: parser.error(f"--replace: name a member of --party (got {member!r})")
        parties = {"yours": (list(args.party), args.party.index(member))}
    screened = None
    if args.variants or args.feats or args.abilities or args.species:
        if args.species:
            base = standard_recipe(args.cls, args.level)
            found = [base] + species_variants(base)
        else:
            found = ability_variants(args.cls, args.level) if args.abilities else variants(args.cls, args.level, feats_only=args.feats)
        if args.only: found = found[:1] + [v for v in found[1:] if v["name"] in args.only]
        if args.screen == "sim" and args.method == "focused" and len(found) - 1 > args.finalists:
            scores = sim_screen(args.level, args.cls, found, seed=args.seed, strategy=args.strategy, workers=args.workers,
                                cover=args.cover, runs=args.screen_runs, parties=parties)
            note = f"A short focused run ({args.screen_runs} runs per bracket step) ranks the variants by their change in rating; the top variants were rated."
            show = lambda x: f"{x:+.0%}"
        else:
            scores = [(v, screen_score(v, args.level)) for v in found]
            note = "Expected damage × effective HP against the level's benchmark brute; the top variants were rated."
            show = lambda x: f"{x:,.0f}"
        ranked = sorted(scores[1:], key=lambda vs: -vs[1])[:max(0, args.finalists)]
        candidates = [found[0]] + [v for v, _ in ranked]
        ordered_scores = sorted(scores, key=lambda vs: -vs[1])
        if args.method == "full": screened = [(v["name"], s, v in candidates) for v, s in ordered_scores]  # published layout
        else: screened = (note, [(v["name"], show(s), v in candidates) for v, s in ordered_scores])
    else:
        candidates = args.candidates
    if args.method == "full":
        results = compare(args.level, args.cls, candidates, args.references, seed=args.seed, strategy=args.strategy, workers=args.workers, cover=args.cover)
        text = markdown(args.level, args.cls, results, screened, cover=args.cover)
    else:
        results = focused_compare(args.level, args.cls, candidates, args.references, seed=args.seed, strategy=args.strategy,
                                  workers=args.workers, cover=args.cover, runs=args.runs, parties=parties)
        text = focused_markdown(args.level, args.cls, results, screened, cover=args.cover, runs=args.runs)
        if args.write:
            data = {ref: {"base": asdict(d["base"]), "party": d["party"], "member": label(d["member"]), "runs": d["focused"].runs,
                          "rows": [[name, ch] for name, ch in d["rows"]]} for ref, d in results.items()}
            (REPORTS / f"compare_{args.write}.md").write_text(text, encoding="utf-8")
            (REPORTS / f"compare_{args.write}.json").write_text(json.dumps({"level": args.level, "class": args.cls, "method": "focused",
                                                                            "runs": args.runs, "screen": screened, "results": data},
                                                                           indent=1, default=str), encoding="utf-8")
        print(text)
        return
    if args.write:
        (REPORTS / f"compare_{args.write}.md").write_text(text, encoding="utf-8")
        data = {ref: {"base": asdict(d["base"]), "rows": [[name, asdict(r)] for name, r in d["rows"]]} for ref, d in results.items()}
        (REPORTS / f"compare_{args.write}.json").write_text(json.dumps({"level": args.level, "class": args.cls, "screen": screened,
                                                                        "results": data}, indent=1, default=str), encoding="utf-8")
    print(text)


if __name__ == "__main__": main()
