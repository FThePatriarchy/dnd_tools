"""Build comparison (Phase 5): variants, screen and swap-and-rate grid."""
from types import SimpleNamespace

import pytest
import yaml

import engine.compare as compare_mod
from engine.compare import compare, delta, markdown, screen_score, standard_recipe, variants
from engine.loader import ROOT
from engine.presets import party


@pytest.mark.parametrize("cls", ["fighter", "rogue", "cleric", "wizard", "barbarian", "paladin", "warlock", "bard", "monk", "ranger"])
def test_variants_start_with_standard_and_are_distinct(cls):
    for level in (1, 5, 7):
        found = variants(cls, level)
        base = yaml.safe_load((ROOT / "builds" / f"{cls}_{level}.yaml").read_text(encoding="utf-8"))
        assert {k: v for k, v in found[0].items() if k != "name"} == base and found[0]["name"] == "standard"
        names = [v["name"] for v in found]
        assert len(set(names)) == len(names)
        assert all(v["abilities"] == base["abilities"] for v in found)  # only the decision changes
        assert len(found) >= 2


def test_fighter_variants_cover_kits_and_styles():
    names = [v["name"] for v in variants("fighter", 5)]
    kits = [n for n in names if not n.startswith("feat:")]
    assert names[0] == "standard" and len(kits) == 6
    assert "sword and shield + dueling" in names and "archer + archery" in names
    # Sharpshooter is dropped: the standard fighter's 12 Dex misses its prerequisite
    assert [n for n in names if n.startswith("feat:")] == ["feat: alert", "feat: great weapon master"]
    level7 = [v["name"] for v in variants("fighter", 7)]
    assert len([n for n in level7 if not n.startswith("feat:")]) == 3  # two styles from level 7: one combination per kit


def test_screen_prefers_heavy_melee_fighter_to_archer():
    found = {v["name"]: v for v in variants("fighter", 5)}
    assert screen_score(found["standard"], 5) > screen_score(found["archer + archery"], 5) > 0


def fake_rating(xp, **types):
    return SimpleNamespace(xp=xp, types={k: SimpleNamespace(xp=v, censored="") for k, v in types.items()},
                           multiple=lambda x: x / 1000)


def test_compare_swaps_the_class_member_and_reuses_the_base(monkeypatch):
    calls = []
    def rate(builds, **kw):
        calls.append(list(builds))
        return fake_rating(1100 if "fighter_5_optimized" in builds else 1000, brute=500, solo=600)
    monkeypatch.setattr(compare_mod, "rate_party", rate)
    results = compare(5, "fighter", ["fighter_5", "fighter_5_optimized"], ("standard",))
    assert calls == [party(5), ["fighter_5_optimized", "cleric_5", "rogue_5", "wizard_5"]]  # base rated once
    rows = dict(results["standard"]["rows"])
    assert rows["fighter_5"] is results["standard"]["base"]
    assert delta(rows["fighter_5_optimized"].xp, results["standard"]["base"].xp) == pytest.approx(0.1)
    text = markdown(5, "fighter", results)
    assert "| fighter_5_optimized | +10% (1.10×)" in text and "| fighter_5 | +0% ≈ (1.00×)" in text


def test_recipe_candidates_use_their_label(monkeypatch):
    monkeypatch.setattr(compare_mod, "rate_party", lambda builds, **kw: fake_rating(1000, brute=1))
    candidate = {**standard_recipe("fighter", 5), "name": "my build"}
    results = compare(5, "fighter", [candidate], ("standard",))
    assert results["standard"]["rows"][0][0] == "my build"
