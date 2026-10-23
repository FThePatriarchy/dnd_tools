from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from engine import Combat, Combatant, load_sheet, load_spells, ValidationError
from engine.loader import ROOT
from engine.monster_import import STEP2, ORIGINAL, RAW, slug, source_monsters, parse_monster, check_sheet
from engine.monster_validation import source_tag_gaps, source_attack_dpr, sheet_attack_dpr
from engine.policy import Policy
from engine.sheets import validate_sheet, effect_block
from engine.step2 import condition, damage


@pytest.fixture(scope='module')
def spells(): return load_spells()


@pytest.fixture(scope='module')
def sources(): return source_monsters()


def sheet(name): return load_sheet(ROOT / 'monsters' / (slug(name) + '.yaml'))


def encounter(name, spells, seed=1, policy=None, ally=False):
    actor = Combatant.from_sheet(sheet(name), 'monster', 'enemy')
    targets = [Combatant(f'd{i}', team='party', max_hp=100000, ac=-100,
                         save_bonuses=dict.fromkeys(('str','dex','con','int','wis','cha'), -100)) for i in range(4)]
    actors = [actor] + targets
    if ally: actors += [Combatant('ally', team='enemy', attacks=[{'name':'club','kind':'melee','to_hit':2,'effects':[damage('1d4','bludgeoning')]}])]
    return Combat(actors, spells, seed=seed, policy=policy), actor, targets


@pytest.mark.parametrize('name', ORIGINAL + STEP2)
def test_step2_strict_source_numeric_tags_and_damage(name, sources, spells):
    s = sheet(name)
    assert s['source'] == 'XMM'
    assert check_sheet(s, sources[name]) == []
    assert source_tag_gaps(sources[name], s, spells) == []
    assert sheet_attack_dpr(s) == pytest.approx(source_attack_dpr(sources[name]), abs=1e-10)
    # Every source spell is either executable by name or explicitly unsupported.
    import re
    source_spells = set(re.findall(r'\{@spell ([^|}]+)', json.dumps(sources[name].get('spellcasting', []))))
    assert source_spells <= set(s.get('spells', [])) | set(s.get('unsupported_spells', []))


@pytest.mark.parametrize('name', ORIGINAL + STEP2)
def test_step2_three_turn_execution_and_each_declared_option(name, spells):
    b, actor, targets = encounter(name, spells, ally=True)
    for _ in range(3):
        b.begin_turn(actor); b.policy.take_turn(b, actor); b.end_turn(actor)
        for target in targets: b.begin_turn(target); b.end_turn(target)
    assert sum(e['event'] == 'turn_start' and e['actor'] == actor.id for e in b.log) == 3
    assert any(e['event'] in {'weapon','cast','action'} and e.get('actor', e.get('caster')) == actor.id for e in b.log)
    # Deliberately exercise alternatives the damage policy might never select.
    for attack in actor.attacks:
        trial, a, ts = encounter(name, spells)
        trial.begin_turn(a)
        for _ in range(10): trial.weapon_attack(a, ts[0], attack)
        assert any(e['event'] == 'weapon' and e['name'] == attack['name'] for e in trial.log)
        assert any(e['event'] == 'damage' for e in trial.log)
    for action in actor.actions + actor.traits:
        trial, a, ts = encounter(name, spells)
        if name in {'Vampire Spawn','Aboleth'}:
            for _ in range(3): trial.weapon_attack(a, ts[0], a.attacks[0])
        if action.get('trigger'):
            trial.begin_turn(ts[0])
            assert any(e['event'] == 'trait' and e['name'] == action['name'] for e in trial.log)
        elif action.get('passive'):
            trial.begin_turn(a); trial.end_turn(a)
            assert any(e['event'] == 'trait' and e['name'] == action['name'] for e in trial.log)
        else:
            trial.begin_turn(a)
            assert trial.use_action(a, action['name'])
            assert any(e['event'] == 'action' and e['name'] == action['name'] for e in trial.log)


@pytest.mark.parametrize('key', ['ac','max_hp','speed','proficiency_bonus','initiative_bonus'])
def test_step2_check_rejects_base_numeric_drift(key):
    s=sheet('Adult Red Dragon');s[key]+=1
    assert any(e.startswith(key+':') for e in check_sheet(s))


@pytest.mark.parametrize('mutation', [
    lambda s: s['attacks'][0].update(to_hit=99),
    lambda s: s['attacks'][0]['effects'][0]['damage'].update(dice='9d12'),
    lambda s: s['actions'][0].update(recharge=6),
    lambda s: s['actions'][0]['effects'][0]['save'].update(dc=1),
    lambda s: s['actions'][0]['effects'][0]['on_fail'][0]['damage'].update(dice='1d4'),
    lambda s: s['limited_uses'].update(legendary_resistance=4),
    lambda s: s.update(spell_dc=21),
])
def test_step2_check_rejects_attack_save_recharge_daily_spell_drift(mutation):
    s=sheet('Adult Red Dragon');mutation(s)
    assert check_sheet(s)


