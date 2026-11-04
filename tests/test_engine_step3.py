"""Step 3 source gate, mutation proof and executable spell regressions."""
from copy import deepcopy
import hashlib
from pathlib import Path
from statistics import mean
from functools import lru_cache

import pytest

from engine import Combat, Combatant, load_spells
from engine.loader import ROOT, Validator, read_yaml, scaled_spell
from engine.policy import Policy
from engine.spell_validation import source_spells, source_errors, mutants, numeric_fields


# SHA-256 of each file with line endings normalized to LF, so the check holds on any OS checkout.
GOLDEN = {'banishment.yaml': 'a4150e71fad39ca450b62097aa31dbed3657f600aff0d0280d3f6e8aee684676', 'bless.yaml': '149916737f9482ba21acee321a15fd1895754e598a44949bde289cb7641b4e9c', 'counterspell.yaml': '8c86aa56347a3605069860ba5652362169a6f2f4965fc29a8f77c9876627de47', 'cure_wounds.yaml': '994fb6e0f876d6c0258a2b2e935c756efeafdf962d673a94f56ef22573af66f6', 'eldritch_blast.yaml': '6772c4a4e98885681a3f33f2ff4451eb263b56621923801ccbf8a70148e8195a', 'fireball.yaml': 'ee298be5006a264f2fa3ec3156c5e8b365ce0699acc80368672322457a4474f5', 'fire_bolt.yaml': '708fa31698daa5326be286135664375ae5e997685e1c8231cb50d4cace6ed218', 'guiding_bolt.yaml': 'ad06e79a34dcea39ae63dd6d1a87ecc5c184593357cda9a5d61332dc4c1c6371', 'haste.yaml': '633a6e330e3a8d9858591c42a7cac85e37684d685dd62dc5f80d52aadfd8ad6c', 'healing_word.yaml': 'bade97f69bfe520284b0aa3f349ac7d377447778e7c32801c5209d0d9c8d165e', 'hex.yaml': '68b57dfff1783938174316a6e76151fd93db71c50dbe84131c5d9f2c7ec54dbb', 'hold_person.yaml': 'a91a21b1729d9d5c8cbd4d899f7d3a725ff5da361c494a2b4397038adef22eb6', 'hunters_mark.yaml': 'f46a4398048d7a099b3660d161d20b513debefaf118c0ca1873724c19f9f0687', 'magic_missile.yaml': '36d2e7b4cdc94157146e77c6aeafd9523d34e9ce6ca3c83cac388d7b51e1bbb6', 'sacred_flame.yaml': 'a548e40280258361ed3fd827c3044444a6d9388dca5ce8449eb28637393a880f', 'scorching_ray.yaml': '7de0a75e6c9c8d091804e4ae094e72e0596c5cef8f2eee163abc4ebdca43a089', 'shield.yaml': '8ea882e786b7c59863cc601037fdf9f42dfc9b11b906fbff0009159dd2ad7e7b', 'shield_of_faith.yaml': 'cbd45d05d356f6c33fa069a44a2810476d91811d2bc05dd1c303a085febe7144', 'spiritual_weapon.yaml': 'd8cf694a41c7b35cbc4f194726a4848b6866fb4066f5538b7ee69c97bd4e7600', 'spirit_guardians.yaml': 'e52b033d3c628aaeabb784e67063d1f2f01851cd8a8ccf04d10cb1efbbb25b38'}


class NoReactions(Policy):
    def reaction(self, *args): return False


@lru_cache(maxsize=1)
def spell_specs():
    return load_spells()


