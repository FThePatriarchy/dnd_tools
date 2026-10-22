# Combat engine build report

## Implemented

- Standalone `engine/` package. No imports from or edits to `spellsim/` or
  `ai_extractors/`. The 20 reviewed spell YAML files were not modified.
- Strict YAML loading (including duplicate-key rejection), recursive validation
  of spell fields, primitives, events/arguments, target declarations, scaling,
  choices, references, guards and exact lifetimes. Errors identify source file
  and field path. Stat sheets are validated too.
- Safe tokenizer/recursive-descent expression parser; no Python evaluation.
  Supports the golden set's Boolean operators, comparisons, lists, enum
  literals, dotted references, choice substitution and three permitted methods.
- Dataclass combatants and spell instances; HP/temp HP, AC, abilities, save
  proficiency/overrides, spell statistics, slots, counters, defenses, conditions,
  source-scoped markers, concentration and per-turn action economy.
- Seeded initiative/rounds, event dispatch, pending spell and provisional-hit
  reactions, commands, durations, exact next-turn boundaries, repeat saves,
  target-local removal and one-shot spell-end callbacks. Haste's detached end
  effects outlive the originating instance.
- Attack/save resolution, advantage/disadvantage cancellation, natural-20
  critical dice, half damage and mitigation. Confirmed-hit riders share their
  attack's critical treatment and one combined concentration damage check.
  Concentration DC is `min(30, max(10, damage // 2))`, including temp-HP damage.
- All 20 spells' executable mechanics: cantrip/upcast scaling, shared simultaneous
  Magic Missile darts, Guiding Bolt's incoming one-use advantage, marks and
  transfers, per-target Hold Person repeat saves, Spirit Guardians' end-turn
  timing/limits, Shield rechecks, 2024 Constitution-save Counterspell, Haste
  lethargy and Banishment's conditional return.
- One pluggable area heuristic plus policy hooks for target selection, choices,
  optional attacks, aura exemptions, reaction use and complete turns.
- Default damage-oriented AI, bonus-action/normal healing below 50%, ongoing
  concentration preservation and commands, outcome-aware Shield, and
  Counterspell against meaningful opposing spells with a possible failed save.
- Deterministic structured 5etools importer, four reviewed XMM monster sheets,
  and fixed Fighter 5 / Cleric 5 sheets. Monster additions are documented in
  `data/handwritten/MONSTER_FORMAT.md`.
- Fighter Extra Attack, Graze, Second Wind and Action Surge; also small Vex/Sap
  handlers. Action Surge cannot supply a spellcasting action. Monster daily
  spell uses, Nimble Escape bookkeeping, dragon recharge and three-Rend
  Multiattack use the same resolution core.
- Reusable `simulate()` summary and `python -m engine.simulate` CLI, with text
  or JSON output: wins/draws, win rate, mean rounds, remaining party HP and mean
  resources spent. Every trial receives its own seed from the seeded run RNG.
- Added PyYAML in `pyproject.toml`; preserved the existing pytest configuration.

## Verification

