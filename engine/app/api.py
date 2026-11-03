"""The web app's operations: plain functions from a JSON request to a JSON-ready result.

Each function validates its request (raising ValueError with a message the page
shows), calls the engine, and returns dicts, lists, numbers and strings only.
Long operations take a log(message) callback for progress lines.
"""
from dataclasses import asdict
from fractions import Fraction
import re

from ..calibration import BUDGETS, DIFFICULTIES, XP_BY_CR, budget
from ..loader import ROOT, load_sheet

STRATEGIES = ("default", "nova", "conservative", "rationed")
MORALE = ("none", "dmg", "rout")
PROFILES = ("casual", "standard", "optimized")
NAME = re.compile(r"[a-z][a-z0-9_]*")


# ---------- shared request parsing ----------

def _choice(value, options, field, default=None):
    if value is None: value = default
    if value not in options: raise ValueError(f"{field}: expected one of {', '.join(map(str, options))}")
    return value


def _int(value, field, lo, hi, default=None):
    if value is None and default is not None: return default
    if type(value) is not int or not lo <= value <= hi: raise ValueError(f"{field}: expected a whole number from {lo} to {hi}")
    return value


def _build_name(name, field="party"):
    if not isinstance(name, str) or not NAME.fullmatch(name) or not (ROOT / "builds" / f"{name}.yaml").is_file():
        raise ValueError(f"{field}: unknown build {name!r}")
    return name


def party_of(req):
    """{"party": {"preset": {"level", "profile"}} | {"builds": [...]}, "items": null|"half"|"full"} -> builds list."""
    from ..presets import party, preset_levels
    p = req.get("party") or {}
    if "builds" in p:
        builds = p["builds"]
        if not isinstance(builds, list) or not 1 <= len(builds) <= 8: raise ValueError("party: choose 1 to 8 builds")
        builds = [_build_name(b) for b in builds]
    else:
        preset = p.get("preset") or {}
        level = _int(preset.get("level"), "party level", 1, 20, 5)
        if level not in preset_levels(): raise ValueError(f"party level: presets exist for levels {', '.join(map(str, preset_levels()))}")
        builds = party(level, _choice(preset.get("profile"), PROFILES, "party profile", "standard"))
    items = _choice(req.get("items"), (None, "half", "full"), "items")
    if items:
        from ..items import with_items
        builds = with_items(builds, items)
    return builds


def _levels(builds):
    from ..day_options import DayOptions
    from ..encounters import party_sheets
    return [s["level"] for s in party_sheets(builds, DayOptions())]


def _label(build):
    if isinstance(build, dict):
        items = build.get("choices", {}).get("items")
        return build["name"] + (f" [{', '.join(items)}]" if items else "")
    return build


def monster_entries(groups, field="monsters"):
    """[{"name": "ogre", "count": 2}, ...] -> ["ogre x2", ...]."""
    if not isinstance(groups, list) or not groups: raise ValueError(f"{field}: add at least one monster")
    out = []
    for g in groups:
        name = g.get("name") if isinstance(g, dict) else None
        if not isinstance(name, str) or not NAME.fullmatch(name) or not (ROOT / "monsters" / f"{name}.yaml").is_file():
            raise ValueError(f"{field}: unknown monster {name!r}")
        count = _int(g.get("count"), f"{field}: count of {name}", 1, 40, 1)
        out.append(name if count == 1 else f"{name} x{count}")
    return out


def _xp(entries):
    from ..day import encounter_names
    return sum(XP_BY_CR[str(load_sheet(ROOT / "monsters" / f"{n}.yaml")["cr"])] for n in encounter_names(entries))


def budget_info(xp, levels):
    if any(l not in BUDGETS for l in levels): return {"xp": xp}
    low, moderate, high = (sum(BUDGETS[l][k] for l in levels) for k in range(3))
    band = "Low" if xp <= low else "Moderate" if xp <= moderate else "High" if xp <= high else "above High"
    return {"xp": xp, "low": low, "moderate": moderate, "high": high, "multiple": xp / high, "band": band}


