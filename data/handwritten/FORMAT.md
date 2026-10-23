# Handwritten spell effects (XPHB only)

These are declarations, not engine code. Source: `raw_data/spell/spells-xphb.json`.
All distances are feet, costs GP, levels spell-slot levels unless labeled cantrip.
`null` means inapplicable; empty lists mean no entries. Policy chooses legal targets
and choices; no target count, position, caster DC, or attack bonus is guessed here.

## Required structure

Every spell has `name`, `source: XPHB`, `level`, full lowercase `school`,
`casting_time`, `reaction_trigger`, `range`, `components`, `duration`,
`concentration`, `ritual`, `choices`, `effects`, `scaling`, `ends_on`, `unsupported`.

- Casting time: `action | bonus_action | reaction | minute | ...`.
- Range: `{type: self|touch|point|sight|unlimited, feet?: number}`.
- Components: `{v: boolean, s: boolean, m: string|null, m_consumed: boolean,
  m_cost_gp: number|null}`. Cost is a minimum requirement, not an expenditure.
- Duration: `{type: instant|rounds|minutes|hours|until_dispelled|special, n?: number}`.
  Timed durations require `n`. Concentration ends the spell when lost.
- Choices: `[{id, options: [...], when: on_cast}]`; `$id` references the result.
- `ends_on` contains additional end-event expressions. An explicit next-turn
  boundary defines the precise endpoint instead of a nominal `rounds` duration.
- `unsupported` contains short omissions, never executable instructions.

Each block requires `id`, `event`, `target`, `attack`, `save`, `on_hit`, `on_fail`,
`on_success`, `apply`, `limit`. IDs are unique within a spell instance.
`attack: {type: ranged_spell|melee_spell}` and
`save: {ability: str|dex|con|int|wis|cha, on_success: half|negate}` are exclusive.
Attack hits run `on_hit`; failed saves run `on_fail`; unconditional blocks run
`apply`. `half` halves only damage, rounding down; `negate` applies none
of the failed-save effects. `on_success` adds any explicitly listed success effects.
Use caster spell attack bonus, spell save DC, and `spell_mod` throughout.

## Targets and events

- `self`; `single` with `filter` and `affects`; `n_targets` additionally has `n`
  and `distinct`; `area` has `shape`, `size_ft`, `affects`; `ref` has `ref`.
- `affects: any` does not impose allegiance. `enemy|ally|all|enemies|chosen` are
  also supported. Filters are conjunctive; `creature_or_object` is a union.
  `humanoid`, `visible` (to caster), `willing`, and `creature` have literal meanings.
- `n_targets` resolves the block once per selected occurrence. With `distinct:
  false`, repeat targets are legal, each attack has its own roll, and damage is
  not collapsed into one hit. Single-block references retain the selected creature;
  references to multi-target blocks retain the selected list.
- A `ref` does not reselect or recheck original casting range/visibility.
  `spell_target` aliases the initial target binding when unambiguous.
- Sphere/emanation `size_ft` is radius. An emanation excludes its origin creature.
  Area membership/counts are provided by the global engine heuristic, never by
  a spell. Area events resolve only the triggering creature, not every member.
- Base events: `on_cast`, `start_of_turn(who)`, `end_of_turn(who)`,
  `on_attack_hit(attacker, defender)` (confirmed hits only), `on_damaged(who)`,
  `on_attacked(who)`, `on_spell_cast_nearby(range_ft)`, `bonus_action_command`,
  `action_command`.
  `who` may be caster, target, affected, or any_enemy_in_area.
  Commands cost the named action and do not recast the spell or reset duration.
- Limits: `null`, `once_per_turn`, `once_per_turn_per_target`. Turn means **any
  combatant's turn**, not a round or only the caster's turn. Limits belong to the
  block/spell instance and are shared across all its alternative event triggers.
  A save-based block consumes its limit on making the save, even on success.

## Primitives and lifetime

