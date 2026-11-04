"""More XMM monsters for DMs: the ones the importer reads fully, plus reviewed on-hit riders.

    python -m engine.monster_more      # writes any missing monster files

CLEAN monsters import with no manual work: every action is a weapon attack or
a save action the importer parses, with no traits, reactions, spellcasting or
on-hit riders. RIDERS lists monsters whose weapon hits add a condition the
engine already models (Prone, Grappled, Poisoned, Frightened, Disadvantage);
each is a reviewed decision below. Riders that need a grid ("moved 20+ feet
straight toward it immediately before the hit") are left out and noted, as
the dragons' Pounce is. Monsters with bespoke rules (Cockatrice petrification,
Death Dog disease, Stirge attachment, Rug of Smothering) are not in this batch.

Existing files are never overwritten. tests/test_monster_more.py checks every
sheet against the source with the importer's drift check.
"""
from copy import deepcopy

import yaml

from .loader import ROOT
from .monster_import import import_monsters, slug, source_monsters
from .sheets import validate_sheet
from .spell_catalog import area, condition

CLEAN = ["Aarakocra Skirmisher", "Animated Armor", "Ape", "Awakened Tree", "Axe Beak", "Black Bear", "Camel", "Draft Horse",
         "Eagle", "Giant Badger", "Giant Bat", "Giant Eagle", "Giant Venomous Snake", "Giant Weasel", "Goat", "Grimlock",
         "Hook Horror", "Jackal", "Larva", "Manes", "Myconid Spore Servant", "Needle Blight", "Ogrillon Ogre", "Pegasus",
         "Polar Bear", "Pony", "Riding Horse", "Scorpion", "Venomous Snake", "Violet Fungus", "Violet Fungus Necrohulk",
         "Brass Dragon Wyrmling", "Copper Dragon Wyrmling", "Silver Dragon Wyrmling", "Blue Dragon Wyrmling", "Red Dragon Wyrmling",
         "Dretch", "Harpy", "Nothic", "Constrictor Snake"]

CHARGE = "needs a grid: the rider applies only after moving 20+ feet straight toward the target, which is not simulated"
# name -> [(attack, [effects added on hit], note or None)]
RIDERS = {
    "Ettin": [("Battleaxe", [{"apply_condition": {"condition": "prone", "max_size": "L"}}], None),
              ("Morningstar", [{"disadvantage": {"on": "attack_rolls", "scope": "all", "against": None, "uses": 1},
                                "until": "end_of_turn(target.next_turn)"}], None)],
    "Mastiff": [("Bite", [{"apply_condition": {"condition": "prone", "max_size": "M"}}], None)],
    "Giant Axe Beak": [("Talons", [{"apply_condition": {"condition": "prone", "max_size": "L"}}], None)],
    "Ankylosaurus": [("Tail", [{"apply_condition": {"condition": "prone", "max_size": "H"}}], None)],
    "Grick": [("Tentacles", [{"apply_condition": {"condition": "grappled", "escape_dc": 12, "max_size": "M", "linked": True}}], None)],
    "Grick Ancient": [("Slam", [{"apply_condition": {"condition": "prone", "max_size": "L"}}], None),
                      ("Tentacles", [{"apply_condition": {"condition": "grappled", "escape_dc": 14, "max_size": "L", "linked": True}}], None)],
    "Giant Scorpion": [("Claw", [{"apply_condition": {"condition": "grappled", "escape_dc": 13, "max_size": "L", "linked": True, "capacity": 2}}], None)],
    "Griffon": [("Rend", [{"apply_condition": {"condition": "grappled", "escape_dc": 14, "max_size": "M", "linked": True}}], None)],
    "Otyugh": [("Tentacle", [{"apply_condition": {"condition": "grappled", "escape_dc": 13, "max_size": "M", "linked": True, "capacity": 2}}], None),
               ("Bite", [{"apply_condition": {"condition": "poisoned"}}],
                "Bite: the Poisoned condition lasts the fight; its Hit Point maximum loss after a Long Rest is not modeled.")],
    "Giant Centipede": [("Bite", [{"apply_condition": {"condition": "poisoned"}, "until": "start_of_turn(caster.next_turn)"}], None)],
    "Scarecrow": [("Fearsome Claw", [{"apply_condition": {"condition": "frightened"}, "until": "end_of_turn(caster.next_turn)"}], None)],
    "Allosaurus": [("Claws", [], "Claws: Prone and the extra Bite " + CHARGE + ".")],
    "Rhinoceros": [("Gore", [], "Gore: the extra damage and Prone " + CHARGE + ".")],
    "Gorgon": [("Gore", [], "Gore: Prone " + CHARGE + ".")],
    "Mammoth": [("Gore", [], "Gore: Prone " + CHARGE + ".")],
    "Elephant": [("Gore", [], "Gore: Prone " + CHARGE + ".")],
    "Triceratops": [("Gore", [], "Gore: the extra damage and Prone " + CHARGE + ".")],
    "Giant Goat": [("Ram", [], "Ram: the extra damage and Prone " + CHARGE + ".")],
    "Elk": [("Ram", [], "Ram: the extra damage and Prone " + CHARGE + ".")],
    "Giant Elk": [("Ram", [], "Ram: the extra damage and Prone " + CHARGE + ".")],
    "Minotaur Skeleton": [("Gore", [], "Gore: the extra damage and Prone " + CHARGE + ".")],
    "Warhorse": [("Hooves", [], "Hooves: the extra damage and Prone " + CHARGE + ".")],
    "Warhorse Skeleton": [("Hooves", [], "Hooves: Prone " + CHARGE + ".")],
}