def arena(name, seed=1, level=1, enemies=8):
    spells = spell_specs()
    c = Combatant("caster", team="party", max_hp=100000, abilities={"wis": 18}, level=level,
                  spells=[name], spell_slots={i: 100 for i in range(1, 10)}, spell_dc=15, spell_attack_bonus=100)
    ds = [Combatant("target" + str(i), max_hp=100000, save_bonuses=dict.fromkeys(("str", "dex", "con", "int", "wis", "cha"), -100)) for i in range(enemies)]
    if name == "Polymorph":
        for d in ds: d.level = 9
    if name == "Planar Binding":
        for d in ds: d.creature_type = "fiend"
    if name == "Heat Metal":
        for d in ds: d.statuses["heated_metal"] = {}
    if name == "Arcane Vigor": c.hit_die = "d8"; c.hit_dice = 10; c.hp -= 100
    if name in {"Animal Friendship", "Dominate Beast"}:
        for d in ds: d.creature_type = "beast"
    if name in {"Spare the Dying", "Aura of Life"}:
        ds[0].hp = 0
        ds[0].conditions.add("unconscious")
        if name == "Aura of Life": ds[0].team = "party"
    if name in {"True Strike", "Shillelagh", "Magic Weapon", "Elemental Weapon", "Swift Quiver", "Alter Self"}:
        c.attacks = [{"name": "Club", "kind": "melee", "to_hit": 100, "effects": [{"damage": {"dice": "1d4", "bonus": 0, "type": "bludgeoning"}}]}, {"name": "Longbow", "kind": "ranged", "to_hit": 100, "effects": [{"damage": {"dice": "1d8", "bonus": 0, "type": "piercing"}}]}]
    if name == "Banishing Smite": ds[0].hp = 40
    b = Combat([c, *ds], spells, seed=seed, policy=NoReactions())
    b.begin_turn(c)
    return b, c, ds


def cast_fixture(b, c, name, slot=None):
    spec = b.spells[name]
    if spec.get("casting_trigger"):
        d = next(d for d in b.enemies(c))
        result = []
        def hit(crit, attack): result.append(b.cast(c, name, [d], slot=slot, trigger={"attacker": c, "defender": d, "attack": attack, "critical": crit}))
        b.attack(c, d, 100, hit, melee=spec["casting_trigger"] != "ranged_hit_or_miss", weapon=True)
        return result[0] if result else None
    return b.cast(c, name, slot=slot, trigger={"attacker":b.enemies(c)[0]} if name == "Hellish Rebuke" else None)


@lru_cache(maxsize=1)
def new_spells():
    return {name: s for name, s in load_spells().items() if (ROOT / "spells" / (name.lower().replace("'", "").replace(" ", "_") + ".yaml")).name not in GOLDEN}


def test_step3_scope_covers_all_xphb():
    records = read_yaml(ROOT / "spell_scope.yaml")["spells"]
    raw = source_spells()
    assert len(records) == len(raw) == 391
    assert {r["name"] for r in records} == set(raw)
    for r in records:
        assert r["level"] == raw[r["name"]]["level"]
        assert r["scope"] in {"combat", "partial", "out_of_scope"}
        assert len(r["reason"]) > 15 and "\n" not in r["reason"]
    scopes = {r["name"]: r["scope"] for r in records}
    assert scopes["Continual Flame"] == scopes["Light"] == "partial"
    assert scopes["Friends"] == "out_of_scope"
    assert scopes["Enthrall"] == "out_of_scope"
    assert scopes["Spare the Dying"] == "combat"
    assert scopes["Time Stop"] == scopes["Contingency"] == scopes["Wish"] == "combat"


def test_step3_golden_bytes():
    assert len(GOLDEN) == 20
    for filename, digest in GOLDEN.items():
        text = (ROOT / "spells" / filename).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(text).hexdigest() == digest


@pytest.mark.parametrize("name", sorted(load_spells()))
def test_step3_every_loaded_spell_has_independent_source_evidence(name):
    assert source_errors(spell_specs()[name]) == []


def test_step3_source_and_all_numeric_mutations():
    raw = source_spells()
    fields = mutations = 0
    survivors = []
    for name, spec in new_spells().items():
        assert source_errors(spec, raw[name]) == [], name
        fields += len(list(numeric_fields(spec)))
        for path, value, mutant in mutants(spec):
            mutations += 1
            if not source_errors(mutant, raw[name], validate=False): survivors.append((name, path, value))
    assert not survivors, survivors
    assert fields > 0 and mutations >= fields
    print(f"Step 3 numeric fields={fields}, mutations={mutations}, rejected={mutations}, survivors=0")


