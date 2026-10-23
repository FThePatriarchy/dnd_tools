"""Review regressions and executable, in-memory mutation witnesses."""
from copy import deepcopy
import inspect
import json
from pathlib import Path
import textwrap
import zipfile

import pytest

from engine import Combat, Combatant, dice
from engine import builder
from engine.loader import load_spells, ValidationError
from engine.policy import Policy
from engine.state import Effect


@pytest.fixture(scope="module")
def spells(): return load_spells()


def built(name, level):
    return Combatant.from_sheet(builder.build(name, level, background=False), name, "party")


def pool_probe(spells, allocations=None):
    c = built("cleric", 3)
    allies = [Combatant(str(i), team="party", max_hp=40, hp=0) for i in range(3)]
    combat = Combat([c, *allies], spells)
    combat.begin_turn(c)
    combat.use_action(c, "Preserve Life", allies, allocations=allocations)
    return combat, c, allies


def test_step4_fix1_allocation_and_recovery(spells):
    _, c, allies = pool_probe(spells, {"0": 5, "1": 5, "2": 5})
    assert [a.hp for a in allies] == [5, 5, 5]
    assert c.limited_uses["channel_divinity"] == 1
    assert [a.hp for a in pool_probe(spells)[2]] == [5, 5, 5]
    assert [a.hp for a in pool_probe(spells,{})[2]] == [0, 0, 0]
    c = built("cleric", 3)
    c.spell_slots = dict.fromkeys(c.spell_slots, 0)
    c.limited_uses["channel_divinity"] = 1
    allies = [Combatant(str(i), team="party", max_hp=40, hp=0) for i in range(2)]
    combat = Combat([c, *allies], spells)
    combat.policy.recover_downed(combat, [c, *allies])
    assert [a.hp for a in allies] == [8, 7]
    assert c.limited_uses["channel_divinity"] == 0


@pytest.mark.parametrize("allocation", [{"0": -1}, {"0": 21}, {"0": True}, {"0": 16}, {"unknown": 1}, [1, 2]])
def test_step4_fix1_invalid_allocation_is_atomic(spells, allocation):
    c = built("cleric", 3)
    a = Combatant("0", team="party", max_hp=40, hp=0)
    combat = Combat([c, a], spells)
    combat.begin_turn(c)
    with pytest.raises(ValueError, match="allocation"):
        combat.use_action(c, "Preserve Life", [a], allocations=allocation)
    assert (a.hp, c.action, c.limited_uses["channel_divinity"]) == (0, 1, 2)


def mutate(monkeypatch, owner, name, old, new):
    original = getattr(owner, name)
    source = textwrap.dedent(inspect.getsource(original))
    assert old in source
    namespace = {}
    exec(compile(source.replace(old, new), "<in-memory review mutation>", "exec"), original.__globals__, namespace)
    monkeypatch.setattr(owner, name, namespace[name])


def test_step4_fix1_mutation_proof(spells, monkeypatch):
    mutate(monkeypatch, Combat, "execute", 'amount = instance.choices["_pool_" + block][target.id]',
           'amount = min(remaining, max(0, target.max_hp // 2 - target.hp))')
    with pytest.raises(AssertionError): test_step4_fix1_allocation_and_recovery(spells)


def reroll_probe(spells, monkeypatch, feature, advantage=False):
    f = built("fighter", 10 if feature == "inspiration" else 9)
    combat = Combat([f], spells)
    f.effects.append(Effect("advantage" if advantage else "disadvantage", {"on": "saves", "scope": "dex"}, 0, "test"))
    if feature == "inspiration":
        f.statuses["heroic_inspiration"] = {}
        f.limited_uses["indomitable"] = 0
    draws = iter([1, 2, 20 if feature == "inspiration" else 19])
    monkeypatch.setattr(combat.rng, "randint", lambda a, b: next(draws))
    assert not combat.saving_throw(f, "dex", 15 if feature == "inspiration" else 25)
    event = next(e for e in combat.log if e.get("name") == ("Heroic Inspiration" if feature == "inspiration" else "Indomitable"))
    if feature == "indomitable": assert event["total"] == 12
    assert next(draws, None) is None


@pytest.mark.parametrize("feature", ["inspiration", "indomitable"])
def test_step4_fix2_underlying_disadvantage_draws(spells, monkeypatch, feature):
    reroll_probe(spells, monkeypatch, feature)


def test_step4_fix2_advantage_keeps_other_die(monkeypatch):
    draws = iter([3, 12, 1])
    import random
    rng = random.Random(1)
    monkeypatch.setattr(rng, "randint", lambda a, b: next(draws))
    original = dice.d20(rng, True)
    result = dice.reroll(rng, original, 0)
    assert result == 12 and result.values == (1, 12)


