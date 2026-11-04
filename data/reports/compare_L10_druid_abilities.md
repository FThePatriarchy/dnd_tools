# Build comparison: druid, level 10

Each row swaps the candidate into the reference party in place of its cleric and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Dex | 2,173 | yes |
| 14 Con, 13 Dex; ASI con first | 2,156 | yes |
| 14 Dex, 13 Con; ASI split | 2,116 | yes |
| standard | 2,102 | yes |
| 14 Con, 13 Dex; ASI split | 1,924 | yes |
| 14 Int, 13 Con; ASI split | 1,924 | yes |
| 14 Int, 13 Con | 1,911 | no |
| 14 Dex, 13 Int; ASI split | 1,862 | no |
| 14 Int, 13 Dex; ASI split | 1,692 | no |

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,058 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Con, 13 Dex; ASI con first | -10% (0.66×) | -7% ≈ | -16% | -6% ≈ | -19% | -11% | -1% ≈ |
| 14 Con, 13 Dex | -10% (0.65×) | -7% ≈ | -16% | -7% ≈ | -17% | -14% | -1% ≈ |
| 14 Con, 13 Dex; ASI split | -11% (0.65×) | -8% ≈ | -16% | -8% ≈ | -20% | -13% | -1% ≈ |
| 14 Int, 13 Con; ASI split | -11% (0.65×) | -8% ≈ | -16% | -8% ≈ | -20% | -13% | -1% ≈ |
| 14 Dex, 13 Con; ASI split | -11% (0.65×) | -8% ≈ | -14% | -8% ≈ | -20% | -15% | -1% ≈ |
| standard | -11% (0.65×) | -8% ≈ | -15% | -8% ≈ | -20% | -15% | -1% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
