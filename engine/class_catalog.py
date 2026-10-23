"""Authoring recipes, intentionally separate from the source-number verifier."""
import json
from pathlib import Path
import yaml

from .loader import ROOT
from .sheets import effect_block

RAW = Path(__file__).resolve().parents[1] / "raw_data" / "class"
SUBS = {"fighter": "Champion", "rogue": "Assassin", "wizard": "Evoker", "cleric": "Life"}


def records(name):
    data = json.loads((RAW / ("class-" + name + ".json")).read_text(encoding="utf-8"))
    base = next(x for x in data["class"] if x["source"] == "XPHB")
    sub = next(x for x in data["subclass"] if x["source"] == "XPHB" and x["shortName"] == SUBS[name])
    features = [("class", x) for x in data["classFeature"] if x["source"] == "XPHB" and x["level"] <= 10]
    features += [("subclass", x) for x in data["subclassFeature"] if x["source"] == "XPHB" and x.get("subclassShortName") == SUBS[name] and x["level"] <= 10]
    return base, sub, features


def action(name, cost, effects, resource=None, **extra):
    return {"name": name, "cost": cost, **({"resource": resource} if resource else {}), "effects": effects, **({"magical":True} if resource=="channel_divinity" else {}), **extra}


def feature_payload(name, feature):
    n = feature["name"]
    flags = {
        "Tactical Mind": {"tactical_mind": True}, "Tactical Master": {"tactical_master": True},
        "Improved Critical": {"improved_critical": 19},
        "Remarkable Athlete": {"initiative_advantage": True, "remarkable_athlete": True},
        "Heroic Warrior": {"heroic_warrior": True},
        "Sneak Attack": {"sneak_attack": "sneak_dice"},
        "Assassinate": {"initiative_advantage": True, "assassinate": True},
        "Uncanny Dodge": {"uncanny_dodge": True}, "Evasion": {"evasion": True},
        "Reliable Talent": {"reliable_talent": True},
        "Infiltration Expertise": {"roving_aim": True}, "Assassin's Tools": {"poisoners_kit": True},
        "Potent Cantrip": {"potent_cantrip": True}, "Sculpt Spells": {"sculpt_spells": True},
        "Empowered Evocation": {"empowered_evocation": True},
        "Arcane Recovery": {"arcane_recovery": True},
        "Memorize Spell": {"memorize_spell": True}, "Sear Undead": {"sear_undead": True},
        "Disciple of Life": {"disciple_of_life": True}, "Blessed Healer": {"blessed_healer": True},
        "Divine Strike": {"divine_strike": "1d8"}, "Potent Spellcasting": {"potent_spellcasting": True},
        "Thaumaturge": {"thaumaturge": True},
    }
    if n in flags: return {"mechanics": flags[n]}
    if n == "Second Wind":
        return {"actions": [action(n, "bonus_action", [effect_block("second_wind", apply=[{"heal": {"dice": "1d10", "bonus": "class_level"}}])], "second_wind")]}
    if n == "Action Surge":
        return {"actions": [action(n, "free", [], "action_surge", grants_action=True)]}
    if n == "Indomitable": return {"mechanics": {"progression": True}}
    if n == "Steady Aim":
        return {"actions": [action(n, "bonus_action", [effect_block("steady_aim", apply=[
            {"advantage": {"on": "attack_rolls", "scope": "all", "against": None, "uses": 1}, "until": "end_of_turn(caster.this_turn)"},
            {"modify": {"stat": "speed", "op": "set", "value": 0, "scope": "all"}, "until": "end_of_turn(caster.this_turn)"}])])]}
    if n == "Cunning Action":
        return {"actions": [action(n, "bonus_action", [effect_block("cunning_action", apply=[{"status": {"id": "disengaged", "data": {}}, "until": "end_of_turn(caster.this_turn)"}])])],
                "unsupported": "Disengage bookkeeping executes; Dash movement and Hide concealment require a grid/adjudication, and give no invented advantage."}
    if n == "Divine Spark":
        t = {"select": "single", "filter": ["creature", "visible"], "affects": "any", "eligible_if": "target != caster", "within_ft": 30}
        h = effect_block("spark_heal", target=t, apply=[{"heal": {"dice": "spark_dice", "bonus": "spell_mod"}}])
        d = effect_block("spark_damage", target=t, save={"ability": "con", "on_success": "half"}, on_fail=[{"damage": {"dice": "spark_dice", "bonus": "spell_mod", "type": "radiant"}}])
        from copy import deepcopy
        necrotic=deepcopy(d); necrotic["on_fail"][0]["damage"]["type"]="necrotic"
        return {"actions": [action("Divine Spark (Heal)", "action", [h], "channel_divinity"), action("Divine Spark (Radiant)", "action", [d], "channel_divinity"), action("Divine Spark (Necrotic)", "action", [necrotic], "channel_divinity")]}
    if n == "Turn Undead":
        t = {"select": "n_targets", "n": "all", "distinct": True, "up_to": True, "filter": ["creature"], "affects": "enemy", "within_ft": 30, "eligible_if": "target.creature_type == undead"}
        b = effect_block("turn_undead", target=t, save={"ability": "wis", "on_success": "negate"}, on_fail=[
            {"apply_condition": {"condition": "frightened", "ends_on_damage": "any", "linked": True}},
            {"apply_condition": {"condition": "incapacitated", "ends_on_damage": "any", "linked": True}}])
        return {"actions": [action(n, "action", [b], "channel_divinity", duration={"type": "minutes", "n": 1})],
                "unsupported": "Fleeing movement is not simulated; chosen visible/in-range undead are assumed in reach under the shared no-grid convention."}
    if n == "Preserve Life":
        b = effect_block("preserve_life", target={"select": "n_targets", "n": "all", "distinct": True, "up_to": True, "filter": ["creature"], "affects": "any", "within_ft": 30, "eligible_if": "target.bloodied"}, apply=[{"heal_pool": {"amount": "life_pool", "cap": "half"}}])
        return {"actions": [action(n, "action", [b], "channel_divinity")]}
    if n in {"Thieves' Cant", "Ritual Adept"}:
        return {"unsupported": "Language/ritual exploration outside combat and scripted rests."}
    if n == "Tactical Shift": return {"unsupported": "Movement and opportunity attacks require a grid."}
    return {"mechanics": {"builder": True}}


