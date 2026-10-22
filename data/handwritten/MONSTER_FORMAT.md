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
- `limited_uses`: resource-name-to-maximum-count map (starts full). Legacy
  integer counters remain supported; explicit recovery mappings and character
  Hit Dice are documented in `CHARACTER_FORMAT.md`. Monsters are constructed
  fresh for each day encounter, not carried through party rests.
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
Channel Divinity's two-use counter and rest recovery are tracked; its effects
and other omissions are explicit in the Cleric sheet. See `CHARACTER_FORMAT.md`
for the fixed character additions and day-file contract.

## Step 2: XMM imports and minimal combat extensions

The roster now contains **66 additional XMM creatures (70 total)**. The exact
names live in `engine.monster_import.STEP2`; filenames are lowercase names with
spaces replaced by underscores. All source records must say `source: XMM`.
No 2014 MM fallback or synthesized spell declaration is used.

### Deterministic import and drift gate

```powershell
& C:/Users/xgxxg/anaconda3/python -m engine.monster_import --name 'Young Black Dragon'
& C:/Users/xgxxg/anaconda3/python -m engine.monster_import --check
& C:/Users/xgxxg/anaconda3/python -m engine.monster_import --check data/handwritten/monsters/troll.yaml
```

`--check` strictly loads the reviewed YAML, reparses the local source, reports
field-path differences, and exits 1 on drift. It checks structured statistics,
all parsed weapon damage components (including flat riders), hit bonuses/reach,
simple routines, save DCs/damage/geometry, recharge, daily counters, parsed
Regeneration/Undead Fortitude/Parry numbers, spell statistics/levels/shared pools,
and simple legendary options/costs/budgets. Hand-added conditions cannot hide a
missing damage component. This is not a source hash or a second stored numeric
snapshot. It intentionally cannot verify arbitrary prose interpretation: those
mechanics also have behavioral tests. Unresolved spatial target counts (Engulf,
Whelm) are hand decisions rather than numbers inferred from nonexistent geometry.

`movement_modes` records unconditional numeric walk/fly/swim/climb/burrow speeds;
`speed` remains walking speed. Conditional modes/defenses are unsupported text,
not executable unconditional benefits. Movement, flight and hover still do not
simulate positions. `size` is T/S/M/L/H/G (a variable-size humanoid uses M).
Explicit initiative totals override Dex, otherwise proficiency multipliers or
an explicit initiative skill supply the extra bonus. Save totals are never
replaced by inferred proficiency totals.

`engine.step2.supplement` is the reviewed, explicit hand-finishing ledger. Running
`python -m engine.step2 --write` regenerates only the 66 new YAML sheets. Source
parsing and review decisions are separate; neither command edits spell files.

### Additions and their first users

