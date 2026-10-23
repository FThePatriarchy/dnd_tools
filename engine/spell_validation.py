"""Independent XPHB text/tag gate. Does not call translation recipes.

Checks source numbers at their semantic field, not hashes or a source-wide
numeric pool. Unrecognized numeric paths are errors, not silent exceptions.
"""
import json
from pathlib import Path
import re
from functools import lru_cache

from .loader import ROOT, Validator


def source_spells():
    path = ROOT.parents[1] / "raw_data/spell/spells-xphb.json"
    st = path.stat()
    return _source_spells(str(path), st.st_mtime_ns, st.st_size)


@lru_cache(maxsize=1)
def _source_spells(path, mtime_ns, size):
    # Source evidence is read-only; it is never a mutation candidate.
    return {s["name"]: s for s in json.loads(Path(path).read_text(encoding="utf8"))["spell"]}


def text_entries(value):
    if isinstance(value, str): return value
    if isinstance(value, list): return " ".join(map(text_entries, value))
    if isinstance(value, dict): return " ".join(text_entries(v) for k, v in value.items() if k in {"entries", "items", "entry", "name"})
    return ""


def dice_in(text):
    return {re.sub(r"\s+", "", d).lower() for d in re.findall(r"\{@(?:damage|dice|scaledamage|scaledice)\s+([^|}]+)", text)}


def numeric_fields(value, path=()):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from numeric_fields(item, path + (key,))
    elif isinstance(value, list):
        for i, item in enumerate(value): yield from numeric_fields(item, path + (i,))
    elif type(value) in {int, float} or isinstance(value, str) and re.search(r"\d", value):
        yield path, value


def get(data, path):
    for key in path: data = data[key]
    return data


