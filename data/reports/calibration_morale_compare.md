# Morale comparison

Same DMG budget sweep, compositions and seeds, on the engine-default `party_spread` areas and `grab_half` grabs. Only the optional morale rule changes; the engine default is `none`. Runs per composition: `none` 100, `dmg` 100, `rout` 100.

A fleeing monster leaves the fight, and a fight in which every remaining monster fled counts as a win. Creatures immune to the frightened condition never check.

| Rule | Meaning |
| --- | --- |
| `none` | Engine default: monsters fight to the last. |
| `dmg` | Optional DMG morale: at half HP, and when the side is down to half its number, DC 10 Wisdom save or flee. |
| `rout` | Upper bound: the same triggers, but the monster flees with no save. |

## Median defeat chance (across the compositions in each slot)

| Level | Difficulty | `none` | `dmg` | `rout` |
| ---: | --- | ---: | ---: | ---: |
| 1 | low | 0% | 0% | 0% |
| 1 | moderate | 8% | 2% | 0% |
| 1 | high | 10% | 3% | 1% |
| 1 | over | 22% | 8% | 2% |
| 3 | low | 0% | 0% | 0% |
| 3 | moderate | 0% | 0% | 0% |
| 3 | high | 4% | 2% | 2% |
| 3 | over | 25% | 14% | 0% |
| 5 | low | 0% | 0% | 0% |
| 5 | moderate | 0% | 0% | 0% |
| 5 | high | 18% | 5% | 0% |
| 5 | over | 12% | 6% | 0% |
| 7 | low | 0% | 0% | 0% |
| 7 | moderate | 0% | 0% | 0% |
| 7 | high | 0% | 0% | 0% |
| 7 | over | 30% | 20% | 3% |
| 10 | low | 0% | 0% | 0% |
| 10 | moderate | 4% | 0% | 0% |
| 10 | high | 3% | 2% | 0% |
| 10 | over | 98% | 94% | 64% |

## Median chance someone goes down (across the compositions in each slot)

| Level | Difficulty | `none` | `dmg` | `rout` |
| ---: | --- | ---: | ---: | ---: |
| 1 | low | 22% | 18% | 11% |
| 1 | moderate | 68% | 54% | 38% |
| 1 | high | 78% | 59% | 39% |
| 1 | over | 74% | 56% | 41% |
| 3 | low | 12% | 6% | 2% |
| 3 | moderate | 22% | 12% | 4% |
| 3 | high | 68% | 57% | 46% |
| 3 | over | 96% | 87% | 50% |
| 5 | low | 8% | 4% | 1% |
| 5 | moderate | 56% | 38% | 18% |
| 5 | high | 82% | 66% | 40% |
| 5 | over | 95% | 82% | 63% |
| 7 | low | 10% | 7% | 2% |
| 7 | moderate | 45% | 40% | 18% |
| 7 | high | 76% | 66% | 34% |
| 7 | over | 92% | 86% | 63% |
| 10 | low | 5% | 4% | 0% |
| 10 | moderate | 59% | 51% | 20% |
| 10 | high | 87% | 74% | 36% |
| 10 | over | 100% | 100% | 95% |

## Median chance someone dies (across the compositions in each slot)

| Level | Difficulty | `none` | `dmg` | `rout` |
| ---: | --- | ---: | ---: | ---: |
| 1 | low | 2% | 0% | 0% |
| 1 | moderate | 18% | 4% | 2% |
| 1 | high | 28% | 11% | 4% |
| 1 | over | 41% | 24% | 6% |
| 3 | low | 0% | 0% | 0% |
| 3 | moderate | 0% | 0% | 0% |
| 3 | high | 6% | 5% | 2% |
| 3 | over | 35% | 20% | 0% |
| 5 | low | 0% | 0% | 0% |
| 5 | moderate | 0% | 0% | 0% |
| 5 | high | 23% | 6% | 0% |
| 5 | over | 30% | 23% | 6% |
| 7 | low | 0% | 0% | 0% |
| 7 | moderate | 1% | 1% | 0% |
| 7 | high | 2% | 1% | 0% |
| 7 | over | 36% | 23% | 4% |
| 10 | low | 0% | 0% | 0% |
| 10 | moderate | 6% | 2% | 0% |
| 10 | high | 10% | 3% | 0% |
| 10 | over | 96% | 95% | 66% |

## Mean party HP lost (across the compositions in each slot)

| Level | Difficulty | `none` | `dmg` | `rout` |
| ---: | --- | ---: | ---: | ---: |
| 1 | low | 16% | 11% | 8% |
| 1 | moderate | 31% | 20% | 16% |
| 1 | high | 34% | 21% | 14% |
| 1 | over | 45% | 31% | 18% |
| 3 | low | 7% | 6% | 5% |
| 3 | moderate | 9% | 8% | 7% |
| 3 | high | 33% | 23% | 19% |
| 3 | over | 54% | 41% | 18% |
| 5 | low | 18% | 17% | 15% |
| 5 | moderate | 16% | 14% | 13% |
| 5 | high | 51% | 36% | 24% |
| 5 | over | 47% | 40% | 27% |
| 7 | low | 12% | 11% | 10% |
| 7 | moderate | 22% | 19% | 16% |
| 7 | high | 20% | 19% | 17% |
| 7 | over | 52% | 46% | 37% |
| 10 | low | 14% | 12% | 10% |
| 10 | moderate | 42% | 35% | 26% |
| 10 | high | 41% | 33% | 26% |
| 10 | over | 90% | 88% | 75% |

