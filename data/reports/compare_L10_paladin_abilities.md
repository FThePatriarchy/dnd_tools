# Build comparison: paladin, level 10

Each row swaps the candidate into the reference party in place of its fighter and re-rates the party against benchmark v1 (5% defeat threshold, same seeds). Values are the change in rating; ≈ marks changes within noise: under 3% overall and under 10% for a single opponent type, whose rating rests on one interpolated crossing.

## Screen

Expected damage × effective HP against the level's benchmark brute; the top variants were rated.

| Variant | Screen score | Rated |
| --- | ---: | --- |
| standard | 3,623 | yes |
| 14 Con, 13 Cha; ASI con first | 3,498 | yes |
| 14 Cha, 13 Con | 3,238 | yes |
| 14 Wis, 13 Con | 3,238 | yes |
| 14 Con, 13 Cha; ASI split | 3,162 | yes |
| 14 Cha, 13 Con; ASI split | 3,162 | yes |
| 14 Wis, 13 Con; ASI split | 3,162 | no |
| 14 Cha, 13 Wis; ASI split | 2,825 | no |
| 14 Wis, 13 Cha; ASI split | 2,825 | no |

## Reference party: standard (fighter_10, cleric_10, rogue_10, wizard_10)

Base rating 9,058 XP (0.73× High).

| Candidate | Overall | brute | ranged | caster | swarm | control | solo |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 14 Cha, 13 Con; ASI split | -3% ≈ (0.71×) | +0% ≈ | +1% ≈ | +2% ≈ | -10% ≈ | -9% ≈ | -1% ≈ |
| 14 Con, 13 Cha; ASI split | -4% (0.70×) | +2% ≈ | +0% ≈ | +2% ≈ | -12% | -14% | -1% ≈ |
| 14 Con, 13 Cha; ASI con first | -4% (0.70×) | +1% ≈ | +1% ≈ | +3% ≈ | -15% | -11% | -1% ≈ |
| 14 Cha, 13 Con | -4% (0.70×) | +2% ≈ | +2% ≈ | +0% ≈ | -16% | -13% | +1% ≈ |
| 14 Wis, 13 Con | -5% (0.70×) | +2% ≈ | +1% ≈ | +1% ≈ | -14% | -16% | +0% ≈ |
| standard | -5% (0.70×) | +1% ≈ | +1% ≈ | +2% ≈ | -16% | -14% | -1% ≈ |

† a rating at the edge of its benchmark ladder (a bound), so the change is a bound too.
