"""Completion regressions: every embedded form, source-derived exact attack means."""
import re
from copy import deepcopy
from statistics import mean
import pytest
from engine.state import Effect
from engine.summoning import take_summoned_turns
from engine.spell_validation import source_spells, source_errors
from engine.summon_validation import referenced_stat_block, xmm_stat_blocks
from test_engine_step3 import arena, spell_specs, cast_fixture
from test_engine_step3_damage import BalancedRolls


def summons():
    return [(name,form,slot) for name,s in spell_specs().items() for b in s["effects"] for p in b["apply"] if "summon" in p for form in p["summon"]["forms"] for slot in sorted({s["level"],5})]


def summon_cast(b,c,name,form,slot):
    if b.spells[name]["casting_time"] in {"minute","minutes","hour","hours"}:
        b.current=None; return b.prepare(c,name,slot=slot,choices={"form":form})
    return b.cast(c,name,slot=slot,choices={"form":form})


@pytest.mark.parametrize("name,form,slot",summons())
def test_step3_every_embedded_form_is_targetable_and_actions_fire(name,form,slot):
    b,c,ds=arena(name);b.rng=BalancedRolls(10,False)
    inst=summon_cast(b,c,name,form,slot); assert inst and inst.summoned
    for spirit in inst.summoned:
        assert spirit in b.enemies(ds[0])
        assert spirit.team==c.team and spirit.summoner_id==c.id
    take_summoned_turns(b,c)
    for spirit in inst.summoned:
        if spirit.statuses.get("summon_rules",{}).get("familiar"):
            assert not spirit.attacks and any(e["event"]=="help" and e["actor"]==spirit.id for e in b.log)
        for a in spirit.actions:
            b.begin_turn(spirit)
            targets=None if a["effects"][0]["target"]["select"] in {"self","area"} else [ds[0]]
            if not a.get("resource") or spirit.limited_uses[a["resource"]]: assert b.use_action(spirit,a["name"],targets)
        for t in spirit.traits:
            if t.get("passive"):
                b.weapon_attack(ds[0],spirit,{"name":"Probe","kind":"melee","to_hit":100,"effects":[]})
                if "on_damaged" in t["effects"][0]["event"]: b.damage(spirit,1,"force",ds[0])
            elif t.get("trigger")=="creature_turn_start": b.begin_turn(ds[0])
        required={(a["name"],bl["id"]) for a in spirit.actions+spirit.traits for bl in a["effects"]}
        fired={(e["spell"],e["block"]) for e in b.log if e["event"]=="effect_block"}
        assert required<=fired, required-fired
        if not spirit.statuses.get("summon_rules",{}).get("persistent"):
            b.end_spell(inst.id);assert not spirit.alive


def attack_source(name,form,attack_name):
    raw=source_spells()[name]
    if name in {"Animate Dead","Phantom Steed"}:
        ref={"skeleton":"Skeleton","zombie":"Zombie","horse":"Riding Horse"}[form]
        return next(a for a in xmm_stat_blocks()[ref]["action"] if a["name"]==attack_name),False
    ref=referenced_stat_block(raw)
    return next(a for a in ref["action"] if a["name"]==attack_name or a["name"].split(" (")[0]==attack_name),True


