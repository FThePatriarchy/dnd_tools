"""Deterministic XMM importer; prints bases, never overwrites reviewed sheets.

python -m engine.monster_import --name Ogre
python -m engine.monster_import --check [data/handwritten/monsters/ogre.yaml ...]
"""
import argparse
from fractions import Fraction
from functools import lru_cache
import json
from pathlib import Path
import re
import yaml

from .dice import parts
from .loader import DAMAGE_TYPES, ROOT, load_sheet, load_spells
from .sheets import effect_block

RAW = Path(__file__).resolve().parents[1] / "raw_data/bestiary/bestiary-xmm.json"
ORIGINAL = ["Goblin Warrior", "Ogre", "Cultist Fanatic", "Young Red Dragon"]
STEP2 = "Bandit|Bandit Captain|Guard|Guard Captain|Tough|Cultist|Priest|Mage|Mage Apprentice|Knight|Warrior Veteran|Gladiator|Assassin|Scout|Berserker|Goblin Minion|Goblin Boss|Hobgoblin Warrior|Hobgoblin Captain|Bugbear Warrior|Bugbear Stalker|Kobold Warrior|Gnoll Warrior|Pirate|Spy|Skeleton|Zombie|Ghoul|Ghast|Wight|Wraith|Specter|Mummy|Vampire Spawn|Wolf|Dire Wolf|Brown Bear|Giant Spider|Owlbear|Worg|Basilisk|Manticore|Wyvern|Troll|Hill Giant|Minotaur of Baphomet|Gelatinous Cube|Imp|Quasit|Hell Hound|Air Elemental|Earth Elemental|Fire Elemental|Water Elemental|Stone Golem|Barbed Devil|Chain Devil|Bone Devil|Vrock|Hezrou|Young White Dragon|Young Black Dragon|Young Green Dragon|Young Blue Dragon|Aboleth|Adult Red Dragon".split("|")
COUNTS = {"one": 1, "two": 2, "three": 3, "four": 4}


def slug(name):
    return name.lower().replace(" ", "_")


def entries_text(value):
    if isinstance(value, str): return value
    if isinstance(value, list): return " ".join(entries_text(x) for x in value)
    if isinstance(value, dict): return entries_text(value.get("entries", value.get("items", [])))
    return ""


def clean_name(name):
    return re.sub(r"\s*(?:\{@recharge[^}]*\}|\(\d+/Day\))", "", name).strip()


def damage_expression(expression):
    n, sides, bonus = parts(expression)
    return f"{n}d{sides}", bonus


def tagged_damage(text, label):
    """Both tagged dice and flat riders, in source order; never infer dice."""
    pattern = r"(?:\{@damage ([^}]+)\}\)|(?<![\w}])\b(\d+))\s+([A-Za-z]+) damage"
    matches = list(re.finditer(pattern, text, re.I))
    effects = []
    for i, match in enumerate(matches):
        expr, flat, dtype = match.groups()
        dtype = dtype.lower()
        if dtype not in DAMAGE_TYPES: raise ValueError(f"{label}: unknown damage type {dtype}")
        rolled, bonus = damage_expression(expr) if expr else ("1d1", int(flat) - 1)
        effect = {"damage": {"dice": rolled, "bonus": bonus, "type": dtype}}
        suffix = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        if "damage if the attack roll had" in match[0] + suffix:
            effect["if"] = "attack.advantage"
        elif re.match(r"\s+if the attack roll had", suffix): effect["if"] = "attack.advantage"
        if "moved 10+ feet" in text[:match.start()] and i > 0:
            effect["if"] = "caster.has_status(charged) and target.size in [T, S, M, L]"
        effects.append(effect)
    if sum(bool(m[1]) for m in matches) != len(re.findall(r"\{@damage ", text)):
        raise ValueError(f"{label}: unparsed weapon damage")
    return effects


def action_limits(entry):
    result = {}
    recharge = re.search(r"\{@recharge(?: (\d)(?:[^}]*))?\}", entry["name"])
    if recharge: result["recharge"] = int(recharge[1] or 6)
    daily = re.search(r"\((\d+)/Day\)", entry["name"])
    if daily: result["resource"] = clean_name(entry["name"])
    return result


