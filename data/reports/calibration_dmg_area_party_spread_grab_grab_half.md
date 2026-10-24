# DMG 2024 budget calibration

Party: fighter, cleric, rogue, wizard at each level; single encounter from full resources; default DayOptions; 100 runs per composition, seed 1. Groups are one monster type, 75%-100% of budget, at most 8 creatures. 'Over' is 1.5x High, a probe beyond the DMG categories.

Area rule: `party_spread` — Monster areas use the halved count (the party spreads out); party areas keep the DMG count.

Grab rule: `grab_half` — A grab reaches at most half the target group, rounded up (2 of a party of 4).

## Summary (mean across compositions, [min-max] in brackets)

| Level | Difficulty | Groups | Win | Any down | Any death | TPK | HP lost | Slots spent | Rounds |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | low | 1 | 65% [65%-65%] | 80% [80%-80%] | 52% [52%-52%] | 35% [35%-35%] | 65% [65%-65%] | 28% [28%-28%] | 4.6 [4.6-4.6] |
| 5 | high | 1 | 59% [59%-59%] | 91% [91%-91%] | 44% [44%-44%] | 41% [41%-41%] | 69% [69%-69%] | 51% [51%-51%] | 6.2 [6.2-6.2] |
| 7 | over | 1 | 0% [0%-0%] | 100% [100%-100%] | 100% [100%-100%] | 100% [100%-100%] | 100% [100%-100%] | 21% [21%-21%] | 3.4 [3.4-3.4] |

## Per composition

| Level | Difficulty | Encounter | XP / budget | Win | Any down | Any death | TPK | HP lost | Slots spent | Rounds |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 5 | low | gelatinous_cube x4 | 1800 / 2000 | 65% | 80% | 52% | 35% | 65% | 28% | 4.6 |
| 5 | high | water_elemental x2 | 3600 / 4400 | 59% | 91% | 44% | 41% | 69% | 51% | 6.2 |
| 7 | over | water_elemental x5 | 9000 / 10200 | 0% | 100% | 100% | 100% | 100% | 21% | 3.4 |
