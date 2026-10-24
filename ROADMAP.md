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
- Decide fight-to-extermination vs. morale/fleeing.
- ~~Fix the Cunning Strike crash and explain the aboleth result.~~ Done 2026-10-24.
  - **Crash:** the rogue hit a dominated ally, which was a legal enemy while charmed. The Sneak Attack damage let the ally make its repeat save, so it broke free and its team flipped back mid-attack. Cunning Strike then re-checked `affects: enemy` against a creature that was now an ally. Cunning Strike now follows the creature that was hit. The sweep has no engine errors left.
  - **Aboleth ×3 (L10 Over):** 97 of 100 fights end with every conscious PC dominated (`party_unavailable`). That is a loss, but not a TPK, because those PCs still have HP. Most killing blows on downed PCs come from Psychic Drain, a legendary action that drains a creature the aboleth has charmed. That includes dominated PCs already at 0 HP. Tentacle attacks on downed PCs come next, once no free PC is left. This is rules-legal behaviour, not an engine bug.
- Count losses where every remaining PC is dominated or otherwise unavailable as defeats in the calibration metrics. TPK alone misses them; the aboleth fights show 0% wins but only 3% TPK.
- Adaptive run counts: run more where an estimate is uncertain or near a threshold that matters, fewer where the answer is 0% or 100%.

**Done when** no single monster type dominates its budget slot, the remaining outliers are understood and justified by the rules, and the median curve is monotone at every level.

## Phase 2 — Benchmark set and party rating

- Freeze a benchmark set of encounters for each level covering opponent types: melee brutes, ranged attackers, casters, swarms, solo legendaries, control monsters.
- **Party rating** = the XP budget at which wipe chance reaches a set threshold (for example 5%), found by search over encounter budget. Report it overall and per opponent type.
- Treat AI skill (default / nova / conservative, plus future strategies) as a setting, so build strength and play strength can be separated.

**Done when** any party gets a rating in minutes, and the ratings are stable across seeds.

## Phase 3 — Sample parties and opponents (Goal 1)

- Party presets per level: casual, standard (today's builds) and optimized, each with its measured rating.
- Encounter templates: solo boss, boss plus minions, elite pack, swarm. The user can also give a shape directly (for example, "1 boss, 6 goons"). A generator fills the template from the budget and the monster catalogue.

## Phase 4 — Encounter and day finder (Goals 3 and 4)

- **Encounter:** the user gives a party, a template and a target risk (for example, "wipe under 2%, someone goes down about half the time"). Search one setting, such as goon count or monster CR, until the simulated result hits the target. The answer then reflects that party's actual strength, not the DMG table.
- **Day:** the user gives a day template (number of encounters, where the rests go) and an end-of-day target (for example, "nobody dies, party ends with 10–20% of slots and hit dice"). Search one difficulty scale factor applied across the day.

## Phase 5 — Build comparison (Goal 2)

- **Build value** = the change in party outcomes (wipe chance, someone going down, resources spent) when the build replaces a reference member, measured across the benchmark set. This values healers and controllers by their effect on the party, not by their damage per round.
- Report the result as a grid: build × opponent type × party composition.
- Search: limit the build space to a few decision points (subclass, feats, spell picks), screen with a quick expected-damage score, and run the full simulation only on the finalists.

## Later

- More classes (Paladin, Warlock, Barbarian, Bard) and levels 11–20, each checked against the calibration report.
- A command line for DMs: give it a party and an encounter, get back win rate, wipe chance and resources spent.
- Repo housekeeping: commit `readme.md` and fix its usage example; ignore the 5etools zip and `raw_data/`; archive the old `spellsim/` + `ai_extractors/` pipeline.
