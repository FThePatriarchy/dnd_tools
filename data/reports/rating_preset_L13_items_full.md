# Party rating: fighter_13+items_full, cleric_13+items_full, rogue_13+items_full, wizard_13+items_full

Level 13, 4 PCs; benchmark v2; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 6,150 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 13 (5400 XP).

**Overall: 19,607 XP (4,902 per PC, 0.91x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 15,721 | 3,930 | 0.73 |
| ranged | 27,988 | 6,997 | 1.30 |
| caster | 14,439 | 3,610 | 0.67 |
| swarm | 19,500 | 4,875 | 0.90 |
| control | 20,719 | 5,180 | 0.96 |
| solo | 22,136 | 5,534 | 1.02 |

## Magic items

DMG-sized kits (`engine/items.py`).

- fighter_13+items_full: +3 Weapon, Belt of Hill Giant Strength, +1 Armor, Ring of Protection, Cloak of Protection
- cleric_13+items_full: +3 Shield, +1 Armor, Ring of Protection, Cloak of Protection, Stone of Good Luck, +1 Weapon
- rogue_13+items_full: +3 Weapon, +1 Armor, Ring of Protection, Cloak of Protection, Stone of Good Luck
- wizard_13+items_full: +2 Wand of the War Mage, Bracers of Defense, Ring of Protection

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| tyrannosaurus_rex x1 | 3,900 | 0.0% | 1.8% | 100 |
| tyrannosaurus_rex x2 | 7,800 | 0.0% | 1.8% | 100 |
| tyrannosaurus_rex x3 | 11,700 | 0.0% | 1.8% | 100 |
| tyrannosaurus_rex x4 | 15,600 | 3.8% | 1.9% | 400 |
| tyrannosaurus_rex x5 | 19,500 | 44.0% | 13.3% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| assassin x1 | 3,900 | 0.0% | 1.8% | 100 |
| assassin x2 | 7,800 | 0.0% | 1.8% | 100 |
| assassin x3 | 11,700 | 0.0% | 1.8% | 100 |
| assassin x4 | 15,600 | 0.0% | 1.8% | 100 |
| assassin x5 | 19,500 | 0.0% | 1.8% | 100 |
| assassin x6 | 23,400 | 0.0% | 1.8% | 100 |
| assassin x8 | 31,200 | 8.5% | 3.9% | 200 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| mage x1 | 2,300 | 0.0% | 1.8% | 100 |
| mage x2 | 4,600 | 0.0% | 1.8% | 100 |
| mage x3 | 6,900 | 0.0% | 1.8% | 100 |
| mage x4 | 9,200 | 0.0% | 1.8% | 100 |
| mage x5 | 11,500 | 0.0% | 1.8% | 100 |
| mage x6 | 13,800 | 0.0% | 1.8% | 100 |
| mage x8 | 18,400 | 36.0% | 12.9% | 50 |

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
| gladiator x10 | 18,000 | 0.0% | 1.8% | 100 |
| gladiator x12 | 21,600 | 12.0% | 9.1% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| chain_devil x1 | 3,900 | 0.0% | 1.8% | 100 |
| chain_devil x2 | 7,800 | 0.0% | 1.8% | 100 |
| chain_devil x3 | 11,700 | 0.0% | 1.8% | 100 |
| chain_devil x4 | 15,600 | 0.0% | 1.8% | 100 |
| chain_devil x5 | 19,500 | 0.0% | 1.8% | 100 |
| chain_devil x6 | 23,400 | 16.0% | 10.1% | 50 |

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
| adult_red_dragon x1 | 18,000 | 0.7% | 1.8% | 150 |
| ancient_white_dragon x1 | 25,000 | 8.0% | 3.1% | 300 |
