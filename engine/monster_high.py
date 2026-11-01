"""Reviewed high-CR XMM monsters for the level 11-20 benchmark.

    python -m engine.monster_high      # writes any missing monster files

Each sheet starts from the deterministic importer (engine.monster_import) and
applies the explicit review decisions below: multiattack routines, hit riders,
legendary actions and the rules the importer leaves as "Manual ... required".
Existing files are never overwritten. Omissions are listed in `unsupported`.
"""
from copy import deepcopy
import re

import yaml

from .loader import ROOT
from .monster_import import import_monsters, slug, source_monsters, entries_text
from .sheets import validate_sheet
from .spell_catalog import area, block, condition, damage, modify, single

DRAGONS = ["Adult White Dragon", "Adult Black Dragon", "Adult Green Dragon", "Adult Blue Dragon",
           "Ancient White Dragon", "Ancient Black Dragon", "Ancient Green Dragon", "Ancient Blue Dragon", "Ancient Red Dragon"]
OTHERS = ["Tyrannosaurus Rex", "Clay Golem", "Roc", "Purple Worm", "Stone Giant", "Frost Giant", "Fire Giant",
          "Horned Devil", "Archmage", "Archpriest", "Mind Flayer", "Vampire"]
MAGIC_RESISTANCE = {"Clay Golem", "Horned Devil", "Archmage", "Mind Flayer"}


def save_block(name, target, ability, dc, effects, *, half=False):
    b = block(target=target, save=ability, half=half, effects=effects)
    b["save"]["dc"] = dc
    b["source_ref"] = "legendary:" + name
    return b


def rider(attack, *effects):
    attack["effects"] += list(effects)


def grapple(dc, max_size, *, restrained=False, stunned=False):
    out = [{"apply_condition": {"condition": "grappled", "escape_dc": dc, "max_size": max_size, "linked": True}}]
    # The engine links a rider condition to the grapple through its source; it ends with the grapple.
    if restrained: out.append({"apply_condition": {"condition": "restrained", "max_size": max_size, "linked": True}})
    if stunned: out.append({"apply_condition": {"condition": "stunned", "max_size": max_size, "linked": True}})
    return out


def attack(sheet, name):
    return next(a for a in sheet["attacks"] if a["name"] == name)


def dc_of(text):
    return int(re.search(r"\{@dc (\d+)\}", text)[1])


def legendary_entries(raw):
    return {e["name"]: entries_text(e["entries"]) for e in raw.get("legendary", [])}


def dragon(sheet, raw):
    """Three Rends (one may be a spell), the breath from the importer, and legendary actions from the text."""
    multi = entries_text(next(e for e in raw["action"] if e["name"] == "Multiattack")["entries"])
    replace = re.search(r"cast \{@spell ([^|}]+)", multi)
    if not sheet.get("multiattack"):
        sheet["multiattack"] = []
        sheet["routines"] = [["Rend", "Rend", "Rend"]]
    if replace: sheet["replacements"] = [replace[1]]
    if "Fear" not in sheet.get("spells", []) and any("Fear" in entries_text(e.get("headerEntries", [])) for e in raw.get("spellcasting", [])):
        sheet.setdefault("spells", []).append("Fear")
        sheet.setdefault("spell_levels", {})["Fear"] = 3
        sheet.setdefault("spell_costs", {})["Fear"] = "action"
        sheet.setdefault("spell_components", {})["Fear"] = {"m": False}
        frightful = next(e for e in raw["spellcasting"] if "Fear" in entries_text(e.get("headerEntries", [])))
        sheet["spell_dc"] = sheet.get("spell_dc", dc_of(entries_text(frightful["headerEntries"])))
        sheet.setdefault("spell_ability", "cha")
    options = []
    for name, text in legendary_entries(raw).items():
        option = {"name": name, "cost": 1}
        spell = re.search(r"uses Spellcasting to cast \{@spell ([^|}]+)", text)
        if spell: option["spell"] = spell[1]
        elif "makes one Rend attack" in text: option["attacks"] = ["Rend"]
        elif name == "Freezing Burst":
            option["effects"] = [save_block(name, area("sphere", 30), "con", dc_of(text), [damage(re.search(r"\{@damage ([^}]+)", text)[1], "cold")])]
        elif name == "Cloud of Insects":
            option["effects"] = [save_block(name, single("visible"), "dex", dc_of(text), [damage(re.search(r"\{@damage ([^}]+)", text)[1], "poison")])]
        elif name == "Noxious Miasma":
            size = int(re.search(r"(\d+)-foot-radius", text)[1])
            option["effects"] = [save_block(name, area("sphere", size), "con", dc_of(text), [damage(re.search(r"\{@damage ([^}]+)", text)[1], "poison"),
                                 modify("ac", -2, until="end_of_turn(target.next_turn)")])]
        else: raise ValueError(f"unreviewed legendary action {name}")
        if "can't take this action again until the start of its next turn" in text: option["once_per_round"] = True
        options.append(option)
    sheet["legendary"] = {"uses": 3, "options": options}
    notes = ["Lair actions and the in-lair Legendary Resistance count are excluded.",
             "Pounce, Cloaked Flight and breath positioning need a grid: Pounce is one Rend, Cloaked Flight is the Invisibility casting."]
    if "Freezing Burst" in options_names(options): notes.append("Freezing Burst's Speed loss is not simulated.")
    if "Cloud of Insects" in options_names(options): notes.append("Cloud of Insects' Disadvantage on Concentration saves is not modeled.")
    return notes