| Key | Fields / meaning |
| --- | --- |
| `damage` | `{dice, bonus: number|spell_mod, type}`; immediate damage, attack damage can critically hit |
| `heal` | `{dice, bonus: number|spell_mod}`; immediate healing capped at maximum HP |
| `temp_hp` | `{dice}` or `{amount}` |
| `apply_condition` | `{condition, repeat_save?: {ability, timing, on_success: end}}`; official conditions only |
| `modify` | `{stat, op: add|mul|set, value, scope}`; stats ac, speed, attack_roll, save, damage_roll, ability_check, action_count |
| `advantage`, `disadvantage` | `{on: attack_rolls|saves|ability_checks, scope, against}`; recipient is the effect target by default, `against: null` is unrestricted |
| `grant_action` | `{kind: action|bonus_action|reaction, restricted_to: [...]}`; grants one additional action of that kind on each recipient turn |
| `status` | `{id, data}`; persistent named marker, not an official condition |
| `remove_from_combat` | `{until: spell_ends, returns}`; unavailable to normal combat targeting/actions while removed |
| `counter_spell` | `{target: trigger.spell, cancel_effects: true, consume_casting_action: true, expend_slot: false}`; cancel the pending spell, waste its action/bonus action/reaction, but do not expend its spell slot (Counterspell) |
| `end_spell` | `true`; end this spell instance |
| `on_spell_end` | List of primitives registered now and run once on the bound recipient after the spell's persistent effects are removed |

Damage/healing are instantaneous. Other applied effects persist to spell end
unless a narrower lifetime is specified. A repeated successful condition save
ends this spell's effects **on that target only**, not other targets or concentration.
Evaluate removal return rules before cleanup; then remove conditions even from
nonreturning creatures. Haste's end effects have their own lifetime and survive
the originating spell ending. Speed modifications are recorded but currently no-ops.
Dice-valued modifiers (Bless) roll afresh for each qualifying roll.
Damage added by a confirmed-hit block is part of that triggering attack's damage,
including its critical-hit dice treatment; it does not generate another hit event.

`if` may guard a primitive or a whole block and is checked before its execution
(before target selection for block guards). Expressions are declarative, not Python:
`and`, `or`, `not`, `==`, `!=`, `<`, `>`, `>=`, `in`, parentheses, literal lists,
and dotted state references. Bare enum names are literals; `$choice` is substitution.
An event expression containing `or` subscribes to each event; it does not execute twice.
`target` is the current selected recipient; `defender` comes from a hit event.
`target.has_status(id)` checks active markers from any source. Ordinary markers
are scoped to their originating spell instance for replacement/cleanup.
`shielded` is used explicitly by Magic Missile to suppress its damage; it is not
a blanket immunity. There are no implicit mechanics hidden in arbitrary status data.

## Scaling

`cantrip: {at: [5, 11, 17], effect: {block, dice_add|beam_count_add}}` adds one
increment per reached **character-level** threshold. Beam count changes target `n`.
`upcast: {per_slot_above: base, changes: [...]}` applies `dice_add` or
`target_n_add` to the named block per slot above base. Dice additions change the
block's damage/healing dice, not bonus dice from another block. Target additions
preserve filters, distinctness, and selection semantics. Unlisted scaling is absent.

## Necessary additions / precise extensions

