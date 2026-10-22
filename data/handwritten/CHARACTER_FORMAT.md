# Fixed character sheets and adventuring days

Characters use the common combat-sheet fields in `MONSTER_FORMAT.md` and the
unmodified effect vocabulary in `FORMAT.md`. This is not class progression.
Unknown keys, duplicate YAML keys, wrong types (including Boolean counters),
and unsupported spell references are errors.

## Hit Dice and recoverable resources

```yaml
hit_dice: {die: d10, count: 5}
limited_uses:
  second_wind: {max: 3, short_rest: 1, long_rest: all}
  action_surge: {max: 1, short_rest: all, long_rest: all}
```

- `hit_dice` is optional. Its only fields are required `die` (`d6`, `d8`,
  `d10`, or `d12`) and positive integer `count`. Characters start with all
  their dice; omitting the declaration means no Hit Dice are available.
- A `limited_uses` entry may be a nonnegative integer (legacy) or a mapping
  with required nonnegative integer `max` and optional `short_rest` and
  `long_rest`. Recovery is `all` or a nonnegative integer no greater than
  `max`. Omitted recovery is zero. Integer entries recover all on a long rest
  and none on a short rest. The runtime always exposes remaining integer
  counters, separate from the immutable maximum/recovery declarations.
- Numeric recovery **adds** that many uses, capped at the declared maximum;
  `all` sets remaining uses to maximum. Neither rest resets cumulative
  `resources_spent`. Spell slots recover only on a long rest.
- Fighter 5 has five d10 Hit Dice, Second Wind 3 uses (one back on a short
  rest), and Action Surge 1 use (all back on either rest).
- Cleric 5 has five d8 Hit Dice, Channel Divinity 2 uses (one back on a short
  rest, all on a long rest), and slots 4/3/2. Channel Divinity **effects remain
  unsupported**; its counter/recovery are tracked without inventing actions.

Both checked-in characters use explicit recovery mappings. Legacy monster
integer counters remain compatible and monsters are rebuilt every encounter.

## Day files

Files live in `data/handwritten/days/`. The only top-level fields are required
`name` (nonempty string) and `steps` (nonempty list with at least one encounter).
Every step contains exactly one key:

```yaml
name: Example
steps:
  - encounter: [goblin_warrior x4]
  - encounter: [goblin_warrior x3, cultist_fanatic]
  - rest: short
  - encounter: [ogre x2]
  - rest: long
```

`encounter` is a nonempty list of strings, each an existing monster filename
stem, optionally followed by ` xN` for a positive integer count. Paths, unknown
monsters, extra words, and `x0` are rejected. `rest` is exactly `short` or `long`.
No implicit rest occurs before, between, or after steps. A simulation trial
initially constructs a full-resource party, then keeps those **same objects**.

### Boundaries, knockouts, and rests

- Between encounters the gap is assumed to exceed **every** spell duration,
  even nominally indefinite spells. All instances end through their normal
  callbacks; afterward concentration, conditions, detached end effects,
  statuses, temp HP, temporary removal, and per-turn bookkeeping are cleared.
  Exhaustion is also cleared by this deliberately broad condition cleanup.
  Permanent removal remains permanent. Zero HP still means unconscious/prone:
  cleanup never revives a character. HP and remaining/spent resources persist.
- After a cleared encounter, living allies may cast Cure Wounds or Healing
  Word (or an explicitly ally-targetable healing action) once successfully per
  downed ally. This uses actual spell/action resolution and spends resources;
  it is not an automatic HP reset or general out-of-combat top-up. Defeated
  enemies cannot react. Each healing attempt gets a fresh out-of-combat turn.
  The policy hook `recover_downed` may replace or decline this behavior.
- Short rests require at least 1 HP and availability in the party. The policy
  spends dice one at a time, healing `max(1, die roll + Constitution modifier)`
  each, capped at maximum HP, then short-rest counters recover. Default/nova
  aim for full HP; conservative aims for 85%. Short rests never restore slots.
- Long rests require at least 1 HP and availability. They restore all HP,
  slots, **all** Hit Dice (2024), and declared long-rest resources. Rest length,
  interruption, food, and daily eligibility limits are assumed satisfied.
- A character still at 0 HP gets **no** short- or long-rest benefit and stays
  out until a living ally heals them (including during later combat) or the
  day ends. There are no death saves, spontaneous stabilization, or deaths.
- A TPK at encounter end immediately fails the day, before healing/rests.
  Round-limit draws and losses due to unavailable/removed PCs also fail rather
  than silently deleting undefeated monsters. Only party victories count as
  encounters cleared. A successful day may still have individual PCs down.

## Running and reading results

```powershell
python -m engine.day --party fighter5 cleric5 --day goblin_warren --runs 1000 --seed 1 --strategy conservative
python -m engine.day --party fighter5 cleric5 --day hard_day --runs 1000 --seed 1 --strategy nova --monster-strategy default --json
```

Party `--strategy` and independent `--monster-strategy` accept `default`,
`nova`, and `conservative`; both default to the original policy. A named day
or an explicit `.yaml` path is accepted. See `engine/BUILD_REPORT.md` for
heuristics and the measured content difficulty. `engine.simulate` is unchanged
at its public CLI/API: it still runs full-resource single encounters.

Python APIs in `engine.day`:

- `load_day(name_or_path)` validates a definition.
- `run_day(party, definition, spells, seed=1, policy=..., monster_policy=...)`
  mutates supplied `Combatant` objects and returns `DayResult`: `survived`,
  `encounters_cleared`, `encounters`, and optional `failure_reason`.
- Every `EncounterResult` includes `index`, expanded `monsters`, `cleared`,
  `rounds`, `start`, `end`, `after_healing`, `downs`, and
  `downs_by_character`. Snapshots keyed by PC id contain real HP/max HP,
  temp HP, remaining slots/resources/Hit Dice and cumulative resources spent.
  `end` is **before** cleanup/healing; `after_healing` is after both (or just
  cleanup for a failed encounter). Downs count each positive-to-zero HP
  transition during combat, including repeated knockouts of the same PC.
- `simulate_day(...)` returns `DaySummary`. The JSON CLI serializes that
  summary, not all raw runs. Distribution values are counts, HP% uses total
  party HP / total maximum HP, and slot/resource/Hit Dice means sum over the
  party. All encounter means are **conditional on reaching that encounter**;
  `reached` gives that denominator. Never-reached entries have null scalar
  means and empty resource maps. JSON object keys (including slot levels and
  cleared counts) are strings. Every trial/encounter/rest uses seeded RNGs.