def options_names(options):
    return {o["name"] for o in options}


def review(name, sheet, raw):
    notes = []
    if name in DRAGONS: notes += dragon(sheet, raw)
    if name in MAGIC_RESISTANCE: sheet.setdefault("features", {})["magic_resistance"] = True
    if name == "Tyrannosaurus Rex":
        rider(attack(sheet, "Bite"), *grapple(17, "L", restrained=True))
        rider(attack(sheet, "Tail"), {"apply_condition": {"condition": "prone", "max_size": "H"}})
        notes.append("A creature grappled by the Bite can still be targeted by the Tail.")
    if name == "Clay Golem":
        sheet["multiattack"] = ["Slam", "Slam"]
        sheet["immunities"] = sorted(set(sheet["immunities"]) | {"acid"})
        notes += ["Acid Absorption is modeled as Acid immunity; the healing from Acid damage is not.",
                  "Berserk, Immutable Form and Hasten (with its third Slam) are not modeled.",
                  "The Slam's Hit Point maximum reduction is not modeled."]
    if name == "Roc":
        sheet["routines"] = [["Beak", "Beak"], ["Beak", "Talons"]]
        rider(attack(sheet, "Talons"), *grapple(19, "H", restrained=True))
        notes.append("Swoop (flying off and dropping a grappled creature) needs a grid.")
    if name == "Purple Worm":
        rider(attack(sheet, "Bite"), *grapple(19, "L", restrained=True))
        swallow = next(a for a in sheet["actions"] if a["name"] == "Swallow")["effects"][0]
        swallow["target"]["eligible_if"] = "target.has_condition_from(grappled, caster)"
        swallow["if"] = "target.has_condition_from(grappled, caster)"
        notes += ["Swallow deals its Acid damage once, to a creature the worm has grappled, which stays grappled and restrained; being inside the worm (Blinded, Cover, Acid each turn, regurgitation) is not modeled.",
                  "Tunneler and burrowing need a grid."]
    if name == "Stone Giant":
        sheet["routines"] = [["Stone Club", "Stone Club"], ["Boulder", "Boulder"]]
        rider(attack(sheet, "Boulder"), {"apply_condition": {"condition": "prone", "max_size": "L"}})
        notes.append("Deflect Missile is not modeled.")
    if name == "Frost Giant":
        sheet["routines"] = [["Frost Axe", "Frost Axe"], ["Great Bow", "Great Bow"]]
        text = entries_text(next(e for e in raw["bonus"] if e["name"].startswith("War Cry"))["entries"])
        cry = block(target={"select": "self"}, effects=[{"temp_hp": {"dice": re.search(r"\{@dice ([^}]+)", text)[1].replace(" ", "")}},
                    {"advantage": {"on": "attack_rolls", "scope": "all", "against": None}, "until": "start_of_turn(caster.next_turn)"}])
        cry["source_ref"] = "bonus:" + next(e for e in raw["bonus"] if e["name"].startswith("War Cry"))["name"]
        sheet["traits"].append({"name": "War Cry", "cost": "bonus_action", "recharge": 5, "effects": [cry]})
        notes += ["War Cry always targets the giant itself.", "The Great Bow's Speed reduction is not simulated."]
    if name == "Fire Giant":
        sheet["routines"] = [["Flame Sword", "Flame Sword"], ["Hammer Throw", "Hammer Throw"]]
        rider(attack(sheet, "Hammer Throw"), {"disadvantage": {"on": "attack_rolls", "scope": "all", "against": None, "uses": 1}, "until": "end_of_turn(target.next_turn)"})
        notes.append("The Hammer Throw's push needs a grid.")
    if name == "Horned Devil":
        sheet["routines"] = [["Searing Fork", "Searing Fork", "Searing Fork"], ["Hurl Flame", "Hurl Flame", "Hurl Flame"]]
        sheet["replacements"] = ["Infernal Tail"]
        notes += ["The Infernal Tail's lingering wound (Hit Point loss each turn until stanched or healed) is not modeled.",
                  "Diabolical Restoration happens after death and does not affect the fight."]
    if name == "Archmage":
        # Mind Blank is cast before combat (the stat block's own note), giving the conditional immunities.
        sheet["condition_immunities"] = ["charmed"]
        notes += ["Mind Blank is cast before combat, so the archmage starts immune to Psychic damage and the Charmed condition; Scrying, Teleport, Detect Thoughts and Disguise Self are out of combat."]
    if name == "Archpriest":
        notes.append("Raise Dead and Zone of Truth are out of combat.")
    if name == "Mind Flayer":
        rider(attack(sheet, "Tentacles"), *grapple(14, "M", stunned=True))
        notes += ["Extract Brain killing and devouring is modeled by its damage only; Plane Shift and Detect Thoughts are out of combat."]
    if name == "Vampire":
        strike = attack(sheet, "Grave Strike (Vampire Form Only)")
        rider(strike, {"apply_condition": {"condition": "grappled", "escape_dc": 14, "max_size": "L", "linked": True}})
        sheet["routines"] = [[strike["name"], strike["name"], "Bite (Bat or Vampire Form Only)"]]
        sheet["legendary"]["options"][0]["attacks"] = [strike["name"]]
        bite = next(a for a in sheet["actions"] if a["name"].startswith("Bite"))["effects"][0]
        bite["target"]["eligible_if"] = "target.has_condition(grappled) or target.has_condition(incapacitated) or target.has_condition(restrained)"
        sheet.setdefault("features", {})["life_drain"] = {"attacks": ["Bite (Bat or Vampire Form Only)"], "type": "necrotic", "heal": True}
        beguile = next(e for e in raw["spellcasting"] if e["name"] == "Beguile")
        sheet["spells"] = sheet.get("spells", []) + ["Command"]
        sheet["spell_levels"]["Command"] = 1
        sheet["spell_costs"]["Command"] = "action"
        sheet.setdefault("spell_components", {})["Command"] = {"v": False, "s": False, "m": False}
        sheet["legendary"]["options"].append({"name": "Beguile", "cost": 1, "spell": "Command", "once_per_round": True})  # a Spellcasting entry shown among the legendary actions
        assert "can't take this action again" in entries_text(beguile["headerEntries"])
        notes += ["Shape-Shift, Misty Escape, Spider Climb and Vampire Weakness are not modeled (no sunlight, running water or mist form).",
                  "Each hand grapples separately, but the second-hand limit is not tracked."]
    sheet["unsupported"] = [n for n in sheet.get("unsupported", []) if not n.startswith("Manual") and not n.startswith("Conditional fly")] + notes
    return sheet


def sheets():
    raw = source_monsters()
    bases = import_monsters(names=DRAGONS + OTHERS)
    return {name: review(name, deepcopy(bases[name]), raw[name]) for name in DRAGONS + OTHERS}


def main():
    written = 0
    for name, sheet in sheets().items():
        validate_sheet(sheet, name)
        path = ROOT / "monsters" / (slug(name) + ".yaml")
        if path.exists(): continue
        path.write_text(yaml.safe_dump(sheet, sort_keys=False, allow_unicode=True, width=110), encoding="utf-8")
        written += 1
    print("New monsters:", written)


if __name__ == "__main__":
    main()