Executed with the provided Anaconda Python, without installing anything or
accessing the network:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& C:/Users/xgxxg/anaconda3/python -m pytest -q -p no:cacheprovider --disable-warnings
```

Final full-repository pytest summary (85 new engine cases and 9 legacy cases):

```text
94 passed in 26.52s
```

Tests cover loading all 26 sheets/specs, malformed declarations and unsafe
expressions, seeded per-spell behavior/statistics, critical riders,
concentration, action economy, target filters, source scoping, independent
timed effects, area membership/limits, optional force activation, conditional
return with fractional round clocks, monster parser fidelity, Ogre hit math,
12,000 recharge trials, Multiattack, class features and default AI behavior.
Each requested 1,000-run encounter is executed twice and its complete summary
must match exactly for seed 1. The CLI is tested in a subprocess.

Both requested CLI encounters were also run directly with 1,000 trials:

| Opponents | Party wins | Mean rounds | Mean party HP | Mean resources spent |
| --- | ---: | ---: | ---: | --- |
| 4 Goblin Warriors | 1000/1000 | 1.820 | 79.569 | Action Surge 0.970; level-1 slots 0.169; level-3 slots 1.062 |
| 1 Ogre | 1000/1000 | 2.088 | 77.873 | Action Surge 1.000; level-1 slots 0.561; level-3 slots 1.074 |

These are results for these exact simplified builds/policy, not encounter
balance recommendations. Starting total party HP is 87; remaining HP excludes
temp HP and creatures currently or permanently removed from combat.

```powershell
& C:/Users/xgxxg/anaconda3/python -m engine.simulate --party fighter5 cleric5 --monsters goblin_warrior x4 --runs 1000 --seed 1
& C:/Users/xgxxg/anaconda3/python -m engine.simulate --party fighter5 cleric5 --monsters ogre --runs 1000 --seed 1
```

## Specs not executed / explicit unsupported content

No new contradiction or unexecutable **golden spell instruction** required a
spell-file edit. All executable effects in the 20 files are supported within
the requested no-grid boundary. Existing `unsupported` notes stay omissions,
not executable behavior: object ignition, tracking, appearance, demiplane and
return positioning, and exact Spiritual Weapon placement/movement.

As explicitly requested, aura movement/entry events validate but never fire;
speed modifiers are stored without simulating movement. Spirit Guardians
still resolves on each affected creature's end turn, not at creation/start.

Monster/class omissions are recorded in their sheets:

- Cultist Fanatic: Light, Thaumaturgy and Command are outside the golden set.
  Hold Person and Spiritual Weapon use their actual reviewed specifications
  and per-day counters, not guessed spell slots.
- Goblin Warrior: Nimble Escape can spend its bonus action and record
  Disengage. Hide needs concealment/Stealth/Perception adjudication, absent
  from this no-grid model. Default AI never invents hidden advantage.
- The Young Red Dragon has no Legendary Resistance in this XMM source; none
  was added. A generic finite-use failed-save override is available for sheets
  that explicitly supply that counter.
- Cleric: Channel Divinity (including Divine Spark and Turn Undead) and Sear
  Undead are unsupported. The fixed sheet explicitly says so.
- No subclasses, species/background/feat packages, rests or class progression.

## Rules approximations and policy choices

- Default AoE coverage follows the DMG "Targets in Areas of Effect" table:
  `min(eligible_count, max(1, ceil(size_ft / k)))` with k = 10 for cones,
  30 for lines and 5 for every other shape. A replacement receives **only** shape, size and eligible count and
  returns a count or eligible-list indices. Policy orders placement. An area
  does not gain an allegiance exemption: legal allies/caster can be included
  when the heuristic fills the area. Spirit Guardians' designated exemptions
  are selected and frozen at cast time. Identical persistent-area declarations
  share membership, refreshed on cast/turn starts, without firing entry events.
- No distances, movement, line of sight, cover, concealment, senses, flight,
  opportunity attacks or object/environment physics. Otherwise legal creatures
  are assumed in declared range/reach. Explicit visibility/willingness/type
  flags are honored; refs do not recheck original targeting restrictions.
  Sacred Flame's cover exclusions are validated; no cover bonuses exist.
- All melee attacks are treated as within 5 feet for prone advantage and
  paralysis/unconscious criticals, including weapons with longer printed reach.
- Area damage rolls independently per target unless the block explicitly
  requests a shared roll. Magic Missile uses its specified shared roll and
  preselected simultaneous volley; concentration checks are per dart.
- Zero HP means unconscious/prone and unable to fight; there are no death saves,
  stabilization or instant-death calculations. Healing can restore an ally
  while combat continues. A side entirely knocked out/removed loses immediately;
  there is no postcombat wait to see whether a banished creature returns.
- The 2024 spell restriction is **one expended spell slot per global turn**,
  including reactions, not the old bonus-action/cantrip rule. Cantrips and
  slotless innate casts do not themselves consume that allowance. Counterspell
  wastes casting economy but does not spend the interrupted slot; daily innate
  uses are not refunded. Existing concentration ends when a new concentration
  spell's casting starts, before reactions; end callbacks can incapacitate the
  caster and prevent the replacement from being established.
- Prepared casters are assumed to have required components/foci/material value;
  material inventory/consumption and antimagic/silence are not simulated.
- AI uses direct damage expectations, approximate hit/save probabilities and
  a two-turn aura horizon, not search or optimal tactics. It ignores mitigation,
  friendly-fire risk and crit corrections in its scoring; buff/control spells
  without direct damage usually are not proactively selected. It prefers weak
  enemies and low-HP allies, commands existing forces, never replaces working
  concentration voluntarily, and uses Action Surge as a nova resource. It
  considers a bonus-action spell plus the remaining weapon routine together.
  Shield checks the actual pending roll; Counterspell is an attempt with a
  possible outcome change, not a prediction of the future save die.

## Known gaps

- Review finding #7 is deliberately deferred this round: Petrified does not
  grant incoming-attack advantage or Poisoned immunity, and Invisible does not
  grant initiative advantage. No changes for these omissions were made.
- This is the reviewed core, not a complete 2024 rules implementation. Equipment
  accounting, skill proficiencies/contests, sensory/social condition subrules,
  terrain, tactical movement, full monster automation and adventuring-day/rest
  resource recovery remain outside it. Base frightened conditions assume their
  source is visible; source-bound charm/grapple restrictions require an effect
  source. Generic condition support does not substitute for those missing systems.
- Statistical tolerances exercise means and frequencies, not an exhaustive rules
  oracle or all possible interactions among arbitrary future spells. No separate
  large-scale performance benchmark or cross-Python-version determinism guarantee
  is claimed. Reproducibility was verified on the supplied Anaconda environment.
- New effect vocabulary must be explicitly added to validation and execution;
  unrecognized declarations deliberately fail rather than being silently ignored.

No commits were made. The reviewed spell set and legacy pipeline source files
remain unchanged.

## Fix round 1

Only engine code, engine tests and `MONSTER_FORMAT.md` were changed. No spell
YAML, `FORMAT.md`, dependencies or legacy pipeline source was edited. No pip,
network access or commits were used. Existing statistical tolerances remain
unchanged.

### Findings and regressions

- **#6 — Guards:** Weapon/monster damage now goes through `execute`, including
  the shared expression evaluator and complete hit context. Continuous areas
  go through `resolve_block`, rechecking block/primitive guards on refresh and
  removing effects whose guards stopped passing. Block guards run per selected
  target before binding/economy effects. Spell attack primitives receive
  attacker/defender context too. Action/trait declarations with
  `grants_action: true` and nonempty effects are rejected, since that special
  action path replaces rather than executes effects.
  Tests in `test_engine_findings.py`:
  `test_finding6_weapon_guard_false_suppresses_damage`,
  `test_finding6_spell_guard_false_suppresses_each_path`,
  `test_finding6_continuous_area_guard_false_suppresses_effect`,
  `test_finding6_continuous_guard_rechecked_and_context_has_target`,
  `test_finding6_guarded_off_area_does_not_suppress_existing_spell`,
  `test_finding6_action_trait_guard_false_suppresses_damage`,
  `test_finding6_grants_action_rejects_unexecuted_guarded_effects`,
  `test_finding6_spell_success_and_end_callback_guards_false`, and
  `test_finding6_spell_attack_guard_receives_full_attack_context`.
- **#1 — Combining spells:** All instances retain their independent clocks,
  bindings, concentration and cleanup. Only the most potent same-spell instance
  applies to an overlapping target; equal potency favors the latest instance.
  Numerical ongoing strength uses expected dice/flat modifier magnitudes, not
  higher slot level by itself: more targets or longer duration do not strengthen
  an individual benefit, and past instantaneous damage does not strengthen a
  lingering marker. Suppressed effects remain stored, so ending/expiring the
  applicable instance immediately exposes the survivor. Modifiers, conditions,
  statuses, roll flags, action grants and recurring area damage respect selection.
  Tests: `test_finding1_same_spell_benefits_do_not_stack_and_survive_cleanup`
  (two Shield of Faith give +2 AC; two Bless give one d4; end either instance),
  `test_finding1_potency_beats_recency_and_durations_remain_independent`,
  `test_finding1_upcasting_target_count_is_not_greater_potency`,
  `test_finding1_instant_damage_does_not_strengthen_lingering_advantage`, and
  `test_finding1_most_potent_ac_bonus_applies`.
- **#9 — Encounter traces:** Added initiative order, turn-start and action log
  entries. Seed-1 real-sheet traces independently recompute initiative, assert
  turn/action/attack order, require enemy Attack actions and hits, and verify
  exactly 13 enemy damage reached party HP (87 to 74) in both encounters.
  Tests in `test_engine_simulation.py`:
  `test_finding9_enemies_act_hit_damage_and_follow_initiative` and
  `test_finding9_monsters_never_act_mutation_is_detected`. The latter patches
  `Policy.take_turn` to skip enemies and proves the same trace assertions fail
  with `enemies never act` for both opponents. Existing 1,000-run exact
  reproducibility tests remain intact; they are not the combat-sanity oracle.
- **#8 — Attack spells:** Added exact natural-1/natural-20 casts for every
  previously exercised attack-spell/scaling case, including independent beams,
  exact doubled dice counts and undoubled spellcasting modifiers. Separate
  casts at +7 versus AC 16 check a 60% hit rate and natural-critical frequency.
  Tests: `test_finding8_cast_nat1_nat20_exact_dice`,
  `test_finding8_cast_hit_rate_against_realistic_ac`, and
  `test_finding8_missing_critical_dice_mutation_is_detected`. The mutation
  forces `dice.roll(..., critical=False)` and the exact cast test fails.
- **#2 — Concentration timing:** Replacement ends existing concentration before
  offering Counterspell, even when the new casting is countered. Incapacity is
  checked after end callbacks and again after reactions, before establishing
  the replacement. Tests: `test_finding2_concentration_ends_before_counterspell`
  (also asserts state inside the reaction hook) and
  `test_finding2_haste_callback_cannot_establish_new_concentration`.
- **#4 — Self-Haste:** Applying a grant during the recipient's turn immediately
  provides the restricted action. Per-turn grant tokens prevent refresh or
  source replacement from granting a second entitlement. Each new turn resets
  the entitlement; ending the effect removes an unspent action.
  Test: `test_finding4_self_haste_grants_current_turn_once_and_one_next_turn`.
- **#5 — Damage instances:** Batches now hold unmitigated components, sum each
  type before save-half/resistance/vulnerability rounding, then apply the whole
  instance with one concentration check. Magic Missile still rolls its shared
  volley before application, but each dart remains an independent damage event
  and concentration check. Tests:
  `test_finding5_goblin_components_combine_before_mitigation`,
  `test_finding5_spell_components_one_instance_and_one_concentration_save`, and
  `test_finding5_magic_missile_keeps_per_dart_concentration_checks`.
  The existing Goblin rider test now checks one combined seven-damage packet
  instead of counting two component log entries; this strengthens the seeded
  damage assertion rather than relaxing a tolerance.
- **#3 — Innate levels:** `can_cast` rejects an explicit innate slot differing
  from the spell's permitted base level, before spending actions, daily uses,
  slots or concentration. Omitted and explicit correct levels still work.
  Test: `test_finding3_innate_upcast_rejected_before_resources`.
- **#7 — Deferred:** The three Petrified/Invisible omissions remain listed under
  Known gaps above, as requested.

### Verification and simulations

Executed with `PYTHONDONTWRITEBYTECODE=1` and the supplied Anaconda interpreter:

```powershell
& C:/Users/xgxxg/anaconda3/python -m pytest tests -q
& C:/Users/xgxxg/anaconda3/python -m engine.simulate --party fighter5 cleric5 --monsters goblin_warrior x4 --runs 1000 --seed 1
& C:/Users/xgxxg/anaconda3/python -m engine.simulate --party fighter5 cleric5 --monsters ogre --runs 1000 --seed 1
```

Both simulations are unchanged from the reviewed baseline:

| Opponents | Party wins | Draws | Mean rounds | Mean party HP | Mean resources spent |
| --- | ---: | ---: | ---: | ---: | --- |
| 4 Goblin Warriors | 1000/1000 | 0 | 1.820 | 79.569 | Action Surge 0.970; level-1 slots 0.169; level-3 slots 1.062 |
| 1 Ogre | 1000/1000 | 0 | 2.088 | 77.873 | Action Surge 1.000; level-1 slots 0.561; level-3 slots 1.074 |

These fixed builds/encounters do not exercise overlapping buffs, concentration
replacement, self-Haste, innate upcasting or guarded-off declarations. Their
targets have no relevant damage resistance/vulnerability, and the existing
spell critical implementation was already correct. New logging does not draw
random numbers. Therefore the fixes and stronger tests do not change these
seeded outcomes.

Final requested suite result (94 existing cases plus 66 regression cases,
including the mutation checks):

```text
160 passed in 31.74s
```

## Known issues accepted at gate (fix round 1)

Verified by the re-review and accepted for this milestone; none is reachable by the golden spells,
monsters, or builds in a normal simulation.

- **#7** Petrified incoming-attack advantage / Poisoned immunity and Invisible initiative advantage are
  not implemented (no current content applies these conditions).
- **#10** A creature already under another caster's Haste that casts Haste on itself loses its unspent
  Haste action for that turn (`engine/combat.py` grant suppression runs before the new grant is
  installed). Requires two concurrent Hastes on one creature.
- **#11** A same-spell instance whose primitives are all guarded off can still win overlap selection and
  suppress a working instance. No golden spell guards every primitive of an area block.

## Step 1: adventuring day

This section supersedes the historical exclusions of rests/adventuring-day
recovery above. The previously accepted issues **#7, #10 and #11** are unchanged.
Only the permitted engine, engine-test, character and documentation/content
paths were edited. No spell YAML or `FORMAT.md` was edited; no installation,
network access or commits were used.

### Implemented

- `engine/day.py`: strictly validated ordered encounter/rest YAML, three
  reviewed days, persistent party **object identity**, fresh monsters per
  encounter, seeded runs, per-encounter snapshots and summary/CLI output.
  `load_day`, `run_day` and `simulate_day` are reusable Python entry points.
- HP, slots, limited uses, remaining Hit Dice and cumulative resource spending
  carry across steps. Maxima/recovery declarations are separate from remaining
  counters. All positive-to-zero transitions are counted, including repeated
  knockouts of the same PC in one encounter.
- Short rests: only available PCs with positive HP participate; policy-selected
  Hit Dice heal `max(1, die + Con modifier)` each, capped at max HP; declared
  counters then recover. Long rests restore all HP, slots, **all Hit Dice** and
  declared long-rest resources, without erasing resource-spending history.
- Fighter recovery: Second Wind 3 maximum, +1/short rest, all/long rest;
  Action Surge 1 maximum, all on either rest. Cleric recovery: Channel Divinity
  2 maximum, +1/short rest, all/long rest; effects still unsupported. Slots
  recover only on long rests. Legacy integer counters remain compatible
  (no short-rest recovery, all on long rest); legacy sheets without Hit Dice
  simply cannot spend them. Both supplied PC sheets were migrated.
- Encounter cleanup ends instances through normal callbacks and then removes
  concentration, conditions, detached temporary effects, statuses and temp HP.
  Turn/slot bookkeeping is reset so a new combat's turn indices cannot collide
  with the previous encounter. HP and resources are not reset.
- A policy-controlled postcombat pass uses actual healing spell/feature
  resolution to rescue downed allies; it spends slots/uses, grants no free
  top-up, and permits no defeated-monster reactions. Zero-HP characters get no
  rest benefits and stay unconscious/out until an ally heals them or the day
  ends. A TPK fails immediately, before any healing or later rests.
- Raw `DayResult` includes survived/cleared and start/end/after-healing state,
  rounds, total downs and per-PC downs for every reached encounter. End state
  precedes cleanup/healing. JSON summary includes survival probability,
  cleared-count distribution, reached counts, mean starting HP%, slots,
  limited uses/Hit Dice, downs and rounds. Encounter means are **conditional on
  reaching that encounter**; unreachable entries have null scalar means.
- `--strategy` controls the party and independent `--monster-strategy`
  controls enemies. Both accept `default`, `nova`, `conservative`. Every policy
  decision (including reactions, targets, slot level and area exemptions) is
  routed to the appropriate side. The original `engine.simulate` public
  interface/default behavior remains available without CLI changes.
- `CHARACTER_FORMAT.md` documents the new declarations, day format, APIs,
  output semantics and rest/knockout model. `MONSTER_FORMAT.md` cross-references
  recovery and fresh per-encounter monsters.

### Strategy heuristics

These are transparent heuristics, not optimal play or a rules-based difficulty
oracle. Neither policy sees future rolls or encounter results.

- **Default:** original damage scoring, lowest legal slot, healing below 50%,
  weak-enemy targeting, existing concentration preservation/commands and
  immediate Action Surge when enemies remain. New short-rest hook spends dice
  toward full HP. The postcombat hook prefers Cure Wounds, otherwise Healing
  Word, otherwise an available ally-targetable healing action, stopping once
  that ally has positive HP.
- **Nova:** same damage scorer but always selects the **highest** legal slot,
  including healing/reactions. Damaging concentration spells (notably Spirit
  Guardians) score over the existing two-turn horizon and are opened early;
  working concentration is not replaced. Action Surge is used on the first
  available turn (normally round 1) if enemies remain. It does not budget for
  later encounters. Short-rest target is full HP.
- **Conservative:** estimates weapon/cantrip-only fight length as enemy HP /
  party expected DPR. Incoming DPR averages enemy weapon routines against
  allies, with currently available damaging nonspell actions also considered.
  Estimated total HP loss exceeding **35% of current party HP**, or any ally
  down, marks danger. Otherwise it prefers cantrips/weapons and withholds
  Action Surge and offensive slots. It only surges in danger.
- In danger, ordinary offensive/reaction slot spending is capped at
  `ceil(starting slots / remaining encounters)`, counting the current encounter
  and all later encounters in the definition (even beyond a long rest). It
  uses the lowest legal slot. An ally down or below **25% HP** overrides this
  cap. Combat healing below **35% HP** and postcombat rescue also bypass the
  offensive cap. Second Wind retains its original below-50% threshold.
  Short-rest dice are spent one at a time toward **85% HP**. Innate spells
  require danger but use daily counters rather than the spell-slot budget.
- Monster strategies use the same decision rules from their own allegiance;
  monster counters remain fresh each encounter. The default monster policy is
  independent of the selected party strategy.

### Three-day measurements

All below use exactly Fighter 5 + Cleric 5, **1,000 trials, seed 1**,
`--monster-strategy default`, maximum 100 rounds per encounter. Each trial
receives its own seed from the run RNG; encounter seeds and rest rolls come
from that trial's RNG. Policies consume different rolls as their actions and
rest decisions diverge; these are not identical combat-roll replays.

| Day file | Encounters / short rests | Nova survives | Conservative survives |
| --- | --- | ---: | ---: |
| `easy_day` | 3 / 1 | 1000/1000 (100.0%) | 992/1000 (99.2%) |
| `goblin_warren` (standard) | 7 / 2 | 114/1000 (11.4%) | 173/1000 (17.3%) |
| `hard_day` (dragon finale) | 5 / 2 | 0/1000 (0.0%) | 0/1000 (0.0%) |

Encounters-cleared distributions (`cleared: number of trials`):

| Day | Nova | Conservative |
| --- | --- | --- |
| Easy | `{3: 1000}` | `{2: 8, 3: 992}` |
| Standard | `{2: 2, 3: 112, 5: 379, 6: 393, 7: 114}` | `{1: 1, 2: 17, 3: 242, 4: 1, 5: 339, 6: 227, 7: 173}` |
| Hard | `{1: 13, 2: 63, 3: 385, 4: 539}` | `{1: 8, 2: 102, 3: 459, 4: 431}` |

The standard day is **demanding for these two simplified builds**, not a claim
that a standard adventuring day should kill 80% of tabletop parties. Nova is
safer early but exhausts its best slots before the first rest (rests do not
restore those slots). Conservative loses more parties in the middle but wins
more complete days, by 5.9 percentage points here. It is not universally better:
nova wins slightly more easy days and gets more parties to the dragon. Of
539 nova and 431 conservative parties reaching that finale, none defeat it.
No content/threshold/statistical tolerances were retuned after measuring these
outcomes to force the comparison to pass.

Standard-day per-encounter details (means conditional on reaching; slots are
level 1 / 2 / 3, HP% is summed real HP / summed max HP):

| Strategy | Encounter | Reached | Start HP% | Starting slots | Downs | Rounds |
| --- | ---: | ---: | ---: | --- | ---: | ---: |
| Nova | 1 | 1000 | 100.00 | 4.00 / 3.00 / 2.00 | 0.000 | 1.839 |
| Nova | 2 | 1000 | 91.63 | 4.00 / 2.98 / 0.76 | 0.022 | 2.463 |
| Nova | 3 | 1000 | 98.96 | 3.99 / 1.62 / 0.01 | 0.110 | 3.042 |
| Nova | 4 | 998 | 79.24 | 3.08 / 0.15 / 0.00 | 0.638 | 5.799 |
| Nova | 5 | 886 | 69.54 | 0.84 / 0.03 / 0.00 | 0.040 | 3.106 |
| Nova | 6 | 886 | 53.57 | 0.81 / 0.03 / 0.00 | 0.721 | 4.729 |
| Nova | 7 | 507 | 33.19 | 0.45 / 0.01 / 0.00 | 0.862 | 3.746 |
| Conservative | 1 | 1000 | 100.00 | 4.00 / 3.00 / 2.00 | 0.005 | 2.806 |
| Conservative | 2 | 1000 | 86.39 | 3.92 / 3.00 / 2.00 | 0.136 | 2.974 |
| Conservative | 3 | 999 | 91.44 | 3.43 / 3.00 / 2.00 | 0.254 | 3.715 |
| Conservative | 4 | 982 | 64.71 | 2.81 / 2.99 / 1.59 | 0.629 | 5.057 |
| Conservative | 5 | 740 | 65.58 | 1.91 / 2.87 / 1.01 | 0.020 | 3.366 |
| Conservative | 6 | 739 | 51.09 | 1.78 / 2.77 / 1.00 | 0.589 | 4.187 |
| Conservative | 7 | 400 | 44.45 | 1.12 / 2.25 / 0.66 | 0.818 | 4.245 |

For example, standard encounter 2 begins with mean remaining Action Surge
0.029 for nova versus 0.997 for conservative; mean total slots are 7.742
versus 8.920. At encounter 7 they are 0.464 versus 4.035 slots. These figures
include living and downed PCs, not just currently acting characters.

To reproduce every day/strategy result (no external tools):

```powershell
foreach ($day in 'easy_day', 'goblin_warren', 'hard_day') {
  foreach ($strategy in 'nova', 'conservative') {
    & C:/Users/xgxxg/anaconda3/python -m engine.day --party fighter5 cleric5 --day $day --runs 1000 --seed 1 --strategy $strategy --monster-strategy default --json
  }
}
```

### Simplifications and remaining gaps

- All encounters are separated by longer than every effect duration: no buff,
  concentration, temp-HP or condition carry-over, including exhaustion. This
  intentionally removes long-duration prebuff optimization. Knockout conditions
  are reapplied at zero HP; cleanup never grants HP. Permanent removal persists.
- Rests assume adequate uninterrupted time, food, and eligibility; no rest
  interruption, fatigue/sleep scheduling or once-per-day long-rest timer.
  Downed PCs cannot self-heal with Second Wind or spend Hit Dice at zero HP.
- Postcombat healing only rescues downed allies. No general healing-to-full,
  potions, resurrection, death saves, death, retreat, or retrying failed fights.
  A round-limit draw or party-unavailable loss fails the day; success counts
  cleared encounters rather than just having someone alive at timeout.
- The danger estimate ignores most control/spell tactics and shares the
  original scorer's no-grid/mitigation/crit limitations. It can hoard resources
  too long, especially when an injured party loses before the final encounter;
  it does not foresee long rests to reset its budgeting horizon. Positive-HP
  unavailable allies and enemy action economy can also distort that estimate.
  Nondamaging buffs/control are still generally not proactively selected.
- Channel Divinity effects and the previously recorded class/monster omissions
  are still unsupported. Known issues #7/#10/#11 were not folded into this task.
- Summary JSON is compact aggregate output; callers wanting every raw run's
  snapshots use `run_day` and `dataclasses.asdict`. No cross-Python-version
  reproducibility or broad performance guarantee is claimed.

### Verification

The new seeded tests cover strict/duplicate validation, legacy normalization,
exact Hit Die rolls/modifiers/minimum/capping, policy HP targets, partial/full
resource recovery, zero-HP exclusion from both rests, long-rest restoration,
cumulative spending, party identity, fresh monsters, cleanup, postcombat spell
and feature healing, repeated downs, unavailable allies, TPK/clear counts,
round limits, conditional summary means, JSON/text CLI, side-specific policies,
slot budgeting, early nova spending and reproducibility for all three policies.

The 1,000-run standard-day regression compares both strategies without changing
existing tolerances. Its predeclared 0.07 absolute survival-rate allowance
exceeds three worst-case independent-binomial standard errors
(`3 * sqrt(2 * .25 / 1000) = 0.0671`); the measured conservative advantage is
positive even with **zero** allowance. Existing engine/legacy tests remain in
the full suite.

Executed with the supplied interpreter:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& C:/Users/xgxxg/anaconda3/python -m pytest tests -q
```