def _common(req):
    return {"seed": _int(req.get("seed"), "seed", 0, 10**9, 1),
            "strategy": _choice(req.get("strategy"), STRATEGIES, "strategy", "default"),
            "monster_strategy": _choice(req.get("monster_strategy"), STRATEGIES, "monster strategy", "default"),
            "morale": _choice(req.get("morale"), MORALE, "morale", "none")}


# ---------- reference data ----------

def meta():
    """Everything the page needs to fill its menus."""
    from ..builder import SPECIES
    from ..compare import CLASSES
    from ..presets import preset_levels
    from ..templates import TEMPLATES
    monsters = []
    for path in sorted((ROOT / "monsters").glob("*.yaml")):
        s = load_sheet(path)
        monsters.append({"name": path.stem, "label": s["name"], "cr": str(s["cr"]), "cr_value": float(Fraction(str(s["cr"]))),
                         "xp": XP_BY_CR[str(s["cr"])], "hp": s["max_hp"], "ac": s["ac"], "type": s.get("creature_type", ""),
                         "unsupported": s.get("unsupported", [])})
    monsters.sort(key=lambda m: (m["cr_value"], m["name"]))
    builds = []
    for path in sorted((ROOT / "builds").glob("*.yaml")):
        m = re.fullmatch(r"([a-z]+)_(\d+)(?:_([a-z]+))?", path.stem)
        if m: builds.append({"name": path.stem, "class": m[1], "level": int(m[2]), "profile": m[3] or "standard"})
    order = {"standard": 0, "casual": 1, "optimized": 2}
    builds.sort(key=lambda b: (b["class"], b["level"], order.get(b["profile"], 3), b["name"]))
    return {"preset_levels": preset_levels(), "profiles": list(PROFILES), "strategies": list(STRATEGIES), "morale": list(MORALE),
            "difficulties": list(DIFFICULTIES), "templates": {k: v for k, v in TEMPLATES.items()},
            "themes": sorted({m["type"] for m in monsters if m["type"]}), "classes": list(CLASSES),
            "species": {k: sorted(v) if v else None for k, v in SPECIES.items()}, "monsters": monsters, "builds": builds,
            "budgets": {str(l): list(v) for l, v in BUDGETS.items()}}


def build_sheet(req):
    """The built character sheet of one build, for the build viewer."""
    from ..builder import load_character
    sheet = load_character(_build_name(req.get("name"), "build"))
    keep = ("name", "level", "max_hp", "ac", "abilities", "speed", "proficiency_bonus", "spell_dc", "spell_attack_bonus",
            "spell_slots", "spells", "limited_uses", "resistances", "save_proficiencies", "unsupported")
    out = {k: sheet[k] for k in keep if k in sheet}
    def dmg(d):
        bonus = d.get("bonus") or 0
        flat = f"{bonus:+d}" if isinstance(bonus, int) and bonus else ""
        return f"{d.get('dice', '')}{flat} {d.get('type', '')}".strip()
    out["attacks"] = [{"name": a["name"], "to_hit": a["to_hit"], "damage": " + ".join(dmg(p["damage"]) for p in a["effects"] if "damage" in p)}
                      for a in sheet.get("attacks", [])]
    out["features"] = sorted(k for k, v in sheet.get("features", {}).items() if v)
    return out


# ---------- DM: one fight, one day ----------

def fight(req, log=lambda m: None):
    from ..encounters import Adaptive, run_encounter
    builds = party_of(req)
    entries = monster_entries(req.get("monsters"))
    runs = req.get("runs")
    spec = Adaptive(min_runs=100) if runs in (None, 0, "") else _int(runs, "runs", 10, 5000)
    common = _common(req)
    cover = bool(req.get("cover"))
    log(f"Simulating {', '.join(entries)} against {', '.join(map(_label, builds))}")
    result = run_encounter(builds, entries, spec, common["seed"], detail=True, cover=cover, morale=common["morale"],
                           strategy=common["strategy"], monster_strategy=common["monster_strategy"])
    if not result["runs"]: raise ValueError("every run hit an engine error: " + "; ".join(result["errors"]))
    return {"party": [_label(b) for b in builds], "encounter": entries, "budget": budget_info(_xp(entries), _levels(builds)),
            "options": {**common, "cover": cover, "items": req.get("items")}, **result}