def test_step3_coverage_audit_reports_missing_files_without_claiming_completion():
    from engine.step3_report import audit, REFERENCES
    result = audit()
    scope = read_yaml(ROOT / "spell_scope.yaml")["spells"]
    required = {r["name"] for r in scope if r["level"] <= 5 and r["scope"] != "out_of_scope"} | REFERENCES
    assert result["required"] == len(required)
    assert result["missing"] == sorted(required - spell_specs().keys())
    assert len(required & spell_specs().keys()) + len(result["missing"]) == result["required"]
    assert result["failures"] == [] and result["allowlist"] == {}


def test_step3_audit_cli_fails_when_required_files_are_missing():
    import subprocess
    import sys
    from engine.step3_report import audit
    missing = audit()["missing"]
    result = subprocess.run([sys.executable, "-m", "engine.step3_report"],
        cwd=ROOT.parents[1], capture_output=True, text=True)
    assert result.returncode == (2 if missing else 0), result.stdout + result.stderr
    assert ("INCOMPLETE:" in result.stdout) == bool(missing)


@pytest.mark.parametrize("name", ["Acid Splash", "Chill Touch", "Mind Sliver", "Poison Spray", "Produce Flame", "Ray of Frost", "Shocking Grasp", "Sorcerous Burst", "Starry Wisp", "Thorn Whip", "Thunderclap", "Toll the Dead", "Vicious Mockery", "Word of Radiance", "Blade Ward"])
@pytest.mark.parametrize("level", [1, 5, 11, 17])
def test_step3_cantrips_cast_and_each_block_fires(name, level):
    b, c, ds = arena(name, level=level)
    inst = b.cast(c, name)
    assert inst is not None
    if name == "Produce Flame": assert b.command(inst, "action_command")
    fired = {e["block"] for e in b.log if e["event"] == "effect_block" and e["source"] == inst.id}
    assert fired == {e["id"] for e in inst.spec["effects"]}


def test_step3_riders_and_exact_lifetimes():
    b, c, (d, *_) = arena("Mind Sliver", seed=2)
    b.cast(c, "Mind Sliver", [d])
    assert b.modifier(d, "save", 0) in {-1, -2, -3, -4}
    b.saving_throw(d, "dex", 15)
    assert b.modifier(d, "save", 0) == 0
    b, c, (d, *_) = arena("Chill Touch", seed=2)
    b.cast(c, "Chill Touch", [d])
    assert d.has_status("healing_blocked")
    hp = d.hp
    b.heal(d, 100)
    assert d.hp == hp
    b.begin_turn(c); b.end_turn(c)
    b.heal(d, 100)
    assert d.hp > hp
    b, c, (d, *_) = arena("Starry Wisp", seed=2)
    d.conditions.add("invisible")
    b.cast(c, "Starry Wisp", [d])
    assert not d.has_condition("invisible")
    b.begin_turn(c); b.end_turn(c)
    assert d.has_condition("invisible")


def test_step3_blade_ward_is_incoming_only():
    b, c, (d, *_) = arena("Blade Ward")
    b.cast(c, "Blade Ward")
    assert b.modifier(c, "attack_roll", 10) == 10
    assert b.modifier(d, "attack_roll", 10, against=c) in {6, 7, 8, 9}
    assert b.modifier(d, "attack_roll", 10) == 10


def test_step3_toll_wounded_die_and_scaling():
    for level, n in [(1, 1), (5, 2), (11, 3), (17, 4)]:
        s = scaled_spell(load_spells()["Toll the Dead"], 0, level)
        assert s["effects"][0]["on_fail"][0]["damage"]["wounded_dice"] == f"{n}d12"
    b, c, (d, *_) = arena("Toll the Dead")
    d.hp -= 1
    b.cast(c, "Toll the Dead", [d])
    assert len([e for e in b.log if e["event"] == "save"]) == 1


@pytest.mark.parametrize("name", ["Arms of Hadar", "Burning Hands", "Dissonant Whispers", "Inflict Wounds", "Thunderwave", "Ray of Sickness", "Color Spray", "Bane", "Command", "Witch Bolt", "Ice Knife", "Mage Armor", "False Life", "Light", "Mage Hand", "Prestidigitation", "Thaumaturgy", "Detect Magic", "Disguise Self"])
@pytest.mark.parametrize("upcast", [False, True])
def test_step3_first_level_and_required_utility_casts(name, upcast):
    b, c, ds = arena(name)
    s = b.spells[name]
    inst = b.cast(c, name, slot=5 if upcast and s["level"] else s["level"])
    assert inst is not None
    if name == "Witch Bolt":
        b.begin_turn(c)
        assert b.command(inst)
    fired = {e["block"] for e in b.log if e["event"] == "effect_block" and e["source"] == inst.id}
    assert fired == {e["id"] for e in inst.spec["effects"]}


