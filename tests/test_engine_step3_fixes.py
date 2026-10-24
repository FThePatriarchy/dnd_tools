"""Review fixes: exact behavioral oracles, each killed by an in-memory regression."""
import inspect
import textwrap
from copy import deepcopy

import pytest

from engine import Combat, Combatant
from engine.state import Effect, SpellInstance
from test_engine_step3 import arena, spell_specs, NoReactions
from test_engine_step3_damage import BalancedRolls


def mutation_fails(monkeypatch, owner, method, good, bad, oracle):
    """Compile only an in-memory method mutant; never alter the working tree."""
    original = getattr(owner, method)
    source = textwrap.dedent(inspect.getsource(original))
    assert good in source, (method, good)
    namespace = dict(original.__globals__)
    exec(compile(source.replace(good, bad, 1), '<step3-review-mutant>', 'exec'), namespace)
    with monkeypatch.context() as patch:
        patch.setattr(owner, method, namespace[method])
        with pytest.raises(AssertionError):
            oracle()


def test_step3_fix8_mirror_interception_ends_invisibility(monkeypatch):
    def oracle():
        b,c,(d,)=arena('Invisibility',enemies=1)
        c.spells.append('Mirror Image'); d.spells=['Mirror Image']; d.spell_slots={2:1}
        inst=b.cast(c,'Invisibility',[c])
        assert c.has_condition('invisible')
        b.begin_turn(d); b.cast(d,'Mirror Image'); b.begin_turn(c)
        b.rng=BalancedRolls(20,True)
        assert b.attack(c,d,100,lambda *_: pytest.fail('duplicate must intercept')) is False
        assert sum(e['event']=='mirror_intercept' for e in b.log)==1
        assert c.has_condition('invisible') is False
        assert inst.active is False
    oracle()
    mutation_fails(monkeypatch,Combat,'attack',
        'self.end_activity_effects(attacker)\n        return False',
        'pass\n        return False',oracle)


def test_step3_fix2_circle_protects_only_successful_magical_saves(monkeypatch):
    def oracle():
        for magical,success,expected in [(True,False,8),(True,True,0),(False,True,1),(False,False,2)]:
            b,c,(d,)=arena('Fireball',enemies=1); b.rng=BalancedRolls(10,False)
            d.effects.append(Effect('magic_saves',{},-999,'probe'))
            d.save_bonuses['dex']=100 if success else -100
            spec=deepcopy(b.spells['Fireball'])
            if not magical: spec.pop('level')
            block=spec['effects'][0]
            block['target']={'select':'single','filter':['creature'],'affects':'any'}
            block['on_fail']=[{'damage':{'amount':8 if magical else 2,'type':'fire' if magical else 'bludgeoning'}}]
            inst=SpellInstance(999,spec,c,3,b.turn_index,b.time_rounds)
            b.resolve_block(inst,block,'on_cast',{},[d])
            assert d.max_hp-d.hp==expected,(magical,success)
            assert not any(e['event']=='trait' and e.get('name')=='Evasion' for e in b.log)
    oracle()
    mutation_fails(monkeypatch,Combat,'resolve_block',
        'magic_protection = "level" in instance.spec and',
        'evasion = bool(evasion) or any(e.kind == "magic_saves" for e in target.active_effects)\n                magic_protection =',oracle)

    mutation_fails(monkeypatch,Combat,'resolve_block',
        'magic_protection = "level" in instance.spec and',
        'magic_protection =',oracle)


