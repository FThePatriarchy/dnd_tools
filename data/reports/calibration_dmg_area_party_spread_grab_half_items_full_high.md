# DMG 2024 budget calibration

Party: fighter, cleric, rogue, wizard at each level; single encounter from full resources; default DayOptions; 100 runs per composition, seed 1. Groups are one monster type, 75%-100% of budget, at most 8 creatures. 'Over' is 1.5x High, a probe beyond the DMG categories.

Area rule: `party_spread` — Monster areas use the halved count (the party spreads out); party areas keep the DMG count (engine default).

Grab rule: `grab_half` — A grab reaches at most half the target group, rounded up: 2 of a party of 4 (engine default).

Morale: `none` — Engine default: monsters fight to the last. Fled is the share of monsters that fled.

Magic items: `full` — DMG-sized kits (`engine/items.py`, 100% of the uncommon-and-better items awarded by this level kept as combat items):

- Level 11: fighter +3 Weapon, Belt of Hill Giant Strength, Cloak of Protection, Stone of Good Luck; cleric +2 Shield, +1 Armor, Cloak of Protection, Stone of Good Luck, +1 Wand of the War Mage, +1 Weapon; rogue +2 Weapon, +1 Armor, Cloak of Protection, Stone of Good Luck; wizard +2 Wand of the War Mage, Bracers of Defense, Cloak of Protection
- Level 13: fighter +3 Weapon, Belt of Hill Giant Strength, +1 Armor, Ring of Protection, Cloak of Protection; cleric +3 Shield, +1 Armor, Ring of Protection, Cloak of Protection, Stone of Good Luck, +1 Weapon; rogue +3 Weapon, +1 Armor, Ring of Protection, Cloak of Protection, Stone of Good Luck; wizard +2 Wand of the War Mage, Bracers of Defense, Ring of Protection
- Level 15: fighter Belt of Storm Giant Strength, +3 Weapon, +1 Armor, Ring of Protection, Ioun Stone, Protection; cleric +3 Shield, +2 Armor, Ring of Protection, Ioun Stone, Protection, +2 Wand of the War Mage, +1 Weapon; rogue +3 Weapon, +1 Armor, Ring of Protection, Ioun Stone, Protection, Cloak of Protection; wizard Staff of Power, +2 Wand of the War Mage, Bracers of Defense
- Level 17: fighter Belt of Storm Giant Strength, +3 Weapon, +2 Armor, Ring of Protection, Ioun Stone, Protection; cleric +3 Armor, +3 Shield, +3 Wand of the War Mage, Ring of Protection, Ioun Stone, Protection, +1 Weapon; rogue +3 Weapon, +2 Armor, Ring of Protection, Ioun Stone, Protection, Cloak of Protection; wizard Staff of Power, +3 Wand of the War Mage, Bracers of Defense
- Level 20: fighter Belt of Storm Giant Strength, +3 Armor, +3 Weapon, Ring of Protection, Ioun Stone, Protection; cleric +3 Armor, Ioun Stone, Mastery, +3 Shield, +3 Wand of the War Mage, Ring of Protection, +1 Weapon; rogue +3 Armor, Ioun Stone, Mastery, +3 Weapon, Ring of Protection, Ioun Stone, Protection; wizard Robe of the Archmagi, Ioun Stone, Mastery, Staff of Power

TPK: every PC at 0 HP. Defeat: the party loses, either by TPK or with every PC still standing dominated or otherwise out of the fight.

## Summary (mean across compositions, [min-max] in brackets)

