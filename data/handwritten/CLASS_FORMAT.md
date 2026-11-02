# Single-class progression (XPHB, levels 1–20)

`classes/{fighter,rogue,wizard,cleric,barbarian,paladin,warlock,bard,monk,ranger,druid,sorcerer}.yaml` is strictly validated by
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
not consume this count. Rows cover levels 1–20 (2026-11-01). A feature above
level 10 is implemented, a builder choice, a progression repeat, or
`unsupported` with the reason "Not implemented yet (high-level features are in
progress)" until its class is done; see "Levels 11–20" below.

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

Species, backgrounds, multiclassing and equipment purchases are outside scope.
Feats are limited to the eight listed under "Feats" below (2026-10-26, extended 2026-10-31); any other
feat is rejected. Fighting Style choices implement
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

## Feats (2024 rules)

A General feat replaces an earned ASI: `asis: {4: {feat: great_weapon_master,
ability: str}}`. The feat's +1 goes to one of its listed abilities (capped at
20), its prerequisite is checked against the scores at that level, and a feat
cannot be taken twice. Alert, Lucky and Tough are Origin feats: `origin_feat: alert`, at any
level; a build has at most one. Each feat becomes a sheet feature flag.

| Feat | +1 to | Prerequisite | Simulated | Not simulated (no grid) |
|---|---|---|---|---|
| Great Weapon Master | Str | Str 13 | +PB damage on a hit with a Heavy weapon (greatsword, longbow) made in the Attack action on the attacker's turn; Hew: after a critical hit or a kill with a melee weapon, one attack with the same weapon as a Bonus Action (once per Bonus Action) | — |
| Sharpshooter | Dex | Dex 13 | the +1 only | ignoring half and three-quarters cover; no disadvantage in melee or at long range. By default cover and melee adjacency are not modelled, so Sharpshooter is valued as +1 Dex. With `DayOptions.cover` it ignores row-based half cover and the in-melee disadvantage for weapon attacks; monsters never have cover, and range bands are not modelled. |
| War Caster | Int, Wis or Cha | Spellcasting | advantage on Constitution saves to maintain Concentration | Reactive Spell (no opportunity attacks); somatic components with full hands |
| Polearm Master | Str or Dex | Str or Dex 13 | Pole Strike: after the Attack action with a Quarterstaff, Spear or Heavy and Reach weapon (the glaive), one attack with the same weapon as a Bonus Action, d4 Bludgeoning plus the usual modifier. Great Weapon Master's +PB does not apply to it (it is not part of the Attack action). | Reactive Strike (no movement into reach) |
| Resilient | the chosen ability | — | +1 and saving-throw proficiency in one ability whose save the class lacks | — |
| Alert (Origin) | — | — | +PB to initiative; Initiative Swap at initiative: trades places with the slowest ally with spell slots who would act later | — |
| Lucky (Origin) | — | — | PB Luck Points per long rest. After a failed D20 Test that a 20 would pass, one point rolls another d20 and keeps the higher: Advantage taken once the roll is known, which is how a table usually plays it. Saves and death saves always use a point; attack rolls and checks only while another point stays in reserve. | Imposing Disadvantage on an attack against you |
| Tough (Origin) | — | — | +2 HP maximum per character level | — |

The greataxe, greatsword, maul, glaive and longbow carry the 2024 `heavy` property; the glaive also has
`reach` (reach 10 ft, Graze mastery; kits `chain_glaive` and `unarmored_glaive`). Sheet attack
properties accept `heavy` and `reach`.

## Builder and build recipes

`build(class_name, level, subclass, abilities, equipment, choices)` returns a
validated ordinary character sheet; optional arguments have deterministic
defaults. `load_build("wizard_7")` loads a recipe. A recipe requires exactly
`class`, `level`, `subclass`, `abilities`, `equipment`, `choices`. Both CLIs
accept build stems as party names; existing fixed stems take precedence.
Subclass is dormant before level three. Only the eight named subclasses exist.

Choices: `ability_method`, `asis`, `fighting_style`, `weapon_masteries`,
`skills`, `expertise`, `cunning_strike`, `cantrips`, `prepared_spells`,
`spellbook`, `divine_order`, `blessed_strikes`, `background`, `origin_feat`,
`invocations`, `magical_discoveries`.

- Input abilities are pre-ASI. Default `standard_array` is a permutation of
  15,14,13,12,10,8. `point_buy` uses scores 8–15 and at most 27 points.
  Explicit `assigned` accepts externally assigned 3–20 scores for compatibility
  with fixed sheets, whose background bonuses cannot come from point buy alone.
  Every earned ASI allocates exactly two points, maximum score 20, or is replaced
  by one of the supported General feats (see "Feats"). Other feats and species are
  not implemented or silently added.
