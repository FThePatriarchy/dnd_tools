# Roadmap

## Goals

1. **Sample parties and opponents** for each level.
2. **Build comparison (min-maxing)** at a given level.
3. **Encounter building** for a specific party.
4. **Adventuring-day building** — encounters plus short and long rests.

## Guiding principle: every answer is relative

Party strength varies a lot (an optimized party can be roughly twice as strong as a casual one), opponents vary in shape (one solo boss vs. a swarm), and "best build" depends on role, party and opponent. The tool therefore never reports a universal number such as "this encounter is Hard" or "this build is best". Every answer is stated against a named party and a named set of opponents, and those variables are inputs, not obstacles.

The simulation is the source of truth. Expected-value maths (hit chance × damage) is used only where it is cheap and safe: AI move scoring inside the simulation, quick screening before a full run, and exact single-roll damage distributions.

## Current state (2026-10-23)

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
- **Not yet done:**
  - Searching ability-score and ASI choices.
  - The optimized and casual reference parties for every class.
  - Feats, the lever the Phase 3 presets showed is missing.

- **Build value** = the change in party outcomes (wipe chance, someone going down, resources spent) when the build replaces a reference member, measured across the benchmark set. This values healers and controllers by their effect on the party, not by their damage per round.
- Report the result as a grid: build × opponent type × party composition.
- Search: limit the build space to a few decision points (subclass, feats, spell picks), screen with a quick expected-damage score, and run the full simulation only on the finalists.

## Later

- More classes (Paladin, Warlock, Barbarian, Bard) and levels 11–20, each checked against the calibration report.
- A command line for DMs: give it a party and an encounter, get back win rate, wipe chance and resources spent.
- Repo housekeeping: commit `readme.md` and fix its usage example; ignore the 5etools zip and `raw_data/`; archive the old `spellsim/` + `ai_extractors/` pipeline.
