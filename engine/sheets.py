"""Minimal stat sheets: the same effect blocks power spells and creature actions."""
from .loader import Validator, ABILITIES, CONDITIONS, DAMAGE_TYPES


def effect_block(identifier, *, target=None, save=None, apply=None, on_fail=None):
    return {"id": identifier, "event": "on_cast", "target": target or {"select": "self"},
            "attack": None, "save": save, "on_hit": [], "on_fail": on_fail or [],
            "on_success": [], "apply": apply or [], "limit": None}


def validate_sheet(data, path, *, summoned=False):
    v = Validator(path)
    v.obj(data, "$", "name source max_hp ac abilities speed creature_type proficiency_bonus",
          "hp_formula cr level save_proficiencies save_bonuses resistances immunities vulnerabilities condition_immunities spell_ability spell_dc spell_attack_bonus spell_slots spells innate_spells limited_uses hit_dice attacks multiattack extra_attack actions traits alignment initiative_bonus unsupported unsupported_spells features movement_modes size routines replacements legendary spell_resources spell_levels spell_costs spell_recharge spell_components")
    for k in ("name", "creature_type", "source"): v.text(data[k], k)
    v.enum(data["source"], {"XMM", "XPHB"}, "source")
    for k in ("max_hp", "ac", "proficiency_bonus"):
        if summoned and k == "proficiency_bonus" and data[k] == "caster": pass
        else: v.number(data[k], k, 1, True)
    v.number(data["speed"], "speed", 0)
    v.obj(data["abilities"], "abilities", ABILITIES)
    for k, val in data["abilities"].items(): v.number(val, "abilities." + k, 1, True)
    for key, allowed in (("resistances", DAMAGE_TYPES), ("immunities", DAMAGE_TYPES), ("vulnerabilities", DAMAGE_TYPES), ("condition_immunities", CONDITIONS), ("save_proficiencies", ABILITIES)):
        if key in data:
            v.sequence(data[key], key)
            for x in data[key]: v.enum(x, allowed, key)
    if "hp_formula" in data: v.dice(data["hp_formula"], "hp_formula")
    if "cr" in data:
        from fractions import Fraction
        try: v.check(Fraction(str(data["cr"])) >= 0, "cr", "negative CR")
        except (ValueError, ZeroDivisionError): v.fail("cr", "invalid CR")
    if "alignment" in data: v.enum(data["alignment"], {"good", "neutral", "evil"}, "alignment")
    if "spell_ability" in data: v.enum(data["spell_ability"], ABILITIES, "spell_ability")
    for k in ("level", "spell_dc", "extra_attack"):
        if k in data: v.number(data[k], k, 1, True)
    for k in ("spell_attack_bonus", "initiative_bonus"):
        if k in data: v.number(data[k], k, integer=True)
    if "hit_dice" in data:
        v.obj(data["hit_dice"], "hit_dice", "die count")
        v.enum(data["hit_dice"]["die"], {"d6", "d8", "d10", "d12"}, "hit_dice.die")
        v.number(data["hit_dice"]["count"], "hit_dice.count", 1, True)
    if "save_bonuses" in data:
        v.check(isinstance(data["save_bonuses"], dict), "save_bonuses", "expected mapping")
        for k, val in data["save_bonuses"].items():
            v.enum(k, ABILITIES, "save_bonuses." + k); v.number(val, "save_bonuses." + k, integer=True)
    for k in ("limited_uses", "innate_spells", "spell_slots"):
        if k in data:
            v.check(isinstance(data[k], dict), k, "expected mapping")
            for key, val in data[k].items():
                if k == "spell_slots":
                    v.number(key, k, 1, True); v.check(key <= 9, k, "slot level > 9")
                else: v.text(key, k)
                p = k + "." + str(key)
                if k == "limited_uses" and isinstance(val, dict):
                    v.obj(val, p, "max", "short_rest long_rest")
                    v.number(val["max"], p + ".max", 0, True)
                    for rest in ("short_rest", "long_rest"):
                        if rest not in val: continue
                        if val[rest] != "all":
                            v.number(val[rest], p + "." + rest, 0, True)
                            v.check(val[rest] <= val["max"], p + "." + rest, "recovery exceeds max")
                else: v.number(val, p, 0, True)
    spells = None
    if "spells" in data:
        from .loader import load_spells
        spells = load_spells()
        v.sequence(data["spells"], "spells")
        for name in data["spells"]: v.check(name in spells, "spells", f"unknown spell {name}")
    for name in data.get("innate_spells", {}):
        v.check(name in data.get("spells", []) and name in data.get("limited_uses", {}), "innate_spells", "innate spell requires prepared spell and matching limited-use counter")
    attacks = data.get("attacks", [])
    v.sequence(attacks, "attacks")
    v.check(len({a.get('name') for a in attacks}) == len(attacks), "attacks", "duplicate attack name")
    for i, a in enumerate(attacks):
        p = f"attacks[{i}]"
        v.obj(a, p, "name kind to_hit effects", "reach_ft range_ft ability mastery recharge resource riders advantage_if on_hit_self")
        v.text(a["name"], p + ".name")
        v.enum(a["kind"], {"melee", "ranged"}, p + ".kind")
        if summoned and a["to_hit"] == "spell_attack": pass
        else: v.number(a["to_hit"], p + ".to_hit", integer=True)
        if "reach_ft" in a: v.number(a["reach_ft"], p + ".reach_ft", 0)
        if "range_ft" in a: v.number(a["range_ft"], p + ".range_ft", 0)
        if "ability" in a: v.enum(a["ability"], ABILITIES, p + ".ability")
        if "mastery" in a: v.enum(a["mastery"], {"graze", "vex", "sap"}, p + ".mastery")
        v.primitives(a["effects"], p + ".effects")
        if "on_hit_self" in a: v.primitives(a["on_hit_self"], p + ".on_hit_self")
        if "riders" in a: v.blocks(a["riders"], p + ".riders")
        if "advantage_if" in a: v.enum(a["advantage_if"], {"grappled_by_self"}, p)
        if "recharge" in a:
            v.number(a["recharge"], p + ".recharge", 1, True)
            v.check(a["recharge"] <= 6, p, "recharge must be 1..6")
        if "resource" in a: v.check(a["resource"] in data.get("limited_uses", {}), p, "counter not defined")
    if "multiattack" in data:
        v.sequence(data["multiattack"], "multiattack")
        for name in data["multiattack"]: v.check(name in {a["name"] for a in attacks}, "multiattack", "unknown attack")
    for k in ("actions", "traits"):
        v.sequence(data.get(k, []), k)
        for i, a in enumerate(data.get(k, [])):
            p = f"{k}[{i}]"
            v.obj(a, p, "name cost effects", "resource recharge grants_action restricted_to duration passive trigger")
            v.text(a["name"], p + ".name")
            v.enum(a["cost"], {"action", "bonus_action", "reaction", "free"}, p + ".cost")
            if "resource" in a: v.check(a["resource"] in data.get("limited_uses", {}), p + ".resource", "counter not defined")
            if "recharge" in a:
                v.number(a["recharge"], p + ".recharge", 1, True)
                v.check(a["recharge"] <= 6, p, "recharge must be 1..6")
            if "grants_action" in a:
                v.boolean(a["grants_action"], p + ".grants_action")
                v.check(not a["grants_action"] or not a["effects"], p + ".effects", "grants_action replaces effects; effects must be empty")
            if "restricted_to" in a:
                v.sequence(a["restricted_to"], p + ".restricted_to")
                for x in a["restricted_to"]: v.enum(x, {"hide", "disengage", "attack"}, p)
            if "duration" in a: v.duration(a["duration"], p + ".duration")
            if "passive" in a: v.boolean(a["passive"], p + ".passive")
            if "trigger" in a: v.enum(a["trigger"], {"enemy_turn_start", "creature_turn_start", "own_turn_start"}, p + ".trigger")
            v.blocks(a["effects"], p + ".effects")
    if "unsupported" in data:
        v.sequence(data["unsupported"], "unsupported")
        for x in data["unsupported"]: v.text(x, "unsupported")

    if "size" in data: v.enum(data["size"], {"T", "S", "M", "L", "H", "G"}, "size")
    for key in ("routines", "replacements"):
        if key not in data: continue
        v.sequence(data[key], key)
        options = {a["name"] for a in attacks + data.get("actions", [])} | set(data.get("spells", []))
        for routine in (data[key] if key == "routines" else [data[key]]):
            v.sequence(routine, key)
            v.check(bool(routine), key, "empty routine")
            for name in routine: v.check(name in options, key, "unknown routine option")
    for key in ("spell_resources", "spell_levels", "spell_costs"):
        if key not in data: continue
        v.check(isinstance(data[key], dict), key, "expected mapping")
        for name, value in data[key].items():
            v.check(name in data.get("spells", []), key, "spell not prepared")
            if key == "spell_resources": v.check(value in data.get("limited_uses", {}), key, "unknown spell counter")
            elif key == "spell_costs": v.enum(value, {"action", "bonus_action", "reaction"}, key)
            else:
                v.number(value, key, 0 if key == "spell_levels" else 1, True)
                v.check(spells[name]["level"] <= value <= 9, key, "invalid innate spell level")
    if "spell_recharge" in data:
        v.check(isinstance(data["spell_recharge"], dict), "spell_recharge", "expected mapping")
        for name, threshold in data["spell_recharge"].items():
            v.check(name in data.get("spells", []), "spell_recharge", "unknown spell")
            v.number(threshold, "spell_recharge." + name, 1, True)
            v.check(threshold <= 6, "spell_recharge." + name, "threshold exceeds 6")
    if "spell_components" in data:
        v.check(isinstance(data["spell_components"], dict), "spell_components", "expected mapping")
        for name, components in data["spell_components"].items():
            v.check(name in data.get("spells", []), "spell_components", "unknown spell")
            v.obj(components, "spell_components." + name, "", "v s m")
            for key, present in components.items(): v.boolean(present, "spell_components." + name + "." + key)
    if "features" in data:
        f = data["features"]
        v.obj(f, "features", "", "pack_tactics magic_resistance sunlight_sensitivity bloodied_frenzy evasion parry regeneration undead_fortitude life_drain redirect_attack authority_aura grapple_damage rampage")
        for key, value in f.items():
            if key in {"parry", "undead_fortitude"}: v.number(value, "features." + key, 1, True)
            elif key == "regeneration":
                v.obj(value, "features.regeneration", "amount blocked_by at_zero")
                v.number(value["amount"], "features.regeneration.amount", 1, True)
                v.boolean(value["at_zero"], "features.regeneration.at_zero")
                v.sequence(value["blocked_by"], "features.regeneration.blocked_by")
                for x in value["blocked_by"]: v.enum(x, DAMAGE_TYPES, "features.regeneration.blocked_by")
            elif key == "life_drain":
                v.obj(value, "features.life_drain", "attacks type heal")
                v.sequence(value["attacks"], "features.life_drain.attacks")
                for name in value["attacks"]: v.check(name in {a["name"] for a in attacks + data.get("actions", [])}, "features.life_drain", "unknown drain")
                v.enum(value["type"], DAMAGE_TYPES | {"all"}, "features.life_drain.type")
                v.boolean(value["heal"], "features.life_drain.heal")
            else: v.boolean(value, "features." + key)
    if "legendary" in data:
        l = data["legendary"]
        v.obj(l, "legendary", "uses options")
        v.number(l["uses"], "legendary.uses", 1, True)
        v.sequence(l["options"], "legendary.options")
        v.check(len({a.get("name") for a in l["options"]}) == len(l["options"]), "legendary.options", "duplicate name")
        for i, option in enumerate(l["options"]):
            p = f"legendary.options[{i}]"
            v.obj(option, p, "name cost", "attacks effects spell once_per_round heal requires_bound_target")
            v.text(option["name"], p)
            v.number(option["cost"], p + ".cost", 1, True)
            v.check(option["cost"] <= l["uses"], p, "cost exceeds budget")
            v.check(sum(k in option for k in ("attacks", "effects", "spell")) == 1, p, "one executable payload required")
            if "attacks" in option:
                v.sequence(option["attacks"], p)
                for name in option["attacks"]: v.check(name in {a["name"] for a in attacks}, p, "unknown attack")
            if "effects" in option: v.blocks(option["effects"], p + ".effects")
            if "spell" in option: v.check(option["spell"] in data.get("spells", []), p, "unknown spell")
            if "once_per_round" in option: v.boolean(option["once_per_round"], p)
            if "requires_bound_target" in option: v.boolean(option["requires_bound_target"], p)
            if "heal" in option: v.dice(option["heal"], p)
    if "unsupported_spells" in data:
        v.sequence(data["unsupported_spells"], "unsupported_spells")
        for name in data["unsupported_spells"]: v.text(name, "unsupported_spells")

    if "movement_modes" in data:
        v.obj(data["movement_modes"], "movement_modes", "", "walk fly climb swim burrow")
        for key, value in data["movement_modes"].items(): v.number(value, "movement_modes." + key, 0)
