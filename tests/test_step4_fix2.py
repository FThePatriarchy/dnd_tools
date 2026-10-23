"""Second re-review: exact rules regressions and in-memory reversion witnesses."""
import pytest

from engine import Combat, Combatant
from engine.builder import build
from engine.loader import load_spells
from engine.loader import ROOT, load_sheet
from engine.day_options import DayOptions
from engine.policy import ConservativePolicy
from engine.day import ClockRest, run_day
from test_step4_fixes import mutate


@pytest.fixture(scope="module")
def spells(): return load_spells()


def pc(cls="wizard", level=5):
    return Combatant.from_sheet(build(cls, level), cls, "party")


def test_step4_fix2_6_safe_time_economy(spells):
    w = pc()
    w.spells = ["Shield", "Counterspell"]
    combat = Combat([w], spells)
    combat.begin_turn(w)
    combat.cast(w, "Shield", slot=1)
    w.statuses["sneak_turn"] = combat.turn_index
    old_turn = combat.turn_index
    assert (w.reaction, w.slot_cast_turn, combat.can_cast(w, "Counterspell")) == (0, old_turn, False)
    combat.advance_time(0)
    assert (w.reaction, combat.turn_index) == (0, old_turn)
    w.action = w.bonus_action = 0
    w.surge_actions = 1
    w.extra_actions = [{"restricted_to": ["attack"]}]
    w.action_grants.add(("old",))
    combat.advance_time(100)
    assert (combat.time_rounds, combat.current) == (100, None)
    assert combat.turn_index == old_turn + 1
    assert (w.action, w.bonus_action, w.reaction, w.surge_actions) == (1, 1, 1, 0)
    assert (w.slot_cast_turn, w.extra_actions, w.action_grants, w.blocked_economy) == (None, [], set(), {})
    assert w.statuses["sneak_turn"] != combat.turn_index
    assert combat.can_cast(w, "Counterspell") is True
    assert combat.armor_class(w) == w.ac


@pytest.mark.parametrize("old,new", [
    ('self.reset_turn_economy(actor)', 'pass'),
    ('self.turn_index += 1  # Safe time leaves the old global spell/feature turn behind.', 'pass'),
])
def test_step4_fix2_6_mutation_proof(spells, monkeypatch, old, new):
    mutate(monkeypatch, Combat, "advance_time", old, new)
    with pytest.raises(AssertionError): test_step4_fix2_6_safe_time_economy(spells)


def test_step4_fix2_6_periodic_safe_turn_limits(spells, monkeypatch):
    w = pc(level=10); w.features = {}; w.spells = ["Cloudkill"]
    targets = [Combatant(str(i), max_hp=1000) for i in range(2)]
    combat = Combat([w, *targets], spells)
    monkeypatch.setattr(combat, "class_weapon_dice", lambda *a: 8)
    monkeypatch.setattr(combat, "saving_throw", lambda *a, **kw: False)
    combat.begin_turn(w); combat.cast(w, "Cloudkill", slot=5)
    combat.advance_time(3)
    assert [1000 - t.hp for t in targets] == [32, 32]


def test_step4_fix2_6_periodic_mutation_proof(spells, monkeypatch):
    mutate(monkeypatch, Combat, "advance_time", 'if periodic and actor.alive:\n                self.turn_index += 1',
           'if periodic and actor.alive:\n                pass')
    with pytest.raises(AssertionError): test_step4_fix2_6_periodic_safe_turn_limits(spells, monkeypatch)


