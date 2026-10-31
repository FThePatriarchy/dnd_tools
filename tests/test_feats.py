"""2024 feats: Great Weapon Master, Sharpshooter, War Caster, Polearm Master, Resilient (General) and Alert, Lucky, Tough (Origin)."""
import pytest
import yaml

from engine import Combat, Combatant, dice
from engine.builder import build
from engine.loader import ROOT, ValidationError, load_spells


def recipe(name):
    return yaml.safe_load((ROOT / "builds" / f"{name}.yaml").read_text(encoding="utf-8"))


def built(name, equipment=None, **choices):
    r = recipe(name)
    return build(r["class"], r["level"], r["subclass"], r["abilities"], equipment or r["equipment"], {**r["choices"], **choices})


def test_general_feat_replaces_an_asi_with_plus_one():
    standard = built("fighter_5")
    gwm = built("fighter_5", asis={4: {"feat": "great_weapon_master", "ability": "str"}})
    assert gwm["abilities"]["str"] == standard["abilities"]["str"] - 1 and gwm["features"]["great_weapon_master"]
    assert "heavy" in gwm["attacks"][0]["properties"]
    caster = built("wizard_5", asis={4: {"feat": "war_caster", "ability": "int"}})
    assert caster["features"]["war_caster"]


@pytest.mark.parametrize("name,asis,message", [
    ("fighter_5", {4: {"feat": "sharpshooter", "ability": "dex"}}, "requires Dex 13"),
    ("fighter_5", {4: {"feat": "war_caster", "ability": "int"}}, "Spellcasting"),
    ("wizard_5", {4: {"feat": "war_caster", "ability": "str"}}, "expected one of"),
    ("fighter_7", {4: {"feat": "great_weapon_master", "ability": "str"}, 6: {"feat": "great_weapon_master", "ability": "str"}}, "already taken"),
    ("fighter_5", {4: {"feat": "lucky", "ability": "str"}}, "expected one of"),
    ("fighter_5", {4: {"feat": "resilient", "ability": "con"}}, "without proficiency"),
    ("wizard_5", {4: {"feat": "polearm_master", "ability": "int"}}, "expected one of"),
])
def test_feat_validation(name, asis, message):
    with pytest.raises(ValidationError, match=message):
        built(name, asis=asis)


def test_alert_adds_proficiency_to_initiative():
    sheet = built("rogue_5", origin_feat="alert")
    assert sheet["features"]["alert"] and sheet["initiative_bonus"] == 3
    with pytest.raises(ValidationError):
        built("rogue_5", origin_feat="magic_initiate")


def fighter(**features):
    attack = {"name": "Greatsword", "kind": "melee", "properties": ["two_handed", "heavy"], "ability": "str", "to_hit": 7,
              "reach_ft": 5, "effects": [{"damage": {"dice": "2d6", "bonus": 4, "type": "slashing"}}]}
    return Combatant("f", team="party", max_hp=50, proficiency_bonus=3, attacks=[attack], features=dict(features))


def test_great_weapon_master_adds_proficiency_bonus_on_heavy_hits(monkeypatch):
    monkeypatch.setattr(dice, "d20", lambda *a, **k: 15)
    results = {}
    for flag in (False, True):
        f = fighter(**({"great_weapon_master": True} if flag else {}))
        t = Combatant("t", team="enemy", max_hp=500, ac=10)
        combat = Combat([f, t], load_spells(), seed=4)
        combat.begin_turn(f)
        combat.weapon_attack(f, t, f.attacks[0])
        results[flag] = 500 - t.hp
    assert results[True] == results[False] + 3
    f = fighter(great_weapon_master=True)
    f.attacks[0]["properties"] = ["two_handed"]  # not Heavy: no bonus
    t = Combatant("t", team="enemy", max_hp=500, ac=10)
    combat = Combat([f, t], load_spells(), seed=4); combat.begin_turn(f)
    combat.weapon_attack(f, t, f.attacks[0])
    assert 500 - t.hp == results[False]


def test_hew_attacks_again_after_a_kill_once_per_bonus_action():
    f = fighter(great_weapon_master=True)
    weak = Combatant("weak", team="enemy", max_hp=1, ac=-20)
    other = Combatant("other", team="enemy", max_hp=500, ac=-20)
    combat = Combat([f, weak, other], load_spells(), seed=2)
    combat.record_log = True
    combat.begin_turn(f)
    combat.weapon_attack(f, weak, f.attacks[0])
    assert weak.hp == 0 and other.hp < 500 and f.bonus_action == 0
    before = other.hp
    combat.weapon_attack(f, other, f.attacks[0])  # no bonus action left: no second Hew
    assert sum(e["event"] == "trait" and e.get("name") == "Hew" for e in combat.log) == 1 and other.hp < before


