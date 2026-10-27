"""Independent numeric oracle: structured XPHB tables + feature text, not recipes.

This module deliberately does not import class_catalog. Core rules absent from
the supplied class records are identified explicitly in CORE_ALLOWLIST.
"""
from functools import lru_cache
import json
from pathlib import Path
import re

from .loader import Validator

CORE_ALLOWLIST = {
    "proficiency_bonus": "Universal 2024 PB = 2 + floor((level-1)/4); omitted from raw class tables.",
    "zero": "Absent spellcasting/mastery/resource recovery is zero, not a printed grant.",
    "single_use": "Once/next/one in source prose denotes one (including Arcane Recovery).",
}


@lru_cache(None)
def source(name):
    path = Path(__file__).resolve().parents[1] / "raw_data/class" / ("class-" + name + ".json")
    d = json.loads(path.read_text(encoding="utf-8"))
    c = next(x for x in d["class"] if x["source"] == "XPHB")
    short = {"fighter": "Champion", "rogue": "Assassin", "wizard": "Evoker", "cleric": "Life", "barbarian": "Berserker", "paladin": "Devotion"}[name]
    s = next(x for x in d["subclass"] if x["source"] == "XPHB" and x["shortName"] == short)
    f = {("class", x["name"], x["level"]): x for x in d["classFeature"] if x["source"] == "XPHB" and x["level"] <= 10}
    f.update({("subclass", x["name"], x["level"]): x for x in d["subclassFeature"] if x["source"] == "XPHB" and x["subclassShortName"] == short and x["level"] <= 10})
    return c, s, f


def numeric_leaves(value, path=()):
    """Every numeric scalar/string, including mapping keys and table cells."""
    if isinstance(value, bool): return
    if isinstance(value, dict):
        for k, x in value.items():
            if type(k) in {int, float} or isinstance(k, str) and re.search(r"\d", k): yield path + (("key", k),), k
            yield from numeric_leaves(x, path + (k,))
    elif isinstance(value, list):
        for i, x in enumerate(value): yield from numeric_leaves(x, path + (i,))
    elif type(value) in {int, float} or isinstance(value, str) and re.search(r"\d", value):
        yield path, value


