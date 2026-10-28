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
SPELL_LISTS["paladin"] = set("Bless; Shield of Faith; Cure Wounds; Heroism; Command; Aid; Protection from Evil and Good; Protection from Poison; Lesser Restoration; Zone of Truth; Divine Smite; Searing Smite; Thunderous Smite; Wrathful Smite; Magic Weapon; Shining Smite; Prayer of Healing; Warding Bond; Dispel Magic; Revivify; Aura of Vitality; Blinding Smite; Daylight; Remove Curse; Create Food and Water".split("; "))
SPELL_LISTS["warlock"] = set("Blade Ward; Chill Touch; Eldritch Blast; Friends; Mage Hand; Mind Sliver; Minor Illusion; Poison Spray; Prestidigitation; Thunderclap; Toll the Dead; True Strike; Armor of Agathys; Arms of Hadar; Bane; Charm Person; Comprehend Languages; Detect Magic; Expeditious Retreat; Hellish Rebuke; Hex; Illusory Script; Protection from Evil and Good; Speak with Animals; Tasha's Hideous Laughter; Unseen Servant; Witch Bolt; Cloud of Daggers; Crown of Madness; Darkness; Enthrall; Hold Person; Invisibility; Mirror Image; Misty Step; Ray of Enfeeblement; Shatter; Spider Climb; Suggestion; Counterspell; Dispel Magic; Fear; Fly; Gaseous Form; Hunger of Hadar; Hypnotic Pattern; Magic Circle; Major Image; Remove Curse; Summon Fey; Summon Undead; Tongues; Vampiric Touch; Banishment; Blight; Charm Monster; Dimension Door; Hallucinatory Terrain; Summon Aberration; Contact Other Plane; Dream; Hold Monster; Mislead; Planar Binding; Scrying; Synaptic Static; Teleportation Circle".split("; "))
SPELL_LISTS["bard"] = set("Blade Ward; Dancing Lights; Friends; Light; Mage Hand; Mending; Message; Minor Illusion; Prestidigitation; Starry Wisp; Thunderclap; True Strike; Vicious Mockery; Animal Friendship; Bane; Charm Person; Color Spray; Command; Comprehend Languages; Cure Wounds; Detect Magic; Disguise Self; Dissonant Whispers; Faerie Fire; Feather Fall; Healing Word; Heroism; Identify; Illusory Script; Longstrider; Silent Image; Sleep; Speak with Animals; Tasha's Hideous Laughter; Thunderwave; Unseen Servant; Aid; Animal Messenger; Blindness/Deafness; Calm Emotions; Cloud of Daggers; Crown of Madness; Detect Thoughts; Enhance Ability; Enlarge/Reduce; Enthrall; Heat Metal; Hold Person; Invisibility; Knock; Lesser Restoration; Locate Animals or Plants; Locate Object; Magic Mouth; Mirror Image; Phantasmal Force; See Invisibility; Shatter; Silence; Suggestion; Zone of Truth; Bestow Curse; Clairvoyance; Dispel Magic; Fear; Feign Death; Glyph of Warding; Hypnotic Pattern; Leomund's Tiny Hut; Major Image; Mass Healing Word; Nondetection; Plant Growth; Sending; Slow; Speak with Dead; Speak with Plants; Stinking Cloud; Tongues; Charm Monster; Compulsion; Confusion; Dimension Door; Freedom of Movement; Greater Invisibility; Hallucinatory Terrain; Locate Creature; Phantasmal Killer; Polymorph; Animate Objects; Awaken; Dominate Person; Dream; Geas; Greater Restoration; Hold Monster; Legend Lore; Mass Cure Wounds; Mislead; Modify Memory; Planar Binding; Raise Dead; Rary's Telepathic Bond; Scrying; Seeming; Synaptic Static; Teleportation Circle".split("; "))
SPELL_LISTS["druid"] = set("Guidance; Resistance; Starry Wisp; Thorn Whip; Shillelagh; Produce Flame; Entangle; Faerie Fire; Goodberry; Healing Word; Cure Wounds; Thunderwave; Barkskin; Heat Metal; Moonbeam; Pass without Trace; Spike Growth; Call Lightning; Conjure Animals; Plant Growth; Sleet Storm; Conjure Woodland Beings; Conjure Minor Elementals; Ice Storm; Wall of Fire; Antilife Shell; Cone of Cold; Insect Plague; Mass Cure Wounds; Wall of Stone".split("; "))
SPELL_LISTS["druid"].update("Animal Friendship; Charm Person; Create or Destroy Water; Detect Magic; Detect Poison and Disease; Fog Cloud; Jump; Longstrider; Protection from Evil and Good; Purify Food and Drink; Speak with Animals; Animal Messenger; Augury; Beast Sense; Continual Flame; Darkvision; Enhance Ability; Enlarge/Reduce; Find Traps; Flame Blade; Flaming Sphere; Gust of Wind; Hold Person; Lesser Restoration; Locate Animals or Plants; Locate Object; Protection from Poison; Summon Beast; Aura of Vitality; Conjure Minor Elementals; Conjure Elemental; Daylight; Dispel Magic; Elemental Weapon; Feign Death; Meld into Stone; Protection from Energy; Revivify; Speak with Plants; Summon Fey; Water Breathing; Water Walk; Wind Wall; Blight; Charm Monster; Confusion; Divination; Dominate Beast; Fire Shield; Freedom of Movement; Giant Insect; Grasping Vine; Hallucinatory Terrain; Locate Creature; Polymorph; Stone Shape; Stoneskin; Summon Elemental; Awaken; Commune with Nature; Contagion; Geas; Greater Restoration; Planar Binding; Reincarnate; Scrying; Tree Stride; Druidcraft; Elementalism; Mending; Poison Spray; Thunderclap".split("; "))
SPELL_LISTS["ranger"] = set("Hunter's Mark; Cure Wounds; Entangle; Ensnaring Strike; Hail of Thorns; Fog Cloud; Longstrider; Jump; Goodberry; Detect Magic; Detect Poison and Disease; Speak with Animals; Animal Friendship; Alarm; Protection from Poison; Lesser Restoration; Aid; Enhance Ability; Gust of Wind; Magic Weapon; Pass without Trace; Silence; Spike Growth; Summon Beast; Barkskin; Beast Sense; Cordon of Arrows; Darkvision; Find Traps; Locate Animals or Plants; Locate Object; Animal Messenger; Conjure Animals; Conjure Barrage; Daylight; Dispel Magic; Elemental Weapon; Lightning Arrow; Meld into Stone; Nondetection; Plant Growth; Protection from Energy; Revivify; Speak with Plants; Summon Fey; Water Breathing; Water Walk; Wind Wall".split("; "))
PRIORITY = {
    "ranger": ["Cure Wounds","Entangle","Hail of Thorns","Aid","Spike Growth","Magic Weapon","Summon Beast","Revivify","Lightning Arrow"],
    "warlock": ["Hex", "Armor of Agathys", "Hellish Rebuke", "Hold Person", "Mirror Image", "Hypnotic Pattern", "Counterspell", "Hunger of Hadar", "Banishment", "Synaptic Static"],
    "bard": ["Healing Word", "Fireball", "Wall of Force", "Dissonant Whispers", "Sleep", "Faerie Fire", "Shatter", "Hold Person", "Hypnotic Pattern", "Slow", "Aid", "Polymorph", "Synaptic Static", "Mass Cure Wounds", "Lesser Restoration"],
    "paladin": ["Bless", "Cure Wounds", "Heroism", "Command", "Shield of Faith", "Aid", "Lesser Restoration", "Magic Weapon", "Revivify", "Dispel Magic"],
    "wizard": ["Fireball", "Shield", "Mage Armor", "Magic Missile", "Counterspell", "Scorching Ray", "Thunderwave", "Mirror Image", "Misty Step", "Haste", "Web", "Cone of Cold", "Ice Storm", "Wall of Fire", "Fire Shield", "Slow", "Sleep", "Chromatic Orb", "Burning Hands", "Lightning Bolt"],
    "cleric": ["Spirit Guardians", "Healing Word", "Guiding Bolt", "Spiritual Weapon", "Hold Person", "Shield of Faith", "Bless", "Cure Wounds", "Aid", "Lesser Restoration", "Mass Healing Word", "Bane", "Sanctuary", "Command", "Inflict Wounds", "Silence", "Warding Bond", "Death Ward", "Mass Cure Wounds", "Flame Strike"],
}
CANTRIPS = {"ranger": [], "warlock": ["Eldritch Blast", "Mind Sliver", "Mage Hand", "Minor Illusion"], "bard": ["Vicious Mockery", "Starry Wisp", "Mage Hand", "Minor Illusion"],"paladin": [], "wizard": ["Fire Bolt", "Ray of Frost", "Toll the Dead", "Shocking Grasp", "Acid Splash"],
            "cleric": ["Sacred Flame", "Toll the Dead", "Guidance", "Word of Radiance", "Resistance", "Thaumaturgy"]}