def test_step3_command_delayed_grovel_and_actions():
    b, c, (d, *_) = arena("Command")
    b.cast(c, "Command", [d], choices={"command": "grovel"})
    assert not d.has_condition("prone")
    b.begin_turn(d)
    assert d.has_condition("prone") and d.action == d.bonus_action == 0
    assert d.reaction == 1
    b.policy.take_turn(b, d)
    assert d.has_condition("prone")
    b.end_turn(d); b.begin_turn(d)
    assert d.action == d.bonus_action == 1
    assert d.has_condition("prone")  # Grovel doesn't magically stand the target up.


def test_step3_witch_bolt_miss_still_allows_sustain():
    b, c, (d, *_) = arena("Witch Bolt")
    c.spell_attack_bonus = -100
    inst = b.cast(c, "Witch Bolt", [d])
    assert d.hp == d.max_hp
    assert not b.command(inst)
    b.begin_turn(c)
    assert b.command(inst) and d.hp < d.max_hp


def test_step3_ice_knife_miss_explodes_on_actual_target():
    b, c, ds = arena("Ice Knife")
    c.spell_attack_bonus = -100
    d = ds[5]
    b.cast(c, "Ice Knife", [d])
    log = [e for e in b.log if e["event"] == "damage"]
    assert log and all(e["type"] == "cold" for e in log)
    assert log[0]["target"] == d.id and d.hp < d.max_hp


def test_step3_false_life_flat_scaling_and_base_ac():
    s = scaled_spell(spell_specs()["False Life"], 5, 1)
    assert s["effects"][0]["apply"][0]["temp_hp"]["dice"] == "2d4+24"
    b, c, (d, *_) = arena("Mage Armor")
    d.ac = 10; d.abilities["dex"] = 14
    b.cast(c, "Mage Armor", [d])
    assert b.armor_class(d) == 15
    d.features["armored"] = True
    assert b.armor_class(d) == 10


def test_step3_hadar_reaction_and_dissonant_spending():
    b, c, (d, *_) = arena("Arms of Hadar")
    d.spells = ["Shield"]; d.spell_slots = {1: 1}
    b.cast(c, "Arms of Hadar")
    assert not b.can_cast(d, "Shield")
    b.begin_turn(d)
    assert b.can_cast(d, "Shield")
    b, c, (d, *_) = arena("Dissonant Whispers")
    b.cast(c, "Dissonant Whispers", [d])
    assert d.reaction == 0


def configurations():
    result = []
    for name, s in new_spells().items():
        if s["level"] == 0: result.extend((name, 0, level) for level in (1, 5, 11, 17))
        else: result.extend((name, slot, 9) for slot in sorted({s["level"], max(5, s["level"])}))
    return result


@pytest.mark.parametrize("name,slot,level", configurations())
def test_step3_every_new_spell_cast_and_all_blocks(name, slot, level):
    b, c, ds = arena(name, level=level)
    if b.spells[name]["casting_time"] in {"minute", "minutes", "hour", "hours"}:
        b.current = None
        inst = b.prepare(c, name, slot=slot)
    else: inst = cast_fixture(b, c, name, slot=slot)
    assert inst is not None
    if name == "Glyph of Warding": b.dispatch("glyph_triggered")
    if name == "Bigby's Hand":
        inst.choices["mode"] = "grasp"
        b.begin_turn(c); b.command(inst)
        inst.choices["mode"] = "crush"
        b.begin_turn(c); b.command(inst)
    for command in ("action_command", "bonus_action_command"):
        b.begin_turn(c)
        b.command(inst, command)
    for d in ds:
        b.begin_turn(d); b.end_turn(d)
    if name == "Conjure Elemental": b.begin_turn(ds[0]); b.end_turn(ds[0])
    if any("on_attack_hit" in block["event"] for block in inst.spec["effects"]):
        d = next(d for d in ds if d.alive and d.team != c.team)
        b.weapon_attack(c, d, {"name": "Probe", "kind": "melee", "to_hit": 100, "effects": []})
    if any("on_attack_hit(any, caster)" in block["event"] for block in inst.spec["effects"]):
        b.weapon_attack(ds[0], c, {"name": "Probe", "kind": "melee", "to_hit": 100, "effects": []})
    if any("on_damaged(caster)" in block["event"] for block in inst.spec["effects"]):
        c.save_bonuses["con"] = 100
        b.damage(c, 1, "piercing", ds[0])
    fired = {e["block"] for e in b.log if e["event"] == "effect_block" and e["source"] == inst.id}
    assert fired == {e["id"] for e in inst.spec["effects"]}