```text
223 passed in 95.38s (0:01:35)
```

Both original 1,000-run `engine.simulate` CLIs were also rerun directly: the
four-goblin result remains 100% wins, 1.820 rounds, 79.569 HP; the ogre result
remains 100% wins, 2.088 rounds, 77.873 HP, with identical resource means to
the recorded baseline. `git diff --check` passed.


## Step 1 fix round

This section supersedes the earlier scorer limitations and measured results;
previous sections retain the historical build/review record. Changes in this
round are limited to `engine/combat.py`, `engine/policy.py`, this report, and
`tests/test_engine_*.py`. No spell YAML, `FORMAT.md`, or dependencies were changed. No network, pip,
or commits were used. Existing uncommitted step-1 work was preserved.

### Fixes and regression coverage

1. **Recovery eligibility:** before selecting a healing spell or feature,
   recovery probes the shared `Combat.eligible` rules for the downed ally.
   Incompatible features are skipped before `use_action` can spend their uses.
   `test_step1_fix1_humanoid_heal_skips_downed_beast_without_spending` uses
   validated Fighter-derived sheets, a real seed-1 Goblin Warrior fight, a
   humanoid-only heal, and a downed beast PC. Both leaving the beast down and
   falling through to a second, compatible heal are tested; the incompatible
   counter remains untouched.