def source_errors(spec, raw=None, *, validate=True):
    raw = raw or source_spells()[spec["name"]]
    errors = numeric_coverage_errors(spec)
    if validate:
        try: Validator(spec["name"]).spell(spec)
        except ValueError as exc: return [str(exc)]
    entries = text_entries(raw["entries"])
    higher = text_entries(raw.get("entriesHigherLevel", []))
    distance_type = raw["range"].get("distance", {}).get("type")
    if raw["range"]["type"] != "point": expected_range = "self"
    else: expected_range = "point" if distance_type == "feet" else distance_type
    if spec["range"]["type"] != expected_range:
        errors.append(f"range.type: expected {expected_range!r} from XPHB, got {spec['range']['type']!r}")
    if expected_range != "point" and "feet" in spec["range"]:
        errors.append("range.feet: self-centred shape/size belongs on the target, not the range")
    d = raw["duration"][0]
    expected_duration = {"instant":"instant", "permanent":"until_dispelled", "special":"special"}.get(d["type"])
    if d["type"] == "timed": expected_duration = {"round":"rounds", "minute":"minutes", "hour":"hours", "day":"hours"}[d["duration"]["type"]]
    if spec["duration"]["type"] != expected_duration: errors.append("duration.type: does not match XPHB unit")
    expected_time = {"bonus":"bonus_action"}.get(raw["time"][0]["unit"], raw["time"][0]["unit"])
    if spec["casting_time"] != expected_time: errors.append("casting_time: does not match XPHB")
    explicit = " ".join(spec["unsupported"]).lower()
    from .monster_validation import executable_tags
    damages, conditions, saves = executable_tags(spec)
    attacks = set()
    def attack_tags(obj):
        if isinstance(obj, dict):
            if obj.get("attack"): attacks.add(obj["attack"]["type"])
            for value in obj.values(): attack_tags(value)
        elif isinstance(obj, list):
            for value in obj: attack_tags(value)
    attack_tags(spec["effects"])
    present = {"damageInflict": damages, "conditionInflict": conditions, "savingThrow": saves, "spellAttack": attacks}
    tags = {"damageInflict": lambda x: x, "conditionInflict": lambda x: x,
            "savingThrow": lambda x: x[:3], "spellAttack": lambda x: {"M": "melee_spell", "R": "ranged_spell"}[x]}
    for key, convert in tags.items():
        for tag in raw.get(key, []):
            if convert(tag) not in present[key] and not any(re.search(r"\b" + re.escape(t) + r"\b", explicit) for t in (tag.lower(), convert(tag))):
                errors.append(f"unrepresented {key}: {tag}")
    for path, value in numeric_fields(spec):
        metadata = expected_numeric_text(spec, path, raw)
        if metadata is not None:
            if value != metadata: errors.append(f"{path}: {value!r}, source text expectation {metadata!r}")
            continue
        if path[0] == "unsupported":
            expected = annotation_numbers(raw, path[-1])
            if re.findall(r"\d+", value) != expected: errors.append(f"{path}: annotation numbers lack source/model evidence: {expected!r}")
            continue
        if "summon" in path:
            from .summon_validation import expected_spell_summon_number
            index = path.index("summon")
            declaration = get(spec, path[:index + 1])
            expected = expected_spell_summon_number(path[index + 1:], declaration, raw)
            if expected is None or value != expected:
                errors.append(f"{path}: {value!r}, XPHB stat-block expectation {expected!r}")
            continue
        if "transform" in path:
            from .summon_validation import fixed_number
            i = path.index("transform"); declaration = get(spec,path[:i+1]); tail=path[i+1:]
            expected = fixed_number(tail[2:],declaration["forms"][tail[1]],raw)
            if value != expected or expected is None: errors.append(f"{path}: {value!r}, beast stat expectation {expected!r}")
            continue
        entries = text_entries(raw["entries"])
        if path[0] == "effects":
            ref = spec["effects"][path[1]].get("source_ref")
            if ref is not None and path[-1] in {"dice", "bonus", "value", "wounded_dice"}:
                m = re.fullmatch(r"entries\.(\d+)", ref)
                if not m or int(m[1]) >= len(raw["entries"]):
                    errors.append(f"invalid spell source_ref: {ref}")
                    continue
                entries = text_entries(raw["entries"][int(m[1])])
        expected = None
        key = path[-1]
        if "weapon_enchantment" in path or "weapon_strike" in path:
            expected = weapon_number(path, raw)
        elif key == "minimum" and "weapon_adjustment" in path: expected = 1 if "below 1" in entries else None
        elif path[:1] == ("duration_tiers",):
            tiers = re.findall(r"level (\d+)(?:[-+]\d*)? spell slot[^.]*?(\d+) minutes|duration becomes (\d+) hours \(level (\d+)|or (\d+) hours \(level (\d+)|level (9) spell slot", higher)
            parsed = []
            for m in tiers:
                if m[0]: parsed.append((int(m[0]), int(m[1])))
                elif m[2]: parsed.append((int(m[3]), int(m[2])))
                elif m[4]: parsed.append((int(m[5]), int(m[4])))
                elif m[6]: parsed.append((int(m[6]), None))
            i = path[1]
            if i < len(parsed): expected = parsed[i][0] if key == "slot_min" else parsed[i][1] if key == "n" else None
        elif key in {"successes", "failures"}: expected = 3 if "three successes or failures" in entries else None
        elif key == "failure_hours":
            m = re.search(r"lasts for (\d+) days", entries); expected = 24 * int(m[1]) if m else None
        elif key == "duration_hours_add":
            m = re.search(r"duration increases by (\d+) hour", higher); expected = int(m[1]) if m else None
        elif path == ("level",): expected = raw["level"]
        elif path == ("casting_time_n",): expected = raw["time"][0]["number"]
        elif path == ("range", "feet"):
            if expected_range == "point": expected = raw["range"].get("distance", {}).get("amount")
        elif path == ("components", "m_cost_gp"):
            m = raw.get("components", {}).get("m", {})
            expected = m.get("cost", 0) / 100 if isinstance(m, dict) and "cost" in m else None
        elif path == ("duration", "n"):
            d = raw["duration"][0].get("duration", {})
            expected = d.get("amount", 0) * (24 if d.get("type") == "day" else 1)
        elif path[0] == "effects" and len(path) > 2 and path[-2:] == ("duration", "n"):
            m = re.search(r"for (\d+) minute", entries)
            expected = int(m[1]) if m else None
        elif path[:2] == ("scaling", "cantrip") and path[2] == "at":
            levels = [int(n) for n in re.findall(r"(?:levels?\s+|,\s*|and\s+)(5|11|17)\b", higher)]
            expected = sorted(set(levels))[path[-1]] if len(set(levels)) == 3 else None
        elif key == "per_slot_above": expected = raw["level"]
        elif path[:3] == ("scaling", "upcast", "changes") and "duration" in get(spec, path[:4]):
            tiers = re.findall(r"(?<!\d)(\d+)(?:-(\d+)|(\+))?\s*\((?:up to )?(\d+) (?:minutes?|hours?)\)", higher)
            index = path[3]
            if index < len(tiers):
                low, high, unlimited, hours = tiers[index]
                expected = {"slot_min": int(low), "slot_max": None if unlimited else int(high or low), "n": int(hours)}.get(key)
        elif key == "area_size_add":
            m = re.search(r"(?:radius|size of the .*?) increases by (\d+) feet", higher)
            expected = int(m[1]) if m else None
        elif key == "area_size_add":
            m = re.search(r"(?:radius|size of the .*?) increases by (\d+) feet", higher)
            expected = int(m[1]) if m else None
        elif key == "beam_count_add":
            expected = 1 if "two beams at level 5, three beams at level 11, and four beams at level 17" in higher else None
        elif key == "range_multiplier": expected = 2 if "range doubles" in higher else None
        elif key == "value_add":
            m = re.search(r"increase(?:s)? by (\d+) for each", higher)
            expected = int(m[1]) if m else 1 if "increases by one for each" in higher else None
        elif key == "ac" and "force_object" in path:
            m = re.search(r"has AC (\d+)", entries); expected = int(m[1]) if m else None
        elif key == "max_dice": expected = 2 if "one or two" in entries else None
        elif key == "floor":
            m = re.search(r"instead drops to (\d+)", entries)
            expected = int(m[1]) if m else None
        elif key == "healing":
            m = re.search(r"restores (\d+)", entries)
            expected = int(m[1]) if m else None
        elif key == "count":
            expected = 10 if "Ten berries" in entries else 3 if "Three illusory duplicates" in entries else None
        elif key == "threshold":
            m = re.search(r"rolls a (\d+) or higher|roll of (\d+)-", entries)
            expected = int(m[1] or m[2]) if m else None
        elif key in {"capacity", "large_cost"}:
            expected = 1 if "only one creature at a time" in entries or "spirit has no creature" in entries or "hand attempts to grapple a" in entries else None
        elif key == "capacity_add": expected = 1 if "increases by one" in higher else None
        elif key == "max_uses": expected = 4 if "up to four" in entries else None
        elif key == "uses_add": expected = 2 if "increases by two" in higher else None
        elif key == "amount" and "max_hp" in path:
            m = re.search(r"increase by (\d+)", entries)
            expected = int(m[1]) if m else None
        elif key == "amount" and "temp_hp" in path:
            m = re.search(r"gain (\d+)", entries)
            expected = int(m[1]) if m else None
        elif key == "amount" and "heal" in path:
            m = re.search(r"regains? (\d+) ", entries)
            expected = int(m[1]) if m else None
        elif key == "amount" and "damage" in path:
            m = re.search(r"(?:taking|takes) (\d+) (?:\w+ )?damage", entries, re.I)
            expected = int(m[1]) if m else None
        elif key == "leech": expected = .5 if "half the amount" in entries else None
        elif key == "end_after_total":
            m = re.search(r"total of (\d+) damage", entries)
            expected = int(m[1]) if m else None
        elif key == "amount_add":
            m = re.search(r"gain (\d+) additional .*?for each spell slot", higher)
            expected = int(m[1]) if m else None
        elif key == "base" and path[-2] == "base_ac":
            m = re.search(r"base AC becomes (\d+)", entries)
            if not m: m = re.search(r"of (\d+) if its AC", entries)
            expected = int(m[1]) if m else None
        elif key == "auto_level":
            m = re.search(r"spell of level (\d+) or lower", entries)
            expected = int(m[1]) if m else None
        elif key == "dc_base":
            m = re.search(r"\{@dc (\d+)\} plus that spell's level", entries)
            expected = int(m[1]) if m else None
        elif key == "attack_limit": expected = 1 if "only one attack" in entries or "one attack only" in entries else None
        elif key == "somatic_failure_percent":
            m = re.search(r"\{@chance (\d+)", entries)
            expected = int(m[1]) if m else None
        elif key in {"n", "min", "target_n_add"} and (key == "target_n_add" or "target" in path):
            words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6}
            if key == "min": expected = 1  # Format identity: at least one target when casting.
            elif key == "target_n_add": expected = 1 if re.search(r"one (?:additional (?:creature|Humanoid|Beast|ray)|more dart)", higher) else None
            else:
                m = re.search(r"(?:[Uu]p to|[Cc]hoose up to) (\w+) creatures", entries)
                if not m: m = re.search(r"(?:create|hurl) (\w+) (?:glowing darts|fiery rays)", entries)
                expected = words.get(m[1], int(m[1]) if m[1].isdigit() else None) if m else 1
        elif key in {"dice_add", "miss_dice_add"}:
            # Upcast increments come only from the higher-slot clause, not base dice.
            increments = re.findall(r"\{@scale(?:damage|dice) [^|]+\|[^|]+\|([^}]+)\}", higher)
            if increments: expected = re.sub(r"\s+", "", increments[0])
            elif "Cantrip Upgrade" in higher:
                dice = re.findall(r"\{@damage (\d+d\d+)\}", higher)
                expected = dice[0] if dice and dice[0].startswith("1d") else ("1d" + re.search(r"d(\d+)", entries)[1] if "one die" in higher else None)
        elif key == "behavior_die":
            expected = re.search(r"roll \{@dice ([^}]+)\} at the start", entries)[1]
        elif key == "dice" and "damage" in path and path[0] == "effects" and "if" in get(spec, path[:-2]) and "fiend, undead" in get(spec, path[:-2])["if"]:
            m = re.search(r"damage increases by \{@damage ([^}]+)\} if the target", entries)
            expected = m[1] if m else None
        elif key in {"dice", "wounded_dice"}:
            if re.sub(r"\s+", "", value) in dice_in(entries): expected = value
            elif value == "1d6" and "{@dice d6}" in entries: expected = "1d6"
            elif key == "dice":
                parent = get(spec, path[:-1])
                combined = value + (f"+{parent['bonus']}" if type(parent.get("bonus")) is int and parent["bonus"] > 0 else "")
                if combined in dice_in(entries): expected = value
        elif key == "bonus":
            # A zero bonus is the explicit no-flat-bonus identity in the format.
            expected = 0
            parent = get(spec, path[:-1])
            for expression in dice_in(entries):
                match = re.fullmatch(re.escape(parent.get("dice", "")) + r"\+(\d+)", expression)
                if match: expected = int(match[1])
        elif key == "size_ft":
            shape = get(spec, path[:-1])["shape"]
            pattern = r"(\d+)-foot(?:-radius)?\s+(?:\{@[^}]*\|)?" + shape
            sizes = [int(n) for n in re.findall(pattern, entries, re.I)]
            expected = sizes[0] if sizes else None
            if expected is None and shape == "cylinder":
                m = re.search(r"(\d+)-foot-radius[^.]*?Cylinder", entries)
                expected = int(m[1]) if m else None
            if expected is None and shape == "line":
                m = re.search(r"(\d+)-foot-long[^.]*?Line", entries)
                if not m: m = re.search(r"wall up to (\d+) feet long", entries, re.I)
                expected = int(m[1]) if m else None
            if expected is None and shape == "sphere":
                m = re.search(r"(?:within|a space within) (\d+) feet of (?:that point|the sphere|the guardian|the spirit|the ammunition|the target|it)", entries, re.I)
                expected = int(m[1]) if m else None
            if expected is None and shape == "sphere":
                m = re.search(r"radius up to (\d+) feet", entries); expected = int(m[1]) if m else None
            if expected is None and shape == "cube":
                m = re.search(r"(\d+)-foot square", entries)
                expected = int(m[1]) if m else None
            if expected is None and get(spec, path[:-1]).get("origin") not in {None, "caster", "spiritual_weapon"}:
                m = re.search(r"target and each creature within (\d+) feet of it", entries)
                expected = int(m[1]) if m else None
            if expected is None and raw["name"] == "Conjure Animals":
                m = re.search(r"moves within (\d+) feet of a creature", entries)
                expected = int(m[1]) if m else None
        elif key == "within_ft":
            m = re.search(r"(\d+)-foot .*?Emanation", entries)
            if not m: m = re.search(r"within (\d+) feet of the force", entries)
            if not m: m = re.search(r"enemy within (\d+) feet of it", entries)
            if not m: m = re.search(r"within (\d+) feet of yourself", entries)
            expected = int(m[1]) if m else None
        elif key == "uses":
            expected = 1 if re.search(r"next (?:attack roll|saving throw)", entries, re.I) else None
        elif key == "value":
            if isinstance(value, str) and value in dice_in(entries): expected = value
            elif get(spec, path[:-1])["stat"] == "ac":
                m = re.search(r"\+(\d+) bonus to (?:\{@variantrule )?(?:AC|Armor Class)", entries)
                penalty = re.search(r"-(\d+) penalty to AC and Dexterity saving throws", entries)
                expected = int(m[1]) if m else -int(penalty[1]) if penalty else None
            elif get(spec, path[:-1])["stat"] == "save" and "+1 bonus to AC and saving throws" in entries: expected = 1
            elif get(spec, path[:-1])["stat"] == "fly_speed":
                m = re.search(r"Fly Speed[^.]*?of (\d+) feet", entries)
                expected = int(m[1]) if m else None
            elif "halved" in entries and get(spec, path[:-1])["stat"] == "speed": expected = .5
            elif re.search(r"-(\d+) penalty to AC and Dexterity saving throws", entries):
                expected = -int(re.search(r"-(\d+) penalty to AC and Dexterity saving throws", entries)[1])
            elif "Speed" in entries:
                m = re.search(r"reduced by (\d+) feet", entries)
                if m: expected = -int(m[1])
                elif re.search(r"increases by (\d+) feet", entries): expected = int(re.search(r"increases by (\d+) feet", entries)[1])
                elif "doubled" in entries and get(spec, path[:-1])["op"] == "mul": expected = 2
                elif (re.search(r"Speed[^.]*?(?:of|is) 0", entries) or "only method of movement" in entries) and get(spec, path[:-1])["op"] == "set": expected = 0
        if expected is None or value != expected:
            errors.append(f"{'.'.join(map(str, path))}: {value!r} not independently justified (expected {expected!r})")
    return errors