def check_class_source(data, path="<class>"):
    v = Validator(path)
    c, s, features = source(data["name"])
    def eq(actual, expected, p): v.check(type(actual) is type(expected) and actual == expected, p, f"XPHB source drift: expected {expected!r}, got {actual!r}")
    eq(data["source"], "XPHB", "source")
    eq(data["hit_die"], "d" + str(c["hd"]["faces"]), "hit_die")
    eq(data["saves"], c["proficiency"], "saves")
    eq(data["subclass"], s["shortName"].lower(), "subclass")
    eq(data["subclass_level"], min(int(ref.split("|")[-1]) for ref in s["subclassFeatures"]), "subclass_level")
    asi = sorted(k[2] for k in features if k[0] == "class" and k[1] == "Ability Score Improvement")
    eq(data["asi_levels"], asi, "asi_levels")
    got = [(f["origin"], f["name"], f["level"]) for f in data["features"]]
    v.check(len(got) == len(features) and set(got) == set(features), "features", "XPHB feature inventory drift")
    for level, row in data["levels"].items():
        p = f"levels.{level}"
        eq(row["proficiency_bonus"], 2 + (level-1)//4, p + ".proficiency_bonus")
        eq(row["hit_die"], data["hit_die"], p + ".hit_die")
        eq(row["features"], [f["name"] for f in data["features"] if f["level"] == level], p + ".features")
        table = c["classTableGroups"][0]["rows"][level-1]
        slots, cantrips, prepared, masteries = {}, 0, 0, 0
        resources = {}
        def use(key, maximum, short=0): resources[key] = {"max": maximum, "short_rest": short, "long_rest": "all"}
        if c["name"] == "Fighter":
            use("second_wind", int(table[0]), 1)
            masteries = int(table[1])
            if level >= 2:
                text = json.dumps(features[("class", "Action Surge", 2)]["entries"])
                v.check("Once" in text and "Short" in text and "Long" in text, p, "missing source recovery")
                use("action_surge", 1, "all")
            if level >= 9:
                v.check("can't use this feature again until" in json.dumps(features[("class", "Indomitable", 9)]["entries"]), p, "missing single-use rule")
                use("indomitable", 1)
        elif c["name"] == "Rogue":
            v.check("two kinds" in json.dumps(features[("class", "Weapon Mastery", 1)]["entries"]), p, "missing two-masteries rule")
            masteries = 2
            d = table[0]["toRoll"][0]
            eq(row.get("sneak_attack"), f"{d['number']}d{d['faces']}", p + ".sneak_attack")
        elif c["name"] == "Barbarian":
            use("rage", int(table[0]), 1)
            masteries = int(table[2])
        elif c["name"] == "Paladin":
            use("lay_on_hands", 5 * level)
            if level >= 2: use("paladins_smite", 1)
            if level >= 3: use("channel_divinity", table[0], 1)
            masteries, prepared = 2, table[1]
            slots = {i:n for i,n in enumerate(c["classTableGroups"][1]["rowsSpellProgression"][level-1],1) if n}
        else:
            cantrips, prepared = table[-2:]
            slots = {i: n for i, n in enumerate(c["classTableGroups"][1]["rowsSpellProgression"][level-1], 1) if n}
            if c["name"] == "Wizard": use("arcane_recovery", 1)
            if c["name"] == "Cleric" and level >= 2: use("channel_divinity", table[0], 1)
            if c["name"] == "Cleric" and level >= 10: use("divine_intervention", 1)
        for k, expected in (("slots", slots), ("resources", resources), ("cantrips", cantrips), ("prepared", prepared), ("weapon_masteries", masteries)):
            eq(row[k], expected, p + "." + k)
    # Rules below are path-specific: another number elsewhere in the prose can
    # never validate a mutant at the wrong path (e.g. uses vs range vs die size).
    for i, f in enumerate(data["features"]):
        entry = features[(f["origin"], f["name"], f["level"])]
        text = json.dumps(entry["entries"])
        for route, actual in numeric_leaves(f):
            p = f"features[{i}]." + ".".join(map(str, route))
            if route == ("level",): expected = entry["level"]
            elif route == ("name",): expected = entry["name"]
            elif f["name"] == "Improved Critical" and route == ("mechanics", "improved_critical"):
                expected = int(re.search(r"roll of (\d+) or", text)[1])
            elif f["name"] == "Divine Strike" and route == ("mechanics", "divine_strike"):
                expected = re.search(r"\{@damage ([0-9]+d[0-9]+)", text)[1]
            elif f["name"] == "Second Wind" and route == ("actions", 0, "effects", 0, "apply", 0, "heal", "dice"):
                expected = re.search(r"\{@dice ([0-9]+d[0-9]+)", text)[1]
            elif f["name"] in {"Divine Spark", "Turn Undead", "Preserve Life"} and route[-2:] == ("target", "within_ft"):
                expected = int(re.search(r"within (\d+) feet", text)[1])
            elif f["name"] == "Turn Undead" and route == ("actions", 0, "duration", "n"):
                expected = int(re.search(r"for (\d+) minute", text)[1])
            elif f["name"] == "Steady Aim" and route == ("actions", 0, "effects", 0, "apply", 0, "advantage", "uses"):
                v.check("next attack" in text, p, "missing next-attack rule"); expected = 1
            elif f["name"] == "Steady Aim" and route == ("actions", 0, "effects", 0, "apply", 1, "modify", "value"):
                expected = int(re.search(r"Speed\|XPHB} is (\d+)", text)[1])
            else: v.fail(p, "numeric declaration has no source rule/allow-list")
            eq(actual, expected, p)
    return len(list(numeric_leaves(data)))
