"""Weapon-bound spell recipes and post-hit Bonus Action smites (2024)."""
from .spell_catalog import base, sources, block, single, area, damage, condition, modify, scale


def spells():
    raw = sources(); out = []
    s = base(raw["True Strike"]); s["choices"] = [{"id": "type", "options": ["radiant", "bludgeoning", "piercing", "slashing"], "when": "on_cast"}]
    s["effects"] = [block(effects=[{"weapon_strike": {"count": 1, "spell_ability": True, "type": "$type", "upgrade_levels": [5, 11, 17], "upgrade_dice": "1d6"}}])]
    s["unsupported"] = ["The caster must supply the material weapon's attack; normal damage-type choices must match that weapon. Radiant upgrade dice and the weapon's normal attack/damage execute."]; out.append(s)
    s = base(raw["Shillelagh"]); s["choices"] = [{"id": "type", "options": ["force", "bludgeoning"], "when": "on_cast"}]
    s["effects"] = [block(target={"select": "self"}, effects=[{"weapon_enchantment": {"names": ["club", "quarterstaff"], "spell_ability": True, "dice": "1d8", "type": "$type", "cantrip_dice": [{"level": 5, "dice": "1d10"}, {"level": 11, "dice": "1d12"}, {"level": 17, "dice": "2d6"}]}}])]; s["recast_ends_previous"] = True
    s["unsupported"] = ["Letting go of the chosen Club/Quarterstaff needs inventory state; only named eligible weapons are changed, never other attacks."]; out.append(s)
    for name in ("Magic Weapon", "Elemental Weapon"):
        s = base(raw[name]); v = {"attack_bonus": 1}
        if name == "Magic Weapon":
            v.update(damage_bonus=1, tiers=[{"slot_min": 3, "attack_bonus": 2, "damage_bonus": 2}, {"slot_min": 6, "attack_bonus": 3, "damage_bonus": 3}]); s["recast_ends_previous"] = True
        else:
            s["choices"] = [{"id": "type", "options": ["acid", "cold", "fire", "lightning", "thunder"], "when": "on_cast"}]
            v.update(extra_dice="1d4", extra_type="$type", tiers=[{"slot_min": 5, "attack_bonus": 2, "extra_dice": "2d4"}, {"slot_min": 7, "attack_bonus": 3, "extra_dice": "3d4"}])
        s["effects"] = [block(effects=[{"weapon_enchantment": v}])]
        s["unsupported"] = ["Targets use the wielding creature's first weapon as the touched weapon; nonmagical eligibility, transfers and inventory must be supplied externally. This does not enchant spell attacks."]; out.append(s)
    s = base(raw["Enlarge/Reduce"]); s["choices"] = [{"id": "size", "options": ["enlarge", "reduce"], "when": "on_cast"}]
    ps = []
    for mode, flag in [("enlarge", "advantage"), ("reduce", "disadvantage")]:
        ps += [{"size_change": {"direction": "increase" if mode == "enlarge" else "decrease"}, "if": "$size == " + mode}, *[{flag: {"on": on, "scope": "str", "against": None}, "if": "$size == " + mode} for on in ("ability_checks", "saves")], {"weapon_adjustment": {"dice": "1d4", "op": "add" if mode == "enlarge" else "sub", "minimum": 1}, "if": "$size == " + mode}]
    s["effects"] = [block(save="con", effects=ps)]; s["effects"][0]["save"]["if"] = "not target.willing"
    s["unsupported"] = ["Objects, equipment resizing, carrying capacity and occupied space need inventory/positions; size and weapon/Unarmed Strike extra or reduced 1d4 (minimum 1) execute."]; out.append(s)
    s = base(raw["Swift Quiver"]); s["effects"] = [block(event="on_cast or bonus_action_command", effects=[{"weapon_strike": {"count": 2, "kind": "ranged"}}])]
    s["unsupported"] = ["Caster supplies the Arrow/Bolt weapon attack. Ammunition inventory is not tracked; the spell's two attacks need none consumed."]; out.append(s)
    smites = [("Divine Smite", "2d8", "radiant", "1d8"), ("Searing Smite", "1d6", "fire", "1d6"), ("Thunderous Smite", "2d6", "thunder", "1d6"), ("Wrathful Smite", "1d6", "necrotic", "1d6"), ("Shining Smite", "2d6", "radiant", "1d6"), ("Blinding Smite", "3d8", "radiant", "1d8"), ("Staggering Smite", "4d6", "psychic", "1d6"), ("Banishing Smite", "5d10", "force", None)]
    for name, die, typ, inc in smites:
        s = base(raw[name]); s["casting_trigger"] = "weapon_hit" if name == "Banishing Smite" else "melee_hit"
        s["effects"] = [block(effects=[damage(die, typ)])]
        if name == "Divine Smite": s["effects"][0]["apply"].append({**damage("1d8", "radiant"), "if": "target.creature_type in [fiend, undead]"})
        if name == "Searing Smite":
            s["effects"] += [block("burn", target={"select": "ref", "ref": "main"}, event="start_of_turn(target)", effects=[damage(die, typ)]), block("extinguish", target={"select": "ref", "ref": "main"}, event="start_of_turn(target)", save="con")]
            s["effects"][-1]["on_success"] = [{"end_spell": True}]
        if name in {"Thunderous Smite", "Wrathful Smite", "Staggering Smite"}:
            save, cond = {"Thunderous Smite": ("str", "prone"), "Wrathful Smite": ("wis", "frightened"), "Staggering Smite": ("wis", "stunned")}[name]
            p = condition(cond, **({"persistent": True} if cond == "prone" else {"repeat_save": {"ability": "wis", "timing": "end_of_turn", "on_success": "end"}} if cond == "frightened" else {}))
            if cond == "stunned": p["until"] = "end_of_turn(caster.next_turn)"
            s["effects"].append(block("rider", target={"select": "ref", "ref": "main"}, save=save, effects=[p]))
        if name == "Shining Smite": s["effects"][0]["apply"] += [{"advantage": {"on": "attack_rolls", "scope": "all", "against": "target", "recipient": "any_attacker"}}, {"status": {"id": "invisibility_suppressed", "data": {}}}]
        if name == "Blinding Smite": s["effects"][0]["apply"].append(condition("blinded", repeat_save={"ability": "con", "timing": "end_of_turn", "on_success": "end"}))
        if name == "Banishing Smite":
            s["effects"].append(block("banish", target={"select": "ref", "ref": "main"}, save="cha", effects=[condition("incapacitated"), {"remove_from_combat": {"until": "spell_ends", "returns": "true"}}], **{"if": "target.hp <= 50"}))
            s["effects"][-1]["after_damage"] = True
            s["unsupported"] = ["Space of return needs positions. The post-hit cast occurs after the triggering weapon's damage; the bonus damage is resolved before the 50-HP check."]
        if inc:
            scale(s, dice=inc)
            if name == "Divine Smite": s["scaling"]["upcast"]["changes"][0]["exclude_conditional"] = True
            if name == "Searing Smite": s["scaling"]["upcast"]["changes"].append({"block": "burn", "dice_add": inc})
        if name == "Staggering Smite": s["ends_on"] = ["end_of_turn(caster.next_turn)"]
        if name == "Thunderous Smite": s["unsupported"] = ["Audibility and 10-foot push need sensory/position adjudication; Strength save and Prone execute."]
        if name == "Shining Smite": s["unsupported"] = ["Five-foot Bright Light radius needs sensory/position adjudication; incoming Advantage and Invisible suppression execute."]
        out.append(s)
    s = base(raw["Ensnaring Strike"]); s["casting_trigger"] = "weapon_hit"
    s["effects"] = [block(save="str", effects=[condition("restrained", escape_dc="spell_dc")]), block("vines", target={"select": "ref", "ref": "main"}, event="start_of_turn(target)", effects=[{**damage("1d6", "piercing"), "requires_condition": "restrained"}])]
    s["effects"][0]["save"]["advantage_if"] = "target.size in [L, H, G]"; s["effects"][0]["on_success"] = [{"end_spell": True}]; scale(s, block="vines", dice="1d6")
    s["unsupported"] = ["Another creature's in-reach Strength (Athletics) rescue needs an explicit ally action choice; self-escape executes."]; out.append(s)
    s = base(raw["Hail of Thorns"]); s["casting_trigger"] = "weapon_hit"; s["effects"] = [block(target={**area("sphere", 5), "origin": "trigger.defender"}, save="dex", half=True, effects=[damage("1d10", "piercing")])]; scale(s, dice="1d10")
    s["unsupported"] = ["Only Ranged weapon hits are legal; the caller supplies that trigger. Exact five-foot splash membership needs positions."]; out.append(s)
    s = base(raw["Lightning Arrow"]); s["casting_trigger"] = "ranged_hit_or_miss"
    s["effects"] = [block(effects=[damage("4d8", "lightning")]), block("splash", target={**area("sphere", 10), "origin": "main", "exclude": "origin"}, save="dex", half=True, effects=[damage("2d8", "lightning")])]
    scale(s, dice="1d8"); s["scaling"]["upcast"]["changes"].append({"block": "splash", "dice_add": "1d8"})
    s["unsupported"] = ["Invoke using replace_weapon_attack to replace all original attack damage/riders; the direct target takes half on a miss. Splash excludes that target. Exact ten-foot proximity requires positions."]; out.append(s)
    s = base(raw["Alter Self"]); s["choices"] = [{"id": "type", "options": ["slashing", "piercing", "bludgeoning"], "when": "on_cast"}]
    s["effects"] = [block(target={"select": "self"}, effects=[{"weapon_enchantment": {"names": ["unarmed strike"], "spell_ability": True, "dice": "1d6", "type": "$type"}}])]
    s["unsupported"] = ["Aquatic adaptation, appearance, and changing options with a Magic action require environment/sensory choices; the Natural Weapons option alters an existing Unarmed Strike, not all weapons."]; out.append(s)
    return out
