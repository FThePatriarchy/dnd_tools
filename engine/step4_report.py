"""Reproduce the numeric mutation audit and seed-1 class-party day results."""
import argparse
from copy import deepcopy
from dataclasses import asdict
import json
from pathlib import Path
import re

from .class_source import numeric_leaves, check_class_source, CORE_ALLOWLIST
from .classes import validate_class
from .loader import ROOT, ValidationError, read_yaml


def mutants(data):
    for route, value in numeric_leaves(data):
        if isinstance(value,str):
            changes=[value[:m.start()]+str(int(m[0])+1)+value[m.end():] for m in re.finditer(r"\d+",value)]
        else: changes=[value+1]
        for replacement in changes:
            altered=deepcopy(data); parent=altered
            for key in route[:-1]: parent=parent[key]
            key=route[-1]
            if isinstance(key,tuple):
                old=key[1]; parent[replacement]=parent.pop(old)
            else: parent[key]=replacement
            yield route,altered


def source_audit(names=("fighter", "rogue", "wizard", "cleric")):
    # Keep the historical four-class report reproducible; callers can audit other classes.
    report={"classes":{},"numeric_fields":0,"mutants":0,"survivors":[],"allow_list":CORE_ALLOWLIST}
    for name in names:
        path=ROOT/"classes"/(name+".yaml"); data=read_yaml(path)
        validate_class(data,path)
        count=check_class_source(data,path); attempts=0
        for route,altered in mutants(data):
            attempts+=1
            try: validate_class(altered,"<numeric mutant>")
            except ValidationError: pass
            else: report["survivors"].append({"class":name,"path":str(route)})
        report["classes"][name]={"numeric_fields":count,"mutants":attempts}
        report["numeric_fields"]+=count; report["mutants"]+=attempts
    return report


def _day_row(args):
    from .day import simulate_day
    level,strategy,runs,seed=args
    party=tuple(f"{name}_{level}" for name in ("fighter", "rogue", "wizard", "cleric"))
    summary=simulate_day(party,f"classes_level_{level}",runs,seed,strategy=strategy)
    return {"level":level,**asdict(summary)}


def day_results(runs=1000,seed=1,output=None):
    from concurrent.futures import ProcessPoolExecutor
    rows=[]
    jobs=[(level,strategy,runs,seed) for level in (3,5,10) for strategy in ("nova","conservative")]
    # Each row owns its seeded RNG. Ordered map keeps artifacts deterministic.
    with ProcessPoolExecutor(max_workers=3) as pool:
        for row in pool.map(_day_row,jobs):
            rows.append(row)
            if output is not None: output.write_text(json.dumps(rows,indent=2)+"\n",encoding="utf-8")
            print(f"level {row['level']} {row['strategy']}: {row['survived']}/{runs}",flush=True)
    return rows


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-only",action="store_true")
    parser.add_argument("--results-only",action="store_true")
    parser.add_argument("--runs",type=int,default=1000); parser.add_argument("--seed",type=int,default=1)
    args=parser.parse_args(); folder=Path(__file__).resolve().parent
    if not args.results_only:
        audit=source_audit(); (folder/"step4_validation.json").write_text(json.dumps(audit,indent=2)+"\n",encoding="utf-8")
        print(f"{audit['numeric_fields']} numeric fields; {audit['mutants']} mutants; {len(audit['survivors'])} survivors",flush=True)
        if audit["survivors"]: raise SystemExit(1)
    if not args.source_only:
        results=day_results(args.runs,args.seed,folder/"step4_results.json")
        (folder/"step4_results.json").write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__": main()
