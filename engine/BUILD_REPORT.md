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
