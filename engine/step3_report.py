"""Reproduce Step 3's numeric audit and (optionally) post-wiring CR rows.

python -m engine.step3_report [--measure-after --runs 500 --seed 1]
Writes measurements under engine/, not an automatically embellished build report.
"""
import argparse
from collections import Counter
from dataclasses import asdict
import json
from pathlib import Path

from .loader import ROOT, load_spells, read_yaml
from .spell_validation import source_spells, source_errors, mutants, numeric_fields


GOLDEN = set("Banishment; Bless; Counterspell; Cure Wounds; Eldritch Blast; Fire Bolt; Fireball; Guiding Bolt; Haste; Healing Word; Hex; Hold Person; Hunter's Mark; Magic Missile; Sacred Flame; Scorching Ray; Shield; Shield of Faith; Spirit Guardians; Spiritual Weapon".split("; "))
REFERENCES = set("Command; Cone of Cold; Detect Magic; Disguise Self; Dispel Magic; Fly; Ice Knife; Invisibility; Lesser Restoration; Light; Mage Armor; Mage Hand; Misty Step; Prestidigitation; Slow; Thaumaturgy; Thunderwave".split("; "))
MONSTERS = ("mage", "priest", "mage_apprentice", "cultist_fanatic", "imp", "quasit", "stone_golem", "aboleth", "adult_red_dragon")
SPELL_NUMERIC_ALLOWLIST = {}  # No survivors are exempted or silently accepted.


def audit():
    spells = load_spells()
    source = source_spells()
    scope = read_yaml(ROOT / "spell_scope.yaml")["spells"]
    required = {r["name"] for r in scope if r["level"] <= 5 and r["scope"] != "out_of_scope"} | REFERENCES
    fields = mutations = 0
    failures = []
    per_spell = {}
    for name, spec in spells.items():
        problems = source_errors(spec, source[name])
        if problems: failures.append({"spell": name, "original": problems})
        if name in GOLDEN: continue
        count = 0
        for path, value, mutant in mutants(spec):
            count += 1
            errors = source_errors(mutant, source[name], validate=False)
            if not errors: failures.append({"spell": name, "path": path, "survivor": value})
        field_count = len(list(numeric_fields(spec)))
        fields += field_count
        mutations += count
        per_spell[name] = {"numeric_fields": field_count, "mutations": count}
    return dict(scope_counts=dict(Counter(r["scope"] for r in scope)), levels=[
        dict(level=level, scopes=dict(Counter(r["scope"] for r in scope if r["level"] == level)),
             required=sum(source[n]["level"] == level for n in required),
             loaded=sum(s["level"] == level for s in spells.values())) for level in range(10)],
        loaded=len(spells), new=len(per_spell), required=len(required), missing=sorted(required - spells.keys()),
        numeric_fields=fields, mutations=mutations, failures=failures,
        rejected=mutations - sum("survivor" in f for f in failures), allowlist=SPELL_NUMERIC_ALLOWLIST, per_spell=per_spell)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--measure-after", action="store_true")
    p.add_argument("--runs", type=int, default=500)
    p.add_argument("--seed", type=int, default=1)
    args = p.parse_args()
    output = Path(__file__).resolve().parent
    result = audit()
    (output / "step3_validation.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf8")
    print(f"{result['loaded']}/{result['required']} required/catalog spells loaded; {len(result['missing'])} missing; {result['mutations']} numeric mutants; {len(result['failures'])} failures")
    if result["failures"]: raise SystemExit(1)
    if args.measure_after:
        from .simulate import simulate
        records = {}
        for name in MONSTERS:
            records[name] = asdict(simulate(("fighter5", "fighter5", "cleric5", "cleric5"), (name,), args.runs, args.seed))
            r = records[name]
            print(f"{name}: {r['win_rate']:.1%}, rounds {r['mean_rounds']:.3f}, party HP {r['mean_party_hp']:.3f}", flush=True)
            (output / "step3_cr_after.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf8")
    if result["missing"]:
        print("INCOMPLETE: required spell files are missing; see engine/step3_validation.json.")
        raise SystemExit(2)


if __name__ == "__main__": main()