def mutants(spec):
    """Each numeric scalar and each dice component, including embedded bonuses."""
    from copy import deepcopy
    for path, value in numeric_fields(spec):
        if isinstance(value, str):
            variants = []
            for match in re.finditer(r"\d+", value):
                variants.append(value[:match.start()] + str(int(match[0]) + 1) + value[match.end():])
        else: variants = [value + 1]
        for variant in variants:
            mutated = deepcopy(spec)
            parent = get(mutated, path[:-1])
            parent[path[-1]] = variant
            yield path, variant, mutated


def weapon_number(path, raw):
    text = text_entries(raw["entries"]); higher = text_entries(raw.get("entriesHigherLevel", []))
    key = path[-1]
    norm = lambda d: "1" + d if d.startswith("d") else d
    if "cantrip_dice" in path:
        i = path[path.index("cantrip_dice") + 1]
        pairs = re.findall(r"(5|11|17) \(\{@damage ([^}]+)\}\)", higher)
        return int(pairs[i][0]) if key == "level" else norm(pairs[i][1])
    if "upgrade_levels" in path:
        levels = re.findall(r"(5|11|17) \(\{@damage", higher)
        return int(levels[path[-1]])
    if "tiers" in path:
        i = path[path.index("tiers") + 1]
        sentences = [t for t in re.split(r"\. ", higher) if re.search(r"level \d", t)]
        part = sentences[i]
        if key == "slot_min": return int(re.search(r"level (\d+)", part)[1])
        if key in {"attack_bonus", "damage_bonus"}: return int(re.search(r"\+(\d+)", part)[1])
        if key == "extra_dice": return re.search(r"\{@damage ([^}]+)\}", part)[1]
    if key in {"attack_bonus", "damage_bonus"}: return int(re.search(r"\+(\d+) bonus", text)[1])
    if key == "upgrade_dice": return re.search(r"\{@damage ([^}]+)\}", higher)[1]
    if key in {"dice", "extra_dice"}:
        m = re.search(r"\{@(?:damage|dice) ([^}]+)\}", text)
        return norm(m[1]) if m else None
    if key == "count": return 2 if "two attacks" in text else 1 if "one attack" in text else None
    return None