2. **Routing coverage:** the original all-decisions test now drives two actual
   slot casters through Spiritual Weapon's optional attack and Shield's
   reaction. Separate team-checking policies use different slot preferences
   (lowest for party, highest for enemy), explicitly assert every hook was
   invoked for both teams, and verify slots and reaction economy actually
   changed. The day-level monster-policy wiring check is retained.
   `test_step1_fix2_*` independently recompiles `available_slot`,
   `offer_reactions`, and `resolve_block` in memory, routing just the tested
   slot/reaction/optional hook to the party policy. Each mutated implementation
   fails the same scenario with its specific `... misrouted` assertion; pytest
   restores the original method after each mutation.
3. **Shared EV scorer:** default, nova, and conservative still share
   `expected_spell_damage`; there is no spell-name preference or search.
   `test_step1_fix3_*` covers Spiritual Weapon beating Guiding Bolt (including
   its remaining mace action) against an Ogre with at least three estimated
   rounds left; proactive Hold Person against a weak-Wis Fanatic; all three
   strategies selecting Hold against a durable heavy-hitter variant; and all
   three rejecting it against a giant. Additional regressions check duration
   caps, aura/command/Hex/Hunter's Mark repeat credit, opportunity discounts,
   repeat-save uptime, start-versus-end save timing, immunity, Banishment,
   and scoring without RNG, resource, or instance mutation.