def _add(*effects, until=None):
    """Effects added to a save action's failed save (the importer keeps only its damage)."""
    def fix(block):
        for e in effects:
            e = deepcopy(e)
            if until: e["until"] = until
            block["on_fail"].append(e)
    return fix


def _only_if(expression):
    """The action can only target a creature that meets the expression (e.g. Trample needs a Prone target)."""
    def fix(block):
        block["target"]["eligible_if"] = expression
        block["if"] = expression
    return fix


def _area(shape, size):
    def fix(block): block["target"] = area(shape, size)
    return fix


NOT_MODELED = "not modeled (the action has no simulated effect, so the AI never uses it)"
# name -> {action: ([fixes applied to its block], note or None)}. The importer reads each save action's
# damage and target; these add the conditions its failed save gives, from the source text.
ACTIONS = {
    "Violet Fungus Necrohulk": {
        "Spore Bomb": ([_area("sphere", 20), _add(condition("poisoned"), until="start_of_turn(caster.next_turn)")],
                       "Spore Bomb: being unable to regain Hit Points while Poisoned is not modeled."),
        "Absorb Body": ([], "Absorb Body (grafting a creature) is " + NOT_MODELED + ".")},
    "Brass Dragon Wyrmling": {"Sleep Breath": ([_add(condition("incapacitated"), until="end_of_turn(target.next_turn)")],
                                               "Sleep Breath: the second save's Unconscious condition is not modeled.")},
    "Silver Dragon Wyrmling": {"Paralyzing Breath": ([_add(condition("incapacitated"), until="end_of_turn(target.next_turn)")],
                                                     "Paralyzing Breath: the second save's Paralyzed condition is not modeled.")},
    "Copper Dragon Wyrmling": {"Slowing Breath": ([], "Slowing Breath (no Reactions, half Speed, action or Bonus Action) is " + NOT_MODELED + ".")},
    "Dretch": {"Fetid Cloud": ([_add(condition("poisoned"), until="end_of_turn(target.next_turn)")],
                               "Fetid Cloud: the action-or-Bonus-Action limit and losing Reactions while Poisoned are not modeled.")},
    "Harpy": {"Luring Song": ([], "Luring Song (Charmed and pulled toward the harpy) is " + NOT_MODELED + ".")},
    "Nothic": {"Weird Insight": ([], None)},
    "Constrictor Snake": {"Constrict": ([_add(condition("grappled", escape_dc=12, max_size="M", linked=True))], None)},
    "Otyugh": {"Tentacle Slam": ([_only_if("target.has_condition_from(grappled, caster)"),
                                  _add(condition("stunned"), until="start_of_turn(caster.next_turn)")], None)},
    "Scarecrow": {"Terrifying Glare": ([_add(condition("frightened"), condition("paralyzed"), until="end_of_turn(caster.next_turn)")],
                                       "Terrifying Glare: Paralyzed is applied with Frightened and for the same time.")},
    "Gorgon": {"Petrifying Breath": ([_add(condition("restrained"), until="end_of_turn(target.next_turn)")],
                                     "Petrifying Breath: the second save's Petrified condition is not modeled, so the breath is weaker than printed."),
               "Trample": ([_only_if("target.has_condition(prone)")], None)},
    "Mammoth": {"Trample": ([_only_if("target.has_condition(prone)")], None)},
    "Elephant": {"Trample": ([_only_if("target.has_condition(prone)")], None)},
}
NAMES = CLEAN + list(RIDERS)


def review(name, sheet, raw):
    sheet["size"] = raw["size"][-1]
    notes = [n for n in sheet.get("unsupported", []) if n.startswith("Conditional")]
    for attack, effects, note in RIDERS.get(name, []):
        target = next(a for a in sheet["attacks"] if a["name"] == attack)
        target["effects"] += deepcopy(effects)
        if note: notes.append(note)
    for action, (fixes, note) in ACTIONS.get(name, {}).items():
        block = next(a for a in sheet["actions"] if a["name"] == action)["effects"][0]
        for fix in fixes: fix(block)
        if note: notes.append(note)
    for a in sheet["actions"]:  # every save action is reviewed: it does something, or it is listed above
        if not any(b["on_fail"] or b["on_success"] for b in a["effects"]) and a["name"] not in ACTIONS.get(name, {}):
            raise ValueError(f"{name}: {a['name']} has no effect and no review decision")
    if any(n.startswith("Manual") for n in sheet.get("unsupported", [])):
        raise ValueError(f"{name}: unreviewed manual entries {sheet['unsupported']}")
    sheet["unsupported"] = notes
    return sheet


def sheets():
    raw = source_monsters()
    bases = import_monsters(names=NAMES)
    return {name: review(name, deepcopy(bases[name]), raw[name]) for name in NAMES}


def main():
    written = 0
    for name, sheet in sheets().items():
        validate_sheet(sheet, name)
        path = ROOT / "monsters" / (slug(name) + ".yaml")
        if path.exists(): continue
        path.write_text(yaml.safe_dump(sheet, sort_keys=False, allow_unicode=True, width=110), encoding="utf-8")
        written += 1
    print("New monsters:", written)


if __name__ == "__main__":
    main()