## Mean rounds (across the compositions in each slot)

| Level | Difficulty | `none` | `dmg` | `rout` |
| ---: | --- | ---: | ---: | ---: |
| 1 | low | 2.3 | 1.6 | 1.1 |
| 1 | moderate | 3.5 | 2.2 | 1.3 |
| 1 | high | 3.9 | 2.4 | 1.4 |
| 1 | over | 4.4 | 3.0 | 1.7 |
| 3 | low | 2.4 | 1.9 | 1.3 |
| 3 | moderate | 2.9 | 2.2 | 1.4 |
| 3 | high | 5.3 | 4.1 | 2.6 |
| 3 | over | 6.4 | 4.8 | 2.5 |
| 5 | low | 2.7 | 2.3 | 1.7 |
| 5 | moderate | 3.8 | 3.0 | 1.5 |
| 5 | high | 6.6 | 4.3 | 2.1 |
| 5 | over | 5.2 | 4.2 | 2.3 |
| 7 | low | 3.1 | 2.6 | 1.4 |
| 7 | moderate | 5.1 | 4.0 | 2.4 |
| 7 | high | 4.4 | 3.6 | 2.1 |
| 7 | over | 6.7 | 5.6 | 3.1 |
| 10 | low | 2.6 | 2.1 | 1.5 |
| 10 | moderate | 5.0 | 3.9 | 2.1 |
| 10 | high | 5.8 | 4.2 | 2.1 |
| 10 | over | 5.1 | 4.9 | 3.5 |

## Mean share of monsters that fled (across the compositions in each slot)

| Level | Difficulty | `none` | `dmg` | `rout` |
| ---: | --- | ---: | ---: | ---: |
| 1 | low | 0% | 36% | 77% |
| 1 | moderate | 0% | 42% | 79% |
| 1 | high | 0% | 49% | 91% |
| 1 | over | 0% | 40% | 93% |
| 3 | low | 0% | 36% | 87% |
| 3 | moderate | 0% | 37% | 76% |
| 3 | high | 0% | 36% | 77% |
| 3 | over | 0% | 39% | 99% |
| 5 | low | 0% | 34% | 80% |
| 5 | moderate | 0% | 39% | 96% |
| 5 | high | 0% | 46% | 95% |
| 5 | over | 0% | 38% | 97% |
| 7 | low | 0% | 38% | 94% |
| 7 | moderate | 0% | 30% | 80% |
| 7 | high | 0% | 41% | 99% |
| 7 | over | 0% | 33% | 85% |
| 10 | low | 0% | 40% | 98% |
| 10 | moderate | 0% | 37% | 96% |
| 10 | high | 0% | 41% | 99% |
| 10 | over | 0% | 8% | 46% |

## Shape checks

Same definitions as the other comparisons, using defeat (which includes TPK).

| Rule | Monotone levels | Defeat outliers | Spread |
| --- | ---: | ---: | ---: |
| `none` | 3 / 5 | 3 | 24% |
| `dmg` | 5 / 5 | 0 | 12% |
| `rout` | 4 / 5 | 0 | 4% |

## Largest defeat changes, `none` vs `dmg`

| Level | Difficulty | Encounter | `none` defeat | `dmg` defeat | `rout` defeat | `dmg` fled | `rout` fled |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 5 | high | fire_elemental x2 | 93% | 46% | 12% | 44% | 88% |
| 1 | over | gnoll_warrior x6 | 74% | 35% | 3% | 44% | 95% |
| 3 | over | bandit_captain x5 | 61% | 23% | 0% | 39% | 98% |
| 10 | moderate | fire_elemental x5 | 79% | 42% | 3% | 41% | 98% |
| 5 | over | guard_captain x6 | 83% | 47% | 10% | 37% | 91% |
| 3 | high | brown_bear x8 | 42% | 11% | 3% | 38% | 85% |
| 3 | high | imp x8 | 50% | 23% | 4% | 36% | 80% |
| 7 | over | air_elemental x5 | 45% | 21% | 2% | 51% | 99% |
| 1 | high | worg x4 | 29% | 6% | 1% | 55% | 96% |
| 3 | over | priest x5 | 100% | 77% | 0% | 24% | 97% |
| 1 | high | goblin_warrior x8 | 29% | 7% | 2% | 41% | 71% |
| 1 | low | bandit x8 | 25% | 6% | 1% | 36% | 73% |
| 1 | over | giant_spider x3 | 39% | 21% | 9% | 43% | 88% |
| 10 | over | young_green_dragon x4 | 54% | 37% | 6% | 27% | 95% |
| 1 | over | brown_bear x3 | 23% | 6% | 3% | 44% | 91% |
