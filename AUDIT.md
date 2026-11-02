# Audit and plan (2026-11-02)

A self-audit of the three user-facing tools: combat simulation (`engine/combat.py`, `engine/policy.py`), build comparison or min-maxing (`engine/compare.py`), and encounter design for DMs (`engine/dm.py`, `engine/templates.py`, `engine/finder.py`). Each finding says how it was checked. "Reproduced" means it was run in a fresh cloud clone on this date.

## 0. Blocker: a fresh clone cannot run

- **Reproduced.** `python -m engine.dm fight ...` fails at once with `No such file or directory: raw_data/class/class-fighter.json`. The test suite fails at collection on `raw_data/spell/spells-xphb.json`.
- `raw_data/` and `5etools-v2.30.1.zip` are gitignored, but they are read at **runtime**, not only by the source-check tests:
  - the builder reads class JSON for invocation counts, skill lists and subclass prepared spells (`builder.py:370,414,446`);
  - summon spells read the bestiaries (`spell_more_summons.py`, `spell_wiring.py`).
- `pytest` is not a declared dependency.
- **Reproduced:** `test_step3_golden_bytes` hashes the raw bytes of 20 spell files. 19 of the 20 digests only match with Windows CRLF line endings, so the test fails on any Linux or macOS checkout.
- Workaround used for this audit: download the pinned v2.30.1 files from the 5etools mirror into `raw_data/`.

**Plan**
1. Add `python -m engine.fetch_source` to download the pinned v2.30.1 files into `raw_data/` (class, spells, bestiary, and the book/items files the tests read), with a SHA-256 check.
2. Make the runtime path work without the raw files: cache the few facts the builder and summons need in a small committed JSON file generated from the source, and keep the source cross-checks in tests only. Tests that need the raw files skip with a message saying to run the fetch step.
3. Add `[project.optional-dependencies] dev = ["pytest"]`.
4. Hash spell files with line endings normalized to LF (or add a `.gitattributes` pinning `eol`), so golden checks pass on every OS.

## 1. Combat simulation

