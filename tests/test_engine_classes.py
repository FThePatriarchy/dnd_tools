"""Step 4: format, source, progression, builder and behavior gates."""
import pytest
from copy import deepcopy

from engine.classes import validate_class, load_class, substitute
from engine.loader import ValidationError, load_spells
from engine import Combat, Combatant
from engine import dice
from engine.builder import build as _build, load_build as _load_build, EQUIPMENT, WEAPONS


def build(*args, **kwargs):
    return _build(*args, background=False, **kwargs)


def load_build(*args, **kwargs):
    return _load_build(*args, background=False, **kwargs)
from engine.loader import ROOT, read_yaml, load_sheet


@pytest.fixture(scope="module")
def spells(): return load_spells()


def actor(name="fighter", level=5):
    # Scenario stats are assigned deliberately, but every grant crosses build().
    choices = {"ability_method": "assigned", "asis": {n: {"cha": 2} for n in load_class(name)["asi_levels"] if n <= level}}
    if name == "rogue": choices["cunning_strike"] = []
    if name == "cleric": choices["blessed_strikes"] = "divine_strike"
    sheet = build(name, level, abilities=dict(str=18,dex=18,con=14,int=18,wis=18,cha=10-2*len(choices["asis"])), choices=choices)
    sheet.update(max_hp=100, ac=16, spell_dc=15, spell_attack_bonus=7, spells=[], prepared_spells=[], spellbook=[])
    sheet["attacks"] = [{"name":"Rapier", "kind":"melee", "properties":["finesse"], "ability":"dex", "to_hit":7, "effects":[{"damage":{"dice":"1d8", "bonus":4, "type":"piercing"}}]}]
    return Combatant.from_sheet(sheet, name, "party")


def test_class_unknown_keys_rejected():
    with pytest.raises(ValidationError, match="unknown key"):
        validate_class({"typo": 1})


def test_fighter_2024_progression():
    c = load_class("fighter")
    assert c["asi_levels"] == [4, 6, 8]
    assert [x["resources"]["second_wind"]["max"] for x in c["levels"].values()] == [2,2,2,3,3,3,3,3,3,4]
    assert [x["weapon_masteries"] for x in c["levels"].values()] == [3,3,3,4,4,4,4,4,4,5]
    assert not any(f["name"] == "Studied Attacks" for f in c["features"])


def test_champion_critical_is_weapon_only_and_automatic_hit(spells, monkeypatch):
    f = actor(); t = Combatant("target", ac=99)
    combat = Combat([f,t], spells)
    monkeypatch.setattr(dice, "d20", lambda *a, **k: 19)
    critical = []
    assert combat.attack(f,t,0,lambda crit, roll: critical.append(crit),weapon=True)
    assert critical == [True]
    assert not combat.attack(f,t,0,lambda *a: None,weapon=False)


def test_fighter_actions_and_tactical_mind(spells, monkeypatch):
    f = actor(level=9); t = Combatant("target")
    combat = Combat([f,t], spells)
    combat.begin_turn(f); f.hp = 1
    monkeypatch.setattr(combat.rng, "randint", lambda a,b: 5)
    assert combat.use_action(f,"Second Wind",[f])
    assert f.hp == 15 and f.limited_uses["second_wind"] == 2
    assert combat.use_action(f,"Action Surge") and f.action == 2 and f.surge_actions == 1
    assert not combat.use_action(f,"Action Surge")
    monkeypatch.setattr(dice,"d20",lambda *a,**k: 1)
    assert combat.ability_check(f,"str",10)
    assert f.limited_uses["second_wind"] == 1
    assert not combat.ability_check(f,"str",30)
    assert f.limited_uses["second_wind"] == 1
    assert any(x.get("name") == "Tactical Mind" for x in combat.log)


def test_indomitable_reroll_plus_class_level(spells, monkeypatch):
    f = actor(level=9); combat = Combat([f],spells)
    rolls=iter([1,8]); monkeypatch.setattr(dice,"d20",lambda *a,**k: next(rolls))
    assert combat.saving_throw(f,"cha",17)
    assert f.limited_uses["indomitable"] == 0
    assert next(x for x in combat.log if x.get("name")=="Indomitable")["total"] == 17


def test_heroic_warrior_refresh_and_reroll(spells,monkeypatch):
    f=actor(level=10); combat=Combat([f],spells); combat.begin_turn(f)
    rolls=iter([1,20]); monkeypatch.setattr(dice,"d20",lambda *a,**k: next(rolls))
    assert combat.ability_check(f,"cha",20)
    assert "heroic_inspiration" not in f.statuses
    combat.begin_turn(f)
    assert "heroic_inspiration" in f.statuses


