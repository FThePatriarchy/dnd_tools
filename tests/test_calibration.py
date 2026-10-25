from engine import Combat, Combatant
from engine.calibration import AREA_RULES, GRAB_RULES, budget, compositions
from engine.policy import area_heuristic, dmg_area_heuristic, grab_cap, is_grab, printed_grab_count
from engine.loader import ROOT, load_sheet
from test_engine_step3 import spell_specs, NoReactions


def test_rule_names_map_to_fixed_rules():
    # None is the engine default; the pre-2026-10-24 rules are explicit functions.
    assert AREA_RULES["party_spread"][0] is None and AREA_RULES["dmg"][0] is dmg_area_heuristic
    assert GRAB_RULES["grab_half"][0] is None and GRAB_RULES["data"][0] is printed_grab_count


def test_area_rule_counts():
    half, half_group, single = (AREA_RULES[r][0] for r in ("half", "half_group", "single"))
    spread = area_heuristic
    # Fireball: 20 ft sphere is 4 under the DMG table.
    assert half("sphere", 20, 6) == 2
    assert half_group("sphere", 20, 4) == 2 and half_group("sphere", 20, 8) == 4
    assert single("sphere", 20, 4) == 1 and single("sphere", 20, 0) == 0
    pc, monster = Combatant("pc", team="party"), Combatant("m", team="enemy")
    assert spread("sphere", 20, 4, caster=monster) == 2
    assert spread("sphere", 20, 4, caster=pc) == 4
    assert spread("emanation", 10, 4) == 2  # no caster (Aura of Authority): DMG count
    assert dmg_area_heuristic("sphere", 20, 4, caster=monster) == 4


def test_default_monster_areas_halved_party_areas_not():
    for area, expected in ((None, 2), (dmg_area_heuristic, 4)):
        mage = Combatant.from_sheet(load_sheet(ROOT / "monsters/mage.yaml"), "mage", "enemy")
        pcs = [Combatant.from_sheet(load_sheet(ROOT / "characters/fighter5.yaml"), f"pc{i}", "party") for i in range(4)]
        b = Combat([mage, *pcs], spell_specs(), seed=1, policy=NoReactions(), area=area)
        b.begin_turn(mage)
        assert len(b.cast(mage, "Fireball", slot=4).area_members["blast"]) == expected


def test_custom_rule_opts_in_to_ally_avoidance_and_caster():
    seen = []
    def rule(shape, size_ft, eligible, caster=None):
        seen.append(caster)
        return eligible
    rule.avoids_allies = rule.wants_caster = True
    mage = Combatant.from_sheet(load_sheet(ROOT / "monsters/mage.yaml"), "mage", "enemy")
    ally = Combatant("ally", team="enemy")
    pcs = [Combatant.from_sheet(load_sheet(ROOT / "characters/fighter5.yaml"), f"pc{i}", "party") for i in range(2)]
    b = Combat([mage, ally, *pcs], spell_specs(), seed=1, policy=NoReactions(), area=rule)
    b.begin_turn(mage)
    hp = ally.hp
    inst = b.cast(mage, "Fireball", slot=4)
    assert inst is not None and ally.hp == hp
    assert set(inst.area_members["blast"]) == set(pcs)
    assert seen and all(c is mage for c in seen)  # may be consulted more than once per cast


def _grab_setup(name, action):
    from engine.state import SpellInstance
    monster = Combatant.from_sheet(load_sheet(ROOT / f"monsters/{name}.yaml"), "m", "enemy")
    pcs = [Combatant.from_sheet(load_sheet(ROOT / "characters/fighter5.yaml"), f"pc{i}", "party") for i in range(4)]
    b = Combat([monster, *pcs], spell_specs(), seed=1, policy=NoReactions())
    block = next(a for a in monster.actions if a["name"] == action)["effects"][0]
    probe = SpellInstance(0, {"name": action}, monster, 0, b.turn_index, b.time_rounds)
    return b, block, probe


