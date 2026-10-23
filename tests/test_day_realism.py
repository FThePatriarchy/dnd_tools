"""Exact day-rule regressions; legacy tests retain their original numeric oracles."""
from dataclasses import asdict, replace
import random

import pytest

from engine import Combat, Combatant, dice
from engine.builder import build, load_build
from engine.day import run_day, simulate_day, take_rest, validate_day
from engine.day_options import DayOptions
from engine.loader import load_spells, ValidationError
from engine.policy import Policy, ConservativePolicy


@pytest.fixture(scope="module")
def spells(): return load_spells()


def pc(cls="fighter", level=5, identifier=None):
    return Combatant.from_sheet(build(cls, level), identifier or cls, "party")


def combat_with_rules(actors, spells, **options):
    combat = Combat(actors, spells)
    combat.day_options = DayOptions(**options)
    combat.death_rules = combat.day_options.death
    return combat


def day(*steps): return {"name":"realism test", "steps":list(steps)}


def test_day_options_defaults_legacy_validation():
    assert all(asdict(DayOptions())[n] for n in ("clock","prebuffs","death","backgrounds","engagement","spending"))
    assert not any(asdict(DayOptions.legacy())[n] for n in ("clock","prebuffs","death","backgrounds","engagement","spending"))
    for options in ({"clock":1}, {"gap_minutes":-1}, {"gap_minutes":float("nan")}, {"screen":True}, {"targeting":"bad"}, {"oops":True}):
        with pytest.raises((ValueError, ValidationError)):
            validate_day({**day({"encounter":["ogre"]}), "options":options})


def test_b1_clock_durations_concentration_and_actual_rounds(spells, monkeypatch):
    w, c = pc("wizard"), pc("cleric")
    seen = []

    class BuffOnce(Policy):
        def precombat_buffs(self, combat, party, phase):
            if phase != "day_start": return
            combat.begin_turn(w); combat.cast(w,"Mage Armor",targets=[w],slot=1)
            combat.begin_turn(c); combat.cast(c,"Shield of Faith",targets=[w],slot=1)
            combat.current = None

    def scripted(combat, *args):
        seen.append((combat.armor_class(w), c.concentration is not None, combat.time_rounds))
        return {"winner":"party", "rounds":[2,3,4][len(seen)-1]}

    monkeypatch.setattr(Combat,"run",scripted)
    result = run_day([w,c], day({"encounter":["ogre"]},{"encounter":["ogre"]},{"rest":"short"},{"encounter":["ogre"]}),
                     spells, policy=BuffOnce(), options=DayOptions(gap_minutes=1))
    assert seen == [(17, True, 0), (17, True, 12), (15, False, 625)]
    assert result.elapsed_seconds == 629*6
    assert result.encounters[0].end_seconds == 12
    assert result.encounters[1].start_seconds == 72


def test_b1_false_life_is_instantaneous_temp_hp(spells):
    w = pc("wizard")
    w.spells = ["False Life"]
    combat = combat_with_rules([w],spells)
    combat.begin_turn(w); combat.cast(w,"False Life",slot=1)
    temp = w.temp_hp
    assert spells["False Life"]["duration"] == {"type":"instant"}
    assert temp >= 6 and not any(i.active for i in combat.instances.values())
    combat.advance_time(600)
    assert w.temp_hp == temp


def test_b1_long_rest_clock_and_no_encounter_wipe(spells, monkeypatch):
    a = pc()
    def scripted(combat,*args): return {"winner":"party","rounds":2}
    monkeypatch.setattr(Combat,"run",scripted)
    result = run_day([a],day({"encounter":["ogre"]},{"rest":"long"},{"encounter":["ogre"]}), spells,
                     options=DayOptions(prebuffs=False))
    assert result.elapsed_seconds == (2+100+4800+2)*6