def parse_save_action(entry, cost="action"):
    text = entries_text(entry.get("entries", []))
    save = re.search(r"\{@actSave (\w+)\}\s*\{@dc (\d+)\}", text)
    if not save: return None
    # Only the first failed-save clause is immediate damage. Later recurring
    # damage and escape checks are hand-finished, never front-loaded.
    fail = re.search(r"\{@actSaveFail(?: \d+)?\}", text)
    failed = text[fail.end():] if fail else ""
    immediate = re.split(r"\{@actSaveSuccess|While |Until |at the start|at the end|An engulfed", failed, maxsplit=1)[0]
    damage = tagged_damage(immediate, entry["name"])
    target = {"select": "single", "filter": ["creature"], "affects": "any"}
    area = re.search(r"(\d+)-foot(?:-long, \d+-foot-wide)?\s+\{@variantrule (Cone|Line|Emanation|Sphere|Cube)", text, re.I)
    if area:
        target = {"select": "area", "shape": area[2].lower(), "size_ft": int(area[1]), "affects": "all", "filter": ["creature"]}
    block = effect_block("main", target=target, save={"ability": save[1], "dc": int(save[2]), "on_success": "half" if re.search(r"\{@actSaveSuccess\} Half damage", text) else "negate"}, on_fail=damage)
    return {"name": clean_name(entry["name"]), "cost": cost, **action_limits(entry), "effects": [block]}


def parse_multiattack(text, names):
    """Only a plain ordered count, no alternatives or replacement guesses."""
    if re.search(r"\bor\b|combination|replace|uses? |Spellcasting", text): return []
    result = []
    for count, attack in re.findall(r"\b(one|two|three|four|\d+) (.+?) attacks?(?= and |[.,]|$)", text):
        if attack not in names: return []
        result.extend([attack] * (COUNTS[count] if count in COUNTS else int(count)))
    return result


@lru_cache(maxsize=1)
def golden_metadata():
    # Import checks repeatedly need only metadata; invalidate when files change.
    paths = sorted((ROOT / "spells").glob("*.yaml"))
    signature = tuple((str(p), p.stat().st_mtime_ns, p.stat().st_size) for p in paths)
    return dict(_catalog_metadata(signature))


from functools import lru_cache


@lru_cache(maxsize=1)
def _catalog_metadata(signature):
    return tuple((name, (s["level"], s["casting_time"])) for name, s in load_spells().items())