| # | Finding | Evidence | Effect |
| --- | --- | --- | --- |
| C1 | The AI's damage estimates ignore resistance, immunity and vulnerability. | **Reproduced:** the L5 wizard with a fighter against 2 fire elementals (fire immune) cast **Fireball 22 times in 100 fights**. `expected_spell_damage`/`expected_weapon_damage` only check condition immunities. | Slots wasted against elementals, devils, undead, dragons; also why no AI deliberately picks fire against a troll (ROADMAP, Warlock). Distorts every comparison involving those monsters. |
| C2 | No overkill cap: expected damage is counted in full against a target with fewer HP left. | Code (`combat.py:1695-1710`). **Reproduced side effect:** in a 0.25× High fight (2 ogres, 4 goblins) the wizard spent 1.78 L3 slots and the cleric 2.6 slots. | Default strategy overspends; DM resource readouts overstate the cost of easy fights. |
| C3 | Spells and actions are valued against `enemies[0]`, not against the target that will be chosen. | Code (`policy.py` `take_turn`). | Wrong choice when the first enemy is a minion and the threat is a boss, or the reverse. |
| C4 | Buff valuation (`values_buffs`) is switched off for the cleric and wizard "to preserve published baselines". | Code comment in `policy.py`. | Bless, Haste and similar are undervalued on the **reference party**, which is the yardstick for every build comparison, so paladin/bard/druid results are measured against a handicapped cleric. |
| C5 | The turn logic is a one-turn greedy script with hard-coded spell names (Healing Word, Cure Wounds, Revivify, Hex, Hunter's Mark, Preserve Life). | Code. | New spells and classes need code changes; healing thresholds (below half HP) are fixed. |
| C6 | No positions: everyone is engaged from round 1; cover is optional and row-based; no range, movement, flying or kiting. | Documented (REVIEW_NOTES, CLASS_FORMAT). | Sharpshooter, ranged kits, Polearm Master reach, flyers and terrain can't be valued properly. |

**Plan**
1. C1 + C2: one damage-value helper applying resistance/immunity/vulnerability and `min(expected, target HP left)` (with a small credit for a kill). Use it in spell, weapon, action and routine valuation.
2. C3: value each option against the target its own targeting would pick.
3. C4: turn on `values_buffs` for every class, then **rerun the baselines once**: calibration, preset ratings, compare reports. Stop preserving the old blind spot.
4. Regression tests for C1-C3 (e.g. no Fireball into all-fire-immune groups; no level 3 slot into a group the cantrips already kill).
5. Later (larger): a light range-band model (melee / near / far) to replace the "all engaged" assumption, so that cover, reach and ranged builds matter without a full grid.

## 2. Min-max (build comparison)

| # | Finding | Evidence |
| --- | --- | --- |
| M1 | Slow: one comparison of 2 fighter builds at L5 took **7.5 min** on 4 cores (21 CPU-min). A `--variants` or `--feats` grid is an hour or more. | Reproduced. |
| M2 | Results sit in the noise: most feat and ability findings are within the fixed 3% / 10% noise bars, and the level 5 **control crossing swings +11-14% for almost any change** (again here: `fighter_5_optimized` +3% overall, +14% of that against control). | Reproduced + ROADMAP. |
| M3 | "Optimized" isn't a real min-maxer: no species, no multiclassing, a handful of feats, no Fighting Style beyond the kit list. Optimized is only 3-12% above standard and converges by level 15. | ROADMAP Phase 3, levels 11-20. |
| M4 | Every value is "swap one member into the F/C/R/W reference party". There is no answer to "best build for *my* party" or "best class in this slot", and casual/optimized references are missing for most classes. | `compare.py` CLI. |
| M5 | Depends on C1-C4: an AI that wastes slots or ignores buffs undervalues casters and buffers. | — |

**Plan**
1. Fix C1-C4 first; the comparisons are only as good as the AI.
2. Replace the fixed noise bars with a measured interval: rate finalists on 3 seeds (common random numbers within each seed) and report mean ± spread. Flag single-type values whose crossing moves between seeds instead of trusting one crossing.
3. Speed: a quick-screen mode that uses a fixed short ladder around the expected crossing (bracket from the reference rating) instead of the full ladder, and cache reference-party ratings per seed.
4. `compare --party <your builds> --slot N`: swap candidates into any party, not only the reference one.
5. Widen the build space in this order: species (2024 PHB origin traits that matter in combat), the remaining combat feats (e.g. Crossbow Expert, Shield Master, Mage Slayer, Sentinel once C6 bands exist), then simple multiclass dips (Fighter 1-2, Warlock 2, Sorcerer 1).

## 3. DM combat design

| # | Finding | Evidence |
| --- | --- | --- |
| D1 | `dm fight --level 4` (and 2, 6, 8, 9, 12, 14, 16, 18, 19) **crashes** with a raw `FileNotFoundError`. The CLI offers 1-20, but builds exist only for 1/3/5/7/10/11/13/15/17/20. | Reproduced. |
| D2 | Only 91 of 503 XMM monsters are usable (e.g. `orc` is "unknown monster"). | Reproduced; count from `bestiary-xmm.json`. |
| D3 | Options are inconsistent across tools: `--items` and `--cover` exist on `rating`/`compare` but not on `dm fight/day` or `finder`, so a DM can't model an equipped party. `dm --level` only builds the fighter/cleric/rogue/wizard party. | CLI help. |
| D4 | `dm` defaults to the greedy `default` strategy, so "resources spent" overstates what a sensible party spends (see C2). | Reproduced (1.78 Fireballs on a 0.25× High fight). |
| D5 | Encounter templates have no theme or creature-type filter (only `--exclude`), use one monster type per role, and the finder's XP steps are coarse, so its curve isn't monotone. | `templates.py` CLI; ROADMAP Phase 4. |
| D6 | No surprise, starting distance, terrain or lair actions to design with. | Documented scope. |
| D7 | The XP line gives "0.25× DMG High" but doesn't say when an encounter is below Low or above High. | Reproduced (minor). |

**Plan**
1. D1: generate preset builds for every level 1-20 (the preset rules already exist), or reject missing levels with a clear message. Do the generation.
2. D3: `--items`, `--cover` and a mixed-class `--classes` preset on `dm` and `finder`, sharing one option parser with `rating`.
3. D4: default `dm` to `rationed`, and show `default` alongside when they differ.
4. D2: import monsters in batches by how often DMs use them (CR 0-10 humanoids, beasts, undead, fiends first) through the existing importer and source check. Report which abilities each batch can't model.
5. D5: `--theme undead|fiend|humanoid|...` and mixed-type roles in templates; finder XP steps that can add or remove one minion.
6. D7: name the DMG band next to the multiple.
7. D6 waits on the range-band model (C plan 5): surprise and starting distance come almost free once bands exist.

## Proposed order

1. **Unblock** (section 0). Small, needed for any cloud work.
2. **AI correctness**: C1, C2, C3 with regression tests, then C4 with one baseline rerun. Every number downstream depends on these.
3. **DM quick fixes**: D1, D3, D4, D7.
4. **Min-max trust**: multi-seed intervals (M2), faster screen (M1), `--party/--slot` (M4).
5. **Content breadth**: monsters (D2), species/feats/multiclass (M3), templates (D5).
6. **Positioning**: range bands (C6), then surprise/terrain (D6).

## Test suite

Full suite in the cloud clone (Linux, Python 3.13), with the v2.30.1 `raw_data/` files fetched but without the zip: **2976 passed, 3 failed, 32 errors** in 9 min 20 s.

- 34 of the 35 failures and errors are the missing `5etools-v2.30.1.zip` (the item checks and the step 4 source checks read the XDMG and book data from it).
- The other is `test_step3_golden_bytes`, the CRLF line-ending issue above.
- No engine failures.
