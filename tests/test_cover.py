"""Optional no-grid cover and ranged-in-melee rules (DayOptions.cover)."""
import pytest

from engine import Combat, Combatant
from engine import combat as combat_module
from engine.day_options import DayOptions
from engine.loader import load_spells


def bow(to_hit=5): return {"name": "Shortbow", "kind": "ranged", "to_hit": to_hit, "effects": [{"damage": {"dice": "1d6", "type": "piercing"}}]}
def blade(to_hit=5): return {"name": "Rapier", "kind": "melee", "to_hit": to_hit, "effects": [{"damage": {"dice": "1d8", "type": "piercing"}}]}


@pytest.fixture(scope="module")
def spells(): return load_spells()


def fight(spells, cover=True, archer_features=None):
    archer = Combatant("archer", team="enemy", max_hp=50, ac=12, attacks=[bow(), blade()], features=archer_features or {})
    brute = Combatant("brute", team="enemy", max_hp=50, ac=12, attacks=[blade()])
    fighter = Combatant("fighter", team="party", max_hp=50, ac=18, attacks=[blade()], position="front")
    wizard = Combatant("wizard", team="party", max_hp=30, ac=12, attacks=[bow()], position="back")
    b = Combat([archer, brute, fighter, wizard], spells, seed=1)
    b.day_options = DayOptions(cover=cover)
    return b, archer, brute, fighter, wizard


def rolls(monkeypatch, natural):
    seen = []
    def d20(rng, adv=False, dis=False):
        seen.append((adv, dis)); return natural
    monkeypatch.setattr(combat_module.dice, "d20", d20)
    return seen


def test_back_row_behind_a_standing_front_line_has_half_cover(spells, monkeypatch):
    b, archer, _, fighter, wizard = fight(spells)
    rolls(monkeypatch, 8)  # 8 + 5 = 13: hits AC 12, misses AC 12 + 2
    assert b.half_cover(wizard) and not b.half_cover(fighter) and not b.half_cover(archer)
    assert not b.attack(archer, wizard, 5, lambda *a: None, melee=False, weapon=True)
    assert b.attack(archer, fighter, -1, lambda *a: None, melee=False, weapon=True) is False  # 7 vs AC 18
    fighter.hp = 0
    assert not b.half_cover(wizard) and b.attack(archer, wizard, 5, lambda *a: None, melee=False, weapon=True)


def test_ranged_attacks_in_melee_have_disadvantage_until_the_end_of_the_turn(spells, monkeypatch):
    b, archer, _, fighter, wizard = fight(spells)
    seen = rolls(monkeypatch, 15)
    b.attack(archer, wizard, 5, lambda *a: None, melee=False, weapon=True)
    assert seen[-1] == (False, False) and not b.in_melee(archer)
    b.attack(fighter, archer, 5, lambda *a: None, melee=True, weapon=True)
    assert b.in_melee(archer)
    b.attack(archer, wizard, 5, lambda *a: None, melee=False, weapon=True)
    assert seen[-1] == (False, True)
    assert b.pc_weapon(archer)["name"] == "Rapier"
    b.end_turn(archer)
    assert not b.in_melee(archer) and b.pc_weapon(archer)["name"] == "Shortbow"
    assert b.in_melee(fighter) and not b.in_melee(wizard)  # the front row faces the melee enemies


def test_sharpshooter_ignores_cover_and_melee_for_weapon_attacks(spells, monkeypatch):
    b, archer, _, fighter, wizard = fight(spells, archer_features={"sharpshooter": True})
    seen = rolls(monkeypatch, 8)
    b.attack(fighter, archer, 5, lambda *a: None, melee=True, weapon=True)
    assert b.attack(archer, wizard, 5, lambda *a: None, melee=False, weapon=True) and seen[-1] == (False, False)
    assert b.pc_weapon(archer)["name"] == "Shortbow"
    assert not b.attack(archer, wizard, 5, lambda *a: None, melee=False, weapon=False, spell=True)  # spell attacks still covered


def test_rules_are_off_by_default(spells, monkeypatch):
    b, archer, _, fighter, wizard = fight(spells, cover=False)
    seen = rolls(monkeypatch, 8)
    b.attack(fighter, archer, 5, lambda *a: None, melee=True, weapon=True)
    assert b.attack(archer, wizard, 5, lambda *a: None, melee=False, weapon=True) and seen[-1] == (False, False)
    assert "melee_engaged" not in archer.statuses and b.pc_weapon(archer)["name"] == "Shortbow"
    assert DayOptions().cover is False
