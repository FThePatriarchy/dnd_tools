"""Magic items: a combat-relevant XDMG subset, and DMG-sized item kits for parties.

Each item is a plain stat change the builder applies (``choices.items``):

- ``weapon``: +N to attack and damage rolls with the character's first weapon.
- ``armor`` / ``shield``: +N AC while wearing armor / holding a Shield.
- ``ac`` and ``saves``: a bonus to AC (kept on top of Mage Armor and similar base-AC
  effects) and to every saving throw.
- ``scores``: an ability score becomes N unless it is already higher (belts, Amulet
  of Health, Gauntlets, Headband).
- ``spell_attack`` / ``spell_dc``: bonuses to spell attack rolls / spell save DC.
- ``proficiency``: +N Proficiency Bonus (Ioun Stone of Mastery).
- ``base_ac``: unarmored base AC is N + Dex (Robe of the Archmagi).
- ``magic_resistance``: advantage on saves against spells and magical effects.

Charges, spells cast from items and out-of-combat properties are not modeled.

Kits follow the 2024 DMG "Magic Items Awarded by Level" table (p. 218): a party
reaching level L has received the items of every completed level, spread evenly
within each tier. Commons are skipped (potions and trinkets). ``share`` is the
fraction of the uncommon-and-better items that are combat items this party keeps;
the DMG's "Player Wish List" advice picks which: rarest items first, handed round
the party, each PC taking the best item of that rarity on its class wish list.
The DMG notes that encounters are built without assuming magic items.
"""
import math

RARITIES = ("uncommon", "rare", "very rare", "legendary")

# Magic Items Awarded by Level (2024 DMG p. 218): (first level, last level, counts by rarity).
AWARDS = (
    (1, 4, {"uncommon": 4, "rare": 1, "very rare": 0, "legendary": 0}),
    (5, 10, {"uncommon": 17, "rare": 6, "very rare": 1, "legendary": 0}),
    (11, 16, {"uncommon": 7, "rare": 11, "very rare": 7, "legendary": 2}),
    (17, 20, {"uncommon": 0, "rare": 5, "very rare": 11, "legendary": 9}),
)
SHARES = {"half": 0.5, "full": 1.0}


def _item(rarity, attune, slot, source=None, **effects):
    return {"rarity": rarity, "attune": attune, "slot": slot, "source": source, "effects": effects}


ITEMS = {}
for n, rarity in zip((1, 2, 3), ("uncommon", "rare", "very rare")):
    ITEMS[f"+{n} Weapon"] = _item(rarity, False, "weapon", f"+{n} Weapon", weapon=n)
    ITEMS[f"+{n} Shield"] = _item(rarity, False, "shield", f"+{n} Shield (*)", shield=n)
for n, rarity in zip((1, 2, 3), ("rare", "very rare", "legendary")):
    ITEMS[f"+{n} Armor"] = _item(rarity, False, "armor", f"+{n} Armor", armor=n)
for n, rarity in zip((1, 2, 3), ("uncommon", "rare", "very rare")):
    ITEMS[f"+{n} Wand of the War Mage"] = _item(rarity, True, "wand", spell_attack=n)
    ITEMS[f"+{n} Rod of the Pact Keeper"] = _item(rarity, True, "rod", spell_attack=n, spell_dc=n)
ITEMS.update({
    "Cloak of Protection": _item("uncommon", True, "cloak", ac=1, saves=1),
    "Stone of Good Luck": _item("uncommon", True, "luckstone", saves=1),
    "Gauntlets of Ogre Power": _item("uncommon", True, "strength", scores={"str": 19}),
    "Headband of Intellect": _item("uncommon", True, "headband", scores={"int": 19}),
    "Ring of Protection": _item("rare", True, "ring", ac=1, saves=1),
    "Ioun Stone, Protection": _item("rare", True, "ioun_protection", ac=1),
    "Bracers of Defense": _item("rare", True, "bracers", unarmored_ac=2),
    "Amulet of Health": _item("rare", True, "amulet", scores={"con": 19}),
    "Belt of Hill Giant Strength": _item("rare", True, "strength", scores={"str": 21}),
    "Belt of Frost Giant Strength": _item("very rare", True, "strength", scores={"str": 23}),
    "Belt of Fire Giant Strength": _item("very rare", True, "strength", scores={"str": 25}),
    "Belt of Cloud Giant Strength": _item("legendary", True, "strength", scores={"str": 27}),
    "Belt of Storm Giant Strength": _item("legendary", True, "strength", scores={"str": 29}),
    "Staff of Power": _item("very rare", "caster", "weapon", staff=2, ac=2, saves=2, spell_attack=2),
    "Robe of the Archmagi": _item("legendary", "caster", "robe", base_ac=15, magic_resistance=True, spell_attack=2, spell_dc=2),
    "Ioun Stone, Mastery": _item("legendary", True, "ioun_mastery", proficiency=1),
})
ATTUNEMENT_SLOTS = 3
ARCANE = {"sorcerer", "warlock", "wizard"}  # "by a sorcerer, warlock, or wizard"
CASTERS = {"bard", "cleric", "druid", "paladin", "ranger", "sorcerer", "warlock", "wizard"}
STRENGTH = {"fighter", "barbarian", "paladin"}
MARTIAL = {"fighter", "barbarian", "paladin", "ranger", "rogue"}