def test_grab_rules_cap_only_grabs():
    one = GRAB_RULES["grab_one"][0]
    b, engulf, probe = _grab_setup("gelatinous_cube", "Engulf")
    assert is_grab(engulf)
    assert is_grab(_grab_setup("water_elemental", "Whelm")[1])
    assert b.target_cap is grab_cap
    assert len(b.select_targets(probe, engulf, {})) == 2  # engine default: half of 4
    b.target_cap = printed_grab_count
    assert len(b.select_targets(probe, engulf, {})) == 4
    b.target_cap = one
    assert len(b.select_targets(probe, engulf, {})) == 1
    # Non-grab n_targets blocks keep their count.
    plain = {**engulf, "on_fail": [{"damage": {"dice": "1d6", "bonus": 0, "type": "acid"}}]}
    b.target_cap = grab_cap
    assert not is_grab(plain) and len(b.select_targets(probe, plain, {})) == 4


def test_defeat_counts_dominated_losses_not_draws():
    from engine.calibration import DEFEATS, run_cell, fmt_metric
    assert DEFEATS == {"tpk", "party_unavailable"}
    # Aboleths win mostly by dominating every PC still standing: a defeat, rarely a TPK.
    cell = run_cell((10, "over", "aboleth", 3, 17700, 3, 1, "party_spread", "grab_half"))
    assert cell["runs"] == 3 and cell["defeat"] >= cell["tpk"] and cell["win"] + cell["defeat"] <= 1
    assert fmt_metric({"tpk": 0.5}, "defeat") == "-" and fmt_metric(cell, "rounds") != "-"


def test_wilson_interval():
    from engine.calibration import wilson
    lo, hi = wilson(0.5, 100)
    assert abs(lo - 0.4038) < 1e-3 and abs(hi - 0.5962) < 1e-3
    lo, hi = wilson(0.0, 50)
    assert lo == 0.0 and abs(hi - 0.0713) < 1e-3
    assert wilson(0.3, 0) == (0.0, 1.0)


def test_adaptive_stopping_rule():
    import pytest
    from engine.calibration import Adaptive, needs_more
    rows = lambda n, defeats=0, downs=0: [{"defeat": i < defeats, "down": i < downs, "death": False} for i in range(n)]
    spec = Adaptive(min_runs=50, max_runs=400, batch=50, precision=0.05, thresholds=(0.5,))
    assert needs_more(rows(10), 10, spec)                       # below the minimum
    assert not needs_more(rows(50), 50, spec)                   # clear-cut 0%: stop at the minimum
    assert needs_more(rows(50, downs=25), 50, spec)             # 50% is uncertain at n=50
    assert not needs_more(rows(400, downs=200), 400, spec)      # maximum reached
    loose = Adaptive(min_runs=50, max_runs=400, batch=50, precision=0.5, thresholds=(0.5,))
    assert needs_more(rows(100, defeats=52), 100, loose)        # precise enough, but straddles 50%
    assert not needs_more(rows(100, defeats=52), 100, Adaptive(50, 400, 50, 0.5, ()))
    assert not needs_more([], 50, spec)                         # every run failed
    with pytest.raises(ValueError): Adaptive(min_runs=100, max_runs=50)


def test_adaptive_runs_are_a_prefix_of_fixed_runs():
    from engine.calibration import Adaptive, run_cell
    fixed = run_cell((1, "low", "goblin_boss", 1, 200, 30, 1, "party_spread", "grab_half"))
    adaptive = run_cell((1, "low", "goblin_boss", 1, 200, Adaptive(30, 30, 10, 0.5, ()), 1, "party_spread", "grab_half"))
    keys = ("win", "defeat", "down", "death", "hp_lost", "rounds", "runs")
    assert {k: fixed[k] for k in keys} == {k: adaptive[k] for k in keys}
    assert set(fixed["ci"]) == {"defeat", "down", "death"}


def test_compositions_fit_budget():
    xp = {"goblin": 50, "ogre": 450, "dragon": 5000}
    for name, count, total in compositions(budget(3, "moderate"), xp):
        assert 0.75 * budget(3, "moderate") <= total <= budget(3, "moderate") and 1 <= count <= 8