@pytest.mark.parametrize("feature", ["inspiration", "indomitable"])
def test_step4_fix2_mutation_proof(spells, monkeypatch, feature):
    monkeypatch.setattr(dice, "reroll", lambda rng, natural, index=0: dice.d20(rng))
    with pytest.raises(AssertionError): reroll_probe(spells, monkeypatch, feature)


def source_membership():
    # Deliberately independent of builder tables and its spell_options cache.
    archive = Path(__file__).resolve().parents[1] / "5etools-v2.30.1.zip"
    with zipfile.ZipFile(archive) as z:
        data = json.loads(z.read("data/spells/sources.json"))["XPHB"]
    return {cls: {n for n, v in data.items() if any(c["source"] == "XPHB" and c["name"].lower() == cls for c in v.get("class", []))}
            for cls in ("wizard", "cleric")}


def test_step4_fix3_source_membership_and_buildability(spells):
    for cls, names in source_membership().items():
        assert builder.SPELL_LISTS[cls] == names
        base = builder.build(cls, 10)
        for name in names & spells.keys():
            if spells[name]["level"] > 5: continue
            if spells[name]["level"] == 0:
                cantrips = [n for n in base["spells"] if spells[n]["level"] == 0]
                if name not in cantrips: cantrips[0] = name
                assert name in builder.build(cls, 10, choices={"cantrips": cantrips})["spells"]
            elif cls == "cleric":
                if name in base["spells"]: continue  # always-prepared domain grant
                prepared = base["prepared_spells"][:]
                prepared[0] = name
                assert name in builder.build(cls, 10, choices={"prepared_spells": prepared})["spells"]
            else:
                if name in base["spellbook"]: continue
                for old in base["spellbook"]:
                    book = [name if n == old else n for n in base["spellbook"]]
                    prepared = builder.spell_order(cls, {n: spells[n] for n in book})[:15]
                    try: result = builder.build(cls, 10, choices={"spellbook": book, "prepared_spells": prepared})
                    except ValidationError: continue
                    assert name in result["spellbook"]
                    break
                else: pytest.fail(f"supported list spell cannot be built: {name}")


def test_step4_fix3_mutation_proof(spells, monkeypatch):
    lists = deepcopy(builder.SPELL_LISTS)
    lists["wizard"].remove("Arcane Vigor")
    monkeypatch.setattr(builder, "SPELL_LISTS", lists)
    with pytest.raises(AssertionError): test_step4_fix3_source_membership_and_buildability(spells)


GRANTS = [("fighter", "improved_critical", 19), ("rogue", "assassinate", True),
          ("rogue", "initiative_advantage", True),
          ("rogue", "sneak_attack", "5d6"), ("cleric", "disciple_of_life", True),
          ("cleric", "blessed_healer", True), ("wizard", "sculpt_spells", True),
          ("rogue", "uncanny_dodge", True)]


@pytest.mark.parametrize("cls,flag,expected", GRANTS)
def test_step4_fix4_builder_grants(cls, flag, expected):
    assert builder.build(cls, 10)["features"].get(flag) == expected
    assert builder.load_build(f"{cls}_10")["features"].get(flag) == expected


@pytest.mark.parametrize("cls,flag,expected", GRANTS)
def test_step4_fix4_each_builder_grant_mutation(monkeypatch, cls, flag, expected):
    mutate(monkeypatch, builder, "_build", 'if k not in {"builder","progression"}',
           f'if k not in {{"builder","progression",{flag!r}}}')
    with pytest.raises(AssertionError): test_step4_fix4_builder_grants(cls, flag, expected)


def test_step4_fix5_minimum_level_hp():
    sheet = builder.build("wizard", 10, abilities=dict(str=10,dex=10,con=3,int=15,wis=10,cha=10),
                          choices={"ability_method":"assigned", "asis":{4:{"int":2},8:{"int":2}}}, background=False)
    assert sheet["max_hp"] == 11


def test_step4_fix5_mutation_proof(monkeypatch):
    mutate(monkeypatch, builder, "_build", '*max(1,faces//2+1+mod("con"))', '*(faces//2+1+mod("con"))')
    with pytest.raises(AssertionError): test_step4_fix5_minimum_level_hp()


def test_step4_fix2_reliable_talent_keeps_original_disadvantage(spells,monkeypatch):
    r = built("rogue",7)
    r.conditions.add("poisoned")
    r.statuses["heroic_inspiration"] = {}
    combat = Combat([r],spells)
    draws = iter([1,2,20])
    monkeypatch.setattr(combat.rng,"randint",lambda a,b:next(draws))
    # Stealth Expertise + Dex = 10; retained 2 becomes Reliable Talent 10,
    # not the replacement 20. Only one original die was replaced.
    assert not combat.ability_check(r,"dex",21,skill="stealth")