def test_sneak_attack_critical_once_per_global_turn_and_assassinate(spells,monkeypatch):
    r=actor("rogue"); t=Combatant("target",max_hp=500); combat=Combat([r,t],spells)
    combat.begin_turn(r)
    monkeypatch.setattr(dice,"d20",lambda *a,**k: 20)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b: 1)
    combat.weapon_attack(r,t,r.attacks[0])
    assert t.hp == 500 - (2+4+6+5)  # critical rapier, 3d6 doubled, flat Assassin 5
    combat.weapon_attack(r,t,r.attacks[0])
    assert t.hp == 500 - 17 - 6
    combat.begin_turn(t)
    combat.weapon_attack(r,t,r.attacks[0])  # no ally or first-round advantage after target turn
    assert t.hp == 500 - 17 - 6 - 6
    ally=actor(); ally.id="ally"; combat.combatants.append(ally)
    combat.begin_turn(ally)
    combat.weapon_attack(r,t,r.attacks[0])
    assert t.hp == 500 - 17 - 6 - 6 - 17


def test_sneak_attack_disadvantage_and_weapon_eligibility(spells):
    r=actor("rogue"); f=actor(); t=Combatant("target"); combat=Combat([r,f,t],spells)
    assert combat.sneak_eligible(r,t,r.attacks[0],{"advantage":False,"disadvantage":False})
    assert not combat.sneak_eligible(r,t,r.attacks[0],{"advantage":False,"disadvantage":True})
    assert not combat.sneak_eligible(r,t,{**r.attacks[0],"properties":[]},{"advantage":True,"disadvantage":False})
    f.conditions.add("incapacitated")
    assert not combat.sneak_eligible(r,t,r.attacks[0],{"advantage":False,"disadvantage":False})


@pytest.mark.parametrize("level, speed",[(3,0),(9,30)])
def test_steady_aim_and_roving_aim(spells,level,speed):
    r=actor("rogue",level); combat=Combat([r],spells); combat.begin_turn(r)
    r.statuses["moved_turn"]=combat.turn_index
    assert not combat.use_action(r,"Steady Aim")
    r.statuses.clear()
    assert combat.use_action(r,"Steady Aim")
    assert combat.modifier(r,"speed",30)==speed
    assert combat.roll_flags(r,"attack_rolls",consume=True)==(True,False)
    assert combat.roll_flags(r,"attack_rolls")== (False,False)
    combat.end_turn(r)
    assert combat.modifier(r,"speed",30)==30


def test_uncanny_dodge_complete_packet_and_visibility(spells,monkeypatch):
    r=actor("rogue"); e=Combatant("enemy"); combat=Combat([r,e],spells)
    monkeypatch.setattr(dice,"d20",lambda *a,**k: 20)
    def hit(*a):
        combat.damage(r,7,"slashing",e); combat.damage(r,5,"fire",e)
    combat.attack(e,r,50,hit)
    assert r.hp == 94 and r.reaction == 0
    combat.attack(e,r,50,hit)
    assert r.hp == 82
    r.reaction=1; e.visible=False
    combat.attack(e,r,50,hit)
    assert r.hp == 70 and r.reaction==1


@pytest.mark.parametrize("option,condition",[("poison","poisoned"),("trip","prone"),("withdraw",None)])
def test_cunning_strike_cost_and_effect(spells,monkeypatch,option,condition):
    r=actor("rogue"); r.cunning_strike=[option]; t=Combatant("target",max_hp=500)
    combat=Combat([r,t],spells); combat.begin_turn(r)
    monkeypatch.setattr(combat.policy,"cunning_strike",lambda *a: option)
    monkeypatch.setattr(dice,"d20",lambda *a,**k: 10)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b: 1)
    combat.weapon_attack(r,t,r.attacks[0])
    assert t.hp == 500-(1+4+2+5)
    if condition: assert t.has_condition(condition)
    else: assert r.has_status("withdraw")
    if option=="poison":
        assert next(e for e in t.effects if e.kind=="apply_condition").data["save_dc"]==15
        monkeypatch.setattr(dice,"d20",lambda *a,**k: 20)
        combat.end_turn(t); assert not t.has_condition("poisoned")


def test_cunning_strike_follows_hit_target_whose_control_ends_on_damage(spells,monkeypatch):
    # A dominated ally is a legal attack target; Sneak Attack damage lets it break
    # free (team reverts) before Cunning Strike resolves. The rider still applies
    # to the creature that was hit instead of failing target selection.
    from engine.state import Effect
    r=actor("rogue"); r.cunning_strike=["trip"]; t=Combatant("ally",team="party",max_hp=500)
    t.effects.append(Effect("control",{"control_team":"enemy"},0,"control"))
    combat=Combat([r,t],spells); combat.begin_turn(r)
    assert t.team=="enemy" and t in combat.enemies(r)
    monkeypatch.setattr(combat.policy,"cunning_strike",lambda *a: "trip")
    monkeypatch.setattr(dice,"d20",lambda *a,**k: 10)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b: 1)
    damage=combat.damage
    def damage_then_break_free(target,*a,**k):
        result=damage(target,*a,**k)
        if target is t: t.effects=[e for e in t.effects if e.kind!="control"]
        return result
    monkeypatch.setattr(combat,"damage",damage_then_break_free)
    combat.weapon_attack(r,t,r.attacks[0])
    assert t.team=="party" and t.has_condition("prone")