### Simple expected-value formula

All estimates use current state only. The scorer first applies the engine's
actual target filters, including humanoid/visibility restrictions and condition
immunities, and caps distinct targets by the available legal enemies. It scores
the same low-HP target order as the default policy. Mark riders inherit their
mark block's target eligibility. Damage uses the existing mean-dice, hit, save,
and half-on-success math.

- Let `DPR` be the sum over available allies of the better of their weapon
  routine and damaging cantrips. Let `H = max(1, current enemy HP / max(1, DPR))`.
  For a lasting spell, `R = min(H, duration in rounds)` (10 rounds/minute,
  600/hour). Fractional rounds receive proportional credit. The explicit
  one-round cantrip calculation does not recursively estimate an encounter.
- **Commands:** one expected attack on casting plus
  `0.85 * (R - 1)` later attacks. The 15% haircut reserves later bonus actions
  for healing/other uses. Current bonus-action availability remains enforced
  by `can_cast`; a bonus-action cast still receives the existing accompanying
  weapon-action credit in `Policy.take_turn`.
- **Recurring auras:** expected per-round damage times `R`, with the existing
  area coverage heuristic and one end-turn damage opportunity per target per
  round. No movement/entry triggers are invented.
- **Hit riders:** rider damage times expected successful attacks per round
  times `R`. Hit count uses the better weapon routine or attack cantrip;
  multiple attacks/beams count separately. The mark itself does not deal
  invented on-cast damage.
