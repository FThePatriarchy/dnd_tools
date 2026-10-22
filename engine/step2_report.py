"""Reproduce Step 2 CR sanity measurements (not a statistical test).

python -m engine.step2_report --runs 500 --seed 1
Writes the measured records and Markdown table under engine/.
"""
import argparse
from dataclasses import asdict
from fractions import Fraction
import json
from pathlib import Path

from .loader import ROOT, load_sheet
from .monster_import import ORIGINAL, STEP2, slug, source_monsters
from .monster_validation import source_attack_dpr, sheet_attack_dpr
from .simulate import simulate


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runs', type=int, default=500)
    p.add_argument('--seed', type=int, default=1)
    args = p.parse_args()
    raw = source_monsters()
    records=[]
    names=sorted(ORIGINAL+STEP2,key=lambda n:(Fraction(str(raw[n]['cr']['cr'] if isinstance(raw[n]['cr'],dict) else raw[n]['cr'])),n))
    for name in names:
        sheet=load_sheet(ROOT/'monsters'/(slug(name)+'.yaml'))
        result=simulate(('fighter5','fighter5','cleric5','cleric5'),(slug(name),),args.runs,args.seed)
        record={'name':name,'cr':sheet['cr'],**asdict(result), 'source_attack_dpr_ac16':source_attack_dpr(raw[name]),'yaml_attack_dpr_ac16':sheet_attack_dpr(sheet)}
        records.append(record)
        print(f"{name}: CR {sheet['cr']}; party {result.win_rate:.1%}; {result.mean_rounds:.3f} rounds; HP {result.mean_party_hp:.1f}; draws {result.draws}",flush=True)
    output=Path(__file__).resolve().parent
    (output/'step2_cr.json').write_text(json.dumps(records,indent=2)+'\n',encoding='utf8')
    rows=['| CR | Monster | Party win rate | Mean rounds | Party HP | Draws | Attack DPR source/YAML |','| --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for r in records:
        rows.append(f"| {r['cr']} | {r['name']} | {r['win_rate']:.1%} | {r['mean_rounds']:.3f} | {r['mean_party_hp']:.1f} | {r['draws']} | {r['source_attack_dpr_ac16']:.3f} / {r['yaml_attack_dpr_ac16']:.3f} |")
    (output/'step2_cr_table.md').write_text('\n'.join(rows)+'\n',encoding='utf8')


if __name__=='__main__':main()