def test_expertise_reliable_talent(spells,monkeypatch):
    r=actor("rogue",7); r.skill_proficiencies=["stealth"]; r.expertise=["stealth"]
    combat=Combat([r],spells); monkeypatch.setattr(dice,"d20",lambda *a,**k: 1)
    assert combat.ability_check(r,"dex",20,skill="stealth") # 10 + 4 + 6
    assert not combat.ability_check(r,"dex",21,skill="stealth")
    assert not combat.ability_check(r,"dex",10,skill="acrobatics")


@pytest.mark.parametrize("name,roll,damage",[("Ray of Frost",1,2),("Toll the Dead",20,2)])
def test_evoker_potent_cantrip_no_rider(spells,monkeypatch,name,roll,damage):
    w=actor("wizard",3); w.spells=[name]; t=Combatant("target")
    combat=Combat([w,t],spells); combat.begin_turn(w)
    monkeypatch.setattr(dice,"d20",lambda *a,**k: roll)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b: 5)
    combat.cast(w,name,targets=[t])
    assert t.hp==100-damage and not t.effects


def test_sculpt_spells_spillover_not_caster_and_limit(spells,monkeypatch):
    w=actor("wizard",7); w.spells=["Fireball"]
    allies=[Combatant(f"ally{i}",team="party",max_hp=500) for i in range(6)]
    t=Combatant("enemy",max_hp=500)
    combat=Combat([w,*allies,t],spells,area=lambda shape,size,n:n); combat.begin_turn(w)
    monkeypatch.setattr(dice,"d20",lambda *a,**k: 1)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b: 1)
    combat.cast(w,"Fireball",slot=3)
    assert [a.hp for a in allies] == [500]*4+[492]*2
    assert w.hp==92 and t.hp==492
    assert sum(x.get("name")=="Sculpt Spells" for x in combat.log)==4


def test_empowered_evocation_one_damage_roll_and_not_other_schools(spells,monkeypatch):
    w=actor("wizard",10); w.spells=["Scorching Ray","Toll the Dead"]; t=Combatant("target",max_hp=500)
    combat=Combat([w,t],spells); combat.begin_turn(w)
    monkeypatch.setattr(dice,"d20",lambda *a,**k: 10)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b: 1)
    combat.cast(w,"Scorching Ray",targets=[t,t,t],slot=2)
    assert t.hp==490 # 3 * 2d6 plus one +4
    assert sum(x.get("name")=="Empowered Evocation" for x in combat.log)==1
    combat.begin_turn(w); combat.cast(w,"Toll the Dead",targets=[t])
    assert t.hp==488


def test_arcane_recovery_short_rest_once_and_long_reset(spells):
    import random
    from engine.day import take_rest
    w=actor("wizard",7); w.spell_slots={1:0,2:0,3:0,4:0}; trace=[]
    take_rest([w],"short",random.Random(1),log=trace)
    assert w.spell_slots=={1:0,2:0,3:0,4:1}
    assert w.limited_uses["arcane_recovery"]==0
    assert trace[0]["name"]=="Arcane Recovery"
    take_rest([w],"short",random.Random(1),log=trace)
    assert len(trace)==1
    take_rest([w],"long",random.Random(1),log=trace)
    assert w.spell_slots==w.max_spell_slots and w.limited_uses["arcane_recovery"]==1


@pytest.mark.parametrize("roll,amount",[(1,4),(20,0)])
def test_rogue_evasion_exact(spells,monkeypatch,roll,amount):
    r=actor("rogue",7); w=actor("wizard",5); w.team="enemy"; w.spells=["Fireball"]
    combat=Combat([r,w],spells); combat.begin_turn(w)
    monkeypatch.setattr(dice,"d20",lambda *a,**k: roll)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b: 1)
    combat.cast(w,"Fireball")
    assert r.hp==100-amount


