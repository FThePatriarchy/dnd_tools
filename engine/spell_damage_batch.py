"""Reviewed recurring-damage, attack-rider and area-control recipes."""
from copy import deepcopy
from .spell_catalog import base, block, single, multi, area, damage, condition, modify, scale, sources


def spells():
    raw = sources(); out = []
    for name, die, dtype, save, target, event, inc in [
        ("Call Lightning", "3d10", "lightning", "dex", area("sphere", 5), "on_cast or action_command", "1d10"),
        ("Flaming Sphere", "2d6", "fire", "dex", area("sphere", 5), "end_of_turn_in_aura(target)", "1d6"),
        ("Wind Wall", "4d8", "bludgeoning", "str", area("line", 50), "on_cast", None),
        ("Vampiric Touch", "3d6", "necrotic", None, single(), "on_cast or action_command", "1d6"),
        ("Wall of Fire", "5d8", "fire", "dex", area("line", 60), "on_cast", "1d8"),
    ]:
        s = base(raw[name]); p = damage(die, dtype)
        if name == "Vampiric Touch": p["damage"]["leech"] = .5
        s["effects"] = [block(target=target, save=save, half=bool(save), attack="melee_spell" if name == "Vampiric Touch" else None, effects=[p], event=event)]
        if name == "Call Lightning": s["effects"][0]["source_ref"] = "entries.1"
        if inc: scale(s, dice=inc)
        if name == "Wall of Fire":
            # Entry is externally geometric; end-turn heat is unconditional damage.
            s["effects"].append(block("heat", target=deepcopy(target), event="end_of_turn_in_aura(target)", effects=[damage(die, dtype)]))
            s["scaling"]["upcast"]["changes"].append({"block": "heat", "dice_add": inc})
        s["unsupported"] = ["Exact placement, surfaces, height, entry/movement, line-of-sight, lighting and environmental eligibility require a grid. Recurring commands/end-turn damage execute where declared."]
        if name == "Call Lightning": s["unsupported"].append("The outdoor-storm conditional extra 1d10 Lightning damage requires an externally supplied weather state; normal-cloud bolts execute.")
        if name == "Flaming Sphere": s["unsupported"].append("Bonus-action rolling/ramming, barriers, pits and unworn object ignition require movement and object state; no automatic creation damage is invented.")
        if name == "Wind Wall": s["unsupported"].append("Projectile interception, flying-creature crossing, gas dispersal and Gaseous Form passage require relative positions/projectile kinds.")
        out.append(s)
    s = base(raw["Dragon's Breath"])
    s["choices"] = [{"id": "damage_type", "options": ["acid", "cold", "fire", "lightning", "poison"], "when": "on_cast"}]
    s["effects"] = [block(target=single("willing"), effects=[{"grant_command": {"block": "breath", "action": "action"}}]),
        block("breath", target={**area("cone", 15), "origin": "main"}, save="dex", half=True, effects=[damage("3d6", "$damage_type")], event="action_command")]
    scale(s, block="breath", dice="1d6")
    s["unsupported"] = ["Cone direction and placement require positions. The touched recipient, not only the caster, can spend its Magic action to command the granted breath."]
    out.append(s)
    s = base(raw["Hunger of Hadar"])
    s["choices"] = [{"id": "upgrade", "options": ["cold", "acid"], "when": "on_cast"}]
    t = area("sphere", 20)
    s["effects"] = [block("dark", target=t, event="while_in_area", effects=[condition("blinded")]),
        block("cold", target=deepcopy(t), event="start_of_turn(target)", effects=[damage("2d6", "cold")]),
        block("acid", target=deepcopy(t), event="end_of_turn_in_aura(target)", save="dex", effects=[damage("2d6", "acid")])]
    s["scaling"] = {"upcast": {"per_slot_above": 3, "changes": [{"block": k, "dice_add": "1d6", "if": "$upgrade == " + k} for k in ("cold", "acid")]}}
    s["unsupported"] = ["Absolute Darkness, sounds, difficult terrain and fully-within membership require sensory/position adjudication; Blindness and correctly timed Cold/Acid damage execute."]
    out.append(s)
    s = base(raw["Sleet Storm"])
    s["effects"] = [block(target=area("cylinder", 20), event="on_creature_enters_aura(target) or start_of_turn(target)", save="dex", effects=[condition("prone", persistent=True), {"end_concentration": True}])]
    s["unsupported"] = ["Heavy obscurement, difficult terrain, exposed flame extinguishing and entry geometry require positions/environment."]
    out.append(s)
    s = base(raw["Stinking Cloud"])
    until = "end_of_turn(target.this_turn)"
    s["effects"] = [block(target=area("sphere", 20), event="start_of_turn(target)", save="con", effects=[{**condition("poisoned"), "until": until},
        {"turn_rules": {"no_action": True, "no_bonus_action": True}, "until": until, "requires_condition": "poisoned"}])]
    s["unsupported"] = ["Heavy obscurement, strong-wind dispersal and membership need sensory/position adjudication."]
    out.append(s)
    s = base(raw["Vitriolic Sphere"])
    s["effects"] = [block(target=area("sphere", 20), save="dex", half=True, effects=[damage("10d4", "acid"), damage("5d4", "acid", delay="end_of_turn(target.next_turn)")])]
    s["scaling"] = {"upcast": {"per_slot_above": 4, "changes": [{"block": "main", "dice_add": "2d4", "timing": "immediate"}]}}
    out.append(s)
    s = base(raw["Synaptic Static"])
    duration = {"type": "minutes", "n": 1}
    s["effects"] = [block(target=area("sphere", 20), save="int", half=True, effects=[damage("8d6", "psychic"),
        *[{**modify(stat, "1d6", "sub"), "duration": duration.copy()} for stat in ("attack_roll", "ability_check", "concentration_save")],
        {"turn_rules": {"repeat_save": {"ability": "int", "timing": "end_of_turn", "on_success": "end"}}, "duration": duration.copy()}])]
    out.append(s)
    s = base(raw["Ray of Enfeeblement"])
    s["effects"] = [block(save="con", effects=[*[{"disadvantage": {"on": on, "scope": "str", "against": None}} for on in ("attack_rolls", "ability_checks", "saves")], modify("damage_roll", "1d8", "sub"),
        {"turn_rules": {"repeat_save": {"ability": "con", "timing": "end_of_turn", "on_success": "end"}}}])]
    s["effects"][0]["on_success"] = [{"disadvantage": {"on": "attack_rolls", "scope": "all", "against": None, "uses": 1}, "until": "start_of_turn(caster.next_turn)"}]
    out.append(s)
    s = base(raw["Phantasmal Force"])
    s["effects"] = [block(target=single("visible"), save="int", effects=[{"status": {"id": "phantasmal_force", "data": {}}}]),
        block("hazard", target={"select": "ref", "ref": "main"}, event="start_of_turn(caster)", effects=[damage("2d8", "psychic")])]
    s["effects"][0]["on_success"] = [{"end_spell": True}]
    s["effects"][1]["source_ref"] = "entries.3"
    s["unsupported"] = ["Illusion content, rationalization, dangerous-hazard eligibility/proximity and sensory reactions need DM/position adjudication; the seeded hazard assumes an eligible dangerous illusion. A Study check can end it via study_illusion."]
    out.append(s)
    s = base(raw["Guardian of Faith"])
    s["effects"] = [block(target={**area("sphere", 10, "enemy")}, save="dex", half=True, event="on_creature_enters_aura(target) or start_of_turn(target)", limit="once_per_turn_per_target", effects=[{"damage": {"amount": 20, "type": "radiant", "end_after_total": 60}}])]
    s["unsupported"] = ["Guardian placement, space occupancy and movement entry require positions; starting enemies use the declared proximity heuristic. This invulnerable spectral force is not a creature summon."]
    out.append(s)
    for name, size in [("Darkness", 15), ("Silence", 20)]:
        s = base(raw[name])
        if name == "Silence": s["effects"] = [block(target=area("sphere", size), event="while_in_area", effects=[condition("deafened"), {"defense": {"immunity": ["thunder"]}}, {"status": {"id": "verbal_components_blocked", "data": {}}}])]
        s["unsupported"] = ["Lighting, hearing/sound propagation, spatial overlap dispelling, opaque coverings and object targeting require sensory/position adjudication; no blanket Blinded is invented for magical Darkness."]
        out.append(s)
    for name, die, dtype in [("Divine Favor", "1d4", "radiant"), ("Crusader's Mantle", "1d4", "radiant"), ("Fount of Moonlight", "2d6", "radiant"), ("Conjure Minor Elementals", "2d8", "$damage_type")]:
        s = base(raw[name]); extra = []
        if name == "Crusader's Mantle":
            extra = [block("aura", target={**area("emanation", 30, "ally"), "include_caster": True, "origin": "caster"}, event="while_in_area", effects=[{"status": {"id": "crusaders_mantle", "data": {}}}])]
            event = "on_attack_hit(attacker, defender)"; predicate = "attacker.has_status_from(crusaders_mantle, caster) and attack.weapon"
        else:
            event = "on_attack_hit(caster, defender)"
            predicate = "attack.weapon" if name == "Divine Favor" else "attack.melee" if name == "Fount of Moonlight" else None
        rider = block(target={"select": "ref", "ref": "trigger.defender"}, event=event, effects=[damage(die, dtype)])
        if predicate: rider["if"] = predicate
        s["effects"] = [*extra, rider]
        if name == "Conjure Minor Elementals":
            s["choices"] = [{"id": "damage_type", "options": ["acid", "cold", "fire", "lightning"], "when": "on_attack"}]
            scale(s, dice="1d8")
        if name == "Fount of Moonlight":
            s["effects"].insert(0, block("protection", target={"select": "self"}, effects=[{"defense": {"resistance": ["radiant"]}}]))
            s["effects"].append(block("flare", target={"select": "ref", "ref": "trigger.attacker", "within_ft": 60}, event="on_damaged(caster)", save="con", effects=[{**condition("blinded"), "until": "end_of_turn(caster.next_turn)"}], cost="reaction", optional=True, **{"if": "attacker.visible_to(caster)"}))
        s["unsupported"] = ["Emanation proximity, lighting and difficult terrain require positions/lighting; legal hit riders execute using the no-grid range convention."]
        out.append(s)
    return out