| Name | Fields | One-line semantics | Needed by |
| --- | --- | --- | --- |
| Exact lifetime | Primitive `until: end_of_turn(actor.next_turn)`; matching spell `ends_on` expressions also allow `start_of_turn` | Expire at the specified actor's next turn boundary, measured when that effect is created. | Guiding Bolt, Shield, Haste |
| Incoming-roll advantage | `advantage.recipient: any_attacker`, `uses: 1`, `against: target` | Benefit the next attack roll against this target, consuming the use whether it hits or misses and regardless of other advantage. | Guiding Bolt |
| Cover exclusion | `save.ignore_cover: [half, three_quarters]` | Omit these cover bonuses from this saving throw only. | Sacred Flame |
| Optional count | `target.up_to: true`, `min?: number` | Policy may choose fewer than `n` distinct recipients, but no fewer than `min` (default 0), including declining optional upcast targets. | Bless, Hold Person, Banishment |
| Simultaneous shared roll | Block `resolution: simultaneous`, `damage_roll: shared` | Select all darts first, roll damage once, assign that value per dart, then resolve the volley simultaneously. | Magic Missile |
| Reaction context | `on_spell_targeted(caster, magic_missile)`; `on_attack_provisional_hit(attacker, defender)`, where `any` matches every attacker; `trigger.caster`, `trigger.spell`; `visible_to`, `has_any_component` | Expose a pending spell's caster/components/targets before resolution, or a provisional hit before its hit effects and damage. | Shield, Counterspell |
| Rebinding activation | Combined block event, block `if`, filter `new_target`; `block.target`, `block.target_dropped_to_zero`, `block.drop_turn` | Reexecuting a persistent application block replaces its old target/effects without refreshing spell duration; new_target excludes its current target. | Hex, Hunter's Mark |
| Turn history | `event`, `turn.index`, `spell.cast_turn` | Compare global turn identities; block drop history latches when the current marked target drops to zero after marking, and resets on transfer. | Hex, Hunter's Mark, Spiritual Weapon |
| Duration tiers | Upcast change `{slot_min, slot_max: number|null, duration}` | Replace duration once when slot is in the inclusive interval; null maximum means no upper bound, not a per-slot increment. | Hex, Hunter's Mark |
| Remote origin / optional activation | `target.origin: spiritual_weapon`, `within_ft: 5`; block `optional: true` | Declare reach from the force rather than caster; policy may decline an attack without preventing creation or ending the force. | Spiritual Weapon |
| Persistent area | `target.origin: caster`, `exclude: designated_on_cast`; events `while_in_area`, `on_aura_moves_onto_creature(target)`, `on_creature_enters_aura(target)`, `end_of_turn_in_aura(target)` | Track a caster-centered aura, frozen policy-selected exemptions, continuous membership effects, and the two distinct entry triggers. | Spirit Guardians |
| Choice eligibility | `choices[].option_conditions: {option: expression}` | Policy may only choose an option whose condition is true; alignment is good/neutral/evil for this purpose. | Spirit Guardians |
| Restricted extra attack | `grant_action.attack_limit: 1` | If the granted action is Attack, allow one attack only, not the creature's full Attack routine. | Haste |
| Conditional return | `remove_from_combat.returns: expression`; `spell.elapsed_minutes`, `target.creature_type` | Evaluate return eligibility at spell end using actual elapsed duration and creature type, including interrupted concentration. | Banishment |

### Scheduling clarifications

- Shield triggers on `on_attack_provisional_hit`; apply its AC bonus and recheck
  that same roll before hit effects/damage. Only a confirmed hit dispatches
  `on_attack_hit` blocks such as Hex. Shield can also interrupt Magic Missile targeting
  without an attack roll. Its protection covers the entire triggering volley.
- Counterspell's save is made by `trigger.caster`, against the reacting caster's DC.
  It has no spell-level test, ability check, or automatic low-level success.
- A mark's drop flag is false before its target actually drops to zero while marked.
  Hex transfers only on a later turn; Hunter's Mark has no later-turn restriction.
  Transfer removes the previous Hex check penalty as well as its marker, and keeps
  the original ability choice. Current attack-event binding is not replaced by refs.
- Spiritual Weapon's range governs initial force placement, not a recurring
  caster-to-target range check. Its reach/movement require heuristic adjudication.
- `while_in_area` installs/removes the speed multiplier as membership changes,
  including initial membership; it is not a per-turn stacking application.
  Spirit Guardians damage has no start-of-turn or unconditional on-cast trigger.
  Initial creation alone is not treated as entry; later abstract entry events and
  end-of-turn membership trigger the save. Even without movement events, end-turn
  damage works. Area IDs/membership and exclusions belong to the spell instance.

