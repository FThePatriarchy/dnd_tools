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

## Step 2: 2025 Monster Manual import

### Delivery and source boundary

Imported **all 66 exact requested names**, bringing the reviewed monster set to
70. Every record is from `raw_data/bestiary/bestiary-xmm.json` with `source: XMM`.
There is no MM/2014 fallback. The four original sheets only gained numeric
movement provenance and, for Cultist Fanatic, an explicit unsupported-spell/tag
note; their executable numbers and routines did not change.

Changed only `engine/`, `tests/test_engine_*.py`, the monster directory and
`MONSTER_FORMAT.md`. No spell files, `FORMAT.md`, character/build files,
dependencies, legacy pipeline code or day files were edited. No network, pip or
commits were used.

### Deterministic versus reviewed work

- The importer now handles tagged/flat weapon damage and multiple typed riders,
  structured saves/initiative/speeds/defenses, simple counted routines, simple
  save actions and areas, per-block DC, recharge/default Recharge 6, daily uses,
  printed spell statistics/levels/shared pools, simple legendary options, and
  directly stated Regeneration/Undead Fortitude/Parry numbers. Conditional
  defenses/movement remain unsupported text rather than unconditional bonuses.
- `python -m engine.monster_import --check` strictly loads all 70 sheets, reparses
  source-owned fields and fails with field paths on drift. Tests mutate hit/dice,
  DC, base statistics, recharge, daily uses, trait numbers, spell level/pool and
  legendary budget/cost to demonstrate that this gate is not vacuous.
- `engine/step2.py` is the explicit, reviewed hand-finishing ledger. Its optional
  `--write` regenerates only the 66 new YAML sheets; it does not write spell
  declarations. Every non-golden spell is named in `unsupported_spells` and has
  an omission note. Golden spells use real shared pools, printed levels and
  costs (Mage Fireball level 4; Mage Protective Magic; Priest Divine Aid).
- Minimal format additions and their motivating monsters are documented in
  `MONSTER_FORMAT.md`. Shared primitive resolution handles weapon conditions,
  hit-save riders, staged petrification, source-bound grapples/capacities/escape,
  abstract destructible webs, ongoing engulf/spore damage, auras, domination,
  healing prevention and maximum-HP drain. No damage-type or condition is merely
  declared supported because its name appears in a trait title.
- Legendary options spend a finite start-of-own-turn-reset budget at the end of
  other turns via the policy. Aboleth and Adult Red Dragon have lair-free 3/day
  Legendary Resistance, including policy refusal and automatic-failure coverage;
  neither mechanic was invented for the young dragons. Adult Red Dragon's
  Commanding Presence is unsupported until Command enters the golden set.
- Pack Tactics uses the requested no-grid approximation: another living,
  capable, melee-equipped ally is assumed engaged in melee. Ranged-only allies
  do not count. Parry changes only the pending melee hit, not subsequent AC.
  Troll regeneration can recover from 0; fire/acid damage disables exactly the
  next regeneration and permits a final death. Zombie Fortitude uses the whole
  mitigated packet and excludes Radiant/critical damage. Magic Resistance gets
  magical context from actual spell saves, not concentration checks.

### Validation and damage sanity definition

Every sheet is strictly loaded, fresh-source checked and cross-checked against
`damageTags`, `conditionInflict`, `savingThrowForced` and their Spell/Legendary
variants. A missing tag must have an explicit unsupported explanation; the test
also removes real Wyvern effects to prove that unexplained omissions fail.

Each creature takes three policy turns against four durable dummy opponents.
Seeded follow-up scenarios exercise every alternative weapon/action/trait,
every declared feature and every executable legendary option, asserting names
in the combat log. Behavioral tests separately cover legendary timing/reset/
cost/refusal, resistance spending, Troll shutoff/recovery, Pack Tactics, Zombie
Fortitude, magical versus nonmagical saves, Parry, source cleanup/immunity,
capacity, Web object mitigation, staged saves, domination and shared spell uses.

The table's **attack DPR** is a numeric fidelity oracle, not the policy's claimed
combat output: AC 16, neutral rolls, no critical correction, no conditional
riders, and one best legal source weapon routine. The source calculation derives
counts/alternatives directly from XMM prose plus parsed attacks; the YAML
calculation independently walks declared routines. All 70 agree to numerical
precision (test tolerance 1e-10); no numeric-drift exception was accepted.