@pytest.mark.parametrize("name,form,slot",[x for x in summons() if x[0]!="Find Familiar"])
def test_step3_all_summon_primary_damage_exact_from_source(name,form,slot):
    probe,c,_=arena(name,enemies=1);inst=summon_cast(probe,c,name,form,slot)
    primary=inst.summoned[0].attacks[0]
    raw,scales=attack_source(name,form,primary["name"])
    text=str(raw["entries"])
    components=[]
    if name=="Animate Objects":
        displays=re.findall(r"\|([\d]+)d(\d+) \+ (\d+)\}",text)
        n,sides,flat=map(int,displays[{"medium":0,"large":1,"huge":2}[form]])
        n+=slot-5;components=[(n,sides,flat+c.spell_mod)]
    else:
        for m in re.finditer(r"\{@damage (\d+)d(\d+)(?: \+ (\d+))?( \+ summonSpellLevel)?\}",text):
            n,sides,flat,lev=m.groups();components.append((int(n),int(sides),int(flat or 0)+(slot if lev else 0)))
    assert components
    normal=sum(n*(d+1)/2+f for n,d,f in components)
    critical=sum(n*(d+1)+f for n,d,f in components)
    hit=min(.95,max(.05,(21+inst.summoned[0].attacks[0]["to_hit"]-10)/20))
    attacks=sum(s.extra_attack for s in inst.summoned)
    expected=attacks*((hit-.05)*normal+.05*critical)
    samples=[]
    for natural in range(1,21):
        for high in (False,True):
            b,c,(d,)=arena(name,seed=natural,enemies=1);b.rng=BalancedRolls(natural,high)
            inst=summon_cast(b,c,name,form,slot);b.log.clear()
            for spirit in inst.summoned:
                for _ in range(spirit.extra_attack):b.weapon_attack(spirit,d,spirit.attacks[0])
            samples.append(sum(e["amount"] for e in b.log if e["event"]=="damage" and e["target"]==d.id))
    assert mean(samples)==pytest.approx(expected,abs=1e-10)


def test_step3_aid_ends_arcane_dice_and_death_ward():
    b,c,(d,*_)=arena("Aid");hp=d.hp;maximum=d.max_hp
    inst=b.cast(c,"Aid",[d],slot=5);assert d.hp==hp+20 and d.max_hp==maximum+20
    b.end_spell(inst.id);assert d.max_hp==maximum and d.hp==hp
    b,c,_=arena("Arcane Vigor");before=c.hit_dice; hp=c.hp
    b.cast(c,"Arcane Vigor",slot=5);assert c.hit_dice==before-5 and c.hp>hp
    b,c,(d,*_)=arena("Death Ward");b.cast(c,"Death Ward",[d]);b.damage(d,d.hp+20,"force")
    assert d.hp==1;b.damage(d,1,"force");assert d.hp==0


def test_step3_delayed_acid_is_not_on_miss_and_guardian_budget():
    b,c,(d,*_)=arena("Melf's Acid Arrow");c.spell_attack_bonus=-100;b.rng=BalancedRolls(10,False)
    b.cast(c,"Melf's Acid Arrow",[d]);assert d.max_hp-d.hp==2
    b.begin_turn(d);b.end_turn(d);assert d.max_hp-d.hp==2
    b,c,ds=arena("Guardian of Faith");inst=b.cast(c,"Guardian of Faith")
    for d in (ds[0],ds[1],ds[0]): b.begin_turn(d)
    assert not inst.active and inst.damage_total==60


def test_step3_protection_is_source_typed_and_contagion_tallies():
    b,c,(d,*_)=arena("Protection from Evil and Good");b.cast(c,"Protection from Evil and Good",[d]);c.creature_type="fiend"
    assert b.condition_immune(d,"charmed",True,c)
    c.creature_type="humanoid";assert not b.condition_immune(d,"charmed",True,c)
    b,c,(d,*_)=arena("Contagion");inst=b.cast(c,"Contagion",[d])
    for _ in range(3):b.begin_turn(d);b.end_turn(d)
    assert d.has_condition("poisoned") and not any("tally_save" in e.data for e in d.effects)
    assert inst.spec["duration"]=={"type":"hours","n":168}


def test_step3_polymorph_retains_hp_and_reverts_on_temp_hp_loss():
    b,c,(d,*_)=arena("Polymorph");hp=d.hp;old=d.abilities.copy();kind=d.creature_type
    inst=b.cast(c,"Polymorph",[d],choices={"form":"wolf"});assert d.hp==hp and d.temp_hp==11
    assert d.creature_type==kind  # Casting gate has an eligible-caster oracle in fix9.
    b.damage(d,12,"force");assert d.hp==hp-1 and not d.temp_hp and d.abilities==old


