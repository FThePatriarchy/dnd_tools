"""Magic items: source fields, builder effects, engine hooks and DMG-sized kits."""
import json

import pytest

from engine import Combat, Combatant
from engine.builder import build
from engine.items import AWARDS, ITEMS, allocate, awarded, with_items
from engine.loader import ROOT, ValidationError, load_spells
from engine.source_files import archive_member


@pytest.fixture(scope="module")
def source():
    items = {i["name"]: i for i in json.loads(archive_member("data/items.json"))["item"] if i.get("source") == "XDMG"}
    for v in json.loads(archive_member("data/magicvariants.json"))["magicvariant"]:
        if v.get("inherits", {}).get("source") == "XDMG": items[v["name"]] = v["inherits"]
    book = json.loads(archive_member("data/book/book-xdmg.json"))
    return items, book


def bonus(text): return int(text) if text else 0


@pytest.mark.parametrize("name", sorted(ITEMS))
def test_every_item_matches_the_xdmg(source, name):
    items, _ = source
    item = ITEMS[name]; e = item["effects"]
    src = items[item["source"] or name]
    assert src["rarity"] == item["rarity"]
    assert bool(src.get("reqAttune")) == bool(item["attune"])
    if item["attune"] == "caster": assert src["reqAttune"] == "by a sorcerer, warlock, or wizard"
    assert bonus(src.get("bonusWeapon")) == e.get("weapon", 0) + e.get("staff", 0)
    assert bonus(src.get("bonusAc")) == e.get("armor", 0) + e.get("shield", 0) + e.get("ac", 0) + e.get("unarmored_ac", 0)
    assert bonus(src.get("bonusSavingThrow")) == e.get("saves", 0)
    assert bonus(src.get("bonusSpellAttack")) == e.get("spell_attack", 0)
    assert bonus(src.get("bonusSpellSaveDc")) == e.get("spell_dc", 0)
    assert src.get("ability", {}).get("static", {}) == e.get("scores", {})
    text = json.dumps(src.get("entries", []))
    if "proficiency" in e: assert "Proficiency Bonus} increases by 1" in text
    if "base_ac" in e: assert "base {@variantrule Armor Class|XPHB} is 15 plus your Dexterity modifier" in text
    if e.get("magic_resistance"): assert "Advantage|XPHB} on saving throws against spells and other magical effects" in text
    if "unarmored_ac" in e: assert "no armor and using no {@item Shield|XPHB}" in text


def test_award_table_matches_the_dmg(source):
    _, book = source
    s = json.dumps(book)
    i = s.find('"caption": "Magic Items Awarded by Level"')
    rows = json.loads(s[s.find('"rows": ', i) + 8: s.find("]]", i) + 2])
    for (first, last, counts), row in zip(AWARDS, rows):
        assert row[0].startswith(f"{first}–{last}")
        assert [str(counts[r]) for r in ("uncommon", "rare", "very rare", "legendary")] == row[2:6]


def test_awarded_counts_completed_levels():
    assert awarded(1, 1.0) == dict.fromkeys(("uncommon", "rare", "very rare", "legendary"), 0)
    assert awarded(5, 1.0) == {"uncommon": 4, "rare": 1, "very rare": 0, "legendary": 0}
    assert awarded(11, 1.0) == {"uncommon": 21, "rare": 7, "very rare": 1, "legendary": 0}
    assert awarded(11, 0.5) == {"uncommon": 10, "rare": 3, "very rare": 0, "legendary": 0}


def test_kits_respect_attunement_slots_and_legality():
    for level in (5, 10, 15, 20):
        for share in ("half", "full"):
            for r in with_items([f"{c}_{level}" for c in ("fighter", "cleric", "rogue", "wizard")], share):
                items = r["choices"]["items"]
                assert sum(bool(ITEMS[n]["attune"]) for n in items) <= 3
                sheet = build(r["class"], r["level"], r["subclass"], r["abilities"], r["equipment"], r["choices"])
                assert sheet.get("items", []) == items


def test_builder_applies_item_effects():
    plain = build("fighter", 20)
    kit = build("fighter", 20, choices={**load_choices("fighter_20"), "items": ["+3 Weapon", "+2 Armor", "Belt of Storm Giant Strength", "Ring of Protection", "Ioun Stone, Mastery"]})
    assert kit["abilities"]["str"] == 29 and kit["proficiency_bonus"] == plain["proficiency_bonus"] + 1
    assert kit["attacks"][0]["to_hit"] == plain["attacks"][0]["to_hit"] + 4 + 3 + 1 and kit["attacks"][0]["magical"]
    assert kit["attacks"][0]["effects"][0]["damage"]["bonus"] == plain["attacks"][0]["effects"][0]["damage"]["bonus"] + 4 + 3
    assert kit["ac"] == plain["ac"] + 2 and kit["features"]["item_ac_bonus"] == 1 and kit["features"]["item_save_bonus"] == 1
    robe = build("wizard", 20, choices={**load_choices("wizard_20"), "items": ["Robe of the Archmagi", "Staff of Power"]})
    base = build("wizard", 20)
    assert robe["ac"] == 15 + (robe["abilities"]["dex"] - 10) // 2 and robe["features"]["magic_resistance"]
    assert robe["spell_dc"] == base["spell_dc"] + 2 and robe["spell_attack_bonus"] == base["spell_attack_bonus"] + 4


def load_choices(name):
    from engine.loader import read_yaml
    return read_yaml(ROOT / "builds" / f"{name}.yaml")["choices"]


@pytest.mark.parametrize("items, message", [
    (["Robe of the Archmagi"], "sorcerer, warlock, or wizard"),
    (["+1 Shield"], "requires a Shield"),
    (["Cloak of Protection", "Ring of Protection", "Stone of Good Luck", "Ioun Stone, Protection"], "attuned"),
    (["+1 Weapon", "+2 Weapon"], "one slot"),
])
def test_builder_rejects_illegal_kits(items, message):
    with pytest.raises(ValidationError, match=message):
        build("fighter", 10, choices={**load_choices("fighter_10"), "items": items})


def test_engine_adds_item_ac_on_top_of_mage_armor_and_item_saves():
    c = Combatant("c", team="party", max_hp=50, ac=12, features={"item_ac_bonus": 2, "item_save_bonus": 1},
                  save_proficiencies=["int"], proficiency_bonus=4)
    b = Combat([c, Combatant("e", team="enemy", max_hp=10)], load_spells(), seed=1)
    assert b.armor_class(c) == 14
    assert c.save_bonus("int") == c.mod("int") + 4 + 1 and c.save_bonus("str") == c.mod("str") + 1


def test_allocation_places_rarest_first_and_reports_leftovers():
    members = [{"class": "wizard", "armor": "none", "shield": False, "sheet": build("wizard", 20)}]
    kits, left = allocate(members, 20, 1.0)
    assert kits[0][0] == "Robe of the Archmagi" and len(kits[0]) <= 3 and sum(left.values()) > 0