def test_cleric_channel_uses_spark_and_shared_resource(spells,monkeypatch):
    c=actor("cleric",7); t=Combatant("target"); combat=Combat([c,t],spells)
    assert c.limited_uses["channel_divinity"]==3
    combat.begin_turn(c)
    monkeypatch.setattr(dice,"d20",lambda *a,**k: 20)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b: 1)
    combat.use_action(c,"Divine Spark (Radiant)",[t])
    assert t.hp==97  # (2d8 + 4) / 2
    combat.begin_turn(c); t.hp=1
    combat.use_action(c,"Divine Spark (Heal)",[t])
    assert t.hp==7 and c.limited_uses["channel_divinity"]==1
    combat.begin_turn(c)
    with pytest.raises(ValueError,match="illegal target"):
        combat.use_action(c,"Divine Spark (Heal)",[c])


def test_preserve_life_finite_pool_half_cap_and_zero_hp(spells):
    c=actor("cleric",5); a=Combatant("a",team="party",max_hp=40,hp=0); b=Combatant("b",team="party",max_hp=40,hp=1)
    combat=Combat([c,a,b],spells); combat.begin_turn(c)
    assert combat.use_action(c,"Preserve Life",[a,b])
    assert (a.hp,b.hp)==(13,13) and c.hp==100
    assert c.limited_uses["channel_divinity"]==1
    assert not a.has_condition("unconscious")


def test_turn_undead_sear_does_not_end_turn_but_later_damage_does(spells,monkeypatch):
    c=actor("cleric",5); u=Combatant("u",creature_type="undead"); beast=Combatant("b",creature_type="beast")
    combat=Combat([c,u,beast],spells); combat.begin_turn(c)
    monkeypatch.setattr(dice,"d20",lambda *a,**k: 1)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b: 2)
    combat.use_action(c,"Turn Undead")
    assert u.hp==92 and u.has_condition("incapacitated") and u.has_condition("frightened")
    assert beast.hp==100 and not beast.effects
    combat.damage(u,1,"fire",beast)
    assert not u.has_condition("incapacitated") and not u.has_condition("frightened")


def test_disciple_and_blessed_healer_actual_slot_level_not_channel(spells,monkeypatch):
    c=actor("cleric",7); c.hp=30; c.spells=["Cure Wounds"]; a=Combatant("a",team="party",hp=1)
    combat=Combat([c,a],spells); combat.begin_turn(c)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b: 1)
    combat.cast(c,"Cure Wounds",slot=2,targets=[a])
    assert a.hp==13  # 4d8 + Wis 4 + Disciple (2+2)
    assert c.hp==34
    combat.begin_turn(c); combat.use_action(c,"Divine Spark (Heal)",[a])
    assert a.hp==19 and c.hp==34


def test_potent_spellcasting_and_divine_strike_own_turn_limit(spells,monkeypatch):
    c=actor("cleric",7); c.features.pop("divine_strike"); c.features["potent_spellcasting"]=build("cleric",7)["features"]["potent_spellcasting"]; c.spells=["Sacred Flame"]; t=Combatant("target",max_hp=500)
    combat=Combat([c,t],spells); combat.begin_turn(c)
    monkeypatch.setattr(dice,"d20",lambda *a,**k: 1)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b: 1)
    combat.cast(c,"Sacred Flame",targets=[t]); assert t.hp==494  # 2d8 + Wis 4
    monkeypatch.setattr(dice,"d20",lambda *a,**k: 20)
    c.features.pop("potent_spellcasting"); c.features["divine_strike"]=build("cleric",7,choices={"blessed_strikes":"divine_strike"})["features"]["divine_strike"]
    combat.begin_turn(c); combat.weapon_attack(c,t,c.attacks[0]); assert t.hp==486
    combat.weapon_attack(c,t,c.attacks[0]); assert t.hp==480
    combat.begin_turn(t); combat.weapon_attack(c,t,c.attacks[0]); assert t.hp==474


