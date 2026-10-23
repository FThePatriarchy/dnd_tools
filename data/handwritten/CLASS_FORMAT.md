# Single-class progression (XPHB, levels 1–10)

`classes/{fighter,rogue,wizard,cleric}.yaml` is strictly validated by
`engine.classes.load_class`. Only the named XPHB class and subclass are allowed.
Each feature has `name`, `level`, `origin: class|subclass`, and executable
`mechanics`/`actions`, or `unsupported` with a reason. Mixed features can have
both an implementation and an explicit spatial/social omission. Wrapper
features delegate to their named children; they do not grant duplicate effects.

Each `levels` row has proficiency bonus, hit die, features **gained** at that
level, recoverable `resources` (CHARACTER_FORMAT convention), weapon mastery
count, cantrips, prepared spell count, and integer-keyed `slots`. Rogue also has
Sneak Attack dice. Subclass/ASI levels are explicit. Spell counts are the 2024
fixed table, **not** ability modifier + level. Always-prepared domain spells do
not consume this count. No feature above level 10 is backported (notably Fighter
Studied Attacks is level 13, not within this milestone).

`actions` reuse complete existing creature actions and effect blocks. Two
substitution symbols needed by Second Wind/Divine Spark are `class_level`
(healing bonus) and `spark_dice` (d8 count at the selected level). `sneak_dice`
selects the row's Sneak Attack dice. Substitution happens before ordinary sheet
validation. `spell_mod` retains its existing meaning. No arbitrary expressions
or unrecognized mechanics are executable. Non-block rule hooks live in a
strictly enumerated `mechanics` map and become sheet `features`; their initial
users and precise timing are documented below as stages land.

The independent local source checker reads only `source: XPHB` class,
classFeature, subclass and subclassFeature records. It verifies numeric leaves,
including numbers embedded in strings and tables, rather than trusting a hash.
Universal core rules absent from those records must be an explicit, justified
allow-list, not silently asserted to have come from class prose.

## Scope

Species, backgrounds, multiclassing, equipment purchases and feats other than
Ability Score Improvement are outside scope. Fighting Style choices implement
the referenced styles rather than general feat machinery. Ability input is
pre-ASI; HP uses maximum hit die at first level and fixed average thereafter.
No grid, concealment, movement or opportunity attacks are fabricated.

## Minimal extensions and their first users

| Addition / first user | Execution |
|---|---|
| Critical threshold / Champion | `improved_critical`: weapons only, qualifying natural rolls also hit automatically; spell attacks retain natural 20. |
| Initiative / Champion, Assassin | `initiative_advantage`; Remarkable Athlete adds Athletics advantage. Assassinate grants attack advantage in round one against creatures without a turn; first-round Sneak Attack adds Rogue level as undoubled damage. |
| Failed rolls / Fighter | Tactical Mind rolls d10 after a failed check, spending Second Wind only on success. Indomitable spends its daily counter and rerolls with class level added, retaining roll flags. Automatic save failures cannot be rerolled away. Heroic Warrior grants Inspiration at own turn start; policy rerolls failed D20s, not damage dice. |
| Sneak Attack / Rogue | One use per global turn, with a Finesse/ranged weapon and advantage or a capable melee-equipped ally without net disadvantage. No-grid approximation: that ally is adjacent to the target, as for Pack Tactics. Damage joins the attack packet and doubles on criticals. |
| Cunning Strike / Rogue | One configured Poison/Trip/Withdraw option, one d6 removed before rolling; effect after damage. Poison requires a Poisoner's Kit, Con save with end-turn repeats, one minute. Trip: Dex save, Large or smaller. DC = 8 + Dex modifier + PB. Withdraw records permission only; no displacement or invented protection. |
| Uncanny Dodge / Rogue | Visible attacker's confirmed hit, one available reaction, halve the complete packet rounded down before typed mitigation. Odd mixed-type remainders are distributed in packet order. No use while incapacitated/reactions prohibited. |
| Steady Aim / Rogue | Existing one-use advantage and speed modifier, ending this turn. Explicit `statuses.moved_turn == combat.turn_index` prevents activation; default no-grid turns assume no movement. Roving Aim omits only the speed penalty. |
| Skills / Expertise, Scholar, Reliable Talent | New sheet lists `skill_proficiencies`, `expertise`; Expertise requires proficiency. Named proficient checks add PB (twice with Expertise); Reliable Talent floors their D20 at 10. Thaumaturge adds max(1,Wis) to Intelligence Arcana/Religion checks. |
| Potent Cantrip / Evoker | Damage-only half damage on misses/successful saves; never copies riders or doubles existing native half damage. |
| Sculpt Spells / Evoker | Choose up to 1 + cast spell level other visible creatures affected by an Evocation save block. Automatic success, no damage when success normally halves. Caster cannot be sculpted. AI uses actual area membership/exclusion quota, including injected friendly spill-over. |
| Empowered Evocation / Evoker | Int modifier to one damage roll per cast; shared rolls reuse that value. Existing independent per-target area rolls remain independent, so one receives the bonus, not all separately rolled recipients. |
| `heal_pool` / Preserve Life | `{amount, cap: half}` in an ordinary block; finite per-instance pool allocated in selection order, capped at floor(max HP/2). Zero HP is a legal healing target. `life_pool` substitutes 5 × class level. |
| Sear Undead / Cleric | Shared max(1,Wis modifier)d8 to failed Turn saves, before installing conditions; cannot break that turn. Later damage does. Source incapacity/death uses existing linked cleanup. Fleeing movement is unsupported. |
| Magical actions / Channel Divinity | Optional action `magical: true` marks a nonspell Magic action. Its saves/conditions honor Magic Resistance, magical defenses and type masks, but it is not a spell/Counterspell trigger. Action Surge cannot supply it. |
| Life healing / Life Domain | Disciple: 2 + expended slot level on cast-turn healing. Blessed Healer: that amount to caster once after a slot-cast spell actually heals someone else. Channel Divinity/Divine Intervention do not qualify. |
| Blessed Strikes / Cleric | Divine Strike: own-turn weapon hit, once per turn, Radiant d8 in critical packet. Alternative Potent Spellcasting adds Wis to Cleric cantrip damage. Builder enforces exclusivity. |
| Rest callbacks / Wizard | Arcane Recovery once per long rest, slot levels sum <= ceil(level/2), no sixth-level slots. Memorize Spell may exchange one prepared leveled spell for another in the book. Both validate choices and optionally append structured entries to `take_rest(..., log=trace)`. |
| Masteries / Tactical Master | Existing Sap/Vex/Graze. Slow: nonstacking -10 speed until attacker's next turn. Topple: Con vs 8 + attack ability + PB. Push: permission marker only, no position. Tactical Master offers Sap/Slow/Push instead of a known mastery per attack. |

