"""Source-reviewed survival, reaction and persistent hazard translations."""
from .spell_catalog import base, sources, block, single, multi, area, damage, condition, modify, scale
from .loader import DAMAGE_TYPES


def spells():
    raw = sources(); out = []
    s = base(raw["Aid"]); s["effects"] = [block(target=multi(3), effects=[{"max_hp": {"amount": 5}}])]
    s["scaling"] = {"upcast": {"per_slot_above": 2, "changes": [{"block": "main", "value_add": 5}]}}; out.append(s)
    s = base(raw["Arcane Vigor"]); s["effects"] = [block(target={"select": "self"}, effects=[{"hit_dice_heal": {"max_dice": 2}}])]
    s["scaling"] = {"upcast": {"per_slot_above": 2, "changes": [{"block": "main", "value_add": 1}]}}; out.append(s)
    s = base(raw["Armor of Agathys"])
    s["effects"] = [block(target={"select": "self"}, effects=[{"temp_hp": {"amount": 5}}]), block("frost", target={"select": "ref", "ref": "trigger.attacker"}, event="on_attack_hit(any, caster)", effects=[{"damage": {"amount": 5, "type": "cold"}}], **{"if": "attack.melee"})]
    s["scaling"] = {"upcast": {"per_slot_above": 1, "changes": [{"block": b, "value_add": 5} for b in ("main", "frost")]}}
    s["effects"][0]["apply"].append({"status": {"id": "agathys", "data": {}}})
    out.append(s)
    s = base(raw["Death Ward"]); s["effects"] = [block(effects=[{"death_ward": {"floor": 1}}])]
    s["unsupported"] = ["Nondamaging instant death requires an explicit death event; the arena uses knockout rather than death saves. Zero-HP damage prevention executes."]; out.append(s)
    s = base(raw["Goodberry"]); s["effects"] = [block(target={"select": "self"}, effects=[{"berries": {"count": 10, "healing": 1}}])]
    s["unsupported"] = ["Inventory transfer and nourishment are outside the arena; eat_berry consumes the shared stock using a living creature's Bonus Action."]; out.append(s)
    s = base(raw["Resistance"]); s["choices"] = [{"id": "type", "options": sorted(DAMAGE_TYPES - {"force", "psychic"}), "when": "on_cast"}]
    s["effects"] = [block(target=single("willing"), effects=[{"reduce_damage": {"dice": "1d4", "type": "$type"}}])]; out.append(s)
    s = base(raw["Circle of Power"]); s["effects"] = [block(target={**area("emanation", 30, "ally"), "include_caster": True}, event="while_in_area", effects=[{"magic_saves": {}}])]
    s["unsupported"] = ["Exact emanation membership requires positions; magical saving-throw Advantage and successful half-damage-save negation execute."]; out.append(s)
    s = base(raw["Warding Bond"]); t = single("willing"); t["eligible_if"] = "target != caster"
    s["effects"] = [block(target=t, effects=[modify("ac", 1), modify("save", 1), {"defense": {"resistance": sorted(DAMAGE_TYPES)}}, {"bond": {}, "participants": ["caster", "target"]}])]
    
    s["unsupported"] = ["Separation beyond 60 feet and ring inventory require positions/equipment. Same post-mitigation damage is copied directly to the caster without another resistance reduction."]; out.append(s)
    s = base(raw["Fire Shield"]); s["choices"] = [{"id": "shield", "options": ["warm", "chill"], "when": "on_cast"}]
    s["effects"] = [block(target={"select": "self"}, effects=[{"defense": {"resistance": ["cold"]}, "if": "$shield == warm"}, {"defense": {"resistance": ["fire"]}, "if": "$shield == chill"}]), block("retaliate", target={"select": "ref", "ref": "trigger.attacker"}, event="on_attack_hit(any, caster)", effects=[{**damage("2d8", "fire"), "if": "$shield == warm"}, {**damage("2d8", "cold"), "if": "$shield == chill"}], **{"if": "attack.melee"})]
    s["unsupported"] = ["Lighting and 5-foot attacker proximity use the melee no-grid convention; retaliation dice are not doubled by the attacker's critical hit."]; out.append(s)
    s = base(raw["Hellish Rebuke"]); s["reaction_trigger"] = "on_damaged(caster)"
    s["effects"] = [block(target={"select":"ref","ref":"trigger.attacker"}, save="dex", half=True, effects=[damage("2d10", "fire")])]; scale(s, dice="1d10"); out.append(s)
    s = base(raw["Hypnotic Pattern"]); s["effects"] = [block(target=area("cube", 30), save="wis", effects=[condition("charmed", ends_on_damage="any"), {**condition("incapacitated"), "requires_condition": "charmed"}, {**modify("speed", 0, "set"), "requires_condition": "charmed"}])]
    s["unsupported"] = ["Seeing the pattern, cube placement and another creature's shake-awake action require external sensory/rescue choices; damage ends all target-local effects."]; out.append(s)
    s = base(raw["Levitate"]); s["unsupported"] = ["Vertical movement, suspension, climbing against surfaces, 500-pound loose objects, altitude commands and range require a grid/object state. The Constitution saving throw has no nonspatial condition: levitation is not Restrained or Incapacitated."]; out.append(s)
    s = base(raw["Heat Metal"]); t = single("visible"); t["eligible_if"] = "target.has_status(heated_metal)"
    until = "start_of_turn(caster.next_turn)"
    s["effects"] = [block(target=t, event="on_cast or bonus_action_command", effects=[damage("2d8", "fire"), *[{"disadvantage": {"on": on, "scope": "all", "against": None}, "until": until} for on in ("attack_rolls", "ability_checks")]])]; scale(s, dice="1d8")
    s["unsupported"] = ["The caller must mark an eligible worn metal item as heated_metal; armor cannot be dropped. Constitution saving throws, held-object dropping, object contact/visibility/range and donning inventory require equipment state; no invented drop failure is imposed on a wearer."]; out.append(s)
    s = base(raw["Melf's Acid Arrow"]); s["effects"] = [block(attack="ranged_spell", effects=[damage("4d4", "acid"), damage("2d4", "acid", delay="end_of_turn(target.next_turn)")])]; scale(s, dice="1d4")
    s["effects"][0]["on_miss"] = [damage("4d4", "acid", half=True)]
    s["scaling"]["upcast"]["changes"].append({"block": "main", "miss_dice_add": "1d4"}); out.append(s)
    s = base(raw["Evard's Black Tentacles"]); s["effects"] = [block(target=area("cube", 20), save="str", event="on_cast or on_creature_enters_aura(target) or end_of_turn_in_aura(target)", limit="once_per_turn_per_target", effects=[damage("3d6", "bludgeoning"), condition("restrained", escape_dc="spell_dc")])]
    s["unsupported"] = ["Ground placement, entry and Difficult Terrain require positions. Strength (Athletics) escape uses escape(); no Acrobatics alternative."]; out.append(s)
    s = base(raw["Grasping Vine"]); s["effects"] = [block(target=single(), attack="melee_spell", event="on_cast or bonus_action_command", effects=[damage("4d8", "bludgeoning"), condition("grappled", max_size="H", escape_dc="spell_dc", capacity=1)])]
    s["scaling"] = {"upcast": {"per_slot_above": 4, "changes": [{"block": "main", "capacity_add": 1}]}}
    s["unsupported"] = ["Vine placement, 30-foot reach/pull and release placement require positions; Huge-or-smaller grapple and capacity execute."]; out.append(s)
    s = base(raw["Conjure Elemental"]); s["choices"] = [{"id": "type", "options": ["lightning", "thunder", "fire", "cold"], "when": "on_cast"}]
    t = area("sphere", 5, "chosen")
    s["effects"] = [block("catch", target={**t, "eligible_if": "not target.has_condition_from(restrained, spell)"}, event="start_of_turn(target) or on_creature_enters_aura(target)", save="dex", effects=[damage("8d8", "$type"), condition("restrained")], admission={"condition": "restrained", "capacity": 1, "large_cost": 1}), block("hold", target={**t, "eligible_if": "target.has_condition_from(restrained, spell)"}, event="start_of_turn(target)", save="dex", effects=[damage("4d8", "$type")])]
    s["effects"][1]["on_success"] = [{"remove_condition": {"condition": "restrained"}}]
    s["unsupported"] = ["Intangible Large spirit is an area force, not a creature; placement, entering its exact space and choosing not to force a save require positions/choices. Only one creature is restrained at a time."]; out.append(s)
    s = base(raw["Cordon of Arrows"]); s["effects"] = [block(target={**area("sphere", 30, "enemy"), "exclude": "caster"}, event="on_creature_enters_aura(target) or end_of_turn_in_aura(target)", save="dex", effects=[damage("2d4", "piercing")], limit="once_per_turn_per_target", max_uses=4)]
    s["scaling"] = {"upcast": {"per_slot_above": 2, "changes": [{"block": "main", "uses_add": 2}]}}
    s["unsupported"] = ["Ammunition inventory, planting and movement entry require positions; four projectiles plus upcast ammunition are consumed even on a successful save. Default exempt group is the caster's allies."]; out.append(s)
    s = base(raw["Blink"]); s["effects"] = [block(target={"select": "self"}, effects=[{"blink": {"dice": "1d6", "threshold": 4}}])]
    s["unsupported"] = ["Ethereal sensory range, existing Ethereal creatures and return-space placement require planar/position state; start/end-turn cross-plane isolation executes."]; out.append(s)
    s = base(raw["Mirror Image"]); s["effects"] = [block(target={"select": "self"}, effects=[{"mirror_images": {"count": 3, "dice": "1d6", "threshold": 3}}])]; out.append(s)
    for s in out:
        if s["name"] == "Conjure Elemental":
            for b in s["effects"]:
                predicate = b["target"].pop("eligible_if")
                if b["id"] == "hold": b["requires_condition"] = "restrained"
                else: b["if"] = predicate
                b["limit"] = "once_per_turn_per_target"; b["limit_group"] = "elemental_save"
    return out
