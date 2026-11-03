# Party rating: fighter_20, cleric_20, rogue_20, wizard_20

Level 20, 4 PCs; benchmark v2; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 5,200 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 20 (22000 XP).

**Overall: 41,720 XP (10,430 per PC, 0.47x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 45,095 | 11,274 | 0.51 |
| ranged | 38,455 | 9,614 | 0.44 |
| caster | 35,082 | 8,771 | 0.40 |
| swarm | 47,658 | 11,914 | 0.54 |
| control | 45,357 | 11,339 | 0.52 |
| solo | 40,097 | 10,024 | 0.46 |

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| roc x1 | 7,200 | 0.0% | 1.8% | 100 |
| roc x2 | 14,400 | 0.0% | 1.8% | 100 |
| roc x3 | 21,600 | 0.0% | 1.8% | 100 |
| roc x4 | 28,800 | 0.0% | 1.8% | 100 |
| roc x5 | 36,000 | 0.0% | 1.8% | 100 |
| roc x6 | 43,200 | 0.0% | 1.8% | 100 |
| roc x8 | 57,600 | 38.0% | 13.0% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| horned_devil x1 | 7,200 | 0.0% | 1.8% | 100 |
| horned_devil x2 | 14,400 | 0.0% | 1.8% | 100 |
| horned_devil x3 | 21,600 | 0.0% | 1.8% | 100 |
| horned_devil x4 | 28,800 | 0.0% | 1.8% | 100 |
| horned_devil x5 | 36,000 | 0.0% | 1.8% | 100 |
| horned_devil x6 | 43,200 | 14.7% | 5.7% | 150 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| archmage x1 | 8,400 | 0.0% | 1.8% | 100 |
| archmage x2 | 16,800 | 0.0% | 1.8% | 100 |
| archmage x3 | 25,200 | 0.0% | 1.8% | 100 |
| archmage x4 | 33,600 | 2.0% | 1.9% | 250 |
| archmage x5 | 42,000 | 19.0% | 7.6% | 100 |

### swarm

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| frost_giant x1 | 3,900 | 0.0% | 1.8% | 100 |
| frost_giant x2 | 7,800 | 0.0% | 1.8% | 100 |
| frost_giant x3 | 11,700 | 0.0% | 1.8% | 100 |
| frost_giant x4 | 15,600 | 0.0% | 1.8% | 100 |
| frost_giant x5 | 19,500 | 0.0% | 1.8% | 100 |
| frost_giant x6 | 23,400 | 0.0% | 1.8% | 100 |
| frost_giant x8 | 31,200 | 0.0% | 1.8% | 100 |
| frost_giant x10 | 39,000 | 0.0% | 1.8% | 100 |
| frost_giant x12 | 46,800 | 1.3% | 2.2% | 150 |
| frost_giant x16 | 62,400 | 68.0% | 12.5% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| vampire x1 | 10,000 | 0.0% | 1.8% | 100 |
| vampire x2 | 20,000 | 0.0% | 1.8% | 100 |
| vampire x3 | 30,000 | 0.0% | 1.8% | 100 |
| vampire x4 | 40,000 | 0.0% | 1.8% | 100 |
| vampire x5 | 50,000 | 9.3% | 4.7% | 150 |

### solo

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| adult_white_dragon x1 | 10,000 | 0.0% | 1.8% | 100 |
| adult_black_dragon x1 | 11,500 | 0.0% | 1.8% | 100 |
| adult_green_dragon x1 | 13,000 | 0.0% | 1.8% | 100 |
| adult_blue_dragon x1 | 15,000 | 0.0% | 1.8% | 100 |
| adult_red_dragon x1 | 18,000 | 0.0% | 1.8% | 100 |
| ancient_white_dragon x1 | 25,000 | 0.0% | 1.8% | 100 |
| ancient_black_dragon x1 | 33,000 | 0.0% | 1.8% | 100 |
| ancient_green_dragon x1 | 41,000 | 5.6% | 1.9% | 550 |
| ancient_blue_dragon x1 | 50,000 | 0.0% | 1.8% | 100 |
| ancient_red_dragon x1 | 62,000 | 64.0% | 12.9% | 50 |
