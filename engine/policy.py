"""Replace Policy or area_heuristic without changing spell resolution."""
from .dice import mean


def area_heuristic(shape: str, size_ft: float, eligible: int) -> int:
    """One no-grid AoE rule: one creature per 5 feet of radius/length.

    Returns a count; a custom heuristic may instead return indices into the
    eligible list. Placement and ordering remain policy decisions.
    """
    return min(eligible, max(1, int(size_ft // 5)))


class Policy:
    def choose(self, combat, caster, choice, eligible):
        return eligible[0]

    def targets(self, combat, instance, block, eligible, n):
        beneficial = any(k in p for key in ("apply", "on_hit") for p in block[key] for k in ("heal", "temp_hp", "grant_action")) or instance.spec["name"] in {"Bless", "Shield of Faith", "Haste"}
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
        enemies = combat.enemies(actor)
        if not enemies: return
        # Bonus-action healing leaves the action available for a cantrip/weapon.
        wounded = sorted([x for x in combat.combatants if x.team == actor.team and not x.removed and x.hp < x.max_hp / 2], key=lambda c: c.hp / c.max_hp)
        if wounded:
            if combat.can_cast(actor, "Healing Word"):
                combat.cast(actor, "Healing Word", targets=[wounded[0]])
            elif combat.can_cast(actor, "Cure Wounds"):
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
            for name in actor.spells:
                if not combat.can_cast(actor, name): continue
                spec = combat.spells[name]
                if spec["casting_time"] not in {"action", "bonus_action"}: continue
                if spec["concentration"] and actor.concentration is not None: continue
                slot = combat.available_slot(actor, spec)
                scaled = combat.scale(actor, spec, slot)
                value = combat.expected_spell_damage(actor, scaled, enemies[0])
                if value > 0:
                    # A bonus-action spell leaves the weapon routine available.
                    options.append((value + (weapon if spec["casting_time"] == "bonus_action" else 0), name))
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
        if surge and combat.enemies(actor) and combat.action_available(actor, surge):
            combat.use_action(actor, surge["name"])
            combat.weapon_action(actor)
        for extra in list(actor.extra_actions):
            if "attack" in extra["restricted_to"] and combat.enemies(actor) and not actor.has_condition("incapacitated"):
                actor.extra_actions.remove(extra)
                combat.weapon_action(actor, granted=extra)
        for trait in actor.traits:
            if trait["name"] == "Nimble Escape" and combat.action_available(actor, trait):
                combat.use_action(actor, trait["name"])
