# Party rating: fighter_20_optimized, cleric_20_optimized, rogue_20_optimized, wizard_20_optimized

Level 20, 4 PCs; benchmark v2; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 7,650 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 20 (22000 XP).

**Overall: 43,794 XP (10,948 per PC, 0.50x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 44,100 | 11,025 | 0.50 |
| ranged | 36,556 | 9,139 | 0.42 |
| caster | 30,450 | 7,612 | 0.35 |
| swarm | 46,861 | 11,715 | 0.53 |
| control | 60,000 | 15,000 | 0.68 |
| solo | 51,111 | 12,778 | 0.58 |

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
| roc x6 | 43,200 | 2.0% | 1.9% | 250 |
| roc x8 | 57,600 | 50.0% | 13.4% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| horned_devil x1 | 7,200 | 0.0% | 1.8% | 100 |
| horned_devil x2 | 14,400 | 0.0% | 1.8% | 100 |
| horned_devil x3 | 21,600 | 0.0% | 1.8% | 100 |
| horned_devil x4 | 28,800 | 0.0% | 1.8% | 100 |
| horned_devil x5 | 36,000 | 2.6% | 1.7% | 350 |
| horned_devil x6 | 43,200 | 34.0% | 12.7% | 50 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| archmage x1 | 8,400 | 0.0% | 1.8% | 100 |
| archmage x2 | 16,800 | 0.0% | 1.8% | 100 |
| archmage x3 | 25,200 | 0.0% | 1.8% | 100 |
| archmage x4 | 33,600 | 8.0% | 2.9% | 350 |

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
| frost_giant x12 | 46,800 | 4.7% | 2.0% | 450 |
| frost_giant x16 | 62,400 | 90.0% | 8.5% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| vampire x1 | 10,000 | 0.0% | 1.8% | 100 |
| vampire x2 | 20,000 | 0.0% | 1.8% | 100 |
| vampire x3 | 30,000 | 0.0% | 1.8% | 100 |
| vampire x4 | 40,000 | 0.0% | 1.8% | 100 |
| vampire x5 | 50,000 | 0.0% | 1.8% | 100 |
| vampire x6 | 60,000 | 5.0% | 1.9% | 500 |
| vampire x8 | 80,000 | 96.0% | 6.2% | 50 |

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
| ancient_green_dragon x1 | 41,000 | 2.3% | 1.8% | 300 |
| ancient_blue_dragon x1 | 50,000 | 0.0% | 1.8% | 100 |
| ancient_red_dragon x1 | 62,000 | 54.0% | 13.3% | 50 |