ABILITIES = ("str", "dex", "con", "int", "wis", "cha")
DEFAULT_ABILITIES = {
    "monk": dict(zip(ABILITIES, [10,15,13,8,14,12])),
    "ranger": dict(zip(ABILITIES, [10,15,13,8,14,12])),
    "warlock": dict(zip(ABILITIES, [8,14,13,12,10,15])),
    "bard": dict(zip(ABILITIES, [8,14,13,12,10,15])),
    "barbarian": dict(zip(ABILITIES, [15,14,13,8,12,10])),
    "paladin": dict(zip(ABILITIES, [15,10,14,8,12,13])),
    "fighter": dict(zip(ABILITIES, [15,12,14,10,13,8])),
    "rogue": dict(zip(ABILITIES, [8,15,14,12,13,10])),
    "wizard": dict(zip(ABILITIES, [8,14,13,15,12,10])),
    "cleric": dict(zip(ABILITIES, [13,10,14,12,15,8])),
}
SKILLS = {"monk":["acrobatics","insight"], "ranger":["perception","stealth","survival"], "warlock": ["arcana", "deception"], "bard": ["performance", "persuasion", "perception"],"barbarian": ["athletics", "perception", "survival"], "paladin": ["athletics", "persuasion"], "fighter": ["athletics", "perception"], "rogue": ["stealth", "sleight of hand", "perception", "investigation"],
          "wizard": ["arcana", "history"], "cleric": ["religion", "insight"]}
