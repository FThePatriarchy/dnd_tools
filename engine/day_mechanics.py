"""Day-only combat hooks: death, safe elapsed time, and no-grid reachability."""
from . import dice
from .state import compare_deadline


class DayMechanics:
    def interrupt_rest(self, reason, actor=None):
        rest = getattr(self, "resting", None)
        if rest is not None: rest.interrupt(reason, actor)

    def expected_buff_prevention(self, actor, spec):
        """Damage-equivalent EV over forecast encounters inside the duration.

        Uses the same no-RNG scorer as combat decisions. HP pools are one-use;
        AC and recurring temporary HP accrue over covered attack opportunities.
        """
        from .state import SpellInstance
        duration = spec.get("duration", {"type": "instant"})
        cap = duration.get("n", 1) * {"rounds": 1, "minutes": 10, "hours": 600}.get(duration["type"], 0)
        schedule = getattr(self, "future_encounters", [(0, 3)])
        if duration["type"] == "instant": covered = schedule[:1]
        else: covered = [(start, rounds) for start, rounds in schedule if compare_deadline(start, cap) < 0]
        if not covered: return 0, []
        horizon = sum(min(rounds, cap - start) if cap else rounds for start, rounds in covered)
        probe = SpellInstance(0, spec, actor, spec["level"], self.turn_index, self.time_rounds)
        total = 0
        chosen = []
        for block in spec["effects"]:
            if block["target"]["select"] == "ref":
                targets = chosen
            else:
                legal = [c for c in self.eligible(probe, block) if c.team == actor.team and c.alive]
                if block["target"]["select"] == "self": legal = [actor] if actor in legal else []
                armor = next((p["base_ac"] for p in block["apply"] if "base_ac" in p), None)
                if armor:
                    legal = [c for c in legal if not (armor.get("unarmored_only") and c.features.get("armored"))]
                    legal.sort(key=lambda c: -(armor["base"] + c.mod(armor.get("ability") or "dex") - self.armor_class(c)))
                    targets = legal[:block["target"].get("n", 1)]
                else:
                    targets = self.policy_for(actor).targets(self, probe, block, legal, block["target"].get("n", 1))
                chosen = list(dict.fromkeys([*chosen, *targets]))
            for target in targets:
                if any(i.active and i.spec["name"] == spec["name"] and any(e.source == i.id for e in target.effects) for i in self.instances.values()): continue
                enemies = getattr(self, "forecast_enemies", None) or self.combatants
                incoming = max((self.at_will_damage_rate(e, target) for e in enemies if e.team != actor.team and e.alive), default=6)
                for p in block["apply"]:
                    if "base_ac" in p:
                        v = p["base_ac"]
                        if v.get("unarmored_only") and target.features.get("armored"): continue
                        gain = max(0, v["base"] + (target.mod(v["ability"]) if v.get("ability") else 0) - self.armor_class(target))
                        total += gain * .05 * incoming / .6 * horizon
                    elif "max_hp" in p:
                        total += p["max_hp"]["amount"]
                    elif "temp_hp" in p:
                        v = p["temp_hp"]
                        amount = dice.mean(v["dice"]) if "dice" in v else actor.spell_mod if v.get("amount") == "spell_mod" else v.get("amount", 0)
                        amount += actor.spell_mod if v.get("bonus") == "spell_mod" else v.get("bonus", 0)
                        recurring = "start_of_turn" in block["event"]
                        total += min(incoming * horizon, max(0, amount - target.temp_hp) * (horizon if recurring else 1))
                    elif "modify" in p and p["modify"]["stat"] == "ac" and p["modify"]["op"] == "add":
                        total += p["modify"]["value"] * .05 * incoming / .6 * horizon
        if spec.get("concentration"): total *= .7
        return total, chosen

    MORALE_DC = 10

    def morale_checks(self):
        """Optional DMG morale rule (DayOptions.morale; off by default).

        A monster checks the first time it is at half its hit points or fewer,
        and every monster on a side checks the first time that side is down to
        half its starting number. "dmg": a DC 10 Wisdom save, fleeing on a
        failure; "rout": flee without a save (an upper bound). A fleeing
        creature leaves the combat. Creatures immune to the frightened
        condition never check, and an incapacitated one checks once it can act.
        Checks run at the end of each turn, after that turn's damage.
        """
        options = getattr(self, "day_options", None)
        mode = options.morale if options else "none"
        start = getattr(self, "morale_start", None)
        if mode == "none" or not start: return
        monsters = [c for c in self.combatants if c.cr is not None and c.summoner_id is None and c.team != "party"]
        standing = {}
        for c in monsters:
            if c.alive: standing[c.team] = standing.get(c.team, 0) + 1
        for c in monsters:
            if not c.alive or c.has_condition("incapacitated") or "frightened" in c.condition_immunities: continue
            triggers = []
            if c.hp * 2 <= c.max_hp and "morale_hurt" not in c.statuses: triggers.append("morale_hurt")
            if standing.get(c.team, 0) * 2 <= start.get(c.team, 0) and "morale_group" not in c.statuses: triggers.append("morale_group")
            for trigger in triggers:
                c.statuses[trigger] = {}
                if mode == "rout" or not self.saving_throw(c, "wis", self.MORALE_DC):
                    self.flee(c, trigger)
                    break

    def flee(self, actor, reason):
        actor.removed = True
        actor.statuses["fled"] = {"reason": reason}
        if actor.concentration is not None: self.end_spell(actor.concentration)
        self.record("fled", actor=actor.id, reason=reason)

    def kill(self, actor):
        if actor.dead: return
        actor.dead = True
        actor.hp = 0
        actor.deaths += 1
        actor.dead_at = self.time_rounds
        actor.stable_wake_at = None
        actor.statuses.pop("stable", None)
        if actor.concentration is not None: self.end_spell(actor.concentration)
        self.record("death", actor=actor.id, time_rounds=self.time_rounds)

    def stabilize(self, actor):
        if actor.hp or actor.dead: return
        actor.death_successes = actor.death_failures = 0
        actor.statuses["stable"] = {}
        if self.death_rules and actor.stable_wake_at is None:
            actor.stable_wake_at = self.time_rounds + self.rng.randint(1, 4) * 600
        self.record("stabilize", actor=actor.id, wake_at=actor.stable_wake_at)

    def death_save(self, actor):
        if not self.death_rules or actor.team != "party" or actor.hp or actor.dead or actor.removed or actor.permanently_removed or actor.has_status("stable"): return
        adv, dis = self.roll_flags(actor,"saves","death")
        natural = dice.d20(self.rng,adv,dis)
        bonus = self.modifier(actor,"save",0,"death",consume=True) - self.exhaustion_penalty(actor)
        natural = self.heroic_reroll(actor, natural, lambda n: n == 20 or n != 1 and n + bonus >= 10)
        success, total, natural = self.class_failed_save(actor,"death",10,bonus,natural,natural == 20 or natural != 1 and natural + bonus >= 10)
        if natural == 20:
            self.heal(actor, 1)
        elif natural == 1:
            actor.death_failures += 2
        elif success:
            actor.death_successes += 1
        else:
            actor.death_failures += 1
        self.record("death_save", actor=actor.id, natural=natural, total=total, successes=actor.death_successes, failures=actor.death_failures)
        if actor.death_failures >= 3: self.kill(actor)
        elif actor.death_successes >= 3: self.stabilize(actor)

    def death_damage(self, actor, before, amount, absorbed=0):
        if not self.death_rules or actor.team != "party" or actor.dead or amount <= 0 or actor.hp: return
        if amount - absorbed - before >= actor.max_hp:
            self.kill(actor)
        elif before == 0:
            actor.death_failures += 2 if self._critical_damage else 1
            actor.stable_wake_at = None
            if actor.death_failures >= 3: self.kill(actor)

    def can_revive(self, target):
        return (target.dead and target.max_hp > 0 and target.dead_at is not None
                and compare_deadline(self.time_rounds, target.dead_at + 10) <= 0)

    def revive(self, caster, target):
        """Revivify's one-minute window; caller still pays its normal slot."""
        if not self.can_revive(target): return False
        target.dead = False
        target.dead_at = None
        target.death_successes = target.death_failures = 0
        target.stable_wake_at = None
        self.heal(target, 1)
        self.record("revivify", caster=caster.id, target=target.id)
        return True

    def settle_downed(self, party):
        """Six-second rescue/check turns; unsuccessful checks allow death saves."""
        if not self.death_rules: return
        for target in party:
            if not target.dead or target.max_hp < 1: continue
            for healer in party:
                if not healer.alive: continue
                self.begin_turn(healer)
                if self.can_cast(healer, "Revivify") and self.can_revive(target):
                    self.cast(healer, "Revivify", targets=[target])
                    self.time_rounds += 1
                    break
        for _ in range(6):
            downed = [t for t in party if not t.dead and t.hp == 0 and not t.has_status("stable") and not t.permanently_removed]
            rescuers = [a for a in party if a.alive and not a.has_condition("incapacitated")]
            if not downed or not rescuers: break
            for healer in sorted(rescuers, key=lambda a: -(a.mod("wis") + (a.proficiency_bonus if "medicine" in a.skill_proficiencies else 0))):
                if not downed: break
                target = downed.pop(0)
                self.begin_turn(healer)
                if self.can_cast(healer, "Spare the Dying"):
                    self.cast(healer, "Spare the Dying", targets=[target])
                elif self.ability_check(healer, "wis", 10, "medicine"):
                    self.stabilize(target)
            self.time_rounds += 1
            for target in party: self.death_save(target)
        self.current = None

    def advance_time(self, rounds):
        """Advance safe time without wiping effects or faking rest eligibility."""
        if rounds < 0: raise ValueError("cannot reverse day clock")
        if rounds == 0: return
        end = self.time_rounds + rounds
        self.turn_index += 1  # Safe time leaves the old global spell/feature turn behind.
        # Turn-bound effects expire after their actual next boundary, not the next fight.
        for actor in list(self.combatants):
            actor.turns_taken += 1
            self.reset_turn_economy(actor)
            self.expire("start_of_turn", actor)
            self.expire("end_of_turn", actor)
            self.reconcile_economy(actor)
        while compare_deadline(self.time_rounds, end) < 0:
            pending = [a for a in self.combatants if self.death_rules and a.team == "party" and not a.dead and a.hp == 0 and not a.has_status("stable")]
            periodic = (any(i.active and any("start_of_turn" in b["event"] or "end_of_turn" in b["event"] for b in i.spec["effects"]) for i in self.instances.values())
                        or any(e.data.get("repeat_save") for a in self.combatants for e in a.active_effects))
            self.time_rounds = min(end, self.time_rounds + 1) if pending or periodic else end
            for actor in list(self.combatants):
                self.expire("clock", actor)
                if periodic and actor.alive:
                    self.turn_index += 1
                    self.reset_turn_economy(actor)
                    actor.turns_taken += 1
                    self.expire("start_of_turn", actor)
                    self.reconcile_economy(actor)
                    self.repeat_saves(actor,"start_of_turn")
                    self.dispatch("start_of_turn", who=actor)
                    self.dispatch("end_of_turn", who=actor)
                    self.dispatch("end_of_turn_in_aura", who=actor)
                    self.repeat_saves(actor,"end_of_turn")
                    self.expire("end_of_turn", actor)
                self.death_save(actor)
                if actor.stable_wake_at is not None and compare_deadline(self.time_rounds, actor.stable_wake_at) >= 0 and not actor.dead:
                    self.heal(actor, 1)
        self.time_rounds = end
        self.current = None

    def reachable(self, actor, enemies, attack=None):
        options = getattr(self, "day_options", None)
        if not options or not options.engagement or actor.team == "party": return enemies
        if attack is not None and attack.get("kind") == "ranged": return enemies
        if attack is None or attack.get("reach_ft", 5) > 5 or actor.movement_modes.get("fly") or set(actor.engagement_tags) & {"reach", "flying", "teleport"}:
            return enemies
        if any("teleport" in a["name"].lower() for a in actor.actions + actor.traits) or any(n in actor.spells for n in ("Misty Step", "Dimension Door")):
            return enemies
        fronts = sorted([c for c in enemies if c.alive and not c.has_condition("incapacitated") and c.position == "front"], key=lambda c: c.id)
        melee = sorted([c for c in self.combatants if c.team == actor.team and c.alive
                        and any(a.get("kind") == "melee" for a in c.attacks)
                        and not c.movement_modes.get("fly")
                        and not set(c.engagement_tags) & {"reach","flying","teleport"}
                        and not any(a.get("kind") == "melee" and a.get("reach_ft",5)>5 for a in c.attacks)
                        and not any("teleport" in a["name"].lower() for a in c.actions+c.traits)
                        and not any(n in c.spells for n in ("Misty Step","Dimension Door"))], key=lambda c: c.id)
        if actor in melee and melee.index(actor) < len(fronts) * options.screen: return fronts
        return enemies

    def monster_target(self, actor, enemies):
        options = getattr(self, "day_options", None)
        if not options or actor.team == "party": return None
        candidates = [c for c in enemies if c.hp > 0] if not options.attack_downed else enemies
        candidates = candidates or enemies
        if not candidates: return None
        if options.targeting == "random": return self.rng.choice(candidates)
        if options.targeting == "focus_low_hp": return min(candidates, key=lambda c: (c.hp, c.id))
        def threat(c):
            damage = self.damage_dealt.get(c.id, 0)
            forecast = self.at_will_damage_rate(c, actor)
            return damage, forecast, c.id
        return max(candidates, key=threat)

    def monster_order(self, actor, enemies):
        """The order that repeated monster_target picks (removing each pick) would give,
        computing each candidate's key once. Not for "random" targeting, which draws dice."""
        options = self.day_options
        tiers = (list(enemies), []) if options.attack_downed else ([c for c in enemies if c.hp > 0], [c for c in enemies if c.hp <= 0])
        if options.targeting == "focus_low_hp":
            return [c for tier in tiers for c in sorted(tier, key=lambda c: (c.hp, c.id))]
        keys = {c.id: (self.damage_dealt.get(c.id, 0), self.at_will_damage_rate(c, actor), c.id) for c in enemies}
        return [c for tier in tiers for c in sorted(tier, key=lambda c: keys[c.id], reverse=True)]