- Equipment presets: `chain_greatsword`, `chain_sword_shield`, `leather_archer`,
  `studded_rapier`, `studded_shortbow`, `unarmored_staff`, `chain_shield`,
  `scale_shield`. Training is checked. AC: chain 16; studded 12 + Dex; scale
  14 + min(2,Dex); none 10 + Dex; shield +2; applicable Defense +1. Chain with
  Str below 13 costs 10 speed. Presets never combine shield/two-handed weapon.
  Mage Armor must actually be cast and spend a slot; builder never grants it
  free AC, except the explicitly modeled at-will Armor of Shadows invocation
  described below. Equipment prices/inventory are not simulated.
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


## Barbarian (Berserker) and Paladin (Devotion), XPHB 1–10

Both use the same strict declaration/source audit and build recipes as the
original four classes. Standard, casual and optimized builds cover 1/3/5/7/10;
all intervening levels can be built. Reference parties and historical calibration
and Step-4 reports remain the original four PCs. `compare.ROLES` maps both new
classes to the Fighter reference slot. `source_audit(names)` optionally audits
the new declarations without changing the historical report's default cohort.

| Feature | Simulated | Not simulated / approximation |
|---|---|---|
| Rage | Bonus action; 2/3/4 daily uses at levels 1/3/6, regain one on a Short Rest; +2 damage (+3 at 9) on Strength weapon hits; B/P/S resistance; Strength check/save advantage; drops concentration and prevents spells; ends on incapacity | Assumed extended throughout combat, capped at 10 minutes; no per-round attack/damage/bonus-action renewal tracking. XPHB actually extends via attack, enemy save or bonus action, not taking damage. Heavy armor is rejected by builder; mid-combat equipment changes unsupported. |
| Unarmored Defense | 10 + Dex + Con, plus shield when equipped | No equipment swapping. Unarmored axe/greatsword/maul and scale greataxe kits added. |
| Reckless Attack / Danger Sense | Policy defaults to Reckless on first weapon attack of own turn; Strength attack advantage and incoming attack advantage until next turn; Dexterity save advantage unless incapacitated | No visibility restriction on Danger Sense (2024). Policy may decline Reckless. |
| Extra Attack / Feral Instinct | Two Attack-action attacks from 5; initiative advantage from 7 | Fast Movement and Instinctive Pounce omitted (no grid). |
| Brutal Strike | From 9, once on own turn, forgo all advantage on a Strength attack without disadvantage; +1d10 on hit, doubled on critical; Hamstring Blow stores nonstacking -15 speed until next turn | Policy defaults to using it. No Forceful Blow displacement; movement penalties have no positional effect. |
| Frenzy | First Strength hit on own turn while raging and Reckless: Rage-bonus count of d6, doubled on critical | No exhaustion cost (2024). |
| Mindless Rage / Retaliation | Charmed/frightened immunity during Rage, removes existing conditions on entering; at 10, reaction melee attack after damage | Retaliation assumes the damaging creature is in melee reach under existing no-grid reachability; ranged separation is not known. No Relentless Rage (11). |
| Weapon masteries | Existing Graze/Topple etc.; greataxe Cleave: once per turn, extra attack on a different enemy without positive ability damage modifier | Cleave assumes second enemy within 5 feet of first and in reach. |
| Paladin spellcasting | 2024 half-caster slots starting at 1; Charisma attack/DC; fixed prepared counts 2/3/4/5/6/6/7/7/9/9; existing spell specs only; Devotion oath spells additional; Divine Smite always prepared from 2; flagged in-combat buff EV (also Bard/Warlock) over remaining rounds capped by duration: attack-roll hit gains (weapon or best attack cantrip), weapon enchantment hit/damage gains, AC prevention on front-line allies, recurring temp HP capped by incoming damage; concentration buffs last the expected rounds before a failed DC 10 Constitution save; a buff's slot is charged the Smite it would have powered when slots are scarcer than rounds; bonus-action buffs retain weapon DPR but are charged this turn's Smite | Prepared count is the XPHB table, **not** Cha modifier + level. Blessed Warrior cantrip style, Find Steed/its free cast and exploration preparation changes omitted. |
| Lay on Hands | Bonus action, finite 5 × level pool, partial or full healing including downed PCs, daily recovery; AI prioritizes downed/under-half-HP allies | Touch range assumes ally reachable; removing Poisoned for 5 pool points omitted. |
| Divine Smite / Paladin’s Smite | Actual existing bonus-action spell, only after melee weapon hit; slot upcasting and fiend/undead die; critical doubles dice; same attack damage packet; one free first-level cast per Long Rest from 2; ordinary slot-per-turn, components and Counterspell handling | AI spends free cast first, otherwise slots permitted by strategy; holds a lone slot for a later hit/critical in a two-attack turn. Rationed uses its existing slot-level budget. No unarmed attacks in equipment kits. |
| Fighting Style / Sacred Weapon | One supported style from 2; Sacred Weapon from 3 consumes Channel Divinity as part of Attack action, adds max(1,Cha) to chosen melee weapon attacks for 10 minutes; two daily CD uses, regain one on Short Rest | Sacred Weapon light and optional Radiant damage conversion omitted; carrying/dropping weapons unsupported. Divine Sense and Abjure Foes omitted. |
| Aura of Protection / Devotion / Courage | From 6, max(1,Cha) to saves, strongest aura only; charmed immunity from 7 and frightened immunity from 10, suppress existing conditions; inactive while source incapacitated/dead | Same `area("emanation",10,ally_count)` coverage as Aura of Authority: source plus first covered allies in combatant order, no grid. Original team membership is used so existing charms can be suppressed. No Radiant Strikes (11). |

