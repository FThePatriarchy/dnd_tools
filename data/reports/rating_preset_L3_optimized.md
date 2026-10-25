# Party rating: fighter_3_optimized, cleric_3_optimized, rogue_3_optimized, wizard_3_optimized

Level 3, 4 PCs; benchmark v1; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 5,000 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 3 (400 XP).

**Overall: 1,296 XP (324 per PC, 0.81x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 1,330 | 332 | 0.83 |
| ranged | 1,382 | 345 | 0.86 |
| caster | 2,475 | 619 | 1.55 |
| swarm | 662 | 166 | 0.41 |
| control | 1,313 | 328 | 0.82 |
| solo | 1,200 | 300 | 0.75 |

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| brown_bear x1 | 200 | 0.0% | 1.8% | 100 |
| brown_bear x2 | 400 | 0.0% | 1.8% | 100 |
| brown_bear x3 | 600 | 0.0% | 1.8% | 100 |
| brown_bear x4 | 800 | 0.0% | 1.8% | 100 |
| brown_bear x5 | 1,000 | 0.0% | 1.8% | 100 |
| brown_bear x6 | 1,200 | 0.7% | 1.8% | 150 |
| brown_bear x8 | 1,600 | 14.0% | 9.6% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| spy x1 | 200 | 0.0% | 1.8% | 100 |
| spy x2 | 400 | 0.0% | 1.8% | 100 |
| spy x3 | 600 | 0.0% | 1.8% | 100 |
| spy x4 | 800 | 0.0% | 1.8% | 100 |
| spy x5 | 1,000 | 0.0% | 1.8% | 100 |
| spy x6 | 1,200 | 0.0% | 1.8% | 100 |
| spy x8 | 1,600 | 11.0% | 6.2% | 100 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| cultist_fanatic x1 | 450 | 0.0% | 1.8% | 100 |
| cultist_fanatic x2 | 900 | 0.0% | 1.8% | 100 |
| cultist_fanatic x3 | 1,350 | 0.0% | 1.8% | 100 |
| cultist_fanatic x4 | 1,800 | 0.0% | 1.8% | 100 |
| cultist_fanatic x5 | 2,250 | 0.0% | 1.8% | 100 |
| cultist_fanatic x6 | 2,700 | 10.0% | 4.8% | 150 |

### swarm

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| hobgoblin_warrior x1 | 100 | 0.0% | 1.8% | 100 |
| hobgoblin_warrior x2 | 200 | 0.0% | 1.8% | 100 |
| hobgoblin_warrior x3 | 300 | 0.0% | 1.8% | 100 |
| hobgoblin_warrior x4 | 400 | 0.0% | 1.8% | 100 |
| hobgoblin_warrior x5 | 500 | 0.0% | 1.8% | 100 |
| hobgoblin_warrior x6 | 600 | 0.0% | 1.8% | 100 |
| hobgoblin_warrior x8 | 800 | 16.0% | 10.1% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| ghoul x1 | 200 | 0.0% | 1.8% | 100 |
| ghoul x2 | 400 | 0.0% | 1.8% | 100 |
| ghoul x3 | 600 | 0.0% | 1.8% | 100 |
| ghoul x4 | 800 | 0.0% | 1.8% | 100 |
| ghoul x5 | 1,000 | 0.0% | 1.8% | 100 |
| ghoul x6 | 1,200 | 0.7% | 1.8% | 150 |
| ghoul x8 | 1,600 | 16.0% | 10.1% | 50 |

### solo

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| ogre x1 | 450 | 0.0% | 1.8% | 100 |
| owlbear x1 | 700 | 0.0% | 1.8% | 100 |
| troll x1 | 1,800 | 11.0% | 6.2% | 100 |
