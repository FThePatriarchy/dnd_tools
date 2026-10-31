"""Small class hooks at existing roll, hit, save and rest boundaries."""
from . import dice
from .state import Effect, SpellInstance, compare_deadline
from .sheets import effect_block
from copy import copy, deepcopy

SKILLS = {"acrobatics", "animal handling", "arcana", "athletics", "deception", "history", "insight", "intimidation", "investigation", "medicine", "nature", "perception", "performance", "persuasion", "religion", "sleight of hand", "stealth", "survival", "thieves' tools", "poisoner's kit", "disguise kit"}


class ClassMechanics:
    def class_bonus_available(self, actor):
        return self.current is actor and actor.alive and not actor.has_condition("incapacitated") and actor.bonus_action>0 and not self.turn_rules(actor).get("no_bonus_action")

    def wild_shape(self, actor, form_name):
        from fractions import Fraction
        from .loader import ROOT, load_sheet
        if not actor.features.get("wild_shape") or not actor.limited_uses.get("wild_shape") or not self.class_bonus_available(actor) or actor.has_status("wild_shape") or actor.transform_snapshot is not None: return False
        # shortcut: known forms use existing Beast sheets; expand when more Beasts are imported.
        if form_name not in {"wolf","dire_wolf","brown_bear","giant_spider"}: return False
        form=load_sheet(ROOT/"monsters"/(form_name+".yaml"))
        cap=actor.level//3 if actor.features.get("circle_forms") else .25 if actor.level<4 else .5
        if form["creature_type"]!="beast" or Fraction(str(form["cr"]))>cap or form.get("movement_modes",{}).get("fly",0) and actor.level<8: return False
        fields=("abilities","ac","attacks","multiattack","routines","actions","features","speed","movement_modes","size","save_bonuses","resistances","immunities","vulnerabilities","condition_immunities","creature_type","position")
        snapshot={k:deepcopy(getattr(actor,k)) for k in fields}
        for key in fields:
            if key in form: setattr(actor,key,deepcopy(form[key]))
        actor.abilities.update({a:snapshot["abilities"][a] for a in ("int","wis","cha")})
        actor.features={**snapshot["features"],**form.get("features",{})}
        actor.routines=deepcopy(form.get("routines",[]))
        actor.multiattack=deepcopy(form.get("multiattack",[]))
        for ability in ("str","dex","con","int","wis","cha"):
            own=actor.mod(ability)+(actor.proficiency_bonus if ability in actor.save_proficiencies else 0)
            actor.save_bonuses[ability]=max(own,form.get("save_bonuses",{}).get(ability,actor.mod(ability)))
        if actor.features.get("circle_forms"): actor.ac=max(actor.ac,13+actor.mod("wis"))
        actor.temp_hp=max(actor.temp_hp,actor.level*(3 if actor.features.get("circle_forms") else 1))
        actor.statuses["wild_shape"]={"snapshot":snapshot,"expires":self.time_rounds+600*(actor.level//2),"form":form_name}
        actor.position="front"
        self.spend_economy(actor,"bonus_action"); actor.limited_uses["wild_shape"]-=1; actor.spend("wild_shape")
        self.feature_log(actor,"Wild Shape",form=form_name)
        return True

    def end_wild_shape(self, actor):
        shaped=actor.statuses.pop("wild_shape",None)
        if shaped:
            for k,v in shaped["snapshot"].items(): setattr(actor,k,v)
            self.feature_log(actor,"End Wild Shape")

    def innate_sorcery(self, actor):
        if not actor.features.get("innate_sorcery") or not actor.limited_uses.get("innate_sorcery") or actor.has_status("innate_sorcery") or not self.class_bonus_available(actor): return False
        self.spend_economy(actor,"bonus_action"); actor.limited_uses["innate_sorcery"]-=1; actor.spend("innate_sorcery")
        actor.statuses["innate_sorcery"]={"expires":self.time_rounds+10}
        actor.spell_dc+=1
        self.feature_log(actor,"Innate Sorcery")
        return True

    def font_of_magic(self, actor, slot, *, create=False):
        if not actor.features.get("font_of_magic") or self.current is not actor or not actor.alive or actor.has_condition("incapacitated") or type(slot) is not int or not 1<=slot<=5: return False
        points=actor.limited_uses["sorcery_points"]
        if create:
            cost=(2,3,5,6,7)[slot-1]
            if actor.level<max(2,2*slot-1) or points<cost or not self.class_bonus_available(actor): return False
            self.spend_economy(actor,"bonus_action"); actor.limited_uses["sorcery_points"]-=cost; actor.spend("sorcery_points",cost)
            actor.spell_slots[slot]=actor.spell_slots.get(slot,0)+1
        else:
            if not actor.spell_slots.get(slot) or points>=actor.max_limited_uses["sorcery_points"]: return False
            actor.spell_slots[slot]-=1; actor.spend(f"slot_{slot}")
            actor.limited_uses["sorcery_points"]=min(actor.max_limited_uses["sorcery_points"],points+slot)
        self.feature_log(actor,"Font of Magic",slot=slot,create=create)
        return True

    def metamagic_cast(self, actor, name, option, **kwargs):
        costs={"quickened_spell":2,"heightened_spell":2,"careful_spell":1,"extended_spell":1}
        if option not in costs or not actor.features.get(option) or actor.limited_uses.get("sorcery_points",0)<costs[option] or name not in self.spells: return None
        spec=self.spells[name]
        if option in {"heightened_spell","careful_spell"} and not any(b["save"] for b in spec["effects"]): return None
        if option=="extended_spell" and spec["duration"]["type"] not in {"minutes","hours","days"}: return None
        if option=="quickened_spell" and (spec["casting_time"]!="action" or actor.statuses.get("leveled_spell_turn")==self.turn_index): return None
        old_costs=actor.spell_costs
        if option=="quickened_spell": actor.spell_costs={**old_costs,name:"bonus_action"}
        actor.statuses["casting_metamagic"]={"option":option,"cost":costs[option],"spell":name,"target":next((t.id for t in kwargs.get("targets") or [] if t.team!=actor.team),None)}
        try: return self.cast(actor,name,**kwargs)
        finally:
            actor.spell_costs=old_costs
            actor.statuses.pop("casting_metamagic",None)

    def apply_metamagic(self, instance):
        meta=instance.caster.statuses.get("casting_metamagic",{})
        if meta.get("spell")!=instance.spec["name"]: return
        option=meta.get("option")
        if not option: return
        instance.choices["_metamagic"]=option
        if option=="heightened_spell":
            enemies=self.enemies(instance.caster)
            if enemies: instance.choices["_heightened_target"]=instance.caster.statuses["casting_metamagic"].get("target") or min(enemies,key=lambda t:(t.hp,t.id)).id
        if option=="extended_spell":
            duration=instance.spec["duration"]
            minutes=duration["n"]*{"minutes":1,"hours":60,"days":1440}[duration["type"]]
            instance.spec["duration"]={"type":"minutes","n":min(1440,minutes*2)}

    def spell_save(self, instance, target, ability, dc, *args, **kwargs):
        penalty=None
        if target.id==instance.choices.get("_heightened_target"):
            penalty=Effect("disadvantage",{"on":"saves","scope":ability,"against":None},instance.id,"heightened")
            target.effects.append(penalty)
        try: return self.saving_throw(target,ability,dc,*args,**kwargs)
        finally:
            if penalty in target.effects: target.effects.remove(penalty)

    def pole_strike(self, actor, attack):
        """Polearm Master: after the Attack action with a qualifying weapon, a d4 Bludgeoning butt-end attack as a Bonus Action."""
        if not actor.features.get("polearm_master") or self.current is not actor or actor.bonus_action < 1 or not actor.alive or actor.has_condition("incapacitated"): return False
        enemies = self.reachable(actor, self.enemies(actor), attack)
        if not enemies or self.turn_rules(actor).get("no_bonus_action"): return False
        strike = {**deepcopy(attack), "name": attack["name"]}
        strike["effects"][0]["damage"].update(dice="1d4", type="bludgeoning")
        self.spend_economy(actor, "bonus_action")
        self.feature_log(actor, "Pole Strike")
        actor.statuses["pole_strike"] = True
        try: return self.weapon_attack(actor, self.policy_for(actor).weapon_target(self, actor, enemies), strike)
        finally: actor.statuses.pop("pole_strike", None)

    def martial_die(self, actor):
        return "1d10" if actor.level>=11 else "1d8" if actor.level>=5 else "1d6"

    def free_mark(self, actor, name, slot=None):
        return name=="Hunter's Mark" and actor.features.get("favored_enemy") and actor.limited_uses.get("favored_enemy",0)>0 and slot in {None,1}

    def monk_initiative(self, actor):
        if actor.alive and actor.features.get("uncanny_metabolism") and actor.limited_uses.get("uncanny_metabolism") and (actor.limited_uses.get("focus",0)<actor.max_limited_uses["focus"] or actor.hp<actor.max_hp):
            actor.limited_uses["uncanny_metabolism"]-=1; actor.spend("uncanny_metabolism")
            actor.limited_uses["focus"]=actor.max_limited_uses["focus"]
            self.heal(actor,dice.roll(self.rng,self.martial_die(actor))+actor.level)
            self.feature_log(actor,"Uncanny Metabolism")

    def spend_focus(self, actor):
        actor.limited_uses["focus"]-=1; actor.spend("focus")

    def patient_defense(self, actor, dodge=False):
        if self.current is not actor or not actor.features.get("monks_focus") or not actor.alive or actor.has_condition("incapacitated") or not actor.bonus_action or self.turn_rules(actor).get("no_bonus_action") or dodge and not actor.limited_uses.get("focus"): return False
        self.spend_economy(actor,"bonus_action")
        actor.effects.append(Effect("status",{"id":"disengaged","data":{}},0,"patient_defense",("end_of_turn",actor.id,actor.turns_taken)))
        if dodge:
            self.spend_focus(actor)
            actor.effects.append(Effect("status",{"id":"monk_dodge","data":{}},0,"patient_defense",("start_of_turn",actor.id,actor.turns_taken+1)))
        self.feature_log(actor,"Patient Defense",dodge=dodge)
        return True

    def wholeness(self, actor):
        if self.current is not actor or not actor.features.get("wholeness_of_body") or not actor.alive or actor.has_condition("incapacitated") or not actor.bonus_action or self.turn_rules(actor).get("no_bonus_action") or not actor.limited_uses.get("wholeness_of_body") or actor.hp>=actor.max_hp: return False
        self.spend_economy(actor,"bonus_action")
        actor.limited_uses["wholeness_of_body"]-=1; actor.spend("wholeness_of_body")
        self.heal(actor,max(1,dice.roll(self.rng,self.martial_die(actor))+actor.mod("wis")))
        self.feature_log(actor,"Wholeness of Body")
        return True

    def monk_bonus(self, actor, flurry=False):
        if self.current is not actor or not actor.features.get("martial_arts") or not actor.alive or actor.has_condition("incapacitated") or not actor.bonus_action or self.turn_rules(actor).get("no_bonus_action") or flurry and not actor.limited_uses.get("focus"): return False
        attack=next((a for a in actor.attacks if a["name"]=="Unarmed Strike"),None)
        if attack is None or not self.reachable(actor,self.enemies(actor),attack): return False
        self.spend_economy(actor,"bonus_action")
        if flurry: self.spend_focus(actor)
        self.feature_log(actor,"Flurry of Blows" if flurry else "Martial Arts")
        actor.statuses["flurry"]=flurry
        try:
            for _ in range((3 if actor.features.get("heightened_focus") else 2) if flurry else 1):
                enemies=self.reachable(actor,self.enemies(actor),attack)
                if not enemies or actor.has_condition("incapacitated"): break
                self.weapon_attack(actor,self.policy_for(actor).weapon_target(self,actor,enemies),attack)
        finally: actor.statuses.pop("flurry",None)
        return True

    def monk_hit(self, actor, target, attack):
        if not actor.features.get("martial_arts") or not target.alive or attack["name"] not in {"Unarmed Strike","Quarterstaff","Mace"}: return
        dc=8+actor.mod("wis")+actor.proficiency_bonus
        until=("start_of_turn",actor.id,actor.turns_taken+1)
        if actor.features.get("stunning_strike") and actor.statuses.get("stun_turn")!=self.turn_index and self.policy_for(actor).stunning_strike(self,actor,target):
            actor.statuses["stun_turn"]=self.turn_index
            self.spend_focus(actor)
            success=self.saving_throw(target,"con",dc,conditions=["stunned"])
            if success:
                target.effects.append(Effect("modify",{"stat":"speed","op":"mul","value":0.5,"scope":"all"},0,"stunning_strike",until))
                target.effects.append(Effect("advantage",{"on":"attack_rolls","scope":"all","recipient":"any_attacker"},0,"stunning_strike",until,uses=1))
            elif not target.immune_to("stunned"):
                target.effects.append(Effect("apply_condition",{"condition":"stunned"},0,"stunning_strike",until))
                if target.concentration is not None: self.end_spell(target.concentration)
            self.feature_log(actor,"Stunning Strike",target=target.id,success=success)
        if actor.statuses.get("flurry") and actor.features.get("open_hand_technique"):
            # Addle only stops Opportunity Attacks, which need a grid; it is a no-op unless chosen.
            addle=bool(actor.features.get("open_hand_addle"))
            if addle:
                target.effects.append(Effect("status",{"id":"no_opportunity_attacks","data":{}},0,"open_hand",("start_of_turn",target.id,target.turns_taken+1)))
            elif not target.has_condition("prone") and not target.immune_to("prone") and not self.saving_throw(target,"dex",dc,conditions=["prone"]): target.conditions.add("prone")
            self.feature_log(actor,"Open Hand Technique",option="Addle" if addle else "Topple",target=target.id)

    def deflect_reduce(self, typed, attack_context):
        if attack_context is None: return
        attacker,target,attack=attack_context
        if not target.features.get("deflect_attacks") or not target.alive or not target.reaction or target.has_condition("incapacitated") or self.turn_rules(target).get("no_reactions"): return
        entries=[(k,n) for k,n in typed.items() if k[0] is target]
        if not any(k[1] in {"bludgeoning","piercing","slashing"} and n>0 for k,n in entries): return
        target.reaction-=1
        reduction=dice.roll(self.rng,"1d10")+target.mod("dex")+target.level
        for k,n in entries:
            removed=min(n,max(0,reduction)); typed[k]-=removed; reduction-=removed
        self.feature_log(target,"Deflect Attacks")
        # shortcut: redirection needs reach/cover adjudication; reduction alone is modeled.

    def hunter_attack(self, actor, target, attack):
        if not actor.features.get("horde_breaker") or self.current is not actor or actor.statuses.get("horde_turn")==self.turn_index: return
        attacked=actor.statuses.setdefault("hunter_targets",set())
        attacked.add(target.id)
        others=[e for e in self.reachable(actor,self.enemies(actor),attack) if e.id not in attacked]
        if not others: return
        actor.statuses["horde_turn"]=self.turn_index
        self.feature_log(actor,"Horde Breaker")
        # shortcut: another reachable enemy is assumed within five feet of the first.
        self.weapon_attack(actor,self.policy_for(actor).weapon_target(self,actor,others),attack)

    def monk_end_turn(self, actor):
        if not actor.features.get("self_restoration"): return
        condition=next((c for c in ("charmed","frightened","poisoned") if actor.has_condition(c)),None)
        if condition and self.can_end_condition(actor,condition):
            actor.conditions.discard(condition)
            actor.effects=[e for e in actor.effects if not (e.kind=="apply_condition" and e.data["condition"]==condition)]
            self.refresh_spell_effects()
            self.feature_log(actor,"Self-Restoration",condition=condition)

    def bardic_die(self, actor):
        return 10 if actor.level>=10 else 8 if actor.level>=5 else 6

    def inspire(self, actor, target):
        if not actor.features.get("bardic_inspiration") or not actor.alive or actor.has_condition("incapacitated") or not actor.bonus_action or self.turn_rules(actor).get("no_bonus_action") or not actor.limited_uses.get("bardic_inspiration"): return False
        if target is actor or target.team!=actor.team or not target.alive or self.isolation(target)!=self.isolation(actor): return False
        if not actor.visible_to(target) and target.has_condition("deafened"): return False
        if target.statuses.get("bardic_inspiration",{}).get("expires",0)>self.time_rounds: return False
        self.spend_economy(actor,"bonus_action")
        actor.limited_uses["bardic_inspiration"]-=1; actor.spend("bardic_inspiration")
        target.statuses["bardic_inspiration"]={"die":self.bardic_die(actor),"expires":self.time_rounds+600}
        self.feature_log(actor,"Bardic Inspiration",target=target.id)
        return True

    def failed_test_bonus(self, actor, total, dc, *, luck=True):
        inspiration=actor.statuses.get("bardic_inspiration",{})
        if inspiration.get("expires",0)<=self.time_rounds:
            actor.statuses.pop("bardic_inspiration",None); inspiration={}
        if 0<dc-total<=inspiration.get("die",0):
            total+=self.rng.randint(1,inspiration["die"])
            actor.statuses.pop("bardic_inspiration",None)
            self.feature_log(actor,"Bardic Inspiration used",total=total,dc=dc)
        if luck and 0<dc-total<=10 and actor.limited_uses.get("dark_ones_own_luck"):
            actor.limited_uses["dark_ones_own_luck"]-=1; actor.spend("dark_ones_own_luck")
            total+=dice.roll(self.rng,"1d10")
            self.feature_log(actor,"Dark One's Own Luck",total=total,dc=dc)
        return total

    def cutting_words(self, enemy, total, dc=None, defender=None):
        for bard in self.combatants:
            if not bard.features.get("cutting_words") or bard.team==enemy.team or not bard.alive or bard.has_condition("incapacitated") or not bard.reaction or self.turn_rules(bard).get("no_reactions") or not bard.limited_uses.get("bardic_inspiration"): continue
            if not enemy.visible_to(bard) or self.isolation(enemy)!=self.isolation(bard) or defender is not None and defender.team!=bard.team: continue
            if dc is not None and not 0<=total-dc<self.bardic_die(bard) or dc is None and total<=0: continue
            if defender is not None and defender.hp>defender.max_hp/2 and bard.limited_uses["bardic_inspiration"]<=1 and any(c.team==bard.team and not c.dead and c.hp<=c.max_hp/2 for c in self.combatants): continue
            bard.reaction-=1; bard.limited_uses["bardic_inspiration"]-=1; bard.spend("bardic_inspiration")
            total-=self.rng.randint(1,self.bardic_die(bard))
            if dc is None: total=max(0,total)
            self.feature_log(bard,"Cutting Words",target=enemy.id,total=total)
            if dc is None or total<dc: break
        return total

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
        fail = min(.95, max(.05, (9 - bonus) / 20)) * (.5 if (actor.features.get("war_caster") or actor.features.get("eldritch_mind")) else 1)
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
        if actor.features.get("agonizing_blast") and spec["name"]=="Eldritch Blast":
            for b in spec["effects"]:
                for p in b["on_hit"]:
                    if "damage" in p: p["damage"]["bonus"]+=actor.mod("cha")
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

    def class_damage_bonus(self, instance, target, amount, block, dtype=None):
        caster, spec = instance.caster, instance.spec
        if "level" not in spec: return amount
        if caster.features.get("elemental_affinity") and dtype=="fire" and "_affinity_roll" not in instance.choices:
            instance.choices["_affinity_roll"]=True
            amount+=caster.mod("cha")
            self.feature_log(caster,"Elemental Affinity")
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
        if actor.features.get("colossus_slayer") and target.hp<target.max_hp and actor.statuses.get("colossus_turn")!=self.turn_index:
            actor.statuses["colossus_turn"]=self.turn_index
            self.damage(target,dice.roll(self.rng,"1d8",critical),attack["effects"][0]["damage"]["type"],actor)
            self.feature_log(actor,"Colossus Slayer")
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
        dodge=actor.features.get("monks_focus",False) and actor.has_status("monk_dodge") and not actor.has_condition("incapacitated") and self.modifier(actor,"speed",actor.speed)>0
        adv |= on=="saves" and scope=="dex" and dodge
        dis=False
        if on=="attack_rolls" and against is not None:
            dis |= against.features.get("monks_focus",False) and against.has_status("monk_dodge") and not against.has_condition("incapacitated") and self.modifier(against,"speed",against.speed)>0 and actor.visible_to(against)
            dis |= against.features.get("multiattack_defense",False) and against.statuses.get("multiattack_defense",{}).get(actor.id)==self.turn_index
        return adv, dis

    def heroic_reroll(self, actor, natural, succeeds, kind="save"):
        if not succeeds(natural) and actor.statuses.pop("heroic_inspiration", None) is not None:
            self.feature_log(actor, "Heroic Inspiration")
            natural = dice.reroll(self.rng, natural, self.policy_for(actor).reroll_die(self, actor, natural))
        if not succeeds(natural) and actor.features.get("lucky") and actor.limited_uses.get("luck") and succeeds(20) and self.policy_for(actor).use_luck(self, actor, kind):
            # Lucky: Advantage on the roll, taken once the roll is known, so a second d20 keeps the higher.
            actor.limited_uses["luck"] -= 1; actor.spend("luck")
            natural = max(natural, dice.d20(self.rng))
            self.feature_log(actor, "Lucky", roll=kind)
        return natural

    def class_failed_save(self, actor, ability, dc, bonus, natural, success):
        if not success and not (ability=="death" and natural==1):
            total=self.failed_test_bonus(actor,natural+bonus,dc)
            if total!=natural+bonus: return total>=dc,total,natural
        if not success and actor.limited_uses.get("indomitable", 0) and self.policy_for(actor).indomitable(self, actor, ability, dc):
            actor.limited_uses["indomitable"] -= 1
            actor.spend("indomitable")
            natural = dice.reroll(self.rng, natural, self.policy_for(actor).reroll_die(self, actor, natural))
            total = natural + bonus + actor.level
            self.feature_log(actor, "Indomitable", total=total, dc=dc)
            return total >= dc, total, natural
        return success, natural + bonus, natural

    def class_expire(self, actor):
        if actor.has_status("innate_sorcery") and compare_deadline(self.time_rounds,actor.statuses["innate_sorcery"]["expires"])>=0:
            actor.statuses.pop("innate_sorcery"); actor.spell_dc-=1
        if actor.has_status("wild_shape") and (not actor.alive or actor.has_condition("incapacitated") or compare_deadline(self.time_rounds,actor.statuses["wild_shape"]["expires"])>=0): self.end_wild_shape(actor)
        if "rage" in actor.statuses and (not actor.raging or compare_deadline(self.time_rounds,actor.statuses["rage"]["expires"]) >= 0): actor.statuses.pop("rage",None)
        if "sacred_weapon" in actor.statuses and compare_deadline(self.time_rounds,actor.statuses["sacred_weapon"]["expires"]) >= 0: actor.statuses.pop("sacred_weapon",None)

    def class_start_turn(self, actor):
        if actor.features.get("horde_breaker"): actor.statuses["hunter_targets"]=set()
        if actor.features.get("lay_on_hands"): actor.statuses["weapon_hits"] = 0
        actor.statuses.pop("reckless",None)
        actor.statuses.pop("reckless_decided",None)
        self.class_expire(actor)
        if actor.features.get("heroic_warrior") and actor.alive:
            actor.statuses.setdefault("heroic_inspiration", {})
            self.feature_log(actor, "Heroic Warrior")

    def class_weapon(self, actor, attack, target):
        if actor.has_status("wild_shape") and actor.features.get("improved_circle_forms"):
            attack=deepcopy(attack)
            for p in attack["effects"]:
                if "damage" in p: p["damage"]["type"]="radiant"
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
        if total>=dc: total=self.cutting_words(actor,total,dc)
        total=self.failed_test_bonus(actor,total,dc)
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