Rage/Sacred Weapon are encounter statuses and are cleared by the ordinary
encounter cleanup. Finite pools, slots and daily counters persist between
encounters and use the existing rest machinery. Long-lived positioning and
manual out-of-combat weapon handling remain outside this model.


## Warlock (Fiend) and Bard (Lore), 2024

Class declarations cover levels 1-10; standard/casual/optimized build files
cover 1, 3, 5, 7 and 10. Reference parties remain Fighter/Cleric/Rogue/Wizard:
Warlock replaces the Wizard slot, Bard the Cleric slot in comparison variants.
All spells must already have a handwritten executable spec.

| Feature | Simulated | Deliberate omissions / choices |
|---|---|---|
| Pact Magic | Charisma, XPHB prepared/cantrip counts; one level-1 slot at L1, two thereafter through L10; pact level 1/1/2/2/3/3/4/4/5/5. Every slot is at that level, fully restored by short or long rests. | No multiclass slot pool or Mystic Arcanum (L11). Magical Cunning's one-minute rite is skipped, not granted during combat or silently as a short rest. |
| Eldritch Invocations | `invocations` accepts a modeled subset, bounded by the XPHB invocation count: Armor of Shadows at L1; Agonizing Blast and Eldritch Mind require L2. Defaults take all three when eligible. Agonizing Blast adds Cha on each Eldritch Blast hit, including EV; existing beam scaling gives one beam before L5, two at L5-10. Eldritch Mind gives concentration-save advantage. | Armor of Shadows assumes at-will Mage Armor was cast before combat: unarmored AC 13 + Dex, no slot. No Blade/Tome, forced movement, or other invocations; unused selections confer no invented benefit. |
| Fiend spells | Existing patron spell specs are always prepared, separately from the table count. | Missing specs (currently Geas) are reported in the built sheet, never fabricated. |
| Dark One's Blessing | On the Warlock's enemy reduction from positive HP to zero, temp HP = max(1, Cha + Warlock level); replaces only lower temp HP. | The 2024 additional trigger for someone else's kill within 10 feet is omitted without adjacency. |
| Dark One's Own Luck | L6+, max(1, Cha) uses per long rest; after a failed check/save with a deficit <=10, roll and add d10, spend even if it still fails. | No use on guaranteed failures or successful rolls. No initiative use (initiative has no failure DC). |
| Fiendish Resilience | L10 slashing resistance, including magical slashing, through typed mitigation. | Fixed sensible weapon-damage choice; no adaptive enemy knowledge or automatic type switching on rests. |
| Warlock AI | Compares leveled spell damage/control and buffs with the best cantrip; estimates Hex over concentration uptime, otherwise Eldritch Blast. Bonus-action Hex leaves the action for Blast, and pact slots upcast existing spells. | Shared no-grid concentration and remaining-round estimates; no spellcasting during the omitted rite. |
| Bard spellcasting | Simple-weapon training (studded-staff presets, not martial rapiers), Charisma, XPHB full-caster slots, 2/3/4 cantrips and table-fixed prepared counts; Healing Word can revive a downed ally before the action. | No rituals, instruments or exploration skill scenes. |
| Bardic Inspiration | Bonus action, max(1, Cha) uses; d6 / d8 at L5 / d10 at L10. Another ally who can see or hear the Bard gets one die for one hour. Only a failed attack/check/save with a recoverable deficit consumes it; no natural-1 attack rescue. Font at L5 fully restores uses on short rests; long rests always restore uses. | No automatic Font spell-slot conversion. AI distributes to the ally with the greatest expected attack-roll count (low HP breaks ties), after healing/spell bonus actions. No failed-initiative interpretation. |
| Jack of All Trades / Expertise | L2+ half PB on initiative; stacks with Alert's PB. | Other Jack checks and Bard Expertise are omitted; initiative is not a proficient skill. Lore Bonus Proficiencies and L7 Countercharm omitted. |
| Cutting Words | Lore L3+: reaction plus Inspiration use, visible enemy under the shared 60-foot no-grid reach assumption. Subtract the die on a successful attack with margin < die maximum, or a successful check; never negates a natural-20 attack. Critical attack damage can instead be reduced before typed mitigation. | A damage-roll reducer is available to callers; AI's noncritical default is attack interception, not speculative damage reduction. Reserve the last use against healthy allies when a downed/low-HP ally needs protection. No future-turn prediction or positional line-of-sight geometry. |
| Magical Discoveries / Secrets | L6 two distinct `magical_discoveries`, always prepared outside the normal count, selected from supported Cleric/Druid/Wizard spells within available slots (defaults Counterspell and Spirit Guardians). L10 ordinary prepared choices can also use those lists, with Charisma. | Discovery replacements are chosen in each build, not dynamically in combat. No above-slot spells or duplicate discoveries. |
| Shared buff valuation | Builder sets `values_buffs` for Paladin, Warlock, Bard, Monk and Ranger; these classes use `expected_buff_value`, attack gains and concentration horizon. | Smite opportunity costs remain Paladin-only. Cleric/Wizard keep their published AI blind spot, intentionally preserving old results. |

