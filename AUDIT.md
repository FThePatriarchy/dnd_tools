# Audit and plan (2026-11-02)

A self-audit of the three user-facing tools: combat simulation (`engine/combat.py`, `engine/policy.py`), build comparison or min-maxing (`engine/compare.py`), and encounter design for DMs (`engine/dm.py`, `engine/templates.py`, `engine/finder.py`). Each finding says how it was checked. "Reproduced" means it was run in a fresh cloud clone on this date.

## 0. Blocker: a fresh clone cannot run

- **Reproduced.** `python -m engine.dm fight ...` fails at once with `No such file or directory: raw_data/class/class-fighter.json`. The test suite fails at collection on `raw_data/spell/spells-xphb.json`.
- The engine simulates from `data/handwritten/` only, but `raw_data/` (gitignored) was still opened while loading:
  - every class load ran the XPHB source cross-check (`load_class` defaulted to `source_check=True`);
  - the builder read three facts from the raw class JSON: the warlock's invocation count, each class's skill choices and the subclass's always-prepared spells (`builder.py:370,414,446`).
  - (Correction: the summon modules that read the bestiaries, `spell_more_summons.py` and `spell_wiring.py`, are generators; summon forms are already in the spell YAML.)
- `pytest` is not a declared dependency.
- **Reproduced:** `test_step3_golden_bytes` hashes the raw bytes of 20 spell files. 19 of the 20 digests only match with Windows CRLF line endings, so the test fails on any Linux or macOS checkout.
- Workaround used for this audit: download the pinned v2.30.1 files from the 5etools mirror into `raw_data/`.