def test_b2_prebuff_real_slots_ev_duration_and_no_recast(spells):
    w, c, f = pc("wizard"), pc("cleric"), pc()
    combat = combat_with_rules([w,c,f],spells)
    combat.future_encounters = [(0,3),(100,3),(800,3)]
    before = w.spell_slots.copy(), c.spell_slots.copy()
    combat.policy.precombat_buffs(combat,[w,c,f],"day_start")
    assert combat.armor_class(w) == 15
    assert w.spell_slots[1] == before[0][1]-1
    assert all(a.spell_hp_bonus == 5 for a in (w,c,f))
    assert c.spell_slots[2] == before[1][2]-1
    used = w.spell_slots.copy(), c.spell_slots.copy()
    combat.policy.precombat_buffs(combat,[w,c,f],"before_encounter")
    assert (w.spell_slots,c.spell_slots) == used
    spec = combat.scale(w,spells["Mage Armor"],1)
    # Fresh target: same scorer, fewer covered encounters => lower prevention EV.
    w.effects.clear()
    long = combat.expected_spell_damage(w,spec,w,precombat=True)
    combat.future_encounters = [(0,3),(5000,3),(6000,3)]
    assert 0 < combat.expected_spell_damage(w,spec,w,precombat=True) < long


def test_b2_false_life_and_heroism_like_buff_slots(spells):
    w = pc("wizard"); w.spells = ["False Life"]
    combat = combat_with_rules([w],spells)
    combat.future_encounters = [(0,3)]
    combat.policy.precombat_buffs(combat,[w],"day_start")
    assert w.temp_hp >= 6 and w.spell_slots[1] == 3
    c = pc("cleric",10); c.spells = ["Heroism"]
    combat = combat_with_rules([c],spells)
    combat.future_encounters = [(0,4)]
    combat.policy.precombat_buffs(combat,[c],"before_encounter")
    assert c.concentration is not None and sum(c.spell_slots.values()) == sum(c.max_spell_slots.values())-1


@pytest.mark.parametrize("natural,failures,hp",[(1,2,0),(9,1,0),(10,0,0),(20,0,1)])
def test_b3_death_save_exact_faces(spells,monkeypatch,natural,failures,hp):
    f = pc(); f.hp = 0
    combat = combat_with_rules([f],spells)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b:natural)
    combat.death_save(f)
    assert (f.hp,f.death_failures) == (hp,failures)
    assert f.death_successes == int(natural==10)


def test_b3_three_successes_stable_wake_then_rest(spells,monkeypatch):
    f = pc(); f.hp = 0; f.conditions.update({"unconscious","prone"})
    combat = combat_with_rules([f],spells)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b:10 if b==20 else 2)
    for _ in range(3): combat.death_save(f)
    assert f.has_status("stable") and f.stable_wake_at == 1200
    assert (f.death_successes,f.death_failures) == (0,0)
    combat.advance_time(600)
    assert f.hp == 0
    combat.advance_time(600)
    assert f.hp == 1 and not f.has_status("stable")
    take_rest([f],"long",random.Random(1))
    assert f.hp == f.max_hp


def test_b3_damage_failures_crit_massive_and_dead_healing(spells):
    f = pc(); f.hp = 0
    combat = combat_with_rules([f],spells)
    combat.apply_damage(f,1)
    assert f.death_failures == 1 and not f.dead
    combat._critical_damage = True
    combat.apply_damage(f,1)
    assert f.dead and f.deaths == 1
    combat.heal(f,1000)
    take_rest([f],"long",random.Random(1))
    assert f.hp == 0 and f.dead
    g = pc(identifier="g"); combat.combatants.append(g)
    combat.apply_damage(g,g.hp+g.max_hp)
    assert g.dead and g.deaths == 1 and g.downs == 1


def test_b3_revivify_window_real_slot_and_death_report(spells):
    c, f = pc("cleric"), pc()
    c.spells.append("Revivify")
    combat = combat_with_rules([c,f],spells)
    combat.kill(f)
    combat.time_rounds = 10
    combat.begin_turn(c)
    assert combat.cast(c,"Revivify",targets=[f],slot=3)
    assert not f.dead and f.hp == 1 and f.deaths == 1 and c.spell_slots[3] == 1
    combat.kill(f); combat.time_rounds += 10.01; combat.begin_turn(c)
    with pytest.raises(ValueError,match="one minute"): combat.cast(c,"Revivify",targets=[f],slot=3)
    assert f.dead and c.spell_slots[3] == 1