def day(req, log=lambda m: None):
    from ..day import validate_day
    from ..encounters import run_day_runs
    builds = party_of(req)
    raw = req.get("steps")
    if not isinstance(raw, list) or not raw: raise ValueError("steps: add at least one encounter")
    steps = []
    for i, s in enumerate(raw, 1):
        if isinstance(s, dict) and s.get("rest") in ("short", "long"): steps.append({"rest": s["rest"]})
        elif isinstance(s, dict) and "encounter" in s: steps.append({"encounter": monster_entries(s["encounter"], f"step {i}")})
        else: raise ValueError(f"step {i}: expected an encounter or a short/long rest")
    if not any("encounter" in s for s in steps): raise ValueError("steps: add at least one encounter")
    definition = {"name": "web day", "steps": steps}
    validate_day(definition)
    runs = _int(req.get("runs"), "runs", 10, 5000, 400)
    common = _common(req)
    log(f"Simulating a day of {sum('encounter' in s for s in steps)} encounters, {runs} runs")
    result = run_day_runs(builds, definition, runs, common["seed"], detail=True, morale=common["morale"],
                          strategy=common["strategy"], monster_strategy=common["monster_strategy"])
    if not result["runs"]: raise ValueError("every run hit an engine error: " + "; ".join(result["errors"]))
    levels = _levels(builds)
    fights = iter(result["encounters"])
    rows = []
    for s in steps:
        if "rest" in s: rows.append({"rest": s["rest"]})
        else: rows.append({"encounter": s["encounter"], "budget": budget_info(_xp(s["encounter"]), levels), **next(fights)})
    total = sum(_xp(s["encounter"]) for s in steps if "encounter" in s)
    guideline = 3 * sum(BUDGETS[l][1] for l in levels if l in BUDGETS)
    out = {k: v for k, v in result.items() if k != "encounters"}
    return {"party": [_label(b) for b in builds], "steps": rows, "day_xp": total, "guideline_xp": guideline,
            "options": {**common, "items": req.get("items")}, **out}


# ---------- encounter suggestions ----------

def suggest(req):
    from ..templates import TEMPLATES, describe, encounter_entries, parse_shape, suggest as fill
    level = _int(req.get("level"), "level", 1, 20, 5)
    size = _int(req.get("size"), "party size", 1, 8, 4)
    if req.get("xp"): total = _int(req.get("xp"), "XP budget", 10, 10**7)
    else: total = budget(level, _choice(req.get("difficulty"), DIFFICULTIES, "difficulty", "moderate"), size)
    if req.get("shape"): shape = parse_shape(str(req["shape"]))
    else: shape = TEMPLATES[_choice(req.get("template"), tuple(TEMPLATES), "template", "boss_minions")]
    themes = req.get("themes") or None
    if themes is not None and (not isinstance(themes, list) or not all(isinstance(t, str) for t in themes)): raise ValueError("themes: expected a list of creature types")
    picks = fill(shape, total, seed=_int(req.get("seed"), "seed", 0, 10**9, 1), count=_int(req.get("count"), "count", 1, 10, 4), themes=themes)
    return {"budget": total, "level": level, "size": size,
            "suggestions": [{"label": describe(f, xp, total), "xp": xp, "share": xp / total,
                             "monsters": [{"name": m, "count": n, "role": r} for r, m, n, _ in f], "entries": encounter_entries(f)}
                            for f, xp in picks]}


# ---------- builds: compare, search, rating ----------

def _rating_dict(r):
    return {"xp": r.xp, "multiple": r.multiple(r.xp), "per_pc": r.per_char(r.xp), "runs": r.runs, "level": r.level,
            "types": {k: {"xp": t.xp, "multiple": r.multiple(t.xp), "censored": t.censored} for k, t in r.types.items()}}


def rate(req, log=lambda m: None):
    from ..rating import rate_party
    builds = party_of(req)
    common = _common(req)
    log(f"Rating {', '.join(map(_label, builds))} against the benchmark (several minutes)")
    r = rate_party(builds, seed=common["seed"], strategy=common["strategy"], morale=common["morale"], cover=bool(req.get("cover")),
                   workers=req.get("workers"))
    return {"party": [_label(b) for b in builds], **_rating_dict(r)}