def parse_monster(raw: dict) -> dict:
    if raw["source"] != "XMM": raise ValueError("only XMM (2025) is accepted")
    metadata = golden_metadata() if raw.get("spellcasting") else {}
    cr = raw["cr"]
    if isinstance(cr, dict): cr = cr["cr"]
    pb = raw.get("pb", max(2, 2 + (max(1, int(Fraction(cr))) - 1) // 4))
    ac = raw["ac"][0]
    ctype = raw["type"]
    walk = raw["speed"].get("walk", 0)
    if isinstance(walk, dict): walk = walk["number"]
    initiative = raw.get("initiative", {})
    extra_init = initiative - (raw["dex"] - 10) // 2 if isinstance(initiative, int) else initiative.get("bonus", pb * initiative.get("proficiency", 0))
    if not initiative and "initiative" in raw.get("skill", {}): extra_init = int(raw["skill"]["initiative"]) - (raw["dex"] - 10) // 2
    result = {
        "name": raw["name"], "source": "XMM", "cr": str(cr),
        "ac": ac["ac"] if isinstance(ac, dict) else ac,
        "max_hp": raw["hp"]["average"], "hp_formula": raw["hp"]["formula"],
        "abilities": {a: raw[a] for a in ("str", "dex", "con", "int", "wis", "cha")},
        "speed": walk, "movement_modes": {k: v for k, v in raw["speed"].items() if type(v) in {int, float}}, "creature_type": ctype["type"] if isinstance(ctype, dict) else ctype,
        "alignment": "evil" if "E" in raw.get("alignment", []) else "good" if "G" in raw.get("alignment", []) else "neutral",
        "proficiency_bonus": pb, "save_bonuses": {k: int(v) for k, v in raw.get("save", {}).items()},
        "save_proficiencies": [a for a, value in raw.get("save", {}).items() if int(value) >= (raw[a] - 10) // 2 + pb],
        "initiative_bonus": extra_init,
        "resistances": [], "immunities": [], "vulnerabilities": [],
        "condition_immunities": raw.get("conditionImmune", []),
        "attacks": [], "multiattack": [], "actions": [], "traits": [], "unsupported": [],
    }
    for mode, value in raw["speed"].items():
        if isinstance(value, dict): result["unsupported"].append(f"Conditional {mode} speed: {json.dumps(value, sort_keys=True)}; movement is not simulated")
    for source, dest in (("resist", "resistances"), ("immune", "immunities"), ("vulnerable", "vulnerabilities")):
        for item in raw.get(source, []):
            if isinstance(item, str): result[dest].append(item)
            else: result["unsupported"].append(f"Conditional {source}: {json.dumps(item, sort_keys=True)}")
    for field, cost in (("action", "action"), ("bonus", "bonus_action")):
        for entry in raw.get(field, []):
            name = clean_name(entry["name"])
            if name == "Multiattack": continue
            text = entries_text(entry.get("entries", []))
            hit = re.search(r"\{@hit ([+-]?\d+)\}", text)
            kind = re.search(r"\{@atkr ([^}]+)\}", text)
            if hit and kind:
                # A save rider is not part of a weapon's automatic hit damage.
                immediate = text.split("{@actSave ")[0]
                effects = tagged_damage(immediate, f"{raw['name']}/{name}")
                if not effects: raise ValueError(f"{name}: unparsed weapon damage")
                reach = re.search(r"reach (\d+) ft", text)
                result["attacks"].append({"name": name, "kind": "melee" if "m" in kind[1] else "ranged", "to_hit": int(hit[1]), "reach_ft": int(reach[1]) if reach else 0, "effects": effects, **action_limits(entry)})
            else:
                action = parse_save_action(entry, cost)
                if action: result["actions"].append(action)
                else: result["unsupported"].append(f"Manual {field} required: {entry['name']}")
            daily = re.search(r"\((\d+)/Day\)", entry["name"])
            if daily: result.setdefault("limited_uses", {})[name] = int(daily[1])
    for entry in raw.get("action", []):
        if entry["name"] == "Multiattack":
            result["multiattack"] = parse_multiattack(entries_text(entry["entries"]), {a["name"] for a in result["attacks"]})
            if not result["multiattack"]: result["unsupported"].append("Manual action required: Multiattack")
    for field in ("trait", "reaction", "legendary"):
        for entry in raw.get(field, []): result["unsupported"].append(f"Manual {field} required: {entry['name']}")
    if raw.get("spellcasting"):
        result["unsupported"].append("Manual spellcasting required")
        for sc in raw["spellcasting"]:
            ability = sc["ability"]
            result["spell_ability"] = ability
            result.setdefault("spell_dc", 8 + pb + (raw[ability] - 10) // 2)
            result.setdefault("spell_attack_bonus", pb + (raw[ability] - 10) // 2)
            header = entries_text(sc.get("headerEntries", []))
            dc = re.search(r"\{@dc (\d+)\}", header)
            hit = re.search(r"\{@hit ([+-]?\d+)\}", header)
            if dc: result["spell_dc"] = int(dc[1])
            if hit: result["spell_attack_bonus"] = int(hit[1])
            groups = [("will", sc.get("will", []))] + list(sc.get("daily", {}).items())
            groups += [("recharge " + k, values) for k, values in sc.get("recharge", {}).items()]
            for frequency, entries in groups:
                for text in entries:
                    name = re.search(r"\{@spell ([^|}]+)", text)[1]
                    if name not in metadata: continue
                    result.setdefault("spells", []).append(name)
                    level = re.search(r"level (\d+) version", text)
                    result.setdefault("spell_levels", {})[name] = int(level[1]) if level else metadata[name][0]
                    result.setdefault("spell_costs", {})[name] = {"bonus": "bonus_action"}.get(sc.get("displayAs", "action"), sc.get("displayAs", "action"))
                    if "requiring no spell components" in header:
                        result.setdefault("spell_components", {})[name] = {"v": False, "s": False, "m": False}
                    elif "requiring no Material components" in header:
                        result.setdefault("spell_components", {})[name] = {"m": False}
                    if frequency.startswith("recharge "):
                        result.setdefault("spell_recharge", {})[name] = int(frequency.split()[1])
                    elif frequency != "will":
                        resource = name if frequency.endswith("e") or len(entries) == 1 else clean_name(sc["name"])
                        result.setdefault("limited_uses", {})[resource] = int(frequency.rstrip("e"))
                        result.setdefault("spell_resources", {})[name] = resource
    for trait in raw.get("trait", []):
        if trait["name"].startswith("Legendary Resistance"):
            result.setdefault("limited_uses", {})["legendary_resistance"] = int(re.search(r"\((\d+)/Day", trait["name"])[1])
    for trait in raw.get("trait", []):
        if trait["name"] == "Regeneration":
            text = entries_text(trait["entries"])
            amount = int(re.search(r"regains (\d+)", text)[1])
            blocked = re.search(r"takes (.+?) damage", text)
            types = [t.lower() for t in re.findall(r"[A-Z][a-z]+", blocked[1])] if blocked else []
            result.setdefault("features", {})["regeneration"] = {"amount": amount, "blocked_by": types, "at_zero": "starts its turn with 0" in text}
        elif trait["name"] == "Undead Fortitude":
            result.setdefault("features", {})["undead_fortitude"] = int(re.search(r"\{@dc (\d+)\}", entries_text(trait["entries"]))[1])
    for entry in raw.get("reaction", []):
        if entry["name"] == "Parry":
            result.setdefault("features", {})["parry"] = int(re.search(r"adds (\d+) to its AC", entries_text(entry["entries"]))[1])
    if raw.get("legendary"):
        result["legendary"] = {"uses": raw.get("legendaryActions", 3), "options": []}
        for entry in raw["legendary"]:
            text = entries_text(entry["entries"])
            count = re.search(r"Costs (\d+) Actions", entry["name"])
            option = {"name": entry["name"], "cost": int(count[1]) if count else 1}
            attack = re.search(r"makes one (.+?) attack", text)
            spell = re.search(r"\{@spell ([^|}]+)", text)
            if attack:
                # "Grave Strike" names the attack printed as "Grave Strike (Vampire Form Only)".
                option["attacks"] = [next((a["name"] for a in result["attacks"] if a["name"].split(" (")[0] == attack[1]), attack[1])]
            elif spell and spell[1] in metadata: option["spell"] = spell[1]
            else: continue
            result["legendary"]["options"].append(option)
    return result


def source_monsters(path=RAW):
    with Path(path).open(encoding="utf8") as stream:
        return {m["name"]: m for m in json.load(stream)["monster"] if m.get("source") == "XMM"}


def import_monsters(path=RAW, names=None):
    raw = source_monsters(path)
    names = names or ORIGINAL
    if set(names) - raw.keys(): raise ValueError(f"missing monsters: {set(names) - raw.keys()}")
    return {name: parse_monster(raw[name]) for name in names}



def check_finished_numbers(sheet, raw):
    """Independent text-to-number gate for supplemented payloads, not importer output.

    Each block names its actual XMM entry; copied legendary payloads may name
    the action they invoke. No shared number pool across a monster's entries.
    """
    errors = []
    entries = {f"{kind}:{e['name']}": entries_text(e.get("entries", []))
               for kind in ("action", "trait", "reaction", "bonus", "legendary") for e in raw.get(kind, [])}
    # Spellcasting entries shown among the legendary actions (the vampire's Beguile).
    entries.update({f"legendary:{e['name']}": entries_text(e.get("headerEntries", []))
                    for e in raw.get("spellcasting", []) if e.get("displayAs") == "legendary"})

    def source(ref, path):
        if ref not in entries:
            errors.append(f"{path}.source_ref: unknown XMM entry {ref!r}")
        return entries.get(ref, "")

    def damage_numbers(text, recurring):
        # Parse tagged dice and the plain printed-average form independently of
        # parse_monster/tagged_damage/damage_expression.
        pattern = r"(?:\{@damage (\d+d\d+)(?:\s*([+-])\s*(\d+))?\}|\b\d+ \((\d+d\d+)(?:\s*([+-])\s*(\d+))?\))\)?\s+(\w+) damage"
        result = set()
        for m in re.finditer(pattern, text, re.I):
            die, sign, bonus, plain_die, plain_sign, plain_bonus, dtype = m.groups()
            if recurring:
                start = text.rfind(". ", 0, m.start())
                start = start + 2 if start >= 0 else 0
                end = text.find(". ", m.end())
                sentence = text[max(0, start):end if end != -1 else len(text)]
                if not re.search(r"at the (?:start|end) of (?:each|every)", sentence, re.I): continue
            result.add((die or plain_die, int(bonus or plain_bonus or 0) * (-1 if (sign or plain_sign) == "-" else 1), dtype.lower()))
        # Flat damage is represented by the engine as 1d1 + (N-1).
        for m in re.finditer(r"(?<![\w}])\b(\d+)\s+(\w+) damage", text, re.I):
            result.add(("1d1", int(m[1])-1, m[2].lower()))
        return result

    def declared_capacity(text):
        # Engulf delegates its occupancy rule to this specific trait, not a
        # monster-wide pool of numbers interchangeable with damage or DCs.
        if text == entries.get("action:Engulf"): text = entries.get("trait:Ooze Cube", "")
        match = re.search(r"one Large creature or up to (\w+) Medium", text)
        if match: return COUNTS.get(match[1])
        limbs = re.search(r"from (?:one of (\w+)|both) (tentacles|chains|claws)", text)
        if limbs: return COUNTS.get(limbs[1]) if limbs[1] else 1

    def walk(node, text, path, recurring=False):
        if isinstance(node, list):
            for i, value in enumerate(node): walk(value, text, f"{path}[{i}]", recurring)
        elif isinstance(node, dict):
            if "source_ref" in node: text = source(node["source_ref"], path)
            if "event" in node: recurring = node["event"].startswith(("start_of_turn(", "end_of_turn("))
            if isinstance(node.get("target"), dict):
                target = node["target"]
                if "size_ft" in target:
                    sizes = [int(n) for n in re.findall(r"(\d+)-foot(?:-long, \d+-foot-wide|-radius)?\s+\{@variantrule (?:Cone|Line|Emanation|Sphere|Cube)", text, re.I)]
                    if target["size_ft"] not in sizes: errors.append(f"{path}.target.size_ft: absent from source entry")
                if "n" in target and target["n"] != declared_capacity(text):
                    errors.append(f"{path}.target.n: absent from source entry")
            if isinstance(node.get("duration"), dict) and "n" in node["duration"]:
                minutes = re.search(r"After (\d+) minute", text)
                expected = int(minutes[1]) * 10 if minutes and node["duration"]["type"] == "rounds" else None
                if node["duration"]["n"] != expected: errors.append(f"{path}.duration.n: absent from source entry")
            if "uses" in node and ("on" in node):
                if "the next attack roll" not in text or node["uses"] != 1:
                    errors.append(f"{path}.uses: absent from source entry")
            if isinstance(node.get("save"), dict):
                # A save DC is not interchangeable with an escape DC in that entry.
                dc = re.findall(r"\{@actSave \w+\}\s*\{@dc (\d+)\}", text)
                if not dc: dc = re.findall(r"(?<!escape )\{@dc (\d+)\}", text)
                actual = node["save"].get("dc", sheet.get("spell_dc", 13))
                if actual not in [int(n) for n in dc]: errors.append(f"{path}.save.dc: {actual!r} absent from source entry")
            if "escape_dc" in node:
                dc = [int(n) for n in re.findall(r"escape \{@dc (\d+)\}", text, re.I)]
                dc += [int(n) for n in re.findall(r"escape by taking an action to make a \{@dc (\d+)\}", text, re.I)]
                if node["escape_dc"] not in dc: errors.append(f"{path}.escape_dc: {node['escape_dc']!r} absent from source entry")
            if "obstacle" in node:
                for key, label in (("ac", "AC"), ("hp", "HP")):
                    expected = re.search(rf"\b{label} (\d+)\b", text)
                    if not expected or node["obstacle"][key] != int(expected[1]):
                        errors.append(f"{path}.obstacle.{key}: absent from source entry")
            if "capacity" in node or "large_cost" in node:
                capacity = declared_capacity(text)
                for key in ("capacity", "large_cost"):
                    if key in node and node[key] != capacity:
                        errors.append(f"{path}.{key}: {node[key]!r} absent from source entry")
            if "heal" in node:
                healing = node["heal"]
                expr = healing if isinstance(healing, str) else healing["dice"]
                bonus = 0 if isinstance(healing, str) else healing.get("bonus", 0)
                expected = {(m[1], int(m[2] or 0)) for m in re.finditer(r"regains \d+ \(\{@dice (\d+d\d+)(?:\s*\+\s*(\d+))?\}\)", text)}
                if (expr, bonus) not in expected: errors.append(f"{path}.heal: {(expr, bonus)!r} absent from source entry")
            if isinstance(node.get("damage"), dict):
                d = node["damage"]
                actual = (d["dice"], d.get("bonus", 0), d["type"])
                if actual not in damage_numbers(text, recurring): errors.append(f"{path}.damage: {actual!r} absent from source entry")
            for key, value in node.items():
                if key != "source_ref": walk(value, text, path + "." + str(key), recurring)

    for kind in ("attacks", "actions", "traits"):
        for ability in sheet.get(kind, []):
            matches = [ref for ref in entries if clean_name(ref.split(":", 1)[1]) == ability["name"]]
            text = source(matches[0], kind + "." + ability["name"]) if matches else ""
            for block in ability.get("riders", []) if kind == "attacks" else ability.get("effects", []):
                if block.get("source_ref") and block["source_ref"] not in matches:
                    errors.append(f"{kind}.{ability['name']}.{block.get('id')}.source_ref: does not name this ability's XMM entry")
            walk(ability, text, kind + "." + ability["name"])
    for option in sheet.get("legendary", {}).get("options", []):
        cost = re.search(r"Costs (\d+) Actions", option["name"])
        if option["cost"] != (int(cost[1]) if cost else 1): errors.append(f"legendary.{option['name']}.cost: source cost mismatch")
        walk(option, source("legendary:" + option["name"], "legendary." + option["name"]), "legendary." + option["name"])
    return errors


def check_sheet(sheet, raw=None):
    """Compare source-owned fields, not a frozen hash or a second copy of numbers.

    Hand-finished effects may add riders, but cannot hide missing/changed damage,
    saves, targeting, uses or recharge. All mismatches are returned with paths.
    """
    raw = raw or source_monsters()[sheet["name"]]
    base = parse_monster(raw)
    errors = check_finished_numbers(sheet, raw)
    def compare(expected, actual, path):
        if isinstance(expected, dict):
            for key, value in expected.items(): compare(value, actual.get(key) if isinstance(actual, dict) else None, path + "." + key)
        elif expected != actual: errors.append(f"{path}: source={expected!r}, YAML={actual!r}")
    for key in ("source", "cr", "ac", "max_hp", "hp_formula", "abilities", "speed", "movement_modes", "creature_type", "proficiency_bonus", "save_bonuses", "save_proficiencies", "initiative_bonus", "resistances", "immunities", "vulnerabilities", "condition_immunities"):
        expected = base[key]
        if key in {"condition_immunities", "immunities", "resistances"} and isinstance(expected, list):
            # Conditional entries ("with Mind Blank") are reviewed as their listed names.
            expected = [x for e in expected for x in (e.get("conditionImmune", e.get("immune", [])) if isinstance(e, dict) else [e])]
        compare(expected, sheet.get(key), key)
    for key in ("spell_dc", "spell_ability", "spell_attack_bonus"):
        if key in base: compare(base[key], sheet.get(key), key)
    if base["multiattack"]: compare(base["multiattack"], sheet.get("multiattack"), "multiattack")
    for kind in ("attacks", "actions"):
        for expected in base[kind]:
            actual = next((a for a in sheet.get(kind, []) if a["name"] == expected["name"]), {})
            path = kind + "." + expected["name"]
            for key in expected.keys() - {"effects"}: compare(expected[key], actual.get(key), path + "." + key)
            if kind == "attacks":
                compare([p for p in expected["effects"] if "damage" in p], [p for p in actual.get("effects", []) if "damage" in p], path + ".damage")
            else:
                for block in expected["effects"]:
                    ab = next((b for b in actual.get("effects", []) if b["id"] == block["id"]), {})
                    # Original reviewed dragon uses sheet DC and its own block ID.
                    if not ab and len(actual.get("effects", [])) == 1: ab = actual["effects"][0]
                    save = dict(ab.get("save") or {})
                    save.setdefault("dc", sheet.get("spell_dc"))
                    compare(block["save"], save, path + ".save")
                    entry = next(e for e in (raw or source_monsters()[sheet["name"]]).get("action", []) + (raw or source_monsters()[sheet["name"]]).get("bonus", []) if clean_name(e["name"]) == expected["name"])
                    if "each creature" not in entries_text(entry["entries"]) or block["target"]["select"] == "area":
                        compare(block["target"], ab.get("target"), path + ".target")
                    compare([p for p in block["on_fail"] if "damage" in p], [p for p in ab.get("on_fail", []) if "damage" in p], path + ".damage")
    for key, count in base.get("limited_uses", {}).items(): compare(count, sheet.get("limited_uses", {}).get(key), "limited_uses." + key)
    for key, value in base.get("features", {}).items(): compare(value, sheet.get("features", {}).get(key), "features." + key)
    for key, value in base.get("spell_recharge", {}).items(): compare(value, sheet.get("spell_recharge", {}).get(key), "spell_recharge." + key)
    for key, value in base.get("spell_components", {}).items(): compare(value, sheet.get("spell_components", {}).get(key), "spell_components." + key)
    for name in base.get("spells", []):
        if name not in sheet.get("spells", []): errors.append(f"spells.{name}: missing golden spell")
        compare(base["spell_levels"][name], sheet.get("spell_levels", {}).get(name, golden_metadata()[name][0]), "spell_levels." + name)
        compare(base["spell_costs"][name], sheet.get("spell_costs", {}).get(name, golden_metadata()[name][1]), "spell_costs." + name)
        expected_resource = base.get("spell_resources", {}).get(name)
        actual_resource = sheet.get("spell_resources", {}).get(name, name if name in sheet.get("innate_spells", {}) else None)
        compare(expected_resource, actual_resource, "spell_resources." + name)
        if name in sheet.get("innate_spells", {}):
            compare(base.get("limited_uses", {}).get(expected_resource), sheet["innate_spells"][name], "innate_spells." + name)
    if "legendary" in base:
        compare(base["legendary"]["uses"], sheet.get("legendary", {}).get("uses"), "legendary.uses")
        for option in base["legendary"]["options"]:
            actual = next((o for o in sheet.get("legendary", {}).get("options", []) if o["name"] == option["name"]), {})
            compare(option, actual, "legendary." + option["name"])
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", action="append")
    parser.add_argument("--check", nargs="*", metavar="YAML")
    args = parser.parse_args()
    if args.check is not None:
        paths = [Path(p) for p in args.check] or [ROOT / "monsters" / (slug(n) + ".yaml") for n in (args.name or ORIGINAL + STEP2)]
        failures = []
        for path in paths:
            try: failures.extend(f"{path}: {e}" for e in check_sheet(load_sheet(path)))
            except (ValueError, OSError) as exc: failures.append(f"{path}: {exc}")
        if failures: parser.exit(1, "\n".join(failures) + "\n")
        print(f"{len(paths)} XMM sheets checked: no source drift")
    else: print(yaml.safe_dump(list(import_monsters(names=args.name).values()), sort_keys=False))


if __name__ == "__main__": main()