def test_step3_fix3_aid_overlap_duration_and_rescue(monkeypatch):
    def oracle():
        b,c,(d,)=arena('Aid',enemies=1); d.max_hp=100; d.hp=50
        first=b.cast(c,'Aid',[d],slot=2)
        assert (d.max_hp,d.hp)==(105,55)
        b.begin_turn(c); second=b.cast(c,'Aid',[d],slot=2)
        assert (d.max_hp,d.hp)==(105,55)
        assert [(e.source,e.suppressed) for e in d.effects if e.kind=='max_hp']==[(first.id,True),(second.id,False)]
        b.begin_turn(c); stronger=b.cast(c,'Aid',[d],slot=3)
        assert (d.max_hp,d.hp)==(110,60)
        b.end_spell(stronger.id)
        assert (d.max_hp,d.hp)==(105,55)
        b.end_spell(second.id)
        assert (d.max_hp,d.hp)==(105,55)
        b.time_rounds=4800; b.expire('end_of_turn',c)
        assert first.active is False
        assert (d.max_hp,d.hp)==(100,50)
        b.begin_turn(c); d.hp=0; d.conditions.add('unconscious')
        try: rescue=b.cast(c,'Aid',[d],slot=2)
        except ValueError as exc: raise AssertionError('Aid must accept unconscious recipients') from exc
        assert (d.max_hp,d.hp,d.has_condition('unconscious'))==(105,5,False)
        b.damage(d,3,'force'); assert d.hp==2
        b.end_spell(rescue.id)
        assert (d.max_hp,d.hp,d.has_condition('unconscious'))==(100,0,True)
    oracle()
    mutation_fails(monkeypatch,Combat,'refresh_spell_effects',
        'for e in actor.active_effects if e.kind == "max_hp"',
        'for e in actor.effects if e.kind == "max_hp"',oracle)
    mutation_fails(monkeypatch,Combat,'eligible',
        ' or "max_hp" in p','',oracle)
    mutation_fails(monkeypatch,Combat,'refresh_spell_effects',
        'actor.hp + delta','actor.hp + max(0, delta)',oracle)


def test_step3_fix4_control_depends_on_its_own_active_charm(monkeypatch):
    def oracle():
        for name in ['Suggestion','Crown of Madness','Hypnotic Pattern']:
            b,c,(d,ally)=arena(name,enemies=2); d.condition_immunities=['charmed']
            d.attacks=[{'name':'Probe','kind':'melee','to_hit':100,'effects':[]}]
            inst=b.cast(c,name,None if name=='Hypnotic Pattern' else [d])
            assert not d.has_condition('charmed')
            assert not d.has_condition('incapacitated')
            assert b.modifier(d,'speed',30)==30
            assert not b.turn_rules(d).get('forced_melee')
            assert not any(e.kind=='pacify' for e in d.active_effects)
            b.begin_turn(d)
            assert d.action==1
            assert not any(e['event']=='attack' for e in b.log)
            assert b.attack(d,c,100,lambda *_: None) is True
        b,c,(d,other)=arena('Hypnotic Pattern',enemies=2)
        b.area=lambda *_: [1]  # Explicit placement: victim, not either caster.
        inst=b.cast(c,'Hypnotic Pattern')
        assert d.has_condition('charmed') and d.has_condition('incapacitated')
        assert b.modifier(d,'speed',30)==0
        # A second caster avoids ending the original caster's concentration.
        other.spells=['Calm Emotions'];other.spell_slots={2:1}
        b.begin_turn(other);calm=b.cast(other,'Calm Emotions',choices={'mode':'immune'})
        assert not d.has_condition('charmed') and not d.has_condition('incapacitated')
        assert b.modifier(d,'speed',30)==30
        assert b.attack(d,c,100,lambda *_: None) is True
        b.end_spell(calm.id)
        assert d.has_condition('charmed') and d.has_condition('incapacitated')
        b.restore(d,'charmed')
        assert not d.has_condition('incapacitated') and b.modifier(d,'speed',30)==30
        # Another source's charm must not revive the removed source's riders.
        d.effects.append(Effect('apply_condition',{'condition':'charmed','caster_id':other.id},999,'probe'))
        assert not d.has_condition('incapacitated')
    oracle()
    mutation_fails(monkeypatch,Combat,'execute',
        'effect.requires_condition = primitive.get("requires_condition")',
        'effect.requires_condition = None',oracle)

    mutation_fails(monkeypatch,Combat,'condition_sources',
        ' and actor.condition_effective(e, actor.active_effects)',
        '',oracle)


