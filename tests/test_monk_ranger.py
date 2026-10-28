"""XPHB Open Hand / Hunter builds and deterministic feature boundaries."""
from copy import deepcopy
import random

import pytest

from engine import Combat, Combatant, dice
from engine.builder import build, load_build, EQUIPMENT
from engine.class_catalog import declaration
from engine.classes import load_class
from engine.class_source import check_class_source
from engine.compare import ROLES, variants
from engine.day import take_rest
from engine.loader import ROOT, load_spells, read_yaml, ValidationError
from engine.policy import RationedPolicy
from engine.sheets import validate_sheet, effect_block

LEVELS=(1,3,5,7,10)
BUILDS=[f"{name}_{level}{profile}" for name in ("monk","ranger") for level in LEVELS for profile in ("","_casual","_optimized")]


@pytest.fixture(scope="module")
def spells(): return load_spells()


def pc(name="monk",level=5,**kwargs):
    return Combatant.from_sheet(build(name,level,**kwargs),name,"party")


def fixed(c,monkeypatch,natural=10,die=1):
    monkeypatch.setattr(dice,"d20",lambda *a,**k:natural)
    monkeypatch.setattr(c.rng,"randint",lambda a,b:die)


def armed(name="t",**kwargs):
    return Combatant(name,attacks=[{"name":"Club","kind":"melee","to_hit":6,"effects":[{"damage":{"dice":"1d6","bonus":2,"type":"bludgeoning"}}]}],**kwargs)