def numeric_coverage_errors(spec):
    """Independent iterative leaf walk, not a second call to the scan iterator."""
    pending = [((), spec)]; expected = set()
    while pending:
        path, value = pending.pop()
        if isinstance(value, dict): pending.extend((path + (k,), v) for k, v in value.items())
        elif isinstance(value, list): pending.extend((path + (i,), v) for i, v in enumerate(value))
        elif type(value) in (int, float) or isinstance(value, str) and any(c.isdecimal() for c in value): expected.add(path)
    scanned = [path for path, _ in numeric_fields(spec)]
    errors = []
    if len(set(scanned)) != len(scanned): errors.append('numeric coverage: duplicate paths')
    if expected != set(scanned): errors.append(f'numeric coverage: missing {sorted(expected - set(scanned), key=str)!r}, extra {sorted(set(scanned) - expected, key=str)!r}')
    return errors


def expected_numeric_text(spec, path, raw):
    """Executable expressions and source references have semantic anchors."""
    if path == ('components', 'm'):
        m=raw.get('components',{}).get('m')
        return m.get('text') if isinstance(m,dict) else m
    if path[-1] == 'source_ref':
        block=spec['effects'][path[1]]['id']
        anchors={('Call Lightning','main'):'A lightning bolt',
                 ('Phantasmal Force','hazard'):'An affected target can even take damage',
                 ('Witch Bolt','main'):'A beam of crackling energy',
                 ('Witch Bolt','sustain'):'On each of your subsequent turns'}
        anchor=anchors.get((raw['name'],block))
        if anchor:
            return next((f'entries.{i}' for i,e in enumerate(raw['entries']) if anchor in text_entries(e)), '')
    if path[-1] == 'eligible_if' and raw['name'] in {'Aura of Life','Spare the Dying'}: return 'target.hp == 0'
    if path[-1] == 'if' and raw['name'] == 'Banishing Smite':
        number=re.search(r'reduces the target to (\d+)',text_entries(raw['entries']))
        return f'target.hp <= {number[1]}' if number else ''
    if path[-1] == 'returns' and raw['name'] == 'Banishment':
        n=raw['duration'][0]['duration']['amount']
        return f'not (spell.elapsed_minutes >= {n} and target.creature_type in [aberration, celestial, elemental, fey, fiend])'
    if path == ('reaction_trigger',) and raw['name'] == 'Counterspell':
        n=raw['range']['distance']['amount']
        return f'on_spell_cast_nearby({n}) and trigger.caster.visible_to(caster) and trigger.spell.has_any_component(v, s, m)'
    return None