- **Control:** `P(initial save fails) * U * (enemy DPR denied + allied DPR gained)`.
  For an end-turn repeat-save failure probability `q`,
  `U = 1 + q + ... + q^(floor(R)-1) + fractional(R) * q^floor(R)`.
  Without repeat saves, `U = R`; a start-turn repeat save multiplies uptime
  by another `q`. The implementation uses the closed-form geometric sum,
  including exact `q = 1` handling. Incapacitated/Paralyzed/Stunned/
  Unconscious/Petrified deny the target's best at-will output against the
  available allies. Removal (e.g. Banishment) denies that output without
  awarding attacks against an absent target. Multiple incapacitating
  primitives in one block are not double-counted.
- Allied weapon damage gained uses `P(advantage) = 1 - (1 - P(hit))^2` and
  the increase over ordinary hit chance; Paralyzed/Unconscious also add
  expected melee critical dice, following the engine's within-5-feet model.
  Existing conditions and condition immunities do not earn duplicate credit.
- Lasting concentration value receives a **0.90 multiplier**, a fixed 10%
  opportunity-cost reserve for occupying concentration. Working concentration
  is still not voluntarily replaced. These 0.85/0.90 coefficients are explicit
  policy approximations, not measured probabilities or seed-tuned tolerances.

This remains a whole-round, at-will-rate heuristic, not an optimizer. It does
not forecast concentration-breaking rolls, enemy spell-slot expenditure,
future movement, mitigation/friendly fire, exact initiative fractions, or
advantage already supplied by another effect. Control attack-gain credit is
weapon-based, not a full resimulation of the party's future spells. There is
no promise that stronger scoring improves every seeded matchup or policy.