Four Fighting Styles are selectable: Defense, Archery, Dueling, Great Weapon
Fighting. The first three modify builder equipment math. GWF uses the 2024
minimum of 3 per damage die, **not** the 2014 reroll. Other styles are rejected.
Styles, equipment, ASI and core formulas are reviewed builder rules; class
records reference feats but do not contain their numeric text. They are not
claimed as extracted class-file numbers.

## Builder and build recipes

`build(class_name, level, subclass, abilities, equipment, choices)` returns a
validated ordinary character sheet; optional arguments have deterministic
defaults. `load_build("wizard_7")` loads a recipe. A recipe requires exactly
`class`, `level`, `subclass`, `abilities`, `equipment`, `choices`. Both CLIs
accept build stems as party names; existing fixed stems take precedence.
Subclass is dormant before level three. Only the four named subclasses exist.

Choices: `ability_method`, `asis`, `fighting_style`, `weapon_masteries`,
`skills`, `expertise`, `cunning_strike`, `cantrips`, `prepared_spells`,
`spellbook`, `divine_order`, `blessed_strikes`.

- Input abilities are pre-ASI. Default `standard_array` is a permutation of
  15,14,13,12,10,8. `point_buy` uses scores 8–15 and at most 27 points.
  Explicit `assigned` accepts externally assigned 3–20 scores for compatibility
  with fixed sheets, whose background bonuses cannot come from point buy alone.
  Every earned ASI allocates exactly two points, maximum score 20. Other feats,
  backgrounds and species are not implemented or silently added.
- Equipment presets: `chain_greatsword`, `chain_sword_shield`, `leather_archer`,
  `studded_rapier`, `studded_shortbow`, `unarmored_staff`, `chain_shield`,
  `scale_shield`. Training is checked. AC: chain 16; studded 12 + Dex; scale
  14 + min(2,Dex); none 10 + Dex; shield +2; applicable Defense +1. Chain with
  Str below 13 costs 10 speed. Presets never combine shield/two-handed weapon.
  Mage Armor must actually be cast and spend a slot; builder never grants it
  free AC. Equipment prices/inventory are not simulated.
- HP applies final Con modifier retroactively at all levels: max die first,
  fixed average thereafter. Weapon and spell attack/DC math uses final scores.
- Select no more than the mastery table's count, only supported proficient
  weapons. Rogue Expertise: two skills, four at sixth. Scholar: one proficient
  Wizard skill at second. Named tool checks use the same check API.
- Cantrip/prepared counts are exact. Existing specs only. The supplied raw spell
  JSON has no class-list metadata: `builder.SPELL_LISTS` is an explicit reviewed
  membership whitelist, not an inference from school/older-edition sources.
  Missing specs are rejected. Domain spells are additional and always prepared;
  missing domain specs are recorded as unsupported, never synthesized.
- Wizard book: six initial spells, two per subsequent level, plus Savant's
  Evocation-only additions. Bipartite matching checks legal acquisition levels
  and bonus slots. Purchased copies are outside scope. Prepared spells must be
  in the book. Sheet `prepared_spells`/`spellbook` metadata enables rest swaps.
- Divine Order: `protector|thaumaturge`; Blessed Strikes:
  `potent_spellcasting|divine_strike`. Divine Intervention API:
  `combat.divine_intervention(actor, spell, targets=None, choices=None)`;
  existing Cleric spell of levels 1–5, not a reaction; one action and daily use,
  no slot/materials. Default AI uses it once slots are exhausted.

Preset builds deliberately omit background/species boosts and are weaker than
optimized PCs. Their core/equipment constants are covered by independent math
tests, separately from the numeric class-source audit.

## Independent source audit

`python -m engine.step4_report --source-only` verifies feature inventory,
progression/resource tables, dice, ranges, durations and numeric parameters
against fresh local XPHB records. No recipe module is imported by the oracle.
Every numeric leaf/key and each digit sequence inside numeric strings receives
a distinct mutation; key collisions are rejected, not skipped. Path-specific
rules prevent an unrelated number elsewhere in prose from validating a mutant.
Allow-list: universal PB omitted from raw tables, zero for absent grants, and
lexical one/once/next. `engine/step4_validation.json` records counts. Raw sources
and reviewed spell/monster files are never rewritten.