def test_war_caster_gives_advantage_on_concentration_saves(monkeypatch):
    flags = []
    monkeypatch.setattr(dice, "d20", lambda rng, advantage=False, disadvantage=False: flags.append((advantage, disadvantage)) or 10)
    caster = Combatant("c", team="party", max_hp=40, features={"war_caster": True})
    combat = Combat([caster], load_spells(), seed=1)
    combat.saving_throw(caster, "con", 10, concentration=True)
    combat.saving_throw(caster, "con", 10)
    assert flags == [(True, False), (False, False)]


def test_alert_swaps_initiative_with_the_slowest_spellcaster(monkeypatch):
    rolls = iter([20, 15, 1])  # initiative: alert 20, foe 15, wizard 1; later rolls are 10
    monkeypatch.setattr(dice, "d20", lambda *a, **k: next(rolls, 10))
    alert = Combatant("alert", team="party", max_hp=30, features={"alert": True}, attacks=fighter().attacks)
    wizard = Combatant("wizard", team="party", max_hp=30, spell_slots={1: 2}, max_spell_slots={1: 2})
    foe = Combatant("foe", team="enemy", max_hp=1, ac=-20)
    combat = Combat([alert, foe, wizard], load_spells(), seed=1)
    combat.record_log = True
    combat.run(1)
    order = next(e["order"] for e in combat.log if e["event"] == "initiative")
    assert order[0] == "wizard" and order[-1] == "alert"


def test_tough_lucky_and_resilient_on_the_sheet():
    standard = built("fighter_5")
    assert built("fighter_5", origin_feat="tough")["max_hp"] == standard["max_hp"] + 10
    assert built("fighter_5", origin_feat="lucky")["limited_uses"]["luck"] == {"max": 3, "long_rest": "all"}
    resilient = built("fighter_5", asis={4: {"feat": "resilient", "ability": "wis"}})
    assert "wis" in resilient["save_proficiencies"] and resilient["abilities"]["wis"] == standard["abilities"]["wis"] + 1


def test_lucky_rerolls_a_failed_save_and_keeps_a_point_for_saves(monkeypatch):
    rolls = iter([2, 18, 2, 2, 18])
    monkeypatch.setattr(dice, "d20", lambda *a, **k: next(rolls))
    lucky = Combatant("l", team="party", max_hp=30, features={"lucky": True}, limited_uses={"luck": 2}, max_limited_uses={"luck": 2})
    combat = Combat([lucky], load_spells(), seed=1)
    assert combat.saving_throw(lucky, "wis", 15) and lucky.limited_uses["luck"] == 1
    assert combat.heroic_reroll(lucky, 2, lambda n: n >= 15, "attack") == 2 and lucky.limited_uses["luck"] == 1  # last point kept
    assert not combat.saving_throw(lucky, "wis", 15) and lucky.limited_uses["luck"] == 0
    assert combat.heroic_reroll(lucky, 2, lambda n: n >= 25, "save") == 2  # hopeless rolls spend nothing


def test_pole_strike_follows_the_attack_action_without_heavy_weapon_bonus():
    glaive = built("fighter_5", equipment="chain_glaive", weapon_masteries=["glaive"],
                   asis={4: {"feat": "polearm_master", "ability": "str"}}, origin_feat="alert")
    attack = glaive["attacks"][0]
    assert attack["reach_ft"] == 10 and {"heavy", "reach"} <= set(attack["properties"])
    f = Combatant.from_sheet(glaive, "f", "party")
    t = Combatant("t", team="enemy", max_hp=500, ac=-20)
    combat = Combat([f, t], load_spells(), seed=3)
    combat.record_log = True
    combat.begin_turn(f)
    combat.weapon_action(f)
    assert f.bonus_action == 0
    assert sum(e.get("name") == "Pole Strike" for e in combat.log) == 1
    # Two glaive hits and the d4 butt end: GWF floors each die at 3, so the butt end deals 3-4 + Str.
    assert sum(e.get("name") == "Great Weapon Master" for e in combat.log) == 0
    plain = Combatant.from_sheet(built("fighter_5", equipment="chain_glaive", weapon_masteries=["glaive"]), "p", "party")
    t2 = Combatant("t2", team="enemy", max_hp=500, ac=-20)
    combat = Combat([plain, t2], load_spells(), seed=3); combat.begin_turn(plain)
    combat.weapon_action(plain)
    assert plain.bonus_action == 1