def test_step2_check_cli_and_error_exit(tmp_path):
    result = subprocess.run([sys.executable,'-m','engine.monster_import','--check'], capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    assert '70 XMM sheets checked' in result.stdout
    import yaml
    s=sheet('Wolf');s['attacks'][0]['to_hit']+=1
    p=tmp_path/'drift.yaml';p.write_text(yaml.safe_dump(s),encoding='utf8')
    result = subprocess.run([sys.executable,'-m','engine.monster_import','--check',str(p)],capture_output=True,text=True)
    assert result.returncode == 1 and 'to_hit' in result.stderr


def test_step2_parser_flat_damage_and_conditional_fields(sources):
    base=parse_monster(sources['Cultist'])
    assert base['attacks'][0]['effects'][1]['damage'] == {'dice':'1d1','bonus':0,'type':'necrotic'}
    raw=deepcopy(sources['Bandit']);raw['resist']=[{'resist':['fire'],'note':'while underwater'}]
    raw['initiative']=7;raw['speed']['fly']={'number':60,'condition':'while transformed'}
    b=parse_monster(raw)
    assert not b['resistances'] and any('underwater' in x for x in b['unsupported'])
    assert b['initiative_bonus']==7-(raw['dex']-10)//2
    assert any('transformed' in x for x in b['unsupported'])
    raw['source']='MM'
    with pytest.raises(ValueError,match='only XMM'):parse_monster(raw)


def test_step2_tag_crosscheck_is_not_vacuous(sources,spells):
    s=sheet('Wyvern');s['attacks'][1]['effects']=[s['attacks'][1]['effects'][0]]
    assert source_tag_gaps(sources['Wyvern'],s,spells)
    s['unsupported'].append('Sting: Poison damage and Poisoned condition omitted for fixture.')
    assert source_tag_gaps(sources['Wyvern'],s,spells)==[]


class DeclineLegendary(Policy):
    def legendary_action(self,*args):return None
    def legendary_resistance(self,*args):return False


def test_step2_legendary_timing_budget_reset_and_policy(spells):
    b,a,ts=encounter('Adult Red Dragon',spells)
    b.begin_turn(a);b.end_turn(a)
    assert not any(e['event']=='legendary_action' for e in b.log)
    for t in ts:b.begin_turn(t);b.end_turn(t)
    logs=[e for e in b.log if e['event']=='legendary_action']
    assert len(logs)==3 and a.legendary_remaining==0
    assert all(e['after']!=a.id for e in logs)
    assert sum(e['name']=='Fiery Rays' for e in logs)==1
    b.begin_turn(a)
    assert a.legendary_remaining==3 and not a.legendary_used
    a.conditions.add('incapacitated');b.end_turn(ts[0])
    assert a.legendary_remaining==3
    b,a,ts=encounter('Adult Red Dragon',spells,policy=DeclineLegendary())
    b.end_turn(ts[0]);assert a.legendary_remaining==3


@pytest.mark.parametrize('name',['Aboleth','Adult Red Dragon'])
def test_step2_legendary_resistance_three_lair_free_and_automatic_fail(name,spells):
    b,a,ts=encounter(name,spells)
    a.save_bonuses['dex']=-100
    a.conditions.add('paralyzed')
    assert all(b.saving_throw(a,'dex',25) for _ in range(3))
    assert not b.saving_throw(a,'dex',25)
    assert a.resources_spent['legendary_resistance']==3
    b,a,ts=encounter(name,spells,policy=DeclineLegendary())
    a.save_bonuses['con']=-100
    assert not b.saving_throw(a,'con',25) and a.limited_uses['legendary_resistance']==3


@pytest.mark.parametrize('dtype',['acid','fire'])
def test_step2_troll_regeneration_shutoff_and_zero_hp(dtype,spells):
    b,a,ts=encounter('Troll',spells)
    a.hp=30;b.begin_turn(a);assert a.hp==45
    b.damage(a,5,dtype,ts[0]);b.begin_turn(a);assert a.hp==40
    b.begin_turn(a);assert a.hp==55
    a.hp=1;b.damage(a,10,'slashing',ts[0]);assert a.hp==0
    b.begin_turn(a);assert a.hp==15 and a.alive
    b.damage(a,100,dtype,ts[0]);b.begin_turn(a);assert a.hp==0


def test_step2_pack_tactics_melee_ally_approximation(spells):
    b,a,ts=encounter('Wolf',spells)
    assert not b.roll_flags(a,'attack_rolls',against=ts[0])[0]
    ally=Combatant('friend',team=a.team,attacks=[deepcopy(a.attacks[0])]);b.combatants.append(ally)
    assert b.roll_flags(a,'attack_rolls',against=ts[0])[0]
    ally.conditions.add('incapacitated');assert not b.roll_flags(a,'attack_rolls',against=ts[0])[0]
    ally.conditions.clear();ally.attacks[0]['kind']='ranged'
    assert not b.roll_flags(a,'attack_rolls',against=ts[0])[0]


def test_step2_undead_fortitude_radiant_critical_and_damage_dc(spells):
    b,a,ts=encounter('Zombie',spells)
    a.hp=1;a.save_bonuses['con']=100
    b.damage(a,10,'slashing',ts[0]);assert a.hp==1
    save=next(e for e in b.log if e['event']=='save');assert save['dc']==15
    b.damage(a,10,'radiant',ts[0]);assert a.hp==0
    a.hp=1;a.conditions.clear();b._critical_damage=True
    b.damage(a,10,'slashing',ts[0]);assert a.hp==0
    b,a,ts=encounter('Zombie',spells);a.hp=1;a.save_bonuses['con']=-100
    b.damage(a,10,'slashing',ts[0]);assert a.hp==0


def test_step2_magic_resistance_only_magical_saves(spells):
    b,a,ts=encounter('Imp',spells,seed=7)
    for _ in range(1000):b.saving_throw(a,'wis',11,magical=True)
    magical=sum(e['success'] for e in b.log if e['event']=='save')
    assert 650<magical<850
    b.log.clear()
    for _ in range(1000):b.saving_throw(a,'wis',11)
    plain=sum(e['success'] for e in b.log if e['event']=='save')
    assert 400<plain<650 and magical>plain
    b.log.clear();b.begin_turn(ts[0]);ts[0].spells=['Hold Person'];ts[0].spell_slots={2:1}
    # Actual golden spell path supplies magical=True, independent of direct API.
    ts[0].spells=['Fireball'];ts[0].spell_slots={3:1};b.cast(ts[0],'Fireball')
    assert any(e['event']=='trait' and e['name']=='Magic Resistance' for e in b.log)


@pytest.mark.parametrize('name,bonus',[('Bandit Captain',2),('Gladiator',3),('Knight',2),('Warrior Veteran',2)])
def test_step2_parry_only_provisional_melee_hit_once(name,bonus,spells):
    b,a,ts=encounter(name,spells);a.ac=15
    roll={'natural':10,'total':15,'critical':False,'advantage':False}
    assert b.monster_reaction(ts[0],a,roll,True)
    assert a.reaction==0 and not b.monster_reaction(ts[0],a,roll,True)
    b.begin_turn(a);assert not b.monster_reaction(ts[0],a,roll,False)
    assert not b.monster_reaction(ts[0],a,{**roll,'natural':20},True)
    assert not b.monster_reaction(ts[0],a,{**roll,'total':15+bonus},True)


def test_step2_grapple_escape_size_and_source_cleanup(spells):
    b,a,ts=encounter('Chain Devil',spells)
    b.begin_turn(a)
    for _ in range(5):b.weapon_attack(a,ts[0],a.attacks[0])
    t=ts[0];assert t.has_condition('grappled') and t.has_condition('restrained')
    assert a in b.condition_sources(t,'grappled')
    t.abilities['str']=100;b.begin_turn(t);assert b.escape(t)
    assert not t.has_condition('restrained') and not t.has_condition('grappled')
    ts[1].size='H';b.weapon_attack(a,ts[1],a.attacks[0]);assert not ts[1].has_condition('grappled')
    b.weapon_attack(a,t,a.attacks[0]);a.hp=0;b.end_turn(t)
    assert not t.has_condition('grappled')


def test_step2_sunlight_frenzy_authority_and_evasion(spells):
    b,a,ts=encounter('Kobold Warrior',spells);b.sunlight=True
    assert b.roll_flags(a,'attack_rolls',against=ts[0])==(False,True)
    b,a,ts=encounter('Berserker',spells);a.hp=a.max_hp//2
    assert b.roll_flags(a,'saves')[0] and b.roll_flags(a,'attack_rolls')[0]
    b,a,ts=encounter('Hobgoblin Captain',spells)
    assert b.roll_flags(a,'attack_rolls')[0]
    a.conditions.add('incapacitated');assert not b.roll_flags(a,'saves')[0]
    b,a,ts=encounter('Assassin',spells)
    caster=ts[0];caster.spells=['Fireball'];caster.spell_slots={3:2};caster.spell_dc=15
    a.save_bonuses['dex']=100;b.begin_turn(caster);b.cast(caster,'Fireball')
    assert a.hp==a.max_hp
    a.save_bonuses['dex']=-100;b.begin_turn(caster);b.cast(caster,'Fireball')
    assert any(e['event']=='trait' and e['name']=='Evasion' for e in b.log)
    assert 4<=a.max_hp-a.hp<=24


def test_step2_life_drain_not_double_damage_and_mummy_healing_block(spells):
    b,a,ts=encounter('Specter',spells);t=ts[0]
    b.weapon_attack(a,t,a.attacks[0])
    amount=sum(e['amount'] for e in b.log if e['event']=='damage')
    assert t.hp==100000-amount and t.max_hp==100000-amount
    b,a,ts=encounter('Mummy',spells);b.weapon_attack(a,ts[0],a.attacks[0]);hp=ts[0].hp
    b.heal(ts[0],100);assert ts[0].hp==hp


def test_step2_engulf_whelm_spores_and_petrification(spells):
    for name, action, kind, count, initial, recurring in [
        ('Gelatinous Cube', 'Engulf', 'acid', 4, 6, 6),
        ('Water Elemental', 'Whelm', 'bludgeoning', 2, 12, 4),
        ('Vrock', 'Spores', 'poison', 4, 0, 2),
    ]:
        b, a, ts = encounter(name, spells); b.rng = Step2FixedDice()
        b.begin_turn(a); b.use_action(a, action)
        assert fix_damage_log(b) == ([(t.id, initial, kind) for t in ts[:count]] if initial else [])
        b.log.clear()
        if name == 'Vrock':
            b.begin_turn(a); assert fix_damage_log(b) == []
            b.begin_turn(ts[0]); expected = [('d0', recurring, kind)]
        else:
            b.begin_turn(ts[0]); assert fix_damage_log(b) == []
            b.begin_turn(a); expected = [(t.id, recurring, kind) for t in ts[:count]]
        assert fix_damage_log(b) == expected
        assert [t.hp for t in ts] == [100000-initial-(recurring if name != 'Vrock' or i == 0 else 0) if i < count else 100000 for i in range(4)]
    b,a,ts=encounter('Basilisk',spells);b.begin_turn(a);b.use_action(a,'Petrifying Gaze')
    assert ts[0].has_condition('restrained') and not ts[0].has_condition('petrified')
    b.begin_turn(ts[0]);b.end_turn(ts[0]);assert ts[0].has_condition('petrified') and not ts[0].has_condition('restrained')


def test_step2_aboleth_domination_and_damage_repeat_save(spells):
    b,a,ts=encounter('Aboleth',spells);b.begin_turn(a);b.use_action(a,'Dominate Mind',[ts[0]])
    assert ts[0].team==a.team and ts[0].has_condition('charmed')
    ts[0].save_bonuses['wis']=100;b.damage(ts[0],1,'force',a)
    assert ts[0].team=='party' and not ts[0].has_condition('charmed')


def test_step2_shared_innate_pool_upcast_and_bonus_casting(spells):
    b,a,ts=encounter('Mage',spells);b.begin_turn(a)
    assert b.cast(a,'Fireball').slot==4
    assert a.limited_uses['Fireball']==1
    a.action=1
    assert b.cast(a,'Shield')
    assert a.limited_uses['Protective Magic']==2
    a.reaction=1
    # Counterspell shares exactly the same pool, not three extra uses.
    b.cast(a,'Counterspell',trigger={'caster':ts[0],'spell':spells['Fireball'],'cancelled':False})
    assert a.limited_uses['Protective Magic']==1
    b,a,ts=encounter('Priest',spells);b.begin_turn(a)
    assert b.cast(a,'Bless',targets=[a])
    assert a.bonus_action==0 and a.action==1 and a.limited_uses['Divine Aid']==2


@pytest.mark.parametrize('mutate',[
    lambda s:s.update(features={'typo':True}),
    lambda s:s['legendary'].update(uses=0),
    lambda s:s['legendary']['options'][0].update(cost=4),
    lambda s:s.update(routines=[['typo']]),
    lambda s:s.update(spell_resources={'Scorching Ray':'missing'}),
    lambda s:s['actions'][0]['effects'][0]['save'].update(dc=0),
])
def test_step2_new_fields_still_validate_strictly(mutate):
    s=sheet('Adult Red Dragon');mutate(s)
    with pytest.raises(ValidationError):validate_sheet(s,'fixture.yaml')
FEATURE_LABELS={
    'pack_tactics':'Pack Tactics','magic_resistance':'Magic Resistance','sunlight_sensitivity':'Sunlight Sensitivity',
    'bloodied_frenzy':'Bloodied Frenzy','evasion':'Evasion','parry':'Parry','regeneration':'Regeneration',
    'undead_fortitude':'Undead Fortitude','life_drain':'Life Drain','redirect_attack':'Redirect Attack',
    'authority_aura':'Aura of Authority','grapple_damage':'Barbed Hide','rampage':'Rampage',
}


@pytest.mark.parametrize('name',[n for n in STEP2 if sheet(n).get('features')])
def test_step2_every_declared_feature_is_observed_in_seeded_log(name,spells):
    b,a,ts=encounter(name,spells,ally=True)
    expected=set()
    for feature in a.features:
        expected.add(FEATURE_LABELS[feature])
        if feature=='pack_tactics': b.roll_flags(a,'attack_rolls',against=ts[0])
        elif feature=='magic_resistance':b.saving_throw(a,'con',15,magical=True)
        elif feature=='sunlight_sensitivity':b.sunlight=True;b.roll_flags(a,'ability_checks')
        elif feature=='bloodied_frenzy':a.hp=1;b.roll_flags(a,'saves')
        elif feature=='regeneration':b.begin_turn(a)
        elif feature=='undead_fortitude':
            a.hp=1;a.save_bonuses['con']=100;b.damage(a,1,'bludgeoning',ts[0])
        elif feature=='parry':b.monster_reaction(ts[0],a,{'natural':10,'total':a.ac,'critical':False},True)
        elif feature=='authority_aura':b.roll_flags(a,'saves')
        elif feature=='life_drain':
            b._monster_attack=(a,a.features['life_drain']['attacks'][0]);b.damage(ts[0],1,'necrotic',a);b._monster_attack=None
        elif feature=='redirect_attack':b.redirect_target(ts[0],a)
        elif feature=='grapple_damage':
            for _ in range(10):b.weapon_attack(a,ts[0],a.attacks[0])
            b.begin_turn(a)
        elif feature=='rampage':
            ts[0].hp=40000
            for _ in range(10):b.weapon_attack(a,ts[0],a.attacks[0])
        elif feature=='evasion':
            caster=ts[0];caster.spells=['Fireball'];caster.spell_slots={3:1};b.begin_turn(caster);b.cast(caster,'Fireball')
        else:pytest.fail('feature has no coverage: '+feature)
    observed={e['name'] for e in b.log if e['event'] in {'trait','reaction'}}
    assert expected<=observed


class FirstLegendary(Policy):
    def __init__(self,name):self.name=name
    def legendary_action(self,combat,actor,finished,options):
        return next((o for o in options if o['name']==self.name),None)


@pytest.mark.parametrize('name,option',[('Aboleth','Lash'),('Aboleth','Psychic Drain'),('Adult Red Dragon','Pounce'),('Adult Red Dragon','Fiery Rays')])
def test_step2_each_executable_legendary_option_logged(name,option,spells):
    b,a,ts=encounter(name,spells,policy=FirstLegendary(option))
    if name=='Aboleth':
        for _ in range(3): b.weapon_attack(a, ts[0], a.attacks[0])
    a.hp-=20
    b.begin_turn(ts[0]);b.end_turn(ts[0])
    assert any(e['event']=='legendary_action' and e['name']==option for e in b.log)
    assert any(e['event']=='damage' for e in b.log)
    if option=='Psychic Drain':assert a.hp>a.max_hp-20


def test_step2_legendary_cost_and_no_reaction_or_action_spend(spells):
    b,a,ts=encounter('Adult Red Dragon',spells,policy=FirstLegendary('Pounce'))
    p=next(o for o in a.legendary['options'] if o['name']=='Pounce');p['cost']=2
    a.action=a.reaction=0
    b.begin_turn(ts[0]);b.end_turn(ts[0])
    assert a.legendary_remaining==1 and a.action==a.reaction==0
    b.begin_turn(ts[1]);b.end_turn(ts[1])
    assert sum(e['event']=='legendary_action' for e in b.log)==1


def test_step2_parry_live_pending_hit_path(spells):
    b,a,ts=encounter('Knight',spells);a.ac=15
    class Fixed:
        def randint(self,*_):return 10
    b.rng=Fixed()
    assert not b.attack(ts[0],a,5,lambda *_:pytest.fail('Parried hit dealt damage'))
    assert a.hp==a.max_hp and a.reaction==0
    assert b.armor_class(a)==15


def test_step2_redirect_weapon_and_spell_damage_go_to_ally(spells):
    for spell in (False,True):
        b,a,ts=encounter('Goblin Boss',spells,ally=True)
        ally=b.combatants[-1];ally.max_hp=ally.hp=10000;ally.ac=-100
        a.ac=-100
        if spell:
            attacker=ts[0];attacker.spells=['Guiding Bolt'];attacker.spell_slots={1:1}
            b.begin_turn(attacker);b.cast(attacker,'Guiding Bolt',targets=[a])
        else:b.weapon_attack(ts[0],a,{'name':'club','kind':'melee','to_hit':100,'effects':[damage('1d4','bludgeoning')]})
        assert a.hp==a.max_hp and ally.hp<ally.max_hp and a.reaction==0
        assert any(e['event']=='reaction' and e['name']=='Redirect Attack' for e in b.log)


def test_step2_stench_success_immunity_independent_of_logging(spells):
    for log in (True,False):
        b,a,ts=encounter('Ghast',spells);b.record_log=log
        ts[0].save_bonuses['con']=100
        b.begin_turn(ts[0]);assert ts[0].has_status('stench_immune')
        ts[0].save_bonuses['con']=-100
        b.begin_turn(ts[0]);assert not ts[0].has_condition('poisoned')


def test_step2_unnerving_gaze_ends_this_turn_and_uses_reaction(spells):
    b,a,ts=encounter('Chain Devil',spells);b.begin_turn(ts[0])
    assert ts[0].has_condition('frightened') and a.reaction==0
    b.end_turn(ts[0]);assert not ts[0].has_condition('frightened')
    b.begin_turn(ts[1]);assert not ts[1].has_condition('frightened')
@pytest.mark.parametrize('name,key,mutate',[
    ('Troll','features.regeneration',lambda s:s['features']['regeneration'].update(amount=16)),
    ('Zombie','features.undead_fortitude',lambda s:s['features'].update(undead_fortitude=6)),
    ('Knight','features.parry',lambda s:s['features'].update(parry=3)),
    ('Mage','limited_uses.Protective Magic',lambda s:s['limited_uses'].update({'Protective Magic':4})),
    ('Mage','spell_levels.Fireball',lambda s:s['spell_levels'].update(Fireball=3)),
    ('Mage','spell_resources.Shield',lambda s:s['spell_resources'].update(Shield='Fireball')),
    ('Adult Red Dragon','legendary.uses',lambda s:s['legendary'].update(uses=4)),
    ('Adult Red Dragon','legendary.Pounce',lambda s:s['legendary']['options'][1].update(cost=2)),
])
def test_step2_check_also_protects_trait_legendary_and_spell_numbers(name,key,mutate):
    s=sheet(name);mutate(s)
    assert any(e.startswith(key) for e in check_sheet(s))


def test_step2_source_scoped_stench_and_ally_friendly_fire(spells):
    first=Combatant.from_sheet(sheet('Ghast'),'g1','enemy')
    second=Combatant.from_sheet(sheet('Ghast'),'g2','enemy')
    ally=Combatant('ally',team='enemy',save_bonuses={'con':-100})
    b=Combat([first,ally],spells)
    b.begin_turn(ally);assert ally.has_condition('poisoned')
    t=Combatant('target',team='party',save_bonuses={'con':100})
    b=Combat([first,second,t],spells)
    # Widen this test's abstract area to isolate source scope from coverage.
    b.area=lambda shape,size,count:count
    b.begin_turn(t)
    assert t.has_status_from('stench_immune',first) and t.has_status_from('stench_immune',second)
    for e in list(t.effects):
        if e.data.get('caster_id')==second.id:t.effects.remove(e)
    t.save_bonuses['con']=-100;b.begin_turn(t)
    assert t.has_condition_from('poisoned',second) and not t.has_condition_from('poisoned',first)


def test_step2_repeated_engulf_does_not_duplicate_ongoing_damage(spells):
    b,a,ts=encounter('Gelatinous Cube',spells)
    b.begin_turn(a);b.use_action(a,'Engulf',[ts[0]])
    a.action=1;b.use_action(a,'Engulf',[ts[0]])
    b.log.clear();b.begin_turn(a)
    damages=[e for e in b.log if e['event']=='damage' and e['target']==ts[0].id]
    assert len(damages)==1
    assert 3<=damages[0]['amount']<=18
def test_step2_web_can_be_cut_and_respects_printed_object_stats(spells):
    b,a,ts=encounter('Giant Spider',spells)
    target=ts[0];target.attacks=[{'name':'cut','kind':'melee','to_hit':100,'effects':[damage('1d1','slashing',5)]}]
    b.begin_turn(a);b.use_action(a,'Web',[target]);assert target.has_condition('restrained')
    b.begin_turn(target);assert b.escape(target)
    assert not target.has_condition('restrained')
    assert any(e['event']=='break_obstacle' and e['remaining_hp']==0 for e in b.log)
    b.begin_turn(a);a.recharge_ready['Web']=True;b.use_action(a,'Web',[target])
    target.attacks[0]['effects']=[damage('1d1','poison',5)]
    b.begin_turn(target);b.escape(target);assert target.has_condition('restrained')
    target.attacks[0]['effects']=[damage('1d1','fire',2)]
    b.begin_turn(target);b.escape(target);assert not target.has_condition('restrained')


def test_step2_aboleth_multiattack_can_select_domination(spells):
    b,a,ts=encounter('Aboleth',spells)
    # Conversion of a capable opponent is worthwhile, not ordinary harmless charm.
    for t in ts:t.attacks=[{'name':'hit','kind':'melee','to_hit':10,'effects':[damage('4d10','slashing')]}]
    b.begin_turn(a);b.policy.take_turn(b,a)
    names=[e['name'] for e in b.log if e['event'] in {'action','weapon'} and e.get('actor')==a.id]
    assert names.count('Tentacle')==2 and 'Dominate Mind' in names
    assert any(t.team==a.team for t in ts)
def test_step2_printed_grapple_and_engulf_capacities(spells):
    b,a,ts=encounter('Chain Devil',spells)
    for target in ts:
        for _ in range(3):b.weapon_attack(a,target,a.attacks[0])
    assert sum(t.has_condition_from('grappled',a) for t in ts)==2
    assert sum(t.has_condition_from('restrained',a) for t in ts)==2
    for name,action,capacity in [('Gelatinous Cube','Engulf',4),('Water Elemental','Whelm',2)]:
        b,a,ts=encounter(name,spells);ts[0].size='L'
        b.begin_turn(a);b.use_action(a,action,ts[:capacity])
        assert ts[0].has_condition_from('restrained',a)
        assert not any(t.has_condition_from('restrained',a) for t in ts[1:])


def test_step2_domination_survives_incapacitation_but_not_source_death(spells):
    b,a,ts=encounter('Aboleth',spells);b.begin_turn(a);b.use_action(a,'Dominate Mind',[ts[0]])
    a.conditions.add('stunned');b.end_turn(ts[1]);assert ts[0].team==a.team
    a.hp=0;b.end_turn(ts[1]);assert ts[0].team=='party'
def test_step2_embedded_save_action_reselects_legal_recipient(spells):
    b,a,ts=encounter('Vampire Spawn',spells)
    ts[0].hp=1
    for _ in range(3):b.weapon_attack(a,ts[1],a.attacks[0])
    before=ts[1].hp
    assert b.perform_option(a,'Bite',[ts[0]])
    assert ts[0].hp==1 and ts[1].hp<before

# Fix-round probes use exact deterministic dice, and compile legacy branches only
# in memory. Every mutant must trip the very same behavioral assertion.
class Step2FixedDice:
    def randint(self, low, high): return min(2, high)


def fix_damage_log(combat):
    return [(e['target'], e['amount'], e['type']) for e in combat.log if e['event'] == 'damage']


def fix_save_log(combat):
    return [(e['target'], e['ability'], e['dc'], e['success']) for e in combat.log if e['event'] == 'save']


def fix_mutate_method(patch, cls, method, before, after):
    import inspect
    import textwrap
    original = getattr(cls, method)
    source = inspect.getsource(original)
    assert before in source, f'mutant no longer applies: {method}'
    namespace = {}
    exec(compile(textwrap.dedent(source.replace(before, after)), '<step2 in-memory mutant>', 'exec'), original.__globals__, namespace)
    patch.setattr(cls, method, namespace[method])


def fix_mutate_sheet(patch, name, mutate):
    original = sheet
    def changed(requested):
        value = original(requested)
        if requested == name: mutate(value)
        return value
    patch.setattr(sys.modules[__name__], 'sheet', changed)


def test_step2_fix1_spores_recipient_timing_and_no_duplicate_ticks(spells, monkeypatch):
    def check():
        b, a, ts = encounter('Vrock', spells); b.rng = Step2FixedDice()
        b.begin_turn(a); b.use_action(a, 'Spores', ts)
        a.action = 1; a.recharge_ready['Spores'] = True
        b.use_action(a, 'Spores', ts)
        assert fix_damage_log(b) == []
        for target in ts:
            b.log.clear(); b.begin_turn(target)
            assert fix_damage_log(b) == [(target.id, 2, 'poison')]
            b.log.clear(); b.end_turn(target)
            assert fix_save_log(b) == [(target.id, 'con', 15, False)]
            assert fix_damage_log(b) == []
        b.log.clear(); b.begin_turn(a)
        assert fix_damage_log(b) == []
        ts[0].save_bonuses['con'] = 100
        b.end_turn(ts[0]); b.log.clear(); b.begin_turn(ts[0])
        assert fix_damage_log(b) == []
        b.begin_turn(ts[1]); assert fix_damage_log(b) == [('d1', 2, 'poison')]
        assert [t.hp for t in ts] == [99998, 99996, 99998, 99998]
    check()
    for cls, method, before, after in [
        (Combat, 'select_targets', 'if block["event"] in {"start_of_turn(target)"', 'if False and block["event"] in {"start_of_turn(target)"'),
        (Combat, 'execute', '(value.get("linked") or other.spec["name"] == instance.spec["name"])', 'value.get("linked")'),
    ]:
        with monkeypatch.context() as patch:
            fix_mutate_method(patch, cls, method, before, after)
            with pytest.raises(AssertionError): check()


def test_step2_fix2_petrification_immunity_and_normal_side_effects(spells, monkeypatch):
    def check():
        for immune in (True, False):
            b, a, ts = encounter('Basilisk', spells); b.rng = Step2FixedDice()
            target = Combatant.from_sheet(sheet('Stone Golem'), 'golem', 'party') if immune else ts[0]
            b.combatants[1] = target
            target.spells = ['Bless']; target.spell_slots = {1: 1}; target.save_bonuses['con'] = -100
            b.begin_turn(target); blessing = b.cast(target, 'Bless', targets=[target])
            assert target.concentration == blessing.id
            b.begin_turn(a); b.use_action(a, 'Petrifying Gaze', [target])
            assert target.has_condition('restrained') and not target.has_condition('petrified')
            b.log.clear(); b.begin_turn(target)
            assert fix_save_log(b) == [] and target.has_condition('restrained')
            b.end_turn(target)
            assert fix_save_log(b) == [(target.id, 'con', 12, False)]
            assert not target.has_condition('restrained')
            assert target.has_condition('petrified') is (not immune)
            assert target.has_condition('incapacitated') is (not immune)
            assert blessing.active is immune
            assert target.concentration == (blessing.id if immune else None)
    check()
    with monkeypatch.context() as patch:
        fix_mutate_method(patch, Combat, 'repeat_saves', '''data = dict(effect.data)
                    data["condition"] = data.pop("upgrade_on_failure")
                    data.pop("repeat_save", None)
                    actor.effects.remove(effect)
                    self.execute(instance, actor, [{"apply_condition": data}], self.context(instance, actor), effect.block)
                    for replacement in actor.effects:
                        if replacement.source == effect.source and replacement.block == effect.block:
                            replacement.until = effect.until''', '''effect.data["condition"] = effect.data.pop("upgrade_on_failure")
                    effect.data.pop("repeat_save", None)''')
        with pytest.raises(AssertionError): check()


def test_step2_fix3_passive_auras_survive_incapacitation(spells, monkeypatch):
    def stench():
        for name, dc in [('Hezrou', 16), ('Ghast', 10)]:
            b, a, ts = encounter(name, spells); b.rng = Step2FixedDice(); a.conditions.add('stunned')
            b.begin_turn(ts[0])
            assert fix_save_log(b) == [('d0', 'con', dc, False)]
            assert [t.has_condition('poisoned') for t in ts] == [True, False, False, False]
            b.end_turn(ts[0]); b.begin_turn(ts[0])
            assert len(fix_save_log(b)) == 2
            assert len([e for e in ts[0].effects if e.kind == 'apply_condition']) == 1
            a.hp = 0; b.log.clear(); b.begin_turn(ts[1])
            assert fix_save_log(b) == []
    def fire():
        b, a, ts = encounter('Fire Elemental', spells); b.rng = Step2FixedDice(); a.conditions.add('stunned')
        b.begin_turn(a); assert fix_damage_log(b) == []
        b.end_turn(a)
        assert fix_damage_log(b) == [('d0', 2, 'fire'), ('d1', 2, 'fire')]
        assert [t.hp for t in ts] == [99998, 99998, 100000, 100000]
        a.hp = 0; b.log.clear(); b.end_turn(a)
        assert fix_damage_log(b) == []
    stench(); fire()
    for method, before, after, probe in [
        ('start_monster_turn', 'if not source.alive: continue', 'if not source.alive or source.has_condition("incapacitated"): continue', stench),
        ('dispatch', 'and not instance.caster.alive: continue', 'and (not instance.caster.alive or instance.caster.has_condition("incapacitated")): continue', fire),
    ]:
        with monkeypatch.context() as patch:
            fix_mutate_method(patch, Combat, method, before, after)
            with pytest.raises(AssertionError): probe()


def test_step2_fix3_audit_all_monster_passive_incapacitation_gates(sources, spells):
    # All 70 entries, not just the reported auras. These are the only explicit
    # passive capability exclusions; Vampire Weakness mentions staking instead.
    explicit = {(n, t['name']) for n in ORIGINAL + STEP2 for t in sources[n].get('trait', [])
                if 'Incapacitated' in str(t) and t['name'] != 'Vampire Weakness'}
    assert explicit == {('Assassin', 'Evasion'), ('Hobgoblin Captain', 'Aura of Authority')} | {
        (n, 'Pack Tactics') for n in ['Tough', 'Hobgoblin Warrior', 'Kobold Warrior', 'Wolf', 'Dire Wolf', 'Hell Hound']}
    passive = {(n, t['name']) for n in ORIGINAL + STEP2 for t in sheet(n).get('traits', []) if t['cost'] == 'free'}
    assert passive == {('Ghast', 'Stench'), ('Hezrou', 'Stench'), ('Fire Elemental', 'Fire Aura')}
    # Barbed Hide also remains passive while its owner is stunned and held by someone else.
    b, a, ts = encounter('Barbed Devil', spells); b.rng = Step2FixedDice()
    inst = b.monster_instance(ts[0], 'hold', [])
    b.execute(inst, a, [condition('grappled', linked=True)], b.context(inst, a), 'hold')
    a.conditions.add('stunned'); b.begin_turn(a)
    assert fix_damage_log(b) == [('d0', 2, 'piercing')]
    # Reaction traits must NOT inherit the free-trait exception.
    b, a, ts = encounter('Chain Devil', spells); a.conditions.add('stunned')
    b.begin_turn(ts[0]); assert fix_save_log(b) == [] and a.reaction == 1


def test_step2_fix4_infernal_sting_healing_depends_on_own_active_poison(spells, monkeypatch):
    def check():
        for immune in (True, False):
            b, a, ts = encounter('Bone Devil', spells); b.rng = Step2FixedDice(); t = ts[0]
            if immune: t.condition_immunities = ['poisoned']
            b.begin_turn(a); b.weapon_attack(a, t, a.attacks[1])
            assert fix_damage_log(b) == [('d0', 8, 'piercing'), ('d0', 8, 'poison')]
            assert t.hp == 99984 and t.has_condition('poisoned') is (not immune)
            assert t.has_status('healing_blocked') is (not immune)
            b.heal(t, 5); assert t.hp == (99989 if immune else 99984)
            # Removing just this poison must stop the ban even if unrelated poison remains.
            if not immune:
                t.effects = [e for e in t.effects if e.kind != 'apply_condition']
                t.conditions.add('poisoned')
                assert not t.has_status('healing_blocked')
                b.heal(t, 5); assert t.hp == 99989
            b.begin_turn(a)
            assert not t.has_status('healing_blocked')
            b.heal(t, 5); assert t.hp == 99994
            assert [x.hp for x in ts[1:]] == [100000] * 3
    check()
    with monkeypatch.context() as patch:
        fix_mutate_sheet(patch, 'Bone Devil', lambda s: s['attacks'][1]['effects'][-1]['status'].update(data={}))
        with pytest.raises(AssertionError): check()
    with monkeypatch.context() as patch:
        # An application-time guard alone is insufficient: poison can be removed later.
        patch.setattr(Combatant, 'status_effects', lambda self, name: [e for e in self.active_effects if e.kind == 'status' and e.data['id'] == name])
        with pytest.raises(AssertionError): check()


def test_step2_fix5_engulf_admits_before_saves_and_damage(spells, monkeypatch):
    def check():
        b, a, ts = encounter('Gelatinous Cube', spells); b.rng = Step2FixedDice(); ts[0].size = 'L'
        b.begin_turn(a); b.use_action(a, 'Engulf', ts)
        assert fix_save_log(b) == [('d0', 'dex', 12, False)]
        assert fix_damage_log(b) == [('d0', 6, 'acid')]
        assert [t.has_condition('restrained') for t in ts] == [True, False, False, False]
        assert [t.hp for t in ts] == [99994, 100000, 100000, 100000]
        a.action = 1; b.log.clear(); b.use_action(a, 'Engulf', ts[1:])
        assert fix_save_log(b) == [] and fix_damage_log(b) == []
        b.begin_turn(ts[0]); assert fix_damage_log(b) == []
        b.begin_turn(a); assert fix_damage_log(b) == [('d0', 6, 'acid')]
        assert ts[0].hp == 99988
        # A full-size candidate that doesn't fit is skipped without excluding smaller ones.
        b, a, ts = encounter('Gelatinous Cube', spells); b.rng = Step2FixedDice(); ts[1].size = 'L'
        b.begin_turn(a); b.use_action(a, 'Engulf', ts)
        assert fix_save_log(b) == [(f'd{i}', 'dex', 12, False) for i in [0, 2, 3]]
        assert fix_damage_log(b) == [(f'd{i}', 6, 'acid') for i in [0, 2, 3]]
    check()
    with monkeypatch.context() as patch:
        fix_mutate_method(patch, Combat, 'resolve_block', 'if block.get("admission") and not self.has_capacity(instance, target, block["admission"]): continue', 'if False: continue')
        with pytest.raises(AssertionError): check()


def test_step2_fix6_troll_dies_when_actual_regeneration_is_zero(spells, monkeypatch):
    def check():
        troll = Combatant.from_sheet(sheet('Troll'), 'troll', 'party'); troll.ac = -100; troll.hp = 10
        mummy = Combatant.from_sheet(sheet('Mummy'), 'mummy', 'enemy')
        b = Combat([mummy, troll], spells); b.rng = Step2FixedDice()
        b.begin_turn(mummy); b.weapon_attack(mummy, troll, mummy.attacks[0])
        assert fix_damage_log(b) == [('troll', 5, 'bludgeoning'), ('troll', 6, 'necrotic')]
        assert troll.hp == 0 and not troll.permanently_removed
        b.log.clear(); b.begin_turn(troll)
        assert (troll.hp, troll.permanently_removed, troll.alive) == (0, True, False)
        assert [(e['name'], e['amount']) for e in b.log if e['event'] == 'trait'] == [('Regeneration', 0)]
        assert fix_damage_log(b) == []
        result = b.run(max_rounds=3)
        assert (result['winner'], result['rounds']) == ('enemy', 1)
        b, a, ts = encounter('Troll', spells); b.rng = Step2FixedDice()
        a.conditions.add('stunned'); a.hp = 0; b.begin_turn(a)
        assert (a.hp, a.permanently_removed) == (15, False)
    check()
    with monkeypatch.context() as patch:
        fix_mutate_method(patch, Combat, 'start_monster_turn', 'if actor.hp == 0: actor.permanently_removed = True', 'if blocked is not None and actor.hp == 0: actor.permanently_removed = True')
        with pytest.raises(AssertionError): check()


def test_step2_fix7_independent_entry_numbers_kill_review_mutations(sources, spells, monkeypatch):
    import engine.monster_import as importer
    mutations = [
        ('Aboleth', lambda s: s['attacks'][0]['effects'][-1]['apply_condition'].update(escape_dc=99), 'attacks.Tentacle.effects[1].apply_condition.escape_dc: 99 absent from source entry'),
        ('Hezrou', lambda s: s['traits'][0]['effects'][0]['save'].update(dc=1), 'traits.Stench.effects[0].save.dc: 1 absent from source entry'),
        ('Vrock', lambda s: s['actions'][0]['effects'][1]['apply'][0]['damage'].update(dice='100d10'), "actions.Spores.effects[1].apply[0].damage: ('100d10', 0, 'poison') absent from source entry"),
    ]
    def check():
        for name, mutate, expected in mutations:
            s = sheet(name); mutate(s)
            assert check_sheet(s, sources[name]) == [expected]
            with monkeypatch.context() as patch:
                patch.setattr(sys.modules[__name__], 'sheet', lambda _: s)
                # The original combined source/tag/DPR gate must now fail too.
                with pytest.raises(AssertionError): test_step2_strict_source_numeric_tags_and_damage(name, sources, spells)
    check()
    with monkeypatch.context() as patch:
        patch.setattr(importer, 'check_finished_numbers', lambda *_: [])
        with pytest.raises(AssertionError): check()


def test_step2_fix7_scoped_bonus_and_plain_damage_not_shared_oracle(sources):
    from engine.monster_import import check_finished_numbers
    for name, mutate in [
        ('Fire Elemental', lambda s: s['traits'][0]['effects'][0]['apply'][0]['damage'].update(bonus=9)),
        ('Water Elemental', lambda s: s['actions'][0]['effects'][1]['apply'][0]['damage'].update(dice='4d8', bonus=4)),
        ('Ghast', lambda s: s['traits'][0]['effects'][0].update(source_ref='action:Claw')),
        ('Aboleth', lambda s: s['attacks'][0]['effects'][-1]['apply_condition'].update(escape_dc=16)),
    ]:
        s = sheet(name); mutate(s)
        assert check_finished_numbers(s, sources[name])
    # A synthetic plain-text entry exercises the other printed XMM damage form.
    raw = {'trait': [{'name': 'Aura', 'entries': ['DC {@dc 17}; 12 (2d6 + 5) Fire damage.']}]}
    block = effect_block('aura', apply=[damage('2d6', 'fire', 5)])
    block['source_ref'] = 'trait:Aura'
    s = {'traits': [{'name': 'Aura', 'effects': [block]}]}
    assert check_finished_numbers(s, raw) == []
    block['apply'][0]['damage']['bonus'] = 6
    assert check_finished_numbers(s, raw) == ["traits.Aura.effects[0].apply[0].damage: ('2d6', 6, 'fire') absent from source entry"]


def test_step2_fix8_burning_is_generic_persistent_nonstacking_and_extinguishable(spells, monkeypatch):
    def check():
        b, a, ts = encounter('Fire Elemental', spells); b.rng = Step2FixedDice(); t = ts[0]
        b.begin_turn(a)
        for _ in range(2): b.weapon_attack(a, t, a.attacks[0])
        assert fix_damage_log(b) == [('d0', 7, 'fire')] * 2
        assert t.has_status('burning') and [x.has_status('burning') for x in ts[1:]] == [False] * 3
        a.hp = 0; b.log.clear(); b.begin_turn(ts[1]); assert fix_damage_log(b) == []
        b.begin_turn(t); assert fix_damage_log(b) == [('d0', 2, 'fire')]
        b.end_turn(t); assert fix_damage_log(b) == [('d0', 2, 'fire')]
        b.begin_turn(t); assert fix_damage_log(b) == [('d0', 2, 'fire')] * 2
        assert t.hp == 99982
        assert b.extinguish(t) and t.action == 0 and t.has_condition('prone')
        assert not t.has_status('burning') and not b.extinguish(t)
        b.log.clear(); b.begin_turn(t); assert fix_damage_log(b) == []
        # Same primitive works in an arbitrary later spell, with no monster-name path.
        inst = b.monster_instance(ts[1], 'Future Fire Spell', [])
        b.execute(inst, t, [{'burning': {}}], b.context(inst, t), 'ignition')
        b.end_spell(inst.id); assert t.has_status('burning')
        t.conditions.add('stunned'); assert not b.extinguish(t) and t.action == 1
        t.conditions.clear(); t.condition_immunities = ['prone']; assert not b.extinguish(t)
        t.condition_immunities.clear()
        for method in ('doused', 'submerged', 'suffocated'):
            b.ignite(t, ts[1]); assert b.extinguish(t, method=method) and t.action == 1
            assert not t.has_status('burning')
        # Fire Aura must ignite exactly its recipients as well, not only Burn hits.
        b, a, ts = encounter('Fire Elemental', spells); b.rng = Step2FixedDice()
        b.begin_turn(a); b.end_turn(a)
        assert [t.has_status('burning') for t in ts] == [True, True, False, False]
        b.log.clear(); b.begin_turn(ts[1])
        assert fix_damage_log(b) == [('d1', 2, 'fire')]
    check()
    for method in ('ignite', 'tick_burning', 'extinguish'):
        with monkeypatch.context() as patch:
            patch.setattr(Combat, method, lambda *args, **kwargs: None)
            with pytest.raises(AssertionError): check()
    for payload in ('burn', 'aura'):
        def omit(s):
            effects = s['attacks'][0]['effects'] if payload == 'burn' else s['traits'][0]['effects'][0]['apply']
            effects[:] = [p for p in effects if 'burning' not in p]
        with monkeypatch.context() as patch:
            fix_mutate_sheet(patch, 'Fire Elemental', omit)
            with pytest.raises(AssertionError): check()


def test_step2_fix9_vampire_bites_ally_grapple_and_preserves_alternatives(spells, monkeypatch):
    def check():
        for mode in ('ally', 'self', 'incapacitated', 'restrained', 'none'):
            b, a, ts = encounter('Vampire Spawn', spells); b.rng = Step2FixedDice(); t = ts[0]; a.hp -= 20
            if mode == 'ally':
                ally = Combatant.from_sheet(sheet('Bugbear Stalker'), 'bugbear', 'enemy'); b.combatants.append(ally)
                b.begin_turn(ally); b.use_action(ally, 'Quick Grapple', [t])
                assert t.has_condition_from('grappled', ally) and not t.has_condition_from('grappled', a)
            elif mode == 'self': b.weapon_attack(a, t, a.attacks[0])
            elif mode != 'none': t.conditions.add(mode)
            t.hp = t.max_hp = 100000; b.log.clear(); b.begin_turn(a)
            block = a.actions[0]['effects'][0]
            probe = b.monster_instance(a, 'Bite legality', [block])
            assert (t in b.eligible(probe, block)) is (mode != 'none')
            b.use_action(a, 'Bite', [t] if mode != 'none' else None)
            if mode == 'none':
                assert fix_save_log(b) == [] and fix_damage_log(b) == []
                assert t.hp == 100000 and a.hp == a.max_hp - 20
            else:
                assert fix_save_log(b) == [('d0', 'con', 14, False)]
                assert fix_damage_log(b) == [('d0', 5, 'piercing'), ('d0', 6, 'necrotic')]
                assert (t.hp, t.max_hp, a.hp) == (99989, 99994, a.max_hp - 14)
                assert [x.hp for x in ts[1:]] == [100000] * 3
    check()
    with monkeypatch.context() as patch:
        def revert(s):
            block = s['actions'][0]['effects'][0]
            for owner, key in [(block, 'if'), (block['target'], 'eligible_if')]:
                owner[key] = owner[key].replace('target.has_condition(grappled)', 'target.has_condition_from(grappled, caster)')
        fix_mutate_sheet(patch, 'Vampire Spawn', revert)
        with pytest.raises(AssertionError): check()


def test_step2_fix7_tenfold_spore_damage_fails_exact_combat_probe(spells, monkeypatch):
    test_step2_engulf_whelm_spores_and_petrification(spells)
    with monkeypatch.context() as patch:
        fix_mutate_sheet(patch, 'Vrock', lambda s: s['actions'][0]['effects'][1]['apply'][0]['damage'].update(dice='10d10'))
        with pytest.raises(AssertionError): test_step2_engulf_whelm_spores_and_petrification(spells)


@pytest.mark.parametrize('immune', [False, True])
def test_step2_fix10_engulf_independent_state_capacity_and_escape(spells, immune):
    b, cube, ts = encounter('Gelatinous Cube', spells); b.rng = Step2FixedDice()
    victim = Combatant.from_sheet(sheet('Air Elemental'), 'air', 'party') if immune else ts[0]
    if immune:
        b.combatants[1] = victim
    victim.size = 'L'; victim.save_bonuses['dex'] = -100
    b.begin_turn(cube); b.use_action(cube, 'Engulf', [victim] + ts[1:])
    assert fix_save_log(b) == [(victim.id, 'dex', 12, False)]
    assert fix_damage_log(b) == [(victim.id, 6, 'acid')]
    assert victim.has_status_from('engulfed', cube)
    assert victim.has_condition('restrained') is (not immune)
    cube.conditions.add('stunned')
    b.end_turn(cube); b.log.clear(); b.begin_turn(cube)
    assert victim.has_status_from('engulfed', cube)
    assert victim.has_condition('restrained') is (not immune)
    assert fix_damage_log(b) == [(victim.id, 6, 'acid')]
    # Removing the condition cannot remove occupancy or any other consequence.
    victim.effects = [e for e in victim.effects if e.kind != 'apply_condition']
    cube.conditions.clear(); cube.action = 1; b.log.clear()
    b.use_action(cube, 'Engulf', ts[1:])
    assert fix_save_log(b) == [] and fix_damage_log(b) == []
    victim.spells = ['Bless']; victim.spell_slots = {1: 1}
    b.begin_turn(victim)
    assert not b.cast(victim, 'Bless', targets=[victim])
    victim.abilities.update(str=10, dex=100)
    assert b.escape(victim) and victim.action == 0
    assert victim.has_status('engulfed')  # Strength, not the very high Dexterity.
    b.log.clear(); b.begin_turn(cube)
    assert fix_damage_log(b) == [(victim.id, 6, 'acid')]
    b.begin_turn(victim); victim.abilities['str'] = 30
    assert b.escape(victim) and not victim.has_status('engulfed')
    assert not victim.has_condition('restrained')
    b.log.clear(); b.begin_turn(cube)
    assert fix_damage_log(b) == []
    b.use_action(cube, 'Engulf', ts[1:])
    assert fix_save_log(b) == [(t.id, 'dex', 12, False) for t in ts[1:]]


def test_step2_fix10_immune_engulf_reapplication_and_default_escape(spells):
    b, cube, ts = encounter('Gelatinous Cube', spells); b.rng = Step2FixedDice()
    t = ts[0]; t.condition_immunities = ['restrained']
    b.begin_turn(cube); b.use_action(cube, 'Engulf', [t])
    cube.action = 1; b.use_action(cube, 'Engulf', [t])
    assert len(t.status_effects('engulfed')) == 1
    b.log.clear(); b.begin_turn(cube)
    assert fix_damage_log(b) == [('d0', 6, 'acid')]
    t.abilities['str'] = 30
    b.begin_turn(t); b.policy.take_turn(b, t)
    assert not t.has_status('engulfed')
    assert [(e['dc'], e['success']) for e in b.log if e['event'] == 'escape'] == [(12, True)]


@pytest.mark.parametrize('name,path,value', [
    ('Aboleth', ('legendary', 'options', 1, 'heal'), '100d10'),
    ('Giant Spider', ('actions', 0, 'effects', 0, 'on_fail', 0, 'apply_condition', 'obstacle', 'hp'), 500),
    ('Giant Spider', ('actions', 0, 'effects', 0, 'on_fail', 0, 'apply_condition', 'obstacle', 'ac'), 99),
    ('Water Elemental', ('actions', 0, 'effects', 0, 'on_fail', 1, 'apply_condition', 'capacity'), 99),
    ('Gelatinous Cube', ('actions', 0, 'effects', 0, 'admission', 'capacity'), 99),
])
def test_step2_fix11_review_numeric_mutations(sources, name, path, value):
    s = sheet(name)
    node = s
    for key in path[:-1]: node = node[key]
    node[path[-1]] = value
    validate_sheet(s, '<schema-valid numeric mutant>')
    assert check_sheet(s, sources[name])


# Exact (monster, path) exceptions only, each requiring a substantive reason.
# No numeric exceptions remain. Booleans are flags, not numerical fields;
# source_ref/unsupported prose is metadata rather than executable numeric data.
STEP2_NUMERIC_ALLOWLIST = {}


def step2_numeric_mutations(node, path=()):
    import re
    from fractions import Fraction
    if isinstance(node, dict):
        for key, value in node.items(): yield from step2_numeric_mutations(value, path + (key,))
    elif isinstance(node, list):
        for i, value in enumerate(node): yield from step2_numeric_mutations(value, path + (i,))
    elif type(node) in (int, float):
        yield path, 'scalar', node + 1000
    elif isinstance(node, str) and re.fullmatch(r'\d+d\d+(?:\s*[+-]\s*\d+)?', node):
        # Exercise each constituent of a dice field, including embedded HP bonuses.
        for i, match in enumerate(re.finditer(r'\d+', node)):
            yield path, f'dice-part-{i}', node[:match.start()] + str(int(match[0]) + 1000) + node[match.end():]
    elif path == ('cr',):
        yield path, 'numeric-string', str(Fraction(node) + 1000)


def test_step2_fix11_systematic_numeric_mutation_scan(sources):
    fields = set(); rejected = allowed = 0; seen_allowlist = set()
    assert all(STEP2_NUMERIC_ALLOWLIST.values()), 'Every exception requires a reason'
    assert len(ORIGINAL + STEP2) == 70
    for name in ORIGINAL + STEP2:
        original = sheet(name)
        assert check_sheet(original, sources[name]) == []
        for path, variant, value in step2_numeric_mutations(original):
            fields.add((name, path))
            mutant = deepcopy(original); node = mutant
            for key in path[:-1]: node = node[key]
            node[path[-1]] = value
            if check_sheet(mutant, sources[name]):
                rejected += 1
            else:
                key = (name, path)
                assert key in STEP2_NUMERIC_ALLOWLIST, f'Uncaught number: {name} {path} {variant}'
                seen_allowlist.add(key); allowed += 1
    assert seen_allowlist == STEP2_NUMERIC_ALLOWLIST.keys(), 'Stale numeric exceptions'
    print(f'Numeric scan: 70 sheets, {len(fields)} fields, {rejected + allowed} mutations, {rejected} rejected, {allowed} allow-listed')
    assert len(fields) == 1760
    assert rejected == 2052
    assert allowed == 0


@pytest.mark.parametrize('size,charged,amount,prone', [
    ('L', True, 18, True), ('H', True, 12, False), ('G', True, 12, False),
    ('M', True, 18, True), ('L', False, 12, False),
])
def test_step2_fix12_minotaur_charge_damage_and_prone_share_size_gate(spells, size, charged, amount, prone):
    b, actor, ts = encounter('Minotaur of Baphomet', spells); b.rng = Step2FixedDice()
    t = ts[0]; t.size = size
    if charged: actor.statuses['charged'] = {}
    b.begin_turn(actor); b.weapon_attack(actor, t, actor.attacks[1])
    assert t.hp == 100000 - amount
    assert t.has_condition('prone') is prone