def compare(req, log=lambda m: None):
    from .. import compare as cmp
    level = _int(req.get("level"), "level", 1, 20, 5)
    cls = _choice(req.get("class"), cmp.CLASSES, "class")
    mode = _choice(req.get("mode"), ("variants", "feats", "abilities", "species", "candidates"), "mode", "feats")
    runs = _int(req.get("runs"), "runs per step", 50, 2000, 400)
    if mode == "candidates":
        cands = req.get("candidates")
        if not isinstance(cands, list) or not cands: raise ValueError("candidates: choose at least one build")
        found = [_build_name(c, "candidates") for c in cands]
    else:
        if mode == "abilities": found = cmp.ability_variants(cls, level)
        elif mode == "species":
            base = cmp.standard_recipe(cls, level); found = [base] + cmp.species_variants(base)
        else: found = cmp.variants(cls, level, feats_only=(mode == "feats"))
    parties = None
    if req.get("party"):
        party = [_build_name(b) for b in req["party"]]
        member = req.get("replace") or next((b for b in party if b.split("_")[0] == cls), None)
        if member not in party: raise ValueError("replace: choose the party member the candidates replace")
        parties = {"your party": (party, party.index(member))}
    screened = None
    finalists = _int(req.get("finalists"), "finalists", 1, 40, 4)
    if mode != "candidates" and len(found) - 1 > finalists:
        log(f"Screening {len(found) - 1} variants with a short run")
        scores = cmp.sim_screen(level, cls, found, runs=max(50, runs // 4), parties=parties)
        ranked = sorted(scores[1:], key=lambda vs: -vs[1])[:finalists]
        candidates = [found[0]] + [v for v, _ in ranked]
        screened = [{"name": v["name"], "change": s, "rated": v in candidates} for v, s in sorted(scores, key=lambda vs: -vs[1])]
    else:
        candidates = found
    log(f"Measuring {len(candidates)} candidates, {runs} runs per deciding ladder step")
    results = cmp.focused_compare(level, cls, candidates, ("standard",), runs=runs, parties=parties)
    out = []
    for ref, d in results.items():
        rows = [{"name": name, "overall": list(ch["overall"]),
                 "types": {k: {"change": list(v[:3]), "edge": bool(v[3])} for k, v in ch.items() if k != "overall"}}
                for name, ch in d["rows"]]
        out.append({"party": [cmp.label(b) for b in d["party"]], "replacing": cmp.label(d["member"]), "base": _rating_dict(d["base"]),
                    "runs": d["focused"].runs, "rows": sorted(rows, key=lambda r: -r["overall"][0])})
    return {"level": level, "class": cls, "mode": mode, "screen": screened, "results": out}


def optimize(req, log=lambda m: None):
    from ..optimize import DEFAULT_FINALISTS, MIN_GAIN, optimize as search
    party = req.get("party")
    if not isinstance(party, list) or not 1 <= len(party) <= 8: raise ValueError("party: choose 1 to 8 builds")
    party = [_build_name(b) for b in party]
    member = req.get("member")
    if member not in party: raise ValueError("member: choose the party member to improve")
    runs = _int(req.get("runs"), "runs per step", 50, 2000, 300)
    screen = _int(req.get("screen_runs"), "screen runs per step", 20, 1000, 60)
    final, steps = search(party, member, runs=runs, screen_runs=screen, finalists=_int(req.get("finalists"), "finalists", 1, 10, DEFAULT_FINALISTS),
                          max_rounds=_int(req.get("rounds"), "rounds", 1, 10, 4), min_gain=req.get("min_gain", MIN_GAIN), log=log)
    return {"party": party, "member": member, "final": final,
            "rounds": [{"round": s.round, "accepted": s.accepted, "rating": s.rating,
                        "finalists": [{"name": f[0], "change": list(f[1:4])} for f in s.finalists],
                        "screened": [{"name": x[0], "change": list(x[1:4])} for x in s.screened]} for s in steps]}