| Addition | Contract and execution | Needed by |
| --- | --- | --- |
| Per-block save DC | Optional `save.dc` overrides sheet `spell_dc`, including repeat saves; golden spell blocks omit it and are unchanged. | Adult Red Dragon (breath DC 21, spells DC 20), Aboleth |
| Weapon primitives and save riders | `attacks[].effects` may also apply existing condition/status/advantage primitives. Optional `riders` is a list of complete blocks, resolved only on a confirmed hit. Damage remains batched with that hit. `advantage_if: grappled_by_self` is checked against actual condition sources. | Ghoul/Ghast Claw, Wolf, Worg, Bugbear Warrior/Stalker |
| Attack limits | `recharge` and `resource` also work on individual weapon attacks, using the same ready/resource accounting as actions. | Minotaur of Baphomet's Gore |
| Alternative routines | `routines: [[name, ...], ...]` lists legal complete routines; each name is an attack, action or prepared spell. The policy selects one. Embedded options do not cost an extra normal action. | Bandit Captain, Chain Devil, Vampire Spawn, Aboleth |
| Replacement | `replacements: [name, ...]` allows at most one replacement of the last routine attack. Granted single-attack actions do not get this replacement or expand into a full routine. | Gladiator, Pirate, Wight, Adult Red Dragon |
| Action duration | Optional `duration` uses existing duration syntax. Omitted remains instantaneous; `special` retains source/bindings until effects end. Only matching `on_cast` blocks run immediately; recurring blocks use the normal dispatcher. | Engulf, Whelm, Spores, Scare |
| Passive and turn-triggered traits | `passive: true` installs event blocks at combat creation. `trigger: creature_turn_start` resolves an aura only for its covered triggering creature; `enemy_turn_start` is the policy's hostile-only reaction opportunity. Reaction triggers spend the reaction. | Fire Elemental aura; Ghast/Hezrou Stench; Chain Devil Unnerving Gaze |
| Source-aware predicates | `has_condition(name)`, `has_condition_from(name, caster)`, `has_status_from(name, caster)` are safe declarative creature methods. Optional `target.eligible_if` filters before policy selection; `target.max_size` filters size. | Vampire Bite, Consume Memories, source-specific Stench/Glare immunity |
| Grapple/escape | `apply_condition.escape_dc` offers an action-cost Str/Dex ability check for Grappled. `max_size` enforces size; `linked: true` releases effects when the source is unavailable/incapacitated. Engulf instead uses independent `status: {id: engulfed, data: {escape_dc: 12}}` with a Strength-only escape. | Bugbears, Vampire Spawn, Aboleth, Chain Devil, Cube, Water Elemental |
| Capacity | Condition `capacity` is a number of occupied slots; optional `large_cost` charges that many slots for Large targets. Same-source reapplication replaces its old grab rather than stacking duplicate grapples/ticks. Linked restraint is guarded by an actual successful grapple. | Aboleth's four tentacles; two vampire claws/chains; Barbed Devil's claws; Cube (4 slots, Large costs 4), Whelm (2 slots, Large costs 2) |
| Destructible restraint | `apply_condition.obstacle: {ac, hp, vulnerabilities, immunities}` creates an abstract damageable restraint. The trapped creature can spend its Attack action cutting it; normal hit rolls, restrained disadvantage, attacks and mitigation apply. HP persists until destroyed. No roster creature or invented escape save is added. | Giant Spider Web (AC 10, HP 5) |
| Staged condition | `upgrade_on_failure` on a repeat-save condition replaces that condition on the next failed repeat, removing further repeats. A success removes that source's target-local effects. | Basilisk's Restrained -> Petrified |
| Domination | `apply_condition.control: true` switches the recipient to the caster's team, restores it when removed, and is not ended merely by source incapacitation. `repeat_on_damage: true` repeats its Wisdom save on damage. | Aboleth Dominate Mind |
| Shared innate pools | `spell_resources: {spell: counter}`, `spell_levels: {spell: level}`, `spell_costs: {spell: action\|bonus_action\|reaction}` reference golden spells with printed casting level/cost and shared daily uses. Level without a counter means at will; no spell slots are invented. | Mage Protective Magic and level-4 Fireball; Priest Divine Aid; Adult Red Dragon |
| Unsupported spells | `unsupported_spells: [exact names]` lists every source spell absent from the golden set. Short `unsupported` notes identify omitted tagged damage/conditions/saves. Other executable choices remain usable. | Mage Apprentice, Imp, Quasit, Stone Golem, all other casters |

New monster feature fields are **strictly enumerated**, not arbitrary trait names
with implicit behavior. They are contained in `features`:

| Key | Semantics / parameters | Needed by |
| --- | --- | --- |
| `pack_tactics: true` | Attack advantage when another living, non-incapacitated ally has a melee attack. With no grid, such an ally is assumed engaged in melee; a ranged-only ally does not qualify. | Tough, Wolves, Kobold/Hobgoblin Warriors, Hell Hound |
| `magic_resistance: true` | Advantage on magical saving throws. Spell blocks and their repeat saves supply the magical context; ordinary concentration/weapon/action saves do not acquire it. The direct save API also accepts `magical=True`. | Imp, Quasit, Stone Golem, devils, Vrock, Hezrou |
| `sunlight_sensitivity: true` | Attack/check disadvantage when the caller sets `combat.sunlight = True`; standard dry encounters use false. | Kobold Warrior, Specter, Wight, Wraith, Vampire Spawn |
| `bloodied_frenzy: true` | Attack/save advantage while HP <= half maximum. | Berserker |
| `evasion: true` | For Dex half-damage saves: no damage on success, half on failure; failed-save non-damage riders still apply. Disabled while incapacitated. | Assassin |
| `parry: N` | Policy may spend one reaction to negate a pending noncritical melee hit only if +N AC would turn it into a miss. AC is not changed for other attacks. | Bandit Captain/Knight/Warrior Veteran (2), Gladiator (3) |
| `regeneration: {amount, blocked_by, at_zero}` | Heal at turn start; taking nonzero listed-type damage disables the next such heal only. `at_zero` allows recovery from 0 and prevents premature encounter victory; blocked regeneration at 0 on its turn is final. | Troll: 15, [acid, fire], true |
| `undead_fortitude: 5` | On reduction to 0, Con save DC 5 + the complete mitigated damage packet; success leaves 1 HP. No attempt against Radiant damage or critical hits. | Zombie |
| `authority_aura: true` | Captain and abstractly covered allies get attack/save advantage while captain is capable. Allied coverage uses the DMG 10-foot emanation count; origin benefits explicitly. | Hobgoblin Captain |
| `grapple_damage: true` | At own turn start, 1d10 Piercing to actual grapple partners in either direction. | Barbed Devil |
| `redirect_attack: true` | Policy may redirect an incoming weapon/spell attack to a living S/M ally, spending the reaction. No-grid approximation: a selected ally is adjacent. | Goblin Boss |
| `rampage: true` | Immediately after damaging an already Bloodied creature, spend bonus action and the daily Rampage counter for one Rend. | Gnoll Warrior |
| `life_drain: {attacks, type, heal}` | Listed attacks/actions reduce maximum HP by mitigated damage of `type` (`all` also allowed); optional heal returns that much to source. Does not double the target's current-HP loss. | Specter, Wight, Wraith; Vampire Spawn Bite (necrotic, heal true) |

Mummy healing prevention and Bone Devil's temporary healing prevention reuse the
existing `status` primitive with the explicitly implemented `healing_blocked`
marker. Cube's `engulfed` status prevents Verbal spells. The Minotaur's conditional
charge rider uses `caster.has_status(charged)`; the no-grid policy never invents
the required 10-foot movement. Explicit injected charge state is opt-in only.

Capable, ungrappled/unrestrained creatures stand from Prone on their turn using
abstract available movement. Escape/destruction attempts cost an action, not a
free end-turn save. Ally rescue, precise grab/release positioning, line of sight,
cover, movement-triggered damage, environmental water/sunlight damage, suffocation,
corpse/limb spawning, and long-timescale curses/restoration remain recorded in
individual `unsupported` notes. Known issue #7 (Petrified incoming advantage and
Poisoned immunity; Invisible initiative advantage) is still an engine limitation,
not an invented monster mechanic.

### Legendary actions and resistance (lair-free)

```yaml
legendary:
  uses: 3
  options:
  - name: Pounce
    cost: 1
    attacks: [Rend]
  - name: Fiery Rays
    cost: 1
    spell: Scorching Ray
    once_per_round: true
limited_uses:
  legendary_resistance: 3
```

An option contains exactly one of `attacks`, complete effect-block `effects`, or
`spell`; optional `heal: 1d10` is used by Aboleth Psychic Drain. Its
`requires_bound_target: true` checks for an actual source-bound Grappled/Charmed
recipient before offering the option. The default policy scores eligible options;
`Policy.legendary_action` can choose a different option or return `None`.

Budgets start full, reset at the **start of that monster's turn**, and spend only
at the **end of another creature's turn**, after that turn's effects/repeat saves
and expiration. At most one option is chosen at each such opportunity. They do
not consume normal actions/reactions or advance the turn clock. Incapacitated or
unavailable monsters cannot use them. `once_per_round` means once between own
turn starts, not once per global initiative-round number.

