"""Strict level-1..10 class declarations; no older-edition fallback."""
import re

from .loader import ROOT, Validator, ValidationError, read_yaml
from .sheets import validate_sheet

SUBCLASSES = {"fighter": "champion", "rogue": "assassin", "wizard": "evoker", "cleric": "life"}
SYMBOLS = {"class_level", "sneak_dice", "spark_dice", "wis_dice"}
CLASS_FLAGS = set("improved_critical initiative_advantage remarkable_athlete tactical_mind tactical_master heroic_warrior sneak_attack assassinate uncanny_dodge reliable_talent roving_aim poisoners_kit evasion potent_cantrip sculpt_spells empowered_evocation disciple_of_life blessed_healer potent_spellcasting divine_strike arcane_recovery memorize_spell sear_undead thaumaturge armored".split())
BOOL_FLAGS = CLASS_FLAGS - {"improved_critical", "sneak_attack", "divine_strike"}


def substitute(value, level, row):
    if isinstance(value, dict): return {k: substitute(v, level, row) for k, v in value.items()}
    if isinstance(value, list): return [substitute(v, level, row) for v in value]
    if value == "class_level": return level
    if value == "sneak_dice": return row["sneak_attack"]
    if value == "spark_dice": return "2d8" if level >= 7 else "1d8"
    if value == "life_pool": return 5 * level
    return value


def validate_class(data, path="<class>", *, source_check=True):
    v = Validator(path)
    v.obj(data, "$", "name source subclass hit_die saves subclass_level asi_levels levels features")
    v.enum(data["name"], SUBCLASSES, "name")
    v.enum(data["source"], {"XPHB"}, "source")
    v.enum(data["subclass"], {SUBCLASSES[data["name"]]}, "subclass")
    v.enum(data["hit_die"], {"d6", "d8", "d10"}, "hit_die")
    v.sequence(data["saves"], "saves")
    for s in data["saves"]: v.enum(s, {"str", "dex", "con", "int", "wis", "cha"}, "saves")
    v.number(data["subclass_level"], "subclass_level", 1, True)
    v.sequence(data["asi_levels"], "asi_levels")
    for n in data["asi_levels"]: v.number(n, "asi_levels", 1, True)
    v.check(isinstance(data["levels"], dict), "levels", "expected mapping")
    v.check(set(data["levels"]) == set(range(1, 11)), "levels", "requires levels 1..10")
    v.sequence(data["features"], "features")
    names = set()
    for i, f in enumerate(data["features"]):
        p = f"features[{i}]"
        v.obj(f, p, "name level origin", "mechanics actions unsupported")
        v.text(f["name"], p + ".name")
        v.number(f["level"], p + ".level", 1, True)
        v.check(f["level"] <= 10, p, "level beyond scope")
        v.enum(f["origin"], {"class", "subclass"}, p + ".origin")
        v.check((f["name"], f["level"], f["origin"]) not in names, p, "duplicate feature")
        names.add((f["name"], f["level"], f["origin"]))
        v.check(any(k in f for k in ("mechanics", "actions", "unsupported")), p, "no implementation or reason")
        if "unsupported" in f: v.text(f["unsupported"], p + ".unsupported")
        if "mechanics" in f:
            v.obj(f["mechanics"], p + ".mechanics", "", CLASS_FLAGS | {"progression", "builder"})
            for k, x in f["mechanics"].items():
                if k in BOOL_FLAGS: v.boolean(x, p + ".mechanics." + k)
                elif k in {"progression", "builder"}: v.boolean(x, p + ".mechanics." + k)
                elif k == "improved_critical": v.number(x, p + ".mechanics." + k, 1, True)
                else: v.check(x in SYMBOLS or bool(re.fullmatch(r"[1-9][0-9]*d[1-9][0-9]*", str(x))), p, "invalid dice")
        if "actions" in f: v.sequence(f["actions"], p + ".actions")
    for level, row in data["levels"].items():
        p = f"levels.{level}"
        v.obj(row, p, "proficiency_bonus hit_die features resources weapon_masteries cantrips prepared slots", "sneak_attack")
        for k in ("proficiency_bonus", "weapon_masteries", "cantrips", "prepared"): v.number(row[k], p + "." + k, 0, True)
        v.enum(row["hit_die"], {data["hit_die"]}, p + ".hit_die")
        v.sequence(row["features"], p + ".features")
        for name in row["features"]: v.text(name, p + ".features")
        dummy = {"name": "Validation", "source": "XPHB", "max_hp": 1, "ac": 10,
                 "abilities": dict.fromkeys(("str", "dex", "con", "int", "wis", "cha"), 10),
                 "speed": 30, "creature_type": "humanoid", "proficiency_bonus": row["proficiency_bonus"],
                 "limited_uses": row["resources"], "spell_slots": row["slots"], "actions": []}
        for f in data["features"]:
            if f["level"] <= level:
                dummy["actions"].extend(substitute(f.get("actions", []), level, row))
        validate_sheet(dummy, str(path) + ":" + p)
        if "sneak_attack" in row: v.dice(row["sneak_attack"], p + ".sneak_attack")
    if source_check:
        from .class_source import check_class_source
        check_class_source(data, path)
    return data


def load_class(name):
    if name not in SUBCLASSES: raise ValueError(f"unknown class: {name}")
    path = ROOT / "classes" / (name + ".yaml")
    try: return validate_class(read_yaml(path), path)
    except (TypeError, KeyError, AttributeError, IndexError) as exc:
        raise ValidationError(f"{path}:$: malformed class ({exc})") from exc