def annotation_numbers(raw, index):
    """Even numeric prose is scanned. Evidence is clause-local, not a number pool.

    These are omission/model-boundary notes, not executable rules. Zero HP is
    the arena's knockout identity; all other values come from specific clauses.
    """
    text=text_entries(raw['entries']); higher=text_entries(raw.get('entriesHigherLevel',[]))
    def match(pattern, source=text):
        m=re.search(pattern,source)
        return re.findall(r'\d+', m[1]) if m else []
    name=raw['name']
    patterns={
        'Animate Dead':r'under your control for (\d+) hours',
        'Animate Objects':r'within (\d+) feet of you',
        'Banishing Smite':r'reduces the target to (\d+)',
        'Call Lightning':r'damage increases by \{@damage ([^}]+)',
        'Confusion':r'roll \{@dice \d*d(\d+)',
        'Find Familiar':r'Challenge Rating of (\d+)',
        'Fire Shield':r'creature within (\d+) feet',
        'Grasping Vine':r'creature within (\d+) feet',
        'Levitate':r'weighs up to (\d+) pounds',
        'Thunderous Smite':r'be pushed (\d+) feet',
        'Warding Bond':r'within (\d+) feet',
    }
    if name in patterns: return match(patterns[name])
    if name=='Enlarge/Reduce': return match(r'extra \{@damage ([^}]+)')+match(r'below (\d+)')
    if name=='Ice Storm':
        return match(r'\{@scaledamage ([^|]+)',higher)+match(r'\{@damage ([^}]+)')+match(r'\{@scaledamage [^|]+\|[^|]+\|([^}]+)',higher)
    if name=='Meld into Stone': return match(r'deals \{@damage ([^}]+)')+match(r'deals (\d+) Force')
    if name=='Revivify': return ['0']  # Arena unconscious-at-zero identity, not a death rule.
    if name=='Spiritual Weapon': return [str(raw['range']['distance']['amount'])]+match(r'move the force up to (\d+) feet')
    if name=='Summon Undead':
        from .summon_validation import referenced_stat_block
        block=referenced_stat_block(raw)
        entry=next(t for t in block['trait'] if t['name'].startswith('Incorporeal'))
        return match(r'\{@damage ([^}]+)',text_entries(entry))+match(r'every (\d+) feet',text_entries(entry))
    return []
