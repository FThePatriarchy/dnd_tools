from copy import deepcopy
import random

import pytest

from engine import Combat, Combatant, dice
from engine.builder import build, load_build, EQUIPMENT
from engine.class_catalog import declaration
from engine.classes import load_class
from engine.class_source import check_class_source
from engine.compare import ROLES, variants
from engine.day import take_rest, cleanup_encounter
from engine.loader import ROOT, load_spells, read_yaml, ValidationError
from engine.sheets import validate_sheet

LEVELS=(1,3,5,7,10)
BUILDS=[f'{name}_{level}{profile}' for name in ('druid','sorcerer') for level in LEVELS for profile in ('','_casual','_optimized')]


@pytest.fixture(scope='module')
def spells(): return load_spells()


def pc(name='druid',level=5,**kwargs):
    return Combatant.from_sheet(build(name,level,**kwargs),name,'party')


def fight(spells,name='druid',level=5,**kwargs):
    actor=pc(name,level,**kwargs); target=Combatant('target',max_hp=500)
    combat=Combat([actor,target],spells,seed=1); combat.begin_turn(actor)
    return actor,target,combat


def fixed(combat,monkeypatch):
    monkeypatch.setattr(dice,'d20',lambda *a,**k:10)
    monkeypatch.setattr(combat.rng,'randint',lambda a,b:1)


