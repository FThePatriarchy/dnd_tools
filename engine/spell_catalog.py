"""XPHB scope review and spell-file authoring helpers. No legacy extractor use.

Run ``python -m engine.spell_catalog --scope`` to reproduce the scope inventory.
Translation recipes are explicit review decisions, not inferred from tags.
Existing files (in particular the golden set) are never overwritten.
"""
import argparse
import json
from pathlib import Path
import re

import yaml

from .loader import ROOT, Validator


SOURCE = ROOT.parents[1] / "raw_data/spell/spells-xphb.json"
SCHOOLS = dict(zip("ACDEINVT", ("abjuration", "conjuration", "divination", "enchantment", "illusion", "necromancy", "evocation", "transmutation")))


def sources():
    return {s["name"]: s for s in json.loads(SOURCE.read_text(encoding="utf8"))["spell"]}


def names(text):
    return set(text.split("; "))


# The negative lists are reviewed semantically: damage/save tags on a social
# spell (Dream, Contact Other Plane) do not make it an arena combat spell.
UTILITY = names("Druidcraft; Elementalism; Friends; Mage Hand; Mending; Message; Prestidigitation; Thaumaturgy; Alarm; Comprehend Languages; Create or Destroy Water; Detect Evil and Good; Detect Magic; Detect Poison and Disease; Disguise Self; Identify; Illusory Script; Purify Food and Drink; Speak with Animals; Tenser's Floating Disk; Unseen Servant; Animal Messenger; Arcane Lock; Augury; Beast Sense; Detect Thoughts; Find Traps; Gentle Repose; Knock; Locate Animals or Plants; Locate Object; Magic Mouth; Nystul's Magic Aura; Pass without Trace; Prayer of Healing; Zone of Truth; Clairvoyance; Create Food and Water; Nondetection; Sending; Speak with Dead; Speak with Plants; Tongues; Water Breathing; Arcane Eye; Divination; Fabricate; Hallucinatory Terrain; Leomund's Secret Chest; Locate Creature; Mordenkainen's Private Sanctum; Stone Shape; Awaken; Commune; Commune with Nature; Contact Other Plane; Creation; Dream; Geas; Legend Lore; Modify Memory; Planar Binding; Raise Dead; Rary's Telepathic Bond; Reincarnate; Scrying; Seeming; Teleportation Circle; Drawmij's Instant Summons; Find the Path; Forbiddance; Guards and Wards; Move Earth; Planar Ally; Programmed Illusion; Tasha's Bubbling Cauldron; Transport via Plants; Wind Walk; Word of Recall; Mirage Arcane; Mordenkainen's Magnificent Mansion; Project Image; Resurrection; Sequester; Teleport; Clone; Control Weather; Demiplane; Glibness; Telepathy; Astral Projection; Gate; True Resurrection")
SPATIAL = names("Dancing Lights; Light; Minor Illusion; Produce Flame; Ray of Frost; Spare the Dying; Thorn Whip; Expeditious Retreat; Feather Fall; Find Familiar; Fog Cloud; Grease; Jump; Longstrider; Silent Image; Thunderous Smite; Thunderwave; Entangle; Faerie Fire; Dissonant Whispers; Ensnaring Strike; Hail of Thorns; Ice Knife; Compelled Duel; Cloud of Daggers; Cordon of Arrows; Darkness; Darkvision; Dragon's Breath; Enthrall; Find Steed; Flaming Sphere; Gust of Wind; Levitate; Misty Step; Moonbeam; Rope Trick; See Invisibility; Silence; Spider Climb; Spike Growth; Web; Blink; Call Lightning; Conjure Animals; Daylight; Fear; Fly; Gaseous Form; Glyph of Warding; Hunger of Hadar; Leomund's Tiny Hut; Lightning Arrow; Magic Circle; Major Image; Meld into Stone; Phantom Steed; Plant Growth; Sleet Storm; Stinking Cloud; Water Walk; Wind Wall; Compulsion; Conjure Minor Elementals; Conjure Woodland Beings; Control Water; Dimension Door; Evard's Black Tentacles; Freedom of Movement; Grasping Vine; Guardian of Faith; Ice Storm; Mordenkainen's Faithful Hound; Otiluke's Resilient Sphere; Wall of Fire; Antilife Shell; Bigby's Hand; Cloudkill; Conjure Elemental; Hallow; Insect Plague; Jallarzi's Storm of Radiance; Mislead; Passwall; Steel Wind Strike; Telekinesis; Tree Stride; Wall of Force; Wall of Stone; Yolande's Regal Presence; Arcane Gate; Blade Barrier; Conjure Fey; Contingency; Otiluke's Freezing Sphere; True Seeing; Wall of Ice; Wall of Thorns; Conjure Celestial; Etherealness; Forcecage; Plane Shift; Reverse Gravity; Symbol; Antimagic Field; Antipathy/Sympathy; Earthquake; Incendiary Cloud; Maze; Tsunami; Imprisonment; Prismatic Wall; Storm of Vengeance; Time Stop; Wish")
REASONS = {
    "Friends": "Social charm automatically fails against a creature you are fighting.",
    "Spare the Dying": "Stabilizes a dying combatant; death-save state is required but no grid is needed.",
    "Find Familiar": "An allied familiar can Help; scouting, senses and placement need adjudication.",
    "Conjure Animals": "2024 intangible pack is a damaging area, not summoned creature stat blocks; end-turn saves are simulable.",
    "Conjure Elemental": "2024 intangible spirit restrains and damages; adjacency and movement triggers need adjudication.",
    "Conjure Minor Elementals": "Attack damage rider is simulable; emanation membership and difficult terrain need adjudication.",
    "Conjure Woodland Beings": "End-turn force damage is simulable; moving emanation and Disengage movement need adjudication.",
    "Dream": "Long-cast sleeping-target communication/nightmare, not an arena damage attack.",
    "Contact Other Plane": "Divination with a self-inflicted failure risk, not an attack spell.",
    "Prayer of Healing": "Ten-minute Short Rest recovery cannot resolve during an arena fight.",
    "Geas": "Minute-long coercion with daily punishment, primarily social rather than a combat action.",
    "Modify Memory": "Fighting targets have Advantage, not automatic success; failed saves cause Charmed and dependent Incapacitated.",
    "Nystul's Magic Aura": "Mask changes how spells and magical effects treat creature type, affecting combat targeting and protection.",
    "Create or Destroy Water": "Extinguishes exposed flames or destroys fog; quantities and affected volumes require environmental geometry.",
    "Speak with Plants": "Creates or removes plant-based Difficult Terrain; plants and terrain membership need a map.",
    "Stone Shape": "Can seal a stone door or open a passage, changing barriers and battlefield access; object geometry is required.",
    "Arcane Lock": "Magically locks doors and other barriers against nonmagical entry; objects and access paths require geometry.",
    "Planar Ally": "Explicitly permits negotiated battle assistance; creature selection, willingness and payment require DM adjudication.",
    "Enthrall": "Fighting targets automatically succeed; distracting noncombatants' Perception is social/exploration utility.",
    "Contingency": "Stores a triggered spell, changing combat action economy without requiring positions.",
    "Imprisonment": "A failed save imposes indefinite combat removal; prison location and objects need separate adjudication.",
    "Time Stop": "Extra personal turns directly change action economy without requiring a grid.",
    "Wish": "Its explicit lower-level spell duplication includes no-grid combat effects; free-form wishes need adjudication.",
}