@pytest.mark.parametrize("path", sorted((ROOT/"builds").glob("*.yaml")), ids=lambda p:p.stem)
def test_every_preset_builder_math(path):
    spec=read_yaml(path); sheet=load_build(path); level=spec["level"]; name=spec["class"]
    faces={"fighter":10,"rogue":8,"wizard":6,"cleric":8}[name]
    abilities=spec["abilities"].copy()
    for add in spec["choices"]["asis"].values():
        for a,n in add.items(): abilities[a]+=n
    mod=lambda a:(abilities[a]-10)//2
    assert sheet["abilities"]==abilities
    assert sheet["max_hp"]==faces+(level-1)*(faces//2+1)+level*mod("con")
    assert sheet["hit_dice"]=={"die":f"d{faces}","count":level}
    assert sheet["proficiency_bonus"]==2+(level-1)//4
    armor,shield,weapons=EQUIPMENT[spec["equipment"]]
    styles=spec["choices"].get("fighting_style",[]) if name=="fighter" else []
    assert sheet["ac"]=={"none":10+mod("dex"),"chain":16,"studded":12+mod("dex"),"scale":14+min(2,mod("dex"))}[armor]+2*shield+int("defense" in styles and armor!="none")
    for attack in sheet["attacks"]:
        archery=2 if "archery" in styles and attack["kind"]=="ranged" else 0
        dueling=2 if "dueling" in styles and attack["kind"]=="melee" and shield and "two_handed" not in attack["properties"] else 0
        assert attack["to_hit"]==sheet["proficiency_bonus"]+mod(attack["ability"])+archery
        assert attack["effects"][0]["damage"]["bonus"]==mod(attack["ability"])+dueling
    if name in {"wizard","cleric"}:
        ability="int" if name=="wizard" else "wis"
        assert sheet["spell_dc"]==8+sheet["proficiency_bonus"]+mod(ability)
        assert sheet["spell_attack_bonus"]==sheet["spell_dc"]-8
        expected=[[2],[3],[4,2],[4,3],[4,3,2],[4,3,3],[4,3,3,1],[4,3,3,2],[4,3,3,3,1],[4,3,3,3,2]][level-1]
        assert sheet["spell_slots"]==dict(enumerate(expected,1))
        assert len(sheet["prepared_spells"])==[4,5,6,7,9,10,11,12,14,15][level-1]
        assert len(spec["choices"]["cantrips"])==(3 if level<4 else 4 if level<10 else 5)


@pytest.mark.parametrize("name,sub,equipment",[("fighter","champion","chain_greatsword"),("cleric","life","chain_shield")])
def test_fixed_sheet_numeric_regression(name,sub,equipment):
    fixed=load_sheet(ROOT/"characters"/(name+"5.yaml"))
    base=fixed["abilities"].copy(); primary="str" if name=="fighter" else "wis"; base[primary]-=2
    built=build(name,5,sub,base,equipment,{"ability_method":"assigned","asis":{4:{primary:2}}})
    for key in ("max_hp","ac","proficiency_bonus","abilities","hit_dice","limited_uses","spell_dc","spell_attack_bonus","spell_slots"):
        if key in fixed: assert built[key]==fixed[key],key
    assert built["attacks"][0]["to_hit"]==fixed["attacks"][0]["to_hit"]
    assert built["attacks"][0]["effects"]==fixed["attacks"][0]["effects"]


@pytest.mark.parametrize("kwargs",[
    {"level":0},{"level":11},{"level":True},{"subclass":"battle_master"},
    {"choices":{"feats":["Alert"]}},{"choices":{"asis":{4:{"str":3}}}},
    {"choices":{"asis":{}}},{"choices":{"weapon_masteries":["greatsword"]*5}},
    {"choices":{"fighting_style":"blind_fighting"}},{"choices":{"cunning_strike":["trip"]}},
    {"abilities":dict(str=20,dex=20,con=20,int=20,wis=20,cha=20)},
])
def test_builder_strict_choices(kwargs):
    args={"class_name":"fighter","level":5}; args.update(kwargs)
    with pytest.raises(ValidationError): build(**args)


def test_other_equipment_styles_and_point_buy(spells,monkeypatch):
    f=build("fighter",5,equipment="chain_sword_shield",choices={"fighting_style":"dueling"})
    assert f["ac"]==18 and f["attacks"][0]["effects"][0]["damage"]["bonus"]==5
    a=build("fighter",5,equipment="leather_archer",choices={"fighting_style":"archery"})
    assert a["ac"]==13 and a["attacks"][0]["to_hit"]==6
    c=build("cleric",3,equipment="scale_shield",choices={"divine_order":"thaumaturge"})
    assert c["ac"]==16 and len(c["spells"])-len(c["prepared_spells"])>=4
    p=build("rogue",1,abilities=dict(str=8,dex=15,con=15,int=8,wis=15,cha=8),choices={"ability_method":"point_buy"})
    assert p["max_hp"]==10
    f=Combatant.from_sheet(build("fighter",7),"f","party"); t=Combatant("t"); combat=Combat([f,t],spells)
    monkeypatch.setattr(dice,"d20",lambda *a,**k: 10); monkeypatch.setattr(combat.rng,"randint",lambda a,b:1)
    combat.weapon_attack(f,t,f.attacks[0]); assert t.hp==90 # GWF min3 per d6 + Str4


def test_divine_intervention_slotless_nonprepared_and_rest(spells,monkeypatch):
    c=Combatant.from_sheet(build("cleric",10),"c","party"); c.hp=1; c.spells=[]; c.spell_slots={}
    combat=Combat([c],spells); combat.begin_turn(c)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b:1)
    inst=combat.divine_intervention(c,"Cure Wounds",[c])
    assert inst and c.hp==7  # 2d8 + Wis4, no Disciple for a slotless cast
    assert c.limited_uses["divine_intervention"]==0 and not c.spells
    assert not c.resources_spent.get("slot_1")
    assert combat.divine_intervention(c,"Cure Wounds",[c]) is None
    with pytest.raises(ValueError): combat.divine_intervention(c,"Fireball")


