"""Remaining XPHB summon blocks. Forms are embedded, never runtime imports."""
import re
from copy import deepcopy
from .spell_catalog import sources, base, block, single, area, condition, damage, modify
from .summon_validation import source_stat_blocks


MODERN = {"Summon Aberration": ("Aberrant Spirit", ["beholderkin", "mind flayer", "slaad"]), "Summon Celestial": ("Celestial Spirit", ["avenger", "defender"]), "Summon Construct": ("Construct Spirit", ["clay", "metal", "stone"]), "Summon Dragon": ("Draconic Spirit", ["acid", "cold", "fire", "lightning", "poison"]), "Summon Fey": ("Fey Spirit", ["fuming", "mirthful", "tricksy"]), "Giant Insect": ("Giant Insect", ["centipede", "spider", "wasp"]), "Find Steed": ("Otherworldly Steed", ["celestial", "fey", "fiend"])}


def action(name, effects, cost="action", **kw): return dict(name=name, cost=cost, effects=effects, **kw)


def modern():
    result=[]
    for name, (creature, forms) in MODERN.items():
        r = source_stat_blocks()[creature]; s = base(sources()[name]); level=s["level"]; sheets={}
        for form in forms:
            hp = int(re.match(r"\d+", r["hp"]["special"])[0]); ac = int(re.match(r"\d+", r["ac"][0]["special"])[0])+level
            if name == "Find Steed": hp += 10*level
            if form == "defender": ac += 2
            modes={k:v if isinstance(v,int) else v["number"] for k,v in r["speed"].items() if k != "canHover" and (not isinstance(v,dict) or "Only" not in v.get("condition", "") and "only" not in v.get("condition", "") or form in v.get("condition", "").lower())}
            # Steed flight begins at slot 4, not base slot 2.
            if name == "Find Steed": modes.pop("fly",None)
            sheet=dict(name=creature, source="XPHB", max_hp=hp, ac=ac, abilities={a:r[a] for a in ("str","dex","con","int","wis","cha")}, speed=r["speed"]["walk"], movement_modes=modes, creature_type=form if name=="Find Steed" else r["type"], size=r["size"][0], proficiency_bonus="caster", attacks=[], resistances=r.get("resist",[]), immunities=r.get("immune",[]), condition_immunities=r.get("conditionImmune",[]), features={})
            entries=[a for a in r["action"] if "{@hitYourSpellAttack" in str(a) and ("Only" not in a["name"] or form in a["name"].lower())]
            if form == "spider": entries.sort(key=lambda a: "Web Bolt" not in a["name"])
            for a in entries:
                text=" ".join(a["entries"]); ps=[]
                for m in re.finditer(r"\{@damage (\d+d\d+)(?: \+ (\d+))?( \+ summonSpellLevel)?\}\s*(\w+)?", text):
                    die,bonus,slot,typ=m.groups(); typ=(typ or "").lower()
                    if typ not in {"slashing","piercing","bludgeoning","fire","poison","force","psychic","radiant","necrotic"}: typ={"celestial":"radiant","fey":"psychic","fiend":"necrotic"}.get(form,"piercing")
                    ps.append(damage(die,typ,bonus=int(bonus or 0)+(level if slot else 0),slot_bonus=bool(slot)))
                attack=dict(name=a["name"],kind="ranged" if "{@atkr r}" in text else "melee",to_hit="spell_attack",reach_ft=int(re.search(r"reach (\d+) (?:ft|feet)",text)[1]) if "reach" in text else 0,effects=ps)
                if "range" in text: attack["range_ft"]=int(re.search(r"range (\d+) ft",text)[1])
                if "can't regain" in text: ps.append({"status":{"id":"healing_blocked","data":{}},"until":"start_of_turn(caster.next_turn)"})
                if "Speed is reduced to 0" in text: ps.append({**modify("speed",0,"set"),"until":"start_of_turn(caster.next_turn)"})
                if form=="defender": attack["on_hit_self"]=[{"temp_hp":{"dice":"1d10"}}]
                sheet["attacks"].append(attack)
            if form=="slaad": sheet["features"]["regeneration"]={"amount":5,"blocked_by":[],"at_zero":False}
            if form=="mind flayer": sheet["traits"]=[action("Whispering Aura",[block(target={**area("emanation",5),"exclude":"summoner"},save="wis",effects=[damage("2d6","psychic")])],"free",trigger="own_turn_start")]
            if form=="centipede": sheet["actions"]=[action("Venomous Spew",[block(save="con",effects=[{**condition("poisoned"),"until":"start_of_turn(caster.next_turn)"}])],"bonus_action")]
            if name=="Summon Celestial" or form=="celestial":
                sheet.setdefault("actions",[]).append(action("Healing Touch",[block(effects=[{"heal":{"dice":"2d8","bonus":"summon_slot"}}])],"action" if name=="Summon Celestial" else "bonus_action",resource="Healing Touch"));sheet["limited_uses"]={"Healing Touch":1}
            if form=="fiend":
                sheet["actions"]=[action("Fell Glare",[block(save="wis",effects=[{**condition("frightened"),"until":"end_of_turn(caster.next_turn)"}])],"bonus_action",resource="Fell Glare")];sheet["limited_uses"]={"Fell Glare":1}
            if name=="Summon Dragon":
                sheet["actions"]=[action("Breath Weapon",[block(target={**area("cone",30),"origin":"caster"},save="dex",half=True,effects=[damage("2d6",form,slot_bonus=False)])],"free")]
            if form=="fuming": sheet["actions"]=[action("Fey Step",[block(target={"select":"self"},effects=[{"advantage":{"on":"attack_rolls","scope":"all","against":None,"uses":1},"until":"end_of_turn(caster.this_turn)"}])],"bonus_action")]
            if form=="mirthful": sheet["actions"]=[action("Fey Step",[block(save="wis",effects=[{**condition("charmed",ends_on_damage="any"),"duration":{"type":"minutes","n":1}}])],"bonus_action")]
            if form=="stone": sheet["traits"]=[action("Stony Lethargy",[block(target=area("emanation",10),save="wis",effects=[{**modify("speed",.5,"mul"),"until":"start_of_turn(target.next_turn)"},{"status":{"id":"no_opportunity_attacks","data":{}},"until":"start_of_turn(target.next_turn)"}])],"free",trigger="creature_turn_start")]
            if form=="metal": sheet["traits"]=[action("Heated Body",[block(target={"select":"ref","ref":"trigger.attacker"},event="on_attack_hit(any, caster)",effects=[damage("1d10","fire",slot_bonus=False)],**{"if":"attack.melee"})],"free",passive=True)]
            if form=="clay": sheet["traits"]=[action("Berserk Lashing",[block(target={"select":"ref","ref":"trigger.attacker"},event="on_damaged(caster)",cost="reaction",effects=[{"weapon_strike":{"count":1,"kind":"melee"}}])],"free",passive=True)]
            sheets[form]=sheet
        s["choices"]=[{"id":"form","options":forms,"when":"on_cast"}]
        hp_inc=int(re.search(r"(?:\+ |^)(\d+) (?:for each spell level above|per spell level)",r["hp"]["special"])[1])
        declaration=dict(choice="$form",forms=sheets,base_slot=level,per_slot={"ac":1,"max_hp":hp_inc,"damage_bonus":1},attack_count_divisor=2)
        if name=="Find Steed": declaration.pop("attack_count_divisor"); declaration.update(fixed_attacks=1,persistent=True,mount=True,fly_slot=4)
        if name=="Summon Dragon": declaration["after_attack_action"]="Breath Weapon"
        s["effects"]=[block(target={"select":"self"},effects=[{"summon":declaration}])]
        if name=="Summon Dragon": s["effects"][0]["apply"].append({"defense":{"resistance":["$form"]}})
        s["unsupported"]=["Unoccupied placement, ranges, languages, senses and movement need geometry/environment. Summoned creatures are real targetable combatants immediately after the caster. The printed parent stat blocks, not contradictory generated versions, determine statistics."]
        if name=="Find Steed": s["recast_ends_previous"]=True;s["unsupported"].append("Mounted movement and Life Bond's five-foot proximity need explicit mounted/proximity state. When mounted, the controlled steed Dodges rather than attacks; independent protection acts after caster. Fey teleport requires positions.")
        if name=="Summon Fey": s["unsupported"].append("Fey Step teleport and Tricksy Darkness are spatial. Mirthful Charmed source is the spirit; joint caster/spirit social allegiance needs external adjudication.")
        if name=="Summon Construct": s["unsupported"].append("Heated Body's grapple-start branch and Berserk Lashing's fallback movement need reach/grapple positions. On-damage Clay reaction attacks execute.")
        result.append(s)
    return result


