"""Explicit remaining XPHB recipes, reviewed in small executable batches."""
from .spell_catalog import base, block, single, multi, area, damage, condition, modify, scale, sources


SPATIAL = {
    "Dancing Lights": "Light-source placement, illumination, movement and inter-light distances require positions and lighting.",
    "Minor Illusion": "Sound/image placement, physical interaction and observer-specific Intelligence (Investigation) Study checks need sensory/object adjudication.",
    "Expeditious Retreat": "Immediate Dash and subsequent bonus-action Dash change movement only; there is no movement budget in this arena.",
    "Feather Fall": "Falling eligibility, altitude, descent, landing and fall-damage prevention require falling/position state; on_falling is an explicit external reaction event.",
    "Jump": "Once-per-turn jumping and its movement expenditure require positions; no attack or unrestricted action bonus is invented.",
    "Fog Cloud": "Heavy obscurement, wind dispersal and the slot-scaled fog radius require lighting/positions; this is not blanket Blinded.",
    "Silent Image": "Image placement/movement, physical interaction and observer-specific Intelligence (Investigation) Study checks require sensory/object adjudication.",
    "Continual Flame": "Permanent heatless object illumination and opaque coverings require an object/lighting model.",
    "Darkvision": "Sense-specific visibility and Darkvision distance require lighting; Darkvision is not immunity to Invisible or Blinded.",
    "Gust of Wind": "Strength saves resolve directional pushing only. Wind direction, movement costs, gas dispersal and flame extinguishing require a grid/environment.",
    "Rope Trick": "Climbing the rope, portal entry/exit, extradimensional capacity, crossing and barrier targeting require positions/objects; no automatic removal is invented.",
    "Spider Climb": "Surface traversal, hands-free climbing and Climb Speed equal to Speed require movement; higher slots add willing targets.",
    "Spike Growth": "Piercing damage is per distance actually traveled through camouflaged difficult terrain, not on creation or each turn. Movement and recognition require a grid.",
    "Daylight": "Sunlight illumination, overlapping Darkness dispelling and sunlight-sensitive creature membership require lighting/positions.",
    "Major Image": "Multisensory illusion placement, movement, interaction and observer-specific Intelligence (Investigation) Study checks require sensory/environment adjudication.",
    "Plant Growth": "Existing vegetation and changed movement costs require terrain. The alternative long casting enriches crops rather than inflicting combat damage.",
    "Water Walk": "Liquid-surface traversal, submerged ascent and hot-surface consequences require terrain/altitude/movement.",
    "Control Water": "Water availability, flooding, redirected flow, parting, whirlpool entry, Strength saves and Bludgeoning damage from water movement require fluid terrain/positions; damage is not front-loaded.",
    "Antilife Shell": "The barrier prevents eligible living creatures crossing/reaching through its moving boundary; forced contact and spell/ranged reach require positions. It is not damage immunity or unconditional incapacitation.",
    "Leomund's Tiny Hut": "Fixed dome occupants, one-way visibility, physical/spell crossing and dismissal on leaving require geometry; there is no blanket damage immunity.",
}


def spatial():
    result = []
    raw = sources()
    for name, omission in SPATIAL.items():
        s = base(raw[name])
        s["unsupported"] = [omission]
        if name == "Minor Illusion": s["recast_ends_previous"] = True
        if name == "Feather Fall": s["reaction_trigger"] = "on_falling(target)"
        result.append(s)
    return result