Existing unclocked day cleanup still removes all effects between encounters;
the clocked day runner preserves real deadlines. These classes do not change
that shared lifecycle or any old-class spell/rule behavior.


## Monk (Warrior of the Open Hand) and Ranger (Hunter), 2024

Class declarations cover levels 1-10; standard/casual/optimized builds cover
1, 3, 5, 7 and 10. The independent source checker verifies the XPHB feature
inventory, focus/free-cast counters, prepared counts and slots. Reference
parties remain Fighter/Cleric/Rogue/Wizard: Monk replaces Rogue, Ranger replaces
Fighter. Both classes opt into `values_buffs`; old classes' policies are unchanged.

| Feature | Simulated | Deliberate omissions / choices |
|---|---|---|
| Martial Arts / Unarmored Defense | Unarmored, no-shield staff or mace kits; Dex may replace Str on weapons/unarmed attacks. Unarmed damage d6, d8 at L5 (helper supports d10 at L11, beyond builder scope). Monk weapons use the larger of their normal die and Martial Arts. AC 10 + Dex + Wis. One bonus-action unarmed strike (no Attack action prerequisite). Extra Attack at L5. | Armor/shield/non-Monk kits rejected rather than granting invalid benefits. Flurry is independently available as a bonus action, following its XPHB text. No grapple/shove choice. |
| Monk's Focus | L2+, points equal Monk level; full short/long-rest recovery. Flurry spends one point and the bonus action for two unarmed strikes, three at L10 (Heightened Focus). | No Step of the Wind, jumping, forced displacement or positional movement. Heightened Patient Defense temp HP omitted. |
| Patient Defense | Free bonus-action Disengage bookkeeping, or one focus for Disengage + Dodge. Dodge lasts to the Monk's next turn: visible attackers have disadvantage and Monk has Dex-save advantage; lost while incapacitated or speed is zero. AI prioritizes Dodge below 35% HP when enemies have attacks and the shared focus budget permits it. | No opportunity-attack movement simulation; reach/threat follows the existing no-grid convention. |
| Uncanny Metabolism | At actual initiative, when injured or missing focus, once per long rest: restore all focus and heal Martial Arts die + Monk level. Does not spend the use while full. | Not automatically triggered at individual turn starts or on a short rest. |
| Deflect Attacks | Reaction on an attack packet containing B/P/S: reduce total packet by d10 + Dex + Monk level before mitigation, including mixed damage. No use without reactions or while incapacitated; does not reduce nonattack damage. | Redirect omitted (no focus charged). No speculative damage reduction against pure elemental/force attacks. |
| Stunning Strike | L5+, once per global turn after a qualifying hit, one focus; Con vs 8 + Wis + PB. Failure stuns to Monk's next turn and ends concentration. Success halves speed and grants exactly the next incoming attack advantage to that deadline. Immunities honored. | AI avoids immune/incapacitated targets, low remaining HP and high Con saves; prioritizes spellcasters or targets with at least three-quarters of the largest enemy HP maximum; balanced requires >=40% estimated failure, reserve variant >=60%. Uses a per-encounter focus share across encounters until the next rest (falls back to encounters remaining), paced over expected turns; <25% HP releases the reserve. Flurry uses the same budget, never a separate unlimited pool. No Legendary Resistance prediction. |
| Empowered Strikes / Evasion | Unarmed strikes choose force from L6; weapons remain their own type. L7 Evasion reuses existing Dex-save half-damage logic, disabled while incapacitated. | Force is the fixed default, not an adaptive damage-type optimizer. |
| Open Hand Technique | On Flurry hits only: Topple, Dex save vs focus DC or prone. Addle (`open_hand: addle`) applies only the no-opportunity-attacks status until the target's next turn. | Push omitted. Addle has no effect here, since no opportunity attacks are simulated, so the AI never picks it. |
| Wholeness of Body / Self-Restoration | L6 bonus heal max(1, Martial Arts die + Wis), max(1, Wis) long-rest uses; AI heals below half HP when bonus action is free. L10 removes one charmed/frightened/poisoned condition at each turn end, including effect-based conditions (priority in that order). | Food/drink and exhaustion prevention omitted. Dodge can take priority over healing when low and threatened. |
| Ranger spellcasting / Favored Enemy | Wisdom; XPHB half-caster slots from L1; prepared counts 2/3/4/5/6/6/7/7/9/9. Hunter's Mark always prepared separately. Free casts 2 at L1, 3 at L5, 4 at L9, long-rest recovery; used first without slots, falling back to ordinary slots when exhausted. Only existing spell specs are selectable. | No rituals/exploration or unimplemented spell specs. Explicit higher-slot casts use slots rather than free casts. |
| Ranger weapons / AI | Two masteries from L1; Fighting Style from L2 (default Archery, +2 ranged hit); Extra Attack L5. Generalized existing Hex hit-count/concentration valuation to Hunter's Mark. Mark consumes a bonus action, leaving the Attack action; existing bonus-action command retargets after the marked creature drops to zero, without another cast/slot/free use. | Warlock Hex valuation unchanged. Spell-slot rationing remains the existing policy; free casts are independently available to the rationed strategy. No dual wielding added. Comparison includes a medium-armor longsword-and-shield/Dueling alternative and Sharpshooter. |
| Hunter's Prey | Default Colossus Slayer: d8 weapon-type damage once per global turn, only if target was already missing HP before the hit; critical doubles its dice. `hunters_prey: horde_breaker` adds one same-weapon attack on own turn against another not-yet-attacked target, even after a miss. | Horde Breaker assumes another reachable enemy is within 5 feet of the first (no-grid approximation). Choice is build-time, not automatically exchanged on rests. Hunter's Lore resistance discovery omitted. |
| Defensive Tactics | L7 Multiattack Defense: after a creature hits, that creature's subsequent attacks against this Ranger have disadvantage for the rest of that global turn. No effect on other attackers or future turns. | Escape the Horde not selected (no opportunity-attack movement). Roving, Deft Explorer/Expertise and Tireless (including temp-HP preparation and exhaustion recovery) omitted. |

