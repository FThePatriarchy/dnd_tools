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
    expires_at: float | None = None
    requires_condition: str | None = None


@dataclass(eq=False)
class Combatant:
    id: str
    name: str = "Dummy"
    team: str = "enemy"
    max_hp: int = 100
    base_max_hp: int = field(init=False)
    hp: int | None = None
    temp_hp: int = 0
    spell_hp_bonus: int = 0
    transform_snapshot: dict | None = None
    effective_transform: Effect | None = None
    ac: int = 10
    abilities: dict[str, int] = field(default_factory=lambda: dict.fromkeys(("str", "dex", "con", "int", "wis", "cha"), 10))
    save_proficiencies: list[str] = field(default_factory=list)
    save_bonuses: dict[str, int] = field(default_factory=dict)
    proficiency_bonus: int = 2
    spell_ability: str = "wis"
    spell_dc: int = 13
    spell_attack_bonus: int = 5
    level: int = 1
    cr: str | None = None
    speed: int = 30
    movement_modes: dict = field(default_factory=dict)
    resistances: list[str] = field(default_factory=list)
    immunities: list[str] = field(default_factory=list)
    vulnerabilities: list[str] = field(default_factory=list)
    condition_immunities: list[str] = field(default_factory=list)
    conditions: set[str] = field(default_factory=set)
    exhaustion_level: int = 0
    original_max_hp: int | None = None
    original_abilities: dict = field(default_factory=dict)
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
    spell_recharge: dict[str, int] = field(default_factory=dict)
    spell_components: dict[str, dict] = field(default_factory=dict)
    summoner_id: str | None = None
    summoned_source: int | None = None
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
    blocked_economy: dict[str, int] = field(default_factory=dict)
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
        self.base_max_hp -= self.spell_hp_bonus
        if self.hp is None: self.hp = self.max_hp
        self.abilities = {**dict.fromkeys(("str", "dex", "con", "int", "wis", "cha"), 10), **self.abilities}
        if self.original_max_hp is None: self.original_max_hp = self.base_max_hp
        if not self.original_abilities: self.original_abilities = self.abilities.copy()
        if not self.max_spell_slots: self.max_spell_slots = self.spell_slots.copy()
        if not self.max_limited_uses: self.max_limited_uses = self.limited_uses.copy()

    def _get_max_hp(self):
        return max(0, self.base_max_hp + self.spell_hp_bonus)

    def _set_max_hp(self, value):
        self.base_max_hp = value - self.spell_hp_bonus

    def _get_team(self):
        active = self.active_effects
        return next((e.data["control_team"] for e in reversed(active)
                     if "control_team" in e.data and (e.kind == "control" or
                         e.kind == "apply_condition" and self.condition_effective(e, active))), self.__dict__["team"])

    def _set_team(self, value):
        self.__dict__["team"] = value

    @property
    def alive(self):
        return self.hp > 0 and self.exhaustion_level < 6 and not self.removed and not self.permanently_removed

    def mod(self, ability: str) -> int:
        return (self.abilities[ability] - 10) // 2

    def immune_to(self, condition):
        return condition in self.condition_immunities or any(e.kind == "defense" and condition in e.data.get("condition_immunity", []) for e in self.active_effects)

    @property
    def spell_mod(self):
        return self.mod(self.spell_ability)

    @property
    def magical_type(self):
        return next((e.data["type"] for e in reversed(self.active_effects) if e.kind == "type_mask"), self.creature_type)

    @property
    def active_effects(self):
        active = [e for e in self.effects if not e.suppressed]
        effective = [e for e in active if not e.requires_condition]
        pending = [e for e in active if e.requires_condition]
        if not pending: return active
        while pending:
            ready = [e for e in pending if self.has_condition_source(e.requires_condition, e.source, effective)]
            if not ready: break
            effective.extend(ready)
            pending = [e for e in pending if e not in ready]
        return [e for e in active if e in effective]

    def has_condition_source(self, name, source, active=None):
        active = self.active_effects if active is None else active
        return any(e.kind == "apply_condition" and e.source == source and e.data["condition"] == name
                   and self.condition_effective(e, active) for e in active)

    def condition_effective(self, effect, active):
        condition = effect.data["condition"]
        if condition in self.condition_immunities: return False
        for defense in active:
            if defense.kind == "defense" and (condition in defense.data.get("condition_immunity", []) or
                    effect.data.get("magical") and condition in defense.data.get("magical_condition_immunity", [])): return False
            if defense.kind == "ward" and defense.data.get("suppress_existing") and condition in defense.data.get("conditions", []) and effect.data.get("source_type") in defense.data["types"]: return False
        return True

    def has_condition(self, condition: str) -> bool:
        if condition == "invisible" and self.has_status("invisibility_suppressed"): return False
        if condition == "exhaustion" and self.exhaustion_level > 0: return True
        if not self.effects:
            return condition in self.conditions or condition == "incapacitated" and bool(self.conditions & {"paralyzed", "stunned", "unconscious", "petrified"})
        active = self.active_effects
        defenses = [e.data for e in active if e.kind == "defense"]
        immune = any(condition in d.get("condition_immunity", []) for d in defenses)
        magical_immune = any(condition in d.get("magical_condition_immunity", []) for d in defenses)
        if condition in self.conditions and not immune: return True
        if not immune:
            for e in active:
                if e.kind != "apply_condition" or e.data["condition"] != condition or magical_immune and e.data.get("magical"): continue
                if self.condition_effective(e, active): return True
        return condition == "incapacitated" and any(self.has_condition(x) for x in ("paralyzed", "stunned", "unconscious", "petrified"))

    def status_effects(self, name):
        active = self.active_effects
        return [e for e in active if e.kind == "status" and e.data["id"] == name
                and (not e.data["data"].get("requires_condition") or any(
                    c.kind == "apply_condition" and c.source == e.source
                    and c.data["condition"] == e.data["data"]["requires_condition"] and self.condition_effective(c, active) for c in active))]

    def has_status(self, name: str) -> bool:
        return name in self.statuses or bool(self.status_effects(name))

    def has_status_from(self, name, other) -> bool:
        return any(e.data.get("caster_id") == other.id for e in self.status_effects(name))

    def has_condition_from(self, name, other) -> bool:
        if isinstance(other, SpellInstance): return self.has_condition_source(name, other.id)
        return any(e.kind == "apply_condition" and e.data["condition"] == name and e.data.get("caster_id") == other.id and self.condition_effective(e, self.active_effects) for e in self.active_effects)

    def visible_to(self, other) -> bool:
        return self.visible and (not self.has_condition("invisible") or other.has_status("see_invisible")) and not other.has_condition("blinded")

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


# Install after dataclass captures constructor defaults. Assignments update base
# values; reads expose effective allegiance and base-plus-bonus maximum HP.
Combatant.team = property(Combatant._get_team, Combatant._set_team)
Combatant.max_hp = property(Combatant._get_max_hp, Combatant._set_max_hp)


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
    affected: dict[str, set[Combatant]] = field(default_factory=dict)
    active: bool = True
    elapsed_minutes: float = 0
    summoned: list[Combatant] = field(default_factory=list)
    damage_total: int = 0
    limits_count: dict = field(default_factory=dict)
    maintained_turn: int = 0

    @property
    def target(self):
        bindings = [b.target for b in self.bindings.values() if b.targets]
        return bindings[0] if bindings else None
