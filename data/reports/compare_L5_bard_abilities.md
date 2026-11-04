# Build comparison: bard, level 5

Each row swaps the candidate into the reference party in place of its cleric and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Dex; ASI split | 387 | yes |
| 14 Con, 13 Wis; ASI split | 387 | yes |
| 14 Dex, 13 Con; ASI con first | 387 | yes |
| standard | 366 | yes |
| 14 Dex, 13 Wis; ASI split | 366 | yes |
| 14 Con, 13 Dex; ASI con first | 361 | yes |
| 14 Con, 13 Wis; ASI con first | 361 | no |
| 14 Wis, 13 Con; ASI con first | 361 | no |
| 14 Dex, 13 Wis; ASI con first | 342 | no |
| 14 Con, 13 Dex | 342 | no |
| 14 Con, 13 Wis | 342 | no |
| 14 Wis, 13 Con | 342 | no |
| 14 Wis, 13 Dex; ASI con first | 319 | no |
| 14 Dex, 13 Wis | 318 | no |
| 14 Wis, 13 Dex | 297 | no |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| standard | +2% ≈ (0.81×) | +4% ≈ | -4% ≈ | -2% ≈ | -2% ≈ | +17% | -1% ≈ |
| 14 Dex, 13 Wis; ASI split | +2% ≈ (0.81×) | +4% ≈ | -4% ≈ | -2% ≈ | -2% ≈ | +17% | -1% ≈ |
| 14 Con, 13 Dex; ASI split | +1% ≈ (0.81×) | +2% ≈ | -7% ≈ | -2% ≈ | -2% ≈ | +23% | -2% ≈ |
| 14 Con, 13 Wis; ASI split | +1% ≈ (0.81×) | +2% ≈ | -7% ≈ | -2% ≈ | -2% ≈ | +23% | -2% ≈ |
| 14 Dex, 13 Con; ASI con first | -0% ≈ (0.80×) | +0% ≈ | -3% ≈ | -9% ≈ | -3% ≈ | +18% | -1% ≈ |
| 14 Con, 13 Dex; ASI con first | -1% ≈ (0.79×) | -2% ≈ | -6% ≈ | -9% ≈ | -4% ≈ | +19% | -2% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
