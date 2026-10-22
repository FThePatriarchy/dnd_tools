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
