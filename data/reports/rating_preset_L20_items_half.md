# Party rating: fighter_20+items_half, cleric_20+items_half, rogue_20+items_half, wizard_20+items_half

Level 20, 4 PCs; benchmark v2; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 6,900 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 20 (22000 XP).

**Overall: 61,429 XP (15,357 per PC, 0.70x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 59,727 | 14,932 | 0.68 |
| ranged | 57,979 | 14,495 | 0.66 |
| caster | 54,166 | 13,541 | 0.62 |
| swarm | 64,453 | 16,113 | 0.73 |
| control | 81,200 | 20,300 | 0.92 |
| solo | 54,737 | 13,684 | 0.62 |

## Magic items

DMG-sized kits (`engine/items.py`).

- fighter_20+items_half: Belt of Storm Giant Strength, +3 Weapon, +2 Armor, Ring of Protection, Ioun Stone, Protection
- cleric_20+items_half: +3 Armor, +3 Shield, +3 Wand of the War Mage, Ring of Protection, Ioun Stone, Protection, +1 Weapon
- rogue_20+items_half: +3 Armor, +3 Weapon, Ring of Protection, Ioun Stone, Protection, Cloak of Protection
- wizard_20+items_half: Robe of the Archmagi, Staff of Power, +3 Wand of the War Mage

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
| roc x8 | 57,600 | 0.7% | 1.8% | 150 |
| roc x10 | 72,000 | 30.0% | 12.3% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| horned_devil x1 | 7,200 | 0.0% | 1.8% | 100 |
| horned_devil x2 | 14,400 | 0.0% | 1.8% | 100 |
| horned_devil x3 | 21,600 | 0.0% | 1.8% | 100 |
| horned_devil x4 | 28,800 | 0.0% | 1.8% | 100 |
| horned_devil x5 | 36,000 | 0.0% | 1.8% | 100 |
| horned_devil x6 | 43,200 | 0.0% | 1.8% | 100 |
| horned_devil x8 | 57,600 | 4.0% | 2.0% | 400 |
| horned_devil x10 | 72,000 | 42.0% | 13.2% | 50 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| archmage x1 | 8,400 | 0.0% | 1.8% | 100 |
| archmage x2 | 16,800 | 0.0% | 1.8% | 100 |
| archmage x3 | 25,200 | 0.0% | 1.8% | 100 |
| archmage x4 | 33,600 | 0.0% | 1.8% | 100 |
| archmage x5 | 42,000 | 0.0% | 1.8% | 100 |
| archmage x6 | 50,400 | 0.7% | 1.8% | 150 |
| archmage x8 | 67,200 | 20.0% | 10.9% | 50 |

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
| frost_giant x12 | 46,800 | 0.0% | 1.8% | 100 |
| frost_giant x16 | 62,400 | 0.0% | 1.8% | 100 |
| frost_giant x20 | 78,000 | 38.0% | 13.0% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| vampire x1 | 10,000 | 0.0% | 1.8% | 100 |
| vampire x2 | 20,000 | 0.0% | 1.8% | 100 |
| vampire x3 | 30,000 | 0.0% | 1.8% | 100 |
| vampire x4 | 40,000 | 0.0% | 1.8% | 100 |
| vampire x5 | 50,000 | 0.0% | 1.8% | 100 |
| vampire x6 | 60,000 | 0.0% | 1.8% | 100 |
| vampire x8 | 80,000 | 2.0% | 1.7% | 300 |
| vampire x10 | 100,000 | 52.0% | 13.3% | 50 |

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
| ancient_green_dragon x1 | 41,000 | 0.0% | 1.8% | 100 |
| ancient_blue_dragon x1 | 50,000 | 0.0% | 1.8% | 100 |
| ancient_red_dragon x1 | 62,000 | 12.7% | 5.3% | 150 |