def buffs():
    raw = sources()
    out = []
    for name, primitive, target in [
        ("Longstrider", modify("speed", 10), multi(1)),
        ("Blur", {"disadvantage": {"on": "attack_rolls", "scope": "all", "against": "target", "recipient": "any_attacker"}}, {"select": "self"}),
        ("See Invisibility", {"status": {"id": "see_invisible", "data": {}}}, {"select": "self"}),
        ("Remove Curse", {"restore": {"kind": "curse", "all": True}}, single()),
    ]:
        s = base(raw[name]); s["effects"] = [block(target=target, effects=[primitive])]
        if name == "Longstrider":
            scale(s, targets=1); s["unsupported"] = ["Speed is stored; movement is not simulated."]
        if name == "Blur": s["unsupported"] = ["Blindsight and Truesight exceptions require sense-specific visibility adjudication."]
        if name == "See Invisibility": s["unsupported"] = ["Ethereal-plane sensing and objects require a sensory/object model; seeing Invisible combatants is executable."]
        if name == "Remove Curse": s["unsupported"] = ["Cursed-item attunement requires an item/inventory model; creature spell curses can end."]
        out.append(s)
    s = base(raw["Guidance"])
    s["choices"] = [{"id": "skill", "when": "on_cast", "options": "acrobatics animal_handling arcana athletics deception history insight intimidation investigation medicine nature perception performance persuasion religion sleight_of_hand stealth survival".split()}]
    s["effects"] = [block(target=single("willing"), effects=[modify("ability_check", "1d4", scope="$skill")])]
    out.append(s)
    s = base(raw["Enhance Ability"])
    s["choices"] = [{"id": "ability", "when": "on_cast", "options": ["str", "dex", "int", "wis", "cha"], "per_target": True}]
    s["effects"] = [block(target=multi(1), effects=[{"advantage": {"on": "ability_checks", "scope": "$ability", "against": None}}])]
    scale(s, targets=1); out.append(s)
    s = base(raw["Protection from Energy"])
    s["choices"] = [{"id": "damage_type", "when": "on_cast", "options": ["acid", "cold", "fire", "lightning", "thunder"]}]
    s["effects"] = [block(target=single("willing"), effects=[{"defense": {"resistance": ["$damage_type"]}}])]
    out.append(s)
    s = base(raw["Protection from Poison"])
    s["effects"] = [block(effects=[{"remove_condition": {"condition": "poisoned"}}, {"defense": {"resistance": ["poison"], "save_conditions": ["poisoned"]}}])]
    out.append(s)
    s = base(raw["Faerie Fire"])
    s["effects"] = [block(target={**area("cube", 20), "filter": ["creature_or_object"]}, save="dex", effects=[
        {"status": {"id": "invisibility_suppressed", "data": {}}},
        {"advantage": {"on": "attack_rolls", "scope": "all", "against": "target", "recipient": "any_attacker", "require_visible": True}}])]
    s["unsupported"] = ["Outlined object lighting and precise Cube placement require lighting/positions."]
    out.append(s)
    for name, size, save, cond, event in [
        ("Grease", 10, "dex", "prone", "on_cast or on_creature_enters_aura(target) or end_of_turn_in_aura(target)"),
        ("Entangle", 20, "str", "restrained", "on_cast"),
        ("Web", 20, "dex", "restrained", "on_creature_enters_aura(target) or start_of_turn(target)"),
    ]:
        s = base(raw[name]); t = area("cube", size)
        if name == "Entangle": t["exclude"] = "caster"
        c = condition(cond, persistent=True) if name == "Grease" else condition(cond, escape_dc="spell_dc")
        s["effects"] = [block(target=t, save=save, effects=[c], event=event)]
        s["unsupported"] = ["Difficult terrain, ground/surface eligibility, anchoring, precise membership and movement entry require a grid/environment. Escape uses an action and Strength (Athletics)."]
        if name == "Web": s["unsupported"].append("Burning Webs' Fire damage and local web removal require external fire/object geometry; no automatic burning damage is invented.")
        out.append(s)
    s = base(raw["Heroism"])
    s["effects"] = [block(target=multi(1, "willing"), effects=[{"defense": {"condition_immunity": ["frightened"]}}]),
        block("bravery", target={"select": "ref", "ref": "main"}, event="start_of_turn(target)", effects=[{"temp_hp": {"amount": "spell_mod"}}])]
    s["scaling"] = {"upcast": {"per_slot_above": 1, "changes": [{"block": "main", "target_n_add": 1}]}}
    out.append(s)
    for name, dtype, extra in [("Aura of Purity", "poison", {"defense": {"save_conditions": ["blinded", "charmed", "deafened", "frightened", "paralyzed", "poisoned", "stunned"]}}),
                               ("Aura of Life", "necrotic", {"status": {"id": "max_hp_protected", "data": {}}})]:
        s = base(raw[name]); t = {**area("emanation", 30, "ally"), "origin": "caster", "include_caster": True}
        s["effects"] = [block(target=t, event="while_in_area", effects=[{"defense": {"resistance": [dtype]}}, extra])]
        if name == "Aura of Life": s["effects"].append(block("revive", target={**t, "eligible_if": "target.hp == 0"}, event="start_of_turn(target)", effects=[{"heal": {"amount": 1}}]))
        s["unsupported"] = ["Emanation membership uses the no-grid heuristic; movement is not simulated."]
        out.append(s)
    s = base(raw["Beacon of Hope"])
    s["effects"] = [block(target={**multi(1), "n": "all"}, effects=[{"advantage": {"on": "saves", "scope": "wis", "against": None}}, {"status": {"id": "maximize_healing", "data": {}}}])]
    s["unsupported"] = ["Death saving throw Advantage requires a death-save clock, absent from this knockout-based arena; healing maximization and Wisdom save Advantage execute."]
    out.append(s)
    s = base(raw["Feign Death"])
    all_types = "acid bludgeoning cold fire force lightning necrotic piercing poison radiant slashing thunder".split()
    s["effects"] = [block(target=single("willing"), effects=[condition("blinded"), condition("incapacitated"), modify("speed", 0, "set"), {"defense": {"resistance": all_types, "condition_immunity": ["poisoned"]}}])]
    s["unsupported"] = ["Apparent death and diagnostic spell deception require sensory/social adjudication."]
    out.append(s)
    s = base(raw["Gaseous Form"])
    s["effects"] = [block(target=multi(1, "willing"), effects=[modify("speed", 0, "set"), modify("fly_speed", 10, "set"), {"defense": {"resistance": ["bludgeoning", "piercing", "slashing"], "condition_immunity": ["prone"]}},
        *[{"advantage": {"on": "saves", "scope": a, "against": None}} for a in ("str", "dex", "con")], {"turn_rules": {"no_attacks": True, "no_spells": True, "dismiss_action": True, "end_at_zero": True}}])]
    scale(s, targets=1)
    s["unsupported"] = ["Cloud traversal, hovering, liquids and equipment manipulation require movement/inventory; the recipient may request target-local dismissal with a Magic action."]
    out.append(s)
    s = base(raw["Freedom of Movement"])
    s["effects"] = [block(target=multi(1, "willing"), effects=[{"defense": {"magical_condition_immunity": ["paralyzed", "restrained"]}}, {"status": {"id": "magical_speed_protected", "data": {}}}])]
    scale(s, targets=1)
    s["unsupported"] = ["Difficult terrain, Swim Speed equal to Speed and spending movement to leave nonmagical restraints require movement/terrain state."]
    out.append(s)
    s = base(raw["Greater Restoration"])
    s["choices"] = [{"id": "kind", "when": "on_cast", "options": ["exhaustion", "charmed", "petrified", "curse", "max_hp", "str", "dex", "con", "int", "wis", "cha"]}]
    s["effects"] = [block(effects=[{"restore": {"kind": "$kind"}}])]
    s["unsupported"] = ["Cursed-item attunement needs an item model; one creature condition/curse, Exhaustion level, ability reduction or HP-maximum reduction can be restored."]
    out.append(s)
    s = base(raw["Spare the Dying"])
    s["effects"] = [block(target={**single(), "eligible_if": "target.hp == 0"}, effects=[{"stabilize": True}])]
    s["scaling"] = {"cantrip": {"at": [5, 11, 17], "effect": {"range_multiplier": 2}}}
    s["unsupported"] = ["Stable state is recorded and cleared by damage/healing; this arena does not roll death saving throws or track elapsed dying time."]
    out.append(s)
    return out
