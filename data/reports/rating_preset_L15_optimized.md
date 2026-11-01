# Party rating: fighter_15_optimized, cleric_15_optimized, rogue_15_optimized, wizard_15_optimized

Level 15, 4 PCs; benchmark v2; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 6,250 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 15 (7800 XP).

**Overall: 18,279 XP (4,570 per PC, 0.59x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 15,428 | 3,857 | 0.49 |
| ranged | 24,900 | 6,225 | 0.80 |
| caster | 17,578 | 4,394 | 0.56 |
| swarm | 17,169 | 4,292 | 0.55 |
| control | 19,798 | 4,949 | 0.63 |
| solo | 16,250 | 4,062 | 0.52 |

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| tyrannosaurus_rex x1 | 3,900 | 0.0% | 1.8% | 100 |
| tyrannosaurus_rex x2 | 7,800 | 0.0% | 1.8% | 100 |
| tyrannosaurus_rex x3 | 11,700 | 0.7% | 1.8% | 150 |
| tyrannosaurus_rex x4 | 15,600 | 5.2% | 2.0% | 500 |
| tyrannosaurus_rex x5 | 19,500 | 48.0% | 13.3% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| assassin x1 | 3,900 | 0.0% | 1.8% | 100 |
| assassin x2 | 7,800 | 0.0% | 1.8% | 100 |
| assassin x3 | 11,700 | 0.0% | 1.8% | 100 |
| assassin x4 | 15,600 | 0.0% | 1.8% | 100 |
| assassin x5 | 19,500 | 0.0% | 1.8% | 100 |
| assassin x6 | 23,400 | 0.0% | 1.8% | 100 |
| assassin x8 | 31,200 | 26.0% | 11.8% | 50 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| archmage x1 | 8,400 | 0.0% | 1.8% | 100 |
| archmage x2 | 16,800 | 0.0% | 1.8% | 100 |
| archmage x3 | 25,200 | 54.0% | 13.3% | 50 |

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
| gladiator x10 | 18,000 | 6.5% | 2.0% | 600 |
| gladiator x12 | 21,600 | 62.0% | 13.0% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| chain_devil x1 | 3,900 | 0.0% | 1.8% | 100 |
| chain_devil x2 | 7,800 | 0.0% | 1.8% | 100 |
| chain_devil x3 | 11,700 | 0.0% | 1.8% | 100 |
| chain_devil x4 | 15,600 | 0.0% | 1.8% | 100 |
| chain_devil x5 | 19,500 | 3.4% | 2.0% | 350 |
| chain_devil x6 | 23,400 | 24.0% | 11.6% | 50 |

### solo

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| young_green_dragon x1 | 3,900 | 0.0% | 1.8% | 100 |
| young_blue_dragon x1 | 5,000 | 0.0% | 1.8% | 100 |
| young_red_dragon x1 | 5,900 | 0.0% | 1.8% | 100 |
| adult_white_dragon x1 | 10,000 | 0.0% | 1.8% | 100 |
| adult_black_dragon x1 | 11,500 | 0.0% | 1.8% | 100 |
| adult_green_dragon x1 | 13,000 | 0.0% | 1.8% | 100 |
| adult_blue_dragon x1 | 15,000 | 0.0% | 1.8% | 100 |
| adult_red_dragon x1 | 18,000 | 12.0% | 9.1% | 50 |
