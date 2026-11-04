# Build comparison: ranger, level 10

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Wis | 2,923 | yes |
| 14 Con, 13 Str | 2,923 | yes |
| standard | 2,612 | yes |
| 14 Wis, 13 Str | 2,612 | yes |
| 14 Str, 13 Con | 2,612 | yes |
| 14 Con, 13 Wis; ASI con first | 2,505 | yes |
| 14 Con, 13 Str; ASI con first | 2,505 | no |
| 14 Con, 13 Wis; ASI split | 2,264 | no |
| 14 Con, 13 Str; ASI split | 2,264 | no |
| 14 Wis, 13 Con; ASI split | 2,264 | no |
| 14 Wis, 13 Str; ASI con first | 2,264 | no |
| 14 Str, 13 Con; ASI split | 2,264 | no |
| 14 Wis, 13 Str; ASI split | 2,023 | no |
| 14 Str, 13 Wis; ASI split | 2,023 | no |

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,058 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| standard | -12% (0.64×) | -6% ≈ | +0% ≈ | -3% ≈ | -21% | -35% | -1% ≈ |
| 14 Wis, 13 Str | -12% (0.64×) | -6% ≈ | +0% ≈ | -3% ≈ | -21% | -35% | -1% ≈ |
| 14 Con, 13 Wis | -12% (0.64×) | -5% ≈ | +1% ≈ | -3% ≈ | -22% | -36% | -1% ≈ |
| 14 Con, 13 Str | -12% (0.64×) | -5% ≈ | +1% ≈ | -3% ≈ | -22% | -36% | -1% ≈ |
| 14 Str, 13 Con | -12% (0.64×) | -5% ≈ | -0% ≈ | -2% ≈ | -22% | -36% | -1% ≈ |
| 14 Con, 13 Wis; ASI con first | -14% (0.63×) | -6% ≈ | -1% ≈ | -5% ≈ | -23% | -41% | -1% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
