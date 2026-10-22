"""Event-driven resolution. The engine never imports the old extraction pipeline."""
from collections import Counter, defaultdict
from types import SimpleNamespace
import random

from . import dice
from .expressions import evaluate, parse
from .loader import scaled_spell
from .policy import Policy, area_heuristic
from .state import Combatant, Effect, Binding, SpellInstance

MOVEMENT_EVENTS = {"on_aura_moves_onto_creature", "on_creature_enters_aura"}


class Combat:
    def __init__(self, combatants: list[Combatant], spells: dict, seed=1, policy=None, area=None):
        if len({c.id for c in combatants}) != len(combatants):
            raise ValueError("combatant ids must be unique")
        self.combatants = combatants
        self.spells = spells
        self.rng = random.Random(seed)
        self.policy = policy or Policy()
        self.area = area or area_heuristic
        self.instances: dict[int, SpellInstance] = {}
        self.next_instance = 1
        self.turn_index = 0
        self.round = 1
        self.time_rounds = 0.0
        self.current: Combatant | None = None
        self.log: list[dict] = []
        self.record_log = True
        self._damage_batch = None

    def record(self, kind, **data):
        if self.record_log: self.log.append({"event": kind, "turn": self.turn_index, **data})

    def enemies(self, actor):
        return [x for x in self.combatants if x.alive and x.team != actor.team]

    def spell_potency(self, instance):
        # Compare numerical effect strength, not duration or number of targets.
        strength = 0
        for block in instance.spec["effects"]:
            branches = []
            for branch in ("apply", "on_hit", "on_fail", "on_success"):
                total = 0
                for primitive in block[branch]:
                    for kind in ("damage", "heal", "modify", "temp_hp"):
                        if kind not in primitive: continue
                        # A past instantaneous hit does not strengthen a lingering benefit.
                        if kind in {"damage", "heal"} and block["event"] == "on_cast": continue
                        value = primitive[kind]
                        if "dice" in value:
                            bonus = value.get("bonus", 0)
                            amount = dice.mean(value["dice"]) + (instance.caster.spell_mod if bonus == "spell_mod" else bonus)
                        else:
                            amount = value.get("value", value.get("amount", 0))
                            if isinstance(amount, str): amount = dice.mean(amount)
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
        if self.current is not None: self.grant_current_actions(self.current)

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

    def modifier(self, actor, stat, base=0, scope="all"):
        result = base
        for effect in actor.active_effects:
            if effect.kind != "modify" or effect.data["stat"] != stat or effect.data["scope"] not in {"all", scope}: continue
            value = effect.data["value"]
            if isinstance(value, str): value = dice.roll(self.rng, value)
            op = effect.data["op"]
            if op == "add": result += value
            elif op == "mul": result *= value
            else: result = value
        return result

    def armor_class(self, actor):
        return self.modifier(actor, "ac", actor.ac)

    def condition_sources(self, actor, condition):
        return [self.instances[e.source].caster for e in actor.active_effects
                if e.kind == "apply_condition" and e.data["condition"] == condition and e.source in self.instances]

    def exhaustion_penalty(self, actor):
        return 2 * max(actor.exhaustion_level, int(actor.has_condition("exhaustion")))

    def roll_flags(self, actor, on, scope="all", against=None, consume=False):
        advantage = disadvantage = False
        effects = list(actor.active_effects)
        if on == "attack_rolls" and against is not None:
            effects += [e for e in against.active_effects if e.kind in {"advantage", "disadvantage"} and e.data.get("recipient") == "any_attacker"]
        for effect in effects:
            if effect.kind not in {"advantage", "disadvantage"} or effect.data["on"] != on or effect.data["scope"] not in {"all", scope}: continue
            if effect.data.get("recipient") == "any_attacker" and (against is None or effect not in against.effects): continue
            if effect.kind == "advantage": advantage = True
            else: disadvantage = True
            if consume and effect.uses is not None:
                effect.uses -= 1
                if effect.uses == 0:
                    for c in self.combatants:
                        if effect in c.effects: c.effects.remove(effect)
        if consume: self.refresh_spell_effects()
        return advantage, disadvantage

    def saving_throw(self, target, ability, dc, ignore_cover=None):
        if ability in {"str", "dex"} and any(target.has_condition(x) for x in ("paralyzed", "stunned", "unconscious", "petrified")):
            self.record("save", target=target.id, ability=ability, success=False, automatic=True)
            return False
        advantage, disadvantage = self.roll_flags(target, "saves", ability)
        disadvantage |= ability == "dex" and target.has_condition("restrained")
        bonus = target.save_bonuses.get(ability, target.mod(ability) + (target.proficiency_bonus if ability in target.save_proficiencies else 0))
        total = dice.d20(self.rng, advantage, disadvantage) + self.modifier(target, "save", bonus, ability)
        total -= self.exhaustion_penalty(target)
        success = total >= dc
        # Sheets may use the same counter for monster Legendary Resistance.
        if not success and target.limited_uses.get("legendary_resistance", 0):
            target.limited_uses["legendary_resistance"] -= 1
            target.spend("legendary_resistance")
            success = True
        self.record("save", target=target.id, ability=ability, total=total, dc=dc, success=success)
        return success

    def ability_check(self, target, ability, dc):
        adv, dis = self.roll_flags(target, "ability_checks", ability)
        dis |= target.has_condition("poisoned") or target.has_condition("frightened")
        total = dice.d20(self.rng, adv, dis) + self.modifier(target, "ability_check", target.mod(ability), ability)
        total -= self.exhaustion_penalty(target)
        return total >= dc

    def attack(self, attacker, defender, bonus, on_hit, melee=True):
        if not attacker.alive or not defender.alive or attacker.has_condition("incapacitated"): return False
        if defender in self.condition_sources(attacker, "charmed"): return False
        self.dispatch("on_attacked", who=defender, attacker=attacker, defender=defender)
        adv, dis = self.roll_flags(attacker, "attack_rolls", against=defender, consume=True)
        adv |= any(defender.has_condition(c) for c in ("paralyzed", "stunned", "unconscious", "blinded", "restrained"))
        adv |= attacker.has_condition("invisible") and not defender.has_condition("invisible")
        dis |= any(attacker.has_condition(c) for c in ("blinded", "restrained", "poisoned", "frightened", "prone"))
        dis |= defender.has_condition("invisible") and not attacker.has_condition("invisible")
        grapplers = self.condition_sources(attacker, "grappled")
        dis |= bool(grapplers) and defender not in grapplers
        if defender.has_condition("prone"):
            if melee: adv = True
            else: dis = True
        natural = dice.d20(self.rng, adv, dis)
        total = natural + self.modifier(attacker, "attack_roll", bonus)
        total -= self.exhaustion_penalty(attacker)
        critical = natural == 20 or (melee and any(defender.has_condition(c) for c in ("paralyzed", "unconscious")))
        attack = {"natural": natural, "total": total, "critical": critical, "advantage": adv and not dis}
        hit = natural != 1 and (natural == 20 or total >= self.armor_class(defender))
        if hit:
            self.offer_reactions("on_attack_provisional_hit", attacker=attacker, defender=defender, who=defender, attack=attack)
            hit = natural != 1 and (natural == 20 or total >= self.armor_class(defender))
        self.record("attack", attacker=attacker.id, defender=defender.id, hit=hit, **attack)
        if hit:
            previous = self._damage_batch
            self._damage_batch = []
            on_hit(critical, attack)
            self.dispatch("on_attack_hit", attacker=attacker, defender=defender, attack=attack, critical=critical)
            batch = self._damage_batch
            self._damage_batch = previous
            self.flush_damage(batch)
        return hit

    def damage(self, target, amount, dtype, source=None, half=False):
        amount = max(0, int(amount))
        if self._damage_batch is not None:
            self._damage_batch.append((target, amount, dtype, source, half))
            return amount
        if half: amount //= 2
        amount = self.mitigate_damage(target, amount, dtype, source)
        self.apply_damage(target, amount, source)
        return amount

    def mitigate_damage(self, target, amount, dtype, source):
        if dtype in target.immunities: amount = 0
        else:
            if dtype in target.resistances or target.has_condition("petrified"): amount //= 2
            if dtype in target.vulnerabilities: amount *= 2
        self.record("damage", target=target.id, amount=amount, type=dtype, source=source.id if source else None)
        return amount

    def flush_damage(self, batch):
        components = defaultdict(int)
        sources = {}
        for target, amount, dtype, source, half in batch:
            components[target, dtype, half] += amount
            sources[target] = source
        typed = defaultdict(int)
        for (target, dtype, half), amount in components.items():
            typed[target, dtype] += amount // 2 if half else amount
        grouped = defaultdict(int)
        for (target, dtype), amount in typed.items():
            grouped[target] += self.mitigate_damage(target, amount, dtype, sources[target])
        for target, amount in grouped.items(): self.apply_damage(target, amount, sources[target])

    def apply_damage(self, target, amount, source=None):
        before = target.hp
        absorbed = min(target.temp_hp, amount)
        target.temp_hp -= absorbed
        target.hp = max(0, target.hp - (amount - absorbed))
        if before > 0 and target.hp == 0:
            target.conditions.update({"unconscious", "prone"})
            for instance in self.instances.values():
                for binding in instance.bindings.values():
                    if target in binding.targets:
                        binding.target_dropped_to_zero = True
                        binding.drop_turn = self.turn_index
        if target.concentration is not None:
            if target.has_condition("incapacitated") or not target.alive:
                self.end_spell(target.concentration)
            elif amount and not self.saving_throw(target, "con", min(30, max(10, amount // 2))):
                self.end_spell(target.concentration)
        if amount: self.dispatch("on_damaged", who=target, attacker=source, defender=target)

    def heal(self, target, amount):
        target.hp = min(target.max_hp, target.hp + max(0, int(amount)))
        if target.hp > 0: target.conditions.discard("unconscious")

    def context(self, instance, target=None, event="on_cast", trigger=None, **extra):
        ctx = {"caster": instance.caster, "target": target, "spell": instance,
               "turn": SimpleNamespace(index=self.turn_index), "event": event,
               "trigger": trigger or {}, **instance.bindings,
               **{"$" + k: v for k, v in instance.choices.items()},
               **{k: v for k, v in extra.items() if k not in {"caster", "spell", "target", "event", "trigger"}}}
        return ctx

    def event_matches(self, expression, instance, event, frame):
        ctx = self.context(instance, event=event, trigger=frame, **{k: v for k, v in frame.items() if k != "trigger"})
        # In subscriptions only, bare event names mean event predicates.
        ctx["_subscription"] = True
        ctx["target"] = instance.target or "target"
        def match(name, args):
            if name != event: return False
            if name == "end_of_turn_in_aura": return True  # membership is resolved per block
            if name in {"start_of_turn", "end_of_turn", "on_damaged", "on_attacked", "end_of_turn_in_aura"}:
                who = args[0]
                if who in ("target", "affected") or isinstance(who, list):
                    return frame.get("who") in [x for b in instance.bindings.values() for x in b.targets]
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
        if spec["level"] == 0: return 0
        if spec["name"] in actor.innate_spells: return spec["level"] if actor.limited_uses.get(spec["name"], 0) > 0 else None
        return next((n for n in sorted(actor.spell_slots) if n >= spec["level"] and actor.spell_slots[n] > 0), None)

    def can_cast(self, actor, name, slot=None):
        if name not in self.spells or name not in actor.spells or not actor.alive or actor.has_condition("incapacitated"): return False
        spec = self.spells[name]
        kind = spec["casting_time"]
        if kind not in {"action", "bonus_action", "reaction"} or getattr(actor, kind) < 1: return False
        if kind == "action" and actor.action <= actor.surge_actions: return False
        if kind != "reaction" and self.current is not actor: return False
        innate = name in actor.innate_spells
        if spec["level"] and not innate and actor.slot_cast_turn == self.turn_index: return False
        available = self.available_slot(actor, spec) if slot is None else slot
        if available is None or available < spec["level"]: return False
        if innate and available != spec["level"]: return False
        if not spec["level"]: return available == 0
        return actor.limited_uses.get(name, 0) > 0 if innate else actor.spell_slots.get(available, 0) > 0

    def scale(self, actor, spec, slot):
        return scaled_spell(spec, slot or spec["level"], actor.level)

    def cast(self, caster, name, targets=None, slot=None, choices=None, trigger=None):
        if not self.can_cast(caster, name, slot): return None
        spec = self.spells[name]
        slot = self.available_slot(caster, spec) if slot is None else slot
        spec = self.scale(caster, spec, slot)
        instance = SpellInstance(0, spec, caster, slot, self.turn_index, self.time_rounds)
        for choice in spec["choices"]:
            ctx = self.context(instance)
            options = [v for v in choice["options"] if v not in choice.get("option_conditions", {}) or evaluate(choice["option_conditions"][v], ctx)]
            selected = (choices or {}).get(choice["id"], self.policy.choose(self, caster, choice, options) if options else None)
            if selected not in options: raise ValueError(f"illegal choice {choice['id']}: {selected}")
            instance.choices[choice["id"]] = selected
        instance.exclusions = {x.id for x in self.policy.exemptions(self, caster)}
        # Reject explicit illegal input before spending anything or offering reactions.
        if targets is not None:
            for block in spec["effects"]:
                if block["target"]["select"] not in {"single", "n_targets"}: continue
                if not self.event_matches(block["event"], instance, "on_cast", trigger or {}): continue
                if "if" in block and not any(evaluate(block["if"], self.context(instance, target, trigger=trigger)) for target in targets): continue
                self.select_targets(instance, block, trigger or {}, targets)
        kind = spec["casting_time"]
        setattr(caster, kind, getattr(caster, kind) - 1)
        if spec["concentration"] and caster.concentration is not None:
            self.end_spell(caster.concentration)
        # Ending self-Haste (or a reaction) can make this casting impossible.
        if caster.has_condition("incapacitated") or not caster.alive: return None
        pending = {"caster": caster, "spell": spec, "targets": targets or [], "cancelled": False}
        innate = name in caster.innate_spells
        previous_slot_turn = caster.slot_cast_turn
        if innate:
            caster.limited_uses[name] -= 1
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
        instance.id = self.next_instance
        self.next_instance += 1
        self.instances[instance.id] = instance
        if spec["concentration"]: caster.concentration = instance.id
        instance.ends = [self.boundary(x, instance, caster) for x in spec["ends_on"]]
        self.record("cast", caster=caster.id, spell=name, slot=slot)
        for block in spec["effects"]:
            if self.event_matches(block["event"], instance, "on_cast", trigger or {}):
                self.resolve_block(instance, block, "on_cast", trigger or {}, targets)
        self.refresh_areas(instance)
        if spec["duration"]["type"] == "instant": self.end_spell(instance.id)
        return instance

    def offer_reactions(self, event, **frame):
        # Shared pending frame: a nested Counterspell sets cancelled on this object.
        self.dispatch(event, **frame)
        for actor in self.combatants:
            for name in actor.spells:
                spec = self.spells.get(name)
                if not spec or spec["casting_time"] != "reaction" or not self.can_cast(actor, name): continue
                probe = SpellInstance(-1, spec, actor, spec["level"], self.turn_index, self.time_rounds)
                if not self.event_matches(spec["reaction_trigger"], probe, event, frame): continue
                if not self.policy.reaction(self, actor, spec, frame): continue
                self.cast(actor, name, trigger=frame)
        return frame

    def eligible(self, instance, block):
        target = block["target"]
        caster = instance.caster
        binding = instance.bindings.get(block["id"], Binding())
        result = []
        for creature in self.combatants:
            if creature.removed or creature.permanently_removed: continue
            healing = any("heal" in p for p in block["apply"])
            if not creature.alive and not healing: continue
            affects = target.get("affects", "any")
            if affects in {"enemy", "enemies"} and creature.team == caster.team: continue
            if affects == "ally" and creature.team != caster.team: continue
            filters = target.get("filter", [])
            harmful = bool(block["on_hit"] or block["on_fail"] or any(k in p for p in block["apply"] for k in ("damage", "apply_condition", "remove_from_combat")))
            if harmful and creature in self.condition_sources(caster, "charmed"): continue
            if "humanoid" in filters and creature.creature_type != "humanoid": continue
            if "creature" in filters and creature.creature_type == "object": continue
            if "object" in filters and creature.creature_type != "object": continue
            if "visible" in filters and not creature.visible_to(caster): continue
            if "willing" in filters and not creature.willing: continue
            if "new_target" in filters and creature in binding.targets: continue
            if target.get("shape") == "emanation" and creature is caster: continue
            if target.get("exclude") == "designated_on_cast" and creature.id in instance.exclusions: continue
            result.append(creature)
        return result

    def select_targets(self, instance, block, frame, explicit=None):
        target = block["target"]
        kind = target["select"]
        if kind == "self": return [instance.caster]
        if kind == "ref":
            ref = target["ref"]
            if ref == "trigger.caster": return [frame["caster"]]
            if ref == "spell_target":
                value = instance.target
                return value if isinstance(value, list) else [value] if value else []
            return instance.bindings.get(ref, Binding()).targets[:]
        eligible = self.eligible(instance, block)
        if kind == "area":
            cached = instance.area_members.get(block["id"])
            members = [c for c in cached if c in eligible] if cached is not None else self.area_members(instance, block, eligible)
            if frame.get("who") is not None: return [frame["who"]] if frame["who"] in members else []
            return members
        n = target.get("n", 1)
        selected = list(explicit) if explicit is not None else self.policy.targets(self, instance, block, eligible, n)
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
        count = self.area(target["shape"], target["size_ft"], len(eligible))
        if isinstance(count, int):
            if not 0 <= count <= len(eligible): raise ValueError("area heuristic returned invalid count")
            # Policy determines placement/order; it does not change legal allegiance.
            ordered = self.policy.targets(self, instance, block, eligible, len(eligible))
            # An area may include allies: unlike optional individual targets, fill it.
            ordered += [x for x in eligible if x not in ordered]
            return ordered[:count]
        indices = list(count)
        if len(set(indices)) != len(indices) or any(type(i) is not int or not 0 <= i < len(eligible) for i in indices): raise ValueError("invalid area indices")
        return [eligible[i] for i in indices]

    def resolve_block(self, instance, block, event, frame, explicit=None):
        if not instance.active: return False
        if block.get("optional") and not self.policy.optional(self, instance, block): return False
        targets = self.select_targets(instance, block, frame, explicit)
        if "if" in block:
            targets = [t for t in targets if evaluate(block["if"], self.context(instance, t, event, frame, **frame))]
        if not targets: return False
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
        shared = {} if block.get("damage_roll") == "shared" else None
        deferred = [] if block.get("resolution") == "simultaneous" else None
        performed = False
        for target in targets:
            if not instance.active: break
            ctx = self.context(instance, target, event, frame, **frame)
            if event not in {"on_cast", "while_in_area"} and not self.spell_applies(instance, target, event, frame): continue
            key = (block["id"], self.turn_index, target.id if block["limit"] == "once_per_turn_per_target" else None)
            if block["limit"] and key in instance.limits: continue
            if block["limit"]: instance.limits.add(key)
            performed = True
            if block["attack"]:
                self.attack(instance.caster, target, instance.caster.spell_attack_bonus,
                    lambda crit, attack, t=target, c=ctx: self.execute(instance, t, block["on_hit"], {**c, "attacker": instance.caster, "defender": t, "critical": crit, "attack": attack}, block["id"], shared=shared),
                    melee=block["attack"]["type"] == "melee_spell")
            else:
                previous_batch = self._damage_batch
                self._damage_batch = []
                if block["save"]:
                    save = block["save"]
                    success = self.saving_throw(target, save["ability"], instance.caster.spell_dc, save.get("ignore_cover"))
                    if not success: self.execute(instance, target, block["on_fail"], ctx, block["id"], shared=shared)
                    else:
                        if save["on_success"] == "half": self.execute(instance, target, block["on_fail"], ctx, block["id"], half=True, shared=shared)
                        self.execute(instance, target, block["on_success"], ctx, block["id"], shared=shared)
                else: self.execute(instance, target, block["apply"], ctx, block["id"], shared=shared)
                batch = self._damage_batch
                self._damage_batch = previous_batch
                if deferred is not None: deferred.append(batch)
                elif previous_batch is not None: previous_batch.extend(batch)
                else: self.flush_damage(batch)
        if deferred is not None:
            # All darts roll before damage; each dart remains its own instance.
            for batch in deferred: self.flush_damage(batch)
        return performed

    def boundary(self, expression, instance, target):
        node = parse(expression)
        event = node[1][1]
        actor_name = node[2][0][1][1]
        actor = instance.caster if actor_name == "caster" else target
        return event, actor.id, actor.turns_taken + 1

    def execute(self, instance, target, primitives, ctx, block, half=False, shared=None):
        for primitive in primitives:
            if not instance.active and block != "after_end": break
            if "if" in primitive and not evaluate(primitive["if"], ctx): continue
            key = next(k for k in primitive if k not in {"if", "until"})
            value = primitive[key]
            if half and key != "damage": continue
            if key in {"damage", "heal", "temp_hp"}:
                bonus = value.get("bonus", 0)
                if bonus == "spell_mod": bonus = instance.caster.spell_mod
                cache_key = (value.get("dice"), bonus)
                if shared is not None and cache_key in shared: amount = shared[cache_key]
                else:
                    amount = dice.roll(self.rng, value["dice"], bool(ctx.get("critical")) and key == "damage") + bonus if "dice" in value else value["amount"]
                    if key == "damage": amount = self.modifier(instance.caster, "damage_roll", amount)
                    if shared is not None: shared[cache_key] = amount
                if key == "damage":
                    dtype = value["type"]
                    if dtype.startswith("$"): dtype = instance.choices[dtype[1:]]
                    self.damage(target, amount, dtype, instance.caster, half=half)
                elif key == "heal": self.heal(target, amount)
                else: target.temp_hp = max(target.temp_hp, amount)
            elif key == "end_spell": self.end_spell(instance.id)
            elif key == "counter_spell": ctx["trigger"]["cancelled"] = True
            elif key == "on_spell_end": instance.end_callbacks.append((target, value))
            else:
                if key == "apply_condition" and value["condition"] in target.condition_immunities: continue
                data = dict(value)
                if isinstance(data.get("scope"), str) and data["scope"].startswith("$"): data["scope"] = instance.choices[data["scope"][1:]]
                effect = Effect(key, data, instance.id, block,
                    self.boundary(primitive["until"], instance, target) if "until" in primitive else None, data.get("uses"))
                # Continuous effects replace rather than stack on redispatch.
                target.effects = [e for e in target.effects if not (e.source == instance.id and e.block == block and e.kind == key and e.data == data)]
                target.effects.append(effect)
                self.refresh_spell_effects()
                if key == "remove_from_combat": target.removed = True
                if key == "apply_condition" and target.has_condition("incapacitated") and target.concentration is not None:
                    self.end_spell(target.concentration)

    def remove_effects(self, instance, target=None, block=None):
        for actor in ([target] if target else self.combatants):
            actor.effects = [e for e in actor.effects if not (e.source == instance.id and (block is None or e.block == block))]
        self.refresh_spell_effects()

    def end_spell(self, identifier):
        instance = self.instances.get(identifier)
        if instance is None or not instance.active: return
        instance.active = False
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
                key = (target["shape"], target["size_ft"], target.get("origin"), target.get("exclude"), target["affects"], tuple(target.get("filter", [])))
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
            instance.elapsed_minutes = round((self.time_rounds - instance.cast_round) / 10, 10)
            for block in instance.spec["effects"]:
                if not instance.active: break
                if self.event_matches(block["event"], instance, event, frame):
                    self.resolve_block(instance, block, event, frame)

    def command(self, instance, event="bonus_action_command", targets=None):
        actor = instance.caster
        kind = "bonus_action" if event == "bonus_action_command" else "action"
        if event not in {"bonus_action_command", "action_command"} or self.current is not actor or not actor.alive or actor.has_condition("incapacitated") or getattr(actor, kind) < 1: return False
        performed = False
        for block in instance.spec["effects"]:
            if self.event_matches(block["event"], instance, event, {}):
                if self.resolve_block(instance, block, event, {}, targets):
                    performed = True
        if performed: setattr(actor, kind, getattr(actor, kind) - 1)
        return performed

    def expire(self, event, actor):
        def due(boundary):
            return boundary and boundary[0] == event and boundary[1] == actor.id and actor.turns_taken >= boundary[2]
        for instance in list(self.instances.values()):
            if not instance.active: continue
            duration = instance.spec["duration"]
            units = {"rounds": 1, "minutes": 10, "hours": 600}
            timed = not instance.ends and duration["type"] in units and self.time_rounds - instance.cast_round + 1e-9 >= duration.get("n", 0) * units.get(duration["type"], 0)
            if timed or any(due(x) for x in instance.ends): self.end_spell(instance.id)
        for creature in self.combatants:
            creature.effects = [e for e in creature.effects if not due(e.until)]
        self.refresh_spell_effects()

    def begin_turn(self, actor):
        self.current = actor
        self.turn_index += 1
        actor.turns_taken += 1
        actor.action = actor.bonus_action = actor.reaction = 1
        actor.surge_actions = 0
        actor.extra_actions = []
        actor.action_grants.clear()
        if actor.concentration is not None and (actor.has_condition("incapacitated") or not actor.alive):
            self.end_spell(actor.concentration)
        self.expire("start_of_turn", actor)
        self.grant_current_actions(actor)
        actor.action = int(self.modifier(actor, "action_count", actor.action))
        for action in actor.actions:
            if "recharge" in action and not actor.recharge_ready.get(action["name"], True):
                actor.recharge_ready[action["name"]] = self.rng.randint(1, 6) >= action["recharge"]
        self.repeat_saves(actor, "start_of_turn")
        self.refresh_areas()
        self.dispatch("start_of_turn", who=actor)
        self.record("turn_start", actor=actor.id, round=self.round)

    def repeat_saves(self, actor, timing):
        for effect in list(actor.effects):
            repeat = effect.data.get("repeat_save") if effect.kind == "apply_condition" else None
            instance = self.instances.get(effect.source)
            if repeat and repeat["timing"] == timing and instance and instance.active:
                if self.saving_throw(actor, repeat["ability"], instance.caster.spell_dc):
                    self.remove_effects(instance, actor)
                    for binding in instance.bindings.values():
                        if actor in binding.targets: binding.targets.remove(actor)

    def end_turn(self, actor):
        self.dispatch("end_of_turn", who=actor)
        self.dispatch("end_of_turn_in_aura", who=actor)
        self.repeat_saves(actor, "end_of_turn")
        self.expire("end_of_turn", actor)
        self.time_rounds += 1 / max(1, len(self.combatants))
        self.current = None

    def weapon_attack(self, actor, target, attack):
        def hit(critical, roll):
            instance = SpellInstance(0, {"name": attack["name"]}, actor, 0, self.turn_index, self.time_rounds)
            frame = {"attacker": actor, "defender": target, "attack": roll, "critical": critical}
            self.execute(instance, target, attack["effects"], self.context(instance, target, "on_attack_hit", frame, **frame), "weapon")
            if attack.get("mastery") == "sap":
                target.effects.append(Effect("disadvantage", {"on": "attack_rolls", "scope": "all", "against": None}, 0, "sap", ("start_of_turn", actor.id, actor.turns_taken + 1), uses=1))
            if attack.get("mastery") == "vex":
                # Restricted to this attacker's next attack against the target.
                actor.statuses["vex"] = {"target": target.id, "expires": actor.turns_taken + 1}
        vex = actor.statuses.pop("vex", None)
        extra = None
        if vex and vex["target"] == target.id and actor.turns_taken <= vex["expires"]:
            extra = Effect("advantage", {"on": "attack_rolls", "scope": "all", "against": None}, 0, "vex", uses=1)
            actor.effects.append(extra)
        success = self.attack(actor, target, attack["to_hit"], hit, attack.get("kind", "melee") == "melee")
        if not success and attack.get("mastery") == "graze":
            self.damage(target, max(0, actor.mod(attack.get("ability", "str"))), attack["effects"][0]["damage"]["type"], actor)
        if extra in actor.effects: actor.effects.remove(extra)
        return success

    def weapon_action(self, actor, granted=None):
        if not actor.alive or actor.has_condition("incapacitated") or not actor.attacks or (not granted and actor.action < 1): return False
        if not granted:
            actor.action -= 1
            if actor.surge_actions: actor.surge_actions -= 1
        self.record("action", actor=actor.id, name="Attack", granted=bool(granted))
        names = actor.multiattack or [actor.attacks[0]["name"]] * actor.extra_attack
        if granted: names = names[:granted.get("attack_limit", 1)]
        for name in names:
            enemies = self.enemies(actor)
            if not enemies: break
            target = min(enemies, key=lambda c: (c.hp, c.id))
            self.weapon_attack(actor, target, next(a for a in actor.attacks if a["name"] == name))
        return True

    def action_available(self, actor, action):
        if not actor.alive or actor.has_condition("incapacitated"): return False
        if self.current is not actor: return False
        if action["cost"] != "free" and getattr(actor, action["cost"]) < 1: return False
        if action.get("resource") and actor.limited_uses.get(action["resource"], 0) < 1: return False
        return actor.recharge_ready.get(action["name"], True)

    def use_action(self, actor, name, targets=None):
        action = next(a for a in actor.actions + actor.traits if a["name"] == name)
        if not self.action_available(actor, action): return False
        self.record("action", actor=actor.id, name=name)
        if action["cost"] != "free": setattr(actor, action["cost"], getattr(actor, action["cost"]) - 1)
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
        spec = {"name": name, "duration": {"type": "instant"}, "effects": action["effects"], "ends_on": []}
        inst = SpellInstance(self.next_instance, spec, actor, 0, self.turn_index, self.time_rounds)
        self.next_instance += 1
        self.instances[inst.id] = inst
        for block in action["effects"]: self.resolve_block(inst, block, "on_cast", {}, targets)
        for creature in self.combatants:
            for effect in creature.effects:
                if effect.source == inst.id and effect.until: effect.source = -inst.id
        self.end_spell(inst.id)
        return True

    def hit_probability(self, actor, target, bonus):
        return min(.95, max(.05, (21 + bonus - self.armor_class(target)) / 20))

    def expected_weapon_damage(self, actor, target):
        if not actor.attacks: return 0
        total = 0
        names = actor.multiattack or [actor.attacks[0]["name"]] * actor.extra_attack
        for name in names:
            attack = next(a for a in actor.attacks if a["name"] == name)
            expected = sum(dice.mean(p["damage"]["dice"]) + p["damage"].get("bonus", 0) for p in attack["effects"] if "damage" in p and "if" not in p)
            total += expected * self.hit_probability(actor, target, attack["to_hit"])
            if attack.get("mastery") == "graze": total += max(0, actor.mod("str")) * (1 - self.hit_probability(actor, target, attack["to_hit"]))
        return total

    def expected_spell_damage(self, actor, spec, target):
        total = 0
        for block in spec["effects"]:
            damage = sum(dice.mean(p["damage"]["dice"]) + (actor.spell_mod if p["damage"]["bonus"] == "spell_mod" else p["damage"]["bonus"]) for key in ("on_hit", "on_fail", "apply") for p in block[key] if "damage" in p)
            if not damage: continue
            if block["attack"]: damage *= self.hit_probability(actor, target, actor.spell_attack_bonus)
            if block["save"]:
                ability = block["save"]["ability"]
                bonus = target.save_bonuses.get(ability, target.mod(ability) + (target.proficiency_bonus if ability in target.save_proficiencies else 0))
                fail = min(1, max(0, (actor.spell_dc - bonus - 1) / 20))
                damage *= fail + ((1 - fail) / 2 if block["save"]["on_success"] == "half" else 0)
            t = block["target"]
            if t["select"] == "n_targets": damage *= t["n"]
            if t["select"] == "area":
                count = self.area(t["shape"], t["size_ft"], len(self.enemies(actor)))
                damage *= count if isinstance(count, int) else len(count)
            if block["event"] != "on_cast" and "on_cast" not in block["event"]:
                if "end_of_turn_in_aura" in block["event"]: damage *= 2  # two-turn planning horizon
                else: damage = 0
            total += damage
        return total

    def expected_action_damage(self, actor, action, target):
        return self.expected_spell_damage(actor, {"effects": action["effects"]}, target)

    def run(self, max_rounds=100):
        initiative = sorted(self.combatants, key=lambda c: (-(dice.d20(self.rng) + c.mod("dex") + c.initiative_bonus), c.id))
        self.record("initiative", order=[c.id for c in initiative])
        for round_number in range(1, max_rounds + 1):
            self.round = round_number
            for actor in initiative:
                self.begin_turn(actor)
                self.policy.take_turn(self, actor)
                self.end_turn(actor)
                teams = {c.team for c in self.combatants if c.alive}
                if len(teams) <= 1:
                    return {"winner": next(iter(teams), None), "rounds": round_number, "hp": self.party_hp(), "resources": self.resources()}
        return {"winner": None, "rounds": max_rounds, "hp": self.party_hp(), "resources": self.resources()}

    def party_hp(self):
        return sum(c.hp for c in self.combatants if c.team == "party" and not c.permanently_removed and not c.removed)

    def resources(self):
        result = Counter()
        for c in self.combatants:
            if c.team == "party": result.update(c.resources_spent)
        return dict(result)
