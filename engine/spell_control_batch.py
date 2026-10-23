"""XPHB control/protection: explicit saves, targeting and ending rules."""
from .spell_catalog import base, block, single, multi, area, condition, scale, sources


TYPES = ["celestial", "elemental", "fey", "fiend", "undead"]


def spells():
    raw = sources(); out = []
    for name, ctype, control in [("Animal Friendship", "beast", False), ("Charm Person", "humanoid", False), ("Charm Monster", None, False), ("Dominate Beast", "beast", True), ("Dominate Person", "humanoid", True), ("Suggestion", None, False)]:
        s = base(raw[name]); t = multi(1, "visible")
        if ctype: t["eligible_if"] = "target.creature_type == " + ctype
        options = {"control": True, "repeat_on_damage": True} if control else {"ends_on_damage": "caster_allies"}
        effects = [condition("charmed", **options)]
        if name == "Suggestion": effects.append({"pacify": {}, "requires_condition": "charmed"})
        b = block(target=t, save="wis", effects=effects)
        if name in {"Charm Person", "Charm Monster", "Dominate Beast", "Dominate Person"}: b["save"]["advantage_if"] = "target.team != caster.team"
        s["effects"] = [b]
        if name in {"Animal Friendship", "Charm Person", "Charm Monster"}: scale(s, targets=1)
        if control:
            first = 5 if name == "Dominate Beast" else 6
            s["scaling"] = {"upcast": {"per_slot_above": s["level"], "changes": [
                {"slot_min": first, "slot_max": first, "duration": {"type": "minutes", "n": 10}},
                {"slot_min": first + 1, "slot_max": first + 1, "duration": {"type": "hours", "n": 1}},
                {"slot_min": first + 2, "slot_max": None, "duration": {"type": "hours", "n": 8}}]}}
            s["unsupported"] = ["Noncombat orders, planar telepathy and commanded reactions requiring both actors' reactions need external command adjudication. The executable order is to attack the caster's enemies on the target's own turn."]
        elif name == "Suggestion": s["unsupported"] = ["Hearing/language and arbitrary achievable natural-language instructions need adjudication. The executable suggestion is the explicitly permitted cease-fighting order; no damaging order or invented attack control is used."]
        else: s["unsupported"] = ["Friendly attitude, social checks and remembering the charm are outside the arena; Charmed combat restrictions and allied-damage ending execute."]
        out.append(s)
    s = base(raw["Calm Emotions"])
    s["choices"] = [{"id": "mode", "options": ["immune", "indifferent"], "when": "on_cast", "per_target": True}]
    t = area("sphere", 20); t["filter"].append("humanoid")
    s["effects"] = [block(target=t, save="cha", effects=[{"defense": {"condition_immunity": ["charmed", "frightened"]}, "if": "$mode == immune"}, {"pacify": {"witness_allies": True}, "if": "$mode == indifferent"}])]
    s["unsupported"] = ["Indifference selects the caster's allies as its protected group. Precise witnessing and arbitrary social attitudes need sensory adjudication; damage witnessed among arena allies ends indifference."]
    out.append(s)
    s = base(raw["Crown of Madness"])
    s["effects"] = [block(target=single("visible"), save="wis", effects=[condition("charmed", repeat_save={"ability": "wis", "timing": "end_of_turn", "on_success": "end"}), {"turn_rules": {"forced_melee": True, "maintained_by_action": True}, "requires_condition": "charmed"}]),
        block("maintain", target={"select": "self"}, event="action_command", effects=[{"maintain_spell": True}])]
    s["effects"][0]["save"]["auto_success_if"] = "target.creature_type != humanoid"
    s["unsupported"] = ["Melee reach is assumed under the no-grid convention; if there is no eligible other creature or melee attack, the victim can act normally. The chosen target is an enemy of the caster other than the victim."]
    out.append(s)
    s = base(raw["Confusion"])
    s["effects"] = [block(target=area("sphere", 10), save="wis", effects=[{"turn_rules": {"behavior_die": "1d10", "no_bonus_action": True, "no_reactions": True, "repeat_save": {"ability": "wis", "timing": "end_of_turn", "on_success": "end"}}}])]
    s["scaling"] = {"upcast": {"per_slot_above": 4, "changes": [{"block": "main", "area_size_add": 5}]}}
    s["unsupported"] = ["Random-direction movement, reach and no-movement cases require positions; action denial, random single melee attack and free-behavior d10 outcomes execute."]
    out.append(s)
    s = base(raw["Fear"])
    s["effects"] = [block(target={**area("cone", 30), "origin": "caster"}, save="wis", effects=[condition("frightened")])]
    s["unsupported"] = ["Dropping inventory, mandatory Dash when an escape route exists, safe-route movement and repeat Wisdom saves only after losing line of sight require inventory/positions. No unconditional action denial or repeat save is invented."]
    out.append(s)
    s = base(raw["Sleep"])
    s["effects"] = [block(target=area("sphere", 5, "chosen"), save="wis", effects=[condition("incapacitated", ends_on_damage="any", repeat_save={"ability": "wis", "timing": "end_of_turn", "on_success": "end"}, upgrade_on_failure="unconscious")])]
    s["effects"][0]["save"]["auto_success_if"] = "target.immune_to(exhaustion) or target.has_status(no_sleep)"
    s["unsupported"] = ["Non-sleeping species must be supplied as no_sleep; proximity and another creature's shake-awake action require an external rescue choice."]
    out.append(s)
    s = base(raw["Tasha's Hideous Laughter"])
    s["effects"] = [block(target=multi(1, "visible"), save="wis", effects=[condition("prone"), condition("incapacitated", repeat_save={"ability": "wis", "timing": "end_of_turn", "on_success": "end"}, repeat_on_damage=True, damage_save_advantage=True)])]
    scale(s, targets=1); out.append(s)
    s = base(raw["Compelled Duel"])
    s["effects"] = [block(target=single("visible"), save="wis", effects=[{"duel": {}}])]
    s["unsupported"] = ["The distance leash and end-turn separation check require positions; disadvantage against other attackers and offensive/allied-damage ending rules execute."]
    out.append(s)
    s = base(raw["Compulsion"])
    s["effects"] = [block(target={**multi(1, "visible"), "n": "all"}, save="wis", effects=[condition("charmed")])]
    s["unsupported"] = ["Bonus-action horizontal directions, safe-route movement and the Wisdom repeat save after that movement require a grid; Charmed applies without inventing an end-turn save."]
    out.append(s)
    s = base(raw["Sanctuary"])
    s["effects"] = [block(effects=[{"sanctuary": {"ability": "wis"}}])]
    out.append(s)
    s = base(raw["Telekinesis"])
    s["effects"] = [block(target={**single("visible"), "max_size": "H"}, save="str", event="on_cast or action_command", effects=[{**condition("restrained"), "until": "end_of_turn(caster.next_turn)"}])]
    s["unsupported"] = ["Creature displacement, suspension/falling and object disarming/manipulation require positions and inventory; target replacement and short-lived Restrained execute."]
    out.append(s)
    s = base(raw["Otiluke's Resilient Sphere"])
    s["effects"] = [block(target={**single(), "max_size": "L"}, save="dex", effects=[{"status": {"id": "isolated", "data": {}}}])]
    s["effects"][0]["save"]["auto_fail_if"] = "target.willing"
    s["unsupported"] = ["Sphere rolling, object pickup and Disintegrate targeting the sphere need positions/objects. Cross-boundary targeting and damage are blocked, but enclosed creatures may act on themselves; they are not removed/incapacitated."]
    out.append(s)
    s = base(raw["Protection from Evil and Good"])
    s["effects"] = [block(target=single("willing"), effects=[{"ward": {"types": ["aberration", *TYPES], "conditions": ["charmed", "frightened"], "attack_disadvantage": True, "existing_saves_advantage": True}}])]
    s["unsupported"] = ["Possession requires a possession state; source-typed attack disadvantage, new Charmed/Frightened immunity and existing-condition repeat-save Advantage execute."]
    out.append(s)
    s = base(raw["Dispel Evil and Good"])
    s["choices"] = [{"id": "function", "options": ["break", "dismiss"], "when": "on_cast"}]
    t = single(); t["eligible_if"] = "$function == break or target.creature_type in [celestial, elemental, fey, fiend, undead]"
    command = block("function", target=t, event="action_command", save="cha", effects=[{"remove_from_combat": {"until": "spell_ends", "returns": "false"}, "if": "target.has_status(off_home_plane)"}, {"end_spell": True}])
    command["save"]["if"] = "$function == dismiss"
    command["apply"] = [{"restore": {"kind": "charmed", "source_types": TYPES}}, {"restore": {"kind": "frightened", "source_types": TYPES}}, {"end_spell": True}]
    command["on_success"] = [{"end_spell": True}]
    s["effects"] = [block(target={"select": "self"}, effects=[{"ward": {"types": TYPES, "attack_disadvantage": True}}]), command]
    s["unsupported"] = ["Possession and home-plane identity require external state. Dismissal requires off_home_plane; Fey/Undead destination geometry is not modeled. Break Enchantment requires a source of an eligible type; fixtures select eligible enchantments."]
    out.append(s)
    s = base(raw["Mislead"])
    s["effects"] = [block(target={"select": "self"}, effects=[condition("invisible", ends_on_activity=True)])]
    s["unsupported"] = ["Intangible invulnerable illusion placement/movement, gestures and remote senses require sensory/position adjudication. Invisibility ends on attack, damage or another spell; the illusion can persist independently off-grid."]
    out.append(s)
    return out
