"""Optional DMG morale rule: DayOptions.morale, off by default."""
import pytest

from engine import Combat, Combatant
from engine.day_options import DayOptions, day_options


def monsters(n, **kw):
    return [Combatant(f"m{i}", team="enemy", cr="1", max_hp=20, **kw) for i in range(n)]


def arena(mode, n=1, **kw):
    ms = monsters(n, **kw)
    pc = Combatant("pc", team="party", max_hp=50)
    b = Combat([pc, *ms], {}, seed=1)
    b.day_options = DayOptions(morale=mode)
    b.morale_start = {"enemy": n}
    return b, pc, ms


def test_option_defaults_and_validation():
    assert DayOptions().morale == "none" and DayOptions.legacy().morale == "none"
    assert day_options({"morale": "dmg"}).morale == "dmg"
    with pytest.raises(ValueError): DayOptions(morale="panic")


def test_off_by_default_never_flees():
    b, pc, (m,) = arena("none")
    m.hp = 1
    b.morale_checks()
    assert m.alive and not m.has_status("fled")
    b.day_options = None  # plain Combat without a day model: also off
    b.morale_checks()
    assert m.alive


def test_rout_flees_at_half_hp_once():
    b, pc, (m,) = arena("rout")
    m.hp = 11
    b.morale_checks()
    assert m.alive
    m.hp = 10  # exactly half
    b.morale_checks()
    assert m.removed and not m.alive and m.statuses["fled"]["reason"] == "morale_hurt"


def test_dmg_save_consumes_the_trigger(monkeypatch):
    b, pc, (m,) = arena("dmg")
    rolls = []
    monkeypatch.setattr(b, "saving_throw", lambda target, ability, dc, **k: rolls.append((ability, dc)) or True)
    m.hp = 5
    b.morale_checks(); b.morale_checks()
    assert m.alive and rolls == [("wis", 10)]  # passed once; the same trigger does not repeat
    b2, _, (m2,) = arena("dmg")
    monkeypatch.setattr(b2, "saving_throw", lambda *a, **k: False)
    m2.hp = 5
    b2.morale_checks()
    assert m2.has_status("fled")


def test_group_trigger_at_half_the_starting_number(monkeypatch):
    b, pc, ms = arena("dmg", n=4)
    checked = []
    monkeypatch.setattr(b, "saving_throw", lambda target, *a, **k: checked.append(target.id) or True)
    ms[0].hp = 0
    b.morale_checks()
    assert checked == []  # 3 of 4 standing
    ms[1].hp = 0
    b.morale_checks()
    assert sorted(checked) == ["m2", "m3"]  # 2 of 4: every survivor checks once
    b.morale_checks()
    assert sorted(checked) == ["m2", "m3"]


def test_fearless_and_incapacitated_creatures_do_not_check():
    b, pc, (m,) = arena("rout", condition_immunities=["frightened"])
    m.hp = 1
    b.morale_checks()
    assert m.alive
    b, pc, (m,) = arena("rout")
    m.hp = 1; m.conditions.add("stunned")
    b.morale_checks()
    assert m.alive and "morale_hurt" not in m.statuses  # checks once it can act
    m.conditions.discard("stunned")
    b.morale_checks()
    assert m.has_status("fled")


def test_pcs_never_check():
    b, pc, (m,) = arena("rout")
    pc.hp = 1
    b.morale_checks()
    assert pc.alive


def test_party_wins_when_the_last_monster_flees():
    from engine.loader import ROOT, load_sheet
    pcs = [Combatant.from_sheet(load_sheet(ROOT / "characters/fighter5.yaml"), f"pc{i}", "party") for i in range(2)]
    ogre = Combatant.from_sheet(load_sheet(ROOT / "monsters/ogre.yaml"), "ogre", "enemy")
    from engine.loader import load_spells
    b = Combat([*pcs, ogre], load_spells(), seed=3)
    b.day_options = DayOptions(morale="rout")
    b.record_log = True
    result = b.run(20)
    assert result["winner"] == "party" and ogre.has_status("fled") and ogre.hp > 0
    assert any(e["event"] == "fled" for e in b.log)