@pytest.mark.parametrize("name", ["Cone of Cold", "Fireball", "Cold Breath"])
def test_step4_fix2_7_simultaneous_save_damage(spells, monkeypatch, name):
    caster = pc(level=10)
    if name == "Cold Breath":
        caster = Combatant.from_sheet(load_sheet(ROOT / "monsters/young_white_dragon.yaml"), "dragon", "party")
    else:
        caster.spells = [name]
        caster.features = {}
    targets = [Combatant(str(i), max_hp=1000) for i in range(4)]
    combat = Combat([caster, *targets], spells, area=lambda shape, size, n: n)
    calls = []
    def roll(*args):
        calls.append(args[1])
        return 8 * len(calls)
    monkeypatch.setattr(combat, "class_weapon_dice", roll)
    monkeypatch.setattr(combat, "saving_throw", lambda target, *a, **kw: target.id == "2")
    targets[3].resistances = ["fire" if name == "Fireball" else "cold"]
    combat.begin_turn(caster)
    if name == "Cold Breath": combat.use_action(caster, name)
    else: combat.cast(caster, name, slot=spells[name]["level"])
    assert [1000 - t.hp for t in targets] == [8, 8, 4, 4]
    assert len(calls) == 1


def test_step4_fix2_7_components_attacks_and_ticks(spells, monkeypatch):
    w = pc(level=10)
    w.features = {}
    w.spells = ["Flame Strike", "Scorching Ray", "Cloudkill"]
    targets = [Combatant(str(i), max_hp=1000) for i in range(2)]
    combat = Combat([w, *targets], spells)
    calls = []
    def roll(*args):
        calls.append(args[1])
        return 5 * len(calls)
    monkeypatch.setattr(combat, "class_weapon_dice", roll)
    monkeypatch.setattr(combat, "saving_throw", lambda *a, **kw: False)
    monkeypatch.setattr(combat.rng, "randint", lambda a, b: 20)
    combat.begin_turn(w); combat.cast(w, "Flame Strike", slot=5)
    assert [1000 - t.hp for t in targets] == [15, 15]
    assert calls == ["5d6", "5d6"]  # Independent components, each shared across victims.
    combat.begin_turn(w); combat.cast(w, "Scorching Ray", targets=[targets[0]] * 3, slot=2)
    assert [1000 - t.hp for t in targets] == [75, 15]
    assert len(calls) == 5  # Three attacks, not one shared roll.
    combat.begin_turn(w); combat.cast(w, "Cloudkill", slot=5)
    assert [1000 - t.hp for t in targets] == [105, 45]
    combat.begin_turn(targets[0]); combat.dispatch("end_of_turn_in_aura", who=targets[0])
    combat.begin_turn(targets[1]); combat.dispatch("end_of_turn_in_aura", who=targets[1])
    assert [1000 - t.hp for t in targets] == [140, 85]
    assert len(calls) == 8  # Initial cloud shared; two later ticks independent.


def test_step4_fix2_7_mutation_proof(spells, monkeypatch):
    mutate(monkeypatch, Combat, "resolve_block", ' or block["save"] and not block["attack"]', '')
    with pytest.raises(AssertionError): test_step4_fix2_7_simultaneous_save_damage(spells, monkeypatch, "Cone of Cold")


def test_step4_fix2_7_component_mutation_proof(spells, monkeypatch):
    mutate(monkeypatch, Combat, "execute", '(key, id(primitive), value.get("dice"), bonus)', '(value.get("dice"), bonus)')
    with pytest.raises(AssertionError): test_step4_fix2_7_components_attacks_and_ticks(spells, monkeypatch)


