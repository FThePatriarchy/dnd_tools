"""Schema and independent numeric evidence for referenced XPHB stat blocks."""
import json
from functools import lru_cache
import re

from .loader import ROOT


def validate_summon(v, value, path):
    from .sheets import validate_sheet
    v.obj(value, path, "choice forms base_slot per_slot", "attack_count_divisor ends_on_damage creature_type_choice fixed_attacks persistent mount fly_slot after_attack_action count count_per_slot command_cost familiar control_hours form_cost damage_dice_add")
    v.check(value["choice"] in {"$" + c for c in v.choices}, path + ".choice", "unknown summon choice")
    v.number(value["base_slot"], path + ".base_slot", 1, True)
    for flag in ("persistent", "mount", "familiar", "ends_on_damage"):
        if flag in value: v.boolean(value[flag], path)
    for k in ("fixed_attacks", "fly_slot", "count_per_slot", "control_hours"):
        if k in value: v.number(value[k], path, 1, True)
    if "count" in value and value["count"] != "spell_mod": v.number(value["count"], path, 1, True)
    if "command_cost" in value: v.enum(value["command_cost"], {"bonus_action"}, path)
    v.check(("attack_count_divisor" in value) != ("fixed_attacks" in value), path, "exactly one attack count rule required")
    if "attack_count_divisor" in value: v.number(value["attack_count_divisor"], path + ".attack_count_divisor", 1, True)
    if "form_cost" in value:
        for n in value["form_cost"].values(): v.number(n, path, 1, True)
    if "damage_dice_add" in value:
        for d in value["damage_dice_add"].values(): v.dice(d, path)
    v.obj(value["per_slot"], path + ".per_slot", "ac max_hp damage_bonus")
    for key, n in value["per_slot"].items(): v.number(n, path + ".per_slot." + key, 0, True)
    v.check(isinstance(value["forms"], dict) and bool(value["forms"]), path + ".forms", "expected nonempty forms")
    options = getattr(v, "choice_options", {}).get(value["choice"][1:], [])
    v.check(set(value["forms"]) == set(options), path + ".forms", "forms must match the declared choice options")
    for name, sheet in value["forms"].items():
        v.text(name, path + ".forms")
        validate_sheet(sheet, v.filename + ":" + path + ".forms." + name, summoned=True)


@lru_cache(maxsize=1)
def source_stat_blocks():
    path = ROOT.parents[1] / "raw_data/bestiary/bestiary-xphb.json"
    return {s["name"]: s for s in json.loads(path.read_text(encoding="utf8"))["monster"]}


def referenced_stat_block(raw):
    matches = re.findall(r"\{@creature ([^|}]+)\|XPHB", json.dumps(raw["entries"]))
    return source_stat_blocks()[matches[0]]


def _original_number(path, declaration, source):
    """Derive a field from its specific printed stat entry, not a number pool."""
    base = source["summonedBySpellLevel"]
    hp_text = source["hp"]["special"]
    if path == ("base_slot",): return base
    if path == ("attack_count_divisor",):
        text = json.dumps(next(a for a in source["action"] if a["name"] == "Multiattack")["entries"])
        return 2 if "half" in text and "round down" in text else None
    if path[:1] == ("per_slot",):
        if path[-1] == "ac": return 1 if "+ the spell's level" in source["ac"][0]["special"] else None
        if path[-1] == "max_hp":
            m = re.search(r"\+ (\d+) for each spell level above", hp_text)
            return int(m[1]) if m else None
        if path[-1] == "damage_bonus": return 1 if "summonSpellLevel" in json.dumps(source["action"]) else None
    if len(path) < 3 or path[0] != "forms": return None
    form, field = path[1:3]
    rest = path[3:]
    if field == "ac":
        m = re.fullmatch(r"(\d+) \+ the spell's level", source["ac"][0]["special"])
        return int(m[1]) + base if m else None
    if field == "max_hp":
        for amount, clause in re.findall(r"(\d+) \(([^)]+)\)", hp_text):
            if form in clause.lower(): return int(amount)
        match = re.match(r"(\d+) \+ \d+ for each spell level above", hp_text)
        return int(match[1]) if match else None
    if field == "abilities": return source.get(rest[0])
    if field == "speed": return source["speed"].get("walk", 0)
    if field == "movement_modes":
        val = source["speed"].get(rest[0])
        if isinstance(val, dict):
            if "only" in val.get("condition", "").lower() and form not in val["condition"].lower(): return None
            return val["number"]
        return val
    if field == "attacks":
        attack = next((a for a in source["action"] if a["name"] != "Multiattack" and ("Only" not in a["name"] or form in a["name"].lower())), None)
        if attack is None: return None
        text = " ".join(attack["entries"])
        if rest[-1] == "reach_ft":
            m = re.search(r"reach (\d+) ft", text)
            return int(m[1]) if m else 0  # Established schema sentinel for ranged reach.
        if rest[-1] == "range_ft":
            m = re.search(r"range (\d+) ft", text)
            return int(m[1]) if m else None
        m = re.search(r"\{@damage (\d+d\d+) \+ (\d+) \+ summonSpellLevel\}", text)
        if m and rest[-1] == "dice": return m[1]
        if m and rest[-1] == "bonus": return int(m[2]) + base
    if field == "traits" and rest[-1] == "size_ft":
        entry = next((t for t in source["trait"] if form in t["name"].lower() and "Aura" in t["name"]), None)
        m = re.search(r"(\d+)-foot Emanation", json.dumps(entry)) if entry else None
        return int(m[1]) if m else None
    return None


