"""Mutable state owned by one simulation; no module-global RNG or counters."""
from dataclasses import dataclass, field
from copy import deepcopy


@dataclass(eq=False)
class Effect:
    kind: str
    data: dict
    source: int
    block: str
    until: tuple[str, str, int] | None = None
    uses: int | None = None
    suppressed: bool = False


@dataclass(eq=False)
class Combatant:
    id: str
    name: str = "Dummy"
    team: str = "enemy"
    max_hp: int = 100
    hp: int | None = None
    temp_hp: int = 0
    ac: int = 10
    abilities: dict[str, int] = field(default_factory=lambda: dict.fromkeys(("str", "dex", "con", "int", "wis", "cha"), 10))
    save_proficiencies: list[str] = field(default_factory=list)
    save_bonuses: dict[str, int] = field(default_factory=dict)
    proficiency_bonus: int = 2
    spell_ability: str = "wis"
    spell_dc: int = 13
    spell_attack_bonus: int = 5
    level: int = 1
    speed: int = 30
    movement_modes: dict = field(default_factory=dict)
    resistances: list[str] = field(default_factory=list)
    immunities: list[str] = field(default_factory=list)
    vulnerabilities: list[str] = field(default_factory=list)
    condition_immunities: list[str] = field(default_factory=list)
    conditions: set[str] = field(default_factory=set)
    exhaustion_level: int = 0
    effects: list[Effect] = field(default_factory=list)
    statuses: dict[str, dict] = field(default_factory=dict)
    concentration: int | None = None
    spell_slots: dict[int, int] = field(default_factory=dict)
    limited_uses: dict[str, int] = field(default_factory=dict)
    max_spell_slots: dict[int, int] = field(default_factory=dict)
    max_limited_uses: dict[str, int] = field(default_factory=dict)
    resource_recovery: dict[str, dict] = field(default_factory=dict)
    hit_die: str | None = None
    hit_dice: int = 0
    max_hit_dice: int = 0
    downs: int = 0
    spells: list[str] = field(default_factory=list)
    innate_spells: dict[str, int] = field(default_factory=dict)
    attacks: list[dict] = field(default_factory=list)
    features: dict = field(default_factory=dict)
    size: str = "M"
    routines: list[list[str]] = field(default_factory=list)
    replacements: list[str] = field(default_factory=list)
    legendary: dict = field(default_factory=dict)
    legendary_remaining: int = 0
    legendary_used: set[str] = field(default_factory=set)
    spell_resources: dict[str, str] = field(default_factory=dict)
    spell_levels: dict[str, int] = field(default_factory=dict)
    spell_costs: dict[str, str] = field(default_factory=dict)
    multiattack: list[str] = field(default_factory=list)
    extra_attack: int = 1
    actions: list[dict] = field(default_factory=list)
    traits: list[dict] = field(default_factory=list)
    recharge_ready: dict[str, bool] = field(default_factory=dict)
    creature_type: str = "humanoid"
    alignment: str = "neutral"
    visible: bool = True
    willing: bool = True
    removed: bool = False
    permanently_removed: bool = False
    action: int = 1
    bonus_action: int = 1
    reaction: int = 1
    extra_actions: list[dict] = field(default_factory=list)
    action_grants: set[tuple] = field(default_factory=set)
    surge_actions: int = 0
    slot_cast_turn: int | None = None
    turns_taken: int = 0
    initiative_bonus: int = 0
    resources_spent: dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if self.hp is None: self.hp = self.max_hp
        self.abilities = {**dict.fromkeys(("str", "dex", "con", "int", "wis", "cha"), 10), **self.abilities}
        if not self.max_spell_slots: self.max_spell_slots = self.spell_slots.copy()
        if not self.max_limited_uses: self.max_limited_uses = self.limited_uses.copy()

    @property
    def alive(self):
        return self.hp > 0 and self.exhaustion_level < 6 and not self.removed and not self.permanently_removed

    def mod(self, ability: str) -> int:
        return (self.abilities[ability] - 10) // 2

    @property
    def spell_mod(self):
        return self.mod(self.spell_ability)

    @property
    def active_effects(self):
        return [e for e in self.effects if not e.suppressed]

    def has_condition(self, condition: str) -> bool:
        if condition == "exhaustion" and self.exhaustion_level > 0: return True
        if condition in self.conditions or any(e.kind == "apply_condition" and e.data["condition"] == condition for e in self.active_effects):
            return True
        if condition == "incapacitated":
            return any(self.has_condition(x) for x in ("paralyzed", "stunned", "unconscious", "petrified"))
        return False

    def status_effects(self, name):
        active = self.active_effects
        return [e for e in active if e.kind == "status" and e.data["id"] == name
                and (not e.data["data"].get("requires_condition") or any(
                    c.kind == "apply_condition" and c.source == e.source
                    and c.data["condition"] == e.data["data"]["requires_condition"] for c in active))]

    def has_status(self, name: str) -> bool:
        return name in self.statuses or bool(self.status_effects(name))

    def has_status_from(self, name, other) -> bool:
        return any(e.data.get("caster_id") == other.id for e in self.status_effects(name))

    def has_condition_from(self, name, other) -> bool:
        return any(e.kind == "apply_condition" and e.data["condition"] == name and e.data.get("caster_id") == other.id for e in self.active_effects)

    def visible_to(self, other) -> bool:
        return self.visible and not self.has_condition("invisible") and not other.has_condition("blinded")

    def spend(self, resource: str, n=1):
        self.resources_spent[resource] = self.resources_spent.get(resource, 0) + n

    @classmethod
    def from_sheet(cls, sheet: dict, identifier: str, team: str):
        fields = cls.__dataclass_fields__
        data = {k: deepcopy(v) for k, v in sheet.items() if k in fields and k not in {"id", "team"}}
        if "hit_dice" in sheet:
            data["hit_die"] = sheet["hit_dice"]["die"]
            data["hit_dice"] = data["max_hit_dice"] = sheet["hit_dice"]["count"]
        data["limited_uses"] = {}
        data["resource_recovery"] = {}
        for name, value in sheet.get("limited_uses", {}).items():
            entry = value if isinstance(value, dict) else {"max": value, "long_rest": "all"}
            data["limited_uses"][name] = entry["max"]
            data["resource_recovery"][name] = {k: entry.get(k, 0) for k in ("short_rest", "long_rest")}
        return cls(id=identifier, team=team, **data)


@dataclass
class Binding:
    targets: list[Combatant] = field(default_factory=list)
    target_dropped_to_zero: bool = False
    drop_turn: int = -1

    @property
    def target(self):
        return self.targets[0] if len(self.targets) == 1 else self.targets


@dataclass
class SpellInstance:
    id: int
    spec: dict
    caster: Combatant
    slot: int
    cast_turn: int
    cast_round: int
    choices: dict = field(default_factory=dict)
    bindings: dict[str, Binding] = field(default_factory=dict)
    end_callbacks: list[tuple[Combatant, list[dict]]] = field(default_factory=list)
    limits: set[tuple] = field(default_factory=set)
    ends: list[tuple[str, str, int]] = field(default_factory=list)
    exclusions: set[str] = field(default_factory=set)
    area_members: dict[str, list[Combatant]] = field(default_factory=dict)
    active: bool = True
    elapsed_minutes: float = 0

    @property
    def target(self):
        bindings = [b.target for b in self.bindings.values() if b.targets]
        return bindings[0] if bindings else None
