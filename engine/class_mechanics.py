"""Small class hooks at existing roll, hit, save and rest boundaries."""
from . import dice
from .state import Effect
from .sheets import effect_block
from copy import deepcopy

SKILLS = {"acrobatics", "animal handling", "arcana", "athletics", "deception", "history", "insight", "intimidation", "investigation", "medicine", "nature", "perception", "performance", "persuasion", "religion", "sleight of hand", "stealth", "survival", "thieves' tools", "poisoner's kit", "disguise kit"}


class ClassMechanics:
    def divine_intervention(self, actor, name, targets=None, choices=None):
        from .builder import spell_options
        options=spell_options("cleric",10)
        if name not in options or not 1 <= options[name]["level"] <= 5 or options[name]["casting_time"]=="reaction": raise ValueError("Divine Intervention requires a supported level 1–5 Cleric nonreaction spell")
        if not actor.limited_uses.get("divine_intervention",0): return None
        spells=actor.spells[:]; resources=actor.spell_resources.copy(); costs=actor.spell_costs.copy()
        if name not in actor.spells: actor.spells.append(name)
        actor.spell_resources[name]="divine_intervention"; actor.spell_costs[name]="action"
        try:
            if not self.can_cast(actor,name): return None
            self.feature_log(actor,"Divine Intervention",spell=name)
            return self.cast(actor,name,targets=targets,choices=choices)
        finally:
            actor.spells=spells; actor.spell_resources=resources; actor.spell_costs=costs

    def sear_undead(self, instance, target):
        if instance.spec["name"] != "Turn Undead" or not instance.caster.features.get("sear_undead"): return
        if "_sear" not in instance.choices: instance.choices["_sear"] = dice.roll(self.rng, f"{max(1,instance.caster.mod('wis'))}d8")
        previous = self._damage_batch
        self._damage_batch = None
        self.damage(target, instance.choices["_sear"], "radiant", instance.caster)
        self._damage_batch = previous
        self.feature_log(instance.caster,"Sear Undead",target=target.id)

    def class_scale(self, actor, spec):
        if actor.features.get("potent_cantrip") and spec["level"] == 0:
            for b in spec["effects"]:
                if b["attack"] and not b.get("on_miss"):
                    b["on_miss"] = [{"damage": {**deepcopy(p["damage"]), "half": True}} for p in b["on_hit"] if "damage" in p]
                if b["save"] and any("damage" in p for p in b["on_fail"]):
                    b["save"]["on_success"] = "half"
        return spec

    def sculpt_targets(self, instance, block, targets):
        caster = instance.caster
        if not caster.features.get("sculpt_spells") or instance.spec.get("school") != "evocation" or not block["save"]: return
        chosen = instance.choices.setdefault("_sculpted", set())
        eligible = [t for t in targets if t is not caster and t.team == caster.team and t.visible_to(caster) and t.id not in chosen]
        n = 1 + max(instance.slot, instance.spec["level"]) - len(chosen)
        selected = self.policy_for(caster).sculpt_spells(self, caster, eligible, max(0,n))
        if len(selected) > max(0,n) or len(set(selected)) != len(selected) or any(t not in eligible for t in selected): raise ValueError("illegal Sculpt Spells selection")
        chosen.update(t.id for t in selected)

    def class_damage_bonus(self, instance, target, amount, block):
        caster, spec = instance.caster, instance.spec
        if "level" not in spec: return amount
        if spec["level"] == 0 and caster.features.get("potent_spellcasting"):
            amount += caster.spell_mod
            self.feature_log(caster, "Potent Spellcasting")
        if caster.features.get("empowered_evocation") and spec["school"] == "evocation":
            # One roll, not one target: shared-roll spells reuse this augmented value.
            if "_empowered_roll" not in instance.choices:
                instance.choices["_empowered_roll"] = (block, target.id)
                amount += caster.mod("int")
                self.feature_log(caster, "Empowered Evocation")
        return amount

    def class_weapon_dice(self, actor, expression, critical, ctx):
        if actor.features.get("great_weapon_fighting") and ctx.get("attack",{}).get("weapon") and ctx.get("attack",{}).get("melee") and "two_handed" in ctx.get("weapon_properties",[]):
            n,sides,flat=dice.parts(expression)
            self.feature_log(actor,"Great Weapon Fighting")
            return sum(max(3,self.rng.randint(1,sides)) for _ in range(n*(2 if critical else 1)))+flat
        return dice.roll(self.rng,expression,critical)

    def sneak_eligible(self, actor, target, attack, roll=None):
        if not actor.features.get("sneak_attack") or not (attack["kind"] == "ranged" or "finesse" in attack.get("properties", [])): return False
        if actor.statuses.get("sneak_turn") == self.turn_index: return False
        if roll is None:
            adv, dis = self.roll_flags(actor, "attack_rolls", attack.get("ability", "dex"), against=target)
            dis |= any(actor.has_condition(c) for c in ("blinded", "restrained", "poisoned", "frightened", "prone"))
            adv |= any(target.has_condition(c) for c in ("prone", "restrained", "paralyzed", "stunned", "unconscious", "blinded")) and attack["kind"] == "melee"
            advantage, disadvantage = adv and not dis, dis and not adv
        else: advantage, disadvantage = roll["advantage"], roll["disadvantage"]
        adjacent = any(c is not actor and c.team == actor.team and c.alive and not c.has_condition("incapacitated") and any(a["kind"] == "melee" for a in c.attacks) for c in self.combatants)
        return advantage or adjacent and not disadvantage

    def class_hit(self, actor, target, attack, critical, roll):
        option = None
        if self.sneak_eligible(actor, target, attack, roll):
            dtype = next((p["damage"]["type"] for p in attack["effects"] if "damage" in p), "piercing")
            actor.statuses["sneak_turn"] = self.turn_index
            n, sides, flat = dice.parts(actor.features["sneak_attack"])
            options = [o for o in actor.cunning_strike if o != "poison" or actor.features.get("poisoners_kit")]
            option = self.policy_for(actor).cunning_strike(self, actor, target, options)
            if option not in options and option is not None: raise ValueError("invalid Cunning Strike choice")
            if option: n -= 1
            amount = dice.roll(self.rng, f"{n}d{sides}", critical) + flat if n else flat
            if actor.features.get("assassinate") and self.round == 1: amount += actor.level
            self.damage(target, amount, dtype, actor)
            self.feature_log(actor, "Sneak Attack", dice=f"{n}d{sides}", critical=critical)
        if actor.features.get("divine_strike") and self.current is actor and actor.statuses.get("strike_turn") != self.turn_index:
            actor.statuses["strike_turn"] = self.turn_index
            self.damage(target, dice.roll(self.rng, actor.features["divine_strike"], critical), "radiant", actor)
            self.feature_log(actor, "Divine Strike")
        return option

    def class_after_hit(self, actor, target, option):
        if option is None or not target.alive: return
        self.feature_log(actor, "Cunning Strike", option=option)
        if option == "withdraw":
            actor.statuses["withdraw"] = {"turn": self.turn_index}
            return
        if option == "trip" and target.size not in {"T", "S", "M", "L"}: return
        condition = {"condition": "poisoned" if option == "poison" else "prone"}
        if option == "poison": condition["repeat_save"] = {"ability": "con", "timing": "end_of_turn", "on_success": "end"}
        # The rider follows the creature just hit, even if the hit's damage changed
        # its allegiance (a dominated ally breaking free on its repeat save).
        block = effect_block("cunning_strike", target={"select": "single", "filter": ["creature"], "affects": "any"}, save={"ability": "con" if option == "poison" else "dex", "dc": 8 + actor.mod("dex") + actor.proficiency_bonus, "on_success": "negate"}, on_fail=[{"apply_condition": condition}])
        inst = self.monster_instance(actor, "Cunning Strike", [block], {"type": "minutes", "n": 1} if option == "poison" else {"type": "special"})
        self.resolve_block(inst, block, "on_cast", {}, [target])

    def uncanny_reduce(self, typed, attack_context):
        if attack_context is None: return
        attacker, target, attack = attack_context
        if not target.features.get("uncanny_dodge") or not target.reaction or target.has_condition("incapacitated") or self.turn_rules(target).get("no_reactions") or not attacker.visible_to(target): return
        entries = [(k, n) for k, n in typed.items() if k[0] is target]
        total = sum(n for k, n in entries)
        if total <= 0 or not self.policy_for(target).reaction(self, target, {"name": "Uncanny Dodge"}, {"attack": attack, "damage": total}): return
        target.reaction -= 1
        self.record("reaction", actor=target.id, name="Uncanny Dodge", damage=total)
        spare = total // 2 - sum(n // 2 for k, n in entries)
        for k, n in entries:
            extra = int(bool(n % 2 and spare))
            typed[k] = n // 2 + extra
            spare -= extra

    def class_flags(self, actor, on, scope, against):
        adv = bool(on == "initiative" and actor.features.get("initiative_advantage"))
        adv |= on == "ability_checks" and scope == "athletics" and actor.features.get("remarkable_athlete", False)
        if on == "attack_rolls" and against is not None and actor.features.get("assassinate") and self.round == 1 and against.turns_taken == 0:
            adv = True
        return adv, False

    def heroic_reroll(self, actor, natural, succeeds):
        if not succeeds(natural) and actor.statuses.pop("heroic_inspiration", None) is not None:
            self.feature_log(actor, "Heroic Inspiration")
            return dice.reroll(self.rng, natural, self.policy_for(actor).reroll_die(self, actor, natural))
        return natural

    def class_failed_save(self, actor, ability, dc, bonus, natural, success):
        if not success and actor.limited_uses.get("indomitable", 0) and self.policy_for(actor).indomitable(self, actor, ability, dc):
            actor.limited_uses["indomitable"] -= 1
            actor.spend("indomitable")
            natural = dice.reroll(self.rng, natural, self.policy_for(actor).reroll_die(self, actor, natural))
            total = natural + bonus + actor.level
            self.feature_log(actor, "Indomitable", total=total, dc=dc)
            return total >= dc, total, natural
        return success, natural + bonus, natural

    def class_start_turn(self, actor):
        if actor.features.get("heroic_warrior") and actor.alive:
            actor.statuses.setdefault("heroic_inspiration", {})
            self.feature_log(actor, "Heroic Warrior")

    def class_weapon(self, actor, attack, target):
        if actor.features.get("tactical_master") and attack.get("mastery"):
            selected = self.policy_for(actor).tactical_master(self, actor, attack, target)
            if selected not in {None, "sap", "slow", "push"}: raise ValueError("invalid Tactical Master choice")
            if selected:
                attack = {**attack, "mastery": selected}
                self.feature_log(actor, "Tactical Master", mastery=selected)
        return attack

    def class_mastery(self, actor, target, attack):
        mastery = attack.get("mastery")
        if mastery == "slow":
            target.effects = [e for e in target.effects if e.block != "mastery_slow"]
            target.effects.append(Effect("modify", {"stat": "speed", "op": "sub", "value": 10, "scope": "all"}, 0, "mastery_slow", ("start_of_turn", actor.id, actor.turns_taken + 1)))
        elif mastery == "push":
            self.feature_log(actor, "Push", target=target.id, spatial_only=True)
        elif mastery == "topple" and target.size in {"T", "S", "M", "L", "H", "G"}:
            dc = 8 + actor.proficiency_bonus + actor.mod(attack.get("ability", "str"))
            if not self.saving_throw(target, "con", dc): target.conditions.add("prone")

    def class_check(self, actor, ability, skill, natural, bonus, dc):
        if actor.features.get("thaumaturge") and ability == "int" and skill in {"arcana","religion"}: bonus += max(1,actor.mod("wis"))
        total = natural + bonus
        if total < dc and actor.features.get("tactical_mind") and actor.limited_uses.get("second_wind", 0) and self.policy_for(actor).tactical_mind(self, actor, ability, dc):
            added = dice.roll(self.rng, "1d10")
            if total + added >= dc:
                actor.limited_uses["second_wind"] -= 1
                actor.spend("second_wind")
            self.feature_log(actor, "Tactical Mind", added=added, success=total + added >= dc)
            total += added
        return total >= dc