| Level | Difficulty | Groups | Win | Any down | Any death | TPK | Defeat | HP lost | Slots spent | Rounds | Fled |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 11 | low | 6 | 100% [98%-100%] | 9% [0%-21%] | 1% [0%-2%] | 0% [0%-1%] | 0% [0%-2%] | 19% [12%-33%] | 15% [11%-21%] | 3.0 [1.7-5.6] | 0% [0%-0%] |
| 11 | moderate | 6 | 100% [98%-100%] | 34% [0%-91%] | 2% [0%-5%] | 0% [0%-1%] | 0% [0%-2%] | 20% [11%-29%] | 18% [13%-26%] | 2.9 [1.7-4.2] | 0% [0%-0%] |
| 11 | high | 6 | 85% [25%-100%] | 62% [7%-100%] | 17% [0%-78%] | 14% [0%-75%] | 15% [0%-75%] | 42% [20%-91%] | 22% [11%-31%] | 3.9 [2.1-5.8] | 0% [0%-0%] |
| 11 | over | 6 | 56% [2%-99%] | 90% [74%-100%] | 46% [1%-98%] | 40% [1%-98%] | 44% [1%-98%] | 64% [25%-100%] | 28% [12%-40%] | 5.3 [3.5-7.0] | 0% [0%-0%] |
| 13 | low | 6 | 100% [99%-100%] | 10% [0%-33%] | 0% [0%-3%] | 0% [0%-1%] | 0% [0%-1%] | 9% [1%-15%] | 20% [13%-37%] | 2.8 [1.9-4.7] | 0% [0%-0%] |
| 13 | moderate | 6 | 99% [94%-100%] | 32% [1%-88%] | 1% [0%-8%] | 1% [0%-6%] | 1% [0%-6%] | 20% [10%-49%] | 21% [12%-26%] | 3.0 [1.8-4.3] | 0% [0%-0%] |
| 13 | high | 6 | 84% [23%-100%] | 55% [7%-91%] | 18% [0%-84%] | 6% [0%-31%] | 16% [0%-77%] | 37% [18%-74%] | 28% [20%-33%] | 4.6 [2.7-7.1] | 0% [0%-0%] |
| 13 | over | 6 | 74% [0%-100%] | 82% [35%-100%] | 31% [0%-100%] | 26% [0%-100%] | 26% [0%-100%] | 57% [16%-100%] | 35% [19%-48%] | 6.6 [3.3-10.2] | 0% [0%-0%] |
| 15 | low | 6 | 100% [97%-100%] | 3% [0%-11%] | 0% [0%-3%] | 0% [0%-0%] | 0% [0%-3%] | 10% [1%-21%] | 16% [12%-22%] | 2.6 [1.9-3.7] | 0% [0%-0%] |
| 15 | moderate | 6 | 92% [58%-100%] | 21% [0%-60%] | 9% [0%-48%] | 2% [0%-8%] | 8% [0%-42%] | 23% [13%-53%] | 22% [16%-32%] | 3.7 [2.3-6.7] | 0% [0%-0%] |
| 15 | high | 6 | 83% [0%-100%] | 64% [7%-100%] | 18% [0%-100%] | 17% [0%-100%] | 17% [0%-100%] | 44% [16%-100%] | 28% [17%-35%] | 5.1 [2.7-7.8] | 0% [0%-0%] |
| 15 | over | 6 | 48% [0%-99%] | 87% [65%-100%] | 51% [1%-81%] | 36% [1%-76%] | 52% [1%-100%] | 66% [20%-89%] | 33% [14%-50%] | 7.3 [2.3-12.2] | 0% [0%-0%] |
| 17 | low | 6 | 100% [100%-100%] | 1% [0%-4%] | 0% [0%-0%] | 0% [0%-0%] | 0% [0%-0%] | 11% [6%-24%] | 13% [11%-15%] | 1.9 [1.5-2.4] | 0% [0%-0%] |
| 17 | moderate | 6 | 100% [100%-100%] | 22% [1%-55%] | 0% [0%-0%] | 0% [0%-0%] | 0% [0%-0%] | 20% [13%-32%] | 17% [11%-22%] | 2.4 [1.6-3.2] | 0% [0%-0%] |
| 17 | high | 6 | 82% [0%-100%] | 51% [3%-92%] | 15% [0%-70%] | 3% [0%-9%] | 18% [0%-100%] | 36% [13%-60%] | 24% [15%-37%] | 4.5 [2.4-7.4] | 0% [0%-0%] |
| 17 | over | 6 | 24% [0%-69%] | 97% [84%-100%] | 78% [35%-100%] | 76% [31%-100%] | 76% [31%-100%] | 89% [72%-100%] | 21% [7%-31%] | 4.7 [1.6-6.8] | 0% [0%-0%] |
| 20 | low | 6 | 100% [100%-100%] | 0% [0%-2%] | 0% [0%-0%] | 0% [0%-0%] | 0% [0%-0%] | 10% [1%-24%] | 10% [8%-14%] | 1.7 [1.1-2.2] | 0% [0%-0%] |
| 20 | moderate | 6 | 84% [1%-100%] | 36% [2%-88%] | 14% [0%-80%] | 2% [0%-12%] | 16% [0%-99%] | 29% [17%-64%] | 18% [14%-28%] | 3.1 [2.4-4.6] | 0% [0%-0%] |
| 20 | high | 6 | 29% [0%-70%] | 100% [98%-100%] | 76% [34%-100%] | 71% [30%-100%] | 71% [30%-100%] | 88% [67%-100%] | 20% [7%-28%] | 4.7 [1.6-7.8] | 0% [0%-0%] |
| 20 | over | 6 | 13% [0%-80%] | 91% [44%-100%] | 88% [25%-100%] | 87% [20%-100%] | 87% [20%-100%] | 93% [56%-100%] | 12% [5%-27%] | 2.8 [1.3-5.1] | 0% [0%-0%] |