Comparison variants also include Alert and a
reserve Stunning Strike threshold. No benchmark ratings or comparison batches
are generated by this addition.

## Druid (Circle of the Moon) and Sorcerer (Draconic Sorcery), 2024

Declarations cover levels 1-10; builds cover 1/3/5/7/10 in all three profiles.
Only existing XPHB spell specs are selected. Independent source checks cover
feature inventories, prepared/cantrip counts, slots and resource tables.
Reference parties remain Fighter/Cleric/Rogue/Wizard; Druid replaces Cleric,
Sorcerer replaces Wizard. Both new classes use `values_buffs`.

| Feature | Simulated | Deliberate omissions / choices |
|---|---|---|
| Druid spellcasting / Primal Order | Wisdom, full-caster slots and table-fixed prepared counts. Warden grants martial-weapon and medium-armor training, defaulting to medium armor and shield. Magician permits an extra cantrip with a legal light/unarmored kit. | Druidic language and free Speak with Animals, rituals and Magician's knowledge-check bonus are outside combat. No new spells or equipment types. |
| Wild Shape | From L2, two uses, three from L6; short rest restores one, long rest all. Bonus action; keeps own HP, mental scores, proficiency bonus, save proficiencies, spells and concentration. Physical stats, AC, size, movement, defenses, attacks, multiattack, actions and Beast flags come from the form. Save modifiers use the better Beast modifier or retained proficiency with current ability. Temp HP equals level, or three times level with Circle Forms. Duration is half Druid level (round down) hours. | Known forms are Wolf, Dire Wolf, Brown Bear and Giant Spider (only Wolf before Moon L3). These are all existing Beast sheets: CR 1/4 or 1. There are no CR 2/3 Beasts in the repository; higher Moon CR caps do not invent one. Owlbear is a Monstrosity and rejected. Form ends on temp-HP depletion, incapacitation/death, expiry or explicit helper call; leftover damage reaches own HP. Voluntary exit has no AI plan. No object handling, nested transformation planning or Beast skill selection. |
| Circle Forms / Improved Circle Forms | L3 CR cap floor(level/3), AC max(form AC, 13 + Wis), triple-level temp HP. L6 adds Wis to Con saves while shaped, including concentration; form attacks use Radiant. | Fixed Radiant choice rather than adaptive damage-type selection. Old-class attack/save behavior is unchanged. |
| Moon spells | Existing Circle spells always prepared separately: Cure Wounds, Moonbeam, Starry Wisp at L3, Conjure Animals at L5, Fount of Moonlight at L7, Mass Cure Wounds at L9. These spells can be cast while shaped, unlike other Druid spells. | XPHB explicitly allows Circle spellcasting in Wild Shape, overriding the brief's blanket casting prohibition. Wild Companion, Wild Resurgence and Moonlight Step (including its attack advantage) omitted. |
| Elemental Fury / Druid AI | Potent Spellcasting from L7 adds Wis to Druid cantrip damage, using the existing damage and EV hooks. AI chooses the strongest of its legal known forms by weapon EV when concentrating, below half HP, or without an available concentration spell; after casting concentration it can shape with the remaining bonus action. Form attacks and supported form actions enter the normal policy. | Primal Strike not selected. Existing concentration/control/healing policy, not a form/spell lookahead planner. Higher temp HP replaces lower, never stacks; depletion exit is a simulator simplification, not an XPHB requirement. |
| Sorcerer spellcasting / Draconic Resilience | Charisma; full-caster slots, XPHB prepared counts (two at L1) and cantrip counts. At L3+, HP increases by Sorcerer level and unarmored AC is 10 + Dex + Cha. | No armor training granted, multiclassing or spell-replacement history optimization. |
| Innate Sorcery | Bonus action, two long-rest uses, ten rounds; spell DC +1 and advantage on spell attacks, never weapon attacks. DC restored on expiry, cleanup or long rest. AI activates at combat start if available. | No Sorcery Incarnate extra activations or dual Metamagic from L7. Clocked days retain the real duration; legacy unclocked cleanup ends it between encounters. |
| Font of Magic | L2+ Sorcery Points equal level, long-rest recovery. API converts slots to equal points without an action (capped at maximum), or points to slots with a bonus action: costs 2/3/5/6/7 and minimum levels 2/3/5/7/9. Extra created slots vanish at long rest. | AI does not convert in either direction; reserves points for Metamagic. No above-level or above-fifth-level created slot. |
| Metamagic | Two choices at L2, four at L10. Implemented options: Quickened (two points, action spell becomes bonus action; blocks leveled casting after it, disallowed after a leveled cast), Heightened (two points; one target has disadvantage on initial and later saves against that spell), Careful (one point; up to max(1, Cha) allies automatically save and take no half damage), Extended (one point; doubles duration up to 24 hours and gives concentration-save advantage). Defaults Quickened/Heightened, adding Careful/Extended at L10. | One option per cast; Sorcery Incarnate's stacking omitted. No Twinned, Empowered or other options. AI quickens leveled action spells when its bonus action is free, then uses an action cantrip; otherwise heightens leveled saving-throw spells, then extends concentration spells if selected. Careful is available explicitly; default no-grid areas avoid allies, so AI does not spend points on it. No metamagic EV lookahead or day-level point budget. |
| Sorcerous Restoration | L5+: on a short rest regain up to floor(level/2) missing points, once per long rest; does not spend the entitlement at full points. | XPHB once-per-long-rest restriction is retained rather than granting points on every short rest. |
| Draconic Spells / Elemental Affinity | Existing Draconic spells always prepared separately. L6 Fire affinity: permanent Fire resistance, Cha added to one Fire damage roll per spell (shared rolls reuse the augmented roll; separate rays do not each gain Cha). EV includes the bonus. | Missing Arcane Eye and Legend Lore specs are reported by the builder. Fire is fixed, not adaptive. Dragon Wings is beyond supported levels. |
| Comparison | Spell-profile and War Caster/Alert variants for both; alternative Heightened/Extended Metamagic at levels before L10. | No reference-party change, ratings or comparison batches. |

