"""Weapon spell effects preserve the chosen weapon instead of inventing its dice."""
from copy import deepcopy
from . import dice
from .state import Effect, SpellInstance


class WeaponSpells:
    def enchanted_attack(self, actor, attack):
        if not any(e.kind == "weapon_enchantment" for e in actor.active_effects): return attack
        result = deepcopy(attack)
        for e in actor.active_effects:
            if e.kind != "weapon_enchantment": continue
            v = dict(e.data)
            if v.get("names") and attack["name"].lower() not in v["names"]: continue
            for tier in v.get("tiers", []):
                if self.instances[e.source].slot >= tier["slot_min"]: v.update(tier)
            for tier in v.get("cantrip_dice", []):
                if actor.level >= tier["level"]: v["dice"] = tier["dice"]
            ability = attack.get("ability", "str" if attack["kind"] == "melee" else "dex")
            delta = actor.spell_mod - actor.mod(ability) if v.get("spell_ability") else 0
            result["to_hit"] += delta + v.get("attack_bonus", 0)
            for p in result["effects"]:
                if "damage" not in p: continue
                p["damage"]["bonus"] = p["damage"].get("bonus", 0) + delta + v.get("damage_bonus", 0)
                if v.get("dice"): p["damage"]["dice"] = v["dice"]
                if v.get("type"): p["damage"]["type"] = self.instances[e.source].choices[v["type"][1:]] if v["type"].startswith("$") else v["type"]
            if v.get("extra_dice"):
                typ = v["extra_type"]
                if typ.startswith("$"): typ = self.instances[e.source].choices[typ[1:]]
                result["effects"].append({"damage": {"dice": v["extra_dice"], "bonus": 0, "type": typ}})
        return result

    def weapon_spell(self, instance, target, value):
        actor = instance.caster
        attacks = [a for a in actor.attacks if not value.get("kind") or a["kind"] == value["kind"]]
        if not attacks: return False
        a = deepcopy(attacks[0])
        if value.get("spell_ability"):
            ability = a.get("ability", "str" if a["kind"] == "melee" else "dex")
            delta = actor.spell_mod - actor.mod(ability)
            a["to_hit"] += delta
            for p in a["effects"]:
                if "damage" in p: p["damage"]["bonus"] = p["damage"].get("bonus", 0) + delta
        if value.get("type"):
            for p in a["effects"]:
                if "damage" in p: p["damage"]["type"] = instance.choices[value["type"][1:]] if value["type"].startswith("$") else value["type"]
        n = sum(actor.level >= level for level in value.get("upgrade_levels", []))
        if n:
            dn, ds, flat = dice.parts(value["upgrade_dice"])
            a["effects"].append({"damage": {"dice": f"{n * dn}d{ds}", "bonus": 0, "type": "radiant"}})
        for _ in range(value["count"]): self.weapon_attack(actor, target, a)
        return True