def declaration(name):
    base, sub, raw_features = records(name)
    result = {"name": name, "source": "XPHB", "subclass": sub["shortName"].lower(),
              "hit_die": "d" + str(base["hd"]["faces"]), "saves": base["proficiency"],
              "subclass_level": 3, "asi_levels": [], "levels": {}, "features": []}
    for origin, f in raw_features:
        record={"name": f["name"], "level": f["level"], "origin": origin, **feature_payload(name, f)}
        notes={"Remarkable Athlete":"Post-critical movement needs a grid.",
               "Tactical Master":"Push displacement and Slow movement need a grid; Sap executes and Slow's speed modifier is stored.",
               "Infiltration Expertise":"Mimicry is social/exploration only; Roving Aim executes.",
               "Withdraw (Cost: 1d6)":"Movement and opportunity attacks require a grid; only expenditure/permission bookkeeping executes."}
        if f["name"] in notes: record["unsupported"]=notes[f["name"]]
        result["features"].append(record)
        if origin == "class" and f["name"] == "Ability Score Improvement": result["asi_levels"].append(f["level"])
    for level in range(1, 11):
        row = {"proficiency_bonus": 2 + (level - 1) // 4, "hit_die": result["hit_die"],
               "features": [f["name"] for f in result["features"] if f["level"] == level],
               "resources": {}, "weapon_masteries": 0, "cantrips": 0, "prepared": 0, "slots": {}}
        def resource(key, maximum, short=0):
            row["resources"][key] = {"max": maximum, "short_rest": short, "long_rest": "all"}
        if name == "fighter":
            resource("second_wind", 2 if level < 4 else 3 if level < 10 else 4, 1)
            if level >= 2: resource("action_surge", 1, "all")
            if level >= 9: resource("indomitable", 1)
            row["weapon_masteries"] = 3 if level < 4 else 4 if level < 10 else 5
        if name == "rogue":
            row["weapon_masteries"] = 2
            row["sneak_attack"] = f"{(level+1)//2}d6"
        if name in {"wizard", "cleric"}:
            row["cantrips"] = 3 if level < 4 else 4 if level < 10 else 5
            row["prepared"] = [4, 5, 6, 7, 9, 10, 11, 12, 14, 15][level - 1]
            slots = base["classTableGroups"][1]["rowsSpellProgression"][level - 1]
            row["slots"] = {i: n for i, n in enumerate(slots, 1) if n}
            if name == "wizard": resource("arcane_recovery", 1)
            if name == "cleric" and level >= 2: resource("channel_divinity", 2 if level < 6 else 3, 1)
            if name == "cleric" and level >= 10: resource("divine_intervention", 1)
        result["levels"][level] = row
    return result


def write_class(name):
    folder = ROOT / "classes"
    folder.mkdir(exist_ok=True)
    (folder / (name + ".yaml")).write_text(yaml.safe_dump(declaration(name), sort_keys=False, allow_unicode=True), encoding="utf-8")


if __name__ == "__main__":
    import sys
    for name in sys.argv[1:] or SUBS: write_class(name)