def fixed_sheet(name, no_attacks=False):
    from .monster_import import source_monsters, parse_monster
    r=source_monsters()[name]
    if not no_attacks:
        sheet=parse_monster(r)
        for k in ("hp_formula","initiative_bonus","save_bonuses","save_proficiencies","cr","alignment","unsupported","multiattack","actions","traits"): sheet.pop(k,None)
        sheet["size"]=r["size"][0]
        return sheet
    return dict(name=name,source="XMM",max_hp=r["hp"]["average"],ac=r["ac"][0] if isinstance(r["ac"][0],int) else r["ac"][0]["ac"],abilities={a:r[a] for a in ("str","dex","con","int","wis","cha")},speed=r["speed"].get("walk",0),movement_modes={k:v for k,v in r["speed"].items() if type(v)==int},creature_type="beast",size=r["size"][0],proficiency_bonus=2,attacks=[])


def others():
    out=[]; raw=sources()
    s=base(raw["Animate Dead"]); forms={n.lower():fixed_sheet(n) for n in ("Skeleton","Zombie")}
    s["choices"]=[{"id":"form","options":list(forms),"when":"on_cast"}]
    s["effects"]=[block(target={"select":"self"},effects=[{"summon":dict(choice="$form",forms=forms,base_slot=3,per_slot={"ac":0,"max_hp":0,"damage_bonus":0},fixed_attacks=1,count=1,count_per_slot=2,persistent=True,command_cost="bonus_action",control_hours=24)}])]
    s["unsupported"]=["Caller supplies distinct eligible Small/Medium Humanoid corpses or bones; no corpse inventory is invented. Reasserting control over four existing Undead requires explicit existing-corpse/control identities. Created bodies persist; one Bonus Action issues a continuing attack order, and loss of control occurs at 24 hours."]
    out.append(s)
    s=base(raw["Find Familiar"]);forms={n.lower():fixed_sheet(n,True) for n in ("Bat","Cat","Frog","Hawk","Lizard","Octopus","Owl","Rat","Raven","Spider","Weasel")}
    s["choices"]=[{"id":"form","options":list(forms),"when":"on_cast"},{"id":"type","options":["celestial","fey","fiend"],"when":"on_cast"}];s["recast_ends_previous"]=True
    s["effects"]=[block(target={"select":"self"},effects=[{"summon":dict(choice="$form",forms=forms,base_slot=1,per_slot={"ac":0,"max_hp":0,"damage_bonus":0},fixed_attacks=1,persistent=True,familiar=True,creature_type_choice="$type")}])]
    s["unsupported"]=["Per task convention familiar acts after caster rather than its printed independent initiative. It cannot attack; Help executes. Touch-spell delivery range/reaction, remote senses, pocket-dimension placement, carried inventory and other CR-0 Beast forms need additional explicit choices/environment."];out.append(s)
    s=base(raw["Phantom Steed"]);sheet=fixed_sheet("Riding Horse");sheet["speed"]=100;sheet["movement_modes"]["walk"]=100
    s["choices"]=[{"id":"form","options":["horse"],"when":"on_cast"}]
    s["effects"]=[block(target={"select":"self"},effects=[{"summon":dict(choice="$form",forms={"horse":sheet},base_slot=3,per_slot={"ac":0,"max_hp":0,"damage_bonus":0},fixed_attacks=1,ends_on_damage=True,mount=True)}])]
    s["unsupported"]=["Equipment distance, mounted movement, travel and the one-minute dismount grace require positions/rider state. Any damage ends combat utility immediately; the horse is targetable and does not ignore hits."];out.append(s)
    s=base(raw["Animate Objects"]);r=source_stat_blocks()["Animated Object"]; forms={}
    for form,hp,die in [("medium",10,"1d4"),("large",20,"2d6"),("huge",40,"2d12")]:
        forms[form]=dict(name="Animated Object",source="XPHB",max_hp=hp,ac=15,abilities={a:r[a] for a in ("str","dex","con","int","wis","cha")},speed=30,movement_modes={"walk":30},creature_type="construct",size={"medium":"M","large":"L","huge":"H"}[form],proficiency_bonus="caster",attacks=[dict(name="Slam",kind="melee",to_hit="spell_attack",reach_ft=5,effects=[damage(die,"force",bonus=3,add_caster_mod=True)])])
    s["choices"]=[{"id":"form","options":list(forms),"when":"on_cast"}]
    s["effects"]=[block(target={"select":"self"},effects=[{"summon":dict(choice="$form",forms=forms,base_slot=5,per_slot={"ac":0,"max_hp":0,"damage_bonus":0},fixed_attacks=1,count="spell_mod",form_cost={"medium":1,"large":2,"huge":3},damage_dice_add={"medium":"1d4","large":"1d6","huge":"1d12"},command_cost="bonus_action")}])]
    s["unsupported"]=["Caller supplies eligible loose nonmagical non-Gargantuan objects. A homogeneous selected size is supported with exact weighted count; mixed-size inventories require explicit object selections. The printed Animated Object Slam deals Force, not the obsolete Bludgeoning/Piercing/Slashing spell tags. Object-form overflow after reversion, legs/placement and 500-foot commands need object/geometry state."];out.append(s)
    s=base(raw["Polymorph"]);forms={n.lower():fixed_sheet(n) for n in ("Wolf","Brown Bear","Riding Horse")}
    from .step2 import supplement
    from .monster_import import source_monsters
    for n in ("wolf", "brown bear"):
        forms[n] = supplement(source_monsters()[forms[n]["name"]], {})
        for key in ("hp_formula", "initiative_bonus", "spells", "unsupported_spells"):
            forms[n].pop(key, None)
    for n,sh in forms.items(): sh["cr"]=str(__import__("engine.monster_import",fromlist=["source_monsters"]).source_monsters()[sh["name"]]["cr"])
    s["choices"]=[{"id":"form","options":list(forms),"when":"on_cast"}]
    s["effects"]=[block(target=single("visible"),save="wis",effects=[{"transform":{"choice":"$form","forms":forms}}])]
    s["unsupported"]=["Embedded Beast choices are Wolf, Brown Bear and Riding Horse; other Beast forms need a reviewed stat block, not invented statistics. Anatomy/equipment/speech, movement and gear merging require inventory/geometry. CR eligibility, replaced statistics, retained HP/type, form Temporary HP and reversion execute."];out.append(s)
    s=base(raw["Bigby's Hand"]);s["choices"]=[{"id":"mode","options":["fist","grasp","crush"],"when":"on_cast"}]
    s["effects"]=[block("hand",target={"select":"self"},effects=[{"force_object":{"ac":20,"hp":"caster_max_hp"}}]),block("fist",event="on_cast or bonus_action_command",attack="melee_spell",effects=[damage("5d8","force")],**{"if":'$mode == "fist"'}),block("grasp",target={**single(),"max_size":"H"},event="on_cast or bonus_action_command",save="dex",effects=[condition("grappled",escape_dc="spell_dc",capacity=1)],**{"if":'$mode == "grasp"'}),block("crush",target={**single(),"eligible_if":"target.has_condition_from(grappled, spell)"},event="bonus_action_command",effects=[damage("4d6","bludgeoning",bonus="spell_mod")],**{"if":'$mode == "crush"', "requires_condition": "grappled"})]
    s["unsupported"]=["Clenched Fist/Grasping Hand are chosen commands, not autonomous creature turns. Forceful Hand's Strength-save push, interposing Half Cover, Difficult Terrain and movement/reach require positions. Object has real AC/HP; its destruction ends the spell."];out.append(s)
    return out
