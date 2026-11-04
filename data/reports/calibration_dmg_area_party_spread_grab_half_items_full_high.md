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
| 11 | low | 6 | 100% [98%-100%] | 11% [0%-31%] | 0% [0%-2%] | 0% [0%-0%] | 0% [0%-2%] | 19% [11%-32%] | 15% [10%-19%] | 2.9 [1.7-5.1] | 0% [0%-0%] |
| 11 | moderate | 6 | 100% [99%-100%] | 34% [0%-94%] | 1% [0%-5%] | 0% [0%-1%] | 0% [0%-1%] | 20% [10%-28%] | 17% [10%-26%] | 2.9 [1.9-4.2] | 0% [0%-0%] |
| 11 | high | 6 | 84% [22%-100%] | 62% [7%-100%] | 18% [0%-81%] | 15% [0%-78%] | 16% [0%-78%] | 42% [20%-92%] | 21% [11%-30%] | 3.9 [2.3-5.8] | 0% [0%-0%] |
| 11 | over | 6 | 58% [7%-100%] | 85% [44%-100%] | 44% [0%-93%] | 38% [0%-81%] | 42% [0%-93%] | 61% [18%-95%] | 28% [12%-37%] | 5.3 [3.4-8.1] | 0% [0%-0%] |
| 13 | low | 6 | 100% [99%-100%] | 11% [0%-36%] | 0% [0%-2%] | 0% [0%-1%] | 0% [0%-1%] | 9% [1%-16%] | 20% [12%-37%] | 2.8 [2.0-4.8] | 0% [0%-0%] |
| 13 | moderate | 6 | 99% [92%-100%] | 32% [0%-90%] | 2% [0%-10%] | 1% [0%-8%] | 1% [0%-8%] | 20% [10%-51%] | 21% [12%-26%] | 3.1 [1.9-4.3] | 0% [0%-0%] |
| 13 | high | 6 | 84% [20%-100%] | 59% [13%-93%] | 18% [0%-86%] | 6% [0%-27%] | 16% [0%-80%] | 36% [19%-72%] | 26% [20%-34%] | 4.4 [2.6-6.6] | 0% [0%-0%] |
| 13 | over | 6 | 76% [0%-100%] | 82% [32%-100%] | 28% [0%-100%] | 24% [0%-100%] | 24% [0%-100%] | 55% [16%-100%] | 32% [19%-44%] | 6.2 [3.3-10.2] | 0% [0%-0%] |
| 15 | low | 6 | 100% [98%-100%] | 3% [0%-13%] | 0% [0%-2%] | 0% [0%-0%] | 0% [0%-2%] | 9% [1%-20%] | 16% [12%-22%] | 2.6 [1.9-3.9] | 0% [0%-0%] |
| 15 | moderate | 6 | 92% [58%-100%] | 22% [0%-61%] | 9% [0%-46%] | 2% [0%-7%] | 8% [0%-42%] | 24% [14%-54%] | 22% [16%-31%] | 3.6 [2.2-6.6] | 0% [0%-0%] |
| 15 | high | 6 | 83% [0%-100%] | 64% [7%-100%] | 18% [0%-100%] | 17% [0%-100%] | 17% [0%-100%] | 44% [16%-100%] | 26% [17%-33%] | 4.9 [2.8-8.0] | 0% [0%-0%] |
| 15 | over | 6 | 48% [0%-95%] | 89% [78%-100%] | 52% [5%-76%] | 36% [5%-72%] | 52% [5%-100%] | 67% [26%-86%] | 33% [13%-53%] | 7.5 [2.2-13.8] | 0% [0%-0%] |
| 17 | low | 6 | 100% [100%-100%] | 1% [0%-5%] | 0% [0%-0%] | 0% [0%-0%] | 0% [0%-0%] | 10% [6%-24%] | 12% [11%-15%] | 1.9 [1.4-2.5] | 0% [0%-0%] |
| 17 | moderate | 6 | 100% [100%-100%] | 23% [1%-56%] | 0% [0%-0%] | 0% [0%-0%] | 0% [0%-0%] | 20% [12%-32%] | 17% [11%-22%] | 2.5 [1.6-3.3] | 0% [0%-0%] |
| 17 | high | 6 | 82% [0%-100%] | 52% [2%-92%] | 17% [0%-83%] | 5% [0%-18%] | 18% [0%-100%] | 37% [13%-67%] | 23% [15%-37%] | 4.5 [2.4-7.3] | 0% [0%-0%] |
| 17 | over | 6 | 24% [0%-62%] | 98% [90%-100%] | 80% [43%-100%] | 76% [38%-100%] | 76% [38%-100%] | 90% [72%-100%] | 21% [7%-34%] | 4.8 [1.6-6.9] | 0% [0%-0%] |
| 20 | low | 6 | 100% [100%-100%] | 0% [0%-2%] | 0% [0%-0%] | 0% [0%-0%] | 0% [0%-0%] | 10% [1%-24%] | 11% [8%-14%] | 1.7 [1.1-2.3] | 0% [0%-0%] |
| 20 | moderate | 6 | 84% [1%-100%] | 36% [6%-86%] | 13% [0%-77%] | 3% [0%-19%] | 16% [0%-99%] | 30% [17%-67%] | 18% [14%-28%] | 3.2 [2.4-4.6] | 0% [0%-0%] |
| 20 | high | 6 | 30% [0%-72%] | 100% [99%-100%] | 75% [33%-100%] | 70% [28%-100%] | 70% [28%-100%] | 88% [67%-100%] | 19% [7%-28%] | 4.7 [1.6-7.9] | 0% [0%-0%] |
| 20 | over | 6 | 14% [0%-85%] | 99% [96%-100%] | 86% [17%-100%] | 86% [15%-100%] | 86% [15%-100%] | 93% [60%-100%] | 15% [6%-36%] | 3.1 [1.3-6.5] | 0% [0%-0%] |

