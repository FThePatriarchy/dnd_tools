"""Strict validation of the handwritten effect contract, with source paths."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import yaml

from .dice import parts, add
from .expressions import parse, EVENTS, ExpressionError

ROOT = Path(__file__).resolve().parents[1] / "data" / "handwritten"
ABILITIES = {"str", "dex", "con", "int", "wis", "cha"}
CONDITIONS = {"blinded", "charmed", "deafened", "exhaustion", "frightened", "grappled", "incapacitated", "invisible", "paralyzed", "petrified", "poisoned", "prone", "restrained", "stunned", "unconscious"}
DAMAGE_TYPES = {"acid", "bludgeoning", "cold", "fire", "force", "lightning", "necrotic", "piercing", "poison", "psychic", "radiant", "slashing", "thunder"}
TOP = "name source level school casting_time reaction_trigger range components duration concentration ritual choices effects scaling ends_on unsupported".split()
BLOCK = "id event target attack save on_hit on_fail on_success apply limit".split()
PRIMITIVES = {
    "heal_pool": ("amount cap", ""), "kill": ("", ""),
    "damage": ("type", "dice amount bonus explode_max wounded_dice delay leech half end_after_total leap_on_duplicate slot_bonus add_caster_mod"), "heal": ("", "dice bonus amount"),
    "temp_hp": ("", "dice amount"),
    "type_mask": ("type", ""), "extinguish": ("", ""),
    "apply_condition": ("condition", "repeat_save escape_dc max_size linked upgrade_on_failure control repeat_on_damage obstacle capacity large_cost ends_on_activity persistent ends_on_spell_targeted ends_spell ends_on_damage damage_save_advantage tally_save resist_removal"),
    "modify": ("stat op value scope", "recipient uses"),
    "advantage": ("on scope against", "recipient uses require_visible"),
    "disadvantage": ("on scope against", "recipient uses require_visible"),
    "grant_action": ("kind restricted_to", "attack_limit"),
    "status": ("id data", ""), "burning": ("", ""),
    "remove_from_combat": ("until returns", ""),
    "counter_spell": ("target cancel_effects consume_casting_action expend_slot", ""),
    "end_spell": ("", ""), "on_spell_end": ("", ""),
    "turn_rules": ("", "no_action no_bonus_action no_reactions no_spells no_attacks forced_melee maintained_by_action dismiss_action end_at_zero behavior_die on_turn_condition action_or_bonus attack_limit somatic_failure_percent repeat_save"),
    "spend_reaction": ("", ""),
    "base_ac": ("base ability unarmored_only", ""),
    "remove_condition": ("condition", ""), "dispel": ("auto_level dc_base", ""),
    "defense": ("", "resistance vulnerability immunity condition_immunity magical_condition_immunity save_conditions"),
    "stabilize": ("", ""), "restore": ("kind", "all source_types"),
    "end_concentration": ("", ""), "grant_command": ("block action", ""),
    "pacify": ("", "witness_allies"), "duel": ("", ""), "sanctuary": ("ability", ""),
    "ward": ("types", "conditions attack_disadvantage existing_saves_advantage suppress_existing"), "maintain_spell": ("", ""),
    "summon": ("choice forms base_slot per_slot", "attack_count_divisor ends_on_damage creature_type_choice fixed_attacks persistent mount fly_slot after_attack_action count count_per_slot command_cost familiar control_hours form_cost damage_dice_add"),
    "transform": ("choice forms", ""), "force_object": ("ac hp", ""),
    "weapon_strike": ("count", "kind spell_ability type upgrade_levels upgrade_dice"),
    "weapon_enchantment": ("", "attack_bonus damage_bonus dice spell_ability type extra_dice extra_type tiers cantrip_dice names"),
    "weapon_adjustment": ("dice op minimum", ""),
    "size_change": ("direction", ""), "curse_damage": ("dice type", ""), "curse_dodge": ("ability", ""), "control": ("", ""),
    "max_hp": ("amount", ""), "hit_dice_heal": ("max_dice", ""),
    "death_ward": ("floor", ""), "berries": ("count healing", ""),
    "reduce_damage": ("dice type", ""), "magic_saves": ("", ""), "bond": ("", ""),
    "mirror_images": ("count dice threshold", ""), "blink": ("dice threshold", ""),
}


class ValidationError(ValueError):
    pass


class Validator:
    def __init__(self, filename):
        self.filename = str(filename)
        self.ids = set()
        self.choices = set()

    def fail(self, path, message):
        raise ValidationError(f"{self.filename}:{path}: {message}")

    def check(self, ok, path, message):
        if not ok:
            self.fail(path, message)

    def obj(self, value, path, required="", optional=""):
        self.check(isinstance(value, dict), path, "expected mapping")
        required = set(required.split() if isinstance(required, str) else required)
        allowed = required | set(optional.split() if isinstance(optional, str) else optional)
        for key in value:
            self.check(key in allowed, f"{path}.{key}", "unknown key")
        for key in required:
            self.check(key in value, f"{path}.{key}", "missing required key")

    def enum(self, value, choices, path):
        self.check(any(type(value) is type(x) and value == x for x in choices), path, f"expected one of {sorted(str(x) for x in choices)}")

    def number(self, value, path, minimum=None, integer=False):
        self.check(type(value) in ({int} if integer else {int, float}), path, "expected number")
        self.check(minimum is None or value >= minimum, path, f"must be >= {minimum}")

    def boolean(self, value, path):
        self.check(type(value) is bool, path, "expected boolean")

    def sequence(self, value, path):
        self.check(isinstance(value, list), path, "expected list")

    def text(self, value, path):
        self.check(isinstance(value, str) and bool(value), path, "expected nonempty string")

    def expr(self, value, path, event=False, lifetime=False):
        try:
            tree = parse(value)
        except (ValueError, TypeError, IndexError) as exc:
            self.fail(path, str(exc))
        def walk(node):
            kind = node[0]
            if kind == "name" and node[1].startswith("$"):
                self.check(node[1][1:] in self.choices, path, "unknown choice")
            if kind == "attr":
                root = node[1]
                while root[0] == "attr": root = root[1]
                self.check(root[0] == "name" and root[1] in self.ids | {"caster", "target", "attacker", "defender", "affected", "trigger", "spell", "turn", "attack"}, path, "unknown state reference")
                chain = []
                current = node
                while current[0] == "attr":
                    chain.insert(0, current[2]); current = current[1]
                domain = "binding" if root[1] in self.ids else {"caster": "creature", "target": "creature", "attacker": "creature", "defender": "creature", "affected": "creature"}.get(root[1], root[1])
                attributes = {
                    "creature": {k: "scalar" for k in ("alignment", "creature_type", "actual_creature_type", "size", "hp", "max_hp", "team", "willing", "next_turn", "this_turn", "has_status", "has_status_from", "has_condition", "has_condition_from", "visible_to", "immune_to", "bloodied")},
                    "binding": {"target": "creature", "target_dropped_to_zero": "scalar", "drop_turn": "scalar"},
                    "spell": {"elapsed_minutes": "scalar", "cast_turn": "scalar"},
                    "trigger": {"caster": "creature", "spell": "pending_spell"},
                    "pending_spell": {"has_any_component": "scalar"},
                    "turn": {"index": "scalar"},
                    "attack": {k: "scalar" for k in ("advantage", "critical", "total", "natural", "weapon", "melee")},
                }
                for attr in chain:
                    self.check(attr in attributes.get(domain, {}), path, f"unknown {domain} attribute {attr}")
                    domain = attributes[domain][attr]
            for child in node[1:]:
                if isinstance(child, tuple): walk(child)
                elif isinstance(child, list):
                    for x in child: walk(x)
        walk(tree)
        if event or lifetime:
            def subscription(node):
                if node[0] in {"or", "and"} and not lifetime:
                    subscription(node[1]); subscription(node[2]); return
                if node[0] == "call" and node[1][0] == "attr" and not lifetime:
                    return
                name = node[1] if node[0] == "name" else node[1][1] if node[0] == "call" and node[1][0] == "name" else None
                self.check(name in EVENTS, path, f"unknown event {name}")
                args = node[2] if node[0] == "call" else []
                self.check(len(args) == EVENTS[name], path, f"wrong arity for {name}")
                if lifetime:
                    self.check(name in {"start_of_turn", "end_of_turn"}, path, "invalid lifetime boundary")
                    args = node[2] if node[0] == "call" else []
                    self.check(len(args) == 1 and args[0][0] == "attr" and args[0][2] in {"next_turn", "this_turn"}, path, "expected actor.next_turn/this_turn")
                    self.check(args[0][1] in {("name", "caster"), ("name", "target")}, path, "lifetime actor must be caster or target")
                elif name in {"start_of_turn", "end_of_turn", "on_damaged", "on_attacked", "on_falling"}:
                    self.check(args[0] in {("name", x) for x in ("caster", "target", "affected", "any_enemy_in_area")}, path, "unknown event actor")
                elif name in {"on_attack_hit", "on_attack_provisional_hit"}:
                    self.check(all(a in {("name", x) for x in ("caster", "target", "attacker", "defender", "any")} for a in args), path, "invalid attack event actor")
                elif name in {"on_aura_moves_onto_creature", "on_creature_enters_aura", "end_of_turn_in_aura"}:
                    self.check(args == [("name", "target")], path, "area event requires target")
                elif name == "on_spell_cast_nearby":
                    self.check(args[0][0] == "literal" and type(args[0][1]) in {int, float} and args[0][1] > 0, path, "range must be positive number")
                elif name == "on_spell_targeted":
                    self.check(args == [("name", "caster"), ("name", "magic_missile")], path, "unsupported targeted-spell trigger")
            subscription(tree)

    def dice(self, value, path):
        try: parts(value)
        except (ValueError, AttributeError, TypeError) as exc: self.fail(path, str(exc))

    def duration(self, value, path):
        self.obj(value, path, "type", "n")
        self.enum(value["type"], {"instant", "rounds", "minutes", "hours", "until_dispelled", "special"}, path + ".type")
        if value["type"] in {"rounds", "minutes", "hours"}:
            self.check("n" in value, path + ".n", "timed duration requires n")
            self.number(value["n"], path + ".n", 1)
        else:
            self.check("n" not in value, path, "n only valid for timed durations")

    def target(self, value, path):
        self.check(isinstance(value, dict) and "select" in value, path, "target requires select")
        kind = value["select"]
        self.enum(kind, {"self", "single", "n_targets", "area", "ref"}, path + ".select")
        common = "origin within_ft eligible_if max_size include_caster"
        req = {"self": "select", "single": "select filter affects", "n_targets": "select n distinct filter affects", "area": "select shape size_ft affects", "ref": "select ref"}[kind]
        opt = common + (" up_to min" if kind == "n_targets" else "") + (" filter exclude" if kind == "area" else "")
        self.obj(value, path, req, opt)
        if "max_size" in value: self.enum(value["max_size"], {"T", "S", "M", "L", "H", "G"}, path + ".max_size")
        if "eligible_if" in value: self.expr(value["eligible_if"], path + ".eligible_if")
        if "affects" in value: self.enum(value["affects"], {"any", "enemy", "ally", "all", "enemies", "chosen"}, path + ".affects")
        if "filter" in value:
            self.sequence(value["filter"], path + ".filter")
            for f in value["filter"]: self.enum(f, {"creature", "object", "creature_or_object", "humanoid", "visible", "willing", "new_target"}, path + ".filter")
        if "n" in value and value["n"] != "all": self.number(value["n"], path + ".n", 1, True)
        if "include_caster" in value: self.boolean(value["include_caster"], path + ".include_caster")
        for k in ("distinct", "up_to"):
            if k in value: self.boolean(value[k], path + "." + k)
        if "min" in value:
            self.number(value["min"], path + ".min", 0, True)
            self.check(value["n"] == "all" or value["min"] <= value["n"], path, "min exceeds n")
        if "shape" in value: self.enum(value["shape"], {"sphere", "emanation", "cone", "cube", "line", "cylinder"}, path + ".shape")
        for k in ("size_ft", "within_ft"):
            if k in value: self.number(value[k], path + "." + k, 0)
        if "origin" in value: self.enum(value["origin"], {"caster", "spiritual_weapon", "trigger.defender"} | self.ids, path + ".origin")
        if "exclude" in value: self.enum(value["exclude"], {"designated_on_cast", "summoner", "caster", "origin"}, path + ".exclude")
        if kind == "ref":
            self.check(value["ref"] in self.ids | {"spell_target", "trigger.caster", "trigger.spell", "trigger.attacker", "trigger.defender"}, path + ".ref", "unknown target reference")

    def primitives(self, effects, path):
        self.sequence(effects, path)
        for i, item in enumerate(effects):
            p = f"{path}[{i}]"
            self.check(isinstance(item, dict), p, "expected primitive mapping")
            keys = set(item) - {"if", "until", "duration", "requires_condition", "participants"}
            self.check(len(keys) == 1, p, "expected exactly one primitive")
            key = next(iter(keys))
            self.check(key in PRIMITIVES, p + "." + str(key), "unknown primitive")
            if "participants" in item:
                self.sequence(item["participants"], p + ".participants")
                for participant in item["participants"]: self.enum(participant, {"caster", "target"}, p + ".participants")
            if "requires_condition" in item: self.enum(item["requires_condition"], CONDITIONS, p + ".requires_condition")
            if "if" in item: self.expr(item["if"], p + ".if")
            if "until" in item: self.expr(item["until"], p + ".until", lifetime=True)
            if "duration" in item: self.duration(item["duration"], p + ".duration")
            value = item[key]
            q = p + "." + key
            if key in {"end_spell", "spend_reaction", "stabilize", "end_concentration", "maintain_spell"}:
                self.check(value is True, q, "must be true"); continue
            if key == "on_spell_end":
                self.primitives(value, q); continue
            self.obj(value, q, *PRIMITIVES[key])
            if "dice" in value: self.dice(value["dice"], q + ".dice")
            if "bonus" in value:
                self.check(type(value["bonus"]) in {int, float} or value["bonus"] in {"spell_mod", "summon_slot"}, q + ".bonus", "invalid bonus")
            if key == "damage":
                self.check(("dice" in value) != ("amount" in value), q, "damage requires dice or amount")
                if "amount" in value: self.number(value["amount"], q + ".amount", 0)
                if "add_caster_mod" in value: self.boolean(value["add_caster_mod"], q)
                if "slot_bonus" in value: self.boolean(value["slot_bonus"], q)
                if "leap_on_duplicate" in value: self.boolean(value["leap_on_duplicate"], q)
                if "leech" in value: self.number(value["leech"], q + ".leech", 0)
                if "end_after_total" in value: self.number(value["end_after_total"], q + ".end_after_total", 1)
                if "delay" in value: self.expr(value["delay"], q + ".delay", lifetime=True)
                if "half" in value: self.boolean(value["half"], q + ".half")
                dtype = value["type"]
                self.check(dtype in DAMAGE_TYPES or (isinstance(dtype, str) and dtype.startswith("$") and dtype[1:] in self.choices), q + ".type", "unknown damage type")
                if "explode_max" in value: self.enum(value["explode_max"], {"spell_mod"}, q + ".explode_max")
                if "wounded_dice" in value: self.dice(value["wounded_dice"], q + ".wounded_dice")
            elif key == "heal_pool":
                self.number(value["amount"], q + ".amount", 0, True)
                self.enum(value["cap"], {"half", "full"}, q + ".cap")
            elif key in {"temp_hp", "heal"}:
                self.check(("dice" in value) != ("amount" in value), q, "requires exactly one of dice/amount")
                if "amount" in value and value["amount"] not in {"spell_mod", "full"} or key == "temp_hp" and value.get("amount") == "full": self.number(value["amount"], q + ".amount", 0)
            elif key == "apply_condition":
                self.enum(value["condition"], CONDITIONS, q + ".condition")
                if "resist_removal" in value: self.enum(value["resist_removal"], ABILITIES, q)
                if "tally_save" in value:
                    self.obj(value["tally_save"], q, "ability successes failures failure_hours")
                    self.enum(value["tally_save"]["ability"], ABILITIES, q)
                    for k in ("successes", "failures", "failure_hours"): self.number(value["tally_save"][k], q, 1, True)
                if "repeat_save" in value:
                    r = value["repeat_save"]
                    self.obj(r, q + ".repeat_save", "ability timing on_success")
                    self.enum(r["ability"], ABILITIES, q)
                    self.enum(r["timing"], {"start_of_turn", "end_of_turn"}, q)
                    self.check(r["on_success"] == "end", q, "repeat success must end")
                for k in ("capacity", "large_cost"):
                    if k in value: self.number(value[k], q + "." + k, 1, True)
                if "escape_dc" in value and value["escape_dc"] != "spell_dc": self.number(value["escape_dc"], q + ".escape_dc", 1, True)
                if "max_size" in value: self.enum(value["max_size"], {"T", "S", "M", "L", "H", "G"}, q + ".max_size")
                for flag in ("linked", "control", "repeat_on_damage", "ends_on_activity", "persistent", "ends_on_spell_targeted", "ends_spell", "damage_save_advantage"):
                    if flag in value: self.boolean(value[flag], q + "." + flag)
                if "ends_on_damage" in value: self.enum(value["ends_on_damage"], {"any", "caster_allies"}, q + ".ends_on_damage")
                if "upgrade_on_failure" in value: self.enum(value["upgrade_on_failure"], CONDITIONS, q + ".upgrade_on_failure")
                if "obstacle" in value:
                    o = value["obstacle"]
                    self.obj(o, q + ".obstacle", "ac hp vulnerabilities immunities")
                    for k in ("ac", "hp"): self.number(o[k], q + ".obstacle." + k, 1, True)
                    for k in ("vulnerabilities", "immunities"):
                        self.sequence(o[k], q + ".obstacle." + k)
                        for t in o[k]: self.enum(t, DAMAGE_TYPES, q + ".obstacle." + k)
            elif key == "modify":
                self.enum(value["stat"], {"ac", "speed", "fly_speed", "attack_roll", "save", "concentration_save", "damage_roll", "ability_check", "action_count"}, q + ".stat")
                self.enum(value["op"], {"add", "sub", "mul", "set"}, q + ".op")
                if isinstance(value["value"], str): self.dice(value["value"], q + ".value")
                else: self.number(value["value"], q + ".value")
                self.enum(value["scope"], {"all"} | ABILITIES | {"$" + x for x in self.choices}, q + ".scope")
                if "recipient" in value: self.enum(value["recipient"], {"any_attacker"}, q + ".recipient")
                if "uses" in value: self.number(value["uses"], q + ".uses", 1, True)
            elif key == "base_ac":
                self.number(value["base"], q + ".base", 0, True)
                self.enum(value["ability"], ABILITIES | {None}, q + ".ability")
                self.boolean(value["unarmored_only"], q + ".unarmored_only")
            elif key == "type_mask":
                self.enum(value["type"], {"$" + c for c in self.choices}, q + ".type")
            elif key == "turn_rules":
                self.check(bool(value), q, "empty turn rules")
                for k in ("no_action", "no_bonus_action", "no_reactions", "no_spells", "no_attacks", "forced_melee", "maintained_by_action", "dismiss_action", "end_at_zero", "action_or_bonus"):
                    if k in value: self.boolean(value[k], q + "." + k)
                if "on_turn_condition" in value: self.enum(value["on_turn_condition"], CONDITIONS, q + ".on_turn_condition")
                if "behavior_die" in value: self.dice(value["behavior_die"], q + ".behavior_die")
                if "attack_limit" in value: self.number(value["attack_limit"], q + ".attack_limit", 1, True)
                if "somatic_failure_percent" in value:
                    self.number(value["somatic_failure_percent"], q + ".somatic_failure_percent", 0, True)
                    self.check(value["somatic_failure_percent"] <= 100, q, "percentage exceeds 100")
                if "repeat_save" in value:
                    r = value["repeat_save"]
                    self.obj(r, q + ".repeat_save", "ability timing on_success")
                    self.enum(r["ability"], ABILITIES, q)
                    self.enum(r["timing"], {"start_of_turn", "end_of_turn"}, q)
                    self.enum(r["on_success"], {"end"}, q)
            elif key == "remove_condition":
                self.check(value["condition"] in CONDITIONS or value["condition"] in {"$" + c for c in self.choices}, q, "unknown condition/choice")
            elif key == "dispel":
                self.number(value["auto_level"], q + ".auto_level", 0, True)
                self.number(value["dc_base"], q + ".dc_base", 0, True)
            elif key == "defense":
                self.check(bool(value), q, "empty defense")
                for field, values in value.items():
                    self.sequence(values, q + "." + field)
                    self.check(bool(values), q, "empty defense list")
                    allowed = DAMAGE_TYPES | {"$" + x for x in self.choices} if field in {"resistance", "immunity", "vulnerability"} else CONDITIONS
                    for val in values: self.enum(val, allowed, q + "." + field)
            elif key in {"weapon_strike", "weapon_enchantment"}:
                for field in ("count", "attack_bonus", "damage_bonus"):
                    if field in value: self.number(value[field], q + "." + field, 0, True)
                for field in ("dice", "extra_dice", "upgrade_dice"):
                    if field in value: self.dice(value[field], q + "." + field)
                if "spell_ability" in value: self.boolean(value["spell_ability"], q)
                if "kind" in value: self.enum(value["kind"], {"melee", "ranged"}, q)
                for field in ("type", "extra_type"):
                    if field in value: self.enum(value[field], DAMAGE_TYPES | {"$" + c for c in self.choices}, q)
                for field in ("names", "upgrade_levels", "tiers", "cantrip_dice"):
                    if field in value: self.sequence(value[field], q + "." + field)
                for tier in value.get("tiers", []):
                    self.obj(tier, q + ".tiers", "slot_min", "attack_bonus damage_bonus extra_dice")
                    for k, n in tier.items():
                        if k == "extra_dice": self.dice(n, q)
                        else: self.number(n, q, 1, True)
                for tier in value.get("cantrip_dice", []):
                    self.obj(tier, q, "level dice"); self.number(tier["level"], q, 1, True); self.dice(tier["dice"], q)
                for n in value.get("upgrade_levels", []): self.number(n, q, 1, True)
                for n in value.get("names", []): self.text(n, q)
            elif key == "weapon_adjustment":
                self.dice(value["dice"], q); self.enum(value["op"], {"add", "sub"}, q); self.number(value["minimum"], q, 0, True)
            elif key == "size_change": self.enum(value["direction"], {"increase", "decrease"}, q)
            elif key == "curse_damage":
                self.dice(value["dice"], q); self.enum(value["type"], DAMAGE_TYPES, q)
            elif key in {"max_hp", "hit_dice_heal", "death_ward", "berries", "mirror_images", "blink"}:
                for field, n in value.items():
                    if field == "dice": self.dice(n, q + ".dice")
                    else: self.number(n, q + "." + field, 1, True)
            elif key == "reduce_damage":
                self.dice(value["dice"], q + ".dice")
                self.enum(value["type"], DAMAGE_TYPES | {"$" + c for c in self.choices}, q + ".type")
            elif key == "restore":
                self.enum(value["kind"], ABILITIES | CONDITIONS | {"curse", "max_hp"} | {"$" + x for x in self.choices}, q + ".kind")
                if "all" in value: self.boolean(value["all"], q + ".all")
                if "source_types" in value:
                    self.sequence(value["source_types"], q)
                    for t in value["source_types"]: self.enum(t, {"celestial","elemental","fey","fiend","undead"}, q)
            elif key == "grant_command":
                self.enum(value["block"], self.ids, q + ".block")
                self.enum(value["action"], {"action", "bonus_action"}, q + ".action")
            elif key == "ward":
                self.sequence(value["types"], q + ".types")
                for x in value["types"]: self.enum(x, {"aberration", "celestial", "elemental", "fey", "fiend", "undead"}, q + ".types")
                for x in value.get("conditions", []): self.enum(x, CONDITIONS, q + ".conditions")
                for x in ("attack_disadvantage", "existing_saves_advantage", "suppress_existing"):
                    if x in value: self.boolean(value[x], q + "." + x)
            elif key == "pacify":
                if "witness_allies" in value: self.boolean(value["witness_allies"], q)
            elif key == "curse_dodge": self.enum(value["ability"], ABILITIES, q)
            elif key == "sanctuary": self.enum(value["ability"], ABILITIES, q + ".ability")
            elif key == "force_object":
                self.number(value["ac"], q, 1, True); self.enum(value["hp"], {"caster_max_hp"}, q)
            elif key == "transform":
                from .sheets import validate_sheet
                self.enum(value["choice"], {"$" + c for c in self.choices}, q)
                for name, sheet in value["forms"].items(): validate_sheet(sheet, q + "." + name, summoned=True)
            elif key == "summon":
                from .summon_validation import validate_summon
                validate_summon(self, value, q)
            elif key in {"advantage", "disadvantage"}:
                self.enum(value["on"], {"attack_rolls", "saves", "ability_checks"}, q + ".on")
                self.check(value["scope"] in {"all"} | ABILITIES or value["scope"] in {"$" + x for x in self.choices}, q + ".scope", "unknown scope")
                self.enum(value["against"], {None, "target"}, q + ".against")
                if "recipient" in value: self.enum(value["recipient"], {"any_attacker"}, q)
                if "uses" in value: self.number(value["uses"], q + ".uses", 1, True)
                if "require_visible" in value: self.boolean(value["require_visible"], q + ".require_visible")
            elif key == "grant_action":
                self.enum(value["kind"], {"action", "bonus_action", "reaction"}, q + ".kind")
                self.sequence(value["restricted_to"], q)
                for x in value["restricted_to"]: self.enum(x, {"attack", "dash", "disengage", "hide", "utilize", "cast"}, q)
                if "attack_limit" in value: self.number(value["attack_limit"], q, 1, True)
            elif key == "status":
                self.text(value["id"], q + ".id")
                self.check(isinstance(value["data"], dict), q + ".data", "expected mapping")
                if value["id"] == "engulfed":
                    self.obj(value["data"], q + ".data", "escape_dc")
                    self.number(value["data"]["escape_dc"], q + ".data.escape_dc", 1, True)
            elif key == "remove_from_combat":
                self.check(value["until"] == "spell_ends", q, "invalid removal lifetime")
                self.expr(value["returns"], q + ".returns")
            elif key == "counter_spell":
                self.check(value == {"target": "trigger.spell", "cancel_effects": True, "consume_casting_action": True, "expend_slot": False}, q, "unsupported counterspell semantics")

    def blocks(self, blocks, path="effects"):
        self.sequence(blocks, path)
        ids = [b.get("id") for b in blocks if isinstance(b, dict)]
        self.check(len(ids) == len(blocks) and all(isinstance(x, str) and x for x in ids), path, "blocks require string ids")
        self.check(len(set(ids)) == len(ids), path, "duplicate block id")
        self.ids = set(ids)
        for i, block in enumerate(blocks):
            p = f"{path}[{i}]"
            self.obj(block, p, BLOCK, "if optional resolution damage_roll source_ref admission cost on_miss max_uses limit_group after_damage end_after_resolution requires_condition")
            if "requires_condition" in block: self.enum(block["requires_condition"], CONDITIONS, p + ".requires_condition")
            if "end_after_resolution" in block: self.boolean(block["end_after_resolution"], p)
            if "after_damage" in block: self.boolean(block["after_damage"], p)
            if "limit_group" in block: self.text(block["limit_group"], p + ".limit_group")
            if "max_uses" in block: self.number(block["max_uses"], p + ".max_uses", 1, True)
            if "on_miss" in block: self.primitives(block["on_miss"], p + ".on_miss")
            if "cost" in block: self.enum(block["cost"], {"reaction"}, p + ".cost")
            if "source_ref" in block: self.text(block["source_ref"], p + ".source_ref")
            if "admission" in block:
                self.obj(block["admission"], p + ".admission", "capacity large_cost", "condition status")
                self.check(("condition" in block["admission"]) != ("status" in block["admission"]), p, "admission requires condition or status")
                if "condition" in block["admission"]: self.enum(block["admission"]["condition"], CONDITIONS, p)
                if "status" in block["admission"]: self.text(block["admission"]["status"], p + ".admission.status")
                for key in ("capacity", "large_cost"): self.number(block["admission"][key], p, 1, True)
            self.expr(block["event"], p + ".event", event=True)
            if "if" in block: self.expr(block["if"], p + ".if")
            if "optional" in block: self.boolean(block["optional"], p + ".optional")
            if "resolution" in block: self.enum(block["resolution"], {"simultaneous"}, p)
            if "damage_roll" in block:
                self.enum(block["damage_roll"], {"shared"}, p)
                self.check(block.get("resolution") == "simultaneous", p, "shared roll requires simultaneous resolution")
            self.target(block["target"], p + ".target")
            self.check(not (block["attack"] and block["save"]), p, "attack and save are exclusive")
            if block["attack"] is not None:
                self.obj(block["attack"], p + ".attack", "type")
                self.enum(block["attack"]["type"], {"ranged_spell", "melee_spell"}, p + ".attack.type")
            if block["save"] is not None:
                self.obj(block["save"], p + ".save", "ability on_success", "ignore_cover dc disadvantage_if advantage_if auto_fail_if auto_success_if if")
                for flag in ("disadvantage_if", "advantage_if", "auto_fail_if", "auto_success_if", "if"):
                    if flag in block["save"]: self.expr(block["save"][flag], p + ".save." + flag)
                self.enum(block["save"]["ability"], ABILITIES, p + ".save.ability")
                if "dc" in block["save"]: self.number(block["save"]["dc"], p + ".save.dc", 1, True)
                self.enum(block["save"]["on_success"], {"half", "negate"}, p + ".save.on_success")
                if "ignore_cover" in block["save"]:
                    self.sequence(block["save"]["ignore_cover"], p + ".save.ignore_cover")
                    for x in block["save"]["ignore_cover"]: self.enum(x, {"half", "three_quarters"}, p)
            self.enum(block["limit"], {None, "once_per_turn", "once_per_turn_per_target"}, p + ".limit")
            for key in ("on_hit", "on_fail", "on_success", "apply"):
                self.primitives(block[key], p + "." + key)

    def spell(self, data):
        self.obj(data, "$", TOP, "recast_ends_previous casting_time_n casting_trigger duration_tiers")
        for tier in data.get("duration_tiers", []):
            self.obj(tier, "duration_tiers", "slot_min duration concentration")
            self.number(tier["slot_min"], "duration_tiers", 1, True); self.duration(tier["duration"], "duration_tiers"); self.boolean(tier["concentration"], "duration_tiers")
        if "casting_trigger" in data: self.enum(data["casting_trigger"], {"melee_hit", "weapon_hit", "ranged_hit_or_miss"}, "casting_trigger")
        if "casting_time_n" in data:
            self.enum(data["casting_time"], {"minute", "minutes", "hour", "hours"}, "casting_time_n")
            self.number(data["casting_time_n"], "casting_time_n", 1, True)
        if "recast_ends_previous" in data: self.boolean(data["recast_ends_previous"], "recast_ends_previous")
        for key in ("name", "school"): self.text(data[key], key)
        self.check(data["source"] == "XPHB", "source", "expected XPHB")
        self.number(data["level"], "level", 0, True)
        self.check(data["level"] <= 9, "level", "maximum level 9")
        self.enum(data["school"], {"abjuration", "conjuration", "divination", "enchantment", "evocation", "illusion", "necromancy", "transmutation"}, "school")
        self.enum(data["casting_time"], {"action", "bonus_action", "reaction", "minute", "minutes", "hour", "hours"}, "casting_time")
        for key in ("concentration", "ritual"): self.boolean(data[key], key)
        self.obj(data["range"], "range", "type", "feet")
        self.enum(data["range"]["type"], {"self", "touch", "point", "sight", "unlimited"}, "range.type")
        if data["range"]["type"] == "point": self.check("feet" in data["range"], "range.feet", "required for point range")
        if "feet" in data["range"]: self.number(data["range"]["feet"], "range.feet", 0)
        c = data["components"]
        self.obj(c, "components", "v s m m_consumed m_cost_gp")
        for k in ("v", "s", "m_consumed"): self.boolean(c[k], "components." + k)
        if c["m"] is not None: self.text(c["m"], "components.m")
        if c["m_cost_gp"] is not None: self.number(c["m_cost_gp"], "components.m_cost_gp", 0)
        self.duration(data["duration"], "duration")
        self.sequence(data["choices"], "choices")
        self.choices = {c.get("id") for c in data["choices"]}
        self.choice_options = {c.get("id"): c.get("options", []) for c in data["choices"]}
        self.check(len(self.choices) == len(data["choices"]), "choices", "duplicate choice id")
        for i, choice in enumerate(data["choices"]):
            p = f"choices[{i}]"
            self.obj(choice, p, "id options when", "option_conditions per_target")
            if "per_target" in choice: self.boolean(choice["per_target"], p + ".per_target")
            self.text(choice["id"], p + ".id")
            self.sequence(choice["options"], p + ".options")
            self.check(bool(choice["options"]), p, "empty choices")
            self.enum(choice["when"], {"on_cast", "on_attack"}, p + ".when")
            for option in choice["options"]: self.text(option, p + ".options")
            if "option_conditions" in choice:
                self.check(isinstance(choice["option_conditions"], dict), p, "expected option conditions mapping")
                for option, expr in choice["option_conditions"].items():
                    self.check(option in choice["options"], p, "condition for unknown option")
                    self.expr(expr, p + ".option_conditions." + option)
        self.blocks(data["effects"])
        if data["reaction_trigger"] is not None: self.expr(data["reaction_trigger"], "reaction_trigger", event=True)
        self.check((data["casting_time"] == "reaction") == (data["reaction_trigger"] is not None), "reaction_trigger", "reaction trigger/casting time mismatch")
        self.sequence(data["ends_on"], "ends_on")
        for i, x in enumerate(data["ends_on"]): self.expr(x, f"ends_on[{i}]", lifetime=True)
        self.sequence(data["unsupported"], "unsupported")
        for x in data["unsupported"]: self.text(x, "unsupported")
        scaling = data["scaling"]
        if scaling is None: return
        self.obj(scaling, "scaling", "", "cantrip upcast")
        if "cantrip" in scaling:
            c = scaling["cantrip"]
            self.obj(c, "scaling.cantrip", "at effect")
            self.sequence(c["at"], "scaling.cantrip.at")
            self.check(c["at"] == sorted(set(c["at"])), "scaling.cantrip.at", "thresholds must be sorted and unique")
            for x in c["at"]: self.number(x, "scaling.cantrip.at", 1, True)
            self.change(c["effect"], "scaling.cantrip.effect", cantrip=True)
        if "upcast" in scaling:
            u = scaling["upcast"]
            self.obj(u, "scaling.upcast", "per_slot_above changes")
            self.check(u["per_slot_above"] == data["level"] > 0, "scaling.upcast.per_slot_above", "must equal base spell level")
            self.sequence(u["changes"], "scaling.upcast.changes")
            for i, c in enumerate(u["changes"]): self.change(c, f"scaling.upcast.changes[{i}]")
        for kind in scaling:
            changes = [scaling[kind]["effect"]] if kind == "cantrip" else scaling[kind]["changes"]
            for c in changes:
                if "block" not in c: continue
                b = next(b for b in data["effects"] if b["id"] == c["block"])
                if "amount_add" in c:
                    ps = [p for key in ("on_hit", "on_fail", "on_success", "apply") for p in b[key]]
                    self.check(any("temp_hp" in p for p in ps), "scaling", "amount scaling needs temp_hp")
                elif "dice_add" in c:
                    dice = [p[k]["dice"] for key in ("on_hit", "on_fail", "on_success", "apply") for p in b[key] for k in ("damage", "heal") if k in p and ("damage_type" not in c or p[k].get("type") == c["damage_type"])]
                    self.check(bool(dice), "scaling", "dice scaling block has no damage/healing")
                    for d in dice:
                        self.check(parts(d)[1] == parts(c["dice_add"])[1], "scaling", "incompatible dice scaling")
                elif any(k in c for k in ("value_add", "miss_dice_add", "capacity_add", "uses_add")): pass
                elif "area_size_add" in c: self.check(b["target"]["select"] == "area", "scaling", "area scaling needs area")
                else: self.check(b["target"]["select"] == "n_targets", "scaling", "count scaling needs n_targets")

    def change(self, c, path, cantrip=False):
        if "duration_hours_add" in c:
            self.obj(c, path, "duration_hours_add"); self.number(c["duration_hours_add"], path, 1, True); return
        if cantrip and "range_multiplier" in c:
            self.obj(c, path, "range_multiplier")
            self.number(c["range_multiplier"], path, 1, True)
            return
        if isinstance(c, dict) and "duration" in c:
            self.obj(c, path, "slot_min slot_max duration")
            self.number(c["slot_min"], path, 1, True)
            if c["slot_max"] is not None: self.number(c["slot_max"], path, c["slot_min"], True)
            self.duration(c["duration"], path + ".duration")
            return
        keys = "dice_add beam_count_add" if cantrip else "dice_add target_n_add amount_add area_size_add value_add miss_dice_add capacity_add uses_add"
        self.obj(c, path, "block", keys + " damage_type if timing exclude_conditional")
        if "if" in c: self.expr(c["if"], path + ".if")
        if "exclude_conditional" in c: self.boolean(c["exclude_conditional"], path)
        if "timing" in c: self.enum(c["timing"], {"immediate", "delayed"}, path + ".timing")
        self.check(c["block"] in self.ids, path + ".block", "unknown block")
        self.check(len(set(c) - {"block", "damage_type", "if", "timing", "exclude_conditional"}) == 1, path, "requires exactly one scaling operation")
        if "damage_type" in c:
            self.enum(c["damage_type"], DAMAGE_TYPES, path + ".damage_type")
            self.check("dice_add" in c, path, "damage_type requires dice_add")
        for key in c:
            if key in {"dice_add", "miss_dice_add"}: self.dice(c[key], path + "." + key)
            elif key not in {"block", "damage_type", "if", "timing", "exclude_conditional"}: self.number(c[key], path + "." + key, 1, True)


def read_yaml(path):
    try:
        with Path(path).open(encoding="utf8") as stream:
            # Reject duplicate keys instead of silently accepting the last value.
            class UniqueLoader(yaml.SafeLoader):
                pass
            def mapping(loader, node):
                result = {}
                for k, v in node.value:
                    key = loader.construct_object(k)
                    if key in result: raise ValidationError(f"{path}: duplicate key {key}")
                    result[key] = loader.construct_object(v)
                return result
            UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
            return yaml.load(stream, Loader=UniqueLoader)
    except yaml.YAMLError as exc:
        raise ValidationError(f"{path}: YAML: {exc}") from exc


@lru_cache(maxsize=512)
def _validated_spell(path, mtime_ns, size):
    data = read_yaml(path)
    try:
        Validator(path).spell(data)
    except ValidationError:
        raise
    except (TypeError, KeyError, AttributeError, IndexError) as exc:
        raise ValidationError(f"{path}:$: malformed spell structure ({exc})") from exc
    return data


def load_spell(path) -> dict:
    path = Path(path).resolve()
    stat = path.stat()
    # Every caller owns its dictionaries; parsing/validation alone is cached.
    return deepcopy(_validated_spell(str(path), stat.st_mtime_ns, stat.st_size))


def load_spells(directory=None) -> dict[str, dict]:
    return {s["name"]: s for s in (load_spell(p) for p in sorted(Path(directory or ROOT / "spells").glob("*.yaml")))}


def scaled_spell(spell: dict, slot: int, level: int, choices=None) -> dict:
    result = deepcopy(spell)
    for tier in spell.get("duration_tiers", []):
        if slot >= tier["slot_min"]: result["duration"] = deepcopy(tier["duration"]); result["concentration"] = tier["concentration"]
    scaling = result.get("scaling") or {}
    increments = []
    if "cantrip" in scaling:
        c = scaling["cantrip"]
        increments.append((c["effect"], sum(level >= x for x in c["at"])))
    if "upcast" in scaling:
        u = scaling["upcast"]
        for c in u["changes"]:
            if "duration" in c:
                if slot >= c["slot_min"] and (c["slot_max"] is None or slot <= c["slot_max"]): result["duration"] = deepcopy(c["duration"])
            else: increments.append((c, max(0, slot - u["per_slot_above"])))
    for c, count in increments:
        if not count: continue
        if "if" in c:
            from .expressions import evaluate
            selected = {ch["id"]: ch["options"][0] for ch in spell["choices"]}
            selected.update(choices or {})
            if not evaluate(c["if"], {"$" + k: v for k, v in selected.items()}): continue
        if "duration_hours_add" in c:
            result["duration"]["n"] += count * c["duration_hours_add"]; continue
        if "range_multiplier" in c:
            result["range"]["feet"] *= c["range_multiplier"] ** count
            continue
        b = next(b for b in result["effects"] if b["id"] == c["block"])
        if "uses_add" in c: b["max_uses"] += c["uses_add"] * count
        elif "capacity_add" in c:
            for branch in ("on_hit", "on_fail", "apply"):
                for p in b[branch]:
                    if "apply_condition" in p: p["apply_condition"]["capacity"] += c["capacity_add"] * count
        elif "miss_dice_add" in c:
            for p in b.get("on_miss", []):
                if "damage" in p: p["damage"]["dice"] = add(p["damage"]["dice"], c["miss_dice_add"], count)
        elif "value_add" in c:
            for branch in ("on_hit", "on_fail", "on_success", "apply"):
                for p in b[branch]:
                    for kind in ("max_hp", "temp_hp", "damage", "hit_dice_heal"):
                        if kind in p:
                            key = "max_dice" if kind == "hit_dice_heal" else "amount"
                            if key in p[kind]: p[kind][key] += c["value_add"] * count
        elif "area_size_add" in c:
            b["target"]["size_ft"] += c["area_size_add"] * count
        elif "amount_add" in c:
            for key in ("on_hit", "on_fail", "on_success", "apply"):
                for p in b[key]:
                    if "temp_hp" in p:
                        value = p["temp_hp"]
                        if "amount" in value: value["amount"] += c["amount_add"] * count
                        else:
                            n, sides, bonus = parts(value["dice"])
                            value["dice"] = f"{n}d{sides}{bonus + c['amount_add'] * count:+d}"
        elif "dice_add" in c:
            for key in ("on_hit", "on_fail", "on_success", "apply"):
                for p in b[key]:
                    if c.get("exclude_conditional") and "if" in p: continue
                    for kind in ("damage", "heal"):
                        if "timing" in c and bool(p.get(kind, {}).get("delay")) != (c["timing"] == "delayed"): continue
                        if kind in p and ("damage_type" not in c or p[kind].get("type") == c["damage_type"]):
                            p[kind]["dice"] = add(p[kind]["dice"], c["dice_add"], count)
                            if "wounded_dice" in p[kind]:
                                n, sides, _ = parts(c["dice_add"])
                                wounded_sides = parts(p[kind]["wounded_dice"])[1]
                                p[kind]["wounded_dice"] = add(p[kind]["wounded_dice"], f"{n}d{wounded_sides}", count)
        else: b["target"]["n"] += count * c.get("beam_count_add", c.get("target_n_add", 0))
    return result


@lru_cache(maxsize=64)
def _validated_sheet(path, mtime_ns, size):
    return load_sheet(path)


def monster_sheet(name) -> dict:
    """A monster sheet by name, parsed and validated once (Wild Shape loads forms every turn)."""
    path = (ROOT / "monsters" / (name + ".yaml")).resolve()
    stat = path.stat()
    return deepcopy(_validated_sheet(str(path), stat.st_mtime_ns, stat.st_size))


def load_sheet(path) -> dict:
    from .sheets import validate_sheet
    data = read_yaml(path)
    try:
        validate_sheet(data, path)
    except ValidationError:
        raise
    except (TypeError, KeyError, AttributeError, IndexError) as exc:
        raise ValidationError(f"{path}:$: malformed stat sheet ({exc})") from exc
    return data
