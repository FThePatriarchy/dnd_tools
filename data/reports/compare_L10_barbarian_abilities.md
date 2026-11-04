# Build comparison: barbarian, level 10

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Dex; ASI con first | 2,787 | yes |
| 14 Con, 13 Dex | 2,760 | yes |
| 14 Dex, 13 Con; ASI split | 2,544 | yes |
| standard | 2,497 | yes |
| 14 Con, 13 Dex; ASI split | 2,362 | yes |
| 14 Wis, 13 Con; ASI split | 2,362 | yes |
| 14 Wis, 13 Con | 2,331 | no |
| 14 Dex, 13 Wis; ASI split | 2,138 | no |
| 14 Wis, 13 Dex; ASI split | 1,995 | no |

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,058 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Dex, 13 Con; ASI split | -2% ≈ (0.72×) | +3% ≈ | -8% ≈ | +0% ≈ | -1% ≈ | -5% ≈ | -0% ≈ |
| 14 Con, 13 Dex; ASI con first | -2% ≈ (0.71×) | +3% ≈ | -6% ≈ | +0% ≈ | -0% ≈ | -11% | +0% ≈ |
| 14 Con, 13 Dex | -3% ≈ (0.71×) | +3% ≈ | -13% | +2% ≈ | -2% ≈ | -6% ≈ | +2% ≈ |
| 14 Con, 13 Dex; ASI split | -4% (0.70×) | +1% ≈ | -14% | -1% ≈ | -2% ≈ | -7% ≈ | +0% ≈ |
| 14 Wis, 13 Con; ASI split | -4% (0.70×) | +1% ≈ | -14% | -1% ≈ | -2% ≈ | -7% ≈ | +0% ≈ |
| standard | -5% (0.69×) | +0% ≈ | -13% | +2% ≈ | -10% | -9% ≈ | +1% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
