"""Single-class XPHB character builder, with strict choices and computed math."""
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
import re

from .classes import load_class, substitute, SUBCLASSES
from .class_source import source
from .loader import ROOT, Validator, ValidationError, load_spells, read_yaml
from .sheets import validate_sheet

# XPHB class membership, transcribed from archive data/spells/sources.json.
SPELL_LISTS = {
    'wizard': set("Acid Splash; Alarm; Alter Self; Animate Dead; Animate Objects; Antimagic Field; Antipathy/Sympathy; Arcane Eye; Arcane Gate; Arcane Lock; Arcane Vigor; Astral Projection; Augury; Banishment; Befuddlement; Bestow Curse; Bigby's Hand; Blade Ward; Blight; Blindness/Deafness; Blink; Blur; Burning Hands; Chain Lightning; Charm Monster; Charm Person; Chill Touch; Chromatic Orb; Circle of Death; Circle of Power; Clairvoyance; Clone; Cloud of Daggers; Cloudkill; Color Spray; Comprehend Languages; Cone of Cold; Confusion; Conjure Elemental; Conjure Minor Elementals; Contact Other Plane; Contingency; Continual Flame; Control Water; Control Weather; Counterspell; Create Undead; Creation; Crown of Madness; Dancing Lights; Darkness; Darkvision; Delayed Blast Fireball; Demiplane; Detect Magic; Detect Thoughts; Dimension Door; Disguise Self; Disintegrate; Dispel Magic; Divination; Dominate Monster; Dominate Person; Dragon's Breath; Drawmij's Instant Summons; Dream; Elementalism; Enhance Ability; Enlarge/Reduce; Etherealness; Evard's Black Tentacles; Expeditious Retreat; Eyebite; Fabricate; False Life; Fear; Feather Fall; Feign Death; Find Familiar; Finger of Death; Fire Bolt; Fire Shield; Fireball; Flaming Sphere; Flesh to Stone; Fly; Fog Cloud; Forcecage; Foresight; Friends; Gaseous Form; Gate; Geas; Gentle Repose; Globe of Invulnerability; Glyph of Warding; Grease; Greater Invisibility; Guards and Wards; Gust of Wind; Hallucinatory Terrain; Haste; Hold Monster; Hold Person; Hypnotic Pattern; Ice Knife; Ice Storm; Identify; Illusory Script; Imprisonment; Incendiary Cloud; Invisibility; Jallarzi's Storm of Radiance; Jump; Knock; Legend Lore; Leomund's Secret Chest; Leomund's Tiny Hut; Levitate; Light; Lightning Bolt; Locate Creature; Locate Object; Longstrider; Mage Armor; Mage Hand; Magic Circle; Magic Jar; Magic Missile; Magic Mouth; Magic Weapon; Major Image; Mass Suggestion; Maze; Melf's Acid Arrow; Mending; Message; Meteor Swarm; Mind Blank; Mind Sliver; Mind Spike; Minor Illusion; Mirage Arcane; Mirror Image; Mislead; Misty Step; Modify Memory; Mordenkainen's Faithful Hound; Mordenkainen's Magnificent Mansion; Mordenkainen's Private Sanctum; Mordenkainen's Sword; Move Earth; Nondetection; Nystul's Magic Aura; Otiluke's Freezing Sphere; Otiluke's Resilient Sphere; Otto's Irresistible Dance; Passwall; Phantasmal Force; Phantasmal Killer; Phantom Steed; Planar Binding; Plane Shift; Poison Spray; Polymorph; Power Word Kill; Power Word Stun; Prestidigitation; Prismatic Spray; Prismatic Wall; Programmed Illusion; Project Image; Protection from Energy; Protection from Evil and Good; Rary's Telepathic Bond; Ray of Enfeeblement; Ray of Frost; Ray of Sickness; Remove Curse; Reverse Gravity; Rope Trick; Scorching Ray; Scrying; See Invisibility; Seeming; Sending; Sequester; Shapechange; Shatter; Shield; Shocking Grasp; Silent Image; Simulacrum; Sleep; Sleet Storm; Slow; Speak with Dead; Spider Climb; Steel Wind Strike; Stinking Cloud; Stone Shape; Stoneskin; Suggestion; Summon Aberration; Summon Construct; Summon Dragon; Summon Elemental; Summon Fey; Summon Fiend; Summon Undead; Sunbeam; Sunburst; Symbol; Synaptic Static; Tasha's Bubbling Cauldron; Tasha's Hideous Laughter; Telekinesis; Telepathy; Teleport; Teleportation Circle; Tenser's Floating Disk; Thunderclap; Thunderwave; Time Stop; Toll the Dead; Tongues; True Polymorph; True Seeing; True Strike; Unseen Servant; Vampiric Touch; Vitriolic Sphere; Wall of Fire; Wall of Force; Wall of Ice; Wall of Stone; Water Breathing; Web; Weird; Wish; Witch Bolt; Yolande's Regal Presence".split("; ")),
    'cleric': set("Aid; Animate Dead; Antimagic Field; Astral Projection; Augury; Aura of Life; Aura of Purity; Aura of Vitality; Bane; Banishment; Beacon of Hope; Bestow Curse; Blade Barrier; Bless; Blindness/Deafness; Calm Emotions; Circle of Power; Clairvoyance; Command; Commune; Conjure Celestial; Contagion; Continual Flame; Control Water; Control Weather; Create Food and Water; Create Undead; Create or Destroy Water; Cure Wounds; Daylight; Death Ward; Detect Evil and Good; Detect Magic; Detect Poison and Disease; Dispel Evil and Good; Dispel Magic; Divination; Divine Word; Earthquake; Enhance Ability; Etherealness; Feign Death; Find Traps; Find the Path; Fire Storm; Flame Strike; Forbiddance; Freedom of Movement; Gate; Geas; Gentle Repose; Glyph of Warding; Greater Restoration; Guardian of Faith; Guidance; Guiding Bolt; Hallow; Harm; Heal; Healing Word; Heroes' Feast; Hold Person; Holy Aura; Inflict Wounds; Insect Plague; Legend Lore; Lesser Restoration; Light; Locate Creature; Locate Object; Magic Circle; Mass Cure Wounds; Mass Heal; Mass Healing Word; Meld into Stone; Mending; Planar Ally; Planar Binding; Plane Shift; Power Word Fortify; Power Word Heal; Prayer of Healing; Protection from Energy; Protection from Evil and Good; Protection from Poison; Purify Food and Drink; Raise Dead; Regenerate; Remove Curse; Resistance; Resurrection; Revivify; Sacred Flame; Sanctuary; Scrying; Sending; Shield of Faith; Silence; Spare the Dying; Speak with Dead; Spirit Guardians; Spiritual Weapon; Stone Shape; Summon Celestial; Sunbeam; Sunburst; Symbol; Thaumaturgy; Toll the Dead; Tongues; True Resurrection; True Seeing; Warding Bond; Water Walk; Word of Radiance; Word of Recall; Zone of Truth".split("; ")),
}
PRIORITY = {
    "wizard": ["Fireball", "Shield", "Mage Armor", "Magic Missile", "Counterspell", "Scorching Ray", "Thunderwave", "Mirror Image", "Misty Step", "Haste", "Web", "Cone of Cold", "Ice Storm", "Wall of Fire", "Fire Shield", "Slow", "Sleep", "Chromatic Orb", "Burning Hands", "Lightning Bolt"],
    "cleric": ["Spirit Guardians", "Healing Word", "Guiding Bolt", "Spiritual Weapon", "Hold Person", "Shield of Faith", "Bless", "Cure Wounds", "Aid", "Lesser Restoration", "Mass Healing Word", "Bane", "Sanctuary", "Command", "Inflict Wounds", "Silence", "Warding Bond", "Death Ward", "Mass Cure Wounds", "Flame Strike"],
}
CANTRIPS = {"wizard": ["Fire Bolt", "Ray of Frost", "Toll the Dead", "Shocking Grasp", "Acid Splash"],
            "cleric": ["Sacred Flame", "Toll the Dead", "Guidance", "Word of Radiance", "Resistance", "Thaumaturgy"]}
