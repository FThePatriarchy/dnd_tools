# Party rating: fighter_1_casual, cleric_1_casual, rogue_1_casual, wizard_1_casual

Level 1, 4 PCs; benchmark v1; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 3,300 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 1 (100 XP).

**Overall: 272 XP (68 per PC, 0.68x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 252 | 63 | 0.63 |
| ranged | 172 | 43 | 0.43 |
| caster | 508 | 127 | 1.27 |
| swarm | 137 | 34 | 0.34 |
| control | 271 | 68 | 0.68 |
| solo | 489 | 122 | 1.22 |

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| worg x1 | 100 | 0.0% | 1.8% | 100 |
| worg x2 | 200 | 0.0% | 1.8% | 100 |
| worg x3 | 300 | 9.6% | 3.7% | 250 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| skeleton x1 | 50 | 0.0% | 1.8% | 100 |
| skeleton x2 | 100 | 0.0% | 1.8% | 100 |
| skeleton x3 | 150 | 2.0% | 1.9% | 250 |
| skeleton x4 | 200 | 8.7% | 4.6% | 150 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| cultist_fanatic x1 | 450 | 1.3% | 2.2% | 150 |
| cultist_fanatic x2 | 900 | 30.0% | 12.3% | 50 |

### swarm

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| kobold_warrior x1 | 25 | 0.0% | 1.8% | 100 |
| kobold_warrior x2 | 50 | 0.0% | 1.8% | 100 |
| kobold_warrior x3 | 75 | 0.0% | 1.8% | 100 |
| kobold_warrior x4 | 100 | 0.0% | 1.8% | 100 |
| kobold_warrior x5 | 125 | 2.6% | 1.7% | 350 |
| kobold_warrior x6 | 150 | 7.6% | 2.5% | 450 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| ghoul x1 | 200 | 0.0% | 1.8% | 100 |
| ghoul x2 | 400 | 14.0% | 6.8% | 100 |

### solo

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| ogre x1 | 450 | 0.0% | 1.8% | 100 |
| owlbear x1 | 700 | 32.0% | 12.5% | 50 |