def test_step3_fix5_polymorph_replaces_statistics_and_executes_beast_traits(monkeypatch):
    def oracle():
        for form in ['wolf','brown bear','riding horse']:
            b,c,(d,ally)=arena('Polymorph',enemies=2); b.rng=BalancedRolls(10,False)
            c.spell_dc=100; b.policy.legendary_resistance=lambda *_: False
            d.extra_attack=3;d.save_bonuses['wis']=12;d.save_proficiencies=['wis']
            d.features={'magic_resistance':True};d.vulnerabilities=['fire']
            d.spells=['Fireball'];d.spell_slots={3:2};d.limited_uses={'legendary_resistance':3}
            d.routines=[['Fireball']];d.replacements=['Fireball'];d.legendary={'uses':3};d.legendary_remaining=3
            d.innate_spells={'Fireball':1};d.spell_resources={'Fireball':'Fireball'}
            original=deepcopy({k:getattr(d,k) for k in ['extra_attack','save_bonuses','save_proficiencies','features','vulnerabilities','spells','spell_slots','limited_uses','routines','replacements','legendary','legendary_remaining','innate_spells','spell_resources','abilities','size','cr','level']})
            hp=d.hp;kind=d.creature_type;alignment=d.alignment;hd=(d.hit_die,d.hit_dice)
            inst=b.cast(c,'Polymorph',[d],choices={'form':form})
            assert d.extra_attack==1 and d.save_bonuses=={} and d.save_proficiencies==[]
            assert d.vulnerabilities==[] and d.spell_slots=={} and d.limited_uses=={}
            assert not d.features.get('magic_resistance')
            assert d.spells==[] and d.innate_spells=={} and d.spell_resources=={}
            assert d.replacements==[] and d.legendary=={} and d.legendary_remaining==0
            assert (d.hp,d.creature_type,d.alignment,(d.hit_die,d.hit_dice))==(hp,kind,alignment,hd)
            assert d.temp_hp=={'wolf':11,'brown bear':22,'riding horse':13}[form]
            assert d.multiattack==(['Bite','Claw'] if form=='brown bear' else [])
            assert d.features==({'pack_tactics':True} if form=='wolf' else {})
            ally.attacks=[{'name':'Ally','kind':'melee','to_hit':1,'effects':[]}]
            b.begin_turn(d);b.log.clear();b.weapon_action(d)
            attacks=[e for e in b.log if e['event']=='attack']
            assert len(attacks)==(2 if form=='brown bear' else 1)
            assert attacks[0]['advantage'] is (form=='wolf')
            assert c.has_condition('prone') is (form!='riding horse')
            b.end_spell(inst.id)
            assert all(getattr(d,k)==v for k,v in original.items())
            assert d.temp_hp==0 and d.hp==hp
    oracle()
    from engine.spell_mechanics import SpellMechanics
    mutation_fails(monkeypatch,SpellMechanics,'reconcile_transform',
        'for k, v in stats.items(): setattr(target, k, deepcopy(v))',
        'for k, v in stats.items():\n                if k not in {\"extra_attack\", \"features\"}: setattr(target, k, deepcopy(v))',oracle)
    forms=spell_specs()['Polymorph']['effects'][0]['on_fail'][0]['transform']['forms']
    with monkeypatch.context() as patch:
        patch.setitem(forms['wolf'],'features',{})
        with pytest.raises(AssertionError): oracle()
    with monkeypatch.context() as patch:
        patch.setitem(forms['brown bear'],'multiattack',[])
        with pytest.raises(AssertionError): oracle()
    with monkeypatch.context() as patch:
        patch.setitem(forms['wolf']['attacks'][0],'effects',forms['wolf']['attacks'][0]['effects'][:1])
        with pytest.raises(AssertionError): oracle()



    with monkeypatch.context() as patch:
        patch.setitem(forms['brown bear']['attacks'][1],'effects',forms['brown bear']['attacks'][1]['effects'][:1])
        with pytest.raises(AssertionError): oracle()


def test_step3_fix6_dispel_tracks_ongoing_self_spell_ownership(monkeypatch):
    def oracle():
        b,c,(d,other)=arena('Aura of Vitality',enemies=2)
        c.hp-=20;inst=b.cast(c,'Aura of Vitality',[c])
        assert inst.active and c.concentration==inst.id
        assert not any(e.source==inst.id for e in c.effects)
        assert inst.affected['_owner']=={c}
        d.spells=['Dispel Magic'];d.spell_slots={3:2}
        b.begin_turn(d);b.cast(d,'Dispel Magic',[other],slot=3)
        assert inst.active and c.concentration==inst.id
        b.begin_turn(d);dispel=b.cast(d,'Dispel Magic',[c],slot=3)
        assert dispel is not None
        assert inst.active is False and c.concentration is None
        assert inst.affected=={}
        assert [e['spell'] for e in b.log if e['event']=='dispel']==['Aura of Vitality']
        assert not any(e['event']=='check' for e in b.log)  # Level 3 ends automatically.
        hp=c.hp;b.begin_turn(c);assert c.hp==hp
    oracle()
    mutation_fails(monkeypatch,Combat,'cast',
        'instance.affected["_owner"] = {caster}',
        'instance.affected["_owner"] = set()',oracle)
    mutation_fails(monkeypatch,Combat,'execute',
        'any(target in recipients for recipients in other.affected.values())',
        'any(e.source == other.id for e in target.effects)',oracle)


