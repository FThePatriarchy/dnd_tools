# Party rating: fighter_10, cleric_10, rogue_10, wizard_10

Level 10, 4 PCs; benchmark v1; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 6,000 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 10 (3100 XP).

**Overall: 9,065 XP (2,266 per PC, 0.73x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 10,158 | 2,540 | 0.82 |
| ranged | 11,103 | 2,776 | 0.90 |
| caster | 7,539 | 1,885 | 0.61 |
| swarm | 8,974 | 2,243 | 0.72 |
| control | 11,014 | 2,753 | 0.89 |
| solo | 6,603 | 1,651 | 0.53 |

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| wyvern x1 | 2,300 | 0.0% | 1.8% | 100 |
| wyvern x2 | 4,600 | 0.0% | 1.8% | 100 |
| wyvern x3 | 6,900 | 0.0% | 1.8% | 100 |
| wyvern x4 | 9,200 | 0.0% | 1.8% | 100 |
| wyvern x5 | 11,500 | 12.0% | 6.4% | 100 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| barbed_devil x1 | 1,800 | 0.0% | 1.8% | 100 |
| barbed_devil x2 | 3,600 | 0.0% | 1.8% | 100 |
| barbed_devil x3 | 5,400 | 0.0% | 1.8% | 100 |
| barbed_devil x4 | 7,200 | 0.0% | 1.8% | 100 |
| barbed_devil x5 | 9,000 | 0.0% | 1.8% | 100 |
| barbed_devil x6 | 10,800 | 2.3% | 1.8% | 300 |
| barbed_devil x8 | 14,400 | 34.0% | 12.7% | 50 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| mage x1 | 2,300 | 0.0% | 1.8% | 100 |
| mage x2 | 4,600 | 0.0% | 1.8% | 100 |
| mage x3 | 6,900 | 0.0% | 1.8% | 100 |
| mage x4 | 9,200 | 18.0% | 10.5% | 50 |

### swarm

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| guard_captain x1 | 1,100 | 0.0% | 1.8% | 100 |
| guard_captain x2 | 2,200 | 0.0% | 1.8% | 100 |
| guard_captain x3 | 3,300 | 0.0% | 1.8% | 100 |
| guard_captain x4 | 4,400 | 0.0% | 1.8% | 100 |
| guard_captain x5 | 5,500 | 0.0% | 1.8% | 100 |
| guard_captain x6 | 6,600 | 0.0% | 1.8% | 100 |
| guard_captain x8 | 8,800 | 2.0% | 1.9% | 250 |
| guard_captain x10 | 11,000 | 40.0% | 13.1% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| vampire_spawn x1 | 1,800 | 0.0% | 1.8% | 100 |
| vampire_spawn x2 | 3,600 | 0.0% | 1.8% | 100 |
| vampire_spawn x3 | 5,400 | 0.0% | 1.8% | 100 |
| vampire_spawn x4 | 7,200 | 0.0% | 1.8% | 100 |
| vampire_spawn x5 | 9,000 | 0.0% | 1.8% | 100 |
| vampire_spawn x6 | 10,800 | 2.7% | 1.9% | 300 |
| vampire_spawn x8 | 14,400 | 42.0% | 13.2% | 50 |

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