def test_step4_fix2_8_cheapest_equal_effect(spells):
    c = pc("cleric")
    mage = Combatant.from_sheet(load_sheet(ROOT / "monsters/mage.yaml"), "mage", "enemy")
    mage.hp = 40
    combat = Combat([c, mage], spells, policy=ConservativePolicy())
    combat.day_options = DayOptions()
    combat.encounters_remaining = 1
    combat.expected_remaining_rounds = lambda actor: 1
    before = c.spell_slots.copy(), combat.rng.getstate()
    scores = []
    for name in ("Hold Person", "Command"):
        spec = spells[name]
        scores.append([combat.expected_spell_damage(c, combat.scale(c, spec, slot), mage) for slot in (spec["level"], 3)])
        assert combat.available_slot(c, spec) == spec["level"]
    assert scores == [[11.71125, 11.71125], [11.1375, 11.1375]]
    assert (c.spell_slots, combat.rng.getstate()) == before
    # More real targets make a higher slot useful, without changing the forecast.
    combat.combatants += [Combatant.from_sheet(load_sheet(ROOT / "monsters/mage.yaml"), "mage2", "enemy")]
    assert combat.available_slot(c, spells["Hold Person"]) == 3
    combat.combatants.pop()
    c.features = {}
    c.hp = c.max_hp - 1
    assert combat.available_slot(c, spells["Cure Wounds"]) == 1
    c.hp = 1
    assert combat.available_slot(c, spells["Cure Wounds"]) == 3
    assert combat.available_slot(c, spells["Shield"]) == 1
    assert combat.available_slot(c, spells["Magic Missile"]) == 3


def test_step4_fix2_8_mutation_proof(spells, monkeypatch):
    mutate(monkeypatch, ConservativePolicy, "slot",
           'return next(slot for slot, value in scored if math.isclose(value, best, rel_tol=1e-12, abs_tol=1e-9))',
           'return slots[-1]')
    with pytest.raises(AssertionError): test_step4_fix2_8_cheapest_equal_effect(spells)


def hex_rest(spells, feature=None):
    w = pc(level=10)
    w.spells = ["Hex"]
    w.features = {feature: True} if feature else {}
    enemy = Combatant("enemy")
    combat = Combat([w, enemy], spells)
    combat.begin_turn(w); combat.cast(w, "Hex", targets=[enemy], slot=5)
    assert w.concentration == 1
    return combat, w


def test_step4_fix2_9_long_rest_clock_and_recovery(spells):
    combat, w = hex_rest(spells)
    f = Combatant("fighter", team="party", max_hp=44, hp=1, abilities={"str":19})
    f.max_hp = 34; f.abilities["str"] = 8
    f.exhaustion_level = 2; f.conditions.add("exhaustion")
    combat.combatants.append(f)
    rest = ClockRest(combat, [w, f], "long")
    assert w.concentration is None
    combat.advance_time(4800); rest.finish()
    assert (f.max_hp, f.hp, f.abilities["str"], f.exhaustion_level) == (44, 44, 19, 1)
    assert (f.last_long_rest_end, w.last_long_rest_end) == (4800, 4800)
    assert w.spell_slots == w.max_spell_slots
    with pytest.raises(ValueError, match="16 hours"): ClockRest(combat, [w, f], "long")
    assert (combat.time_rounds, combat.resting) == (4800, None)
    combat.advance_time(9599)
    with pytest.raises(ValueError, match="16 hours"): ClockRest(combat, [w, f], "long")
    combat.advance_time(1)
    rest = ClockRest(combat, [w, f], "long")
    combat.advance_time(4800); rest.finish()
    assert (combat.time_rounds, f.last_long_rest_end, f.exhaustion_level) == (19200, 19200, 0)
    assert "exhaustion" not in f.conditions


@pytest.mark.parametrize("feature", ["no_sleep", "concentration_while_asleep"])
def test_step4_fix2_9_specific_exceptions(spells, feature):
    combat, w = hex_rest(spells, feature)
    w.max_hp -= 10; w.abilities["str"] = 1; w.exhaustion_level = 2
    w.statuses["long_rest_no_restore"] = {"max_hp":True, "str":True, "exhaustion":True}
    reduced = w.max_hp
    rest = ClockRest(combat, [w], "long")
    combat.advance_time(4800); rest.finish()
    assert (w.concentration, w.max_hp, w.hp, w.abilities["str"], w.exhaustion_level) == (1, reduced, reduced, 1, 2)


