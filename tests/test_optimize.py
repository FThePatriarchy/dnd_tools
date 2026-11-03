"""Build search (engine.optimize) with a fake comparison: real recipes and builder, no simulation."""
from types import SimpleNamespace

from engine.optimize import apply_change, candidate_changes, change_between, neighbours, optimize, recipe_of

PARTY = ["fighter_5", "cleric_5", "rogue_5", "wizard_5"]


def score(recipe):
    """A made-up value: Lucky +5%, Great Weapon Master +3%, the archer kit -10%."""
    c = recipe["choices"]
    feats = {v.get("feat") for v in (c.get("asis") or {}).values() if isinstance(v, dict)}
    return (.05 * (c.get("origin_feat") == "lucky") + .03 * ("great_weapon_master" in feats)
            - .10 * (recipe["equipment"] == "leather_archer"))


class FakeComparison:
    def __init__(self, builds, runs):
        self.base_builds = builds
        self.base_rating = SimpleNamespace(xp=1000 * (1 + score(builds[0])))
    def measure(self, label, builds): return builds
    def change(self, builds):
        d = (1 + score(builds[0])) / (1 + score(self.base_builds[0])) - 1
        return {"overall": (d, d - .01, d + .01), "brute": (d, d - .02, d + .02, "")}


def test_changes_are_differences_from_the_standard_build():
    base = recipe_of("fighter_5")
    changes = dict(candidate_changes("fighter", 5))
    assert changes["feat: lucky"] == {("choices", "origin_feat"): "lucky"}
    assert apply_change(base, changes["feat: lucky"], "x")["choices"]["origin_feat"] == "lucky"
    assert change_between(base, base) == {}


def test_neighbours_skip_applied_and_no_op_changes():
    base, changes = recipe_of("fighter_5"), candidate_changes("fighter", 5)
    labels = [l for l, _ in neighbours(base, changes, [])]
    assert "feat: lucky" in labels and len(labels) == len(set(labels))
    assert "feat: lucky" not in [l for l, _ in neighbours(base, changes, ["feat: lucky"])]


def test_hill_climb_stacks_good_changes_and_stops():
    final, steps = optimize(PARTY, "fighter_5", comparison=FakeComparison, log=lambda m: None)
    accepted = [s.accepted for s in steps if s.accepted]
    assert accepted == ["feat: lucky", "feat: great weapon master"]
    assert steps[-1].accepted is None                     # the last round found nothing above zero
    assert final["choices"]["origin_feat"] == "lucky" and final["equipment"] != "leather_archer"
    assert final["name"] == "feat: lucky + feat: great weapon master"


def test_a_change_that_rewrites_an_accepted_changes_fields_replaces_it():
    changes = candidate_changes("fighter", 5)
    labels = dict(changes)
    split = next(l for l in labels if "ASI split" in l)
    gwm = "feat: great weapon master"
    assert set(labels[split]) & set(labels[gwm])           # both set choices.asis
    def fake(builds, runs):
        c = FakeComparison(builds, runs)
        def change(b):
            r = b[0]; name = r.get("name", "")
            d = .04 if name == gwm else .06 if name == split else -.01
            if r["name"] == c.base_builds[0].get("name"): d = 0
            return {"overall": (d, d - .01, d + .01)}
        c.change = change
        return c
    final, steps = optimize(PARTY, "fighter_5", comparison=fake, changes=[(gwm, labels[gwm]), (split, labels[split])], log=lambda m: None)
    # Round 1 takes the split ASI; round 2's Great Weapon Master rewrites choices.asis, so it replaces the split.
    assert [s.accepted for s in steps if s.accepted] == [split, gwm]
    assert final["name"] == gwm
    assert any(isinstance(v, dict) and v.get("feat") == "great_weapon_master" for v in final["choices"]["asis"].values())


def test_min_gain_rejects_changes_that_barely_clear_zero():
    class Marginal(FakeComparison):
        def change(self, builds):
            est, lo, hi = super().change(builds)["overall"]
            return {"overall": (est, min(lo, .003), hi)}  # every lower bound at most +0.3%
    final, steps = optimize(PARTY, "fighter_5", comparison=Marginal, log=lambda m: None)
    assert [s.accepted for s in steps if s.accepted] == []
    final, steps = optimize(PARTY, "fighter_5", comparison=Marginal, log=lambda m: None, min_gain=0)
    assert [s.accepted for s in steps if s.accepted]
