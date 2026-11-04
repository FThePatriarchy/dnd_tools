# Handoff (2026-11-04)

Where the project stands, how to run it, and what to do next. Written at the end of a long cloud session so work can continue locally or in a new session.

## 1. Get the latest code

All recent work is on the branch **`master-2ex6wj`** (76 commits ahead of `master`). `master` does not have it yet.

```bash
git fetch origin
git checkout master-2ex6wj          # or merge it into master:  git checkout master && git merge master-2ex6wj
pip install -e ".[dev]"             # pyyaml, plus pytest for the tests
```

Python 3.11+ and `pyyaml` are the only requirements to run the program.

## 2. Run it

```bash
python -m engine.app                # opens the web app at http://127.0.0.1:8765
```

Tabs:

- **Fight**: a party against monsters: win, defeat, someone down and someone dies, the DMG budget band, and per character. **Difficulty range** runs the same fight with no resources, in its place in an adventuring day, and with full resources.
- **Adventuring day**: fights and rests in order, or filled from a preset (Typical: easy, hard, short rest, easy, boss; Short; Long), with an intensity scale.
- **Encounter ideas**: DMG-budget fills by shape and creature type, sent to the Fight tab.
- **Compare builds** and **Build search**: min-maxing with 95% intervals, judged by single fights (party rating) or by adventuring days.
- **Party rating**, **My characters** (build and save your own characters at any level 1-20; saved in `data/user/builds`, gitignored), **Library** of builds and monsters.

The command-line tools still work: `engine.dm`, `engine.compare`, `engine.optimize`, `engine.rating`, `engine.finder`, `engine.templates` (see `readme.md`).

Tests: `python -m engine.source_files --fetch` once (downloads the pinned 5etools v2.30.1 data the source cross-checks need), then `python -m pytest` (3,202 tests, about 10 minutes).

## 3. Where to read more

- `ROADMAP.md`: the project record. The section **"Audit and fixes (2026-11-02)"** at the top summarizes the recent work; older phases follow (their tables are pre-rerun values).
- `AUDIT.md`: the audit of combat simulation, build comparison and DM tools, with what was fixed and what is still open.
- `data/handwritten/CLASS_FORMAT.md`: class, feat, species and builder rules and their omissions.
- `data/handwritten/MONSTER_FORMAT.md`: monster sheet format and import workflow.

## 4. What was done (this session)

- **Runs from a fresh clone**: the engine reads only `data/handwritten/` at runtime.
- **Combat AI**: damage estimates respect immunity, resistance and vulnerability, cap damage at a target's HP, value the weapon against the creature actually attacked; every class values buffs; Haste values its extra attack minus lethargy risk.
- **All calibration sweeps and preset ratings rerun** with the new AI (ratings moved at most 0.05x).
- **Build comparison** is focused and paired (`engine/focused.py`), with bootstrap intervals; `--party/--replace` for your own party; day-based comparison (`engine/day_compare.py`).
- **Build search** (`engine/optimize.py`): hill-climbs one member's build; `--min-gain`, finalist cap, accepts `.yaml` builds in `--party`. First result: the L5 fighter in the standard party gained about 15% (Goliath Stone, Lucky, Great Weapon Master; `data/reports/optimize_L5_fighter_standard_party.*`).
- **Species**: Dwarf, Gnome, Halfling, Human, Orc, Tiefling, Dragonborn, Goliath (Stone/Fire).
- **Monsters**: 63 more XMM monsters (154 total, `engine/monster_more.py`); calibration keeps its original 91-monster roster.
- **Adventuring days**: presets (`engine/day_presets.py`), a no-resources floor (`run_encounter(resources="none")`), the difficulty range.
- **Resources**: experimental `budgeted` strategy (evaluated: not better than `rationed`, which stays the default for days); `rationed` now shares pact slots until the next rest and budgets Sorcery Points (neutral in evaluation, kept as rules-correct).
- **Web app** (`engine/app/`) and the character builder.
- **Speed-ups with identical results**: single fights about 4.6x faster, rationed days about 10x, day building 11 s -> 2.6 s (`Combat.memo`, `Combat.state_key`).

