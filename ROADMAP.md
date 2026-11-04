# Roadmap

## Goals

1. **Sample parties and opponents** for each level.
2. **Build comparison (min-maxing)** at a given level.
3. **Encounter building** for a specific party.
4. **Adventuring-day building** — encounters plus short and long rests.

## Guiding principle: every answer is relative

Party strength varies a lot (an optimized party can be roughly twice as strong as a casual one), opponents vary in shape (one solo boss vs. a swarm), and "best build" depends on role, party and opponent. The tool therefore never reports a universal number such as "this encounter is Hard" or "this build is best". Every answer is stated against a named party and a named set of opponents, and those variables are inputs, not obstacles.

The simulation is the source of truth. Expected-value maths (hit chance × damage) is used only where it is cheap and safe: AI move scoring inside the simulation, quick screening before a full run, and exact single-roll damage distributions.

## Audit and fixes (2026-11-02)

`AUDIT.md` has the full audit, the evidence behind each finding, and what is still open. In short:

- **Fresh clones run.** The engine reads only `data/handwritten/` at runtime. The three builder facts it took from the raw class JSON are in `data/handwritten/class_facts.json`, and the XPHB cross-check runs in tests only. `python -m engine.source_files --fetch` downloads the pinned 5etools files those tests need.
- **AI fixes that change results.** Damage estimates apply immunity, resistance and vulnerability (the L5 wizard had cast Fireball at fire elementals 22 times in 100 fights). Leveled spells count each victim's damage only up to its HP. The party values its weapon against the creature it would attack. Every class values buffs, the reference cleric and wizard included, and Haste values its extra attack minus the lethargy risk. The calibration sweeps (levels 1-20, with and without item kits, and the DMG morale sweep) and every preset party rating were **rerun with this AI on 2026-11-03**. The old rule-comparison sweeps (area, grab, morale side-by-side), the `compare_*` build comparisons and the `finder_*` reports were not; they predate it.
- **Ratings barely moved.** Every preset rating (casual, standard, optimized, item kits, levels 1-20) is within ±0.05× of its earlier value, most within ±0.02×; the largest moves are L11 standard 0.62× → 0.67× and L15 casual 0.47× → 0.43×, within single-seed noise. The fixes mainly change what the party spends, which a rating from full resources does not measure. Calibration cells move where immunity matters: one adult red dragon at L13 High drops from 29% to 11% defeat. The tables further down this file are the pre-rerun values.
- **Build comparison is focused and paired.** The full rating's crossings rest on one under-sampled ladder step (50-150 runs), which made per-type values swing 10-14%. `compare` now rates the base once, runs base and candidates on the deciding steps with shared seeds, and reports paired bootstrap 95% intervals. The "optimized fighter +14% against control" result became +2% (-1% to +9%). `--party ... --replace` compares builds in your own party; `--method full` keeps the old method.
- **Build search.** `python -m engine.optimize --party ... --member NAME` hill-climbs one member's build (kits, spell lists, feats, ability/ASI plans, species), accepting a change only when its interval is above zero.
- **Speed-ups (2026-11-04), bit-identical results.** The AI's read-only estimates (a creature's per-round damage, rounds left, and rationed's at-will forecast and "losing" test) are cached under a fingerprint of the fight's state (`Combat.memo`, `Combat.state_key`), recomputed whenever HP, conditions, effects, statuses, spells or the action economy change; probes and copies are never cached. Sheet validation reads spell levels from the parse cache instead of copying every spell, and monster XP comes from the validated-sheet cache. Measured: 40 runs of an L5 fight 13.0 s -> 2.8 s, five rationed typical days ~38.6 s -> 3.9 s, building a day's encounters 11 s -> 2.6 s. The pinned-result tests and a side-by-side run of the old and new code (days under rationed, budgeted and default, a caster party, a no-resources fight) give identical numbers.
- **Web app** (`python -m engine.app`): a local browser UI over the engine (fight, day, encounter ideas, compare, build search, rating, library), standard library only.
- **Resources and the adventuring day.** A single fight from full resources is the ceiling of what it demands; `run_encounter(resources="none")` gives the floor (cantrips, weapons and passive traits only). Two trolls against the standard L5 party: 1% defeat at full resources, 47-48% with none. `engine/day_presets.py` builds days between long rests: *typical* (the default: an easy fight, a hard fight, a short rest, an easy fight, a boss), *short*, *long* (the 2014 DMG's 6-8 encounters) or custom slots, filled with seeded monster picks at DMG budgets, with an intensity scale. The 2024 DMG no longer prescribes encounters per day, and informal table polls put most groups at 2-5 combats per long rest. Findings:
  - At full DMG budgets the simulated L5 party does not survive a four-fight day (every run died against Low, High, short rest, Low, High boss), and each Low fight costs it about 40% of its spell slots. Easy fights are therefore half of Low, and days are judged as comparisons with an adjustable intensity.
  - The app's **difficulty range** runs a fight three ways: no resources, in its place in several random days (rationed tactics), and full resources. Two trolls as the boss of a typical day: won 82% of the time, someone down 80%, a death somewhere in the day 22%.
  - `engine/day_compare.py` judges builds over days (`compare`/`optimize` with `measure: day` in the app): the change in the chance of finishing the day without a death, with paired 95% intervals. On the typical day (0.8×), the casual rogue costs 27 points (-37 to -19) and the optimized rogue is within noise; at 1.0×, a monk in the rogue's place adds 19.5 points (+12 to +27.5).
- **Resource valuation (2026-11-04).** `rationed` budgets spell slots as slot levels (a 3rd-level slot = three 1st) shared over the fights until the long rest, keeps Action Surge and Channel Divinity for costly fights or the last fight before a rest, shares Hit Dice per short rest, and leaves other features unbudgeted; it treats warlock pact slots as long-rest slots. The experimental `budgeted` strategy budgets every feature until it comes back (short rest or long rest, pact slots included) and prices slots in the AI's damage-equivalent unit. A paired evaluation (four L5 parties, typical and long days, 120 runs each) found it never better than `rationed` and worse twice (standard party's typical day: days without a death 78% -> 65%; sorcerer's long day 73% -> 62%), always ending days with more unspent slots, even after letting costly fights free slots. `rationed` stays the default for days; `budgeted` stays available for experiments. The likely cause is that the price compares an overkill-capped value now with an uncapped future value, so it leans towards saving.
  - `rationed` then got two rule fixes: pact slots are shared over the fights until the next rest (they return on a short rest), and Sorcery Points get a per-fight share until the long rest. Paired against the old behaviour (warlock and sorcerer parties, typical and long days, 120 runs each) neither changed outcomes measurably: warlock -1.7 and -4.2 points of days without a death, both within noise; the sorcerer was identical, because it already spends about one Metamagic per fight. They are kept because they follow the rules. In this engine, resource rationing is no longer what limits these parties' days.
- **First build search** (`data/reports/optimize_L5_fighter_standard_party.md`, about 13 hours on 4 cores). Starting from the standard L5 fighter in the standard party, it accepted Orc (+3.8%), Lucky (+3.9%), Great Weapon Master (+3.1%), then Goliath (Stone) in place of Orc (+1.4%, lower bound +0.1%), and stopped when no change in round 5 cleared zero. The party rating rose from 3,562 to 4,084 XP (about +15%, from separate full ratings). Orc, Goliath (Stone) and Human (Tough) measure within noise of each other once Lucky and Great Weapon Master are in place; the late Orc-to-Goliath swap is why `--min-gain` (0.5% by default) now guards acceptance. Ability-array changes were within noise throughout, as in Phase 5.
- **Species.** Dwarf, Gnome, Halfling, Human (a second Origin feat), Orc, Tiefling, Dragonborn and Goliath (Stone or Fire); see `CLASS_FORMAT.md`, "Species".
- **DM tools.** 63 more XMM monsters (154 in all; `engine/monster_more.py`). Reviewing them showed that the importer keeps only a save action's damage and target, so every save action in the batch was reviewed. Calibration keeps its original 91-monster roster. `--theme TYPE` on `templates` and `finder`. `dm` has `--items` and `--cover` and names the DMG band. `--level` offers only levels with preset builds instead of crashing.

## Current state (2026-10-23)

- Druid (Moon) and Sorcerer (Draconic), levels 1-10, now have standard/casual/optimized builds at 1/3/5/7/10. Both use `values_buffs`; reference parties are unchanged. Wild Shape, Innate Sorcery, selected Metamagic and rest resources are implemented; scope and XPHB corrections are in `data/handwritten/CLASS_FORMAT.md`. Comparison results are under Phase 5.
- Monk (Open Hand) and Ranger (Hunter), levels 1–10, added 2026-10-27 with casual, standard and optimized builds at 1/3/5/7/10. Both use the `values_buffs` flag, and the ranger's free Hunter's Mark casts share the warlock's Hex valuation; the eight earlier classes give bit-identical results. Combat scope and omissions are in `data/handwritten/CLASS_FORMAT.md`.
- Warlock (Fiend) and Bard (Lore), levels 1–10, added 2026-10-27 with casual, standard and optimized builds at 1/3/5/7/10. They use the paladin's buff valuation through a `values_buffs` flag; the six earlier classes give bit-identical results. Combat scope and omissions are in `data/handwritten/CLASS_FORMAT.md`.
- Barbarian (Berserker) and Paladin (Devotion), levels 1–10, added 2026-10-26 with casual, standard and optimized builds at 1/3/5/7/10. The reference parties stay fighter, cleric, rogue, wizard, and the four original classes give bit-identical results.
- Combat engine with 245 XPHB spells, 70 XMM monsters, Fighter/Rogue/Wizard/Cleric levels 1–10, 20 preset builds, adventuring-day mode with 2024 rests.
- DMG 2024 budget sweep: `python -m engine.calibration --runs 100 --write` runs the engine defaults → `data/reports/calibration_dmg_area_party_spread_grab_half.md` (the baseline). Run it under a Python with pyyaml (currently `C:\Python312`).
- Engine no-grid defaults since 2026-10-24: monster areas hit half the DMG-table count (`party_spread`), and multi-target grabs reach at most half the group (`grab_half`). The old rules are `policy.dmg_area_heuristic` and `policy.printed_grab_count`.
- First-sweep findings (2026-10-23, old defaults; `data/reports/calibration_dmg.md`):
  - On a typical encounter, difficulty climbs Low → Moderate → High as the DMG describes from level 3 up. Level 1 is too lethal: someone dies in about 1 in 10 Low fights.
  - A few multi-target monster abilities produce near-certain wipes at any budget: Engulf (gelatinous cube, water elemental), caster area spells (mage, priest), breath weapons in groups, Petrifying Gaze.
  - Aboleth ×3 has an inconsistent result: deaths in 96% of runs, 0% wins, 2% TPK.
  - Engine crash: Cunning Strike can target an illegal creature. The seed is in the report.

## Phase 1 — Trustworthy benchmark

Fix the modelling distortions the sweep exposed, comparing options side by side before changing any default.

- ~~Add an area-rule option to the sweep and compare the current DMG table with tighter rules.~~ Done 2026-10-24: `--area` and `--compare`, report in `data/reports/calibration_area_compare.md`. Findings:
  - Area rules fix the big single-caster and breath outliers: mage ×4 at L10 Moderate drops from 86% TPK to 12%, young red dragon at L5 Over from 64% to 28%, basilisks from 57% to 19% under `party_spread`.
  - Tighter rules that apply to both sides make swarms deadlier, because the party's own Fireball and Spirit Guardians shrink too. `party_spread` (only monster areas tightened) avoids this. It has the lowest spread and the fewest wipe outliers, so it was adopted as the engine default on 2026-10-24.
  - The remaining outliers don't respond to any area rule: Engulf/Whelm (gelatinous cube, water elemental use `n_targets`, not areas), fire elemental burning, and stacked Spirit Guardians (priest ×5) or large swarms. These are the next levers.
- ~~Cap multi-target grabs such as Engulf and Whelm to a positional estimate instead of "everyone".~~ What-if done 2026-10-24: `--grab` and `--compare-grab`, report in `data/reports/calibration_grab_compare.md`. Only Engulf (up to 4) and Whelm (up to 2) are multi-target grabs. Findings:
  - Gelatinous cube ×4 at L5 Low: TPK 90% by default, 35% with `grab_half` (2 per use), 1% with `grab_one`. Even two per use leaves a "Low" fight wiping a third of the time, because four cubes together can still swallow the whole party every round.
  - Whelm already prints 2, so `grab_half` changes nothing for it. `grab_one` takes water elemental ×2 at L5 High from 41% to 1% TPK. Water elemental ×5 (an Over probe) stays at 88% under every rule.
  - Best whole-sweep combination: `party_spread` + `grab_half` (3 wipe outliers, 24% spread, vs 6 and 33% for the old defaults). Adopted as the engine defaults on 2026-10-24. The rerun baseline reproduces the what-if results exactly. `grab_one` remains available if four-cube "Low" fights should stop wiping at all; gelatinous cube ×4 at L5 Low is still 35% TPK.
- ~~Decide fight-to-extermination vs. morale/fleeing.~~ Done 2026-10-24: morale is an optional rule, so it is a toggle (`DayOptions.morale`, `--morale`, or `options: {morale: dmg}` in a day file), off by default. `dmg` uses the DMG optional morale rule: at half HP, and when the side is down to half its number, a DC 10 Wisdom save or the monster flees. `rout` flees on every trigger with no save, as an upper bound. Report: `data/reports/calibration_morale_compare.md`. Findings:
  - With `dmg`, about 35–45% of monsters flee, fights are about a round shorter, and every slot gets easier. For example, the chance someone goes down at L5 Moderate drops from 56% to 38%, and the chance someone dies at L5 High from 23% to 6%. The DMG budgets therefore read about one step easier with morale on. A later encounter finder needs to know whether a table uses morale.
  - Morale mostly defuses swarms and groups. The fire elemental pair at L5 High drops from 93% defeat to 46%, and bandit captain ×5 at L3 Over from 61% to 23%. No Low–High encounter stays at 50% defeat or more (3 do with morale off), and the spread halves from 24% to 12%.
  - Fearless monsters never check (the cube is immune to frightened and stays at 35% at L5 Low), and aboleths win by domination before morale matters.
  - `rout` makes almost everything trivial (Low–High defeat about 0%, fights of 1.5–2 rounds). It is useful only as a bound.
- ~~Fix the Cunning Strike crash and explain the aboleth result.~~ Done 2026-10-24.
  - **Crash:** the rogue hit a dominated ally, which was a legal enemy while charmed. The Sneak Attack damage let the ally make its repeat save, so it broke free and its team flipped back mid-attack. Cunning Strike then re-checked `affects: enemy` against a creature that was now an ally. Cunning Strike now follows the creature that was hit. The sweep has no engine errors left.
  - **Aboleth ×3 (L10 Over):** 97 of 100 fights end with every conscious PC dominated (`party_unavailable`). That is a loss, but not a TPK, because those PCs still have HP. Most killing blows on downed PCs come from Psychic Drain, a legendary action that drains a creature the aboleth has charmed. That includes dominated PCs already at 0 HP. Tentacle attacks on downed PCs come next, once no free PC is left. This is rules-legal behaviour, not an engine bug.
- ~~Count losses where every remaining PC is dominated or otherwise unavailable as defeats in the calibration metrics.~~ Done 2026-10-24: the sweep reports a **Defeat** column (TPK or `party_unavailable`) next to TPK. On the baseline the two differ only for aboleth ×3 at L10 Over (3% TPK, 100% defeat). Wins plus defeats add up to 100% in every encounter, so no fight hit the round limit. The shape checks still use TPK so they stay comparable with the older sweeps, which predate the column.
- ~~Adaptive run counts: run more where an estimate is uncertain or near a threshold that matters, fewer where the answer is 0% or 100%.~~ Done 2026-10-24: `--adaptive` (with `--min-runs`, `--max-runs`, `--batch`, `--precision`, `--threshold`) writes `*_adaptive` reports. Each encounter runs in batches of 50 until defeat, any down and any death are within ±5 points at 95% confidence (Wilson interval) and the defeat interval excludes 50%, or until 800 runs. Run seeds follow the fixed sweep's order, so the first N adaptive runs are a fixed N-run sweep's runs. Every report now lists runs and the defeat ± per encounter. Results on the baseline (`calibration_dmg_area_party_spread_grab_half_adaptive.md`):
  - 34,700 runs instead of 12,000 (about 27 minutes on 16 cores). 9 clear-cut encounters stop at 50 runs; the median is 325 and one reaches 800. The widest interval tightens from ±9.6 to ±5.0 points.
  - "Someone goes down" drives most of the extra runs, since it often sits near 50%. A looser target for it alone would cut the cost if needed.
  - Conclusions hold. Only 1 of 120 fixed-run intervals misses the adaptive estimate, which is in line with 95% intervals. Imp ×8 at L3 High (50% → 45%) drops below the outlier line, leaving the two fire elemental groups as the only Low–High outliers with morale off. Two slot medians for "someone goes down" move by 5 or more points (L3 Moderate 22% → 17%, L7 High 76% → 69%).

**Done when** no single monster type dominates its budget slot, the remaining outliers are understood and justified by the rules, and the median curve is monotone at every level.

## Phase 2 — Benchmark set and party rating

- ~~Freeze a benchmark set of encounters for each level covering opponent types.~~ Done 2026-10-24: `data/benchmarks/benchmark_v1.yaml`, generated by `python -m engine.benchmark --freeze --version 1` from the rules in `engine/benchmark.py`. A test checks that v1 still reproduces from those rules. Six types for a party of four at every level 1–10:
  - **Count types** (brute, ranged, caster, swarm, control): one roster monster per level, the one whose XP is nearest (on a log scale) to a third of the Low budget (a sixth for swarm). The ladder adds more of it: 1, 2, 3, 4, 5, 6, 8, 10, 12, 16, 20, 24, stopping once a step reaches 2.5× High.
  - **Solo:** a ladder of single monsters by CR (ogre, owlbear, troll, then young white → red dragons, then adult red).
  - The gelatinous cube is left out because it is fearless and already a known outlier. The caster roster is thin (cultist fanatic below level 8, mage from level 8).
- ~~**Party rating** = the XP budget at which wipe chance reaches a set threshold.~~ Done 2026-10-24: `python -m engine.rating --party <builds>` (`engine/rating.py`).
  - **Definition:** the encounter XP at which defeat (TPK or `party_unavailable`) reaches 5%, interpolated in XP between ladder steps. It is reported per type and as an overall geometric mean, in total XP, per PC, and as a multiple of DMG High (1.00× = reaches 5% defeat exactly at High). A crossing on the first step or past the last is reported as a bound ("<" or ">").
  - **Sampling:** each step runs in 50-run batches with seeds fixed by (rating seed, encounter, batch number). A step stops once its defeat interval clears 5%, or reaches ±2 points, or 800 runs. Spare workers run extra batches early, but a step's result is always its shortest qualifying batch prefix, so a rating depends only on its seed. Once a step is confirmed above 5%, larger steps of that type are skipped.
  - **Shared runner:** `engine/encounters.py` holds the per-run logic shared with the calibration sweep. The calibration numbers are unchanged by the refactor.
- ~~Treat AI skill as a setting.~~ `--strategy default|nova|conservative` (party) and `--morale` are rating options.
- **Preset party ratings** (Fighter/Cleric/Rogue/Wizard; `data/reports/rating_preset_L*.md`; seed 1 vs seed 2):

  | Level | Overall seed 1 | Overall seed 2 | Gap | Lowest type | Highest type | Time |
  | ---: | ---: | ---: | ---: | --- | --- | ---: |
  | 1 | 0.75× | 0.76× | 0.1% | swarm 0.40× | caster 1.36× | 23 s |
  | 3 | 0.72× | 0.73× | 1.4% | swarm 0.42× | caster 1.15× | 1.3 min |
  | 5 | 0.80× | 0.82× | 2.3% | swarm 0.57× | solo 1.18× | 8 min |
  | 7 | 0.75× | 0.76× | 2.0% | control 0.58× | solo 0.96× | 17–19 min |
  | 10 | 0.73× | 0.73× | 0.4% | solo 0.53× | ranged 0.90× | 3.5 min |

  - The standard parties reach 5% defeat at about three-quarters of the DMG High budget at every level. Swarms are the weak spot at levels 1–5.
  - **Overall ratings are stable:** within 2.3% across seeds. Single types move more (up to about 0.1×, e.g. L1 brute 0.77× vs 0.66×), because a type rests on one interpolated crossing.
  - **Strategy barely matters for a single encounter:** at L5, nova 0.82× and conservative 0.82× vs default 0.80×, all within seed noise. The strategies trade resources across a day, which a one-encounter rating from full resources cannot show; a day-level rating would.
  - **Speed:** level 7 was the slow case at 17–19 minutes, because large L7 fights cost up to 2.4 s of CPU per run. After the 2026-10-25 engine speed-ups below it takes 6.6 minutes.
- **Engine speed-ups (2026-10-25), all with bit-identical results** (the full calibration baseline and the L7 rating reproduce exactly):
  - Monster target ordering now computes each candidate's threat once and sorts. It used to re-run `monster_target` for every pick, which made area-membership refreshes quadratic.
  - Scaled cantrips are cached per caster for read-only damage estimates. They used to be deep-copied on every call.
  - `Combatant.team` skips building the active-effects list when no effect carries a domination override.
  - `eligible()` reads per-block and per-caster facts once per call, not once per creature.
  - Basilisk ×6 at L7: 2.57 → 0.94 s per run. The full calibration sweep takes 3.6 minutes (was about 20) and the test suite 7.6 (was 14.7).

**Done when** any party gets a rating in minutes, and the ratings are stable across seeds.

## Phase 3 — Sample parties and opponents (Goal 1)

- ~~Party presets per level: casual, standard and optimized, each with its measured rating.~~ Done 2026-10-25: `python -m engine.presets --write` generates `{class}_{level}_casual` and `_optimized` builds from explicit rules in `engine/presets.py`; standard is the existing `{class}_{level}`. A test checks the committed files still match the rules.
  - **Casual:** standard array with the primary at 14 and a flavour stat at 15, a +1/+1/+1 background, ASIs split primary/flavour, sword and shield or a shortbow, thematic spells, and no reaction spells.
  - **Optimized:** point buy 15/15/14, +2 primary / +1 Con, ASIs to the primary, then greatsword with Great Weapon Fighting, and combat-first spells (Shield, Sleep, Web, Fireball, Spirit Guardians).
  - **Ratings** (× DMG High, `data/reports/rating_preset_L*_{casual,optimized}.md`):

    | Level | Casual | Standard | Optimized |
    | ---: | ---: | ---: | ---: |
    | 1 | 0.70× | 0.75× | 0.81× |
    | 3 | 0.59× | 0.72× | 0.81× |
    | 5 | 0.60× | 0.80× | 0.84× |
    | 7 | 0.61× | 0.75× | 0.77× |
    | 10 | 0.59× | 0.73× | 0.76× |

  - Optimized is only 3–12% above standard, and about 1.2–1.4× casual, far from the "twice as strong" a real min-maxer reaches. Standard already uses combat-first spell priorities, and the big optimizer levers (feats like Great Weapon Master, Sharpshooter, War Caster, Alert; species; multiclassing) are outside the builder's scope. Widening the gap means adding feats to the builder.
  - Building the casual cleric exposed an engine crash: pre-combat buff planning did not resolve `n: all` targets (Beacon of Hope). Fixed in `day_mechanics.py`.
- ~~Encounter templates.~~ Done 2026-10-25: `python -m engine.templates` (`engine/templates.py`). Templates are `solo`, `boss_minions`, `elite_pack`, `swarm` and `mixed`, or a custom `--shape "1 boss, 6 goons"` (roles boss/elite/minion; goon and mook mean minion).
  - **Fill:** roles get XP in the ratio boss 6 : elite 3 : minion 1, each role uses one monster type from the three nearest XP tiers, and the encounter must land at 75–100% of the budget. The budget is a DMG slot (`--difficulty`) or `--xp`.
  - **Choice:** a seeded choice among the best fills gives variety.
  - **Simulate:** `--simulate --profile casual|standard|optimized` runs each suggestion against a preset party and prints its defeat, down and death chances.
  - The gelatinous cube is excluded by default (calibration outlier); pass `--exclude` with no names to allow it.

## Phase 4 — Encounter and day finder (Goals 3 and 4)

- ~~**Encounter** and **day** finders.~~ Done 2026-10-25: `python -m engine.finder encounter|day` (`engine/finder.py`).
  - **Goal:** a primary `--target metric=value` (matched as closely as possible) plus `--limit metric<=value` / `>=` (must hold). With limits only, it returns the hardest setting that meets them.
  - **Setting searched:** one scale on the DMG budget. The encounter finder scales High and fills a template or shape (Phase 3). The day finder scales Moderate for every encounter in a `--plan "E E S E E S E E"` (E encounter, S/L short/long rest). Each encounter in the day gets its own seeded fill, cycling through the given templates.
  - **Search:** a coarse parallel scan (0.25×–2.7×, 100 runs per point), then two refinement rounds of three interior points (400 runs) inside the bracket where the target or a limit is crossed. Each distinct encounter or day is simulated once per sample size, with a seed derived from its contents, so a search depends only on its seed.
  - **Output:** the recommendation and its metrics (with 95% ± for yes/no metrics), and the curve with each distinct fill once. The report notes when stepwise fills keep any tested point from landing near the target. `--write NAME` saves `data/reports/finder_NAME.md`. The whole-day runner is `encounters.run_day_runs`.
- **Encounter demo** (L5, `boss_minions`, someone down ≈ 50%, defeat ≤ 2%; `data/reports/finder_L5_*_boss_minions.md`):
  - Casual: 0.51× High (an air elemental and four hobgoblins, 2,200 XP; down 64%).
  - Standard: 0.67× (a guard captain and four berserkers, 2,900 XP; down 58%).
  - Optimized: the same encounter, down 43%.
  - The curve is not monotone in XP: a 3,100 XP mage-led fight is far deadlier than a 3,700 XP young black dragon fight. That is the case for simulating instead of trusting XP.
- **Day demo** (L5 standard, six encounters with two short rests, mixed template, deaths ≤ 5%, 15% of slots left; `finder_L5_standard_day_{default,conservative}.md`):
  - The party stays within 5% deaths only up to about 0.33× Moderate per encounter (about 1,000 XP each, half of DMG Low). From 0.37× there is a 6–17% chance of a death, and at 0.55× about half of days end in one.
  - Slots run out on every survivable day, so the 15% slot target is unreachable. The conservative strategy does not ration better: on the easiest day it ends with 14% of slots against default's 27%.
  - Day-level answers are therefore limited by the AI's resource management more than by the finder. A strategy that rations slots and hit dice across a known day is the next lever.
- ~~A strategy that rations slots and Hit Dice across a known day.~~ Done 2026-10-25: `--strategy rationed` (`RationedPolicy`; design in `engine/BUILD_REPORT.md`, "Rationed strategy").
  - **Cause:** default casts any spell that beats a cantrip on expected damage (Fireball three times a day into 600 XP fights). Conservative's "dangerous" test is a fraction of party HP that shrinks with the number of encounters left, so trivial fights still qualify, and its slot choice upcasts.
  - **Approach:** rationed gives each encounter an equal share of slot levels, overridden for emergencies and forecast-costly fights, skips slots once a fight is already won, never upcasts, and shares Hit Dice per short rest.
  - **Results** (`data/reports/finder_L5_standard_day_survive_*.md`): the L5 standard party ends the easiest day with 69% of slots (default 27%, conservative 14%). The hardest day with deaths ≤ 5% rises from 0.35× to 0.43× Moderate per encounter (800 → 1,200 XP per fight; same day at 0.42×: default 16% deaths, rationed 0%), with 24% of slots left. The single-encounter rating is unchanged within noise (0.78× vs 0.80×).
  - **Known gap:** on hopeless days rationed could die with slots unspent (49% left at 0.71×).
- ~~Release everything once the fight is being lost.~~ Done 2026-10-25. The release triggers when at most half the party can act, or when the at-will forecast costs half the party's HP: any spell, the highest slot, healing below half HP, and short-rest features. The forecast also stopped counting incapacitated allies, which had produced false "already won" refusals in basilisk fights.
  - **Results:** unspent slots on hopeless days drop (40% left at 0.71×, 12% at 2.04×), but those days still always end in a death. The survivable boundary stays at 0.43× Moderate, and the single-encounter rating is 0.80× High, equal to default.
  - **Still open:** the forecast sees HP damage only, so control (petrifying gaze, paralysis, domination) looks cheap until PCs are out of action, often the casters holding the slots. A control-aware forecast that counts expected incapacitation as lost party actions is the next lever for rationing.
- ~~Control-aware forecast.~~ Done 2026-10-26: `RationedPolicy.control_share` (design in `engine/BUILD_REPORT.md`).
  - **Results:** it changes no measured outcome. The survivable day is still 0.43×, the rating is identical (0.80×), and single control fights match default.
  - **Why:** the hopeless days are lost to HP attrition, not control (each basilisk fight alone is 0–1% defeat), and single fights already get the full budget. Rationing on these benchmarks is now limited by attrition, not by forecast blind spots.
  - **Data gap found:** the ghoul's paralyzing Claw is in no monster routine, so ghouls never paralyze.

## Phase 5 — Build comparison (Goal 2)

Started 2026-10-26: `python -m engine.compare` (`engine/compare.py`).

- **Value:** a candidate's value is the change in the Phase 2 party rating when it replaces the reference party's member of its class, overall and per opponent type. Every candidate is rated with the same seed and per-encounter batch seeds (common random numbers). Changes under 3% overall, or under 10% for a single type, are marked as within noise, from the Phase 2 seed check.
- **Grid:** candidate × opponent type × reference party (`--references casual standard optimized`).
- **Candidates:** build names, or `--variants`, recipes of a class's main decisions at standard abilities. Fighter: kit × style. Rogue: kit and Cunning Strike pairs. Cleric: Blessed Strikes, Divine Order, spell profile. Wizard: spell profile. The shared runner now accepts in-memory recipes.
- **Screen:** a crude expected damage × effective HP score against the level's benchmark brute picks `--finalists`. It ranks fighter kits sensibly but cannot separate spell profiles, so casters are effectively all rated.
- **Fighter, level 5** (`data/reports/compare_L5_fighter_variants.md`):
  - In the standard party, every melee choice (greatsword with GWF or Defense, sword and shield with Dueling or Defense) is within ±2% overall.
  - The archer kit costs 13%: the standard fighter has only 12 Dex and light armour as an archer.
  - In the casual party the archer costs 27%, and sword and shield loses about a quarter of its solo rating. A build's value depends on the party.
- **Wizard, level 5** (`compare_L5_wizard_variants.md`): the optimized spell list matches standard (+0%), and the casual list costs 18% (21–26% against most types). Spell choice is the biggest single lever found so far.
- **Feats** (`compare_L5_{fighter,rogue,cleric,wizard}_feats.md`, `compare_L10_fighter_feats.md`): the builder now takes Great Weapon Master, Sharpshooter and War Caster in place of an ASI (with their +1), and Alert as the origin feat. See `data/handwritten/CLASS_FORMAT.md` for what each one simulates. In the standard party:
  - Great Weapon Master: +4% at level 5 and +4% at level 10 (+14% against brutes). It is the only feat clearly above noise at both levels.
  - Alert: +1% to +4% on every class. Most of its gain is against control, where acting before the controller matters.
  - War Caster: +2% on the cleric (+13% against control, from holding concentration) and exactly +0% on the wizard.
  - Sharpshooter: identical to the plain shortbow-first rogue. With no cover or long range modelled it is only +1 Dex, and 19 and 18 Dex give the same modifier. With the optional cover rules (below) it is still within noise.
  - A feat replaces a +2 ASI, so where that +2 does not change a modifier (odd starting scores) the feat is free; with even scores it would cost a point of attack and damage.
- **More feats (2026-10-31):** Tough and Lucky (Origin, like Alert), Resilient and Polearm Master (General), and a glaive kit (`chain_glaive`, `unarmored_glaive`). `python -m engine.compare --feats` rates only the standard build and its feat variants; `--only NAME…` narrows them further. Rules and approximations are in `data/handwritten/CLASS_FORMAT.md`. Reports `compare_L5_{fighter,rogue,cleric,wizard}_feats.md` and `compare_L10_fighter_feats.md` were rerun with every feat; the earlier rows reproduce exactly. In the standard party:
  - Tough: +6% fighter, +5% cleric, +4% rogue, +3% wizard at level 5, but only +1% on the level 10 fighter. Extra HP matters most while HP pools are small.
  - Lucky: +4% to +6% at level 5 on the fighter, rogue and wizard (+2% on the cleric) and +3% on the level 10 fighter. Together with Tough it is the best feat on every class at level 5 except the cleric.
  - Resilient (Wisdom on martials, Constitution on casters) is within noise everywhere: -1% to +2%. The +1 it gives seldom changes a modifier, and one more save proficiency rarely decides a fight.
  - Polearm Master: +2% at level 5, -1% at level 10. Paired with Great Weapon Master at level 10 it is +1%, below Great Weapon Master alone with the greatsword (+4%). The glaive's d10 is weaker than the greatsword's 2d6 under Great Weapon Fighting, the Pole Strike's d4 takes the Bonus Action that Hew would use, and two feats leave Str at 19, not 20.
  - At level 5 almost every candidate, Resilient included, rates +11% to +17% against control. The level 5 control crossing is sensitive to any change in the random stream, so per-type control values there are weak evidence (feat-specific claims such as Alert's against control above included).
- **Feats on the other eight classes (2026-11-01)** (`compare_L5_{barbarian,paladin,monk,ranger,warlock,bard,druid,sorcerer}_feats.md`, standard party, level 5). The reports give each value against the reference member the class replaces; the gains below are against the class's own standard build:
  - Lucky is the best or tied best feat on every class: +6% monk, +3% barbarian, druid and sorcerer, +2% paladin and warlock, +1% ranger, +0% bard. Tough is close behind (+3% barbarian and druid, +2% sorcerer and paladin, +1% elsewhere), as on the reference classes.
  - Great Weapon Master: +1% on the barbarian and paladin, below its +4% on the fighter. Its +3 damage per hit is a smaller share of a turn that already carries Rage damage or Divine Smite.
  - Polearm Master costs 5% on the barbarian and 1% on the paladin (-17% against casters on both). The glaive kit gives up the greataxe's Cleave or the greatsword, and the Pole Strike competes for the Bonus Action with Rage's turn and the paladin's bonus-action spells.
  - War Caster: +1% on the sorcerer and druid, exactly +0% on the warlock and bard (the same as the wizard).
  - Resilient: -4% to +1%. On the barbarian it is -15% against casters, and on the sorcerer -4% overall, because the +1 lands on an even score where the +2 ASI it replaces would have raised a modifier.
  - Alert: -2% to +1% on these classes, unlike its +1% to +4% on the reference four. The bard gains +7% against control with it, but the druid loses 10% against casters.
  - Sharpshooter matches the plain ranger exactly, as on the rogue; the warlock's solo ladder (-77% to -78% for every feat) still sets its overall value.
  - Across all twelve classes at level 5, no feat moves a class more than 6%. Class, kit and spell choice dominate.
- **Barbarian and Paladin in the fighter's slot** (`compare_L{5,10}_{barbarian,paladin}_variants.md`, standard party; the change is against the standard fighter):
  - Barbarian: +3% at level 5 (Great Weapon Master or Alert +4%), but -5% at level 10 (-13% against ranged, -10% against swarms). Great Weapon Master brings level 10 back to +0%. The greataxe (Cleave mastery) beats the greatsword kit by 5% overall; the greatsword kit is -17% against casters.
  - Paladin, with in-combat buff valuation: -2% at level 5 (within noise for the standard kit, both spell profiles and Great Weapon Master; -7% against casters, -6% against control), and -5% at level 10 (-16% against swarms, -14% against control). The sword-and-shield kits are -3% to -4% at level 5 (-18% against casters).
  - Buffs are now valued against attacking: gain per round over the remaining rounds, cut short by the chance of losing concentration (a DC 10 Constitution save per expected hit) and charged for the Divine Smite the spent slot would have dealt later; a bonus-action buff is also charged for this turn's smite. A first version without the slot and concentration costs cast Bless on round 1 and lost 12% against casters. With them, Bless is rarely worth its action in the standard party (the cleric and wizard mostly cast save spells, so Bless helps only the paladin and rogue), Magic Weapon is cast in about a third of fights, and Command stays below attacking. At level 5 the spell profiles prepare the same spells, so they still match. The cleric and wizard keep the old buff blind spot to preserve the published baselines.
  - Parties with a paladin simulate about 40% slower, because the auras are recomputed on every save and condition check.
- **Warlock in the wizard's slot, Bard in the cleric's** (`compare_L{5,10}_{warlock,bard}_variants.md`, standard party):
  - Warlock: -23% at level 5, but only because of the solo ladder (-78%); every other opponent type is within noise. Without the wizard the party has no fire, so the troll keeps regenerating: the party wins 82% of fights against one troll (100% with the wizard) and the solo ladder stops there. No AI targets regeneration, so the wizard stops it only because Fire Bolt and Fireball happen to be fire. The warlock prepares Hellish Rebuke but the AI does not pick fire for it. At level 10 the warlock is +4% (+23% against casters). Dropping Agonizing Blast or Armor of Shadows from the default three invocations costs another 3–5%, mostly against solo and ranged opponents.
  - Bard: +2% at level 5 (within noise; +17% against control) and -10% at level 10 (-16% to -18% against ranged, swarm and control). The casual spell profile is -4% at level 5 (-15% against casters). Alert and War Caster are within noise.
- **Monk in the rogue's slot, Ranger in the fighter's** (`compare_L{5,10}_{monk,ranger}_variants.md`, standard party):
  - Monk: +8% at level 5 (+20% against brutes, +13% against control) and +5% at level 10 (+14% against brutes). Holding back focus for Stunning Strike ("reserve") and Alert are both +9%, within noise of the standard monk.
  - Ranger: -8% at level 5 (-19% against casters, -12% against control) and -12% at level 10 (-35% against control, -21% against swarms). The sword-and-shield kit, Horde Breaker, Alert and Sharpshooter are all within 1% of the longbow default; Sharpshooter matches it exactly, as on the rogue. Against vampire spawn the level 10 ranger casts Entangle before Hunter's Mark (Hunter's Mark then waits for concentration, 0.08 casts per fight) and spends its action on Cure Wounds about twice per fight. Banning Entangle cuts the win rate against five spawn from 75% to 64%; banning Cure Wounds raises it to 80% there but lowers it against eight guard captains (17% to 11%). So the gap is the fighter's kit (heavy armour, Action Surge, Indomitable, 83% against the same spawn), not a ranger AI fault.
- **Druid in the cleric's slot, Sorcerer in the wizard's** (`compare_L{5,10}_{druid,sorcerer}_variants.md`, standard party):
  - Druid: -5% at level 5 (-11% against ranged and casters) and -11% at level 10 (-20% against swarms, -15% against ranged and control). The three spell profiles give identical results at level 5: the AI casts the same few spells from each list. Alert (-6%) and War Caster (-4%) are within noise of the standard druid. Only the standard druid was rated at level 10.
  - Sorcerer: +11% at level 5 (+19% against brutes, +18% against swarms) and +12% at level 10 (+25% against casters, +23% against swarms). Innate Sorcery (+1 DC and advantage on spell attacks), Quickened leveled spells plus a cantrip, and Draconic Resilience's extra HP and AC outweigh the wizard's extra prepared spells. The casual spell list costs 2% at level 5 and 7% at level 10; the "lasting control" Metamagic pair (Heightened + Extended) is 3% below the default Quickened + Heightened at level 5.
- **Ability scores and ASIs (2026-10-31)** (`compare_L5_{fighter,wizard,rogue,cleric}_abilities.md`): `python -m engine.compare --abilities` keeps 15 on the class's primary ability, tries each ordering of 14 and 13 over two likely secondaries (the rest get 12/10/8), and crosses that with three ASI plans: everything into the primary (the default), split (+1 primary, +1 Con at each ASI) and Con first (the first ASI is +2 Con). Arrays the builder rejects and arrays that give an identical sheet are dropped (11–16 per class), and the five best by the screen are rated. In the standard party at level 5:
  - Every candidate is within noise of the standard build on all four classes: -1% to +3% overall. The best is the split ASI with 14 Con (+2% to +3% on each class). The background's +2/+1 already leaves the primary at 19 by level 4, so the split costs no modifier and buys +1 Con.
  - Almost all of that gain is the level 5 control crossing (+11% to +14%), which moves with any change to the random stream (see Feats above). On the other five opponent types the swaps are within ±4%, apart from the fighter's Con-first plans at about +10% against brutes.
  - Moving 14 and 13 between secondaries without changing the ASIs does nothing measurable (±1%), since most secondary modifiers are never rolled in combat.
  - So at level 5 the standard array is as good as any legal alternative; the decisions that matter are kit, spells and feats. See below for level 10.
- **Ability scores and ASIs at level 10 (2026-11-02)** (`compare_L10_{fighter,cleric,rogue,wizard}_abilities.md`, standard party, the same three ASI plans applied to both ASIs, top 5 by the screen rated). The search leaves 5–15 distinct alternatives per class, since several plans give the same sheet once the primary reaches 20.
  - Every candidate on the fighter, cleric and rogue is within noise of the standard build: -2% to +1% overall, and within ±7% on every opponent type.
  - The wizard's best is 14 Con, 13 Dex with the first ASI on Con (+3%, at the noise threshold; +9% against brutes and +8% against casters, both within type noise). It trades reaching Int 20 one ASI later for +1 Con modifier (HP and concentration saves).
  - The split plan that led at level 5 (via the control crossing) is no better at level 10: within ±1% wherever it was rated.
  - So the level 5 conclusion holds at level 10: the standard array and putting ASIs in the primary are as good as any legal alternative, with at most a few percent for a Con-first caster.
- **Cover and ranged attacks in melee (2026-11-02)** (`DayOptions.cover`, `--cover` on `engine.rating` and `engine.compare`; off by default, so every published rating is unchanged). With no grid, cover follows the rows: a back-row PC behind a standing, not-incapacitated front-row ally has half cover (+2 AC) against ranged attacks. A ranged attacker has disadvantage while an enemy with a melee attack is engaged with it: a monster that made a melee attack against it this turn cycle, or any such enemy for a front-row PC. Sharpshooter ignores both for weapon attacks; spell attacks still suffer them. A PC whose first weapon is ranged and would have disadvantage switches to its first melee weapon, and the AI's value estimate squares the hit chance for disadvantage. Monsters have no rows, so they never get cover, and long range, three-quarters cover and cover on Dex saves are not modelled. Tests in `tests/test_cover.py`.
  - The standard party at level 5 rates 3,517 XP with the rules on and 3,512 off. The level 5 ranged ladder (manticores) attacks with melee Rend, so little changes; brutes and control move by under 2%.
  - Sharpshooter under these rules (`compare_L{5,10}_{rogue,ranger}_sharpshooter_cover.md`): the rogue with Sharpshooter is 1% below the same archer without it at both levels; on the ranger it is +0% at level 5 and +1% at level 10. Everything is within noise. The feat's cover half does nothing for PCs, since monsters have no cover, and its melee half rarely matters, because back-row archers are seldom engaged and front-row ones switch to melee weapons. The fighter was not rated: the standard fighter has 12 Dex and cannot take the feat (it needs Dex 13).
- **Monster rows under the cover rules (2026-11-04)**, written by Codex (gpt-6-astra) from a brief and reviewed here. With `DayOptions.cover` on, monsters also get rows: a monster without an explicit `position` stands in front if its first attack is melee and at the back otherwise. A back-row monster behind a standing front-row ally has half cover, as PCs do. A front-row combatant on either side counts as in melee only while a front-row enemy with a melee attack is standing. Party melee attackers are screened to front-row monsters by the same `screen` rule that applies to monsters. Off by default; the standard level 5 party still rates exactly 3,511.9 XP with it off. Tests in `tests/test_cover.py`.
  - Every benchmark encounter has a single monster type, so a whole group stands in one row and monster cover never triggers there. Sharpshooter, rerated with monster rows (`compare_L{5,10}_{rogue,ranger}_sharpshooter_cover.md`), is still within noise: -1% on the rogue against the plain archer at both levels, +0% on the ranger.
  - The rows do change one thing: front-row monsters are now in melee, so their ranged attacks have disadvantage. Barbed devils (Claws first, so front row) stop using Hurl Flame and use their melee multiattack. Against six devils at level 10 (40 runs), the standard party's defeat rate goes from 0% (2,530 ranged attacks, none in melee) to 57% (3,704 melee, 306 ranged). The level 10 ranged rating falls 27% (11,335 to 8,259 XP) and the party's overall rating 5% (9,113 to 8,645 XP); the other types are unchanged. So under the default rules the devils' targeting (the threat target first, then the best routine against it) keeps them throwing flame at the back row, and the level 10 ranged ladder understates them. That is an AI question, separate from cover.
- **Ability scores and ASIs on the other eight classes (2026-11-04)** (`compare_L{5,10}_{barbarian,paladin,monk,ranger,warlock,bard,druid,sorcerer}_abilities.md`, standard party, top 5 by the screen rated). The reports give values against the reference member the class replaces; the gains below are against the class's own standard build:
  - Level 5: no alternative beats the standard build by more than 2% on any class. The standard array is best or tied on the monk, warlock, bard and sorcerer; the barbarian, ranger and druid gain 1% and the paladin 2%, all within noise.
  - Level 10: the best alternative is 1–3% above standard on six classes and tied on the ranger and sorcerer. The barbarian gains most (+3%, at the noise threshold, with 14 Dex/13 Con and the split plan or 14 Con/13 Dex with Con first). The monk, warlock and paladin gain 2%, all with 14 Con; the monk's 14 Con is +8% against brutes over its standard build.
  - Across all twelve classes and both levels, the standard array with ASIs into the primary is within 3% of the best legal alternative. Where an alternative leads at level 10, it moves the 14 to Con.
- **Not yet done:**
  - The optimized and casual reference parties for every class.
  - Range bands (long range), and a benchmark with mixed monster groups so monster cover is exercised.

- **Build value** = the change in party outcomes (wipe chance, someone going down, resources spent) when the build replaces a reference member, measured across the benchmark set. This values healers and controllers by their effect on the party, not by their damage per round.
- Report the result as a grid: build × opponent type × party composition.
- Search: limit the build space to a few decision points (subclass, feats, spell picks), screen with a quick expected-damage score, and run the full simulation only on the finalists.

## Levels 11–20 (2026-11-01)

- **Classes:** all twelve class tables run to level 20 and are checked against the XPHB tables; every level 11–20 feature is implemented, a builder choice, or a documented omission (`data/handwritten/CLASS_FORMAT.md`, "Levels 11–20"). The level 19 Epic Boon is an extra ASI (Boon of Fortitude is the one boon modeled). Presets exist at 11/13/15/17/20 for every class and profile.
- **Spells:** 28 level 6–9 combat spells (`engine/spell_high.py`), source-checked like the rest. Omitted on purpose: Wish, Time Stop, True Polymorph, Shapechange, Simulacrum, Imprisonment, Contingency, Heroes' Feast, Prismatic Spray, Eyebite and the walls. New engine primitives: `kill` (Power Word Kill, Divine Word), full healing (Power Word Heal), and an uncapped healing pool (Mass Heal).
- **Monsters:** 21 high-CR XMM monsters (`engine/monster_high.py`): tyrannosaurus, clay golem, roc, purple worm, stone/frost/fire giants, horned devil, archmage, archpriest, mind flayer, vampire, adult white/black/green/blue and ancient white/black/green/blue/red dragons. All pass the source check.
- **Fix that changes old results:** the adult red dragon's Commanding Presence legendary action lacked its once-per-round limit, so it cast Command about twice a round. Rerunning the three level 10 preset ratings changes nothing that matters (0.73×, 0.59× and 0.76× as before, within 0.1% in XP): their solo crossing comes before the adult red dragon step.
- **Benchmark v2** (`data/benchmarks/benchmark_v2.yaml`): v1's levels 1–10 unchanged, plus levels 11–20 frozen by the same rules with the new monsters added to the rosters. Ratings use v1 up to level 10 and v2 above.
- **Standard party ratings** (Fighter/Cleric/Rogue/Wizard, `data/reports/rating_preset_L{11,13,15,17,20}.md`, 4–6 minutes each):

  | Level | Overall | Lowest type | Highest type |
  | ---: | ---: | --- | --- |
  | 11 | 0.62× | solo 0.43× | ranged 0.83× |
  | 13 | 0.72× | brute 0.57× | ranged 1.00× |
  | 15 | 0.59× | brute 0.44× | ranged 0.78× |
  | 17 | 0.62× | control 0.50× | swarm 0.75× |
  | 20 | 0.50× | caster 0.40× | solo 0.59× |

  - The party reaches 5% defeat at about 0.5–0.7× DMG High, below the 0.73–0.80× of levels 1–10. The builder gives no magic items (the DMG builds encounters without assuming any, p. 218, but a typical campaign hands out about 75 by level 17; see "Magic items" below), and tier 4 monsters (legendary resistance and actions, breath recharge) hit harder than the PCs' new features add.
  - Single-type values rest on one roster monster per level (e.g. tyrannosaurus brutes at 13–15), so they are weaker evidence than the overall value.
- **Calibration sweep at 11–20** (2026-11-01): `python -m engine.calibration --high --runs 100 --write` → `data/reports/calibration_dmg_area_party_spread_grab_half_high.md` (engine defaults, same party and rules as the level 1–10 baseline, about 25 minutes). No engine errors. Median per slot:

  | Level | Low defeat | Moderate: any down / defeat | High: any down / any death / defeat |
  | ---: | ---: | ---: | ---: |
  | 10 (baseline, rerun 2026-11-02) | 0% | 56% / 0% | 82% / 6% / 6% |
  | 11 | 0% | 23% / 0% | 80% / 17% / 16% |
  | 13 | 0% | 31% / 0% | 84% / 29% / 24% |
  | 15 | 0% | 50% / 6% | 100% / 34% / 26% |
  | 17 | 0% | 41% / 0% | 85% / 35% / 34% |
  | 20 | 0% | 81% / 15% | 100% / 100% / 100% |

  - Median TPK never falls from Low to Moderate to High to Over at any level, so the shape holds. Low is easy and Moderate stays survivable through level 17, as the DMG describes.
  - High gets steadily deadlier with level: median defeat climbs from 16% at 11 to 34% at 17, against 0–10% at levels 1–10 (0–18% before the 2026-11-02 baseline rerun). This agrees with the ratings falling to 0.5–0.7×.
  - **Level 20 breaks.** The High budget nearly doubles from 17 to 20 (11,700 → 22,000 XP per PC), and every High group (8 adult white dragons, 7 adult black, 5 adult blue, 6 purple worms, 3 ancient white, 2 ancient green) wipes the party, mostly in rounds 1–3 from stacked breath weapons. Moderate is already 15% defeat. This is rules-legal (the 2024 DMG has no group multiplier), but the 4 PCs have no magic items, Wish or other omitted spells.
  - Low–High outliers (defeat ≥ 50%): aboleths at every level (domination, as at level 10), mage ×7 at 11 High (94%), tyrannosaurus ×8 at 15 High (100%), horned devil ×6–7 at 17 High and 20 Moderate, mind flayer ×7 at 13 High, and the six level 20 High groups.
- **Casual and optimized ratings at 11–20** (2026-11-01, `data/reports/rating_preset_L{11,13,15,17,20}_{casual,optimized}.md`, × DMG High):

  | Level | Casual | Standard | Optimized |
  | ---: | ---: | ---: | ---: |
  | 10 | 0.59× | 0.73× | 0.76× |
  | 11 | 0.47× | 0.62× | 0.69× |
  | 13 | 0.52× | 0.72× | 0.74× |
  | 15 | 0.47× | 0.59× | 0.59× |
  | 17 | 0.47× | 0.62× | 0.60× |
  | 20 | 0.40× | 0.50× | 0.48× |

  - Casual stays about 0.75–0.8× standard, as at levels 1–10.
  - Optimized converges on standard from level 15: by then both max the primary and Con (20/20 for the fighter, cleric and rogue at 17), use the same weapons, and share most spells. What is left is the dump stat; the optimized fighter's Wis 10 against standard's 13 matters against mind flayers and aboleths. The 2–4% gaps below standard are within the noise of a single-seed rating.
  - So the builder's profiles no longer spread parties apart at tier 3–4. A real optimized table differs there through magic items, feats beyond ASIs and multiclassing, which the builder does not model (magic items are now an option; see below).
- **Fix:** a blinded caster tried to Healing Word itself and crashed the run (Healing Word needs a target the caster can see; the rogue's level 14 Obscure strike blinds). It now falls back to Cure Wounds. Level 1–10 results are unchanged, since the old path always raised.
- **Class comparisons at 15 and 20** (2026-11-01, `data/reports/compare_L{15,20}_{class}_class.md`): each of the other eight classes' standard build in its role slot of the standard party, as in Phase 5. Change in overall rating against the reference member, levels 5 and 10 from Phase 5 for comparison:

  | Class (slot) | L5 | L10 | L15 | L20 |
  | --- | ---: | ---: | ---: | ---: |
  | Monk (rogue) | +8% | +5% | +10% | +16% |
  | Sorcerer (wizard) | +11% | +12% | +10% | +3% ≈ |
  | Warlock (wizard) | -23% | +4% | -1% ≈ | -11% |
  | Barbarian (fighter) | +3% | -5% | -5% | -8% |
  | Bard (cleric) | +2% ≈ | -10% | -10% | -15% |
  | Druid (cleric) | -5% | -11% | -20% | -17% |
  | Paladin (fighter) | -2% ≈ | -5% | -17% | -19% |
  | Ranger (fighter) | -8% | -12% | -27% | -38% |

  - The monk is the only class that gains on its reference at every level, and its lead grows: at level 20 it is +19% to +27% against brutes, ranged and casters. The sorcerer stays ahead of the wizard but its lead shrinks to noise at 20.
  - The fighter's replacements fall further behind with level. At 20 the paladin is -55% against control and -35% against solo, and the barbarian -34% and -32%; the losses are concentrated against the control (chain devil) and solo (dragon) ladders, not yet traced to a cause. The ranger is below the fighter against every type at 20 (-18% to -61%).
  - Neither cleric replacement holds up past level 5: the bard loses most against control (-34% at 20); the druid loses 31% against ranged and control at 15 and 31% against solo at 20.
  - The warlock swings with the opponent type (at 15, +32% against casters but -30% against control), so its overall value is less stable than the others'.
  - As at level 5–10, these are the builder's standard builds without magic items; per-type values rest on one roster monster per level.
- **Fix:** each druid turn reloaded and re-validated four beast sheets (and through them every spell file) to choose a Wild Shape form. Monster sheets are now parsed once per process (`loader.monster_sheet`). The level 15 druid comparison crashed twice with a Windows access violation inside that file I/O; with the cache it completes. Results are unchanged (same random stream).

## Magic items (2026-11-01)

- **Catalog** (`engine/items.py`): 31 combat XDMG items that are plain stat changes, each checked against the 5etools XDMG data (rarity, attunement, weapon/AC/save/spell bonuses, set scores, rules text). Included:
  - +1 to +3 weapons, armor and shields;
  - Cloak and Ring of Protection, Stone of Good Luck, Ioun Stones of Protection and Mastery, Bracers of Defense;
  - Gauntlets of Ogre Power, Headband of Intellect, Amulet of Health, the five Giant Strength belts;
  - Wand of the War Mage and Rod of the Pact Keeper (+1 to +3), Staff of Power, Robe of the Archmagi.
  - Not modeled: charges and spells cast from items, consumables (potions, scrolls), and items with bespoke rules (Cloak of Displacement, Mantle of Spell Resistance, Armor of Invulnerability, and the like).
- **Builder:** `choices.items` lists a build's items. The builder rejects two items in one slot, more than 3 attuned items, wrong attunement (Robe and Staff are sorcerer/warlock/wizard only), and items that need armor, a Shield or no armor.
  - Weapon bonuses go to the first weapon and make it magical.
  - Armor and shield bonuses and the Robe's base AC change the sheet's AC.
  - Other AC bonuses and save bonuses are new `item_ac_bonus` / `item_save_bonus` features, so they stack with Mage Armor.
  - Ioun Stone of Mastery raises the Proficiency Bonus. Uses already fixed by the class table do not change.
  - Saves now go through `Combatant.save_bonus()`. Item-free results are bit-identical (full suite passes).
- **Kits:** `--items half|full` on `engine.rating` gives each PC a kit sized from the 2024 DMG "Magic Items Awarded by Level" table (p. 218).
  - A party reaching level L has the items of levels 1 to L−1, spread evenly within each tier. Commons are skipped.
  - `half` assumes half of the uncommon-and-better items are combat items this party keeps; `full` keeps them all.
  - Following the DMG's "Player Wish List", the rarest items are placed first, handed round the party, each PC taking the best item of that rarity on its class wish list.
  - The DMG itself says encounters are built *without* assuming magic items, so these ratings measure a typically equipped party against budgets that assume none.
- **Standard party with items** (`data/reports/rating_preset_L*_items_{half,full}.md`, × DMG High):

  | Level | No items | Half kit | Full kit |
  | ---: | ---: | ---: | ---: |
  | 10 | 0.73× | 0.83× | 0.84× |
  | 11 | 0.62× | 0.76× | 0.82× |
  | 13 | 0.72× | 0.84× | 0.91× |
  | 15 | 0.59× | 0.77× | 0.85× |
  | 17 | 0.62× | 0.79× | 0.82× |
  | 20 | 0.50× | 0.68× | 0.68× |

  - Items add about 15–30%, more at higher levels. With the half kit, levels 10–17 rate 0.76–0.84×, level with the item-free 0.73–0.80× of levels 1–10. The tier 3 drop was mostly missing items.
  - Level 20 stays low (0.68×). Its solo ladder tops out before the party reaches 5% defeat, so the overall value is a lower bound. Half and full rate the same at 20 (every type within 2%). Attunement and item slots are already full there, so the full share only upgrades a few items (+3 instead of +2 Armor on the fighter, Ioun Stones of Mastery on the cleric, rogue and wizard), which barely changes the party.
  - At 10 and 17 the full kit adds little over half for the same reason. Wish-list slots, not the DMG count, become the limit.
- **Calibration sweep with items** (2026-11-02): `python -m engine.calibration [--high] --runs 100 --items half|full --write` → `data/reports/calibration_dmg_area_party_spread_grab_half_items_{half,full}[_high].md`. Each report lists the kit per level. No engine errors. Median defeat per slot, no items / half kit / full kit:

  | Level | Moderate | High | Over (1.5× High) |
  | ---: | --- | --- | --- |
  | 1 | 8% / 8% / 8% | 10% / 10% / 10% | 22% / 22% / 22% |
  | 3 | 0% / 0% / 0% | 4% / 3% / 2% | 25% / 22% / 21% |
  | 5 | 0% / 0% / 0% | 7% / 4% / 2% | 22% / 20% / 15% |
  | 7 | 0% / 0% / 0% | 0% / 0% / 0% | 22% / 19% / 12% |
  | 10 | 0% / 0% / 0% | 6% / 1% / 0% | 72% / 36% / 33% |
  | 11 | 0% / 0% / 0% | 16% / 3% / 2% | 62% / 40% / 33% |
  | 13 | 0% / 0% / 0% | 24% / 3% / 1% | 58% / 27% / 14% |
  | 15 | 6% / 0% / 0% | 26% / 7% / 0% | 96% / 72% / 49% |
  | 17 | 0% / 0% / 0% | 34% / 2% / 2% | 100% / 90% / 85% |
  | 20 | 15% / 0% / 0% | 100% / 68% / 74% | 100% / 100% / 100% |

  - Low stays at 0% defeat everywhere. Level 1 has no kit (nothing is awarded before level 2), so its rows match.
  - Items matter little at levels 1–7, where kits are one to four uncommon items, and a lot from level 10: median High defeat at 11–17 falls from 16–34% to 0–7%, the same range as levels 1–10 without items. Moderate never defeats a kitted party below level 20. With DMG-sized items, High is again "hard but survivable" through level 17. The rising High lethality of the item-free sweep was the missing items.
  - Someone still goes down in most High fights with items (median 59–94% at 11–17, against 80–100% without).
  - Level 20 still breaks. High is 68–74% defeat even with the full kit (the half/full gap is within noise: 6 groups of 100 runs), from the same stacked breath weapons. Moderate drops from 15% to 0%.
  - Outliers that survive the items (defeat ≥ 50% at Low–High): mage ×7 at 11 High (75%), aboleths at 13–20, tyrannosaurus ×8 at 15 High (100%), and five of the six level 20 High groups. Kits add AC, saves and damage, not the counters these need (aboleth domination, eight T-rexes' single-target damage).
- **Baseline rerun** (2026-11-02): the level 1–10 sweep was last written on 2026-10-24, and later engine fixes shift some cells (median level 5 High defeat 18% → 7%, level 10 Over 98% → 72%). It was rerun with the current engine (`calibration_dmg_area_party_spread_grab_half.md`) so the item sweeps compare against the same engine; the "no items" column above is the rerun.

## Later

- ~~Levels 11–20.~~ Done 2026-11-01 (see "Levels 11–20" below). Calibration sweep done 2026-11-01. Casual/optimized ratings done 2026-11-01. Magic items done 2026-11-01 (see "Magic items" below). Class comparisons at 15 and 20 done 2026-11-01. Items in calibration done 2026-11-02.
- More classes: all twelve 2024 classes are done at levels 1–20.
- ~~A command line for DMs: give it a party and an encounter, get back win rate, wipe chance and resources spent.~~ Done 2026-10-31: `python -m engine.dm fight|day|monsters` (`engine/dm.py`). `fight` runs adaptively (100–800 runs) and reports win, defeat, TPK, someone down and someone dead with 95% margins, the encounter's XP as a multiple of this party's DMG High budget, and each PC's chance to drop or die, HP left and mean resources spent. `day` takes a day file or inline `--steps` and adds, per encounter, how often it is reached and cleared. `monsters` lists usable monsters by CR. The shared runners gained an optional `detail` output; their metrics are unchanged.
- Repo housekeeping: done 2026-10-26. `readme.md` has working usage examples; the 5etools zip, `raw_data/` and the retired `spellsim/` + `ai_extractors/` pipeline are ignored and kept locally.
