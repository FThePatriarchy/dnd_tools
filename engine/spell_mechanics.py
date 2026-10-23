"""Small, shared spell mechanics, not spell-name-to-prose dispatch."""
from . import dice
from .state import Effect


class SpellMechanics:
    def damage_hook(self, spell, hook, amount):
        if hook.get("leech"): self.heal(spell.caster, int(amount * hook["leech"]))
        spell.damage_total += amount
        if hook.get("end_after_total") and spell.damage_total >= hook["end_after_total"]: self.end_spell(spell.id)
    def condition_immune(self, target, condition, magical=False, source=None):
        if condition in target.condition_immunities: return True
        if source and any(e.kind == "ward" and (source.magical_type if magical else source.creature_type) in e.data["types"] and condition in e.data.get("conditions", []) for e in target.active_effects): return True
        return any(condition in e.data.get("condition_immunity", []) or
            magical and condition in e.data.get("magical_condition_immunity", [])
            for e in target.active_effects if e.kind == "defense")

    def spell_roll_flags(self, actor, on, against):
        dis = False
        if on == "attack_rolls" and against:
            dis |= any(e.kind == "disadvantage" and e.data.get("curse_attack") and e.source in self.instances and against is self.instances[e.source].caster for e in actor.active_effects)
            dis |= any(e.kind == "ward" and e.data.get("attack_disadvantage") and actor.magical_type in e.data["types"] for e in against.active_effects)
            dis |= any(e.kind == "duel" and e.source in self.instances and against is not self.instances[e.source].caster for e in actor.active_effects)
        return False, dis

    def sanctuary_allows(self, actor, target):
        for effect in target.active_effects:
            if effect.kind == "sanctuary":
                inst = self.instances.get(effect.source)
                if inst and not self.saving_throw(actor, effect.data["ability"], inst.caster.spell_dc):
                    self.record("sanctuary_block", actor=actor.id, target=target.id)
                    return False
        return True

    def isolation(self, actor):
        return {e.source for e in actor.active_effects if e.kind == "status" and e.data["id"] == "isolated"} if actor else set()

    def duel_activity(self, actor, target):
        for inst in list(self.instances.values()):
            if inst.active and inst.caster is actor and any(e.kind == "duel" and e.source == inst.id for c in self.combatants for e in c.active_effects):
                if not any(target in b.targets for b in inst.bindings.values()): self.end_spell(inst.id)

    def spell_turn(self, actor):
        for e in list(actor.active_effects):
            if e.kind == "curse_dodge" and e.source in self.instances and not self.saving_throw(actor, e.data["ability"], self.instances[e.source].caster.spell_dc):
                actor.action = 0
                actor.effects.append(Effect("disadvantage", {"on": "attack_rolls", "scope": "all", "against": "target", "recipient": "any_attacker"}, e.source, "curse_dodge", ("start_of_turn", actor.id, actor.turns_taken + 1)))
                self.record("dodge", actor=actor.id)
        self.reconcile_economy(actor)
        for effect in list(actor.active_effects):
            if effect.kind != "turn_rules": continue
            inst = self.instances.get(effect.source)
            if effect.data.get("forced_melee") and inst:
                candidates = [c for c in self.enemies(inst.caster) if c is not actor]
                attack = next((a for a in actor.attacks if a["kind"] == "melee"), None)
                if candidates and attack:
                    actor.action = 0
                    self.weapon_attack(actor, candidates[0], attack)
            if effect.data.get("behavior_die"):
                roll = dice.roll(self.rng, effect.data["behavior_die"])
                self.record("confusion", actor=actor.id, roll=roll)
                if roll <= 8: actor.action = 0
                if 7 <= roll <= 8:
                    candidates = [c for c in self.combatants if c is not actor and c.alive]
                    attack = next((a for a in actor.attacks if a["kind"] == "melee"), None)
                    if candidates and attack: self.weapon_attack(actor, self.rng.choice(candidates), attack)

    def study_illusion(self, actor, source):
        inst = self.instances.get(source)
        if not inst or not actor.action or not actor.has_status_from("phantasmal_force", inst.caster): return False
        self.spend_economy(actor, "action")
        if self.ability_check(actor, "int", inst.caster.spell_dc, "investigation"): self.end_spell(source)
        return True

    def restore(self, target, kind, all_curses=False, source_types=None):
        if kind == "exhaustion":
            target.exhaustion_level = max(0, target.exhaustion_level - 1)
            if not target.exhaustion_level: target.conditions.discard("exhaustion")
        elif kind == "max_hp": target.base_max_hp = target.original_max_hp
        elif kind in target.abilities: target.abilities[kind] = target.original_abilities[kind]
        elif kind == "curse":
            ids = []
            for effect in target.active_effects:
                if effect.kind == "status" and effect.data["id"] in {"hexed", "cursed"} and effect.source not in ids: ids.append(effect.source)
            for source in ids if all_curses else ids[:1]: self.end_spell(source)
        else:
            if not self.can_end_condition(target, kind): return
            if not source_types: target.conditions.discard(kind)
            for effect in list(target.effects):
                if effect.kind == "apply_condition" and effect.data["condition"] == kind:
                    if source_types and (effect.source not in self.instances or self.instances[effect.source].caster.creature_type not in source_types): continue
                    target.effects.remove(effect)
        self.refresh_spell_effects()
        self.record("restore", target=target.id, restored=kind)

    def spell_primitive(self, key, value, instance, target):
        if key == "force_object":
            from .state import Combatant
            obj = Combatant(f"hand_{instance.id}", name="Bigby's Hand", team=instance.caster.team, max_hp=instance.caster.max_hp, ac=value["ac"], creature_type="object", size="L")
            obj.summoner_id = instance.caster.id; obj.summoned_source = instance.id
            obj.statuses["summon_rules"] = {"object_only": True}
            obj.statuses["force_object"] = {}
            instance.summoned.append(obj); self.combatants.append(obj)
        elif key == "transform":
            from fractions import Fraction
            from copy import deepcopy
            form = value["forms"][instance.choices[value["choice"][1:]]]
            original = target.transform_snapshot or {"cr": target.cr, "level": target.level}
            if Fraction(form["cr"]) > Fraction(str(original["cr"] if original["cr"] is not None else original["level"])): return True
            from .state import Combatant
            fields = ("ac", "abilities", "original_abilities", "speed", "movement_modes", "proficiency_bonus",
                      "save_bonuses", "save_proficiencies", "initiative_bonus", "extra_attack", "attacks",
                      "actions", "traits", "features", "spells", "size", "resistances", "immunities",
                      "vulnerabilities", "condition_immunities", "multiattack", "routines", "replacements",
                      "legendary", "legendary_remaining", "legendary_used", "spell_ability", "spell_dc",
                      "spell_attack_bonus", "spell_slots", "max_spell_slots", "innate_spells", "spell_resources", "spell_levels",
                      "spell_costs", "spell_recharge", "spell_components", "limited_uses", "max_limited_uses", "resource_recovery", "recharge_ready",
                      "extra_actions", "action_grants", "surge_actions", "level", "cr")
            if target.transform_snapshot is None:
                target.transform_snapshot = {k: deepcopy(getattr(target, k)) for k in fields}
            beast = Combatant.from_sheet(form, "_form", target.team)
            stats = {k: deepcopy(getattr(beast, k)) for k in fields}
            target.effects.append(Effect("transform", {"stats": stats, "temp_hp": form["max_hp"]}, instance.id, "transform"))
            target.effects.append(Effect("turn_rules", {"no_spells": True}, instance.id, "transform"))
            self.refresh_spell_effects()
        elif key == "control":
            target.effects.append(Effect("control", {"control_team": instance.caster.team}, instance.id, "control"))
            if target.summoned_source in self.instances:
                parent = self.instances[target.summoned_source]
                parent.spec = {**parent.spec, "duration": instance.spec["duration"]}
        elif key == "size_change":
            target.effects.append(Effect("size_change", {"original": target.size}, instance.id, "size"))
            i = "TSMLHG".index(target.size) + (1 if value["direction"] == "increase" else -1)
            target.size = "TSMLHG"[max(0, min(5, i))]
        elif key == "max_hp":
            old = next((e for e in target.effects if e.kind == key and e.source == instance.id), None)
            if not old:
                target.effects.append(Effect(key, dict(value), instance.id, "max_hp"))
                self.refresh_spell_effects()
        elif key == "hit_dice_heal":
            count = min(target.hit_dice, value["max_dice"])
            if target.hit_die and count:
                target.hit_dice -= count
                self.heal(target, sum(dice.roll(self.rng, "1" + target.hit_die if target.hit_die.startswith("d") else target.hit_die) for _ in range(count)) + instance.caster.spell_mod)
        elif key == "extinguish": self.extinguish(target, method="doused")
        elif key == "stabilize":
            if target.hp == 0 and not target.permanently_removed: target.statuses["stable"] = {}
        elif key == "restore":
            kind = value["kind"]
            if kind.startswith("$"): kind = instance.choices[kind[1:]]
            self.restore(target, kind, value.get("all", False), value.get("source_types"))
        elif key == "maintain_spell": instance.maintained_turn = instance.caster.turns_taken
        else: return False
        return True

    def reconcile_transform(self, target):
        from copy import deepcopy
        effective = next((e for e in reversed(target.active_effects) if e.kind == "transform"), None)
        if effective is not target.effective_transform:
            if target.effective_transform is not None:
                target.effective_transform.data["temp_hp"] = target.temp_hp
            stats = effective.data["stats"] if effective else target.transform_snapshot
            if stats is not None:
                for k, v in stats.items(): setattr(target, k, deepcopy(v))
                target.temp_hp = effective.data["temp_hp"] if effective else 0
            target.effective_transform = effective
        if not any(e.kind == "transform" for e in target.effects): target.transform_snapshot = None

    def deplete_transform(self, target):
        effect = target.effective_transform
        if effect is None or target.temp_hp: return
        instance = self.instances[effect.source]
        self.remove_effects(instance, target)
        if not any(e.kind == "transform" and e.source == instance.id for c in self.combatants for e in c.effects):
            self.end_spell(instance.id)

    def eat_berry(self, actor, source):
        inst = self.instances.get(source)
        stock = next((e for c in self.combatants for e in c.active_effects if e.source == source and e.kind == "berries" and e.data["count"]), None)
        if not inst or not stock or not actor.bonus_action or not actor.alive: return False
        actor.bonus_action -= 1
        stock.data["count"] -= 1
        self.heal(actor, stock.data["healing"])
        self.record("eat_berry", actor=actor.id, source=source)
        return True

    def mirror_intercepts(self, attacker, target):
        if attacker.has_condition("blinded") or attacker.features.get("blindsight") or attacker.features.get("truesight"): return False
        for e in target.active_effects:
            if e.kind == "mirror_images" and any(dice.roll(self.rng, e.data["dice"]) >= e.data["threshold"] for _ in range(e.data["count"])):
                e.data["count"] -= 1
                self.record("mirror_intercept", target=target.id)
                if not e.data["count"]: self.end_spell(e.source)
                return True
        return False

    def spell_end_turn(self, actor):
        for e in list(actor.active_effects):
            if e.kind == "blink":
                roll = dice.roll(self.rng, e.data["dice"])
                self.record("blink_roll", actor=actor.id, roll=roll)
                if roll >= e.data["threshold"]:
                    actor.effects.append(Effect("status", {"id": "isolated", "data": {}}, e.source, "ethereal", ("start_of_turn", actor.id, actor.turns_taken + 1)))

    def curse_extra(self, target, source, amount):
        if not amount or getattr(self, "_curse_packet", False): return
        for e in list(target.active_effects):
            if e.kind == "curse_damage" and e.source in self.instances and self.instances[e.source].caster is source:
                self._curse_packet = True
                try: self.damage(target, dice.roll(self.rng, e.data["dice"]), e.data["type"], source)
                finally: self._curse_packet = False

    def tally_saves(self, actor):
        for e in list(actor.active_effects):
            if e.kind != "apply_condition" or "tally_save" not in e.data: continue
            inst = self.instances.get(e.source)
            if not inst: continue
            v = e.data["tally_save"]
            outcome = "success" if self.saving_throw(actor, v["ability"], inst.caster.spell_dc, magical=True) else "failure"
            e.data[outcome] = e.data.get(outcome, 0) + 1
            if e.data[outcome] >= v[outcome + "es" if outcome == "success" else "failures"]:
                if outcome == "success": self.remove_effects(inst, actor)
                else:
                    inst.spec = {**inst.spec, "duration": {"type": "hours", "n": v["failure_hours"]}}
                    e.data.pop("tally_save")

    def orb_leap(self, inst, block, target):
        seen = inst.limits_count.setdefault("orb_seen", set()); seen.add(target.id)
        leaps = inst.limits_count.get("orb_leaps", 0)
        if not inst.limits_count.get("orb_duplicate") or leaps >= max(1, inst.slot): return
        candidates = [c for c in self.eligible(inst, block) if c.id not in seen]
        if not candidates: return
        inst.limits_count["orb_leaps"] = leaps + 1
        next_target = self.policy_for(inst.caster).targets(self, inst, block, candidates, 1)
        if next_target: self.resolve_block(inst, block, "on_cast", {}, next_target)

    def replace_weapon_attack(self, actor, target, attack, slot=None):
        """Lightning Arrow replaces the original hit/miss packet, not just dice."""
        if not self.can_cast(actor, "Lightning Arrow", slot): return None
        result = []
        def replace(critical, roll):
            result.append(self.cast(actor, "Lightning Arrow", [target], slot=slot, trigger={"attacker":actor,"defender":target,"attack":roll,"critical":critical}))
        hit = self.attack(actor,target,attack["to_hit"],replace,melee=False,weapon=True)
        if not hit:
            replace(False,{"weapon":True,"melee":False,"hit":False})
        return result[0] if result else None

    def can_end_condition(self, target, condition):
        for e in target.active_effects:
            if e.kind == "apply_condition" and e.data["condition"] == condition and e.data.get("resist_removal"):
                inst = self.instances.get(e.source)
                if inst and not self.saving_throw(target, e.data["resist_removal"], inst.caster.spell_dc, magical=True): return False
        return True

    def dismiss_form(self, actor, source):
        inst = self.instances.get(source)
        if not inst or self.current is not actor or not actor.action or actor.has_condition("incapacitated"): return False
        if not any(e.source == source and e.kind == "turn_rules" and e.data.get("dismiss_action") for e in actor.active_effects): return False
        self.spend_economy(actor,"action"); self.remove_effects(inst,actor)
        return True