## Step 3 additions

- `modify.op: sub` subtracts the rolled value; `modify.recipient: any_attacker`
  applies to the attacker against the effect recipient (Blade Ward, Bane).
  `modify.uses: 1` consumes the modifier on the next qualifying roll (Mind Sliver).
- Instantaneous spells detach primitives with exact `until` boundaries instead of
  deleting their riders at cast completion (Chill Touch, Mind Sliver, Starry Wisp,
  Ray of Frost, Vicious Mockery). Other instantaneous effects still end normally.
- `damage.explode_max: spell_mod` rolls additional dice on maximum results, capped
  at the spellcasting modifier in added dice (Sorcerous Burst).
- `damage.wounded_dice` replaces damage dice for a target below maximum HP;
  cantrip scaling adds the same number of dice of the alternate die size (Toll the Dead).
- Optional `recast_ends_previous: true` ends the same caster's previous instance
  on successful recast (Produce Flame). Hurling uses `action_command`.
- Engine-recognized status `invisibility_suppressed` suppresses Invisible
  benefits without deleting their source (Starry Wisp).
- `turn_rules` stores explicit action restrictions (`no_action`, `no_bonus_action`,
  `no_reactions`); `on_turn_condition` applies at the recipient's turn start
  (Command's Grovel, rather than knocking the target prone early). Exact
  `until` boundaries govern these restrictions (Command, Arms of Hadar).
- `spend_reaction: true` spends an available reaction without movement
  (Dissonant Whispers).
- `base_ac: {base, ability, unarmored_only}` supplies an alternative AC
  calculation; use the better legal base before AC bonuses (Mage Armor).
- Upcast `{block, amount_add}` adds flat temporary HP per slot (False Life).
- An area `origin` may name an earlier block; its bound target is included
  first by the no-grid heuristic (Ice Knife's hit-or-miss explosion).
- A spell block's optional `source_ref: entries.N` identifies the XPHB paragraph
  for independent numeric checking (Witch Bolt's initial versus sustained damage).
- `base_ac.ability: null` is a static alternative base AC (Barkskin).
- `remove_condition: {condition}` ends one named condition, including a `$choice`
  (Lesser Restoration). `defense: {resistance: [...]}` supplies source-scoped
  resistances which never stack with existing resistance (Stoneskin).
- `apply_condition.ends_on_activity: true` ends that recipient's participation
  after an attack roll, dealing damage or casting a spell (Invisibility).
  `persistent: true` installs a normal condition that survives the originating
  instantaneous spell and is removed normally, e.g. by standing (Destructive Wave).
- `save.auto_fail_if` and `save.disadvantage_if` are target-local expressions
  (Blight's Plants and Shatter's Constructs).
- `modify.stat: fly_speed` stores a separate Fly Speed, not walking speed (Fly).
- `dispel: {auto_level, dc_base}` ends ongoing spells on the recipient;
  compare their cast slot against max(auto_level, this cast slot), otherwise
  check the caster's spellcasting ability against dc_base + that slot (Dispel Magic).
- `turn_rules` also supports `action_or_bonus`, `attack_limit`,
  `somatic_failure_percent` and the existing `repeat_save` structure (Slow).
  Somatic failure spends the casting economy and slot, but creates no effects.
- An upcast dice change may include `damage_type` to scale only that damage
  component without changing the block's shared save (Ice Storm).
- `summon: {choice, forms, base_slot, per_slot, attack_count_divisor}` embeds
  complete stat sheets keyed by form. `per_slot` has `ac`, `max_hp` and
  `damage_bonus` increments above base_slot; attacks per turn are floor(slot /
  attack_count_divisor). Only embedded sheets may use `proficiency_bonus: caster`
  and attack `to_hit: spell_attack`. These inherit the original caster's actual
  values, as does their save DC (Summon Beast, Summon Undead).
  Each creature has independent HP, defenses, conditions and actions; it acts
  immediately after its caster. `Policy.command_summon` chooses commands without
  an action cost; false takes Dodge. Zero HP or spell ending makes it disappear.
  `target.exclude: summoner` excludes only its summoner from an aura (Summon Undead).
  Skeletal attacks declare `range_ft` alongside the existing ranged reach sentinel.
- Monster `spell_recharge: {spell: d6_threshold}` reuses the existing recharge
  clocks instead of inventing daily uses (Stone Golem's Slow).
- The same embedded `summon` contract also supports all four Summon Elemental
  forms; their damage types use the printed main stat block, not conflicting
  generated 5etools `_versions`. No additional primitive is introduced.
- Engine-recognized status `verbal_components_blocked` prohibits only spells
  whose effective components include V, honoring innate component exemptions
  (Jallarzi's Storm of Radiance). `while_in_area` removes it and the storm's
  Blinded/Deafened conditions when membership ends; these do not allow saves.
- Long castings retain `casting_time_n` (Leomund's Tiny Hut; later long
  castings). `Combat.prepare` explicitly completes an uninterrupted preparation
  interval, spends its slot and advances time before effects begin; normal
  combat casting does not turn minutes/hours into one action. `on_falling(target)`
  declares an external falling reaction event (Feather Fall); the arena does not
  invent falling damage or movement.
- `target.n: all` means any number of otherwise legal targets (Beacon of Hope);
  `include_caster: true` explicitly includes the origin in an Emanation (Auras
  of Life/Purity). `exclude: caster` implements Entangle's exception.
- `defense` also supports damage `immunity`, `condition_immunity`,
  `magical_condition_immunity` and `save_conditions` (Protection from Poison,
  Heroism, Feign Death, Gaseous Form, Freedom of Movement, Aura of Purity).
- `heal.amount` represents flat healing; `temp_hp.amount: spell_mod` represents
  Heroism. `maximize_healing` and `max_hp_protected` are recognized statuses
  (Beacon of Hope, Aura of Life). `see_invisible` affects visibility and attack
  benefits (See Invisibility). Incoming Advantage may `require_visible` (Faerie Fire).
- `modify.scope` accepts a chosen skill (Guidance); `ability_check` accepts an
  optional skill tag. `choices.per_target` allows recipient-keyed ability choices
  (Enhance Ability). `escape_dc: spell_dc` uses the caster's actual DC (Entangle, Web).
- `turn_rules.no_attacks/no_spells` prohibit those activities (Gaseous Form).
  `restore: {kind, all?}` removes one declared condition/Exhaustion level, curse,
  HP-maximum or ability reduction; `all` only controls curse count (Greater
  Restoration, Remove Curse). Item attunement remains outside the object model.
- `stabilize: true` records Stable without healing (Spare the Dying); damage or
  healing clears it. `cantrip.effect.range_multiplier` scales range at thresholds.
  The knockout arena has no death-saving-throw clock; this is not resurrection.

- Damage phases may use a flat `amount`, `delay` boundary, `leech`, `half`, or
  `end_after_total` (Guardian of Faith, Vampiric Touch, Vitriolic Sphere, Acid
  Arrow). A block may add `on_miss`; `miss_dice_add` scales only that branch.
  Fixed damage/retaliation does not inherit the triggering attack's critical.
- `grant_command: {block, action}` lets the recipient activate a command
  (Dragon's Breath). A command's acting recipient supplies its damage source.
  Reactive blocks can spend `cost: reaction` (Fount of Moonlight).
- Damage hit events expose `attack.weapon/melee/hit` and trigger attacker/
  defender references (Divine Favor, Crusader's Mantle, Fire Shield, smites).
  Delayed phases and `duration` on a primitive survive an instantaneous parent
  (Synaptic Static). `modify.stat: concentration_save` affects maintenance only.
- Scaling changes can select `if`, `timing`, `area_size_add`, `value_add`,
  `capacity_add`, `uses_add`, or `exclude_conditional` (Hunger of Hadar,
  Vitriolic Sphere, Confusion, Aid, Arcane Vigor, Agathys, Grasping Vine,
  Cordon of Arrows, Divine Smite). The fiend/undead Smite bonus never upcasts.
- Blocks can share a `limit_group`; `max_uses` consumes ammunition even on a
  save (Conjure Elemental, Cordon of Arrows). `after_damage` flushes the triggering
  packet before an HP gate (Banishing Smite). `end_after_resolution` ends a
  single triggered area after all its targets resolve (Glyph of Warding).
  `glyph_triggered` is an external event, not automatic preparation damage.
- Saves can have `if`, `advantage_if` or `auto_success_if` (Enlarge/Reduce,
  charms, Ensnaring Strike, Sleep). Conditions can `ends_on_damage`, request
  damage-save Advantage, tally successes/failures, or `resist_removal`
  (charms, Sleep, Hideous Laughter, Hypnotic Pattern, Contagion).
- `pacify`, `duel`, `sanctuary: {ability}` and source-typed `ward` express
  combat restrictions rather than prose effects (Suggestion, Calm Emotions,
  Compelled Duel, Sanctuary, Protection from Evil and Good, Dispel Evil and
  Good, Magic Circle, Hallow). `restore.source_types` restricts Break Enchantment.
  Wards distinguish new-condition immunity from existing-condition suppression
  or repeat-save Advantage. `defense.vulnerability` is nonstacking (Hallow).
- `turn_rules.behavior_die/forced_melee/maintained_by_action` express Confusion
  and Crown of Madness; `dismiss_action/end_at_zero` permit target-local Magic
  dismissal and zero-HP ending (Gaseous Form). `isolated` blocks cross-boundary
  targeting/damage without Incapacitating the recipient (Resilient Sphere).
- `max_hp`, `hit_dice_heal`, `death_ward`, `berries`, `reduce_damage`,
  `magic_saves` and `bond` handle Aid, Arcane Vigor, Death Ward, Goodberry,
  Resistance, Circle of Power and Warding Bond. `eat_berry` spends the eater's
  Bonus Action and shared stock. Bond copies actual damage and excludes
  overlapping participant bonds. Stable/knockout is still not a death clock.
- `mirror_images: {count, dice, threshold}` redirects confirmed hits; `blink`
  uses the same dice/threshold structure at turn end (Mirror Image, Blink).
- `weapon_strike` uses the supplied weapon, optional spell ability/type, count
  and source-declared `upgrade_levels/upgrade_dice` (True Strike, Swift Quiver).
  `weapon_enchantment` binds one eligible weapon, with `tiers/cantrip_dice`,
  bonuses and damage overrides (Shillelagh, Magic Weapon, Elemental Weapon,
  Alter Self). `weapon_adjustment` and `size_change` model Enlarge/Reduce.
- `casting_trigger` distinguishes `melee_hit`, `weapon_hit` and
  `ranged_hit_or_miss`; a post-hit cast needs the actual attacker/defender/attack
  frame (all smites, Ensnaring Strike, Hail of Thorns, Lightning Arrow).
  `replace_weapon_attack` suppresses Lightning Arrow's original weapon packet.
  `duration_tiers` can replace duration/concentration (Bestow Curse);
  `curse_dodge/curse_damage/control` express its orders/damage and Planar Binding.
  `leap_on_duplicate` uses actual rolled faces and distinct slot-limited targets
  (Chromatic Orb), not an assumed guaranteed leap.
- Embedded summons may instead declare `fixed_attacks`; use exactly one count
  rule. XMM-referenced forms retain fixed PB/to-hit (Animate Dead, Find Familiar,
  Phantom Steed). `count/count_per_slot/form_cost/damage_dice_add` support
  Animate Dead/Objects; `command_cost`, `control_hours`, `persistent`, `familiar`,
  `creature_type_choice`, `mount/fly_slot`, and `after_attack_action` retain their
  distinct control/lifetime rules (also Find Steed, Summon Dragon).
  `slot_bonus/add_caster_mod` distinguish scaled damage components; `summon_slot`
  supplies a summoned creature's slot-based healing (Celestial/Steed).
- Summon stat sheets also use `on_hit_self`, `own_turn_start` and existing
  actions/passive traits for source riders (Summon Aberration/Celestial/Construct/
  Fey, Giant Insect). The same strict referenced-block numeric gate covers them.
  `force_object` creates a targetable object with caster-max HP (Bigby's Hand),
  not an autonomous extra attacker. `transform` embeds legal CR-checked Beast
  sheets, retaining HP/type and restoring statistics on reversion (Polymorph).

### Step 3 fix round: persistent dependencies and source-aware targeting

- A persistent primitive can declare `requires_condition: charmed` alongside
  its primitive mapping. The rider is active only while a condition from that
  same spell instance is effective on that recipient, including immunity and
  suppression. Removing the condition does not let another caster's charm
  activate the rider. Existing `if` remains a one-time application predicate.
- `type_mask: {type: $type}` declares a chosen magical creature type. Actual
  creature type is unchanged; spell eligibility, magical expression type checks
  and magical protection checks use the mask. `extinguish: {}` douses exposed
  Burning without spending a separate recipient action.
- `apply_condition` additionally accepts boolean `ends_on_spell_targeted` and
  `ends_spell`. The former ends its originating spell when another spell
  targets the recipient; the latter makes its damage-ending rule end the spell
  instead of merely removing target-local effects.
- Ongoing spell recipients are tracked separately from their stored effects.
  The default hostile-area heuristic assumes freely chosen enemy-only placement;
  custom count/index heuristics may explicitly model friendly spill-over. Fixed
  self-origin emanations and known bound origins retain their own target rules.

For Mask's "other than actual type" eligibility, expressions can read
`target.actual_creature_type`; ordinary `target.creature_type` inside a magical
spell context reads the effective masked type. This does not change the
combatant's actual type. Implicit-caster emanations, such as ambient monster
auras, are fixed-origin geometry too; their hostile effects can still affect
eligible allies.


## Step 3 fix round 2: participants and condition dependencies

- A persistent primitive may declare `participants: [caster, target]`. The
  recipient is always registered; this list additionally registers every named
  participant for Dispel Magic and spell-ending cleanup. Warding Bond explicitly
  registers both endpoints; range `self` is not an ownership inference for bonds.
- `requires_condition: CONDITION` is persistent primitive metadata, not an
  application-time `if`. The condition must be effective on the same recipient
  from the **same spell instance**. Removing/suppressing it disables its riders;
  resumption re-enables surviving riders without reapplying them. Dependent
  conditions can themselves supply dependencies; unrooted cycles stay inactive.
- The same `requires_condition` metadata on an effect block gates the whole
  resolution (including its save and action cost), and on instantaneous
  primitives gates each recurring application. `has_condition_from(NAME, spell)`
  tests an exact instance; the existing `..., caster` form tests caster ownership.
- When a conditional save is skipped, use the explicit `apply` branch if one
  exists; otherwise apply `on_fail` without rolling. This covers willing
  Enlarge/Reduce without changing Dispel Evil and Good's Break Enchantment branch.
- Controlling Charmed effects derive allegiance only while effective. Base
  allegiance is retained. HP maximum is base maximum plus effective spell
  bonuses; maximum-HP restoration changes only the underlying base.
- Transformations retain one original-stat snapshot and a stack of forms with
  separate remaining temporary HP. Ending a suppressed form does not alter the
  effective form. Ending/depleting the effective form resumes the next eligible
  form, or restores the original. Single-target depletion also ends its spell
  and concentration. Temporary action prohibitions mask, not spend, budgets;
  removing a condition-dependent prohibition restores only unspent actions.
