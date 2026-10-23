"""Replace Policy or area_heuristic without changing spell resolution."""
import math

from .dice import mean
from .state import SpellInstance


FEET_PER_TARGET = {"cone": 10, "line": 30}  # every other shape: 5


def area_heuristic(shape: str, size_ft: float, eligible: int) -> int:
    """No-grid AoE rule from the DMG "Targets in Areas of Effect" table.

    Cone size/10, line length/30, sphere/cylinder/emanation radius/5 and cube
    size/5, rounded up, at least one, capped by the eligible creatures.
    Returns a count; a custom heuristic may instead return indices into the
    eligible list. Placement and ordering remain policy decisions.
    """
    return min(eligible, max(1, math.ceil(size_ft / FEET_PER_TARGET.get(shape, 5))))


class Policy:
    def reroll_die(self, combat, actor, natural):
        values = getattr(natural, "values", (natural,))
        return min(range(len(values)), key=values.__getitem__)

    def healing_pool(self, combat, instance, targets, amount):
        allocations = dict.fromkeys((t.id for t in targets), 0)
        ordered = sorted(targets, key=lambda t: (t.hp != 0, t.hp / max(1, t.max_hp), t.id))
        # First buy as many revivals as possible; then spread the remaining pool.
        for t in ordered:
            if amount and t.hp == 0 and t.max_hp >= 2:
                allocations[t.id] += 1
                amount -= 1
        while amount:
            eligible = [t for t in ordered if t.hp + allocations[t.id] < t.max_hp // 2]
            if not eligible: break
            t = min(eligible, key=lambda t: ((t.hp + allocations[t.id]) / t.max_hp, t.id))
            allocations[t.id] += 1
            amount -= 1
        return allocations

    def allow_action(self, combat, actor, action):
        return True

    def weapon_target(self, combat, actor, enemies):
        target = combat.monster_target(actor, enemies)
        if target is not None: return target
        active=[c for c in enemies if not c.has_condition("incapacitated")] if "armored" in actor.features or actor.features.get("sneak_attack") else enemies
        candidates=active or enemies
        if actor.features.get("sneak_attack"):
            return max(candidates,key=lambda c:(combat.expected_weapon_damage(actor,c),-c.hp,c.id))
        return min(candidates,key=lambda c:(c.hp,c.id))

    def memorize_spell(self, actor):
        if "Fireball" in actor.spellbook and "Fireball" not in actor.spells and actor.prepared_spells:
            return actor.prepared_spells[-1], "Fireball"
        return None

    def sculpt_spells(self, combat, actor, eligible, n):
        return sorted(eligible, key=lambda t: (t.hp, t.id))[:n]

    def arcane_recovery(self, actor, budget):
        selected = {}
        for level in sorted(actor.max_spell_slots, reverse=True):
            if level > 5: continue
            count = min(actor.max_spell_slots[level] - actor.spell_slots.get(level,0), budget // level)
            if count: selected[level] = count
            budget -= level * count
        return selected

    def indomitable(self, combat, actor, ability, dc):
        return True

    def tactical_mind(self, combat, actor, ability, dc):
        return True

    def tactical_master(self, combat, actor, attack, target):
        if any(e.block=="sap" for e in target.active_effects): return None
        prevented=combat.expected_weapon_damage(target,actor)*.3
        lost_graze=max(0,actor.mod(attack.get("ability","str")))*(1-combat.hit_probability(actor,target,attack["to_hit"])) if attack.get("mastery")=="graze" else 0
        return "sap" if prevented>lost_graze and target.attacks else None

    def cunning_strike(self, combat, actor, target, options):
        if "poison" in options and "poisoned" not in target.condition_immunities and not target.has_condition("poisoned") and target.hp > 12 and target.attacks:
            return "poison"
        if "trip" in options and target.size in {"T", "S", "M", "L"} and not target.has_condition("prone") and sum(c.team == actor.team and c.alive and any(a["kind"] == "melee" for a in c.attacks) for c in combat.combatants) >= 2:
            return "trip"
        return None

    def command_summon(self, combat, caster, creature):
        return True

    def legendary_resistance(self, combat, actor, ability, dc):
        return True

    def redirect_attack(self, combat, actor, allies):
        return max(allies, key=lambda c: c.hp, default=None)

    def legendary_action(self, combat, actor, finished, options):
        def value(option):
            target = combat.enemies(actor)[0]
            if "attacks" in option: return combat.routine_value(actor, option["attacks"], target)
            if "spell" in option: return combat.expected_spell_damage(actor, combat.scale(actor, combat.spells[option["spell"]], actor.spell_levels.get(option["spell"])), target, horizon=1)
            return combat.expected_action_damage(actor, option, target)
        return max(options, key=value, default=None)

    def monster_routine(self, combat, actor, target, options):
        return max(options, key=lambda names: combat.routine_value(actor, names, target, control=True), default=[])

    def monster_replacements(self, combat, actor, names):
        if not names or not combat.enemies(actor): return names
        target = combat.enemies(actor)[0]
        best = max(actor.replacements, key=lambda name: combat.routine_value(actor, [name], target))
        if combat.routine_value(actor, [best], target) > combat.routine_value(actor, [names[-1]], target):
            return names[:-1] + [best]
        return names

    def slot(self, combat, actor, spec, slots):
        return slots[0]

    def allow_spell(self, combat, actor, spec):
        return True

    def allow_healing(self, combat, actor, target):
        return True

    def allow_surge(self, combat, actor):
        return True

    def spend_hit_die(self, actor):
        return actor.hp < actor.max_hp

    def recover_downed(self, combat, party):
        """One successful heal per downed ally, not a free full-party top-up."""
        for target in party:
            if target.dead or target.hp != 0 or target.permanently_removed: continue
            for healer in party:
                if not healer.alive: continue
                combat.begin_turn(healer)
                def eligible_heal(spec):
                    probe = SpellInstance(0, spec, healer, 0, combat.turn_index, combat.time_rounds)
                    return any(b["target"]["select"] in {"single", "n_targets"}
                               and any("heal" in p or "heal_pool" in p for p in b["apply"])
                               and target in combat.eligible(probe, b) for b in spec["effects"])

                name = next((name for name in ("Cure Wounds", "Healing Word")
                             if combat.can_cast(healer, name) and eligible_heal(combat.spells[name])), None)
                if name:
                    combat.cast(healer, name, targets=[target])
                    if getattr(combat,"day_options",None): combat.advance_time(1)
                else:
                    # Only explicitly ally-targetable healing features can rescue another PC.
                    action = next((a for a in sorted(healer.actions, key=lambda a: a["name"] != "Preserve Life") if combat.action_available(healer, a)
                                   and eligible_heal(a)), None)
                    if action:
                        combat.use_action(healer, action["name"], None if action["name"] == "Preserve Life" else [target])
                        if getattr(combat,"day_options",None): combat.advance_time(1)
                if target.hp > 0: break

    def choose(self, combat, caster, choice, eligible):
        return eligible[0]

    def targets(self, combat, instance, block, eligible, n):
        beneficial = any(k in p for key in ("apply", "on_hit") for p in block[key] for k in ("heal", "heal_pool", "temp_hp", "grant_action", "base_ac", "defense", "remove_condition")) or any(p.get("apply_condition", {}).get("condition") == "invisible" for p in block["apply"]) or instance.spec.get("name") in {"Bless", "Shield of Faith", "Haste", "Fly"}
        # Allegiance-neutral legality stays in the engine; this is preference only.
        preferred = [x for x in eligible if (x.team == instance.caster.team) == beneficial]
        ordered = sorted(preferred or eligible, key=lambda x: (x.hp / max(1,x.max_hp) if beneficial else x.hp, x.id))
        if not beneficial and instance.caster.team != "party" and getattr(combat, "day_options", None):
            candidates = preferred or eligible
            ordered = []
            while candidates:
                # EV probes never draw targeting randomness.
                chosen = min(candidates,key=lambda c:c.id) if instance.id == 0 and combat.day_options.targeting == "random" else combat.monster_target(instance.caster, candidates)
                ordered.append(chosen)
                candidates = [c for c in candidates if c is not chosen]
        if not ordered: return []
        if block["target"].get("distinct", True): return ordered[:n]
        return [ordered[0]] * n

    def precombat_buffs(self, combat, party, phase):
        """Policy hook at day start, after rests, and just before encounters."""
        for caster in party:
            if not caster.alive or caster.has_condition("incapacitated"): continue
            candidates = []
            for name in caster.spells:
                spec = combat.spells[name]
                if not spec["level"] or spec["casting_time"] != "action": continue
                if spec["concentration"] and caster.concentration is not None: continue
                slots = sorted(k for k, count in caster.spell_slots.items() if count and k >= spec["level"])
                # Evaluate actual slots, but do not upcast just because slots exist.
                for slot in slots[:1]:
                    scaled = combat.scale(caster, spec, slot)
                    value, targets = combat.expected_buff_prevention(caster, scaled)
                    value = combat.expected_spell_damage(caster, scaled, caster, precombat=True)
                    # Reserve an offensive/healing alternative for this slot.
                    threshold = 4 + 4 * slot
                    if isinstance(self, ConservativePolicy): threshold *= 1.25
                    if value >= threshold: candidates.append((value / (slot + 1), name, slot, targets))
            for _, name, slot, targets in sorted(candidates, reverse=True):
                if not caster.spell_slots.get(slot): continue
                spec = combat.scale(caster, combat.spells[name], slot)
                if spec["concentration"] and caster.concentration is not None: continue
                value, targets = combat.expected_buff_prevention(caster, spec)
                threshold = (4 + 4 * slot) * (1.25 if isinstance(self, ConservativePolicy) else 1)
                if value < threshold: continue
                combat.begin_turn(caster)
                if combat.can_cast(caster, name, slot):
                    result = combat.cast(caster, name, targets=targets, slot=slot)
                    if result:
                        combat.record("prebuff", caster=caster.id, spell=name, phase=phase, prevented_ev=value)
                        if combat.day_options.clock: combat.advance_time(1)
                combat.current = None

    def exemptions(self, combat, caster):
        return [c for c in combat.combatants if c.team == caster.team]

    def optional(self, combat, instance, block):
        return True

    def reaction(self, combat, reactor, spell, trigger):
        if spell["name"] == "Shield":
            attack = trigger.get("attack")
            return (not attack or (not attack.get("critical") and attack["total"] < combat.armor_class(reactor) + 5))
        if spell["name"] == "Counterspell":
            pending_caster = trigger["caster"]
            if pending_caster.team == reactor.team: return False
            con = pending_caster.save_bonuses.get("con", pending_caster.mod("con") + (pending_caster.proficiency_bonus if "con" in pending_caster.save_proficiencies else 0))
            if con + 1 >= reactor.spell_dc: return False
            # Control, buffs, healing and counter-counterspells can matter too.
            return any(block[key] for block in trigger["spell"]["effects"] for key in ("on_hit", "on_fail", "apply"))
        return True

    def take_turn(self, combat, actor):
        if not actor.alive or actor.has_condition("incapacitated"): return
        rules = combat.turn_rules(actor)
        if rules.get("no_action") and rules.get("no_bonus_action"): return
        enemies = combat.enemies(actor)
        if not enemies: return
        if combat.death_rules and combat.can_cast(actor,"Revivify"):
            dead = [c for c in combat.combatants if c.team == actor.team and combat.can_revive(c)]
            if dead: combat.cast(actor,"Revivify",targets=[dead[0]])
        if actor.has_status("burning"): combat.extinguish(actor)
        if actor.has_condition("restrained") or actor.has_condition("grappled") or actor.has_status("engulfed"):
            combat.escape(actor)
        if actor.has_condition("prone") and not actor.has_condition("grappled") and not actor.has_condition("restrained") and actor.speed > 0:
            actor.conditions.discard("prone")
            actor.effects = [e for e in actor.effects if not (e.kind == "apply_condition" and e.data["condition"] == "prone")]
            combat.record("stand", actor=actor.id)
        for option in actor.actions:
            if option["cost"] == "bonus_action" and any(b["on_fail"] or b["on_hit"] for b in option["effects"]) and combat.action_available(actor, option): combat.use_action(actor, option["name"])
        # Bonus-action healing leaves the action available for a cantrip/weapon.
        wounded = sorted([x for x in combat.combatants if x.team == actor.team and not x.dead and not x.removed and not x.permanently_removed and x.hp < x.max_hp / 2], key=lambda c: c.hp / c.max_hp)
        support=[a for a in actor.actions if a["name"] in {"Preserve Life","Divine Spark (Heal)"} and combat.action_available(actor,a) and self.allow_action(combat,actor,a)]
        if support and wounded:
            best=max(support,key=lambda a:combat.expected_action_damage(actor,a,enemies[0]))
            value=combat.expected_action_damage(actor,best,enemies[0])
            if value>combat.expected_weapon_damage(actor,enemies[0]) and (best["name"]=="Preserve Life" or not combat.can_cast(actor,"Healing Word")):
                combat.use_action(actor,best["name"])
        if wounded:
            if self.allow_healing(combat, actor, wounded[0]) and combat.can_cast(actor, "Healing Word"):
                combat.cast(actor, "Healing Word", targets=[wounded[0]])
            elif self.allow_healing(combat, actor, wounded[0]) and combat.can_cast(actor, "Cure Wounds"):
                combat.cast(actor, "Cure Wounds", targets=[wounded[0]])
        for action in actor.actions:
            if action.get("resource") == "second_wind" and actor.hp < actor.max_hp / 2:
                combat.use_action(actor, action["name"], [actor])
        # Keep concentration and command existing forces/marks rather than recast.
        for instance in list(combat.instances.values()):
            if instance.active and instance.caster is actor and actor.bonus_action:
                combat.command(instance, "bonus_action_command")
        aim=next((a for a in actor.actions if a["name"]=="Steady Aim"),None)
        if aim and actor.action and combat.action_available(actor,aim):
            target=self.weapon_target(combat,actor,combat.enemies(actor))
            adv,dis=combat.roll_flags(actor,"attack_rolls",against=target)
            if not adv or dis: combat.use_action(actor,"Steady Aim")
        if actor.action and actor.limited_uses.get("divine_intervention") and not any(actor.spell_slots.values()):
            from .builder import spell_options
            choices=spell_options("cleric",10)
            if wounded: combat.divine_intervention(actor,"Mass Cure Wounds")
            else:
                names=[n for n,s in choices.items() if s["level"] and s["casting_time"]!="reaction"]
                name=max(names,key=lambda n:combat.expected_spell_damage(actor,combat.scale(actor,choices[n],choices[n]["level"]),enemies[0]))
                combat.divine_intervention(actor,name)
        if actor.action and not actor.has_condition("incapacitated"):
            options = []
            weapon = combat.expected_weapon_damage(actor, enemies[0])
            if actor.routines: weapon = max(weapon, max(combat.routine_value(actor, r, enemies[0], control=True) for r in actor.routines))
            for name in actor.spells:
                if not combat.can_cast(actor, name): continue
                spec = combat.spells[name]
                if not self.allow_spell(combat, actor, spec): continue
                casting_time = actor.spell_costs.get(name, spec["casting_time"])
                if casting_time not in {"action", "bonus_action"}: continue
                if spec["concentration"] and actor.concentration is not None: continue
                slot = combat.available_slot(actor, spec)
                scaled = combat.scale(actor, spec, slot)
                value = combat.expected_spell_damage(actor, scaled, enemies[0])
                if value > 0:
                    # A bonus-action spell leaves the weapon routine available.
                    options.append((value + (weapon if casting_time == "bonus_action" else 0), name))
            for action in actor.actions:
                if combat.action_available(actor, action) and self.allow_action(combat,actor,action):
                    value = combat.expected_action_damage(actor, action, enemies[0])
                    if value: options.append((value, ("action", action["name"])))
            best = max(options, key=lambda x: x[0], default=(0, None))
            if best[0] > weapon:
                if isinstance(best[1], tuple): combat.use_action(actor, best[1][1])
                else: combat.cast(actor, best[1])
            else: combat.weapon_action(actor)
            if actor.action and combat.enemies(actor): combat.weapon_action(actor)
        # Action Surge is deliberately nova; it never bypasses slot-per-turn rules.
        surge = next((x for x in actor.actions if x.get("resource") == "action_surge"), None)
        if surge and self.allow_surge(combat, actor) and combat.enemies(actor) and combat.action_available(actor, surge):
            combat.use_action(actor, surge["name"])
            combat.weapon_action(actor)
        for extra in list(actor.extra_actions):
            if "attack" in extra["restricted_to"] and combat.enemies(actor) and not actor.has_condition("incapacitated"):
                actor.extra_actions.remove(extra)
                combat.weapon_action(actor, granted=extra)
        for trait in actor.traits + [a for a in actor.actions if a["name"]=="Cunning Action"]:
            if trait["name"] in {"Nimble Escape", "Cunning Action", "Deathless Agility"} and combat.action_available(actor, trait):
                combat.use_action(actor, trait["name"])


class NovaPolicy(Policy):
    def slot(self, combat, actor, spec, slots):
        return slots[-1]


class ConservativePolicy(Policy):
    def slot_value(self, combat, actor, spec, slot):
        scaled = combat.scale(actor, spec, slot)
        target = next(iter(combat.enemies(actor)), actor)
        value = combat.expected_spell_damage(actor, scaled, target)
        value += combat.expected_spell_damage(actor, scaled, actor, precombat=True)
        probe = SpellInstance(0, scaled, actor, slot, combat.turn_index, combat.time_rounds)
        for block in scaled["effects"]:
            heals = [p["heal"] for p in block["apply"] if "heal" in p]
            if not heals: continue
            for recipient in combat.select_targets(probe, block, {}):
                if recipient.dead: continue
                amount = 0
                for heal in heals:
                    base = mean(heal["dice"]) if "dice" in heal else heal["amount"]
                    bonus = heal.get("bonus", 0)
                    amount += (actor.spell_mod if base == "spell_mod" else base) + (actor.spell_mod if bonus == "spell_mod" else bonus)
                if actor.features.get("disciple_of_life"): amount += 2 + slot
                value += min(max(0, recipient.max_hp - recipient.hp), amount)
        return value

    def slot(self, combat, actor, spec, slots):
        if getattr(combat, "day_options", None) and combat.day_options.spending:
            turns = max(1, combat.expected_remaining_rounds(actor)) * max(1, getattr(combat, "encounters_remaining", 1))
            if sum(actor.spell_slots.values()) >= turns:
                scored = [(slot, self.slot_value(combat, actor, spec, slot)) for slot in sorted(slots)]
                best = max(value for slot, value in scored)
                return next(slot for slot, value in scored if math.isclose(value, best, rel_tol=1e-12, abs_tol=1e-9))
        return slots[0]

    def allow_action(self, combat, actor, action):
        if action.get("resource") != "channel_divinity": return True
        return self.emergency(combat,actor) or self.dangerous(combat,actor)

    def dangerous(self, combat, actor):
        allies = [c for c in combat.combatants if c.team == actor.team and not c.permanently_removed]
        if any(c.hp == 0 for c in allies): return True
        hp = sum(c.hp for c in allies)
        enemies = combat.enemies(actor)
        if not enemies: return False
        # Estimate a weapon/cantrip-only fight; no knowledge of future rolls.
        outgoing = 0
        for ally in allies:
            damage = combat.expected_weapon_damage(ally, enemies[0])
            for name in ally.spells:
                spec = combat.spells[name]
                if spec["level"] == 0:
                    damage = max(damage, combat.expected_spell_damage(ally, combat.scale(ally, spec, 0), enemies[0]))
            outgoing += damage
        rounds = sum(c.hp for c in enemies) / max(1, outgoing)
        incoming = sum(combat.expected_weapon_damage(enemy, ally) for enemy in enemies for ally in allies) / len(allies)
        # Include ready nonspell damage, notably the dragon's breath.
        for enemy in enemies:
            for action in enemy.actions:
                if combat.action_available(enemy, action):
                    incoming = max(incoming, combat.expected_action_damage(enemy, action, allies[0]))
        if getattr(combat, "day_options", None) and combat.day_options.spending:
            budget = hp / max(1, getattr(combat, "encounters_remaining", 1))
            return rounds * incoming > budget
        return rounds * incoming > hp * .35

    def emergency(self, combat, actor):
        threshold = .5 if getattr(combat, "day_options", None) and combat.day_options.spending else .25
        return any(c.team == actor.team and not c.dead and (c.hp == 0 or c.hp < c.max_hp * threshold) for c in combat.combatants)

    def allow_spell(self, combat, actor, spec):
        if spec["level"] == 0: return True
        if getattr(combat, "day_options", None) and combat.day_options.spending:
            remaining = max(1, getattr(combat, "encounters_remaining", 1))
            return (remaining == 1 or self.emergency(combat, actor) or self.dangerous(combat, actor)
                    or sum(actor.spell_slots.values()) >= remaining * max(1, combat.expected_remaining_rounds(actor)))
        if self.emergency(combat, actor): return True
        if not self.dangerous(combat, actor): return False
        remaining = max(1, getattr(combat, "encounters_remaining", 1))
        start = getattr(combat, "slots_at_start", {}).get(actor.id, actor.spell_slots)
        budget = math.ceil(sum(start.values()) / remaining)
        spent = sum(start.values()) - sum(actor.spell_slots.values())
        if spec["name"] in actor.innate_spells:
            return True  # daily innate counters have no slot budget
        return spent < budget

    def allow_healing(self, combat, actor, target):
        return target.hp < target.max_hp * (.5 if getattr(combat, "day_options", None) and combat.day_options.spending else .35)

    def allow_surge(self, combat, actor):
        return self.dangerous(combat, actor)

    def reaction(self, combat, reactor, spell, trigger):
        return ("level" not in spell or self.allow_spell(combat, reactor, spell)) and super().reaction(combat, reactor, spell, trigger)

    def spend_hit_die(self, actor):
        return actor.hp < actor.max_hp * .85


STRATEGIES = {"default": Policy, "nova": NovaPolicy, "conservative": ConservativePolicy}


def strategy_policy(name):
    if name not in STRATEGIES: raise ValueError(f"unknown strategy: {name}")
    return STRATEGIES[name]()
