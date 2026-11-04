# Build comparison: druid, level 5

Each row swaps the candidate into the reference party in place of its cleric and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Dex, 13 Con; ASI con first | 542 | yes |
| 14 Con, 13 Dex; ASI split | 528 | yes |
| standard | 513 | yes |
| 14 Con, 13 Dex; ASI con first | 493 | yes |
| 14 Int, 13 Con; ASI con first | 493 | yes |
| 14 Dex, 13 Int; ASI con first | 479 | yes |
| 14 Con, 13 Dex | 466 | no |
| 14 Int, 13 Con | 466 | no |
| 14 Dex, 13 Int | 446 | no |
| 14 Int, 13 Dex; ASI con first | 435 | no |
| 14 Int, 13 Dex | 405 | no |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Dex, 13 Con; ASI con first | -4% (0.77×) | -1% ≈ | -12% | -12% | -4% ≈ | +10% | -1% ≈ |
| 14 Con, 13 Dex; ASI con first | -4% (0.76×) | -2% ≈ | -14% | -11% | -8% ≈ | +10% | -1% ≈ |
| 14 Int, 13 Con; ASI con first | -4% (0.76×) | -2% ≈ | -14% | -11% | -8% ≈ | +10% | -1% ≈ |
| 14 Con, 13 Dex; ASI split | -5% (0.76×) | -2% ≈ | -12% | -8% ≈ | -4% ≈ | -1% ≈ | -1% ≈ |
| standard | -5% (0.76×) | -1% ≈ | -11% | -11% | -6% ≈ | +2% ≈ | -1% ≈ |
| 14 Dex, 13 Int; ASI con first | -6% (0.75×) | -3% ≈ | -14% | -13% | -8% ≈ | +2% ≈ | -1% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