def test_step3_banishing_threshold_sees_damage_and_lightning_replaces_weapon():
    b,c,(d,*_)=arena("Banishing Smite");d.hp=55;b.rng=BalancedRolls(10,False)
    inst=cast_fixture(b,c,"Banishing Smite",5);assert inst and d.removed and d.hp==50
    b,c,ds=arena("Lightning Arrow");b.rng=BalancedRolls(10,False)
    attack={"name":"Bow","kind":"ranged","to_hit":100,"effects":[{"damage":{"dice":"10d10","bonus":0,"type":"piercing"}}]}
    b.replace_weapon_attack(c,ds[0],attack,3)
    assert not any(e["event"]=="damage" and e["type"]=="piercing" for e in b.log)
    assert ds[0].max_hp-ds[0].hp==4


def test_step3_complete_required_inventory():
    from engine.step3_report import audit
    report=audit()
    # Required: in-scope spells of level 0-5; loaded adds the 28 reviewed level 6-9 spells.
    assert report["required"]==245 and report["loaded"]==273 and not report["missing"] and not report["failures"]


def test_step3_gaseous_dismissal_zero_hp_and_contagion_resists_restoration():
    b,c,(d,*_)=arena("Gaseous Form");inst=b.cast(c,"Gaseous Form",[d]);b.begin_turn(d)
    assert b.dismiss_form(d,inst.id) and not d.action and not b.turn_rules(d).get("no_spells")
    b.begin_turn(c);inst=b.cast(c,"Gaseous Form",[d]);b.damage(d,d.hp,"force")
    assert not b.turn_rules(d).get("no_spells")
    b,c,(d,*_)=arena("Contagion");b.cast(c,"Contagion",[d]);c.spells.append("Lesser Restoration")
    b.begin_turn(c);b.cast(c,"Lesser Restoration",[d],choices={"condition":"poisoned"})
    assert d.has_condition("poisoned")
    b.begin_turn(c);d.save_bonuses["con"]=100
    b.cast(c,"Lesser Restoration",[d],choices={"condition":"poisoned"});assert not d.has_condition("poisoned")


def test_step3_fire_shield_attribution_and_only_one_weapon_enchanted():
    b,c,(d,*_)=arena("Fire Shield");b.rng=BalancedRolls(20,False);b.cast(c,"Fire Shield")
    b.weapon_attack(d,c,{"name":"Probe","kind":"melee","to_hit":100,"effects":[]})
    fire=[e for e in b.log if e["event"]=="damage"]
    assert len(fire)==1 and fire[0]["amount"]==2 and fire[0]["source"]==c.id
    b,c,_=arena("Magic Weapon");b.cast(c,"Magic Weapon",[c],slot=5)
    club,bow=c.attacks
    assert b.enchanted_attack(c,club)["to_hit"]==club["to_hit"]+2
    assert b.enchanted_attack(c,bow)==bow


def test_step3_explosive_rune_waits_and_hand_is_destructible():
    b,c,_=arena("Glyph of Warding");b.current=None
    inst=b.prepare(c,"Glyph of Warding");assert not any(e["event"]=="damage" for e in b.log)
    b.dispatch("glyph_triggered");assert any(e["event"]=="damage" for e in b.log)
    assert not inst.active
    before=len(b.log);b.dispatch("glyph_triggered");assert len(b.log)==before
    b,c,_=arena("Bigby's Hand");inst=b.cast(c,"Bigby's Hand");(hand,)=inst.summoned
    assert hand.ac==20 and hand.hp==c.max_hp
    b.damage(hand,hand.hp,"force");assert not inst.active


def test_step3_familiar_recast_replaces_persistent_body():
    b,c,_=arena("Find Familiar");first=summon_cast(b,c,"Find Familiar","owl",1)
    b.current=None;second=b.prepare(c,"Find Familiar",choices={"form":"cat"})
    assert all(s.removed for s in first.summoned) and second.summoned[0].alive