**Done (2026-11-02)**
1. `load_class` no longer cross-checks by default; `tests/test_class_facts.py` runs the check for all twelve classes.
2. The three builder facts are in the committed `data/handwritten/class_facts.json` (`python -m engine.class_facts --write`); a test checks it against the source. A test also blocks any read of `raw_data/` while building every class and running a fight, and the DM tool was run with `raw_data/` removed.
3. `python -m engine.source_files --fetch` downloads the pinned v2.30.1 files the cross-check tests need (the zip's four files go to `raw_data/archive/`, read when the zip is absent).
4. `pytest` is a `dev` extra in `pyproject.toml`.
5. Golden spell hashes are of LF-normalized content.

## 1. Combat simulation

| # | Finding | Evidence | Effect |
| --- | --- | --- | --- |
| C1 | The AI's damage estimates ignore resistance, immunity and vulnerability. | **Reproduced:** the L5 wizard with a fighter against 2 fire elementals (fire immune) cast **Fireball 22 times in 100 fights**. `expected_spell_damage`/`expected_weapon_damage` only check condition immunities. | Slots wasted against elementals, devils, undead, dragons; also why no AI deliberately picks fire against a troll (ROADMAP, Warlock). Distorts every comparison involving those monsters. |
| C2 | No overkill cap: expected damage is counted in full against a target with fewer HP left. | Code (`combat.py:1695-1710`). **Reproduced side effect:** in a 0.25× High fight (2 ogres, 4 goblins) the wizard spent 1.78 L3 slots and the cleric 2.6 slots. | Default strategy overspends; DM resource readouts overstate the cost of easy fights. |
| C3 | Spells and actions are valued against `enemies[0]`, not against the target that will be chosen. | Code (`policy.py` `take_turn`). | Wrong choice when the first enemy is a minion and the threat is a boss, or the reverse. |
| C4 | Buff valuation (`values_buffs`) is switched off for the cleric and wizard "to preserve published baselines". | Code comment in `policy.py`. | Bless, Haste and similar are undervalued on the **reference party**, which is the yardstick for every build comparison, so paladin/bard/druid results are measured against a handicapped cleric. |
| C5 | The turn logic is a one-turn greedy script with hard-coded spell names (Healing Word, Cure Wounds, Revivify, Hex, Hunter's Mark, Preserve Life). | Code. | New spells and classes need code changes; healing thresholds (below half HP) are fixed. |
| C6 | No positions: everyone is engaged from round 1; cover is optional and row-based; no range, movement, flying or kiting. | Documented (REVIEW_NOTES, CLASS_FORMAT). | Sharpshooter, ranged kits, Polearm Master reach, flyers and terrain can't be valued properly. |

**Done (2026-11-02):** C1, C2 and C3 (steps 1, 2 and 4 below). `Combat.damage_factor` mirrors `mitigate_damage`; spell and weapon estimates use it; leveled spells are valued with each victim's damage capped at its HP; the party values its weapon against the creature it would attack. Regression tests: `tests/test_ai_valuation.py` (the wizard casts no Fireball at fire elementals in 30 fights, where it cast 22 in 100 before). Three pinned baselines moved and were re-pinned: fighter + cleric against 4 goblin warriors now spend 0.81 3rd-level slots per fight instead of 1.06; on the goblin warren day the nova strategy survives 152 of 1,000 days instead of 127 (conservative 163 vs 162). The weapon estimate is not capped, because extra attacks move to the next creature. **The published reports in `data/reports/` predate this change** and are not rerun yet.

**Done (2026-11-02): C4.** Every class now values buffs (`values_buffs`), the reference cleric and wizard included. The buff valuation also learned Haste: one extra weapon attack per round while the spell lasts, minus the target's lost turn (lethargy) weighted by the chance that concentration breaks before the fight ends (`concentration_keep`). Before this, Haste counted only its +2 AC, and the reference cleric and wizard never cast a buff. In 200 L5 fights against three ogres the cleric now casts Aid 85 times, mostly in place of Guiding Bolt. Bless still loses to Spirit Guardians (both need concentration), and Haste stays below Fireball in short fights.

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

**Why the comparisons were noisy (found 2026-11-02).** The full rating stops sampling a step as soon as its interval clears 5%. So each type's crossing is usually interpolated between a 0% step and the next step measured on just 50-150 runs. In the stored L5 fighter base: swarm goes from bugbear ×12 at 0% to ×16 at 36% (50 runs), control from basilisk ×4 at 0% to ×5 at 9% (150 runs), solo from young blue at 0% to young red at 24% (50 runs). That one under-sampled point sets the crossing, which is the "control swings 10-14%" effect.

**Done (2026-11-02): focused comparison** (`engine/focused.py`, now the default for `python -m engine.compare`).
- The base party is rated once to find each type's bracket (the steps that decide its crossing).
- The base and every candidate are then run on those steps with the same `--runs` per step (default 400) and the same batch seeds.
- A candidate's bracket widens one step at a time when its crossing falls outside it.
- Each change is reported with a paired bootstrap 95% interval over batches; ≈ now means "the interval contains zero" instead of fixed 3%/10% bars.
- The variant screen is now a short focused run (`--screen sim`, 100 runs per step). The old expected-damage screen couldn't separate spell profiles; it stays as `--screen ev`.
- `--party ... --replace NAME` compares builds in your own party.
- `--method full` reproduces the published method.

**Done (2026-11-02): build search** (`python -m engine.optimize --party ... --member NAME`). It hill-climbs one member's build in your party: each round it screens every one-change neighbour (kits, spell lists, feats, ability/ASI plans, species), measures the leaders with focused paired runs, and accepts the best change only when its 95% interval is above zero. A change that rewrites an accepted change's fields replaces it, and builds already visited are skipped, so the search cannot cycle.

**Done (2026-11-02): M3, species.** The builder takes `choices.species` for Dwarf, Gnome, Halfling, Human (a second Origin feat), Orc, Tiefling (resistance), Dragonborn (resistance and Breath Weapon) and Goliath (Stone or Fire ancestry); see `CLASS_FORMAT.md`, "Species". `compare --species` rates each one, and `optimize` searches them.

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

**Done (2026-11-02): D5 (themes) and D7.** `--theme TYPE…` on `engine.templates` and `engine.finder` keeps only monsters of those creature types (for example `--theme undead`), and `dm` names the DMG band next to the XP multiple, using the repo's convention: the smallest budget that fits, with below Low counted as Low.

**Done (2026-11-02): D2, first batch.** `engine/monster_more.py` adds 63 XMM monsters (154 in all): 40 that the importer reads fully, and 23 whose on-hit riders (Prone, Grappled, Poisoned, Frightened, Disadvantage) are reviewed decisions. Reviewing the batch exposed that the importer keeps only a save action's damage and target. Conditions on a failed save were dropped, a point-centred sphere (Spore Bomb) was parsed as a single target, and Trample was legal against creatures that weren't prone. Every save action in the batch is now reviewed, and unmodeled effects are listed in `unsupported`. Charge riders ("moved 20+ feet straight") need a grid and are noted, like the dragons' Pounce. Cockatrice, Death Dog, Stirge and Rug of Smothering need bespoke rules and are left for later. The calibration sweeps keep their original 91-monster roster (`calibration_roster`), so the new monsters feed the DM tools and templates without changing the sweeps.

**Done (2026-11-02):** D1 (`dm`/`finder --level` only offer levels that have preset builds, instead of crashing) and D3 for `dm` (`--items half|full` on `fight` and `day`, `--cover` on `fight`).

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
