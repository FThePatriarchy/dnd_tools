# Party rating: fighter_11+items_full, cleric_11+items_full, rogue_11+items_full, wizard_11+items_full

Level 11, 4 PCs; benchmark v2; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 7,150 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 11 (4100 XP).

**Overall: 13,369 XP (3,342 per PC, 0.82x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 14,328 | 3,582 | 0.87 |
| ranged | 15,497 | 3,874 | 0.94 |
| caster | 11,500 | 2,875 | 0.70 |
| swarm | 11,660 | 2,915 | 0.71 |
| control | 12,439 | 3,110 | 0.76 |
| solo | 15,417 | 3,854 | 0.94 |

## Magic items

DMG-sized kits (`engine/items.py`).

- fighter_11+items_full: +3 Weapon, Belt of Hill Giant Strength, Cloak of Protection, Stone of Good Luck
- cleric_11+items_full: +2 Shield, +1 Armor, Cloak of Protection, Stone of Good Luck, +1 Wand of the War Mage, +1 Weapon
- rogue_11+items_full: +2 Weapon, +1 Armor, Cloak of Protection, Stone of Good Luck
- wizard_11+items_full: +2 Wand of the War Mage, Bracers of Defense, Cloak of Protection

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| wyvern x1 | 2,300 | 0.0% | 1.8% | 100 |
| wyvern x2 | 4,600 | 0.0% | 1.8% | 100 |
| wyvern x3 | 6,900 | 0.0% | 1.8% | 100 |
| wyvern x4 | 9,200 | 0.0% | 1.8% | 100 |
| wyvern x5 | 11,500 | 0.0% | 1.8% | 100 |
| wyvern x6 | 13,800 | 1.5% | 1.9% | 200 |
| wyvern x8 | 18,400 | 32.0% | 12.5% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| stone_giant x1 | 2,900 | 0.0% | 1.8% | 100 |
| stone_giant x2 | 5,800 | 0.0% | 1.8% | 100 |
| stone_giant x3 | 8,700 | 0.0% | 1.8% | 100 |
| stone_giant x4 | 11,600 | 0.0% | 1.8% | 100 |
| stone_giant x5 | 14,500 | 1.3% | 2.2% | 150 |
| stone_giant x6 | 17,400 | 12.0% | 9.1% | 50 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| mage x1 | 2,300 | 0.0% | 1.8% | 100 |
| mage x2 | 4,600 | 0.0% | 1.8% | 100 |
| mage x3 | 6,900 | 0.0% | 1.8% | 100 |
| mage x4 | 9,200 | 0.7% | 1.8% | 150 |
| mage x5 | 11,500 | 5.0% | 1.9% | 500 |
| mage x6 | 13,800 | 36.0% | 12.9% | 50 |

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
| guard_captain x10 | 11,000 | 2.0% | 1.7% | 300 |
| guard_captain x12 | 13,200 | 12.0% | 9.1% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| mind_flayer x1 | 2,900 | 0.0% | 1.8% | 100 |
| mind_flayer x2 | 5,800 | 0.0% | 1.8% | 100 |
| mind_flayer x3 | 8,700 | 0.0% | 1.8% | 100 |
| mind_flayer x4 | 11,600 | 1.3% | 2.2% | 150 |
| mind_flayer x5 | 14,500 | 14.0% | 9.6% | 50 |

### solo

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| young_white_dragon x1 | 2,300 | 0.0% | 1.8% | 100 |
| young_black_dragon x1 | 2,900 | 0.0% | 1.8% | 100 |
| young_green_dragon x1 | 3,900 | 0.0% | 1.8% | 100 |
| young_blue_dragon x1 | 5,000 | 0.0% | 1.8% | 100 |
| young_red_dragon x1 | 5,900 | 0.0% | 1.8% | 100 |
| adult_white_dragon x1 | 10,000 | 2.0% | 1.9% | 250 |
| adult_black_dragon x1 | 11,500 | 0.0% | 1.8% | 100 |
| adult_green_dragon x1 | 13,000 | 4.7% | 2.0% | 450 |
| adult_blue_dragon x1 | 15,000 | 0.0% | 1.8% | 100 |
| adult_red_dragon x1 | 18,000 | 36.0% | 12.9% | 50 |
