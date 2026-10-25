# Party rating: fighter_1_optimized, cleric_1_optimized, rogue_1_optimized, wizard_1_optimized

Level 1, 4 PCs; benchmark v1; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 5,200 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 1 (100 XP).

**Overall: 326 XP (81 per PC, 0.81x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 307 | 77 | 0.77 |
| ranged | 219 | 55 | 0.55 |
| caster | 611 | 153 | 1.53 |
| swarm | 150 | 38 | 0.38 |
| control | 401 | 100 | 1.00 |
| solo | 485 | 121 | 1.21 |

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| worg x1 | 100 | 0.0% | 1.8% | 100 |
| worg x2 | 200 | 0.0% | 1.8% | 100 |
| worg x3 | 300 | 2.9% | 1.8% | 350 |
| worg x4 | 400 | 34.0% | 12.7% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| skeleton x1 | 50 | 0.0% | 1.8% | 100 |
| skeleton x2 | 100 | 0.0% | 1.8% | 100 |
| skeleton x3 | 150 | 0.0% | 1.8% | 100 |
| skeleton x4 | 200 | 2.0% | 1.9% | 250 |
| skeleton x5 | 250 | 10.0% | 4.8% | 150 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| cultist_fanatic x1 | 450 | 0.0% | 1.8% | 100 |
| cultist_fanatic x2 | 900 | 14.0% | 9.6% | 50 |

### swarm

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| kobold_warrior x1 | 25 | 0.0% | 1.8% | 100 |
| kobold_warrior x2 | 50 | 0.0% | 1.8% | 100 |
| kobold_warrior x3 | 75 | 0.0% | 1.8% | 100 |
| kobold_warrior x4 | 100 | 0.0% | 1.8% | 100 |
| kobold_warrior x5 | 125 | 0.7% | 1.8% | 150 |
| kobold_warrior x6 | 150 | 4.9% | 1.8% | 550 |
| kobold_warrior x8 | 200 | 44.0% | 13.3% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| ghoul x1 | 200 | 0.0% | 1.8% | 100 |
| ghoul x2 | 400 | 4.8% | 1.9% | 500 |
| ghoul x3 | 600 | 34.0% | 12.7% | 50 |

### solo

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| ogre x1 | 450 | 0.0% | 1.8% | 100 |
| owlbear x1 | 700 | 36.0% | 12.9% | 50 |
