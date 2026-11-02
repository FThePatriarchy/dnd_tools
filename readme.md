# 🎲 D&D 5.5e Monte Carlo Combat Simulator

![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Status](https://img.shields.io/badge/Status-In%20Development-orange)

A high-performance mathematical combat simulator and state-machine engine designed for Dungeons & Dragons 5.5e. By running thousands of automated battles using Monte Carlo simulations, this tool provides real statistical data on encounter difficulty, resource expenditure, and tactical optimization.

---

## 📖 The Problem & Goal
Dungeon Masters (DMs) frequently struggle to balance combat encounters using the standard Challenge Rating (CR) system, often resulting in accidentally deadly or boringly easy fights. Similarly, theorycrafters rely on "white-room" math to optimize character builds, which fails to account for resource drain over a full "Adventuring Day."

**Our Goal:** Build a pure-function, mathematically rigorous combat engine that accurately predicts encounter difficulty and resource management. 

### Target Audience
* **Dungeon Masters:** Validate homebrew monsters or test if a boss fight will result in a Total Party Kill (TPK).
* **Min-Maxers & Theorycrafters:** Mathematically prove which class build, weapon, or spell is statistically superior over a multi-encounter Adventurers League-style day.

---

## ⚙️ Features & Scope

### In-Scope (Core Mechanics)
* D&D 5.5e core combat mechanics (AC, HP, Initiative, Attack/Damage Rolls, Saving Throws).
* Advantage / Disadvantage system.
* Basic status conditions (Stunned, Poisoned, etc.).
* Damage Resistances and Immunities.
* Action Economy strictness (Actions, Bonus Actions, Reactions).
* Mathematical approximations for Area of Effect (AoE) spells.
* AI Strategy toggles (e.g., "Nova Strategy" vs. "Conservative Resource Strategy").

### Out-of-Scope (Iterative Boundary)
* Roleplay features and out-of-combat utility spells.
* 2D grid/spatial movement (distance and positioning).
* Complex line-of-sight and cover rules.

---

## 🚀 Usage (Command Line Interface)

As a backend-first engine, the primary UI is a Command Line Interface (CLI). 

Run from the repository root. Builds are named after files in `data/handwritten/builds/` and monsters after files in `data/handwritten/monsters/`.

**For DMs: how will my party do against this fight?** Win, defeat, someone down and someone dead (with 95% margins), the encounter's XP against the DMG budget for this party, and each character's chance of dropping plus the resources they spend:
```bash
python -m engine.dm fight --party fighter_5 cleric_5 rogue_5 wizard_5 --monsters "ogre x2" "goblin_warrior x4"
```

**A whole adventuring day** (encounters and rests in order; per-encounter and per-character results):
```bash
python -m engine.dm day --level 5 --steps "ogre x2" short "bandit x6, bandit_captain" long troll
```

**Which monsters can I use?**
```bash
python -m engine.dm monsters --max-cr 3
```

`--level N --profile casual|standard|optimized` picks a preset party instead of `--party`; `--strategy`, `--morale dmg` and `--json` work on both `fight` and `day`.

**One fight, raw summary (the original runner):**
```bash
python -m engine.simulate --party fighter_5 cleric_5 rogue_5 wizard_5 --monsters ogre ogre --runs 1000
```

**Rate a party against the benchmark set:**
```bash
python -m engine.rating --party fighter_5 cleric_5 rogue_5 wizard_5
```

**Find the encounter a party can take (here: half the time someone goes down):**
```bash
python -m engine.finder encounter --level 5 --template elite_pack --target down=0.5
```

**Compare build choices by swapping them into a reference party** (paired runs on the ladder steps that decide the rating, with 95% intervals; `--method full` re-rates each candidate from scratch):
```bash
python -m engine.compare --level 5 --class fighter --variants
```

**...or into your own party:**
```bash
python -m engine.compare --level 5 --class fighter --feats --party fighter_5 paladin_5 bard_5 sorcerer_5 --replace fighter_5
```

**Let it find a better build for one member of your party** (tries kits, spell lists, feats and ability/ASI plans one change at a time, keeping a change only when its 95% interval is above zero):
```bash
python -m engine.optimize --party fighter_5 cleric_5 rogue_5 wizard_5 --member fighter_5 --write my_fighter
```

**Source cross-checks.** The engine runs from `data/handwritten/` alone. The tests that check those files against the 2024 books also need the pinned 5etools v2.30.1 data (gitignored); in a fresh clone, fetch it once:
```bash
pip install -e ".[dev]"
python -m engine.source_files --fetch
python -m pytest
```

See `ROADMAP.md` for what each tool measures and the results so far.