ABILITIES = ("str", "dex", "con", "int", "wis", "cha")
DEFAULT_ABILITIES = {
    "fighter": dict(zip(ABILITIES, [15,12,14,10,13,8])),
    "rogue": dict(zip(ABILITIES, [8,15,14,12,13,10])),
    "wizard": dict(zip(ABILITIES, [8,14,13,15,12,10])),
    "cleric": dict(zip(ABILITIES, [13,10,14,12,15,8])),
}
SKILLS = {"fighter": ["athletics", "perception"], "rogue": ["stealth", "sleight of hand", "perception", "investigation"],
          "wizard": ["arcana", "history"], "cleric": ["religion", "insight"]}
WEAPONS = {
    "greatsword": ("2d6", "slashing", "melee", "graze", ["two_handed"]),
    "longsword": ("1d8", "slashing", "melee", "sap", ["versatile"]),
    "rapier": ("1d8", "piercing", "melee", "vex", ["finesse"]),
    "shortbow": ("1d6", "piercing", "ranged", "vex", ["two_handed"]),
    "longbow": ("1d8", "piercing", "ranged", "slow", ["two_handed"]),
    "mace": ("1d6", "bludgeoning", "melee", "sap", []),
    "quarterstaff": ("1d6", "bludgeoning", "melee", "topple", ["versatile"]),
}
EQUIPMENT = {
    "chain_greatsword": ("chain", False, ["greatsword"]),
    "chain_sword_shield": ("chain", True, ["longsword"]),
    "leather_archer": ("studded", False, ["longbow"]),
    "studded_rapier": ("studded", False, ["rapier", "shortbow"]),
    "studded_shortbow": ("studded", False, ["shortbow", "rapier"]),
    "unarmored_staff": ("none", False, ["quarterstaff"]),
    "chain_shield": ("chain", True, ["mace"]),
    "scale_shield": ("scale", True, ["mace"]),
}
DEFAULT_EQUIPMENT = dict(zip(SUBCLASSES, ("chain_greatsword", "studded_rapier", "unarmored_staff", "chain_shield")))
STYLES = {"defense", "archery", "dueling", "great_weapon_fighting"}


