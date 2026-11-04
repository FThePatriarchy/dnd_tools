"""The builder runs from committed files; the XPHB cross-checks run here."""
import json

import pytest

from engine import class_facts
from engine.class_facts import CLASSES, extract_all, facts
from engine.classes import load_class
from engine.source_files import RAW


def test_committed_class_facts_match_the_source():
    committed = json.loads(class_facts.PATH.read_text(encoding="utf-8"))
    assert committed == json.loads(json.dumps(extract_all()))


@pytest.mark.parametrize("name", CLASSES)
def test_every_class_passes_the_source_check(name):
    load_class(name, source_check=True)


def test_builder_facts_cover_what_the_builder_reads():
    assert len(facts("warlock")["invocations"]) == 20
    for name in ("cleric", "paladin", "warlock", "druid", "sorcerer"):
        assert facts(name)["prepared"], name
    assert facts("fighter")["skills"] and facts("bard")["skills"] is None


def test_builds_and_fights_need_no_raw_data(monkeypatch, tmp_path):
    """A fresh clone has no raw_data/: building a party and running a fight must not read it."""
    import builtins, io, pathlib
    from engine.builder import build, load_character
    from engine import Combat, Combatant
    from engine.loader import ROOT, load_sheet, load_spells
    real_open, real_read_text, real_read_bytes = builtins.open, pathlib.Path.read_text, pathlib.Path.read_bytes
    def guard(path):
        if str(RAW) in str(pathlib.Path(path).resolve()): raise AssertionError(f"read raw_data at runtime: {path}")
    monkeypatch.setattr(builtins, "open", lambda f, *a, **k: (guard(f), real_open(f, *a, **k))[1])
    monkeypatch.setattr(pathlib.Path, "read_text", lambda self, *a, **k: (guard(self), real_read_text(self, *a, **k))[1])
    monkeypatch.setattr(pathlib.Path, "read_bytes", lambda self, *a, **k: (guard(self), real_read_bytes(self, *a, **k))[1])
    from engine import builder, class_source
    builder._class.cache_clear(); class_source.source.cache_clear()
    for cls in CLASSES:
        build(cls, 10)
    party = [Combatant.from_sheet(load_character(n), f"p{i}", "party") for i, n in enumerate(("warlock_5", "cleric_5", "druid_5", "sorcerer_5"))]
    combat = Combat(party + [Combatant.from_sheet(load_sheet(ROOT / "monsters" / "ogre.yaml"), "e0", "enemy")], load_spells(), seed=1)
    combat.run(20)
