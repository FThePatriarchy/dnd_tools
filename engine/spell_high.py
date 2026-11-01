"""Reviewed no-grid translations of level 6-9 XPHB combat spells.

    python -m engine.spell_high      # writes any missing spell files

Only spells a level 11-20 party or monster would cast in a fight are here.
Spells whose effect needs a map, a long casting time or free-form adjudication
(Wish, Time Stop, True Polymorph, Shapechange, Simulacrum, Imprisonment,
Contingency, Heroes' Feast, the walls) stay missing rather than half-working.
"""
from .spell_catalog import sources, base, block, single, multi, area, damage, modify, condition, scale, write_spell


def repeat(ability):
    return {"ability": ability, "timing": "end_of_turn", "on_success": "end"}


def enemies(target):
    return {**target, "affects": "enemy"}


def spells():
    raw = sources()
    out = []

    def add(name, effects, *, unsupported=(), dice=None, targets=None, block_id="main", **extra):
        s = base(raw[name])
        s["effects"] = effects
        s["unsupported"] = list(unsupported)
        if dice or targets: scale(s, block=block_id, dice=dice, targets=targets)
        s.update(extra)
        out.append(s)
        return s

    # Level 6
    add("Chain Lightning", [block(target=multi(4, "visible"), save="dex", half=True, effects=[damage("10d8", "lightning")])],
        targets=1, unsupported=["The leaping bolts are assumed to find targets close enough to the first one; objects are not targeted."])
    add("Circle of Death", [block(target=area("sphere", 60), save="con", half=True, effects=[damage("8d8", "necrotic")])], dice="2d8")
    add("Disintegrate", [block(target=single("visible"), save="dex", effects=[damage("10d6", "force", bonus=40)])], dice="3d6",
        unsupported=["A creature reduced to zero Hit Points by this damage is disintegrated; in the arena it is simply out of the fight. Objects and walls of force are not modeled."])
    add("Harm", [block(target=single("visible"), save="con", half=True, effects=[damage("14d6", "necrotic")])],
        unsupported=["The Hit Point maximum reduction on a failed save is not modeled."])
    add("Heal", [block(target=single("visible"), effects=[{"heal": {"amount": 70}}, *({"remove_condition": {"condition": c}} for c in ("blinded", "deafened", "poisoned"))])],
        unsupported=["The extra healing from a higher spell slot is not modeled."])
    add("Otiluke's Freezing Sphere", [block(target=area("sphere", 60), save="con", half=True, effects=[damage("10d6", "cold")])], dice="1d6",
        unsupported=["Freezing water and holding the globe to throw later are not modeled."])
    sunbeam = block(target=area("line", 60), save="con", half=True, effects=[damage("6d8", "radiant"), {**condition("blinded"), "until": "start_of_turn(caster.next_turn)"}],
                    event="on_cast or action_command")
    sunbeam["if"] = "event == on_cast or turn.index > spell.cast_turn"
    sunbeam["optional"] = True
    add("Sunbeam", [sunbeam], unsupported=["Bright light and the Oozes' save Disadvantage are not modeled."])
    stone = block(target=single("visible"), save="con", effects=[condition("restrained", repeat_save=repeat("con"))])
    stone["save"]["auto_success_if"] = "target.creature_type == construct"
    stone["on_success"] = [modify("speed", 0, "set", until="start_of_turn(caster.next_turn)")]
    add("Flesh to Stone", [stone],
        unsupported=["Becoming Petrified after repeated failed saves is not modeled: the target stays Restrained until it saves."])
    dance = block(target=single("visible"), save="wis", effects=[condition("charmed", repeat_save=repeat("wis")),
        {"disadvantage": {"on": "saves", "scope": "dex", "against": None}, "requires_condition": "charmed"},
        {"disadvantage": {"on": "attack_rolls", "scope": "all", "against": None}, "requires_condition": "charmed"},
        {"advantage": {"on": "attack_rolls", "scope": "all", "against": "target", "recipient": "any_attacker"}, "requires_condition": "charmed"}])
    add("Otto's Irresistible Dance", [dance],
        unsupported=["The dance on a successful save only costs movement, which is not simulated; the repeat save is made at the end of each turn instead of with an action."])
    # Level 7
    add("Finger of Death", [block(target=single("visible"), save="con", half=True, effects=[damage("7d8", "necrotic", bonus=30)])],
        unsupported=["A Humanoid killed by the spell rising as a Zombie is not modeled."])
    add("Fire Storm", [block(target=area("cube", 30), save="dex", half=True, effects=[damage("7d10", "fire")])],
        unsupported=["The contiguous cubes are approximated by one cube of the same total area. Igniting objects is not modeled."])
    add("Delayed Blast Fireball", [block(target=area("sphere", 20), save="dex", half=True, effects=[damage("12d6", "fire")])], dice="1d6",
        unsupported=["The bead is assumed to explode at once; holding it for extra damage, and throwing it, are not modeled."])
    word = block(target={"select": "n_targets", "n": "all", "distinct": True, "up_to": True, "filter": ["creature"], "affects": "enemy"}, save="cha", effects=[
        {"kill": {}, "if": "target.hp <= 20"},
        {**condition("stunned"), "if": "target.hp > 20 and target.hp <= 30"},
        {**condition("blinded"), "if": "target.hp > 20 and target.hp <= 40"},
        {**condition("deafened"), "if": "target.hp > 20 and target.hp <= 50"},
        {"remove_from_combat": {"until": "spell_ends", "returns": "false"}, "if": "target.creature_type in [celestial, elemental, fey, fiend]"}])
    add("Divine Word", [word],
        unsupported=["The condition durations from the effects table are not tracked: conditions last for the fight."])
    add("Power Word Fortify", [block(target=multi(6, "visible"), effects=[{"temp_hp": {"amount": 20}}])],
        unsupported=["The Temporary Hit Points are split evenly among the six recipients."])
    regen = block(target=single(), effects=[{"heal": {"dice": "4d8", "bonus": 15}}])
    tick = block("regrow", {"select": "ref", "ref": "main"}, effects=[{"heal": {"amount": 1}}], event="start_of_turn(target)")
    add("Regenerate", [regen, tick], unsupported=["Regrowing severed body parts is not modeled."])
    sword = block("sword", target={"select": "single", "filter": ["creature"], "affects": "any"}, attack="melee_spell",
                  effects=[damage("4d12", "force", bonus="spell_mod")], event="on_cast or bonus_action_command")
    sword["if"] = "event == on_cast or turn.index > spell.cast_turn"
    sword["optional"] = True
    add("Mordenkainen's Sword", [sword], unsupported=["Moving the sword is not simulated; the target is assumed to be in reach."])
    # Level 8
    burst = block(target=area("sphere", 60), save="con", half=True, effects=[damage("12d6", "radiant"), condition("blinded", repeat_save=repeat("con"))])
    add("Sunburst", [burst], unsupported=["Dispelling magical Darkness is not modeled."])
    add("Power Word Stun", [block(target=single("visible"), effects=[
        {**condition("stunned", repeat_save=repeat("con")), "if": "target.hp <= 150"},
        {**modify("speed", 0, "set", until="start_of_turn(caster.next_turn)"), "if": "target.hp > 150"}])])
    dominate = block(target=multi(1, "visible"), save="wis", effects=[condition("charmed", control=True, repeat_on_damage=True)])
    dominate["save"]["advantage_if"] = "target.team != caster.team"
    add("Dominate Monster", [dominate], unsupported=["Telepathic commands outside the fight and the longer duration from a higher slot are not modeled."])
    aura = block(target={"select": "n_targets", "n": "all", "distinct": True, "up_to": True, "filter": ["creature"], "affects": "ally", "within_ft": 30}, effects=[
        {"advantage": {"on": "saves", "scope": "all", "against": None}},
        {"disadvantage": {"on": "attack_rolls", "scope": "all", "against": "target", "recipient": "any_attacker"}}])
    add("Holy Aura", [aura], unsupported=["The Constitution save that leaves a Fiend or Undead attacker Blinded is not modeled; creatures that move out of the aura keep its benefit."])
    befuddle = block(target=single("visible"), save="int", half=True, effects=[damage("10d12", "psychic"), {"turn_rules": {"no_spells": True}}])
    add("Befuddlement", [befuddle], unsupported=["The monthly repeat save is not tracked: a failed save stops spellcasting for the fight."])
    add("Mind Blank", [block(target=single("willing"), effects=[{"defense": {"immunity": ["psychic"], "condition_immunity": ["charmed"]}}])],
        unsupported=["Protection from divination and mind reading is outside combat."])
    # Level 9
    add("Meteor Swarm", [block(target=area("sphere", 40), save="dex", half=True, effects=[damage("20d6", "fire"), damage("20d6", "bludgeoning")])],
        unsupported=["The four spheres are approximated by one; a creature is affected only once either way. Igniting objects is not modeled."])
    add("Power Word Kill", [block(target=single("visible"), effects=[{"kill": {}, "if": "target.hp <= 100"}, {**damage("12d12", "psychic"), "if": "target.hp > 100"}])])
    add("Power Word Heal", [block(target=single("visible"), effects=[{"heal": {"amount": "full"}},
        *({"remove_condition": {"condition": c}} for c in ("charmed", "frightened", "paralyzed", "poisoned", "stunned"))])],
        unsupported=["Standing up from Prone with a Reaction is not modeled."])
    add("Mass Heal", [block(target={"select": "n_targets", "n": "all", "distinct": True, "up_to": True, "filter": ["creature", "visible"], "affects": "ally"},
                            effects=[{"heal_pool": {"amount": 700, "cap": "full"}}, *({"remove_condition": {"condition": c}} for c in ("blinded", "deafened", "poisoned"))])])
    weird = block(target=enemies(area("sphere", 30)), save="wis", half=True, effects=[damage("10d10", "psychic"), condition("frightened", repeat_save=repeat("wis"))])
    add("Weird", [weird], unsupported=["The psychic damage on each failed repeat save is not modeled."])
    add("Foresight", [block(target=single("willing"), effects=[
        {"advantage": {"on": "attack_rolls", "scope": "all", "against": None}},
        {"advantage": {"on": "saves", "scope": "all", "against": None}},
        {"advantage": {"on": "ability_checks", "scope": "all", "against": None}},
        {"disadvantage": {"on": "attack_rolls", "scope": "all", "against": "target", "recipient": "any_attacker"}}])])
    return out


def main():
    print("New spells:", sum(write_spell(s) for s in spells()))


if __name__ == "__main__":
    main()