## Levels 11–20 (2026-11-01)

Class rows, slots, prepared counts and resources run to level 20 for all twelve
classes and are checked against the XPHB tables. The level 19 Epic Boon is an
extra ASI or feat level (default: an ASI); `boon_of_fortitude` (+40 HP and +1
to any ability, up to 30) is the one Epic Boon feat modeled. All twelve classes
have their level 11–20 features and presets at 11/13/15/17/20 in all three
profiles. Scaling already in the engine was
extended: Monk Martial Arts die d10/d12 at 11/17 and Unarmored Movement to +30,
Bardic Inspiration d12 at 15, Rage Damage +4 at 16, Sorcerer Metamagic count 6
at 17 (only the four modeled options are selectable).

| Feature | Simulated | Deliberate omissions / choices |
|---|---|---|
| Fighter: Two/Three Extra Attacks | Three attacks at 11, four at 20. | — |
| Studied Attacks (13) | After a weapon attack misses, this fighter's next attack roll against that creature, before the end of its next turn, has Advantage. | — |
| Superior Critical (15) | Critical hits on 18–20 with weapons. | — |
| Survivor (18) | Heroic Rally: at the start of each turn while Bloodied and above 0 HP, regain 5 + Con modifier HP. Defy Death: Advantage on death saves, and 18–20 counts as a 20. | — |
| Indomitable / Action Surge | Two Indomitable uses at 13, three at 17; two Action Surge uses at 17 (still one per turn). | — |
| Rogue: Improved Cunning Strike (11) | A second, different Cunning Strike effect on the same Sneak Attack, if the dice can pay for both. | — |
| Devious Strikes (14) | `cunning_strike` may add `daze` (2d6: Con save or only one of action/Bonus Action on its next turn), `obscure` (3d6: Dex save or Blinded until the end of its next turn) and `knock_out` (6d6: Con save or Unconscious for a minute, ending on damage or a successful end-of-turn save). Default and optimized builds add Obscure; casual adds Daze. The AI picks Poison, then Trip, then Obscure. | The AI never chooses Knock Out. |
| Envenom Weapons (13) | Poison Cunning Strike also deals 2d6 Poison damage. | The damage does not ignore Poison Resistance. |
| Slippery Mind (15), Elusive (18) | Wisdom and Charisma save proficiency; no attack roll against the rogue has Advantage unless it is Incapacitated. | — |
| Death Strike (17) | On a Sneak Attack hit in the first round, a failed Con save (DC 8 + Dex + PB) doubles the Sneak Attack damage. | Approximation: only the Sneak Attack dice are doubled, not the whole attack's damage. |
| Stroke of Luck (20) | Once per Short Rest, a failed saving throw becomes a 20. | Not used on missed attacks or ability checks. |
| Wizard: Overchannel (14) | Once per Long Rest, the first damaging Wizard spell of level 3–5 deals maximum damage. | Later uses, with their escalating Necrotic backlash, are never taken. |
| Spell Mastery (18) | A level 1 and a level 2 action spell from the spellbook (default Magic Missile and Scorching Ray) cast at will at their base level. | Not upcast with slots. |
| Signature Spells (20) | Two level 3 spells (default Fireball and Counterspell, else the next listed) always prepared, each cast once per Short Rest at level 3 without a slot. | — |
| Evocation Savant | One free evocation spell at 11, 13, 15 and 17 as well. | — |
| Cleric: Improved Blessed Strikes (14) | Divine Strike 2d8; with Potent Spellcasting, a damaging cantrip also gives 2 × Wis modifier Temporary HP to the ally with the lowest HP fraction. | — |
| Supreme Healing (17) | Healing dice from the cleric's spells are maximized. | — |
| Greater Divine Intervention (20) | — | Wish is not modeled. |