@lru_cache(None)
def _spells(): return load_spells()


@lru_cache(None)
def _class(name): return load_class(name)


@lru_cache(None)
def spell_options(name, level):
    spells = _spells()
    cap = (level + 1)//2
    return {n: spells[n] for n in SPELL_LISTS.get(name, ()) if n in spells and spells[n]["level"] <= cap}


def spell_order(name, options):
    return [n for n in PRIORITY[name] if n in options] + sorted(set(options) - set(PRIORITY[name]))


def default_asis(name, level, abilities):
    c = _class(name); result={}; scores=abilities.copy()
    primary = {"fighter":"str", "rogue":"dex", "wizard":"int", "cleric":"wis"}[name]
    for n in c["asi_levels"]:
        if n > level: continue
        add={}
        for _ in range(2):
            ability=next((a for a in [primary,"con",*ABILITIES] if scores[a]<20), None)
            if ability is None: raise ValidationError("<build>:choices.asis: no uncapped ability can receive an ASI")
            scores[ability]+=1; add[ability]=add.get(ability,0)+1
        result[n]=add
    return result


def default_book(level, options):
    book=[]
    for at in range(1,level+1):
        eligible = {n:v for n,v in options.items() if 0 < v["level"] <= (at+1)//2}
        for n in [n for n in spell_order("wizard", eligible) if n not in book][:6 if at==1 else 2]: book.append(n)
        if at==3:
            book += [n for n in spell_order("wizard",eligible) if n not in book and eligible[n]["school"]=="evocation"][:2]
        elif at in {5,7,9}:
            book += [n for n in spell_order("wizard",eligible) if n not in book and eligible[n]["school"]=="evocation"][:1]
    return book


def validate_book(book, level, options, v):
    # A small bipartite matching verifies acquisition timing, including the
    # Evocation-only free slots, rather than merely counting the final book.
    slots=[]
    for at in range(1,level+1):
        slots.extend([((at+1)//2,False)]*(6 if at==1 else 2))
        if at==3: slots.extend([(2,True)]*2)
        elif at in {5,7,9}: slots.append(((at+1)//2,True))
    v.check(len(book)==len(slots),"choices.spellbook","wrong learned/Savant spell count; purchased copies are out of scope")
    owners={}
    def place(name,seen):
        for i,(cap,evocation) in enumerate(slots):
            if i in seen or options[name]["level"]>cap or evocation and options[name]["school"]!="evocation": continue
            seen.add(i)
            if i not in owners or place(owners[i],seen): owners[i]=name; return True
        return False
    for n in book: v.check(place(n,set()),"choices.spellbook","spells cannot be learned at legal levels/Savant choices")


def _build(class_name, level, subclass=None, abilities=None, equipment=None, choices=None, *, background=True):
    """Return a validated combat sheet; input abilities are pre-ASI scores."""
    v=Validator("<build>")
    v.enum(class_name,SUBCLASSES,"class")
    v.number(level,"level",1,True); v.check(level<=10,"level","supported levels are 1..10")
    c=_class(class_name); row=c["levels"][level]
    subclass = c["subclass"] if subclass is None else subclass
    v.enum(subclass,{c["subclass"]},"subclass")
    choices=deepcopy(choices) if choices is not None else {}
    v.obj(choices,"choices","","ability_method asis fighting_style weapon_masteries cantrips prepared_spells spellbook expertise skills cunning_strike divine_order blessed_strikes background")
    v.check(type(background) is bool,"background","expected boolean")
    abilities=deepcopy(abilities if abilities is not None else DEFAULT_ABILITIES[class_name])
    v.obj(abilities,"abilities",ABILITIES)
    for a,n in abilities.items(): v.number(n,"abilities."+a,3,True); v.check(n<=20,"abilities."+a,"score exceeds 20")
    method=choices.get("ability_method","standard_array")
    v.enum(method,{"standard_array","point_buy","assigned"},"choices.ability_method")
    if method=="standard_array": v.check(sorted(abilities.values())==[8,10,12,13,14,15],"abilities","not a standard array")
    if method=="point_buy":
        costs={8:0,9:1,10:2,11:3,12:4,13:5,14:7,15:9}
        v.check(all(n in costs for n in abilities.values()),"abilities","point-buy scores must be 8..15")
        v.check(sum(costs[n] for n in abilities.values())<=27,"abilities","point-buy budget exceeds 27")
    unboosted = abilities.copy()
    if background:
        primary = {"fighter":"str", "rogue":"dex", "wizard":"int", "cleric":"wis"}[class_name]
        increases = choices.get("background", {primary:2,"con":1})
        v.obj(increases,"choices.background","",ABILITIES)
        v.check(sorted(increases.values()) in ([1,2],[1,1,1]),"choices.background","expected +2/+1 or +1/+1/+1")
        for a,n in increases.items():
            v.check(type(n) is int,"choices.background","expected integer increases")
            abilities[a] = min(20, abilities[a]+n)
    asis=choices.get("asis",default_asis(class_name,level,abilities))
    v.check(isinstance(asis,dict) and all(type(k) is int for k in asis),"choices.asis","expected level mapping")
    v.check(set(asis)=={n for n in c["asi_levels"] if n<=level},"choices.asis","must choose each earned ASI exactly once")
    for n,add in asis.items():
        v.obj(add,f"choices.asis.{n}","",ABILITIES)
        for a,count in add.items(): v.number(count,f"choices.asis.{n}.{a}",1,True)
        v.check(sum(add.values())==2,f"choices.asis.{n}","ASI must add exactly two ability points")
        for a,count in add.items():
            unboosted[a] += count
            v.check(unboosted[a] <= 20, f"choices.asis.{n}.{a}", "ASI exceeds ability cap")
            for _ in range(count):
                selected = a
                if abilities[a] >= 20 and background:
                    selected = next((x for x in [primary,"con",*ABILITIES] if abilities[x] < 20), None)
                    v.check(selected is not None, f"choices.asis.{n}.{a}", "no ability can receive reallocated ASI")
                abilities[selected] += 1
                v.check(abilities[selected] <= 20, f"choices.asis.{n}.{a}", "ASI exceeds ability cap")
    mod=lambda a:(abilities[a]-10)//2
    equipment=DEFAULT_EQUIPMENT[class_name] if equipment is None else equipment
    v.enum(equipment,EQUIPMENT,"equipment")
    armor,shield,weapons=EQUIPMENT[equipment]
    order=choices.get("divine_order","protector")
    if class_name=="cleric": v.enum(order,{"protector","thaumaturge"},"choices.divine_order")
    else: v.check("divine_order" not in choices,"choices.divine_order","Cleric choice only")
    if class_name=="wizard": v.check(armor=="none" and not shield and weapons==["quarterstaff"],"equipment","Wizard lacks armor/weapon training")
    if class_name=="rogue": v.check(armor=="studded" and not shield and set(weapons)<={"rapier","shortbow"},"equipment","Rogue equipment not proficient")
    if class_name=="cleric": v.check(armor in {"chain","scale"} and (armor!="chain" or order=="protector"),"equipment","requires Protector for heavy armor")
    styles=choices.get("fighting_style",["defense"] + (["great_weapon_fighting"] if level>=7 else [])) if class_name=="fighter" else []
    if isinstance(styles,str): styles=[styles]
    if class_name=="fighter":
        v.sequence(styles,"choices.fighting_style"); v.check(len(styles)==1+int(level>=7) and len(set(styles))==len(styles),"choices.fighting_style","wrong number of distinct styles")
        for style in styles: v.enum(style,STYLES,"choices.fighting_style")
    else: v.check("fighting_style" not in choices,"choices.fighting_style","Fighter choice only")
    masteries=choices.get("weapon_masteries",weapons if class_name in {"fighter","rogue"} else [])
    v.sequence(masteries,"choices.weapon_masteries"); v.check(len(set(masteries))==len(masteries) and len(masteries)<=row["weapon_masteries"],"choices.weapon_masteries","exceeds mastery count or duplicate")
    for n in masteries:
        v.enum(n,WEAPONS,"choices.weapon_masteries")
        if class_name=="rogue": v.enum(n,{"rapier","shortbow","mace","quarterstaff"},"choices.weapon_masteries")
    ac={"none":10+mod("dex"),"chain":16,"studded":12+mod("dex"),"scale":14+min(2,mod("dex"))}[armor] + 2*shield + int("defense" in styles and armor!="none")
    faces=int(c["hit_die"][1:]); hp=max(1,faces+mod("con"))+(level-1)*max(1,faces//2+1+mod("con"))
    sheet={"name":f"{class_name.title()} {level} ({subclass.title()})", "source":"XPHB", "level":level,
           "hit_dice":{"die":c["hit_die"],"count":level}, "max_hp":hp,"ac":ac,"abilities":abilities,
           "speed":20 if armor=="chain" and abilities["str"]<13 else 30,"creature_type":"humanoid","proficiency_bonus":row["proficiency_bonus"],
           "save_proficiencies":c["saves"].copy(),"limited_uses":deepcopy(row["resources"]),"features":{"armored":armor!="none"},"actions":[],"attacks":[]}
    selected_strike=choices.get("blessed_strikes","potent_spellcasting")
    if class_name=="cleric": v.enum(selected_strike,{"potent_spellcasting","divine_strike"},"choices.blessed_strikes")
    else: v.check("blessed_strikes" not in choices,"choices.blessed_strikes","Cleric choice only")
    sheet["unsupported"]=[]
    sheet["position"] = "front" if armor in {"chain","scale"} and any(WEAPONS[n][2] == "melee" for n in weapons) else "back"
    for f in c["features"]:
        if f["level"]>level: continue
        if f["name"] in {"Divine Strike","Potent Spellcasting"} and f["name"].lower().replace(" ","_")!=selected_strike: continue
        if f["name"] in {"Thaumaturge","Protector"} and f["name"].lower()!=order: continue
        sheet["actions"].extend(substitute(f.get("actions",[]),level,row))
        sheet["features"].update({k:substitute(x,level,row) for k,x in f.get("mechanics",{}).items() if k not in {"builder","progression"}})
        if "unsupported" in f: sheet["unsupported"].append(f["name"]+": "+f["unsupported"])
    if "great_weapon_fighting" in styles: sheet["features"]["great_weapon_fighting"]=True
    if class_name=="fighter" and level>=5: sheet["extra_attack"]=2
    for weapon in weapons:
        ds,dt,kind,mastery,properties=WEAPONS[weapon]
        ability="dex" if kind=="ranged" or "finesse" in properties and mod("dex")>mod("str") else "str"
        if weapon in {"longsword","quarterstaff"} and not shield: ds="1d10" if weapon=="longsword" else "1d8"
        if "versatile" in properties and not shield: properties=[*properties,"two_handed"]
        bonus=mod(ability)+(2 if "dueling" in styles and kind=="melee" and "two_handed" not in properties and shield else 0)
        attack={"name":weapon.title(),"kind":kind,"ability":ability,"properties":properties.copy(),"to_hit":row["proficiency_bonus"]+mod(ability)+(2 if "archery" in styles and kind=="ranged" else 0),"effects":[{"damage":{"dice":ds,"bonus":bonus,"type":dt}}]}
        if kind=="melee": attack["reach_ft"]=5
        else: attack["range_ft"]=80 if weapon=="shortbow" else 150
        if weapon in masteries: attack["mastery"]=mastery
        sheet["attacks"].append(attack)
    skills=choices.get("skills",SKILLS[class_name]); v.sequence(skills,"choices.skills")
    expected=4 if class_name=="rogue" else 2
    v.check(len(skills)==expected and len(set(skills))==len(skills),"choices.skills","wrong skill count")
    allowed=source(class_name)[0]["startingProficiencies"]["skills"][0]["choose"]["from"]
    for skill in skills: v.enum(skill,set(allowed),"choices.skills")
    count=(2+2*int(level>=6)) if class_name=="rogue" else int(class_name=="wizard" and level>=2)
    expertise=choices.get("expertise",skills[:count]); v.sequence(expertise,"choices.expertise")
    v.check(len(expertise)==count and len(set(expertise))==count and set(expertise)<=set(skills),"choices.expertise","Expertise requires distinct proficient skills and exact count")
    if class_name=="wizard":
        for skill in expertise: v.enum(skill,{"arcana","history","investigation","medicine","nature","religion"},"choices.expertise")
    sheet["skill_proficiencies"]=skills.copy(); sheet["expertise"]=expertise.copy()
    if class_name=="rogue":
        sheet["skill_proficiencies"].append("thieves' tools")
        if level>=3: sheet["skill_proficiencies"] += ["poisoner's kit","disguise kit"]
    cunning=choices.get("cunning_strike",["poison","trip"] if class_name=="rogue" and level>=5 else [])
    v.sequence(cunning,"choices.cunning_strike")
    v.check(not cunning or class_name=="rogue" and level>=5,"choices.cunning_strike","requires Rogue 5")
    for x in cunning: v.enum(x,{"poison","trip","withdraw"},"choices.cunning_strike")
    sheet["cunning_strike"]=cunning.copy()
    if class_name in SPELL_LISTS:
        ability="int" if class_name=="wizard" else "wis"
        sheet.update(spell_ability=ability,spell_dc=8+row["proficiency_bonus"]+mod(ability),spell_attack_bonus=row["proficiency_bonus"]+mod(ability),spell_slots=deepcopy(row["slots"]))
        options=spell_options(class_name,level)
        cantrips=choices.get("cantrips",CANTRIPS[class_name][:row["cantrips"]+int(order=="thaumaturge" and class_name=="cleric")])
        v.sequence(cantrips,"choices.cantrips")
        v.check(len(cantrips)==row["cantrips"]+int(class_name=="cleric" and order=="thaumaturge") and len(set(cantrips))==len(cantrips),"choices.cantrips","wrong cantrip count")
        for n in cantrips: v.check(n in options and options[n]["level"]==0,"choices.cantrips",f"not a supported {class_name} cantrip: {n}")
        domain=[]
        if class_name=="cleric" and level>=3:
            for at,names in source("cleric")[1]["additionalSpells"][0]["prepared"].items():
                if int(at)<=level:
                    for ref in names:
                        n=next((n for n in _spells() if n.lower()==ref.split('|')[0]),None)
                        if n: domain.append(n)
                        else: sheet["unsupported"].append("Domain spell has no existing spec: "+ref.split('|')[0])
        if class_name=="wizard":
            book=choices.get("spellbook",default_book(level,options))
            v.sequence(book,"choices.spellbook"); v.check(len(set(book))==len(book),"choices.spellbook","duplicate spell")
            for n in book: v.check(n in options and options[n]["level"]>0,"choices.spellbook",f"illegal book spell {n}")
            validate_book(book,level,options,v)
            sheet["spellbook"]=book.copy(); available={n:options[n] for n in book}
        else:
            v.check("spellbook" not in choices,"choices.spellbook","Wizard choice only")
            available={n:v for n,v in options.items() if v["level"]>0 and n not in domain}
        prepared=choices.get("prepared_spells",spell_order(class_name,available)[:row["prepared"]])
        v.sequence(prepared,"choices.prepared_spells")
        v.check(len(prepared)==row["prepared"] and len(set(prepared))==len(prepared),"choices.prepared_spells","wrong prepared spell count")
        for n in prepared: v.check(n in available,"choices.prepared_spells",f"illegal prepared spell {n}")
        sheet["prepared_spells"]=prepared.copy()
        sheet["spells"]=list(dict.fromkeys(cantrips+prepared+domain))
    else:
        v.check(not any(k in choices for k in ("cantrips","prepared_spells","spellbook")),"choices","class has no spellcasting")
    validate_sheet(sheet,"<built character>")
    return sheet


def build(class_name, level, subclass=None, abilities=None, equipment=None, choices=None, *, background=True):
    """Build one strict sheet, reporting malformed caller data as validation errors."""
    try: return _build(class_name,level,subclass,abilities,equipment,choices,background=background)
    except (TypeError,KeyError,AttributeError,IndexError) as exc:
        raise ValidationError(f"<build>:$: malformed build ({exc})") from exc


def load_build(name_or_path, *, background=True):
    path=Path(name_or_path)
    if path.suffix!=".yaml":
        if not re.fullmatch(r"[a-z][a-z0-9_]*",str(path)): raise ValueError("invalid build name")
        path=ROOT/"builds"/(str(path)+".yaml")
    d=read_yaml(path); v=Validator(path)
    v.obj(d,"$","class level subclass abilities equipment choices")
    try: return build(d["class"],d["level"],d["subclass"],d["abilities"],d["equipment"],d["choices"],background=background)
    except ValidationError as exc: raise ValidationError(f"{path}: {exc}") from exc


def load_character(name, *, background=True):
    from .loader import load_sheet
    if not re.fullmatch(r"[a-z][a-z0-9_]*",name): raise ValueError("invalid character name")
    fixed=ROOT/"characters"/(name+".yaml")
    return load_sheet(fixed) if fixed.is_file() else load_build(name,background=background)


def write_presets():
    import yaml
    folder=ROOT/"builds"; folder.mkdir(exist_ok=True)
    for name,sub in SUBCLASSES.items():
        for level in (1,3,5,7,10):
            d={"class":name,"level":level,"subclass":sub,"abilities":DEFAULT_ABILITIES[name],"equipment":DEFAULT_EQUIPMENT[name],"choices":{"ability_method":"standard_array","asis":default_asis(name,level,DEFAULT_ABILITIES[name])}}
            sheet=build(name,level,sub,d["abilities"],d["equipment"],d["choices"])
            d["choices"]["weapon_masteries"]=[n for n in EQUIPMENT[d["equipment"]][2] if name in {"fighter","rogue"}]
            if name=="fighter": d["choices"]["fighting_style"]=["defense"]+(["great_weapon_fighting"] if level>=7 else [])
            for k in ("cantrips","prepared_spells","spellbook"):
                if k=="cantrips" and "spells" in sheet: d["choices"][k]=[n for n in sheet["spells"] if _spells()[n]["level"]==0]
                elif k in sheet: d["choices"][k]=sheet[k]
            d["choices"]["expertise"]=sheet["expertise"]
            if name=="rogue" and level>=5: d["choices"]["cunning_strike"]=["poison","trip"]
            if name=="cleric": d["choices"].update(divine_order="protector",blessed_strikes="potent_spellcasting")
            (folder/f"{name}_{level}.yaml").write_text(yaml.safe_dump(d,sort_keys=False),encoding="utf-8")


if __name__=="__main__": write_presets()