@pytest.mark.parametrize("form", ["air", "land", "water"])
@pytest.mark.parametrize("slot", [2, 3, 4, 5])
def test_step3_beast_is_targetable_scaled_combatant_and_expires(form, slot):
    from engine.summoning import take_summoned_turns
    b, c, ds = arena("Summon Beast", level=9)
    inst = b.cast(c, "Summon Beast", slot=slot, choices={"form": form})
    (spirit,) = inst.summoned
    assert spirit in b.combatants and spirit in b.enemies(ds[0])
    assert spirit.ac == 11 + slot
    assert spirit.hp == (20 if form == "air" else 30) + 5 * (slot - 2)
    assert spirit.extra_attack == slot // 2
    assert spirit.attacks[0]["to_hit"] == c.spell_attack_bonus
    assert spirit.attacks[0]["effects"][0]["damage"]["bonus"] == 4 + slot
    b.log.clear()
    take_summoned_turns(b, c)
    assert len([e for e in b.log if e["event"] == "attack"]) == slot // 2
    assert [e["actor"] for e in b.log if e["event"] == "turn_start"] == [spirit.id]
    b.end_spell(inst.id)
    assert not spirit.alive and spirit.removed


def test_step3_summon_no_command_dodges_and_zero_hp_disappears():
    from engine.summoning import take_summoned_turns
    class Silent(NoReactions):
        def command_summon(self, *args): return False
    b, c, _ = arena("Summon Beast")
    b.policy = Silent()
    inst = b.cast(c, "Summon Beast")
    (spirit,) = inst.summoned
    take_summoned_turns(b, c)
    assert any(e["event"] == "dodge" for e in b.log)
    assert not any(e["event"] == "attack" for e in b.log)
    b.apply_damage(spirit, spirit.hp)
    assert spirit.removed and not spirit.alive
    assert c.concentration == inst.id  # Creature death is not caster concentration loss.


def test_step3_invisibility_ends_after_attack_not_before_and_is_target_local():
    b, c, (a, d, *_) = arena("Invisibility")
    inst = b.cast(c, "Invisibility", [a, d], slot=3)
    assert a.has_condition("invisible") and d.has_condition("invisible")
    b.attack(a, c, -100, lambda *args: None)
    assert not a.has_condition("invisible") and d.has_condition("invisible")
    assert [e for e in b.log if e["event"] == "attack"][-1]["advantage"]
    b.damage(c, 1, "force", d)
    assert not d.has_condition("invisible") and not inst.active


def test_step3_lesser_restoration_selects_one_and_barkskin_never_lowers_ac():
    b, c, (d, *_) = arena("Lesser Restoration")
    d.conditions.update({"paralyzed", "poisoned"})
    b.cast(c, "Lesser Restoration", [d], choices={"condition": "poisoned"})
    assert d.has_condition("paralyzed") and not d.has_condition("poisoned")
    b, c, (d, *_) = arena("Barkskin")
    d.ac = 20
    b.cast(c, "Barkskin", [d])
    assert b.armor_class(d) == 20
    d.ac = 10
    assert b.armor_class(d) == 17