| Barbarian: Relentless Rage (11) | Dropping to 0 HP while raging: Con save (DC 10, +5 per use) to return at twice the Barbarian level in HP. | The DC resets each fight, not on a rest. |
| Improved Brutal Strike (13, 17) | Staggering Blow (Disadvantage on the target's next save) replaces Hamstring Blow; from 17 the die is 2d10 and Sundering Blow (+5 to the next attack roll against the target) is added. | Hamstring Blow's Speed loss and Sundering's "another creature" limit are not modeled. |
| Intimidating Presence (14) | Bonus Action, once per Long Rest: enemies make a Wis save (DC 8 + Str + PB) or are Frightened, repeating the save each turn. | Restoring it with a Rage use is not modeled. |
| Persistent Rage (15), Indomitable Might (18), Primal Champion (20) | Regain all Rages on initiative once per Long Rest; a Strength save below the Strength score uses the score; +4 Str and Con (max 25). | — |
| Paladin: Radiant Strikes (11) | Melee weapon hits deal an extra 1d8 Radiant. | — |
| Holy Nimbus (20) | Once per Long Rest, active from the start of a fight for 10 minutes: enemies take Cha + PB Radiant damage at the start of their turns. | No Bonus Action spent; every enemy is assumed in the aura. Fiend/Undead save Advantage not modeled. Restoring Touch and Smite of Protection (Cover) are not modeled. |
| Monk: Deflect Energy (13), Disciplined Survivor (14) | Deflect Attacks works on any damage type; proficiency in all saves and a 1-Focus reroll of a failed save. | — |
| Perfect Focus (15), Superior Defense (18), Body and Mind (20) | Focus back to 4 on initiative if Uncanny Metabolism was not used; 3 Focus at the start of a turn below 75% HP for Resistance to all but Force for a minute; +4 Dex and Wis (max 25). | — |
| Quivering Palm (17) | 4 Focus on an Unarmed Strike hit against a creature with 40+ HP: Con save or 10d12 Force (half on success). | Approximation: the vibrations end at once, without spending a later action or attack. |
| Ranger: Superior Hunter's Prey (11) | Once per turn, a weapon hit on the marked creature also deals the Hunter's Mark die to the lowest-HP other enemy. | — |
| Relentless Hunter (13), Precise Hunter (17), Foe Slayer (20) | Damage can't break Concentration on Hunter's Mark; Advantage against the marked creature; the mark's die becomes a d10. | — |
| Nature's Veil (14), Superior Hunter's Defense (15) | Bonus Action Invisible until the end of the next turn (Wis-mod uses); a Reaction halves the damage of a hit. | Superior Hunter's Defense covers attack damage only. Feral Senses is not modeled. |
| Warlock: Mystic Arcanum (11–17) | One spell of each level 6–9 (default Circle of Death, Finger of Death, Power Word Stun, Power Word Kill), cast once per Long Rest without a slot. | — |
| Hurl Through Hell (14) | Once per Long Rest, on its first hit against a creature with 30+ HP: Cha save or 8d10 Psychic (not Fiends) and Incapacitated until the end of the warlock's next turn. | Eldritch Master needs Magical Cunning, which is not automated. |
| Bard: Peerless Skill (14), Superior Inspiration (18) | A missed attack can add the bard's Bardic Inspiration die (spent only if it turns the miss into a hit); uses back to 2 on initiative. | Peerless Skill on ability checks is not modeled. |
| Words of Creation (20) | Power Word Heal and Power Word Kill always prepared. | The second target is not modeled. |
| Druid: Lunar Form (14), Beast Spells (18), Archdruid (20) | Once per turn +2d10 Radiant on a Wild Shape hit; any spell without a costly or consumed component can be cast in Wild Shape; regain a Wild Shape use on initiative when none are left. | Improved Elemental Fury (range), Nature Magician and Longevity are not modeled. |
| Sorcerer: Dragon Companion (18), Arcane Apotheosis (20) | Summon Dragon once per Long Rest without a slot; one Metamagic per turn costs no points while Innate Sorcery is active. | Dragon Wings and the no-Concentration Summon Dragon are not modeled. |

Free castings (Signature Spells, Mystic Arcanum, Dragon Companion) share one
mechanism: a `free_<spell>` counter that pays for the spell at its own level.
Warlock, Bard and Druid spell lists gained their XPHB level 6–9 spells.

From level 11, default and preset characters prepare their class's listed
spells of level 6+ before lower-level ones (`builder.high_first`); levels 1–10
are unchanged. The level 6–9 spells are in `engine/spell_high.py`, which lists
the omitted ones and why.