def expected_summon_number(path, declaration, source):
    base = source["summonedBySpellLevel"]
    if path == ("fixed_attacks",): return 1 if not any(a["name"] == "Multiattack" for a in source["action"]) else None
    if path == ("fly_slot",): return int(re.search(r"level (\d+)\+", str(source["speed"]["fly"]))[1])
    if path == ("attack_count_divisor",) and "fixed_attacks" in declaration: return 2  # Unused divisor's format identity; fixed count overrides it.
    if path == ("per_slot", "ac") and "per spell level" in source["ac"][0].get("special", ""): return 1
    if path == ("per_slot", "max_hp") and "per spell level" in source["hp"]["special"]: return int(re.search(r"(\d+) per spell level", source["hp"]["special"])[1])
    if len(path) >= 3 and path[0] == "forms":
        form, field = path[1:3]; rest = path[3:]; sheet = declaration["forms"][form]
        if field == "ac":
            text = source["ac"][0]["special"]
            result = int(re.match(r"\d+", text)[0]) + base
            m = re.search(r"\+ (\d+) \(([^)]+) only\)", text)
            if m and form in m[2].lower(): result += int(m[1])
            return result
        if field == "max_hp" and "per spell level" in source["hp"]["special"]:
            t=source["hp"]["special"]; return int(re.match(r"\d+",t)[0])+base*int(re.search(r"(\d+) per spell level",t)[1])
        if field == "attacks":
            a = sheet["attacks"][rest[0]]
            raw = next(x for x in source["action"] if x["name"] == a["name"] or x["name"].split(" (")[0] == a["name"])
            text = " ".join(raw["entries"])
            if rest[-1] == "reach_ft":
                m = re.search(r"reach (\d+) (?:ft|feet)",text); return int(m[1]) if m else 0
            if rest[-1] == "range_ft": return int(re.search(r"range (\d+) ft",text)[1])
            if "on_hit_self" in rest: return re.search(r"\{@dice ([^}]+)\} Temporary",text)[1]
            if rest[-1] in {"dice", "bonus"} and "damage" in rest:
                expressions = re.findall(r"\{@damage (\d+d\d+)(?: \+ (\d+))?( \+ summonSpellLevel)?\}",text)
                # Source order is the executable damage-component order.
                i = rest[rest.index("effects") + 1]
                die, flat, slot = expressions[i]
                return die if rest[-1] == "dice" else int(flat or 0)+(base if slot else 0)
            if rest[-1] == "value" and "Speed is reduced to 0" in text: return 0
        if field in {"traits", "actions"}:
            record = sheet[field][rest[0]]; raw_records = source.get("trait",[])+source.get("action",[])+source.get("bonus",[])+source.get("reaction",[])
            raw = next((x for x in raw_records if x["name"].split(" (")[0] == record["name"]),None)
            if raw:
                text = json.dumps(raw)
                key=rest[-1]
                if key=="size_ft":
                    m=re.search(r"(\d+)(?:-foot| feet)",text); return int(m[1]) if m else None
                if key=="dice":
                    m=re.search(r"\{@(?:damage|dice) (\d+d\d+)",text);return m[1] if m else None
                if key=="bonus": return 0
                if key=="value" and "halved" in text:return .5
                if key=="uses":return 1 if "next attack roll" in text else None
                if key=="n":
                    m=re.search(r"for (\d+) minute",text);return int(m[1]) if m else None
                if key=="count":return 1 if "a Slam attack" in text else None
        if field=="limited_uses":
            return 1 if any(rest[0] in a["name"] and ("1/Day" in a["name"] or "Long Rest" in a["name"]) for a in source.get("action",[])+source.get("bonus",[])) else None
        if field=="features" and rest==("regeneration","amount"):
            return int(re.search(r"regains (\d+) Hit Points",json.dumps(source["trait"]))[1])
    return _original_number(path, declaration, source)