def test_step4_fix2_9_interrupt_resume_and_short_benefit(spells):
    f = pc("fighter")
    f.limited_uses["action_surge"] = 0
    f.exhaustion_level = 2
    combat = Combat([f], spells)
    rest = ClockRest(combat, [f], "long")
    combat.advance_time(600)
    combat.damage(f, 1, "force")
    assert rest.interrupted == {f.id:600}
    assert f.limited_uses["action_surge"] == 1  # An hour before interruption earns a Short Rest.
    assert f.exhaustion_level == 2 and f.last_long_rest_end is None
    with pytest.raises(ValueError, match="interrupted"): rest.finish()
    combat.advance_time(10); rest.resume()
    assert rest.deadlines == {f.id:5410}
    combat.advance_time(4799)
    with pytest.raises(ValueError, match="not lasted"): rest.finish()
    combat.advance_time(1); rest.finish()
    assert (f.hp, f.exhaustion_level, f.last_long_rest_end) == (f.max_hp, 1, 5410)
    rest = ClockRest(combat, [f], "short")
    f.limited_uses["action_surge"] = 0
    combat.damage(f, 1, "force")
    combat.advance_time(600)
    with pytest.raises(ValueError, match="interrupted"): rest.finish()
    assert f.limited_uses["action_surge"] == 0
    with pytest.raises(ValueError, match="start over"): rest.resume()
    rest.abort()


def test_step4_fix2_9_interrupt_sources_and_day_wiring(spells, monkeypatch):
    w = pc(); w.spells = ["Fire Bolt", "Shield"]
    enemy = Combatant("enemy", max_hp=10000)
    combat = Combat([w, enemy], spells)
    rest = ClockRest(combat, [w], "long")
    combat.begin_turn(w); combat.cast(w, "Fire Bolt", targets=[enemy])
    assert rest.interrupted == {}
    rest.interrupt("exertion", exertion_rounds=599)
    assert rest.interrupted == {}
    rest.interrupt("exertion", exertion_rounds=600)
    assert rest.interrupted == {w.id:0}
    rest.resume()
    combat.begin_turn(w); combat.cast(w, "Shield", slot=1)
    assert rest.interrupted == {w.id:0}
    rest.resume()
    combat.run(1)
    assert rest.interrupted == {w.id:0}  # Initiative, even without damage to the resting PC.
    rest.abort()
    monkeypatch.setattr(Combat, "run", lambda *a: {"winner":"party", "rounds":1})
    definition = {"name":"rest history", "steps":[{"encounter":["ogre"]}, {"rest":"long"}, {"rest":"long"}]}
    with pytest.raises(ValueError, match="16 hours"):
        run_day([pc()], definition, spells, options=DayOptions(prebuffs=False))


def test_step4_fix2_9_interrupted_deadline_no_benefits(spells):
    w = pc("cleric"); w.spell_slots = dict.fromkeys(w.spell_slots, 0)
    combat = Combat([w], spells)
    rest = ClockRest(combat, [w], "long")
    combat.advance_time(600); combat.damage(w, 1, "force")
    combat.advance_time(4200)
    with pytest.raises(ValueError, match="interrupted"): rest.finish()
    assert (sum(w.spell_slots.values()), w.last_long_rest_end) == (0, None)


@pytest.mark.parametrize("method,old,new,probe", [
    ("__init__", 'compare_deadline(start, a.last_long_rest_end + 9600) < 0', 'False', "clock"),
    ("sleep", 'self.combat.end_spell(a.concentration)', 'pass', "clock"),
    ("finish", 'if self.interrupted:', 'if False:', "interrupt"),
])
def test_step4_fix2_9_mutation_proof(spells, monkeypatch, method, old, new, probe):
    mutate(monkeypatch, ClockRest, method, old, new)
    check = test_step4_fix2_9_long_rest_clock_and_recovery if probe == "clock" else test_step4_fix2_9_interrupted_deadline_no_benefits
    with pytest.raises((AssertionError, pytest.fail.Exception)): check(spells)