def test_step3_cached_loads_are_independent_and_invalidate(tmp_path):
    import yaml
    from engine.loader import load_spell
    p = tmp_path / "spell.yaml"
    p.write_text(yaml.safe_dump(spell_specs()["Fire Bolt"]), encoding="utf8")
    first = load_spell(p)
    first["range"]["feet"] = 999
    assert load_spell(p)["range"]["feet"] == 120
    changed = load_spell(p); changed["range"]["feet"] = 121
    p.write_text(yaml.safe_dump(changed), encoding="utf8")
    assert load_spell(p)["range"]["feet"] == 121
    changed["surprise"] = True
    p.write_text(yaml.safe_dump(changed), encoding="utf8")
    with pytest.raises(ValueError): load_spell(p)


def test_step3_source_tag_gate_is_semantic_not_substring():
    s = deepcopy(spell_specs()["Mind Sliver"])
    s["effects"][0]["save"]["ability"] = "str"
    assert any("savingThrow: intelligence" in e for e in source_errors(s))


@pytest.mark.parametrize("form", ["ghostly", "putrid", "skeletal"])
@pytest.mark.parametrize("slot", [3, 4, 5])
def test_step3_undead_scaled_forms_and_riders(form, slot):
    from engine.summoning import take_summoned_turns
    b, c, ds = arena("Summon Undead")
    inst = b.cast(c, "Summon Undead", slot=slot, choices={"form": form})
    (s,) = inst.summoned
    assert s.ac == 11 + slot
    assert s.hp == (20 if form == "skeletal" else 30) + 10 * (slot - 3)
    assert s.immunities == ["necrotic", "poison"]
    assert s.spell_dc == c.spell_dc and s.extra_attack == slot // 2
    if form == "putrid":
        b.begin_turn(c)
        assert not c.has_condition("poisoned")
        b.begin_turn(ds[0])
        assert ds[0].has_condition("poisoned")
    take_summoned_turns(b, c)
    assert len([e for e in b.log if e["event"] == "attack"]) == slot // 2
    if form == "ghostly": assert ds[0].has_condition("frightened")
    if form == "putrid": assert ds[0].has_condition("paralyzed")
    c.save_bonuses["con"] = -100
    b.damage(c, 1, "force")
    assert not inst.active and not s.alive


def test_step3_summons_share_initiative_without_double_turns():
    class Summoner(NoReactions):
        def take_turn(self, b, actor):
            if actor.id == "caster":
                if actor.concentration is None: b.cast(actor, "Summon Beast")
            else: super().take_turn(b, actor)
    b, c, ds = arena("Summon Beast")
    c.initiative_bonus = 100
    b.policy = Summoner()
    inst = b.cast(c, "Summon Beast")  # Already present before run(), too.
    b.log.clear(); b.run(max_rounds=2)
    starts = [e["actor"] for e in b.log if e["event"] == "turn_start"]
    assert starts[:2] == [c.id, inst.summoned[0].id]
    assert starts.count(inst.summoned[0].id) == 2
    assert inst.summoned[0].id not in next(e["order"] for e in b.log if e["event"] == "initiative")


def test_step3_dispel_uses_actual_cast_level_and_check():
    b, c, (d, *_) = arena("Dispel Magic")
    c.spells.extend(["Bless", "Haste"])
    buff = b.cast(c, "Bless", [d], slot=5)
    b.begin_turn(c)
    c.abilities["wis"] = 1
    # Fixed failing check: 1 + (-5) cannot meet 10 + 5.
    class Ones:
        def randint(self, a, z): return a
    b.rng = Ones()
    b.cast(c, "Dispel Magic", [d], slot=3)
    assert buff.active
    b.begin_turn(c)
    b.cast(c, "Dispel Magic", [d], slot=5)
    assert not buff.active


def test_step3_slow_action_choice_attack_limit_reactions_and_repeat_save():
    b, c, (d, *_) = arena("Slow")
    d.spells = ["Shield"]; d.spell_slots = {1: 100}
    d.attacks = [{"name": "sword", "kind": "melee", "to_hit": 100, "effects": [{"damage": {"dice": "1d6", "bonus": 0, "type": "slashing"}}]}]
    d.extra_attack = 3
    inst = b.cast(c, "Slow", [d])
    assert b.armor_class(d) == 8 and not b.can_cast(d, "Shield")
    b.begin_turn(d)
    assert b.weapon_action(d)
    assert d.action == d.bonus_action == 0
    assert len([e for e in b.log if e["event"] == "attack"]) == 1
    d.save_bonuses["wis"] = 100
    b.end_turn(d)
    assert b.armor_class(d) == 10 and b.can_cast(d, "Shield")
    assert not any(e.source == inst.id for e in d.effects)


