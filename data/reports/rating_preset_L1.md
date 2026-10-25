# Party rating: fighter_1, cleric_1, rogue_1, wizard_1

Level 1, 4 PCs; benchmark v1; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 4,200 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 1 (100 XP).

**Overall: 302 XP (75 per PC, 0.75x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 306 | 77 | 0.77 |
| ranged | 212 | 53 | 0.53 |
| caster | 544 | 136 | 1.36 |
| swarm | 158 | 40 | 0.40 |
| control | 277 | 69 | 0.69 |
| solo | 487 | 122 | 1.22 |

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| worg x1 | 100 | 0.0% | 1.8% | 100 |
| worg x2 | 200 | 0.0% | 1.8% | 100 |
| worg x3 | 300 | 3.8% | 1.9% | 400 |
| worg x4 | 400 | 24.0% | 11.6% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| skeleton x1 | 50 | 0.0% | 1.8% | 100 |
| skeleton x2 | 100 | 0.0% | 1.8% | 100 |
| skeleton x3 | 150 | 0.0% | 1.8% | 100 |
| skeleton x4 | 200 | 2.9% | 1.8% | 350 |
| skeleton x5 | 250 | 12.0% | 9.1% | 50 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| cultist_fanatic x1 | 450 | 0.0% | 1.8% | 100 |
| cultist_fanatic x2 | 900 | 24.0% | 11.6% | 50 |

### swarm

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| kobold_warrior x1 | 25 | 0.0% | 1.8% | 100 |
| kobold_warrior x2 | 50 | 0.0% | 1.8% | 100 |
| kobold_warrior x3 | 75 | 0.0% | 1.8% | 100 |
| kobold_warrior x4 | 100 | 0.0% | 1.8% | 100 |
| kobold_warrior x5 | 125 | 0.0% | 1.8% | 100 |
| kobold_warrior x6 | 150 | 1.3% | 2.2% | 150 |
| kobold_warrior x8 | 200 | 24.0% | 11.6% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| ghoul x1 | 200 | 0.0% | 1.8% | 100 |
| ghoul x2 | 400 | 13.0% | 6.6% | 100 |

### solo

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| ogre x1 | 450 | 1.3% | 2.2% | 150 |
| owlbear x1 | 700 | 26.0% | 11.8% | 50 |
