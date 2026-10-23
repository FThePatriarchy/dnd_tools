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
            if target.hp != 0 or target.permanently_removed: continue
            for healer in party:
                if not healer.alive: continue
                combat.begin_turn(healer)
                def eligible_heal(spec):
                    probe = SpellInstance(0, spec, healer, 0, combat.turn_index, combat.time_rounds)
                    return any(b["target"]["select"] in {"single", "n_targets"}
                               and any("heal" in p for p in b["apply"])
                               and target in combat.eligible(probe, b) for b in spec["effects"])

                name = next((name for name in ("Cure Wounds", "Healing Word")
                             if combat.can_cast(healer, name) and eligible_heal(combat.spells[name])), None)
                if name:
                    combat.cast(healer, name, targets=[target])
                else:
                    # Only explicitly ally-targetable healing features can rescue another PC.
                    action = next((a for a in healer.actions if combat.action_available(healer, a)
                                   and eligible_heal(a)), None)
                    if action: combat.use_action(healer, action["name"], [target])
                if target.hp > 0: break

    def choose(self, combat, caster, choice, eligible):
        return eligible[0]

    def targets(self, combat, instance, block, eligible, n):
        beneficial = any(k in p for key in ("apply", "on_hit") for p in block[key] for k in ("heal", "temp_hp", "grant_action", "base_ac", "defense", "remove_condition")) or any(p.get("apply_condition", {}).get("condition") == "invisible" for p in block["apply"]) or instance.spec["name"] in {"Bless", "Shield of Faith", "Haste", "Fly"}
        # Allegiance-neutral legality stays in the engine; this is preference only.
        preferred = [x for x in eligible if (x.team == instance.caster.team) == beneficial]
        ordered = sorted(preferred or eligible, key=lambda x: (x.hp / x.max_hp if beneficial else x.hp, x.id))
        if not ordered: return []
        if block["target"].get("distinct", True): return ordered[:n]
        return [ordered[0]] * n

    def exemptions(self, combat, caster):
        return [c for c in combat.combatants if c.team == caster.team]

    def optional(self, combat, instance, block):
        return True

    def reaction(self, combat, reactor, spell, trigger):
        if spell["name"] == "Shield":
            attack = trigger.get("attack")
            return (not attack or (attack["natural"] != 20 and attack["total"] < combat.armor_class(reactor) + 5))
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
        wounded = sorted([x for x in combat.combatants if x.team == actor.team and not x.removed and x.hp < x.max_hp / 2], key=lambda c: c.hp / c.max_hp)
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
                if combat.action_available(actor, action):
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
        for trait in actor.traits:
            if trait["name"] in {"Nimble Escape", "Cunning Action", "Deathless Agility"} and combat.action_available(actor, trait):
                combat.use_action(actor, trait["name"])


class NovaPolicy(Policy):
    def slot(self, combat, actor, spec, slots):
        return slots[-1]


class ConservativePolicy(Policy):
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
        return rounds * incoming > hp * .35

    def emergency(self, combat, actor):
        return any(c.team == actor.team and (c.hp == 0 or c.hp < c.max_hp * .25) for c in combat.combatants)

    def allow_spell(self, combat, actor, spec):
        if spec["level"] == 0: return True
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
        return target.hp < target.max_hp * .35

    def allow_surge(self, combat, actor):
        return self.dangerous(combat, actor)

    def reaction(self, combat, reactor, spell, trigger):
        return self.allow_spell(combat, reactor, spell) and super().reaction(combat, reactor, spell, trigger)

    def spend_hit_die(self, actor):
        return actor.hp < actor.max_hp * .85


STRATEGIES = {"default": Policy, "nova": NovaPolicy, "conservative": ConservativePolicy}


def strategy_policy(name):
    if name not in STRATEGIES: raise ValueError(f"unknown strategy: {name}")
    return STRATEGIES[name]()