# Preparation time is not, by itself, a reason to exclude a combat ward or
# control spell. Likewise, lack of engine support doesn't make a spell spatial.
UTILITY -= names("Forbiddance; Guards and Wards; Programmed Illusion; Planar Binding")
SPATIAL |= names("Forbiddance; Guards and Wards; Programmed Illusion")
SPATIAL.add("Continual Flame")  # Same lighting boundary as Light, not a grid-free combat buff.
UTILITY.add("Enthrall")
SPATIAL -= names("Enthrall; Contingency; Imprisonment; Time Stop; Wish")
SPATIAL.discard("Spare the Dying")
UTILITY -= names("Modify Memory; Nystul's Magic Aura; Create or Destroy Water; Speak with Plants; Stone Shape; Arcane Lock; Planar Ally")
SPATIAL |= names("Create or Destroy Water; Speak with Plants; Stone Shape; Arcane Lock; Planar Ally")


def classify(s):
    name = s["name"]
    scope = "out_of_scope" if name in UTILITY else "partial" if name in SPATIAL else "combat"
    if name in REASONS:
        reason = REASONS[name]
    elif scope == "out_of_scope":
        reason = "Utility, information, social or downtime effect; no primary no-grid combat resolution."
    elif scope == "partial":
        if s.get("damageInflict"):
            reason = "Damage is simulable where a trigger/target is known; movement, terrain or vision needs adjudication."
        elif s.get("conditionInflict") or s.get("savingThrow"):
            reason = "Control/save consequences are simulable; spatial or sensory eligibility needs adjudication."
        else:
            reason = "Combat positioning, protection or visibility use; geometry/vision is not modeled."
    elif "SMN" in s.get("miscTags", []):
        reason = "Creates allied combatants that change attacks, defenses or action economy."
    elif s.get("damageInflict"):
        reason = "Direct damage or an attack damage rider changes combat outcomes without a grid."
    elif "HL" in s.get("miscTags", []) or "THP" in s.get("miscTags", []):
        reason = "Healing or temporary hit points changes combat survival."
    elif s.get("conditionInflict"):
        reason = "Applies combat conditions/control; attack and save resolution does not require a grid."
    else:
        reason = "Combat buff, debuff, defense, restoration or action economy changes fight outcomes."
    return {"name": name, "level": s["level"], "scope": scope, "reason": reason}


