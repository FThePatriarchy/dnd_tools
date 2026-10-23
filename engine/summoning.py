"""Materialize embedded spell stat blocks as independent, targetable combatants."""
from copy import deepcopy

from .state import Combatant, Effect, compare_deadline


def materialize(combat, instance, declaration):
    choice = declaration["choice"]
    if not declaration.get("_one"):
        selected = instance.choices[choice[1:]] if choice.startswith("$") else choice
        count = declaration.get("count", 1)
        if count == "spell_mod": count = max(0, instance.caster.spell_mod) // declaration.get("form_cost", {}).get(selected, 1)
        count += declaration.get("count_per_slot", 0) * (instance.slot - declaration["base_slot"])
        return [materialize(combat, instance, {**declaration, "_one": True}) for _ in range(count)]
    if choice.startswith("$"): choice = instance.choices[choice[1:]]
    sheet = deepcopy(declaration["forms"][choice])
    caster = instance.caster
    delta = instance.slot - declaration["base_slot"]
    scaling = declaration["per_slot"]
    if declaration.get("creature_type_choice"): sheet["creature_type"] = instance.choices[declaration["creature_type_choice"][1:]]
    sheet["ac"] += delta * scaling["ac"]
    sheet["max_hp"] += delta * scaling["max_hp"]
    if sheet["proficiency_bonus"] == "caster": sheet["proficiency_bonus"] = caster.proficiency_bonus
    for attack in sheet["attacks"]:
        if attack["to_hit"] == "spell_attack": attack["to_hit"] = caster.spell_attack_bonus
        for primitive in attack["effects"]:
            if "damage" in primitive and primitive["damage"].get("add_caster_mod"): primitive["damage"]["bonus"] += caster.spell_mod
            if "damage" in primitive and declaration.get("damage_dice_add"):
                from .dice import add
                primitive["damage"]["dice"] = add(primitive["damage"]["dice"], declaration["damage_dice_add"][choice], delta)
            if "damage" in primitive and primitive["damage"].get("slot_bonus", True): primitive["damage"]["bonus"] += delta * scaling["damage_bonus"]
    def replace_slot(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if v == "summon_slot": obj[k] = instance.slot
                else: replace_slot(v)
        elif isinstance(obj, list):
            for v in obj: replace_slot(v)
    replace_slot(sheet)
    if declaration.get("fly_slot") and instance.slot >= declaration["fly_slot"]: sheet["movement_modes"]["fly"] = sheet["speed"]
    identifier = f"summon_{instance.id}_{len(instance.summoned)}"
    spirit = Combatant.from_sheet(sheet, identifier, caster.team)
    spirit.extra_attack = declaration["fixed_attacks"] if "fixed_attacks" in declaration else instance.slot // declaration["attack_count_divisor"]
    if declaration.get("after_attack_action"):
        spirit.routines = [[spirit.attacks[0]["name"]] * spirit.extra_attack + [declaration["after_attack_action"]]]
    spirit.statuses["summon_rules"] = {**declaration, "form": choice}
    for trait in spirit.traits:
        if trait.get("passive"):
            passive = combat.monster_instance(spirit, trait["name"], trait["effects"]); passive.spec["monster_passive"] = True
    spirit.spell_dc = caster.spell_dc
    spirit.spell_attack_bonus = caster.spell_attack_bonus
    spirit.summoner_id = caster.id
    spirit.summoned_source = instance.id
    instance.summoned.append(spirit)
    combat.combatants.append(spirit)
    combat.record("summon", caster=caster.id, source=instance.id, creature=spirit.id, form=choice, ac=spirit.ac, hp=spirit.hp, attacks=spirit.extra_attack)
    return spirit


def take_summoned_turns(combat, caster):
    # Newly created creatures act after this very turn, never at a new random
    # initiative position. Snapshot permits future nested summons safely.
    for spirit in list(combat.combatants):
        if spirit.summoner_id != caster.id or not spirit.alive: continue
        combat.begin_turn(spirit)
        rules = spirit.statuses.get("summon_rules", {})
        for trait in spirit.traits:
            if trait.get("trigger") == "own_turn_start" and not spirit.has_condition("incapacitated"):
                inst = combat.monster_instance(spirit, trait["name"], trait["effects"])
                for block in inst.spec["effects"]: combat.resolve_block(inst, block, "on_cast", {})
        allowed = combat.policy_for(caster).command_summon(combat, caster, spirit)
        if rules.get("mount") and caster.has_status("mounted"): allowed = False
        if rules.get("command_cost") and not rules.get("ordered"):
            if caster.bonus_action:
                caster.bonus_action -= 1
                for c in combat.combatants:
                    if c.summoned_source == spirit.summoned_source: c.statuses["summon_rules"]["ordered"] = True
            else: allowed = False
        if rules.get("control_hours"):
            parent = combat.instances.get(spirit.summoned_source)
            if parent and compare_deadline(combat.time_rounds, parent.cast_round + rules["control_hours"] * 600) >= 0:
                spirit.team = "uncontrolled"; allowed = False
        if rules.get("object_only"): continue
        if allowed and rules.get("familiar"):
            enemies = combat.enemies(caster)
            if enemies:
                enemy = enemies[0]
                enemy.effects.append(Effect("advantage", {"on": "attack_rolls", "scope": "all", "against": "target", "recipient": "any_attacker", "uses": 1}, 0, "help", ("start_of_turn", spirit.id, spirit.turns_taken + 1), uses=1))
                combat.record("help", actor=spirit.id, target=enemy.id)
        elif allowed:
            combat.policy_for(spirit).take_turn(combat, spirit)
        elif not spirit.has_condition("incapacitated"):
            spirit.action -= 1
            spirit.effects.extend([
                Effect("disadvantage", {"on": "attack_rolls", "scope": "all", "against": "target", "recipient": "any_attacker"}, 0, "dodge", ("start_of_turn", spirit.id, spirit.turns_taken + 1)),
                Effect("advantage", {"on": "saves", "scope": "dex", "against": None}, 0, "dodge", ("start_of_turn", spirit.id, spirit.turns_taken + 1)),
            ])
            combat.record("dodge", actor=spirit.id)
        combat.end_turn(spirit)
