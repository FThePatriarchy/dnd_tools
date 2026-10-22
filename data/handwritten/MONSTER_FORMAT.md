# Combat stat sheets (monsters and fixed characters)

Distances are feet. Sources are `XMM` (2025 Monster Manual) or `XPHB`.
These are fixed sheets, not a class/level progression format. They use the
spell primitives and full effect-block structure from `FORMAT.md` unchanged.

## Required fields

`name`, `source`, `max_hp`, `ac`, `abilities` (all six abbreviated scores),
`speed` (walking), `creature_type`, `proficiency_bonus`.

## Optional fields

- `cr`, `hp_formula`: imported provenance; HP uses the printed average.
- `level`: character level for cantrip scaling; defaults to 1 for monsters.
- `alignment`: `good | neutral | evil` (defaults to neutral).
- `initiative_bonus`: extra initiative beyond Dexterity; the dragon adds PB.
- `save_proficiencies`: ability names; `save_bonuses`: explicit total bonuses
  overriding score + proficiency. Both are imported from structured saves.
- `resistances`, `immunities`, `vulnerabilities`: damage-type lists;
  `condition_immunities`: official condition names.
- `spell_ability`, `spell_dc`, `spell_attack_bonus`, `spell_slots` (integer
  level-to-remaining-count map), `spells` (exact golden-set names).
- `limited_uses`: resource-name-to-remaining-count map.
- `innate_spells`: exact spell-name-to-daily-maximum map; every entry also
  requires a `spells` entry and a same-named `limited_uses` counter. These
  casts spend that counter, not a slot, at the spell's base level. A countered
  innate cast still spends its daily use. No unreviewed spells are synthesized.
- `unsupported`: human-readable omissions, never executable.

## Weapon attacks and routines

`attacks: [{name, kind: melee|ranged, to_hit, effects, reach_ft?, ability?, mastery?}]`

`effects` is a list of spell `damage` primitives. Same-type components,
including hit riders, combine before resistance/vulnerability. Different types
are mitigated separately; the complete attack causes one concentration check.
Primitive `if` guards use the same expression evaluator as spells, with
`caster`, `target`, `attacker`, `defender`, `attack`, `event` and `trigger`
context. The importer emits `if: attack.advantage` for Goblin Warrior's extra d4;
other validated expressions (including `false`) are honored too.

`mastery: graze|vex|sap` is optional. Graze uses the named `ability` (default
Strength) on a miss; Vex benefits the same wielder's next attack against the
same target through the end of its next turn; Sap gives the target's next attack
disadvantage before the start of the wielder's next turn. The supplied build
uses Graze. Reach is recorded; the engine treats melee attacks as within 5 ft
for prone/paralysis/unconsciousness, not as a simulated distance.

`multiattack` is an ordered list of attack names, with repetition. If absent
or empty, repeat the first weapon `extra_attack` times (default 1). Each attack
selects an available enemy and rolls separately. Haste restricts its separately
granted Attack action to one attack, not this complete routine.

## Actions and traits

Both `actions` and `traits` contain:

```yaml
- name: Fire Breath
  cost: action                 # action | bonus_action | reaction | free
  recharge: 5                  # optional: ready initially; d6 >= 5 at turn start
  # resource: second_wind      # optional: spend matching limited_uses counter
  effects: []                  # complete spell-format blocks, normally on_cast
```

Action blocks use the creature's `spell_dc` for saves even for nonspell
abilities; Fire Breath therefore sets that sheet's DC to 17. These actions
are not spells and do not trigger Counterspell or consume a spell slot.
`Combat.use_action` executes either an action or a trait. Recharge only rolls
while expended, once per creature turn, including turns it cannot act.

`grants_action: true` requires an empty effects list and replaces effects for Action Surge. The engine tracks
that particular action as unable to cast a spell (the 2024 Magic restriction).
`restricted_to` on a trait records `hide|disengage|attack` choices. Nimble
Escape's default no-grid choice is Disengage; its status is recorded, with
no opportunity attacks or movement modeled. Hide/concealment is unsupported.
Its exact next-turn marker lifetime is bookkeeping only, not extra protection.
Explicitly timed action effects survive the instantaneous action instance.

`limited_uses.legendary_resistance`, if supplied, automatically turns failed
saves into successes while uses remain. None of these four XMM stat blocks
has Legendary Resistance; no such trait was invented for the young dragon.

## Import/review workflow

`python -m engine.monster_import --name Ogre` prints deterministic base YAML
from `raw_data/bestiary/bestiary-xmm.json`; it never overwrites reviewed files.
The parser reads structured AC, HP, abilities, saves, defenses, type, CR/PB,
initiative proficiency, and tagged weapon hit/damage expressions. Conditional
defenses are reported as unsupported, not silently treated as unconditional.
Unparsed weapon damage is a hard error. Nonweapon actions/traits/spellcasting
are explicitly flagged for manual review. The committed supplements supply:

- Goblin Warrior: Nimble Escape (and its no-grid limitation).
- Ogre: no extra mechanics needed.
- Cultist Fanatic: Hold Person 1/day and Spiritual Weapon 2/day via golden
  spell references; Light, Thaumaturgy and Command explicitly unsupported.
- Young Red Dragon: three Rends; Fire Breath, Dex DC 17, 16d6 fire, half on
  success, 30-foot cone, Recharge 5–6. No older-edition bite/claw routine.

The Fighter uses Chain Mail + Defense (AC 17), Strength 18, Constitution 16,
49 HP, Greatsword/Graze, two attacks, Second Wind 3 uses (1d10+5), Action Surge
1 use. The Cleric uses Protector/Chain Mail + Shield (AC 18), Wisdom 18,
Constitution 14, 38 HP, DC 15 / +7, slots 4/3/2. No subclass is modeled.
Channel Divinity and other omissions are explicit in the Cleric sheet.