### Rerun: all three days

Exactly Fighter 5 + Cleric 5, **1,000 runs per row, seed 1**, default monster
policy, maximum 100 rounds, unchanged day/character/spell definitions:

| Day | Nova survivors (previous -> new) | Conservative survivors (previous -> new) |
| --- | ---: | ---: |
| `easy_day` | 1000 -> **991/1000 (99.1%)** | 992 -> **963/1000 (96.3%)** |
| `goblin_warren` (standard) | 114 -> **128/1000 (12.8%)** | 173 -> **163/1000 (16.3%)** |
| `hard_day` | 0 -> **0/1000 (0.0%)** | 0 -> **0/1000 (0.0%)** |

New encounters-cleared distributions:

| Day | Nova | Conservative |
| --- | --- | --- |
| Easy | `{2: 9, 3: 991}` | `{2: 37, 3: 963}` |
| Standard | `{2: 11, 3: 98, 5: 431, 6: 332, 7: 128}` | `{1: 1, 2: 59, 3: 192, 4: 1, 5: 412, 6: 172, 7: 163}` |
| Hard | `{1: 39, 2: 52, 3: 423, 4: 486}` | `{1: 29, 2: 102, 3: 464, 4: 405}` |

These changes are attributable to changed decisions, not rest/slot-rule changes:
monsters also use the improved scorer, including their innate control and
command spells. Thus an easier day can become less survivable even when the
party has a better scorer. Nova spends/control choices earlier; conservative
retains its unchanged danger gate and encounter budget. On the standard day,
the Cleric now casts **Spiritual Weapon 545 times and Hold Person 876 times**
under nova, and **78 / 23 times**, respectively, under conservative (counts
across all 1,000 trials, including trials failing before the finale). The
previous conservative counts were both zero. The predeclared **0.07** survival
allowance is unchanged; conservative's new advantage is 0.035 even without it.
The standard-day test additionally locks both new survivor counts and complete
cleared-count distributions, rather than merely comparing strategies.

