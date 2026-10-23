"""Source-reviewed additions from the Step 3 scope correction."""
from .spell_catalog import base, sources, block, single, area, condition


def translations():
    raw = sources(); out = []
    omissions = {
        'Speak with Plants': 'Plants can create or remove Difficult Terrain. Plant presence, immobile area membership, communication and terrain movement costs require environmental geometry.',
        'Stone Shape': 'Can seal a stone door or make a passage or other shape. Eligible stone objects, dimensions, barrier access and hinges need object geometry; no arbitrary creature removal is invented.',
        'Arcane Lock': 'Locks doors, windows, gates, containers or hatches against nonmagical unlocking. Designated access, password proximity and barriers require an object/access model.',
    }
    for name, reason in omissions.items():
        s=base(raw[name]);s['unsupported']=[reason];out.append(s)
    s=base(raw['Create or Destroy Water'])
    s['choices']=[{'id':'mode','options':['rain','destroy fog'],'when':'on_cast'}]
    b=block(target=area('cube',30),effects=[{'extinguish':{}}]);b['if']='$mode == rain'
    s['effects']=[b]
    s['scaling']={'upcast':{'per_slot_above':1,'changes':[{'block':'main','area_size_add':5}]}}
    s['unsupported']=['Rain douses exposed burning combatants in the chosen volume. Container water quantities, fog-volume destruction and object flames need environmental geometry; destroying fog does not dispel the spell producing it.']
    out.append(s)
    s=base(raw["Nystul's Magic Aura"])
    types='aberration beast celestial construct dragon elemental fey fiend giant humanoid monstrosity ooze plant undead'.split()
    s['choices']=[{'id':'type','options':types,'when':'on_cast'}]
    s['effects']=[block(target={**single('willing'),'eligible_if':'target.actual_creature_type != $type'},effects=[{'type_mask':{'type':'$type'}}])]
    s['unsupported']=['Mask affects spell and magical-effect type checks, not actual creature type or mundane attacks. False Aura needs an object/magic-detection model; repeated daily permanence requires a calendar.']
    out.append(s)
    s=base(raw['Modify Memory'])
    b=block(target={**single('visible'),'eligible_if':'target != caster'},save='wis',effects=[condition('charmed',ends_on_damage='any',ends_spell=True,ends_on_spell_targeted=True),{'apply_condition':{'condition':'incapacitated'},'requires_condition':'charmed'}])
    b['save']['advantage_if']='target.team != caster.team'
    s['effects']=[b]
    s['unsupported']=['Memory content, hearing/language, descriptions and the longer higher-slot recall windows require social/time adjudication. Combat Charmed, dependent Incapacitated and ending on damage or another spell targeting execute.']
    out.append(s)
    return out