@pytest.mark.parametrize("name",["True Strike","Shillelagh","Swift Quiver"])
@pytest.mark.parametrize("level",[1,5,11,17])
def test_step3_weapon_spell_damage_exact(name,level):
    upgrade=sum(level>=n for n in (5,11,17)); samples=[]
    if name=="True Strike": normal=2.5+4+upgrade*3.5; critical=5+4+upgrade*7;count=1
    elif name=="Shillelagh":
        normal=[4.5,5.5,6.5,7][upgrade]+4;critical=2*(normal-4)+4;count=1
    else:normal=4.5;critical=9;count=2
    for natural in range(1,21):
        for high in (False,True):
            b,c,(d,)=arena(name,level=level,enemies=1);b.rng=BalancedRolls(natural,high)
            b.cast(c,name,[c] if name=="Shillelagh" else [d])
            if name=="Shillelagh":b.weapon_attack(c,d,c.attacks[0])
            samples.append(d.max_hp-d.hp)
    assert mean(samples)==pytest.approx(count*(.9*normal+.05*critical),abs=1e-10)


def test_step3_divine_smite_upcast_does_not_scale_type_bonus_and_stagger_exact_end():
    b,c,(d,*_)=arena("Divine Smite");b.rng=BalancedRolls(10,False);d.creature_type="fiend"
    cast_fixture(b,c,"Divine Smite",5);assert d.max_hp-d.hp==7
    b,c,(d,*_)=arena("Staggering Smite");b.rng=BalancedRolls(10,False)
    inst=cast_fixture(b,c,"Staggering Smite",4);assert d.has_condition("stunned")
    b.end_turn(c);b.begin_turn(c);assert d.has_condition("stunned")
    b.end_turn(c);assert not d.has_condition("stunned")


def test_step3_critical_trigger_does_not_double_hail_save_damage_or_arrow_splash():
    b,c,(d,*_)=arena("Hail of Thorns");b.rng=BalancedRolls(20,False)
    cast_fixture(b,c,"Hail of Thorns",1);assert d.max_hp-d.hp==1
    b,c,ds=arena("Lightning Arrow");b.rng=BalancedRolls(20,False)
    attack={"name":"Bow","kind":"ranged","to_hit":100,"effects":[]}
    b.replace_weapon_attack(c,ds[0],attack,3)
    assert ds[0].max_hp-ds[0].hp==8 and ds[1].max_hp-ds[1].hp==2


@pytest.mark.parametrize("name",["Bestow Curse","Alter Self"])
def test_step3_special_damage_modes_have_source_exact_means(name):
    from engine.spell_validation import text_entries
    raw=source_spells();samples=[]
    if name=="Bestow Curse":
        text=text_entries(raw[name]["entries"])+" "+text_entries(raw["Inflict Wounds"]["entries"])
        terms=[tuple(map(int,m)) for m in re.findall(r"\{@damage (\d+)d(\d+)\}",text)]
        expected=sum(n*(d+1)/2 for n,d in terms)
        for high in (False,True):
            b,c,(d,)=arena(name,enemies=1);b.rng=BalancedRolls(10,high)
            b.cast(c,name,[d],choices={"curse":"damage"});c.spells.append("Inflict Wounds")
            b.begin_turn(c);b.log.clear();b.cast(c,"Inflict Wounds",[d])
            samples.append(sum(e["amount"] for e in b.log if e["event"]=="damage" and e["target"]==d.id))
    else:
        n,sides=map(int,re.search(r"\{@damage (\d+)d(\d+)\}",text_entries(raw[name]["entries"])).groups())
        expected=.9*(n*(sides+1)/2+4)+.05*(n*(sides+1)+4)
        for natural in range(1,21):
            for high in (False,True):
                b,c,(d,)=arena(name,enemies=1);b.rng=BalancedRolls(natural,high)
                c.attacks=[{"name":"Unarmed Strike","kind":"melee","to_hit":100,"effects":[{"damage":{"dice":"1d1","bonus":0,"type":"bludgeoning"}}]}]
                b.cast(c,name);b.begin_turn(c);b.weapon_action(c)
                samples.append(d.max_hp-d.hp)
    assert mean(samples)==pytest.approx(expected,abs=1e-10)