## Per composition

Runs is the number of runs used; ± is the 95% half-width of the defeat estimate.

| Level | Difficulty | Encounter | XP / budget | Runs | ± | Win | Any down | Any death | TPK | Defeat | HP lost | Slots spent | Rounds | Fled |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 11 | low | guard_captain x6 | 6600 / 7600 | 100 | 1.8% | 100% | 9% | 0% | 0% | 0% | 15% | 16% | 2.6 | 0% |
| 11 | low | fire_elemental x4 | 7200 / 7600 | 100 | 1.8% | 100% | 2% | 0% | 0% | 0% | 24% | 21% | 5.6 | 0% |
| 11 | low | water_elemental x4 | 7200 / 7600 | 100 | 2.6% | 99% | 21% | 2% | 1% | 1% | 33% | 17% | 3.7 | 0% |
| 11 | low | wyvern x3 | 6900 / 7600 | 100 | 1.8% | 100% | 13% | 0% | 0% | 0% | 13% | 15% | 2.3 | 0% |
| 11 | low | aboleth x1 | 5900 / 7600 | 100 | 3.2% | 98% | 8% | 2% | 0% | 2% | 15% | 13% | 2.0 | 0% |
| 11 | low | roc x1 | 7200 / 7600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 12% | 11% | 1.7 | 0% |
| 11 | moderate | air_elemental x6 | 10800 / 11600 | 100 | 1.8% | 100% | 85% | 0% | 0% | 0% | 25% | 26% | 4.2 | 0% |
| 11 | moderate | hill_giant x6 | 10800 / 11600 | 100 | 2.6% | 99% | 91% | 5% | 1% | 1% | 29% | 26% | 4.2 | 0% |
| 11 | moderate | wraith x6 | 10800 / 11600 | 100 | 1.8% | 100% | 4% | 4% | 0% | 0% | 15% | 13% | 2.8 | 0% |
| 11 | moderate | mind_flayer x4 | 11600 / 11600 | 100 | 3.2% | 98% | 19% | 2% | 1% | 2% | 26% | 15% | 2.6 | 0% |
| 11 | moderate | clay_golem x2 | 10000 / 11600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 11% | 13% | 2.0 | 0% |
| 11 | moderate | adult_black_dragon x1 | 11500 / 11600 | 100 | 1.8% | 100% | 3% | 0% | 0% | 0% | 16% | 13% | 1.7 | 0% |
| 11 | high | mage x7 | 16100 / 16400 | 100 | 8.4% | 25% | 100% | 78% | 75% | 75% | 91% | 11% | 3.6 | 0% |
| 11 | high | mind_flayer x5 | 14500 / 16400 | 100 | 6.4% | 88% | 48% | 14% | 4% | 12% | 43% | 18% | 3.2 | 0% |
| 11 | high | chain_devil x4 | 15600 / 16400 | 100 | 2.6% | 99% | 81% | 1% | 1% | 1% | 25% | 31% | 5.8 | 0% |
| 11 | high | bone_devil x3 | 15000 / 16400 | 100 | 3.7% | 97% | 87% | 8% | 3% | 3% | 43% | 30% | 5.3 | 0% |
| 11 | high | horned_devil x2 | 14400 / 16400 | 100 | 1.8% | 100% | 46% | 0% | 0% | 0% | 20% | 24% | 3.4 | 0% |
| 11 | high | adult_blue_dragon x1 | 15000 / 16400 | 100 | 1.8% | 100% | 7% | 1% | 0% | 0% | 32% | 16% | 2.1 | 0% |
| 11 | over | mind_flayer x8 | 23200 / 24600 | 100 | 6.0% | 10% | 98% | 90% | 69% | 90% | 94% | 12% | 3.5 | 0% |
| 11 | over | chain_devil x6 | 23400 / 24600 | 100 | 3.2% | 2% | 100% | 98% | 98% | 98% | 100% | 28% | 7.0 | 0% |
| 11 | over | young_green_dragon x6 | 23400 / 24600 | 100 | 9.6% | 45% | 87% | 58% | 55% | 55% | 75% | 26% | 5.2 | 0% |
| 11 | over | young_blue_dragon x4 | 20000 / 24600 | 100 | 2.6% | 99% | 74% | 1% | 1% | 1% | 25% | 31% | 5.0 | 0% |
| 11 | over | horned_devil x3 | 21600 / 24600 | 100 | 6.2% | 89% | 89% | 17% | 11% | 11% | 47% | 40% | 6.7 | 0% |
| 11 | over | adult_black_dragon x2 | 23000 / 24600 | 100 | 4.8% | 94% | 93% | 11% | 6% | 6% | 45% | 33% | 4.5 | 0% |
| 13 | low | air_elemental x5 | 9000 / 10400 | 100 | 1.8% | 100% | 17% | 0% | 0% | 0% | 14% | 20% | 2.9 | 0% |
| 13 | low | troll x5 | 9000 / 10400 | 100 | 2.6% | 99% | 33% | 3% | 1% | 1% | 15% | 37% | 4.7 | 0% |
| 13 | low | wyvern x4 | 9200 / 10400 | 100 | 1.8% | 100% | 7% | 0% | 0% | 0% | 9% | 20% | 2.5 | 0% |
| 13 | low | chain_devil x2 | 7800 / 10400 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 1% | 13% | 1.9 | 0% |
| 13 | low | clay_golem x2 | 10000 / 10400 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 5% | 16% | 2.2 | 0% |
| 13 | low | vampire x1 | 10000 / 10400 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 8% | 15% | 2.6 | 0% |
| 13 | moderate | mage x7 | 16100 / 16800 | 100 | 4.8% | 94% | 88% | 8% | 6% | 6% | 49% | 24% | 4.3 | 0% |
| 13 | moderate | stone_giant x5 | 14500 / 16800 | 100 | 1.8% | 100% | 42% | 0% | 0% | 0% | 17% | 26% | 3.4 | 0% |
| 13 | moderate | frost_giant x4 | 15600 / 16800 | 100 | 1.8% | 100% | 45% | 0% | 0% | 0% | 16% | 23% | 3.0 | 0% |
| 13 | moderate | clay_golem x3 | 15000 / 16800 | 100 | 1.8% | 100% | 1% | 0% | 0% | 0% | 10% | 18% | 2.5 | 0% |
| 13 | moderate | roc x2 | 14400 / 16800 | 100 | 1.8% | 100% | 12% | 0% | 0% | 0% | 16% | 22% | 3.2 | 0% |
| 13 | moderate | adult_blue_dragon x1 | 15000 / 16800 | 100 | 1.8% | 100% | 1% | 0% | 0% | 0% | 13% | 12% | 1.8 | 0% |
| 13 | high | mind_flayer x7 | 20300 / 21600 | 100 | 7.8% | 80% | 55% | 20% | 3% | 20% | 47% | 21% | 3.6 | 0% |
| 13 | high | chain_devil x5 | 19500 / 21600 | 100 | 1.8% | 100% | 77% | 1% | 0% | 0% | 18% | 33% | 6.0 | 0% |
| 13 | high | bone_devil x4 | 20000 / 21600 | 100 | 3.2% | 98% | 71% | 5% | 2% | 2% | 33% | 32% | 4.9 | 0% |
| 13 | high | aboleth x3 | 17700 / 21600 | 100 | 8.2% | 23% | 91% | 84% | 31% | 77% | 74% | 31% | 7.1 | 0% |
| 13 | high | archmage x2 | 16800 / 21600 | 100 | 1.8% | 100% | 7% | 0% | 0% | 0% | 23% | 20% | 2.7 | 0% |
| 13 | high | adult_red_dragon x1 | 18000 / 21600 | 100 | 1.8% | 100% | 28% | 1% | 0% | 0% | 29% | 29% | 3.4 | 0% |
| 13 | over | assassin x8 | 31200 / 32400 | 100 | 7.8% | 80% | 100% | 25% | 20% | 20% | 62% | 34% | 5.8 | 0% |
| 13 | over | tyrannosaurus_rex x8 | 31200 / 32400 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 19% | 4.0 | 0% |
| 13 | over | young_blue_dragon x6 | 30000 / 32400 | 100 | 5.2% | 93% | 97% | 18% | 7% | 7% | 47% | 42% | 7.5 | 0% |
| 13 | over | horned_devil x4 | 28800 / 32400 | 100 | 8.3% | 76% | 98% | 33% | 24% | 24% | 57% | 48% | 8.9 | 0% |
| 13 | over | vampire x3 | 30000 / 32400 | 100 | 1.8% | 100% | 35% | 0% | 0% | 0% | 16% | 45% | 10.2 | 0% |
| 13 | over | ancient_white_dragon x1 | 25000 / 32400 | 100 | 5.4% | 92% | 60% | 8% | 8% | 8% | 60% | 21% | 3.3 | 0% |
| 15 | low | air_elemental x7 | 12600 / 13200 | 100 | 1.8% | 100% | 11% | 0% | 0% | 0% | 12% | 17% | 2.4 | 0% |
| 15 | low | vampire_spawn x7 | 12600 / 13200 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 4% | 14% | 2.4 | 0% |
| 15 | low | mind_flayer x4 | 11600 / 13200 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 1% | 12% | 1.9 | 0% |
| 15 | low | hezrou x3 | 11700 / 13200 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 10% | 19% | 3.2 | 0% |
| 15 | low | aboleth x2 | 11800 / 13200 | 100 | 3.7% | 97% | 8% | 3% | 0% | 3% | 21% | 22% | 3.7 | 0% |
| 15 | low | purple_worm x1 | 13000 / 13200 | 100 | 1.8% | 100% | 1% | 0% | 0% | 0% | 10% | 14% | 2.1 | 0% |
| 15 | moderate | mind_flayer x7 | 20300 / 21600 | 100 | 4.8% | 94% | 11% | 6% | 3% | 6% | 19% | 16% | 2.5 | 0% |
| 15 | moderate | chain_devil x5 | 19500 / 21600 | 100 | 1.8% | 100% | 22% | 0% | 0% | 0% | 13% | 24% | 4.4 | 0% |
| 15 | moderate | bone_devil x4 | 20000 / 21600 | 100 | 1.8% | 100% | 32% | 0% | 0% | 0% | 19% | 24% | 3.7 | 0% |
| 15 | moderate | aboleth x3 | 17700 / 21600 | 100 | 9.5% | 58% | 60% | 48% | 8% | 42% | 53% | 32% | 6.7 | 0% |
| 15 | moderate | archmage x2 | 16800 / 21600 | 100 | 1.8% | 100% | 1% | 0% | 0% | 0% | 16% | 17% | 2.4 | 0% |
| 15 | moderate | adult_red_dragon x1 | 18000 / 21600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 20% | 20% | 2.3 | 0% |
| 15 | high | assassin x8 | 31200 / 31200 | 100 | 2.6% | 99% | 96% | 2% | 1% | 1% | 37% | 29% | 4.3 | 0% |
| 15 | high | tyrannosaurus_rex x8 | 31200 / 31200 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 21% | 4.9 | 0% |
| 15 | high | young_blue_dragon x6 | 30000 / 31200 | 100 | 1.8% | 100% | 86% | 5% | 0% | 0% | 32% | 31% | 5.4 | 0% |
| 15 | high | horned_devil x4 | 28800 / 31200 | 100 | 2.6% | 99% | 77% | 3% | 1% | 1% | 28% | 35% | 5.6 | 0% |
| 15 | high | vampire x3 | 30000 / 31200 | 100 | 1.8% | 100% | 7% | 0% | 0% | 0% | 16% | 32% | 7.8 | 0% |
| 15 | high | ancient_white_dragon x1 | 25000 / 31200 | 100 | 1.8% | 100% | 20% | 1% | 0% | 0% | 51% | 17% | 2.7 | 0% |
| 15 | over | aboleth x7 | 41300 / 46800 | 100 | 1.8% | 0% | 77% | 74% | 3% | 100% | 57% | 14% | 2.3 | 0% |
| 15 | over | horned_devil x6 | 43200 / 46800 | 100 | 8.3% | 24% | 100% | 81% | 76% | 76% | 89% | 38% | 8.4 | 0% |
| 15 | over | archpriest x5 | 42000 / 46800 | 100 | 9.5% | 42% | 100% | 62% | 58% | 58% | 80% | 45% | 8.1 | 0% |
| 15 | over | vampire x4 | 40000 / 46800 | 100 | 2.6% | 99% | 65% | 1% | 1% | 1% | 20% | 50% | 12.2 | 0% |
| 15 | over | purple_worm x3 | 39000 / 46800 | 100 | 9.4% | 61% | 98% | 45% | 39% | 39% | 68% | 32% | 8.5 | 0% |
| 15 | over | ancient_green_dragon x1 | 41000 / 46800 | 100 | 9.4% | 60% | 84% | 41% | 40% | 40% | 81% | 22% | 4.2 | 0% |
| 17 | low | mage x7 | 16100 / 18000 | 100 | 1.8% | 100% | 4% | 0% | 0% | 0% | 24% | 12% | 1.8 | 0% |
| 17 | low | stone_giant x6 | 17400 / 18000 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 6% | 11% | 1.6 | 0% |
| 17 | low | hezrou x4 | 15600 / 18000 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 7% | 12% | 2.0 | 0% |
| 17 | low | fire_giant x3 | 15000 / 18000 | 100 | 1.8% | 100% | 2% | 0% | 0% | 0% | 9% | 15% | 2.4 | 0% |
| 17 | low | horned_devil x2 | 14400 / 18000 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 8% | 12% | 2.0 | 0% |
| 17 | low | adult_red_dragon x1 | 18000 / 18000 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 11% | 14% | 1.5 | 0% |
| 17 | moderate | assassin x7 | 27300 / 28800 | 100 | 1.8% | 100% | 55% | 0% | 0% | 0% | 23% | 20% | 3.0 | 0% |
| 17 | moderate | tyrannosaurus_rex x7 | 27300 / 28800 | 100 | 1.8% | 100% | 28% | 0% | 0% | 0% | 16% | 11% | 1.6 | 0% |
| 17 | moderate | fire_giant x5 | 25000 / 28800 | 100 | 1.8% | 100% | 40% | 0% | 0% | 0% | 17% | 22% | 3.2 | 0% |
| 17 | moderate | young_red_dragon x4 | 23600 / 28800 | 100 | 1.8% | 100% | 5% | 0% | 0% | 0% | 20% | 16% | 2.5 | 0% |
| 17 | moderate | archpriest x3 | 25200 / 28800 | 100 | 1.8% | 100% | 4% | 0% | 0% | 0% | 13% | 19% | 2.3 | 0% |
| 17 | moderate | ancient_white_dragon x1 | 25000 / 28800 | 100 | 1.8% | 100% | 1% | 0% | 0% | 0% | 32% | 11% | 2.0 | 0% |
| 17 | high | aboleth x7 | 41300 / 46800 | 100 | 1.8% | 0% | 76% | 70% | 9% | 100% | 60% | 15% | 2.9 | 0% |
| 17 | high | horned_devil x6 | 43200 / 46800 | 100 | 5.2% | 93% | 92% | 14% | 7% | 7% | 43% | 37% | 7.4 | 0% |
| 17 | high | archpriest x5 | 42000 / 46800 | 100 | 3.2% | 98% | 71% | 5% | 2% | 2% | 30% | 31% | 4.3 | 0% |
| 17 | high | vampire x4 | 40000 / 46800 | 100 | 1.8% | 100% | 3% | 0% | 0% | 0% | 13% | 25% | 6.9 | 0% |
| 17 | high | purple_worm x3 | 39000 / 46800 | 100 | 1.8% | 100% | 47% | 0% | 0% | 0% | 21% | 16% | 3.0 | 0% |
| 17 | high | ancient_green_dragon x1 | 41000 / 46800 | 100 | 2.6% | 99% | 17% | 1% | 1% | 1% | 47% | 18% | 2.4 | 0% |
| 17 | over | archmage x8 | 67200 / 70200 | 100 | 7.0% | 15% | 96% | 85% | 85% | 85% | 93% | 10% | 3.1 | 0% |
| 17 | over | adult_white_dragon x7 | 70000 / 70200 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 7% | 1.6 | 0% |
| 17 | over | adult_black_dragon x6 | 69000 / 70200 | 100 | 7.0% | 15% | 100% | 89% | 85% | 85% | 95% | 26% | 5.2 | 0% |
| 17 | over | purple_worm x5 | 65000 / 70200 | 100 | 9.6% | 48% | 100% | 62% | 52% | 52% | 73% | 26% | 6.8 | 0% |
| 17 | over | adult_red_dragon x3 | 54000 / 70200 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 24% | 6.5 | 0% |
| 17 | over | ancient_red_dragon x1 | 62000 / 70200 | 100 | 8.9% | 69% | 84% | 35% | 31% | 31% | 72% | 31% | 5.1 | 0% |
| 20 | low | mind_flayer x8 | 23200 / 25600 | 100 | 1.8% | 100% | 1% | 0% | 0% | 0% | 1% | 9% | 1.2 | 0% |
| 20 | low | frost_giant x6 | 23400 / 25600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 5% | 8% | 1.1 | 0% |
| 20 | low | bone_devil x5 | 25000 / 25600 | 100 | 1.8% | 100% | 2% | 0% | 0% | 0% | 10% | 14% | 2.2 | 0% |
| 20 | low | stone_golem x4 | 23600 / 25600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 7% | 10% | 2.0 | 0% |
| 20 | low | archmage x3 | 25200 / 25600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 11% | 9% | 1.8 | 0% |
| 20 | low | ancient_white_dragon x1 | 25000 / 25600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 24% | 12% | 1.8 | 0% |
| 20 | moderate | aboleth x8 | 47200 / 52800 | 100 | 2.6% | 1% | 88% | 80% | 12% | 99% | 64% | 14% | 3.3 | 0% |
| 20 | moderate | horned_devil x7 | 50400 / 52800 | 100 | 1.8% | 100% | 48% | 0% | 0% | 0% | 24% | 28% | 4.6 | 0% |
| 20 | moderate | archpriest x6 | 50400 / 52800 | 100 | 1.8% | 100% | 21% | 0% | 0% | 0% | 22% | 20% | 3.2 | 0% |
| 20 | moderate | adult_black_dragon x4 | 46000 / 52800 | 100 | 1.8% | 100% | 30% | 1% | 0% | 0% | 25% | 16% | 2.8 | 0% |
| 20 | moderate | adult_blue_dragon x3 | 45000 / 52800 | 100 | 1.8% | 100% | 25% | 0% | 0% | 0% | 24% | 14% | 2.6 | 0% |
| 20 | moderate | ancient_blue_dragon x1 | 50000 / 52800 | 100 | 1.8% | 100% | 2% | 0% | 0% | 0% | 17% | 16% | 2.4 | 0% |
| 20 | high | adult_white_dragon x8 | 80000 / 88000 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 7% | 1.6 | 0% |
| 20 | high | adult_black_dragon x7 | 80500 / 88000 | 100 | 9.6% | 46% | 100% | 64% | 54% | 54% | 83% | 26% | 6.2 | 0% |
| 20 | high | purple_worm x6 | 78000 / 88000 | 100 | 9.1% | 34% | 99% | 78% | 66% | 66% | 82% | 28% | 7.8 | 0% |
| 20 | high | adult_blue_dragon x5 | 75000 / 88000 | 100 | 8.8% | 70% | 100% | 34% | 30% | 30% | 67% | 23% | 5.3 | 0% |
| 20 | high | ancient_white_dragon x3 | 75000 / 88000 | 100 | 4.5% | 5% | 100% | 96% | 95% | 95% | 99% | 14% | 3.2 | 0% |
| 20 | high | ancient_green_dragon x2 | 82000 / 88000 | 100 | 7.6% | 19% | 98% | 84% | 81% | 81% | 95% | 19% | 4.2 | 0% |
| 20 | over | adult_blue_dragon x8 | 120000 / 132000 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 10% | 2.2 | 0% |
| 20 | over | adult_red_dragon x7 | 126000 / 132000 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 5% | 2.0 | 0% |
| 20 | over | ancient_white_dragon x5 | 125000 / 132000 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 7% | 1.3 | 0% |
| 20 | over | ancient_green_dragon x3 | 123000 / 132000 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 10% | 2.1 | 0% |
| 20 | over | ancient_blue_dragon x2 | 100000 / 132000 | 100 | 7.8% | 80% | 44% | 25% | 20% | 20% | 56% | 27% | 5.1 | 0% |
| 20 | over | ancient_red_dragon x2 | 124000 / 132000 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 14% | 4.3 | 0% |
