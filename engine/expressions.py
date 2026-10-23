"""A small declarative expression parser, never Python evaluation.

Only the three documented methods and explicitly supplied event functions can
be called. Attribute lookup cannot reach arbitrary Python object internals.
"""
import re
from functools import lru_cache

EVENTS = {
    "on_cast": 0, "start_of_turn": 1, "end_of_turn": 1,
    "on_attack_hit": 2, "on_damaged": 1, "on_attacked": 1,
    "on_spell_cast_nearby": 1, "bonus_action_command": 0, "action_command": 0,
    "while_in_area": 0, "on_aura_moves_onto_creature": 1,
    "on_creature_enters_aura": 1, "end_of_turn_in_aura": 1,
    "on_spell_targeted": 2, "on_attack_provisional_hit": 2,
    "on_falling": 1, "glyph_triggered": 0,
}
METHODS = {"has_status", "has_status_from", "has_condition", "has_condition_from", "visible_to", "has_any_component", "immune_to"}
ATTRS = {
    "size", "temp_hp", "team", "willing", "immune_to", "bloodied",
    "has_status_from", "has_condition", "has_condition_from", "alignment", "creature_type", "actual_creature_type", "hp", "max_hp", "next_turn", "this_turn", "index",
    "cast_turn", "elapsed_minutes", "caster", "spell", "target",
    "target_dropped_to_zero", "drop_turn", "has_status", "visible_to",
    "has_any_component", "advantage", "critical", "total", "natural", "weapon", "melee",
}
TOKEN = re.compile(r'\s*(?:(\d+(?:\.\d+)?)|(\$?[A-Za-z_][A-Za-z_0-9]*)|("[^"\\]*"|\x27[^\x27\\]*\x27)|(==|!=|>=|<=|[<>()\[\],.]))')


class ExpressionError(ValueError):
    pass


class Parser:
    def __init__(self, source: str):
        self.tokens = []
        pos = 0
        while pos < len(source):
            if not source[pos:].strip():
                break
            match = TOKEN.match(source, pos)
            if not match:
                raise ExpressionError(f"invalid token near {source[pos:]!r}")
            self.tokens.append(next(x for x in match.groups() if x is not None))
            pos = match.end()
        self.tokens.append("<end>")
        self.i = 0

    def take(self, value=None):
        item = self.tokens[self.i]
        if value is not None and item != value:
            raise ExpressionError(f"expected {value}, got {item}")
        self.i += 1
        return item

    def expression(self, precedence=0):
        token = self.take()
        if token == "not":
            node = ("not", self.expression(3))
        elif token == "(":
            node = self.expression()
            self.take(")")
        elif token == "[":
            node = ("list", self.arguments("]"))
        elif token[0] in "\"'":
            node = ("literal", token[1:-1])
        elif token[0].isdigit():
            node = ("literal", float(token) if "." in token else int(token))
        elif re.fullmatch(r"\$?[A-Za-z_][A-Za-z_0-9]*", token):
            if token.startswith("_"):
                raise ExpressionError("private names are forbidden")
            node = ("name", token)
        else:
            raise ExpressionError(f"unexpected {token}")
        while True:
            op = self.tokens[self.i]
            if op == ".":
                self.take()
                attr = self.take()
                if attr not in ATTRS:
                    raise ExpressionError(f"unknown attribute {attr}")
                node = ("attr", node, attr)
            elif op == "(":
                self.take()
                args = self.arguments(")")
                if node[0] == "name" and node[1] in EVENTS:
                    if len(args) != EVENTS[node[1]]:
                        raise ExpressionError(f"wrong arity for {node[1]}")
                elif node[0] == "attr" and node[2] in METHODS:
                    if len(args) != (3 if node[2] == "has_any_component" else 2 if node[2] in {"has_status_from", "has_condition_from"} else 1):
                        raise ExpressionError(f"wrong arity for {node[2]}")
                else:
                    raise ExpressionError("unknown function")
                node = ("call", node, args)
            elif op in {"or", "and", "==", "!=", "<", ">", ">=", "<=", "in"}:
                level = {"or": 1, "and": 2}.get(op, 3)
                if level <= precedence:
                    break
                self.take()
                node = (op, node, self.expression(level))
            else:
                break
        return node

    def arguments(self, end):
        args = []
        if self.tokens[self.i] != end:
            while True:
                args.append(self.expression())
                if self.tokens[self.i] != ",":
                    break
                self.take()
        self.take(end)
        return args


@lru_cache(maxsize=2048)
def parse(source: str):
    if not isinstance(source, str) or not source.strip():
        raise ExpressionError("expected nonempty expression")
    parser = Parser(source)
    node = parser.expression()
    parser.take("<end>")
    return node


def evaluate(source: str, context: dict):
    def visit(node):
        kind, *args = node
        if kind == "literal":
            return args[0]
        if kind == "name":
            name = args[0]
            if name in {"true", "false", "null"}:
                return {"true": True, "false": False, "null": None}[name]
            if name in EVENTS and context.get("_subscription"):
                return context.get("_event", lambda *a: False)(name, [])
            return context.get(name, name)
        if kind == "list":
            return [visit(x) for x in args[0]]
        if kind == "attr":
            obj = visit(args[0])
            if args[1] == "actual_creature_type": return getattr(obj, "creature_type", None)
            if args[1] == "creature_type" and context.get("_magical") and hasattr(obj, "magical_type"):
                return obj.magical_type
            if isinstance(obj, dict):
                return obj.get(args[1])
            return getattr(obj, args[1], None) if obj is not None else None
        if kind == "call":
            func, parameters = args
            values = [visit(x) for x in parameters]
            if func[0] == "name":
                return context.get("_event", lambda *a: False)(func[1], values)
            obj = visit(func[1])
            method = func[2]
            if method == "has_status":
                return obj is not None and obj.has_status(values[0])
            if method in {"has_status_from", "has_condition_from"}:
                return obj is not None and getattr(obj, method)(*values)
            if method == "immune_to":
                return obj is not None and obj.immune_to(values[0])
            if method == "has_condition":
                return obj is not None and obj.has_condition(values[0])
            if method == "visible_to":
                return obj is not None and obj.visible_to(values[0])
            components = obj.get("components", {}) if isinstance(obj, dict) else {}
            return any(bool(components.get(x)) for x in values)
        if kind == "not":
            return not visit(args[0])
        if kind == "or":
            return visit(args[0]) or visit(args[1])
        if kind == "and":
            return visit(args[0]) and visit(args[1])
        a, b = visit(args[0]), visit(args[1])
        if kind == "==": return a == b
        if kind == "!=": return a != b
        if kind == "in": return a in b
        if a is None or b is None: return False
        if kind == "<": return a < b
        if kind == ">": return a > b
        if kind == ">=": return a >= b
        if kind == "<=": return a <= b
        raise ExpressionError(f"unknown operator {kind}")
    return visit(parse(source))