def test_step4_fix2_9_restoration_mutation_proof(spells, monkeypatch):
    import engine.day as day
    mutate(monkeypatch, day, "take_rest", 'exceptions = actor.statuses.get("long_rest_no_restore", {})',
           'exceptions = dict.fromkeys(("max_hp", "exhaustion", *actor.abilities), True)')
    with pytest.raises(AssertionError): test_step4_fix2_9_long_rest_clock_and_recovery(spells)


@pytest.mark.parametrize("path", ["explicit", "automatic", "policy", "settle", "helper"])
def test_step4_fix2_10_accumulated_revivify_boundary(spells, path):
    c = pc("cleric")
    c.spells = ["Revivify"]
    target = Combatant("dead", team="party")
    others = [Combatant(str(i)) for i in range(3)]
    combat = Combat([c, target, *others], spells)
    combat.death_rules = True
    combat.time_rounds = 100
    combat.kill(target)
    # Ten real rounds through end_turn's five fractional clock increments.
    for _ in range(10):
        for actor in combat.combatants:
            combat.begin_turn(actor); combat.end_turn(actor)
    assert 10 < combat.time_rounds - target.dead_at < 10 + 1e-9
    assert combat.can_revive(target) is True
    combat.begin_turn(c)
    before = c.spell_slots[3]
    if path == "explicit": combat.cast(c, "Revivify", targets=[target])
    elif path == "automatic": combat.cast(c, "Revivify")
    elif path == "policy": combat.policy.take_turn(combat, c)
    elif path == "settle": combat.settle_downed([c, target])
    else: assert combat.revive(c, target) is True
    assert (target.dead, target.hp, target.deaths, target.dead_at) == (False, 1, 1, None)
    assert c.spell_slots[3] == before - (path != "helper")
    combat.kill(target)
    combat.time_rounds += 10.01
    combat.begin_turn(c)
    assert combat.can_revive(target) is False
    assert combat.revive(c, target) is False
    before = c.spell_slots.copy()
    with pytest.raises(ValueError, match="one minute"): combat.cast(c, "Revivify", targets=[target])
    assert c.spell_slots == before


def test_step4_fix2_10_expiry_and_waking_below_boundary(spells):
    from engine.state import Effect, SpellInstance, compare_deadline
    a = Combatant("stable", team="party", hp=0)
    a.statuses["stable"] = {}
    a.stable_wake_at = 101
    combat = Combat([a], spells)
    combat.death_rules = True
    combat.time_rounds = 100
    effect = Effect("modify", {"stat":"ac", "op":"add", "value":1, "scope":"all"}, 0, "timer", expires_at=101)
    a.effects.append(effect)
    timer = SpellInstance(1, {"name":"timer", "duration":{"type":"rounds", "n":1}, "effects":[], "ends_on":[]}, a, 0, 0, 100)
    combat.instances[1] = timer
    for _ in range(7): combat.advance_time(1 / 7)
    assert 0 < 101 - combat.time_rounds < 1e-9
    assert (a.hp, timer.active, effect in a.effects) == (1, False, False)
    assert [compare_deadline(n, 101) for n in (100.99, 101 - 1e-12, 101, 101 + 1e-12, 101.01)] == [-1, 0, 0, 0, 1]


def test_step4_fix2_10_mutation_proof(spells, monkeypatch):
    mutate(monkeypatch, Combat, "can_revive", 'compare_deadline(self.time_rounds, target.dead_at + 10) <= 0',
           'self.time_rounds <= target.dead_at + 10')
    with pytest.raises(AssertionError): test_step4_fix2_10_accumulated_revivify_boundary(spells, "explicit")


def test_step4_fix2_10_expiry_mutation_proof(spells, monkeypatch):
    import engine.state as state
    import engine.combat as combat_module
    import engine.day_mechanics as day_mechanics
    raw = lambda now, deadline: (now > deadline) - (now < deadline)
    for module in (state, combat_module, day_mechanics): monkeypatch.setattr(module, "compare_deadline", raw)
    with pytest.raises(AssertionError): test_step4_fix2_10_expiry_and_waking_below_boundary(spells)