def test_step3_slow_somatic_failure_is_seeded_and_spends_slot():
    failures = 0
    for seed in range(1600):
        b, c, (d, *_) = arena("Slow", seed)
        b.cast(c, "Slow", [d])
        d.spells = ["Fire Bolt"]; d.spell_slots = {1: 1}
        b.begin_turn(d)
        result = b.cast(d, "Fire Bolt")
        failures += result is None
        assert d.action == d.bonus_action == 0
    assert failures / 1600 == pytest.approx(.25, abs=.03)
    b, c, (d, *_) = arena("Slow", seed=1)
    b.cast(c, "Slow", [d])
    d.spells = ["Inflict Wounds"]; d.spell_slots = {1: 1}
    b.begin_turn(d); b.cast(d, "Inflict Wounds")
    assert d.spell_slots[1] == 0


def test_step3_golem_recharge_and_component_exemptions():
    from engine.loader import load_sheet
    s = load_sheet(ROOT / "monsters/stone_golem.yaml")
    g = Combatant.from_sheet(s, "g", "party")
    d = Combatant("d")
    b = Combat([g, d], spell_specs(), seed=1, policy=NoReactions())
    b.begin_turn(g)
    assert b.cast(g, "Slow")
    assert not g.recharge_ready["Slow"]
    assert not b.can_cast(g, "Slow")
    class Sixes:
        def randint(self, a, z): return z
    b.rng = Sixes(); b.begin_turn(g)
    assert b.can_cast(g, "Slow")
    imp = Combatant.from_sheet(load_sheet(ROOT / "monsters/imp.yaml"), "imp", "party")
    effective = b.scale(imp, spell_specs()["Invisibility"], 2)
    assert not any(effective["components"][key] for key in ("v", "s", "m"))


def test_step3_turn_control_is_valued_by_default_policy():
    b, c, (d, *_) = arena("Slow")
    d.attacks = [{"name": "sword", "kind": "melee", "to_hit": 5, "effects": [{"damage": {"dice": "1d8", "bonus": 3, "type": "slashing"}}]}]
    d.extra_attack = 2
    assert b.expected_spell_damage(c, b.spells["Slow"], d) > 0
    b.policy.take_turn(b, c)
    assert any(e["event"] == "cast" and e["spell"] == "Slow" for e in b.log)


@pytest.mark.parametrize("name", sorted(name for name in load_spells()
    if source_spells()[name]["range"]["type"] != "point"
    and source_spells()[name]["range"].get("distance", {}).get("type") == "feet"))
def test_step3_self_centred_range_and_source_type_mutation(name):
    s = spell_specs()[name]
    assert s["range"] == {"type": "self"}
    assert source_errors(s) == []
    mutant = deepcopy(s)
    mutant["range"] = {"type": "point", "feet": source_spells()[name]["range"]["distance"]["amount"]}
    Validator(name).spell(mutant)  # Schema-valid, but not source-valid.
    assert any("range.type" in e for e in source_errors(mutant, validate=False))


@pytest.mark.parametrize("name", ["Burning Hands", "Color Spray", "Lightning Bolt", "Conjure Barrage"])
def test_step3_caster_is_not_inside_own_cone_or_line(name):
    b, c, ds = arena(name)
    b.combatants = [c, ds[0]]
    b.cast(c, name)
    assert c.hp == c.max_hp and not c.has_condition("blinded")
    assert not any(e["event"] == "effect_block" and e["target"] == c.id for e in b.log)


