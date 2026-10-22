"""Sheet-declared monster mechanics, sharing Combat's rolls/effect resolver."""
from . import dice
from .state import Combatant, SpellInstance

class MonsterMechanics:
    def feature_log(self, actor, name, **extra):
        self.record("trait", actor=actor.id, name=name, **extra)

    def monster_instance(self, actor, name, effects, duration=None):
        spec = {"name": name, "duration": duration or {"type": "special"}, "effects": effects, "ends_on": []}
        inst = SpellInstance(self.next_instance, spec, actor, 0, self.turn_index, self.time_rounds)
        self.next_instance += 1
        self.instances[inst.id] = inst
        return inst

    def initialize_monsters(self):
        self.sunlight = False
        self._monster_attack = None
        self._critical_damage = False
        for actor in self.combatants:
            actor.legendary_remaining = actor.legendary.get("uses", 0)
            for trait in actor.traits:
                if trait.get("passive"):
                    inst = self.monster_instance(actor, trait["name"], trait["effects"])
                    inst.spec["monster_passive"] = True

    def monster_flags(self, actor, on, against=None):
        adv = dis = False
        if actor.features.get("bloodied_frenzy") and actor.hp <= actor.max_hp / 2 and on in {"attack_rolls", "saves"}:
            adv = True
            self.feature_log(actor, "Bloodied Frenzy")
        if actor.features.get("sunlight_sensitivity") and self.sunlight and on in {"attack_rolls", "ability_checks"}:
            dis = True
            self.feature_log(actor, "Sunlight Sensitivity")
        if on == "attack_rolls" and against is not None and actor.features.get("pack_tactics"):
            # No grid: a living, capable melee-equipped ally is engaged in melee.
            if any(c is not actor and c.team == actor.team and c.alive and not c.has_condition("incapacitated") and any(a["kind"] == "melee" for a in c.attacks) for c in self.combatants):
                adv = True
                self.feature_log(actor, "Pack Tactics")
        if on in {"attack_rolls", "saves"}:
            for captain in self.combatants:
                if captain.features.get("authority_aura") and captain.team == actor.team and captain.alive and not captain.has_condition("incapacitated"):
                    allies = [c for c in self.combatants if c.team == actor.team and c.alive and c is not captain]
                    count = self.area("emanation", 10, len(allies))
                    covered = allies[:count] if isinstance(count, int) else [allies[i] for i in count]
                    if actor is captain or actor in covered:
                        adv = True
                        self.feature_log(captain, "Aura of Authority", target=actor.id)
        return adv, dis

    def legendary_resist(self, target, ability, dc):
        if target.limited_uses.get("legendary_resistance", 0) and self.policy_for(target).legendary_resistance(self, target, ability, dc):
            target.limited_uses["legendary_resistance"] -= 1
            target.spend("legendary_resistance")
            self.feature_log(target, "Legendary Resistance")
            return True
        return False

    def start_monster_turn(self, actor):
        actor.legendary_remaining = actor.legendary.get("uses", 0)
        actor.legendary_used.clear()
        regen = actor.features.get("regeneration")
        if regen:
            blocked = actor.statuses.pop("regeneration_blocked", None)
            if blocked is None and (actor.alive or (regen["at_zero"] and actor.hp == 0 and not actor.removed and not actor.permanently_removed)):
                before = actor.hp
                self.heal(actor, regen["amount"])
                self.feature_log(actor, "Regeneration", amount=actor.hp - before)
            elif blocked is not None:
                self.feature_log(actor, "Regeneration", blocked=True)
            if actor.hp == 0: actor.permanently_removed = True
        # Release source-bound grapples/control when their source cannot sustain them.
        for c in self.combatants:
            for effect in list(c.effects):
                inst = self.instances.get(effect.source)
                if inst and effect.data.get("linked") and (not inst.caster.alive or (inst.caster.has_condition("incapacitated") and not effect.data.get("control"))):
                    self.remove_effects(inst, c)
        if actor.alive:
            for source in self.combatants:
                if not source.alive: continue
                for trait in source.traits:
                    if trait.get("trigger") not in {"enemy_turn_start", "creature_turn_start"}: continue
                    if trait["trigger"] == "enemy_turn_start" and source.team == actor.team: continue
                    if trait["cost"] != "free" and source.has_condition("incapacitated"): continue
                    if trait["cost"] == "reaction" and not source.reaction: continue
                    marker = {"Stench": "stench_immune", "Unnerving Gaze": "gaze_immune"}.get(trait["name"], "")
                    if actor.has_status_from(marker, source): continue
                    probe = self.monster_instance(source, trait["name"], trait["effects"], trait.get("duration"))
                    block = trait["effects"][0]
                    members = self.area_members(probe, block, self.eligible(probe, block)) if block["target"]["select"] == "area" else [actor]
                    if actor not in members:
                        self.end_spell(probe.id)
                        continue
                    if trait["cost"] == "reaction": source.reaction -= 1
                    self.feature_log(source, trait["name"], target=actor.id)
                    if block["target"]["select"] == "area": probe.area_members[block["id"]] = [actor]
                    self.resolve_block(probe, block, "on_cast", {"who": actor}, [actor])
                    if trait["name"] == "Unnerving Gaze":
                        for e in actor.effects:
                            if e.source == probe.id and e.until: e.until = ("end_of_turn", actor.id, actor.turns_taken)
        if actor.features.get("grapple_damage") and actor.alive:
            for target in self.combatants:
                if actor in self.condition_sources(target, "grappled") or target in self.condition_sources(actor, "grappled"):
                    self.damage(target, dice.roll(self.rng, "1d10"), "piercing", actor)
                    self.feature_log(actor, "Barbed Hide")

    def monster_damage(self, target, amount, dtype):
        regen = target.features.get("regeneration")
        if amount and regen and dtype in regen["blocked_by"]:
            target.statuses["regeneration_blocked"] = {}

    def monster_drain(self, source, target, typed):
        if source is None: return
        drain = source.features.get("life_drain")
        context = self._monster_attack
        if drain and context and context[0] is source and context[1] in drain["attacks"]:
            amount = sum(typed.values()) if drain["type"] == "all" else typed.get(drain["type"], 0)
            target.max_hp = max(0, target.max_hp - amount)
            target.hp = min(target.hp, target.max_hp)
            if drain["heal"]: self.heal(source, amount)
            self.feature_log(source, "Life Drain", amount=amount)

    def monster_reaction(self, attacker, defender, attack, melee):
        parry = defender.features.get("parry")
        if parry and defender.reaction and not defender.has_condition("incapacitated") and melee and attack["natural"] != 20 and attack["total"] < self.armor_class(defender) + parry and self.policy_for(defender).reaction(self, defender, {"name": "Parry"}, {"attack": attack}):
            defender.reaction -= 1
            self.record("reaction", actor=defender.id, name="Parry")
            return True
        return False

    def redirect_target(self, attacker, defender):
        if defender.features.get("redirect_attack") and defender.reaction and not defender.has_condition("incapacitated"):
            allies = [c for c in self.combatants if c is not defender and c.team == defender.team and c.alive and c.size in {"S", "M"}]
            target = self.policy_for(defender).redirect_attack(self, defender, allies)
            if target in allies:
                defender.reaction -= 1
                self.record("reaction", actor=defender.id, name="Redirect Attack", target=target.id)
                return target
        return defender

    def escape(self, actor):
        effects = [e for e in actor.active_effects if (e.kind == "apply_condition" and ("escape_dc" in e.data or "obstacle" in e.data)) or (e.kind == "status" and e.data["id"] == "engulfed")]
        if not effects or not actor.action or actor.has_condition("incapacitated"): return False
        effect = effects[0]
        actor.action -= 1
        if "obstacle" in effect.data:
            data = effect.data["obstacle"]
            obstacle = Combatant("obstacle", team="object", max_hp=data["hp"], hp=effect.data.get("obstacle_hp", data["hp"]), ac=data["ac"], creature_type="object", vulnerabilities=data["vulnerabilities"], immunities=data["immunities"])
            routine = actor.multiattack or ([actor.attacks[0]["name"]] * actor.extra_attack if actor.attacks else [])
            for name in routine:
                if not obstacle.alive: break
                attack = next((a for a in actor.attacks if a["name"] == name), None)
                if attack: self.weapon_attack(actor, obstacle, attack)
            effect.data["obstacle_hp"] = obstacle.hp
            if obstacle.hp == 0:
                inst = self.instances.get(effect.source)
                if inst: self.remove_effects(inst, actor)
            self.record("break_obstacle", actor=actor.id, remaining_hp=obstacle.hp)
            return True
        data = effect.data["data"] if effect.kind == "status" else effect.data
        ability = max(("str", "dex"), key=actor.mod) if data.get("condition") == "grappled" else "str"
        success = self.ability_check(actor, ability, data["escape_dc"])
        self.record("escape", actor=actor.id, success=success, dc=data["escape_dc"])
        if success:
            inst = self.instances.get(effect.source)
            if inst: self.remove_effects(inst, actor)
        return True

    def routine(self, actor, target):
        options = actor.routines or ([actor.multiattack or [actor.attacks[0]["name"]] * actor.extra_attack] if actor.attacks else [])
        return self.policy_for(actor).monster_routine(self, actor, target, options) if options else []

    def routine_value(self, actor, names, target, control=False):
        total = 0
        for name in names:
            attack = next((a for a in actor.attacks if a["name"] == name), None)
            if attack:
                if not actor.recharge_ready.get(name, True): continue
                total += sum(dice.mean(p["damage"]["dice"]) + p["damage"].get("bonus", 0) for p in attack["effects"] if "damage" in p and "if" not in p) * self.hit_probability(actor, target, attack["to_hit"])
            else:
                action = next((a for a in actor.actions if a["name"] == name), None)
                if action and actor.limited_uses.get(action.get("resource"), 1): total += self.expected_spell_damage(actor, {"effects": action["effects"]}, target, horizon=1, control_value=control)
                elif name in actor.spells: total += self.expected_spell_damage(actor, self.scale(actor, self.spells[name], actor.spell_levels.get(name, self.spells[name]["level"])), target, horizon=1)
        return total

    def perform_option(self, actor, name, targets=None):
        attack = next((a for a in actor.attacks if a["name"] == name), None)
        if attack:
            enemies = self.enemies(actor)
            if not enemies: return False
            target = targets[0] if targets else min(enemies, key=lambda c: (c.hp, c.id))
            return self.weapon_attack(actor, target, attack)
        # A routine/legendary action grants just this option, not a whole turn.
        old = actor.action, actor.bonus_action, actor.reaction, self.current
        actor.action = actor.bonus_action = actor.reaction = 1
        self.current = actor
        try:
            if name in actor.spells: return self.cast(actor, name)
            return self.use_action(actor, name)
        finally: actor.action, actor.bonus_action, actor.reaction, self.current = old

    def legendary_actions(self, finished):
        for actor in self.combatants:
            if actor is finished or not actor.alive or actor.has_condition("incapacitated") or not self.enemies(actor): continue
            options = [a for a in actor.legendary.get("options", []) if a["cost"] <= actor.legendary_remaining and not (a.get("once_per_round") and a["name"] in actor.legendary_used) and (not a.get("requires_bound_target") or any(c.has_condition_from("grappled", actor) or c.has_condition_from("charmed", actor) for c in self.combatants))]
            option = self.policy_for(actor).legendary_action(self, actor, finished, options)
            if option not in options: continue
            actor.legendary_remaining -= option["cost"]
            actor.legendary_used.add(option["name"])
            self.record("legendary_action", actor=actor.id, name=option["name"], after=finished.id, remaining=actor.legendary_remaining)
            if "attacks" in option:
                for name in option["attacks"]: self.perform_option(actor, name)
            elif "spell" in option: self.perform_option(actor, option["spell"])
            else:
                inst = self.monster_instance(actor, option["name"], option["effects"])
                for block in option["effects"]: self.resolve_block(inst, block, "on_cast", {})
            if "heal" in option: self.heal(actor, dice.roll(self.rng, option["heal"]))