## Per composition

Runs is the number of runs used; ± is the 95% half-width of the defeat estimate.

| Level | Difficulty | Encounter | XP / budget | Runs | ± | Win | Any down | Any death | TPK | Defeat | HP lost | Slots spent | Rounds | Fled |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 11 | low | guard_captain x6 | 6600 / 7600 | 100 | 1.8% | 100% | 11% | 0% | 0% | 0% | 14% | 15% | 2.5 | 0% |
| 11 | low | fire_elemental x4 | 7200 / 7600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 27% | 19% | 5.1 | 0% |
| 11 | low | water_elemental x4 | 7200 / 7600 | 100 | 1.8% | 100% | 31% | 1% | 0% | 0% | 32% | 16% | 3.7 | 0% |
| 11 | low | wyvern x3 | 6900 / 7600 | 100 | 1.8% | 100% | 14% | 0% | 0% | 0% | 12% | 14% | 2.3 | 0% |
| 11 | low | aboleth x1 | 5900 / 7600 | 100 | 3.2% | 98% | 7% | 2% | 0% | 2% | 14% | 13% | 2.0 | 0% |
| 11 | low | roc x1 | 7200 / 7600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 11% | 10% | 1.7 | 0% |
| 11 | moderate | air_elemental x6 | 10800 / 11600 | 100 | 1.8% | 100% | 86% | 0% | 0% | 0% | 26% | 24% | 3.9 | 0% |
| 11 | moderate | hill_giant x6 | 10800 / 11600 | 100 | 2.6% | 99% | 94% | 5% | 1% | 1% | 28% | 26% | 4.2 | 0% |
| 11 | moderate | wraith x6 | 10800 / 11600 | 100 | 1.8% | 100% | 2% | 2% | 0% | 0% | 13% | 10% | 2.9 | 0% |
| 11 | moderate | mind_flayer x4 | 11600 / 11600 | 100 | 2.6% | 99% | 17% | 1% | 0% | 1% | 25% | 15% | 2.6 | 0% |
| 11 | moderate | clay_golem x2 | 10000 / 11600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 10% | 12% | 2.1 | 0% |
| 11 | moderate | adult_black_dragon x1 | 11500 / 11600 | 100 | 1.8% | 100% | 3% | 0% | 0% | 0% | 16% | 13% | 1.9 | 0% |
| 11 | high | mage x7 | 16100 / 16400 | 100 | 8.0% | 22% | 100% | 81% | 78% | 78% | 92% | 11% | 3.6 | 0% |
| 11 | high | mind_flayer x5 | 14500 / 16400 | 100 | 6.4% | 88% | 53% | 14% | 5% | 12% | 43% | 17% | 3.2 | 0% |
| 11 | high | chain_devil x4 | 15600 / 16400 | 100 | 2.6% | 99% | 90% | 2% | 1% | 1% | 26% | 30% | 5.8 | 0% |
| 11 | high | bone_devil x3 | 15000 / 16400 | 100 | 4.1% | 96% | 83% | 8% | 4% | 4% | 42% | 29% | 5.1 | 0% |
| 11 | high | horned_devil x2 | 14400 / 16400 | 100 | 1.8% | 100% | 41% | 0% | 0% | 0% | 20% | 23% | 3.3 | 0% |
| 11 | high | adult_blue_dragon x1 | 15000 / 16400 | 100 | 1.8% | 100% | 7% | 0% | 0% | 0% | 32% | 16% | 2.3 | 0% |
| 11 | over | mind_flayer x8 | 23200 / 24600 | 100 | 5.2% | 7% | 98% | 93% | 74% | 93% | 95% | 12% | 3.4 | 0% |
| 11 | over | chain_devil x6 | 23400 / 24600 | 100 | 7.6% | 19% | 100% | 84% | 81% | 81% | 88% | 32% | 8.1 | 0% |
| 11 | over | young_green_dragon x6 | 23400 / 24600 | 100 | 9.5% | 44% | 87% | 57% | 56% | 56% | 73% | 26% | 5.0 | 0% |
| 11 | over | young_blue_dragon x4 | 20000 / 24600 | 100 | 1.8% | 100% | 44% | 0% | 0% | 0% | 18% | 27% | 4.3 | 0% |
| 11 | over | horned_devil x3 | 21600 / 24600 | 100 | 6.2% | 89% | 88% | 16% | 11% | 11% | 47% | 37% | 6.3 | 0% |
| 11 | over | adult_black_dragon x2 | 23000 / 24600 | 100 | 5.4% | 92% | 93% | 12% | 8% | 8% | 47% | 33% | 4.6 | 0% |
| 13 | low | air_elemental x5 | 9000 / 10400 | 100 | 1.8% | 100% | 24% | 0% | 0% | 0% | 14% | 20% | 2.9 | 0% |
| 13 | low | troll x5 | 9000 / 10400 | 100 | 2.6% | 99% | 36% | 2% | 1% | 1% | 16% | 37% | 4.8 | 0% |
| 13 | low | wyvern x4 | 9200 / 10400 | 100 | 1.8% | 100% | 7% | 0% | 0% | 0% | 9% | 19% | 2.6 | 0% |
| 13 | low | chain_devil x2 | 7800 / 10400 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 1% | 13% | 2.0 | 0% |
| 13 | low | clay_golem x2 | 10000 / 10400 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 5% | 15% | 2.1 | 0% |
| 13 | low | vampire x1 | 10000 / 10400 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 9% | 12% | 2.7 | 0% |
| 13 | moderate | mage x7 | 16100 / 16800 | 100 | 5.4% | 92% | 90% | 10% | 8% | 8% | 51% | 23% | 4.3 | 0% |
| 13 | moderate | stone_giant x5 | 14500 / 16800 | 100 | 1.8% | 100% | 43% | 0% | 0% | 0% | 17% | 26% | 3.5 | 0% |
| 13 | moderate | frost_giant x4 | 15600 / 16800 | 100 | 1.8% | 100% | 47% | 0% | 0% | 0% | 16% | 23% | 3.0 | 0% |
| 13 | moderate | clay_golem x3 | 15000 / 16800 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 10% | 18% | 2.6 | 0% |
| 13 | moderate | roc x2 | 14400 / 16800 | 100 | 1.8% | 100% | 10% | 0% | 0% | 0% | 16% | 21% | 3.2 | 0% |
| 13 | moderate | adult_blue_dragon x1 | 15000 / 16800 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 13% | 12% | 1.9 | 0% |
| 13 | high | mind_flayer x7 | 20300 / 21600 | 100 | 6.2% | 89% | 63% | 11% | 2% | 11% | 45% | 22% | 3.7 | 0% |
| 13 | high | chain_devil x5 | 19500 / 21600 | 100 | 2.6% | 99% | 87% | 2% | 1% | 1% | 19% | 34% | 6.2 | 0% |
| 13 | high | bone_devil x4 | 20000 / 21600 | 100 | 3.2% | 98% | 78% | 6% | 2% | 2% | 32% | 28% | 4.6 | 0% |
| 13 | high | aboleth x3 | 17700 / 21600 | 100 | 7.8% | 20% | 93% | 86% | 27% | 80% | 72% | 30% | 6.6 | 0% |
| 13 | high | archmage x2 | 16800 / 21600 | 100 | 1.8% | 100% | 13% | 0% | 0% | 0% | 23% | 20% | 2.8 | 0% |
| 13 | high | adult_red_dragon x1 | 18000 / 21600 | 100 | 2.6% | 99% | 21% | 1% | 1% | 1% | 25% | 23% | 2.6 | 0% |
| 13 | over | assassin x8 | 31200 / 32400 | 100 | 7.5% | 82% | 100% | 22% | 18% | 18% | 61% | 33% | 5.7 | 0% |
| 13 | over | tyrannosaurus_rex x8 | 31200 / 32400 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 19% | 3.9 | 0% |
| 13 | over | young_blue_dragon x6 | 30000 / 32400 | 100 | 3.7% | 97% | 99% | 15% | 3% | 3% | 42% | 36% | 6.6 | 0% |
| 13 | over | horned_devil x4 | 28800 / 32400 | 100 | 7.3% | 83% | 97% | 20% | 17% | 17% | 53% | 40% | 7.5 | 0% |
| 13 | over | vampire x3 | 30000 / 32400 | 100 | 1.8% | 100% | 32% | 0% | 0% | 0% | 16% | 44% | 10.2 | 0% |
| 13 | over | ancient_white_dragon x1 | 25000 / 32400 | 100 | 5.7% | 91% | 64% | 9% | 9% | 9% | 61% | 20% | 3.3 | 0% |
| 15 | low | air_elemental x7 | 12600 / 13200 | 100 | 1.8% | 100% | 13% | 0% | 0% | 0% | 12% | 16% | 2.3 | 0% |
| 15 | low | vampire_spawn x7 | 12600 / 13200 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 3% | 14% | 2.3 | 0% |
| 15 | low | mind_flayer x4 | 11600 / 13200 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 1% | 12% | 1.9 | 0% |
| 15 | low | hezrou x3 | 11700 / 13200 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 9% | 18% | 2.9 | 0% |
| 15 | low | aboleth x2 | 11800 / 13200 | 100 | 3.2% | 98% | 5% | 2% | 0% | 2% | 20% | 22% | 3.9 | 0% |
| 15 | low | purple_worm x1 | 13000 / 13200 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 10% | 14% | 2.1 | 0% |
| 15 | moderate | mind_flayer x7 | 20300 / 21600 | 100 | 4.5% | 95% | 10% | 5% | 3% | 5% | 20% | 16% | 2.6 | 0% |
| 15 | moderate | chain_devil x5 | 19500 / 21600 | 100 | 1.8% | 100% | 30% | 1% | 0% | 0% | 14% | 24% | 4.6 | 0% |
| 15 | moderate | bone_devil x4 | 20000 / 21600 | 100 | 1.8% | 100% | 31% | 0% | 0% | 0% | 19% | 23% | 3.5 | 0% |
| 15 | moderate | aboleth x3 | 17700 / 21600 | 100 | 9.5% | 58% | 61% | 46% | 7% | 42% | 54% | 31% | 6.6 | 0% |
| 15 | moderate | archmage x2 | 16800 / 21600 | 100 | 1.8% | 100% | 1% | 0% | 0% | 0% | 16% | 17% | 2.5 | 0% |
| 15 | moderate | adult_red_dragon x1 | 18000 / 21600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 20% | 18% | 2.2 | 0% |
| 15 | high | assassin x8 | 31200 / 31200 | 100 | 2.6% | 99% | 96% | 1% | 1% | 1% | 37% | 29% | 4.3 | 0% |
| 15 | high | tyrannosaurus_rex x8 | 31200 / 31200 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 21% | 4.9 | 0% |
| 15 | high | young_blue_dragon x6 | 30000 / 31200 | 100 | 1.8% | 100% | 83% | 4% | 0% | 0% | 31% | 26% | 4.4 | 0% |
| 15 | high | horned_devil x4 | 28800 / 31200 | 100 | 2.6% | 99% | 78% | 3% | 1% | 1% | 29% | 32% | 5.2 | 0% |
| 15 | high | vampire x3 | 30000 / 31200 | 100 | 1.8% | 100% | 7% | 0% | 0% | 0% | 16% | 33% | 8.0 | 0% |
| 15 | high | ancient_white_dragon x1 | 25000 / 31200 | 100 | 1.8% | 100% | 19% | 1% | 0% | 0% | 50% | 17% | 2.8 | 0% |
| 15 | over | aboleth x7 | 41300 / 46800 | 100 | 1.8% | 0% | 80% | 75% | 6% | 100% | 58% | 13% | 2.2 | 0% |
| 15 | over | horned_devil x6 | 43200 / 46800 | 100 | 8.7% | 28% | 99% | 76% | 72% | 72% | 86% | 36% | 8.0 | 0% |
| 15 | over | archpriest x5 | 42000 / 46800 | 100 | 9.5% | 41% | 100% | 68% | 59% | 59% | 81% | 42% | 8.0 | 0% |
| 15 | over | vampire x4 | 40000 / 46800 | 100 | 4.5% | 95% | 78% | 5% | 5% | 5% | 26% | 53% | 13.8 | 0% |
| 15 | over | purple_worm x3 | 39000 / 46800 | 100 | 9.3% | 62% | 98% | 46% | 38% | 38% | 68% | 33% | 8.7 | 0% |
| 15 | over | ancient_green_dragon x1 | 41000 / 46800 | 100 | 9.3% | 63% | 81% | 40% | 37% | 37% | 82% | 21% | 4.1 | 0% |
| 17 | low | mage x7 | 16100 / 18000 | 100 | 1.8% | 100% | 5% | 0% | 0% | 0% | 24% | 12% | 1.9 | 0% |
| 17 | low | stone_giant x6 | 17400 / 18000 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 6% | 11% | 1.6 | 0% |
| 17 | low | hezrou x4 | 15600 / 18000 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 6% | 12% | 2.1 | 0% |
| 17 | low | fire_giant x3 | 15000 / 18000 | 100 | 1.8% | 100% | 2% | 0% | 0% | 0% | 9% | 15% | 2.5 | 0% |
| 17 | low | horned_devil x2 | 14400 / 18000 | 100 | 1.8% | 100% | 1% | 0% | 0% | 0% | 8% | 12% | 2.1 | 0% |
| 17 | low | adult_red_dragon x1 | 18000 / 18000 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 9% | 13% | 1.4 | 0% |
| 17 | moderate | assassin x7 | 27300 / 28800 | 100 | 1.8% | 100% | 56% | 0% | 0% | 0% | 23% | 20% | 3.0 | 0% |
| 17 | moderate | tyrannosaurus_rex x7 | 27300 / 28800 | 100 | 1.8% | 100% | 27% | 0% | 0% | 0% | 16% | 11% | 1.6 | 0% |
| 17 | moderate | fire_giant x5 | 25000 / 28800 | 100 | 1.8% | 100% | 42% | 0% | 0% | 0% | 18% | 22% | 3.3 | 0% |
| 17 | moderate | young_red_dragon x4 | 23600 / 28800 | 100 | 1.8% | 100% | 6% | 0% | 0% | 0% | 21% | 16% | 2.6 | 0% |
| 17 | moderate | archpriest x3 | 25200 / 28800 | 100 | 1.8% | 100% | 4% | 0% | 0% | 0% | 12% | 20% | 2.6 | 0% |
| 17 | moderate | ancient_white_dragon x1 | 25000 / 28800 | 100 | 1.8% | 100% | 1% | 0% | 0% | 0% | 32% | 11% | 2.0 | 0% |
| 17 | high | aboleth x7 | 41300 / 46800 | 100 | 1.8% | 0% | 89% | 83% | 18% | 100% | 67% | 15% | 3.1 | 0% |
| 17 | high | horned_devil x6 | 43200 / 46800 | 100 | 4.8% | 94% | 92% | 13% | 6% | 6% | 43% | 37% | 7.3 | 0% |
| 17 | high | archpriest x5 | 42000 / 46800 | 100 | 3.2% | 98% | 62% | 6% | 2% | 2% | 28% | 31% | 4.4 | 0% |
| 17 | high | vampire x4 | 40000 / 46800 | 100 | 1.8% | 100% | 2% | 0% | 0% | 0% | 13% | 23% | 6.7 | 0% |
| 17 | high | purple_worm x3 | 39000 / 46800 | 100 | 1.8% | 100% | 50% | 0% | 0% | 0% | 21% | 16% | 3.0 | 0% |
| 17 | high | ancient_green_dragon x1 | 41000 / 46800 | 100 | 3.2% | 98% | 20% | 2% | 2% | 2% | 48% | 18% | 2.4 | 0% |
| 17 | over | archmage x8 | 67200 / 70200 | 100 | 7.2% | 16% | 98% | 84% | 84% | 84% | 93% | 10% | 3.0 | 0% |
| 17 | over | adult_white_dragon x7 | 70000 / 70200 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 7% | 1.6 | 0% |
| 17 | over | adult_black_dragon x6 | 69000 / 70200 | 100 | 6.8% | 14% | 100% | 89% | 86% | 86% | 96% | 27% | 5.4 | 0% |
| 17 | over | purple_worm x5 | 65000 / 70200 | 100 | 9.6% | 50% | 100% | 62% | 50% | 50% | 72% | 26% | 6.9 | 0% |
| 17 | over | adult_red_dragon x3 | 54000 / 70200 | 100 | 3.2% | 2% | 100% | 99% | 98% | 98% | 99% | 24% | 6.4 | 0% |
| 17 | over | ancient_red_dragon x1 | 62000 / 70200 | 100 | 9.3% | 62% | 90% | 43% | 38% | 38% | 77% | 34% | 5.7 | 0% |
| 20 | low | mind_flayer x8 | 23200 / 25600 | 100 | 1.8% | 100% | 1% | 0% | 0% | 0% | 1% | 9% | 1.2 | 0% |
| 20 | low | frost_giant x6 | 23400 / 25600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 5% | 8% | 1.1 | 0% |
| 20 | low | bone_devil x5 | 25000 / 25600 | 100 | 1.8% | 100% | 2% | 0% | 0% | 0% | 10% | 14% | 2.3 | 0% |
| 20 | low | stone_golem x4 | 23600 / 25600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 7% | 10% | 2.0 | 0% |
| 20 | low | archmage x3 | 25200 / 25600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 11% | 10% | 1.9 | 0% |
| 20 | low | ancient_white_dragon x1 | 25000 / 25600 | 100 | 1.8% | 100% | 0% | 0% | 0% | 0% | 24% | 12% | 1.9 | 0% |
| 20 | moderate | aboleth x8 | 47200 / 52800 | 100 | 2.6% | 1% | 86% | 77% | 19% | 99% | 67% | 14% | 3.3 | 0% |
| 20 | moderate | horned_devil x7 | 50400 / 52800 | 100 | 1.8% | 100% | 49% | 0% | 0% | 0% | 24% | 28% | 4.6 | 0% |
| 20 | moderate | archpriest x6 | 50400 / 52800 | 100 | 1.8% | 100% | 17% | 0% | 0% | 0% | 21% | 21% | 3.3 | 0% |
| 20 | moderate | adult_black_dragon x4 | 46000 / 52800 | 100 | 1.8% | 100% | 35% | 1% | 0% | 0% | 25% | 16% | 2.9 | 0% |
| 20 | moderate | adult_blue_dragon x3 | 45000 / 52800 | 100 | 1.8% | 100% | 26% | 0% | 0% | 0% | 24% | 14% | 2.6 | 0% |
| 20 | moderate | ancient_blue_dragon x1 | 50000 / 52800 | 100 | 1.8% | 100% | 6% | 0% | 0% | 0% | 17% | 19% | 2.4 | 0% |
| 20 | high | adult_white_dragon x8 | 80000 / 88000 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 7% | 1.6 | 0% |
| 20 | high | adult_black_dragon x7 | 80500 / 88000 | 100 | 9.6% | 51% | 100% | 61% | 49% | 49% | 82% | 27% | 6.3 | 0% |
| 20 | high | purple_worm x6 | 78000 / 88000 | 100 | 9.1% | 33% | 99% | 76% | 67% | 67% | 82% | 28% | 7.9 | 0% |
| 20 | high | adult_blue_dragon x5 | 75000 / 88000 | 100 | 8.7% | 72% | 100% | 33% | 28% | 28% | 67% | 23% | 5.3 | 0% |
| 20 | high | ancient_white_dragon x3 | 75000 / 88000 | 100 | 4.8% | 6% | 100% | 95% | 94% | 94% | 99% | 14% | 3.1 | 0% |
| 20 | high | ancient_green_dragon x2 | 82000 / 88000 | 100 | 7.2% | 16% | 100% | 87% | 84% | 84% | 97% | 19% | 3.9 | 0% |
| 20 | over | adult_blue_dragon x8 | 120000 / 132000 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 10% | 2.2 | 0% |
| 20 | over | adult_red_dragon x7 | 126000 / 132000 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 6% | 2.1 | 0% |
| 20 | over | ancient_white_dragon x5 | 125000 / 132000 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 8% | 1.3 | 0% |
| 20 | over | ancient_green_dragon x3 | 123000 / 132000 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 12% | 2.1 | 0% |
| 20 | over | ancient_blue_dragon x2 | 100000 / 132000 | 100 | 7.0% | 85% | 96% | 17% | 15% | 15% | 60% | 36% | 6.5 | 0% |
| 20 | over | ancient_red_dragon x2 | 124000 / 132000 | 100 | 1.8% | 0% | 100% | 100% | 100% | 100% | 100% | 21% | 4.5 | 0% |
