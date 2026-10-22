"""Minimal stat sheets: the same effect blocks power spells and creature actions."""
from .loader import Validator, ABILITIES, CONDITIONS, DAMAGE_TYPES


def effect_block(identifier, *, target=None, save=None, apply=None, on_fail=None):
    return {"id": identifier, "event": "on_cast", "target": target or {"select": "self"},
            "attack": None, "save": save, "on_hit": [], "on_fail": on_fail or [],
            "on_success": [], "apply": apply or [], "limit": None}


def validate_sheet(data, path):
    v = Validator(path)
    v.obj(data, "$", "name source max_hp ac abilities speed creature_type proficiency_bonus",
          "hp_formula cr level save_proficiencies save_bonuses resistances immunities vulnerabilities condition_immunities spell_ability spell_dc spell_attack_bonus spell_slots spells innate_spells limited_uses attacks multiattack extra_attack actions traits alignment initiative_bonus unsupported")
    for k in ("name", "creature_type", "source"): v.text(data[k], k)
    v.enum(data["source"], {"XMM", "XPHB"}, "source")
    for k in ("max_hp", "ac", "proficiency_bonus"): v.number(data[k], k, 1, True)
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
                v.number(val, k + "." + str(key), 0, True)
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
        v.obj(a, p, "name kind to_hit effects", "reach_ft ability mastery")
        v.text(a["name"], p + ".name")
        v.enum(a["kind"], {"melee", "ranged"}, p + ".kind")
        v.number(a["to_hit"], p + ".to_hit", integer=True)
        if "reach_ft" in a: v.number(a["reach_ft"], p + ".reach_ft", 0)
        if "ability" in a: v.enum(a["ability"], ABILITIES, p + ".ability")
        if "mastery" in a: v.enum(a["mastery"], {"graze", "vex", "sap"}, p + ".mastery")
        v.primitives(a["effects"], p + ".effects")
        v.check(all("damage" in x for x in a["effects"]), p, "weapon attacks only support damage; use action blocks otherwise")
    if "multiattack" in data:
        v.sequence(data["multiattack"], "multiattack")
        for name in data["multiattack"]: v.check(name in {a["name"] for a in attacks}, "multiattack", "unknown attack")
    for k in ("actions", "traits"):
        v.sequence(data.get(k, []), k)
        for i, a in enumerate(data.get(k, [])):
            p = f"{k}[{i}]"
            v.obj(a, p, "name cost effects", "resource recharge grants_action restricted_to")
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
            v.blocks(a["effects"], p + ".effects")
    if "unsupported" in data:
        v.sequence(data["unsupported"], "unsupported")
        for x in data["unsupported"]: v.text(x, "unsupported")