def test_step3_fix9_polymorph_casting_gate_is_not_vacuous(monkeypatch):
    def oracle():
        b,c,(d,)=arena('Polymorph',enemies=1)
        d.spells=['Fireball'];d.spell_slots={3:2}
        b.begin_turn(d)
        assert b.current is d and d.action==1 and b.can_cast(d,'Fireball',3) is True
        b.begin_turn(c);inst=b.cast(c,'Polymorph',[d],choices={'form':'wolf'})
        assert d.temp_hp==11 and d.spells==[] and d.spell_slots=={}
        b.begin_turn(d)
        # Isolate the anatomy gate from replaced spell statistics. Supply every
        # other can_cast prerequisite; disabling turn_rules must now allow it.
        d.spells=['Fireball'];d.spell_slots={3:2}
        assert b.current is d and d.action==1 and d.alive and not d.has_condition('incapacitated')
        assert d.slot_cast_turn!=b.turn_index
        assert b.can_cast(d,'Fireball',3) is False
        assert b.cast(d,'Fireball',slot=3) is None
        assert d.action==1 and d.spell_slots=={3:2}
        b.end_spell(inst.id)
        assert d.spells==['Fireball'] and d.spell_slots=={3:2}
        assert b.can_cast(d,'Fireball',3) is True
    oracle()
    with monkeypatch.context() as patch:
        patch.setattr(Combat,'turn_rules',lambda *_: {})
        with pytest.raises(AssertionError): oracle()


def test_step3_fix10_default_hostile_area_never_fills_with_allies(monkeypatch):
    def oracle():
        from engine.loader import ROOT, load_sheet
        for with_ally in [False,True]:
            for count in [1,2]:
                for seed in range(10):
                    mage=Combatant.from_sheet(load_sheet(ROOT/'monsters/mage.yaml'),'mage','enemy')
                    pcs=[Combatant.from_sheet(load_sheet(ROOT/'characters/fighter5.yaml'),f'pc{i}','party') for i in range(count)]
                    ally=Combatant('ally',team='enemy')
                    b=Combat([mage,*([ally] if with_ally else []),*pcs],spell_specs(),seed=seed,policy=NoReactions())
                    b.begin_turn(mage);hp=mage.hp;ally_hp=ally.hp
                    inst=b.cast(mage,'Fireball',slot=4)
                    assert inst is not None
                    assert (mage.hp,ally.hp)==(hp,ally_hp)
                    assert {e['target'] for e in b.log if e['event']=='damage'}=={p.id for p in pcs}
                    assert len(inst.area_members['blast'])==count
        # A caller-supplied count or indices deliberately permits spill-over.
        for area in [lambda *args: args[-1], lambda *args: range(args[-1])]:
            b,c,(d,)=arena('Fireball',enemies=1);b.area=area;b.rng=BalancedRolls(10,False)
            b.cast(c,'Fireball',slot=3)
            assert c.max_hp-c.hp==8 and d.max_hp-d.hp==8
        # Fixed self-origin emanation honors its own include/exclude rules.
        b,c,(d,)=arena('Fireball',enemies=1)
        spec=deepcopy(b.spells['Fireball']);block=spec['effects'][0]
        block['target'].update(shape='emanation',origin='caster',include_caster=True)
        inst=SpellInstance(999,spec,c,3,b.turn_index,b.time_rounds)
        assert set(b.area_members(inst,block,b.eligible(inst,block)))=={c,d}
        block['target']['include_caster']=False
        assert b.area_members(inst,block,b.eligible(inst,block))==[d]
        block['target'].pop('origin')
        assert b.area_members(inst,block,b.eligible(inst,block))==[d]
        # Unavoidable ambient auras retain friendly membership too.
        d.team=c.team
        assert b.area_members(inst,block,b.eligible(inst,block))==[d]
    oracle()
    mutation_fails(monkeypatch,Combat,'area_members',
        'if (self.area is area_heuristic or getattr(self.area, "avoids_allies", False)) and hostile and not fixed_emanation:',
        'if False:',oracle)


