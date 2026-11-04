# Build comparison: ranger, level 5

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| 14 Con, 13 Wis; ASI split | 1,180 | yes |
| 14 Con, 13 Str; ASI split | 1,180 | yes |
| standard | 1,060 | yes |
| 14 Con, 13 Wis | 1,060 | yes |
| 14 Con, 13 Str | 1,060 | yes |
| 14 Wis, 13 Str; ASI split | 1,060 | yes |
| 14 Str, 13 Con | 1,060 | no |
| 14 Wis, 13 Str | 939 | no |
| 14 Str, 13 Wis | 939 | no |
| 14 Con, 13 Wis; ASI con first | 905 | no |
| 14 Con, 13 Str; ASI con first | 905 | no |
| 14 Wis, 13 Con; ASI con first | 905 | no |
| 14 Str, 13 Con; ASI con first | 905 | no |
| 14 Wis, 13 Str; ASI con first | 812 | no |
| 14 Str, 13 Wis; ASI con first | 812 | no |

## Reference party: standard (fighter_5, cleric_5, rogue_5, wizard_5)

Base rating 3,512 XP (0.80× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Con, 13 Wis; ASI split | -7% (0.74×) | -6% ≈ | -9% ≈ | -19% | -2% ≈ | -11% | +5% ≈ |
| 14 Con, 13 Str; ASI split | -7% (0.74×) | -6% ≈ | -9% ≈ | -19% | -2% ≈ | -11% | +5% ≈ |
| 14 Con, 13 Wis | -8% (0.74×) | -6% ≈ | -9% ≈ | -19% | -2% ≈ | -13% | +5% ≈ |
| 14 Con, 13 Str | -8% (0.74×) | -6% ≈ | -9% ≈ | -19% | -2% ≈ | -13% | +5% ≈ |
| standard | -8% (0.74×) | -6% ≈ | -10% ≈ | -19% | -2% ≈ | -12% | +4% ≈ |
| 14 Wis, 13 Str; ASI split | -8% (0.74×) | -6% ≈ | -10% ≈ | -19% | -2% ≈ | -12% | +4% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
