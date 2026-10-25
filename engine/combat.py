"""Event-driven resolution. The engine never imports the old extraction pipeline."""
from collections import Counter, defaultdict
from types import SimpleNamespace
import random

from . import dice
from .expressions import evaluate, parse
from .loader import scaled_spell
from .policy import Policy, area_heuristic, grab_cap
from .state import Combatant, Effect, Binding, SpellInstance, compare_deadline

INSTANT_PRIMITIVES = {"damage", "heal", "heal_pool", "temp_hp", "hit_dice_heal", "restore", "remove_condition", "spend_reaction", "stabilize", "dispel", "end_spell", "end_concentration", "maintain_spell"}

MOVEMENT_EVENTS = {"on_aura_moves_onto_creature", "on_creature_enters_aura"}


from .monster_mechanics import MonsterMechanics
from .spell_mechanics import SpellMechanics
from .weapon_spells import WeaponSpells
from .class_mechanics import ClassMechanics
from .day_mechanics import DayMechanics


class Combat(MonsterMechanics, SpellMechanics, WeaponSpells, ClassMechanics, DayMechanics):
    def __init__(self, combatants: list[Combatant], spells: dict, seed=1, policy=None, area=None, monster_policy=None, target_cap=None):
        if len({c.id for c in combatants}) != len(combatants):
            raise ValueError("combatant ids must be unique")
        self.combatants = combatants
        self.spells = spells
        self.rng = random.Random(seed)
        self.policy = policy or Policy()
        self.monster_policy = monster_policy
        self.area = area or area_heuristic
        self.target_cap = target_cap or grab_cap
        self.instances: dict[int, SpellInstance] = {}
        self.next_instance = 1
        self.turn_index = 0
        self.round = 1
        self.time_rounds = 0.0
        self.current: Combatant | None = None
        self.log: list[dict] = []
        self.record_log = True
        self._damage_batch = None
        self._has_damage_controls = False
        self.death_rules = False
        self.damage_dealt = Counter()
        self.initialize_monsters()

    def policy_for(self, actor):
        return self.monster_policy if actor.team != "party" and self.monster_policy is not None else self.policy

    def record(self, kind, **data):
        if self.record_log: self.log.append({"event": kind, "turn": self.turn_index, **data})

    def enemies(self, actor):
        return [x for x in self.combatants if self.targetable(x, actor) and x.team != actor.team]

    def targetable(self, target, attacker=None):
        return (target.alive or self.regenerating_target(target) or
                self.death_rules and target.team == "party" and not target.dead and not target.removed and not target.permanently_removed)

    def regenerating_target(self, actor):
        # A downed regenerator remains a threat and a legal finishing target.
        return actor.hp == 0 and actor.features.get("regeneration",{}).get("at_zero",False) and not actor.has_status("regeneration_blocked") and not actor.removed and not actor.permanently_removed

    def spell_potency(self, instance):
        # Compare numerical effect strength, not duration or number of targets.
        strength = 0
        for block in instance.spec["effects"]:
            branches = []
            for branch in ("apply", "on_hit", "on_fail", "on_success"):
                total = 0
                for primitive in block[branch]:
                    for kind in ("damage", "heal", "modify", "temp_hp", "max_hp"):
                        if kind not in primitive: continue
                        # A past instantaneous hit does not strengthen a lingering benefit.
                        if kind in {"damage", "heal"} and block["event"] == "on_cast": continue
                        value = primitive[kind]
                        if "dice" in value:
                            bonus = value.get("bonus", 0)
                            amount = dice.mean(value["dice"]) + (instance.caster.spell_mod if bonus == "spell_mod" else bonus)
                        else:
                            amount = value.get("value", value.get("amount", 0))
                            if amount == "spell_mod": amount = instance.caster.spell_mod
                            elif isinstance(amount, str): amount = dice.mean(amount)
                            if value.get("op") == "mul": amount -= 1
                        total += abs(amount)
                branches.append(total)
            strength += max(branches)
        return strength, instance.id

    def spell_applies(self, instance, target, event="while_in_area", frame=None):
        if "level" not in instance.spec or instance.spec["duration"]["type"] == "instant": return True
        candidates = [instance]
        for other in self.instances.values():
            if other is instance or not other.active or other.spec["name"] != instance.spec["name"]: continue
            if "level" not in other.spec or other.spec["duration"]["type"] == "instant": continue
            area_overlap = any(
                target in other.area_members.get(block["id"], [])
                and ("if" not in block or evaluate(block["if"], self.context(other, target, event, frame, **(frame or {}))))
                for block in other.spec["effects"])
            if any(e.source == other.id for e in target.effects) or area_overlap:
                candidates.append(other)
        return max(candidates, key=self.spell_potency) is instance

    def refresh_spell_effects(self):
        for actor in self.combatants:
            for effect in actor.effects:
                instance = self.instances.get(effect.source)
                effect.suppressed = bool(instance and not self.spell_applies(instance, actor))
                if effect.source < 0 and abs(effect.source) in self.instances:
                    source = self.instances[abs(effect.source)]
                    candidates = [self.instances[abs(e.source)] for e in actor.effects if e.source < 0 and abs(e.source) in self.instances and self.instances[abs(e.source)].spec["name"] == source.spec["name"]]
                    effect.suppressed = max(candidates, key=self.spell_potency) is not source
            self.reconcile_transform(actor)
            bonus = sum(e.data["amount"] for e in actor.active_effects if e.kind == "max_hp")
            delta = bonus - actor.spell_hp_bonus
            actor.spell_hp_bonus = bonus
            if delta:
                actor.hp = 0 if actor.dead else max(0, min(actor.max_hp, actor.hp + delta))
                if actor.hp > 0:
                    actor.conditions.discard("unconscious")
                    actor.death_successes = actor.death_failures = 0
                    actor.stable_wake_at = None
                    actor.statuses.pop("stable",None)
                else: actor.conditions.add("unconscious")
        if self.current is not None:
            self.grant_current_actions(self.current)
            self.reconcile_economy(self.current)

    def grant_current_actions(self, actor):
        grants = {}
        for effect in actor.active_effects:
            if effect.kind != "grant_action": continue
            instance = self.instances.get(effect.source)
            origin = instance.spec["name"] if instance and "level" in instance.spec else effect.source
            grants[(origin, effect.block, effect.data["kind"])] = effect.data
        actor.extra_actions = [g for g in actor.extra_actions if g.get("_grant") in grants]
        for token, data in grants.items():
            if token in actor.action_grants: continue
            actor.action_grants.add(token)
            if data["kind"] == "action": actor.extra_actions.append({**data, "_grant": token})
            else: setattr(actor, data["kind"], getattr(actor, data["kind"]) + 1)

    def modifier(self, actor, stat, base=0, scope="all", *, against=None, consume=False):
        result = base
        scopes = {"all", *(scope if isinstance(scope, tuple) else (scope,))}
        effects = list(actor.active_effects)
        if against is not None:
            effects += [e for e in against.active_effects if e.kind == "modify" and e.data.get("recipient") == "any_attacker"]
        for effect in effects:
            if effect.kind != "modify" or effect.data["stat"] != stat or effect.data["scope"] not in scopes: continue
            if effect.data.get("recipient") == "any_attacker" and (against is None or effect not in against.effects): continue
            value = effect.data["value"]
            if isinstance(value, str): value = dice.roll(self.rng, value)
            op = effect.data["op"]
            if stat == "speed" and actor.has_status("magical_speed_protected") and effect.source in self.instances and "level" in self.instances[effect.source].spec:
                if op == "sub" and value > 0 or op == "add" and value < 0 or op == "mul" and value < 1 or op == "set" and value < result: continue
            if op == "add": result += value
            elif op == "sub": result -= value
            elif op == "mul": result *= value
            else: result = value
            if consume and effect.uses is not None:
                effect.uses -= 1
                if effect.uses == 0:
                    for c in self.combatants:
                        if effect in c.effects: c.effects.remove(effect)
        return result

    def armor_class(self, actor):
        bases = [actor.ac]
        for effect in actor.active_effects:
            if effect.kind == "base_ac" and not (effect.data["unarmored_only"] and actor.features.get("armored")):
                bases.append(effect.data["base"] + (actor.mod(effect.data["ability"]) if effect.data["ability"] else 0))
        return self.modifier(actor, "ac", max(bases))

    def turn_rules(self, actor):
        result = {}
        for effect in actor.active_effects:
            if effect.kind == "turn_rules": result.update(effect.data)
        return result

    def reconcile_economy(self, actor):
        # Prohibition is not expenditure: unspent budgets resume with the rider.
        rules = self.turn_rules(actor)
        for kind, flag in (("action", "no_action"), ("bonus_action", "no_bonus_action")):
            if rules.get(flag):
                actor.blocked_economy[kind] = actor.blocked_economy.get(kind, 0) + getattr(actor, kind)
                setattr(actor, kind, 0)
            elif kind in actor.blocked_economy:
                setattr(actor, kind, getattr(actor, kind) + actor.blocked_economy.pop(kind))

    def spend_economy(self, actor, kind):
        setattr(actor, kind, getattr(actor, kind) - 1)
        if kind in {"action", "bonus_action"} and self.turn_rules(actor).get("action_or_bonus"):
            actor.action = actor.bonus_action = 0

    def end_activity_effects(self, actor, effects=None):
        effects = list(actor.active_effects) if effects is None else effects
        for effect in effects:
            if not effect.data.get("ends_on_activity") or effect not in actor.effects: continue
            instance = self.instances.get(effect.source)
            if instance:
                self.remove_effects(instance, actor)
                if not any(e.source == instance.id for c in self.combatants for e in c.effects): self.end_spell(instance.id)

    def condition_sources(self, actor, condition):
        return [self.instances[e.source].caster for e in actor.active_effects
                if e.kind == "apply_condition" and e.data["condition"] == condition and e.source in self.instances and actor.condition_effective(e, actor.active_effects)]

    def exhaustion_penalty(self, actor):
        return 2 * max(actor.exhaustion_level, int(actor.has_condition("exhaustion")))

    def roll_flags(self, actor, on, scope="all", against=None, consume=False):
        advantage, disadvantage = self.monster_flags(actor, on, against)
        ca, cd = self.class_flags(actor, on, scope, against)
        advantage |= ca; disadvantage |= cd
        sa, sd = self.spell_roll_flags(actor, on, against)
        advantage |= sa; disadvantage |= sd
        effects = list(actor.active_effects)
        if on == "attack_rolls" and against is not None:
            effects += [e for e in against.active_effects if e.kind in {"advantage", "disadvantage"} and e.data.get("recipient") == "any_attacker"]
        for effect in effects:
            if effect.kind not in {"advantage", "disadvantage"} or effect.data["on"] != on or effect.data["scope"] not in {"all", scope}: continue
            if effect.data.get("recipient") == "any_attacker" and (against is None or effect not in against.effects): continue
            if effect.data.get("require_visible") and (against is None or not against.visible_to(actor)): continue
            if effect.kind == "advantage": advantage = True
            else: disadvantage = True
            if consume and effect.uses is not None:
                effect.uses -= 1
                if effect.uses == 0:
                    for c in self.combatants:
                        if effect in c.effects: c.effects.remove(effect)
        if consume: self.refresh_spell_effects()
        return advantage, disadvantage

    def saving_throw(self, target, ability, dc, ignore_cover=None, magical=False, conditions=(), concentration=False):
        if ability in {"str", "dex"} and any(target.has_condition(x) for x in ("paralyzed", "stunned", "unconscious", "petrified")):
            success = self.legendary_resist(target, ability, dc)
            self.record("save", target=target.id, ability=ability, success=success, automatic=True)
            return success
        advantage, disadvantage = self.roll_flags(target, "saves", ability)
        advantage |= any(e.kind == "ward" and e.data.get("existing_saves_advantage") and any(c.kind == "apply_condition" and c.data["condition"] in conditions and c.source in self.instances and self.instances[c.source].caster.creature_type in e.data["types"] for c in target.active_effects) for e in target.active_effects)
        advantage |= any(set(conditions) & set(e.data.get("save_conditions", [])) for e in target.active_effects if e.kind == "defense")
        if magical and (target.features.get("magic_resistance") or any(e.kind == "magic_saves" for e in target.active_effects)):
            advantage = True
            self.feature_log(target, "Magic Resistance")
        disadvantage |= ability == "dex" and target.has_condition("restrained")
        bonus = target.save_bonuses.get(ability, target.mod(ability) + (target.proficiency_bonus if ability in target.save_proficiencies else 0))
        natural = dice.d20(self.rng, advantage, disadvantage)
        bonus = self.modifier(target, "save", bonus, ability, consume=True)
        if concentration: bonus += self.modifier(target, "concentration_save", 0, ability)
        bonus -= self.exhaustion_penalty(target)
        natural = self.heroic_reroll(target, natural, lambda n: n + bonus >= dc)
        total = natural + bonus
        success, total, natural = self.class_failed_save(target, ability, dc, bonus, natural, total >= dc)
        # Sheets may use the same counter for monster Legendary Resistance.
        if not success: success = self.legendary_resist(target, ability, dc)
        self.record("save", target=target.id, ability=ability, total=total, dc=dc, success=success)
        return success

    def ability_check(self, target, ability, dc, skill=None):
        adv, dis = self.roll_flags(target, "ability_checks", ability)
        ca, _ = self.class_flags(target, "ability_checks", skill, None)
        adv |= ca
        dis |= target.has_condition("poisoned") or target.has_condition("frightened")
        natural = dice.d20(self.rng, adv, dis)
        reliable = skill in target.skill_proficiencies and target.features.get("reliable_talent")
        bonus = self.modifier(target, "ability_check", target.mod(ability), (ability, skill)) - self.exhaustion_penalty(target)
        if skill in target.skill_proficiencies: bonus += target.proficiency_bonus * (2 if skill in target.expertise else 1)
        natural = self.heroic_reroll(target, natural, lambda n: (max(10,n) if reliable else n) + bonus >= dc)
        if reliable: natural = max(10,natural)
        return self.class_check(target, ability, skill, natural, bonus, dc)

    def attack(self, attacker, defender, bonus, on_hit, melee=True, weapon=False, ability=None):
        if not attacker.alive or not self.targetable(defender, attacker) or attacker.has_condition("incapacitated") or self.turn_rules(attacker).get("no_attacks"): return False
        if defender in self.condition_sources(attacker, "charmed"): return False
        if self.isolation(attacker) != self.isolation(defender): return False
        if any(e.kind == "pacify" and e.source in self.instances and defender.team == self.instances[e.source].caster.team for e in attacker.active_effects): return False
        if not self.sanctuary_allows(attacker, defender): return False
        self.dispatch("on_attacked", who=defender, attacker=attacker, defender=defender)
        adv, dis = self.roll_flags(attacker, "attack_rolls", ability or "all", against=defender, consume=True)
        adv |= any(defender.has_condition(c) for c in ("paralyzed", "stunned", "unconscious", "blinded", "restrained"))
        adv |= attacker.has_condition("invisible") and not defender.has_condition("invisible") and not defender.has_status("see_invisible")
        dis |= any(attacker.has_condition(c) for c in ("blinded", "restrained", "poisoned", "frightened", "prone"))
        dis |= defender.has_condition("invisible") and not attacker.has_condition("invisible") and not attacker.has_status("see_invisible")
        grapplers = self.condition_sources(attacker, "grappled")
        dis |= bool(grapplers) and defender not in grapplers
        if defender.has_condition("prone"):
            if melee: adv = True
            else: dis = True
        self.duel_activity(attacker, defender)
        natural = dice.d20(self.rng, adv, dis)
        natural = self.heroic_reroll(attacker, natural, lambda n: n != 1 and (n >= (attacker.features.get("improved_critical",20) if weapon else 20) or n + bonus >= self.armor_class(defender)))
        total = natural + self.modifier(attacker, "attack_roll", bonus, against=defender, consume=True)
        total -= self.exhaustion_penalty(attacker)
        critical_roll = natural >= (attacker.features.get("improved_critical", 20) if weapon else 20)
        critical = critical_roll or (melee and any(defender.has_condition(c) for c in ("paralyzed", "unconscious")))
        attack = {"natural": natural, "total": total, "critical": critical, "advantage": adv and not dis, "disadvantage": dis and not adv, "weapon": weapon, "melee": melee}
        hit = natural != 1 and (critical_roll or total >= self.armor_class(defender))
        if hit:
            self.offer_reactions("on_attack_provisional_hit", attacker=attacker, defender=defender, who=defender, attack=attack)
            hit = natural != 1 and (critical_roll or total >= self.armor_class(defender))
            if hit and self.monster_reaction(attacker, defender, attack, melee): hit = False
        attack["hit"] = hit
        self.record("attack", attacker=attacker.id, defender=defender.id, **attack)
        if hit and self.mirror_intercepts(attacker, defender):
            self.end_activity_effects(attacker)
            return False
        if hit:
            previous = self._damage_batch
            self._damage_batch = []
            on_hit(critical, attack)
            self.dispatch("on_attack_hit", attacker=attacker, defender=defender, attack=attack, critical=critical)
            batch = self._damage_batch
            self._damage_batch = previous
            old_critical = self._critical_damage
            self._critical_damage = critical
            self.flush_damage(batch, attack_context=(attacker, defender, attack))
            self._critical_damage = old_critical
        self.end_activity_effects(attacker)
        return hit

    def damage(self, target, amount, dtype, source=None, half=False, spell=None, hook=None):
        amount = max(0, int(amount))
        if self.isolation(target) != self.isolation(source): return 0
        if self._damage_batch is not None:
            self._damage_batch.append((target, amount, dtype, source, half, spell, hook))
            return amount
        if half: amount //= 2
        amount = self.mitigate_damage(target, amount, dtype, source)
        self.apply_damage(target, amount, source, {dtype} if amount else set())
        self.monster_drain(source, target, {dtype: amount})
        self.curse_extra(target, source, amount)
        if spell and hook: self.damage_hook(spell, hook, amount)
        return amount

    def mitigate_damage(self, target, amount, dtype, source):
        if dtype in target.immunities: amount = 0
        else:
            if any(e.kind == "defense" and dtype in e.data.get("immunity", []) for e in target.active_effects): amount = 0
            resisted = dtype in target.resistances or target.has_condition("petrified") or any(e.kind == "defense" and dtype in e.data.get("resistance", []) for e in target.active_effects)
            if resisted: amount //= 2
            if dtype in target.vulnerabilities or any(e.kind == "defense" and dtype in e.data.get("vulnerability", []) for e in target.active_effects): amount *= 2
        for e in target.active_effects:
            if e.kind == "reduce_damage":
                inst = self.instances.get(e.source)
                chosen = inst.choices[e.data["type"][1:]] if e.data["type"].startswith("$") else e.data["type"]
                if dtype == chosen and e.data.get("used_turn") != self.turn_index:
                    amount = max(0, amount - dice.roll(self.rng, e.data["dice"])); e.data["used_turn"] = self.turn_index
        self.monster_damage(target, amount, dtype)
        if amount > 0: self.interrupt_rest("damage", target)
        self.record("damage", target=target.id, amount=amount, type=dtype, source=source.id if source else None)
        return amount

    def flush_damage(self, batch, attack_context=None):
        components = defaultdict(int)
        sources = {}
        hooks = {}
        for target, amount, dtype, source, half, spell, hook in batch:
            components[target, dtype, half] += amount
            sources[target] = source
            if spell and hook: hooks[target, dtype] = spell, hook
        typed = defaultdict(int)
        for (target, dtype, half), amount in components.items():
            typed[target, dtype] += amount // 2 if half else amount
        self.uncanny_reduce(typed, attack_context)
        grouped = defaultdict(dict)
        for (target, dtype), amount in typed.items():
            grouped[target][dtype] = self.mitigate_damage(target, amount, dtype, sources[target])
        for target, values in grouped.items():
            self.apply_damage(target, sum(values.values()), sources[target], {k for k, v in values.items() if v})
            self.monster_drain(sources[target], target, values)
            self.curse_extra(target, sources[target], sum(values.values()))
            for dtype, amount in values.items():
                if (target, dtype) in hooks: self.damage_hook(*hooks[target, dtype], amount=amount)

    def apply_damage(self, target, amount, source=None, damage_types=None):
        if target.dead: return
        if amount: target.statuses.pop("stable", None)
        before = target.hp
        absorbed = min(target.temp_hp, amount)
        target.temp_hp -= absorbed
        target.hp = max(0, target.hp - (amount - absorbed))
        for e in list(target.active_effects):
            if before > 0 and target.hp == 0 and e.kind == "death_ward":
                target.hp = e.data["floor"]; self.end_spell(e.source)
        self.death_damage(target, before, amount, absorbed)
        if source is not None and source.team != target.team:
            self.damage_dealt[source.id] += min(before, max(0, amount - absorbed))
        for e in list(target.active_effects):
            if e.kind == "bond" and e.source in self.instances:
                caster = self.instances[e.source].caster
                if caster is not target: self.apply_damage(caster, amount, source, damage_types)
        if before > 0 and target.hp == 0 and target.features.get("undead_fortitude") and "radiant" not in (damage_types or set()) and not self._critical_damage:
            if self.saving_throw(target, "con", target.features["undead_fortitude"] + amount):
                target.hp = 1
                self.feature_log(target, "Undead Fortitude")
        if before > 0 and target.hp == 0:
            target.downs += 1
            target.conditions.update({"unconscious", "prone"})
            if target.summoned_source is not None:
                target.removed = True
                if target.has_status("force_object"): self.end_spell(target.summoned_source)
            for instance in self.instances.values():
                for binding in instance.bindings.values():
                    if target in binding.targets:
                        binding.target_dropped_to_zero = True
                        binding.drop_turn = self.turn_index
        if target.concentration is not None:
            if target.has_condition("incapacitated") or not target.alive:
                self.end_spell(target.concentration)
            elif amount and not self.saving_throw(target, "con", min(30, max(10, amount // 2)), concentration=True):
                self.end_spell(target.concentration)
        if amount:
            if source is not None: self.end_activity_effects(source)
            for effect in list(target.active_effects):
                inst = self.instances.get(effect.source)
                if effect.data.get("ends_on_damage") and inst:
                    if effect.data["ends_on_damage"] == "any" or source and source.team == inst.caster.team:
                        if effect.data.get("ends_spell"): self.end_spell(inst.id)
                        else: self.remove_effects(inst, target)
                if effect.data.get("repeat_on_damage") and inst:
                    bonus = Effect("advantage", {"on": "saves", "scope": "wis", "against": None}, 0, "damage_save") if effect.data.get("damage_save_advantage") else None
                    if bonus: target.effects.append(bonus)
                    if self.saving_throw(target, "wis", effect.data["save_dc"]): self.remove_effects(inst, target)
                    if bonus in target.effects: target.effects.remove(bonus)
            if self._has_damage_controls:
                for creature in self.combatants:
                    for effect in list(creature.active_effects):
                        inst = self.instances.get(effect.source)
                        if not inst: continue
                        if effect.kind == "duel" and creature is target and source and source is not inst.caster and source.team == inst.caster.team: self.end_spell(inst.id)
                        if effect.kind == "pacify" and effect.data.get("witness_allies") and target.team == creature.team and target.visible_to(creature): self.remove_effects(inst, creature)
            if source and any(self.spells.get(n, {}).get("reaction_trigger") == "on_damaged(caster)" for a in self.combatants for n in a.spells):
                self.offer_reactions("on_damaged", who=target, attacker=source, defender=target)
            else: self.dispatch("on_damaged", who=target, attacker=source, defender=target)
            for e in list(target.active_effects):
                if e.kind == "turn_rules" and e.data.get("end_at_zero") and target.hp == 0: self.remove_effects(self.instances[e.source],target)
            if target.summoned_source and target.statuses.get("summon_rules", {}).get("ends_on_damage"): self.end_spell(target.summoned_source)
            self.deplete_transform(target)
            for e in list(target.active_effects):
                if e.kind == "status" and e.data["id"] == "agathys" and not target.temp_hp: self.end_spell(e.source)
            for inst in list(self.instances.values()) if not target.alive else ():
                if inst.active and not inst.caster.alive and any(e.source == inst.id and e.kind == "bond" for c in self.combatants for e in c.active_effects): self.end_spell(inst.id)

    def heal(self, target, amount):
        if target.dead or target.has_status("healing_blocked"): return
        target.hp = min(target.max_hp, target.hp + max(0, int(amount)))
        if target.hp > 0:
            target.conditions.discard("unconscious")
            target.statuses.pop("stable", None)
            target.death_successes = target.death_failures = 0
            target.stable_wake_at = None

    def context(self, instance, target=None, event="on_cast", trigger=None, **extra):
        ctx = {"_magical": instance.magical, "caster": instance.caster, "target": target, "spell": instance,
               "turn": SimpleNamespace(index=self.turn_index), "event": event,
               "trigger": trigger or {}, **instance.bindings,
               **{"$" + k: (v.get(target.id, next(iter(v.values()), None)) if isinstance(v, dict) and target else v) for k, v in instance.choices.items()},
               **{k: v for k, v in extra.items() if k not in {"caster", "spell", "target", "event", "trigger"}}}
        return ctx

    def event_matches(self, expression, instance, event, frame):
        ctx = self.context(instance, event=event, trigger=frame, **{k: v for k, v in frame.items() if k != "trigger"})
        # In subscriptions only, bare event names mean event predicates.
        ctx["_subscription"] = True
        # A subscription's target is resolved by its block, not whichever block
        # happened to install the instance's first binding (mixed aura blocks).
        ctx["target"] = "target"
        def match(name, args):
            if name != event: return False
            if name == "end_of_turn_in_aura": return True  # membership is resolved per block
            if name in {"start_of_turn", "end_of_turn", "on_damaged", "on_attacked", "end_of_turn_in_aura"}:
                who = args[0]
                if who in ("target", "affected") or isinstance(who, list):
                    return frame.get("who") in [x for b in instance.bindings.values() for x in b.targets] or any(frame.get("who") in xs for xs in instance.area_members.values())
                if who == "any_enemy_in_area": return frame.get("who") in self.enemies(instance.caster)
                return who is frame.get("who")
            if name in {"on_attack_hit", "on_attack_provisional_hit"}:
                return all(a == "any" or a is frame.get(k) or (a == k) for a, k in zip(args, ("attacker", "defender")))
            if name == "on_spell_cast_nearby": return True  # no-grid range declaration
            if name == "on_spell_targeted":
                return args[0] in frame.get("targets", []) and args[1] == frame["spell"]["name"].lower().replace(" ", "_")
            return True
        ctx["_event"] = match
        return bool(evaluate(expression, ctx))

    def available_slot(self, actor, spec):
        if spec["name"] in actor.spell_resources:
            return actor.spell_levels.get(spec["name"], spec["level"]) if actor.limited_uses.get(actor.spell_resources[spec["name"]], 0) else None
        if spec["name"] in actor.spell_levels: return actor.spell_levels[spec["name"]]
        if spec["level"] == 0: return 0
        if spec["name"] in actor.innate_spells: return spec["level"] if actor.limited_uses.get(spec["name"], 0) > 0 else None
        slots = [n for n in sorted(actor.spell_slots) if n >= spec["level"] and actor.spell_slots[n] > 0]
        return self.policy_for(actor).slot(self, actor, spec, slots) if slots else None

    def can_cast(self, actor, name, slot=None):
        if name not in self.spells or name not in actor.spells or not actor.alive or actor.has_condition("incapacitated"): return False
        spec = self.spells[name]
        if not actor.recharge_ready.get(name, True): return False
        if (actor.has_status("engulfed") or actor.has_status("verbal_components_blocked")) and actor.spell_components.get(name, {}).get("v", spec["components"]["v"]): return False
        kind = actor.spell_costs.get(name, spec["casting_time"])
        rules = self.turn_rules(actor)
        if rules.get("no_spells"): return False
        if rules.get({"action": "no_action", "bonus_action": "no_bonus_action", "reaction": "no_reactions"}.get(kind)): return False
        if kind not in {"action", "bonus_action", "reaction"} or getattr(actor, kind) < 1: return False
        if kind == "action" and actor.action <= actor.surge_actions: return False
        if kind != "reaction" and self.current is not actor: return False
        innate = name in actor.innate_spells or name in actor.spell_resources or name in actor.spell_levels
        if spec["level"] and not innate and actor.slot_cast_turn == self.turn_index: return False
        available = self.available_slot(actor, spec) if slot is None else slot
        if available is None or available < spec["level"]: return False
        if innate and available != actor.spell_levels.get(name, spec["level"]): return False
        if not spec["level"]: return available == 0
        if name in actor.spell_resources: return actor.limited_uses.get(actor.spell_resources[name], 0) > 0
        if name in actor.spell_levels: return True
        return actor.limited_uses.get(name, 0) > 0 if innate else actor.spell_slots.get(available, 0) > 0

    def scale(self, actor, spec, slot, choices=None):
        result = scaled_spell(spec, slot or spec["level"], actor.level, choices)
        result = self.class_scale(actor, result)
        for component, present in actor.spell_components.get(spec["name"], {}).items():
            if not present:
                result["components"][component] = None if component == "m" else False
                if component == "m": result["components"].update(m_consumed=False, m_cost_gp=None)
        return result

    def cast(self, caster, name, targets=None, slot=None, choices=None, trigger=None):
        if not self.can_cast(caster, name, slot): return None
        if self.death_rules and name == "Revivify":
            targets = targets if targets is not None else [c for c in self.combatants if c.team == caster.team and self.can_revive(c)][:1]
            if len(targets) != 1 or targets[0] not in self.combatants or not self.can_revive(targets[0]):
                raise ValueError("Revivify requires one creature dead no longer than one minute")
        previous_activity = list(caster.active_effects)
        spec = self.spells[name]
        if spec.get("casting_trigger"):
            if not trigger or trigger.get("attacker") is not caster or not trigger.get("attack", {}).get("weapon"): return None
            if spec["casting_trigger"] == "melee_hit" and not trigger["attack"].get("melee"): return None
            targets = [trigger["defender"]]
        slot = self.available_slot(caster, spec) if slot is None else slot
        instance = SpellInstance(0, spec, caster, slot, self.turn_index, self.time_rounds)
        for choice in spec["choices"]:
            ctx = self.context(instance)
            options = [v for v in choice["options"] if v not in choice.get("option_conditions", {}) or evaluate(choice["option_conditions"][v], ctx)]
            selected = (choices or {}).get(choice["id"], self.policy_for(caster).choose(self, caster, choice, options) if options else None)
            legal = choice.get("per_target") and isinstance(selected, dict) and bool(selected) and all(x in options for x in selected.values())
            if not legal and selected not in options: raise ValueError(f"illegal choice {choice['id']}: {selected}")
            instance.choices[choice["id"]] = selected
        spec = self.scale(caster, spec, slot, instance.choices)
        instance.spec = spec
        instance.exclusions = {x.id for x in self.policy_for(caster).exemptions(self, caster)}
        # Reject explicit illegal input before spending anything or offering reactions.
        if targets is not None:
            for block in spec["effects"]:
                if block["target"]["select"] not in {"single", "n_targets"}: continue
                if not self.event_matches(block["event"], instance, "on_cast", trigger or {}): continue
                if "if" in block and not any(evaluate(block["if"], self.context(instance, target, trigger=trigger)) for target in targets): continue
                self.select_targets(instance, block, trigger or {}, targets)
        kind = caster.spell_costs.get(name, spec["casting_time"])
        if spec["level"]: self.interrupt_rest("spell", caster)
        self.spend_economy(caster, kind)
        if spec["concentration"] and caster.concentration is not None:
            self.end_spell(caster.concentration)
        # Ending self-Haste (or a reaction) can make this casting impossible.
        if caster.has_condition("incapacitated") or not caster.alive: return None
        pending = {"caster": caster, "spell": spec, "targets": targets or [], "cancelled": False}
        innate = name in caster.innate_spells or name in caster.spell_resources or name in caster.spell_levels
        instance.choices["_slot_expended"] = bool(slot and not innate)
        previous_slot_turn = caster.slot_cast_turn
        if innate:
            resource = caster.spell_resources.get(name, name)
            if resource in caster.limited_uses:
                caster.limited_uses[resource] -= 1
                caster.spend(resource)
        if name in caster.spell_recharge:
            caster.recharge_ready[name] = False
            caster.spend(name)
        if slot and not innate: caster.slot_cast_turn = self.turn_index
        pending = self.offer_reactions("on_spell_cast_nearby", **pending)
        if pending["cancelled"]:
            # Counterspell does not expend the interrupted spell's slot.
            if slot and not innate: caster.slot_cast_turn = previous_slot_turn
            self.record("countered", caster=caster.id, spell=name)
            return None
        if slot:
            if not innate:
                caster.spell_slots[slot] -= 1
                caster.spend(f"slot_{slot}")
        if caster.has_condition("incapacitated") or not caster.alive: return None
        failure = self.turn_rules(caster).get("somatic_failure_percent", 0)
        if spec["components"]["s"] and failure and self.rng.randint(1, 100) <= failure:
            self.record("spell_failed", caster=caster.id, spell=name, reason="somatic_failure")
            self.end_activity_effects(caster, previous_activity)
            return None
        instance.maintained_turn = caster.turns_taken
        instance.id = self.next_instance
        self.next_instance += 1
        self.instances[instance.id] = instance
        if spec.get("recast_ends_previous"):
            for old in self.instances.values():
                if old is not instance and old.caster is caster and old.spec["name"] == name:
                    for spirit in old.summoned: spirit.removed = True
            for previous in list(self.instances.values()):
                if previous is not instance and previous.active and previous.caster is caster and previous.spec["name"] == name:
                    self.end_spell(previous.id)
        if spec["concentration"]: caster.concentration = instance.id
        instance.ends = [self.boundary(x, instance, caster) for x in spec["ends_on"]]
        if spec["range"]["type"] == "self" and spec["duration"]["type"] != "instant":
            instance.affected["_owner"] = {caster}
        self.record("cast", caster=caster.id, spell=name, slot=slot)
        for block in spec["effects"]:
            if self.event_matches(block["event"], instance, "on_cast", trigger or {}):
                self.resolve_block(instance, block, "on_cast", trigger or {}, targets)
        self.refresh_areas(instance)
        if instance.choices.get("_healed_other") and instance.choices.get("_slot_expended") and caster.features.get("blessed_healer"):
            self.heal(caster, 2 + slot)
            self.feature_log(caster, "Blessed Healer", amount=2 + slot)
        if spec["duration"]["type"] == "instant":
            for creature in self.combatants:
                for effect in creature.effects:
                    if effect.source == instance.id and (effect.until or effect.expires_at is not None): effect.source = -instance.id
            self.end_spell(instance.id)
        self.end_activity_effects(caster, previous_activity)
        if self.death_rules and name == "Revivify": self.revive(caster, targets[0])
        return instance

    def prepare(self, caster, name, targets=None, slot=None, choices=None):
        """Complete explicitly uninterrupted, out-of-turn preparation.

        This is not a policy option during a fight or a shortcut in can_cast.
        The caller supplies the safe preparation interval, like a rest interval.
        """
        if self.current is not None: raise ValueError("preparation requires an out-of-turn interval")
        spec = self.spells[name]
        if spec["casting_time"] not in {"minute", "minutes", "hour", "hours"}: raise ValueError("not a long casting")
        if not caster.alive or caster.has_condition("incapacitated"): return None
        if spec["level"]: self.interrupt_rest("spell", caster)
        if caster.concentration is not None: self.end_spell(caster.concentration)
        elapsed = spec.get("casting_time_n", 1) * (600 if spec["casting_time"].startswith("hour") else 10)
        self.time_rounds += elapsed
        old_cost = caster.spell_costs.get(name)
        caster.spell_costs[name] = "action"
        self.begin_turn(caster)
        try:
            result = self.cast(caster, name, targets, slot, choices)
            self.record("preparation", caster=caster.id, spell=name, rounds=elapsed)
            return result
        finally:
            if old_cost is None: caster.spell_costs.pop(name, None)
            else: caster.spell_costs[name] = old_cost
            self.current = None

    def offer_reactions(self, event, **frame):
        # Shared pending frame: a nested Counterspell sets cancelled on this object.
        self.dispatch(event, **frame)
        for actor in self.combatants:
            for name in actor.spells:
                spec = self.spells.get(name)
                if not spec or spec["casting_time"] != "reaction" or not self.can_cast(actor, name): continue
                probe = SpellInstance(-1, spec, actor, spec["level"], self.turn_index, self.time_rounds)
                if not self.event_matches(spec["reaction_trigger"], probe, event, frame): continue
                if not self.policy_for(actor).reaction(self, actor, spec, frame): continue
                self.cast(actor, name, trigger=frame)
        return frame

    def eligible(self, instance, block):
        target = block["target"]
        caster = instance.caster
        binding = instance.bindings.get(block["id"], Binding())
        result = []
        # Per-block and per-caster facts, read once (nothing changes during the loop).
        caster_isolation = self.isolation(caster)
        healing = any("heal" in p or "heal_pool" in p or "stabilize" in p or "max_hp" in p for p in block["apply"])
        affects = target.get("affects", "any")
        caster_team = caster.team if affects in {"enemy", "enemies", "ally"} else None
        filters = target.get("filter", [])
        harmful = bool(block["on_hit"] or block["on_fail"] or any(k in p for p in block["apply"] for k in ("damage", "apply_condition", "remove_from_combat")))
        charmers = self.condition_sources(caster, "charmed") if harmful else ()
        pacified = {self.instances[e.source].caster.team for e in caster.active_effects
                    if e.kind == "pacify" and e.source in self.instances} if harmful else set()
        for creature in self.combatants:
            if creature.dead or creature.removed or creature.permanently_removed: continue
            if caster_isolation != self.isolation(creature) and instance.spec["name"] != "Dispel Magic": continue
            if not self.targetable(creature, caster) and not healing: continue
            if affects in {"enemy", "enemies"} and creature.team == caster_team: continue
            if affects == "ally" and creature.team != caster_team: continue
            if harmful and creature in charmers: continue
            if harmful and pacified and creature.team in pacified: continue
            treated_type = creature.magical_type if instance.magical else creature.creature_type
            if "humanoid" in filters and treated_type != "humanoid": continue
            if "creature" in filters and creature.creature_type == "object": continue
            if "object" in filters and creature.creature_type != "object": continue
            if "visible" in filters and not creature.visible_to(caster): continue
            if "willing" in filters and not creature.willing: continue
            if "new_target" in filters and creature in binding.targets: continue
            if target.get("shape") == "emanation" and creature is caster and not target.get("include_caster"): continue
            if target.get("exclude") == "origin" and creature in instance.bindings.get(target.get("origin"), Binding()).targets: continue
            if target.get("exclude") == "caster" and creature is caster: continue
            if target.get("origin") == "caster" and target.get("shape") in {"cone", "line"} and creature is caster: continue
            if target.get("exclude") == "designated_on_cast" and creature.id in instance.exclusions: continue
            if target.get("exclude") == "summoner" and creature.id == caster.summoner_id: continue
            if "max_size" in target and "TSMLHG".index(creature.size) > "TSMLHG".index(target["max_size"]): continue
            if "eligible_if" in target and not evaluate(target["eligible_if"], self.context(instance, creature)): continue
            result.append(creature)
        return result

    def select_targets(self, instance, block, frame, explicit=None):
        target = block["target"]
        kind = target["select"]
        if kind == "self": return [instance.caster]
        if kind == "ref":
            ref = target["ref"]
            if ref in {"trigger.attacker", "trigger.defender"}:
                who = frame.get(ref.split(".")[1])
                return [who] if who else []
            if ref == "trigger.caster": return [frame["caster"]]
            if ref == "spell_target":
                value = instance.target
                return value if isinstance(value, list) else [value] if value else []
            members = instance.bindings.get(ref, Binding()).targets[:]
            if block["event"] in {"start_of_turn(target)", "end_of_turn(target)", "start_of_turn(affected)", "end_of_turn(affected)"}:
                return [frame["who"]] if frame.get("who") in members else []
            return members
        eligible = self.eligible(instance, block)
        if kind == "area":
            cached = instance.area_members.get(block["id"])
            members = [c for c in cached if c in eligible] if cached is not None else self.area_members(instance, block, eligible)
            if frame.get("who") is not None and block["event"] not in {"start_of_turn(caster)", "end_of_turn(caster)"}: return [frame["who"]] if frame["who"] in members else []
            return members
        n = len(eligible) if target.get("n") == "all" else target.get("n", 1)
        # May lower an n_targets count; the default caps no-grid multi-target grabs.
        if kind == "n_targets" and self.target_cap is not None: n = min(n, self.target_cap(instance, block, n, eligible))
        selected =list(explicit) if explicit is not None else self.policy_for(instance.caster).targets(self, instance, block, eligible, n)
        if len(selected) > n or (target.get("distinct", True) and len({c.id for c in selected}) != len(selected)):
            raise ValueError(f"invalid selection count/distinctness for {block['id']}")
        minimum = target.get("min", 0) if target.get("up_to") else n
        # Fewer legal distinct creatures than n is not an invented target.
        minimum = min(minimum, len(eligible)) if target.get("distinct", True) else minimum
        if len(selected) < minimum or any(x not in eligible for x in selected):
            raise ValueError(f"illegal target selection for {block['id']}")
        return selected

    def area_members(self, instance, block, eligible):
        target = block["target"]
        hostile = bool(block["on_fail"] or block["on_hit"] or any(
            k in p for p in block["apply"] for k in ("damage", "apply_condition", "turn_rules", "remove_from_combat")))
        fixed_emanation = target.get("origin", "caster") == "caster" and target["shape"] == "emanation"
        # Custom heuristics opt in to the default's ally avoidance and caster context.
        if (self.area is area_heuristic or getattr(self.area, "avoids_allies", False)) and hostile and not fixed_emanation:
            # Freely placed hostile areas do not fill spare capacity with allies.
            eligible = [c for c in eligible if c.team != instance.caster.team or
                        c in instance.bindings.get(target.get("origin"), Binding()).targets]
        context = {"caster": instance.caster} if getattr(self.area, "wants_caster", False) else {}
        count = self.area(target["shape"], target["size_ft"], len(eligible), **context)
        if isinstance(count, int):
            if not 0 <= count <= len(eligible): raise ValueError("area heuristic returned invalid count")
            # Policy determines placement/order; it does not change legal allegiance.
            ordered = self.policy_for(instance.caster).targets(self, instance, block, eligible, len(eligible))
            # Custom counts/indices can explicitly model spill-over into allies.
            if target["affects"] != "chosen": ordered += [x for x in eligible if x not in ordered]
            if target.get("origin") in instance.bindings:
                origins = [c for c in instance.bindings[target["origin"]].targets if c in eligible]
                ordered = origins + [c for c in ordered if c not in origins]
            return ordered[:count]
        indices = list(count)
        if len(set(indices)) != len(indices) or any(type(i) is not int or not 0 <= i < len(eligible) for i in indices): raise ValueError("invalid area indices")
        return [eligible[i] for i in indices]

    def resolve_block(self, instance, block, event, frame, explicit=None):
        if not instance.active: return False
        if block.get("after_damage") and self._damage_batch:
            batch = self._damage_batch; self._damage_batch = None
            self.flush_damage(batch); self._damage_batch = []
        if block.get("optional") and not self.policy_for(instance.caster).optional(self, instance, block): return False
        targets = self.select_targets(instance, block, frame, explicit)
        if block.get("requires_condition"):
            targets = [t for t in targets if t.has_condition_source(block["requires_condition"], instance.id)]
        if "if" in block:
            targets = [t for t in targets if evaluate(block["if"], self.context(instance, t, event, frame, **frame))]
        if not targets: return False
        self.prepare_healing_pool(instance, block, targets)
        self.sculpt_targets(instance, block, targets)
        if block.get("cost"):
            actor = instance.caster
            if getattr(actor, block["cost"]) < 1 or actor.has_condition("incapacitated") or self.turn_rules(actor).get("no_reactions"): return False
            self.spend_economy(actor, block["cost"])
        # Rebinding only persistent application blocks, not hit-event references.
        binding = instance.bindings.setdefault(block["id"], Binding())
        if block["target"]["select"] != "ref":
            if event.endswith("_command") and binding.targets:
                self.remove_effects(instance, block=block["id"])
            binding.targets = targets[:]
            if event.endswith("_command"):
                binding.target_dropped_to_zero = False
                binding.drop_turn = -1
        if instance.spec["name"] == "Magic Missile":
            self.offer_reactions("on_spell_targeted", caster=instance.caster, spell=instance.spec, targets=targets)
        # A save resolution is simultaneous; later dispatches/attacks get fresh rolls.
        shared = {} if block.get("damage_roll") == "shared" or block["save"] and not block["attack"] else None
        deferred = [] if block.get("resolution") == "simultaneous" else None
        performed = False
        for target in targets:
            if not instance.active: break
            if block.get("admission") and not self.has_capacity(instance, target, block["admission"]): continue
            if "level" in instance.spec:
                for effect in list(target.active_effects):
                    if effect.source != instance.id and effect.data.get("ends_on_spell_targeted"):
                        self.end_spell(effect.source)
            ctx = self.context(instance, target, event, frame, **frame)
            if target.team != instance.caster.team: self.duel_activity(instance.caster, target)
            if block["target"]["select"] != "area" and not block["attack"] and any("damage" in p for branch in ("on_fail", "apply") for p in block[branch]) and not self.sanctuary_allows(instance.caster, target): continue
            if event not in {"on_cast", "while_in_area"} and not self.spell_applies(instance, target, event, frame): continue
            key = (block.get("limit_group", block["id"]), self.turn_index, target.id if block["limit"] == "once_per_turn_per_target" else None)
            if block["limit"] and key in instance.limits: continue
            if block["limit"]: instance.limits.add(key)
            if block.get("max_uses") is not None:
                used = instance.limits_count.get(block["id"], 0)
                if used >= block["max_uses"]: continue
                instance.limits_count[block["id"]] = used + 1
            performed = True
            self.record("effect_block", spell=instance.spec["name"], source=instance.id, block=block["id"], target=target.id, trigger=event)
            if block["attack"]:
                target = self.redirect_target(instance.caster, target)
                ctx = self.context(instance, target, event, frame, **frame)
                hit_result = self.attack(instance.caster, target, instance.caster.spell_attack_bonus,
                    lambda crit, attack, t=target, c=ctx: self.execute(instance, t, block["on_hit"], {**c, "attacker": instance.caster, "defender": t, "critical": crit, "attack": attack}, block["id"], shared=shared),
                    melee=block["attack"]["type"] == "melee_spell")
                if hit_result and any(p.get("damage", {}).get("leap_on_duplicate") for p in block["on_hit"]): self.orb_leap(instance, block, target)
                if not hit_result and block.get("on_miss"): self.execute(instance, target, block["on_miss"], ctx, block["id"])
            else:
                previous_batch = self._damage_batch
                self._damage_batch = []
                if block["save"] and ("if" not in block["save"] or evaluate(block["save"]["if"], ctx)):
                    save = block["save"]
                    auto_fail = "auto_fail_if" in save and evaluate(save["auto_fail_if"], ctx)
                    success_auto = "auto_success_if" in save and evaluate(save["auto_success_if"], ctx)
                    advantage_effect = None
                    if "advantage_if" in save and evaluate(save["advantage_if"], ctx):
                        advantage_effect = Effect("advantage", {"on": "saves", "scope": save["ability"], "against": None}, instance.id, block["id"])
                        target.effects.append(advantage_effect)
                    penalty = None
                    if "disadvantage_if" in save and evaluate(save["disadvantage_if"], ctx):
                        penalty = Effect("disadvantage", {"on": "saves", "scope": save["ability"], "against": None}, instance.id, block["id"])
                        target.effects.append(penalty)
                    sculpted = target.id in instance.choices.get("_sculpted", set())
                    if sculpted:
                        success = True
                        self.feature_log(instance.caster, "Sculpt Spells", target=target.id)
                    elif success_auto:
                        success = True
                        self.record("save", target=target.id, ability=save["ability"], success=True, automatic=True)
                    elif auto_fail:
                        success = self.legendary_resist(target, save["ability"], save.get("dc", instance.caster.spell_dc))
                        self.record("save", target=target.id, ability=save["ability"], success=success, automatic=True)
                    else:
                        causes = [p["apply_condition"]["condition"] for p in block["on_fail"] if "apply_condition" in p]
                        success = self.saving_throw(target, save["ability"], save.get("dc", instance.caster.spell_dc), save.get("ignore_cover"), magical=instance.magical, conditions=causes)
                    if penalty in target.effects: target.effects.remove(penalty)
                    if advantage_effect in target.effects: target.effects.remove(advantage_effect)
                    evasion = save["ability"] == "dex" and save["on_success"] == "half" and target.features.get("evasion") and not target.has_condition("incapacitated")
                    protected_save = save["on_success"] == "half" and any(e.kind == "magic_saves" for e in target.active_effects)
                    magic_protection = "level" in instance.spec and protected_save
                    magic_protection |= instance.spec.get("magical",False) and protected_save
                    if evasion: self.feature_log(target, "Evasion")
                    if not success:
                        self.sear_undead(instance, target)
                        self.execute(instance, target, block["on_fail"], ctx, block["id"], half=bool(evasion), shared=shared)
                        if evasion: self.execute(instance, target, [p for p in block["on_fail"] if "damage" not in p], ctx, block["id"], shared=shared)
                    else:
                        if save["on_success"] == "half" and not (evasion or magic_protection or sculpted): self.execute(instance, target, block["on_fail"], ctx, block["id"], half=True, shared=shared)
                        self.execute(instance, target, block["on_success"], ctx, block["id"], shared=shared)
                else:
                    primitives = block["apply"]
                    if block["save"] and not primitives: primitives = block["on_fail"]
                    self.execute(instance, target, primitives, ctx, block["id"], shared=shared)
                batch = self._damage_batch
                self._damage_batch = previous_batch
                if deferred is not None: deferred.append(batch)
                elif previous_batch is not None: previous_batch.extend(batch)
                else: self.flush_damage(batch)
        if deferred is not None:
            # All darts roll before damage; each dart remains its own instance.
            for batch in deferred: self.flush_damage(batch)
        if performed and (block.get("end_after_resolution") or block.get("max_uses") is not None and instance.limits_count.get(block["id"], 0) >= block["max_uses"]): self.end_spell(instance.id)
        return performed

    def boundary(self, expression, instance, target):
        node = parse(expression)
        event = node[1][1]
        actor_name = node[2][0][1][1]
        actor = instance.caster if actor_name == "caster" else target
        return event, actor.id, actor.turns_taken + (1 if node[2][0][2] == "next_turn" else 0)

    def has_capacity(self, instance, target, value):
        def occupied(c):
            return c.has_status_from(value["status"], instance.caster) if "status" in value else c.has_condition_from(value["condition"], instance.caster)
        if not value.get("capacity") or occupied(target): return True
        occupants = [c for c in self.combatants if occupied(c)]
        def cost(c): return value.get("large_cost", 1) if c.size == "L" else 1
        return sum(cost(c) for c in occupants) + cost(target) <= value["capacity"]

    def ignite(self, target, source=None):
        # XPHB Burning is a single hazard, independent of the igniting effect's lifetime.
        target.statuses.setdefault("burning", {"source_id": source.id if source else None})

    def extinguish(self, actor, *, method="roll"):
        if not actor.has_status("burning"): return False
        if method == "roll":
            if self.current is not actor or not actor.alive or actor.has_condition("incapacitated") or actor.action < 1 or "prone" in actor.condition_immunities: return False
            actor.action -= 1
            actor.conditions.add("prone")
        elif method not in {"doused", "submerged", "suffocated"}: raise ValueError("unknown extinguishing method")
        actor.statuses.pop("burning", None)
        self.record("extinguish", actor=actor.id, method=method)
        return True

    def tick_burning(self, actor):
        if actor.alive and actor.has_status("burning"):
            source = next((c for c in self.combatants if c.id == actor.statuses["burning"].get("source_id")), None)
            self.damage(actor, dice.roll(self.rng, "1d4"), "fire", source)

    def execute(self, instance, target, primitives, ctx, block, half=False, shared=None):
        if ctx.get("attack"):
            for choice in instance.spec.get("choices", []):
                if choice["when"] == "on_attack": instance.choices[choice["id"]] = self.policy_for(instance.caster).choose(self, instance.caster, choice, choice["options"])
        for primitive in primitives:
            if not instance.active and block != "after_end": break
            if "if" in primitive and not evaluate(primitive["if"], ctx): continue
            key = next(k for k in primitive if k not in {"if", "until", "duration", "requires_condition", "participants"})
            value = primitive[key]
            if key in INSTANT_PRIMITIVES and primitive.get("requires_condition") and not target.has_condition_source(primitive["requires_condition"], instance.id): continue
            declaration = next((b for b in instance.spec.get("effects", []) if b["id"] == block), {})
            damage_actor = instance.caster if "on_attack_hit(any, caster)" in declaration.get("event", "") else ctx.get("attacker") or ctx.get("actor") or instance.caster
            if key == "damage" and value.get("delay"):
                if half: continue
                data = {**value, "caster_id": instance.caster.id}
                target.effects.append(Effect("delayed_damage", data, -instance.id, block, self.boundary(value["delay"], instance, target)))
                continue
            if key == "damage" and "wounded_dice" in value and target.hp < target.max_hp:
                value = {**value, "dice": value["wounded_dice"]}
            if half and key != "damage": continue
            if key in {"damage", "heal", "temp_hp"}:
                bonus = value.get("bonus", 0)
                if bonus == "spell_mod": bonus = instance.caster.spell_mod
                cache_key = (key, id(primitive), value.get("dice"), bonus)
                if shared is not None and cache_key in shared: amount = shared[cache_key]
                else:
                    if key == "damage" and "explode_max" in value:
                        n, sides, flat = dice.parts(value["dice"])
                        rolled = [self.rng.randint(1, sides) for _ in range(n * (2 if ctx.get("critical") else 1))]
                        pending = rolled.count(sides)
                        extra = []
                        while pending and len(extra) < max(0, instance.caster.spell_mod):
                            pending -= 1
                            die = self.rng.randint(1, sides)
                            extra.append(die)
                            if die == sides: pending += 1
                        amount = sum(rolled) + sum(extra) + flat + bonus
                    else:
                        if key == "damage" and value.get("leap_on_duplicate"):
                            n, sides, flat = dice.parts(value["dice"])
                            rolled = [self.rng.randint(1, sides) for _ in range(n * (2 if ctx.get("critical") else 1))]
                            amount = sum(rolled) + flat + bonus
                            instance.limits_count["orb_duplicate"] = len(set(rolled)) < len(rolled)
                        elif key == "heal" and "dice" in value and target.has_status("maximize_healing"):
                            n, sides, flat = dice.parts(value["dice"])
                            amount = n * sides + flat + bonus
                        else: amount = self.class_weapon_dice(instance.caster, value["dice"], bool(ctx.get("critical")) and key == "damage" and ctx.get("attacker", instance.caster) is instance.caster and not declaration.get("save"), ctx if key == "damage" else {}) + bonus if "dice" in value else value["amount"]
                        if amount == "spell_mod": amount = instance.caster.spell_mod
                    if key == "damage" and ctx.get("attack", {}).get("weapon"):
                        for e in instance.caster.active_effects:
                            if e.kind == "weapon_adjustment":
                                change = dice.roll(self.rng, e.data["dice"], bool(ctx.get("critical")))
                                amount = max(e.data["minimum"], amount + change * (1 if e.data["op"] == "add" else -1))
                    if key == "damage":
                        amount = self.modifier(damage_actor, "damage_roll", amount)
                        amount = self.class_damage_bonus(instance, target, amount, block)
                    if shared is not None: shared[cache_key] = amount
                if key == "damage":
                    dtype = value["type"]
                    if dtype.startswith("$"): dtype = instance.choices[dtype[1:]]
                    self.damage(target, amount, dtype, damage_actor, half=half or value.get("half", False) or instance.spec.get("casting_trigger") == "ranged_hit_or_miss" and block == "main" and not ctx.get("attack", {}).get("hit", True), spell=instance, hook=value if value.get("leech") or value.get("end_after_total") else None)
                elif key == "heal":
                    if instance.choices.get("_slot_expended") and instance.cast_turn == self.turn_index and instance.caster.features.get("disciple_of_life"):
                        amount += 2 + instance.slot
                        self.feature_log(instance.caster, "Disciple of Life", target=target.id, amount=2+instance.slot)
                    before = target.hp
                    self.heal(target, amount)
                    if target is not instance.caster and target.hp > before: instance.choices["_healed_other"] = True
                else: target.temp_hp = max(target.temp_hp, amount)
            elif key == "heal_pool":
                remaining = instance.limits_count.setdefault("healing_pool", value["amount"])
                amount = instance.choices["_pool_" + block][target.id]
                before = target.hp
                self.heal(target, amount)
                instance.limits_count["healing_pool"] -= target.hp - before
            elif key == "weapon_strike": self.weapon_spell(instance, target, value)
            elif key == "burning": self.ignite(target, instance.caster)
            elif key == "spend_reaction":
                if not self.turn_rules(target).get("no_reactions"): target.reaction = max(0, target.reaction - 1)
            elif key == "summon":
                from .summoning import materialize
                materialize(self, instance, value)
            elif key == "remove_condition":
                name = value["condition"]
                if name.startswith("$"): name = instance.choices[name[1:]]
                if not self.can_end_condition(target, name): continue
                target.conditions.discard(name)
                for effect in list(target.effects):
                    if effect.kind == "apply_condition" and effect.data["condition"] == name:
                        target.effects.remove(effect)
                self.refresh_spell_effects()
                self.record("condition_removed", target=target.id, condition=name)
            elif key == "dispel":
                for other in list(self.instances.values()):
                    if not other.active or other is instance or "level" not in other.spec: continue
                    affected = any(target in recipients for recipients in other.affected.values()) or any(target in members for members in other.area_members.values()) or target in other.summoned
                    if not affected: continue
                    effective_level = other.slot or other.spec["level"]
                    if effective_level <= max(instance.slot, value["auto_level"]) or self.ability_check(instance.caster, instance.caster.spell_ability, value["dc_base"] + effective_level):
                        self.end_spell(other.id)
                        self.record("dispel", target=target.id, spell=other.spec["name"])
            elif key == "end_spell": self.end_spell(instance.id)
            elif key == "end_concentration":
                if target.concentration is not None: self.end_spell(target.concentration)
            elif self.spell_primitive(key, value, instance, target): pass
            elif key == "counter_spell": ctx["trigger"]["cancelled"] = True
            elif key == "on_spell_end": instance.end_callbacks.append((target, value))
            else:
                if key == "status" and value["id"] == "engulfed":
                    for old in list(target.status_effects("engulfed")):
                        other = self.instances.get(old.source)
                        if other and other is not instance and other.caster is instance.caster:
                            self.remove_effects(other, target)
                if key == "apply_condition":
                    if self.condition_immune(target, value["condition"], instance.magical, instance.caster): continue
                    if value.get("persistent"):
                        target.conditions.add(value["condition"])
                        continue
                    if "max_size" in value and "TSMLHG".index(target.size) > "TSMLHG".index(value["max_size"]): continue
                    if not self.has_capacity(instance, target, value): continue
                    for old in list(target.effects):
                        other = self.instances.get(old.source)
                        if old.source != instance.id and old.kind == key and old.data.get("condition") == value["condition"] and other and other.caster is instance.caster and (value.get("linked") or other.spec["name"] == instance.spec["name"]):
                            self.remove_effects(other, target)
                data = dict(value)
                if instance.spec["name"] == "Bestow Curse" and key == "disadvantage" and data.get("against") == "target": data["curse_attack"] = True
                if key in {"pacify", "duel"}: self._has_damage_controls = True
                if key == "weapon_enchantment":
                    candidates = [a for a in target.attacks if not data.get("names") or a["name"].lower() in data["names"]]
                    data["names"] = [candidates[0]["name"].lower()] if candidates else ["unavailable_weapon"]
                if key == "bond":
                    for old in list(self.instances.values()):
                        if old is instance: continue
                        participants = [old.caster] + [c for c in self.combatants if any(e.source == old.id and e.kind == "bond" for e in c.active_effects)]
                        if len(participants) > 1 and (target in participants or instance.caster in participants): self.end_spell(old.id)
                if key == "type_mask": data["type"] = instance.choices[data["type"][1:]]
                if key == "sanctuary": data["ends_on_activity"] = True
                if key == "apply_condition": data["magical"] = instance.magical; data["source_type"] = instance.caster.magical_type if instance.magical else instance.caster.creature_type
                if key in {"apply_condition", "status"}: data["caster_id"] = instance.caster.id
                if key == "apply_condition" and (data.get("repeat_save") or data.get("repeat_on_damage") or data.get("resist_removal")):
                    declaration = next((b for b in instance.spec.get("effects", []) if b["id"] == block), {})
                    data["save_dc"] = (declaration.get("save") or {}).get("dc", instance.caster.spell_dc)
                if key == "apply_condition" and data.get("control"):
                    data["control_team"] = instance.caster.team
                if isinstance(data.get("scope"), str) and data["scope"].startswith("$"):
                    chosen = instance.choices[data["scope"][1:]]
                    data["scope"] = chosen.get(target.id, next(iter(chosen.values()))) if isinstance(chosen, dict) else chosen
                if data.get("escape_dc") == "spell_dc": data["escape_dc"] = instance.caster.spell_dc
                for field in ("resistance", "immunity", "vulnerability"):
                    if key == "defense" and field in data:
                        data[field] = [instance.choices[x[1:]] if x.startswith("$") else x for x in data[field]]
                effect = Effect(key, data, instance.id, block,
                    self.boundary(primitive["until"], instance, target) if "until" in primitive else None, data.get("uses"))
                effect.requires_condition = primitive.get("requires_condition")
                if "duration" in primitive:
                    d = primitive["duration"]
                    effect.expires_at = self.time_rounds + d["n"] * {"rounds": 1, "minutes": 10, "hours": 600}[d["type"]]
                # Continuous effects replace rather than stack on redispatch.
                target.effects = [e for e in target.effects if not (e.source == instance.id and e.block == block and e.kind == key and e.data == data)]
                target.effects.append(effect)
                self.refresh_spell_effects()
                if key == "remove_from_combat": target.removed = True
                if key == "apply_condition" and target.has_condition("incapacitated") and target.concentration is not None:
                    self.end_spell(target.concentration)

            if instance.spec.get("duration", {}).get("type") != "instant" and key not in INSTANT_PRIMITIVES:
                instance.affected.setdefault(block, set()).update({target, *(ctx[name] for name in primitive.get("participants", []))})

    def remove_effects(self, instance, target=None, block=None):
        for key in list(instance.affected):
            if block is not None and key != block: continue
            if target is None: instance.affected.pop(key)
            else: instance.affected[key].discard(target)
        for actor in ([target] if target else self.combatants):
            removed = [e for e in actor.effects if e.source == instance.id and (block is None or e.block == block)]
            for effect in removed:
                if effect.kind == "size_change": actor.size = effect.data["original"]
            actor.effects = [e for e in actor.effects if e not in removed]
        if target is not None and block is None and "level" not in instance.spec:
            for binding in instance.bindings.values():
                if target in binding.targets: binding.targets.remove(target)
        self.refresh_spell_effects()

    def end_spell(self, identifier):
        instance = self.instances.get(identifier)
        if instance is None or not instance.active: return
        instance.active = False
        for spirit in instance.summoned:
            if spirit.statuses.get("summon_rules", {}).get("persistent"): continue
            spirit.removed = True
            if spirit.concentration is not None: self.end_spell(spirit.concentration)
        instance.elapsed_minutes = round((self.time_rounds - instance.cast_round) / 10, 10)
        for actor in self.combatants:
            for effect in list(actor.effects):
                if effect.source == instance.id and effect.kind == "remove_from_combat":
                    returns = evaluate(effect.data["returns"], self.context(instance, actor))
                    actor.removed = False
                    actor.permanently_removed = not returns
        self.remove_effects(instance)
        if instance.caster.concentration == instance.id: instance.caster.concentration = None
        callbacks = instance.end_callbacks[:]
        instance.end_callbacks.clear()
        for target, primitives in callbacks:
            # Detached end effects have independent exact lifetimes.
            self.execute(instance, target, primitives, self.context(instance, target), "after_end")
            for effect in target.effects:
                if effect.source == instance.id: effect.source = -instance.id
        self.refresh_spell_effects()
        self.record("spell_end", spell=instance.spec["name"], source=instance.id)

    def refresh_areas(self, instance=None):
        for inst in ([instance] if instance else list(self.instances.values())):
            if not inst.active: continue
            memberships = {}
            for block in inst.spec["effects"]:
                if block["target"]["select"] != "area": continue
                target = block["target"]
                key = (target["shape"], target["size_ft"], target.get("origin"), target.get("exclude"), target["affects"], tuple(target.get("filter", [])), target.get("eligible_if"), target.get("include_caster"))
                if key not in memberships:
                    memberships[key] = self.area_members(inst, block, self.eligible(inst, block))
                members = memberships[key]
                inst.area_members[block["id"]] = members
                if block["event"] == "while_in_area":
                    self.remove_effects(inst, block=block["id"])
                    self.resolve_block(inst, block, "while_in_area", {})
        self.refresh_spell_effects()

    def dispatch(self, event, **frame):
        if event in MOVEMENT_EVENTS: return  # Accepted declarations, never simulated.
        for instance in list(self.instances.values()):
            if not instance.active: continue
            if instance.spec.get("monster_passive") and not instance.caster.alive: continue
            if instance.spec.get("monster_passive") and not any(t["name"] == instance.spec["name"] for t in instance.caster.traits): continue
            instance.elapsed_minutes = round((self.time_rounds - instance.cast_round) / 10, 10)
            for block in instance.spec["effects"]:
                if not instance.active: break
                if self.event_matches(block["event"], instance, event, frame):
                    if instance.spec.get("monster_passive"): self.feature_log(instance.caster, instance.spec["name"])
                    self.resolve_block(instance, block, event, frame)

    def command(self, instance, event="bonus_action_command", targets=None, actor=None):
        actor = actor or instance.caster
        kind = "bonus_action" if event == "bonus_action_command" else "action"
        if event not in {"bonus_action_command", "action_command"} or self.current is not actor or not actor.alive or actor.has_condition("incapacitated") or getattr(actor, kind) < 1: return False
        performed = False
        for block in instance.spec["effects"]:
            if actor is not instance.caster and not any(e.kind == "grant_command" and e.source == instance.id and e.data["block"] == block["id"] for e in actor.active_effects): continue
            if self.event_matches(block["event"], instance, event, {}):
                if self.resolve_block(instance, block, event, {"actor": actor}, targets):
                    performed = True
        if performed: self.spend_economy(actor, kind)
        return performed

    def expire(self, event, actor):
        def due(boundary):
            return boundary and boundary[0] == event and boundary[1] == actor.id and actor.turns_taken >= boundary[2]
        for instance in list(self.instances.values()):
            if not instance.active: continue
            duration = instance.spec["duration"]
            units = {"rounds": 1, "minutes": 10, "hours": 600}
            timed = not instance.ends and duration["type"] in units and compare_deadline(self.time_rounds, instance.cast_round + duration.get("n", 0) * units.get(duration["type"], 0)) >= 0
            if timed or any(due(x) for x in instance.ends): self.end_spell(instance.id)
        for creature in self.combatants:
            for effect in list(creature.effects):
                if due(effect.until) and effect.kind == "delayed_damage":
                    source = next((c for c in self.combatants if c.id == effect.data["caster_id"]), None)
                    value = effect.data
                    amount = dice.roll(self.rng, value["dice"]) + value.get("bonus", 0) if "dice" in value else value["amount"]
                    self.damage(creature, amount, value["type"], source)
            creature.effects = [e for e in creature.effects if not due(e.until) and not (e.expires_at is not None and compare_deadline(self.time_rounds, e.expires_at) >= 0)]
        self.refresh_spell_effects()

    def reset_turn_economy(self, actor):
        actor.blocked_economy.clear()
        actor.action = actor.bonus_action = actor.reaction = 1
        actor.surge_actions = 0
        actor.extra_actions = []
        actor.action_grants.clear()
        actor.slot_cast_turn = None

    def begin_turn(self, actor):
        self.current = actor
        self.turn_index += 1
        actor.turns_taken += 1
        self.reset_turn_economy(actor)
        if actor.concentration is not None and (actor.has_condition("incapacitated") or not actor.alive):
            self.end_spell(actor.concentration)
        self.expire("start_of_turn", actor)
        self.grant_current_actions(actor)
        actor.action = int(self.modifier(actor, "action_count", actor.action + actor.blocked_economy.pop("action", 0)))
        rules = self.turn_rules(actor)
        self.reconcile_economy(actor)
        if rules.get("on_turn_condition") not in actor.condition_immunities and rules.get("on_turn_condition"):
            actor.conditions.add(rules["on_turn_condition"])
        for action in actor.actions + actor.attacks + [{"name": n, "recharge": threshold} for n, threshold in actor.spell_recharge.items()]:
            if "recharge" in action and not actor.recharge_ready.get(action["name"], True):
                actor.recharge_ready[action["name"]] = self.rng.randint(1, 6) >= action["recharge"]
        self.start_monster_turn(actor)
        self.class_start_turn(actor)
        self.death_save(actor)
        self.repeat_saves(actor, "start_of_turn")
        self.refresh_areas()
        self.tick_burning(actor)
        self.dispatch("start_of_turn", who=actor)
        self.spell_turn(actor)
        self.record("turn_start", actor=actor.id, round=self.round)

    def repeat_saves(self, actor, timing):
        for effect in list(actor.effects):
            repeat = effect.data.get("repeat_save") if effect.kind in {"apply_condition", "turn_rules"} else None
            instance = self.instances.get(abs(effect.source))
            if repeat and repeat["timing"] == timing and instance and (instance.active or effect.source < 0):
                if self.saving_throw(actor, repeat["ability"], effect.data.get("save_dc", instance.caster.spell_dc), magical=instance.magical, conditions=[effect.data.get("condition")]):
                    if effect.source < 0:
                        actor.effects = [e for e in actor.effects if e.source != effect.source]
                    else: self.remove_effects(instance, actor)
                    for binding in instance.bindings.values():
                        if actor in binding.targets: binding.targets.remove(actor)
                elif effect.data.get("upgrade_on_failure"):
                    data = dict(effect.data)
                    data["condition"] = data.pop("upgrade_on_failure")
                    data.pop("repeat_save", None)
                    actor.effects.remove(effect)
                    self.execute(instance, actor, [{"apply_condition": data}], self.context(instance, actor), effect.block)
                    for replacement in actor.effects:
                        if replacement.source == effect.source and replacement.block == effect.block:
                            replacement.until = effect.until

    def end_turn(self, actor):
        for inst in list(self.instances.values()):
            if inst.active and inst.caster is actor and inst.maintained_turn < actor.turns_taken and any(e.source == inst.id and e.kind == "turn_rules" and e.data.get("maintained_by_action") for c in self.combatants for e in c.effects): self.end_spell(inst.id)
        self.spell_end_turn(actor)
        self.dispatch("end_of_turn", who=actor)
        self.dispatch("end_of_turn_in_aura", who=actor)
        self.tally_saves(actor)
        self.repeat_saves(actor, "end_of_turn")
        self.expire("end_of_turn", actor)
        for c in self.combatants:
            for e in list(c.effects):
                inst = self.instances.get(e.source)
                if inst and e.data.get("linked") and (not inst.caster.alive or (inst.caster.has_condition("incapacitated") and not e.data.get("control"))): self.remove_effects(inst, c)
        self.time_rounds += 1 / max(1, sum(c.summoner_id is None or c.alive for c in self.combatants))
        self.current = None
        self.legendary_actions(actor)

    def weapon_attack(self, actor, target, attack):
        if not actor.alive or not self.targetable(target, actor) or actor.has_condition("incapacitated"): return False
        attack = self.enchanted_attack(actor, attack)
        attack = self.class_weapon(actor, attack, target)
        if not actor.recharge_ready.get(attack["name"], True): return False
        if attack.get("resource") and not actor.limited_uses.get(attack["resource"]): return False
        if attack.get("recharge"): actor.recharge_ready[attack["name"]] = False
        if attack.get("resource"):
            actor.limited_uses[attack["resource"]] -= 1
            actor.spend(attack["resource"])
        target = self.redirect_target(actor, target)
        self.record("weapon", actor=actor.id, name=attack["name"])
        before_hp = target.hp
        previous_context = self._monster_attack
        self._monster_attack = actor, attack["name"]
        cunning = None
        def hit(critical, roll):
            nonlocal cunning
            persistent = attack.get("riders") or any("damage" not in p for p in attack["effects"])
            instance = self.monster_instance(actor, attack["name"], attack.get("riders", [])) if persistent else SpellInstance(0, {"name": attack["name"]}, actor, 0, self.turn_index, self.time_rounds)
            frame = {"attacker": actor, "defender": target, "attack": roll, "critical": critical, "weapon_properties": attack.get("properties", [])}
            self.execute(instance, target, attack["effects"], self.context(instance, target, "on_attack_hit", frame, **frame), "weapon")
            cunning = self.class_hit(actor, target, attack, critical, roll)
            if attack.get("on_hit_self"): self.execute(instance, actor, attack["on_hit_self"], self.context(instance, actor), "self_hit")
            for block in attack.get("riders", []): self.resolve_block(instance, block, "on_cast", {}, [target])
            if attack.get("mastery") == "sap":
                target.effects.append(Effect("disadvantage", {"on": "attack_rolls", "scope": "all", "against": None}, 0, "sap", ("start_of_turn", actor.id, actor.turns_taken + 1), uses=1))
            if attack.get("mastery") == "vex":
                # Restricted to this attacker's next attack against the target.
                actor.statuses["vex"] = {"target": target.id, "expires": actor.turns_taken + 1}
            self.class_mastery(actor, target, attack)
        vex = actor.statuses.pop("vex", None)
        extra = None
        if vex and vex["target"] == target.id and actor.turns_taken <= vex["expires"]:
            extra = Effect("advantage", {"on": "attack_rolls", "scope": "all", "against": None}, 0, "vex", uses=1)
            actor.effects.append(extra)
        if attack.get("advantage_if") == "grappled_by_self" and actor in self.condition_sources(target, "grappled"):
            from_effect = Effect("advantage", {"on": "attack_rolls", "scope": "all", "against": None}, 0, "grapple", uses=1)
            actor.effects.append(from_effect)
        success = self.attack(actor, target, attack["to_hit"], hit, attack.get("kind", "melee") == "melee", weapon=True, ability=attack.get("ability", "str" if attack.get("kind", "melee") == "melee" else "dex"))
        self._monster_attack = previous_context
        if success: self.class_after_hit(actor, target, cunning)
        if not success and attack.get("mastery") == "graze":
            self.damage(target, max(0, actor.mod(attack.get("ability", "str"))), attack["effects"][0]["damage"]["type"], actor)
        if extra in actor.effects: actor.effects.remove(extra)
        if success and actor.features.get("rampage") and actor.bonus_action and actor.limited_uses.get("Rampage") and before_hp <= target.max_hp / 2 and target.hp < before_hp and self.enemies(actor):
            actor.bonus_action -= 1
            actor.limited_uses["Rampage"] -= 1
            actor.spend("Rampage")
            self.feature_log(actor, "Rampage")
            self.perform_option(actor, "Rend")
        return success

    def weapon_action(self, actor, granted=None):
        if not actor.alive or actor.has_condition("incapacitated") or not actor.attacks or (not granted and actor.action < 1): return False
        if not granted:
            self.spend_economy(actor, "action")
            if actor.surge_actions: actor.surge_actions -= 1
        self.record("action", actor=actor.id, name="Attack", granted=bool(granted))
        names = self.routine(actor, self.enemies(actor)[0]) if self.enemies(actor) else []
        if not granted and actor.replacements:
            names = self.policy_for(actor).monster_replacements(self, actor, names)
        if granted: names = names[:granted.get("attack_limit", 1)]
        if self.turn_rules(actor).get("attack_limit"): names = names[:self.turn_rules(actor)["attack_limit"]]
        for name in names:
            enemies = self.enemies(actor)
            attack = next((a for a in actor.attacks if a["name"] == name), None)
            enemies = self.reachable(actor, enemies, attack)
            if not enemies: break
            target = self.policy_for(actor).weapon_target(self, actor, enemies)
            self.perform_option(actor, name, [target])
        return True

    def action_available(self, actor, action):
        if not actor.alive or actor.has_condition("incapacitated"): return False
        if action.get("passive") or action.get("trigger"): return False
        if self.current is not actor: return False
        if action.get("magical") and action["cost"]=="action" and actor.action<=actor.surge_actions: return False
        if action["name"] == "Steady Aim" and actor.statuses.get("moved_turn") == self.turn_index: return False
        if self.turn_rules(actor).get({"action": "no_action", "bonus_action": "no_bonus_action", "reaction": "no_reactions"}.get(action["cost"])): return False
        if action["cost"] != "free" and getattr(actor, action["cost"]) < 1: return False
        if action.get("resource") and actor.limited_uses.get(action["resource"], 0) < 1: return False
        return actor.recharge_ready.get(action["name"], True)

    def prepare_healing_pool(self, instance, block, targets):
        pool = next((p["heal_pool"] for p in block["apply"] if "heal_pool" in p), None)
        key = "_pool_" + block["id"]
        if pool is None or key in instance.choices: return
        allocations = instance.choices.get("allocations")
        if allocations is None:
            allocations = self.policy_for(instance.caster).healing_pool(self, instance, targets, pool["amount"])
        caps = {t.id: max(0, t.max_hp // 2 - t.hp) for t in targets}
        if (not isinstance(allocations, dict) or set(allocations) - set(caps)
            or any(type(n) is not int or not 0 <= n <= caps[k] for k, n in allocations.items())
            or sum(allocations.values()) > pool["amount"]):
            raise ValueError("illegal healing pool allocation")
        instance.choices[key] = {k: allocations.get(k, 0) for k in caps}

    def use_action(self, actor, name, targets=None, *, allocations=None):
        action = next(a for a in actor.actions + actor.traits if a["name"] == name)
        if not self.action_available(actor, action): return False
        pool_choices = {"allocations": allocations} if allocations is not None else {}
        probe = SpellInstance(0, {"name":name}, actor, 0, self.turn_index, self.time_rounds, choices=pool_choices)
        for block in action["effects"]:
            if any("heal_pool" in p for p in block["apply"]):
                selected = self.select_targets(probe, block, {}, targets)
                self.prepare_healing_pool(probe, block, selected)
        if targets is not None:
            probe = SpellInstance(0, {"name":name}, actor, 0, self.turn_index, self.time_rounds)
            for block in action["effects"]:
                if block["target"]["select"] in {"single","n_targets"} and self.event_matches(block["event"],probe,"on_cast",{}): self.select_targets(probe,block,{},targets)
        self.record("action", actor=actor.id, name=name)
        if action["cost"] != "free": self.spend_economy(actor, action["cost"])
        if action.get("resource"):
            actor.limited_uses[action["resource"]] -= 1
            actor.spend(action["resource"])
        if action.get("recharge"):
            actor.recharge_ready[action["name"]] = False
            actor.spend(name)
        if action.get("grants_action"):
            actor.action += 1
            if action.get("resource") == "action_surge": actor.surge_actions += 1
            return True
        spec = {"name": name, "duration": action.get("duration", {"type": "instant"}), "effects": action["effects"], "ends_on": [], "magical":action.get("magical",False)}
        inst = SpellInstance(self.next_instance, spec, actor, 0, self.turn_index, self.time_rounds)
        inst.choices.update(pool_choices)
        self.next_instance += 1
        self.instances[inst.id] = inst
        previous_context = self._monster_attack
        self._monster_attack = actor, name
        for block in action["effects"]:
            if name == "Steady Aim" and actor.features.get("roving_aim"):
                block = {**block, "apply": [p for p in block["apply"] if "modify" not in p]}
            if self.event_matches(block["event"], inst, "on_cast", {}): self.resolve_block(inst, block, "on_cast", {}, targets)
        self._monster_attack = previous_context
        if action.get("duration"): return True
        for creature in self.combatants:
            for effect in creature.effects:
                if effect.source == inst.id and effect.until: effect.source = -inst.id
        self.end_spell(inst.id)
        return True

    def hit_probability(self, actor, target, bonus):
        return min(.95, max(.05, (21 + bonus - self.armor_class(target)) / 20))

    def expected_weapon_damage(self, actor, target):
        if actor.routines: return max(self.routine_value(actor, names, target) for names in actor.routines)
        if not actor.attacks: return 0
        total = 0
        names = actor.multiattack or [actor.attacks[0]["name"]] * actor.extra_attack
        for name in names:
            attack = next(a for a in actor.attacks if a["name"] == name)
            expected = sum(dice.base_mean(p["damage"]) + p["damage"].get("bonus", 0) for p in attack["effects"] if "damage" in p and "if" not in p)
            if actor.features.get("great_weapon_fighting") and attack["kind"]=="melee" and "two_handed" in attack.get("properties",[]):
                for p in attack["effects"]:
                    if "damage" in p and "dice" in p["damage"]:
                        n,sides,_=dice.parts(p["damage"]["dice"])
                        expected += n*(sum(max(3,i) for i in range(1,sides+1))/sides-(sides+1)/2)
            total += expected * self.hit_probability(actor, target, attack["to_hit"])
            if actor.features.get("improved_critical"):
                total += sum(dice.base_mean(p["damage"]) for p in attack["effects"] if "damage" in p) * (21-actor.features["improved_critical"])/20
            if attack.get("mastery") == "graze": total += max(0, actor.mod("str")) * (1 - self.hit_probability(actor, target, attack["to_hit"]))
        attack=actor.attacks[0]
        if self.sneak_eligible(actor,target,attack):
            hit=self.hit_probability(actor,target,attack["to_hit"])
            adv,dis=self.roll_flags(actor,"attack_rolls",attack.get("ability","dex"),against=target)
            if adv and not dis: hit=1-(1-hit)**2
            if dis and not adv: hit=hit**2
            bonus=dice.mean(actor.features["sneak_attack"])+(actor.level if actor.features.get("assassinate") and self.round==1 else 0)
            total += bonus*(1-(1-hit)**len(names))
        return total

    def save_failure_probability(self, actor, target, ability, dc=None):
        bonus = target.save_bonuses.get(ability, target.mod(ability) + (target.proficiency_bonus if ability in target.save_proficiencies else 0))
        return min(1, max(0, ((actor.spell_dc if dc is None else dc) - bonus - 1) / 20))

    def cantrip_spec(self, actor, name):
        """Scaled cantrip for read-only EV probes, cached per caster (scaling depends only on
        the caster's level, features and components, which do not change in a combat)."""
        cache = self.__dict__.setdefault("_cantrip_specs", {})
        key = (actor.id, actor.name, actor.level, name)
        if key not in cache: cache[key] = self.scale(actor, self.spells[name], 0)
        return cache[key]

    def at_will_damage_rate(self, actor, target):
        # Explicit one-round horizon prevents recursion into encounter estimation.
        return max([self.expected_weapon_damage(actor, target)] + [
            self.expected_spell_damage(actor, self.cantrip_spec(actor, name), target, horizon=1)
            for name in actor.spells if self.spells[name]["level"] == 0])

    def expected_remaining_rounds(self, actor):
        enemies = self.enemies(actor)
        if not enemies: return 1
        allies = [c for c in self.combatants if c.team == actor.team and c.alive and not c.has_condition("incapacitated")]
        rate = sum(self.at_will_damage_rate(c, enemies[0]) for c in allies)
        return max(1, sum(c.hp for c in enemies) / max(1, rate))

    def expected_attack_hits(self, actor, target):
        names = actor.multiattack or ([actor.attacks[0]["name"]] * actor.extra_attack if actor.attacks else [])
        hits = sum(self.hit_probability(actor, target, next(a for a in actor.attacks if a["name"] == name)["to_hit"]) for name in names)
        for name in actor.spells:
            if self.spells[name]["level"] != 0: continue
            spec = self.cantrip_spec(actor, name)
            hits = max(hits, sum(self.hit_probability(actor, target, actor.spell_attack_bonus) * b["target"].get("n", 1)
                                 for b in spec["effects"] if b["attack"] and "on_cast" in b["event"]))
        return hits

    def control_attack_gain(self, ally, target, condition):
        if condition not in {"paralyzed", "stunned", "unconscious", "petrified", "restrained", "blinded"}: return 0
        names = ally.multiattack or ([ally.attacks[0]["name"]] * ally.extra_attack if ally.attacks else [])
        gain = 0
        for name in names:
            attack = next(a for a in ally.attacks if a["name"] == name)
            hit = self.hit_probability(ally, target, attack["to_hit"])
            advantage = 1 - (1 - hit) ** 2
            damage = sum(dice.base_mean(p["damage"]) + p["damage"].get("bonus", 0) for p in attack["effects"] if "damage" in p and "if" not in p)
            crit_dice = sum(dice.base_mean(p["damage"]) for p in attack["effects"] if "damage" in p and "if" not in p)
            auto_crit = condition in {"paralyzed", "unconscious"} and attack.get("kind", "melee") == "melee"
            gain += (advantage - hit) * damage + (advantage * crit_dice if auto_crit else 0)
        return gain

    def expected_spell_damage(self, actor, spec, target, *, horizon=None, control_value=True, precombat=False):
        """Damage-equivalent EV, not search. See BUILD_REPORT's Step 1 fix round.

        Lasting effects use enemy HP / allied at-will DPR, capped by duration.
        Concentration reserves 10% of value; future commands reserve 15% of
        bonus actions for healing/other uses. Repeat saves give geometric uptime.
        """
        if precombat: return self.expected_buff_prevention(actor, spec)[0]
        total = 0
        empowered = actor.features.get("empowered_evocation") and spec.get("school")=="evocation"
        probe = SpellInstance(0, spec, actor, 0, self.turn_index, self.time_rounds)
        probe.exclusions = {c.id for c in self.policy_for(actor).exemptions(self,actor)}
        allies = [c for c in self.combatants if c.team == actor.team and c.alive and not c.has_condition("incapacitated")]
        for block in spec["effects"]:
            primitives = [p for key in ("on_hit", "on_fail", "apply") for p in block[key]]
            if spec.get("level")==0 and actor.features.get("potent_cantrip"):
                for p in primitives:
                    if "weapon_strike" not in p: continue
                    probe.choices={c["id"]:c["options"][0] for c in spec.get("choices",[])}
                    attack=self.spell_weapon_attack(probe,p["weapon_strike"])
                    if attack:
                        amount=sum(dice.base_mean(x["damage"])+x["damage"].get("bonus",0) for x in attack["effects"] if "damage" in x)
                        hit=self.hit_probability(actor,target,attack["to_hit"])
                        total+=p["weapon_strike"]["count"]*amount*(hit+(1-hit)/2)
            if not any("damage" in p or "apply_condition" in p or "remove_from_combat" in p or "turn_rules" in p for p in primitives): continue
            declaration = block
            if block["target"]["select"] == "ref":
                declaration = next((b for b in spec["effects"] if b["id"] == block["target"]["ref"]), block)
            eligible = [c for c in self.eligible(probe, declaration) if c.team != actor.team]
            eligible.sort(key=lambda c: (c.hp, c.id))
            t = declaration["target"]
            if t["select"] == "self": continue
            if t["select"] == "area":
                targets = self.area_members(probe, declaration, self.eligible(probe,declaration))
                self.sculpt_targets(probe, block, targets)
            elif not t.get("distinct", True) and eligible:
                targets = [eligible[0]] * t.get("n", 1)
            else:
                targets = eligible if t.get("n") == "all" else eligible[:t.get("n", 1)]
            if not targets: continue
            event = block["event"]
            command = "bonus_action_command" in event and any("damage" in p for p in primitives)
            aura = "end_of_turn_in_aura" in event
            rider = "on_attack_hit(caster, defender)" in event
            control = control_value and any("apply_condition" in p or "remove_from_combat" in p or p.get("turn_rules", {}).get("no_action") or p.get("turn_rules", {}).get("attack_limit") for p in primitives)
            lasting = command or aura or rider or control
            rounds = 1
            if lasting:
                if horizon is None: horizon = self.expected_remaining_rounds(actor)
                duration = spec.get("duration", {"type": "instant"})
                cap = duration.get("n", 1) * {"rounds": 1, "minutes": 10, "hours": 600, "days": 14400}.get(duration["type"], 1)
                rounds = min(horizon, cap)
            for victim in targets:
                if victim.id in probe.choices.get("_sculpted",set()): continue
                damage = sum(dice.base_mean(p["damage"]) + (actor.spell_mod if p["damage"].get("bonus", 0) == "spell_mod" else p["damage"].get("bonus", 0)) for p in primitives if "damage" in p)
                if damage and spec.get("level")==0 and actor.features.get("potent_spellcasting"): damage += actor.spell_mod
                if damage and empowered: damage += actor.mod("int"); empowered=False
                fail = self.save_failure_probability(actor, victim, block["save"]["ability"], block["save"].get("dc")) if block["save"] else 1
                if block["attack"]:
                    hit=self.hit_probability(actor, victim, actor.spell_attack_bonus)
                    miss=sum(dice.base_mean(p["damage"])+(actor.spell_mod if p["damage"].get("bonus")=="spell_mod" else p["damage"].get("bonus",0)) for p in block.get("on_miss",[]) if "damage" in p)/2
                    damage=damage*hit+miss*(1-hit)
                if block["save"]: damage *= fail + ((1 - fail) / 2 if block["save"]["on_success"] == "half" else 0)
                if command: damage *= 1 + .85 * max(0, rounds - 1)
                elif aura: damage *= rounds
                elif rider: damage *= rounds * self.expected_attack_hits(actor, victim)
                elif "on_cast" not in event: damage = 0
                removed = any("remove_from_combat" in p for p in primitives)
                denied_rate = max((self.at_will_damage_rate(victim, ally) for ally in allies), default=0) if control else 0
                condition_value = fail * rounds * denied_rate if removed else 0
                for p in primitives:
                    rules = p.get("turn_rules", {})
                    if not control or not rules: continue
                    uptime = rounds
                    if rules.get("repeat_save"):
                        q = self.save_failure_probability(actor, victim, rules["repeat_save"]["ability"])
                        whole = int(rounds)
                        uptime = rounds if q == 1 else (1 - q ** whole) / (1 - q) + (rounds - whole) * q ** whole
                    attack_count = len(victim.multiattack) if victim.multiattack else victim.extra_attack
                    fraction = 1 if rules.get("no_action") else max(0, 1 - rules.get("attack_limit", attack_count) / max(1, attack_count))
                    if any(self.spells[n]["level"] == 0 and self.spells[n]["components"]["s"] for n in victim.spells):
                        fraction = max(fraction, rules.get("somatic_failure_percent", 0) / 100)
                    condition_value = max(condition_value, fail * uptime * denied_rate * fraction)
                for p in primitives:
                    if not control or "apply_condition" not in p: continue
                    data = p["apply_condition"]
                    condition = data["condition"]
                    if condition in victim.condition_immunities or victim.has_condition(condition): continue
                    repeat = data.get("repeat_save")
                    uptime = rounds
                    if repeat:
                        q = self.save_failure_probability(actor, victim, repeat["ability"])
                        whole = int(rounds)
                        uptime = rounds if q == 1 else (1 - q ** whole) / (1 - q) + (rounds - whole) * q ** whole
                        if repeat["timing"] == "start_of_turn": uptime *= q
                    denied = 2 * denied_rate if data.get("control") else 0
                    if condition in {"incapacitated", "paralyzed", "stunned", "unconscious", "petrified"}:
                        denied = denied_rate
                    gained = 0 if removed else sum(self.control_attack_gain(ally, victim, condition) for ally in allies)
                    condition_value = max(condition_value, fail * uptime * (denied + gained))
                value = damage + condition_value
                if lasting and spec.get("concentration"): value *= .9
                total += -value if victim.team==actor.team else value
        return total

    def expected_action_damage(self, actor, action, target):
        if action["name"]=="Preserve Life":
            missing=sum(max(0,c.max_hp//2-c.hp)*(2 if c.hp==0 else 1) for c in self.combatants if c.team==actor.team and not c.removed and not c.permanently_removed)
            return min(5*actor.level,missing)
        if action["name"]=="Divine Spark (Heal)":
            missing=max((c.max_hp-c.hp for c in self.combatants if c is not actor and c.team==actor.team and not c.removed and not c.permanently_removed),default=0)
            return min(missing,dice.mean("2d8" if actor.level>=7 else "1d8")+actor.spell_mod)
        if action["name"]=="Turn Undead" and not any(c.creature_type=="undead" and not c.has_condition("incapacitated") for c in self.enemies(actor)): return 0
        value=self.expected_spell_damage(actor, {"name":action["name"],"effects": action["effects"],"duration":action.get("duration",{"type":"instant"})}, target)
        if action["name"]=="Turn Undead" and actor.features.get("sear_undead"):
            value += sum(max(1,actor.spell_mod)*4.5*self.save_failure_probability(actor,c,"wis") for c in self.enemies(actor) if c.creature_type=="undead" and not c.has_condition("incapacitated"))
        return value

    def run(self, max_rounds=100):
        self.interrupt_rest("initiative")
        initiative = sorted((c for c in self.combatants if c.summoner_id is None), key=lambda c: (-(dice.d20(self.rng, advantage=c.has_condition("invisible") or c.features.get("initiative_advantage", False)) + c.mod("dex") + c.initiative_bonus), c.id))
        self.record("initiative", order=[c.id for c in initiative])
        self.morale_start = {}
        for c in self.combatants:
            if c.cr is not None and c.summoner_id is None and c.team != "party" and c.alive:
                self.morale_start[c.team] = self.morale_start.get(c.team, 0) + 1
        for round_number in range(1, max_rounds + 1):
            self.round = round_number
            for actor in initiative:
                self.begin_turn(actor)
                self.policy_for(actor).take_turn(self, actor)
                self.end_turn(actor)
                from .summoning import take_summoned_turns
                take_summoned_turns(self, actor)
                self.morale_checks()
                teams = {c.team for c in self.combatants if c.alive or (self.death_rules and c.team == "party" and not c.dead and not c.removed and not c.permanently_removed) or (c.features.get("regeneration", {}).get("at_zero") and not c.has_status("regeneration_blocked") and not c.removed and not c.permanently_removed)}
                if len(teams) <= 1:
                    return {"winner": next(iter(teams), None), "rounds": round_number, "hp": self.party_hp(), "resources": self.resources()}
        return {"winner": None, "rounds": max_rounds, "hp": self.party_hp(), "resources": self.resources()}

    def party_hp(self):
        return sum(c.hp for c in self.combatants if c.team == "party" and c.summoner_id is None and not c.permanently_removed and not c.removed)

    def resources(self):
        result = Counter()
        for c in self.combatants:
            if c.team == "party": result.update(c.resources_spent)
        return dict(result)