def arcane_recovery(actor, policy, log=None):
    if not actor.features.get("arcane_recovery") or not actor.limited_uses.get("arcane_recovery"): return
    budget = (actor.level + 1) // 2
    selected = policy.arcane_recovery(actor, budget)
    if not isinstance(selected, dict) or any(type(k) is not int or not 1 <= k <= 5 or type(n) is not int or n < 0 or actor.spell_slots.get(k,0) + n > actor.max_spell_slots.get(k,0) for k,n in selected.items()) or sum(k*n for k,n in selected.items()) > budget:
        raise ValueError("illegal Arcane Recovery slot selection")
    if not any(selected.values()): return
    for k,n in selected.items(): actor.spell_slots[k] += n
    actor.limited_uses["arcane_recovery"] -= 1
    actor.spend("arcane_recovery")
    if log is not None: log.append({"event":"rest_feature", "actor":actor.id, "name":"Arcane Recovery", "slots":selected.copy()})


def memorize_spell(actor, policy, log=None):
    if not actor.features.get("memorize_spell"): return
    swap=policy.memorize_spell(actor)
    if swap is None: return
    if not isinstance(swap,(tuple,list)) or len(swap)!=2: raise ValueError("Memorize Spell requires an old/new pair")
    old,new=swap
    if old not in actor.prepared_spells or new not in actor.spellbook or new in actor.spells: raise ValueError("illegal Memorize Spell replacement")
    actor.prepared_spells[actor.prepared_spells.index(old)]=new
    actor.spells[actor.spells.index(old)]=new
    if log is not None: log.append({"event":"rest_feature","actor":actor.id,"name":"Memorize Spell","old":old,"new":new})