@pytest.mark.parametrize('name',BUILDS)
def test_all_builds(name,spells):
    s=load_build(name); validate_sheet(s,name); raw=read_yaml(ROOT/'builds'/(name+'.yaml'))
    level=s['level']; druid=raw['class']=='druid'; faces=8 if druid else 6
    mod=lambda a:(s['abilities'][a]-10)//2
    assert s['max_hp']==faces+(level-1)*(faces//2+1)+level*mod('con')+(level if not druid and level>=3 else 0)
    armor,shield,_=EQUIPMENT[raw['equipment']]
    assert s['ac']==(14+min(2,mod('dex'))+2*shield if druid else 10+mod('dex')+(mod('cha') if level>=3 else 0))
    ability='wis' if druid else 'cha'
    assert s['spell_ability']==ability
    assert s['spell_attack_bonus']==s['proficiency_bonus']+mod(ability)
    assert s['spell_dc']==8+s['spell_attack_bonus']
    assert s['spell_slots']=={1:{1:2},3:{1:4,2:2},5:{1:4,2:3,3:2},7:{1:4,2:3,3:3,4:1},10:{1:4,2:3,3:3,4:3,5:2}}[level]
    assert len(s['prepared_spells'])==({1:4,3:6,5:9,7:11,10:15} if druid else {1:2,3:6,5:9,7:11,10:15})[level]
    uses=s['limited_uses']
    assert uses.get('wild_shape',{}).get('max',0)==((0 if level==1 else 2 if level<6 else 3) if druid else 0)
    assert uses.get('sorcery_points',{}).get('max',0)==(level if not druid and level>=2 else 0)
    assert s['features']['values_buffs'] and all(n in spells for n in s['spells'])
    if level>=3:
        domain=['Cure Wounds','Moonbeam','Starry Wisp'] if druid else ['Chromatic Orb','Command',"Dragon's Breath"]
        assert all(n in s['spells'] and n not in s['prepared_spells'] for n in domain)
    if not druid: assert len([k for k in ('quickened_spell','heightened_spell','careful_spell','extended_spell') if s['features'].get(k)])==(0 if level<2 else 2 if level<10 else 4)


@pytest.mark.parametrize('name',['druid','sorcerer'])
def test_source_and_mutants(name):
    c=load_class(name)
    assert c==declaration(name) and check_class_source(c)>0
    for field in ('prepared','cantrips','slots','resources'):
        bad=deepcopy(c)
        if field=='resources': bad['levels'][5][field]['wild_shape' if name=='druid' else 'sorcery_points']['max']+=1
        elif field=='slots': bad['levels'][5][field][1]+=1
        else: bad['levels'][5][field]+=1
        with pytest.raises(ValidationError): check_class_source(bad)


def test_primal_order_and_training():
    with pytest.raises(ValidationError): build('druid',5,choices={'primal_order':'magician'})
    assert build('druid',5,equipment='scale_sword_shield')['ac']>=16
    with pytest.raises(ValidationError): build('druid',5,equipment='leather_archer',choices={'primal_order':'magician'})
    s=build('druid',5,equipment='studded_staff',choices={'primal_order':'magician'})
    assert len([n for n in s['spells'] if n in ['Thorn Whip','Produce Flame','Guidance','Poison Spray']])==4
    for name in ('druid','sorcerer'):
        with pytest.raises(ValidationError): build(name,5,equipment='chain_shield')
    with pytest.raises(ValidationError): build('sorcerer',5,choices={'metamagic':['quickened_spell']})
    with pytest.raises(ValidationError): build('druid',5,choices={'metamagic':['quickened_spell','heightened_spell']})


@pytest.mark.parametrize('level,form',[(2,'wolf'),(3,'brown_bear'),(5,'dire_wolf'),(7,'giant_spider'),(10,'brown_bear')])
def test_shape_stats_uses_attacks_and_reversion(spells,monkeypatch,level,form):
    a,t,c=fight(spells,level=level); fixed(c,monkeypatch)
    original=deepcopy(a.abilities); ac=a.ac; attacks=deepcopy(a.attacks); hp=a.hp
    assert c.wild_shape(a,form)
    assert a.bonus_action==0 and a.action==1
    assert a.limited_uses['wild_shape']==a.max_limited_uses['wild_shape']-1
    assert all(a.abilities[x]==original[x] for x in ('int','wis','cha'))
    assert a.ac==(12 if level==2 else max(11 if form=='brown_bear' else 14,13+a.mod('wis')))
    assert a.temp_hp==level*(1 if level==2 else 3) and a.hp==hp
    assert c.weapon_action(a) and t.hp<500
    if level>=6:
        assert all(e['type']=='radiant' for e in c.log if e['event']=='damage')
    c.damage(a,a.temp_hp+2,'force',t)
    assert not a.has_status('wild_shape') and a.ac==ac and a.attacks==attacks and a.abilities==original and a.hp==hp-2


def test_shape_eligibility_and_casting_exception(spells):
    a,t,c=fight(spells,level=2)
    assert not c.wild_shape(a,'brown_bear') and not c.wild_shape(a,'owlbear')
    assert c.wild_shape(a,'wolf') and not c.can_cast(a,'Cure Wounds')
    a,t,c=fight(spells,level=5)
    assert c.cast(a,'Entangle',targets=[t]); concentration=a.concentration
    assert c.wild_shape(a,'brown_bear') and a.concentration==concentration
    c.end_turn(a); c.begin_turn(a)
    assert c.can_cast(a,'Moonbeam') and c.can_cast(a,'Starry Wisp') and c.can_cast(a,'Cure Wounds')
    assert not c.can_cast(a,'Entangle') and not c.can_cast(a,'Thorn Whip')


def test_shape_saves_and_duration(spells,monkeypatch):
    a,t,c=fight(spells,level=7); assert c.wild_shape(a,'brown_bear')
    fixed(c,monkeypatch)
    assert c.saving_throw(a,'con',10+2+a.mod('wis'))
    assert not c.saving_throw(a,'con',11+2+a.mod('wis'))
    c.advance_time(600*(a.level//2))
    assert not a.has_status('wild_shape')


def test_potent_spellcasting(spells,monkeypatch):
    a,t,c=fight(spells,level=7); fixed(c,monkeypatch)
    assert c.cast(a,'Thorn Whip',targets=[t])
    assert 500-t.hp==2+a.mod('wis')


def test_innate_sorcery_dc_advantage_expiry_and_economy(spells,monkeypatch):
    a,t,c=fight(spells,'sorcerer',1); base=a.spell_dc; flags=[]
    monkeypatch.setattr(dice,'d20',lambda rng,advantage=False,disadvantage=False: flags.append((advantage,disadvantage)) or 10)
    assert c.innate_sorcery(a) and not c.innate_sorcery(a)
    assert a.spell_dc==base+1 and a.limited_uses['innate_sorcery']==1 and a.action==1 and a.bonus_action==0
    c.cast(a,'Fire Bolt',targets=[t]); assert flags[-1]==(True,False)
    c.end_turn(a); c.begin_turn(a); c.weapon_action(a); assert flags[-1]==(False,False)
    c.advance_time(10); assert a.spell_dc==base and not a.has_status('innate_sorcery')
    c.begin_turn(a); assert c.innate_sorcery(a)
    cleanup_encounter(c); assert a.spell_dc==base
    c.begin_turn(a); assert not c.innate_sorcery(a)
    take_rest([a],'long',c.rng); assert a.limited_uses['innate_sorcery']==2


def test_font_conversion_and_long_rest(spells):
    a,t,c=fight(spells,'sorcerer',5)
    assert not c.font_of_magic(a,3)
    a.limited_uses['sorcery_points']=1
    assert c.font_of_magic(a,3) and a.limited_uses['sorcery_points']==4 and a.action==1 and a.bonus_action==1
    assert c.font_of_magic(a,2,create=True) and a.spell_slots[2]==4 and a.limited_uses['sorcery_points']==1 and a.bonus_action==0
    assert not c.font_of_magic(a,1,create=True) and not c.font_of_magic(a,4,create=True)
    take_rest([a],'long',c.rng); assert a.spell_slots==a.max_spell_slots and a.limited_uses['sorcery_points']==5


def test_short_rest_limits(spells):
    a=pc(level=7); s=pc('sorcerer',7); rng=random.Random(1)
    a.limited_uses['wild_shape']=0; s.limited_uses['sorcery_points']=0
    take_rest([a,s],'short',rng)
    assert a.limited_uses['wild_shape']==1 and s.limited_uses['sorcery_points']==3
    take_rest([a,s],'short',rng)
    assert a.limited_uses['wild_shape']==2 and s.limited_uses['sorcery_points']==3
    take_rest([a,s],'long',rng)
    assert a.limited_uses['wild_shape']==3 and s.limited_uses['sorcery_points']==7 and s.limited_uses['sorcerous_restoration']==1


def test_quickened_action_cantrip_and_level_spell_lock(spells,monkeypatch):
    a,t,c=fight(spells,'sorcerer',5); fixed(c,monkeypatch)
    assert c.cast(a,'Magic Missile',targets=[t,t,t],metamagic='quickened_spell')
    assert a.action==1 and a.bonus_action==0 and a.limited_uses['sorcery_points']==3
    assert not c.can_cast(a,'Scorching Ray')
    assert c.cast(a,'Fire Bolt',targets=[t]) and a.action==0
    c.end_turn(a); c.begin_turn(a)
    assert c.cast(a,'Magic Missile',targets=[t,t,t])
    assert not c.cast(a,'Fire Bolt',targets=[t],metamagic='quickened_spell')
    c.end_turn(a); c.begin_turn(a)
    assert c.cast(a,'Fire Bolt',targets=[t],metamagic='quickened_spell')
    assert not c.can_cast(a,'Magic Missile') and c.can_cast(a,'Fire Bolt')


def test_heightened_first_and_repeat_saves(spells,monkeypatch):
    a,t,c=fight(spells,'sorcerer',5); flags=[]
    monkeypatch.setattr(dice,'d20',lambda rng,advantage=False,disadvantage=False: flags.append(disadvantage) or 1)
    inst=c.cast(a,'Web',metamagic='heightened_spell')
    assert inst and a.limited_uses['sorcery_points']==3
    assert c.spell_save(inst,t,'dex',a.spell_dc)==False and flags[-1]
    other=Combatant('other'); c.combatants.append(other)
    c.spell_save(inst,other,'dex',a.spell_dc); assert not flags[-1]
    c.end_turn(a); flags.clear(); c.begin_turn(t)
    assert flags and all(flags)


def test_extended_duration_and_concentration(spells,monkeypatch):
    a,t,c=fight(spells,'sorcerer',10); flags=[]
    inst=c.cast(a,'Web',metamagic='extended_spell')
    assert inst.spec['duration']=={'type':'minutes','n':120} and a.limited_uses['sorcery_points']==9
    monkeypatch.setattr(dice,'d20',lambda rng,advantage=False,disadvantage=False: flags.append(advantage) or 10)
    c.damage(a,1,'force',t); assert flags[-1]


def test_careful_allies_take_no_half_damage(spells,monkeypatch):
    a,t,c=fight(spells,'sorcerer',10); ally=Combatant('ally',team='party',max_hp=100); c.combatants.append(ally)
    fixed(c,monkeypatch)
    c.area=lambda *args:args[2]
    c.policy.exemptions=lambda *args:[]
    inst=c.cast(a,'Fireball',metamagic='careful_spell')
    assert inst and a.limited_uses['sorcery_points']==9 and ally.hp==100
    assert t.hp<500 and ally.id in inst.choices['_careful']


def test_affinity_one_roll_and_fire_resistance(spells,monkeypatch):
    a,t,c=fight(spells,'sorcerer',7); fixed(c,monkeypatch)
    assert c.cast(a,'Scorching Ray',targets=[t,t,t],slot=2)
    assert 500-t.hp==6+a.mod('cha')
    c.damage(a,10,'fire',t); assert a.hp==a.max_hp-5
    c.end_turn(a); c.begin_turn(a)
    t.hp=500; c.cast(a,'Fireball',targets=None,slot=3)
    assert 500-t.hp==8+a.mod('cha')


def test_ai_shapes_with_concentration_and_sorcerer_uses_metamagic(spells,monkeypatch):
    a,t,c=fight(spells,level=5); fixed(c,monkeypatch)
    c.cast(a,'Entangle',targets=[t]); c.end_turn(a); c.begin_turn(a)
    c.policy.take_turn(c,a); assert a.has_status('wild_shape')
    a,t,c=fight(spells,'sorcerer',5); fixed(c,monkeypatch)
    a.spells=['Fireball','Fire Bolt']; c.policy.take_turn(c,a)
    assert a.has_status('innate_sorcery')
    c.end_turn(a); c.begin_turn(a); c.policy.take_turn(c,a)
    assert a.resources_spent.get('sorcery_points',0)>=2


def test_roles_variants_and_short_fights(spells):
    assert ROLES['druid']=='cleric' and ROLES['sorcerer']=='wizard'
    for name in ('druid','sorcerer'):
        for level in LEVELS:
            found=variants(name,level); assert found[0]['name']=='standard' and len(found)>=3
            if level>=5: assert any(v['name']=='feat: war caster' for v in found)
            a=Combatant.from_sheet(load_build(f'{name}_{level}'),name,'party')
            c=Combat([a,Combatant('t',max_hp=30)],spells,seed=3)
            assert c.run(max_rounds=10)['winner']=='party'



def test_invalid_metamagic_preserves_resources_and_targets(spells):
    a,t,c=fight(spells,'sorcerer',5)
    points=a.limited_uses['sorcery_points']
    assert not c.cast(a,'Fire Bolt',targets=[t],metamagic='heightened_spell')
    assert not c.cast(a,'Fire Bolt',targets=[t],metamagic='extended_spell')
    assert a.limited_uses['sorcery_points']==points and a.action==a.bonus_action==1
    other=Combatant('other',max_hp=600); c.combatants.append(other)
    a.spells.append('Hold Person')
    inst=c.cast(a,'Web',targets=None,metamagic='heightened_spell')
    assert inst.choices['_heightened_target']==t.id
    c.end_turn(a); c.begin_turn(a)
    inst=c.cast(a,'Hold Person',targets=[other],metamagic='heightened_spell')
    assert inst.choices['_heightened_target']==other.id


def test_affinity_shared_roll_and_no_bonus_on_other_elements(spells,monkeypatch):
    a,t,c=fight(spells,'sorcerer',7); fixed(c,monkeypatch)
    other=Combatant('other',max_hp=500); c.combatants.append(other)
    c.cast(a,'Fireball',slot=3)
    assert 500-t.hp==500-other.hp==8+a.mod('cha')
    c.end_turn(a); c.begin_turn(a)
    before=t.hp; c.cast(a,'Ray of Frost',targets=[t])
    assert before-t.hp==2


def test_shape_cleanup_and_long_rest_restore_stats(spells):
    a,t,c=fight(spells,level=7); original=deepcopy(a.abilities); ac=a.ac
    assert c.wild_shape(a,'giant_spider')
    cleanup_encounter(c)
    assert a.abilities==original and a.ac==ac and not a.has_status('wild_shape')
    c.begin_turn(a); assert c.wild_shape(a,'brown_bear')
    take_rest([a],'long',c.rng)
    assert a.abilities==original and a.ac==ac and not a.has_status('wild_shape') and a.temp_hp==0


def test_incapacitation_ends_shape(spells):
    a,t,c=fight(spells,level=5)
    original=deepcopy(a.abilities)
    assert c.wild_shape(a,'brown_bear')
    a.conditions.add('stunned'); c.refresh_spell_effects()
    assert not a.has_status('wild_shape') and a.abilities==original