def expected_spell_summon_number(path, declaration, raw):
    from .spell_validation import text_entries
    text = text_entries(raw["entries"])
    if "{@creature Animated Object|XPHB}" in text: return animated_number(path, declaration, raw)
    if re.search(r"\{@creature [^|}]+\|XPHB",text): return expected_summon_number(path,declaration,referenced_stat_block(raw))
    if path == ("base_slot",): return raw["level"]
    if path[:1] == ("per_slot",): return 0  # XMM referenced block is fixed; upcast changes only count.
    if path == ("fixed_attacks",): return 1
    if path == ("count",): return 1 if "The target becomes an Undead creature" in text else None
    if path == ("count_per_slot",): return 2 if "two additional Undead" in text_entries(raw.get("entriesHigherLevel",[])) else None
    if path == ("control_hours",): return int(re.search(r"control for (\d+) hours",text)[1])
    if path[:1] == ("forms",):
        sheet=declaration["forms"][path[1]]
        return fixed_number(path[2:],sheet,raw)
    return None


def fixed_number(path, sheet, spell):
    from .spell_validation import text_entries
    from fractions import Fraction
    r=xmm_stat_blocks()[sheet["name"]];key=path[0];rest=path[1:]
    if key=="cr": return str(r["cr"])
    if key=="max_hp": return r["hp"]["average"]
    if key=="ac": return r["ac"][0] if isinstance(r["ac"][0],int) else r["ac"][0]["ac"]
    if key=="abilities": return r[rest[0]]
    if key=="proficiency_bonus": return max(2,2+(max(1,int(Fraction(str(r["cr"]))))-1)//4)
    if key in {"speed","movement_modes"}:
        if spell["name"]=="Phantom Steed": return int(re.search(r"Speed[^.]+?of (\d+) feet",text_entries(spell["entries"]))[1])
        val=r["speed"].get(rest[0] if rest else "walk",0)
        return val["number"] if isinstance(val,dict) else val
    if key=="features" and rest==("undead_fortitude",): return int(re.search(r"\{@dc (\d+)\} plus the damage",json.dumps(r["trait"]))[1])
    if key=="attacks":
        a=sheet["attacks"][rest[0]];entry=next(x for x in r["action"] if x["name"]==a["name"])
        text=json.dumps(entry); k=rest[-1]
        if k=="to_hit":return int(re.search(r"\{@hit ([+-]?\d+)\}",text)[1])
        if k=="reach_ft":
            m=re.search(r"reach (\d+) ft",text);return int(m[1]) if m else 0
        if k=="dice":return re.search(r"\{@damage (\d+d\d+)",text)[1]
        if k=="bonus":
            m=re.search(r"\{@damage \d+d\d+(?: \+ (\d+))?",text);return int(m[1] or 0)
    return None


def animated_number(path, declaration, raw):
    source=referenced_stat_block(raw)
    if path==("base_slot",):return raw["level"]
    if path[:1]==("per_slot",):return 0
    if path==("fixed_attacks",):return 1
    if path[:1]==("form_cost",): return {"medium":1,"large":2,"huge":3}[path[1]]  # Explicit one/two/three-object clause in XPHB.
    if path[:1]==("damage_dice_add",):
        higher=json.dumps(raw["entriesHigherLevel"]);m=re.findall(r"\{@damage ([^}]+)\}",higher);return m[{"medium":0,"large":1,"huge":2}[path[1]]]
    if path[:1]==("forms",):
        form,field=path[1:3]; rest=path[3:]
        if field=="ac":return source["ac"][0]
        if field=="max_hp":
            pairs=re.findall(r"(\d+) \(([^)]+)\)",source["hp"]["special"])
            return int(next(n for n,label in pairs if form in label.lower()))
        if field=="abilities":return source[rest[0]]
        if field=="speed":return source["speed"]["walk"]
        if field=="movement_modes":return source["speed"][rest[0]]
        if field=="attacks":
            text=json.dumps(source["action"])
            if rest[-1]=="reach_ft":return int(re.search(r"reach (\d+) ft",text)[1])
            if rest[-1]=="dice":
                dice=re.findall(r"\|([\d]+d\d+) \+ 3\}",text);return dice[{"medium":0,"large":1,"huge":2}[form]]
            if rest[-1]=="bonus":return int(re.search(r"\|\d+d\d+ \+ (\d+)\}",text)[1])
    return None


@lru_cache(maxsize=1)
def xmm_stat_blocks():
    path = ROOT.parents[1] / "raw_data/bestiary/bestiary-xmm.json"
    return {m["name"]: m for m in json.loads(path.read_text(encoding="utf8"))["monster"]}
