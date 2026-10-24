from engine import Combat, Combatant
from engine.calibration import AREA_RULES, budget, compositions
from engine.loader import ROOT, load_sheet
from test_engine_step3 import spell_specs, NoReactions


def test_area_rule_counts():
    half, half_group, spread, single = (AREA_RULES[r][0] for r in ("half", "half_group", "party_spread", "single"))
    # Fireball: 20 ft sphere is 4 under the DMG table.
    assert half("sphere", 20, 6) == 2
    assert half_group("sphere", 20, 4) == 2 and half_group("sphere", 20, 8) == 4
    assert single("sphere", 20, 4) == 1 and single("sphere", 20, 0) == 0
    pc, monster = Combatant("pc", team="party"), Combatant("m", team="enemy")
    assert spread("sphere", 20, 4, caster=monster) == 2
    assert spread("sphere", 20, 4, caster=pc) == 4
    assert spread("emanation", 10, 4) == 2  # no caster (Aura of Authority): DMG count


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


def test_compositions_fit_budget():
    xp = {"goblin": 50, "ogre": 450, "dragon": 5000}
    for name, count, total in compositions(budget(3, "moderate"), xp):
        assert 0.75 * budget(3, "moderate") <= total <= budget(3, "moderate") and 1 <= count <= 8
