# Party rating: fighter_10+items_half, cleric_10+items_half, rogue_10+items_half, wizard_10+items_half

Level 10, 4 PCs; benchmark v1; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 6,500 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 10 (3100 XP).

**Overall: 10,250 XP (2,562 per PC, 0.83x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 12,039 | 3,010 | 0.97 |
| ranged | 13,642 | 3,411 | 1.10 |
| caster | 9,438 | 2,360 | 0.76 |
| swarm | 9,586 | 2,396 | 0.77 |
| control | 11,817 | 2,954 | 0.95 |
| solo | 6,603 | 1,651 | 0.53 |

## Magic items

DMG-sized kits (`engine/items.py`).

- fighter_10+items_half: +2 Weapon, Cloak of Protection, Stone of Good Luck
- cleric_10+items_half: +2 Shield, Cloak of Protection, Stone of Good Luck
- rogue_10+items_half: +2 Weapon, Cloak of Protection, Stone of Good Luck
- wizard_10+items_half: Cloak of Protection, Stone of Good Luck, +1 Wand of the War Mage

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| wyvern x1 | 2,300 | 0.0% | 1.8% | 100 |
| wyvern x2 | 4,600 | 0.0% | 1.8% | 100 |
| wyvern x3 | 6,900 | 0.0% | 1.8% | 100 |
| wyvern x4 | 9,200 | 0.0% | 1.8% | 100 |
| wyvern x5 | 11,500 | 2.9% | 1.8% | 350 |
| wyvern x6 | 13,800 | 12.0% | 9.1% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| barbed_devil x1 | 1,800 | 0.0% | 1.8% | 100 |
| barbed_devil x2 | 3,600 | 0.0% | 1.8% | 100 |
| barbed_devil x3 | 5,400 | 0.0% | 1.8% | 100 |
| barbed_devil x4 | 7,200 | 0.0% | 1.8% | 100 |
| barbed_devil x5 | 9,000 | 0.0% | 1.8% | 100 |
| barbed_devil x6 | 10,800 | 0.0% | 1.8% | 100 |
| barbed_devil x8 | 14,400 | 6.3% | 2.0% | 600 |
| barbed_devil x10 | 18,000 | 68.0% | 12.5% | 50 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| mage x1 | 2,300 | 0.0% | 1.8% | 100 |
| mage x2 | 4,600 | 0.0% | 1.8% | 100 |
| mage x3 | 6,900 | 0.0% | 1.8% | 100 |
| mage x4 | 9,200 | 2.6% | 1.7% | 350 |
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
| guard_captain x10 | 11,000 | 14.0% | 6.8% | 100 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| vampire_spawn x1 | 1,800 | 0.0% | 1.8% | 100 |
| vampire_spawn x2 | 3,600 | 0.0% | 1.8% | 100 |
| vampire_spawn x3 | 5,400 | 0.0% | 1.8% | 100 |
| vampire_spawn x4 | 7,200 | 0.0% | 1.8% | 100 |
| vampire_spawn x5 | 9,000 | 0.0% | 1.8% | 100 |
| vampire_spawn x6 | 10,800 | 0.7% | 1.8% | 150 |
| vampire_spawn x8 | 14,400 | 16.0% | 10.1% | 50 |

### solo

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| troll x1 | 1,800 | 0.0% | 1.8% | 100 |
| young_white_dragon x1 | 2,300 | 0.0% | 1.8% | 100 |
| young_black_dragon x1 | 2,900 | 0.0% | 1.8% | 100 |
| young_green_dragon x1 | 3,900 | 0.0% | 1.8% | 100 |
| young_blue_dragon x1 | 5,000 | 0.0% | 1.8% | 100 |
| young_red_dragon x1 | 5,900 | 0.0% | 1.8% | 100 |
| adult_red_dragon x1 | 18,000 | 86.0% | 9.6% | 50 |
