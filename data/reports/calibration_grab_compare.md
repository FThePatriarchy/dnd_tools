# Grab-cap comparison

Same DMG budget sweep, compositions and seeds as the area-rule comparison. A grab rule lowers the target count of multi-target grabs only (n_targets actions whose failure grapples, restrains or engulfs): Engulf (gelatinous cube) and Whelm (water elemental). Grab variants were run only on the compositions containing `gelatinous_cube`, `water_elemental`; every other composition takes the same area rule's full-sweep result, which is identical by construction.

| Grab rule | Meaning |
| --- | --- |
| `data` | The printed count: Engulf up to 4, Whelm up to 2 (engine default until 2026-10-24). |
| `grab_half` | A grab reaches at most half the target group, rounded up: 2 of a party of 4 (engine default). |
| `grab_one` | Lower bound: a grab reaches one creature per use. |

| Area rule | Meaning |
| --- | --- |
| `dmg` | DMG table, cone size/10, line length/30, other shapes size/5 (engine default until 2026-10-24). |
| `party_spread` | Monster areas use the halved count (the party spreads out); party areas keep the DMG count (engine default). |

## Encounters with a grab action

### Level 5 low: gelatinous_cube x4

| Variant | Win | Any down | Any death | TPK | Defeat | HP lost | Slots spent | Rounds | Fled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `dmg` + `data` | 10% | 98% | 96% | 90% | - | 97% | 13% | 3.6 | - |
| `dmg` + `grab_half` | 65% | 80% | 52% | 35% | - | 65% | 28% | 4.6 | - |
| `dmg` + `grab_one` | 99% | 40% | 5% | 1% | - | 19% | 26% | 3.2 | - |
| `party_spread` + `data` | 10% | 98% | 96% | 90% | - | 97% | 13% | 3.6 | - |
| `party_spread` + `grab_half` | 65% | 80% | 52% | 35% | 35% | 65% | 28% | 4.6 | 0% |

### Level 5 high: water_elemental x2

| Variant | Win | Any down | Any death | TPK | Defeat | HP lost | Slots spent | Rounds | Fled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `dmg` + `data` | 59% | 91% | 44% | 41% | - | 69% | 51% | 6.1 | - |
| `dmg` + `grab_half` | 59% | 91% | 44% | 41% | - | 69% | 51% | 6.2 | - |
| `dmg` + `grab_one` | 99% | 56% | 3% | 1% | - | 24% | 53% | 4.8 | - |
| `party_spread` + `data` | 59% | 91% | 44% | 41% | - | 69% | 51% | 6.1 | - |
| `party_spread` + `grab_half` | 59% | 91% | 44% | 41% | 41% | 69% | 51% | 6.2 | 0% |

### Level 7 over: water_elemental x5

| Variant | Win | Any down | Any death | TPK | Defeat | HP lost | Slots spent | Rounds | Fled |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `dmg` + `data` | 0% | 100% | 100% | 100% | - | 100% | 21% | 3.3 | - |
| `dmg` + `grab_half` | 0% | 100% | 100% | 100% | - | 100% | 21% | 3.4 | - |
| `dmg` + `grab_one` | 12% | 100% | 93% | 88% | - | 94% | 42% | 7.0 | - |
| `party_spread` + `data` | 0% | 100% | 100% | 100% | - | 100% | 21% | 3.3 | - |
| `party_spread` + `grab_half` | 0% | 100% | 100% | 100% | 100% | 100% | 21% | 3.4 | 0% |

## Whole-sweep shape checks

Same definitions as the area-rule comparison: monotone levels (median TPK never falls from Low to Over), wipe outliers (Low to High compositions with TPK of 50% or more), spread (mean max − min TPK within a Low to High slot).

| Variant | Monotone levels | Wipe outliers | Spread |
| --- | ---: | ---: | ---: |
| `dmg` + `data` | 4 / 5 | 6 | 33% |
| `dmg` + `grab_half` | 4 / 5 | 5 | 29% |
| `dmg` + `grab_one` | 4 / 5 | 5 | 27% |
| `party_spread` + `data` | 3 / 5 | 4 | 28% |
| `party_spread` + `grab_half` | 3 / 5 | 3 | 24% |

## Median TPK chance by slot

| Level | Difficulty | `dmg` + `data` | `dmg` + `grab_half` | `dmg` + `grab_one` | `party_spread` + `data` | `party_spread` + `grab_half` |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | low | 0% | 0% | 0% | 0% | 0% |
| 1 | moderate | 8% | 8% | 8% | 8% | 8% |
| 1 | high | 10% | 10% | 10% | 10% | 10% |
| 1 | over | 22% | 22% | 22% | 22% | 22% |
| 3 | low | 0% | 0% | 0% | 0% | 0% |
| 3 | moderate | 0% | 0% | 0% | 0% | 0% |
| 3 | high | 4% | 4% | 4% | 4% | 4% |
| 3 | over | 38% | 38% | 38% | 25% | 25% |
| 5 | low | 0% | 0% | 0% | 0% | 0% |
| 5 | moderate | 0% | 0% | 0% | 0% | 0% |
| 5 | high | 29% | 29% | 15% | 18% | 18% |
| 5 | over | 12% | 12% | 12% | 12% | 12% |
| 7 | low | 0% | 0% | 0% | 0% | 0% |
| 7 | moderate | 0% | 0% | 0% | 0% | 0% |
| 7 | high | 0% | 0% | 0% | 0% | 0% |
| 7 | over | 30% | 30% | 30% | 30% | 30% |
| 10 | low | 0% | 0% | 0% | 0% | 0% |
| 10 | moderate | 4% | 4% | 4% | 4% | 4% |
| 10 | high | 18% | 18% | 18% | 3% | 3% |
| 10 | over | 96% | 96% | 96% | 90% | 90% |
