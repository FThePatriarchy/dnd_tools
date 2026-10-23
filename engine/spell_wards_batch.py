"""Long-preparation wards, curses and explicit external-state boundaries."""
from .spell_catalog import base, sources, block, single, area, damage, condition, modify, scale
from .spell_control_batch import TYPES
from .loader import ABILITIES, DAMAGE_TYPES


def spells():
    raw = sources(); out = []
    s = base(raw["Bestow Curse"]); s["choices"] = [{"id": "curse", "options": ["ability", "attacks", "dodge", "damage"], "when": "on_cast"}, {"id": "ability", "options": sorted(ABILITIES), "when": "on_cast"}]
    s["effects"] = [block(save="wis", effects=[{"status": {"id": "cursed", "data": {}}}, *[{"disadvantage": {"on": on, "scope": "$ability", "against": None}, "if": "$curse == ability"} for on in ("ability_checks", "saves")], {"disadvantage": {"on": "attack_rolls", "scope": "all", "against": "target"}, "if": "$curse == attacks"}, {"curse_dodge": {"ability": "wis"}, "if": "$curse == dodge"}, {"curse_damage": {"dice": "1d8", "type": "necrotic"}, "if": "$curse == damage"}])]
    s["duration_tiers"] = [{"slot_min": 4, "duration": {"type": "minutes", "n": 10}, "concentration": True}, {"slot_min": 5, "duration": {"type": "hours", "n": 8}, "concentration": False}, {"slot_min": 7, "duration": {"type": "hours", "n": 24}, "concentration": False}, {"slot_min": 9, "duration": {"type": "until_dispelled"}, "concentration": False}]; out.append(s)
    s = base(raw["Chromatic Orb"]); s["choices"] = [{"id": "type", "options": ["acid", "cold", "fire", "lightning", "poison", "thunder"], "when": "on_cast"}]
    s["effects"] = [block(attack="ranged_spell", effects=[damage("3d8", "$type", leap_on_duplicate=True)])]; scale(s, dice="1d8")
    s["unsupported"] = ["Thirty-foot leap eligibility uses the no-grid assumption; duplicate dice, slot-limited jumps, independent attacks and never retargeting the same creature execute."]; out.append(s)
    s = base(raw["Contagion"]); s["choices"] = [{"id": "ability", "options": sorted(ABILITIES), "when": "on_cast"}]
    s["effects"] = [block(save="con", effects=[damage("11d8", "necrotic"), condition("poisoned", resist_removal="con", tally_save={"ability": "con", "successes": 3, "failures": 3, "failure_hours": 168}), {"disadvantage": {"on": "saves", "scope": "$ability", "against": None}, "requires_condition": "poisoned"}])]; out.append(s)
    s = base(raw["Glyph of Warding"]); s["choices"] = [{"id": "type", "options": ["acid", "cold", "fire", "lightning", "thunder"], "when": "on_cast"}]
    s["effects"] = [block(target=area("sphere", 20), event="glyph_triggered", end_after_resolution=True, save="dex", half=True, effects=[damage("5d8", "$type")])]; scale(s, dice="1d8")
    s["unsupported"] = ["Explosive Rune waits for an external glyph_triggered event, never explodes during preparation. Placement, movement breakage, perception, passwords and Spell Glyph's prepared-spell storage require object/trigger/prepared-list state; no free spell slot or instant cast is invented."]; out.append(s)
    s = base(raw["Hallow"]); s["choices"] = [{"id": "effect", "options": ["courage", "fear", "resistance", "vulnerability", "silence"], "when": "on_cast"}, {"id": "type", "options": sorted(DAMAGE_TYPES), "when": "on_cast"}]
    t = area("sphere", 60)
    s["effects"] = [block(target=t, event="while_in_area", effects=[{"ward": {"types": ["aberration", *TYPES], "conditions": ["charmed", "frightened"], "suppress_existing": True}}, {"defense": {"condition_immunity": ["frightened"]}, "if": "$effect == courage"}, {**condition("frightened"), "if": "$effect == fear"}, {"defense": {"resistance": ["$type"]}, "if": "$effect == resistance"}, {"defense": {"vulnerability": ["$type"]}, "if": "$effect == vulnerability"}, {"status": {"id": "verbal_components_blocked", "data": {}}, "if": "$effect == silence"}])]
    s["unsupported"] = ["Default type selection is all eligible types; exact chosen groups, possession, overlapping areas, entry/teleport prohibition, darkness/daylight, interred corpses and languages need geometry/possession/sensory state. Frightened and source-typed suppression execute, without inventing a saving throw."]; out.append(s)
    s = base(raw["Magic Circle"]); s["effects"] = [block(target=area("cylinder", 10), event="while_in_area", effects=[{"ward": {"types": TYPES, "conditions": ["charmed", "frightened"], "attack_disadvantage": True}}])]
    s["duration_tiers"] = []
    s["scaling"] = {"upcast": {"per_slot_above": 3, "changes": [{"duration_hours_add": 1}]}}
    s["unsupported"] = ["Chosen default is all eligible types. Ground/cylinder height, entry prohibition, reversed-circle placement, teleportation/interplanar Charisma saves and possession require grid/planar state. Inside recipients receive source-typed protection."]; out.append(s)
    s = base(raw["Meld into Stone"]); s["unsupported"] = ["Stone volume, merging/exit, external perception, partial destruction (6d6 Force), complete destruction (50 Force), expulsion and Prone require a targetable terrain object/geometry. No such stone object exists in a no-grid arena; granting general invulnerability or removal would be false."]; out.append(s)
    s = base(raw["Planar Binding"]); t=single(); t["eligible_if"] = "target.creature_type in [celestial, elemental, fey, fiend]"
    s["effects"] = [block(target=t, save="cha", effects=[{"control": {}}])]
    s["unsupported"] = ["The uninterrupted hour-long casting must be supplied with prepare(). Hostile interpretation of natural-language orders and planar reporting need DM adjudication. Bound creatures attack the caster's enemies; this is service, not an invented Charmed condition. Extending another spell's duration does not waive its concentration."]; out.append(s)
    s = base(raw["Revivify"]); s["unsupported"] = ["Impossible in the current knockout-only arena: a 0-HP creature is unconscious, not Dead. No death timestamp, old-age cause or missing-body-parts state exists to validate the last-minute prerequisite. The spell loads but intentionally does not heal an unconscious creature as if it were dead."]; out.append(s)
    return out
