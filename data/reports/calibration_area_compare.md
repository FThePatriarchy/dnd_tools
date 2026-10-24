# Area-rule comparison

Same DMG budget sweep, same compositions and seeds; only the no-grid area-of-effect target count changes; multi-target grabs keep their printed count (`data`) throughout. Engine default is `party_spread` (it was `dmg` until 2026-10-24). Runs per composition: `dmg` 100, `half` 100, `half_group` 100, `party_spread` 100, `single` 100.

| Rule | Meaning |
| --- | --- |
| `dmg` | DMG table, cone size/10, line length/30, other shapes size/5 (engine default until 2026-10-24). |
| `half` | DMG count halved, rounded up. |
| `half_group` | DMG count, but never more than half the target group (rounded up). |
| `party_spread` | Monster areas use the halved count (the party spreads out); party areas keep the DMG count (engine default). |
| `single` | Lower bound: every area hits one creature. |

## Median TPK chance (across the compositions in each slot)

| Level | Difficulty | `dmg` | `half` | `half_group` | `party_spread` | `single` |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | low | 0% | 0% | 0% | 0% | 0% |
| 1 | moderate | 8% | 12% | 8% | 8% | 17% |
| 1 | high | 10% | 12% | 12% | 10% | 14% |
| 1 | over | 22% | 22% | 20% | 22% | 16% |
| 3 | low | 0% | 0% | 0% | 0% | 0% |
| 3 | moderate | 0% | 0% | 0% | 0% | 0% |
| 3 | high | 4% | 4% | 6% | 4% | 6% |
| 3 | over | 38% | 25% | 25% | 25% | 16% |
| 5 | low | 0% | 0% | 0% | 0% | 0% |
| 5 | moderate | 0% | 0% | 0% | 0% | 1% |
| 5 | high | 29% | 36% | 25% | 18% | 41% |
| 5 | over | 12% | 7% | 8% | 12% | 8% |
| 7 | low | 0% | 0% | 0% | 0% | 0% |
| 7 | moderate | 0% | 5% | 0% | 0% | 6% |
| 7 | high | 0% | 0% | 0% | 0% | 0% |
| 7 | over | 30% | 40% | 52% | 30% | 68% |
| 10 | low | 0% | 0% | 0% | 0% | 0% |
| 10 | moderate | 4% | 4% | 1% | 4% | 0% |
| 10 | high | 18% | 2% | 3% | 3% | 0% |
| 10 | over | 96% | 92% | 78% | 90% | 57% |

## Median chance someone goes down (across the compositions in each slot)

| Level | Difficulty | `dmg` | `half` | `half_group` | `party_spread` | `single` |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | low | 22% | 26% | 27% | 22% | 28% |
| 1 | moderate | 68% | 74% | 72% | 68% | 74% |
| 1 | high | 78% | 76% | 77% | 78% | 82% |
| 1 | over | 74% | 70% | 69% | 74% | 70% |
| 3 | low | 12% | 6% | 6% | 12% | 6% |
| 3 | moderate | 22% | 22% | 22% | 22% | 22% |
| 3 | high | 68% | 68% | 66% | 68% | 66% |
| 3 | over | 98% | 98% | 96% | 96% | 93% |
| 5 | low | 8% | 12% | 13% | 8% | 15% |
| 5 | moderate | 58% | 58% | 60% | 56% | 70% |
| 5 | high | 86% | 88% | 84% | 82% | 95% |
| 5 | over | 96% | 96% | 97% | 95% | 98% |
| 7 | low | 13% | 14% | 12% | 10% | 14% |
| 7 | moderate | 52% | 63% | 62% | 45% | 67% |
| 7 | high | 76% | 78% | 76% | 76% | 64% |
| 7 | over | 92% | 96% | 98% | 92% | 100% |
| 10 | low | 16% | 5% | 4% | 5% | 5% |
| 10 | moderate | 66% | 62% | 52% | 59% | 32% |
| 10 | high | 97% | 82% | 86% | 87% | 76% |
| 10 | over | 100% | 100% | 100% | 100% | 99% |

## Median chance someone dies (across the compositions in each slot)

| Level | Difficulty | `dmg` | `half` | `half_group` | `party_spread` | `single` |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | low | 2% | 2% | 2% | 2% | 1% |
| 1 | moderate | 18% | 22% | 19% | 18% | 30% |
| 1 | high | 28% | 33% | 31% | 28% | 34% |
| 1 | over | 41% | 44% | 42% | 41% | 41% |
| 3 | low | 0% | 0% | 0% | 0% | 0% |
| 3 | moderate | 0% | 0% | 0% | 0% | 0% |
| 3 | high | 6% | 7% | 9% | 6% | 9% |
| 3 | over | 48% | 38% | 37% | 35% | 25% |
| 5 | low | 0% | 2% | 2% | 0% | 1% |
| 5 | moderate | 0% | 0% | 0% | 0% | 1% |
| 5 | high | 35% | 42% | 30% | 23% | 44% |
| 5 | over | 40% | 26% | 28% | 30% | 15% |
| 7 | low | 0% | 0% | 0% | 0% | 0% |
| 7 | moderate | 2% | 6% | 2% | 1% | 6% |
| 7 | high | 4% | 2% | 0% | 2% | 0% |
| 7 | over | 36% | 46% | 55% | 36% | 70% |
| 10 | low | 0% | 0% | 0% | 0% | 0% |
| 10 | moderate | 6% | 5% | 2% | 6% | 3% |
| 10 | high | 23% | 6% | 10% | 10% | 2% |
| 10 | over | 96% | 97% | 96% | 96% | 97% |

