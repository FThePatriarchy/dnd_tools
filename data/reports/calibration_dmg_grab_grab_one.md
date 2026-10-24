# DMG 2024 budget calibration

Party: fighter, cleric, rogue, wizard at each level; single encounter from full resources; default DayOptions; 100 runs per composition, seed 1. Groups are one monster type, 75%-100% of budget, at most 8 creatures. 'Over' is 1.5x High, a probe beyond the DMG categories.

Area rule: `dmg` — Engine default: DMG table, cone size/10, line length/30, other shapes size/5.

Grab rule: `grab_one` — Lower bound: a grab reaches one creature per use.

## Summary (mean across compositions, [min-max] in brackets)

| Level | Difficulty | Groups | Win | Any down | Any death | TPK | HP lost | Slots spent | Rounds |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | low | 1 | 99% [99%-99%] | 40% [40%-40%] | 5% [5%-5%] | 1% [1%-1%] | 19% [19%-19%] | 26% [26%-26%] | 3.2 [3.2-3.2] |
| 5 | high | 1 | 99% [99%-99%] | 56% [56%-56%] | 3% [3%-3%] | 1% [1%-1%] | 24% [24%-24%] | 53% [53%-53%] | 4.8 [4.8-4.8] |
| 7 | over | 1 | 12% [12%-12%] | 100% [100%-100%] | 93% [93%-93%] | 88% [88%-88%] | 94% [94%-94%] | 42% [42%-42%] | 7.0 [7.0-7.0] |

## Per composition

| Level | Difficulty | Encounter | XP / budget | Win | Any down | Any death | TPK | HP lost | Slots spent | Rounds |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | low | gelatinous_cube x4 | 1800 / 2000 | 99% | 40% | 5% | 1% | 19% | 26% | 3.2 |
| 5 | high | water_elemental x2 | 3600 / 4400 | 99% | 56% | 3% | 1% | 24% | 53% | 4.8 |
| 7 | over | water_elemental x5 | 9000 / 10200 | 12% | 100% | 93% | 88% | 94% | 42% | 7.0 |