def test_memorize_spell_default_policy_on_short_rest():
    import random
    from engine.day import take_rest
    w=Combatant.from_sheet(build("wizard",5),"w","party")
    assert "Fireball" in w.spellbook
    w.spells.remove("Fireball"); w.prepared_spells.remove("Fireball")
    w.prepared_spells.append("Sleep"); w.spells.append("Sleep"); trace=[]
    take_rest([w],"short",random.Random(1),log=trace)
    assert "Fireball" in w.spells and "Sleep" not in w.spells
    assert any(x["name"]=="Memorize Spell" for x in trace)


def test_all_class_numeric_mutants_killed():
    from engine.step4_report import source_audit
    report=source_audit()
    assert report["numeric_fields"]==557 and report["mutants"]>=report["numeric_fields"]
    assert report["survivors"]==[]


def test_independent_source_oracle_responds_to_changed_source(monkeypatch):
    import engine.class_source as oracle
    original=oracle.source
    c,s,f=deepcopy(original("fighter")); c["classTableGroups"][0]["rows"][4][0]="4"
    monkeypatch.setattr(oracle,"source",lambda n:(c,s,f))
    with pytest.raises(ValidationError,match="source drift"): validate_class(read_yaml(ROOT/"classes/fighter.yaml"))
    c,s,f=deepcopy(original("fighter")); f[("subclass","Improved Critical",3)]["entries"][0]=f[("subclass","Improved Critical",3)]["entries"][0].replace("19 or","18 or")
    with pytest.raises(ValidationError,match="source drift"): validate_class(read_yaml(ROOT/"classes/fighter.yaml"))


def test_ai_seeded_class_actions_and_reactions_logged(spells):
    from engine.policy import Policy
    policy=Policy(); names=set()
    def collect(combat): names.update(x.get("name") for x in combat.log if "name" in x)
    f=actor(level=5); f.hp=1; t=Combatant("enemy",max_hp=1000)
    combat=Combat([f,t],spells,seed=1); combat.begin_turn(f); policy.take_turn(combat,f); collect(combat)
    r=actor("rogue",7); r.cunning_strike=["poison"]; t=Combatant("enemy",max_hp=1000,attacks=deepcopy(r.attacks))
    combat=Combat([r,t],spells,seed=1); combat.round=2; combat.begin_turn(r); policy.take_turn(combat,r); collect(combat)
    combat.begin_turn(t); combat.weapon_attack(t,r,{**t.attacks[0],"to_hit":100}); collect(combat)
    r=actor("rogue",2); ally=actor(); t=Combatant("enemy",max_hp=1000)
    combat=Combat([r,ally,t],spells,seed=1); combat.begin_turn(r); policy.take_turn(combat,r); collect(combat)
    w=actor("wizard",7); w.spells=["Fireball","Ray of Frost"]
    allies=[Combatant(f"ally{i}",team="party") for i in range(2)]
    enemies=[Combatant(f"enemy{i}",max_hp=1000) for i in range(3)]
    combat=Combat([w,*allies,*enemies],spells,seed=1,area=lambda s,z,n:n); combat.begin_turn(w)
    value=combat.expected_spell_damage(w,combat.scale(w,spells["Fireball"],3),enemies[0])
    w.features["sculpt_spells"]=False
    unsafe=combat.expected_spell_damage(w,combat.scale(w,spells["Fireball"],3),enemies[0]); w.features["sculpt_spells"]=True
    assert value>unsafe
    policy.take_turn(combat,w); collect(combat)
    assert any(x.get("spell")=="Fireball" and x["event"]=="cast" for x in combat.log)
    assert all(a.hp==100 for a in allies)
    c=actor("cleric",5); a=Combatant("a",team="party",max_hp=40,hp=0); b=Combatant("b",team="party",max_hp=40,hp=1)
    combat=Combat([c,a,b,Combatant("enemy",max_hp=1000)],spells,seed=1); combat.begin_turn(c); policy.take_turn(combat,c); collect(combat)
    c=actor("cleric",5); u=Combatant("undead",max_hp=1000,creature_type="undead",attacks=deepcopy(c.attacks))
    combat=Combat([c,u],spells,seed=1); combat.begin_turn(c); policy.take_turn(combat,c); collect(combat)
    f=actor(level=9); combat=Combat([f],spells,seed=1); combat.saving_throw(f,"cha",20); collect(combat)
    assert {"Second Wind","Action Surge","Steady Aim","Sneak Attack","Cunning Strike","Cunning Action","Uncanny Dodge","Sculpt Spells","Preserve Life","Turn Undead","Sear Undead","Indomitable"} <= names