def legal(name, class_name, armor, shield, attack_casters=()):
    """Why the item does nothing or can't be attuned for this class/equipment, or None."""
    item = ITEMS[name]; e = item["effects"]
    if item["attune"] == "caster" and class_name not in ARCANE: return "attunement by a sorcerer, warlock, or wizard"
    if "Pact Keeper" in name and class_name != "warlock": return "attunement by a warlock"
    if "spell_attack" in e and class_name not in CASTERS: return "attunement by a spellcaster"
    if "armor" in e and armor == "none": return "requires worn armor"
    if "shield" in e and not shield: return "requires a Shield"
    if ("unarmored_ac" in e or "base_ac" in e) and (armor != "none" or shield): return "requires no armor and no Shield"
    if "staff" in e and class_name not in ARCANE: return "staff for a sorcerer, warlock, or wizard"
    return None


# Wish lists, best first; a PC only takes items legal for it, and a kit is allocated
# rarest first, so the order matters within a rarity.
DEFENCE = ["Ioun Stone, Mastery", "Ring of Protection", "Cloak of Protection", "Ioun Stone, Protection", "Stone of Good Luck"]
WISH = {
    "strength": ["+3 Weapon", "Belt of Storm Giant Strength", "Belt of Cloud Giant Strength", "+3 Armor", "+3 Shield",
                 "Belt of Fire Giant Strength", "Belt of Frost Giant Strength", "+2 Weapon", "+2 Armor", "+2 Shield",
                 "Belt of Hill Giant Strength", "+1 Weapon", "+1 Armor", "+1 Shield", "Gauntlets of Ogre Power", *DEFENCE,
                 "Amulet of Health", "Bracers of Defense"],
    "martial": ["+3 Weapon", "+3 Armor", "+3 Shield", "+2 Weapon", "+2 Armor", "+2 Shield", "+1 Weapon", "+1 Armor", "+1 Shield",
                *DEFENCE, "Amulet of Health", "Bracers of Defense"],
    "arcane": ["Robe of the Archmagi", "Staff of Power", "+3 Rod of the Pact Keeper", "+3 Wand of the War Mage",
               "+2 Rod of the Pact Keeper", "+2 Wand of the War Mage", "Bracers of Defense", *DEFENCE,
               "+1 Rod of the Pact Keeper", "+1 Wand of the War Mage", "Headband of Intellect", "Amulet of Health"],
    "divine": ["+3 Armor", "+3 Shield", "+2 Armor", "+2 Shield", "+1 Armor", "+1 Shield", *DEFENCE, "Bracers of Defense",
               "+3 Wand of the War Mage", "+2 Wand of the War Mage", "+1 Wand of the War Mage", "Amulet of Health", "+1 Weapon"],
}


def wish_list(class_name):
    if class_name in STRENGTH: return WISH["strength"]
    if class_name in MARTIAL or class_name == "monk": return WISH["martial"]
    if class_name in ARCANE: return WISH["arcane"]
    return WISH["divine"]


def awarded(level, share=0.5):
    """Uncommon-or-better items a party has kept on reaching level (levels 1..level-1 completed)."""
    totals = dict.fromkeys(RARITIES, 0.0)
    for first, last, counts in AWARDS:
        done = max(0, min(last, level - 1) - first + 1)
        for r in RARITIES: totals[r] += counts[r] * done / (last - first + 1)
    return {r: math.floor(totals[r] * share + 1e-9) for r in RARITIES}


def useful(name, sheet):
    """False when the item would change nothing (an ability score already at least the item's)."""
    scores = ITEMS[name]["effects"].get("scores", {})
    return all(sheet["abilities"][a] < n for a, n in scores.items())


def allocate(members, level, share=0.5):
    """members: dicts with class, armor, shield and sheet (built without items).
    Returns one item list per member and the items left unplaced by rarity."""
    budget = awarded(level, share)
    kits = [[] for _ in members]
    left = {}
    turn = 0
    for rarity in reversed(RARITIES):
        for _ in range(budget[rarity]):
            for k in range(len(members)):
                i = (turn + k) % len(members)
                m = members[i]
                slots = {ITEMS[n]["slot"] for n in kits[i]}
                attuned = sum(bool(ITEMS[n]["attune"]) for n in kits[i])
                pick = next((n for n in wish_list(m["class"]) if ITEMS[n]["rarity"] == rarity and ITEMS[n]["slot"] not in slots
                             and not legal(n, m["class"], m["armor"], m["shield"]) and useful(n, m["sheet"])
                             and (not ITEMS[n]["attune"] or attuned < ATTUNEMENT_SLOTS)), None)
                if pick:
                    kits[i].append(pick); turn = i + 1
                    break
            else:
                left[rarity] = left.get(rarity, 0) + 1
    return kits, left


def with_items(builds, share="half"):
    """Build names or recipes -> recipes with a DMG-sized kit in choices.items (and a name label)."""
    from copy import deepcopy
    from .builder import EQUIPMENT, DEFAULT_EQUIPMENT, ROOT, build
    from .loader import read_yaml
    recipes = []
    for b in builds:
        r = deepcopy(b) if isinstance(b, dict) else {"name": b, **read_yaml(ROOT / "builds" / f"{b}.yaml")}
        r.setdefault("name", f"{r['class']}_{r['level']}")
        recipes.append(r)
    members = []
    for r in recipes:
        armor, shield, _ = EQUIPMENT[r["equipment"] or DEFAULT_EQUIPMENT[r["class"]]]
        sheet = build(r["class"], r["level"], r["subclass"], r["abilities"], r["equipment"], r["choices"])
        members.append({"class": r["class"], "armor": armor, "shield": shield, "sheet": sheet})
    level = round(sum(r["level"] for r in recipes) / len(recipes))
    kits, _ = allocate(members, level, SHARES[share])
    for r, kit in zip(recipes, kits):
        r["choices"] = {**r["choices"], "items": kit}
        r["name"] = f"{r['name']}+items_{share}"
    return recipes