def slug(name):
    return re.sub(r"[^a-z0-9]+", "_", name.lower().replace("'", "")).strip("_")


def base(s):
    d = s["duration"][0]
    duration = {"type": {"instant": "instant", "permanent": "until_dispelled", "special": "special"}.get(d["type"], "special")}
    if d["type"] == "timed":
        unit = d["duration"]["type"]
        duration = {"type": {"round": "rounds", "minute": "minutes", "hour": "hours", "day": "hours"}[unit], "n": d["duration"]["amount"] * (24 if unit == "day" else 1)}
    distance = s["range"].get("distance", {})
    kind = distance.get("type", s["range"]["type"])
    ran = {"type": "point", "feet": distance["amount"]} if kind == "feet" else {"type": kind if kind in {"self", "touch", "sight", "unlimited"} else "self"}
    if s["range"]["type"] != "point": ran = {"type": "self"}
    c = s.get("components", {})
    m = c.get("m")
    result = dict(name=s["name"], source="XPHB", level=s["level"], school=SCHOOLS[s["school"]], casting_time={"bonus": "bonus_action"}.get(s["time"][0]["unit"], s["time"][0]["unit"]), reaction_trigger=None, range=ran,
                components=dict(v=bool(c.get("v")), s=bool(c.get("s")), m=m.get("text") if isinstance(m, dict) else m, m_consumed=bool(isinstance(m, dict) and m.get("consume")), m_cost_gp=m.get("cost", 0) / 100 if isinstance(m, dict) and "cost" in m else None),
                duration=duration, concentration=bool(d.get("concentration")), ritual=bool(s.get("meta", {}).get("ritual")), choices=[], effects=[], scaling=None, ends_on=[], unsupported=[])
    if result["casting_time"] in {"minute", "minutes", "hour", "hours"}: result["casting_time_n"] = s["time"][0]["number"]
    return result


def single(*filters):
    return {"select": "single", "filter": ["creature", *filters], "affects": "any"}


def area(shape, size, affects="all"):
    return {"select": "area", "shape": shape, "size_ft": size, "affects": affects, "filter": ["creature"]}


def multi(n, *filters):
    return {"select": "n_targets", "n": n, "distinct": True, "up_to": True, **({"min": 1} if n == 1 else {}), "filter": ["creature", *filters], "affects": "any"}


def block(id="main", target=None, *, attack=None, save=None, half=False, effects=(), event="on_cast", **extra):
    b = dict(id=id, event=event, target=target or single(), attack={"type": attack} if attack else None, save={"ability": save, "on_success": "half" if half else "negate"} if save else None, on_hit=[], on_fail=[], on_success=[], apply=[], limit=None)
    b["on_hit" if attack else "on_fail" if save else "apply"] = list(effects)
    b.update(extra)
    return b


def damage(dice, type, **extra):
    return {"damage": {"dice": dice, "bonus": 0, "type": type, **extra}}


def modify(stat, value, op="add", scope="all", **extra):
    return {"modify": dict(stat=stat, op=op, value=value, scope=scope), **extra}


def condition(name, **options):
    return {"apply_condition": dict(condition=name, **options)}


def scale(s, block="main", dice=None, targets=None, cantrip=False):
    change = {"block": block, **({"dice_add": dice} if dice else {"target_n_add": targets})}
    if cantrip: s["scaling"] = {"cantrip": {"at": [5, 11, 17], "effect": change}}
    else: s["scaling"] = {"upcast": {"per_slot_above": s["level"], "changes": [change]}}


def write_spell(s):
    if s["range"]["type"] == "self":
        for b in s["effects"]:
            if b["target"]["select"] == "area": b["target"].setdefault("origin", "caster")
    Validator(s["name"]).spell(s)
    path = ROOT / "spells" / (slug(s["name"]) + ".yaml")
    if path.exists(): return False
    path.write_text(yaml.safe_dump(s, sort_keys=False, allow_unicode=True, width=110), encoding="utf8")
    return True


