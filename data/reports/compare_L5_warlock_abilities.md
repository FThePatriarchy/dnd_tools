# Build comparison: warlock, level 5

Each row swaps the candidate into the reference party in place of its wizard and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Dex; ASI split | 1,061 | yes |
| 14 Con, 13 Wis; ASI split | 1,061 | yes |
| standard | 1,010 | yes |
| 14 Dex, 13 Wis; ASI split | 1,010 | yes |
| 14 Dex, 13 Con; ASI con first | 981 | yes |
| 14 Con, 13 Dex | 938 | yes |
| 14 Con, 13 Wis | 938 | no |
| 14 Wis, 13 Con | 938 | no |
| 14 Con, 13 Dex; ASI con first | 911 | no |
| 14 Con, 13 Wis; ASI con first | 911 | no |
| 14 Wis, 13 Con; ASI con first | 911 | no |
| 14 Dex, 13 Wis | 877 | no |
| 14 Dex, 13 Wis; ASI con first | 867 | no |
| 14 Wis, 13 Dex | 814 | no |
| 14 Wis, 13 Dex; ASI con first | 805 | no |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| standard | -23% (0.61×) | -1% ≈ | -2% ≈ | +3% ≈ | -1% ≈ | -9% ≈ | -78% |
| 14 Dex, 13 Wis; ASI split | -24% (0.61×) | -1% ≈ | -2% ≈ | +1% ≈ | -1% ≈ | -9% ≈ | -78% |
| 14 Con, 13 Dex; ASI split | -24% (0.61×) | -0% ≈ | -7% ≈ | +5% ≈ | -1% ≈ | -10% | -78% |
| 14 Con, 13 Wis; ASI split | -24% (0.60×) | -0% ≈ | -7% ≈ | +2% ≈ | -1% ≈ | -10% | -78% |
| 14 Dex, 13 Con; ASI con first | -24% (0.60×) | -4% ≈ | -6% ≈ | -1% ≈ | -1% ≈ | -6% ≈ | -78% |
| 14 Con, 13 Dex | -25% (0.60×) | -2% ≈ | -8% ≈ | +2% ≈ | -2% ≈ | -10% | -78% |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
