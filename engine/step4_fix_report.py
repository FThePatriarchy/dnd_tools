"""Resumable fix-round measurements. Artifacts live in data/reports, never engine."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import hashlib
import json
from pathlib import Path
import random

from .day import simulate_day, load_day, day_monsters, encounter_names
from .day_options import DayOptions

ROOT = Path(__file__).resolve().parents[1]
SWITCHES = ("clock", "prebuffs", "death", "backgrounds", "engagement", "spending")
XP = dict(zip(("0","1/8","1/4","1/2","1","2","3","4","5","6","7","8","9","10","11","12","13","14","15","16","17","18","19","20"),
              (10,25,50,100,200,450,700,1100,1800,2300,2900,3900,5000,5900,7200,8400,10000,11500,13000,15000,18000,20000,22000,25000)))


def jobs(main_runs=1000, sensitivity_runs=300):
    result = []
    for level in (3,5,10):
        for strategy in ("nova","conservative"):
            for label, runs, opts in [("defaults",main_runs,DayOptions()), ("sensitivity_reference",sensitivity_runs,DayOptions())] + [("no_"+n,sensitivity_runs,replace(DayOptions(),**{n:False})) for n in SWITCHES]:
                result.append({"id":f"classes_{level}_{strategy}_{label}_{runs}","group":"classes","level":level,
                               "party":[f"{c}_{level}" for c in ("fighter","rogue","wizard","cleric")],"day":f"classes_level_{level}",
                               "strategy":strategy,"variant":label,"runs":runs,"seed":1,"options":asdict(opts)})
    for day in ("easy_day","goblin_warren","hard_day"):
        for strategy in ("nova","conservative"):
            result.append({"id":f"step1_{day}_{strategy}_{main_runs}","group":"step1","level":5,"party":["fighter5","cleric5"],
                           "day":day,"strategy":strategy,"variant":"defaults","runs":main_runs,"seed":1,"options":asdict(DayOptions())})
    return result


def worker(job):
    result = simulate_day(job["party"],job["day"],job["runs"],job["seed"],strategy=job["strategy"],options=job["options"])
    return {**job,"summary":asdict(result)}


def trial_batch(job, start, count):
    """Evaluate an exact seed-one trial slice; no shared actors or RNG."""
    from .builder import load_character
    from .day import run_day
    from .loader import load_spells
    from .policy import strategy_policy
    from .state import Combatant
    opts=DayOptions(**job["options"])
    sheets=[load_character(n,background=opts.backgrounds) for n in job["party"]]
    for sheet in sheets:
        if "position" not in sheet:
            sheet["position"]="front" if sheet["ac"]>=16 and any(a["kind"]=="melee" for a in sheet.get("attacks",[])) else "back"
    definition=load_day(job["day"])
    monsters=day_monsters(definition)
    spells=load_spells()
    policy=strategy_policy(job["strategy"])
    monster_policy=strategy_policy("default")
    rng=random.Random(job["seed"])
    for _ in range(start): rng.getrandbits(64)
    results=[]
    for _ in range(count):
        actors=[Combatant.from_sheet(sheet,f"party_{i}","party") for i,sheet in enumerate(sheets)]
        results.append(run_day(actors,definition,spells,rng.getrandbits(64),policy=policy,
                               monster_policy=monster_policy,monster_sheets=monsters,options=opts))
    return start,results


def summarize_batches(job, batches):
    """Replay evaluated trials into the engine's unchanged summary calculation.

    This local parent-process substitution avoids duplicating summary formulas.
    Child workers have already run real run_day calls with the original seeds.
    """
    from . import day
    results=[]
    for start,part in sorted(batches):
        if start != len(results): raise ValueError("missing/overlapping Monte Carlo batch")
        results.extend(part)
    if len(results)!=job["runs"]: raise ValueError("wrong Monte Carlo trial count")
    iterator=iter(results)
    original=day.run_day
    day.run_day=lambda *args,**kwargs:next(iterator)
    try: return worker(job)
    finally: day.run_day=original


def batch_self_check():
    for job in (jobs(2,2)[0],next(j for j in jobs(2,2) if j["id"]=="step1_easy_day_conservative_2")):
        expected=worker(job)
        actual=summarize_batches(job,[trial_batch(job,1,1),trial_batch(job,0,1)])
        if actual != expected: raise AssertionError("batched and direct simulation differ")
    print("Batched/direct all-field equality: class and fixed-sheet trials passed",flush=True)


def walk(value):
    if isinstance(value,dict):
        yield value
        for v in value.values(): yield from walk(v)
    elif isinstance(value,list):
        for v in value: yield from walk(v)


def budgets():
    from .source_files import archive_member
    book = json.loads(archive_member("data/book/book-xdmg.json"))
    table = next(d for d in walk(book) if d.get("caption") == "XP Budget per Character")
    per_pc = {int(row[0]):[int(n.replace(",","")) for n in row[1:]] for row in table["rows"]}
    result=[]
    for name, level, count in [(f"classes_level_{n}",n,4) for n in (3,5,10)] + [(n,5,2) for n in ("easy_day","goblin_warren","hard_day")]:
        definition=load_day(name); monsters=day_monsters(definition)
        low,moderate,high=[n*count for n in per_pc[level]]
        encounters=[]
        for step in definition["steps"]:
            if "encounter" not in step: continue
            xp=sum(XP[str(monsters[n]["cr"])] for n in encounter_names(step["encounter"]))
            label="Low" if xp<=low else "Moderate" if xp<=moderate else "High" if xp<=high else "Above High"
            encounters.append({"index":len(encounters)+1,"monsters":step["encounter"],"xp":xp,"difficulty":label})
        result.append({"day":name,"level":level,"party_size":count,"low":low,"moderate":moderate,"high":high,"encounters":encounters})
    return {"source":"5etools-v2.30.1.zip:data/book/book-xdmg.json, XP Budget per Character (2024 DMG p.114)","days":result}


def fingerprint():
    names=("builder.py","combat.py","class_mechanics.py","day.py","day_options.py","day_mechanics.py","dice.py","monster_mechanics.py","policy.py","state.py","sheets.py","spell_mechanics.py","summoning.py")
    return hashlib.sha256(b"".join((ROOT/"engine"/n).read_bytes() for n in names)).hexdigest()


def repro_worker(name, shared):
    """Isolate finding 7 in memory; never change a spell/monster/source file."""
    import inspect
    import textwrap
    from .combat import Combat
    from .simulate import simulate
    original = Combat.resolve_block
    if not shared:
        source = textwrap.dedent(inspect.getsource(original))
        old = ' or block["save"] and not block["attack"]'
        if old not in source: raise AssertionError("save-roll control no longer applies")
        namespace = {}
        exec(compile(source.replace(old, ''), '<independent save-roll control>', 'exec'), original.__globals__, namespace)
        Combat.resolve_block = namespace['resolve_block']
    try:
        return name, shared, asdict(simulate(("fighter5", "fighter5", "cleric5", "cleric5"), (name,), 500, 1))
    finally: Combat.resolve_block = original


def reproducibility_baselines(output, workers):
    from .step3_report import MONSTERS
    result = {"engine_sha256":fingerprint(), "runs":500, "seed":1,
              "party":["fighter5", "fighter5", "cleric5", "cleric5"], "monsters":{}}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        pending = [pool.submit(repro_worker, name, shared) for name in (*MONSTERS, "young_white_dragon") for shared in (False, True)]
        for future in as_completed(pending):
            name, shared, summary = future.result()
            result["monsters"].setdefault(name, {})["shared" if shared else "independent_control"] = summary
            print(f"{name} {'shared' if shared else 'independent control'}: {summary['wins']}/500", flush=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True)+"\n", encoding="utf8")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers",type=int,default=8)
    parser.add_argument("--main-runs",type=int,default=1000)
    parser.add_argument("--sensitivity-runs",type=int,default=300)
    parser.add_argument("--batch-size",type=int,default=100,help="trials per task; zero uses original whole-row tasks")
    parser.add_argument("--self-check",action="store_true")
    parser.add_argument("--main-only",action="store_true",help="six class rows and six Step-1 rows, no sensitivity rerun")
    parser.add_argument("--legacy-controls",action="store_true",help="also recheck the two exact seeded standard-day legacy baselines")
    parser.add_argument("--repro-baselines",action="store_true",help="500-run CR rows and matched in-memory independent-save controls only")
    parser.add_argument("--output",type=Path,default=ROOT/"data/reports/step4_fix_results.json")
    args=parser.parse_args()
    if args.repro_baselines:
        reproducibility_baselines(args.output, args.workers)
        return
    if args.self_check:
        batch_self_check()
        return
    if args.batch_size<0: parser.error("batch-size must be nonnegative")
    args.output.parent.mkdir(parents=True,exist_ok=True)
    stamp=fingerprint()
    artifact={"engine_sha256":stamp,"budgets":budgets(),"rows":[]}
    if args.output.exists():
        previous=json.loads(args.output.read_text(encoding="utf8"))
        if previous["engine_sha256"]!=stamp: raise SystemExit("Engine changed: use a fresh --output to avoid mixing checkpoints")
        artifact["rows"]=previous["rows"]
    completed={r["id"] for r in artifact["rows"]}
    requested = jobs(args.main_runs,args.sensitivity_runs)
    if args.main_only: requested = [j for j in requested if j["variant"] == "defaults"]
    if args.legacy_controls:
        for strategy in ("nova", "conservative"):
            job = next(j for j in requested if j["group"] == "step1" and j["day"] == "goblin_warren" and j["strategy"] == strategy).copy()
            job.update(id=f"legacy_goblin_warren_{strategy}_{args.main_runs}", variant="legacy", options=asdict(DayOptions.legacy()))
            requested.append(job)
    todo=[job for job in requested if job["id"] not in completed]
    partial={j["id"]:[] for j in todo}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        pending={}
        # Spread expensive 1,000-run rows across cores too, avoiding a long
        # single-core tail. Row RNG sequences and summary formulas are unchanged.
        for job in sorted(todo,key=lambda j:(-j["runs"],-j["level"],j["id"])):
            if not args.batch_size:
                pending[pool.submit(worker,job)]=job
            else:
                for start in range(0,job["runs"],args.batch_size):
                    pending[pool.submit(trial_batch,job,start,min(args.batch_size,job["runs"]-start))]=job
        for future in as_completed(pending):
            job=pending[future]
            if args.batch_size:
                partial[job["id"]].append(future.result())
                if sum(len(part) for start,part in partial[job["id"]]) != job["runs"]: continue
                row=summarize_batches(job,partial.pop(job["id"]))
            else: row=future.result()
            artifact["rows"].append(row)
            artifact["rows"].sort(key=lambda r:r["id"])
            args.output.write_text(json.dumps(artifact,indent=2,ensure_ascii=False)+"\n",encoding="utf8")
            s=row["summary"]
            print(f"{len(artifact['rows'])}/{len(requested)} {row['id']}: {s['survived']}/{s['runs']}; deaths={s['mean_deaths']:.3f}; slots={s['mean_slots_end']:.3f}",flush=True)


if __name__=="__main__": main()
