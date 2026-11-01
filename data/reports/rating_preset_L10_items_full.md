# Party rating: fighter_10+items_full, cleric_10+items_full, rogue_10+items_full, wizard_10+items_full

Level 10, 4 PCs; benchmark v1; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 5,750 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 10 (3100 XP).

**Overall: 10,414 XP (2,604 per PC, 0.84x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 12,075 | 3,019 | 0.97 |
| ranged | 13,976 | 3,494 | 1.13 |
| caster | 9,529 | 2,382 | 0.77 |
| swarm | 9,717 | 2,429 | 0.78 |
| control | 12,300 | 3,075 | 0.99 |
| solo | 6,638 | 1,659 | 0.54 |

## Magic items

DMG-sized kits (`engine/items.py`).

- fighter_10+items_full: +2 Weapon, Belt of Hill Giant Strength, Cloak of Protection, Stone of Good Luck
- cleric_10+items_full: +2 Shield, +1 Armor, Cloak of Protection, Stone of Good Luck, +1 Wand of the War Mage, +1 Weapon
- rogue_10+items_full: +2 Weapon, Cloak of Protection, Stone of Good Luck
- wizard_10+items_full: +2 Wand of the War Mage, Cloak of Protection, Stone of Good Luck

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| wyvern x1 | 2,300 | 0.0% | 1.8% | 100 |
| wyvern x2 | 4,600 | 0.0% | 1.8% | 100 |
| wyvern x3 | 6,900 | 0.0% | 1.8% | 100 |
| wyvern x4 | 9,200 | 0.0% | 1.8% | 100 |
| wyvern x5 | 11,500 | 2.3% | 1.8% | 300 |
| wyvern x6 | 13,800 | 13.0% | 6.6% | 100 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| barbed_devil x1 | 1,800 | 0.0% | 1.8% | 100 |
| barbed_devil x2 | 3,600 | 0.0% | 1.8% | 100 |
| barbed_devil x3 | 5,400 | 0.0% | 1.8% | 100 |
| barbed_devil x4 | 7,200 | 0.0% | 1.8% | 100 |
| barbed_devil x5 | 9,000 | 0.0% | 1.8% | 100 |
| barbed_devil x6 | 10,800 | 0.0% | 1.8% | 100 |
| barbed_devil x8 | 14,400 | 5.7% | 1.9% | 600 |
| barbed_devil x10 | 18,000 | 66.0% | 12.7% | 50 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| mage x1 | 2,300 | 0.0% | 1.8% | 100 |
| mage x2 | 4,600 | 0.0% | 1.8% | 100 |
| mage x3 | 6,900 | 0.0% | 1.8% | 100 |
| mage x4 | 9,200 | 1.5% | 1.9% | 200 |
| mage x5 | 11,500 | 26.0% | 11.8% | 50 |

### swarm

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| guard_captain x1 | 1,100 | 0.0% | 1.8% | 100 |
| guard_captain x2 | 2,200 | 0.0% | 1.8% | 100 |
| guard_captain x3 | 3,300 | 0.0% | 1.8% | 100 |
| guard_captain x4 | 4,400 | 0.0% | 1.8% | 100 |
| guard_captain x5 | 5,500 | 0.0% | 1.8% | 100 |
| guard_captain x6 | 6,600 | 0.0% | 1.8% | 100 |
| guard_captain x8 | 8,800 | 0.0% | 1.8% | 100 |
| guard_captain x10 | 11,000 | 12.0% | 6.4% | 100 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| vampire_spawn x1 | 1,800 | 0.0% | 1.8% | 100 |
| vampire_spawn x2 | 3,600 | 0.0% | 1.8% | 100 |
| vampire_spawn x3 | 5,400 | 0.0% | 1.8% | 100 |
| vampire_spawn x4 | 7,200 | 0.0% | 1.8% | 100 |
| vampire_spawn x5 | 9,000 | 0.0% | 1.8% | 100 |
| vampire_spawn x6 | 10,800 | 0.0% | 1.8% | 100 |
| vampire_spawn x8 | 14,400 | 12.0% | 9.1% | 50 |

### solo

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| troll x1 | 1,800 | 0.0% | 1.8% | 100 |
| young_white_dragon x1 | 2,300 | 0.0% | 1.8% | 100 |
| young_black_dragon x1 | 2,900 | 0.0% | 1.8% | 100 |
| young_green_dragon x1 | 3,900 | 0.0% | 1.8% | 100 |
| young_blue_dragon x1 | 5,000 | 0.0% | 1.8% | 100 |
| young_red_dragon x1 | 5,900 | 0.0% | 1.8% | 100 |
| adult_red_dragon x1 | 18,000 | 82.0% | 10.5% | 50 |