## Mean win rate (across the compositions in each slot)

| Level | Difficulty | `dmg` | `half` | `half_group` | `party_spread` | `single` |
| ---: | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | low | 95% | 95% | 96% | 95% | 94% |
| 1 | moderate | 90% | 88% | 90% | 90% | 84% |
| 1 | high | 86% | 85% | 86% | 86% | 80% |
| 1 | over | 73% | 70% | 73% | 73% | 72% |
| 3 | low | 100% | 100% | 100% | 100% | 100% |
| 3 | moderate | 100% | 100% | 100% | 100% | 100% |
| 3 | high | 83% | 78% | 83% | 83% | 74% |
| 3 | over | 59% | 60% | 62% | 64% | 63% |
| 5 | low | 85% | 83% | 83% | 85% | 83% |
| 5 | moderate | 100% | 99% | 99% | 100% | 98% |
| 5 | high | 61% | 63% | 63% | 70% | 56% |
| 5 | over | 70% | 76% | 77% | 77% | 78% |
| 7 | low | 100% | 100% | 100% | 100% | 100% |
| 7 | moderate | 92% | 88% | 92% | 96% | 84% |
| 7 | high | 98% | 96% | 98% | 99% | 93% |
| 7 | over | 62% | 56% | 50% | 65% | 43% |
| 10 | low | 100% | 100% | 100% | 100% | 100% |
| 10 | moderate | 68% | 83% | 82% | 83% | 80% |
| 10 | high | 83% | 90% | 92% | 92% | 89% |
| 10 | over | 2% | 9% | 16% | 11% | 29% |

## Shape checks

- **Monotone levels:** levels where median TPK never falls from Low to Moderate to High to Over.
- **Wipe outliers:** compositions in Low, Moderate or High with TPK of 50% or more.
- **Spread:** mean (max − min) TPK across the compositions of a slot, Low to High.

| Rule | Monotone levels | Wipe outliers | Spread |
| --- | ---: | ---: | ---: |
| `dmg` | 4 / 5 | 6 | 33% |
| `half` | 2 / 5 | 5 | 35% |
| `half_group` | 4 / 5 | 5 | 33% |
| `party_spread` | 3 / 5 | 4 | 28% |
| `single` | 2 / 5 | 6 | 41% |

## Encounters with TPK ≥ 30% under the default

| Level | Difficulty | Encounter | `dmg` | `half` | `half_group` | `party_spread` | `single` |
| ---: | --- | --- | ---: | ---: | ---: | ---: | ---: |
| 1 | over | giant_spider x3 | 39% | 45% | 42% | 39% | 41% |
| 1 | over | gnoll_warrior x6 | 74% | 82% | 73% | 74% | 86% |
| 3 | high | brown_bear x8 | 42% | 55% | 42% | 42% | 56% |
| 3 | high | imp x8 | 50% | 66% | 50% | 50% | 86% |
| 3 | over | bandit_captain x5 | 61% | 82% | 70% | 61% | 85% |
| 3 | over | priest x5 | 100% | 100% | 100% | 100% | 100% |
| 3 | over | young_white_dragon x1 | 54% | 28% | 28% | 28% | 3% |
| 5 | low | gelatinous_cube x4 | 90% | 96% | 96% | 90% | 99% |
| 5 | high | basilisk x6 | 57% | 46% | 30% | 19% | 36% |
| 5 | high | fire_elemental x2 | 100% | 93% | 100% | 93% | 89% |
| 5 | high | water_elemental x2 | 41% | 41% | 56% | 41% | 56% |
| 5 | over | guard_captain x6 | 83% | 95% | 86% | 83% | 99% |
| 5 | over | young_red_dragon x1 | 64% | 28% | 28% | 28% | 0% |
| 7 | moderate | basilisk x7 | 41% | 41% | 33% | 12% | 11% |
| 7 | over | air_elemental x5 | 45% | 69% | 54% | 45% | 78% |
| 7 | over | chain_devil x2 | 37% | 37% | 61% | 37% | 61% |
| 7 | over | water_elemental x5 | 100% | 100% | 100% | 100% | 100% |
| 10 | moderate | fire_elemental x5 | 100% | 79% | 100% | 79% | 100% |
| 10 | moderate | mage x4 | 86% | 12% | 1% | 13% | 0% |
| 10 | high | young_green_dragon x3 | 38% | 2% | 6% | 6% | 0% |
| 10 | over | adult_red_dragon x1 | 95% | 85% | 47% | 85% | 12% |
| 10 | over | chain_devil x4 | 96% | 98% | 97% | 96% | 100% |
| 10 | over | mage x8 | 100% | 100% | 100% | 100% | 96% |
| 10 | over | young_green_dragon x4 | 95% | 65% | 59% | 54% | 19% |
| 10 | over | young_white_dragon x8 | 100% | 100% | 100% | 100% | 100% |