@pytest.mark.parametrize("cantrip",[False,True])
def test_b3_postcombat_stabilization_medicine_or_cantrip(spells,monkeypatch,cantrip):
    c, f = pc("cleric"), pc()
    c.spells = ["Spare the Dying"] if cantrip else []
    f.hp = 0
    combat = combat_with_rules([c,f],spells)
    monkeypatch.setattr(combat.rng,"randint",lambda a,b:10 if b==20 else 1)
    combat.settle_downed([c,f])
    assert f.has_status("stable") and not f.dead and f.hp == 0
    assert f.stable_wake_at == 600


def test_b3_default_monsters_avoid_downed_unless_no_other_target(spells):
    f, w = pc(), pc("wizard"); w.hp = 0
    e = Combatant("enemy")
    combat = combat_with_rules([f,w,e],spells)
    assert combat.policy.weapon_target(combat,e,combat.enemies(e)) is f
    f.dead=True
    assert combat.policy.weapon_target(combat,e,combat.enemies(e)) is w
    f.dead=False
    combat.day_options=replace(combat.day_options,attack_downed=True,targeting="focus_low_hp")
    assert combat.policy.weapon_target(combat,e,combat.enemies(e)) is w


def test_b4_background_defaults_caps_reallocation_and_alternative():
    for cls, primary in (("fighter","str"),("rogue","dex"),("wizard","int"),("cleric","wis")):
        s = load_build(f"{cls}_3")
        assert s["abilities"][primary] == 17
        assert s["abilities"]["con"] == (14 if cls=="wizard" else 15)
        old = load_build(f"{cls}_3",background=False)
        assert old["abilities"][primary] == 15
    f = load_build("fighter_10")
    assert f["abilities"]["str"] == 20 and f["abilities"]["con"] == 18
    w = build("wizard",1,choices={"background":{"int":1,"dex":1,"con":1}})
    assert [w["abilities"][a] for a in ("int","dex","con")] == [16,15,14]
    w = build("wizard",1,abilities=dict(str=10,dex=10,con=20,int=20,wis=10,cha=10),choices={"ability_method":"assigned"})
    assert w["abilities"]["con"] == w["abilities"]["int"] == 20


@pytest.mark.parametrize("invalid",[{"int":3},{"int":2},{"int":True,"con":2},{"bogus":1,"int":2}])
def test_b4_background_validation(invalid):
    with pytest.raises(ValidationError): build("wizard",3,choices={"background":invalid})


def test_b5_screen_overflow_reach_flying_ranged_and_front_down(spells):
    f, w = pc(), pc("wizard")
    attack = {"name":"claw","kind":"melee","reach_ft":5,"to_hit":5,"effects":[]}
    foes = [Combatant(f"e{i}",attacks=[attack]) for i in range(3)]
    combat = combat_with_rules([f,w,*foes],spells)
    assert f.position == "front" and w.position == "back"
    assert combat.reachable(foes[0],[f,w],attack) == [f]
    assert combat.reachable(foes[1],[f,w],attack) == [f]
    assert combat.reachable(foes[2],[f,w],attack) == [f,w]
    assert combat.reachable(foes[0],[f,w],{**attack,"reach_ft":10}) == [f,w]
    assert combat.reachable(foes[0],[f,w],{**attack,"kind":"ranged"}) == [f,w]
    assert combat.reachable(foes[0],[f,w],None) == [f,w]  # spells
    foes[0].engagement_tags=["teleport"]
    assert combat.reachable(foes[0],[f,w],attack) == [f,w]
    foes[0].engagement_tags=[]; foes[0].movement_modes={"fly":30}
    assert combat.reachable(foes[0],[f,w],attack) == [f,w]
    foes[0].movement_modes={}; f.hp=0
    assert combat.reachable(foes[0],[f,w],attack) == [f,w]


def test_b5_targeting_threat_low_hp_random_and_reachability(spells):
    f, w = pc(), pc("wizard"); w.hp=2
    e = Combatant("e")
    combat = combat_with_rules([f,w,e],spells)
    combat.damage_dealt={f.id:50,w.id:10}
    assert combat.policy.weapon_target(combat,e,[f,w]) is f
    combat.day_options=replace(combat.day_options,targeting="focus_low_hp")
    assert combat.policy.weapon_target(combat,e,[f,w]) is w
    combat.day_options=replace(combat.day_options,targeting="random")
    assert {combat.policy.weapon_target(combat,e,[f,w]) for _ in range(40)} == {f,w}


