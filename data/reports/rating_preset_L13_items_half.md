# Party rating: fighter_13+items_half, cleric_13+items_half, rogue_13+items_half, wizard_13+items_half

Level 13, 4 PCs; benchmark v2; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 5,550 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 13 (5400 XP).

**Overall: 18,240 XP (4,560 per PC, 0.84x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 13,994 | 3,499 | 0.65 |
| ranged | 24,662 | 6,165 | 1.14 |
| caster | 14,242 | 3,561 | 0.66 |
| swarm | 18,327 | 4,582 | 0.85 |
| control | 19,943 | 4,986 | 0.92 |
| solo | 20,500 | 5,125 | 0.95 |

## Magic items

DMG-sized kits (`engine/items.py`).

- fighter_13+items_half: +3 Weapon, Belt of Hill Giant Strength, Cloak of Protection, Stone of Good Luck
- cleric_13+items_half: +2 Shield, +1 Armor, Cloak of Protection, Stone of Good Luck, +1 Wand of the War Mage, +1 Weapon
- rogue_13+items_half: +2 Weapon, Cloak of Protection, Stone of Good Luck
- wizard_13+items_half: +2 Wand of the War Mage, Cloak of Protection, Stone of Good Luck

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| tyrannosaurus_rex x1 | 3,900 | 0.0% | 1.8% | 100 |
| tyrannosaurus_rex x2 | 7,800 | 0.0% | 1.8% | 100 |
| tyrannosaurus_rex x3 | 11,700 | 0.0% | 1.8% | 100 |
| tyrannosaurus_rex x4 | 15,600 | 8.5% | 3.9% | 200 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| assassin x1 | 3,900 | 0.0% | 1.8% | 100 |
| assassin x2 | 7,800 | 0.0% | 1.8% | 100 |
| assassin x3 | 11,700 | 0.0% | 1.8% | 100 |
| assassin x4 | 15,600 | 0.0% | 1.8% | 100 |
| assassin x5 | 19,500 | 0.0% | 1.8% | 100 |
| assassin x6 | 23,400 | 1.3% | 2.2% | 150 |
| assassin x8 | 31,200 | 24.0% | 11.6% | 50 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| mage x1 | 2,300 | 0.0% | 1.8% | 100 |
| mage x2 | 4,600 | 0.0% | 1.8% | 100 |
| mage x3 | 6,900 | 0.0% | 1.8% | 100 |
| mage x4 | 9,200 | 0.0% | 1.8% | 100 |
| mage x5 | 11,500 | 0.0% | 1.8% | 100 |
| mage x6 | 13,800 | 0.0% | 1.8% | 100 |
| mage x8 | 18,400 | 52.0% | 13.3% | 50 |

### swarm

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| gladiator x1 | 1,800 | 0.0% | 1.8% | 100 |
| gladiator x2 | 3,600 | 0.0% | 1.8% | 100 |
| gladiator x3 | 5,400 | 0.0% | 1.8% | 100 |
| gladiator x4 | 7,200 | 0.0% | 1.8% | 100 |
| gladiator x5 | 9,000 | 0.0% | 1.8% | 100 |
| gladiator x6 | 10,800 | 0.0% | 1.8% | 100 |
| gladiator x8 | 14,400 | 0.0% | 1.8% | 100 |
| gladiator x10 | 18,000 | 1.5% | 1.9% | 200 |
| gladiator x12 | 21,600 | 40.0% | 13.1% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| chain_devil x1 | 3,900 | 0.0% | 1.8% | 100 |
| chain_devil x2 | 7,800 | 0.0% | 1.8% | 100 |
| chain_devil x3 | 11,700 | 0.0% | 1.8% | 100 |
| chain_devil x4 | 15,600 | 0.0% | 1.8% | 100 |
| chain_devil x5 | 19,500 | 0.0% | 1.8% | 100 |
| chain_devil x6 | 23,400 | 44.0% | 13.3% | 50 |

### solo

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| young_black_dragon x1 | 2,900 | 0.0% | 1.8% | 100 |
| young_green_dragon x1 | 3,900 | 0.0% | 1.8% | 100 |
| young_blue_dragon x1 | 5,000 | 0.0% | 1.8% | 100 |
| young_red_dragon x1 | 5,900 | 0.0% | 1.8% | 100 |
| adult_white_dragon x1 | 10,000 | 0.0% | 1.8% | 100 |
| adult_black_dragon x1 | 11,500 | 0.0% | 1.8% | 100 |
| adult_green_dragon x1 | 13,000 | 0.0% | 1.8% | 100 |
| adult_blue_dragon x1 | 15,000 | 0.0% | 1.8% | 100 |
| adult_red_dragon x1 | 18,000 | 0.0% | 1.8% | 100 |
| ancient_white_dragon x1 | 25,000 | 14.0% | 9.6% | 50 |
