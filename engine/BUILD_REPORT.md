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

- Default AoE coverage (since 2026-10-24) starts from the DMG "Targets in Areas of
  Effect" table, `max(1, ceil(size_ft / k))` with k = 10 for cones, 30 for lines
  and 5 for every other shape. The party's areas use that count. Everyone else's
  areas use half of it, rounded up and at least one, because players spread out
  against monster areas. Either is capped by the eligible creatures. The pure DMG
  rule remains available as `policy.dmg_area_heuristic`. A replacement receives
  shape, size and eligible count (plus `caster=` if it sets `wants_caster`;
  `avoids_allies` opts in to the default's ally avoidance) and returns a count
  or eligible-list indices.
- Multi-target grabs (`n_targets` actions whose failure grapples, restrains or
  engulfs: Engulf, Whelm) reach at most half the eligible group, rounded up, by
  default (`policy.grab_cap`; `Combat(target_cap=policy.printed_grab_count)`
  restores the printed count). Both defaults come from the DMG budget
  calibration: `data/reports/calibration_area_compare.md` and
  `calibration_grab_compare.md`. Policy orders placement. An area
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
  controls enemies. Both accept `default`, `nova`, `conservative`, `rationed`
  (added 2026-10-25; see "Rationed strategy" below). Every policy
  decision (including reactions, targets, slot level and area exemptions) is
  routed to the appropriate side. The original `engine.simulate` public
  interface/default behavior remains available without CLI changes.
- `CHARACTER_FORMAT.md` documents the new declarations, day format, APIs,
  output semantics and rest/knockout model. `MONSTER_FORMAT.md` cross-references
  recovery and fresh per-encounter monsters.

### Strategy heuristics

These are transparent heuristics, not optimal play or a rules-based difficulty
oracle. Neither policy sees future rolls or encounter results.

#### Rationed strategy (2026-10-25)

`RationedPolicy` treats a known day's resources as a budget. An audit of an easy
six-encounter L5 day showed why the others run dry: default casts any leveled
spell that beats a cantrip on expected damage (Fireball three times a day into
600 XP fights). Conservative's "dangerous" test compares forecast HP loss with
party HP divided by encounters left, which early in a long day is a small
share, so trivial fights still qualify. Its slot choice also upcasts. Rationed:

- **Slot budget:** an equal share of slot levels (a level-3 slot costs 3) per
  encounter left before the long rest, from the slots held at the encounter's
  start. It is recomputed every encounter, so unspent budget carries forward,
  and a single encounter has the whole budget.
- **Overrides:** it spends beyond the share if an ally is down or below 25% HP,
  or if a weapons-and-cantrips fight is forecast to cost more than 25% of
  current party HP or the fair share for this encounter. The forecast is
  enemy HP over party at-will damage, times average incoming damage, halved
  because enemies drop during the fight.
- **No waste:** no leveled spell once at-will damage this round already covers
  the enemies' HP. Lowest legal slot only. Slot healing only for allies at 0 HP
  or below 25%.
- **Short-rest features:** Action Surge and Channel Divinity are spent on such
  fights, or freely in the last encounter before a rest
  (`combat.encounters_until_rest`, set by `run_day`).
- **Hit Dice:** `run_day` calls `before_rest(combat, party, kind,
  short_rests_left)`. Each short rest gets a share of each character's
  remaining dice, ceil(dice / short rests left before the long rest). That share
  is spent up to 90% HP, and anyone below half HP may go beyond it.

Measured on the L5 standard party, six encounters with two short rests: on the
easiest day it ends with 69% of slots (default 27%, conservative 14%). The
hardest day that keeps deaths at or below 5% rises from 0.35x to 0.43x Moderate
per encounter (800 to 1,200 XP per fight), ending with 24% of slots. The
single-encounter rating is unchanged within seed noise (0.78x vs 0.80x High).
Known gap: on hopeless days it can die with slots unspent, because the
emergency release waits for an ally to fall below 25% HP.

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

## Step 3: spells

### Final inventory

**239 required / 239 loaded / 0 remaining files**: 219 new translations and the
20 byte-identical human-reviewed goldens. All 391 XPHB spells are classified:
**188 combat / 113 partial / 90 out_of_scope**. The 17 mandatory monster
references all load. The source is the 2024 XPHB spell text; embedded creature
statistics use its referenced XPHB blocks or explicitly named XMM creatures,
not legacy spell rules. Conjure Animals is the 2024 intangible damaging pack,
not a fabricated set of animal stat blocks.

One combat spell is deliberately **load-only: Revivify**. This is an explicit
impossibility in the current knockout-only model, not an omitted file disguised
as a translation: no Dead state, death timestamp, old-age cause or missing-body
state exists. Healing an unconscious 0-HP creature would violate its source.
Spare the Dying records Stable, but there is likewise no death-save clock.
Purely spatial partials have explicit unsupported entries and no fake buffs,
removal or guaranteed environmental damage.

| Level | Combat | Partial | Out of scope | Required | Loaded | Remaining |
|---|---:|---:|---:|---:|---:|---:|
| 0 | 20 | 6 | 8 | 29 | 29 | 0 |
| 1 | 34 | 17 | 13 | 53 | 53 | 0 |
| 2 | 29 | 18 | 16 | 47 | 47 | 0 |
| 3 | 24 | 20 | 8 | 44 | 44 | 0 |
| 4 | 20 | 13 | 8 | 33 | 33 | 0 |
| 5 | 18 | 15 | 15 | 33 | 33 | 0 |
| 6 | 16 | 10 | 8 | 0 | 0 | 0 |
| 7 | 9 | 6 | 6 | 0 | 0 | 0 |
| 8 | 7 | 6 | 5 | 0 | 0 | 0 |
| 9 | 11 | 2 | 3 | 0 | 0 | 0 |

Required includes five mandatory utility exceptions. Levels 6?9 are classified,
not translated. No scope entry was downgraded to hide unfinished implementation.

### Resume repairs, batching and format

The interrupted range investigation is resolved: all self-centered cones,
lines, cubes, spheres and emanations use `range: {type: self}` and carry their
shape/size on the target, matching unchanged Spirit Guardians. This includes
Burning Hands, Thunderwave, Lightning Bolt, Arms of Hadar, Word of Radiance,
Thunderclap, Color Spray, Conjure Barrage, Aura of Vitality and Detect Magic.
The independent gate now checks range **type**, not just whether its number
appears somewhere in the text; it also checks duration units and casting time.

The resumed inventory progressed through focused passing checkpoints of
118, 139, 159, 179, 199, 217, 226, 233 and 239 files. The last two small batches
separated preparation wards from creature forms to keep failures local.
Existing golden files were never rewritten. FORMAT's original text and checkout CRLF prefix are
preserved; additions remain in its append-only `## Step 3 additions` section.

New shared mechanics (with their requiring spells listed in FORMAT) cover:

- Long uninterrupted `prepare` casting, target-all and recipient choices;
  source-typed defenses, restoration, healing maximization and stabilization.
- Delayed/flat damage, leeching and damage budgets; recipient commands;
  weapon-only riders, save/concentration modifiers and reaction retaliation.
- Charm ending rules, control, source-typed wards, Sanctuary, Confusion/Crown
  behavior, Sleep progression, counted Contagion saves and resisted removal.
- Aid HP maxima, Hit Dice, Goodberry stock, Death Ward, Warding Bond, Resistance,
  Circle of Power, Mirror Image and Blink. Gaseous Form supports target-local
  Magic-action dismissal and zero-HP ending.
- Weapon-bound attacks/enchantments, post-hit smites, Lightning Arrow packet
  replacement, independent save-based splash (never critical-doubled), exact
  Staggering Smite expiry, and a non-upcasting Divine Smite fiend/undead bonus.
- Triggered Explosive Rune preparation, slot-dependent curse durations,
  distinct duplicate-die Chromatic Orb leaps, targetable Bigby's Hand, and
  Polymorph's retained HP/type, form temporary HP and stat restoration.
- All required summon spells embed targetable combatant stat blocks. They act
  immediately after the caster per the task convention. AC/HP/damage/attack
  counts scale from the printed blocks. Fixed XMM creatures retain their own
  attack bonus/PB. Animate Dead/Objects have real multi-creature counts and
  command costs; persistent bodies, familiar Help, steed flight, construct
  reactions, spirit auras/actions, Dragon breath and shared resistance execute.

### Automated validation and mutation results

`engine/step3_validation.json` is the reproducible per-spell audit. The audit
CLI now exits 0; a regression asserts all 239 required names are installed.

| Check | Final result |
|---|---:|
| Strictly loaded spells | 239 |
| New spell files numerically audited | 219 |
| New-spell numeric fields | 2015 |
| Numeric mutations rejected | 2276 / 2276 |
| Survivors / justified mutation allow-list | 0 / 0 |

Every loaded spell passes source damage-type, condition, saving-throw and
spell-attack tag coverage: a tag is executable or explicitly accounted for in
`unsupported`. Tags are not substituted for the printed mechanics. In particular,
Animated Object's printed Force Slam supersedes obsolete physical-damage tags.
Numeric evidence is role-specific: base dice versus later damage, initial versus
recurring phases, slot tiers, area dimensions, range, duration, components and
referenced stat-block fields. Zero bonuses and unused fixed-stat scaling are
checked format identities, not unchecked arbitrary numbers. Every numeric/dice
component mutation is rejected; no surviving mutant is excused.

- **457 full-cast arena configurations**, including max slot 5 and cantrip
  character levels 1/5/11/17, assert every top-level effect block fires. Chosen
  control/rider states, exact expiry and exceptional mechanics have focused tests.
- **88 embedded-form/slot configurations** exercise real combatants, their
  actions and passive/turn-triggered blocks. Familiars cannot attack and Help;
  summons remain targetable and obey control/lifetime rules.
- **302 direct-damage phase configurations** compare seeded per-target means
  against independent XPHB dice arithmetic, hit/critical and fail/success branches.
  Delayed phases and conditional modes are isolated from unrelated same-type
  damage. Full casting/action economy is tested separately, not replaced by
  isolated-block tests.
- The direct check uses **581,195 seeded effect resolutions**. Tolerance remains
  exactly `max(0.18, 2.5% of expectation)`. Sample sizes use an a-priori Bernstein
  bound (failure bound <= .001 when reducing N), capped at the historical 4,000;
  the separately modeled capped exploding-die process retains 4,000. No
  tolerance or expected value was tuned to make a failing observation pass.
- All **66 attacking summon form/slot configurations**, plus the original
  **20 referenced-block checks**, use exact balanced strata: all 20 natural
  attack results, each paired with low/high damage faces. This checks actual
  resolution and critical dice with exact linear means, without spending
  80,000 random trials testing already-covered uniform dice. Twelve weapon-spell
  configurations use the same method; their tolerance is `1e-10`. Additional
  source-exact checks cover Bestow Curse damage and Alter Self natural weapons.

Performance improvements also cache read-only source evidence/inventory and
share deterministic scaled specs. The hot condition path avoids rebuilding
irrelevant defense/ward lists when there are no effects; unenchanted weapons
are not unnecessarily deep-copied. No baseline trial count, assertion or old
statistical tolerance was loosened.

### Monster wiring and reproducibility

All 70 XMM sheets pass `engine.monster_import --check`. All newly available
`unsupported_spells` were moved into source-owned spell lists, preserving uses,
slot levels, costs, component exemptions, recharges and legendary resources.
No loaded spell remains in an unsupported-spell list. Wiring is idempotent;
monster HP, AC, abilities and ordinary attacks were not retuned.

The XMM numeric scan rejects **2,052 / 2,052** mutations of **1,760** fields,
with no exceptions (historically 2,014 / 1,722). The added fields are actual
spell levels/uses. The only pre-existing reproducibility changes remain the
previously documented enemy Command wiring, not the additional spell files:

| Standard day, 1,000 seed-1 runs | Before wiring | After wiring | Command-disabled control |
|---|---:|---:|---:|
| Nova survived | 128 | 127 | 128 |
| Conservative survived | 163 | 162 | 163 |

Nova cleared counts remain `{2:8, 3:97, 5:449, 6:319, 7:127}`; conservative
counts remain `{1:1, 2:47, 3:203, 4:1, 5:397, 6:189, 7:162}`. The isolated
control and historical distributions are in `engine/step3_day_baselines.json`.
No strategy assertion was relaxed. The catalog-count assertion necessarily
changes to 239; the 20 golden byte hashes remain fixed.

#### CR sanity: before versus after wiring

Fighter 5 / Fighter 5 / Cleric 5 / Cleric 5 versus one monster, **500 runs,
seed 1**. Final measurements reproduce the earlier wired-subset rows exactly:
additional files do not retune monsters whose spell lists were already complete.
Artifacts: `engine/step3_cr_before.json`, `engine/step3_cr_after.json`.

| Monster | Printed CR | Party wins before -> after | Mean rounds before -> after | Mean party HP before -> after |
|---|---:|---:|---:|---:|
| Mage | 6 | 470/500 -> 461/500 | 1.766 -> 1.808 | 95.370 -> 88.472 |
| Priest | 2 | 500/500 -> 500/500 | 1.000 -> 1.000 | 173.516 -> 173.516 |
| Mage Apprentice | 2 | 500/500 -> 500/500 | 1.014 -> 1.022 | 171.348 -> 165.094 |
| Cultist Fanatic | 2 | 500/500 -> 500/500 | 1.000 -> 1.000 | 171.038 -> 171.038 |
| Imp | 1 | 500/500 -> 500/500 | 1.000 -> 1.000 | 171.984 -> 171.984 |
| Quasit | 1 | 500/500 -> 500/500 | 1.000 -> 1.000 | 173.116 -> 173.116 |
| Stone Golem | 10 | 438/500 -> 308/500 | 5.254 -> 6.344 | 92.448 -> 63.204 |
| Aboleth | 10 | 29/500 -> 29/500 | 4.582 -> 4.582 | 5.490 -> 5.490 |
| Adult Red Dragon | 17 | 0/500 -> 0/500 | 1.014 -> 1.022 | 0.000 -> 0.000 |
| Druid | N/A | Not present in the handwritten catalog | N/A | N/A |

Mage now has its real Cone of Cold; Apprentice has Ice Knife/Thunderwave;
Stone Golem has recharging bonus-action Slow; Adult Red Dragon has legendary
Commanding Presence. Unchanged rows are measured, not assumed unchanged.
These are policy/build sanity measurements, not reassigned challenge ratings.

### Least-confident translations and explicit model boundaries

- **Revivify:** load-only impossibility explained above. Stable and Death Ward's
  ordinary damage interception are implemented; the arena has no nondamaging
  instant-death event or death-save clock.
- **Polymorph / inventory-dependent weapons:** three reviewed Beast forms are
  embedded (Wolf, Brown Bear, Riding Horse); other Beast sheets require an
  explicit reviewed form. Weapon spells bind the selected/default first eligible
  weapon, not every attack. Exact item eligibility/transfers, mixed-size Animate
  Objects selections and corpse provenance require external inventory choices.
- **Free-form commands/illusions:** Suggestion implements the explicitly allowed
  cease-fighting suggestion; arbitrary safe instructions, Phantasmal Force content,
  and hostile Planar Binding interpretations need a DM. No prose is executed as
  mechanics. Geometry/senses-dependent Fear movement/line-of-sight saves,
  Compulsion movement saves and illusion-only effects are unsupported explicitly.
- **Glyph of Warding:** Explosive Rune waits for an external trigger and is
  one-shot. Spell Glyph storage needs prepared-spell/object/trigger state; no
  unearned stored slot or instant long casting is fabricated.
- **Hallow, Magic Circle, Meld into Stone, barriers and other spatial-only
  partials:** wards/eligible nonspatial effects execute where declared; terrain,
  overlap, reversed entry boundaries, possession, stone destruction and destination
  mishaps require missing object/grid/planar state. Meld does not grant general
  invulnerability or guaranteed Force damage.
- **Summons:** exact reach, aura membership, mounted movement, shared senses,
  Life Bond proximity and teleport placement use the no-grid boundary. Familiar
  initiative deliberately follows the task's caster-initiative convention rather
  than its printed independent roll. Phantom Steed's dismount fade is spatial.
  Summon Elemental/Aberration generated versions conflict with their printed
  parents; the parent blocks control statistics.
- **Source discrepancies:** Ice Storm uses printed base 2d10 and increment 1d10,
  not the conflicting base in its higher-slot tag; Animated Object uses Force.
  Source tags remain cross-checked, but cannot override the actual paragraph.

### Verification and runtime

Final stable-tree full-suite verification (captured in `engine/step3_pytest.log`):

```text
C:/Users/xgxxg/anaconda3/python -m pytest tests -q
1887 passed in 418.92s (0:06:58)
```

The historical 98-file subset took **723.86s (12:03), 1,153 tests**. The final
239-file catalog takes **418.92s (06:58), 1,887 tests**: **42.1% less wall time**
with 734 additional cases. No tolerance or pre-existing assertion was loosened.
Earlier completed full runs passed 1,885 cases in 496.66s and 1,887 in 420.37s;
the final run also includes the corrected flat-retaliation Bernoulli oracle.
Superseded interrupted development runs are not represented as passing gates.

Final separate checks:

```text
python -m engine.step3_report
239/239 required/catalog spells loaded; 0 missing; 2276 numeric mutants; 0 failures

python -m engine.monster_import --check
70 XMM sheets checked: no source drift
```

Golden SHA-256 checks preserve all 20 files byte-for-byte. FORMAT retains its
original text and checkout CRLF prefix; only the Step 3 section was appended.
A semantic YAML diff confirms the eight changed monster sheets contain only
spell wiring/resource/omission-note changes. Wiring is idempotent and no loaded
spell remains in `unsupported_spells`. `git diff --check` reports no whitespace
errors. No pip, network access or commits were used.

## Step 3 fix round

This section supersedes the Step 3 completion counts and the accepted hostile
area friendly-fire boundary above. The original twenty golden spell files and
all pre-existing FORMAT text remain unchanged. No network, pip or commits.

### Review corrections and regression/mutation gates

Each numbered test below is in `tests/test_engine_step3_fixes.py`. Its exact
behavioral oracle runs normally, then runs against an in-memory regression;
`pytest.raises(AssertionError)` must catch that oracle failing. Method mutants
are compiled from inspected source in an isolated namespace, and monkeypatch
contexts restore all methods/data. No production or fixture file is mutated by
these checks.

| Finding | Root correction | Regression (`test_step3_` prefix omitted) / killed regression |
|---|---|---|
| 1 | Corrected seven scope decisions/reasons; added all six newly required level zero through five translations. Modify Memory grants fighting-target save Advantage, Charmed and charm-dependent Incapacitated, and ends on damage/another targeting spell. Magic Aura Mask changes magical type checks and wards without changing actual type. Rain can douse burning creatures. | `fix1_scope_additions_and_combat_mechanics`: old exclusion, missing translation and automatic fighting-target success. |
| 2 | Successful magical half-damage-save negation is separate from Evasion's failed-save reduction. | `fix2_circle_protects_only_successful_magical_saves`: exact magic fail/success damage eight/zero, mundane fail/success two/one; old conflation fails. |
| 3 | Aid's applied HP bonus is reconciled from active, strongest overlapping effects, not mutated per cast. Changes adjust both maximum and current HP, including duration expiry, and update zero-HP unconscious state. | `fix3_aid_overlap_duration_and_rescue`: duplicate/stronger/reappearing Aid, injured expiry and zero-HP rescue; three independent stacking/eligibility/expiry mutants fail. |
| 4 | Persistent riders declare a source-specific `requires_condition`; active-effect selection rechecks actual condition immunity/suppression rather than a cast-time predicate. | `fix4_control_depends_on_its_own_active_charm`: immune Suggestion/Crown/Pattern, Calm suppression/resumption, charm removal and unrelated charm; deleting the dependency fails. |
| 5 | Polymorph snapshots and replaces combat statistics with form/default statistics, including saves, extra attacks, vulnerabilities, features, resources and routines; reversion restores the snapshot. Wolf/Bear use the existing reviewed Step 2 traits/riders/Multiattack. | `fix5_polymorph_replaces_statistics_and_executes_beast_traits`: original-stat leakage, removed Pack Tactics, removed Multiattack and removed Wolf Prone rider each fail. |
| 6 | Ongoing spells track affected recipients explicitly, including ownership of self spells with no stored effects. Dispel uses these recipients, current area memberships and summoned bodies, not guessed self-effect records. | `fix6_dispel_tracks_ongoing_self_spell_ownership`: Aura of Vitality ends automatically at level three, unrelated targets do not end it; removing owner tracking or using effect records fails. |
| 7 | Numeric enumeration includes every numeric scalar and every string containing a digit: CR/fractions, numeric strings, embedded dice, expressions, source references, materials and annotation prose. CR is checked directly against local XMM. Source references/expressions/materials have independent semantic expectations; numeric omission notes have clause-local source/model evidence. | `fix7_all_numeric_leaves_and_fraction_source_values`: an independent test leaf walk checks every loaded spell and synthetic mixed strings; an independent production stack walk rejects coverage gaps. Dropping CR from the iterator or trusting the translated CR fails. |
| 8 | Mirror interception performs attack-activity cleanup before returning. | `fix8_mirror_interception_ends_invisibility`: a duplicate intercepts exactly once and the invisible attacker's spell ends; deleting cleanup fails. |
| 9 | Removed the vacuous casting check from the HP/reversion test. The new test begins with an eligible caster on its own turn and isolates the anatomy gate from replaced spell statistics by supplying all other casting prerequisites. | `fix9_polymorph_casting_gate_is_not_vacuous`: before/after casting is legal; transformed casting neither starts nor spends resources; disabling `Combat.turn_rules` fails. |
| 10 | Default freely placed hostile areas count only eligible enemies, capped by the size heuristic. They do not fill unused capacity with allies/the caster. A bound origin or a self-origin emanation still follows its declared geometry/target exclusions. | `fix10_default_hostile_area_never_fills_with_allies`: real Mage Fireballs versus one/two PCs, allied spill-over with custom count/indices, and emanation include/exclude; restoring the fill rule fails. |

The additional `test_step3_fix5_original_passive_traits_suspend_and_restore`
checks that original passive trait subscriptions stop in Beast form and resume
on reversion; removing that dispatch gate is also killed. Brown Bear's missing
Prone rider is mutated separately. The charm oracle also verifies that Calm
suppression restores the ability to attack the former charmer. Mask's actual
creature-type exclusion is checked even when a previous mask is active.

### Corrected inventory and boundaries

Across all 391 local XPHB spells: **190 combat, 118 partial, 83 out of scope**.
Modify Memory and Nystul's Magic Aura are combat; Create or Destroy Water,
Speak with Plants, Stone Shape, Arcane Lock and Planar Ally are partial.
Planar Ally is level six, so only its classification/reason changes here.

| Spell level | Required / loaded |
|---|---:|
| 0 | 29 / 29 |
| 1 | 54 / 54 |
| 2 | 49 / 49 |
| 3 | 45 / 45 |
| 4 | 34 / 34 |
| 5 | 34 / 34 |
| Total | **245 / 245** |

There are 225 non-golden translations. The independent audit now visits
**2,082 numeric leaves**, generates **2,359 mutants**, rejects **2,359**, and
reports zero survivors, zero missing spells and zero source failures. Numeric
prose is visited too; it is not silently exempted. Every fraction component and
every embedded numeric token receives its own increment mutation. Coverage is
checked independently of both `numeric_fields()` and `mutants()`.

New partial boundaries are explicit: fog-volume destruction does not dispel a
fog-producing spell; container quantities and object flames need environment
state. Speak with Plants' terrain changes need actual plants and a movement
map. Stone Shape and Arcane Lock need stone/door/access geometry; their loading
does not grant blanket incapacitation or invulnerability. Aura False Aura,
daily permanence, and Modify Memory's narrated/older memories need object,
calendar or social adjudication. These limits are not used to exclude the
spells from completeness.

**Default hostile-area placement:** with no grid, the caster chooses placement.
For a freely placed hostile area the count is `min(size heuristic, eligible
enemies)`; no spare count is filled with friendlies. A self-origin emanation
still obeys `include_caster` and the spell's own exclusions; a known bound origin
remains geometrically required. A caller-supplied `area(shape, size, eligible)`
can explicitly model spill-over by returning a count or indices into the full
eligible list. No callback API or statistical tolerance was loosened.

### Re-run CR rows

Same Fighter 5 / Fighter 5 / Cleric 5 / Cleric 5 party, **500 runs, seed one**.
`engine/step3_fix_cr.json` records every summary/resource field. The previous
post-wiring artifact is preserved in `engine/step3_cr_after.json` for comparison.

| Monster (printed CR) | Previous party wins -> fixed | Previous draws -> fixed | Mean rounds previous -> fixed | Mean party HP previous -> fixed |
|---|---:|---:|---:|---:|
| Mage (6) | 461/500 -> 456/500 | 24 -> 0 | 1.808 -> 1.858 | 88.472 -> 88.718 |
| Priest (2) | 500/500 -> 500/500 | 0 -> 0 | 1.000 -> 1.000 | 173.516 -> 173.516 |
| Stone Golem (10) | 308/500 -> 308/500 | 0 -> 0 | 6.344 -> 6.344 | 63.204 -> 63.204 |

The Mage's old self-Fireball draws disappear; preventing suicide is not an
assumption that the party's win rate must increase. Priest/Golem were measured,
not assumed unchanged. These remain build sanity checks, not CR reassignment.

### Final stable-tree verification

```text
C:/Users/xgxxg/anaconda3/python -m pytest tests -q
1916 passed in 475.38s (0:07:55)

C:/Users/xgxxg/anaconda3/python -m engine.step3_report
245/245 required/catalog spells loaded; 0 missing; 2359 numeric mutants; 0 failures

C:/Users/xgxxg/anaconda3/python -m engine.monster_import --check
70 XMM sheets checked: no source drift
```

Full-suite output is captured in `engine/step3_fix_pytest.log`. It includes all
eleven numbered fix-round regression tests and their in-memory mutation kills.
The three CR rows were repeated on the final code and every summary/resource
field was asserted equal to `engine/step3_fix_cr.json`. All twenty original
golden SHA-256 hashes match; none has a Git diff. The checkout-filtered HEAD
FORMAT prefix is preserved, with only appended sections. `git diff --check`
passes. Existing statistical tolerances are unchanged. Earlier development
runs, including a run that overlapped edits, are not claimed as passing gates.

## Step 3 fix round 2

All A-F findings are fixed through shared state/resolution mechanisms.
`tests/test_engine_step3_fix2.py` contains six `test_step3_fix2_A_...` through
`test_step3_fix2_F_...` regressions with exact assertions and **19 rejected
in-memory regression variants** (A: 3, B: 1, C: 2, D: 2, E: 2, F: 9).
Mutation checks compile or monkeypatch methods/data in memory, never on disk.

### Mechanisms and exact regression coverage

- **A:** one original-stat snapshot plus an ordered stack of transformations.
  Reconciliation handles starts, suppression, resumption and either ending order.
  Eligibility uses original CR/level; each form retains its remaining temporary
  HP. Tests cover Wolf temporary HP 11 -> 8, Horse speed 60/temporary HP 13,
  original speed 30/three attacks, trait restoration, overflow damage, and spell
  and concentration ending on depletion. Ending a suppressed form changes none
  of the effective form's statistics.
- **B:** effective control/charm effects derive `team` over retained base
  allegiance; no one-way team mutation. Both Dominate spells cover suppression,
  resumption, actual attack destinations, removal and foreign-source isolation.
  Calm Emotions is exercised as a real spell.
- **C:** `max_hp` is `base_max_hp + spell_hp_bonus`. Public maximum reductions
  update the base; Greater Restoration restores only the base. Recomputed active
  bonuses adjust current HP once. Exact Aid/drain/restoration/expiry maxima are
  **105 -> 95 -> 105 -> 100**. Tests also cover restoration after Aid ends and
  stronger-bonus suppression/resumption without changing the base.
- **D:** generic primitive `participants` metadata supplements recipient
  registration. Warding Bond explicitly registers both endpoints. Dispel on
  either ends it; an unrelated creature does not. Tests assert 5/5 shared damage
  before ending, 0/10 afterward, and complete source/participant cleanup.
- **E:** skipping a conditional save executes its explicit `apply`, or otherwise
  its application (`on_fail`) effects without rolling. Both Enlarge/Reduce modes
  cover willing caster, willing other recipient, unwilling failure/success,
  exact sizes, Strength roll flags, weapon damage **6/4/5**, and restoration.
  Dispel Evil and Good's distinct no-save application branch is also executed.
- **F:** persistent `requires_condition` checks an effective condition from the
  **same spell instance**, not merely the same caster. The shared query gates
  persistent effect visibility, recurring instantaneous applications and complete
  block save/resolution paths. Surviving riders resume, including ones registered
  while dormant. Temporary action prohibitions mask unspent budgets instead of
  spending them; cure/suppression restores unspent actions, never spent actions.
  Tests exercise real Feign Death suppression, removal/resumption, foreign-source
  poison/restraint/grapples, recurring damage, and action-budget restoration.

### E audit: all 245 spells

Exactly two blocks use `save.if`:

| Spell/block | Skipped-save behavior |
|---|---|
| Enlarge/Reduce / main | Empty `apply`: execute application effects from `on_fail`, without a save. |
| Dispel Evil and Good / function | Preserve explicit Break Enchantment `apply`; do not substitute dismissal effects. |

Also inventoried the other conditional save modifiers: two `auto_fail_if`
(Blight, Otiluke's Resilient Sphere), two `auto_success_if` (Crown of Madness,
Sleep), six `advantage_if`, and one `disadvantage_if` (Shatter). They already
route through failure/success branches rather than the skipped-save application
path. No other E-pattern defect was found. The regression independently asserts
the two-block skipped-save inventory and executes both behaviors.

### F audit: all 245 spells, including embedded forms

Reviewed local XPHB condition passages (70 of these spells contain condition
markup), spell declarations and nested summon/transform forms. The complete
persistent rider inventory is now **10 declarations across nine spells**:

| Spell | Dependent rider / condition | Outcome |
|---|---|---|
| Contagion | Chosen-ability save disadvantage / Poisoned | Converted application-only predicate. |
| Stinking Cloud | Action/Bonus Action prohibition / Poisoned | Converted application-only predicate. |
| Ensnaring Strike | Recurring vine damage / Restrained | Added missing recurring dependency. |
| Bigby's Hand | Crush resolution / Grappled | Added block dependency; selection checks exact instance too. |
| Conjure Elemental | Hold save/damage / Restrained | Converted caster predicate to block dependency; catch checks exact instance. |
| Suggestion | Pacification / Charmed | Retained and audited existing dependency. |
| Crown of Madness | Forced melee / Charmed | Retained and audited existing dependency. |
| Hypnotic Pattern | Incapacitated and speed 0 / Charmed | Retained and audited both dependencies. |
| Modify Memory | Incapacitated / Charmed | Retained and audited existing dependency. |

Dominate Beast/Person control is intrinsic to its Charmed effect and continuously
derived by B, not a separately latched rider. Native condition rules remain live
condition queries. Fear/Compulsion's unimplemented spatial commands remain their
existing explicit boundaries, not fabricated riders.

A recursive declaration audit asserts this full inventory and all remaining
`has_condition...` predicates. Bigby's selection and Elemental's catch reference
`spell`, not `caster`. The only other predicate is Summon Undead's Putrid Spirit
paralysis **application** prerequisite: it must not become an ongoing requirement
that paralysis end when poison ends. Independent duration/area effects such as
Feign Death's defenses, Haste lethargy's speed and Silence/Jallarzi restrictions
are not riders of their adjacent conditions. No other persistent condition-rider
defects were found.

All six edited YAML effect lists match their authoring recipes. The isolated
Ensnaring Strike damage-mean fixture now supplies its own source's Restrained
condition, as the existing Bigby/Elemental fixtures already do. No expected
damage or statistical tolerance was loosened. The old Polymorph mutation check
follows the moved stat-copy loop while retaining its exact behavioral assertions.

### Verification gates

Each fix received a complete passing suite before the next fix's code changed.
Outputs: `engine/step3_fix2_{A..F}_pytest.log`. Temporary directories were placed
inside the workspace using `--basetemp=.pytest_tmp_fix2_X`.

| Gate | Full suite |
|---|---|
| A | 1917 passed in 502.49s |
| B | 1918 passed in 531.11s |
| C | 1919 passed in 526.60s |
| D | 1920 passed in 603.66s |
| E | 1921 passed in 530.52s |
| F | 1922 passed in 577.03s |

```text
C:/Users/xgxxg/anaconda3/python -m pytest tests -q --basetemp=.pytest_tmp_fix2_F
1922 passed in 577.03s (0:09:37)

C:/Users/xgxxg/anaconda3/python -m engine.step3_report
245/245 required/catalog spells loaded; 0 missing; 2359 numeric mutants; 0 failures

C:/Users/xgxxg/anaconda3/python -m engine.monster_import --check
70 XMM sheets checked: no source drift
```

The final targeted regression/completion set also passed: 203 tests. The full
suite verifies all twenty golden SHA-256 hashes. No golden spell was edited.
FORMAT's pre-round byte prefix was asserted intact when appending contract notes.
Existing workspace changes were preserved; no pip, network, commits or tolerance
changes were used. CR simulations were not rerun: preceding CR artifacts/results
are preserved and are not represented as new measurements.

## Step 4: classes

### Delivery and staged gates

New `CLASS_FORMAT.md`, four XPHB progression files (levels 1?10), strict
`engine.classes`/`engine.builder` APIs, and twenty build recipes. Both combat
and day CLIs accept build stems without replacing the fixed sheets. Development
proceeded format ? Fighter ? Rogue ? Wizard ? Cleric ? builder ? AI ? results.
Targeted passing gates before subsequent stages: 49, 54, 63, 70, 75, then 111
and 115 cases respectively. The final full-tree gate is recorded below; early
runs during iteration are not represented as stable-tree verification.

The only new effect primitive is `heal_pool` for Preserve Life. Other changes
are enumerated sheet hooks at existing roll/hit/save boundaries, weapon
properties/masteries, skill/Expertise and spellbook/prepared metadata, and
validated short-rest callbacks. `target.bloodied` exposes the existing rules'
half-HP predicate without inventing a new condition. Full syntax, first users,
execution timing, source limitations and no-grid approximations are in
`data/handwritten/CLASS_FORMAT.md` and appended CHARACTER_FORMAT notes.

### Feature coverage

"Executable" includes builder-time grants/counts and wrapper features that
select their named children; wrappers never apply effects twice. A partial row
states exactly which part is not simulated. All source feature records through
level ten are inventoried, including selectable children and repeated ASIs.

| Fighter / Champion feature | Coverage |
|---|---|
| Fighting Style; Additional Fighting Style | Executable: Defense, Archery, Dueling, 2024 Great Weapon Fighting; distinct second style at seventh. Other style feats are rejected, not guessed. |
| Second Wind | Executable: d10 + Fighter level, bonus action, table uses; one back on short rest, all on long. |
| Weapon Mastery | Executable selections/counts, Graze/Vex/Sap; supported equipment also uses Slow/Topple. Push/Slow displacement remains spatial bookkeeping. |
| Action Surge | Executable non-Magic extra action, short-rest counter. |
| Tactical Mind | Executable failed-check d10, spend Second Wind only if it changes failure to success; includes combat escape checks. |
| Fighter Subclass; Champion; Subclass Feature gates | Executable builder dispatch at source levels. |
| Ability Score Improvement (fourth, sixth, eighth) | Executable ability math/caps, including retroactive Constitution HP. No other ASI feat choices. |
| Improved Critical | Executable weapon critical/automatic hit on 19?20; no spell critical expansion. |
| Remarkable Athlete | Executable initiative/Athletics advantage; unsupported post-critical movement without grid. |
| Extra Attack | Executable two-attack Attack action. |
| Tactical Shift | Unsupported: movement/opportunity attacks require grid. |
| Indomitable | Executable failed-save reroll plus Fighter level, one per long rest in scope. |
| Tactical Master | Executable per-attack mastery replacement with Sap/Slow/Push. Sap changes attacks, Slow stores speed; displacement remains unsupported. |
| Heroic Warrior | Executable own-turn Inspiration grant and failed-D20 reroll policy. Policy does not choose damage-die rerolls. |

**Studied Attacks is level 13 in XPHB**, so deliberately absent, not silently
backported into level ten. The same applies to later Extra Attacks/Indomitable
uses and Champion Superior Critical/Survivor.

| Rogue / Assassin feature | Coverage |
|---|---|
| Expertise (first, sixth) | Executable named skill/tool proficiency checks; two then four proficient skills chosen. |
| Sneak Attack | Executable dice progression, once per global turn, Finesse/ranged eligibility, advantage/adjacent-ally approximation, critical batching. |
| Thieves' Cant | Unsupported: languages/social/exploration only. |
| Weapon Mastery | Executable two selections; no mastery assumed for unselected weapons. |
| Cunning Action | Executable bonus-action Disengage marker. Dash/Hide require movement/concealment adjudication; no free hidden advantage. |
| Rogue Subclass; Assassin; Subclass Feature gate | Executable builder dispatch. |
| Steady Aim | Executable bonus action, next-attack advantage, current-turn speed zero and unmoved prerequisite. |
| Ability Score Improvement (fourth, eighth, tenth) | Executable ASI-only choice. |
| Cunning Strike; Poison; Trip; Withdraw | Executable one-die cost/one option, poison kit/Con save/repeat/end timing, Dex Trip size restriction. Withdraw's movement/protection is unsupported; permission/expenditure is recorded. |
| Uncanny Dodge | Executable visible-hit reaction, complete attack packet halving. |
| Evasion | Executable Dex half-damage success/failure transformation; disabled while incapacitated. |
| Reliable Talent | Executable proficient check D20 floor. |
| Assassin's Tools | Executable kit proficiency/possession prerequisite. Inventory purchasing/disguise narration is not simulated. |
| Assassinate | Executable initiative advantage, first-round advantage against not-yet-acted targets, flat Rogue-level first-round Sneak Attack bonus. No 2014 surprise auto-critical. |
| Infiltration Expertise | Executable Roving Aim; unsupported social mimicry. |

| Wizard / Evoker feature | Coverage |
|---|---|
| Spellcasting | Executable fixed prepared/cantrip/slot tables, validated spellbook and selections, Int attack/DC. Existing specs only. |
| Arcane Recovery | Executable short-rest slot selection, combined-level cap, once per long rest, structured rest log. |
| Ritual Adept | Unsupported: ritual/exploration casting outside combat/scripted-rest model. |
| Scholar | Executable Expertise in a selected proficient Wizard skill. |
| Wizard Subclass; Evoker; Subclass Feature gates | Executable builder dispatch. |
| Ability Score Improvement (fourth, eighth) | Executable ASI-only choice. |
| Memorize Spell | Executable one prepared/book exchange on short rest; default policy prepares Fireball if available in book but not prepared. |
| Evocation Savant | Executable free-book additions, school/learning-level constraints checked by matching. Purchased copying is out of scope. |
| Potent Cantrip (third) | Executable half damage on successful saves/misses, without riders. |
| Sculpt Spells (sixth) | Executable visible-other-creature quota, automatic save/no half damage, friendly-fire-aware scoring. Caster never exempted by this feature. |
| Empowered Evocation (tenth) | Executable Int on one damage roll; respects shared rolls. Existing independent per-target AoE rolls remain an engine approximation, explicitly documented. |

| Cleric / Life feature | Coverage |
|---|---|
| Spellcasting; Divine Order; Protector; Thaumaturge | Executable source counts, Wis attack/DC, equipment training or extra cantrip/Int skill bonus. |
| Channel Divinity | Executable shared counter/recovery; two uses at second, three at sixth. |
| Divine Spark | Executable healing or Radiant/Necrotic damage, Con half save, excludes self, source range and die progression. |
| Turn Undead | Executable chosen Undead Wis save, Frightened/Incapacitated, minute duration, damage/source-capability cleanup. Fleeing movement unsupported. |
| Cleric Subclass; Life Domain; Subclass Feature gate | Executable builder dispatch. |
| Ability Score Improvement (fourth, eighth) | Executable ASI-only choice. |
| Sear Undead | Executable shared Wis-modifier d8 roll, minimum one, does not end this turning. |
| Blessed Strikes; Divine Strike; Potent Spellcasting | Executable mutually exclusive choice: own-turn once-only Radiant weapon d8, or Wis on Cleric cantrip damage. |
| Divine Intervention | Executable daily slotless supported Cleric spell, levels one?five, nonreaction, action override. AI uses it with depleted slots. No material inventory needed. |
| Disciple of Life | Executable slot-level healing bonus only on cast turn, not slotless abilities. |
| Life Domain Spells | Executable always-prepared source list, outside ordinary prepared count. Missing specs would be explicitly unsupported rather than synthesized. |
| Preserve Life | Executable finite level-based pool, bloodied targets only, zero-HP revival, half-maximum cap. |
| Blessed Healer | Executable caster healing once after an expended-slot spell heals another creature. |

### Builder, compatibility and source verification

All twenty presets use a standard array **without** species/background boosts.
ASI allocations are explicit. Point buy and explicit externally assigned scores
are also validated. Equipment AC is computed, never copied from a fixed sheet.
Mage Armor is available as a real spell, not a free AC adjustment. The supplied
raw spell JSON omits class-list membership, so the builder's supported membership
whitelists are explicit reviewed rules, not falsely attributed JSON fields.

| Matching fixed build | HP | AC | Weapon attack / damage | Spell attack / DC | Slots | Limited uses |
|---|---:|---:|---|---|---|---|
| Fighter 5 / Champion | 49 | 17 | +7 / 2d6+4 | Not applicable | None | Second Wind 3; Action Surge 1 |
| Cleric 5 / Life | 38 | 18 | +5 / 1d6+2 | +7 / 15 | 4/3/2 | Channel Divinity 2 |

Every requested numeric field matches `fighter5.yaml` / `cleric5.yaml`; neither
fixed sheet was edited. Compatibility tests supply the fixed scores minus their
fourth-level ASI as `assigned` input. These scores cannot legally be represented
as unboosted point buy/standard array: background bonuses are not silently
fabricated. Champion legitimately adds critical range, initiative/Athletics
advantage. Generated Fighter also enables Tactical Mind and skill proficiency.
Generated Life adds Disciple, Preserve Life, domain preparation, executable
Channel Divinity and Sear Undead. Its four known cantrips, nine ordinary prepared
spells and six additional domain spells replace the fixed sheet's deliberately
short nine-spell list; slots/attack/DC do not change. Fixed-sheet unsupported
notes remain historical and compatible, not automatically upgraded.

The source oracle imports **no authoring recipes** and reads only local XPHB
class/classFeature/subclass/subclassFeature records. Structured progression
cells and path-specific prose extraction validate every numeric class-file leaf,
including keys and numbers embedded in strings. Each embedded digit sequence is
mutated separately. Colliding key mutations are rejected, not skipped. Tests also
alter the independent source table/critical text in memory to prove the oracle
responds to source changes rather than accepting a stored generated snapshot.

| Class | Numeric fields | Numeric mutants | Survivors |
|---|---:|---:|---:|
| Fighter | 120 | 121 | 0 |
| Rogue | 106 | 122 | 0 |
| Wizard | 159 | 159 | 0 |
| Cleric | 172 | 173 | 0 |
| Total | 557 | 575 | 0 |

The explicit allow-list is universal PB (not included in raw class table JSON),
zero for absent grants/recovery, and lexical one/once/next. Equipment, style, ASI,
ability-generation and universal attack/DC/HP constants are reviewed builder
rules outside class-file numeric leaves and independently tested as math, not
misrepresented as numbers present in class prose. `step4_validation.json`
contains the machine-readable audit. No spell/monster/FORMAT files were edited.

### AI and investigations

New feature decisions route through the acting creature's policy. Shared EV
includes Sneak Attack eligibility/targeting, Potent Cantrip miss damage, Potent
Spellcasting/Empowered Evocation, real friendly area coverage and Sculpt Spells,
Preserve Life's finite capped healing, Turn Undead control plus Sear damage, and
Tactical Master's Sap tradeoff. The scorer initializes designated exclusions just
like a real cast; forgetting those exclusions initially undervalued Spirit
Guardians and was fixed rather than changing a historical numeric baseline.
Conservative Channel Divinity is gated by actual danger/emergency; nonspell
Uncanny Dodge is not incorrectly treated as a budgeted leveled spell.

Seeded/exact structured-log cases assert Action Surge, Second Wind, Tactical
Mind, Indomitable, Heroic Warrior/Inspiration, Sneak Attack, Cunning Action,
Steady Aim, Cunning Strike, Uncanny Dodge, Tactical Master, Sculpt Spells,
Divine Spark, Preserve Life, Turn/Sear Undead and short-rest Arcane Recovery /
Memorize Spell execution. Further exact tests cover critical packet math,
mastery duration/consumption, skill floors, Life slot-vs-slotless healing,
Blessed Strikes and Divine Intervention. Every preset has independent HP/AC,
attack/DC, slot/count/PB assertions; all forty class/level combinations build.
Existing test expectations/tolerances were not loosened.

A pilot exposed a pre-existing **zero-HP regenerator targeting trap**: after the
Rogue dropped a Troll to zero, other PCs saw no enemies and skipped their turns;
the Troll regenerated before it could be finished by fire. Zero-HP regenerators
that can return now remain legal attack/spell targets until blocked/permanently
removed. An exact fire-finishing regression covers the fix. No monster sheet was
changed. This was not solved by removing the Troll from the measured day.

### Standard days and reproduction

The new `classes_level_{3,5,10}.yaml` days each contain six encounters, two short
rests (after the second/fourth fights), no long rest and no invented prebuffs.
Their printed CR rosters are deliberately heterogeneous rather than six cloned
monsters. They include an Undead encounter, mixed targets and a tougher finale.
Unadjusted encounter XP totals (2024 no monster-count multiplier):

| Level | Encounter XP, in order | Day XP |
|---|---|---:|
| 3 | 300, 900, 800, 600, 900, 900 | 4,400 |
| 5 | 1,200, 1,800, 1,800, 2,300, 2,250, 2,300 | 11,650 |
| 10 | 5,400, 5,700, 6,400, 6,800, 7,700, 7,300 | 39,300 |

These are encounter-scale CR/XP sanity workloads, not a claim that six fights
at those budgets must be survivable without an optimized build or prebuffing.
One single-class PC each: Fighter, Rogue, Wizard, Cleric. Opponent strategy is
independently `default`; party strategy is nova/conservative. Seed one, 1,000
trials per row. Conditional encounter statistics and resource snapshots are in
`engine/step4_results.json`.

```powershell
C:/Users/xgxxg/anaconda3/python -m engine.step4_report --source-only
C:/Users/xgxxg/anaconda3/python -m engine.step4_report --results-only --runs 1000 --seed 1
C:/Users/xgxxg/anaconda3/python -m engine.day --party fighter_5 rogue_5 wizard_5 cleric_5 --day classes_level_5 --runs 1000 --seed 1 --strategy conservative
C:/Users/xgxxg/anaconda3/python -m pytest tests -q
```

Additional integration gates preserve empty weapon probes (used by existing
spell-rider/summon tests), nameless action scoring probes, and healing selection
after Life Drain reduces a maximum to zero. The zero-maximum ratio crash found
in the level-ten pilot was fixed rather than excluding those targets/monsters.
Channel Divinity explicitly marks a nonspell Magic action, so existing Magic
Resistance/defenses/type masks apply without making it Counterspell-able; Action
Surge cannot supply that action. A focused 329-case integration/source gate
passed after this change. Potent Cantrip also covers missed True Strike weapon
attacks, and Scholar cannot grant Insight Expertise.

### Final verification

```text
C:/Users/xgxxg/anaconda3/python -m pytest tests -q
2009 passed in 728.15s (0:12:08)
```

This includes the unchanged legacy 1,000-run numeric strategy/encounter baselines,
all original spell/source/mutation tests, and 87 new class cases. The previous
spell-specific magic-protection branch remains identifiable by the existing
in-memory mutation oracle; marked magical class actions extend it separately.
No existing test was edited, skipped or loosened. No network, pip or commits
were used. No log or scratch output is retained in `engine/`.

### Measured class-party results (1,000 runs per row, seed one)

| Level | Strategy | Days survived | Survival | Mean encounters cleared / six | Reached final encounter |
|---|---|---:|---:|---:|---:|
| 3 | nova | 0/1000 | 0.0% | 2.274 | 0 |
| 3 | conservative | 0/1000 | 0.0% | 2.397 | 2 |
| 5 | nova | 1/1000 | 0.1% | 2.676 | 59 |
| 5 | conservative | 47/1000 | 4.7% | 3.558 | 228 |
| 10 | nova | 0/1000 | 0.0% | 3.468 | 53 |
| 10 | conservative | 6/1000 | 0.6% | 3.601 | 158 |

The very low survival rates are **not** presented as believable tabletop
balance calibration. Zero is an observed count, not proof of zero win probability.
Investigation found two actual defects (regenerators untargetable at zero and
healing-sort division by zero after maximum-HP drain); both were fixed and the
measurements rerun. The remaining outcomes follow the documented workload/model:

- The presets have no background/species boosts. Their initial total HP is
  93 / 147 / 282 at these levels; Wizard HP is 17 / 27 / 52, with unarmored AC 12.
  Fighter/Cleric fixed-sheet stats are deliberately stronger than the unboosted
  presets, not numerical builder regressions.
- Every melee enemy is assumed able to reach the weakest PC. The policy focuses
  low HP; there is no back line, body blocking, retreat, cover or movement-based
  protection from Cunning Action. Heavy Fighter armor does not screen a Wizard.
  Seeded pilot traces showed the Wizard/Cleric falling while the Fighter still
  had HP/resources, followed by repeated knockouts and loss of healing.
- Mage Armor is prepared and its real AC/slot execution is tested, but the
  inherited damage/control scorer does not proactively value this AC-only buff.
  No free/precombat Mage Armor was injected into the reported days. Encounter
  cleanup deliberately removes all buffs, even long-duration spells, as in the
  accepted day contract; table prebuff/carry-over tactics are not modeled.
- Nova burns high slots on reactions/offense and Channel Divinity early.
  Conservative improves the fifth-level result, but its previously accepted
  under-spending/danger-trigger limits remain. Neither policy is optimal.
- The Undead group has many actions and permanent maximum-HP reduction. Recovery
  does not automatically cast Greater Restoration, and a zero-HP PC cannot rest.
  Two short rests therefore cannot erase a lost healer or accumulated drain.

No encounter was removed or reduced to manufacture a better rate. These are
six-encounter stress workloads for this exact no-grid, unboosted party, not
encounter/CR recommendations. The complete per-encounter conditional denominators,
HP percentages, slot/resource means, downs and rounds remain in the JSON artifact.
The report runner uses three independent process workers with one seed-owned RNG
per row and ordered aggregation; worker scheduling does not choose trial seeds.

## Step 4 fix round

This section supersedes the knockout-only, unboosted day-model assumptions in
the original Step 4 results above. No encounter, monster, golden/translated spell
file, or FORMAT.md was changed for this fix round. Existing unrelated working-tree
edits were retained. No network, pip, or commits were used.

### Review fixes and independent gates

1. **Preserve Life:** `use_action(..., allocations={target_id: hp, ...})` accepts
   explicit allocations, or calls `Policy.healing_pool`. Selection, integer
   amounts, per-target half-HP caps, and total pool are validated **before**
   expenditure. Omitted targets receive zero; an empty allocation is legal.
   Default policy buys one HP for each downed target first, then spreads the
   remaining pool by HP fraction, without exceeding half maximum HP. Cleric 3
   with three 0/40 allies gives exactly **5/5/5**, not 15/0/0. With no slots and
   one Channel Divinity, recovery recognizes `heal_pool` and revives two 0/40
   allies to **8/7**, rather than selecting one-target Divine Spark.
2. **Rerolls:** integer-compatible D20 results retain their underlying dice.
   Heroic Inspiration and Indomitable replace one policy-selected die only.
   The default replaces the lower die; the unchosen die remains. The reviewed
   disadvantage probes now fail with totals **3** and **12**, respectively.
   Attack rolls, checks (including Reliable Talent), saves, and new death saves
   share this mechanism. An engine-wide reroll audit found these two implemented
   D20 reroll features; Great Weapon Fighting's 2024 minimum-three damage dice
   are not rerolls. Advantage/disadvantage tests drive actual `randint` draws,
   rather than mocking an already-collapsed D20.
3. **Spell membership:** the static lists contain all **242 Wizard / 117 Cleric**
   entries in the archive's XPHB class-membership data, not school-based guesses.
   Tests read `5etools-v2.30.1.zip:data/spells/sources.json` independently, compare
   complete sets, and build every supported member legal at the engine's levels
   1–10 (spell levels 0–5), including spellbook acquisition/Savant constraints.
4. **Builder wiring:** class behavior fixtures now cross `build()`; their
   assigned scenario stats do not reconstruct grants from class YAML. Each of
   the seven reviewed flag deletions is compiled in memory and kills its actual
   behavior test, in addition to explicit `build`/`load_build` grant assertions.
   Assassinate initiative's separate grant is tested as well. No class data is
   mutated on disk. Existing numeric/source audit gates remain intact.
5. **HP:** each later level gains `max(1, average_hit_die + Con modifier)`.
   Assigned Constitution 3 Wizard 10, without a Constitution background increase,
   has exactly **11 HP**. An in-memory removal of the minimum fails that test.

`tests/test_step4_fixes.py` supplies `test_step4_fix1_...` through
`test_step4_fix5_...` exact regressions and mutation witnesses. The original
class behavior suite also includes the seven builder-deletion behavior mutants.
The first focused fix gate passed 87 existing class cases and 31 review cases;
the expanded day/class/previous-mutation integration gate passed 428 cases.
After additional death-save, Aid, and zero-maximum-HP edge cases, the focused
class/review/day suite passed **158 tests**. Full-suite verification is below.

### Default day model and compatibility

All six `DayOptions` switches default to true. A day YAML can contain an `options`
mapping; Python callers can pass `options=DayOptions(...)` to `run_day` or
`simulate_day`. The CLI exposes the same switches:

```powershell
& C:/Users/xgxxg/anaconda3/python -m engine.day --party fighter_5:front rogue_5:back wizard_5:back cleric_5:front --day classes_level_5 --strategy conservative --runs 1000 --seed 1 --json
# Exact pre-realism day model (all six switches off, low-HP targeting):
& C:/Users/xgxxg/anaconda3/python -m engine.day --party fighter5 cleric5 --day goblin_warren --strategy conservative --runs 1000 --seed 1 --legacy --json
# Individual sensitivities:
# --no-clock / --no-prebuffs / --no-death / --no-backgrounds
# --no-engagement / --no-spending
```

- **Clock:** six seconds per realized combat round, `--gap-minutes 10` between
  encounters, one-hour short rests, eight-hour long rests. Buff casts and rescue
  actions cost six seconds each. Effects and concentration are retained and
  expire against elapsed time, not an encounter-end wipe. Turn-bound effects
  cross their next actual safe-time boundary; repeating effects/saves advance
  during safe time too. Disabling the clock restores the old effect/temp-HP
  wipe, without accidentally deleting the independent death/stability state.
  **False Life was already instantaneous in the supplied XPHB spec**; no spell
  file needed editing. Its temporary HP now persists until depleted or a long
  rest instead of disappearing after each encounter.
- **Prebuffs:** `Policy.precombat_buffs(combat, party, phase)` runs at day start,
  after rests, and before encounters. The existing EV scorer has a precombat
  prevention mode: known future encounter start offsets within spell duration,
  a three-round planning prior per encounter, incoming at-will damage, AC hit
  probability reduction, maximum HP, and nonstacking/repeating temporary HP.
  The actual clock never uses that planning prior. Concentration reserves 30%
  of forecast value; conservative requires 25% more benefit than nova. A slot
  has opportunity cost `4 + 4 × slot level`; casting uses the cheapest available
  legal slot and real action/slot expenditure. Active same-name benefits are
  not recast. Mage Armor, Aid, False Life, and Heroism-like protection have
  executable prevention scoring; this is an EV heuristic, not optimal planning.
- **Death:** PCs roll death saves at zero: 10+ succeeds, natural 1 adds two
  failures, natural 20 restores one HP, three failures kill, three successes
  stabilize. Damage at zero adds one failure (two on a critical); remaining
  massive damage at least maximum HP kills immediately. Normal healing, Aid
  recovery, and waking reset counters. Life Drain reaching zero maximum HP also
  records a death. Dead is distinct from downed: ordinary healing/rests cannot
  undo it. Revivify consumes its real slot and only returns a dead PC with a
  positive HP maximum within one minute. As elsewhere in the engine, required
  material inventory is assumed available; diamonds/body dismemberment are not
  a new inventory subsystem. Death events remain counted after resurrection.
  After a won fight, surviving allies heal, use Spare the Dying, or attempt
  DC 10 Wisdom (Medicine); failed rescue attempts allow further death saves.
  Stable PCs wake at one HP after an actual 1d4 hours. A designated safe rest
  step waits for stable companions to wake **before** starting the full rest;
  ordinary encounter gaps do not get a free four-hour recovery. Failed
  encounters are never reversed into wins by postcombat recovery.
- **Backgrounds:** `build()` and the presets default to **+2 primary / +1 Con**
  before ASIs. `choices.background` can instead specify another +2/+1 or
  +1/+1/+1 allocation. Scores cap at 20; background-caused ASI overflow moves
  to primary, then Constitution, then another uncapped ability. Pre-background
  ability-generation validation and independently illegal ASIs still reject.
  Use `background=False` for unboosted builder math. The fixed Step 1 sheets
  keep their supplied completed scores; they are not boosted a second time.
- **Engagement:** party entries can be `build_name:front` / `build_name:back`,
  or Python mappings `{"build": ..., "position": ...}`. Build defaults put
  medium/heavy-armored melee PCs in front. Existing fixed armored sheets use
  their AC/melee proxy. Each conscious, non-incapacitated front-liner screens
  `--screen 2` ordinary melee enemies. Overflow, reach beyond five feet,
  flying, and teleport capability bypass screening; ranged attacks and spells
  have unrestricted reach. Explicit `engagement_tags` support reach/flying/
  teleport fixtures without editing monster data. Screened melee chooses among
  reachable front-liners, not a magically invulnerable tank. `--targeting threat`
  prefers actual damage dealt this encounter, then at-will DPR; alternatives
  are `focus_low_hp` and `random`. EV probes do not consume random-targeting
  draws. `--attack-downed` permits deliberate finishing attacks; the default
  avoids downed targets unless no conscious reachable target remains.
  `--no-engagement` restores universal access and the old low-HP default.
- **Morale (optional, off by default):** `--morale dmg` (or `options: {morale: dmg}`
  in a day file) applies the DMG optional morale rule. A monster checks the first
  time it is at half its hit points or fewer, and every monster on a side checks
  the first time that side is down to half its starting number. Each check is a
  DC 10 Wisdom save, and a failure means the monster flees and leaves the
  combat. `--morale rout` flees on every trigger with no save (an upper bound).
  Creatures immune to the frightened condition never check; an incapacitated
  creature checks once it can act. Checks run at the end of each turn. A fight
  in which every remaining monster fled is a party win. Surprise and
  leader-loss triggers are not modelled.
- **Spending:** conservative compares forecast current-encounter party damage
  loss to HP divided by encounters remaining **before the next long rest**.
  An ally down or below 50% is an emergency; the final encounter before a long
  rest is not budget-gated. Surplus slots relative to remaining casting turns
  also justify spending/upcasting. The regression recreates the reviewed
  approximately 16.7-slot failure as an exact **17-slot** state with the Cleric
  at 40% HP and its old encounter budget already spent: healing is permitted,
  a real slot is spent, and the Cleric rises above half HP. The old 25%-HP and
  per-encounter cap remain available with `--no-spending`. This does not burn
  useless spells just to manufacture a zero-slots statistic: limited legal
  turns, death before a turn, and spells with no useful effect can leave slots.
  A pilot caught an avoidable new policy choice: emergency-driven upcasting of
  non-scaling Shield. Conservative now uses the cheapest slot for non-scaling
  spells, and only considers higher beneficial upcasts when slots exceed
  forecast casting turns. A deterministic regression locks both Shield's
  level-one choice and useful surplus-slot Magic Missile upcasting. Pilot rows
  were discarded and measurements restarted after this correction.

The existing day tests explicitly opt into `DayOptions.legacy()` rather than
changing their exact seeded expected outcomes or tolerances. Existing fixed-sheet
builder math opts out of backgrounds; separate new tests assert boosted defaults.
No replacement numeric legacy baseline was introduced. New rules have independent
exact tests in `tests/test_day_realism.py`.
Legacy switches restore the old **day assumptions**, not the reviewed Part A
defects: Preserve Life allocation and one-die rerolls remain corrected in every
mode. Consequently an old class-party measurement depending on those defects
is not promised bit-for-bit reproduction; the accepted fixed-sheet seeded
legacy regression assertions are retained unchanged.

### Measurements and verification

**Metric definitions:** "clearance" means winning every scheduled encounter,
even with casualties; it is the closest comparison to the old party-day-clear
metric. "Whole-party survival" additionally requires no PC dead or permanently
removed at day end. A successfully Revivified PC qualifies as alive, but its
death event is still reported. Deaths count events, not knockouts; downs count
transitions from positive HP to zero. Encounter means are conditional on reaching
that encounter (unreached is `—`, not zero). Slots left is an unconditional
end-of-run mean, including resources stranded when a failed day stops. Complete
reached counts, distributions, per-level slots, and resource means are in JSON.
The 300-run reference uses the same seed-one prefix as the 1,000-run main row;
one-switch-off effects are interactions, not additive contributions.

<!-- STEP4_FIX_RESULTS -->

All rows use seed **1**, default monster policy, and the original, unchanged encounter definitions. Main rows use **1,000 trials**; reference/one-switch-off rows use **300 trials**.

Completed checkpoint: **54/54 rows**. All **24,600 requested/control trials** are complete.

#### Main class-party days (new defaults)

| Party/day | Policy | Encounters all cleared | Whole-party survival | Death events/day | Downs per encounter (1 → n, conditional) | Slots left at day end |
|---|---|---:|---:|---:|---|---:|
| Class party L3 | nova | 30/1000 (3.0%) | 21/1000 (2.1%) | 3.889 | 0.01, 0.22, 0.94, 3.48, 3.35, 2.14 | 0.007 |
| Class party L3 | conservative | 170/1000 (17.0%) | 130/1000 (13.0%) | 3.369 | 0.02, 0.47, 1.06, 2.50, 2.81, 2.06 | 0.044 |
| Class party L5 | nova | 35/1000 (3.5%) | 29/1000 (2.9%) | 3.867 | 0.06, 0.29, 0.15, 3.22, 1.54, 3.25 | 0.089 |
| Class party L5 | conservative | 233/1000 (23.3%) | 192/1000 (19.2%) | 3.123 | 0.12, 0.20, 0.24, 3.13, 1.17, 3.72 | 2.337 |
| Class party L10 | nova | 85/1000 (8.5%) | 51/1000 (5.1%) | 3.726 | 0.02, 0.22, 0.05, 0.84, 2.44, 3.29 | 0.281 |
| Class party L10 | conservative | 137/1000 (13.7%) | 81/1000 (8.1%) | 3.565 | 0.06, 0.48, 0.16, 0.75, 2.14, 3.23 | 0.562 |

#### Step-1 Fighter + Cleric days (new defaults)

| Party/day | Policy | Encounters all cleared | Whole-party survival | Death events/day | Downs per encounter (1 → n, conditional) | Slots left at day end |
|---|---|---:|---:|---:|---|---:|
| `easy_day` | nova | 1000/1000 (100.0%) | 1000/1000 (100.0%) | 0.000 | 0.00, 0.00, 0.01 | 3.283 |
| `easy_day` | conservative | 998/1000 (99.8%) | 997/1000 (99.7%) | 0.005 | 0.00, 0.00, 0.04 | 1.870 |
| `goblin_warren` | nova | 189/1000 (18.9%) | 172/1000 (17.2%) | 1.639 | 0.00, 0.00, 0.01, 0.40, 0.05, 0.66, 1.60 | 0.010 |
| `goblin_warren` | conservative | 311/1000 (31.1%) | 276/1000 (27.6%) | 1.413 | 0.00, 0.00, 0.03, 0.34, 0.02, 0.37, 1.50 | 0.019 |
| `hard_day` | nova | 0/1000 (0.0%) | 0/1000 (0.0%) | 2.000 | 0.00, 0.04, 0.04, 0.89, 2.06 | 0.048 |
| `hard_day` | conservative | 0/1000 (0.0%) | 0/1000 (0.0%) | 2.000 | 0.00, 0.05, 0.06, 0.80, 2.09 | 0.171 |

#### One-switch-off sensitivity (300 trials per row)

Only the named Part B item is disabled; the reference has all defaults enabled. Disabling engagement also restores low-HP targeting. Disabling death structurally reports zero deaths, not evidence that lethal damage disappeared. The no-spending nova row is an exact control: the conservative-only spending change cannot affect nova.

| Level | Policy | Variant | All cleared | Whole-party survival | Deaths/day | Downs per encounter (1 → 6, conditional) | Slots at end |
|---:|---|---|---:|---:|---:|---|---:|
| 3 | nova | defaults reference | 8/300 (2.7%) | 6/300 (2.0%) | 3.900 | 0.01, 0.24, 0.95, 3.34, 3.77, 1.95 | 0.010 |
| 3 | nova | no_clock | 3/300 (1.0%) | 3/300 (1.0%) | 3.960 | 0.01, 0.33, 1.47, 3.72, 3.42, 2.18 | 0.040 |
| 3 | nova | no_prebuffs | 5/300 (1.7%) | 5/300 (1.7%) | 3.933 | 0.01, 0.34, 0.85, 3.69, 3.62, 2.12 | 0.060 |
| 3 | nova | no_death | 4/300 (1.3%) | 4/300 (1.3%) | 0.000 | 0.01, 0.25, 0.97, 3.07, 3.41, 1.83 | 0.103 |
| 3 | nova | no_backgrounds | 2/300 (0.7%) | 1/300 (0.3%) | 3.977 | 0.01, 0.38, 1.31, 3.89, 3.13, 2.09 | 0.027 |
| 3 | nova | no_engagement | 12/300 (4.0%) | 4/300 (1.3%) | 3.877 | 0.01, 0.72, 2.30, 3.00, 3.38, 2.28 | 0.023 |
| 3 | nova | no_spending | 8/300 (2.7%) | 6/300 (2.0%) | 3.900 | 0.01, 0.24, 0.95, 3.34, 3.77, 1.95 | 0.010 |
| 3 | conservative | defaults reference | 50/300 (16.7%) | 42/300 (14.0%) | 3.360 | 0.01, 0.49, 0.93, 2.57, 2.92, 1.79 | 0.020 |
| 3 | conservative | no_clock | 12/300 (4.0%) | 10/300 (3.3%) | 3.847 | 0.01, 0.25, 1.20, 3.80, 3.49, 2.04 | 0.050 |
| 3 | conservative | no_prebuffs | 27/300 (9.0%) | 21/300 (7.0%) | 3.660 | 0.01, 0.53, 1.05, 3.39, 2.92, 2.47 | 0.090 |
| 3 | conservative | no_death | 30/300 (10.0%) | 30/300 (10.0%) | 0.000 | 0.01, 0.47, 0.99, 2.19, 2.75, 2.02 | 0.113 |
| 3 | conservative | no_backgrounds | 8/300 (2.7%) | 5/300 (1.7%) | 3.903 | 0.01, 0.66, 1.46, 3.71, 3.60, 2.22 | 0.087 |
| 3 | conservative | no_engagement | 29/300 (9.7%) | 15/300 (5.0%) | 3.677 | 0.06, 0.60, 1.59, 3.01, 2.98, 2.28 | 0.127 |
| 3 | conservative | no_spending | 92/300 (30.7%) | 67/300 (22.3%) | 2.873 | 0.10, 0.73, 1.18, 1.77, 2.33, 2.13 | 0.280 |
| 5 | nova | defaults reference | 14/300 (4.7%) | 12/300 (4.0%) | 3.820 | 0.07, 0.23, 0.16, 3.18, 1.33, 3.16 | 0.147 |
| 5 | nova | no_clock | 9/300 (3.0%) | 6/300 (2.0%) | 3.893 | 0.07, 0.25, 0.36, 3.49, 1.77, 3.15 | 0.087 |
| 5 | nova | no_prebuffs | 12/300 (4.0%) | 9/300 (3.0%) | 3.850 | 0.07, 0.70, 0.16, 3.49, 1.63, 3.11 | 0.133 |
| 5 | nova | no_death | 9/300 (3.0%) | 9/300 (3.0%) | 0.000 | 0.07, 0.25, 0.17, 3.01, 1.17, 2.86 | 0.247 |
| 5 | nova | no_backgrounds | 4/300 (1.3%) | 3/300 (1.0%) | 3.953 | 0.09, 0.52, 0.19, 3.81, 2.14, 3.12 | 0.083 |
| 5 | nova | no_engagement | 23/300 (7.7%) | 8/300 (2.7%) | 3.770 | 0.08, 0.50, 0.26, 3.00, 1.92, 2.85 | 0.240 |
| 5 | nova | no_spending | 14/300 (4.7%) | 12/300 (4.0%) | 3.820 | 0.07, 0.23, 0.16, 3.18, 1.33, 3.16 | 0.147 |
| 5 | conservative | defaults reference | 70/300 (23.3%) | 57/300 (19.0%) | 3.120 | 0.14, 0.24, 0.22, 3.20, 1.13, 3.76 | 2.330 |
| 5 | conservative | no_clock | 50/300 (16.7%) | 41/300 (13.7%) | 3.363 | 0.14, 0.11, 0.23, 3.64, 1.31, 3.94 | 1.813 |
| 5 | conservative | no_prebuffs | 49/300 (16.3%) | 38/300 (12.7%) | 3.393 | 0.12, 0.66, 0.23, 3.66, 1.24, 4.01 | 2.860 |
| 5 | conservative | no_death | 50/300 (16.7%) | 50/300 (16.7%) | 0.000 | 0.14, 0.24, 0.26, 3.09, 1.15, 3.08 | 3.430 |
| 5 | conservative | no_backgrounds | 27/300 (9.0%) | 19/300 (6.3%) | 3.673 | 0.17, 0.37, 0.26, 4.01, 1.50, 3.81 | 3.187 |
| 5 | conservative | no_engagement | 64/300 (21.3%) | 47/300 (15.7%) | 3.220 | 0.14, 0.26, 0.24, 2.89, 1.56, 3.15 | 1.893 |
| 5 | conservative | no_spending | 125/300 (41.7%) | 116/300 (38.7%) | 2.463 | 0.33, 0.23, 0.36, 3.11, 1.18, 4.18 | 8.617 |
| 10 | nova | defaults reference | 27/300 (9.0%) | 18/300 (6.0%) | 3.690 | 0.03, 0.21, 0.02, 0.79, 2.45, 3.38 | 0.097 |
| 10 | nova | no_clock | 1/300 (0.3%) | 0/300 (0.0%) | 3.990 | 0.03, 0.23, 0.04, 1.28, 3.03, 3.14 | 0.110 |
| 10 | nova | no_prebuffs | 23/300 (7.7%) | 16/300 (5.3%) | 3.740 | 0.02, 0.29, 0.09, 0.88, 2.68, 3.46 | 0.497 |
| 10 | nova | no_death | 22/300 (7.3%) | 22/300 (7.3%) | 0.000 | 0.03, 0.23, 0.05, 0.97, 2.21, 2.77 | 0.797 |
| 10 | nova | no_backgrounds | 2/300 (0.7%) | 1/300 (0.3%) | 3.977 | 0.11, 0.52, 0.23, 1.88, 3.56, 3.21 | 0.590 |
| 10 | nova | no_engagement | 9/300 (3.0%) | 0/300 (0.0%) | 3.953 | 0.37, 0.69, 1.68, 2.58, 3.45, 1.98 | 0.987 |
| 10 | nova | no_spending | 27/300 (9.0%) | 18/300 (6.0%) | 3.690 | 0.03, 0.21, 0.02, 0.79, 2.45, 3.38 | 0.097 |
| 10 | conservative | defaults reference | 41/300 (13.7%) | 23/300 (7.7%) | 3.587 | 0.09, 0.55, 0.17, 0.74, 2.16, 3.21 | 0.690 |
| 10 | conservative | no_clock | 6/300 (2.0%) | 3/300 (1.0%) | 3.937 | 0.09, 0.41, 0.13, 0.91, 2.85, 3.00 | 0.323 |
| 10 | conservative | no_prebuffs | 32/300 (10.7%) | 24/300 (8.0%) | 3.633 | 0.06, 0.62, 0.21, 0.82, 2.51, 3.42 | 0.807 |
| 10 | conservative | no_death | 29/300 (9.7%) | 29/300 (9.7%) | 0.000 | 0.09, 0.51, 0.19, 0.76, 1.95, 2.85 | 1.323 |
| 10 | conservative | no_backgrounds | 14/300 (4.7%) | 5/300 (1.7%) | 3.883 | 0.29, 1.25, 0.54, 1.40, 3.45, 3.17 | 1.223 |
| 10 | conservative | no_engagement | 8/300 (2.7%) | 0/300 (0.0%) | 4.063 | 0.87, 1.07, 1.71, 2.70, 3.37, 2.11 | 1.600 |
| 10 | conservative | no_spending | 133/300 (44.3%) | 117/300 (39.0%) | 2.363 | 0.10, 0.71, 0.19, 2.31, 1.05, 2.04 | 4.033 |

#### 2024 DMG encounter-budget check

Independent local source: `5etools-v2.30.1.zip:data/book/book-xdmg.json`, **XP Budget per Character**, 2024 DMG p. 114. Budgets below are multiplied by party size. XP is raw monster XP: **no 2014 monster-count multiplier or old adventuring-day XP ceiling is applied**. Ratings use the smallest listed budget accommodating the encounter (below Low is included in Low); these are budget brackets, not simulated win probabilities.

| Day | Low | Moderate | High | Encounter XP (1 → n) | Budget brackets (1 → n) |
|---|---:|---:|---:|---|---|
| `classes_level_3` | 600 | 900 | 1,600 | 300, 900, 800, 600, 900, 900 | Low, Moderate, Moderate, Low, Moderate, Moderate |
| `classes_level_5` | 2,000 | 3,000 | 4,400 | 1,200, 1,800, 1,800, 2,300, 2,250, 2,300 | Low, Low, Low, Moderate, Moderate, Moderate |
| `classes_level_10` | 6,400 | 9,200 | 12,400 | 5,400, 5,700, 6,400, 6,800, 7,700, 7,300 | Low, Low, Low, Moderate, Moderate, Moderate |
| `easy_day` | 1,000 | 1,500 | 2,200 | 150, 450, 600 | Low, Low, Low |
| `goblin_warren` | 1,000 | 1,500 | 2,200 | 200, 450, 600, 900, 250, 900, 900 | Low, Low, Low, Low, Low, Low, Low |
| `hard_day` | 1,000 | 1,500 | 2,200 | 200, 900, 900, 700, 5,900 | Low, Low, Low, Low, Above High |

**Above High:** only `hard_day` encounter **5**, `young_red_dragon`: **5,900 XP vs 2,200 High** for the two level-five PCs. **No class-party encounter is above High; none even exceeds its High budget.** Class L10 totals 39,300 raw XP, but the 2024 table supplies encounter budgets, not a daily XP cap.

#### Plausibility judgment

- The easy patrol's 99.7–100% whole-party survival is consistent with its very low per-encounter XP. The hard day's zero observed survivors is unsurprising given the above-High dragon finale; 0/1,000 is not proof of a true zero probability.
- The seven-Low-encounter warren is much more attrition-heavy: whole-party survival is 17.2% nova / 27.6% conservative (clearance 18.9% / 31.1%). An encounter budget does not guarantee surviving a long sequence without a long rest.
- **The class-party results remain too lethal to claim tabletop balance calibration.** Conservative whole-party survival is 13.0%, 19.2%, 8.1% at L3/5/10; nova is 2.1%, 2.9%, 5.1%. These rates cannot be explained by calling any class encounter above High. They remain stress-model results: fixed encounters with no retreat, no grid/cover/dispersal, damaging areas that can cover the whole party, focus-capable enemies, and greedy non-search spell/resource policies. Background ability boosts are not a complete species/origin-feat subsystem.
- Repeated knockouts are not conflated with deaths. In L5 nova, the Moderate-budget Mage encounter produces 3.22 downs per reached fight; this is a concrete warning about AoE exposure and recovery, not a reason to relabel its XP Above High.
- Resource use is not the same as optimal pacing. In the 300-run L5 conservative cohort, disabling the new spending rule increases whole-party survival from 57/300 to 116/300, while increasing slots stranded at day end from 2.330 to 8.617. At L3 it likewise rises from 42/300 to 67/300. The requested 50%-HP/danger triggers can exhaust resources earlier; the sensitivity therefore documents a real tradeoff rather than claiming the under-spending fix automatically improves clearance.
- The L10 300-trial reference also shows the spending tradeoff: 23/300 whole-party survivors with the new rule versus 117/300 with it disabled; slots at end are 0.690 versus 4.033. The six requested realism switches are implemented, but this forecast/spending policy is not claimed to be an optimized adventuring-day strategy.
- New-default conservative slots left average 0.044 / 2.337 / 0.562 at L3/5/10, versus the reviewed approximately 16.7-slot diagnostic failure. These are **unconditional means over the new cohorts**, not a like-for-like remeasurement of the review's failure-only cohort. The exact 17-slot emergency regression separately proves that an exhausted old encounter budget cannot block a useful heal at 40% HP. Finite legal turns or death before acting can still strand resources.

#### Reproduction and verification

Artifacts: [complete rows and per-encounter denominators](../data/reports/step4_fix_results.json), [pytest output](../data/reports/step4_fix_pytest.txt), [batch/direct equality check](../data/reports/step4_fix_batch_check.txt). All logs/checkpoints are outside `engine/`.

The resumable runner accepts seed-preserving trial batches to avoid a single-core tail on expensive 1,000-trial rows. It burns exactly the original master-RNG prefix, calls the real `run_day` on fresh actors for each trial, orders results by original trial index, and uses the engine's unchanged aggregation. Batched versus direct execution passed **all-field equality** for class and fixed-sheet controls. Completed whole-row results are retained when resuming; no input/behavior change was used to accelerate the simulation.

```powershell
& C:/Users/xgxxg/anaconda3/python -m engine.step4_fix_report --self-check
& C:/Users/xgxxg/anaconda3/python -m engine.step4_fix_report --workers 12 --batch-size 100
& C:/Users/xgxxg/anaconda3/python -m pytest tests -q
```

Tracked rule-implementation fingerprint: `02692fa4a21dc73d4dfe4063a416adcd21caece7e8875b63ba67a4428199ecee`. Spell, monster, class recipe, and encounter inputs remained unchanged during the measurements.

```text
2084 passed in 1064.03s (0:17:44)
```
This includes the unchanged exact fixed-sheet legacy survival/distribution assertions, source/numeric mutation audits, review regressions, builder-wiring behavior mutants, all six day switches, and day/CLI validation. Wall time was measured under concurrent Monte Carlo CPU load, not as a performance benchmark.


## Step 4 fix round 2

This section supersedes the earlier Step-4 main results, not the modelling
choices awaiting a product decision. **Only findings 6-10 were addressed.**
Area target counts, positioning/screening, threat selection, pursuit to
extermination, encounter inputs, and the spending forecast/emergency/budget
rules remain unchanged. No spell, monster, class recipe, or encounter YAML was
edited. No pip, network access, or commits were used. New measurement artifacts
and logs are under `data/reports/`, never `engine/`.

### Corrections and exact regression/mutation gates

`tests/test_step4_fix2.py` has **31 parametrized cases**, including **12 killed
in-memory regression variants**. Every finding has a `test_step4_fix2_N_...`
exact behavioral oracle and mutation proof. Mutants recompile inspected methods
or replace functions only in memory; monkeypatch restores each test's state.
No mutation modifies production or fixture files.

| Finding | Root correction | Exact oracle and rejected regression |
|---|---|---|
| 6 | Safe time resets turn economy using the same reset as `begin_turn`, advances the global turn identity, and leaves stale slot/feature markers behind. Periodic safe-time turns also advance identity and expire turn-bound restrictions. A zero gap remains a no-op. | `6_safe_time_economy`: Shield reaction 0 -> 1, Counterspell unavailable -> available after 100 rounds; actions, bonus actions, grants, Surge and slot marker reset. `6_periodic_safe_turn_limits`: Cloudkill initial plus three distinct ticks gives exactly 32 damage to each victim. Removing economy reset, global advancement, or periodic advancement is killed (3 variants). |
| 7 | Every non-attack saving-throw resolution owns a fresh damage cache. All simultaneous victims reuse each component's roll; another resolution gets a new cache. Components are keyed by primitive identity, not merely equal dice text. | `7_simultaneous_save_damage`: Cone of Cold, Fireball and Cold Breath each call the damage roller once, with failed/failed/successful/resistant damage `[8,8,4,4]`. `7_components_attacks_and_ticks`: Flame Strike components give `[15,15]`; three rays roll separately; initial Cloudkill shares, later creature ticks do not. Removing automatic sharing or conflating identical-dice components is killed (2 variants). |
| 8 | With the existing surplus-slot trigger, score every available slot through the existing offensive/control and prevention scorers, plus healing capped at the selected recipients' missing HP. Choose the cheapest maximum useful score. The forecast, danger thresholds, budget and spending permission are unchanged. | `8_cheapest_equal_effect`: one 40-HP Mage makes Hold Person scores `[11.71125,11.71125]` and Command scores `[11.1375,11.1375]` at base/third slots in this one-Cleric, one-round fixture; base slots win. Two actual humanoids make third-level Hold useful. A one-HP deficit uses base Cure Wounds; a large deficit and useful Magic Missile still upcast. Reverting to highest-slot selection is killed (1 variant). |
| 9 | Clocked rests now have explicit start/interrupt/resume/finish state and per-PC last-long-rest history. Start requires 16 hours since the preceding finish. Ordinary sleep ends concentration. Long-rest benefits restore ordinary reduced maximum HP and abilities and reduce Exhaustion by one. | `9_long_rest_clock_and_recovery`: fifth-slot Hex ends; HP maximum 34 -> 44, Strength 8 -> 19, Exhaustion 2 -> 1 -> 0. Immediate/15h59m54s starts reject; the exact 16-hour start accepts. Interruption and feature-exception cases are exact. Bypassing interval, sleep, restoration or interruption gates is killed (4 variants). |
| 10 | `compare_deadline()` provides epsilon-safe three-way round-clock ordering. Revivify validation, automatic targets, policy, rescue and the revival helper share `can_revive()`. Spell/effect expiry, stable waking, summon-control deadlines, rest eligibility/completion and short-rest entitlement use the same comparator. | `10_accumulated_revivify_boundary`: 50 actual fifth-round `end_turn` increments yield elapsed `10.000000000000142`; all five revival paths accept, keep the death event, and charge the real slot except the deliberately payment-free helper. All reject 10.01. Seven seventh-round increments approach expiry from below and still expire a spell, remove a detached effect and wake a stable PC. Raw revival/deadline comparisons are killed (2 variants). |

The pre-existing non-scaling/surplus-slot test was corrected to distinguish
**no enemy** (extra Magic Missile darts score no benefit, choose slot one) from
an actual enemy (useful extra darts still choose slot five). No statistical
expectation or tolerance was weakened. Other existing seeded assertions remain
unchanged. The one-Cleric score fixture above deliberately fixes a one-round
horizon; it is not the re-review's four-PC forecast and does not claim its
30.495375 / 18.5625 scores.

### Damage-roll audit

Local primary rules evidence: `5etools-v2.30.1.zip`, XPHB Playing the Game,
Saving Throws and Damage (p. 28), and XPHB Long Rest/Concentration/Exhaustion
glossary entries. The audit visited **245 spells, 70 monster sheets**, including
embedded effect blocks: **131 declared damage blocks**, **76 with saving throws**.
[Complete block inventory](../data/reports/step4_fix2_damage_audit.json) records
source paths, events, target declarations, components and roll scopes.

**No supported simultaneous saving-throw effect has a printed exception that
requires independent damage per victim.** In particular, dragon/hound breaths,
Vrock's screech, and multi-target Engulf/Whelm share per activation. Single-target
saves remain ordinary single rolls. These legitimate separate rolls remain:

- Separate attacks/rays/beams and later monster weapon attacks/riders. Ice
  Knife's piercing attack and Lightning Arrow's direct attack are separate from
  their shared saving-throw explosion/splash.
- Later per-creature periodic ticks (Cloudkill, Spirit Guardians, Moonbeam,
  Flaming Sphere, etc.), later Call Lightning/Dragon's Breath commands, and
  delayed Vitriolic Sphere damage each have fresh rolls. Only victims in the
  **same resolution** share; a spell's lifetime is not one cached roll.
- Flame Strike, Destructive Wave, Ice Storm and Jallarzi's Storm of Radiance
  have separate damage components. Each component rolls once across the
  simultaneous victims; two components with identical dice are not one roll.
- Magic Missile retains its explicit shared roll. Sear Undead already shares
  its roll and was not changed.

#### Affected reproducibility baselines

The 500-run, seed-one fixed-sheet CR sanity cohort is re-run with fresh actors
and the unchanged default `Combat` policy: Fighter 5 / Fighter 5 / Cleric 5 /
Cleric 5. A matched control disables **only automatic saving-throw sharing**, in
memory. It does not change target counts or enemy/party policy. Thus differences
between those two rows isolate finding 7 rather than a day preparation/AI change.
The old artifacts remain historical; all summary/resource fields for both
current/control cohorts are in
[the new baseline artifact](../data/reports/step4_fix2_repro.json).

| Monster | Wins independent -> shared (of 500) | Mean rounds independent -> shared | Mean party HP independent -> shared |
|---|---:|---:|---:|
| `mage` | 456 -> 437 | 1.858 -> 1.830 | 88.718 -> 89.888 |
| `priest` | 500 -> 500 | 1.000 -> 1.000 | 173.516 -> 173.516 |
| `mage_apprentice` | 500 -> 500 | 1.022 -> 1.016 | 165.094 -> 165.248 |
| `cultist_fanatic` | 500 -> 500 | 1.000 -> 1.000 | 171.038 -> 171.038 |
| `imp` | 500 -> 500 | 1.000 -> 1.000 | 171.984 -> 171.984 |
| `quasit` | 500 -> 500 | 1.000 -> 1.000 | 173.116 -> 173.116 |
| `stone_golem` | 308 -> 308 | 6.344 -> 6.344 | 63.204 -> 63.204 |
| `aboleth` | 29 -> 29 | 4.582 -> 4.582 | 5.490 -> 5.490 |
| `adult_red_dragon` | 0 -> 0 | 1.018 -> 1.084 | 0.000 -> 0.000 |
| `young_white_dragon` | 456 -> 421 | 3.130 -> 3.154 | 68.548 -> 65.030 |

**Explanation of every changed cohort:** Mage changes because Cone of Cold and
Fireball now use one correlated roll across simultaneous targets; Mage Apprentice
changes through Thunderwave/Ice Knife splash; Adult Red Dragon changes through
Fire Breath; Young White Dragon changes through Cold Breath. Sharing also removes
per-victim RNG draws, so subsequent saves, initiative-adjacent decisions and
recharges can diverge in a seeded trial. These are new reproducibility baselines,
not an expectation that fixing damage must improve survival. The shared-roll
Mage cohort wins less often (437 vs 456) despite higher mean remaining party HP;
wins, correlated collapses and unconditional HP are different metrics.

Priest, Cultist Fanatic, Imp, Quasit, Stone Golem and Aboleth reproduce **every
summary/resource field exactly** in the independent/shared cohorts. Their fixed
day/attack paths either do not resolve simultaneous damaging saves or use separate
per-creature periodic events. No expected value, statistical tolerance, monster
stat, coverage count or target policy was adjusted to recover old numbers. All
twenty CR/control cohorts completed (10,000 fresh fights).

### Clocked rest contract

`ClockRest(combat, party, kind)` is the new-clock lifecycle; `take_rest()` remains
the benefits-only helper used by the intentionally unclocked legacy path.
`run_day()` now starts and finishes a `ClockRest`, rather than granting benefits
unconditionally after elapsed time. It rejects an ineligible consecutive long
rest instead of silently inserting sixteen hours into the schedule.

- The default safe long rest supplies eight hours with the required sleep/light
  activity. Ordinary sleep starts when the rest starts and drops concentration;
  explicit `no_sleep` or `concentration_while_asleep` feature flags preserve it.
  The existing `no_sleep` status is also honored. These flags do not shorten the
  rest or waive the sixteen-hour interval.
- Ordinary reductions return to recorded original maxima/ability scores, without
  reducing higher scores or erasing active spell HP bonuses. An explicitly
  adjudicated `long_rest_no_restore` status can exempt `max_hp`, named abilities,
  or `exhaustion` for a specific effect that says the rest cannot restore it.
  No supplied actor is silently assigned an exception. Dead/zero-HP PCs get no
  ordinary rest benefits, and death-event/spending counters are not erased.
- Initiative, an attempted legal non-cantrip casting (including innate,
  countered and long-cast preparation), and positive damage automatically
  interrupt the affected resting PCs even with logging off. The no-grid caller
  reports a completed hour of exertion with
  `rest.interrupt("exertion", exertion_rounds=600)` after advancing the clock;
  lesser exertion and cantrip casting do not trigger this long-rest stop.
- An interruption after a rested hour grants Short Rest benefits, not Long Rest
  benefits. An interrupted Short Rest cannot finish and must be restarted.
  A Long Rest may explicitly `resume()`: each interruption episode adds one
  hour, and time spent interrupted is excluded. Finish before the revised
  deadline or while interrupted raises without granting Long Rest benefits.
  `abort()` ends the attempt. The safe YAML rest steps do not invent/resume an
  interruption automatically; an actual interruption is surfaced to the caller.

### Re-run Step-4 and Step-1 day measurements

All main rows below use **1,000 runs, master seed 1**, default monster policy,
fresh actors and the original day definitions. Clearance, survival, deaths,
conditional encounter denominators and unconditional end-slot means use the
same definitions as the preceding fix round. No balancing or target-density
change was made. Previous sensitivity tables are historical, not remeasured
current-code one-switch-off estimates.

**Completed: 14/14 day rows, 14,000 day trials** (12,000 requested new-default trials plus 2,000 exact legacy controls). The separate CR/control experiment adds 10,000 fights. No trial count was reduced.

#### Class-party days

| Party/day | Policy | All encounters cleared | Whole-party survival | Death events/day | Downs per encounter (conditional) | Slots left |
|---|---|---:|---:|---:|---|---:|
| Class party L3 | nova | 37/1000 (3.7%) | 33/1000 (3.3%) | 3.856 | 0.01, 0.24, 0.97, 3.46, 3.25, 2.37 | 0.006 |
| Class party L3 | conservative | 140/1000 (14.0%) | 101/1000 (10.1%) | 3.483 | 0.02, 0.46, 0.99, 2.54, 2.92, 2.20 | 0.057 |
| Class party L5 | nova | 45/1000 (4.5%) | 38/1000 (3.8%) | 3.827 | 0.07, 0.29, 0.17, 3.10, 1.65, 3.23 | 0.081 |
| Class party L5 | conservative | 253/1000 (25.3%) | 216/1000 (21.6%) | 3.047 | 0.13, 0.19, 0.25, 3.01, 1.14, 3.63 | 2.477 |
| Class party L10 | nova | 82/1000 (8.2%) | 50/1000 (5.0%) | 3.731 | 0.02, 0.23, 0.04, 0.83, 2.42, 3.22 | 0.307 |
| Class party L10 | conservative | 156/1000 (15.6%) | 104/1000 (10.4%) | 3.483 | 0.05, 0.51, 0.14, 0.81, 1.97, 3.24 | 0.490 |

#### Step-1 Fighter + Cleric days

| Party/day | Policy | All encounters cleared | Whole-party survival | Death events/day | Downs per encounter (conditional) | Slots left |
|---|---|---:|---:|---:|---|---:|
| `easy_day` | nova | 1000/1000 (100.0%) | 1000/1000 (100.0%) | 0.000 | 0.00, 0.00, 0.01 | 3.283 |
| `easy_day` | conservative | 998/1000 (99.8%) | 997/1000 (99.7%) | 0.005 | 0.00, 0.00, 0.04 | 1.870 |
| `goblin_warren` | nova | 189/1000 (18.9%) | 172/1000 (17.2%) | 1.639 | 0.00, 0.00, 0.01, 0.40, 0.05, 0.66, 1.60 | 0.010 |
| `goblin_warren` | conservative | 311/1000 (31.1%) | 276/1000 (27.6%) | 1.413 | 0.00, 0.00, 0.03, 0.34, 0.02, 0.37, 1.50 | 0.019 |
| `hard_day` | nova | 0/1000 (0.0%) | 0/1000 (0.0%) | 2.000 | 0.00, 0.04, 0.04, 0.89, 2.07 | 0.048 |
| `hard_day` | conservative | 0/1000 (0.0%) | 0/1000 (0.0%) | 2.000 | 0.00, 0.05, 0.06, 0.80, 2.09 | 0.168 |

#### Changes from the preceding main table

| Class level / policy | All cleared: previous -> current | Whole-party survivors: previous -> current |
|---|---:|---:|
| L3 / nova | 30 -> 37 | 21 -> 33 |
| L3 / conservative | 170 -> 140 | 130 -> 101 |
| L5 / nova | 35 -> 45 | 29 -> 38 |
| L5 / conservative | 233 -> 253 | 192 -> 216 |
| L10 / nova | 85 -> 82 | 51 -> 50 |
| L10 / conservative | 137 -> 156 | 81 -> 104 |

The class cohorts contain area spells and/or damaging multi-target monster
saves, so the corrected correlation and changed RNG consumption affect all six
rows. Conservative also stops buying score-equivalent target capacity and
overhealing with higher slots; nova does not use that policy branch. Safe
periodic turns now have their own limits/economy, and boundary expiry is uniform.
These day-table deltas combine the fixes; unlike the matched CR control above,
they do **not** causally allocate a numerical improvement or loss to each fix.
The class schedules contain only Short Rests, so the Long Rest correction is
not an explanation for their outcomes.

**Measured unchanged controls:** both `easy_day` and both `goblin_warren`
new-default summaries match the preceding artifact in **every field**, including
encounter denominators/resources, elapsed time and end slots. The affected
`hard_day` dragon breath changes internal encounter/down/time measurements
(and conservative end slots 0.171 -> 0.168), although both headline rows remain
0/1,000 survivors and exactly two death events/day. Zero observed survivors is
not a claim that the true survival probability is mathematically zero.

The independent legacy standard-day controls retain **127 nova / 162
conservative** survivors and the unchanged exact distributions:

```text
nova:         {2:8, 3:97, 5:449, 6:319, 7:127}
conservative: {1:1, 2:47, 3:203, 4:1, 5:397, 6:189, 7:162}
```

**Interpretation:** rules corrections do not make this a calibrated tabletop
model. Current conservative whole-party survival is 10.1%, 21.6%, 10.4% at
L3/5/10; nova is 3.3%, 3.8%, 5.0%. The unchanged dense-area, positioning,
extermination and forecasting assumptions remain consequential and pending
product decisions. No target-count cap, retreat rule, screening redesign,
regeneration/fire valuation, or additional resource-reservation policy was
introduced to improve these figures.

Rule-implementation SHA-256: `989f05d61e581dc029b3e5e10ce9163540bba9317cccfcbaff393e14ac9b6d04`.
[Verification manifest](../data/reports/step4_fix2_verification.json) records
trial totals, matched fingerprints, unchanged controls and test outcomes.

### Reproduction and final verification

The resumable runner now accepts `--main-only` and `--legacy-controls`; its
seed-preserving batches and the unchanged aggregation passed direct/batched
all-field equality for both class and fixed-sheet controls. The result artifact
includes a rule-implementation fingerprint; no checkpoint from a different
fingerprint is merged. The additional CR control is in memory only.

```powershell
& C:/Users/xgxxg/anaconda3/python -m engine.step4_fix_report --self-check
& C:/Users/xgxxg/anaconda3/python -m engine.step4_fix_report --main-only --legacy-controls --workers 10 --batch-size 100 --output data/reports/step4_fix2_results.json
& C:/Users/xgxxg/anaconda3/python -m engine.step4_fix_report --repro-baselines --workers 4 --output data/reports/step4_fix2_repro.json
& C:/Users/xgxxg/anaconda3/python -m pytest tests -q
```

Artifacts: [day results](../data/reports/step4_fix2_results.json),
[CR/control results](../data/reports/step4_fix2_repro.json),
[direct/batch check](../data/reports/step4_fix2_batch_check.txt),
[full pytest output](../data/reports/step4_fix2_pytest.txt).
Superseded development runs (including an early test run overlapping source
edits) are not claimed as passing stable-tree verification.

```text
C:/Users/xgxxg/anaconda3/python -m pytest tests -q
2115 passed in 971.18s (0:16:11)
```

The final full-suite run used a stable source tree (no overlapping code edits),
and includes all prior exact seeded legacy assertions, the new 31 cases, and all
12 in-memory regression kills. The focused second-round/day-realism run also
passed **65 cases** ([output](../data/reports/step4_fix2_targeted_final.txt)).
`git diff --check` passes; no statistical tolerances or original golden spell
files were changed. Runtime was measured under concurrent Monte Carlo load,
not as a performance benchmark.
