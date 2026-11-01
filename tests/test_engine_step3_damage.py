"""Seeded per-target damage versus dice parsed independently from XPHB text."""
from functools import lru_cache
from math import comb, ceil, log, sqrt
import re
from statistics import mean

import pytest

from engine.spell_validation import source_spells, text_entries
from test_engine_step3 import arena, new_spells, cast_fixture


RAW = source_spells()


def damage_cases():
    for name, s in new_spells().items():
        for block in s["effects"]:
            if not any("damage" in p for branch in ("apply", "on_hit", "on_fail") for p in block[branch]): continue
            configurations = [(0, level) for level in (1, 5, 11, 17)] if s["level"] == 0 else [(slot, 9) for slot in sorted({s["level"], max(5, s["level"])})]
            for slot, level in configurations:
                for success in ([False, True] if block["save"] else [False]):
                    yield name, block["id"], slot, level, success
                    if any(p.get("damage", {}).get("delay") for p in block["on_fail"] + block["on_hit"] + block["apply"]):
                        yield name, block["id"] + "::delay", slot, level, success


def oracle(name, block, slot, level, success, spell_mod, moments=False):
    """No engine dice/scaling functions or translation recipe imports."""
    raw = RAW[name]
    source = raw["entries"]
    if "source_ref" in block: source = source[int(block["source_ref"].split(".")[1])]
    text = text_entries(source)
    higher = text_entries(raw.get("entriesHigherLevel", []))
    expressions = []
    for match in re.finditer(r"\{@damage (\d+d\d+(?:\s*[+-]\s*\d+)?)\}", text):
        dtype = re.match(r"\s+(\w+) damage", text[match.end():])
        entry = (match[1], dtype[1].lower() if dtype else None)
        if entry not in expressions: expressions.append(entry)
    if name == "Ice Knife": expressions = expressions[:1] if block["id"] == "knife" else expressions[1:2]
    if name == "Toll the Dead": expressions = expressions[:1]
    if not expressions:
        flat = re.search(r"(?:taking|takes) (\d+) \w+ damage", text)
        assert flat, (name, block["id"])
        amount = int(flat[1]) + (5 * (slot - raw["level"]) if name == "Armor of Agathys" else 0)
        if "on_attack_hit" in block["event"]:
            # Retaliation is flat (never critical-doubled), but a trigger attack
            # still misses on natural 1 in this unconditional seeded scenario.
            expected = .95 * amount
            return (.95 * .05 * amount * amount, expected) if moments else expected
        return (0, 0) if moments else amount // 2 if success else amount
    if name == "Bigby's Hand": expressions = expressions[:1] if block["id"] == "fist" else expressions[1:2]
    if name == "Divine Smite": expressions = expressions[:1]
    if name == "Lightning Arrow": expressions = expressions[:1] if block["id"] == "main" else expressions[1:2]
    if name == "Fire Shield": expressions = expressions[:1]
    # The growing bead and Weird's repeat-save damage are later clauses, not the initial blast.
    if name in {"Delayed Blast Fireball", "Weird"}: expressions = expressions[:1]
    if name == "Conjure Elemental": expressions = expressions[:1] if block["id"] == "catch" else expressions[1:]
    if name == "Hunger of Hadar":
        source_type = "cold" if "start_of_turn" in block["event"] else "acid"
        expressions = [e for e in expressions if e[1] == source_type]
    if any(p.get("damage", {}).get("delay") for p in block["on_fail"] + block["on_hit"] + block["apply"]):
        expressions = expressions[1:2] if block.get("_phase") == "delay" else expressions[:1]
        if block.get("_phase") == "delay" and success: return (0, 0) if moments else 0
    dice = []
    for expression, dtype in expressions:
        m = re.fullmatch(r"(\d+)d(\d+)(?:\s*([+-])\s*(\d+))?", expression)
        n, sides = int(m[1]), int(m[2])
        bonus = int(m[4] or 0) * (-1 if m[3] == "-" else 1)
        if raw["level"] == 0:
            thresholds = sorted(set(map(int, re.findall(r"(?:levels?\s+|,\s*|and\s+)(\d+)\s*\(", higher))))
            n += sum(level >= threshold for threshold in thresholds)
        elif slot > raw["level"]:
            increment = re.search(r"\{@scaledamage [^|]+\|[^|]+\|(\d+)d(\d+)\}", higher)
            qualifier = re.search(r"The (\w+) damage increases", higher)
            scales = not qualifier or qualifier[1].lower() not in raw.get("damageInflict", []) or qualifier[1].lower() == dtype
            if qualifier and qualifier[1] == "initial" and "on_cast" not in block["event"]: scales = False
            if block.get("_phase") == "delay" and "initial damage increases" in higher: scales = False
            if name == "Hunger of Hadar": scales = dtype == "cold"
            if increment and scales: n += int(increment[1]) * (slot - raw["level"])
        if re.search(r"damage equal to .*plus your spellcasting ability modifier", text) or name == "Bigby's Hand" and block["id"] == "crush": bonus += spell_mod
        dice.append((n, sides, bonus))
    if name == "Sorcerous Burst":
        if moments: return None
        @lru_cache(None)
        def added(pending, remaining):
            if pending == 0 or remaining == 0: return 0
            return 4.5 + added(pending, remaining - 1) / 8 + 7 * added(pending - 1, remaining - 1) / 8
        def burst(n):
            return 4.5 * n + sum(comb(n, k) * (1/8)**k * (7/8)**(n-k) * added(k, max(0, spell_mod)) for k in range(n + 1))
        return .90 * burst(dice[0][0]) + .05 * burst(2 * dice[0][0])
    normal = sum(n * (sides + 1) / 2 + bonus for n, sides, bonus in dice)
    variance = sum(n * (sides * sides - 1) / 12 for n, sides, _ in dice)
    high = sum(n * sides + bonus for n, sides, bonus in dice)
    low = sum(n + bonus for n, _, bonus in dice)
    if name == "Fire Shield":
        return (variance + .05 * normal * normal, high) if moments else .95 * normal
    if name == "Melf's Acid Arrow" and block.get("_phase") == "delay":
        return (variance + .05 * normal * normal, high) if moments else .95 * normal
    if (block["attack"] or "on_attack_hit" in block["event"]) and block.get("_phase") != "delay":
        critical = sum(n * (sides + 1) + bonus for n, sides, bonus in dice)
        expected = .90 * normal + .05 * critical
        if name == "Melf's Acid Arrow": expected += .05 * (normal / 2 - .25)
        second = .90 * (variance + normal * normal) + .05 * (2 * variance + critical * critical)
        critical_high = sum(2 * n * sides + bonus for n, sides, bonus in dice)
        return (second - expected * expected, max(expected, critical_high - expected)) if moments else expected
    if success:
        recurring = re.split(r"For the duration, the target makes", text)
        if "end_of_turn(target)" == block["event"] and len(recurring) == 2 and "On a successful save, the spell ends" in recurring[1]:
            return (0, 0) if moments else 0
        # Each even-sided damage-type component has equiprobable odd/even sums.
        if not re.search(r"half (?:as much|the initial)", text): return (0, 0) if moments else 0
        expected = sum((n * (sides + 1) / 2 + bonus) / 2 - .25 for n, sides, bonus in dice)
        # A conservative variance bound for per-type floor rounding.
        rounded_variance = (sqrt(variance) / 2 + len(dice) / 2) ** 2
        return (rounded_variance, max(expected - low // 2, high // 2 - expected)) if moments else expected
    return (variance, max(normal - low, high - normal)) if moments else normal


def trial_count(expected, moments):
    """Bernstein bound <= .001 when reducing N; never reduce tolerances.

    Retain the historical 4000 trials if the bound asks for more or the source
    distribution is the separately checked capped exploding-die process.
    """
    if moments is None: return 4000
    variance, deviation = moments
    if variance == deviation == 0: return 64
    tolerance = max(.18, expected * .025)
    n = ceil((2 * variance + 2 * deviation * tolerance / 3) * log(2000) / tolerance ** 2)
    return min(4000, max(64, n))


@pytest.mark.parametrize("name,block_id,slot,level,success", list(damage_cases()))
def test_step3_damage_mean_from_source(name, block_id, slot, level, success):
    spec = new_spells()[name]
    real_id, _, phase = block_id.partition("::")
    declaration = {**next(b for b in spec["effects"] if b["id"] == real_id), "_phase": phase}
    expected = oracle(name, declaration, slot, level, success, 4)
    samples = []
    probe, caster, _ = arena(name, level=level, enemies=1)
    prepared = probe.scale(caster, spec, slot)
    count = trial_count(expected, oracle(name, declaration, slot, level, success, 4, moments=True))
    for seed in range(count):
        b, c, ds = arena(name, seed=seed, level=level, enemies=1)
        # Scaling is deterministic and independently checked above/in the source
        # gate. Share this read-only spec; retain every seeded resolution trial.
        b.scale = lambda *args: prepared
        b.area = lambda shape, size, count: min(1, count)
        if success and "on_cast" in declaration["event"]:
            for d in ds: d.save_bonuses = dict.fromkeys(d.save_bonuses, 100)
        # Full casting/action economy is exercised by the execution arena. Here
        # isolate one block to avoid unrelated same-type phases contaminating it.
        from copy import deepcopy
        from engine.state import SpellInstance, Binding, Effect
        actual = deepcopy(next(x for x in prepared["effects"] if x["id"] == real_id))
        inst = SpellInstance(1, {**prepared, "effects": [actual]}, c, slot, b.turn_index, b.time_rounds)
        inst.choices = {ch["id"]: ch["options"][0] for ch in prepared["choices"]}
        inst.bindings = {x["id"]: Binding([ds[0]]) for x in prepared["effects"]}
        inst.area_members = {real_id: [ds[0]]}
        if name == "Bigby's Hand":
            inst.choices["mode"] = real_id
            if real_id == "crush": ds[0].effects.append(Effect("apply_condition", {"condition":"grappled", "caster_id":c.id}, 1, "grasp"))
        b.instances[1] = inst
        if name == "Witch Bolt" and real_id == "sustain": inst.cast_turn -= 1
        if name == "Crusader's Mantle": c.effects.append(Effect("status", {"id":"crusaders_mantle", "data":{}, "caster_id":c.id}, 1, "aura"))
        if name == "Lightning Arrow" and real_id == "splash": inst.bindings["main"] = Binding([c])
        if success:
            ds[0].save_bonuses = dict.fromkeys(ds[0].save_bonuses, 100)
        if name == "Ensnaring Strike" and real_id == "vines":
            ds[0].effects.append(Effect("apply_condition", {"condition": "restrained", "caster_id": c.id}, inst.id, "main"))
        if name == "Conjure Elemental" and real_id == "hold":
            ds[0].effects.append(Effect("apply_condition", {"condition": "restrained", "caster_id": c.id}, inst.id, "catch"))
        if "on_attack_hit(any, caster)" in actual["event"]:
            b.weapon_attack(ds[0], c, {"name": "Probe", "kind": "melee", "to_hit": 100, "effects": []})
        elif "on_attack_hit" in actual["event"]:
            b.weapon_attack(c, ds[0], {"name": "Probe", "kind": "melee", "to_hit": 100, "effects": []})
        else:
            b.resolve_block(inst, actual, "on_cast", {"who": ds[0], **({"attacker":ds[0]} if name == "Hellish Rebuke" else {})}, None)
        if phase == "delay":
            b.log.clear()
            # Advance the exact boundary, without firing the initial block again.
            ds[0].turns_taken += 1
            b.expire("end_of_turn", ds[0])
        branch = declaration["on_hit"] if declaration["attack"] else declaration["on_fail"] if declaration["save"] else declaration["apply"]
        types = {p["damage"]["type"] for p in branch if "damage" in p}
        types = {inst.choices[t[1:]] if t.startswith("$") else t for t in types}
        samples.append(sum(e["amount"] for e in b.log if e["event"] == "damage" and e["target"] == ds[0].id and e["type"] in types))
    assert mean(samples) == pytest.approx(expected, abs=max(.18, expected * .025)), (name, block_id, slot, level, success)


@pytest.mark.parametrize("name,form,slot", [
    (name, form, slot)
    for name, forms, base in [("Summon Beast", ["air", "land", "water"], 2),
                              ("Summon Undead", ["ghostly", "putrid", "skeletal"], 3),
                              ("Summon Elemental", ["air", "earth", "fire", "water"], 4)]
    for form in forms for slot in (base, 5)
])
def test_step3_summon_damage_from_referenced_stat_block(name, form, slot):
    from engine.summon_validation import referenced_stat_block
    from engine.summoning import take_summoned_turns
    raw = referenced_stat_block(RAW[name])
    declaration = next(a for a in raw["action"] if a["name"] != "Multiattack"
        and ("Only" not in a["name"] or form in a["name"].lower()))
    attack = " ".join(declaration["entries"])
    m = re.search(r"\{@damage (\d+)d(\d+) \+ (\d+) \+ summonSpellLevel\}", attack)
    assert m
    n, sides, flat = map(int, m.groups())
    normal = n * (sides + 1) / 2 + flat + slot
    critical = n * (sides + 1) + flat + slot
    assert "half" in raw["action"][0]["entries"][0] and "round down" in raw["action"][0]["entries"][0]
    expected = (slot // 2) * (.90 * normal + .05 * critical)
    samples = []
    probe, caster, _ = arena(name, enemies=1)
    prepared = probe.scale(caster, probe.spells[name], slot)
    for natural, high in [(n, high) for n in range(1, 21) for high in (False, True)]:
        b, c, (d,) = arena(name, seed=natural, enemies=1)
        b.rng = BalancedRolls(natural, high)
        b.scale = lambda *args: prepared
        b.cast(c, name, slot=slot, choices={"form": form})
        take_summoned_turns(b, c)
        samples.append(d.max_hp - d.hp)
    assert mean(samples) == pytest.approx(expected, abs=max(.18, expected * .025))


class BalancedRolls:
    """Exact attack strata and paired dice extrema; linear means are exact.

    Unlike the seeded direct-damage trials, this checks summon plumbing, not
    RNG quality. Every d20 result has equal weight; critical dice really roll.
    """
    def __init__(self, natural, high): self.natural, self.high = natural, high
    def randint(self, low, high): return self.natural if high == 20 else high if self.high else low
    def choice(self, values): return values[0]
    def random(self): return .5
