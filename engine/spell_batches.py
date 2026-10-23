"""Reviewed no-grid translations, batched by their actual XPHB level.

This is deliberately not a catch-all text-to-mechanics extractor. Missing
spells remain missing rather than being presented as working empty effects.
"""
from .spell_catalog import sources, base, block, single, multi, area, damage, modify, condition, scale


def translations(level):
    raw = sources()
    result = []
    simple = {
        "Shatter": ("3d8", "thunder", "con", area("sphere", 10), "1d8"),
        "Mind Spike": ("3d8", "psychic", "wis", single("visible"), "1d8"),
        "Conjure Barrage": ("5d8", "force", "dex", area("cone", 60, "chosen"), "1d8"),
        "Lightning Bolt": ("8d6", "lightning", "dex", area("line", 100), "1d6"),
        "Blight": ("8d8", "necrotic", "con", single("visible"), "1d8"),
        "Cone of Cold": ("8d8", "cold", "con", area("cone", 60), "1d8"),
        "Conjure Volley": ("8d8", "force", "dex", area("cylinder", 40, "chosen"), None),
    }
    for name, (die, dtype, save, t, increment) in simple.items():
        if raw[name]["level"] != level: continue
        s = base(raw[name])
        if name in {"Conjure Barrage", "Conjure Volley"}: t["filter"].append("visible")
        b = block(target=t, save=save, half=True, effects=[damage(die, dtype)])
        if name == "Shatter":
            b["save"]["disadvantage_if"] = "target.creature_type == construct"
            s["unsupported"].append("Nonmagical unworn/uncarried object damage needs an object model.")
        if name == "Blight":
            b["save"]["auto_fail_if"] = "target.creature_type == plant"
            s["unsupported"].append("Withering a noncreature plant needs an environment/object model.")
        if name == "Mind Spike": s["unsupported"].append("Location tracking, hiding and caster-specific Invisible suppression need a sensory model; only damage is executable.")
        if name == "Cone of Cold": s["unsupported"].append("Frozen corpse/statue and thawing are not simulated.")
        if name in {"Lightning Bolt", "Conjure Volley"}: s["unsupported"].append("Area cross-section/height and exact placement are abstracted by the area heuristic.")
        s["effects"] = [b]
        if increment: scale(s, dice=increment)
        result.append(s)
    if level == 2:
        s = base(raw["Barkskin"])
        s["effects"] = [block(target=single("willing"), effects=[{"base_ac": {"base": 17, "ability": None, "unarmored_only": False}}])]
        result.append(s)
        s = base(raw["Blindness/Deafness"])
        s["choices"] = [{"id": "condition", "options": ["blinded", "deafened"], "when": "on_cast"}]
        s["effects"] = [block(target=multi(1, "visible"), save="con", effects=[
            {**condition(c, repeat_save={"ability": "con", "timing": "end_of_turn", "on_success": "end"}), "if": "$condition == " + c} for c in ("blinded", "deafened")])]
        scale(s, targets=1)
        result.append(s)
        s = base(raw["Lesser Restoration"])
        s["choices"] = [{"id": "condition", "options": ["blinded", "deafened", "paralyzed", "poisoned"], "when": "on_cast"}]
        s["effects"] = [block(effects=[{"remove_condition": {"condition": "$condition"}}])]
        result.append(s)
        s = base(raw["Invisibility"])
        s["effects"] = [block(target=multi(1), effects=[condition("invisible", ends_on_activity=True)])]
        scale(s, targets=1)
        result.append(s)
        s = base(raw["Misty Step"])
        s["unsupported"].append("Teleportation and visible destination selection require positions/vision; no grid-free effect is invented.")
        result.append(s)
        s = base(raw["Flame Blade"])
        s["effects"] = [block(attack="melee_spell", event="action_command", effects=[damage("3d6", "fire", bonus="spell_mod")])]
        scale(s, dice="1d6")
        s["unsupported"].append("Lighting, free-hand inventory and dropping/re-evoking the blade are not simulated.")
        result.append(s)
        for name, t, die, dtype, save, half, increment in [
            ("Cloud of Daggers", area("cube", 5), "4d4", "slashing", None, False, "2d4"),
            ("Moonbeam", area("cylinder", 5), "2d10", "radiant", "con", True, "1d10"),
        ]:
            s = base(raw[name])
            s["effects"] = [block(target=t, save=save, half=half, effects=[damage(die, dtype)], event="on_cast or on_aura_moves_onto_creature(target) or on_creature_enters_aura(target) or end_of_turn_in_aura(target)", limit="once_per_turn_per_target")]
            scale(s, dice=increment)
            s["unsupported"].append("Area relocation, entry/movement triggers and precise area geometry need a grid; creation and end-turn effects execute.")
            if name == "Moonbeam": s["unsupported"].append("Dim Light, shape-shift reversion and shape-shift prevention need lighting/transformation state.")
            result.append(s)
    if level == 3:
        s = base(raw["Fly"])
        s["effects"] = [block(target=multi(1, "willing"), effects=[modify("fly_speed", 60, "set")])]
        scale(s, targets=1)
        s["unsupported"].append("Flight speed is stored; hovering, altitude, movement and falling require positions.")
        result.append(s)
        s = base(raw["Dispel Magic"])
        s["effects"] = [block(effects=[{"dispel": {"auto_level": 3, "dc_base": 10}}])]
        s["unsupported"].append("Object and independently targeted magical-effect selection needs an object model; ongoing spells on creatures can be dispelled.")
        result.append(s)
        s = base(raw["Slow"])
        t = multi(6)
        s["effects"] = [block(target=t, save="wis", effects=[modify("speed", .5, "mul"), modify("ac", -2), modify("save", -2, scope="dex"),
            {"turn_rules": {"no_reactions": True, "action_or_bonus": True, "attack_limit": 1, "somatic_failure_percent": 25, "repeat_save": {"ability": "wis", "timing": "end_of_turn", "on_success": "end"}}}])]
        s["unsupported"].append("Selection inside the source's Cube and speed/movement need a grid; six-target cap, saves and action restrictions execute.")
        result.append(s)
        s = base(raw["Aura of Vitality"])
        s["effects"] = [block(target={**single(), "origin": "caster", "within_ft": 30}, effects=[{"heal": {"dice": "2d6", "bonus": 0}}], event="on_cast or start_of_turn(caster)")]
        s["unsupported"].append("Emanation membership is assumed under the no-grid range convention.")
        result.append(s)
        s = base(raw["Conjure Animals"])
        s["effects"] = [block(target=area("sphere", 10, "chosen"), save="dex", effects=[damage("3d10", "slashing")], event="on_aura_moves_onto_creature(target) or on_creature_enters_aura(target) or end_of_turn_in_aura(target)", limit="once_per_turn_per_target")]
        s["effects"][0]["target"]["filter"].append("visible")
        scale(s, dice="1d10")
        s["unsupported"].append("Intangible pack placement/movement and conditional Strength-save advantage near the pack need a grid; end-turn damage executes. This is not a creature summon in XPHB.")
        result.append(s)
    if level in {3, 5}:
        name = "Mass Healing Word" if level == 3 else "Mass Cure Wounds"
        s = base(raw[name])
        s["effects"] = [block(target=multi(6, *(["visible"] if level == 3 else [])), effects=[{"heal": {"dice": "2d4" if level == 3 else "5d8", "bonus": "spell_mod"}}])]
        scale(s, dice="1d4" if level == 3 else "1d8")
        if level == 5: s["unsupported"].append("Selection inside a sphere centered on a visible point is assumed; precise placement needs a grid.")
        result.append(s)
    if level == 4:
        s = base(raw["Ice Storm"])
        s["effects"] = [block(target=area("cylinder", 20), save="dex", half=True, effects=[damage("2d10", "bludgeoning"), damage("4d6", "cold")])]
        s["scaling"] = {"upcast": {"per_slot_above": 4, "changes": [{"block": "main", "dice_add": "1d10", "damage_type": "bludgeoning"}]}}
        s["unsupported"].append("Cylinder height and difficult terrain until the next turn need a grid. Source upcast tag says 2d8, but base text explicitly says 2d10; retain base text and the explicit 1d10 increment.")
        result.append(s)
        s = base(raw["Greater Invisibility"])
        s["effects"] = [block(effects=[condition("invisible")])]
        result.append(s)
        s = base(raw["Stoneskin"])
        s["effects"] = [block(target=single("willing"), effects=[{"defense": {"resistance": ["bludgeoning", "piercing", "slashing"]}}])]
        result.append(s)
        s = base(raw["Conjure Woodland Beings"])
        t = area("emanation", 10, "chosen")
        t["filter"].append("visible")
        s["effects"] = [block(target=t, save="wis", half=True, effects=[damage("5d8", "force")],
            event="on_aura_moves_onto_creature(target) or on_creature_enters_aura(target) or end_of_turn_in_aura(target)", limit="once_per_turn_per_target")]
        scale(s, dice="1d8")
        s["unsupported"] = ["Moving emanation entry and bonus-action Disengage require movement; end-turn damage executes. XPHB creates intangible spirits, not allied creature stat blocks."]
        result.append(s)
        s = base(raw["Phantasmal Killer"])
        penalties = [{kind: {"on": on, "scope": "all", "against": None}}
            for kind, on in [("disadvantage", "attack_rolls"), ("disadvantage", "ability_checks")]]
        initial = block(target=single("visible"), save="wis", half=True, effects=[damage("4d10", "psychic"), *penalties])
        initial["on_success"] = [{"end_spell": True}]
        recurring = block("nightmare", target={"select": "ref", "ref": "main"}, save="wis", effects=[damage("4d10", "psychic")], event="end_of_turn(target)")
        recurring["on_success"] = [{"end_spell": True}]
        s["effects"] = [initial, recurring]
        scale(s, dice="1d10")
        s["scaling"]["upcast"]["changes"].append({"block": "nightmare", "dice_add": "1d10"})
        result.append(s)
        s = base(raw["Mordenkainen's Faithful Hound"])
        t = single()
        t.update(affects="enemy", within_ft=5)
        s["effects"] = [block(target=t, save="dex", effects=[damage("4d8", "force")], event="start_of_turn(caster)")]
        s["unsupported"] = ["Phantom placement, relocation with the Magic action, barking/password, Small-or-larger detection, Truesight and the distance tether require positions/senses. Bite eligibility assumes an enemy within the declared reach. The invulnerable intangible hound is not a creature summon."]
        result.append(s)
    if level == 5:
        s = base(raw["Hold Monster"])
        s["effects"] = [block(target=multi(1, "visible"), save="wis", effects=[condition("paralyzed", repeat_save={"ability": "wis", "timing": "end_of_turn", "on_success": "end"})])]
        scale(s, targets=1)
        result.append(s)
        s = base(raw["Destructive Wave"])
        s["choices"] = [{"id": "damage_type", "options": ["radiant", "necrotic"], "when": "on_cast"}]
        s["effects"] = [block(target=area("emanation", 30, "chosen"), save="con", half=True, effects=[damage("5d6", "thunder"), damage("5d6", "$damage_type"), condition("prone")])]
        # Knockdown persists until standing, not until an instantaneous spell ends.
        s["effects"][0]["on_fail"][-1]["apply_condition"]["persistent"] = True
        result.append(s)
        s = base(raw["Flame Strike"])
        s["effects"] = [block(target=area("cylinder", 10), save="dex", half=True, effects=[damage("5d6", "fire"), damage("5d6", "radiant")])]
        scale(s, dice="1d6")
        s["unsupported"].append("Cylinder height/placement are abstracted by the area heuristic.")
        result.append(s)
        s = base(raw["Steel Wind Strike"])
        s["effects"] = [block(target=multi(5, "visible"), attack="melee_spell", effects=[damage("6d10", "force")])]
        s["unsupported"].append("Teleporting beside a struck target needs positions and destination visibility.")
        result.append(s)
        for name, die, dtype in [("Cloudkill", "5d8", "poison"), ("Insect Plague", "4d10", "piercing")]:
            s = base(raw[name])
            s["effects"] = [block(target=area("sphere", 20), save="con", half=True, effects=[damage(die, dtype)],
                event="on_cast or on_aura_moves_onto_creature(target) or on_creature_enters_aura(target) or end_of_turn_in_aura(target)", limit="once_per_turn_per_target")]
            scale(s, dice="1d8" if name == "Cloudkill" else "1d10")
            s["unsupported"] = ["Obscurement, difficult terrain, wind dispersal, fog movement and exact entry/area geometry require positions/environment; creation and end-turn damage execute."]
            result.append(s)
        s = base(raw["Yolande's Regal Presence"])
        t = area("emanation", 10, "chosen")
        t["filter"].append("visible")
        s["effects"] = [block(target=t, save="wis", half=True, effects=[damage("4d6", "psychic"), condition("prone", persistent=True)],
            event="on_aura_moves_onto_creature(target) or on_creature_enters_aura(target) or end_of_turn_in_aura(target)", limit="once_per_turn_per_target")]
        s["unsupported"] = ["Moving emanation entry and the optional push require positions; end-turn saves, damage and persistent Prone execute."]
        result.append(s)
        s = base(raw["Jallarzi's Storm of Radiance"])
        t = area("cylinder", 10)
        s["effects"] = [block("storm", target=t, event="while_in_area", effects=[condition("blinded"), condition("deafened"),
            {"status": {"id": "verbal_components_blocked", "data": {}}}]),
            block("damage", target=t.copy(), save="con", half=True, effects=[damage("2d10", "radiant"), damage("2d10", "thunder")],
                event="on_cast or on_creature_enters_aura(target) or end_of_turn_in_aura(target)", limit="once_per_turn_per_target")]
        scale(s, block="damage", dice="1d10")
        s["unsupported"] = ["Cylinder height, chosen-point visibility, positioning and entry events require a grid; area membership uses the existing heuristic. Blindness, deafness and the Verbal-component prohibition apply while in the area without a save."]
        result.append(s)
    return result