### Standard day: level-2 slots per encounter

Means below are **conditional on reaching that encounter**, not all 1,000
trials. `Spent` is the sum of party level-2 slots at combat start minus combat
end; it includes any spell using a level-2 slot, not just native level-2 spells.
Postcombat rescue spent **zero level-2 slots at every encounter** for both
policies. Starting slots and spending were independently aggregated from raw
`run_day` snapshots while running the same `simulate_day` seed stream.

| Encounter | Nova reached | Nova start | Nova spent | Conservative reached | Conservative start | Conservative spent |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1000 | 3.000 | 0.020 | 1000 | 3.000 | 0.000 |
| 2 | 1000 | 2.980 | 1.234 | 1000 | 3.000 | 0.000 |
| 3 | 1000 | 1.746 | 1.593 | 999 | 3.000 | 0.010 |
| 4 | 989 | 0.140 | 0.084 | 940 | 2.989 | 0.103 |
| 5 | 891 | 0.015 | 0.000 | 748 | 2.858 | 0.098 |
| 6 | 891 | 0.015 | 0.000 | 747 | 2.760 | 0.218 |
| 7 | 460 | 0.009 | 0.000 | 335 | 2.090 | 0.278 |

The conservative gate still leaves unused resources on some failing runs;
that budget policy was not silently retuned as part of the scorer fix.

### Single-encounter reproducibility baselines

Both existing 1,000-run seed-1 opponent cases were rerun directly and twice
inside their exact reproducibility tests. No statistical tolerance was loosened;
the tests now also lock the following exact means/resource maps:

| Opponents | Wins / draws | Mean rounds | Mean party HP | Mean resources spent |
| --- | ---: | ---: | ---: | --- |
| 4 Goblin Warriors | 1000 / 0 | 1.820 | 79.569 | Action Surge 0.970; level-1 slots 0.169; level-3 slots 1.062 |
| 1 Ogre | 1000 / 0 | **2.034** | **78.541** | Action Surge 1.000; level-1 slots **0.974**; level-3 slots **0.633** |

The goblin baseline is unchanged: area coverage still makes Spirit Guardians
strong in that opener. The Ogre previously measured 2.088 rounds, 77.873 HP,
0.561 level-1 slots and 1.074 level-3 slots. Unlike the old fixed two-round aura
credit, the new horizon shrinks as the Fighter removes enemy HP, so a near-dead
Ogre can favor Guiding Bolt over starting Spirit Guardians. This legitimately
changes spell choices, resources, subsequent RNG consumption, rounds, and HP;
it does not change spell resolution or encounter rules. The original seed-1
enemy-action/hit trace checks (13 damage, 74 party HP) still pass unchanged.

Reproduction commands (run each day with both strategies):

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
& C:/Users/xgxxg/anaconda3/python -m engine.day --party fighter5 cleric5 --day easy_day --runs 1000 --seed 1 --strategy nova --json
& C:/Users/xgxxg/anaconda3/python -m engine.day --party fighter5 cleric5 --day goblin_warren --runs 1000 --seed 1 --strategy conservative --json
& C:/Users/xgxxg/anaconda3/python -m engine.day --party fighter5 cleric5 --day hard_day --runs 1000 --seed 1 --strategy nova --json
& C:/Users/xgxxg/anaconda3/python -m engine.simulate --party fighter5 cleric5 --monsters goblin_warrior x4 --runs 1000 --seed 1 --json
& C:/Users/xgxxg/anaconda3/python -m engine.simulate --party fighter5 cleric5 --monsters ogre --runs 1000 --seed 1 --json
& C:/Users/xgxxg/anaconda3/python -m pytest tests -q
```

Final verification with the requested interpreter and command:

```text
C:/Users/xgxxg/anaconda3/python -m pytest tests -q
243 passed in 117.21s (0:01:57)
```

All 223 existing cases plus 20 added regression cases pass. No existing
statistical tolerance was loosened. `git diff --check` passed. No separate
performance benchmark or cross-interpreter determinism check was performed.

### Known issues accepted at gate (step 1)

- **Conservative under-spends.** It frequently loses an encounter while holding resources
  (standard day: ~2.1 of 3 level-2 slots still unspent at encounter 7 among runs that reach it), and on
  the easy day it survives less often than nova (96.3% vs 99.1%). The danger trigger fires too late;
  budgeting needs tuning (e.g. spend when expected party loss this encounter exceeds the remaining-day
  budget, or when any ally is below 50% HP).
