# Party rating: fighter_15+items_full, cleric_15+items_full, rogue_15+items_full, wizard_15+items_full

Level 15, 4 PCs; benchmark v2; defeat threshold 5%; party strategy `default`; morale `none`; seed 1; 5,800 runs.

The rating is the encounter XP at which the party's chance of defeat (TPK, or every PC still standing dominated or out of the fight) reaches the threshold. Multiples are of the 2024 DMG High budget per character at level 15 (7800 XP).

**Overall: 26,392 XP (6,598 per PC, 0.85x High)**, the geometric mean of the types.

| Opponent type | Rating | Per PC | × High |
| --- | ---: | ---: | ---: |
| brute | 16,683 | 4,171 | 0.53 |
| ranged | 34,450 | 8,612 | 1.10 |
| caster | 30,993 | 7,748 | 0.99 |
| swarm | 22,886 | 5,721 | 0.73 |
| control | 24,414 | 6,104 | 0.78 |
| solo | 33,952 | 8,488 | 1.09 |

## Magic items

DMG-sized kits (`engine/items.py`).

- fighter_15+items_full: Belt of Storm Giant Strength, +3 Weapon, +1 Armor, Ring of Protection, Ioun Stone, Protection
- cleric_15+items_full: +3 Shield, +2 Armor, Ring of Protection, Ioun Stone, Protection, +2 Wand of the War Mage, +1 Weapon
- rogue_15+items_full: +3 Weapon, +1 Armor, Ring of Protection, Ioun Stone, Protection, Cloak of Protection
- wizard_15+items_full: Staff of Power, +2 Wand of the War Mage, Bracers of Defense

## Ladder results

Defeat chance at each benchmark step, with its 95% half-width and run count.

### brute

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| tyrannosaurus_rex x1 | 3,900 | 0.0% | 1.8% | 100 |
| tyrannosaurus_rex x2 | 7,800 | 0.0% | 1.8% | 100 |
| tyrannosaurus_rex x3 | 11,700 | 0.0% | 1.8% | 100 |
| tyrannosaurus_rex x4 | 15,600 | 0.0% | 1.8% | 100 |
| tyrannosaurus_rex x5 | 19,500 | 18.0% | 10.5% | 50 |

### ranged

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| assassin x1 | 3,900 | 0.0% | 1.8% | 100 |
| assassin x2 | 7,800 | 0.0% | 1.8% | 100 |
| assassin x3 | 11,700 | 0.0% | 1.8% | 100 |
| assassin x4 | 15,600 | 0.0% | 1.8% | 100 |
| assassin x5 | 19,500 | 0.0% | 1.8% | 100 |
| assassin x6 | 23,400 | 0.0% | 1.8% | 100 |
| assassin x8 | 31,200 | 0.0% | 1.8% | 100 |
| assassin x10 | 39,000 | 12.0% | 9.1% | 50 |

### caster

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| archmage x1 | 8,400 | 0.0% | 1.8% | 100 |
| archmage x2 | 16,800 | 0.0% | 1.8% | 100 |
| archmage x3 | 25,200 | 0.0% | 1.8% | 100 |
| archmage x4 | 33,600 | 7.2% | 2.6% | 400 |

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
| gladiator x10 | 18,000 | 0.0% | 1.8% | 100 |
| gladiator x12 | 21,600 | 0.0% | 1.8% | 100 |
| gladiator x16 | 28,800 | 28.0% | 12.1% | 50 |

### control

| Encounter | XP | Defeat | ± | Runs |
| --- | ---: | ---: | ---: | ---: |
| chain_devil x1 | 3,900 | 0.0% | 1.8% | 100 |
| chain_devil x2 | 7,800 | 0.0% | 1.8% | 100 |
| chain_devil x3 | 11,700 | 0.0% | 1.8% | 100 |
| chain_devil x4 | 15,600 | 0.0% | 1.8% | 100 |
| chain_devil x5 | 19,500 | 0.0% | 1.8% | 100 |
| chain_devil x6 | 23,400 | 0.7% | 1.8% | 150 |
| chain_devil x8 | 31,200 | 34.0% | 12.7% | 50 |

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
| adult_red_dragon x1 | 18,000 | 0.0% | 1.8% | 100 |
| ancient_white_dragon x1 | 25,000 | 0.0% | 1.8% | 100 |
| ancient_black_dragon x1 | 33,000 | 0.0% | 1.8% | 100 |
| ancient_green_dragon x1 | 41,000 | 42.0% | 13.2% | 50 |