## 5. Key findings to keep in mind

- A fight's difficulty depends hugely on resources. Two trolls against the standard L5 party: 1% defeat at full resources, 47% with none; as the boss of a typical day, the party wins about 82%.
- At full DMG budgets the simulated L5 party does not survive a four-fight day, and each Low fight costs it about 40% of its spell slots. That is why "easy" is half of Low and day intensity is adjustable. Read day results as comparisons, not absolutes.
- Rationing changes were neutral: in this engine, how resources are rationed is no longer what limits a party's day; the fights themselves and combat play are.
- 2024 DMG gives no encounters-per-day number; informal table polls put most groups at 2-5 combats per long rest.

## 6. Next steps (in suggested order)

### A. Multiclassing, phase 1 (planned, not started)

Build each class at its own class level with the same ability scores, then merge the sheets under the 2024 rules. No simulation slowdown: the merged sheet is built once and cached.

| Part | Rule | How |
| --- | --- | --- |
| Prerequisites | 13+ in each class's primary ability | Check against the 5etools class data (`raw_data/class`, multiclassing section) like the existing source checks |
| Level, proficiency bonus | Total character level | Sum of class levels |
| Hit points | First class's die at max at level 1, then each class's average + Con | Direct |
| Saves, armour, weapons | First class only; later classes add their limited multiclass proficiencies | First sheet plus the class data's gained proficiencies |
| Features, limited uses | Each class's features at its own class level | Union of the two sheets |
| Extra Attack, Unarmored Defense | Don't stack | Keep the best one |
| Spell slots | Full casters count fully, paladin/ranger half rounded up; multiclass spellcaster table | One shared slot table |
| Spells | Per class, from its own list and class level | Union |

- Recipe: `choices.multiclass: [{"class": "fighter", "level": 2}]` on top of the main class.
- Phase 1 supports combinations whose classes share a spellcasting ability or where one class doesn't cast (Fighter/Rogue/Barbarian dips; Sorcerer/Paladin/Bard; Cleric/Druid). The builder should reject, with a clear message:
  - mixed spellcasting abilities (the engine has one spell DC and attack per creature; needs per-spell values);
  - Warlock with another caster (pact slots need a separate pool; the engine refreshes all of a warlock's slots on a short rest).
- Add "Add a class" in the app's My characters tab, and a short list of 4-6 common dips to `engine/optimize.py`'s candidates.
- Verify with unit tests per combination; existing single-class presets must stay bit-identical.

### B. Range bands (largest remaining simulation gap)

A light melee/near/far model, so ranged builds, reach, Sharpshooter, flying and cover can be valued. See `AUDIT.md` C6.

### C. Smaller items

- Monsters with bespoke rules not yet imported: Cockatrice, Death Dog, Stirge, Rug of Smothering, and about 350 XMM monsters with traits needing review (`engine/monster_more.py` shows the pattern; the importer keeps only a save action's damage and target, so review every save action).
- Species: Elf, Aasimar. More feats.
- App: saved parties, charts, exporting a report. Party pickers need a page reload after saving a character.
- Not rerun with the new AI: `data/reports/compare_*`, `finder_*`, and the old rule-comparison sweeps.

## 7. Practical notes

- On 4 cores a full party rating takes several minutes and a build search hours; build comparisons by day take about 2 minutes per candidate. The speed-ups above cut these by roughly 4-10x.
- The engine is deterministic for a given seed. Changes to AI behaviour shift pinned test values (`tests/test_engine_simulation.py`, `tests/test_engine_day_policy.py`); re-pin them with a comment saying why.
- `Combat.memo` caches estimates under `Combat.state_key()`. If you add state that the AI's estimates read, add it to `state_key`, or tests that monkeypatch estimates must clear `combat._memo`.