def test_b6_conservative_specific_retained_slots_diagnostic(spells):
    c, w, f = pc("cleric",10),pc("wizard",10),pc("fighter",10)
    c.hp=int(c.max_hp*.4)
    enemy=Combatant("enemy",max_hp=200,attacks=[{"name":"hit","kind":"melee","to_hit":8,"effects":[{"damage":{"dice":"2d8","bonus":5,"type":"slashing"}}]}])
    policy=ConservativePolicy()
    combat=combat_with_rules([c,w,f,enemy],spells)
    combat.policy=policy
    combat.encounters_remaining=5
    combat.slots_at_start={a.id:a.spell_slots.copy() for a in (c,w)}
    # The reviewed boosted-level-10 failure retained ~16.7 slots: exhausted
    # per-encounter budgets must not block spending while the Cleric is at 40%.
    c.spell_slots={1:1,2:1,3:2,4:2,5:2}; w.spell_slots={1:2,2:2,3:2,4:2,5:1}
    assert sum(c.spell_slots.values())+sum(w.spell_slots.values()) == 17
    assert policy.emergency(combat,c)
    assert policy.allow_spell(combat,c,spells["Healing Word"])
    combat.begin_turn(c)
    before=sum(c.spell_slots.values())
    policy.take_turn(combat,c)
    assert sum(c.spell_slots.values()) < before
    assert c.hp >= c.max_hp*.5
    combat.day_options=replace(combat.day_options,spending=False)
    c.hp=int(c.max_hp*.4)
    assert not policy.emergency(combat,c)
    for actor in (c,w,f): actor.hp=actor.max_hp
    combat.encounters_remaining=1
    combat.day_options=replace(combat.day_options,spending=True)
    assert policy.allow_spell(combat,w,spells["Fireball"])


def test_b_options_individually_selectable_day_and_cli(tmp_path):
    import subprocess, sys, json
    for option in ("clock","prebuffs","death","backgrounds","engagement","spending"):
        opts = replace(DayOptions(), **{option:False})
        assert getattr(opts,option) is False
    command=[sys.executable,"-m","engine.day","--party","fighter_3:front","wizard_3:back","--day","easy_day","--runs","1","--json","--legacy"]
    summary=json.loads(subprocess.run(command,check=True,capture_output=True,text=True).stdout)
    assert summary["options"] == asdict(DayOptions.legacy())
    assert simulate_day([{"build":"fighter_3","position":"back"}],"easy_day",1).runs == 1


def test_b_switches_disable_behaviour_not_just_metadata(spells,monkeypatch):
    w = pc("wizard")
    armor = []
    class CastArmor(Policy):
        def precombat_buffs(self,combat,party,phase):
            if phase == "day_start":
                combat.begin_turn(w); combat.cast(w,"Mage Armor",targets=[w],slot=1)
    def scripted(combat,*args):
        armor.append(combat.armor_class(w))
        return {"winner":"party","rounds":1}
    monkeypatch.setattr(Combat,"run",scripted)
    run_day([w],day({"encounter":["ogre"]},{"encounter":["ogre"]}),spells,
            policy=CastArmor(),options=DayOptions(clock=False))
    assert armor == [15,12]
    w = pc("wizard"); armor.clear()
    run_day([w],day({"encounter":["ogre"]}),spells,policy=CastArmor(),options=DayOptions(prebuffs=False))
    assert armor == [12] and w.spell_slots[1] == 4
    f = pc(); e=Combatant("enemy")
    combat=combat_with_rules([f,e],spells,death=False,engagement=False)
    combat.apply_damage(f,2*f.max_hp)
    assert f.hp == 0 and not f.dead and f.deaths == 0
    assert combat.reachable(e,[f],{"kind":"melee"}) == [f]
    assert combat.day_options.targeting == "focus_low_hp"