Explicit exceptions to interpreting that attack-only number as *encounter* DPR:

- Aboleth, Chain Devil and Vampire Spawn append save actions to the same routine;
  Mummy appends control. Those save DCs/dice are checked separately, and actual
  execution exercises the appended options. Gladiator/Pirate/Wight/Adult Red
  Dragon may replace one attack, so their policy output need not use the neutral
  weapon-only maximum.
- All dragons and Hell Hound use rechargeable AoE breath; Air/Water Elementals
  have rechargeable saves; Basilisk has a bonus-action gaze. Geometry comes from
  the DMG count heuristic rather than invented adjacent squares. Cube Engulf
  and Whelm have hand-reviewed abstract target counts and enforce their printed
  size/capture capacity; exact space-entry paths remain unsupported.
- Fire Elemental aura, Vrock Spores, Cube/Water engulf damage, Barbed Hide,
  Regeneration, Fortitude, healing and drain change multi-turn outcomes, not
  the neutral weapon average. Their timing/typed damage is behaviorally tested.
- Advantage/conditional riders (Pack Tactics, Goblin Warrior/Boss, Bloodied
  Frenzy, Bugbear attacks on their own grappled targets, Worg's next-hit benefit)
  and Minotaur's opt-in charge change the applicable state. The no-grid AI does
  not fabricate a charge or hidden advantage.
- Caster spell damage/control, missing golden spells, legendary options and
  daily resource availability are deliberately not mixed into a supposedly
  universal CR-to-DPR formula. They do participate in the encounter simulations.

### Reproducible CR sanity protocol

Each row below is **one creature versus 2 x Fighter 5 + 2 x Cleric 5**, fresh full
resources/174 initial party HP, **500 independent trials, seed 1**, default
policy, default DMG area table, max 100 rounds. Win rate is **party** win rate;
rounds are averaged over all outcomes, not just party victories. This is a
report, not a balance assertion or a test threshold.

```powershell
& C:/Users/xgxxg/anaconda3/python -m engine.step2_report --runs 500 --seed 1
& C:/Users/xgxxg/anaconda3/python -m engine.monster_import --check
& C:/Users/xgxxg/anaconda3/python -m pytest tests -q
```

The reusable runner writes complete summaries to `engine/step2_cr.json` and the
same table to `engine/step2_cr_table.md`. Existing single-encounter/day
reproducibility baselines and statistical tolerances were retained, not updated
to accommodate the new monsters. The old roster-count assertion was replaced
by an exact 70-name set assertion (stronger than merely increasing a count).

### Outlier investigation and classification

Investigations included source numerical checks and first-trial structured
traces, using `random.Random(1).getrandbits(64)` as the first trial seed, matching
the Monte Carlo runner. They are classifications for this fixed no-grid matchup,
not revisions to official CR.

| Creature/group | Classification | Investigation / explanation |
| --- | --- | --- |
| CR 1/8 through CR 2 easy singletons | Genuine matchup | No low-CR creature beats this fresh four-PC party. Four turns plus two Action Surges routinely remove a singleton in round 1; pack abilities have no ally to activate against. This is not an all-monsters-never-act bug: seeded attack/turn logs are tested. |
| Air Elemental | Engine/AI limitation | First-trial trace selected Whirlwind twice; the policy values Prone but standing costs no modeled positioning. Flight, space occupation and forced displacement cannot protect it. |
| Barbed Devil | Genuine no-grid matchup | Source attacks/routine, immunity and Magic Resistance are intact. A singleton's Barbed Hide needs actual grapple partners; no extra 2014 attacks or allies were invented. Four-PC nova defeats it reliably. |
| Earth Elemental | Engine limitation | Earth Glide/Siege Monster cannot create cover, ambushes or building damage without terrain/objects. Its two printed attacks do not overcome four full-resource turns. |
| Fire Elemental | Engine limitation | End-turn aura executes (not silently lost on the caster's boundary), but entry damage/burning/terrain are explicitly unsupported. Even this weaker implementation causes noticeable party HP loss. |
| Gladiator | Genuine matchup | First-trial trace was disabled before acting and party ended at 174 HP: a Humanoid without Legendary Resistance is susceptible to the clerics' Hold Person and melee criticals. Parry cannot block that save. Three Spear attacks/Parry execute in other seeded coverage. |
| Hill Giant | Genuine no-grid matchup | Slow initiative and one turn versus four full-resource PCs explain its short survival. The two Tree Club/Trash Lob attacks and riders are source-accurate. No ranged kiting or terrain advantage is simulated. |
| Troll | Genuine matchup; roster limitation documented | Neither fixed build has Fire or Acid damage. The party can knock it to 0 but cannot permanently suppress Regeneration. First trial: 10 regenerations, 30 Rends, monster victory. 0-HP regeneration must keep the encounter alive, rather than incorrectly awarding an early party win. Loathsome Limbs spawning remains unsupported; that omission does not explain its wins. |
| Vampire Spawn | Genuine no-grid matchup, with explicit omissions | Two Claws plus save-based Bite and Necrotic healing/max-HP drain execute; no old-MM Regeneration was added (absent in this XMM block). Fresh radiant clerics and four-PC action economy beat this singleton. Environmental weaknesses and ally rescue are outside the encounter. |
| Water Elemental | Engine limitation, not no damage | Whelm executes capture, restraint, escape and recurring damage; it causes significant HP loss despite no party defeats. Suffocation, rescue placement and movement remain unsupported, reducing its threat. |
| Wraith | Engine limitation / genuine matchup | Incorporeal terrain/flight cannot deny melee in this model; the clerics have radiant options and healing. Life Drain still reduces actual maximum HP; its numbers are not replaced with a weak generic weapon. |
| Assassin | Engine limitation | First trial: three Light Crossbow attacks in round 1 but a party win. Cunning Action Hide, concealment and ranged separation cannot create tactical protection here. Evasion and Poison damage/riders execute; no 2014 Assassinate trait was invented. |
| Chain Devil | Engine limitation | Two Chains plus Conjure Infernal Chain and reaction gaze execute with real source-bound restraint. Pulling, limb positioning and battlefield trapping cannot deny four-PC focus fire. |
| Vrock | Engine/AI limitation | Spores are executable and tested, but the default scorer favors immediate Shred/control over recurring Poison damage. Flight and exact spore spacing are absent; four full-resource PCs reliably win despite meaningful HP loss. |
| Wyvern | Genuine no-grid matchup | The two printed Bite/Sting attacks and Poisoned rider execute. A high single-target Sting can down one PC, but two healers and two nova fighters counter a lone creature without legendary turns. Flight/ranged separation are not defensive tools here. |
| Young Black Dragon | Genuine DMG-heuristic result plus no grid | 30-foot Line covers one target, unlike White/Green's 30-foot Cone (three). First trial uses Acid Breath and three Rends, ending with 158 party HP. Flight/kiting cannot compensate. Do not "fix" this by inflating breath damage/coverage or importing a 2014 routine. |
| Stone Golem | Engine/AI limitation | Slow is explicitly outside the golden set. First trial still took 6 rounds and produced 12 Slams plus Magic Resistance saves: source offense is active. Its XMM defenses must not be replaced by 2014 nonmagical-weapon immunity. |
| Mage / young cone/long-line dragons | Genuine burst threat, heuristic-dependent | Printed upcast Fireball/shared protective pool and recharge breath can hit several PCs at once. Different AoE shape/size and initiative explain larger losses than some higher-CR single-target attackers. Missing non-golden spells and flight still limit fidelity. |
| Aboleth | Genuine control/legendary threat; environment limitation | First trial: two Dominate Minds, twelve Tentacles and ten Psychic Drains, monster victory. Control changes allegiance and damage permits repeat saves. Underwater Mucus Cloud, lair actions and long-timescale restoration are explicitly absent; resistance uses only 3/day. |
| Adult Red Dragon | Genuine overwhelming matchup | First trial ended in round 1 after Fire Breath and Fiery Rays. The source has 17d6 breath, DC 21, a 60-foot Cone, three legendary points and three lair-free resistances. No older-edition bite/claw or invented lair bonus was used. |

No remaining outlier required a numeric data correction after the source checks.
Implementation bugs found during development (falsey regeneration shutoff,
duplicate ongoing capture, maximum-HP drain double-counting, source-global aura
immunity and turn-local gaze expiry) were fixed and given targeted regression
tests, rather than reclassified as acceptable creature balance.

### Remaining limits / previously accepted issues

All omitted spells are visible by exact name in each sheet. Position, movement,
lighting/water, ranged separation, concealment, inventory interactions, breath
suffocation timers, corpse/limb summons and long-timescale curses are not silently
claimed executable. Web self-destruction is implemented, but ally rescue and
object-targeted spell planning are not. Domination's damage repeat and source
death are modeled; plane/mile/day checks are not.

Previously accepted #7 is now relevant to Basilisk: Petrified still lacks its
incoming-attack advantage and Poisoned-immunity subrules. Its denied actions,
automatic physical save failures and damage resistance are implemented. #10
(overlapping self-Haste action) and #11 (all-guarded-off spell overlap) remain
unchanged; this import does not introduce new Haste casters or golden spell
changes. Conservative day-policy under-spending also remains outside Step 2.
No separate cross-Python determinism or performance guarantee is asserted.

### Step 2 fix round

All nine review findings were fixed at their shared engine/data causes. No
spell YAML, `data/handwritten/FORMAT.md`, character/build data, dependency,
network, pip, or commit changes were made. Existing statistical tolerances and
seeded baseline expectations were not loosened.

Regression functions are in `tests/test_engine_step2.py`, named
`test_step2_fixN_...`. Dice are fixed to 2 (bounded by die size), so assertions
check exact damage components, recipients, saves/DCs, HP and event boundaries,
not merely a loss of HP. Each behavioral probe first passes on the real code,
then is rerun under an **in-memory** legacy-branch or sheet mutation inside
`monkeypatch.context()`: the same assertions must fail. Production files are
never patched by these mutation probes.

| Finding | Root-cause fix | Regression / killed mutation |
| --- | --- | --- |
| 1 | Target-turn reference resolution filters to the triggering bound creature. Same caster/name/condition reapplication removes that recipient's old effects/binding. | `test_step2_fix1_spores_recipient_timing_and_no_duplicate_ticks`: four infected recipients, reapplication, exactly one 2-Poison tick per recipient's own start, none at source start/end; successful repeat save stops only its recipient. Both unfiltered references and disabled replacement are killed. |
| 2 | Repeat-save upgrades use normal immunity-aware condition application, including concentration termination and other side effects. | `test_step2_fix2_petrification_immunity_and_normal_side_effects`: actual Stone Golem remains neither Petrified nor Incapacitated after DC 12 failure and keeps concentration; a nonimmune recipient petrifies only at end-turn repeat and loses concentration. Direct condition rewrite is killed. |
| 3 | Removed blanket incapacitation exclusions from passive dispatch and free triggered traits; retained restrictions on actions/reactions and explicit feature exceptions. | `test_step2_fix3_passive_auras_survive_incapacitation`: stunned Hezrou/Ghast still force exactly their target's DC 16/10 save; stunned Fire Elemental deals exactly 2 Fire to each of two aura recipients only at its end-turn. Both old blanket gates are killed. |
| 4 | Infernal Sting healing prevention depends on an active Poisoned condition from that exact effect instance, not any Poisoned condition or an unconditional marker. | `test_step2_fix4_infernal_sting_healing_depends_on_own_active_poison`: exact 8 Piercing + 8 Poison; immunity permits healing, removing just this Poisoned immediately permits healing despite unrelated poison, and next-source-turn expiry clears the ban. Unconditional data and ignored dependency are both killed. |
| 5 | Engulf's declarative admission gate rechecks remaining capacity before each target's save/damage; condition-level capacity remains a backstop. | `test_step2_fix5_engulf_admits_before_saves_and_damage`: one Large recipient gets one DC 12 save and 6 Acid, no saves/damage for three overflow creatures; ongoing 6 Acid occurs only on cube start. A Large candidate that cannot fit does not exclude later smaller candidates. Removing preflight is killed. |
| 6 | Zero-HP Troll survival depends on actual HP regained; unsuccessful regeneration permanently removes it even without an acid/fire shutoff marker. Logs record actual healing. | `test_step2_fix6_troll_dies_when_actual_regeneration_is_zero`: real Mummy inflicts exactly 5 Bludgeoning + 6 Necrotic; Troll dies at next own start with 0 healing, and encounter ends in round 1, not a draw. Unblocked zero-HP Troll still regains 15 even while stunned. Old shutoff-only death is killed. |
| 7 | Added an independent entry-scoped text parser, separate from `parse_monster`, `tagged_damage` and damage-expression helpers. Supplemented blocks carry exact XMM `source_ref`s. It verifies save/escape DC roles, damage dice/bonus/type, and recurring versus initial damage sentences. | `test_step2_fix7_independent_entry_numbers_kill_review_mutations`: Aboleth escape **14 -> 99**, Hezrou Stench **16 -> 1**, Vrock recurring **1d10 -> 100d10** each now fails the original combined source/tag/DPR gate with its exact numeric path. Disabling the new checker is killed. Additional scoped, bonus, plain-text and initial/recurring-swap mutations are rejected. `test_step2_fix7_tenfold_spore_damage_fails_exact_combat_probe` kills **1d10 -> 10d10** in the strengthened original Engulf/Whelm/Spores probe. |
| 8 | Added reusable `{burning: {}}`, `ignite`, turn-start ticking, and `extinguish`; both Burn and Fire Aura ignite creatures. Nonstacking hazard survives source/effect end. Local archive XPHB Burning (p. 362) specifies 1d4 Fire at own turn start, action + Prone/rolling, or dousing/submerging/suffocation to extinguish. Default policy extinguishes before attacking. | `test_step2_fix8_burning_is_generic_persistent_nonstacking_and_extinguishable`: two 7-Fire Burn hits produce only one 2-Fire tick per own start, no other-recipient/end-turn tick, exactly one action spent and Prone on rolling; generic later-spell primitive and external extinguishing work. Removing ignition, ticking, extinguishing, Burn wiring or aura wiring is killed. |
| 9 | Vampire Bite checks Grappled from any source, retaining Incapacitated/Restrained alternatives. | `test_step2_fix9_vampire_bites_ally_grapple_and_preserves_alternatives`: actual Bugbear Stalker ally grapple permits exactly one DC 14 save and 5 Piercing + 6 Necrotic, 6 maximum-HP drain/healing, with no other recipient damage; self-grapple and other alternatives still work, unqualified targets remain illegal. Self-source-only eligibility is killed. |

**Finding 3 full-roster audit:** inspected every trait declaration in all 70 XMM
source records and every engine incapacitation gate. The only explicit passive
capability exclusions are Assassin Evasion, Hobgoblin Captain Aura of Authority,
and the capable-ally requirement in Pack Tactics for Tough, Hobgoblin Warrior,
Kobold Warrior, Wolf, Dire Wolf and Hell Hound. These gates remain. Vampire
Weakness's incapacitation mention is the staking prerequisite, not a passive
shutoff. No additional wrongly gated passive traits were found beyond the three
reported auras. `test_step2_fix3_audit_all_monster_passive_incapacitation_gates`
asserts that complete roster and also verifies stunned Barbed Hide's exact
2-Piercing retaliation against its grappler, plus suppression of incapacitated
Unnerving Gaze (a reaction). Source-bound grapple release and action economy
restrictions are intentionally retained.

**CR rerun:** all **70 x 500 = 35,000** trials were rerun with seed 1 and the same
four fixed builds; all source/YAML neutral attack DPRs still match and there are
no draws. Only Fire Elemental's record changed: party wins **500 -> 489**
(**100.0% -> 97.8%**), mean rounds **2.794 -> 4.286**, mean party HP
**139.9 -> 119.6**. Burning now costs both HP and extinguishing actions. All other
69 complete records are unchanged (including Troll, Vrock and the gatekeeper
encounters); targeted mutations cover fixes not exercised by that default party.
`engine/step2_cr.json`, `engine/step2_cr_table.md`, and the table below contain the
new measurements. Terrain/object ignition and movement-triggered Fire Form
remain explicitly unsupported; creature burning is no longer deferred.

### CR measurements (500 runs each, seed 1)

| CR | Monster | Party win rate | Mean rounds | Party HP | Draws | Attack DPR source/YAML |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1/8 | Bandit | 100.0% | 1.000 | 173.5 | 0 | 2.200 / 2.200 |
| 1/8 | Cultist | 100.0% | 1.000 | 173.6 | 0 | 1.800 / 1.800 |
| 1/8 | Goblin Minion | 100.0% | 1.000 | 173.6 | 0 | 2.025 / 2.025 |
| 1/8 | Guard | 100.0% | 1.000 | 173.6 | 0 | 1.800 / 1.800 |
| 1/8 | Kobold Warrior | 100.0% | 1.000 | 173.4 | 0 | 2.025 / 2.025 |
| 1/4 | Goblin Warrior | 100.0% | 1.000 | 173.2 | 0 | 2.475 / 2.475 |
| 1/4 | Skeleton | 100.0% | 1.000 | 172.8 | 0 | 3.250 / 3.250 |
| 1/4 | Wolf | 100.0% | 1.000 | 173.4 | 0 | 2.475 / 2.475 |
| 1/4 | Zombie | 100.0% | 1.000 | 173.7 | 0 | 2.200 / 2.200 |
| 1/2 | Gnoll Warrior | 100.0% | 1.000 | 173.2 | 0 | 2.600 / 2.600 |
| 1/2 | Hobgoblin Warrior | 100.0% | 1.000 | 172.3 | 0 | 5.200 / 5.200 |
| 1/2 | Scout | 100.0% | 1.000 | 172.8 | 0 | 5.850 / 5.850 |
| 1/2 | Tough | 100.0% | 1.000 | 173.4 | 0 | 2.600 / 2.600 |
| 1/2 | Worg | 100.0% | 1.000 | 173.0 | 0 | 3.750 / 3.750 |
| 1 | Brown Bear | 100.0% | 1.000 | 172.5 | 0 | 6.500 / 6.500 |
| 1 | Bugbear Warrior | 100.0% | 1.000 | 172.3 | 0 | 4.275 / 4.275 |
| 1 | Dire Wolf | 100.0% | 1.000 | 172.6 | 0 | 4.250 / 4.250 |
| 1 | Ghoul | 100.0% | 1.000 | 171.8 | 0 | 8.100 / 8.100 |
| 1 | Giant Spider | 100.0% | 1.000 | 171.4 | 0 | 7.250 / 7.250 |
| 1 | Goblin Boss | 100.0% | 1.000 | 172.4 | 0 | 4.950 / 4.950 |
| 1 | Imp | 100.0% | 1.000 | 172.0 | 0 | 6.750 / 6.750 |
| 1 | Pirate | 100.0% | 1.000 | 171.9 | 0 | 5.500 / 5.500 |
| 1 | Quasit | 100.0% | 1.000 | 173.1 | 0 | 2.750 / 2.750 |
| 1 | Specter | 100.0% | 1.000 | 172.8 | 0 | 3.150 / 3.150 |
| 1 | Spy | 100.0% | 1.000 | 172.2 | 0 | 5.625 / 5.625 |
| 2 | Bandit Captain | 100.0% | 1.056 | 170.6 | 0 | 8.500 / 8.500 |
| 2 | Berserker | 100.0% | 1.066 | 171.7 | 0 | 4.750 / 4.750 |
| 2 | Cultist Fanatic | 100.0% | 1.000 | 171.0 | 0 | 6.075 / 6.075 |
| 2 | Gelatinous Cube | 100.0% | 1.030 | 164.4 | 0 | 5.625 / 5.625 |
| 2 | Ghast | 100.0% | 1.000 | 171.3 | 0 | 8.250 / 8.250 |
| 2 | Mage Apprentice | 100.0% | 1.014 | 171.3 | 0 | 7.000 / 7.000 |
| 2 | Ogre | 100.0% | 1.004 | 170.3 | 0 | 7.150 / 7.150 |
| 2 | Priest | 100.0% | 1.000 | 173.5 | 0 | 11.500 / 11.500 |
| 3 | Basilisk | 100.0% | 1.024 | 169.1 | 0 | 8.500 / 8.500 |
| 3 | Bugbear Stalker | 100.0% | 1.208 | 164.9 | 0 | 13.500 / 13.500 |
| 3 | Hell Hound | 100.0% | 1.088 | 156.0 | 0 | 11.000 / 11.000 |
| 3 | Hobgoblin Captain | 100.0% | 1.164 | 161.3 | 0 | 11.250 / 11.250 |
| 3 | Knight | 100.0% | 1.132 | 169.7 | 0 | 14.500 / 14.500 |
| 3 | Manticore | 100.0% | 1.194 | 165.6 | 0 | 11.250 / 11.250 |
| 3 | Minotaur of Baphomet | 100.0% | 1.382 | 166.0 | 0 | 11.550 / 11.550 |
| 3 | Mummy | 100.0% | 1.000 | 167.0 | 0 | 19.000 / 19.000 |
| 3 | Owlbear | 100.0% | 1.008 | 165.5 | 0 | 16.800 / 16.800 |
| 3 | Warrior Veteran | 100.0% | 1.258 | 170.1 | 0 | 10.000 / 10.000 |
| 3 | Wight | 100.0% | 1.602 | 164.8 | 0 | 9.900 / 9.900 |
| 4 | Guard Captain | 100.0% | 1.450 | 166.2 | 0 | 16.500 / 16.500 |
| 5 | Air Elemental | 100.0% | 2.868 | 148.8 | 0 | 18.200 / 18.200 |
| 5 | Barbed Devil | 100.0% | 2.074 | 157.0 | 0 | 17.500 / 17.500 |
| 5 | Earth Elemental | 100.0% | 2.816 | 150.3 | 0 | 18.200 / 18.200 |
| 5 | Fire Elemental | 97.8% | 4.286 | 119.6 | 0 | 11.000 / 11.000 |
| 5 | Gladiator | 100.0% | 2.130 | 160.7 | 0 | 19.800 / 19.800 |
| 5 | Hill Giant | 100.0% | 1.942 | 150.8 | 0 | 24.050 / 24.050 |
| 5 | Troll | 0.0% | 14.062 | 0.0 | 0 | 19.800 / 19.800 |
| 5 | Vampire Spawn | 100.0% | 1.962 | 157.4 | 0 | 8.800 / 8.800 |
| 5 | Water Elemental | 100.0% | 2.270 | 128.4 | 0 | 15.600 / 15.600 |
| 5 | Wraith | 100.0% | 1.828 | 159.7 | 0 | 11.550 / 11.550 |
| 6 | Mage | 94.0% | 1.766 | 95.4 | 0 | 27.225 / 27.225 |
| 6 | Vrock | 100.0% | 3.560 | 131.2 | 0 | 22.550 / 22.550 |
| 6 | Wyvern | 100.0% | 2.264 | 148.6 | 0 | 29.100 / 29.100 |
| 6 | Young White Dragon | 90.6% | 3.130 | 68.5 | 0 | 20.700 / 20.700 |
| 7 | Young Black Dragon | 100.0% | 2.894 | 137.7 | 0 | 22.500 / 22.500 |
| 8 | Assassin | 99.4% | 1.924 | 138.7 | 0 | 53.100 / 53.100 |
| 8 | Chain Devil | 100.0% | 3.422 | 136.7 | 0 | 13.200 / 13.200 |
| 8 | Hezrou | 98.2% | 3.836 | 127.7 | 0 | 27.900 / 27.900 |
| 8 | Young Green Dragon | 69.6% | 3.572 | 48.4 | 0 | 32.400 / 32.400 |
| 9 | Bone Devil | 87.0% | 3.922 | 88.3 | 0 | 38.350 / 38.350 |
| 9 | Young Blue Dragon | 36.0% | 3.910 | 22.4 | 0 | 36.750 / 36.750 |
| 10 | Aboleth | 5.8% | 4.582 | 5.5 | 0 | 16.800 / 16.800 |
| 10 | Stone Golem | 87.6% | 5.254 | 92.4 | 0 | 36.000 / 36.000 |
| 10 | Young Red Dragon | 3.8% | 3.288 | 2.1 | 0 | 37.125 / 37.125 |
| 17 | Adult Red Dragon | 0.0% | 1.014 | 0.0 | 0 | 52.725 / 52.725 |

### Final verification

```text
C:/Users/xgxxg/anaconda3/python -m pytest tests -q
487 passed in 218.81s (0:03:38)

C:/Users/xgxxg/anaconda3/python -m pytest tests/test_engine_step2.py -k step2_fix -q
12 passed, 232 deselected in 24.55s

C:/Users/xgxxg/anaconda3/python -m engine.monster_import --check
70 XMM sheets checked: no source drift

C:/Users/xgxxg/anaconda3/python -m engine.step2_report --runs 500 --seed 1
70 monsters, 35,000 trials completed; no draws
```

All 243 previous cases and 244 Step 2 cases pass, including the 12 fix-round
cases and their in-memory mutation proofs. Existing exact reproducibility
baselines and statistical tolerances are unchanged. Source-tag checks, numeric
checks (now including hand-finished blocks), and neutral attack-DPR equality
cover all 70 sheets. `git diff --check` passes. The golden spells/format,
characters and dependencies have no diff. No network, pip or commits were used.

### Step 2 fix round 2

Findings 10-12 and the remaining portions of 3, 5 and 7 are corrected.

- **Engulf (10; residues 3/5):** `engulfed` is now a source-bound status,
  independent of Restrained and grapple/control cleanup. Restrained is only
  an additional consequence. Admission capacity, recurring acid, Verbal spell
  blocking and Strength-only action escape all use that status. A stunned cube
  retains its occupants and continues its acid ticks. A Restrained-immune actual
  Air Elemental occupies all four capacity units, so later targets in the same
  action (and subsequent attempts) receive neither a save nor damage. Condition
  removal does not release occupancy; successful escape does. Reapplication
  replaces the previous occupancy without duplicate ticks, including immune
  occupants. Default policy attempts escape even without Restrained.
- **Independent numeric gate (11; residue 7):** source-entry checks now include
  legendary-option healing dice, healing primitives, Web obstacle AC/HP, and
  declared capacity/large-creature costs. Engulf explicitly reads the referenced
  Ooze Cube capacity rule; Whelm and limb grapples read their own entry, never
  a monster-wide number pool. Whole legendary options are walked, while copied
  effect blocks retain their own action provenance. The systematic scan exposed
  further holes, also closed: aura radii, declared target counts, minute-to-round
  duration conversion, single-next-attack uses, default legendary costs, and
  duplicate innate-use counters.
- **Minotaur (12):** both the importer/supplement and reviewed Gore sheet gate
  the extra 3d6 on Large-or-smaller size as well as caller-supplied `charged`.
  Exact fixed-dice regressions give Large 18 Piercing plus Prone, Huge/Gargantuan
  12 Piercing without Prone, and uncharged Large 12 without Prone. Reviewed Cube
  and Minotaur sheets were also compared with fresh in-memory generation.

**Systematic mutation scan:** the regression traverses every structured numeric
field in all 70 sheets, a superset of all hand-finished blocks (not just the
reported examples). It changes each scalar/numeric CR string, and separately
changes dice count, die size, and any embedded signed bonus. Boolean flags and
source/unsupported prose are not numeric fields. Each mutant is independently
passed to `check_sheet()` against the original raw XMM entry; exceptions are
not counted as successful rejections. Explicit review mutations are additionally
verified schema-valid before source checking.

| Scan measure | Count |
|---|---:|
| XMM sheets | 70 |
| Distinct numeric fields | 1,722 |
| Scalar/numeric-string fields and mutations | 1,489 |
| Dice-expression fields (including HP and healing) | 233 |
| Dice-component mutations | 525 |
| Total mutations | 2,014 |
| Rejected by `check_sheet()` | 2,014 |
| Surviving / allow-listed mutations | 0 / 0 |

`STEP2_NUMERIC_ALLOWLIST` is explicitly empty. An uncaught field fails with its
monster, path and component; any future exception must name the exact field and
supply a reason. Stale exceptions fail too. Existing tolerances and reproducible
baselines were not relaxed. Protected `data/handwritten/spells/` and
`data/handwritten/FORMAT.md` were not edited; no pip, network or commits used.

The previous 35,000-trial CR measurements were not rerun for this round; they
remain historical results, not fresh measurements of this revision.

Verification:

```text
C:/Users/xgxxg/anaconda3/python -m pytest tests/test_engine_step2.py -k step2_fix -q
26 passed, 232 deselected in 37.19s

C:/Users/xgxxg/anaconda3/python -m engine.monster_import --check
70 XMM sheets checked: no source drift

git diff --check
(no whitespace errors)
```

Summary: Engulf's independent state and immune occupancy are covered, the
independent source gate rejects all 2,014 mutations of 1,722 numeric fields
across 70 sheets (zero survivors or allow-list exceptions), and both charged
Gore consequences respect target size. Full-suite verification:

```text
C:/Users/xgxxg/anaconda3/python -m pytest tests -q
501 passed in 242.38s (0:04:02)
```
