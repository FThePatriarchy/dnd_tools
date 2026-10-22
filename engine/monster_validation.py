"""Independent XMM tag coverage and attack-routine damage sanity checks."""
import re
from .dice import mean
from .loader import load_spells
from .monster_import import parse_monster, entries_text, COUNTS

DAMAGE_TAGS = dict(zip("ABCFILNOPRSTY", ("acid", "bludgeoning", "cold", "fire", "poison", "lightning", "necrotic", "force", "piercing", "radiant", "slashing", "thunder", "psychic")))
SAVE_NAMES = dict(zip(("strength", "dexterity", "constitution", "intelligence", "wisdom", "charisma"), ("str", "dex", "con", "int", "wis", "cha")))


def executable_tags(value):
    damage, conditions, saves = set(), set(), set()
    def walk(obj):
        if isinstance(obj, list):
            for item in obj: walk(item)
        elif isinstance(obj, dict):
            if "damage" in obj: damage.add(obj["damage"]["type"])
            if "apply_condition" in obj:
                c = obj["apply_condition"]
                conditions.add(c["condition"])
                if "upgrade_on_failure" in c: conditions.add(c["upgrade_on_failure"])
            if obj.get("save"): saves.add(obj["save"]["ability"])
            for item in obj.values(): walk(item)
    walk(value)
    for choice in value.get("choices", []):
        if "$" + choice["id"] in damage:
            damage.remove("$" + choice["id"])
            damage.update(choice["options"])
    return damage, conditions, saves


def source_tag_gaps(raw, sheet, spells=None):
    spells = spells if spells is not None else load_spells()
    d, c, s = executable_tags({k: sheet.get(k, []) for k in ("attacks", "actions", "traits", "legendary")})
    for name in sheet.get("spells", []):
        sd, sc, ss = executable_tags(spells[name]); d.update(sd); c.update(sc); s.update(ss)
    notes = " ".join(sheet.get("unsupported", [])).lower()
    missing = []
    for field, mapped, present in (("damageTags", DAMAGE_TAGS, d), ("conditionInflict", None, c), ("savingThrowForced", SAVE_NAMES, s)):
        for suffix in ("", "Spell", "Legendary"):
            for tag in raw.get(field + suffix, []):
                value = mapped[tag] if mapped else tag
                full = next((k for k, v in SAVE_NAMES.items() if v == value), value)
                if value not in present and full not in notes and not re.search(r"\b" + value + r"\b", notes):
                    missing.append(f"{field + suffix}: {tag} ({value})")
    return missing


def attack_value(attack, ac=16):
    # Neutral circumstances: no charge, advantage rider, criticals or defenses.
    return sum(mean(p["damage"]["dice"]) + p["damage"].get("bonus", 0) for p in attack["effects"] if "damage" in p and "if" not in p) * min(.95, max(.05, (21 + attack["to_hit"] - ac) / 20))


def source_attack_dpr(raw, ac=16):
    attacks = {a["name"]: a for a in parse_monster(raw)["attacks"]}
    multi = next((entries_text(a["entries"]) for a in raw.get("action", []) if a["name"] == "Multiattack"), "")
    if not multi:
        return max((attack_value(a, ac) for a in attacks.values() if "recharge" not in a), default=0)
    alternatives = re.split(r",? or it makes ", multi)
    values = []
    for branch in alternatives:
        fixed = []
        for name in attacks:
            for match in re.finditer(r"\b(one|two|three|four|\d+) " + re.escape(name) + r" attacks?\b", branch):
                count = COUNTS.get(match[1], int(match[1]) if match[1].isdigit() else 0)
                fixed.extend([name] * count)
        if fixed: values.append(sum(attack_value(attacks[n], ac) for n in fixed)); continue
        count = re.search(r"\b(one|two|three|four|\d+) ", branch)
        mentioned = [a for name, a in attacks.items() if name in branch]
        if count and mentioned:
            n = COUNTS.get(count[1], int(count[1]) if count[1].isdigit() else 0)
            values.append(n * max(attack_value(a, ac) for a in mentioned))
    if not values: raise ValueError(f"unreviewed source routine: {raw['name']}/{multi}")
    return max(values)


def sheet_attack_dpr(sheet, ac=16):
    attacks = {a["name"]: a for a in sheet.get("attacks", [])}
    routines = sheet.get("routines") or [sheet.get("multiattack") or [next(iter(attacks))] * sheet.get("extra_attack", 1)] if attacks else []
    return max((sum(attack_value(attacks[n], ac) for n in r if n in attacks) for r in routines), default=0)