def cantrips():
    raw = sources()
    result = []
    attacks = {
        "Chill Touch": ("1d10", "necrotic", "melee_spell"),
        "Poison Spray": ("1d12", "poison", "ranged_spell"),
        "Produce Flame": ("1d8", "fire", "ranged_spell"),
        "Ray of Frost": ("1d8", "cold", "ranged_spell"),
        "Shocking Grasp": ("1d8", "lightning", "melee_spell"),
        "Sorcerous Burst": ("1d8", "$damage_type", "ranged_spell"),
        "Starry Wisp": ("1d8", "radiant", "ranged_spell"),
        "Thorn Whip": ("1d6", "piercing", "melee_spell"),
    }
    saves = {
        "Acid Splash": ("1d6", "acid", "dex", area("sphere", 5)),
        "Mind Sliver": ("1d6", "psychic", "int", single("visible")),
        "Thunderclap": ("1d6", "thunder", "con", area("emanation", 5)),
        "Vicious Mockery": ("1d6", "psychic", "wis", single()),
        "Word of Radiance": ("1d6", "radiant", "con", area("emanation", 5, "chosen")),
    }
    for name, (die, dtype, attack) in attacks.items():
        s = base(raw[name])
        t = {"select": "single", "filter": ["creature_or_object"], "affects": "any"} if name in {"Chill Touch", "Produce Flame", "Sorcerous Burst", "Starry Wisp"} else single()
        effects = [damage(die, dtype)]
        if name == "Chill Touch":
            effects.append({"status": {"id": "healing_blocked", "data": {}}, "until": "end_of_turn(caster.next_turn)"})
        if name == "Ray of Frost":
            effects.append(modify("speed", -10, until="start_of_turn(caster.next_turn)"))
            s["unsupported"].append("Speed reduction is stored; no movement is simulated.")
        if name == "Shocking Grasp":
            s["unsupported"].append("Opportunity Attack prevention until the target's next turn: no movement or opportunity attacks are simulated.")
        if name == "Starry Wisp":
            effects.append({"status": {"id": "invisibility_suppressed", "data": {}}, "until": "end_of_turn(caster.next_turn)"})
            s["unsupported"].append("Dim Light emission needs a lighting/vision model.")
        if name == "Thorn Whip": s["unsupported"].append("Optional pull of a Large-or-smaller target needs positions.")
        if name == "Sorcerous Burst":
            s["choices"] = [{"id": "damage_type", "options": raw[name]["damageInflict"], "when": "on_cast"}]
            effects[0]["damage"]["explode_max"] = "spell_mod"
        s["effects"] = [block(attack=attack, target=t, effects=effects)]
        if name == "Produce Flame":
            s["effects"][0]["event"] = "action_command"
            s["recast_ends_previous"] = True
            s["unsupported"].append("Flame lighting and precise hurl range need vision/positions; hurling costs a separate Magic action.")
        scale(s, dice=die, cantrip=True)
        result.append(s)
    for name, (die, dtype, save, t) in saves.items():
        s = base(raw[name])
        effects = [damage(die, dtype)]
        if name == "Mind Sliver":
            p = modify("save", "1d4", op="sub", until="end_of_turn(caster.next_turn)")
            p["modify"]["uses"] = 1
            effects.append(p)
        if name == "Vicious Mockery":
            effects.append({"disadvantage": {"on": "attack_rolls", "scope": "all", "against": None, "uses": 1}, "until": "end_of_turn(target.next_turn)"})
            s["unsupported"].append("See-or-hear eligibility is assumed; hearing and sound propagation are not simulated.")
        if name == "Word of Radiance": t["filter"].append("visible")
        s["effects"] = [block(target=t, save=save, effects=effects)]
        scale(s, dice=die, cantrip=True)
        result.append(s)
    s = base(raw["Toll the Dead"])
    s["effects"] = [block(target=single("visible"), save="wis", effects=[damage("1d8", "necrotic", wounded_dice="1d12")])]
    scale(s, dice="1d8", cantrip=True)
    result.append(s)
    s = base(raw["Blade Ward"])
    p = modify("attack_roll", "1d4", op="sub")
    p["modify"]["recipient"] = "any_attacker"
    s["effects"] = [block(target={"select": "self"}, effects=[p])]
    result.append(s)
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--scope", action="store_true")
    p.add_argument("--level", type=int)
    args = p.parse_args()
    if args.scope:
        records = [classify(s) for s in sources().values()]
        (ROOT / "spell_scope.yaml").write_text(yaml.safe_dump({"source": "XPHB", "spells": records}, sort_keys=False, width=110), encoding="utf8")
        from collections import Counter
        print(Counter(s["scope"] for s in records))
    if args.level == 0:
        print("New cantrips:", sum(write_spell(s) for s in cantrips()))


if __name__ == "__main__":
    main()