def test_b5_random_targeting_ev_probe_does_not_spend_rng(spells):
    f, w = pc(),pc("wizard")
    e=pc("wizard"); e.id="enemy"; e.team="enemy"
    combat=combat_with_rules([f,w,e],spells,targeting="random")
    state=combat.rng.getstate()
    value=combat.expected_spell_damage(e,combat.scale(e,spells["Fireball"],3),f)
    assert value > 0 and combat.rng.getstate() == state


def test_b3_indomitable_death_save_retains_other_die(spells,monkeypatch):
    from engine.state import Effect
    f=pc(level=9); f.hp=0
    f.effects.append(Effect("disadvantage",{"on":"saves","scope":"death"},0,"test"))
    combat=combat_with_rules([f],spells)
    draws=iter([1,2,20])
    monkeypatch.setattr(combat.rng,"randint",lambda a,b:next(draws))
    combat.death_save(f)
    assert f.hp == 0 and f.death_successes == 1 and f.death_failures == 0
    assert f.limited_uses["indomitable"] == 0
    assert next(e for e in combat.log if e["event"]=="death_save")["total"] == 11


def test_b3_aid_revival_resets_saves_and_clock_off_keeps_stability(spells):
    from engine.day import cleanup_encounter
    c,f=pc("cleric"),pc()
    combat=combat_with_rules([c,f],spells)
    f.hp=0; f.death_failures=2
    combat.begin_turn(c); combat.cast(c,"Aid",targets=[f],slot=2)
    assert f.hp == 5 and (f.death_successes,f.death_failures) == (0,0)
    f.hp=0
    combat.stabilize(f)
    wake=f.stable_wake_at
    cleanup_encounter(combat,preserve_death=True)
    assert f.has_status("stable") and f.stable_wake_at == wake


def test_b3_life_drain_zero_maximum_counts_death(spells):
    from engine.loader import ROOT,load_sheet
    f=pc(); f.max_hp=f.hp=5
    e=Combatant.from_sheet(load_sheet(ROOT/"monsters/wight.yaml"),"wight","enemy")
    combat=combat_with_rules([f,e],spells)
    combat._monster_attack=e,e.features["life_drain"]["attacks"][0]
    combat.monster_drain(e,f,{"necrotic":5})
    assert f.max_hp == 0 and f.dead and f.deaths == 1


def test_b1_zero_gap_is_not_a_turn_boundary(spells):
    from engine.state import Effect
    w=pc("wizard")
    combat=combat_with_rules([w],spells)
    effect=Effect("modify",{"stat":"ac","op":"add","value":5,"scope":"all"},0,"shield",("start_of_turn",w.id,1))
    w.effects.append(effect)
    combat.advance_time(0)
    assert combat.time_rounds == 0 and w.turns_taken == 0 and effect in w.effects
    combat.advance_time(1)
    assert effect not in w.effects


def test_b3_friendly_area_damage_at_zero_is_still_damage(spells,monkeypatch):
    w,f=pc("wizard"),pc()
    f.hp=0; f.conditions.update({"unconscious","prone"})
    combat=combat_with_rules([w,f],spells)
    combat.area=lambda shape,size,n:n
    monkeypatch.setattr(combat.rng,"randint",lambda a,b:1)
    combat.begin_turn(w); combat.cast(w,"Fireball",slot=3)
    assert f.hp == 0 and f.death_failures == 1 and not f.dead


def test_b4_all_capped_asis_fail_cleanly():
    with pytest.raises(ValidationError,match="no uncapped ability"):
        build("wizard",10,abilities=dict.fromkeys(("str","dex","con","int","wis","cha"),20),choices={"ability_method":"assigned"})


def test_b6_conservative_does_not_upcast_non_scaling_reactions(spells):
    w=pc("wizard",10); w.hp=1
    combat=combat_with_rules([w],spells)
    combat.policy=ConservativePolicy(); combat.encounters_remaining=1
    assert combat.policy.slot(combat,w,spells["Shield"],[1,2,3,4,5]) == 1
    combat.expected_remaining_rounds=lambda actor:2
    assert combat.policy.slot(combat,w,spells["Magic Missile"],[1,2,3,4,5]) == 1  # No enemy: no useful extra darts.
    combat.combatants.append(Combatant("enemy", max_hp=100))
    assert combat.policy.slot(combat,w,spells["Magic Missile"],[1,2,3,4,5]) == 5
