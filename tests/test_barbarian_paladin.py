"""XPHB Berserker and Devotion builds and deterministic combat hooks."""
from copy import deepcopy
import random

import pytest

from engine import Combat, Combatant, dice
from engine.builder import build, load_build, EQUIPMENT, WEAPONS
from engine.classes import load_class
from engine.class_catalog import declaration
from engine.class_source import check_class_source
from engine.day import take_rest, cleanup_encounter
from engine.loader import ROOT, load_spells, read_yaml, ValidationError
from engine.policy import Policy, NovaPolicy, ConservativePolicy, RationedPolicy
from engine.sheets import validate_sheet
from engine.state import Effect

LEVELS = (1,3,5,7,10)
BUILDS = [f"{name}_{level}{profile}" for name in ("barbarian","paladin") for level in LEVELS for profile in ("","_casual","_optimized")]


@pytest.fixture(scope="module")
def spells(): return load_spells()


def pc(name="barbarian", level=5, **kwargs):
    return Combatant.from_sheet(build(name,level,**kwargs),name,"party")


def fixed(combat, monkeypatch, natural=15):
    monkeypatch.setattr(dice,"d20",lambda *a,**k: natural)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b: 1)


def features(combat, name):
    return [e for e in combat.log if e.get("name")==name]


@pytest.mark.parametrize("name",BUILDS)
def test_all_builds(name):
    r=read_yaml(ROOT/"builds"/(name+".yaml")); s=load_build(name)
    validate_sheet(s,name)
    level=r["level"]; barbarian=r["class"]=="barbarian"; die=12 if barbarian else 10
    mod=lambda a:(s["abilities"][a]-10)//2
    assert s["max_hp"]==die+(level-1)*(die//2+1)+level*mod("con")
    armor,shield,_=EQUIPMENT[r["equipment"]]
    defense="defense" in r["choices"].get("fighting_style",[])
    assert s["ac"]==({"none":10+mod("dex")+(mod("con") if barbarian else 0),"chain":16,"scale":14+min(2,mod("dex"))}[armor])+2*shield+int(defense and armor!="none")
    for a in s["attacks"]:
        assert a["to_hit"]==2+(level-1)//4+mod(a["ability"])
    assert s.get("extra_attack",1)==(2 if level>=5 else 1)
    slots={1:{1:2},3:{1:3},5:{1:4,2:2},7:{1:4,2:3},10:{1:4,2:3,3:2}}[level]
    assert s.get("spell_slots",{})==({} if barbarian else slots)
    if not barbarian:
        assert s["spell_ability"]=="cha" and s["spell_dc"]==8+2+(level-1)//4+mod("cha")
        assert len(s["prepared_spells"])=={1:2,3:4,5:6,7:7,10:9}[level]
        assert ("Divine Smite" in s["spells"]) == (level>=2 or "Divine Smite" in s["prepared_spells"])


@pytest.mark.parametrize("name",["barbarian","paladin"])
def test_source_and_every_level(name):
    c=load_class(name)
    assert c==declaration(name) and check_class_source(c)>0
    assert c["asi_levels"]==[4,8]
    for level in range(1,11): validate_sheet(build(name,level),name)
    mutant=deepcopy(c); mutant["levels"][3]["resources"]["rage" if name=="barbarian" else "channel_divinity"]["max"]+=1
    with pytest.raises(ValidationError): check_class_source(mutant)


def test_new_class_numeric_mutants():
    from engine.step4_report import source_audit
    audit=source_audit(("barbarian","paladin"))
    assert not audit["survivors"] and audit["mutants"]>=audit["numeric_fields"]>0


def test_heavy_weapons_and_training():
    for w in ("greataxe","greatsword","maul"): assert "heavy" in WEAPONS[w][4]
    with pytest.raises(ValidationError): build("barbarian",3,equipment="chain_greatsword")
    with pytest.raises(ValidationError): build("paladin",1,choices={"fighting_style":"defense"})


def test_rage_resistance_strength_flags_and_recovery(spells,monkeypatch):
    b=pc(level=3); t=Combatant("t"); c=Combat([b,t],spells); c.begin_turn(b)
    assert c.rage(b) and b.bonus_action==0 and b.limited_uses["rage"]==2
    assert not c.rage(b)
    for dtype in ("slashing","bludgeoning","piercing"):
        before=b.hp; c.damage(b,5,dtype,t); assert b.hp==before-2
    before=b.hp; c.damage(b,5,"fire",t); assert b.hp==before-5
    assert c.roll_flags(b,"saves","str")[0] and c.roll_flags(b,"ability_checks","str")[0]
    assert not c.roll_flags(b,"saves","con")[0]
    take_rest([b],"short",random.Random(1)); assert b.limited_uses["rage"]==3
    b.limited_uses["rage"]=0
    take_rest([b],"long",random.Random(1)); assert b.limited_uses["rage"]==3
    cleanup_encounter(c); assert not b.raging


def test_rage_blocks_casting_and_ends_concentration(spells):
    b=pc(); b.spells=["Bless"]; b.spell_slots={1:2}
    c=Combat([b],spells); c.begin_turn(b)
    assert c.cast(b,"Bless",targets=[b]) and b.concentration is not None
    assert c.rage(b) and b.concentration is None and not c.can_cast(b,"Bless")
    b.conditions.add("incapacitated"); c.begin_turn(b); assert not b.raging


def test_reckless_frenzy_damage_and_expiry(spells,monkeypatch):
    b=pc(level=5,equipment="unarmored_greatsword"); t=Combatant("t",max_hp=500)
    c=Combat([b,t],spells); c.begin_turn(b); fixed(c,monkeypatch)
    c.rage(b); c.weapon_action(b)
    # Two weapon hits, Str 4 + Rage 2 each; Frenzy 2d6 only on the first.
    assert t.hp==500-2*(2+4+2)-2
    assert len(features(c,"Frenzy"))==1 and len(features(c,"Reckless Attack"))==1
    assert c.roll_flags(t,"attack_rolls","dex",against=b)[0]
    c.begin_turn(t); assert c.roll_flags(b,"attack_rolls","str",against=t)[0]
    c.begin_turn(b); assert not c.roll_flags(t,"attack_rolls","str",against=b)[0]
    c.weapon_action(b); assert len(features(c,"Frenzy"))==2


def test_reckless_can_be_declined_and_danger_sense(spells,monkeypatch):
    class Careful(Policy):
        def reckless_attack(self,*args): return False
    b=pc(level=2); t=Combatant("t"); c=Combat([b,t],spells,policy=Careful()); c.begin_turn(b); fixed(c,monkeypatch)
    c.weapon_attack(b,t,b.attacks[0]); assert not features(c,"Reckless Attack")
    assert c.roll_flags(b,"saves","dex")[0]
    b.conditions.add("incapacitated"); assert not c.roll_flags(b,"saves","dex")[0]
    assert not build("barbarian",6)["features"].get("initiative_advantage")
    assert build("barbarian",7)["features"]["initiative_advantage"]


def test_mindless_rage_ends_and_prevents_conditions(spells):
    b=pc(level=7); c=Combat([b],spells); c.begin_turn(b)
    b.conditions.update({"charmed","frightened"})
    b.effects.append(Effect("apply_condition",{"condition":"charmed"},0,"probe"))
    c.rage(b)
    for condition in ("charmed","frightened"):
        assert not b.has_condition(condition) and c.condition_immune(b,condition)
        assert condition not in b.conditions
    assert not any(e.kind=="apply_condition" for e in b.effects)


def test_brutal_strike_forfeits_advantage_and_hamstrings(spells,monkeypatch):
    b=pc(level=10,equipment="unarmored_greatsword"); t=Combatant("t",max_hp=500)
    c=Combat([b,t],spells); c.begin_turn(b); fixed(c,monkeypatch); c.rage(b); c.weapon_action(b)
    attacks=[e for e in c.log if e["event"]=="attack"]
    assert not attacks[0]["advantage"] and attacks[1]["advantage"]
    assert len(features(c,"Brutal Strike"))==1
    assert c.modifier(t,"speed",t.speed)==15
    c.begin_turn(b); assert c.modifier(t,"speed",t.speed)==30


def test_retaliation_once_per_reaction(spells,monkeypatch):
    b=pc(level=10,equipment="unarmored_greatsword"); t=Combatant("t",max_hp=500)
    c=Combat([b,t],spells); c.begin_turn(t); fixed(c,monkeypatch)
    c.damage(b,1,"fire",t); assert b.reaction==0 and t.hp<500
    hp=t.hp; c.damage(b,1,"fire",t); assert t.hp==hp
    assert len(features(c,"Retaliation"))==1
    c.begin_turn(b); c.damage(b,1,"fire",t); assert len(features(c,"Retaliation"))==2


@pytest.mark.parametrize("critical,kind,slot,expected",[(False,"humanoid",1,2),(True,"undead",2,8),(False,"fiend",3,5)])
def test_smite_spell_dice_slot_critical_and_bonus_action(spells,monkeypatch,critical,kind,slot,expected):
    p=pc("paladin",10); p.limited_uses["paladins_smite"]=0
    t=Combatant("t",max_hp=500,creature_type=kind)
    c=Combat([p,t],spells); c.begin_turn(p); fixed(c,monkeypatch,20 if critical else 15)
    p.statuses["weapon_hits"]=1
    p.spell_slots={slot:1}; a=p.attacks[0]; base=(4 if critical else 2)+p.mod("str")
    c.weapon_attack(p,t,a)
    assert t.hp==500-base-expected and p.bonus_action==0 and p.spell_slots[slot]==0
    assert any(e["event"]=="cast" and e["spell"]=="Divine Smite" for e in c.log)


def test_free_smite_then_slot_and_slot_cast_limit(spells,monkeypatch):
    p=pc("paladin",3); t=Combatant("t",max_hp=500); c=Combat([p,t],spells); fixed(c,monkeypatch)
    c.begin_turn(p); before=p.spell_slots.copy(); c.weapon_attack(p,t,p.attacks[0])
    assert p.spell_slots==before and p.limited_uses["paladins_smite"]==0
    c.begin_turn(p); c.weapon_attack(p,t,p.attacks[0]); assert p.spell_slots[1]==before[1]-1
    c.begin_turn(p); c.cast(p,"Cure Wounds",targets=[p]); before=p.spell_slots.copy()
    c.weapon_attack(p,t,p.attacks[0]); assert p.spell_slots==before and p.bonus_action==1
    take_rest([p],"long",random.Random(1)); assert p.limited_uses["paladins_smite"]==1


def test_smite_waits_for_critical_when_only_one_slot(spells,monkeypatch):
    p=pc("paladin",5); p.limited_uses["paladins_smite"]=0; p.spell_slots={1:1}
    t=Combatant("t",max_hp=500); c=Combat([p,t],spells); c.begin_turn(p); fixed(c,monkeypatch)
    c.weapon_attack(p,t,p.attacks[0]); assert p.bonus_action==1
    monkeypatch.setattr(dice,"d20",lambda *a,**k:20)
    c.weapon_attack(p,t,p.attacks[0]); assert p.bonus_action==0 and p.spell_slots[1]==0


def test_lay_on_hands_pool_downed_and_ai(spells,monkeypatch):
    p=pc("paladin",3); ally=Combatant("ally",team="party",hp=0,max_hp=50,conditions={"unconscious"}); t=Combatant("t",max_hp=500)
    p.spells=[]
    c=Combat([p,ally,t],spells); c.begin_turn(p); fixed(c,monkeypatch)
    c.policy.take_turn(c,p)
    assert ally.hp==15 and not ally.has_condition("unconscious")
    assert p.limited_uses["lay_on_hands"]==0 and p.bonus_action==0 and features(c,"Lay on Hands")
    assert not c.lay_on_hands(p,ally)
    take_rest([p],"long",random.Random(1)); assert p.limited_uses["lay_on_hands"]==15


def test_sacred_weapon_attack_action_duration_and_recovery(spells,monkeypatch):
    p=pc("paladin",5); t=Combatant("t",max_hp=500); c=Combat([p,t],spells); c.begin_turn(p); fixed(c,monkeypatch)
    c.weapon_action(p)
    assert p.limited_uses["channel_divinity"]==1 and len(features(c,"Sacred Weapon"))==1
    attack=next(e for e in c.log if e["event"]=="attack")
    assert attack["total"]==15+p.attacks[0]["to_hit"]+max(1,p.mod("cha"))
    c.begin_turn(p); c.weapon_action(p); assert len(features(c,"Sacred Weapon"))==1
    c.time_rounds=100; c.begin_turn(p); c.weapon_action(p); assert len(features(c,"Sacred Weapon"))==2
    take_rest([p],"short",random.Random(1)); assert p.limited_uses["channel_divinity"]==1


def test_auras_use_area_coverage_no_stacking_and_incapacitation(spells,monkeypatch):
    p=pc("paladin",10); p.abilities["cha"]=18
    q=pc("paladin",10); q.id="q"; q.abilities["cha"]=14
    a=Combatant("a",team="party"); b=Combatant("b",team="party")
    c=Combat([p,q,a,b],spells,area=lambda shape,size,n,*args: 2); fixed(c,monkeypatch,10)
    assert c.aura_save_bonus(a)==4 and c.aura_save_bonus(b)==0
    assert c.saving_throw(a,"dex",14) and not c.saving_throw(b,"dex",14)
    a.conditions.update({"charmed","frightened"})
    assert not a.has_condition("charmed") and not a.has_condition("frightened")
    p.conditions.add("incapacitated"); assert c.aura_save_bonus(a)==2
    q.conditions.add("incapacitated"); assert c.aura_save_bonus(a)==0 and a.has_condition("charmed")


def test_rationed_smite_respects_slot_budget(spells,monkeypatch):
    class Budget(RationedPolicy):
        def emergency(self,*a): return False
        def losing(self,*a): return False
        def already_won(self,*a): return False
        def needs_resources(self,*a): return False
    p=pc("paladin",5); p.limited_uses["paladins_smite"]=0
    t=Combatant("t",max_hp=500); c=Combat([p,t],spells,policy=Budget()); fixed(c,monkeypatch)
    c.encounters_remaining=8
    c.slots_at_start={p.id:p.spell_slots.copy()}
    # 8 slot-level points, share 1: one first-level smite, then save the rest.
    c.begin_turn(p); c.weapon_attack(p,t,p.attacks[0]); assert p.resources_spent.get("slot_1")==1
    c.begin_turn(p); c.weapon_attack(p,t,p.attacks[0]); assert p.resources_spent.get("slot_1")==1


def test_rage_ai_opens_fight(spells,monkeypatch):
    b=pc(level=1); t=Combatant("t",max_hp=500); c=Combat([b,t],spells); fixed(c,monkeypatch); c.begin_turn(b)
    c.policy.take_turn(c,b)
    assert b.raging and b.bonus_action==0 and features(c,"Rage")


@pytest.mark.parametrize("name",["barbarian","paladin"])
def test_compare_uses_fighter_role(name,monkeypatch):
    import engine.compare as compare
    calls=[]
    monkeypatch.setattr(compare,"rate_party",lambda party,**kw: calls.append(party) or object())
    compare.compare(5,name,[f"{name}_5"])
    assert calls[0]==["fighter_5","cleric_5","rogue_5","wizard_5"]
    assert calls[1]==[f"{name}_5","cleric_5","rogue_5","wizard_5"]
    found=compare.variants(name,5)
    assert any(v["choices"]["asis"][4].get("feat")=="great_weapon_master" for v in found)
    assert any(v["equipment"].endswith("greatsword") for v in found)


def test_aura_existing_charm_dependent_incapacity(spells):
    p=pc("paladin",7); c=Combat([p],spells)
    p.effects=[Effect("apply_condition",{"condition":"charmed"},0,"probe"),
               Effect("apply_condition",{"condition":"incapacitated"},0,"probe",requires_condition="charmed")]
    assert p.has_condition("incapacitated") and c.aura_save_bonus(p)==0
    p.effects.pop()
    assert not p.has_condition("charmed") and c.aura_save_bonus(p)==max(1,p.mod("cha"))


def test_frenzy_critical_and_cleave_once(spells,monkeypatch):
    b=pc(level=3); t=Combatant("t",max_hp=500); u=Combatant("u",max_hp=500)
    c=Combat([b,t,u],spells); c.begin_turn(b); fixed(c,monkeypatch,20); c.rage(b)
    c.weapon_attack(b,t,b.attacks[0])
    assert t.hp==500-(2+b.mod("str")+2+4)
    assert u.hp==500-(2+2)  # Cleave omits positive Str modifier; Rage still applies.
    assert len(features(c,"Frenzy"))==1 and len(features(c,"Cleave"))==1
    c.weapon_attack(b,t,b.attacks[0]); assert len(features(c,"Cleave"))==1


def test_feral_instinct_initiative_roll(spells,monkeypatch):
    b=pc(level=7); t=Combatant("t",max_hp=500); c=Combat([b,t],spells)
    rolls=[]
    def roll(rng, advantage=False, disadvantage=False):
        rolls.append(advantage)
        return 10
    monkeypatch.setattr(dice,"d20",roll)
    c.run(max_rounds=1)
    assert rolls[:2]==[True,False]


def test_sacred_weapon_does_not_double_on_hew(spells,monkeypatch):
    p=pc("paladin",5,choices={"asis":{4:{"feat":"great_weapon_master","ability":"str"}}})
    p.spells=[]
    t=Combatant("t",max_hp=500); c=Combat([p,t],spells); c.begin_turn(p); fixed(c,monkeypatch,20)
    c.weapon_action(p)
    attacks=[e for e in c.log if e["event"]=="attack"]
    assert len(attacks)==3 and features(c,"Hew")
    assert len({e["total"] for e in attacks})==1


def test_rage_ends_on_incapacity_and_clock_expiry(spells,monkeypatch):
    b=pc(level=3); t=Combatant("t"); c=Combat([b,t],spells); c.begin_turn(b); c.rage(b)
    b.effects.append(Effect("apply_condition",{"condition":"stunned"},0,"probe"))
    c.refresh_spell_effects(); b.effects.clear()
    assert not b.raging
    c.begin_turn(b); assert c.rage(b)
    c.advance_time(100)
    assert not b.raging


def test_sacred_weapon_expires_during_safe_time(spells,monkeypatch):
    p=pc("paladin",3); t=Combatant("t",max_hp=500); c=Combat([p,t],spells); c.begin_turn(p); fixed(c,monkeypatch)
    c.weapon_action(p); assert "sacred_weapon" in p.statuses
    c.advance_time(100); assert "sacred_weapon" not in p.statuses


def buff_fight(spells, hp=10000):
    p=pc("paladin"); p.spells=["Bless"]
    allies=[pc("fighter") for _ in range(3)]
    for i,a in enumerate(allies): a.id=f"ally{i}"
    enemy=Combatant.from_sheet(read_yaml(ROOT/"monsters"/"ogre.yaml"),"ogre","enemy")
    enemy.hp=enemy.max_hp=hp
    c=Combat([p,*allies,enemy],spells,seed=7); c.begin_turn(p)
    return c,p,allies,enemy


def test_paladin_bless_long_and_short_horizon(spells):
    for hp,cast in ((10000,True),(1,False)):
        c,p,allies,t=buff_fight(spells,hp)
        value=c.expected_buff_value(p,c.scale(p,spells["Bless"],1))
        assert value>0 and (value>c.expected_weapon_damage(p,t))==cast
        c.policy.take_turn(c,p)
        assert any(e["event"]=="cast" and e["spell"]=="Bless" for e in c.log)==cast
        assert any(e["event"]=="attack" for e in c.log)==(not cast)


def test_paladin_buff_values_targets_and_no_recast(spells):
    c,p,allies,t=buff_fight(spells)
    p.spells=["Shield of Faith","Magic Weapon"]
    allies[0].position="back"; allies[0].hp=allies[0].max_hp//2
    for name in p.spells:
        spec=c.scale(p,spells[name],spells[name]["level"])
        assert c.expected_buff_value(p,spec)>0
    p.spells=["Shield of Faith"]
    c.policy.take_turn(c,p)
    casts=[e for e in c.log if e["event"]=="cast"]
    assert len(casts)==1 and casts[0]["spell"] in p.spells
    assert p.bonus_action==0 and any(e["event"]=="attack" for e in c.log)
    assert not any(e["spell"]=="Divine Smite" for e in casts)
    protected=next(a for a in [p,*allies] if any(e.kind=="modify" and e.data.get("stat")=="ac" for e in a.effects))
    assert protected.position=="front"
    c,p,allies,t=buff_fight(spells)
    for a in [p,*allies]:
        c.begin_turn(p); assert c.cast(p,"Bless",targets=[a])
        p.concentration=None  # Fixture: independent active Bless effects on every ally.
    assert c.expected_buff_value(p,c.scale(p,spells["Bless"],1))==0


def test_buff_attack_cantrip_save_cantrip_and_hit_cap(spells):
    c,p,allies,t=buff_fight(spells)
    a=allies[0]; a.attacks=[]; a.spells=["Fire Bolt"]
    assert c.buff_attack_gain(a,t,2.5)>0
    a.spells=["Sacred Flame"]
    assert c.buff_attack_gain(a,t,2.5)==0
    a.spells=[]; a.attacks=deepcopy(p.attacks); a.attacks[0]["to_hit"]=100
    a.features={}; a.multiattack=[a.attacks[0]["name"]]*3
    assert c.buff_attack_gain(a,t,2.5)==pytest.approx(0)
    assert c.buff_attack_gain(a,t,1,1,weapon_only=True)==pytest.approx(3*.95)


def test_heroism_recurs_and_magic_weapon_tiers(spells):
    c,p,allies,t=buff_fight(spells)
    spec=c.scale(p,spells["Heroism"],1)
    target=sorted([p,*allies],key=lambda a:a.id)[0]
    target.temp_hp=100
    kept=c.concentration_horizon(p,c.enemies(p),10)
    assert 1<kept<10
    assert c.expected_buff_value(p,spec)==pytest.approx(min(p.spell_mod,c.at_will_damage_rate(t,target))*kept)
    magic=c.scale(p,spells["Magic Weapon"],3)
    assert c.expected_buff_value(p,magic,slot=3)>c.expected_buff_value(p,magic,slot=2)>0


def test_concentration_horizon_shrinks_with_incoming_hits(spells):
    c,p,allies,t=buff_fight(spells)
    base=c.concentration_horizon(p,[t],10)
    assert c.concentration_horizon(p,[t,t,t],10)<base<10
    p.features["war_caster"]=True
    assert base<c.concentration_horizon(p,[t],10)
    t.attacks=[]; t.multiattack=[]
    assert c.concentration_horizon(p,[t],10)==10


@pytest.mark.parametrize("policy",[Policy,NovaPolicy,ConservativePolicy,RationedPolicy])
def test_paladin_buffs_respect_allow_spell(spells,monkeypatch,policy):
    c,p,allies,t=buff_fight(spells)
    c.policy=policy()
    monkeypatch.setattr(c.policy,"allow_spell",lambda *args:False)
    c.policy.take_turn(c,p)
    assert not any(e["event"]=="cast" for e in c.log)
    assert any(e["event"]=="attack" for e in c.log)


@pytest.mark.parametrize("name",["fighter","rogue","cleric","wizard","barbarian"])
def test_non_paladin_buff_choices_unchanged(spells,monkeypatch,name):
    actor=pc(name); actor.spells=["Bless"]; actor.spell_slots={1:2}
    t=Combatant("t",max_hp=10000)
    c=Combat([actor,t],spells,seed=7); c.begin_turn(actor)
    def unexpected(*args,**kwargs): pytest.fail("non-paladin used new buff valuation")
    monkeypatch.setattr(c,"expected_buff_value",unexpected)
    c.policy.take_turn(c,actor)
    assert not any(e["event"]=="cast" and e["spell"]=="Bless" for e in c.log)
    if name=="cleric":
        assert any(e["event"]=="action" and e["name"]=="Divine Spark (Radiant)" for e in c.log)
    else: assert any(e["event"]=="attack" for e in c.log)


def test_bonus_action_buff_pays_for_the_smite_it_gives_up(spells):
    c,p,allies,t=buff_fight(spells,hp=60)
    p.spells=["Magic Weapon","Divine Smite"]
    forgone=c.policy.smite_forgone(c,p,t)
    assert forgone>0
    c.policy.take_turn(c,p)
    casts=[e["spell"] for e in c.log if e["event"]=="cast"]
    assert "Magic Weapon" not in casts  # a short fight: the smite is worth more
    p.spell_slots={k:0 for k in p.spell_slots}; p.limited_uses["paladins_smite"]=0
    assert c.policy.smite_forgone(c,p,t)==0  # nothing left to smite with
