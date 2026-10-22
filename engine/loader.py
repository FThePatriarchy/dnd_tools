"""Strict validation of the handwritten effect contract, with source paths."""
from copy import deepcopy
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
    "damage": ("dice bonus type", ""), "heal": ("dice bonus", ""),
    "temp_hp": ("", "dice amount"),
    "apply_condition": ("condition", "repeat_save escape_dc max_size linked upgrade_on_failure control repeat_on_damage obstacle capacity large_cost"),
    "modify": ("stat op value scope", ""),
    "advantage": ("on scope against", "recipient uses"),
    "disadvantage": ("on scope against", "recipient uses"),
    "grant_action": ("kind restricted_to", "attack_limit"),
    "status": ("id data", ""), "burning": ("", ""),
    "remove_from_combat": ("until returns", ""),
    "counter_spell": ("target cancel_effects consume_casting_action expend_slot", ""),
    "end_spell": ("", ""), "on_spell_end": ("", ""),
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
                    "creature": {k: "scalar" for k in ("alignment", "creature_type", "size", "hp", "max_hp", "next_turn", "has_status", "has_status_from", "has_condition", "has_condition_from", "visible_to")},
                    "binding": {"target": "creature", "target_dropped_to_zero": "scalar", "drop_turn": "scalar"},
                    "spell": {"elapsed_minutes": "scalar", "cast_turn": "scalar"},
                    "trigger": {"caster": "creature", "spell": "pending_spell"},
                    "pending_spell": {"has_any_component": "scalar"},
                    "turn": {"index": "scalar"},
                    "attack": {k: "scalar" for k in ("advantage", "critical", "total", "natural")},
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
                    self.check(len(args) == 1 and args[0][0] == "attr" and args[0][2] == "next_turn", path, "expected actor.next_turn")
                    self.check(args[0][1] in {("name", "caster"), ("name", "target")}, path, "lifetime actor must be caster or target")
                elif name in {"start_of_turn", "end_of_turn", "on_damaged", "on_attacked"}:
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
        common = "origin within_ft eligible_if max_size"
        req = {"self": "select", "single": "select filter affects", "n_targets": "select n distinct filter affects", "area": "select shape size_ft affects", "ref": "select ref"}[kind]
        opt = common + (" up_to min" if kind == "n_targets" else "") + (" filter exclude" if kind == "area" else "")
        self.obj(value, path, req, opt)
        if "max_size" in value: self.enum(value["max_size"], {"T", "S", "M", "L", "H", "G"}, path + ".max_size")
        if "eligible_if" in value: self.expr(value["eligible_if"], path + ".eligible_if")
        if "affects" in value: self.enum(value["affects"], {"any", "enemy", "ally", "all", "enemies", "chosen"}, path + ".affects")
        if "filter" in value:
            self.sequence(value["filter"], path + ".filter")
            for f in value["filter"]: self.enum(f, {"creature", "object", "creature_or_object", "humanoid", "visible", "willing", "new_target"}, path + ".filter")
        if "n" in value: self.number(value["n"], path + ".n", 1, True)
        for k in ("distinct", "up_to"):
            if k in value: self.boolean(value[k], path + "." + k)
        if "min" in value:
            self.number(value["min"], path + ".min", 0, True)
            self.check(value["min"] <= value["n"], path, "min exceeds n")
        if "shape" in value: self.enum(value["shape"], {"sphere", "emanation", "cone", "cube", "line", "cylinder"}, path + ".shape")
        for k in ("size_ft", "within_ft"):
            if k in value: self.number(value[k], path + "." + k, 0)
        if "origin" in value: self.enum(value["origin"], {"caster", "spiritual_weapon"}, path + ".origin")
        if "exclude" in value: self.enum(value["exclude"], {"designated_on_cast"}, path + ".exclude")
        if kind == "ref":
            self.check(value["ref"] in self.ids | {"spell_target", "trigger.caster", "trigger.spell"}, path + ".ref", "unknown target reference")

    def primitives(self, effects, path):
        self.sequence(effects, path)
        for i, item in enumerate(effects):
            p = f"{path}[{i}]"
            self.check(isinstance(item, dict), p, "expected primitive mapping")
            keys = set(item) - {"if", "until"}
            self.check(len(keys) == 1, p, "expected exactly one primitive")
            key = next(iter(keys))
            self.check(key in PRIMITIVES, p + "." + str(key), "unknown primitive")
            if "if" in item: self.expr(item["if"], p + ".if")
            if "until" in item: self.expr(item["until"], p + ".until", lifetime=True)
            value = item[key]
            q = p + "." + key
            if key == "end_spell":
                self.check(value is True, q, "must be true"); continue
            if key == "on_spell_end":
                self.primitives(value, q); continue
            self.obj(value, q, *PRIMITIVES[key])
            if "dice" in value: self.dice(value["dice"], q + ".dice")
            if "bonus" in value:
                self.check(type(value["bonus"]) in {int, float} or value["bonus"] == "spell_mod", q + ".bonus", "invalid bonus")
            if key == "damage":
                dtype = value["type"]
                self.check(dtype in DAMAGE_TYPES or (isinstance(dtype, str) and dtype.startswith("$") and dtype[1:] in self.choices), q + ".type", "unknown damage type")
            elif key == "temp_hp":
                self.check(("dice" in value) != ("amount" in value), q, "requires exactly one of dice/amount")
                if "amount" in value: self.number(value["amount"], q + ".amount", 0)
            elif key == "apply_condition":
                self.enum(value["condition"], CONDITIONS, q + ".condition")
                if "repeat_save" in value:
                    r = value["repeat_save"]
                    self.obj(r, q + ".repeat_save", "ability timing on_success")
                    self.enum(r["ability"], ABILITIES, q)
                    self.enum(r["timing"], {"start_of_turn", "end_of_turn"}, q)
                    self.check(r["on_success"] == "end", q, "repeat success must end")
                for k in ("capacity", "large_cost"):
                    if k in value: self.number(value[k], q + "." + k, 1, True)
                if "escape_dc" in value: self.number(value["escape_dc"], q + ".escape_dc", 1, True)
                if "max_size" in value: self.enum(value["max_size"], {"T", "S", "M", "L", "H", "G"}, q + ".max_size")
                for flag in ("linked", "control", "repeat_on_damage"):
                    if flag in value: self.boolean(value[flag], q + "." + flag)
                if "upgrade_on_failure" in value: self.enum(value["upgrade_on_failure"], CONDITIONS, q + ".upgrade_on_failure")
                if "obstacle" in value:
                    o = value["obstacle"]
                    self.obj(o, q + ".obstacle", "ac hp vulnerabilities immunities")
                    for k in ("ac", "hp"): self.number(o[k], q + ".obstacle." + k, 1, True)
                    for k in ("vulnerabilities", "immunities"):
                        self.sequence(o[k], q + ".obstacle." + k)
                        for t in o[k]: self.enum(t, DAMAGE_TYPES, q + ".obstacle." + k)
            elif key == "modify":
                self.enum(value["stat"], {"ac", "speed", "attack_roll", "save", "damage_roll", "ability_check", "action_count"}, q + ".stat")
                self.enum(value["op"], {"add", "mul", "set"}, q + ".op")
                if isinstance(value["value"], str): self.dice(value["value"], q + ".value")
                else: self.number(value["value"], q + ".value")
                self.enum(value["scope"], {"all"} | ABILITIES, q + ".scope")
            elif key in {"advantage", "disadvantage"}:
                self.enum(value["on"], {"attack_rolls", "saves", "ability_checks"}, q + ".on")
                self.check(value["scope"] in {"all"} | ABILITIES or value["scope"] in {"$" + x for x in self.choices}, q + ".scope", "unknown scope")
                self.enum(value["against"], {None, "target"}, q + ".against")
                if "recipient" in value: self.enum(value["recipient"], {"any_attacker"}, q)
                if "uses" in value: self.number(value["uses"], q + ".uses", 1, True)
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
            self.obj(block, p, BLOCK, "if optional resolution damage_roll source_ref admission")
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
                self.obj(block["save"], p + ".save", "ability on_success", "ignore_cover dc")
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
        self.obj(data, "$", TOP)
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
        self.check(len(self.choices) == len(data["choices"]), "choices", "duplicate choice id")
        for i, choice in enumerate(data["choices"]):
            p = f"choices[{i}]"
            self.obj(choice, p, "id options when", "option_conditions")
            self.text(choice["id"], p + ".id")
            self.sequence(choice["options"], p + ".options")
            self.check(bool(choice["options"]), p, "empty choices")
            self.check(choice["when"] == "on_cast", p, "choices only on_cast")
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
                if "dice_add" in c:
                    dice = [p[k]["dice"] for key in ("on_hit", "on_fail", "on_success", "apply") for p in b[key] for k in ("damage", "heal") if k in p]
                    self.check(bool(dice), "scaling", "dice scaling block has no damage/healing")
                    for d in dice:
                        self.check(parts(d)[1] == parts(c["dice_add"])[1], "scaling", "incompatible dice scaling")
                else: self.check(b["target"]["select"] == "n_targets", "scaling", "count scaling needs n_targets")

    def change(self, c, path, cantrip=False):
        if isinstance(c, dict) and "duration" in c:
            self.obj(c, path, "slot_min slot_max duration")
            self.number(c["slot_min"], path, 1, True)
            if c["slot_max"] is not None: self.number(c["slot_max"], path, c["slot_min"], True)
            self.duration(c["duration"], path + ".duration")
            return
        keys = "dice_add beam_count_add" if cantrip else "dice_add target_n_add"
        self.obj(c, path, "block", keys)
        self.check(c["block"] in self.ids, path + ".block", "unknown block")
        self.check(len(c) == 2, path, "requires exactly one scaling operation")
        for key in c:
            if key == "dice_add": self.dice(c[key], path + "." + key)
            elif key != "block": self.number(c[key], path + "." + key, 1, True)


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


def load_spell(path) -> dict:
    data = read_yaml(path)
    try:
        Validator(path).spell(data)
    except ValidationError:
        raise
    except (TypeError, KeyError, AttributeError, IndexError) as exc:
        raise ValidationError(f"{path}:$: malformed spell structure ({exc})") from exc
    return data


def load_spells(directory=None) -> dict[str, dict]:
    return {s["name"]: s for s in (load_spell(p) for p in sorted(Path(directory or ROOT / "spells").glob("*.yaml")))}


def scaled_spell(spell: dict, slot: int, level: int) -> dict:
    result = deepcopy(spell)
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
        b = next(b for b in result["effects"] if b["id"] == c["block"])
        if "dice_add" in c:
            for key in ("on_hit", "on_fail", "on_success", "apply"):
                for p in b[key]:
                    for kind in ("damage", "heal"):
                        if kind in p: p[kind]["dice"] = add(p[kind]["dice"], c["dice_add"], count)
        else: b["target"]["n"] += count * c.get("beam_count_add", c.get("target_n_add", 0))
    return result


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