def test_sneak_targeting_prefers_eligible_target(spells):
    r=actor("rogue",5); r.conditions.add("poisoned"); ally=actor()
    weak=Combatant("weak",hp=5); eligible=Combatant("eligible",hp=40,conditions={"restrained"})
    combat=Combat([r,ally,weak,eligible],spells); combat.round=2
    assert combat.policy.weapon_target(combat,r,[weak,eligible]) is eligible


@pytest.mark.parametrize("mastery",["sap","slow","push","topple"])
def test_tactical_master_masteries_exact(spells,monkeypatch,mastery):
    f=actor(level=9); t=Combatant("target",attacks=deepcopy(f.attacks)); f.attacks[0]["mastery"]="graze"
    combat=Combat([f,t],spells); combat.begin_turn(f)
    if mastery=="topple": f.features["tactical_master"]=False; f.attacks[0]["mastery"]="topple"
    monkeypatch.setattr(combat.policy,"tactical_master",lambda *a:mastery)
    rolls=iter([10,1]); monkeypatch.setattr(dice,"d20",lambda *a,**k:next(rolls))
    combat.weapon_attack(f,t,f.attacks[0])
    if mastery!="topple": assert any(e.get("name")=="Tactical Master" and e["mastery"]==mastery for e in combat.log)
    if mastery=="sap": assert combat.roll_flags(t,"attack_rolls",consume=True)==(False,True)
    elif mastery=="slow":
        assert combat.modifier(t,"speed",30)==20
        combat.begin_turn(f); assert combat.modifier(t,"speed",30)==30
    elif mastery=="topple": assert t.has_condition("prone")
    else: assert any(e.get("name")=="Push" and e["spatial_only"] for e in combat.log)


def test_remarkable_athlete_initiative_and_athletics(spells,monkeypatch):
    f=actor(level=3); t=Combatant("target"); combat=Combat([f,t],spells)
    flags=[]
    def roll(rng,advantage=False,disadvantage=False): flags.append((advantage,disadvantage)); return 10
    monkeypatch.setattr(dice,"d20",roll)
    combat.run(max_rounds=1)
    assert flags[0]==(True,False) and flags[1]==(False,False)
    flags.clear(); combat.ability_check(f,"str",15,skill="athletics")
    assert flags==[(True,False)]


def test_thaumaturge_check_and_spell_armor_math(spells,monkeypatch):
    c=Combatant.from_sheet(build("cleric",5,equipment="scale_shield",choices={"divine_order":"thaumaturge"}),"c","party")
    w=Combatant.from_sheet(build("wizard",5),"w","party")
    combat=Combat([c,w],spells)
    monkeypatch.setattr(dice,"d20",lambda *a,**k:10)
    assert combat.ability_check(c,"int",17,skill="religion") # 10 + Int1 + PB3 + Wis3
    assert not combat.ability_check(c,"int",18,skill="religion")
    assert combat.armor_class(w)==12
    combat.begin_turn(w); combat.cast(w,"Mage Armor",targets=[w],slot=1)
    assert combat.armor_class(w)==15 and w.spell_slots[1]==3


def test_regenerating_zero_hp_enemy_can_be_finished_by_fire(spells):
    w=Combatant.from_sheet(build("wizard",5),"w","party")
    t=Combatant.from_sheet(load_sheet(ROOT/"monsters/troll.yaml"),"t","enemy")
    t.hp=0; t.conditions={"unconscious","prone"}
    combat=Combat([w,t],spells,seed=1); combat.begin_turn(w)
    assert combat.enemies(w)==[t]
    assert combat.cast(w,"Fireball",slot=3)
    assert t.has_status("regeneration_blocked")
    combat.begin_turn(t)
    assert t.permanently_removed and t.hp==0


def test_conservative_uncanny_dodge_is_not_a_budgeted_spell(spells):
    from engine.policy import ConservativePolicy
    r=actor("rogue",5); t=Combatant("t"); combat=Combat([r,t],spells,seed=1,policy=ConservativePolicy())
    combat.attack(t,r,100,lambda *a:combat.damage(r,11,"slashing",t))
    assert r.hp==95 and any(e.get("name")=="Uncanny Dodge" for e in combat.log)


def test_default_tactical_master_sap_logged(spells):
    f=actor(level=9); f.attacks[0]["mastery"]="graze"
    t=Combatant("target",max_hp=1000,attacks=deepcopy(f.attacks),extra_attack=3)
    combat=Combat([f,t],spells,seed=1); combat.begin_turn(f); combat.policy.take_turn(combat,f)
    assert any(e.get("name")=="Tactical Master" and e["mastery"]=="sap" for e in combat.log)