WEAPONS = {
    "greataxe": ("1d12", "slashing", "melee", "cleave", ["two_handed", "heavy"]),
    "maul": ("2d6", "bludgeoning", "melee", "topple", ["two_handed", "heavy"]),
    "greatsword": ("2d6", "slashing", "melee", "graze", ["two_handed", "heavy"]),
    "longsword": ("1d8", "slashing", "melee", "sap", ["versatile"]),
    "rapier": ("1d8", "piercing", "melee", "vex", ["finesse"]),
    "shortbow": ("1d6", "piercing", "ranged", "vex", ["two_handed"]),
    "longbow": ("1d8", "piercing", "ranged", "slow", ["two_handed", "heavy"]),
    "mace": ("1d6", "bludgeoning", "melee", "sap", []),
    "quarterstaff": ("1d6", "bludgeoning", "melee", "topple", ["versatile"]),
}
EQUIPMENT = {
    "scale_sword_shield": ("scale", True, ["longsword"]),
    "unarmored_greataxe": ("none", False, ["greataxe"]),
    "unarmored_greatsword": ("none", False, ["greatsword"]),
    "unarmored_maul": ("none", False, ["maul"]),
    "scale_greataxe": ("scale", False, ["greataxe"]),
    "chain_greatsword": ("chain", False, ["greatsword"]),
    "chain_sword_shield": ("chain", True, ["longsword"]),
    "leather_archer": ("studded", False, ["longbow"]),
    "studded_rapier": ("studded", False, ["rapier", "shortbow"]),
    "studded_shortbow": ("studded", False, ["shortbow", "rapier"]),
    "unarmored_staff": ("none", False, ["quarterstaff"]),
    "studded_staff": ("studded", False, ["quarterstaff"]),
    "chain_shield": ("chain", True, ["mace"]),
    "scale_shield": ("scale", True, ["mace"]),
}
DEFAULT_EQUIPMENT = dict(zip(SUBCLASSES, ("chain_greatsword", "studded_rapier", "unarmored_staff", "chain_shield")))
DEFAULT_EQUIPMENT.update(barbarian="unarmored_greataxe", paladin="chain_greatsword", warlock="unarmored_staff", bard="studded_staff", monk="unarmored_staff", ranger="leather_archer")
STYLES = {"defense", "archery", "dueling", "great_weapon_fighting"}
# 2024 General feats taken in place of an ASI: the +1 ability options and prerequisite.
FEATS = {
    "great_weapon_master": {"abilities": {"str"}, "requires": ("str", 13)},
    "sharpshooter": {"abilities": {"dex"}, "requires": ("dex", 13)},
    "war_caster": {"abilities": {"int", "wis", "cha"}, "requires": "spellcasting"},
}
ORIGIN_FEATS = {"alert"}


