"""Explicit XPHB Bestial/Undead Spirit stat blocks embedded in spell YAML."""
from copy import deepcopy

from .spell_catalog import sources, base, block, area, condition, damage


def spells(level):
    if level == 4: return [elemental()]
    if level not in {2, 3}: return []
    name = "Summon Beast" if level == 2 else "Summon Undead"
    s = base(sources()[name])
    beast = level == 2
    forms = {}
    for form in (["air", "land", "water"] if beast else ["ghostly", "putrid", "skeletal"]):
        die = "1d8" if beast or form == "ghostly" else "2d4" if form == "skeletal" else "1d6"
        dtype = "piercing" if beast else "slashing" if form == "putrid" else "necrotic"
        ability_values = (18, 11, 16, 4, 14, 5) if beast else (12, 16, 15, 4, 10, 9)
        effects = [damage(die, dtype, bonus=6)]
        if form == "ghostly": effects.append({**condition("frightened"), "until": "end_of_turn(target.next_turn)"})
        if form == "putrid": effects.append({**condition("paralyzed"), "until": "end_of_turn(target.next_turn)", "if": "target.has_condition(poisoned)"})
        attack_name = "Rend" if beast else {"ghostly": "Deathly Touch", "putrid": "Rotting Claw", "skeletal": "Grave Bolt"}[form]
        sheet = dict(name=("Bestial Spirit" if beast else "Undead Spirit") + " (" + form.title() + ")", source="XPHB", max_hp=(20 if form in {"air", "skeletal"} else 30), ac=11 + level,
                     abilities=dict(zip(("str", "dex", "con", "int", "wis", "cha"), ability_values)), speed=30, movement_modes={"walk": 30}, creature_type="beast" if beast else "undead", size="S" if beast else "M", proficiency_bonus="caster",
                     attacks=[dict(name=attack_name, kind="ranged" if form == "skeletal" else "melee", to_hit="spell_attack", reach_ft=0 if form == "skeletal" else 5, effects=effects)],
                     resistances=[], immunities=[] if beast else ["necrotic", "poison"], condition_immunities=[] if beast else ["exhaustion", "frightened", "paralyzed", "poisoned"], features={})
        if form in {"land", "water"}: sheet["features"]["pack_tactics"] = True
        if form == "skeletal": sheet["attacks"][0]["range_ft"] = 150
        if form == "land": sheet["movement_modes"]["climb"] = 30
        if form == "water": sheet["movement_modes"]["swim"] = 30
        if form == "air": sheet["movement_modes"]["fly"] = 60
        if form == "ghostly": sheet["movement_modes"]["fly"] = 40
        if form == "putrid":
            b = block(target={**area("emanation", 5), "exclude": "summoner"}, save="con", effects=[{**condition("poisoned"), "until": "start_of_turn(target.next_turn)"}])
            sheet["traits"] = [dict(name="Festering Aura", cost="free", trigger="creature_turn_start", effects=[b])]
        forms[form] = sheet
    s["choices"] = [{"id": "form", "options": list(forms), "when": "on_cast"}]
    s["effects"] = [block(target={"select": "self"}, effects=[{"summon": dict(choice="$form", forms=forms, base_slot=level, per_slot={"ac": 1, "max_hp": 5 if beast else 10, "damage_bonus": 1}, attack_count_divisor=2)}])]
    s["unsupported"].append("Unoccupied-space placement, senses, languages, flight, swimming, Flyby and exact Pack Tactics proximity require a grid/environment. Pack Tactics uses the existing no-grid engaged-ally heuristic.")
    if not beast: s["unsupported"].append("Ghostly Incorporeal Passage, shunting and its 1d10 Force damage per 5 feet require object collision/positions; not front-loaded as attack damage.")
    return [s]


def elemental():
    """Use the printed parent stat block, not the erroneous _versions attacks."""
    s = base(sources()["Summon Elemental"])
    types = {"air": "lightning", "earth": "bludgeoning", "fire": "fire", "water": "cold"}
    resistances = {"air": ["lightning", "thunder"], "earth": ["piercing", "slashing"], "fire": [], "water": ["acid"]}
    movement = {"air": {"fly": 40}, "earth": {"burrow": 40}, "fire": {}, "water": {"swim": 40}}
    forms = {}
    for form, dtype in types.items():
        forms[form] = dict(name="Elemental Spirit (" + form.title() + ")", source="XPHB",
            max_hp=50, ac=15, abilities=dict(zip(("str", "dex", "con", "int", "wis", "cha"), (18, 15, 17, 4, 10, 16))),
            speed=40, movement_modes={"walk": 40, **movement[form]}, creature_type="elemental", size="M", proficiency_bonus="caster",
            attacks=[dict(name="Slam", kind="melee", to_hit="spell_attack", reach_ft=5, effects=[damage("1d10", dtype, bonus=8)])],
            resistances=resistances[form], immunities=["poison"] + (["fire"] if form == "fire" else []),
            condition_immunities=["exhaustion", "paralyzed", "petrified", "poisoned"], features={})
    s["choices"] = [{"id": "form", "options": list(forms), "when": "on_cast"}]
    s["effects"] = [block(target={"select": "self"}, effects=[{"summon": dict(choice="$form", forms=forms, base_slot=4,
        per_slot={"ac": 1, "max_hp": 10, "damage_bonus": 1}, attack_count_divisor=2)}])]
    s["unsupported"] = ["Placement, Amorphous Form's narrow-space movement, burrowing, hovering, swimming and senses require positions/environment. The main XPHB stat block determines each form's damage type; conflicting generated _versions are not used."]
    return s
