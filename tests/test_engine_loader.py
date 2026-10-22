from copy import deepcopy
from pathlib import Path

import pytest

from engine import load_spells, load_sheet, ValidationError
from engine.loader import ROOT, Validator, scaled_spell, read_yaml
from engine.expressions import evaluate, parse, ExpressionError
from engine.state import Combatant


@pytest.fixture(scope="module")
def spells():
    return load_spells()


def test_all_reviewed_assets_validate(spells):
    assert len(spells) == 20
    from engine.monster_import import ORIGINAL, STEP2, slug
    assert {p.stem for p in (ROOT / "monsters").glob("*.yaml")} == {slug(n) for n in ORIGINAL + STEP2}
    assert len(list((ROOT / "characters").glob("*.yaml"))) == 2
    for folder in ("monsters", "characters"):
        for path in (ROOT / folder).glob("*.yaml"):
            assert load_sheet(path)["name"]


@pytest.mark.parametrize("mutation,path", [
    (lambda s: s.update(typo=True), "$.typo"),
    (lambda s: s["effects"][0].update(event="on_unknown(caster)"), "effects[0].event"),
    (lambda s: s["effects"][0].update(event="unknown_event"), "effects[0].event"),
    (lambda s: s["effects"][0].update(event="start_of_turn(bogus)"), "effects[0].event"),
    (lambda s: s["effects"][0].update(event="on_attack_hit(caster)"), "effects[0].event"),
    (lambda s: s["effects"][0]["on_hit"].append({"explode": {}}), "effects[0].on_hit[1].explode"),
    (lambda s: s["effects"][0]["on_hit"][0]["damage"].update(typo=1), "damage.typo"),
    (lambda s: s["effects"][0]["target"].update(typo=True), "target.typo"),
    (lambda s: s["scaling"]["cantrip"]["effect"].update(block="missing"), "scaling.cantrip.effect.block"),
    (lambda s: s["effects"][0].update({"if": "target.__class__"}), "effects[0].if"),
    (lambda s: s["effects"][0].update({"if": "target.foo()"}), "effects[0].if"),
    (lambda s: s["effects"][0].update({"if": "nonsense.hp > 1"}), "effects[0].if"),
    (lambda s: s["effects"][0].update({"if": "spell.hp > 1"}), "effects[0].if"),
    (lambda s: s["effects"][0].update({"if": "target.hp + 1"}), "effects[0].if"),
    (lambda s: s["effects"][0]["attack"].update(type="ranged_weapon"), "attack.type"),
    (lambda s: s["effects"][0].update(limit="once_per_round"), "limit"),
    (lambda s: s["effects"][0]["on_hit"][0]["damage"].update(dice="0d6"), "damage.dice"),
])
def test_strict_validation_reports_file_and_path(spells, mutation, path):
    spec = deepcopy(spells["Fire Bolt"])
    mutation(spec)
    with pytest.raises(ValidationError) as exc:
        Validator("broken.yaml").spell(spec)
    assert "broken.yaml:" in str(exc.value)
    assert path in str(exc.value)


def test_duplicate_yaml_keys_are_rejected(tmp_path):
    path = tmp_path / "duplicate.yaml"
    path.write_text("name: A\nname: B\n")
    with pytest.raises(ValidationError, match="duplicate key"):
        read_yaml(path)


def test_safe_expressions_and_short_circuit():
    c = Combatant("c", hp=25, alignment="evil")
    c.statuses["shielded"] = {}
    assert evaluate("target.hp >= 25 and target.creature_type in [humanoid, fey]", {"target": c})
    assert evaluate("not target.has_status(missing) and target.has_status(shielded)", {"target": c})
    assert evaluate("caster.alignment == evil", {"caster": c})
    assert evaluate("event == on_cast or missing.hp > 2", {"event": "on_cast"})
    assert evaluate("$ability == wis", {"$ability": "wis"})
    for bad in ("__import__('os')", "target.__dict__", "open(file)", "target.hp; print(1)", "[x for x in a]"):
        with pytest.raises(ExpressionError): parse(bad)


def test_scaling_does_not_mutate_source(spells):
    original = deepcopy(spells)
    assert scaled_spell(spells["Fireball"], 5, 5)["effects"][0]["on_fail"][0]["damage"]["dice"] == "10d6"
    assert scaled_spell(spells["Cure Wounds"], 3, 5)["effects"][0]["apply"][0]["heal"]["dice"] == "6d8"
    assert scaled_spell(spells["Eldritch Blast"], 0, 17)["effects"][0]["target"]["n"] == 4
    assert scaled_spell(spells["Hold Person"], 4, 5)["effects"][0]["target"]["n"] == 3
    assert scaled_spell(spells["Hex"], 2, 5)["duration"] == {"type": "hours", "n": 4}
    assert scaled_spell(spells["Hex"], 3, 5)["duration"]["n"] == 8
    assert scaled_spell(spells["Hex"], 5, 5)["duration"]["n"] == 24
    assert scaled_spell(spells["Hunter's Mark"], 2, 5)["duration"]["n"] == 1
    assert spells == original