@pytest.mark.parametrize("form", ["air", "earth", "fire", "water"])
@pytest.mark.parametrize("slot", [4, 5])
def test_step3_elemental_forms_use_main_xphb_block(form, slot):
    from engine.summon_validation import source_stat_blocks
    from engine.summoning import take_summoned_turns
    import re
    raw = source_stat_blocks()["Elemental Spirit"]
    b, c, ds = arena("Summon Elemental", level=9)
    inst = b.cast(c, "Summon Elemental", slot=slot, choices={"form": form})
    (spirit,) = inst.summoned
    assert (spirit.ac, spirit.max_hp, spirit.extra_attack) == (11 + slot, 50 + 10 * (slot - 4), slot // 2)
    text = " ".join(raw["action"][1]["entries"])
    damage_types = {m[2].lower(): m[1].lower() for m in re.finditer(r"(\w+) \((\w+) only\)", text)}
    assert spirit.attacks[0]["effects"][0]["damage"]["type"] == damage_types[form]
    def defenses(key):
        result = []
        for item in raw.get(key, []):
            if isinstance(item, str): result.append(item)
            elif form in item["note"].lower(): result.extend(item[key])
        return result
    assert spirit.resistances == defenses("resist")
    assert spirit.immunities == defenses("immune")
    take_summoned_turns(b, c)
    assert len([e for e in b.log if e["event"] == "attack"]) == slot // 2
    assert all(e["type"] == damage_types[form] for e in b.log if e["event"] == "damage")
    b.end_spell(inst.id)
    assert spirit.removed


def test_step3_phantasmal_killer_2024_penalties_and_repeat_success():
    b, c, (d, *_) = arena("Phantasmal Killer")
    inst = b.cast(c, "Phantasmal Killer", [d], slot=5)
    assert inst.active and not d.has_condition("frightened")
    assert b.roll_flags(d, "attack_rolls") == (False, True)
    assert b.roll_flags(d, "ability_checks", "str") == (False, True)
    hp = d.hp
    b.begin_turn(d); b.end_turn(d)
    assert d.hp < hp
    hp = d.hp
    d.save_bonuses["wis"] = 100
    b.begin_turn(d); b.end_turn(d)
    assert d.hp == hp and not inst.active
    assert b.roll_flags(d, "attack_rolls") == (False, False)
    b, c, (d, *_) = arena("Phantasmal Killer")
    d.save_bonuses["wis"] = 100
    inst = b.cast(c, "Phantasmal Killer", [d])
    assert not inst.active and d.hp < d.max_hp
    assert not any(e.source == inst.id for e in d.effects)


def test_step3_hound_bites_on_caster_start_not_creation_or_enemy_turn():
    b, c, (d, *_) = arena("Mordenkainen's Faithful Hound")
    b.cast(c, "Mordenkainen's Faithful Hound")
    hp = d.hp
    assert hp == d.max_hp
    b.begin_turn(d); b.end_turn(d)
    assert d.hp == hp
    b.begin_turn(c)
    assert d.hp < hp


def test_step3_jallarzi_conditions_and_component_prohibition_follow_membership():
    b, c, (d, *_) = arena("Jallarzi's Storm of Radiance")
    inst = b.cast(c, "Jallarzi's Storm of Radiance")
    assert d.has_condition("blinded") and d.has_condition("deafened")
    d.spells = ["Fire Bolt", "Counterspell"]
    d.spell_slots = {3: 1}
    b.begin_turn(d)
    assert not b.can_cast(d, "Fire Bolt")
    assert b.can_cast(d, "Counterspell")  # Somatic only, not blanket anti-magic.
    d.spell_components = {"Fire Bolt": {"v": False}}
    assert b.can_cast(d, "Fire Bolt")
    d.spell_components = {}
    b.area = lambda shape, size, count: 0
    b.refresh_areas(inst)
    assert not d.has_condition("blinded") and not d.has_condition("deafened")
    assert not d.has_status("verbal_components_blocked")
    assert b.can_cast(d, "Fire Bolt")


def test_step3_mage_cone_of_cold_uses_real_fifth_level_daily_cast():
    from engine.loader import load_sheet
    mage = Combatant.from_sheet(load_sheet(ROOT / "monsters/mage.yaml"), "mage", "enemy")
    target = Combatant("target", team="party", max_hp=100000)
    b = Combat([mage, target], spell_specs(), seed=1, policy=NoReactions())
    b.begin_turn(mage)
    inst = b.cast(mage, "Cone of Cold")
    assert inst and inst.slot == 5
    assert target.hp < target.max_hp and mage.hp == mage.max_hp
    assert mage.resources_spent["Cone of Cold"] == 1
    b.begin_turn(mage)
    assert not b.can_cast(mage, "Cone of Cold")
