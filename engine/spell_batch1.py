"""Explicit first-level XPHB declarations, using the golden effect vocabulary."""
from .spell_catalog import sources, base, block, single, multi, area, damage, modify, condition, scale


def spells():
    raw = sources()
    result = []
    saves = {
        "Arms of Hadar": ("2d6", "necrotic", "str", area("emanation", 10), "1d6"),
        "Burning Hands": ("3d6", "fire", "dex", area("cone", 15), "1d6"),
        "Dissonant Whispers": ("3d6", "psychic", "wis", single("visible"), "1d6"),
        "Inflict Wounds": ("2d10", "necrotic", "con", single(), "1d10"),
        "Thunderwave": ("2d8", "thunder", "con", area("cube", 15), "1d8"),
    }
    for name, (die, dtype, save, target, increment) in saves.items():
        s = base(raw[name])
        ps = [damage(die, dtype)]
        if name == "Arms of Hadar": ps.append({"turn_rules": {"no_reactions": True}, "until": "start_of_turn(target.next_turn)"})
        if name == "Dissonant Whispers":
            ps.append({"spend_reaction": True})
            s["unsupported"].append("Safest-route reaction movement requires a grid; the reaction is spent on a failed save if available.")
        if name == "Burning Hands": s["unsupported"].append("Unworn, uncarried object ignition is not simulated.")
        if name == "Thunderwave": s["unsupported"].append("Creature/object pushing and sound propagation require positions/environment.")
        s["effects"] = [block(target=target, save=save, half=True, effects=ps)]
        scale(s, dice=increment)
        result.append(s)
    s = base(raw["Ray of Sickness"])
    s["effects"] = [block(attack="ranged_spell", effects=[damage("2d8", "poison"), {**condition("poisoned"), "until": "end_of_turn(caster.next_turn)"}])]
    scale(s, dice="1d8")
    result.append(s)
    s = base(raw["Color Spray"])
    s["effects"] = [block(target=area("cone", 15), save="con", effects=[{**condition("blinded"), "until": "end_of_turn(caster.next_turn)"}])]
    result.append(s)
    s = base(raw["Bane"])
    s["effects"] = [block(target=multi(3, "visible"), save="cha", effects=[modify("attack_roll", "1d4", "sub"), modify("save", "1d4", "sub")])]
    scale(s, targets=1)
    result.append(s)
    s = base(raw["Command"])
    s["choices"] = [{"id": "command", "options": ["halt", "grovel"], "when": "on_cast"}]
    s["effects"] = [block(target=multi(1, "visible"), save="wis", effects=[
        {"turn_rules": {"no_action": True, "no_bonus_action": True}, "until": "end_of_turn(target.next_turn)"},
        {"turn_rules": {"on_turn_condition": "prone"}, "if": "$command == grovel", "until": "end_of_turn(target.next_turn)"}])]
    s["unsupported"].append("Approach/Flee movement, Halt movement prohibition and Drop equipment handling need a grid/inventory; only Halt/Grovel action denial is executable.")
    scale(s, targets=1)
    result.append(s)
    s = base(raw["Witch Bolt"])
    s["effects"] = [block(attack="ranged_spell", effects=[damage("2d12", "lightning")]),
                    block("sustain", {"select": "ref", "ref": "main"}, effects=[damage("1d12", "lightning")], event="bonus_action_command", **{"if": "turn.index > spell.cast_turn"})]
    scale(s, dice="1d12")
    s["effects"][0]["source_ref"] = "entries.0"
    s["effects"][1]["source_ref"] = "entries.1"
    s["unsupported"].append("End on separation or Total Cover requires range/cover adjudication.")
    result.append(s)
    s = base(raw["Ice Knife"])
    s["effects"] = [block("knife", attack="ranged_spell", effects=[damage("1d10", "piercing")]),
                    block("explosion", area("sphere", 5), save="dex", effects=[damage("2d6", "cold")])]
    s["effects"][1]["target"]["origin"] = "knife"
    scale(s, block="explosion", dice="1d6")
    s["unsupported"].append("Adjacent creatures are selected by the area heuristic around the knife target, not precise positions.")
    result.append(s)
    s = base(raw["Mage Armor"])
    s["effects"] = [block(target=single("willing"), effects=[{"base_ac": {"base": 13, "ability": "dex", "unarmored_only": True}}])]
    s["unsupported"].append("Armor inventory and donning are not modeled; caller must mark armored creatures through the armored feature.")
    result.append(s)
    s = base(raw["False Life"])
    s["effects"] = [block(target={"select": "self"}, effects=[{"temp_hp": {"dice": "2d4+4"}}])]
    s["scaling"] = {"upcast": {"per_slot_above": 1, "changes": [{"block": "main", "amount_add": 5}]}}
    result.append(s)
    # These mandatory monster references have no no-grid combat effect.
    for name, note in {
        "Light": "Lighting, object covering and recoloring need a lighting/object model.",
        "Mage Hand": "Object manipulation, carrying and movement need inventory/positions; the hand cannot attack.",
        "Prestidigitation": "Harmless sensory, cleaning, ignition and trinket effects are not combat primitives.",
        "Thaumaturgy": "Cosmetic effects and Charisma (Intimidation) advantage need a skill/social model.",
        "Detect Magic": "Magic detection, auras, schools and barriers need a sensory/environment model.",
        "Disguise Self": "Illusory appearance and Investigation discovery need social/vision adjudication.",
    }.items():
        s = base(raw[name])
        s["unsupported"].append(note)
        result.append(s)
    return result
