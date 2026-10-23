"""Move newly available XPHB spells into XMM source-owned casting lists only."""
from .loader import ROOT, load_spells, read_yaml, load_sheet
from .monster_import import parse_monster, source_monsters, slug
import yaml


def wire():
    known = load_spells()
    raw = source_monsters()
    changed = []
    for path in sorted((ROOT / "monsters").glob("*.yaml")):
        sheet = read_yaml(path)
        available = set(sheet.get("unsupported_spells", [])) & known.keys()
        if not raw[sheet["name"]].get("spellcasting"): continue
        source = parse_monster(raw[sheet["name"]])
        supported = available & set(source.get("spells", []))
        legendary = [o for o in source.get("legendary", {}).get("options", [])
                     if o.get("spell") in known and o["name"] not in {x["name"] for x in sheet.get("legendary", {}).get("options", [])}]
        components = source.get("spell_components", {})
        components_changed = any(sheet.get("spell_components", {}).get(n) != value for n, value in components.items())
        if not supported and not legendary and not components_changed: continue
        if components: sheet.setdefault("spell_components", {}).update(components)
        for option in legendary:
            sheet.setdefault("legendary", {"uses": source["legendary"]["uses"], "options": []})["options"].append(option)
        for name in source.get("spells", []):
            if name not in supported: continue
            if name not in sheet.setdefault("spells", []): sheet["spells"].append(name)
            for key in ("spell_levels", "spell_costs", "spell_resources", "spell_recharge"):
                if name in source.get(key, {}): sheet.setdefault(key, {})[name] = source[key][name]
            resource = source.get("spell_resources", {}).get(name)
            if resource is not None:
                sheet.setdefault("limited_uses", {})[resource] = source["limited_uses"][resource]
        sheet["unsupported_spells"] = [n for n in sheet["unsupported_spells"] if n not in supported]
        notes = []
        for note in sheet.get("unsupported", []):
            if note.startswith(("Spellcasting outside golden set:", "Spellcasting not yet translated:")): continue
            if any(note.startswith(n + ":") for n in supported): continue
            if note.startswith("Ice Knife:") and {"Ice Knife", "Thunderwave"} <= supported: continue
            if "Slow {@recharge" in note and "Slow" in supported: continue
            notes.append(note)
        if sheet["unsupported_spells"]:
            notes.append("Spellcasting not yet translated: " + ", ".join(sheet["unsupported_spells"]) + ". No substitute effects or invented slots.")
        sheet["unsupported"] = notes
        path.write_text(yaml.safe_dump(sheet, sort_keys=False, allow_unicode=True), encoding="utf8")
        load_sheet(path)
        changed.append((sheet["name"], sorted(supported) + [o["name"] for o in legendary]))
    return changed


if __name__ == "__main__":
    for name, spells in wire(): print(name + ": " + ", ".join(spells))