@lru_cache(None)
def _spells(): return load_spells()


@lru_cache(None)
def _class(name): return load_class(name)


@lru_cache(None)
def spell_options(name, level):
    spells = _spells()
    cap = max(_class(name)["levels"][level]["slots"], default=0) if name in {"paladin", "warlock", "ranger"} else (level + 1)//2
    names = SPELL_LISTS.get(name, set())
    if name=="bard" and level>=10: names = names | {n for n in SPELL_LISTS["cleric"] | SPELL_LISTS["druid"] | SPELL_LISTS["wizard"] if n in spells and spells[n]["level"]>0}
    return {n: spells[n] for n in names if n in spells and spells[n]["level"] <= cap}


def spell_order(name, options):
    return [n for n in PRIORITY[name] if n in options] + sorted(set(options) - set(PRIORITY[name]))


def default_asis(name, level, abilities):
    c = _class(name); result={}; scores=abilities.copy()
    primary = {"fighter":"str", "rogue":"dex", "wizard":"int", "cleric":"wis", "barbarian":"str", "paladin":"str", "warlock":"cha", "bard":"cha", "monk":"dex", "ranger":"dex"}[name]
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
    v.obj(choices,"choices","","ability_method asis fighting_style weapon_masteries cantrips prepared_spells spellbook expertise skills cunning_strike divine_order blessed_strikes background origin_feat invocations magical_discoveries hunters_prey open_hand stunning_budget")
    v.check(class_name=="bard" or "magical_discoveries" not in choices,"choices.magical_discoveries","Bard choice only")
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
        primary = {"fighter":"str", "rogue":"dex", "wizard":"int", "cleric":"wis", "barbarian":"str", "paladin":"str", "warlock":"cha", "bard":"cha", "monk":"dex", "ranger":"dex"}[class_name]
        increases = choices.get("background", {primary:2,"con":1})
        v.obj(increases,"choices.background","",ABILITIES)
        v.check(sorted(increases.values()) in ([1,2],[1,1,1]),"choices.background","expected +2/+1 or +1/+1/+1")
        for a,n in increases.items():
            v.check(type(n) is int,"choices.background","expected integer increases")
            abilities[a] = min(20, abilities[a]+n)
    asis=choices.get("asis",default_asis(class_name,level,abilities))
    v.check(isinstance(asis,dict) and all(type(k) is int for k in asis),"choices.asis","expected level mapping")
    v.check(set(asis)=={n for n in c["asi_levels"] if n<=level},"choices.asis","must choose each earned ASI exactly once")
    feats=[]
    for n,add in sorted(asis.items()):
        if isinstance(add,dict) and "feat" in add:
            # A General feat in place of the ASI: its +1 goes to one of the feat's abilities.
            v.obj(add,f"choices.asis.{n}","feat ability")
            v.enum(add["feat"],FEATS,f"choices.asis.{n}.feat")
            feat=FEATS[add["feat"]]
            v.enum(add["ability"],feat["abilities"],f"choices.asis.{n}.ability")
            v.check(add["feat"] not in feats,f"choices.asis.{n}.feat","feat already taken")
            need=feat["requires"]
            if need=="spellcasting": v.check(class_name in SPELL_LISTS,f"choices.asis.{n}.feat","requires the Spellcasting feature")
            else: v.check(abilities[need[0]]>=need[1],f"choices.asis.{n}.feat",f"requires {need[0].title()} {need[1]}")
            feats.append(add["feat"])
            unboosted[add["ability"]] += 1
            abilities[add["ability"]] = min(20, abilities[add["ability"]] + 1)
            continue
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
    if class_name in {"warlock","bard"}: v.check(armor in {"none","studded"} and not shield and set(weapons)<={"quarterstaff","shortbow","mace"},"equipment","class lacks armor/weapon training")
    if class_name=="rogue": v.check(armor=="studded" and not shield and set(weapons)<={"rapier","shortbow"},"equipment","Rogue equipment not proficient")
    if class_name=="cleric": v.check(armor in {"chain","scale"} and (armor!="chain" or order=="protector"),"equipment","requires Protector for heavy armor")
    if class_name=="barbarian": v.check(armor!="chain","equipment","Barbarian lacks heavy armor training")
    if class_name=="monk": v.check(armor=="none" and not shield and set(weapons)<={"quarterstaff","mace"},"equipment","Monk requires unarmored monk-weapon kit")
    if class_name=="ranger": v.check(armor!="chain","equipment","Ranger lacks heavy armor training")
    styles=choices.get("fighting_style",(["archery"] if class_name=="ranger" else ["defense"]) + (["great_weapon_fighting"] if class_name=="fighter" and level>=7 else [])) if class_name in {"fighter","paladin","ranger"} and (class_name=="fighter" or level>=2) else []
    if isinstance(styles,str): styles=[styles]
    if class_name in {"fighter","paladin","ranger"} and (class_name=="fighter" or level>=2):
        v.sequence(styles,"choices.fighting_style"); v.check(len(styles)==1+int(class_name=="fighter" and level>=7) and len(set(styles))==len(styles),"choices.fighting_style","wrong number of distinct styles")
        for style in styles: v.enum(style,STYLES,"choices.fighting_style")
    else: v.check("fighting_style" not in choices,"choices.fighting_style","Fighter choice only")
    masteries=choices.get("weapon_masteries",weapons if class_name in {"fighter","rogue","barbarian","paladin","ranger"} else [])
    v.sequence(masteries,"choices.weapon_masteries"); v.check(len(set(masteries))==len(masteries) and len(masteries)<=row["weapon_masteries"],"choices.weapon_masteries","exceeds mastery count or duplicate")
    for n in masteries:
        v.enum(n,WEAPONS,"choices.weapon_masteries")
        if class_name=="rogue": v.enum(n,{"rapier","shortbow","mace","quarterstaff"},"choices.weapon_masteries")
    ac={"none":10+mod("dex"),"chain":16,"studded":12+mod("dex"),"scale":14+min(2,mod("dex"))}[armor] + 2*shield + int("defense" in styles and armor!="none")
    if class_name=="barbarian" and armor=="none": ac += mod("con")
    if class_name=="monk": ac += mod("wis")
    faces=int(c["hit_die"][1:]); hp=max(1,faces+mod("con"))+(level-1)*max(1,faces//2+1+mod("con"))
    sheet={"name":f"{class_name.title()} {level} ({subclass.title()})", "source":"XPHB", "level":level,
           "hit_dice":{"die":c["hit_die"],"count":level}, "max_hp":hp,"ac":ac,"abilities":abilities,
           "speed":20 if armor=="chain" and abilities["str"]<13 else 30,"creature_type":"humanoid","proficiency_bonus":row["proficiency_bonus"],
           "save_proficiencies":c["saves"].copy(),"limited_uses":deepcopy(row["resources"]),"features":{"armored":armor!="none"},"actions":[],"attacks":[]}
    selected_strike=choices.get("blessed_strikes","potent_spellcasting")
    if class_name=="cleric": v.enum(selected_strike,{"potent_spellcasting","divine_strike"},"choices.blessed_strikes")
    else: v.check("blessed_strikes" not in choices,"choices.blessed_strikes","Cleric choice only")
    sheet["unsupported"]=[]
    sheet["position"] = "front" if (armor in {"chain","scale"} or class_name in {"barbarian","monk"}) and any(WEAPONS[n][2] == "melee" for n in weapons) else "back"
    for f in c["features"]:
        if f["level"]>level: continue
        if f["name"] in {"Divine Strike","Potent Spellcasting"} and f["name"].lower().replace(" ","_")!=selected_strike: continue
        if f["name"] in {"Thaumaturge","Protector"} and f["name"].lower()!=order: continue
        sheet["actions"].extend(substitute(f.get("actions",[]),level,row))
        sheet["features"].update({k:substitute(x,level,row) for k,x in f.get("mechanics",{}).items() if k not in {"builder","progression"}})
        if "unsupported" in f: sheet["unsupported"].append(f["name"]+": "+f["unsupported"])
    # Do not enable for cleric/wizard: their published results must stay bit-identical.
    if class_name in {"paladin","warlock","bard","monk","ranger"}: sheet["features"]["values_buffs"]=True
    for key,owner,minimum,options,default in (("hunters_prey","ranger",3,{"colossus_slayer","horde_breaker"},"colossus_slayer"),("open_hand","monk",3,{"topple","addle"},"topple"),("stunning_budget","monk",5,{"balanced","reserve"},"balanced")):
        if key in choices: v.check(class_name==owner and level>=minimum,"choices."+key,"choice not available")
        if class_name==owner and level>=minimum:
            chosen=choices.get(key,default); v.enum(chosen,options,"choices."+key)
            if key=="hunters_prey":
                sheet["features"]["colossus_slayer"]=chosen=="colossus_slayer"
                sheet["features"]["horde_breaker"]=chosen=="horde_breaker"
            else: sheet["features"]["open_hand_addle" if key=="open_hand" else "stunning_reserve"]=chosen!=default
    if class_name=="monk":
        sheet.update(spell_ability="wis",spell_dc=8+row["proficiency_bonus"]+mod("wis"))
        sheet["speed"]+=0 if level<2 else 10 if level<6 else 15 if level<10 else 20
        if level>=6: sheet["limited_uses"]["wholeness_of_body"]={"max":max(1,mod("wis")),"long_rest":"all"}
    if class_name=="warlock":
        invocations=choices.get("invocations",["armor_of_shadows"] + (["agonizing_blast","eldritch_mind"] if level>=2 else []))
        v.sequence(invocations,"choices.invocations")
        v.check(len(set(invocations))==len(invocations) and len(invocations)<=source(class_name)[0]["classTableGroups"][0]["rows"][level-1][0],"choices.invocations","duplicate or too many invocations")
        for inv in invocations:
            v.enum(inv,{"armor_of_shadows","agonizing_blast","eldritch_mind"},"choices.invocations")
            v.check(inv=="armor_of_shadows" or level>=2,"choices.invocations","invocation requires level 2")
            sheet["features"][inv]=True
        if "armor_of_shadows" in invocations and armor=="none": sheet["ac"]=13+mod("dex")
        if level>=6: sheet["limited_uses"]["dark_ones_own_luck"]={"max":max(1,mod("cha")),"long_rest":"all"}
        if level>=10: sheet["resistances"]=["slashing"]
    else: v.check("invocations" not in choices,"choices.invocations","Warlock choice only")
    if class_name=="bard":
        sheet["limited_uses"]["bardic_inspiration"]={"max":max(1,mod("cha")),"short_rest":"all" if level>=5 else 0,"long_rest":"all"}
        if level>=2: sheet["initiative_bonus"]=row["proficiency_bonus"]//2
    if "great_weapon_fighting" in styles: sheet["features"]["great_weapon_fighting"]=True
    for feat in feats: sheet["features"][feat]=True
    origin=choices.get("origin_feat")
    if origin is not None:
        v.enum(origin,ORIGIN_FEATS,"choices.origin_feat")
        sheet["features"][origin]=True
        if origin=="alert": sheet["initiative_bonus"]=sheet.get("initiative_bonus",0)+row["proficiency_bonus"]
    if class_name in {"fighter","barbarian","paladin","monk","ranger"} and level>=5: sheet["extra_attack"]=2
    for weapon in weapons:
        ds,dt,kind,mastery,properties=WEAPONS[weapon]
        ability="dex" if kind=="ranged" or "finesse" in properties and mod("dex")>mod("str") else "str"
        if weapon in {"longsword","quarterstaff"} and not shield: ds="1d10" if weapon=="longsword" else "1d8"
        if "versatile" in properties and not shield: properties=[*properties,"two_handed"]
        if class_name=="monk":
            ability="dex" if mod("dex")>=mod("str") else "str"
            if level>=5: ds="1d8"
        bonus=mod(ability)+(2 if "dueling" in styles and kind=="melee" and "two_handed" not in properties and shield else 0)
        attack={"name":weapon.title(),"kind":kind,"ability":ability,"properties":properties.copy(),"to_hit":row["proficiency_bonus"]+mod(ability)+(2 if "archery" in styles and kind=="ranged" else 0),"effects":[{"damage":{"dice":ds,"bonus":bonus,"type":dt}}]}
        if kind=="melee": attack["reach_ft"]=5
        else: attack["range_ft"]=80 if weapon=="shortbow" else 150
        if weapon in masteries: attack["mastery"]=mastery
        sheet["attacks"].append(attack)
    if class_name=="monk":
        ability="dex" if mod("dex")>=mod("str") else "str"
        sheet["attacks"].append({"name":"Unarmed Strike","kind":"melee","ability":ability,"properties":[],"to_hit":row["proficiency_bonus"]+mod(ability),"reach_ft":5,"effects":[{"damage":{"dice":"1d8" if level>=5 else "1d6","bonus":mod(ability),"type":"force" if level>=6 else "bludgeoning"}}]})
    skills=choices.get("skills",SKILLS[class_name]); v.sequence(skills,"choices.skills")
    if class_name=="barbarian" and level<3 and "skills" not in choices: skills=skills[:2]
    expected=4 if class_name=="rogue" else 3 if class_name=="barbarian" and level>=3 else 3 if class_name in {"bard","ranger"} else 2
    v.check(len(skills)==expected and len(set(skills))==len(skills),"choices.skills","wrong skill count")
    allowed=source(class_name)[0]["startingProficiencies"]["skills"][0].get("choose",{}).get("from","acrobatics; animal handling; arcana; athletics; deception; history; insight; intimidation; investigation; medicine; nature; perception; performance; persuasion; religion; sleight of hand; stealth; survival".split("; "))
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
    if class_name in SPELL_LISTS and class_name!="druid":
        ability="int" if class_name=="wizard" else "cha" if class_name in {"paladin","warlock","bard"} else "wis"
        sheet.update(spell_ability=ability,spell_dc=8+row["proficiency_bonus"]+mod(ability),spell_attack_bonus=row["proficiency_bonus"]+mod(ability),spell_slots=deepcopy(row["slots"]))
        options=spell_options(class_name,level)
        cantrips=choices.get("cantrips",CANTRIPS[class_name][:row["cantrips"]+int(order=="thaumaturge" and class_name=="cleric")])
        v.sequence(cantrips,"choices.cantrips")
        v.check(len(cantrips)==row["cantrips"]+int(class_name=="cleric" and order=="thaumaturge") and len(set(cantrips))==len(cantrips),"choices.cantrips","wrong cantrip count")
        for n in cantrips: v.check(n in options and options[n]["level"]==0,"choices.cantrips",f"not a supported {class_name} cantrip: {n}")
        domain=["Hunter's Mark"] if class_name=="ranger" else []
        if class_name in {"cleric","paladin","warlock"} and level>=3:
            for at,names in source(class_name)[1]["additionalSpells"][0]["prepared"].items():
                if int(at)<=level:
                    for ref in names:
                        n=next((n for n in _spells() if n.lower()==ref.split('|')[0]),None)
                        if n: domain.append(n)
                        else: sheet["unsupported"].append("Domain spell has no existing spec: "+ref.split('|')[0])
        if class_name=="paladin" and level>=2: domain.append("Divine Smite")
        discoveries=choices.get("magical_discoveries",["Counterspell","Spirit Guardians"] if class_name=="bard" and level>=6 else [])
        v.sequence(discoveries,"choices.magical_discoveries")
        v.check(len(discoveries)==(2 if class_name=="bard" and level>=6 else 0) and len(set(discoveries))==len(discoveries),"choices.magical_discoveries","requires two distinct Lore spells at level 6")
        for n in discoveries:
            v.check(n in _spells() and n in SPELL_LISTS["cleric"] | SPELL_LISTS["druid"] | SPELL_LISTS["wizard"] and _spells()[n]["level"]<=max(row["slots"]),"choices.magical_discoveries","illegal discovery")
        domain += discoveries
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


def write_presets(names=SUBCLASSES):
    import yaml
    folder=ROOT/"builds"; folder.mkdir(exist_ok=True)
    for name in names:
        sub=SUBCLASSES[name]
        for level in (1,3,5,7,10):
            d={"class":name,"level":level,"subclass":sub,"abilities":DEFAULT_ABILITIES[name],"equipment":DEFAULT_EQUIPMENT[name],"choices":{"ability_method":"standard_array","asis":default_asis(name,level,DEFAULT_ABILITIES[name])}}
            sheet=build(name,level,sub,d["abilities"],d["equipment"],d["choices"])
            d["choices"]["weapon_masteries"]=[n for n in EQUIPMENT[d["equipment"]][2] if name in {"fighter","rogue","barbarian","paladin","ranger"}]
            if name=="ranger" and level>=2: d["choices"]["fighting_style"]=["archery"]
            if name=="paladin" and level>=2: d["choices"]["fighting_style"]=["defense"]
            if name=="fighter": d["choices"]["fighting_style"]=["defense"]+(["great_weapon_fighting"] if level>=7 else [])
            for k in ("cantrips","prepared_spells","spellbook"):
                if k=="cantrips" and "spells" in sheet: d["choices"][k]=[n for n in sheet["spells"] if _spells()[n]["level"]==0]
                elif k in sheet: d["choices"][k]=sheet[k]
            d["choices"]["expertise"]=sheet["expertise"]
            if name=="rogue" and level>=5: d["choices"]["cunning_strike"]=["poison","trip"]
            if name=="cleric": d["choices"].update(divine_order="protector",blessed_strikes="potent_spellcasting")
            (folder/f"{name}_{level}.yaml").write_text(yaml.safe_dump(d,sort_keys=False),encoding="utf-8")


if __name__=="__main__": write_presets()
