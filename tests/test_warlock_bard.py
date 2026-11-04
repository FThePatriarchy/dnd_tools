"""XPHB Fiend and Lore progression, builds and deterministic combat hooks."""
from copy import deepcopy
import random

import pytest

from engine import Combat, Combatant, dice
from engine.builder import build, load_build, EQUIPMENT, spell_options
from engine.class_catalog import declaration
from engine.classes import load_class
from engine.class_source import check_class_source
from engine.compare import ROLES, variants
from engine.day import take_rest, ClockRest
from engine.loader import ROOT, load_spells, read_yaml, ValidationError
from engine.policy import Policy
from engine.sheets import validate_sheet

LEVELS=(1,3,5,7,10)
BUILDS=[f"{name}_{level}{profile}" for name in ("warlock","bard") for level in LEVELS for profile in ("","_casual","_optimized")]


@pytest.fixture(scope="module")
def spells(): return load_spells()


def pc(name="warlock",level=5,**kwargs):
    return Combatant.from_sheet(build(name,level,**kwargs),name,"party")


def fixed(combat,monkeypatch,natural=10,die=1):
    monkeypatch.setattr(dice,"d20",lambda *a,**k:natural)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b:die)


@pytest.mark.parametrize("name",BUILDS)
def test_all_builds(name,spells):
    r=read_yaml(ROOT/"builds"/(name+".yaml")); s=load_build(name); validate_sheet(s,name)
    level=r["level"]; mod=lambda a:(s["abilities"][a]-10)//2
    assert s["max_hp"]==8+(level-1)*5+level*mod("con")
    armor,shield,_=EQUIPMENT[r["equipment"]]
    assert not shield
    assert s["ac"]==(13 if r["class"]=="warlock" else 12)+mod("dex")
    pb=2+(level-1)//4
    assert s["spell_ability"]=="cha" and s["spell_dc"]==8+pb+mod("cha")
    assert s["spell_attack_bonus"]==pb+mod("cha")
    for a in s["attacks"]: assert a["to_hit"]==pb+mod(a["ability"])
    if r["class"]=="warlock":
        pact=min(5,(level+1)//2)
        assert s["spell_slots"]=={pact:1 if level==1 else 2}
        assert len(s["prepared_spells"])=={1:2,3:4,5:6,7:8,10:10}[level]
    else:
        assert s["spell_slots"]=={1:{1:2},3:{1:4,2:2},5:{1:4,2:3,3:2},7:{1:4,2:3,3:3,4:1},10:{1:4,2:3,3:3,4:3,5:2}}[level]
        assert len(s["prepared_spells"])=={1:4,3:6,5:9,7:11,10:15}[level]
    assert all(n in spells for n in s["spells"])
    assert s["features"]["values_buffs"]


@pytest.mark.parametrize("name",["warlock","bard"])
def test_source_tables_and_mutants(name):
    c=load_class(name)
    assert c==declaration(name) and check_class_source(c)>0
    for field in ("prepared","cantrips","slots"):
        bad=deepcopy(c)
        if field=="slots": bad["levels"][5][field][3]+=1
        else: bad["levels"][5][field]+=1
        with pytest.raises(ValidationError): check_class_source(bad)


@pytest.mark.parametrize("level",LEVELS)
def test_pact_slots_cast_at_pact_level_and_recover(spells,level,monkeypatch):
    w=pc(level=level); t=Combatant("t",max_hp=500); c=Combat([w,t],spells); c.begin_turn(w)
    fixed(c,monkeypatch)
    inst=c.cast(w,"Armor of Agathys")
    pact=min(5,(level+1)//2)
    assert inst.slot==pact and w.temp_hp==5*pact
    take_rest([w],"short",c.rng)
    assert w.spell_slots==w.max_spell_slots
    w.spell_slots[pact]=0
    take_rest([w],"short",c.rng)
    assert w.spell_slots[pact]==w.max_spell_slots[pact]
    w.spell_slots[pact]=0
    take_rest([w],"long",c.rng)
    assert w.spell_slots==w.max_spell_slots


def test_clocked_short_rest_and_no_cunning(spells):
    w=pc(); c=Combat([w],spells); w.spell_slots[3]=0
    assert "magical_cunning" not in w.limited_uses
    rest=ClockRest(c,[w],"short"); c.advance_time(600); rest.finish()
    assert w.spell_slots=={3:2}


@pytest.mark.parametrize("level,beams",[(1,1),(3,1),(5,2),(7,2),(10,2)])
def test_eldritch_blast_beams_and_agonizing_per_hit(spells,monkeypatch,level,beams):
    w=pc(level=level); t=Combatant("t",max_hp=500); c=Combat([w,t],spells); c.begin_turn(w)
    fixed(c,monkeypatch)
    spec=c.scale(w,spells["Eldritch Blast"],0)
    assert spec["effects"][0]["target"]["n"]==beams
    c.cast(w,"Eldritch Blast",targets=[t]*beams)
    assert t.hp==500-beams*(1+(w.mod("cha") if level>=2 else 0))
    assert spells["Eldritch Blast"]["effects"][0]["on_hit"][0]["damage"]["bonus"]==0
    assert c.expected_spell_damage(w,spec,t)>0


def test_invocation_validation_and_concentration_advantage(spells,monkeypatch):
    with pytest.raises(ValidationError): build("warlock",1,choices={"invocations":["agonizing_blast"]})
    with pytest.raises(ValidationError): build("warlock",5,choices={"invocations":["unknown"]})
    w=pc(); c=Combat([w],spells); flags=[]
    monkeypatch.setattr(dice,"d20",lambda rng,adv=False,dis=False:(flags.append(adv) or 10))
    c.saving_throw(w,"con",10,concentration=True); assert flags==[True]
    flags.clear(); c.saving_throw(w,"con",10); assert flags==[False]
    assert build("warlock",1,choices={"invocations":[]})["ac"]==12


def test_dark_blessing_kill_not_damage_and_no_stacking(spells):
    w=pc(); t=Combatant("t",hp=2); c=Combat([w,t],spells)
    c.damage(t,1,"force",w); assert not w.temp_hp
    c.damage(t,1,"force",w); assert w.temp_hp==w.level+w.mod("cha")
    w.temp_hp=50; t.hp=1; c.damage(t,1,"force",w); assert w.temp_hp==50
    w.temp_hp=0; c.damage(t,1,"force",w); assert w.temp_hp==0


@pytest.mark.parametrize("kind",["save","check"])
def test_luck_only_recoverable_failures_and_long_rest(spells,monkeypatch,kind):
    w=pc(level=7); c=Combat([w],spells); fixed(c,monkeypatch,natural=5,die=10)
    roll=lambda dc:c.saving_throw(w,"str",dc) if kind=="save" else c.ability_check(w,"str",dc)
    uses=w.limited_uses["dark_ones_own_luck"]
    assert not roll(30) and w.limited_uses["dark_ones_own_luck"]==uses
    assert roll(10) and w.limited_uses["dark_ones_own_luck"]==uses-1
    assert roll(1) and w.limited_uses["dark_ones_own_luck"]==uses-1
    take_rest([w],"short",c.rng); assert w.limited_uses["dark_ones_own_luck"]==uses-1
    take_rest([w],"long",c.rng); assert w.limited_uses["dark_ones_own_luck"]==uses


def test_luck_failed_d10_is_still_spent(spells,monkeypatch):
    w=pc(level=7); c=Combat([w],spells); fixed(c,monkeypatch,natural=5)
    uses=w.limited_uses["dark_ones_own_luck"]
    assert not c.saving_throw(w,"str",10)
    assert w.limited_uses["dark_ones_own_luck"]==uses-1


def test_fiend_resilience(spells):
    w=pc(level=10); c=Combat([w],spells); before=w.hp
    c.damage(w,9,"slashing"); assert w.hp==before-4
    c.damage(w,9,"piercing"); assert w.hp==before-13
    assert not build("warlock",7).get("resistances")


@pytest.mark.parametrize("level,die",[(1,6),(3,6),(5,8),(7,8),(10,10)])
@pytest.mark.parametrize("kind",["attack","save","check"])
def test_inspiration_after_failed_test(spells,monkeypatch,level,die,kind):
    b=pc("bard",level); a=Combatant("a",team="party"); t=Combatant("t",ac=12); c=Combat([b,a,t],spells); c.begin_turn(b)
    fixed(c,monkeypatch,natural=10,die=2)
    assert c.inspire(b,a) and not b.bonus_action
    assert a.statuses["bardic_inspiration"]["die"]==die
    if kind=="attack": assert c.attack(a,t,0,lambda *args:None)
    elif kind=="save": assert c.saving_throw(a,"str",12)
    else: assert c.ability_check(a,"str",12)
    assert "bardic_inspiration" not in a.statuses


def test_inspiration_kept_on_success_impossible_and_expired(spells,monkeypatch):
    b=pc("bard"); a=Combatant("a",team="party"); c=Combat([b,a],spells); c.begin_turn(b); fixed(c,monkeypatch)
    assert c.inspire(b,a)
    assert c.saving_throw(a,"str",10) and "bardic_inspiration" in a.statuses
    assert not c.saving_throw(a,"str",30) and "bardic_inspiration" in a.statuses
    c.time_rounds=600
    assert not c.saving_throw(a,"str",12) and "bardic_inspiration" not in a.statuses


@pytest.mark.parametrize("level",[1,3,5,7,10])
def test_font_recovery(spells,level):
    b=pc("bard",level); uses=b.limited_uses["bardic_inspiration"]; b.limited_uses["bardic_inspiration"]=0
    take_rest([b],"short",random.Random(1)); assert b.limited_uses["bardic_inspiration"]==(uses if level>=5 else 0)
    b.limited_uses["bardic_inspiration"]=0
    take_rest([b],"long",random.Random(1)); assert b.limited_uses["bardic_inspiration"]==uses


def test_2024_simple_weapon_training():
    for name in ("warlock","bard"):
        for equipment in ("studded_rapier","chain_greatsword"):
            with pytest.raises(ValidationError): build(name,5,equipment=equipment)
        assert build(name,5,equipment="studded_staff")["features"]["armored"]


def test_jack_initiative_and_discoveries_secrets():
    for level in range(1,11):
        s=build("bard",level)
        assert s.get("initiative_bonus",0)==(s["proficiency_bonus"]//2 if level>=2 else 0)
        assert ("Spirit Guardians" in s["spells"])==(level>=6)
        assert "Spirit Guardians" not in s["prepared_spells"]
    assert "Fireball" not in spell_options("bard",7) and "Fireball" in spell_options("bard",10)
    assert "Moonbeam" in spell_options("bard",10) and "Fire Bolt" not in spell_options("bard",10)
    for profile in ("","_optimized"):
        assert "Fireball" in load_build("bard_10"+profile)["prepared_spells"]
    with pytest.raises(ValidationError): build("bard",5,choices={"magical_discoveries":["Shield","Fireball"]})
    with pytest.raises(ValidationError): build("bard",7,choices={"magical_discoveries":["Shield","Cone of Cold"]})
    s=build("bard",7,choices={"magical_discoveries":["Shield","Moonbeam"]})
    assert "Shield" in s["spells"] and "Moonbeam" in s["spells"]
    assert build("bard",5,choices={"origin_feat":"alert"})["initiative_bonus"]==4


@pytest.mark.parametrize("natural,bonus,prevented",[(10,2,True),(10,20,False),(20,0,False)])
def test_cutting_words_hit_margin_and_critical(spells,monkeypatch,natural,bonus,prevented):
    b=pc("bard",5); a=Combatant("a",team="party",ac=12,hp=1); e=Combatant("e"); c=Combat([b,a,e],spells)
    fixed(c,monkeypatch,natural=natural,die=2)
    uses=b.limited_uses["bardic_inspiration"]
    assert c.attack(e,a,bonus,lambda *args:None)==(not prevented)
    assert b.limited_uses["bardic_inspiration"]==uses-int(prevented)
    assert b.reaction==1-int(prevented)


def test_cutting_words_check_and_damage_modes(spells,monkeypatch):
    b=pc("bard"); e=Combatant("e"); c=Combat([b,e],spells); fixed(c,monkeypatch,natural=10,die=3)
    assert not c.ability_check(e,"str",10) and b.reaction==0
    c.begin_turn(b)
    assert c.cutting_words(e,12)==9 and b.reaction==0


def test_cutting_words_critical_damage_and_reserve_low_hp(spells,monkeypatch):
    b=pc("bard"); a=Combatant("a",team="party",hp=1); healthy=Combatant("h",team="party"); e=Combatant("e"); c=Combat([b,a,healthy,e],spells)
    fixed(c,monkeypatch,natural=10,die=3); b.limited_uses["bardic_inspiration"]=1
    assert c.cutting_words(e,10,10,healthy)==10
    assert c.cutting_words(e,10,10,a)==7
    c.begin_turn(b); b.limited_uses["bardic_inspiration"]=1; fixed(c,monkeypatch,natural=20,die=3)
    c.attack(e,a,0,lambda *args:c.damage(a,10,"slashing",e))
    assert next(x for x in c.log if x["event"]=="damage")["amount"]==7


def test_cutting_words_reaction_visibility_and_incapacitation(spells):
    b=pc("bard"); e=Combatant("e",visible=False); c=Combat([b,e],spells)
    assert c.cutting_words(e,10,10)==10
    e.visible=True; b.conditions.add("incapacitated"); assert c.cutting_words(e,10,10)==10
    b.conditions.clear(); b.reaction=0; assert c.cutting_words(e,10,10)==10


def test_ai_hex_then_blast_no_slots_blast_and_leveled_aoe(spells,monkeypatch):
    w=pc(); w.spells=["Hex","Eldritch Blast"]; t=Combatant("t",max_hp=500); c=Combat([w,t],spells); c.begin_turn(w); fixed(c,monkeypatch)
    c.policy.take_turn(c,w)
    assert [x["spell"] for x in c.log if x["event"]=="cast"]==["Hex","Eldritch Blast"]
    c.begin_turn(w); c.policy.take_turn(c,w)
    assert [x["spell"] for x in c.log if x["event"]=="cast"][-1]=="Eldritch Blast"
    w.spell_slots={3:0}; c.begin_turn(w); c.policy.take_turn(c,w)
    assert [x["spell"] for x in c.log if x["event"]=="cast"][-1]=="Eldritch Blast"
    w=pc(); w.spells=["Fireball","Eldritch Blast"]; enemies=[Combatant(str(i),max_hp=500) for i in range(4)]
    c=Combat([w,*enemies],spells); c.begin_turn(w); fixed(c,monkeypatch); c.policy.take_turn(c,w)
    assert any(x.get("spell")=="Fireball" and x["event"]=="cast" for x in c.log)


def test_bard_ai_heals_down_then_inspires_most_attacks(spells,monkeypatch):
    b=pc("bard"); b.spells=["Healing Word","Vicious Mockery"]; f=pc("fighter"); a=Combatant("a",team="party",hp=0); t=Combatant("t",max_hp=500); c=Combat([b,f,a,t],spells); c.begin_turn(b); fixed(c,monkeypatch)
    c.policy.take_turn(c,b)
    assert a.hp>0 and "bardic_inspiration" not in f.statuses
    b.spells=["Vicious Mockery"]; c.begin_turn(b); c.policy.take_turn(c,b)
    assert "bardic_inspiration" in f.statuses and "bardic_inspiration" not in b.statuses


@pytest.mark.parametrize("name",["warlock","bard"])
def test_new_buff_flags_and_no_smite_cost(spells,monkeypatch,name):
    a=pc(name); a.spells=["Heroism"]; ally=pc("fighter"); t=Combatant("t",max_hp=500); c=Combat([a,ally,t],spells); c.begin_turn(a)
    calls=[]
    monkeypatch.setattr(c,"expected_buff_value",lambda *args,**kwargs:(calls.append(True) or 100))
    monkeypatch.setattr(c.policy,"smite_slot_cost",lambda *args:pytest.fail("new class charged for smite"))
    monkeypatch.setattr(c.policy,"smite_forgone",lambda *args:pytest.fail("new class charged for smite"))
    c.policy.take_turn(c,a)
    assert calls and any(x.get("spell")=="Heroism" for x in c.log)
    # Since 2026-11-02 every class values buffs, the reference cleric and wizard included.
    assert build("cleric",5)["features"].get("values_buffs")
    assert build("wizard",5)["features"].get("values_buffs")


def test_compare_roles_and_variants():
    assert ROLES["warlock"]=="wizard" and ROLES["bard"]=="cleric"
    for name in ("warlock","bard"):
        options=variants(name,5)
        assert options[0]["name"]=="standard" and any("feat:" in x["name"] for x in options)
        assert any("spells" in x["name"] for x in options)
        if name=="warlock": assert any("invocations:" in x["name"] for x in options)


def test_inspiration_does_not_stack_and_see_or_hear(spells):
    b=pc("bard"); a=Combatant("a",team="party"); c=Combat([b,a],spells); c.begin_turn(b)
    a.conditions.add("deafened")
    assert c.inspire(b,a)
    uses=b.limited_uses["bardic_inspiration"]; c.begin_turn(b)
    assert not c.inspire(b,a) and b.limited_uses["bardic_inspiration"]==uses
    a.statuses.clear(); a.conditions.add("blinded")
    assert not c.inspire(b,a) and b.limited_uses["bardic_inspiration"]==uses


def test_inspiration_consumed_on_failed_die_and_not_natural_one(spells,monkeypatch):
    b=pc("bard"); a=Combatant("a",team="party"); t=Combatant("t",ac=12); c=Combat([b,a,t],spells); c.begin_turn(b)
    assert c.inspire(b,a); fixed(c,monkeypatch,natural=1)
    assert not c.attack(a,t,20,lambda *args:None) and "bardic_inspiration" in a.statuses
    fixed(c,monkeypatch,natural=10)
    assert not c.saving_throw(a,"str",12) and "bardic_inspiration" not in a.statuses


def test_bard_ai_control_and_damage(spells,monkeypatch):
    for name in ("Hypnotic Pattern","Shatter"):
        b=pc("bard"); b.spells=[name,"Vicious Mockery"]; enemies=[Combatant(str(i),max_hp=500,attacks=[{"name":"Club","kind":"melee","to_hit":6,"effects":[{"damage":{"dice":"2d6","bonus":4,"type":"bludgeoning"}}]}]) for i in range(4)]
        c=Combat([b,*enemies],spells); c.begin_turn(b); fixed(c,monkeypatch)
        c.policy.take_turn(c,b)
        assert any(e.get("spell")==name for e in c.log)


def test_hex_rider_per_beam(spells,monkeypatch):
    w=pc(); t=Combatant("t",max_hp=500); c=Combat([w,t],spells); c.begin_turn(w); fixed(c,monkeypatch)
    c.cast(w,"Hex",targets=[t]); c.cast(w,"Eldritch Blast",targets=[t,t])
    assert t.hp==500-2*(1+w.mod("cha")+1)


def test_reference_casters_evaluate_buffs(spells,monkeypatch):
    # Until 2026-11-02 the cleric and wizard skipped buff valuation to keep old baselines.
    for name in ("cleric","wizard"):
        a=pc(name); a.spells=["Bless"]; t=Combatant("t"); c=Combat([a,t],spells); c.begin_turn(a)
        calls=[]
        monkeypatch.setattr(c,"expected_buff_value",lambda *args,**kwargs:(calls.append(True) or 0))
        c.policy.take_turn(c,a)
        assert calls, name