@pytest.mark.parametrize("name",BUILDS)
def test_all_builds(name,spells):
    r=read_yaml(ROOT/"builds"/(name+".yaml")); s=load_build(name); validate_sheet(s,name)
    level=r["level"]; mod=lambda a:(s["abilities"][a]-10)//2
    monk=r["class"]=="monk"; faces=8 if monk else 10; pb=2+(level-1)//4
    assert s["max_hp"]==faces+(level-1)*(faces//2+1)+level*mod("con")
    assert s["ac"]==(10+mod("dex")+mod("wis") if monk else 12+mod("dex"))
    assert s["spell_dc"]==8+pb+mod("wis")
    for a in s["attacks"]: assert a["to_hit"]==pb+mod(a["ability"])+(2 if not monk and level>=2 else 0)
    assert s.get("extra_attack",1)==(2 if level>=5 else 1)
    assert s["features"]["values_buffs"]
    if monk:
        assert s["limited_uses"].get("focus",{}).get("max",0)==(level if level>=2 else 0)
        assert not s.get("spell_slots")
        strike=s["attacks"][-1]["effects"][0]["damage"]
        assert strike["dice"]==("1d8" if level>=5 else "1d6")
        assert strike["type"]==("force" if level>=6 else "bludgeoning")
    else:
        assert s["spell_slots"]=={1:{1:2},3:{1:3},5:{1:4,2:2},7:{1:4,2:3},10:{1:4,2:3,3:2}}[level]
        assert len(s["prepared_spells"])=={1:2,3:4,5:6,7:7,10:9}[level]
        assert s["spell_ability"]=="wis" and s["spell_attack_bonus"]==pb+mod("wis")
        assert s["limited_uses"]["favored_enemy"]["max"]==(2 if level<5 else 3 if level<9 else 4)
        assert "Hunter's Mark" in s["spells"] and "Hunter's Mark" not in s["prepared_spells"]
        assert all(n in spells for n in s["spells"])


@pytest.mark.parametrize("name",["monk","ranger"])
def test_source_inventory_and_mutants(name):
    c=load_class(name)
    assert c==declaration(name) and check_class_source(c)>0
    for field in ("prepared","weapon_masteries","resources"):
        bad=deepcopy(c)
        if field=="resources": bad["levels"][5][field]["focus" if name=="monk" else "favored_enemy"]["max"]+=1
        else: bad["levels"][5][field]+=1
        with pytest.raises(ValidationError): check_class_source(bad)


@pytest.mark.parametrize("level,attacks",[(1,2),(3,3),(5,4),(7,4),(10,5)])
def test_attack_and_bonus_routines(spells,monkeypatch,level,attacks):
    m=pc(level=level); t=Combatant("t",max_hp=500); c=Combat([m,t],spells); c.begin_turn(m); fixed(c,monkeypatch)
    c.weapon_action(m)
    assert c.monk_bonus(m,flurry=level>=2)
    assert len([e for e in c.log if e["event"]=="attack"])==attacks
    assert not m.action and not m.bonus_action
    assert m.limited_uses.get("focus",0)==(level-1 if level>=2 else 0)
    assert not c.monk_bonus(m)


def test_unarmored_defense_and_training():
    for equipment in ("chain_shield","scale_shield","studded_staff","unarmored_greatsword"):
        with pytest.raises(ValidationError): build("monk",5,equipment=equipment)
    with pytest.raises(ValidationError): build("ranger",5,equipment="chain_greatsword")
    assert build("monk",5)["attacks"][0]["ability"]=="dex"
    assert len(build("ranger",5,choices={"weapon_masteries":["longbow","longsword"]})["attacks"])==1
    with pytest.raises(ValidationError): build("ranger",5,choices={"weapon_masteries":["longbow","longsword","mace"]})


def test_focus_metabolism_and_rests(spells,monkeypatch):
    m=pc(); c=Combat([m],spells); fixed(c,monkeypatch); m.hp=1; m.limited_uses["focus"]=0
    c.monk_initiative(m)
    assert m.hp==7 and m.limited_uses["focus"]==5 and m.limited_uses["uncanny_metabolism"]==0
    m.limited_uses["focus"]=0; c.monk_initiative(m); assert m.hp==7 and m.limited_uses["focus"]==0
    take_rest([m],"short",c.rng); assert m.limited_uses["focus"]==5 and not m.limited_uses["uncanny_metabolism"]
    take_rest([m],"long",c.rng); assert m.limited_uses["uncanny_metabolism"]==1


def test_metabolism_actual_initiative(spells,monkeypatch):
    m=pc(); c=Combat([m],spells); fixed(c,monkeypatch); m.hp=1; m.limited_uses["focus"]=0
    c.run()
    assert m.hp==7 and m.limited_uses["focus"]==5


@pytest.mark.parametrize("dtype,amount,remaining",[("slashing",20,10),("force",20,20),("piercing",4,0)])
def test_deflect_attack_packet(spells,monkeypatch,dtype,amount,remaining):
    m=pc(); e=armed(); c=Combat([m,e],spells); c.begin_turn(e); fixed(c,monkeypatch); hp=m.hp
    c.attack(e,m,100,lambda *a:c.damage(m,amount,dtype,e))
    assert m.hp==hp-remaining and m.reaction==int(dtype=="force")
    c.damage(m,3,"slashing",e); assert m.hp==hp-remaining-3
    assert m.limited_uses["focus"]==5  # redirect is deliberately omitted


def test_patient_defense_expiry_and_ai(spells,monkeypatch):
    m=pc(); e=armed(); c=Combat([m,e],spells); c.begin_turn(m); fixed(c,monkeypatch); m.hp=1; m.features["stunning_strike"]=False
    c.policy.take_turn(c,m)
    assert m.has_status("monk_dodge") and c.roll_flags(e,"attack_rolls",against=m)==(False,True)
    assert c.roll_flags(m,"saves","dex")== (True,False)
    assert m.limited_uses["focus"]==4 and not m.bonus_action
    c.end_turn(m); c.begin_turn(e); assert m.has_status("monk_dodge")
    c.begin_turn(m); assert not m.has_status("monk_dodge")
    points=m.limited_uses["focus"]; assert c.patient_defense(m) and m.limited_uses["focus"]==points
    assert m.has_status("disengaged") and not m.has_status("monk_dodge")


@pytest.mark.parametrize("success",[False,True])
def test_stun_once_and_exact_boundary(spells,monkeypatch,success):
    m=pc(); e=armed(max_hp=500); c=Combat([m,e],spells); c.begin_turn(m); fixed(c,monkeypatch)
    monkeypatch.setattr(c,"saving_throw",lambda *a,**k:success)
    c.weapon_attack(m,e,m.attacks[0]); c.weapon_attack(m,e,m.attacks[0])
    assert m.limited_uses["focus"]==4
    assert len([x for x in c.log if x.get("name")=="Stunning Strike"])==1
    assert e.has_condition("stunned")== (not success)
    if success:
        assert c.modifier(e,"speed",30)==15
        # The second strike used the single granted advantage.
        assert [x for x in c.log if x["event"]=="attack"][-1]["advantage"]
        assert not c.roll_flags(m,"attack_rolls",against=e)[0]
    c.begin_turn(e); assert e.has_condition("stunned")== (not success)
    c.begin_turn(m); assert not e.has_condition("stunned") and c.modifier(e,"speed",30)==30


def test_stun_ai_target_quality_and_day_rationing(spells,monkeypatch):
    m=pc(level=10); e=armed(max_hp=500); c=Combat([m,e],spells,policy=RationedPolicy()); c.encounters_until_rest=5; c.begin_turn(m); fixed(c,monkeypatch)
    monkeypatch.setattr(c,"expected_remaining_rounds",lambda a:3)
    e.save_bonuses["con"]=20; assert not c.policy.stunning_strike(c,m,e)
    e.save_bonuses["con"]=0; e.condition_immunities=["stunned"]; assert not c.policy.stunning_strike(c,m,e)
    e.condition_immunities=[]; e.hp=5; assert not c.policy.stunning_strike(c,m,e)
    e.hp=500; assert c.policy.stunning_strike(c,m,e)
    for _ in range(5):
        c.policy.take_turn(c,m); c.end_turn(m); c.begin_turn(m)
    assert m.limited_uses["focus"]>=8
    assert any(x.get("name")=="Stunning Strike" for x in c.log)


@pytest.mark.parametrize("addle",[False,True])
def test_open_hand_only_flurry(spells,monkeypatch,addle):
    m=pc(level=3,choices={"open_hand":"addle" if addle else "topple"}); e=armed(max_hp=500); c=Combat([m,e],spells); c.begin_turn(m); fixed(c,monkeypatch,natural=1)
    monkeypatch.setattr(dice,"d20",lambda *a,**k:10)
    monkeypatch.setattr(c,"saving_throw",lambda *a,**k:False)
    c.weapon_action(m); assert not e.has_condition("prone") and not e.has_status("no_opportunity_attacks")
    c.monk_bonus(m,flurry=True)
    assert not c.turn_rules(e).get("no_reactions")
    assert e.has_status("no_opportunity_attacks")==addle
    assert e.has_condition("prone")== (not addle)


def test_wholeness_and_self_restoration(spells,monkeypatch):
    m=pc(level=10); c=Combat([m],spells); c.begin_turn(m); fixed(c,monkeypatch); m.hp=1
    uses=m.limited_uses["wholeness_of_body"]
    assert c.wholeness(m) and m.hp==4 and m.limited_uses["wholeness_of_body"]==uses-1
    assert not c.wholeness(m)
    m.conditions.update({"charmed","frightened","poisoned"}); c.end_turn(m)
    assert "charmed" not in m.conditions and {"frightened","poisoned"}<=m.conditions
    take_rest([m],"short",c.rng); assert m.limited_uses["wholeness_of_body"]==uses-1
    take_rest([m],"long",c.rng); assert m.limited_uses["wholeness_of_body"]==uses


@pytest.mark.parametrize("success,damage",[(False,5),(True,0)])
def test_evasion(spells,monkeypatch,success,damage):
    m=pc(level=7); e=armed(); c=Combat([m,e],spells); fixed(c,monkeypatch)
    monkeypatch.setattr(c,"saving_throw",lambda *a,**k:success)
    b=effect_block("test",target={"select":"single","filter":["creature"],"affects":"enemy"},save={"ability":"dex","dc":12,"on_success":"half"},on_fail=[{"damage":{"amount":10,"type":"fire"}}])
    inst=c.monster_instance(e,"test",[b]); hp=m.hp
    c.resolve_block(inst,b,"on_cast",{},[m]); assert m.hp==hp-damage


def test_mark_free_casts_fallback_retarget_and_rider(spells,monkeypatch):
    r=pc("ranger"); a=armed("a",max_hp=50); b=armed("b",max_hp=500); c=Combat([r,a,b],spells); c.begin_turn(r); fixed(c,monkeypatch)
    slots=r.spell_slots.copy(); uses=r.limited_uses["favored_enemy"]
    inst=c.cast(r,"Hunter's Mark",targets=[a]); assert inst and r.spell_slots==slots and r.limited_uses["favored_enemy"]==uses-1
    c.weapon_attack(r,a,r.attacks[0]); assert a.hp==44 # 1 bow + 4 Dex + 1 mark; full-health target has no Slayer
    c.damage(a,100,"force",r); c.begin_turn(r)
    assert c.command(inst,"bonus_action_command")
    assert not r.bonus_action and r.spell_slots==slots and r.limited_uses["favored_enemy"]==uses-1
    c.weapon_attack(r,b,r.attacks[0]); assert b.hp==494
    c.end_spell(inst.id); r.limited_uses["favored_enemy"]=0; c.begin_turn(r)
    assert c.cast(r,"Hunter's Mark",targets=[b]) and r.spell_slots[1]==slots[1]-1
    take_rest([r],"short",c.rng); assert not r.limited_uses["favored_enemy"]
    take_rest([r],"long",c.rng); assert r.limited_uses["favored_enemy"]==uses


def test_ranger_ai_mark_and_attack_no_slots(spells,monkeypatch):
    r=pc("ranger"); r.spells=["Hunter's Mark"]; r.spell_slots={1:0,2:0}; e=armed(max_hp=500); c=Combat([r,e],spells,policy=RationedPolicy()); c.begin_turn(r); fixed(c,monkeypatch)
    c.policy.take_turn(c,r)
    assert any(x["event"]=="cast" and x.get("spell")=="Hunter's Mark" for x in c.log)
    assert len([x for x in c.log if x["event"]=="attack"])==2


def test_colossus_once_critical_and_horde(spells,monkeypatch):
    r=pc("ranger"); e=armed(max_hp=500); c=Combat([r,e],spells); c.begin_turn(r); fixed(c,monkeypatch,natural=20)
    c.weapon_attack(r,e,r.attacks[0]); assert e.hp==494 # no Slayer on a full-health hit
    c.weapon_attack(r,e,r.attacks[0]); assert e.hp==486 # critical Slayer 2 + bow 2 + Dex 4
    c.weapon_attack(r,e,r.attacks[0]); assert e.hp==480
    r=pc("ranger",choices={"hunters_prey":"horde_breaker"}); a=armed("a",max_hp=500); b=armed("b",max_hp=500); c=Combat([r,a,b],spells); c.begin_turn(r); fixed(c,monkeypatch,natural=1)
    c.weapon_action(r)
    attacks=[x for x in c.log if x["event"]=="attack"]
    assert len(attacks)==3 and attacks[0]["defender"]!=attacks[1]["defender"]


def test_multiattack_defense_same_attacker_this_turn_only(spells,monkeypatch):
    r=pc("ranger",7); a=armed("a"); b=armed("b"); c=Combat([r,a,b],spells); c.begin_turn(a); fixed(c,monkeypatch)
    c.attack(a,r,100,lambda *args:None)
    assert c.roll_flags(a,"attack_rolls",against=r)==(False,True)
    assert c.roll_flags(b,"attack_rolls",against=r)==(False,False)
    c.begin_turn(b); assert c.roll_flags(a,"attack_rolls",against=r)==(False,False)


def test_compare_variants_and_roles():
    assert ROLES["monk"]=="rogue" and ROLES["ranger"]=="fighter"
    for name in ("monk","ranger"):
        for level in LEVELS:
            options=variants(name,level)
            assert options[0]["name"]=="standard" and any(x["name"]=="feat: alert" for x in options)
            for r in options: validate_sheet(build(r["class"],r["level"],r["subclass"],r["abilities"],r["equipment"],r["choices"]),"<variant>")
    assert any("sharpshooter" in r["name"] for r in variants("ranger",5))
    assert any("Horde Breaker" in r["name"] for r in variants("ranger",5))


def test_flurry_independent_bonus_and_empty_focus_fallback(spells,monkeypatch):
    m=pc(level=3); e=armed(max_hp=500); c=Combat([m,e],spells); c.begin_turn(m); fixed(c,monkeypatch)
    assert c.monk_bonus(m,flurry=True) and m.action==1
    c.begin_turn(m); m.limited_uses["focus"]=0
    assert not c.monk_bonus(m,flurry=True)
    assert c.monk_bonus(m) and not m.bonus_action and m.action==1  # XPHB: no Attack action prerequisite
    c.begin_turn(m); assert not c.patient_defense(m,dodge=True)
    assert c.patient_defense(m) and m.limited_uses["focus"]==0


def test_force_unarmed_and_mixed_deflect_packet(spells,monkeypatch):
    m=pc(level=7); m.features["stunning_strike"]=False
    e=armed(max_hp=500,resistances=["bludgeoning"]); c=Combat([m,e],spells); c.begin_turn(m); fixed(c,monkeypatch)
    c.weapon_attack(m,e,m.attacks[-1]); assert e.hp==495
    c.weapon_attack(m,e,m.attacks[0]); assert e.hp==493
    c.begin_turn(e); hp=m.hp
    def packet(*args):
        c.damage(m,5,"slashing",e)
        c.damage(m,20,"fire",e)
    c.attack(e,m,100,packet)
    assert m.hp==hp-(25-(1+m.mod("dex")+m.level)) and not m.reaction
    assert len([x for x in c.log if x.get("name")=="Deflect Attacks"])==1


def test_dodge_incapacitation_zero_speed_and_unseen_attacks(spells):
    m=pc(); e=armed(); c=Combat([m,e],spells); c.begin_turn(m); c.patient_defense(m,dodge=True)
    e.visible=False; assert not c.roll_flags(e,"attack_rolls",against=m)[1]
    e.visible=True; m.speed=0; assert not c.roll_flags(m,"saves","dex")[0]
    m.speed=30; m.conditions.add("incapacitated")
    assert not c.roll_flags(e,"attack_rolls",against=m)[1] and not c.roll_flags(m,"saves","dex")[0]


def test_open_hand_topples_reactive_enemy(spells,monkeypatch):
    m=pc(level=3); e=armed(max_hp=500,features={"parry":2}); c=Combat([m,e],spells); c.begin_turn(m); fixed(c,monkeypatch)
    monkeypatch.setattr(c,"saving_throw",lambda *a,**k:False)
    c.monk_bonus(m,flurry=True)
    assert not c.turn_rules(e).get("no_reactions") and e.has_condition("prone")


def test_stun_reserve_and_low_value_target(spells):
    m=pc(choices={"stunning_budget":"reserve"}); e=armed(max_hp=500); c=Combat([m,e],spells); c.begin_turn(m)
    assert c.policy.stunning_strike(c,m,e)  # exactly 60% failure chance
    e.save_bonuses["con"]=1; assert not c.policy.stunning_strike(c,m,e)
    e.save_bonuses["con"]=-2; assert c.policy.stunning_strike(c,m,e)
    m.features["stunning_reserve"]=False
    minion=armed("minion",max_hp=40); c.combatants.append(minion)
    assert not c.policy.stunning_strike(c,m,minion)


def test_self_restoration_effect_based_charm(spells,monkeypatch):
    m=pc(level=10); e=armed(spells=["Dominate Person"],spell_slots={5:1}); c=Combat([m,e],spells); c.begin_turn(e); fixed(c,monkeypatch,natural=1)
    inst=c.cast(e,"Dominate Person",targets=[m]); assert inst and m.team==e.team
    c.begin_turn(m); c.end_turn(m)
    assert not m.has_condition("charmed") and m.team=="party"


def test_mark_free_cast_does_not_use_slot_turn_and_explicit_upcast(spells,monkeypatch):
    r=pc("ranger"); e=armed(max_hp=500); c=Combat([r,e],spells); c.begin_turn(r); fixed(c,monkeypatch); r.hp=1
    assert c.cast(r,"Cure Wounds",targets=[r],slot=1)
    slots=r.spell_slots.copy(); uses=r.limited_uses["favored_enemy"]
    assert c.cast(r,"Hunter's Mark",targets=[e])
    assert r.spell_slots==slots and r.limited_uses["favored_enemy"]==uses-1
    c.begin_turn(r); assert c.cast(r,"Hunter's Mark",targets=[e],slot=2)
    assert r.spell_slots[2]==slots[2]-1 and r.limited_uses["favored_enemy"]==uses-1
    c.begin_turn(r); r.limited_uses["favored_enemy"]=0; r.spell_slots={1:0,2:0}
    assert not c.can_cast(r,"Hunter's Mark")
