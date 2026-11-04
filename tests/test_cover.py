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
    brute = Combatant("brute", team="enemy", max_hp=50, ac=12, attacks=[blade()], position="front")
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
    assert b.half_cover(wizard) and not b.half_cover(fighter) and b.half_cover(archer)
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


@pytest.mark.parametrize("cover", [False, True])
def test_encounter_assigns_monster_rows(spells, monkeypatch, cover):
    from engine.day import run_day
    from engine.loader import ROOT, load_sheet
    sheet = load_sheet(ROOT / "monsters" / "ogre.yaml")
    sheets = {"melee": {**sheet, "attacks": [blade()]}, "ranged": {**sheet, "attacks": [bow(), blade()]},
              "unarmed": {**sheet, "attacks": []}, "explicit": {**sheet, "attacks": [blade()], "position": "back"},
              "front": {**sheet, "attacks": [bow()], "position": "front"}}
    seen = []
    def run(combat, max_rounds):
        seen.append([c.position for c in combat.combatants if c.team == "enemy"])
        return {"winner": "party", "rounds": 1}
    monkeypatch.setattr(Combat, "run", run)
    party = [Combatant("pc", team="party", position="back")]
    day = {"name": "rows", "steps": [{"encounter": list(sheets)}] * 2}
    run_day(party, day, spells, monster_sheets=sheets, options=DayOptions(cover=cover))
    expected = ["front" if cover else "back", "back", "back", "back", "front"]
    assert seen == [expected, expected] and party[0].position == "back"
    assert "position" not in sheets["melee"]


def test_monster_cover_and_pc_sharpshooter(spells, monkeypatch):
    b, archer, brute, _, wizard = fight(spells)
    rolls(monkeypatch, 8)
    assert b.half_cover(archer)
    assert not b.attack(wizard, archer, 5, lambda *a: None, melee=False, weapon=True)
    wizard.features["sharpshooter"] = True
    assert b.attack(wizard, archer, 5, lambda *a: None, melee=False, weapon=True)
    assert not b.attack(wizard, archer, 5, lambda *a: None, melee=False, weapon=False, spell=True)
    wizard.features.clear()
    brute.conditions.add("incapacitated")
    assert not b.half_cover(archer)
    brute.conditions.clear()
    brute.hp = 0
    assert not b.half_cover(archer)
    assert b.attack(wizard, archer, 5, lambda *a: None, melee=False, weapon=True)


def test_party_melee_screen(spells):
    b, archer, brute, fighter, _ = fight(spells)
    enemies = [archer, brute]
    assert b.reachable(fighter, enemies, blade()) == [brute]
    for attack in (bow(), {**blade(), "reach_ft": 10}, None):
        assert b.reachable(fighter, enemies, attack) == enemies
    fighter.movement_modes["fly"] = 30
    assert b.reachable(fighter, enemies, blade()) == enemies
    fighter.movement_modes.clear()
    fighter.engagement_tags = ["teleport"]
    assert b.reachable(fighter, enemies, blade()) == enemies
    fighter.engagement_tags.clear()
    allies = [Combatant(f"z{i}", team="party", attacks=[blade()]) for i in range(2)]
    b.combatants.extend(allies)
    assert b.reachable(allies[0], enemies, blade()) == [brute]
    assert b.reachable(allies[1], enemies, blade()) == enemies
    b.day_options = DayOptions(cover=True, screen=0)
    assert b.reachable(fighter, enemies, blade()) == enemies
    b.day_options = DayOptions(cover=False)
    assert b.reachable(fighter, enemies, blade()) == enemies
    b.day_options = DayOptions(cover=True)
    brute.hp = 0
    assert b.reachable(fighter, enemies, blade()) == enemies


def test_front_rows_engage_both_sides(spells):
    b, archer, brute, fighter, wizard = fight(spells)
    brute.position = "back"
    assert not b.in_melee(fighter)
    brute.position = "front"
    assert b.in_melee(fighter) and b.in_melee(brute)
    assert not b.in_melee(archer) and not b.in_melee(wizard)
    brute.conditions.add("incapacitated")
    assert not b.in_melee(fighter)
    brute.conditions.clear()
    brute.hp = 0
    assert not b.in_melee(fighter)


def test_monster_routines_value_ranged_disadvantage(spells, monkeypatch):
    b, archer, _, fighter, _ = fight(spells)
    archer.attacks[0]["effects"][0]["damage"]["dice"] = "1d10"
    archer.routines = [["Shortbow"], ["Rapier"]]
    hit = b.hit_probability(archer, fighter, 5)
    assert b.routine(archer, fighter) == ["Shortbow"]
    rolls(monkeypatch, 15)
    b.attack(fighter, archer, 5, lambda *a: None, melee=True, weapon=True)
    assert b.routine_value(archer, ["Shortbow"], fighter) == pytest.approx(5.5 * hit * hit)
    assert b.routine(archer, fighter) == ["Rapier"]
    b.day_options = DayOptions(cover=False)
    assert b.routine_value(archer, ["Shortbow"], fighter) == pytest.approx(5.5 * hit)
    assert b.routine(archer, fighter) == ["Shortbow"]