def test_preserve_life_rejects_unbloodied_without_spending(spells):
    c=actor("cleric",3); t=Combatant("t",team="party",hp=80)
    combat=Combat([c,t],spells); combat.begin_turn(c)
    with pytest.raises(ValueError,match="invalid selection count"): combat.use_action(c,"Preserve Life",[t])
    assert c.limited_uses["channel_divinity"]==2 and c.action==1


@pytest.mark.parametrize("name",["fighter","rogue","wizard","cleric"])
def test_build_every_level_validates(name):
    for level in range(1,11):
        s=build(name,level)
        assert s["level"]==level and s["proficiency_bonus"]==2+(level-1)//4


def test_scholar_does_not_allow_insight_expertise():
    with pytest.raises(ValidationError,match="choices.expertise"):
        build("wizard",3,choices={"skills":["insight","arcana"],"expertise":["insight"]})


def test_potent_cantrip_weapon_strike_miss_and_scoring(spells,monkeypatch):
    w=Combatant.from_sheet(build("wizard",5),"w","party"); w.spells=["True Strike"]
    t=Combatant("t"); combat=Combat([w,t],spells); combat.begin_turn(w)
    assert combat.expected_spell_damage(w,combat.scale(w,spells["True Strike"],0),t)>0
    monkeypatch.setattr(dice,"d20",lambda *a,**k:1)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b:1)
    combat.cast(w,"True Strike",[t])
    assert t.hp==98 # (quarterstaff 1d8 + Int3 + cantrip 1d6) // 2


def test_class_hook_preserves_empty_weapon_probe(spells,monkeypatch):
    a=Combatant("a",team="party"); t=Combatant("t"); combat=Combat([a,t],spells)
    monkeypatch.setattr(dice,"d20",lambda *a,**k:10)
    assert combat.weapon_attack(a,t,{"name":"Probe","kind":"melee","to_hit":100,"effects":[]})
    assert t.hp==100


def test_slotless_mass_healing_survives_zero_maximum_hp_target(spells):
    c=Combatant.from_sheet(build("cleric",10),"c","party"); c.hp=1
    c.spell_slots=dict.fromkeys(c.spell_slots,0); c.limited_uses["channel_divinity"]=0
    zero=Combatant("zero",team="party",max_hp=10,hp=0); zero.max_hp=0
    enemy=Combatant("enemy",max_hp=1000)
    combat=Combat([c,zero,enemy],spells,seed=1); combat.begin_turn(c); combat.policy.take_turn(combat,c)
    assert c.hp>1 and zero.hp==0
    assert any(e.get("name")=="Divine Intervention" for e in combat.log)


def test_shared_scorer_accepts_nameless_action_probe(spells):
    from engine.sheets import effect_block
    a=Combatant("a",team="party"); t=Combatant("t")
    b=effect_block("probe",target={"select":"area","shape":"cone","size_ft":15,"affects":"all"},save={"ability":"dex","on_success":"half"},on_fail=[{"damage":{"dice":"2d6","type":"fire"}}])
    combat=Combat([a,t],spells)
    assert combat.expected_spell_damage(a,{"effects":[b]},t)>0


def test_channel_divinity_magic_resistance_and_action_surge(spells,monkeypatch):
    c=actor("cleric",7); t=Combatant("t",features={"magic_resistance":True})
    combat=Combat([c,t],spells); combat.begin_turn(c)
    flags=[]
    def roll(rng,advantage=False,disadvantage=False): flags.append((advantage,disadvantage)); return 10
    monkeypatch.setattr(dice,"d20",roll)
    combat.use_action(c,"Divine Spark (Radiant)",[t])
    assert flags==[(True,False)]
    combat.begin_turn(c); c.surge_actions=c.action=1
    assert not combat.use_action(c,"Turn Undead")
    assert c.limited_uses["channel_divinity"]==2


@pytest.mark.parametrize("flag,scenario",[
    ("improved_critical",test_champion_critical_is_weapon_only_and_automatic_hit),
    ("assassinate",test_sneak_attack_critical_once_per_global_turn_and_assassinate),
    ("sneak_attack",test_sneak_attack_critical_once_per_global_turn_and_assassinate),
    ("disciple_of_life",test_disciple_and_blessed_healer_actual_slot_level_not_channel),
    ("blessed_healer",test_disciple_and_blessed_healer_actual_slot_level_not_channel),
    ("sculpt_spells",test_sculpt_spells_spillover_not_caster_and_limit),
    ("uncanny_dodge",test_uncanny_dodge_complete_packet_and_visibility),
])
def test_step4_fix4_behavior_kills_removed_builder_grant(spells,monkeypatch,flag,scenario):
    import engine.builder as module
    from test_step4_fixes import mutate
    mutate(monkeypatch,module,"_build",'if k not in {"builder","progression"}',f'if k not in {{"builder","progression",{flag!r}}}')
    with pytest.raises(AssertionError): scenario(spells,monkeypatch)
