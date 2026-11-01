"""Replace Policy, area_heuristic or grab_cap without changing spell resolution."""
import math

from .dice import mean
from .state import SpellInstance


FEET_PER_TARGET = {"cone": 10, "line": 30}  # every other shape: 5


def _dmg_count(shape, size_ft):
    return max(1, math.ceil(size_ft / FEET_PER_TARGET.get(shape, 5)))


def dmg_area_heuristic(shape: str, size_ft: float, eligible: int, caster=None) -> int:
    """No-grid AoE rule from the DMG "Targets in Areas of Effect" table.

    Cone size/10, line length/30, sphere/cylinder/emanation radius/5 and cube
    size/5, rounded up, at least one, capped by the eligible creatures. This
    was the default until 2026-10-24; pass it as ``area`` to restore it.
    Returns a count; a custom heuristic may instead return indices into the
    eligible list. Placement and ordering remain policy decisions.
    """
    return min(eligible, _dmg_count(shape, size_ft))


def area_heuristic(shape: str, size_ft: float, eligible: int, caster=None) -> int:
    """Default no-grid AoE rule: the DMG table for the party's areas, and half
    that count (rounded up, at least one) for everyone else's, because players
    spread out against monster areas. Chosen from the DMG budget calibration
    (data/reports/calibration_area_compare.md). Without a caster (for example
    Aura of Authority) the DMG count applies.
    """
    count = _dmg_count(shape, size_ft)
    if caster is not None and caster.team != "party": count = max(1, math.ceil(count / 2))
    return min(eligible, count)


# Custom heuristics opt in to these: the default's ally avoidance for freely
# placed hostile areas, and receiving the caster.
area_heuristic.wants_caster = True
dmg_area_heuristic.avoids_allies = True


def is_grab(block) -> bool:
    """A multi-target grab: its failure (or hit) grapples, restrains or engulfs."""
    effects = block.get("on_fail", []) + block.get("on_hit", [])
    return any(p.get("apply_condition", {}).get("condition") in {"grappled", "restrained"} or
               p.get("status", {}).get("id") == "engulfed" for p in effects)


def grab_cap(instance, block, n: int, eligible) -> int:
    """Default cap on n_targets counts: a multi-target grab (Engulf, Whelm)
    reaches at most half the eligible group, rounded up, because without a
    grid it would otherwise take its full printed capacity every use. Chosen
    from the DMG budget calibration (data/reports/calibration_grab_compare.md).
    Other n_targets actions keep their printed count.
    """
    return min(n, max(1, math.ceil(len(eligible) / 2))) if is_grab(block) else n


def printed_grab_count(instance, block, n: int, eligible) -> int:
    """Pass as ``target_cap`` to restore printed grab counts (the pre-2026-10-24 default)."""
    return n