def test_step3_fix1_scope_additions_and_combat_mechanics(monkeypatch):
    from engine import spell_catalog
    from engine.loader import ROOT, read_yaml
    from engine.spell_validation import source_spells, source_errors
    expected={'Modify Memory':'combat',"Nystul's Magic Aura":'combat',
              'Create or Destroy Water':'partial','Speak with Plants':'partial',
              'Stone Shape':'partial','Arcane Lock':'partial','Planar Ally':'partial'}
    def oracle():
        raw=source_spells(); records={s['name']:s for s in read_yaml(ROOT/'spell_scope.yaml')['spells']}
        specs=spell_specs()
        assert len(specs)==245
        for name,scope in expected.items():
            assert records[name]['scope']==spell_catalog.classify(raw[name])['scope']==scope
            if raw[name]['level']<=5:
                assert name in specs
                assert source_errors(specs[name])==[]
        b,c,(d,)=arena('Modify Memory',enemies=1);b.rng=BalancedRolls(10,False)
        inst=b.cast(c,'Modify Memory',[d])
        assert inst.spec['effects'][0]['save'].get('advantage_if')=='target.team != caster.team'
        assert [e['success'] for e in b.log if e['event']=='save']==[False]
        assert d.has_condition('charmed') and d.has_condition('incapacitated')
        b.damage(d,1,'force')
        assert not inst.active and c.concentration is None
        assert not d.has_condition('incapacitated')
        b.begin_turn(c);inst=b.cast(c,'Modify Memory',[d]);c.spells.append('Aid')
        b.begin_turn(c);b.cast(c,'Aid',[d],slot=2)
        assert not inst.active and not d.has_condition('charmed')
        b,c,(d,)=arena("Nystul's Magic Aura",enemies=1)
        inst=b.cast(c,"Nystul's Magic Aura",[d],choices={'type':'beast'})
        assert d.creature_type=='humanoid' and d.magical_type=='beast'
        b.begin_turn(c)
        try: b.cast(c,"Nystul's Magic Aura",[d],choices={'type':'humanoid'})
        except ValueError: pass
        else: raise AssertionError('Mask must exclude the actual type, not the current mask')
        c.spells.append('Hold Person')
        try: b.cast(c,'Hold Person',[d])
        except ValueError: pass
        else: raise AssertionError('Mask must change spell targeting')
        b.end_spell(inst.id)
        assert d.magical_type=='humanoid'
        assert b.cast(c,'Hold Person',[d]) is not None
        b,c,(d,)=arena("Nystul's Magic Aura",enemies=1)
        b.cast(c,"Nystul's Magic Aura",[c],choices={'type':'fiend'})
        c.spells.append('Protection from Evil and Good');b.begin_turn(c)
        b.cast(c,'Protection from Evil and Good',[d])
        assert b.condition_immune(d,'charmed',True,c) is True
        assert b.condition_immune(d,'charmed',False,c) is False
        b,c,(d,)=arena('Create or Destroy Water',enemies=1)
        b.ignite(d,c);inst=b.cast(c,'Create or Destroy Water',slot=2)
        assert inst.spec['effects'][0]['target']['size_ft']==35
        assert not d.has_status('burning')
        for name in ['Speak with Plants','Stone Shape','Arcane Lock']:
            b,c,_=arena(name)
            assert b.cast(c,name) is not None
            assert b.spells[name]['unsupported']
    oracle()
    with monkeypatch.context() as patch:
        patch.setattr(spell_catalog,'UTILITY',spell_catalog.UTILITY|{'Modify Memory'})
        with pytest.raises(AssertionError): oracle()
    with monkeypatch.context() as patch:
        patch.delitem(spell_specs(),'Stone Shape')
        with pytest.raises(AssertionError): oracle()
    save=spell_specs()['Modify Memory']['effects'][0]['save']
    with monkeypatch.context() as patch:
        patch.delitem(save,'advantage_if');patch.setitem(save,'auto_success_if','target.team != caster.team')
        with pytest.raises(AssertionError): oracle()


