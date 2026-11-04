"""The few XPHB class facts the builder needs, committed so builds run without raw_data/.

The builder needs three facts that are not in data/handwritten/classes/*.yaml:
the warlock's invocation count per level, each class's skill choices, and the
subclass's always-prepared spells. They are extracted from the 5etools class
files into data/handwritten/class_facts.json. tests/test_class_facts.py checks
the committed file against the source whenever raw_data/ is present.

    python -m engine.class_facts --write
"""
import argparse
from functools import lru_cache
import json

from .loader import ROOT

PATH = ROOT / "class_facts.json"
CLASSES = ("barbarian", "bard", "cleric", "druid", "fighter", "monk", "paladin", "ranger", "rogue", "sorcerer", "warlock", "wizard")


def extract(name):
    """The builder's facts for one class, read from raw_data/class (needs the source files)."""
    from .class_source import source
    c, s, _ = source(name)
    facts = {"skills": c["startingProficiencies"]["skills"][0].get("choose", {}).get("from"),
             "prepared": s["additionalSpells"][0].get("prepared", {}) if s.get("additionalSpells") else {}}
    if name == "warlock":
        facts["invocations"] = [row[0] for row in c["classTableGroups"][0]["rows"]]
    return facts


def extract_all():
    return {name: extract(name) for name in CLASSES}


@lru_cache(None)
def _all():
    return json.loads(PATH.read_text(encoding="utf-8"))


def facts(name):
    return _all()[name]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--write", action="store_true", help="regenerate the committed file from raw_data/")
    args = parser.parse_args()
    data = extract_all()
    text = json.dumps(data, indent=1, sort_keys=True) + "\n"
    if args.write: PATH.write_text(text, encoding="utf-8", newline="\n")
    else: print(text, end="")


if __name__ == "__main__":
    main()
