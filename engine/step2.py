"""Reviewed Step 2 supplements and reproducible verification/report entry point.

--write regenerates only the 66 new monster sheets from XMM plus these explicit
review decisions. No spell declarations are generated or changed.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import re
import yaml

from .loader import ROOT, load_spells
from .monster_import import STEP2, source_monsters, parse_monster, entries_text, clean_name, slug
from .sheets import effect_block


def condition(name, *, until=None, **options):
    p = {"apply_condition": {"condition": name, **options}}
    if until: p["until"] = until
    return p


def area(shape, size):
    return {"select": "area", "shape": shape, "size_ft": size, "affects": "all", "filter": ["creature"]}


def single():
    return {"select": "single", "filter": ["creature"], "affects": "enemy"}


def damage(dice, dtype, bonus=0):
    return {"damage": {"dice": dice, "bonus": bonus, "type": dtype}}


def supplement(raw, golden):
    s = parse_monster(raw)
    name = s["name"]
    s["size"] = raw["size"][-1]
    notes = [x for x in s["unsupported"] if x.startswith("Conditional")]
    s["unsupported"] = notes
    f = s.setdefault("features", {})
    attacks = {a["name"]: a for a in s["attacks"]}
    actions = {a["name"]: a for a in s["actions"]}

    def note(text): notes.append(text)
    def feature(key, value=True): f[key] = value
    def hit(attack, *effects): attacks[attack]["effects"].extend(effects)
    def failed(action, *effects, duration=None):
        a = actions[action]
        a["effects"][0]["on_fail"].extend(effects)
        if duration: a["duration"] = duration
    def ongoing(action, dice, dtype, event):
        b = effect_block("ongoing", target={"select": "ref", "ref": "main"}, apply=[damage(dice, dtype)])
        b["event"] = event
        if action in {"Engulf", "Whelm"}: b["if"] = "target.has_condition_from(" + ("restrained" if action == "Engulf" else "grappled") + ", caster)"
        if action == "Spores": b["if"] = "target.has_condition_from(poisoned, caster)"
        actions[action]["effects"].append(b)
    def grapple(attack, dc, size, restrained=False):
        capacity = {"Vampire Spawn":2,"Chain Devil":2,"Barbed Devil":1,"Aboleth":4}.get(name)
        hit(attack, condition("grappled", escape_dc=dc, max_size=size, linked=True, **({"capacity":capacity} if capacity else {})))
        if restrained: hit(attack, {**condition("restrained", max_size=size, linked=True), "if":"target.has_condition_from(grappled, caster)"})
        note(f"{attack}: no grid/limb occupancy; grapple size, escape DC and explicitly printed limb capacity are enforced; exact limb positioning is not modeled.")
    def duration(action, value=None): actions[action]["duration"] = value or {"type": "special"}

    # Explicit, reviewed routine choices, not importer prose guesses.
    choices = {
        "Bandit Captain": (2, ["Scimitar", "Pistol"]), "Guard Captain": (2, ["Javelin", "Longsword"]),
        "Priest": (2, ["Mace", "Radiant Flame"]), "Knight": (2, ["Greatsword", "Heavy Crossbow"]),
        "Warrior Veteran": (2, ["Greatsword", "Heavy Crossbow"]), "Assassin": (3, ["Shortsword", "Light Crossbow"]),
        "Scout": (2, ["Shortsword", "Longbow"]), "Goblin Boss": (2, ["Scimitar", "Shortbow"]),
        "Hobgoblin Captain": (2, ["Greatsword", "Longbow"]), "Bugbear Stalker": (2, ["Javelin", "Morningstar"]),
        "Manticore": (3, ["Rend", "Tail Spike"]), "Hill Giant": (2, ["Tree Club", "Trash Lob"]),
        "Earth Elemental": (2, ["Slam", "Rock Launch"]), "Stone Golem": (2, ["Slam", "Force Bolt"]),
        "Wight": (2, ["Necrotic Sword", "Necrotic Bow"]),
    }
    if name in choices:
        from itertools import product
        n, options = choices[name]
        s["routines"] = [list(x) for x in product(options, repeat=n)]
    if not s["multiattack"] and name not in choices:
        s["routines"] = [[a["name"]] for a in s["attacks"]]
    fixed = {"Gladiator": ["Spear"] * 3, "Pirate": ["Dagger"] * 2, "Mummy": ["Rotting Fist"] * 2 + ["Dreadful Glare"],
             "Vampire Spawn": ["Claw"] * 2 + ["Bite"], "Chain Devil": ["Chain"] * 2 + ["Conjure Infernal Chain"],
             "Aboleth": ["Tentacle"] * 2 + ["Consume Memories"], "Adult Red Dragon": ["Rend"] * 3}
    if name in fixed: s["routines"] = [fixed[name]]
    if name == "Barbed Devil": s["routines"] = [["Claws", "Tail"], ["Hurl Flame", "Hurl Flame"]]
    replacements = {"Gladiator": "Shield Bash", "Pirate": "Enthralling Panache", "Wight": "Life Drain", "Adult Red Dragon": "Scorching Ray"}
    if name in replacements: s["replacements"] = [replacements[name]]
    if name == "Aboleth": s["routines"].append(["Tentacle", "Tentacle", "Dominate Mind"])

    for trait in raw.get("trait", []):
        t = trait["name"]
        if t == "Pack Tactics": feature("pack_tactics")
        elif t == "Magic Resistance": feature("magic_resistance")
        elif t == "Sunlight Sensitivity": feature("sunlight_sensitivity")
        elif t == "Bloodied Frenzy": feature("bloodied_frenzy")
        elif t == "Evasion": feature("evasion")
        elif t.startswith("Legendary Resistance"):
            s.setdefault("limited_uses", {})["legendary_resistance"] = 3
        elif t == "Undead Fortitude": feature("undead_fortitude", 5)
        elif t == "Regeneration": feature("regeneration", {"amount": 15, "blocked_by": ["acid", "fire"], "at_zero": True})
        elif t == "Aura of Authority": feature("authority_aura")
        elif t == "Barbed Hide": feature("grapple_damage")
        elif t in {"Stench", "Fire Aura"}:
            if t == "Fire Aura":
                b = effect_block("aura", target=area("emanation", 10), apply=[damage("1d10", "fire"), {"burning": {}}])
                b["event"] = "end_of_turn(caster)"
                s["traits"].append({"name": t, "cost": "free", "passive": True, "effects": [b]})
                note("Fire Aura/Burn: creature burning and extinguishing execute; terrain/object ignition is unsupported.")
            else:
                dc = 10 if name == "Ghast" else 16
                b = effect_block("stench", target=area("emanation", 5 if name == "Ghast" else 10), save={"ability": "con", "dc": dc, "on_success": "negate"}, on_fail=[condition("poisoned", until="start_of_turn(target.next_turn)")])
                if name == "Ghast": b["on_success"] = [{"status": {"id": "stench_immune", "data": {}}}]
                s["traits"].append({"name": t, "cost": "free", "trigger": "creature_turn_start", "duration": {"type": "special"}, "effects": [b]})
        elif t == "Mucus Cloud": note("Mucus Cloud: underwater-only Constitution save DC 14, healing curse and Acid damage every 10 minutes require water/environment and noncombat time; unsupported in dry, lair-free encounters.")
        elif t == "Vampire Weakness":
            feature("sunlight_sensitivity")
            note("Vampire Weakness: Forbiddance, running-water Acid damage, staking, and sunlight Radiant damage require environment/adjudication; not generated in default indoor encounters. Sunlight attack/check disadvantage is executable via combat.sunlight.")
        elif t == "Loathsome Limbs (4/Day)": note("Loathsome Limbs (4/Day): spawning separate Troll Limb creatures/limb occupancy and associated Exhaustion require a dynamic roster; unsupported.")
        elif t == "Fire Form": note("Fire Form: squeezing/space entry and entry Fire damage require movement/grid; unsupported.")
        elif t == "Water Susceptibility": note("Water Susceptibility: environmental water movement/splash Cold damage needs water quantities and movement; unsupported.")
        elif t == "Incorporeal Movement": note("Incorporeal Movement: object traversal, Difficult Terrain and self Force damage inside objects require terrain/grid; unsupported.")
        elif t == "Ooze Cube": note("Ooze Cube: entry disadvantage, total cover, external rescue (Strength check DC 12 plus Acid damage) and transport require grid/object interactions; unsupported. Engulf itself, its escape action and recurring damage execute.")
        else: note(f"{t}: noncombat, sensory, movement, environment or post-encounter restoration; no grid/noncombat adjudication.")

    # Hit riders: explicit lifetimes and source-bound grapples.
    poison = {"Assassin": "Shortsword", "Quasit": "Rend", "Wyvern": "Sting", "Bone Devil": "Infernal Sting"}
    if name in poison: hit(poison[name], condition("poisoned", until="start_of_turn(caster.next_turn)"))
    prone = {"Wolf": ("Bite", "M"), "Dire Wolf": ("Bite", "L"), "Brown Bear": ("Claw", "L"), "Hill Giant": ("Tree Club", "L"), "Earth Elemental": ("Rock Launch", "L"), "Water Elemental": ("Slam", "M")}
    if name in prone:
        attack, size = prone[name]
        hit(attack, condition("prone", max_size=size))
    if name == "Hill Giant": hit("Trash Lob", condition("poisoned", until="end_of_turn(target.next_turn)"))
    for creature, attack, dc, size, restrained in [
        ("Bugbear Warrior", "Grab", 12, "M", False), ("Vampire Spawn", "Claw", 13, "M", False),
        ("Chain Devil", "Chain", 14, "L", True), ("Barbed Devil", "Claws", 13, "L", False),
        ("Aboleth", "Tentacle", 14, "L", False)]:
        if name == creature: grapple(attack, dc, size, restrained)
    if name in {"Bugbear Warrior", "Bugbear Stalker"}:
        attacks["Light Hammer" if name == "Bugbear Warrior" else "Morningstar"]["advantage_if"] = "grappled_by_self"
    if name == "Bugbear Stalker":
        failed("Quick Grapple", condition("grappled", escape_dc=13, max_size="M", linked=True)); duration("Quick Grapple")
    if name in {"Ghoul", "Ghast"}:
        b = effect_block("paralysis", target=single(), save={"ability": "con", "dc": 10, "on_success": "negate"}, on_fail=[condition("paralyzed", until="end_of_turn(target.next_turn)")])
        b["if"] = "target.creature_type != undead"
        attacks["Claw"]["riders"] = [b]
        if name == "Ghoul": note("Claw: elf ancestry immunity is unsupported because fixed combatants have no species/ancestry field; Undead exclusion is enforced.")
    if name == "Worg": hit("Bite", {"advantage": {"on": "attack_rolls", "scope": "all", "against": "target", "recipient": "any_attacker", "uses": 1}, "until": "start_of_turn(caster.next_turn)"})
    if name in {"Specter", "Wraith", "Wight", "Vampire Spawn"}:
        feature("life_drain", {"attacks": ["Bite" if name == "Vampire Spawn" else "Life Drain"], "type": "necrotic" if name == "Vampire Spawn" else "all", "heal": name == "Vampire Spawn"})
        note("Life Drain: revival and maximum-HP recovery after the encounter are outside this single-encounter monster model.")
    if name == "Mummy":
        hit("Rotting Fist", {"status": {"id": "healing_blocked", "data": {}}})
        failed("Dreadful Glare", condition("frightened", until="end_of_turn(caster.next_turn)"))
        actions["Dreadful Glare"]["effects"][0]["on_success"] = [{"status": {"id": "glare_immune", "data": {}}}]
        actions["Dreadful Glare"]["effects"][0]["if"] = "not target.has_status_from(glare_immune, caster)"
        duration("Dreadful Glare")
        note("Rotting Fist: 24-hour maximum-HP curse, dust/death and long-rest recovery require noncombat time; healing prevention executes.")
    if name == "Fire Elemental": hit("Burn", {"burning": {}})
    if name == "Bone Devil": hit("Infernal Sting", {"status": {"id": "healing_blocked", "data": {"requires_condition": "poisoned"}}, "until": "start_of_turn(caster.next_turn)"})
    if name == "Minotaur of Baphomet":
        attacks["Gore"]["effects"][-1]["if"] = "caster.has_status(charged) and target.size in [T, S, M, L]"
        hit("Gore", {**condition("prone", max_size="L"), "if": "caster.has_status(charged)"})
        note("Gore: conditional extra 3d6 Piercing damage/Prone requires 10-foot straight charge; gridless default never invents charged movement (caller may set charged status). Recharge still executes.")
    if name == "Gladiator": failed("Shield Bash", condition("prone", max_size="M")); duration("Shield Bash")
    if name == "Pirate": failed("Enthralling Panache", condition("charmed", until="start_of_turn(caster.next_turn)")); duration("Enthralling Panache")
    if name == "Quasit": failed("Scare", condition("frightened", repeat_save={"ability": "wis", "timing": "end_of_turn", "on_success": "end"})); duration("Scare", {"type": "rounds", "n": 10})
    if name == "Basilisk":
        failed("Petrifying Gaze", condition("restrained", repeat_save={"ability": "con", "timing": "end_of_turn", "on_success": "end"}, upgrade_on_failure="petrified")); duration("Petrifying Gaze")
        note("Petrifying Gaze: self-reflection requires mirrors/grid; unsupported. Failed first save restrains; failed next-turn save petrifies.")
    if name == "Giant Spider":
        failed("Web", condition("restrained", obstacle={"ac":10,"hp":5,"vulnerabilities":["fire"],"immunities":["poison","psychic"]})); duration("Web")
        note("Web: AC 10/HP 5 destructible restraint executes via the trapped creature's Attack action; ally rescue/positioning and object-targeted spell choice are not planned by default AI.")
    if name == "Air Elemental": failed("Whirlwind", condition("prone", max_size="M")); duration("Whirlwind"); note("Whirlwind: forced 20-foot movement and exact occupied-space targeting need a grid; single eligible target approximated.")
    if name == "Chain Devil":
        failed("Conjure Infernal Chain", condition("restrained", until="end_of_turn(caster.next_turn)")); duration("Conjure Infernal Chain")
        note("Conjure Infernal Chain: 30-foot pull has no grid effect.")
    if name == "Gelatinous Cube":
        actions["Engulf"]["effects"][0]["target"] = {"select": "n_targets", "n": 4, "up_to": True, "distinct": True, "filter": ["creature"], "affects": "enemy"}
        failed("Engulf", {"status": {"id": "engulfed", "data": {"escape_dc": 12}}}, condition("restrained", max_size="L")); duration("Engulf")
        actions["Engulf"]["effects"][0]["target"]["max_size"]="L"
        actions["Engulf"]["effects"][0]["admission"] = {"status": "engulfed", "capacity": 4, "large_cost": 4}
        ongoing("Engulf", "3d6", "acid", "start_of_turn(caster)")
        actions["Engulf"]["effects"][-1]["if"] = "target.has_status_from(engulfed, caster)"
        note("Engulf: up to four targets selected without grid; one Large or four smaller creatures capacity is enforced. Exact entry path and suffocation need grid/breath timers. Verbal spells are blocked while engulfed.")
    if name == "Water Elemental":
        actions["Whelm"]["effects"][0]["target"] = {"select": "n_targets", "n": 2, "up_to": True, "distinct": True, "filter": ["creature"], "affects": "enemy"}
        failed("Whelm", condition("grappled", escape_dc=14, max_size="L", linked=True, capacity=2, large_cost=2), {**condition("restrained", max_size="L", linked=True), "if":"target.has_condition_from(grappled, caster)"}); duration("Whelm")
        actions["Whelm"]["effects"][0]["target"]["max_size"]="L"
        ongoing("Whelm", "2d8", "bludgeoning", "start_of_turn(caster)")
        note("Whelm: up to two targets selected without grid; one Large or two smaller creatures capacity is enforced. External rescue and suffocation require grid/breath timers; self escape and recurring damage execute.")
    if name == "Vrock":
        failed("Spores", condition("poisoned", repeat_save={"ability": "con", "timing": "end_of_turn", "on_success": "end"})); duration("Spores", {"type": "special"})
        ongoing("Spores", "1d10", "poison", "start_of_turn(target)")
        failed("Stunning Screech", condition("stunned", until="end_of_turn(caster.next_turn)")); duration("Stunning Screech")
        actions["Stunning Screech"]["effects"][0]["if"] = "target.creature_type != fiend"
        note("Stunning Screech: demons auto-succeed, approximated as fiends (no fiend-subtype field). Spores: Holy Water removal is an unsupported inventory interaction.")
    if name == "Vampire Spawn":
        actions["Bite"]["effects"][0]["if"] = "target.has_condition(grappled) or target.has_condition(incapacitated) or target.has_condition(restrained)"
        actions["Bite"]["effects"][0]["target"]["eligible_if"] = actions["Bite"]["effects"][0]["if"]
        note("Bite: Grappled from any source, Incapacitated and Restrained eligibility execute; AI does not ask enemies to become willing bite targets.")
    if name == "Aboleth":
        actions["Consume Memories"]["effects"][0]["if"] = "target.has_condition_from(grappled, caster) or target.has_condition_from(charmed, caster)"
        actions["Consume Memories"]["effects"][0]["target"]["eligible_if"] = actions["Consume Memories"]["effects"][0]["if"]
        failed("Dominate Mind", condition("charmed", linked=True, control=True, repeat_on_damage=True)); duration("Dominate Mind")
        s["legendary"] = {"uses": raw.get("legendaryActions", 3), "options": [
            {"name": "Lash", "cost": 1, "attacks": ["Tentacle"]},
            {"name": "Psychic Drain", "cost": 1, "effects": deepcopy(actions["Consume Memories"]["effects"]), "heal": "1d10", "requires_bound_target": True}]}
        note("Consume Memories: memory acquisition is noncombat. Dominate Mind: cross-plane and mile/day repeat saves are outside encounter time. Lair actions (including tagged Constitution saves) are deliberately excluded.")
    if name == "Adult Red Dragon":
        s["legendary"] = {"uses": raw.get("legendaryActions", 3), "options": [
            {"name": "Commanding Presence", "cost": 1, "effects": [], "once_per_round": True},
            {"name": "Fiery Rays", "cost": 1, "spell": "Scorching Ray", "once_per_round": True},
            {"name": "Pounce", "cost": 1, "attacks": ["Rend"]}]}
        # Unsupported spell options are notes, not empty executable declarations.
        s["legendary"]["options"].pop(0)
        note("Commanding Presence: Command is outside golden set (Wisdom save; can inflict Prone); unsupported. Pounce movement needs grid. Lair actions (tagged Constitution saves) are deliberately excluded; resistance uses the lair-free 3/day count.")

    for reaction in raw.get("reaction", []):
        if reaction["name"] == "Parry": feature("parry", 3 if name == "Gladiator" else 2)
        elif reaction["name"] == "Redirect Attack": feature("redirect_attack"); note("Redirect Attack: gridless adjacency assumes any living Small/Medium ally is within 5 feet; redirects both weapon and spell attack rolls.")
        elif reaction["name"] == "Unnerving Gaze":
            b = effect_block("gaze", target=single(), save={"ability": "wis", "dc": 15, "on_success": "negate"}, on_fail=[condition("frightened", until="end_of_turn(target.next_turn)")])
            b["on_success"] = [{"status": {"id": "gaze_immune", "data": {}}}]
            s["traits"].append({"name": "Unnerving Gaze", "cost": "reaction", "trigger": "enemy_turn_start", "duration": {"type": "special"}, "effects": [b]})
    for bonus in raw.get("bonus", []):
        bn = clean_name(bonus["name"])
        if bn in actions: continue
        if bn in {"Nimble Escape", "Cunning Action", "Deathless Agility"}:
            b = effect_block("escape", apply=[{"status": {"id": "disengaged", "data": {}}, "until": "end_of_turn(caster.next_turn)"}])
            s["traits"].append({"name": bn, "cost": "bonus_action", "effects": [b]})
            note(f"{bn}: no-grid Disengage bookkeeping only; Hide/Dash need concealment/movement and are unsupported.")
        elif bn == "Rampage":
            feature("rampage"); s.setdefault("limited_uses", {})["Rampage"] = 1
            note("Rampage: bonus attack after damaging an already Bloodied target executes; half-speed movement needs a grid.")
        else: note(f"{bn}: movement-only bonus action needs a grid; unsupported.")
    for action in raw.get("action", []):
        an = clean_name(action["name"])
        if an not in attacks and an not in actions and an != "Multiattack": note(f"{an}: shape, corpse spawning, or noncombat adjudication is unsupported.")
    if name == "Wight": note("Life Drain: Zombie creation after 24 hours and controlled undead roster are noncombat; unsupported.")

    # Golden spells only, preserving shared pools, printed casting levels and costs.
    s["spells"] = []; s["unsupported_spells"] = []
    for sc in raw.get("spellcasting", []):
        ability = sc["ability"]
        s["spell_ability"] = ability
        s.setdefault("spell_dc", 8 + s["proficiency_bonus"] + (s["abilities"][ability] - 10) // 2)
        s.setdefault("spell_attack_bonus", s["proficiency_bonus"] + (s["abilities"][ability] - 10) // 2)
        header = entries_text(sc.get("headerEntries", []))
        dc = re.search(r"\{@dc (\d+)\}", header)
        to_hit = re.search(r"\{@hit ([+-]?\d+)\}", header)
        if dc: s["spell_dc"] = int(dc[1])
        if to_hit: s["spell_attack_bonus"] = int(to_hit[1])
        groups = [("will", sc.get("will", []))] + [(k, v) for k, v in sc.get("daily", {}).items()]
        groups += [("recharge " + k, v) for k, v in sc.get("recharge", {}).items()]
        for frequency, spells in groups:
            for text in spells:
                sn = re.search(r"\{@spell ([^|}]+)", text)[1]
                if sn not in golden:
                    s["unsupported_spells"].append(sn)
                    continue
                if sn not in s["spells"]: s["spells"].append(sn)
                level = re.search(r"level (\d+) version", text)
                s.setdefault("spell_levels", {})[sn] = int(level[1]) if level else golden[sn]["level"]
                cost = {"bonus": "bonus_action"}.get(sc.get("displayAs", "action"), sc.get("displayAs", "action"))
                s.setdefault("spell_costs", {})[sn] = cost
                if "requiring no spell components" in header:
                    s.setdefault("spell_components", {})[sn] = {"v": False, "s": False, "m": False}
                elif "requiring no Material components" in header:
                    s.setdefault("spell_components", {})[sn] = {"m": False}
                if frequency.startswith("recharge "):
                    s.setdefault("spell_recharge", {})[sn] = int(frequency.split()[1])
                elif frequency != "will":
                    count = int(frequency.rstrip("e"))
                    resource = sn if frequency.endswith("e") or len(spells) == 1 else clean_name(sc["name"])
                    s.setdefault("limited_uses", {})[resource] = count
                    s.setdefault("spell_resources", {})[sn] = resource
        if sc.get("recharge") and any(sn not in golden for sn in s["unsupported_spells"]): note(f"{sc['name']}: spell outside golden set, recharge declaration is not executable until that spell is supplied.")
    if s["unsupported_spells"]:
        s["unsupported_spells"] = sorted(set(s["unsupported_spells"]))
        note("Spellcasting outside golden set: " + ", ".join(s["unsupported_spells"]) + ". No substitute effects or invented slots.")
    if name in {"Mage", "Imp", "Quasit"} and "Invisibility" not in golden: note("Invisibility: Invisible condition is from a spell outside the golden set; unsupported.")
    if name == "Mage Apprentice" and not {"Ice Knife", "Thunderwave"} <= golden.keys(): note("Ice Knife: Piercing/Cold damage and Dexterity save; Thunderwave: Constitution save, all outside the golden set and unsupported.")
    if name == "Stone Golem" and "Slow" not in golden: note("Slow: Wisdom save spell outside golden set; unsupported.")
    if not f: s.pop("features")
    # Explicit entry provenance for every supplemented block (including copied legendary blocks).
    entries = {clean_name(e["name"]): f"{kind}:{e['name']}" for kind in ("action", "trait", "reaction", "bonus") for e in raw.get(kind, [])}
    for kind in ("actions", "traits", "attacks"):
        for ability in s[kind]:
            for block in ability.get("riders", []) if kind == "attacks" else ability.get("effects", []):
                block["source_ref"] = entries[ability["name"]]
    for option in s.get("legendary", {}).get("options", []):
        for block in option.get("effects", []):
            block["source_ref"] = entries["Consume Memories" if option["name"] == "Psychic Drain" else option["name"]]
    return s


def write_sheets():
    raw = source_monsters(); golden = load_spells()
    for name in STEP2:
        sheet = supplement(raw[name], golden)
        (ROOT / "monsters" / (slug(name) + ".yaml")).write_text(yaml.safe_dump(sheet, sort_keys=False, allow_unicode=True), encoding="utf8")
    print(f"Wrote {len(STEP2)} reviewed XMM sheets")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--write", action="store_true")
    args = p.parse_args()
    if args.write: write_sheets()


if __name__ == "__main__": main()
