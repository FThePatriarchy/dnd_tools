"""Deterministic 5etools structured-field and tagged-weapon parser.

    python -m engine.monster_import --name Ogre

Prints a base YAML sheet. It deliberately does not overwrite the reviewed
supplements in monsters/: multiattack, breath, traits and spells are manual.
"""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import re
import yaml

from .dice import parts
from .loader import DAMAGE_TYPES

RAW = Path(__file__).resolve().parents[1] / "raw_data" / "bestiary" / "bestiary-xmm.json"


def damage_expression(expression):
    n, sides, bonus = parts(expression)
    return f"{n}d{sides}", bonus


def parse_monster(raw: dict) -> dict:
    """Only structured numbers and explicit hit/damage tags, not prose inference."""
    cr = raw["cr"]
    if isinstance(cr, dict): cr = cr["cr"]
    pb = raw.get("pb", max(2, 2 + (max(1, int(Fraction(cr))) - 1) // 4))
    ac = raw["ac"][0]
    creature_type = raw["type"]
    result = {
        "name": raw["name"], "source": raw["source"], "cr": str(cr),
        "ac": ac["ac"] if isinstance(ac, dict) else ac,
        "max_hp": raw["hp"]["average"], "hp_formula": raw["hp"]["formula"],
        "abilities": {a: raw[a] for a in ("str", "dex", "con", "int", "wis", "cha")},
        "speed": raw["speed"].get("walk", 0),
        "creature_type": creature_type["type"] if isinstance(creature_type, dict) else creature_type,
        "alignment": "evil" if "E" in raw.get("alignment", []) else "good" if "G" in raw.get("alignment", []) else "neutral",
        "proficiency_bonus": pb, "save_bonuses": {k: int(v) for k, v in raw.get("save", {}).items()},
        "save_proficiencies": [a for a, value in raw.get("save", {}).items() if int(value) >= (raw[a] - 10) // 2 + pb],
        "initiative_bonus": pb * raw.get("initiative", {}).get("proficiency", 0),
        "resistances": [], "immunities": [], "vulnerabilities": [],
        "condition_immunities": raw.get("conditionImmune", []),
        "attacks": [], "multiattack": [], "actions": [], "traits": [], "unsupported": [],
    }
    for source, dest in (("resist", "resistances"), ("immune", "immunities"), ("vulnerable", "vulnerabilities")):
        for item in raw.get(source, []):
            if isinstance(item, str): result[dest].append(item)
            else: result["unsupported"].append(f"Conditional {source}: {json.dumps(item, sort_keys=True)}")
    for action in raw.get("action", []):
        text = " ".join(x for x in action.get("entries", []) if isinstance(x, str))
        hit = re.search(r"\{@hit ([+-]?\d+)\}", text)
        kind = re.search(r"\{@atkr ([^}]+)\}", text)
        if not hit or not kind:
            result["unsupported"].append(f"Manual action required: {action['name']}")
            continue
        effects = []
        matches = list(re.finditer(r"\{@damage ([^}]+)\}\)\s+([A-Za-z]+) damage", text, re.I))
        for i, match in enumerate(matches):
            expression, damage_type = match.groups()
            damage_type = damage_type.lower()
            if damage_type not in DAMAGE_TYPES: raise ValueError(f"{raw['name']}/{action['name']}: unknown damage type {damage_type}")
            rolled, bonus = damage_expression(expression)
            effect = {"damage": {"dice": rolled, "bonus": bonus, "type": damage_type}}
            suffix = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
            if " if " in suffix:
                if "attack roll had {@variantrule Advantage" not in suffix:
                    raise ValueError(f"{raw['name']}/{action['name']}: unsupported conditional damage")
                effect["if"] = "attack.advantage"
            effects.append(effect)
        if not effects or len(matches) != len(re.findall(r"\{@damage ", text)):
            raise ValueError(f"{raw['name']}/{action['name']}: unparsed weapon damage")
        reach = re.search(r"reach (\d+) ft", text)
        result["attacks"].append({"name": action["name"], "kind": "melee" if "m" in kind[1] else "ranged",
                                  "to_hit": int(hit[1]), "reach_ft": int(reach[1]) if reach else 0, "effects": effects})
    for field in ("trait", "bonus", "reaction", "legendary"):
        for entry in raw.get(field, []): result["unsupported"].append(f"Manual {field} required: {entry['name']}")
    if raw.get("spellcasting"): result["unsupported"].append("Manual spellcasting required")
    return result


def import_monsters(path=RAW, names=None):
    with Path(path).open(encoding="utf8") as stream: monsters = json.load(stream)["monster"]
    names = names or ["Goblin Warrior", "Ogre", "Cultist Fanatic", "Young Red Dragon"]
    result = {m["name"]: parse_monster(m) for m in monsters if m["name"] in names}
    if set(result) != set(names): raise ValueError(f"missing monsters: {set(names) - set(result)}")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", action="append")
    args = parser.parse_args()
    print(yaml.safe_dump(list(import_monsters(names=args.name).values()), sort_keys=False))


if __name__ == "__main__": main()
