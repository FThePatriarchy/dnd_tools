# Party rating: fighter_10_optimized, cleric_10_optimized, rogue_10_optimized, wizard_10_optimized

Level 10, 4 PCs; benchmark v1; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 4,500 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 10 (3100 XP).

**Overall: 9,618 XP (2,404 per PC, 0.78x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 11,988 | 2,997 | 0.97 |
| ranged | 13,994 | 3,498 | 1.13 |
| caster | 7,858 | 1,965 | 0.63 |
| swarm | 9,247 | 2,312 | 0.75 |
| control | 9,900 | 2,475 | 0.80 |
| solo | 6,558 | 1,639 | 0.53 |

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| wyvern x1 | 2,300 | 0.0% | 1.8% | 100 |
| wyvern x2 | 4,600 | 0.0% | 1.8% | 100 |
| wyvern x3 | 6,900 | 0.0% | 1.8% | 100 |
| wyvern x4 | 9,200 | 0.0% | 1.8% | 100 |
| wyvern x5 | 11,500 | 1.5% | 1.9% | 200 |
| wyvern x6 | 13,800 | 18.0% | 10.5% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| barbed_devil x1 | 1,800 | 0.0% | 1.8% | 100 |
| barbed_devil x2 | 3,600 | 0.0% | 1.8% | 100 |
| barbed_devil x3 | 5,400 | 0.0% | 1.8% | 100 |
| barbed_devil x4 | 7,200 | 0.0% | 1.8% | 100 |
| barbed_devil x5 | 9,000 | 0.0% | 1.8% | 100 |
| barbed_devil x6 | 10,800 | 0.0% | 1.8% | 100 |
| barbed_devil x8 | 14,400 | 5.6% | 1.9% | 550 |
| barbed_devil x10 | 18,000 | 56.0% | 13.3% | 50 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| mage x1 | 2,300 | 0.0% | 1.8% | 100 |
| mage x2 | 4,600 | 0.0% | 1.8% | 100 |
| mage x3 | 6,900 | 0.0% | 1.8% | 100 |
| mage x4 | 9,200 | 12.0% | 9.1% | 50 |

### swarm

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| guard_captain x1 | 1,100 | 0.0% | 1.8% | 100 |
| guard_captain x2 | 2,200 | 0.0% | 1.8% | 100 |
| guard_captain x3 | 3,300 | 0.0% | 1.8% | 100 |
| guard_captain x4 | 4,400 | 0.0% | 1.8% | 100 |
| guard_captain x5 | 5,500 | 0.0% | 1.8% | 100 |
| guard_captain x6 | 6,600 | 0.0% | 1.8% | 100 |
| guard_captain x8 | 8,800 | 0.7% | 1.8% | 150 |
| guard_captain x10 | 11,000 | 22.0% | 11.2% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| vampire_spawn x1 | 1,800 | 0.0% | 1.8% | 100 |
| vampire_spawn x2 | 3,600 | 0.0% | 1.8% | 100 |
| vampire_spawn x3 | 5,400 | 0.0% | 1.8% | 100 |
| vampire_spawn x4 | 7,200 | 0.0% | 1.8% | 100 |
| vampire_spawn x5 | 9,000 | 0.0% | 1.8% | 100 |
| vampire_spawn x6 | 10,800 | 10.0% | 6.0% | 100 |

### solo

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| troll x1 | 1,800 | 0.0% | 1.8% | 100 |
| young_white_dragon x1 | 2,300 | 0.0% | 1.8% | 100 |
| young_black_dragon x1 | 2,900 | 0.0% | 1.8% | 100 |
| young_green_dragon x1 | 3,900 | 0.0% | 1.8% | 100 |
| young_blue_dragon x1 | 5,000 | 0.0% | 1.8% | 100 |
| young_red_dragon x1 | 5,900 | 0.0% | 1.8% | 100 |
| adult_red_dragon x1 | 18,000 | 92.0% | 7.8% | 50 |