def test_step3_fix7_all_numeric_leaves_and_fraction_source_values(monkeypatch):
    import re
    import engine.spell_validation as validation
    from engine import summon_validation
    # This oracle neither calls the production coverage walker nor asks the
    # mutation iterator which paths should exist.
    def leaves(value,path=()):
        if isinstance(value,dict):
            return {p:v for k,x in value.items() for p,v in leaves(x,path+(k,)).items()}
        if isinstance(value,list):
            return {p:v for i,x in enumerate(value) for p,v in leaves(x,path+(i,)).items()}
        return {path:value}
    def coverage_oracle():
        sample={'cr':'1/4','level':'30','dice':'roll 2d6 + 3 damage',
                'components':{'m':'worth 50 GP'},'unsupported':['within 60 feet'],
                'nested':[0,-2,0.5,True,None]}
        for spec in [sample,*spell_specs().values()]:
            expected={p:v for p,v in leaves(spec).items() if type(v) in (int,float) or isinstance(v,str) and re.search('[0-9]',v)}
            scanned=list(validation.numeric_fields(spec))
            assert dict(scanned)==expected
            assert len(scanned)==len(expected)
            assert validation.numeric_coverage_errors(spec)==[]
        assert [(p,v) for p,v,_ in validation.mutants(sample) if p==('cr',)]==[(('cr',),'2/4'),(('cr',),'1/5')]
        assert [(p,v) for p,v,_ in validation.mutants(sample) if p==('dice',)]==[(('dice',),'roll 3d6 + 3 damage'),(('dice',),'roll 2d7 + 3 damage'),(('dice',),'roll 2d6 + 4 damage')]
    def source_oracle():
        spec=deepcopy(spell_specs()['Polymorph'])
        forms=spec['effects'][0]['on_fail'][0]['transform']['forms']
        assert validation.source_errors(spec)==[]
        for form in ['wolf','brown bear','riding horse']:
            original=forms[form]['cr'];forms[form]['cr']='30'
            errors=validation.source_errors(spec)
            assert errors and any('cr' in e and 'beast stat expectation' in e for e in errors)
            forms[form]['cr']=original
    coverage_oracle();source_oracle()
    original=validation.numeric_fields
    # Recreate the old iterator's blind spot. The independent coverage oracle
    # (and the production audit) must notice, even before running mutants.
    with monkeypatch.context() as patch:
        patch.setattr(validation,'numeric_fields',lambda spec,path=(): ((p,v) for p,v in original(spec,path) if not (p[-1]=='cr' and isinstance(v,str))))
        with pytest.raises(AssertionError): coverage_oracle()
        assert 'numeric coverage' in str(validation.source_errors(spell_specs()['Polymorph']))
    fixed=summon_validation.fixed_number
    with monkeypatch.context() as patch:
        patch.setattr(summon_validation,'fixed_number',lambda path,sheet,raw: sheet['cr'] if path==('cr',) else fixed(path,sheet,raw))
        with pytest.raises(AssertionError): source_oracle()


def test_step3_fix5_original_passive_traits_suspend_and_restore(monkeypatch):
    from engine.sheets import effect_block
    def oracle():
        b,c,(d,)=arena('Polymorph',enemies=1);b.rng=BalancedRolls(10,False)
        block=effect_block('aura',target={'select':'single','filter':['creature'],'affects':'enemy'},apply=[{'damage':{'amount':7,'type':'force'}}])
        block['event']='start_of_turn(caster)'
        d.traits=[{'name':'Original Aura','cost':'free','passive':True,'effects':[block]}]
        passive=b.monster_instance(d,'Original Aura',[block]);passive.spec['monster_passive']=True
        inst=b.cast(c,'Polymorph',[d],choices={'form':'wolf'})
        hp=c.hp;b.begin_turn(d)
        assert c.hp==hp and d.traits==[]
        b.end_spell(inst.id);b.begin_turn(d)
        assert c.hp==hp-7 and d.traits[0]['name']=='Original Aura'
    oracle()
    mutation_fails(monkeypatch,Combat,'dispatch',
        'if instance.spec.get("monster_passive") and not any(t["name"] == instance.spec["name"] for t in instance.caster.traits):',
        'if False:',oracle)