class Policy:
    def choose_wild_shape(self, combat, actor):
        from .loader import ROOT, load_sheet
        from .state import Combatant
        if actor.has_status("wild_shape") or not actor.limited_uses.get("wild_shape") or not actor.bonus_action: return
        enemies=combat.enemies(actor)
        if not enemies: return
        concentration=any(combat.spells[n]["concentration"] and combat.can_cast(actor,n) for n in actor.spells)
        if actor.concentration is None and concentration and actor.hp>=actor.max_hp/2: return
        names=["wolf"] if actor.level<3 else ["dire_wolf","brown_bear","giant_spider"]
        forms=[(n,Combatant.from_sheet(load_sheet(ROOT/"monsters"/(n+".yaml")),"shape_probe",actor.team)) for n in names]
        best=max(forms,key=lambda item:combat.expected_weapon_damage(item[1],enemies[0]))[0]
        combat.wild_shape(actor,best)

    def combat_spell(self, combat, actor, name):
        spec=combat.spells[name]
        option=None
        points=actor.limited_uses.get("sorcery_points",0)
        if points>=2 and actor.features.get("quickened_spell") and actor.action and actor.bonus_action and spec["casting_time"]=="action" and spec["level"] and actor.statuses.get("leveled_spell_turn")!=combat.turn_index:
            option="quickened_spell"
        elif points>=2 and actor.features.get("heightened_spell") and spec["level"]>=2 and any(b["save"] for b in spec["effects"]): option="heightened_spell"
        elif points and actor.features.get("extended_spell") and spec["concentration"] and spec["duration"]["type"] in {"minutes","hours","days"}: option="extended_spell"
        return combat.cast(actor,name,metamagic=option)

    def use_luck(self, combat, actor, kind):
        """Lucky: saves and death saves always; attack rolls and checks only while a point stays in reserve for saves."""
        return kind in {"save", "death"} or actor.limited_uses.get("luck", 0) > 1

    def focus_allowed(self, combat, actor):
        points=actor.limited_uses.get("focus",0)
        if not points: return False
        starts=getattr(combat,"focus_at_start",None)
        if starts is None: combat.focus_at_start=starts={}
        start,spent_start=starts.setdefault(actor.id,(points,actor.resources_spent.get("focus",0)))
        remaining=max(1,getattr(combat,"encounters_until_rest",getattr(combat,"encounters_remaining",1)))
        budget=math.ceil(start/remaining)
        spent=actor.resources_spent.get("focus",0)-spent_start
        if actor.hp<actor.max_hp/4: return True
        return spent<budget and spent<max(1,math.ceil(budget*actor.turns_taken/max(2,combat.expected_remaining_rounds(actor)+actor.turns_taken-1)))

    def stunning_strike(self, combat, actor, target):
        if not self.focus_allowed(combat,actor) or target.has_condition("incapacitated") or target.immune_to("stunned"): return False
        bonus=target.save_bonus("con")
        fail=max(0,min(1,(7+actor.mod("wis")+actor.proficiency_bonus-bonus)/20))
        threshold=.6 if actor.features.get("stunning_reserve") else .4
        valuable=bool(target.spells) or target.max_hp>=.75*max((e.max_hp for e in combat.enemies(actor)),default=target.max_hp)
        return valuable and fail>=threshold and target.hp>2*(actor.mod("dex")+4.5) and bool(target.attacks or target.spells or target.actions)

    def reckless_attack(self, combat, actor, target):
        return True

    def brutal_strike(self, combat, actor, target):
        return True

    def smite(self, combat, actor, target, critical, free=False):
        if not free and not self.allow_spell(combat,actor,combat.spells["Divine Smite"]): return False
        # Hold the bonus action for a possible critical on the remaining attack.
        return critical or actor.statuses.get("weapon_hits",0) >= actor.extra_attack or not actor.spell_slots or sum(actor.spell_slots.values()) > 1 or free

    def smite_forgone(self, combat, actor, target):
        """Expected Divine Smite damage this turn: at least one hit, lowest slot (or the free cast)."""
        if "Divine Smite" not in actor.spells or not actor.attacks: return 0
        free = actor.limited_uses.get("paladins_smite", 0) > 0
        slots = sorted(k for k, n in actor.spell_slots.items() if n)
        if not free and (not slots or not self.allow_spell(combat, actor, combat.spells["Divine Smite"])): return 0
        hit = combat.hit_probability(actor, target, actor.attacks[0]["to_hit"])
        return (1 - (1 - hit) ** max(1, actor.extra_attack)) * 4.5 * (1 + (1 if free else slots[0]))

    def smite_slot_cost(self, combat, actor, target, slot):
        """Divine Smite damage a spent slot would have dealt later, when the fight outlasts the slots."""
        if not slot or "Divine Smite" not in actor.spells or not actor.attacks: return 0
        if sum(actor.spell_slots.values()) > combat.expected_remaining_rounds(actor): return 0
        hit = combat.hit_probability(actor, target, actor.attacks[0]["to_hit"])
        return (1 - (1 - hit) ** max(1, actor.extra_attack)) * 4.5 * (1 + slot)

    def reroll_die(self, combat, actor, natural):
        values = getattr(natural, "values", (natural,))
        return min(range(len(values)), key=values.__getitem__)

    def healing_pool(self, combat, instance, targets, amount, cap="half"):
        allocations = dict.fromkeys((t.id for t in targets), 0)
        ordered = sorted(targets, key=lambda t: (t.hp != 0, t.hp / max(1, t.max_hp), t.id))
        # First buy as many revivals as possible; then spread the remaining pool.
        for t in ordered:
            if amount and t.hp == 0 and t.max_hp >= 2:
                allocations[t.id] += 1
                amount -= 1
        while amount:
            limit = {t.id: t.max_hp if cap == "full" else t.max_hp // 2 for t in ordered}
            eligible = [t for t in ordered if t.hp + allocations[t.id] < limit[t.id]]
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

    def overchannel(self, combat, actor, spec):
        # Spend the free use on the first damaging spell of level 3 or higher.
        return spec["level"] >= 3

    def tactical_mind(self, combat, actor, ability, dc):
        return True

    def tactical_master(self, combat, actor, attack, target):
        if any(e.block=="sap" for e in target.active_effects): return None
        prevented=combat.expected_weapon_damage(target,actor)*.3
        lost_graze=max(0,actor.mod(attack.get("ability","str")))*(1-combat.hit_probability(actor,target,attack["to_hit"])) if attack.get("mastery")=="graze" else 0
        return "sap" if prevented>lost_graze and target.attacks else None

    def cunning_strike(self, combat, actor, target, options):
        choice = self.basic_cunning_strike(combat, actor, target, options)
        if choice is None and "obscure" in options and "blinded" not in target.condition_immunities and not target.has_condition("blinded") and target.hp > 20 and target.attacks:
            return "obscure"
        return choice

    def basic_cunning_strike(self, combat, actor, target, options):
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
        paladin_buff = instance.caster.features.get("values_buffs") and any(k in p for p in block["apply"] for k in ("modify", "weapon_enchantment", "max_hp", "temp_hp", "defense"))
        if paladin_buff:
            beneficial = True
            eligible = [c for c in eligible if c.team == instance.caster.team and not any(i.active and i.spec["name"] == instance.spec["name"] and any(e.source == i.id for e in c.effects) for i in combat.instances.values())]
        # Allegiance-neutral legality stays in the engine; this is preference only.
        preferred = [x for x in eligible if (x.team == instance.caster.team) == beneficial]
        ordered = sorted(preferred or eligible, key=lambda x: (x.hp / max(1,x.max_hp) if beneficial else x.hp, x.id))
        if paladin_buff and any(p.get("modify", {}).get("stat") == "ac" for p in block["apply"]):
            ordered = sorted(eligible, key=lambda c: (c.position != "front", -max((combat.at_will_damage_rate(e,c) for e in combat.enemies(instance.caster)), default=0), c.id))
        if not beneficial and instance.caster.team != "party" and getattr(combat, "day_options", None):
            candidates = preferred or eligible
            if combat.day_options.targeting != "random":
                ordered = combat.monster_order(instance.caster, candidates)
            elif instance.id == 0:
                ordered = sorted(candidates, key=lambda c: c.id)  # EV probes never draw targeting randomness.
            else:
                ordered = []
                while candidates:
                    chosen = combat.monster_target(instance.caster, candidates)
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
            con = pending_caster.save_bonus("con")
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
        if actor.features.get("rage"): combat.rage(actor)
        if actor.features.get("innate_sorcery"): combat.innate_sorcery(actor)
        if actor.features.get("wild_shape"): self.choose_wild_shape(combat,actor)
        if actor.features.get("monks_focus") and actor.hp<actor.max_hp*.35 and any(e.attacks for e in enemies) and self.focus_allowed(combat,actor): combat.patient_defense(actor,dodge=True)
        if actor.features.get("wholeness_of_body") and actor.hp<actor.max_hp/2: combat.wholeness(actor)
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
        if wounded and actor.features.get("lay_on_hands") and self.allow_healing(combat,actor,wounded[0]):
            combat.lay_on_hands(actor,wounded[0])
        if wounded:
            # Healing Word needs a target the caster can see (a blinded caster falls back to touch).
            if self.allow_healing(combat, actor, wounded[0]) and combat.can_cast(actor, "Healing Word") and wounded[0].visible_to(actor):
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
            if actor.features.get("pact_magic"):
                weapon=max(weapon,max((combat.expected_spell_damage(actor,combat.cantrip_spec(actor,n),enemies[0]) for n in actor.spells if combat.spells[n]["level"]==0),default=0))
            if actor.routines: weapon = max(weapon, max(combat.routine_value(actor, r, enemies[0], control=True) for r in actor.routines))
            for name in actor.spells:
                if not combat.can_cast(actor, name): continue
                spec = combat.spells[name]
                if actor.features.get("lay_on_hands") and spec.get("casting_trigger"): continue
                if not combat.free_mark(actor,name) and not self.allow_spell(combat, actor, spec): continue
                casting_time = actor.spell_costs.get(name, spec["casting_time"])
                if casting_time not in {"action", "bonus_action"}: continue
                if spec["concentration"] and actor.concentration is not None: continue
                slot = combat.available_slot(actor, spec)
                scaled = combat.scale(actor, spec, slot)
                value = combat.expected_spell_damage(actor, scaled, enemies[0])
                # Cleric/wizard share the buff blind spot; preserve their published baselines.
                if actor.features.get("values_buffs"):
                    value = max(value, combat.expected_buff_value(actor, scaled, slot=slot))
                if actor.features.get("lay_on_hands"):
                    # The slot could power a later smite instead.
                    value -= self.smite_slot_cost(combat, actor, enemies[0], slot)
                    # A bonus-action buff gives up this turn's Divine Smite.
                    if casting_time == "bonus_action": value -= self.smite_forgone(combat, actor, enemies[0])
                if (actor.features.get("pact_magic") and name=="Hex") or (actor.features.get("favored_enemy") and name=="Hunter's Mark"):
                    horizon=combat.concentration_horizon(actor,enemies,combat.expected_remaining_rounds(actor))
                    value=max(value,3.5*combat.expected_attack_hits(actor,enemies[0])*horizon*.9)
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
                elif actor.features.get("font_of_magic"): self.combat_spell(combat,actor,best[1])
                else: combat.cast(actor, best[1])
            elif actor.features.get("pact_magic"):
                cantrips=[n for n in actor.spells if combat.spells[n]["level"]==0 and combat.can_cast(actor,n)]
                if cantrips: combat.cast(actor,max(cantrips,key=lambda n:combat.expected_spell_damage(actor,combat.cantrip_spec(actor,n),enemies[0])))
                else: combat.weapon_action(actor)
            else: combat.weapon_action(actor)
            if actor.action and combat.enemies(actor):
                if actor.features.get("innate_sorcery"):
                    cantrips=[n for n in actor.spells if combat.spells[n]["level"]==0 and combat.can_cast(actor,n)]
                    if cantrips: combat.cast(actor,max(cantrips,key=lambda n:combat.expected_spell_damage(actor,combat.cantrip_spec(actor,n),enemies[0])))
                    else: combat.weapon_action(actor)
                elif actor.features.get("pact_magic") and combat.can_cast(actor,"Eldritch Blast"): combat.cast(actor,"Eldritch Blast")
                else: combat.weapon_action(actor)
        if actor.features.get("wild_shape"): self.choose_wild_shape(combat,actor)
        if actor.features.get("martial_arts") and actor.bonus_action and combat.enemies(actor): combat.monk_bonus(actor,flurry=self.focus_allowed(combat,actor))
        if actor.features.get("bardic_inspiration") and actor.bonus_action and combat.enemies(actor):
            allies=[c for c in combat.combatants if c is not actor and c.team==actor.team and c.alive and c.statuses.get("bardic_inspiration",{}).get("expires",0)<=combat.time_rounds]
            for ally in sorted(allies,key=lambda c:(-combat.expected_attack_hits(c,combat.enemies(actor)[0]),c.hp/c.max_hp,c.id)):
                if combat.inspire(actor,ally): break
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


class RationedPolicy(Policy):
    """Treats a known day's resources as a budget.

    Spell slots, counted in slot levels, get an equal share per encounter left
    before the long rest (recomputed each encounter, so savings carry
    forward). A leveled spell is cast within that share, or beyond it when an
    ally is down or below 25% HP, or when a weapons-and-cantrips fight is
    forecast to cost more than 25% of the party's HP or its fair share for
    this encounter. No slot is spent once at-will damage this round already
    covers the enemies' HP, and slots are never upcast. Short-rest features
    (Action Surge, Channel Divinity) are spent on such fights or before a
    rest. Hit Dice get an equal share per short rest left before the long
    rest, with extra dice for anyone below half HP. With one encounter left,
    the whole budget is available, so a single fight is fought as usual.
    Once a fight is being lost (at most half the party can act, or the
    at-will forecast costs half the party's HP) everything is released: any
    spell, the highest slot, healing below half HP and short-rest features.
    """
    EMERGENCY = 0.25   # an ally below this HP share (or down) frees every resource
    NEED = 0.25        # forecast at-will HP loss above this party share frees slots
    LOSING = 0.5       # forecast loss of this party share (or half the party out of action) releases everything

    def __init__(self):
        self.dice_allowance, self.dice_spent = {}, {}

    @staticmethod
    def remaining(combat):
        return max(1, getattr(combat, "encounters_remaining", 1))

    def emergency(self, combat, actor):
        return any(c.team == actor.team and c.summoner_id is None and not c.dead and not c.removed and not c.permanently_removed
                   and (c.hp == 0 or c.hp < c.max_hp * self.EMERGENCY) for c in combat.combatants)

    def at_will_fight(self, combat, actor):
        """(party HP, enemy HP, party at-will damage per round, forecast HP loss) for a weapons-and-cantrips fight.
        Only allies who can act (not incapacitated: petrified, stunned, paralyzed...) deal damage."""
        allies = [c for c in combat.combatants if c.team == actor.team and c.alive and c.summoner_id is None]
        enemies = combat.enemies(actor)
        if not allies or not enemies: return 0, 0, 0, 0
        outgoing = sum(combat.at_will_damage_rate(a, enemies[0]) for a in allies if not a.has_condition("incapacitated"))
        # Expected incapacitation and domination take party turns away for the rest of the fight.
        outgoing *= 1 - self.control_share(combat, actor, allies, enemies, outgoing)
        enemy_hp = sum(e.hp for e in enemies)
        incoming = 0
        for enemy in enemies:
            rate = sum(combat.at_will_damage_rate(enemy, a) for a in allies) / len(allies)
            for action in enemy.actions:  # ready nonspell attacks such as breath weapons
                if combat.action_available(enemy, action): rate = max(rate, combat.expected_action_damage(enemy, action, allies[0]))
            incoming += rate
        rounds = enemy_hp / max(1, outgoing)
        # Enemies drop over the fight, so on average about half of them are still attacking.
        return sum(a.hp for a in allies), enemy_hp, outgoing, rounds * incoming / 2

    INCAPACITATING = frozenset({"paralyzed", "stunned", "petrified", "unconscious", "incapacitated"})
    MAX_CONTROL = 0.9  # never forecast more than this share of party turns lost

    def control_share(self, combat, actor, allies, enemies, outgoing):
        """Expected share of the party's turns lost to enemy control over the fight.

        Each enemy contributes its strongest ready control source per round: an
        action (weighted by its recharge chance), an attack rider or on-hit
        condition (times its uses in the multiattack), or a leveled spell it can
        still cast. A source counts if it paralyzes, stuns, petrifies, knocks out or
        incapacitates, upgrades to one of those on a failed repeat save (the
        basilisk's gaze), or dominates (a controlling charm, counted double since
        the PC also turns on the party). Lost ally-turns per round, divided by the
        able allies, is the share; the horizon is the fight's at-will length.
        """
        able = [a for a in allies if not a.has_condition("incapacitated")]
        if not able: return self.MAX_CONTROL
        horizon = max(1.0, sum(e.hp for e in enemies) / max(1, outgoing))
        lost = sum(max((self.lost_turns(combat, enemy, block, rate, to_hit, able, horizon)
                        for block, rate, to_hit in self.control_sources(combat, enemy)), default=0) for enemy in enemies)
        return min(self.MAX_CONTROL, lost / len(able))

    @staticmethod
    def control_sources(combat, enemy):
        """(effect block, uses per round, attack bonus or None) for an enemy's ready effects."""
        sources = []
        if not enemy.alive or enemy.has_condition("incapacitated"): return sources
        for action in enemy.actions:
            # Ready on its coming turns (action_available also requires it to be acting now).
            if action.get("cost") not in {"action", "bonus_action"} or action.get("passive") or action.get("trigger"): continue
            if action.get("resource") and enemy.limited_uses.get(action["resource"], 0) < 1: continue
            if not enemy.recharge_ready.get(action["name"], True): continue
            rate = (7 - action["recharge"]) / 6 if action.get("recharge") else 1
            sources += [(block, rate, None) for block in action.get("effects", [])]
        uses = {}  # most uses of each attack in any routine (the monster can pick it)
        for routine in (enemy.routines or []) + [enemy.multiattack or [a["name"] for a in enemy.attacks[:1]]]:
            for name in set(routine): uses[name] = max(uses.get(name, 0), routine.count(name))
        for attack in enemy.attacks:
            n = uses.get(attack["name"], 0)
            if not n: continue
            sources += [(block, n, attack["to_hit"]) for block in attack.get("riders", [])]
            direct = [p for p in attack.get("effects", []) if "apply_condition" in p]
            if direct: sources.append(({"target": {"select": "single"}, "save": None, "on_hit": direct, "on_fail": [], "apply": []}, n, attack["to_hit"]))
        for name in enemy.spells:
            spec = combat.spells[name]
            if spec["level"] and combat.can_cast(enemy, name):
                sources += [(block, 1, enemy.spell_attack_bonus if block.get("attack") else None) for block in spec["effects"]]
        return sources

    def lost_turns(self, combat, enemy, block, rate, to_hit, allies, horizon):
        """Expected ally-turns lost per round of use of one effect block."""
        target = block.get("target", {})
        if target.get("select") == "area":
            n = area_heuristic(target["shape"], target["size_ft"], len(allies), caster=enemy)
        elif target.get("select") == "n_targets":
            n = len(allies) if target.get("n") == "all" else min(len(allies), target.get("n", 1))
        else:
            n = 1
        save = block.get("save")
        best = 0
        for p in block.get("on_fail", []) + block.get("on_hit", []) + block.get("apply", []):
            data = p.get("apply_condition") if isinstance(p, dict) else None
            if not data: continue
            condition, upgrade = data["condition"], data.get("upgrade_on_failure")
            dominated = condition == "charmed" and data.get("control")
            if condition not in self.INCAPACITATING and upgrade not in self.INCAPACITATING and not dominated: continue
            total = 0
            for ally in allies:
                if condition in ally.condition_immunities: continue
                chance = combat.hit_probability(enemy, ally, to_hit) if to_hit is not None else 1
                if save: chance *= combat.save_failure_probability(enemy, ally, save["ability"], save.get("dc"))
                repeat = data.get("repeat_save")
                q = combat.save_failure_probability(enemy, ally, repeat["ability"], (save or {}).get("dc")) if repeat else 1
                if dominated: duration = 2 * min(horizon, 2)
                elif condition in self.INCAPACITATING: duration = min(horizon, 1 / (1 - q)) if q < 1 else horizon
                else: duration = q * horizon  # incapacitated only once it upgrades on a failed repeat save
                total += chance * duration
            best = max(best, rate * n * total / len(allies))
        return best

    def needs_resources(self, combat, actor):
        hp, _, _, loss = self.at_will_fight(combat, actor)
        return loss > min(hp, max(self.NEED * hp, hp / self.remaining(combat)))

    def losing(self, combat, actor):
        """The fight is being lost: at most half the party can still act (down, incapacitated or
        dominated), or a weapons-and-cantrips fight would cost at least half the party's HP."""
        party = [c for c in combat.combatants if c.__dict__["team"] == actor.__dict__["team"] and c.summoner_id is None
                 and not c.dead and not c.removed and not c.permanently_removed]
        able = [c for c in party if c.alive and not c.has_condition("incapacitated") and c.team == actor.team]
        if party and len(able) * 2 <= len(party): return True
        enemies = combat.enemies(actor)
        allies = [c for c in party if c.alive and c.team == actor.team]
        if enemies and allies:
            outgoing = sum(combat.at_will_damage_rate(a, enemies[0]) for a in allies if not a.has_condition("incapacitated"))
            if self.control_share(combat, actor, allies, enemies, outgoing) >= self.LOSING: return True
        hp, _, _, loss = self.at_will_fight(combat, actor)
        return hp > 0 and loss >= self.LOSING * hp

    def slot(self, combat, actor, spec, slots):
        # Released resources go out at full strength; otherwise never upcast.
        return slots[-1] if self.losing(combat, actor) else slots[0]

    def already_won(self, combat, actor):
        _, enemy_hp, outgoing, _ = self.at_will_fight(combat, actor)
        return enemy_hp > 0 and outgoing >= enemy_hp

    def within_budget(self, combat, actor, cost):
        start = getattr(combat, "slots_at_start", {}).get(actor.id, actor.spell_slots)
        start_points = sum(level * n for level, n in start.items())
        spent = start_points - sum(level * n for level, n in actor.spell_slots.items())
        return spent + cost <= math.ceil(start_points / self.remaining(combat))

    def allow_spell(self, combat, actor, spec):
        if spec["level"] == 0 or spec["name"] in actor.innate_spells: return True
        if self.emergency(combat, actor) or self.losing(combat, actor): return True
        if self.already_won(combat, actor): return False
        cost = min((k for k, n in actor.spell_slots.items() if n and k >= spec["level"]), default=spec["level"])
        return self.within_budget(combat, actor, cost) or self.needs_resources(combat, actor)

    def allow_healing(self, combat, actor, target):
        threshold = self.LOSING if self.losing(combat, actor) else self.EMERGENCY
        return target.hp == 0 or target.hp < target.max_hp * threshold

    def short_rest_feature(self, combat, actor):
        return (getattr(combat, "encounters_until_rest", 1) <= 1 or self.emergency(combat, actor)
                or self.losing(combat, actor) or self.needs_resources(combat, actor))

    def allow_surge(self, combat, actor):
        return self.short_rest_feature(combat, actor)

    def allow_action(self, combat, actor, action):
        if action.get("resource") != "channel_divinity": return True
        return self.short_rest_feature(combat, actor)

    def reaction(self, combat, reactor, spell, trigger):
        return ("level" not in spell or self.allow_spell(combat, reactor, spell)) and super().reaction(combat, reactor, spell, trigger)

    def before_rest(self, combat, party, kind, short_rests_left):
        """Called by run_day before each rest with the short rests left before the long rest."""
        self.dice_spent = {}
        self.dice_allowance = {a.id: math.ceil(a.hit_dice / max(1, short_rests_left)) for a in party} if kind == "short" else {}

    def spend_hit_die(self, actor):
        allowance = self.dice_allowance.get(actor.id)
        if allowance is None: return actor.hp < actor.max_hp  # no schedule known
        spent = self.dice_spent.get(actor.id, 0)
        if actor.hp < actor.max_hp * .5 or (spent < allowance and actor.hp < actor.max_hp * .9):
            self.dice_spent[actor.id] = spent + 1
            return True
        return False


STRATEGIES = {"default": Policy, "nova": NovaPolicy, "conservative": ConservativePolicy, "rationed": RationedPolicy}


def strategy_policy(name):
    if name not in STRATEGIES: raise ValueError(f"unknown strategy: {name}")
    return STRATEGIES[name]()
