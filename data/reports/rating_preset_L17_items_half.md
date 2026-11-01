# Party rating: fighter_17+items_half, cleric_17+items_half, rogue_17+items_half, wizard_17+items_half

Level 17, 4 PCs; benchmark v2; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 6,750 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 17 (11700 XP).

**Overall: 37,204 XP (9,301 per PC, 0.79x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 31,049 | 7,762 | 0.66 |
| ranged | 32,200 | 8,050 | 0.69 |
| caster | 43,470 | 10,868 | 0.93 |
| swarm | 36,733 | 9,183 | 0.78 |
| control | 32,018 | 8,004 | 0.68 |
| solo | 51,875 | 12,969 | 1.11 |

## Magic items

DMG-sized kits (`engine/items.py`).

- fighter_17+items_half: Belt of Storm Giant Strength, +3 Weapon, +1 Armor, Ring of Protection, Cloak of Protection
- cleric_17+items_half: +3 Shield, +1 Armor, Ring of Protection, Ioun Stone, Protection, Cloak of Protection, +1 Weapon
- rogue_17+items_half: +3 Weapon, +1 Armor, Ring of Protection, Cloak of Protection, Stone of Good Luck
- wizard_17+items_half: Staff of Power, +2 Wand of the War Mage, Bracers of Defense

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| bone_devil x1 | 5,000 | 0.0% | 1.8% | 100 |
| bone_devil x2 | 10,000 | 0.0% | 1.8% | 100 |
| bone_devil x3 | 15,000 | 0.0% | 1.8% | 100 |
| bone_devil x4 | 20,000 | 0.0% | 1.8% | 100 |
| bone_devil x5 | 25,000 | 0.0% | 1.8% | 100 |
| bone_devil x6 | 30,000 | 1.6% | 1.7% | 250 |
| bone_devil x8 | 40,000 | 34.0% | 12.7% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| fire_giant x1 | 5,000 | 0.0% | 1.8% | 100 |
| fire_giant x2 | 10,000 | 0.0% | 1.8% | 100 |
| fire_giant x3 | 15,000 | 0.0% | 1.8% | 100 |
| fire_giant x4 | 20,000 | 0.0% | 1.8% | 100 |
| fire_giant x5 | 25,000 | 0.0% | 1.8% | 100 |
| fire_giant x6 | 30,000 | 1.3% | 2.2% | 150 |
| fire_giant x8 | 40,000 | 18.0% | 10.5% | 50 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| archmage x1 | 8,400 | 0.0% | 1.8% | 100 |
| archmage x2 | 16,800 | 0.0% | 1.8% | 100 |
| archmage x3 | 25,200 | 0.0% | 1.8% | 100 |
| archmage x4 | 33,600 | 0.0% | 1.8% | 100 |
| archmage x5 | 42,000 | 2.7% | 1.9% | 300 |
| archmage x6 | 50,400 | 16.0% | 10.1% | 50 |

### swarm

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| stone_giant x1 | 2,900 | 0.0% | 1.8% | 100 |
| stone_giant x2 | 5,800 | 0.0% | 1.8% | 100 |
| stone_giant x3 | 8,700 | 0.0% | 1.8% | 100 |
| stone_giant x4 | 11,600 | 0.0% | 1.8% | 100 |
| stone_giant x5 | 14,500 | 0.0% | 1.8% | 100 |
| stone_giant x6 | 17,400 | 0.0% | 1.8% | 100 |
| stone_giant x8 | 23,200 | 0.0% | 1.8% | 100 |
| stone_giant x10 | 29,000 | 0.0% | 1.8% | 100 |
| stone_giant x12 | 34,800 | 0.0% | 1.8% | 100 |
| stone_giant x16 | 46,400 | 30.0% | 12.3% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| chain_devil x1 | 3,900 | 0.0% | 1.8% | 100 |
| chain_devil x2 | 7,800 | 0.0% | 1.8% | 100 |
| chain_devil x3 | 11,700 | 0.0% | 1.8% | 100 |
| chain_devil x4 | 15,600 | 0.0% | 1.8% | 100 |
| chain_devil x5 | 19,500 | 0.0% | 1.8% | 100 |
| chain_devil x6 | 23,400 | 0.0% | 1.8% | 100 |
| chain_devil x8 | 31,200 | 0.7% | 1.8% | 150 |
| chain_devil x10 | 39,000 | 42.0% | 13.2% | 50 |

### solo

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| young_blue_dragon x1 | 5,000 | 0.0% | 1.8% | 100 |
| young_red_dragon x1 | 5,900 | 0.0% | 1.8% | 100 |
| adult_white_dragon x1 | 10,000 | 0.0% | 1.8% | 100 |
| adult_black_dragon x1 | 11,500 | 0.0% | 1.8% | 100 |
| adult_green_dragon x1 | 13,000 | 0.0% | 1.8% | 100 |
| adult_blue_dragon x1 | 15,000 | 0.0% | 1.8% | 100 |
| adult_red_dragon x1 | 18,000 | 0.0% | 1.8% | 100 |
| ancient_white_dragon x1 | 25,000 | 0.0% | 1.8% | 100 |
| ancient_black_dragon x1 | 33,000 | 0.0% | 1.8% | 100 |
| ancient_green_dragon x1 | 41,000 | 0.0% | 1.8% | 100 |
| ancient_blue_dragon x1 | 50,000 | 0.0% | 1.8% | 100 |
| ancient_red_dragon x1 | 62,000 | 32.0% | 12.5% | 50 |