`Policy.legendary_resistance` receives a failed save (including an automatic
failure) and may choose success, spending one daily use; default accepts while
uses remain. Both Aboleth and Adult Red Dragon use the **3/day outside-lair**
number. Lair actions/4-use lair budgets are excluded. Adult Red Dragon's
Commanding Presence is explicitly unsupported until Command enters the golden
set; Fiery Rays and Pounce execute. The young dragons receive neither mechanic.

### Validation and measurements

`tests/test_engine_step2.py` strictly loads every sheet, checks fresh-source
numeric fidelity, audits damage/condition/save source tags (including Spell and
Legendary suffixes), compares neutral weapon-routine DPR, gives each creature
three policy turns, and explicitly exercises every alternative attack/action/
trait and every declared feature/legendary option with seeded log assertions.
Targeted tests cover timing/reset/spending, shutoffs, source cleanup, staged saves,
shared spell pools, typed mitigation, and malformed new fields. No existing
statistical tolerances or reviewed spell files are changed.

`python -m engine.step2_report --runs 500 --seed 1` reproduces the separate CR
sanity report and writes `engine/step2_cr.json` and `engine/step2_cr_table.md`.
See `engine/BUILD_REPORT.md`, Step 2, for measurement definitions and outliers.

### Step 2 fix-round additions

- Every supplemented effect block carries `source_ref: "action:ENTRY"` (or
  `trait:ENTRY`, `reaction:ENTRY`, `bonus:ENTRY`), using the exact local XMM
  entry name, including recharge/daily suffixes. Copied legendary payloads name
  the action they invoke. The independent text gate reads tagged DCs, escape
  DCs, tagged damage and printed `N (XdY + Z)` damage, checking dice, bonus and
  type in that entry. Recurring blocks must match a recurring-damage sentence,
  not the entry's initial hit. References cannot silently name another ability.
- Engulf's main block has `admission: {status: engulfed, capacity: 4,
  large_cost: 4}`. This rechecks capacity before **each** target's save/damage.
  Engulfment is independent of Restrained immunity/removal and grapple cleanup;
  it drives occupancy, recurring acid, Verbal blocking and Strength-only escape,
  including the default policy's escape attempt. Reapplication does not stack.
  The cube's incapacitation does not release occupants. `condition` admission
  remains available for condition-bound occupancy (mutually exclusive with `status`).
- The source-number gate also validates healing (including legendary options),
  obstacle AC/HP, declared capacities, target counts/radii, duration rounds,
  next-attack uses and legendary costs. Minotaur's opt-in charge checks
  `target.size in [T, S, M, L]` for both its damage rider and Prone consequence.
- A status can declare `data: {requires_condition: poisoned}`. It is effective
  only while an active condition from the **same effect instance** exists.
  Infernal Sting uses this for healing prevention; unrelated Poisoned does not
  sustain it, and condition immunity/removal immediately disables the ban.
- `{burning: {}}` is a reusable creature primitive, independent of spell or
  monster names. It creates one nonstacking Burning hazard: 1d4 Fire damage at
  the start of that creature's turns, surviving the igniting instance's end or
  source death (local XPHB Burning, p. 362). `Combat.ignite` exposes the same
  operation. `Combat.extinguish(actor)` spends that actor's action and gives it
  Prone; it requires a capable creature able to become Prone. Explicit
  `method="doused"`, `"submerged"`, or `"suffocated"` clears the hazard without
  an action (the caller must supply that environmental event). Default policy
  extinguishes itself before attacking. Terrain and object ignition are still
  not simulated.
- Target-turn reference blocks resolve only the triggering bound recipient.
  Reapplication of the same named condition effect from the same caster
  replaces that recipient's old instance effects, rather than stacking ticks.
  Free passive auras persist through incapacitation; action/reaction traits and
  explicit source capability exclusions still obey it.
