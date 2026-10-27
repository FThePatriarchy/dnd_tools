"""Small class hooks at existing roll, hit, save and rest boundaries."""
from . import dice
from .state import Effect, SpellInstance, compare_deadline
from .sheets import effect_block
from copy import copy, deepcopy

SKILLS = {"acrobatics", "animal handling", "arcana", "athletics", "deception", "history", "insight", "intimidation", "investigation", "medicine", "nature", "perception", "performance", "persuasion", "religion", "sleight of hand", "stealth", "survival", "thieves' tools", "poisoner's kit", "disguise kit"}


class ClassMechanics:
    def expected_buff_value(self, actor, spec, *, slot=None):
        """In-combat damage-equivalent gain; Bless saves/frightened immunity omitted."""
        enemies = self.enemies(actor)
        if not enemies: return 0
        duration = spec.get("duration", {"type": "instant"})
        cap = duration.get("n", 1) * {"rounds": 1, "minutes": 10, "hours": 600, "days": 14400}.get(duration["type"], 0)
        horizon = min(self.expected_remaining_rounds(actor), cap)
        if spec.get("concentration"): horizon = self.concentration_horizon(actor, enemies, horizon)
        slot = spec["level"] if slot is None else slot
        probe = SpellInstance(0, spec, actor, slot, self.turn_index, self.time_rounds)
        selected = {}
        total = 0
        for block in spec["effects"]:
            t = block["target"]
            if t["select"] == "ref": targets = selected.get(t["ref"], [])
            else:
                legal = [c for c in self.eligible(probe, block) if c.team == actor.team and c.alive]
                if t["select"] == "self": legal = [actor] if actor in legal else []
                n = len(legal) if t.get("n") == "all" else t.get("n", 1)
                targets = self.policy_for(actor).targets(self, probe, block, legal, n)[:n]
            selected[block["id"]] = targets
            for ally in targets:
                if any(i.active and i.spec["name"] == spec["name"] and any(e.source == i.id for e in ally.effects) for i in self.instances.values()): continue
                incoming = max((self.at_will_damage_rate(e, ally) for e in enemies), default=6)
                for p in block["apply"]:
                    v = p.get("modify", {})
                    if v.get("op") == "add" and v.get("stat") == "attack_roll":
                        bonus = dice.mean(v["value"]) if isinstance(v["value"], str) else v["value"]
                        total += self.buff_attack_gain(ally, enemies[0], bonus) * horizon
                    elif "weapon_enchantment" in p:
                        v = dict(p["weapon_enchantment"])
                        for tier in v.get("tiers", []):
                            if slot >= tier["slot_min"]: v.update(tier)
                        total += self.buff_attack_gain(ally, enemies[0], v.get("attack_bonus", 0), v.get("damage_bonus", 0), weapon_only=True) * horizon
                    elif v.get("op") == "add" and v.get("stat") == "ac":
                        total += v["value"] * .05 * incoming / .6 * horizon
                    elif "temp_hp" in p:
                        v = p["temp_hp"]
                        amount = dice.mean(v["dice"]) if "dice" in v else actor.spell_mod if v.get("amount") == "spell_mod" else v.get("amount", 0)
                        amount += actor.spell_mod if v.get("bonus") == "spell_mod" else v.get("bonus", 0)
                        if "start_of_turn" in block["event"]: total += min(incoming, max(0, amount)) * horizon
                        else: total += min(incoming * horizon, max(0, amount - ally.temp_hp))
                    elif "max_hp" in p:
                        total += min(incoming * horizon, p["max_hp"]["amount"])
        return total

    def concentration_horizon(self, actor, enemies, horizon):
        """Expected rounds a concentration spell lasts: each hit risks a DC 10 Constitution save."""
        allies = [c for c in self.combatants if c.team == actor.team and c.alive]
        hits = sum(self.expected_attack_hits(e, actor) for e in enemies) / max(1, len(allies))
        bonus = actor.save_bonuses.get("con", actor.mod("con") + (actor.proficiency_bonus if "con" in actor.save_proficiencies else 0))
        fail = min(.95, max(.05, (9 - bonus) / 20)) * (.5 if actor.features.get("war_caster") else 1)
        keep = (1 - fail) ** hits
        return horizon if keep >= 1 else (1 - keep ** horizon) / (1 - keep)

    def buff_attack_gain(self, ally, target, attack_bonus, damage_bonus=0, *, weapon_only=False):
        weapon = self.expected_weapon_damage(ally, target)
        if not weapon_only:
            cantrips = [self.cantrip_spec(ally, n) for n in ally.spells if self.spells[n]["level"] == 0]
            best = max(cantrips, key=lambda s: self.expected_spell_damage(ally, s, target, horizon=1), default=None)
            if best and self.expected_spell_damage(ally, best, target, horizon=1) > weapon:
                if not any(b["attack"] for b in best["effects"]): return 0
                boosted = copy(ally)
                hit = min(.95, self.hit_probability(ally, target, ally.spell_attack_bonus) + attack_bonus * .05)
                boosted.spell_attack_bonus = self.armor_class(target) - 21 + 20 * hit
                return self.expected_spell_damage(boosted, best, target, horizon=1) - self.expected_spell_damage(ally, best, target, horizon=1)
        return self.expected_weapon_damage(ally, target, attack_bonus=attack_bonus, damage_bonus=damage_bonus) - weapon

    def class_auras(self):
        sources = [c for c in self.combatants if c.features.get("aura_of_protection")]
        if not sources: return
        for c in self.combatants: c.aura_sources = []
        for source in sources:
            allies = [c for c in self.combatants if c is not source and c.__dict__["team"] == source.__dict__["team"] and not c.dead]
            count = self.area("emanation", 10, len(allies))
            covered = allies[:count] if isinstance(count, int) else [allies[i] for i in count]
            for c in [source, *covered]: c.aura_sources.append(source)

    def aura_save_bonus(self, actor):
        self.class_auras()
        return max((max(1,c.mod("cha")) for c in actor.aura_sources if c.aura_active()), default=0)

    def rage(self, actor):
        if not actor.features.get("rage") or actor.raging or not actor.alive or actor.has_condition("incapacitated") or actor.bonus_action < 1 or self.turn_rules(actor).get("no_bonus_action") or not actor.limited_uses.get("rage"): return False
        self.spend_economy(actor,"bonus_action")
        actor.limited_uses["rage"] -= 1; actor.spend("rage")
        actor.statuses["rage"] = {"expires": self.time_rounds + 100}
        if actor.concentration is not None: self.end_spell(actor.concentration)
        if actor.features.get("mindless_rage"):
            actor.conditions.difference_update({"charmed", "frightened"})
            actor.effects = [e for e in actor.effects if not (e.kind == "apply_condition" and e.data["condition"] in {"charmed", "frightened"})]
        self.feature_log(actor,"Rage")
        return True

    def lay_on_hands(self, actor, target, amount=None):
        pool = actor.limited_uses.get("lay_on_hands",0)
        if not actor.features.get("lay_on_hands") or not actor.alive or actor.has_condition("incapacitated") or actor.bonus_action < 1 or self.turn_rules(actor).get("no_bonus_action") or target.dead or target not in self.combatants or not pool: return False
        amount = min(pool, target.max_hp-target.hp) if amount is None else amount
        if type(amount) is not int or not 0 < amount <= min(pool,target.max_hp-target.hp): return False
        self.spend_economy(actor,"bonus_action")
        actor.limited_uses["lay_on_hands"] -= amount; actor.spend("lay_on_hands",amount)
        self.heal(target,amount)
        self.feature_log(actor,"Lay on Hands",target=target.id,amount=amount)
        return True

    def paladin_smite(self, actor, target, critical, roll):
        if not actor.features.get("lay_on_hands") or "Divine Smite" not in actor.spells or not roll.get("melee") or self.current is not actor: return
        free = actor.limited_uses.get("paladins_smite",0) > 0
        policy = self.policy_for(actor)
        if not policy.smite(self,actor,target,critical,free): return
        if free: actor.spell_resources["Divine Smite"] = "paladins_smite"
        try:
            if self.can_cast(actor,"Divine Smite"):
                self.cast(actor,"Divine Smite",trigger={"attacker":actor,"defender":target,"attack":roll,"critical":critical})
        finally:
            if free: actor.spell_resources.pop("Divine Smite",None)

    def retaliation(self, actor, source, amount):
        if not amount or not source or not source.alive or not actor.alive or not actor.features.get("retaliation") or actor.has_condition("incapacitated") or not actor.reaction or self.turn_rules(actor).get("no_reactions"): return
        attacks = [a for a in actor.attacks if a["kind"] == "melee"]
        if not attacks or source not in self.reachable(actor,[source],attacks[0]) or not self.policy_for(actor).reaction(self,actor,{"name":"Retaliation"},{"attacker":source}): return
        actor.reaction -= 1
        self.feature_log(actor,"Retaliation",target=source.id)
        self.weapon_attack(actor,source,attacks[0])

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
        if actor.raging and attack.get("ability", "str") == "str":
            bonus = 2 if actor.level < 9 else 3
            dtype = attack["effects"][0]["damage"]["type"]
            self.damage(target,bonus,dtype,actor)
            self.feature_log(actor,"Rage Damage",amount=bonus)
            if actor.features.get("frenzy") and self.current is actor and actor.statuses.get("reckless") and actor.statuses.get("frenzy_turn") != self.turn_index:
                actor.statuses["frenzy_turn"] = self.turn_index
                self.damage(target,dice.roll(self.rng,f"{bonus}d6",critical),dtype,actor)
                self.feature_log(actor,"Frenzy",dice=f"{bonus}d6")
        if actor.statuses.pop("brutal_attack",False):
            self.damage(target,dice.roll(self.rng,"1d10",critical),attack["effects"][0]["damage"]["type"],actor)
            target.effects = [e for e in target.effects if e.block != "hamstring_blow"]
            target.effects.append(Effect("modify", {"stat":"speed","op":"sub","value":15,"scope":"all"},0,"hamstring_blow",("start_of_turn",actor.id,actor.turns_taken+1)))
            self.feature_log(actor,"Brutal Strike",option="Hamstring Blow")
        self.paladin_smite(actor,target,critical,roll)
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
        adv |= on in {"saves", "ability_checks"} and scope == "str" and actor.raging
        adv |= on == "saves" and scope == "dex" and actor.features.get("danger_sense",False) and not actor.has_condition("incapacitated")
        adv |= on == "attack_rolls" and scope == "str" and bool(actor.statuses.get("reckless"))
        adv |= on == "attack_rolls" and against is not None and bool(against.statuses.get("reckless"))
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

    def class_expire(self, actor):
        if "rage" in actor.statuses and (not actor.raging or compare_deadline(self.time_rounds,actor.statuses["rage"]["expires"]) >= 0): actor.statuses.pop("rage",None)
        if "sacred_weapon" in actor.statuses and compare_deadline(self.time_rounds,actor.statuses["sacred_weapon"]["expires"]) >= 0: actor.statuses.pop("sacred_weapon",None)

    def class_start_turn(self, actor):
        if actor.features.get("lay_on_hands"): actor.statuses["weapon_hits"] = 0
        actor.statuses.pop("reckless",None)
        actor.statuses.pop("reckless_decided",None)
        self.class_expire(actor)
        if actor.features.get("heroic_warrior") and actor.alive:
            actor.statuses.setdefault("heroic_inspiration", {})
            self.feature_log(actor, "Heroic Warrior")

    def class_weapon(self, actor, attack, target):
        if self.current is actor and actor.features.get("reckless_attack") and not actor.statuses.get("reckless_decided"):
            actor.statuses["reckless_decided"] = True
            if self.policy_for(actor).reckless_attack(self,actor,target):
                actor.statuses["reckless"] = True
                self.feature_log(actor,"Reckless Attack")
        sacred = actor.statuses.get("sacred_weapon",{})
        if sacred.get("weapon") == attack["name"] and sacred.get("expires",0) > self.time_rounds and not attack.get("_sacred_weapon"):
            attack = {**attack,"to_hit":attack["to_hit"]+max(1,actor.mod("cha")),"_sacred_weapon":True}
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
